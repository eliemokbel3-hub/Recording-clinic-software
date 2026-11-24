# Feature Implementation Plan
**Feature:** stronger-voice (guided enrolment and matching within a consult; line splitting and several voice vectors measured for a follow-up plan)
**Overall Progress:** `84%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None
- Follow-up plans: one expected, not yet written: the build of line splitting and of several stored voice vectors, if this plan's measurements support them (Deferred, below).
- Related: `plan-practitioner-profile.md` (this plan amends its D3, D8 and D13; its D-P1 pass mark stays 0.50); `plan-ui-refresh.md` (its deferred Phase 6 keeps the number 0.4.1); `plan-phase3a-note-pipeline.md` (Task 9.1's ten consultations restart after this plan's install); `docs/testing/exit-gate-options.md` (route 4, a product change for one failure family).

## Goal
Make the app label who is speaking correctly in a real consultation. Two levers are built, each measured first: (A) a guided voice enrolment with an on-screen reading script that covers the practitioner's normal, quiet, short-phrase and turned-away speech; (B) matching that uses the consultation itself to recover the practitioner's lines near the pass mark. Two more are measured here and built, if at all, by a follow-up plan: (C) splitting a transcript line where the speaker changes, and several stored voice vectors. Then one release (0.4.2), a re-enrolment, and the restart of Task 9.1's ten consultations. Shadow mode stays on. No gate claim. Settled at Task 0.7 (2026-11-21, "Confirm B1-35"): Lever B is row B1-35, a fixed recovery mark at 0.35 under the pass mark. After a match it recovers practitioner lines that score from 0.35 to just under 0.50; it does not draw on the rest of the consultation, which was the session-adaptation rows' approach (B2/B3, not built).

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.2; executor `claude-opus-5-5` high, peer codex `gpt-6.2-astra` (the practitioner's "Entirely premium (Recommended)", 2026-11-20); tier-gap dosing applied (design decisions, the function contracts, the edge-case inventory, the bars and the measurement definitions are fixed here).

### Agreed Scope (Build Now)
- Phase 0: measure, in scratch only, with truth by construction (D2) and numbers-only real speech (D7); freeze the bars first; select what is built by one fixed order (D9).
- Lever A, guided enrolment: built in any case (the practitioner's request, 2026-11-20). One stored vector; no schema change.
- Lever B, matching within a consult: the first candidate in D4's ordered table that qualifies under D9; none means Lever A alone. Settled at Task 0.7 (2026-11-21): row B1-35.
- Lever C (splitting a merged line) and several stored voice vectors: measured in scratch against their frozen bars and reported; not built by this plan (the practitioner's "Measure now, build next (Recommended)" and "Measure now, build later (Recommended)", 2026-11-20).
- Regression on the seven seen synthetic sets, before and after, and product parity on the stitched truth.
- One release, 0.4.2, installed with shadow mode on; the practitioner re-enrols; Task 9.1 restarts at C01 with a fresh config hash.
- The practitioner's words (2026-11-20): "Lets plan the in-app version. I want a good script written for it, that tests all the weaknesses (normal talking and quiet sentences so have a que for when to speak quiet). and anything else you can think of to make it better than it is now"; "All three, Monday can slip"; "No labelling"; "Yes, record it (Recommended)"; "Accept, memory only (Recommended)".

### Deferred — Actionable Later
- Building Lever C (splitting a merged line) and several stored voice vectors.
  - Why deferred: the cross-family review's second round (2026-11-20) found the build of each under-specified in ways that need their own design pass; the practitioner chose to measure both now and build them next.
  - Intended future outcome: a quick back-and-forth appears as two lines, one per speaker; a profile that keeps one vector per part of the script if that beats the single mean.
  - Relevant files / subsystems: `transcription.py` (window-time sub-window vectors and cut candidates in both drivers, the split inside `assemble_transcript`, one scorer), `speaker_eval.py` (its equal-boundaries check and its printed counts), `practitioner_profile.py` (a schema v2), `note_check.py` and `note_config.py` (readers that take a line's first word or look ahead inside a line), `consultation_phrases.py` (the three-segment look-back).
  - Dependencies / prerequisites: this plan's tables for bar C and bar A2; this plan's Lever B built.
  - Recommended next action: a follow-up plan in Plan Mode, seeded by this plan's tables and by these open design points from review round 2: the final pieces when one line holds several cuts, frame alignment and the live path's zero-padded last frame (PR-MED-008); the measurement harness's per-condition counts after a split (PR-MED-009); a cut that moves a line's first word or separates a number from its unit, which changes a warning or a learning refusal (PR-MED-012); a live speed check at real-time cadence (PR-MED-014); centre parameters when no session-rule row is built (PR-HIGH-006); a split that is right in time and wrong in speaker (PR-HIGH-009); a v2 profile's minimum number of vectors and its consent renewal (PR-MED-015); readiness readers that have no audio to score (PR-MED-016); whether `consent-v3` covers several vectors.
  - Risk if deferred: ux-degradation: a quick back-and-forth stays one line under one label, so one speaker's words in it carry the other's label; the practitioner corrects it at review.
  - Revisit by: revisit-when: this plan's Task 0.7 brief is read (the tables say whether either is worth building), and again when the ten consultations are scored.
- Two-tier clinician labels: a line matched only by the session rule (below the pass mark) is labelled the practitioner's and flagged, but not auto-placed in a clinician-owned section. (Task 0.7, 2026-11-21: with B1-35 built, that line is one the recovery mark labels, on its own score from 0.35 to under 0.50 after a direct match.)
  - Why deferred: it needs a new stored transcript field (older builds could not read new transcripts) and about a day; the practitioner chose "Defer (Recommended)" on 2026-11-20.
  - Intended future outcome: a wrongly matched patient line can never enter assessment, diagnosis, advice or plan unflagged, and never teach a phrase or a shorthand rule.
  - Relevant files / subsystems: `transcription.py` (`TranscriptSegment`), `note.py` (`admissible_sections`, the router), `note_config.py` (the phrase learners), `ui/note.py` (the edit-to-rule learner), `ui/models.py` (the line chooser).
  - Dependencies / prerequisites: this plan's Lever B built; evidence from the ten consultations.
  - Recommended next action: decide after the ten are scored, and in any case before shadow mode is turned off.
  - Risk if deferred: correctness: a patient line labelled the clinician's by Lever B can enter a clinician-owned section with no warning and, outside shadow mode, teach a phrase or a shorthand rule; controlled by D4's guards, shadow mode and the practitioner's review.
  - Revisit by: revisit-when: any of the ten consultations shows a patient line in a clinician-owned section (rubric R4), or the ten are complete, or shadow mode is about to be turned off.

### Excluded — Revisit Only If Needed
- Routing of lines that match no section cue.
  - Why excluded: a different failure family (four plans of measurement); this plan fixes who said a line, not where it goes. Task 0.5a reports, on the synthetic sets only, how many note lines correct labels would add and how many clinician lines would still be left out.
  - When to revisit: after the ten, from `docs/testing/exit-gate-options.md`.
  - Relevant files / subsystems: `note.py` (the router), the cue files.
  - Recommended next action (if any): none here.
- A third voice in the room (D-S1), the VAD constants, the `GUARD_*` constants, the recogniser, the primer, the cue file, the frozen vocabularies, the rule files, the held-out sets, the prompts, the consent text, any harness credit change.
  - Why excluded: frozen or owned by other plans; none is needed here.
  - When to revisit: only by its own dated decision.
  - Relevant files / subsystems: as named.
  - Recommended next action (if any): none.
- A side-by-side comparison with another scribe product: not part of this plan. A content-free comparison sheet was offered in chat; nothing about it enters the repository.

### Accepted Assumptions — Revalidate Later
- False matches against real patients are not measured.
  - Why accepted for now: the practitioner chose "No labelling" (2026-11-20); the other voice in the truth set is a computer voice.
  - Risk if assumption becomes false: Lever B labels a real patient's line as the practitioner's. Three consequences, each stated in Task 0.7's brief and in the threat model: (1) the line can enter a clinician-owned section with no warning; (2) in normal mode with learning on, such a line that the practitioner adds or moves and then saves can teach a phrase, kept in a plain config file until deleted, although the consent says only the practitioner's own lines are used; (3) in normal mode, a typed edit over such a line can queue its original words as a shorthand trigger, and Save can write the trigger and the typed text as an autofill rule that later pre-fills notes. Shadow mode teaches nothing, so the ten consultations cannot show (2) or (3).
  - Trigger for revisit: any R4 breach in the ten; the decision to turn shadow mode off.
  - Recommended next action: read rubric R4 on the ten; decide the two-tier Deferred item before shadow-off.
- The consent text `consent-v3` covers the guided enrolment ("A numeric fingerprint of your voice (never a recording), encrypted"): one vector, no audio saved.
  - Why accepted for now: nothing about what is stored changes.
  - Risk if assumption becomes false: a stored artefact the consent does not describe.
  - Trigger for revisit: the follow-up plan's several vectors. This plan never changes the consent text (C6).
  - Recommended next action: none here.

### Key Design Decisions
- Measure before building, with the bars frozen first (D1, Task 0.2).
  - Why: this project's rule since run 5; a bar chosen after the numbers is not a bar.
  - Alternatives rejected: build everything and judge on Monday's consults (no way to tell which lever helped or harmed).
  - Still applies to follow-up work: Yes
- Truth by construction instead of labelling a consultation (D2).
  - Why: the practitioner declined labelling; their own script recordings and a computer voice have a known speaker for every sample.
  - Alternatives rejected: Audacity labels on a kept consultation (declined); synthetic sets alone (almost no merged turns, and no voice is the practitioner's).
  - Still applies to follow-up work: Yes
- One fixed order decides what is built, with Lever A alone as its last case (D4, D9).
  - Why: a recovery mark under the pass mark is one constant; session adaptation is new logic and a new in-memory custody; an order fixed before the numbers leaves no choice to make after them.
  - Alternatives rejected: always building session adaptation; choosing the best-looking row.
  - Result (Task 0.7, 2026-11-21): the order selected B1-35, and the practitioner confirmed it.
  - Still applies to follow-up work: Yes
- Lever B never removes a practitioner label today's rule gives, and never changes how a clinician is confirmed (D4).
  - Why: the fault observed is practitioner lines lost to the other label; a rule that only adds, and only when today's rule has already confirmed the practitioner, cannot make today's confirmed lines worse.
  - Alternatives rejected: re-deriving the clinician and the Review screen's number from the new labels (two review rounds found undefined cases each time).
  - Still applies to follow-up work: Yes
- Speaker-model vectors may be held in memory for the transcription pass, never stored, in scratch as in the product (C4).
  - Why: the session rule cannot work from one number per segment; the practitioner accepted it ("Accept, memory only (Recommended)", 2026-11-20).
  - Alternatives rejected: storing vectors in the transcript (a biometric of the patient at rest); a scratch cache of vectors on disk (the same rule applies to synthetic audio, so one rule has no exception to police).
  - Settled for this plan's product build (Task 0.7, 2026-11-21): the built row B1-35 reads one number per segment, so the product keeps no vector, and C4's owner, collection helper and live handover are not built here. The rule still holds for scratch, and for the follow-up plan if it builds session adaptation or several vectors.
  - Still applies to follow-up work: Yes

## Key Findings

### Files / Symbols Involved
- `desktop/src/scribe_desktop/enrolment.py`: `record_enrolment` (per-call `target_speech_seconds`, `max_seconds`; one stream per call; speech counted per VAD frame at the start threshold; returns the whole captured PCM, pauses included, when the target is reached; `EnrolmentTooShortError` when `max_seconds` of audio arrive first, `EnrolmentCaptureError` for the device or ten seconds without a block, `EnrolmentCancelledError` for Stop), `enrol` (re-segments the PCM; mean of per-segment vectors; its seconds are the stored figure), `EnrolmentProgress` (seconds and level only).
- `desktop/src/scribe_desktop/ui/practitioner.py`: the "Record your voice" group, `on_record`, the `TaskThread` worker, `_progress_text` (its denominator is the module constant), the progress slot (near :1119, updates only on a captured block), the success handler (near :1143, ignores its result), the seams `CaptureFn` and `EmbedFn` (`EmbedFn` returns only a mean and seconds), `_update_controls`.
- `desktop/src/scribe_desktop/ui/models.py`: `CONSENT_TEXT_V3`, `consent_is_current`, `attribution_readiness`; the home for Qt-free strings; the live receiver (near :4796-4830: `worker.drain()`, the header read, `result.assemble(...)`, `worker.stop()` in `finally`, then the transcript write).
- `desktop/src/scribe_desktop/practitioner_profile.py`: `PractitionerProfile` (`schema_version: Literal[1]`, `extra="forbid"`, one `embedding`); not changed by this plan.
- `desktop/src/scribe_desktop/session.py`: `begin_enrolment` / `end_enrolment` (the lease); the controller keeps an uncleared live worker attached and refuses destructive steps.
- `desktop/src/scribe_desktop/speaker_embedding.py`: `ATTRIBUTION_THRESHOLD = 0.50`, the embedder (256-dim, variable-length input).
- `desktop/src/scribe_desktop/transcription.py`: `label_speakers` (:822, the plain two-speaker clustering, no enrolment argument), `_cosine` / `_unit_vector` (:871-897), `enrolled_cluster` (:900), `attribute_speakers` (:937), `transcript_before` (near :1403), `assemble_transcript` (:1652, the one speaker pass for both drivers), the batch loop's per-segment embedding reduced to one number (near :1833-1849), `LiveTranscriber` (`_build_result`, `drain`, `stop`), `TranscriptWord` (absolute `start_seconds` / `end_seconds`).
- `desktop/src/scribe_desktop/speech.py`: `segment_pcm` (returns spans only; `pad_seconds`, 0.10 s by default, clamped to the audio and merged when padding makes spans touch), `MIN_SILENCE_SECONDS = 0.35` (unchanged by this plan).
- `desktop/src/scribe_desktop/speaker_eval.py`: `score_document`, the plain-against-enrolled boundary check (:1180-1197, which uses `label_speakers` for the plain condition), `transcribe_in_temporary_store`, `enrolment_inputs`, `read_wav_pcm`.
- `desktop/src/scribe_desktop/ui/note.py` (:104-127): a typed edit over a clinician line can queue its original tail as a shorthand trigger; Save can write it to `autofill_rules.json`. `desktop/src/scribe_desktop/note.py` (near :1688): phrase learning reads the same clinician label.
- `desktop/src/scribe_desktop/replay_kept.py`: `_load_models`, `_open_store`, the refusal order; it reads one enrolment WAV and refuses a directory.
- `desktop/src/scribe_desktop/validation.py`: the report embeds its commit id (near :3958), so two reports from different commits never share a hash; `validation.py:3414` and `:4763` build each synthetic clinician's profile from that voice's one passage.
- Scratch frames (frozen records, loaded by SHA-256, never edited): `.cursor/loops/ffl-measure-kept.py` (it puts its own folder on the import path and imports `ffl_lib`), `.cursor/loops/lcm-measure-kept.py` (it checks `ffl_lib.py` separately before running the verified frame bytes), `.cursor/loops/ffl_lib.py` (`replaying`, `replay_encounter` with the gate configuration's two stages, `majority_label`), `.cursor/loops/lcm_lib.py`.
- `desktop/src/scribe_desktop/validation_set.py`: `GAP_SECONDS = 0.6` (a script may also place overlapping turns), `ENROLMENT_PASSAGE` (pinned by SHA-256 in tests: copy, never import, never edit).
- The measurement folder already holds `enrolment\me.wav` (`docs/testing/kept-recordings.md`; its own row in `docs/security/retention-schedule.md`); this plan neither moves nor deletes it.

### Codebase Integration Notes
- **Why lines are mislabelled today.** One cosine per VAD segment against one enrolled vector; at or above 0.50 is the practitioner, everything else the other speaker; no smoothing. Clean clips scored 0.85 to 0.89 (D-P1's record).
- **How a clinician is confirmed today.** `enrolled_cluster` takes the labels, each segment's score and whether it holds text. Among labels that hold at least one text-bearing segment and at least one score, it returns the one with the highest mean score (the earlier label on a tie) and that mean. With a match, `speaker_1` is exactly the segments at or above 0.50, so a Review number of about 0.55 means the matches sit just above the pass mark. With no match, an ordinary 2-means over spectral features runs first, and a cluster can be confirmed with every score below 0.50. In that no-match branch `attribute_speakers` swaps the two labels when needed, so the confirmed cluster is `speaker_1` there too. This plan does not edit `enrolled_cluster` or `attribute_speakers`.
- **What a mislabelled practitioner line loses.** It is shut out of the four clinician-owned sections and of their chooser, opens no answer window, and draws no `clinician_line_omitted` warning. It can still draw `high_risk_omission` when it holds a number, side, dose, negation or medication word.
- **What the clinician label also gates.** Phrase learning and the edit-to-rule shorthand learner both read the label, so a wrongly labelled line is a learning input outside shadow mode (Accepted Assumptions).
- **Why lines merge.** A segment ends only after 0.35 s of silence and is never split. Not changed by this plan.
- **Today the model vector never outlives the loop iteration** (the comment in the batch loop). C4 changes that on purpose, and only when the built row needs vectors.
- **A live stop can time out.** `LiveTranscriber.stop` returns False when the worker has not exited; the worker then clears its own buffers when its blocked call returns, and the controller refuses destructive steps meanwhile. On success the worker's data moves into a frozen `LiveResult` that `drain` hands to the receiver, which holds it across a header read, assembly, the stop and the transcript write.
- **A trimmed transcript keeps its clinician.** `transcript_before` keeps the original clinician and number whenever a remaining segment with that label holds text; nothing is recomputed.
- **Score edge cases.** A segment under 25 ms has no score (`None`) and never matches; a zero or non-finite vector scores -1; `_unit_vector` refuses a directionless mean.
- **Found in review round 3 (each verified in the code).** `record_enrolment` queues at most 256 blocks with a non-blocking put, and an overflow is a capture failure; it calls `on_progress` once per block it has consumed. The live worker publishes its result before `drain` claims it, and both `stop` and the worker's exit clean-up can drop that result. The live receiver's `finally` holds only `worker.stop()`; the transcript write comes after it. `speaker_eval.py` (near :1133) already clears an exception's traceback frames for a custody reason of its own. `ffl_lib.replay_encounter` uses a scratch routing provider unless a `factory` is passed. The harness returns `role_unresolved` before it composes a note when its truth track disagrees with the stored clinician, while the Review screen preselects the stored clinician. A harness outcome holds a wall-clock figure (`suggestions.model_seconds`). `test_speaker_embedding.py` pins `ATTRIBUTION_THRESHOLD == 0.50`. The retention schedule (its learned-phrase and shorthand rows) and threat-model surface 10 say without condition that a patient's line never reaches learning; the code tests the speaker label.
- **Found in review round 4 (each verified in the code).** `assemble_transcript` labels every segment `speaker_1` without calling `attribute_speakers` when a slice was empty or fewer than two segments could be embedded, and still records a clinician and a number then. On a normal seal the live worker publishes its result and runs its exit clean-up before `drain` reads the result; that clean-up drops the result only after a failure or a requested stop. A `TranscriptWord` also carries a raw `probability`, which Check 2 reads. `transcribe_in_temporary_store` writes the audio to an encrypted temporary store even with `persist_key=False` (only the key stays in memory). The live segmenter force-closes a span at 30 s; the batch path keeps it whole. `ffl_lib.majority_label` breaks an exact tie by label name. The Practitioner tab's busy state reads the worker thread's running flag, so a finished worker whose result is still queued looks idle to the availability poll; and a failed microphone handoff releases the lease before the error is shown. The Review screen's line for a line that cannot teach says "only your own lines are learned" (`ui/models.py`, `LEARNING_NOT_ATTRIBUTED_NOTE`); the code tests the label. With a current consent record the consent box is already ticked and disabled and the button reads "Re-record my voice".
- **Enrolment tests** fake capture with `_FakeCapture` and the embedder with `_StubEmbedder`, which fails if called directly (`test_ui_screens.py`), under a ten-second deadline; `test_enrolment.py` feeds `MockCaptureBackend` 100 ms blocks. Pinned strings and counts that a guided flow moves: "Speech heard: 12 s of 30 s", "Record my voice (about a minute)", `capture.calls == [(7,)]`, the stored `enrolment_speech_seconds == 31.0`, the busy-state enablement list.
- **Package-wide pins that apply to the new card** (`test_shadow_exits.py`, not edited): no selectable-text flag, lists and combos only from `ui/lists.py`, no clipboard or drag call, no new `wave` reference, no new `write_wav` reference.
- **Design system.** No dialog beyond a short confirmation, no collapsible section, no sub-page; a disabled control is shown with its reason; progress is numbers over a Qt signal; plain clinical English, no exclamation marks.
- **Shared helpers (reuse, do not re-invent):** `record_enrolment`, `enrol`, `segment_pcm`, `_cosine`, `_unit_vector`, `enrolled_cluster`, `enrolment_inputs`, `transcribe_in_temporary_store(persist_key=False)`, `ffl_lib.replaying` / `replay_encounter` / `majority_label`, the ffl frame's refusals and paste-block pattern.
- **Version places:** `desktop/pyproject.toml`, `desktop/src/scribe_desktop/__init__.py`, `extension/package.json`, `extension/package-lock.json`, `extension/src/manifest.ts`; two tests carry the string (`test_ui_shell.py`, `test_ui_phase_s.py`).
- **Lessons that apply** (`docs/lessons.md`): measure the real model before claiming a rate; a worker-custody rule must state the join-timeout case, and a moved plaintext bound earns a fresh cross-family round (C4 is one); per-phase convergence is not whole-surface convergence (Step H); agent shells cannot verify anything under `%LOCALAPPDATA%`.

### External / API Findings
N/A.

## Planned Workflow Summary

### Flow 1 — Measure (Phase 0)
- The practitioner approves the reading script and the bars. They record the script twice and a computer voice once, as plain WAV files in a new subfolder of their measurement folder.
- The agent builds the seven seen sets and decodes each once, measuring every table row while each encounter is in memory. The practitioner runs two numbers-only scripts: one over their own script recordings (tables pasted whole: no patient content), one over kept consultations (words against the bars only).
- The fixed order selects what is built. A plain-English brief sets the tables against the bars, including the two measured for the follow-up plan; the practitioner confirms.

### Flow 2 — Guided enrolment (after install)
- On the Practitioner screen the practitioner presses the record button. With a current consent record (the installed path after 0.4.0) the consent box is already ticked and the button reads "Re-record my voice"; on a first enrolment, or when the consent is out of date, they tick consent first. The card shows part 1 of 6 with its cue and passage; when enough speech is heard there is a three-second "get ready" beat and the next part appears.
- If a part did not match the rest, the weakest one is named and recorded again, once. The profile is saved, and a strength line says in plain words how well the parts matched each other.

### Flow 3 — A consultation after the change
- With Lever B built, lines the practitioner spoke quietly or briefly are labelled theirs. As built (B1-35, Task 0.7, 2026-11-21): a line that scores at or above 0.35 is labelled theirs whenever at least one of their lines matched at the pass mark and today's rule confirms them. A left-out practitioner line draws its warning. A quick back-and-forth is still one line (the follow-up plan).

### Flow 4 — Release and restart
- Build of record, re-verify, install with shadow mode on, re-enrol, mock smoke, a fresh config hash, then C01.

## Design Decisions
- **D1 — Scratch first.** New `.cursor/loops/sv_lib.py`, `sv-measure.py` and `sv-measure-kept.py`. Nothing under `desktop/`, `scripts/`, `validation/` or `extension/` changes before Task 0.7.
  Alternatives considered: building behind a flag and measuring the product (a flag is product code and would ship).
- **D2 — Truth by construction.**
  - Recordings (Task 0.3), 16 kHz mono 16-bit, in a NEW subfolder of the measurement folder, `stronger-voice\`: two takes of the six-part script at the consulting seat, one file per part (`me-a-1.wav` to `me-a-6.wav`, `me-b-1.wav` to `me-b-6.wav`), and `other.wav` (a Windows voice reading a synthetic patient text through the laptop speakers, recorded through the same microphone). Each part file runs for at least twice its part's target (60 / 30 / 25 / 30 / 25 / 30 s), the passage read again when its end is reached; `other.wav` runs for at least 120 s. The script checks that folder against its own thirteen-name manifest and refuses a missing or extra file with the count only; it also refuses, naming the file, an `other.wav` or a required part (1, 3, 4 or 6) of either take in which the VAD finds no speech. An optional part (2 or 5) with no speech is not a refusal: it is left out, as a part short at its cap is, and the quiet pool then reads `unmeasured`. The existing `enrolment\me.wav` is passed separately (`--enrolment`) and is not part of the manifest.
  - Profiles. P0 = the existing `me.wav`, built as the speaker measurement builds it today. P1 = take A through the product's own capture limits: each part file is fed to `record_enrolment` through a file-backed capture in 100 ms blocks with that part's target and cap, and the returned audio goes to `enrol`; one vector, the equal-weight mean of the part vectors. The capture hands over one block, and the next one only when `record_enrolment` reports progress on the one before, so its 256-block queue never overflows and no wall-clock wait is needed. A file that ends before its target is followed by digital silence up to the part's cap, so the product's own cap decision is the outcome: a short required part refuses the take, naming the part number; a short optional part is left out, and the table says so. P2 = exactly P1's retained part vectors, kept apart and scored as the best match: the same audio and the same pass mark, so only mean against best-part scoring differs; measured for the follow-up plan only. Take B's part vectors are built the same way (the parts it retains), for the part-consistency calibration only. The one redo is not simulated, and the tables say so.
  - Custody of the stitched audio. A stitched dialogue is built in memory and is never written in the clear. The product's batch driver reads its audio from a session store, so wherever a dialogue is run through the real pipeline it goes through `transcribe_in_temporary_store(persist_key=False)`: an encrypted temporary store whose key exists only in memory and which is destroyed when the pass ends, the custody D7 uses for a kept consultation. Both stitched runs (Tasks 0.5b and 4.3) use it, and both exercise the batch driver end to end: the store read, the VAD, the decode and assembly.
  - Spans and turns. Speech spans come from the VAD with its padding option at zero (`pad_seconds=0`), clamped to real samples. For each speaker one sequence of turn targets is drawn, uniformly from 1 to 8 s with the fixed seed 20261120, once, and used for all four gap values, so the four mixed dialogues hold the same turns. Spans are taken in recorded order and added to the open turn, joined by 0.15 s of digital silence, until it is at least its target. A span longer than 8 s is always a turn by itself; a turn that is open when one arrives is closed as it stands. A closed turn under 1 s is dropped and counted. Take B's turns alternate with `other.wav`'s; when the other voice's spans run out they start again from its first unreserved span (counted); a dialogue ends when its practitioner spans are used up. Truth seconds are span samples; silence belongs to no one. A true transition is the midpoint of the gap between two turns.
  - The dialogues: four mixed dialogues over take B, one per gap value 0.10, 0.20, 0.35 and 0.60 s (the gap is digital silence between two turns); and six part dialogues at 0.60 s, one per part's spans. The 0.10 s and 0.20 s dialogues each begin with a calibration preamble that is never scored: whole spans only: take B's part-1 spans in order while the running total stays at or under 25 s of speech, and `other.wav`'s spans in order while it stays at or under 10 s (at least one span of each, even when the first is longer), each span followed by 0.60 s of silence. Without it a close-turn dialogue would reach the VAD as one long segment and no speaker centre could be formed. Those spans are reserved in all four mixed dialogues, so the four bodies hold the same turns, built once; only the two close-turn dialogues play the preamble, and the other voice's restart skips the reserved spans. If the reservation leaves either speaker with no turn of at least 1 s, the script refuses, naming the file, before any dialogue is built. The self-test asserts that no source sample is in both a preamble and a scored body.
  - Pools, each dialogue in one pool only: overall = the 0.60 s mixed dialogue; quiet = the part-2 dialogue; close-turn = the bodies of the 0.10 s and 0.20 s dialogues. The other part dialogues and the 0.35 s dialogue are reported and gate nothing.
  - The quiet pool is scored only on speech the VAD detects, and only when each take's quiet file holds at least 8 s of detected speech; otherwise its lines read `unmeasured`.
  - Seen sets: the 50 and `heldout`, `heldout-2` to `heldout-6`, built into a new `C:\sv-sets\`. Their profiles are each set's own one-passage profile per synthetic clinician voice, as the harness builds it: the seen sets test Lever B's rule and its harm, not the reading script, and every seen-set table says so.
  - One scratch pass per encounter, with the audio in hand, decodes it with the real pipeline and, while the encounter's vectors are in memory, evaluates every row of D4's table, every point of D5's grid and Task 0.5a's line comparison. Inputs per segment: its original span, whether it holds text, its words, its speaker-model vector, its spectral features (the no-match branch uses them) and its score. Written to `.cursor/loops/sv-out/` (synthetic only): every field of every word (text, times, probability, marks), the spans, text flags and scores, and which branch assembly took; for each row id the labels, the confirmed clinician, the number and whether the row changed any label; for each grid point whether centres could be formed, eligible mixed seconds, mixed seconds before and after, the proposed and the kept cut counts, the kept cut times, the piece labels, the matched, wrong and excluded cut counts, the exposure and the embedding time; Task 0.5a's line lists. No vector and no cut candidate is written (C4); a restarted run decodes again.
  - Truth on the seen sets comes from the generated label tracks, read as two classes: the clinician, and everyone else. Speaker seconds are counted per class. A transition is a change between the two classes; across a silent gap its instant is the gap's midpoint. A segment's true class is the class with more overlap seconds; an exact tie is detected before any class is chosen (the reused `majority_label` would break it by label name), and a tied or non-overlapping segment keeps its measured label and is counted. A region where a script overlaps two turns is excluded alike from transition truth, from cut scoring and from exposure; cuts that fall inside one are counted on their own line and are neither right nor wrong.
  - Stated on every table: the other voice is a computer voice; digital silence fills the stitched gaps; the seen sets hold almost no turn closer than 0.6 s, so they show Lever C's harm, not its benefit; take B and the seen sets both select and qualify a row, so the tables are qualification on reused data, and the ten consultations are a later observation without hand-labelled truth.
  Alternatives considered: one take (the profile would be tested on its own audio); cutting one long take at silences (part 3 asks for pauses); six-part surrogate profiles for the synthetic clinicians (the profile stays one vector in this plan, the same form the sets already use); a memory-backed stand-in for the session store (new scratch code at the product's store boundary, where the existing encrypted temporary store already has a reviewed custody).
- **D3 — Lever A, guided enrolment.**
  - The script is data in `ui/models.py`: `ENROLMENT_SCRIPT`, a tuple of six parts, each with `key`, `cue`, `title`, `text`, `target_speech_seconds`, `max_seconds`, `required`. Targets 30 / 15 / 12 / 15 / 12 / 15 s of speech (99 s); each cap three times its target and at least 45 s. Parts 2 (quiet) and 5 (moving away) are not required; the rest are. Under every passage the card shows one fixed line: "Keep reading until the counter fills. If you reach the end, start the passage again."
  - One lease across everything: every part, each "get ready" beat, the embedding, the redo, the save and the result handler. One worker; `record_enrolment` is called once per attempt and is not changed. The beat is an injected, cancellable wait (3 s in the app, instant in tests) with no stream open; Stop, screen lock and sleep end it at once.
  - The embedder is built before the first part, as today. Each part's audio is embedded and dropped before the next part starts. The injected per-part embedder returns a typed result: the part's mean vector, its speech seconds (`enrol`'s figure, the one stored) and its per-segment vectors; `enrol`'s existing contract stays for the measurement callers. Only those numbers stay in memory until the save.
  - Events, numbers only, in order over the existing signal: a part start (part index, part count, target seconds, whether it is the redo), a beat start (the next part's index, the beat's seconds), and progress (part index, attempt, speech seconds, level). `EnrolmentProgress` is not changed; the worker wraps it. On a part start or a beat start the meter shows zero and the counter restarts; a progress event for any part or attempt other than the current one is dropped. The success result carries only what the card shows: total speech seconds, the strength share, each left-out part's key with the seconds of speech last heard in it, the key of a part still weak.
  - A part that is not required is left out only when its capture ends at its cap short of its target (`EnrolmentTooShortError`). The line names the part and what was heard: "Only 6 s of speech was heard in the quiet part, so it was left out. Speech that quiet or that far from the microphone may not be heard in a consultation either." Every other failure ends the enrolment with nothing saved: the same shortfall on a required part, an embedding that finds no usable speech in a part, a device failure, a cancellation.
  - Consistency and the one redo. When every part has been captured or left out, each captured part's vector is scored against the unit mean of the other captured parts' vectors. If any figure is under the calibrated figure (Validation), the lowest one (the earlier part on a tie) is named ("The quiet part did not match the rest.") and recorded again, once per enrolment, under the same lease and stop rules. The redo replaces that part's vector, seconds and segment vectors whole. A redo that ends at its cap short of its target keeps the first attempt. The figures are then computed once more; if any part is still under the figure, the lowest one (the earlier part on a tie) is named in a weakness line, and the profile is saved. There is no second redo.
  - Stored profile: one vector, the normalised equal-weight mean of the captured parts' vectors (final attempts only); `enrolment_speech_seconds` is the sum of their seconds. No schema change; it satisfies `PractitionerProfile`'s validators and `made_by` as today's vector does.
  - Strength line after saving, computed in memory, not stored: the share of the final attempts' segments at or above the shipped pass mark against the profile built without their part, in plain words with the one number.
  - Stop, screen lock and sleep end the sequence with "Enrolment stopped - nothing was saved." as today; the two existing stop checks stay, the second just before the save.
  Alternatives considered: a wizard dialog (the design system forbids sub-pages); one long capture (no per-part check, and the quiet part would be averaged away); a redo per weak part (each replacement changes which other parts read as weak, with no fixed end).
- **D4 — Lever B, matching within a consult.** One ordered candidate table with fixed ids; the first row that meets its bars is built (D9). `R0` is today's rule, the baseline and the last case.
  - One condition for every row. A row runs only when assembly reached `attribute_speakers` (not its single-speaker shortcut for an empty slice or fewer than two usable segments), that call matched (at least one segment scores at or above the pass mark, 0.50), and `enrolled_cluster` over today's labels returns `speaker_1`. Otherwise today's outcome stands whole. No row runs in the no-match branch or in the shortcut. The row's one call sits in `assemble_transcript`'s attribution branch.
  - One guarantee for every row. Only a segment scoring under the pass mark can be relabelled, and only to `speaker_1`; every segment at or above the pass mark keeps `speaker_1`. A segment with no score (`None`) or a directionless vector (score -1) is never relabelled. Acceptance: `enrolled_cluster` over the new labels must still return `speaker_1`; if it does not, the row's changes are discarded whole and today's labels stand. The stored clinician and number are today's: `speaker_1` and the number `enrolled_cluster` returned over today's labels (the mean of the direct matches), so the number keeps its meaning. `ATTRIBUTION_THRESHOLD`, `attribute_speakers` and `enrolled_cluster` are not edited.
  - `B1-45`, `B1-40`, `B1-35`, `B1-30`: a recovery mark at 0.45, 0.40, 0.35, 0.30. Every segment scoring at or above the mark and under the pass mark becomes `speaker_1`. One number per segment is enough; no vector is kept. For a B1 row the acceptance check cannot fail (every segment it leaves as the other speaker scores under every segment labelled `speaker_1`); it stays one rule for the table, and a test asserts that invariant.
  - `B2-01` to `B2-36`: session adaptation. Parameter order (the id order): low bar 0.20, 0.15, 0.25; within it margin 0.05, 0.10, 0.00; within it seed floor 20 s, 10 s; within it centre guard 0.5, 0.6.
    - Seeds are segments of 1.0 s or more scoring at or above the pass mark. The practitioner's centre is the unit mean of the seeds' vectors; the other speaker's centre is the unit mean of the vectors of segments scoring under the low bar; a segment with no score or no direction is in neither.
    - A segment under the pass mark becomes `speaker_1` when its cosine to the practitioner's centre exceeds its cosine to the other centre by more than the margin. An equal distance at margin 0.00 changes nothing. One pass, computed from today's labels.
    - No adaptation, and today's labels stand, when: seed speech is under the seed floor; no segment scores under the low bar; either centre has no direction; or the two centres' cosine is above the centre guard.
  - `B3-01` to `B3-36`: the same-numbered B2 row, then smoothing. A segment under 1.5 s that scores under the pass mark and that B2 left as the other speaker takes `speaker_1` when both its neighbours, read from the labels after B2, are `speaker_1`. B3 runs whenever B2 formed its two centres and passed every guard, whether or not B2 changed a label; when a guard stopped B2, B3 does nothing. The acceptance check runs after B3. B3 is never built without B2.
  - Lever B therefore only adds practitioner labels to today's, and only in a consultation where today's rule has matched and confirmed the practitioner. This holds for every row.
  - A trimmed transcript keeps its clinician and number by today's rule, unchanged: after a trim the remaining practitioner lines may all be relabelled ones while the number comes from direct matches that were trimmed away. A test pins it and the threat model states it.
  - Vectors are kept (C4) only when the built row is a B2 or B3 row.
  Alternatives considered: lowering the pass mark itself (it can move a consultation between the two branches, take a practitioner label away and change the number: review round 3); a threshold learned per session (rejected in the practitioner-profile plan's D3; every row here keeps the fixed pass mark and is a new dated decision); re-clustering every segment (splits one voice in two, D13's finding); deriving the clinician and the number from the new labels (undefined when no direct match holds text).
- **D5 — Lever C, measured only.** Scratch applies this rule, in memory, to the stitched truth and the seen sets; nothing of it is built.
  - Frames are consecutive 512-sample (32 ms) frames from the segment's first sample; a last partial frame is dropped. Each segment of at least a floor length is embedded in sliding sub-windows (hop 0.5 s). For each 0.5 s hop interval the cut candidate is the lowest-energy frame starting in it (root-mean-square; the earlier frame on a tie). Grid, in order: floor 3.0 s, then 4.0 s; window 1.5 s, then 1.0 s, then 2.0 s.
  - The two centres are built as D4's B2 builds them, with the centre parameters of `B2-01` (low bar 0.20, seed floor 20 s, centre guard 0.5), whatever row is built, from scores against the profile that table uses: P1 on the stitched truth, each set's own profile on the seen sets. Where no centres can be formed for a dialogue or an encounter, nothing is split and its seconds count as `unmeasured`, never as a failure to split; the tables show eligible mixed seconds and proposed and kept cuts beside the result.
  - Each sub-window takes the label of the nearer centre. At an equal distance it takes the label of the sub-window before it in that segment; the first takes the segment's `R0` label.
  - A speaker change is a label flip that holds for at least two windows. Its anchor is the midpoint between the centre of the last window of the old run and the centre of the first window of the new run; the cut is the candidate nearest the anchor within 0.5 s (the earlier on a tie); with no candidate in range there is no cut.
  - Cuts are resolved in time order. A cut whose left piece (from the previous kept cut or the segment's start) is under 0.5 s or holds no word is dropped; if the last piece is under 0.5 s or holds no word, the last kept cut is dropped. A piece's label is the majority label of the sub-windows whose centre lies in it (the earlier label on a tie); a piece that holds no sub-window centre takes the label of the sub-window whose centre is nearest to it (the earlier of two equally near). Pieces are half-open in time: a piece runs from its start up to, but not including, the next cut, and the last piece includes the segment's end. A word goes to the piece that holds its time midpoint and a sub-window to the piece that holds its centre; one that falls exactly on a cut belongs to the later piece.
  - The measurement is the batch path's, where a long span stays whole. The live path force-closes a span at 30 s, so its unsplit starting point differs; the tables say so and show how many close-turn body segments run past 30 s.
  - What the follow-up plan must still settle is listed in the Deferred item.
  Alternatives considered: building it now (the practitioner's "Measure now, build next"); not measuring it (the follow-up plan would start without evidence); a second measurement at the built row's centre settings (the built row is known only after both measurement passes have ended).
- **D6 — What the agent runs and what the practitioner runs.** The agent runs only the seen-set measurements. The practitioner runs, from a normal terminal with both builds closed: `sv-measure.py --stitched` over their own script recordings (its tables hold no patient content and may be pasted and recorded whole) and `sv-measure-kept.py` over kept consultations. Both refuse unless crash reports are excluded for `python.exe`.
  Alternatives considered: the agent reading the measurement folder (the practitioner's voice is theirs to run).
- **D7 — Real speech gives direction and a sanity check, never accuracy.**
  - Arguments: the Past-sessions folder, `--enrolment` (the P0 WAV), `--take-a` (the folder holding the thirteen files; it reads take A's six), `--config` with the same folder the `lcm-measure-kept.py` run of record used (`docs/testing/kept-recordings.md`), and `--allow-low-count` (the practitioner's override by name).
  - Before any audio is opened it verifies the SHA-256 of every scratch file it will execute against values pinned in the script: the ffl frame, `ffl_lib.py` and `sv_lib.py`. It loads and runs the verified bytes, never a second read. Its self-test, which opens no audio, includes a changed `ffl_lib.py` being refused.
  - It does not use the frame's loader (that one drops the audio and returns only a document). Its own guarded pass decrypts one recording at a time into memory, transcribes it once in a temporary store, collects the per-segment vectors under C4's rules (one clearable owner; a collection helper that hands back numbers only; traceback frames cleared on a failure; every scratch calculation that reads a vector, the second profile's scoring included, sits behind that same boundary), applies every combination in its fixed table, composes the note under each labelling with the shipped extractive provider, and clears everything before the next recording. The archived transcript and saved note are never opened.
  - The combinations are a fixed table in `sv_lib.py`, written before this script is frozen: the baseline `K0` (P0 with `R0`), then P1 with `R0` and with every candidate row id of D4.
  - Eligibility, per combination: for direction, the recordings whose clinician is confirmed under both `K0` and the combination; for sanity, the recordings whose clinician is confirmed under `K0`.
  - Three words per combination. Direction is `met` when, pooled over the direction-eligible recordings, seconds labelled practitioner and note lines both rise against `K0`. Sanity is `met` when no sanity-eligible recording loses its confirmed clinician under the combination and none has more than 80 % of its speech labelled practitioner. The third word compares a row with P1 at `R0`, so that the guided profile's own gain is not credited to the row: `adds` when the row changes at least one label and seconds labelled practitioner, pooled over the direction-eligible recordings, are higher than under P1 with `R0`; otherwise `adds nothing`.
  - Status. `COMPLETE` when every kept recording was processed; anything else is `INCOMPLETE` with a reason code. An incomplete run prints no word: the cause is fixed and the script run again, and D9's selection waits for a complete run. On a complete run a word is printed when its eligible count is at least 3, or at least 1 with the override; otherwise it reads `unmeasured`. Only a complete run can say `unmeasured`.
  - Two output blocks, and nothing else is printed. "For the record" has two exact forms. On a complete run: the status, whether the override was given, and for each combination id its three words. On an incomplete run: the status and one reason code from a fixed, content-free list in the script, and nothing else. Only this block is relayed and may be copied into a tracked file, and the self-test checks each form against its exact list. "For you only", never copied into a tracked file (C1): the recording count; and per combination its two eligible counts, seconds labelled practitioner, seconds that change label against `K0`, note lines, `clinician_line_omitted` warnings, and the share of speech in five score bands (under 0.20, 0.20 to 0.35, 0.35 to 0.50, 0.50 to 0.65, 0.65 and over). The self-test covers a complete, a low-count and an incomplete run.
  - What it can show is direction only: more of the speech labelled the practitioner's and more note lines. It cannot show whether those labels are right, nor which lines would still be left out for want of a cue; that comparison is made on the synthetic sets (Task 0.5a).
- **D8 — Regression.**
  - Reports are provenance. "Before" (Phase 0, where `desktop/` does not change): the harness over each of the seven sets with `--config validation\config --rule validation\rules\rule-v6.json --set <its name> --suggestions off`; the commit id and each report's SHA-256 are recorded in `.cursor/loops/sv-out/`. "After" (the verified commit): the same command, then the gate configuration (`--suggestions confirm-all --prose`) once. A report embeds its commit, so reports from two commits never match byte for byte; their verdict lines are read, their hashes are not compared.
  - The decode check comes first. `sv-measure.py --trace` decodes each set once with the built product and compares every encounter with what Phase 0 wrote for it: the spans, every field of every word (its probability included, which a later check reads), the scores, the branch assembly took, scratch's `R0` labels, clinician and number over the new decode, and, for a built row, the product's own labels, clinician and number against what Phase 0 wrote for that row id (so the row released is the row that qualified, not only one that scratch can reproduce on the day). Scratch's `R0` uses the literal 0.50, never a constant imported from the product. The result must be 0 differences. A set that differs is decoded once more at the same commit (the same audio can, rarely, transcribe differently); a difference that persists is a finding, and that set's trace is not read until it is disposed.
  - The paired trace, for every encounter that passed the decode check and whose labels differ. After = the product's document. Before = the same document relabelled by scratch's `R0`. Each side is evaluated twice, with the stages off and with the gate configuration's two stages, and each evaluation records:
    - the harness's own outcome, replayed through `ffl_lib.replaying` and `replay_encounter` with `factory=validation.extractive_provider_from_config` (the shipped provider, never the scratch one), leaving out wall-clock timings;
    - the FINAL note's placements, from the note that evaluation ends with (after accepted suggestions, in the gate configuration). Where the harness reports the role unresolved and composes nothing, scratch runs the same composition with the role answered by the document's stored clinician, the one the Review screen preselects, so every changed encounter that has a stored clinician is traced in both configurations;
    - how a placement is identified: a quoted line by its segment and word coordinates (and its section); a line that comes from the configuration (autofill or prefill) by its provenance and proposal identity, with no next-patient status;
    - next patient: a quoted line is flagged when any of its words lies after the detected boundary, and when any of its words lies in the script's own next-patient tail; a quoted line that cannot be mapped to the script with certainty is listed as ambiguous.
  - A side on which a requested stage reported itself unavailable (the model missing or failing to load) is `not evaluated` for that encounter and configuration. It is surfaced and the run repeated; it is never counted as equal. A suggestion stage that was not asked because no line was left out is a completed pass that added nothing: it is not unavailable and is never retried.
  - The note path must be the code Phase 0 ran, because both sides of the trace run today's note code and a change there would show on both. Before the trace is read, `git diff <Phase 0 commit> <verified commit>` over the note path (`note.py`, `note_fill.py`, `note_check.py`, `note_config.py`, `note_suggest.py`, `consultation_phrases.py`, `prose_style.py`, `validation.py`, and the composition helpers of `ui/models.py`) must show no executable change; Task 1.4's wording edits are the only difference this plan makes there, and each hunk is read. An executable change to the note path is outside this plan: if hardening finds one is needed it is a must-pause for the practitioner, and the before side is then replayed from a detached worktree of the Phase 0 commit, in both configurations, with no shortcut.
  - Equal by construction, the one shortcut: an encounter that passed the decode check and whose labels are identical before and after is counted, not traced (the stored clinician and number never differ, by D4). With release id `R0` the product's matching code is unchanged, so every encounter that passes the decode check is equal by construction; the trace is then run once with the stages off to show 0 differences.
  - Every difference is listed. One that admits next-patient material to a note (by the detected boundary or by the script's tail), or places a line in a clinician-owned section it was not in before, is never closed as "explained": it is a must-pause finding with the practitioner's disposition recorded before any release. An ambiguous line is surfaced with them.
  - A measurement on seen sets; no rule file changes.
- **D9 — One fixed order selects the release.** Candidate rows are walked in D4's id order: `B1-45`, `B1-40`, `B1-35`, `B1-30`, `B2-01` to `B2-36`, `B3-01` to `B3-36`. A row qualifies when it meets every line of bar B (the stitched lines with P1, the seen-set lines, the kept-consultation direction and sanity words for P1 with that row). A line that reads `unmeasured` is not met. The first row that qualifies is built with Lever A. If no row qualifies, the release is `R0`: Lever A alone, unconditionally. Bar A1 is reported and gates nothing. Bars A2 and C are reported for the follow-up plan and gate nothing here. There is no speed bar (Validation).
  - The brief also says what the selected row adds over the guided profile alone: its recall difference from P1 at `R0` on the stitched pools, and its `adds` word on kept consultations. A selected row that adds nothing is named as such.
  - Task 0.7 confirms the order's result; the practitioner may decline Lever B for a reason recorded by name, which is the `R0` case.
  - A fall-back after Lever B has been built. If the release becomes `R0` for any reason once Phase 2 exists (the practitioner's disposition of a must-pause difference, a parity that cannot be made to pass), Phase 2's commits are reverted, so that matching and vector lifetimes are today's code again; every Lever B result is recorded as measured and not released; and Tasks 4.1 and 4.3 are run on the reverted tree.
  Alternatives considered: choosing the row with the best table (a choice made after the numbers); a timing bar on the built row (every row is arithmetic over numbers the pass already holds, so a timing would measure the laptop, not the row).

## Schema / Data Changes
None. The profile stays schema v1 with one vector. The transcript gains no field and no segment. 0.4.0 reads everything 0.4.2 writes, and 0.4.2 reads a profile recorded by 0.4.0.

## Config / Environment / Deployment Impact
- No environment variable, no new dependency, no new model, no model-pack change.
- One release, 0.4.2; 0.4.1 stays reserved for the UI refresh's Phase 6.
- After the install the practitioner re-enrols; a profile recorded by 0.4.0 keeps working until then.
- Rollback to 0.4.0 needs only finish-or-discard every recording, then reload the extension and restart Chrome; a profile recorded by the guided flow is an ordinary one-vector profile and 0.4.0 uses it. If the guided profile itself is the suspected fault, rolling back is not enough: the practitioner records a new profile on 0.4.0 (its own 30-second enrolment replaces the stored one; no second copy is kept) and repeats the mock before any scoring.

## Critical Constraints
- **C1.** The agent never reads, plays or describes a kept recording, transcript or note, and never opens the measurement folder. Real-speech results reach the repository only as words against the bars; no session id, per-recording number, pooled total or accent count enters a tracked file, from any tool, the kept-recordings replay included. The stitched-voice tables (the practitioner's own voice, synthetic words) may be recorded as totals.
- **C2.** The app saves no enrolment audio: no session, no chunk store, no WAV, no temporary file. The truth recordings are the practitioner's own plain files, outside the app, deleted by name at this plan's close; `enrolment\me.wav` keeps its own retention row.
- **C3.** The bars, grids, orders, ids, pools, seeds and measures are frozen in one commit before any new number (Task 0.2). A bar is never adjusted after a number is seen; a row that misses a gating bar is not built, and D9 says which bars gate. The part-consistency figure is a calibration, not a bar: its derivation is frozen, its value is read from the measurement (Validation).
- **C4.** Speaker-model vectors live in process memory for one transcription pass only. They are never written, logged, pickled or placed in the transcript, the session store, the audit row, a report or a scratch file; this holds for synthetic audio in scratch as it does for the product. They sit in ONE clearable owner object (add, read, clear): `clear()` empties it in place and closes it, so a later add is dropped. The owner keeps one slot per segment, in segment order, empty where no vector exists (a slice under 25 ms is never embedded, as today), so a vector is never read against another segment's score, length or label. `buffers_cleared` inspects the owner with the other holders, so a worker that still owns vectors never reports cleared.
  - collection: a vector is produced and handled only inside one collection helper, which embeds a segment, adds the vector to the owner and hands back the score, a number. The driver's own frame never holds a vector, so a later failure in the driver (the recogniser, a word mark, a live post) cannot keep one alive;
  - batch: the driver creates the owner before the first window and clears it in a `finally` that covers collection, assembly and every failure between them;
  - live, a normal seal: the worker publishes its result and exits; its exit clean-up leaves the populated owner alone, exactly as it leaves the published result alone today, so `drain` finds the vectors;
  - live, before the handover: on a failure or a requested stop, Stop, Discard and the worker's exit clean-up clear the owner in place (the same cases in which they drop the result today), so a result that was published and never drained holds a closed, empty owner. One short lock covers only the stop decision and the handing over of the owner once the worker has exited; neither `drain`'s join nor `stop`'s bounded join is made while holding it, so a Stop during a blocked `drain` still signals the worker and returns in its bounded time, and one of the two wins the owner whole;
  - live, the handover: ownership moves at one point only, a successful `drain`, which hands the result with the owner inside it to the receiver and drops the worker's reference;
  - live, after the handover: the receiver clears the owner in its existing `finally`, beside `worker.stop()`, which covers the header read and assembly; `assemble` also clears it on return or raise, so nothing is left by the time the transcript is written;
  - a window that returns after Stop finds the owner closed and adds nothing;
  - a join timeout: nothing is claimed cleared. The existing refusal stands (the worker stays attached and no destructive step runs), and the worker clears the owner itself when its blocked call returns, as it does its other buffers;
  - a failure inside the collection helper or the session rule can leave a vector in a frame of its traceback. Where the helper and the session rule are called, such an exception has its traceback frames, and those of its chained exceptions, cleared before it goes further (`traceback.clear_frames`, as `speaker_eval` already does for a custody reason of its own); the handling frame itself holds no vector. In scratch the same boundary wraps every calculation that reads a vector (a second profile's scoring, best-part scoring, sub-window scoring);
  - the batch fallback after a live failure, and recovery, recompute from the encrypted audio and never reuse a lost pass's vectors.
  Each of these is pinned by a test whenever the built row keeps vectors (a B2 or B3 row). With `R0` or a B1 row the drivers stay as they are: on the successful path each segment is reduced to one number and no vector is kept. The threat model states the rule, and a cross-family round reviews it.
- **C5.** The recovery mark and the session rule are each a new dated decision (amending the practitioner-profile plan's D3 and D13; its D-P1 pass mark stays 0.50). Any later change repeats this plan's measurement.
- **C6.** Not touched: the VAD constants, `GUARD_*` and the guard's inputs, `UNCERTAINTY_THRESHOLD`, `ATTRIBUTION_THRESHOLD`, the recogniser, the primer, the cue file, the frozen vocabularies and their pins, the rule files, the held-out sets, the prompts, `consent-v3`'s text, the profile schema, `attribute_speakers`, `enrolled_cluster`, `transcript_before`, any harness credit.
- **C7.** `test_shadow_exits.py` is not edited. The passage label is plain and not selectable; nothing in the new code copies, drags or writes audio.
- **C8.** One lease covers a whole enrolment; "nothing was saved" stays true until the final stop check.
- **C9.** Set folders and `.cursor/loops/sv-out/` hold synthetic content only. Long runs are background, lid open; they start on the practitioner's "start now". No script of this plan reads standard input: the agent's shell calls end with `< /dev/null`, and a command for the practitioner is given in PowerShell form, without it.
- **C10.** Nothing is committed, pushed or installed without the practitioner's word. Shadow mode stays on. Cloud sessions stay off. The practitioner's own folders (the measurement folder, the release folders) are named only in chat or the git-ignored `AGENTS.local.md`; the synthetic-set folder may be named here.

## Validation / Verification
- **Definitions used by the bars (frozen with them at Task 0.2):**
  - Rates are shares of truth seconds within one pool (D2's pools). Recall: practitioner seconds labelled practitioner. False match: other-voice seconds labelled practitioner. "Labelled practitioner" means carrying the label of the document's confirmed clinician; a dialogue or encounter with no confirmed clinician contributes its practitioner seconds as not recalled.
  - Seen-set cohort: the encounters whose clinician the harness confirms at baseline. Truth on a label track has two classes, the clinician and everyone else (the patient, a next patient and any other role together). Rates are pooled over that cohort: the label track's clinician seconds labelled other, and its other-speaker seconds labelled clinician, each as a share of that speaker's seconds. A candidate under which any cohort encounter stops confirming fails.
  - Mixed seconds: inside one segment or piece, the seconds of the speaker who has fewer of them by truth. Eligible mixed seconds are those in a dialogue or encounter where D5's centres could be formed.
  - Each true transition is matched to at most one cut, the nearest within 0.5 s, and each cut to at most one transition (nearest first; the earlier on a tie). A matched cut is correct only when the labels of the pieces on its two sides equal the true speakers on those sides. Wrong splits are the unmatched cuts and the matched cuts with a wrong label on either side. Single-speaker exposure is truth time with no transition within 1 s. Excluded overlap regions (D2) are left out of transitions, cuts and exposure alike. A measure with no support reads `unmeasured`.
- **The bars (frozen at Task 0.2, 2026-11-20, as written):**
  - A1 (reported; it gates nothing): at `R0`, P1 reaches at least 90 % recall on the overall pool and at least 80 % on the quiet pool, with at most 2 % false match on the overall pool; P0 is shown beside it.
  - A2 (reported for the follow-up plan): P2 beats P1 by at least 5 points of recall on the quiet pool with no more false match on the overall pool.
  - B (gates every row): with P1, the row reaches 90 % recall on the overall pool and 80 % on the quiet pool with at most 2 % false match on the overall pool; on the seen sets no cohort encounter stops confirming, the clinician-labelled-other rate does not rise, and the other-labelled-clinician rate rises by at most 0.5 percentage point; on kept consultations its direction and sanity words for P1 with that row are both `met`. A line that reads `unmeasured`, the quiet pool's included, is not met.
  - C (reported for the follow-up plan): on the close-turn pool's eligible mixed seconds, mixed seconds fall by at least half against no split; at most one wrong split per 5 minutes of single-speaker exposure over the four mixed dialogues' bodies; no wrong split on the seen sets.
  - Speed: no bar. Every row is arithmetic over numbers and vectors the pass already computes and adds no model call; a test pins one embedder call per segment that can be embedded and none for a slice under 25 ms, as today (Task 2.1). Reported for the follow-up plan, gating nothing: the scratch cost of Lever C's sub-window embedding per minute of audio.
- **The part-consistency calibration (derivation frozen at Task 0.2):** each take's six part vectors are built through the product's capture limits and left-out rule (D2); each part is scored against the unit mean of the other parts of its own take; the figure is the lowest of those cosines over both takes, less 0.05, and never below 0.50.
- **Stated with the tables:** D4 and D5 search a grid, so a row that meets a bar has been chosen among several on the same recordings; the fixed order limits that and does not remove it.
- **Baselines dry-run at planning (2026-11-20, read-only):** `git status` clean at `92d98c4`; no `.cursor/plans/plan-stronger-voice.md` existed; the four scratch frames exist; `label_speakers`, `enrolled_cluster`, `attribute_speakers`, `transcript_before`, `assemble_transcript`, `segment_pcm`'s `pad_seconds`, `ffl_lib.replaying` / `replay_encounter` and `GAP_SECONDS = 0.6` are where this plan says.
- **Phase 0:** the premise in two parts: (1) on every seen-set encounter, scratch's `R0` labels (with the literal 0.50), confirmed clinician and number equal the pipeline's own, 0 differences; (2) a small generated fixture with known sample positions checks, apart from label parity, the absolute times of sub-windows and cut candidates, a segment with no text, an encounter with no segment, an encounter that takes the no-match branch, one that takes the single-speaker shortcut, an overlap region beside an eligible transition, a label track with three roles, and a segment whose overlap with two speakers is an exact tie. The freeze commit precedes every new number; the real-speech script's SHA-256 matches its frozen value before the practitioner's run.
- **Build:** `ruff check . && mypy && pytest` green in `desktop/`; `npm run qa` in `extension/`; scratch against product at 0 differences on the seen sets and, run by the practitioner, on the stitched truth; `git diff` of `test_shadow_exits.py` empty.
- **Regression:** D8.
- **Live:** the install smoke (Task P.3); shadow mode on before and after; the Review screen's similarity line on the first consultations, read by the practitioner.

## Deferred / Out of Scope
See the Planning Extraction Summary: building Lever C and several stored vectors (deferred to a follow-up plan); two-tier clinician labels (deferred); routing of uncued lines, a third voice, the frozen constants and texts, and a comparison with another scribe (excluded).

## Current State / Handoff Note
- Last completed step: (2026-11-24, leg sv9) the held live smoke's result recorded (the two Review-screen lines PASSED, "yes it showed, both pass"; the guided card not yet: "for part b its a bit hard to read the text when walking around the table", fixed as the practitioner's "Bigger text"): the passage in the theme's new `reading` role (16 pt); `TestGuidedCardWidth` at 100 % and 150 %; review round 36 converged (2 LOW, applied). Suite owed to the composer. Earlier (2026-11-23, leg sv2) Phase 5's Tasks 5.1 and 5.2 done (🟩 on the composer's green run: 11176 passed, 9 skipped; `npm run qa` 313 passed); the privacy-notice must-pause disposed (a), "Restate it (a)", and applied (the leg sv2 bullet). Earlier (2026-11-23, leg sv1) Tasks 5.1 and 5.2 written (the leg sv1 bullet). Before that, Phase 4, closed (2026-11-23, legs sg1 to sg14). Task 4.1 is done: the decode check had 0 differences on 7 of 7 sets; both paired traces were run; the one must-pause row (round 29, MP-001, `h4-06`) was accepted by the practitioner, "Accept (a)"; and the "after" reports were run. Task 4.2: `complete`, `no check errors`. Task 4.3: `STITCHED-PRODUCT PARITY: EQUAL`, every Expected item met. Bar B's seen-set lines are met and confirmed on the product (+0.42 point pooled). Hardening of the scratch tooling: rounds 19–28. Before that, Phase 2, closed (2026-11-22, legs sb1 to sb5; committed `4c29283`, not pushed). Task 2.2 PASSED: `sv-measure.py --sets --against-product` from the clean tree at `4c29283` found 0 differences on 7 of 7 sets (183 encounters, 31 relabelled, 0 errors). Its records are under `sv-out/after/4c29283…/`. Before that, Phase 2's build and review (2026-11-21, legs sb1 to sb4): Task 2.1 (row B1-35) is 🟩 on the composer's green suite (11176 passed, 9 skipped). The `/review-loop` converged at round 17 (round 16: 1 MED and 1 LOW, both plan text, applied). The codex pass `stage-2.p1` converged at round 18 with 0 findings. Task 2.2's scratch mode is written and its self-test passes (56 passed), but its long run is owed, so Task 2.2 stays 🟨. Phase 2 has no live smoke of its own: no screen changed, and the labels' live check is Task P.3's mock smoke. Before that, Phase 1 (2026-11-21): Tasks 1.1, 1.2 and 1.4 are 🟩. The review converged at round 13 and the codex pass `stage-1.p1` at round 15. The suite passed: 11156 passed, 9 skipped. Its live smoke was HELD on the practitioner's word, not performed, and is owed before Task P.1. Before that, Phase 0 (2026-11-21): every Phase 0 task is done. Task 0.7's decision was "Confirm B1-35": Lever A is built with Lever B row B1-35, Lever C is not built, and the version is 0.4.2. Earlier: planning complete (Plan Mode with Fable, then `/review-plan`, 2026-11-20); codex plan peer-review rounds 1 to 5 applied (2026-11-20). Round 2 reduced the scope by two practitioner decisions: Lever C and several voice vectors are measured here and built by a follow-up plan.
- Current in-progress step: (2026-11-24, composer) Phase P, Task P.1: the held smoke PASSED (the Review-screen lines and, after the bigger text, the guided card) and the diff check is recorded; the build of record waits on the practitioner's word to push. Earlier (2026-11-24, leg sv9) Phase P's owed smoke: the bigger passage text is built and reviewed; the composer's suite, then the practitioner's re-check of the guided card. Earlier: Phase 5 CLOSED 2026-11-23 (the composer: `/document`, the Phase 5 commit). Next is Phase P, practitioner-run. Earlier entry (2026-11-23, leg sv8): H4's codex pass stage-5.p1, peer round 35, closed docs-only-low-close; Step H complete.
- Immediate next action (2026-11-24, composer): on the practitioner's word: push `main`, run the `Release` workflow, check the attestation, add the row in `docs/release/pilot-builds.md` (Task P.1). Before Task P.3: the practitioner's approval of the review guide's two 0.4.2 lines, the privacy information's restated sentence and the practice README's 0.4.2 sentence. Earlier (2026-11-24, leg sv9): the composer runs the leg sv9 bullet's commands (expected 11177 passed, 9 skipped; the `test_shadow_exits.py` diff empty), then the practitioner re-checks the guided card's bigger passage text on the developer build at 150 % and 100 % (the bullet's steps); a pass clears Task P.1's last owed line, then Task P.1 (push only on the practitioner's word). The practice documents' 0.4.2 approvals are still owed before Task P.3. Earlier (2026-11-23, composer): the practitioner's held live smoke on the developer build (the guided card, round 12's wording points (a)–(c), the learning-on line and the config-line not-learned message), then Task P.1 (the build of record; push only on the practitioner's word). Before Task P.3: the practitioner's approval of the review guide's two 0.4.2 lines, the privacy information's restated sentence and the practice README's 0.4.2 sentence.
- Earlier entry (kept for the record): Phase 4.
  - Task 4.1 first. Its leg writes `sv-measure.py --trace` (scratch). Its decode check reads Task 2.2's clean-HEAD records at `4c29283` against Phase 0's, so the seven sets need no new decode while `desktop/` is unchanged since `4c29283`.
  - The long parts still run on the practitioner's word: the paired trace's gate configuration over the 31 relabelled encounters (overnight), and D8's "after" harness reports. See Task 4.1's dated line.
  - Then Task 4.2 (the practitioner's drift replay, any time, both builds closed).
  - Then Task 4.3, whose leg first builds and hardens the B1-35-against-product stitched comparison in a new scratch module, never editing or running `sv_stitch.py` or `sv-measure-kept.py`, before the practitioner's run. Phase 1's live smoke is HELD and OWED: it must pass before Task P.1 (see the Phase 1 close lines and Task P.1). The earlier entry, kept for the record: the practitioner chose to build ("Start the build", 2026-11-20) after the plan review reached its cap (findings per round 25, 32, 22, 23 and 17, none critical).
- Open blockers / open questions: (2026-11-24, leg sv9) no must-pause open. Before Task P.1: the practitioner's re-check of the guided card's bigger passage text (the Review-screen lines' smoke PASSED 2026-11-24). Before Task P.3: the practitioner's approval of the review guide's two 0.4.2 lines, the privacy information's restated sentence and the practice README's 0.4.2 sentence. Earlier (2026-11-23, leg sv5) no must-pause open. Awaiting the practitioner's approval before Task P.3: the clinician review guide's two 0.4.2 lines (the speaker-label line and item 7's label line), the privacy information's restated learning sentence and the practice README's 0.4.2 sentence (all also await the independent review); the Review screen's learning-on line's wording and the typed-edit "came from your own config" line's (round 32) at Phase 1's held live smoke. Phase 1's held live smoke is owed before Task P.1. Earlier (2026-11-23, leg sv4; disposed 2026-11-23, (a) "Add a 0.4.2 line (Recommended)") MUST-PAUSE: round 31 MED-001 — the clinician review guide's approved 0.3.6 line (item 7) says a line someone else said is never suggested for the four clinician-owned headings; the rule reads the speaker label, and the guide's new 0.4.2 speaker-label line says such a line can be placed there. The brief and the options are in Round 31. Earlier (2026-11-23, leg sv2) no must-pause open. Awaiting the practitioner's approval (not blocking Step H; needed before Task P.3): the clinician review guide's 0.4.2 speaker-label line, and the privacy information's restated learning sentence with the practice README's 0.4.2 sentence (both also await the independent review). Phase 1's held live smoke is owed before Task P.1. Earlier (2026-11-23, leg sv1; disposed 2026-11-23, (a) "Restate it (a)") MUST-PAUSE: `docs/practice/privacy-information.md` (the patient-facing privacy information) promises that the program learns from the practitioner's lines "never from anything you said"; the learners read the speaker label, so a patient's line labelled the practitioner's can teach, more often since 0.4.2's recovery mark. The brief and the recommendation are in the leg sv1 bullet. Also open: the clinician review guide's new 0.4.2 speaker-label line awaits the practitioner's approval (not blocking Step H; needed before Task P.3). Earlier (2026-11-23, leg sg14) none open; Tasks 4.2 and 4.3 are done. Phase 1's held live smoke is owed before Task P.1. Earlier (2026-11-23): none open; Tasks 4.2 and 4.3 are the practitioner's runs. Earlier (2026-11-22, leg sg13) MUST-PAUSE (disposed 2026-11-23, (a) Accept): Task 4.1's `h4-06` brief (round 29, MP-001) waits on the practitioner's disposition before any release; `heldout-4`'s gate report re-run is pending. Tasks 4.2 and 4.3 are the practitioner's runs. Tasks 0.1, 0.2 and 0.7 (decisions) and 0.3, 0.5b and 0.6 (runs) are done. (2026-11-22, leg sg1) Task 4.1's long runs wait on the practitioner's "start now"; Task 4.3's script waits on its hardening and freeze. No must-pause.
- Context a fresh session needs: the first Task 9.1 score of 2026-11-20 is set aside and is recorded nowhere in the repository; the ten restart after this plan's install.
- Executor handoff (leg svx1, 2026-11-20T22:47+11:00): Task 0.4's code is written, not run (verify=composer; this leg runs no Python). Task 0.4 stays 🟨 until the long runs and the premise at 0 differences.
  - Written (git-ignored, `.cursor/loops/` only; no tracked file changed but this plan): `sv_lib.py` (D4's 76 rows with fixed ids and `R0`; `PASS_MARK = 0.50` literal; D5's six grid points `F3.0-W1.5`, `F3.0-W1.0`, `F3.0-W2.0`, `F4.0-W1.5`, `F4.0-W1.0`, `F4.0-W2.0`; D7's 78 combinations `K0`, `P1:R0`, `P1:<row id>`; scratch `R0`, `run_row`, `form_centres`, the D5 rules, the two-class truth with the tie tested first and overlap regions excluded, cut scoring, exposure; C4's `VectorOwner`, `vector_boundary`, `clear_exception_frames`; the size and key check `vector_free_problems`) and `sv-measure.py` (`--self-test`, `--pass`, `--premise`, `--record-before`; `--sets`, `--stitched` and `--trace` are left for later legs). Neither imports `ffl_lib` or `lcm_lib` (the set names and ids are copied), so no hash check is needed yet.
  - How the pass gets its inputs without touching `desktop/`: the harness's own enrolled path (`validation.transcribe_in_temporary_store`, memory-only key, the set's one-passage profiles), with `transcription.assemble_transcript` wrapped for the call to record its inputs (spans, text flags, scores, the shortcut) and the embedder wrapped so each vector also goes to the owner. Vectors map to segments by the product's rule: one embed call per segment that has a score. Sub-window vectors are embedded from the encounter's PCM with the product's slice arithmetic and reduced to two cosines inside one helper. The no-match branch of scratch `R0` calls the product's `_cluster_embeddings` (the 2-means); everything else in `R0` is scratch code with the literal 0.50.
  - Interpretations where the plan leaves a choice (also in `sv_lib.py`'s docstring); none changes a frozen figure: sub-windows start at the segment's first sample and every 0.5 s, whole windows only; a cut candidate's time is the centre of its frame; a flip "holds for two windows" when the next window carries the new label too (a one-window flip is passed over), and the anchor uses the last window that carried the old label; D5's centres form only under D4's one condition; class seconds are the union of a class's spans (same-class overlaps are not counted twice); an overlap region is an overlap of the two classes; a tied piece takes the earliest sub-window's label; a piece "holds a word" when a non-blank word's midpoint is in it; exposure counts single-class speech farther than 1 s from a counted transition. Besides D2's list, each record also holds each segment's truth seconds (per class and per track label) and the encounter's truth totals, so Task 0.5a reads no audio.
  - Quick checks for the composer now (no model, no built set): (1) `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null` should print 24 `[ok]` lines and `SELF-TEST: 24 passed, 0 failed`, exit 0; (2) `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --premise < /dev/null` should print seven `NOT COMPLETE` lines and `PREMISE DIFFERENCES TOTAL: 0 (sets complete 0/7)`, exit 1 (the mode is wired; nothing built yet).
  - Long runs, on the practitioner's "start now" (C9; background, lid open; every call ends `< /dev/null`): (a) the voice check and the seven builds, each into its own empty folder: `.venv/Scripts/python.exe -c 'from scribe_desktop.validation_set import sapi_voices; [print(i, v) for i, v in enumerate(sapi_voices())]' < /dev/null` against the current voice baseline in `docs/testing/validation-harness.md`, then `.venv/Scripts/python.exe scripts/build-validation-set.py validation/<set> C:/sv-sets/<set> < /dev/null` for `scripts`, `heldout`, `heldout-2`, `heldout-3`, `heldout-4`, `heldout-5`, `heldout-6`; (b) the pass, all seven in order, resumable per set (a complete set is skipped, an incomplete one is decoded again whole): `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --pass --built C:/sv-sets --config validation/config < /dev/null` (one set: add `--only heldout-2`); it prints one `[progress]` line per encounter (ids, segment count, branch code, cohort yes/no, seconds), one `[set]` line per set and `PASS PROBLEMS: 0`; (c) `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --premise < /dev/null`, expected `PREMISE DIFFERENCES TOTAL: 0 (sets complete 7/7)`, exit 0; (d) D8's "before" reports, `mkdir -p .cursor/loops/sv-out/before` then for each set `.venv/Scripts/python.exe scripts/run-validation.py C:/sv-sets/<set> --config validation/config --rule validation/rules/rule-v6.json --set <set> --suggestions off > .cursor/loops/sv-out/before/<set>.md < /dev/null` (its exit status is the gate's verdict, not a failure of the step), then `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --record-before .cursor/loops/sv-out/before/scripts.md .cursor/loops/sv-out/before/heldout.md .cursor/loops/sv-out/before/heldout-2.md .cursor/loops/sv-out/before/heldout-3.md .cursor/loops/sv-out/before/heldout-4.md .cursor/loops/sv-out/before/heldout-5.md .cursor/loops/sv-out/before/heldout-6.md < /dev/null`, which writes `sv-out/before/provenance.json` once (HEAD, `desktop/` clean, the seven SHA-256s), prints them, and exits 0 only with `desktop/` clean and all seven.
  - Open points: none is a must-pause. The pass and the harness each decode all 183 encounters once, so each is several hours on this laptop; they can run one after the other in the same "start now". Like the harness, the pass writes its encrypted temporary stores under the system temp folder (memory-only key), so on this host it is as agent-runnable as the harness.
- Executor handoff (leg svx2, 2026-11-20T22:59+11:00): the self-test's two FAILs are fixed and every FAIL now names its failed assertions. Still not run by this leg (verify=composer). Task 0.4 stays 🟨.
  - Cause of both FAILs: the record's grid field `centres` is itself one of the size-and-key check's forbidden keys, so every record failed `vector_free_problems`. The field is renamed `centres_formed` (a yes/no; no vector was ever written), and the check gains a case pinning `centres` as refused.
  - Detail lines: each check collects the code of every assertion that fails (ids, counts, codes, numbers and key paths only). A FAIL prints `  detail: <codes>` (the first 12, then `(+N more)`), and an exception prints its type and `file:line`, with its frames cleared. A passing check may print a note line.
  - Count: 25 checks (svx1's 24 was a miscount: the R0 parity cases are 7). The self-test now fails if it ran any other number (`SELF_TEST_CHECKS = 25`).
  - The sv-out scan: every `.json` under `sv-out` gets the size-and-key check (a failure names its path relative to `sv-out` and the first problem's key path). Every other file (the harness's `report-<set>.md`, `stderr-<set>.txt`, `run.log`) is counted and ignored: sv-measure never writes them, and vectors exist only inside its own pass. This is printed as the check's note.
  - `--record-before` now takes exactly seven existing files, in set order, under any names. It records each file's name and SHA-256 under its set, plus HEAD and whether `desktop/` is clean, and still refuses to overwrite `provenance.json`.
  - Quick check for the composer now: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null` should print 25 `[ok]` lines, then one `  detail: N JSON file(s) checked; M other file(s) ignored (…)` line under the last check, then `SELF-TEST: 25 passed, 0 failed`, exit 0. Any FAIL is followed by its detail line.
  - After the seven before-reports finish: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --record-before .cursor/loops/sv-out/before/report-scripts.md .cursor/loops/sv-out/before/report-heldout.md .cursor/loops/sv-out/before/report-heldout-2.md .cursor/loops/sv-out/before/report-heldout-3.md .cursor/loops/sv-out/before/report-heldout-4.md .cursor/loops/sv-out/before/report-heldout-5.md .cursor/loops/sv-out/before/report-heldout-6.md < /dev/null`. It prints seven `[before] <set> report-<set>.md sha256 …` lines and a HEAD line, and exits 0 only if `desktop/` is clean. The pass (`--pass`) and `--premise` are unchanged from svx1's bullet.
- Executor handoff (leg svx3, 2026-11-20T23:23+11:00): Task 0.5b's `--stitched` mode and its self-test are written, not run (verify=composer). Task 0.5 stays 🟥 until the practitioner's run and Tasks 0.5a and 0.5c.
  - Written (git-ignored, `.cursor/loops/` only): a new `sv_stitch.py`, imported by `sv-measure.py` only for `--stitched` and `--self-test`, so the chained `--pass` never loads it. `sv_lib.py` is unchanged, and so are `--pass`, `--premise` and `--record-before`. `sv-measure.py` gains `--stitched FOLDER --enrolment WAV`, its dispatch, a hooks helper and the self-test's stitched cases.
  - What the mode does (D2): it reads the thirteen manifest files and the enrolment WAV.
    - Profiles: P0 is the enrolment WAV through `enrol`. P1 is each take-A part through `record_enrolment` with a file-backed capture. The capture sends 100 ms blocks, the next one only on the progress callback, then digital silence; the product's caps are 90 / 45 / 45 / 45 / 45 / 45 s. Each part then goes through `enrol`, and P1 is the unit mean of the retained part vectors. P2 is those part vectors scored as the best match. Take B's parts are built the same way, for the calibration only.
    - Dialogues: spans come from the VAD with `pad_seconds=0`, and turns from seed 20261120. There are four mixed dialogues over take B with one shared body, the preamble playing on the 0.10 and 0.20 s dialogues only, plus six part dialogues at 0.60 s.
    - Each dialogue is stitched in memory and decoded through `transcribe_in_temporary_store(persist_key=False)`, with the vectors captured into a clearable owner as in `--pass`.
    - Computed for each dialogue: every D4 row with P1; scratch R0 under P0 and P2 (the same segment vectors rescored with the product's `_cosine`); D5's grid on the four mixed dialogues, reading the body only; the parity of scratch R0 with the pipeline. All profile vectors sit in a holder that is cleared at the run's end and on any failure.
  - What it prints (D6): the recordings, the profiles (each part kept or left out, with seconds heard), the calibration's cosines and its figure, the dialogues and pools, and bar A1 (P1, with P0 beside it). Then bar A2, bar B's stitched lines for R0 and all 76 rows (with each row's points against P1 at R0), bar C for each grid point (with the close-turn body segments past 30 s and the embedding cost), and the parity total. Numbers, ids, codes and the thirteen manifest names only: no path and no transcript text. It writes nothing and reads no standard input.
  - Refusals, in order: developer build; `--enrolment` must be a file; the folder must be a folder holding exactly the thirteen names (missing and extra are given as counts only); crash reports must be excluded for this interpreter (`check_tool_wer`, as `lcm-measure-kept.py` uses it); then the app's instance exclusion (both builds closed). After those: an unreadable or wrong-format WAV, `other.wav` or a required part with no speech, a reservation that leaves a voice no turn, and a required part short at its cap (each names the file or part). Any other failure prints its type name only and no table.
  - Interpretations where the plan leaves a choice (also in `sv_stitch.py`'s docstring); none changes a frozen figure:
    - Turn targets: the first 4096 draws of one generator go to the practitioner, the next 4096 to the other voice, both read from their start in every build.
    - A turn's length is its audio, joins included. Closing an open turn uses up its target; a span over 8 s draws none. Spans left open at the end are closed as they stand.
    - A dialogue starts with the practitioner and ends after the practitioner's last turn. The preamble is the practitioner's spans first, then the other voice's.
    - The part dialogues reserve nothing and have no preamble.
    - The quiet pool's "detected speech" is the practitioner's truth inside the pipeline's own segments.
    - Cuts before a body's start are counted on their own line, not scored.
  - Self-test: 46 checks = the 25 seen-set checks, one for the stitched module's count, and Task 0.5b's 20. They use generated tones, a fake VAD, a fake 4-number embedder and the product's mock recogniser. The real capture, `enrol` and the encrypted temporary store run as shipped; no recording is read and no model is used. The last check runs the whole mode end to end on generated recordings (ten dialogues through the real temporary store) and checks that every store is gone and the output holds numbers only.
  - Quick check for the composer now: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null` should print 46 `[ok]` lines, the sv-out scan's note line, then `SELF-TEST: 46 passed, 0 failed`, exit 0. It now takes longer, probably under two minutes.
  - The practitioner's run (Task 0.5b; the composer gives the PowerShell command in chat): from the repository root, in a normal terminal, with both builds closed and the lid open, `sv-measure.py --stitched` on the measurement folder's stronger-voice subfolder with `--enrolment` naming enrolment\me.wav. It decodes about forty minutes of stitched audio with Whisper `medium`, so expect something like half an hour to an hour. They paste everything from `# Stronger-voice stitched truth` to `STITCHED: COMPLETE`.
- Executor handoff (leg svx4, 2026-11-20T23:27+11:00): the one self-test failure (`second:vector-unreachable`) was a custody defect in the CODE, not in the check. Fixed; not run by this leg (verify=composer).
  - Cause: `sv_stitch.profile_scores` took the best match with `max(cosine(vector, reference, np) for reference in references)`. That generator expression closes over `vector`. The generator's frame keeps a strong reference to its function object, and that function's closure cell keeps the vector. `traceback.clear_frames` clears frame locals but not that cell, so an exception held after a failure in second-profile (P0 / P2) scoring kept the segment vector reachable. The check holds only weak references, and builds its vector inside a helper that has returned, so it was right. The sub-window half of the same check passed, because `sv_lib.subwindow_nearness` has no closure.
  - Fix: `profile_scores` now takes the best match in a plain loop, with a comment giving the C4 reason. The reference list in `run` is also built in a loop rather than a generator over the holder. No other generator expression in the scratch files closes over a vector (`sv_lib.py`'s list comprehensions are inlined since Python 3.12 and keep no function object). `sv_lib.py`, `--pass`, `--premise`, `--record-before` and the check count (46) are unchanged.
  - Quick check for the composer now: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null` should print 46 `[ok]` lines, the sv-out scan's note line, then `SELF-TEST: 46 passed, 0 failed`, exit 0. The practitioner's `--stitched` command is unchanged from svx3's.
- Executor handoff (leg svx5, 2026-11-20T23:40+11:00): Task 0.5a's `--sets` mode is written. Not run by this leg (verify=composer).
  - Where: a new scratch module `.cursor/loops/sv_sets.py`, imported lazily like `sv_stitch`, so `--pass` never loads it. In `sv-measure.py`: the `--sets` flag in the mutually exclusive group, its dispatch (it refuses `--built`, `--config` and `--only`), `_sets_hooks()`, the docstring, and the self-test registration. `--pass`, `--premise`, `--record-before`, `--stitched` and `sv_lib.py` are unchanged.
  - Reads only `sv-out/<set>/run.json`, a complete set's 183 expected records and `sv-out/before/provenance.json`. No audio, nothing decoded or composed, no file written.
  - Refuses, in order:
    - any of those files unreadable;
    - the premise not holding: `premise_differences` itself and `--premise`'s completeness rule (7/7 sets complete, 0 differences, a missing record counted as a difference);
    - no provenance, or one that does not name all seven reports;
    - the scratch confirmation (below) not reproducing the pass's `harness_clinician` at R0's labels on every encounter.
  - "Stops confirming" re-applies `validation.enrolled_clinician` to a row's labels through a scratch copy, `sv_sets.confirmed`. It works from the per-segment `by_label` overlaps and segment times the pass wrote, with the same tie rule (1e-9), the duration-weighted majority, the two-cluster tie and the overlap-seconds test. The self-test pins it against the product function on six generated documents.
  - Bar B, pooled over the cohort:
    - "Labelled clinician" means carrying the baseline confirmed clinician's label.
    - Numerators are the segments' two-class truth seconds, so only speech a segment covers counts.
    - Interpretation: the denominators are the label track's seconds of each class over the whole encounter ("a share of that speaker's seconds"), so R0 and every row share one denominator.
    - Three line words per row, then the seen-set verdict. `unmeasured` (no cohort, or no seconds) is not met.
  - Bar C: per grid point, over every encounter of the seven sets whose centres formed. Wrong splits name their encounters. A point with none formed reads `unmeasured`.
  - Lines comparison:
    - Cohort only, from the `lines` lists the pass composed.
    - Per set: unevaluable, added, removed, still left out, changed encounters, next-patient boundary differences, kept-measured, tied and non-overlapping segment counts.
    - Then per encounter by line identity, as `section sN wA-B`.
  - Self-test: 55 checks = 25 seen-set + 1 stitched module + 20 stitched + 1 sets module + 8 sets. The two module checks each pin the count rule. The 8 sets checks are: the confirmation copy against the product; a hand-checkable cohort for bar B; one for bar C; the lines comparison with its tie and non-overlap counts; the refusals (incomplete or differing premise, missing record, missing or short provenance, unreadable file); the parity refusal; the whole report (no word text, no path); and the real loader end to end on a temporary `sv-out`.
  - For the composer now: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null` should print 55 `[ok]` lines with the sv-out scan's note line, then `SELF-TEST: 55 passed, 0 failed`, exit 0.
  - After the pass and `--premise` finish (premise exit 0): `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --sets < /dev/null > .cursor/loops/sv-sets-report.md`, or to any file the composer chooses outside `sv-out/`. It prints the Markdown report ending `SETS: COMPLETE` and exits 0; a refusal prints one `[refused]` line and exits 2.
- Executor handoff (leg svx6, 2026-11-20T23:58+11:00): Task 0.6's script `.cursor/loops/sv-measure-kept.py` is written. Not run by this leg (verify=composer). No other scratch file changed.
  - The chain, pinned in the script's `PINNED` as clearly marked placeholders. The run refuses with `scratch-unpinned` until the freeze fills them. In dependency order: `sv_lib.py`, `ffl_lib.py`, the frame `ffl-measure-kept.py`, and `sv_stitch.py`. `sv_stitch.py` is a fourth file beyond D7's three, because P1's file-backed capture (`build_take`) lives there.
    - Every file is read once and checked before ANY runs. Each is then executed from the checked bytes under its module name, so the chain's own imports resolve to the checked modules and nothing is read a second time.
    - The freeze must pin these four. It must also record `sv-measure-kept.py`'s own SHA-256 after the four values are filled in, since filling them changes its bytes. From then on `sv_stitch.py` cannot change without a new freeze.
  - Output:
    - Every exit, a refusal included, prints only the two blocks: "For you only", then "For the record". Every refusal is an `INCOMPLETE` record block with a code from the script's fixed `REASONS` list (exit 2). A recording failure, `premise`, `custody` or `interrupted` exits 1. Only `COMPLETE` exits 0.
    - The run prints nothing until it ends: D7 allows nothing but the two blocks, so there is no progress line.
  - Interpretations where D7 leaves a choice:
    - `K0` is decoded by the app's own pipeline with P0. Scratch `R0` must reproduce its labels, clinician and number on every recording; otherwise that recording fails as `premise`. P1's scores are the product's `_cosine` of each captured segment vector against P1.
    - "Seconds labelled practitioner": the durations of the segments carrying the combination's confirmed clinician label. "Speech" for the 80 % rule: the recording's total segment seconds. "Seconds that change label against K0": seconds labelled practitioner under one of the two and not the other. "Note lines": the composed note's quoted transcript lines.
    - The third word's "changes at least one label" is read on the direction-eligible recordings, against P1 at `R0`.
    - `K0`'s direction word, and both `K0`'s and P1 at `R0`'s third word, read `baseline`.
    - Each private-block figure is pooled over that combination's direction-eligible recordings. The score bands are shares of scored segment seconds.
  - The self-test uses generated signals and fakes only. It drives the real batch pipeline (encrypted temporary store, VAD driver, assembly) with a fake VAD, a fake embedder and the mock recogniser. Its 33 cases:
    - the chain loaded from checked bytes;
    - a changed `ffl_lib.py` refused before any scratch file runs, and a changed dependency refused before the file that imports it;
    - the placeholder refusal (once the pins are filled, each must equal its file's SHA-256);
    - 20 refusals in order, each by its reason code and its exact call sequence, nothing decrypted, and 1 for take A;
    - a `COMPLETE` run with both blocks in their exact forms, only take A's six files read, `persist_key=False`, and every owner, captured vector, P1 holder and temporary store cleared;
    - the low-count words with and without `--allow-low-count`;
    - an `INCOMPLETE` run, in which a failure after the vectors were captured leaves no vector reachable;
    - the custody and interrupt stops; the premise failure;
    - the three words by hand; the record block's exact forms; the start-up hook.
  - For the composer now: `.venv/Scripts/python.exe .cursor/loops/sv-measure-kept.py --self-test < /dev/null` should print one `| <case> | pass |` row per case, then `Pinned SHA-256 values: placeholders`, `Self-test cases: 33` and `Self-test failures: 0`, exit 0. The practitioner's PowerShell command is given in chat only.
- Executor handoff (leg svx7, 2026-11-21T00:09+11:00): Task 0.6's hardening before the freeze. Nothing was run by this leg (verify=composer).
  - The count. The composer's self-test gave 32 cases, not leg svx6's 33: that leg counted the take-A refusal twice (once among the refusals and once on its own). 32 is right: 3 for the chain and the pins, 20 refusals, 1 for take A, 5 whole runs and 3 by hand. The script now pins `SELF_TEST_CASES = 32`, and the self-test adds a failing row when the number registered differs, so a dropped or added case fails. Leg svx6's "33" above is superseded.
  - `/review-loop` (cap 3): round 6, 0 CRIT / 0 HIGH / 0 MED / 3 LOW, all applied; converged after one round.
    - LOW-001: the scratch folder is taken off `sys.path` before any other import, and again after each chain module runs.
    - LOW-002: `--take-a` lists every entry, as the stitched mode does.
    - LOW-003: the thread and unraisable hooks print nothing.
  - `/security-review`: round 7, 0 CRIT / 0 HIGH / 0 MED / 1 LOW, applied. SEC-001 silences the warning display (a sibling of LOW-003). Every focus area Task 0.6 names was checked and is clean (the round block lists them), with one named limit: a native library's own console writes.
  - Changed: only `.cursor/loops/sv-measure-kept.py`. `sv_stitch.py`, `sv_lib.py`, `ffl_lib.py` and `ffl-measure-kept.py` are unchanged, so their hashes stand.
  - For the composer: `.venv/Scripts/python.exe .cursor/loops/sv-measure-kept.py --self-test < /dev/null` should exit 0 and print 32 `| <case> | pass |` rows (two case names now longer), then `Pinned SHA-256 values: placeholders`, `Self-test cases: 32` and `Self-test failures: 0`.
- Executor handoff (leg svx8, 2026-11-21T00:20+11:00): leg 1 of peer round 8 (pass `stage-0.p1`), verify-then-fix. Nothing was run by this leg (verify=composer).
  - PR-LOW-3801 verified as labelled: LOW, Fix-now. Applied: the parser has no automatic help, so `--help` and `-h` are `command-line` refusals (exit 2, the two blocks). The tuple is under Round 8.
  - One self-test case added (a `--help` refusal); `SELF_TEST_CASES` is now 33 (21 refusals). Leg svx7's "32" is superseded.
  - Changed: only `.cursor/loops/sv-measure-kept.py`. `sv_lib.py`, `sv_stitch.py`, `ffl_lib.py` and `ffl-measure-kept.py` are unchanged.
  - For the composer: `.venv/Scripts/python.exe .cursor/loops/sv-measure-kept.py --self-test < /dev/null` should exit 0 and print 33 `| <case> | pass |` rows (the new one: `refusal (command-line): help asked for (no argparse help, no exit 0)`), then `Pinned SHA-256 values: placeholders`, `Self-test cases: 33` and `Self-test failures: 0`.
- Executor handoff (leg svx9, 2026-11-21T00:26+11:00): the four pins of `sv-measure-kept.py`'s `PINNED` table are filled with the composer's `sha256sum` values, character for character; nothing else in the script, and nothing in the four pinned files, changed. Nothing was run by this leg (verify=composer).
  - No self-test change was needed. With real pins, the pins case checks that each pin equals its file's SHA-256 instead of running the placeholder refusal. The summary line now reads `frozen`. The chain-refusal case builds its own pins.
  - Task 0.6 gains a dated "Frozen" line with the four hashes. The script's own SHA-256 is the composer's to record at the freeze commit. Task 0.6 stays open: its practitioner run is still to come.
  - For the composer: `.venv/Scripts/python.exe .cursor/loops/sv-measure-kept.py --self-test < /dev/null` should exit 0 and print 33 `| <case> | pass |` rows, then `Pinned SHA-256 values: frozen`, `Self-test cases: 33` and `Self-test failures: 0`. If the pins case fails, one of the four files no longer matches its pin.
- Executor handoff (leg svx10, 2026-11-21T01:50+11:00): the plan only; nothing was run by this leg. I read the pass and premise logs, the self-test outputs and the sets report whole.
  - Task 0.4 stays 🟨, one evidence line short. The size and key check has not yet run over the pass's records (`sv-selftest-5.txt` predates them: `0 JSON file(s) checked`). The command and its expected lines are on the task.
  - Task 0.5 gains its "Done (agent)" 0.5a line (bars B and C's seen-set lines, the labelling-against-routing comparison). It stays 🟥: 0.5b and 0.5c are to come, and no selection is made.
  - The progress figure is 9 % (2 of 22 tasks done).
  - Next: the composer's one self-test run for Task 0.4. Then the practitioner: Task 0.3's recordings, then 0.5b and 0.6.
- Executor handoff (leg svx11, 2026-11-21T01:53+11:00): the plan only; nothing was run by this leg.
  - Task 0.4 is 🟩. `.cursor/loops/sv-selftest-6.txt` (the composer's run with `--config validation/config`, which leg svx10's command left out) checks the pass's 191 JSON records under `sv-out/` and ends 55 passed, 0 failed; the evidence is on the task.
  - Task 0.5 stays 🟥. The progress figure is 14 % (3 of 22 tasks).
  - Next, the practitioner's: Task 0.3's recordings, then 0.5b and 0.6.
- Executor handoff (leg svx12, 2026-11-21T15:05+11:00): the plan only; nothing was run by this leg. I read `.cursor/loops/sv-stitched-paste.md` whole.
  - Task 0.3 is 🟩: the practitioner's word, and the stitched run found all thirteen and kept 6 of 6 parts per take.
  - Task 0.5 gains its "Done (practitioner)" 0.5b line:
    - bar A1 met for P1, and P0's quiet line not met;
    - bar A2 met (+7.2);
    - the calibrated figure 0.651;
    - bar B's stitched lines met by every row;
    - bar C's halving met but its wrong-split rate not met at any point;
    - parity 0.
  - Task 0.5 stays 🟥 until 0.5c. The progress figure is 18 % (4 of 22 tasks).
  - Next: the practitioner's Task 0.6 run (the command is given in chat), then 0.5c.
- Executor handoff (leg svx13, 2026-11-21T18:25+11:00): the plan only; nothing was run by this leg. I read `.cursor/loops/sv-kept-paste.md` whole.
  - Task 0.6 is 🟩. Its "Done (practitioner)" line holds the "For the record" block's content only: COMPLETE, no override, each combination's three words.
  - Task 0.5 is 🟩. 0.5c walked D9's order over the three line sets: B1-45 and B1-40 fail on their kept direction word (`not met`); B1-35 meets every line of bar B, so the selected release id is B1-35.
  - B1-35 adds over P1 at R0 +2.2 / +7.2 / +23.8 recall points on the stitched pools (overall / quiet / close-turn), and its kept third word is `adds`. Bars A2 (met) and C (met at no grid point) are recorded for the follow-up plan.
  - Task 0.7 is untouched and stays 🟥. The progress figure is 27 % (6 of 22 tasks).
  - Next: the practitioner's Task 0.7 decision, on the composer's brief.
- Executor handoff (leg svx14, 2026-11-21T19:00+11:00): plans only; nothing was run by this leg.
  - Task 0.7 is 🟩: the practitioner's "Confirm B1-35", the brief's points and the consequences. Lever A plus Lever B row B1-35; no vector kept; Lever C not built; 0.4.2.
  - Phase 0 is marked done (all seven tasks). The progress figure is 32 % (7 of 22 tasks).
  - Siblings reconciled with dated lines: the Goal; Agreed Scope's Lever B line; two Key Design Decisions (the order's result; C4 settled for the product build); Flow 3; the handoff note's top four lines; Phase 2's built row and which of Task 2.1's parts apply; Task 5.1's version.
  - Swept for contradicted siblings by search (`uses the consultation itself`, `enough of their clear speech`, `row is built`, `the selected row`, `Lever B built`). What remains is conditional on the built row's type and stays true for B1-35.
  - `.cursor/plans/plan-practitioner-profile.md` (LF, kept) gains four dated lines only: D3 (the recovery mark 0.35 after a match; pass mark and remainder rule unchanged), D8 (the guided six-part capture, still in memory, one vector), D13 (`speaker_1` also takes B1-35's relabelled segments; no vector kept), D-P1 (unchanged).
  - Next: the composer's Phase 0 close (review, peer pass, `/document`, commit), then Phase 1.
- Executor handoff (leg svx15, 2026-11-21T19:08+11:00): Phase 0's close review, plans only; nothing was run by this leg.
  - `/review-loop` over Phase 0's tracked diff since `42032e1` (both plans), cap 3: converged after one round (round 10). It found no CRIT, HIGH or MED, so no further round was run.
  - Round 10: 0 CRIT / 0 HIGH / 0 MED / 5 LOW, all wording, all applied. Every recorded figure and word in Tasks 0.3 to 0.7 and the svx10 to svx14 bullets matched its evidence file, and no selection or decision moved.
  - The progress figure counts the 22 numbered tasks (0.1 to 0.7, 1.1, 1.2, 1.4, 2.1, 2.2, 4.1 to 4.3, 5.1, 5.2, P.1 to P.5); Step H's five boxes are not counted (round 10 LOW-005). It stays 32 %.
  - The practitioner-profile plan's D8 dated line was reworded (round 10 LOW-001); it still has four added lines and LF endings.
- Executor handoff (leg svx16, 2026-11-21T19:12+11:00): the plan only; nothing was run by this leg except the history check.
  - Phase 0's close review is done. Round 10 (`/review-loop`) applied 5 LOW. Round 11 (codex `gpt-6-astra` medium, pass `stage-0.p2`, peer round 1 of 5) found nothing, so the pass converged. Round 11's block is transcribed verbatim, and its Review History line is added.
  - Next: the composer runs `/document`, commits Phase 0 locally, then Phase 1 (Task 1.1).
- Executor handoff (leg sx1, 2026-11-21T19:34+11:00): Phase 1's Tasks 1.1, 1.2 and 1.4 are written; ruff and mypy are clean (72 files). This leg ran no pytest and no Python (verify=composer), so all three stay 🟨 until the composer's green suite. No version change. `test_shadow_exits.py` is not touched. No new `wave` or `write_wav` reference, no selectable-text flag, no clipboard or drag call, no new list or combo box. No consent text changed (C6), and no audio is written anywhere (C2). Line endings are kept: the five sources and `test_enrolment.py` are LF, and `test_ui_screens.py` is CRLF throughout, as before.
  - `enrolment.py` (Task 1.1). `enrol` and `record_enrolment` are byte-unchanged.
    - New `PART_CONSISTENCY_FIGURE = 0.651`, with its dated calibration line.
    - New `PartEmbedding` (vector, speech seconds, segment vectors).
    - New `enrol_part`: `enrol` itself, run through a wrapper embedder that keeps each segment vector it returns.
    - New pure functions: `combine_parts` (the normalised equal-weight mean; `EnrolmentError` for none, a zero mean or a non-finite one), `part_consistency` (each part against the unit mean of the others; -1 where the others have no direction), `weakest_part` (the lowest strictly under the figure, the earlier on a tie) and `strength_share` (leave one part out, at or above `ATTRIBUTION_THRESHOLD`).
    - The arithmetic is plain Python (`math.fsum`), not numpy. So the screen tests need neither numpy nor the offline switches, and the cosine follows `transcription._cosine`'s rule.
  - `ui/models.py` (Tasks 1.1 and 1.4).
    - New `EnrolmentPart` and `ENROLMENT_SCRIPT`: the six parts with Task 0.1's words. Targets 30 / 15 / 12 / 15 / 12 / 15 s; caps 90 / 45 / 45 / 45 / 45 / 45 s; parts 2 and 5 not required.
    - New `ENROLMENT_PART_NAMES` ("quiet part", "moving-away part", …), `ENROLMENT_BEAT_SECONDS = 3.0` and the strings: the Record and Re-record labels, the fixed "keep reading" line, the preparing and listening lines, the saved line, the per-part counter (its denominator from the part), the heading, the get-ready line, the redo line, the weak-part line, the left-out line (D3's wording, with its seconds) and the strength line. All are added to `__all__`.
    - `LEARNING_NOT_ATTRIBUTED_NOTE` now reads Task 1.4's wording.
  - `note.py` (`spoken_by_confirmed_clinician`'s docstring) and `ui/note.py` (the module docstring's two learning paragraphs): restated in terms of the label (Task 1.4). Docstrings only; nothing executable changes on the note path (D8).
  - `ui/practitioner.py` (Task 1.2).
    - The seams. `CaptureFn` is now a Protocol that takes the part's two limits by keyword; `EmbedFn` returns `PartEmbedding` (default `enrol_part`); a new `beat_seconds` keyword (default 3.0) sets the beat.
    - The card. Four plain-text labels sit inside "Record your voice" (heading, cue, passage, the fixed line). Qt's default interaction flags are kept, so the passage cannot be selected. The labels are hidden at rest.
    - The worker. One `TaskThread` runs under one lease. The embedder is built first. Each part is one capture call, then `enrol_part`, and its PCM is deleted before the next part. A cancellable beat (`Event.wait`) comes before each later part and before the redo.
      - An optional part short at its cap on its first attempt is left out, with the seconds from its last progress event. A required part's shortfall, an embedding failure, a device failure and a Stop each end the enrolment with nothing saved.
      - At most one redo, of the weakest part; it replaces that part whole, and a redo short at its cap keeps the first attempt. The figures are then recomputed for the weakness line.
      - Then the combine, the seconds sum and the share, the final stop check, and the save. The result is `GuidedEnrolmentResult`.
    - The events: `PartStarted`, `BeatStarted` and `PartProgress`. `BeatStarted` also carries `redo`, beyond D3's two fields, so the redo line shows during the redo's beat. The slot drops progress for any part or attempt but the current one, and zeroes the meter and the counter at each part start and each beat start.
    - The busy test. `is_busy` is now the held lease. `_release_lease` re-applies the enablement after `end_enrolment`, and the failed handoff shows its error before the release. The success handler shows the saved line, the strength line, each left-out line and the weak-part line, then hides the card.
  - Named test changes:
    - `test_ui_screens.py` `_FakeCapture`: takes the two limits by keyword and records `(device, target, cap)` per call. It also gains `steps` (a scripted call: progress, error, a hold before or after the tick) and `progress_callbacks` (for the late-event case). Reason: the seam's new signature, and one call per attempt.
    - New helpers `_Step`, `_ScriptedEmbed`, `_plain_part` and `_SIX_PART_CALLS`. The helper `_practitioner_screen` defaults `embed` to a `PartEmbedding` and `beat_seconds` to 0.0. Reason: the seam's typed result; the beat is instant in tests (D3).
    - `test_enrolment_saves_profile_under_the_lease`:
      - the progress text at the release is the idle counter "Speech heard: 0 s of 30 s" (the card resets on every exit);
      - the status at the release is the saved line and the strength line;
      - `capture.calls` lists the six parts' limits;
      - the stored embedding is compared approximately (it is now the normalised mean);
      - the stored seconds are 6 × 31.0;
      - the busy list adds `is_busy`, Refresh devices and Confirm consent, and the card is hidden at rest.
    - `test_stop_after_the_capture_returned_still_saves_nothing`: its slow embed returns a `PartEmbedding`. Reason: the seam's type.
    - `test_delete_is_key_deletion_and_resets_consent`: the Record button's text is now "Record my voice (about three minutes)". Reason: six parts, 99 s of speech, plus beats.
    - `test_capture_start_hook_runs_before_the_capture_on_the_gui_thread`: the wrapper passes the limits on, and the expected order is the handoff then six captures, all on the one worker thread.
    - `test_a_failing_handoff_releases_the_lease_and_starts_nothing`: gains a release hook (the error is shown before the release) and checks that Record is enabled after it.
    - `TestMainWindow.test_close_refused_while_the_practitioner_tab_is_busy` sets `_lease` instead of `_task = _Running()`. Reason: the busy test is the lease now.
  - New cases:
    - in `test_ui_screens.py` `TestPractitionerScreen`, 17 items:
      - a part start shows its card at zero and drops a late event (with the passage not selectable);
      - Stop during a beat ends it at once;
      - a screen lock during a beat ends it at once, through the main window's `_on_session_locked` with a stand-in `_system_events`;
      - Stop during a re-record leaves `voice.enc` and `key.dpapi` unchanged;
      - a weak part is redone once and replaced whole (profile, seconds, strength line, and the redo's heading and line);
      - a redo that misses again is saved with the part named;
      - a redo short at its cap keeps the first attempt;
      - with two parts under the figure, only the lowest is redone;
      - an optional part is left out at its cap;
      - both optional parts are left out, each line with its own seconds;
      - one parametrised failure case ×3: a required part short, an embedding with no usable speech, a device failure;
      - the availability poll while a finished result is queued (controls disabled; Confirm consent and Delete write nothing over the new profile);
      - the final save under the one lease;
      - a re-record under a current consent record.
    - In `test_enrolment.py`, 16 items: `TestEnrolPart` (2, numpy `importorskip`), `TestGuidedParts` (10) and `TestEnrolmentScript` (4, the script's data and strings, and Task 1.4's line).
    - Stop during a part is the existing `test_stop_cancels_and_saves_nothing`.
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_enrolment.py < /dev/null`: all pass, 0 failed (16 more items than before; the two `TestEnrolPart` cases skip only without numpy).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py < /dev/null`: all pass, 0 failed (17 more items; the Windows-only ones run on this host).
    3. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: the previous total plus 33, 0 failed, the skip count unchanged.
    4. `git diff --stat -- desktop/tests/test_shadow_exits.py`: empty.
  - Open points. None is a must-pause; each is for the review or the live smoke.
    - (1) The script's words ship as approved, with the plan's quotation marks left off; part 3 is one phrase per line.
    - (2) Part 6's cue "Do not read." sits above D3's fixed "Keep reading until the counter fills…" line, as both are written. The practitioner may want that line changed for part 6 at the smoke.
    - (3) Strings the plan left open, written in plain English, are for the practitioner's eye at the smoke: the heading "Part N of 6: <title>" (the redo adds "(again)"), "Get ready - part N of 6 starts in 3 s.", the redo line's second sentence "Record it once more.", the weak-part line, and "Profile strength: N% of your speech matched your voice in the other parts."
    - (4) A required part's shortfall shows `record_enrolment`'s own text, which names no part (kept so the existing pins hold); the card hides on failure.
    - (5) Task 4.3's parity: the product's mean is plain-Python float64 and scratch's is numpy float64, so a vector comparison there needs a tolerance (labels and figures are unaffected in practice).
    - (6) For Task 5.2's wording search, outside Task 1.4's named places: `ui/note_review.py` near :243 and `note_config.py` near :1919 ("the practitioner's OWN utterance"), and `LEARNING_ON_LINE` ("shorthand you type over your own lines").
- Executor handoff (leg sx2, 2026-11-21T20:00+11:00): Tasks 1.1, 1.2 and 1.4 are 🟩, on the composer's evidence (38 / 522 / 11153 passed, 9 skipped; the `test_shadow_exits.py` diff empty; ruff and mypy clean). Progress is 45 % (10 of the 22 numbered tasks).
  - Phase 1's close review, `/review-loop` round 12 (1 of 3): 0 CRIT / 0 HIGH / 0 MED / 3 LOW, all applied. Details are in the Review Findings Log.
    - LOW-001: a Stop during the microphone handoff now stands. `ui/practitioner.py` clears the cancel event before the lease, not after the handoff.
    - LOW-002: a new 150 % pin for the card, `test_ui_phase_s.py` `TestGuidedCardWidth`.
    - LOW-003: the script's words are pinned whole in `test_enrolment.py`.
  - New test items: 1 in `test_ui_screens.py` (`test_a_stop_during_the_handoff_stands`) and 1 in `test_ui_phase_s.py`. `test_enrolment.py`'s count is unchanged (one case made stricter).
  - ruff and mypy are clean (72 files); line endings are unchanged. Not run by this leg (verify=composer).
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_enrolment.py tests/test_ui_screens.py tests/test_ui_phase_s.py < /dev/null`: all pass, 0 failed (38 + 523 items, and `test_ui_phase_s.py`'s previous count plus 1).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11155 passed, 9 skipped, 0 failed.
    3. `git diff --stat -- desktop/tests/test_shadow_exits.py`: empty.
  - Next: resume this leg with the output for round 13. It re-reviews the whole Phase 1 diff and should converge, since round 12 found no CRIT, HIGH or MED.
  - The wording choices for the practitioner's live smoke are listed in round 12, items (a) to (c).
- Executor handoff (leg sx3, 2026-11-21T20:15+11:00): Phase 1's `/review-loop` has CONVERGED in two of its three rounds.
  - Round 12: 0 CRIT / 0 HIGH / 0 MED / 3 LOW, all applied.
  - Round 13: 0 findings. It confirmed round 12's three fixes on the composer's green suite (600 passed over the three touched files; 11155 passed, 9 skipped in the full suite; the `test_shadow_exits.py` diff empty).
  - This leg changed no code and no test, so no suite run is owed.
  - Next (the composer): the codex peer pass over Phase 1's diff. Then the practitioner's live smoke of the guided card on the developer build, where round 12's wording points (a) to (c) are put to the practitioner. Then `/document` and the Phase 1 commit.
  - Reconciliation (leg sx5, 2026-11-21): the smoke was HELD on the practitioner's word, not performed, and is owed before Task P.1. `/document` and the Phase 1 commit go ahead without it.
- Executor handoff (leg sx4, 2026-11-21T20:20+11:00): codex peer round 14 (pass `stage-1.p1`, round 1 of 5) is transcribed and verified.
  - PR-MED-4201 holds as labelled (MED): through the microphone handoff the tab kept its idle controls, and the worker never re-reads the consent box.
  - The fix, applied in `ui/practitioner.py`: `_update_controls()` right after the lease is taken, before the handoff. Every control the busy state governs is then disabled for the whole lease, and Stop is the escape.
  - New case: `test_the_tab_is_busy_through_the_handoff` (`test_ui_screens.py`, Windows-only). It fails on the old code.
  - ruff and mypy are clean (72 files); line endings are unchanged. Not run by this leg (verify=composer).
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py < /dev/null`: 524 passed, 0 failed (523 plus the new case).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11156 passed, 9 skipped, 0 failed.
    3. `git diff --stat -- desktop/tests/test_shadow_exits.py`: empty.
  - Next: peer round 15 confirms PR-MED-4201's fix.
- Executor handoff (leg sx5, 2026-11-21T22:00+11:00): Phase 1 is DONE (Tasks 1.1, 1.2 and 1.4 🟩). This leg wrote the plan only: no code, no test, no Python.
  - The composer's run after leg sx4: `test_ui_screens.py` all passed; the full suite 11156 passed, 9 skipped, 0 failed; the `test_shadow_exits.py` diff empty.
  - Codex peer round 15 (pass `stage-1.p1`, round 2 of 5) is transcribed verbatim. It found 0 findings and confirmed PR-MED-4201's fix as a class, so the pass converged. Its Review History line is added, and `loop-history-check.py` reads 15 entries and 15 headings, OK.
  - The live smoke is recorded as HELD, not performed and not a pass, with the practitioner's words verbatim, on Phase 1's heading lines. It is owed: a dated line on Task P.1 says it must pass first, with round 12's wording points (a) to (c). No task's status changed for it.
  - Siblings reconciled: the handoff note's top lines, leg sx3's "Next" line and round 13's closing line.
  - The progress figure stays 45 %: 10 of the 22 numbered tasks, which already counted Phase 1.
  - Next (the composer): the Phase 1 close — history check, flush, `/document`, the local commit. Then Phase 2, Task 2.1 (the built row B1-35).
- Executor handoff (leg sb1, 2026-11-21T22:20+11:00): Phase 2's Task 2.1 (row B1-35) and Task 2.2's scratch mode are written; ruff and mypy are clean (72 files). This leg ran no pytest and no Python (verify=composer), so both tasks stay 🟨. No version change. Not edited: `attribute_speakers`, `enrolled_cluster`, `label_speakers`, `transcript_before`, `speaker_eval.py`, `ATTRIBUTION_THRESHOLD` and its pin, `test_shadow_exits.py`, and the five frozen scratch files. Line endings are unchanged (every touched tracked file reads CRLF in the working tree, as before).
  - `speaker_embedding.py`: `RECOVERY_MARK: Final = 0.35` beside the pass mark, with its dated decision line (Task 0.7, amending the practitioner-profile plan's D3 and D13); in `__all__` and the module docstring.
  - `transcription.py`:
    - New pure `recover_practitioner_labels(labels, similarities, has_text)`, beside `attribute_speakers` and in `__all__`. It returns the labels unchanged unless some score is at or above the pass mark and `enrolled_cluster` over them confirms `speaker_1`. Otherwise every segment scoring from 0.35 to under 0.50 becomes `speaker_1`. A `None` or -1 score is never relabelled, and no `speaker_1` is taken away. D4's acceptance check is kept as one rule: it cannot fail for a recovery-mark row, and a test pins that. Plain Python; no vector.
    - `assemble_transcript`: in the attribution branch only, `today = attribute_speakers(...)`, then the stored clinician and number are `enrolled_cluster` over `today`, then the labels are `recover_practitioner_labels(today, ...)`. The shortcut and the no-profile branch are as before, and neither calls the rule.
    - The `enrolment_similarity` docstring now says the number is the mean over the segments the cluster held before the mark ran (the direct matches), not over every line labelled the practitioner's. The same in `assemble_transcript`'s docstring.
  - Named test changes: none. Every existing test is unchanged; the items below are new.
  - New tests (20 items):
    - `test_attribution.py` (12):
      - `TestRecoveryMark` (7): the constants (0.35, the pass mark 0.50); at the mark, just under it, at and just under the pass mark; `None` and -1 never relabelled; no match, nothing runs; today's rule confirming `speaker_2`, nothing runs; a length mismatch refused; and the acceptance invariant over 3,000 generated score lists (where the rule runs the result is exactly today's labels plus the band, `speaker_1` still confirmed, no `speaker_1` removed; elsewhere unchanged).
      - `TestRecoveryInAssembly` (5): a relabelled consult stores today's clinician and number (0.9, not 0.65); the single-speaker shortcut after an empty slice and with a lone embedding never calls the rule, with today's number; the no-match branch keeps its 2-means labels; without a profile the rule is never called; a trim past the last direct match keeps the clinician and the number (`transcript_before` unchanged).
    - `test_live_transcription.py` (1), `TestRecoveryMarkOnBothDrivers`: one four-line fixture through the batch driver, and through the live worker drained by its receiver `models._live_transcript`. A direct match, a slice under the minimum, a text-bearing 0.40 line, and the other voice. Each driver embeds exactly the three long slices, in order; the 0.40 line becomes `speaker_1`; labels, clinician and number agree, with the number the direct match's alone. Every real VAD segment is longer than 25 ms, so the fixture raises the module's `MIN_ATTRIBUTION_PCM_BYTES` just past its short middle slice, a monkeypatch the test's docstring states.
    - `test_ui_screens.py` (7):
      - `TestTranscriptAutoConfirm.test_the_radio_follows_the_assembled_labels` ×3. Documents built by `assemble_transcript` for a direct match, a relabelled consult and the no-match branch. The checked radio is `speaker_1` in each, shown at 0.90, 0.90 and 0.45.
      - `TestNoteScreenTypedEdits`, the learning residue pinned as it is (4). The fixture is two patient-worded lines labelled the clinician's, chosen to match no shipped cue. Add then Save writes the phrase, and a number in such a line is refused by the filter. A typed Edit of the added line then Save writes one shorthand rule. With the opt-in off, and on a shadow recording, nothing is written. I chose Add over Move, since the plan's line reads "Add or Move".
  - Scratch, `.cursor/loops/sv-measure.py` (git-ignored; not one of the five frozen files):
    - Task 2.2's `--sets --against-product --built DIR [--only …]` (it refuses `--config`). Each encounter is decoded once with the built product, through the harness's enrolled path with a memory-only key. Scratch R0 (literal 0.50) and the built row `B1-35` are applied in memory to the same decode's assembly inputs and compared with the product's labels, clinician and number.
    - The owner holds only the spectral features, for the no-match 2-means; no speaker-model vector is captured.
    - Records are vector-free, through `write_record`: spans, every word field, scores, the branch, product / R0 / row labels, clinician and number, the harness clinician, the differences. They go to `sv-out/after/<HEAD>/<set>/`, or `<HEAD>-dirty` when `desktop/` is not clean, rewritten each run, so a clean-tree run can feed Task 4.1's decode check. A complete set at the same clean HEAD is skipped.
    - Self-test: one new check, 2b (the built row against the product's `assemble_transcript` over four generated cases: match with the band's edges, `None` and -1; no-match; shortcut; unconfirmed). `SELF_TEST_CHECKS` 55 → 56, and the two count rules move with it (26 → 27, 27 → 28).
    - Two self-test changes, both because the product now applies the mark (reason: Phase 0's premise, R0 equal to the product, no longer holds where a score sits in the band):
      - The whole-encounter check's fixture has a 0.45 segment beside a match. Its premise line now asserts that R0 differs from the product in labels only, at segment 2 only, and that the built row equals the product.
      - The frozen stitched module's checks run inside a new `phase0_product` context, which holds the product's recovery mark off (an identity) for them only. Its whole-run parity line compares scratch R0 with the pipeline, and its fake embedder can put a merged close-turn segment in the band. The 2b check and the whole-encounter check cover the built row against the product.
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_attribution.py tests/test_live_transcription.py < /dev/null`: all pass, 0 failed (13 more items than before).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py < /dev/null`: all pass, 0 failed (7 more items).
    3. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11176 passed, 9 skipped, 0 failed (11156 + 20).
    4. `git diff --stat -- desktop/tests/test_shadow_exits.py desktop/src/scribe_desktop/speaker_eval.py`: empty.
    5. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: equal to Task 0.6's five frozen values.
    6. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 56 `[ok]` lines (the sv-out scan's note under its check), `SELF-TEST: 56 passed, 0 failed`, exit 0.
    7. Task 2.2's run, on the practitioner's "start now" (C9: background, lid open; `C:\sv-sets\` from Phase 0 must still exist): `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --sets --against-product --built C:/sv-sets < /dev/null`. It prints one `[progress]` line per encounter (ids, segment count, branch, relabelled yes/no, differences), seven `[set]` lines each with `differences 0, errors 0, complete`, then `AGAINST-PRODUCT DIFFERENCES TOTAL: 0 (sets complete 7/7, errors 0, row B1-35)`, exit 0. It takes hours, like Phase 0's pass (the harness path decodes each encounter twice).
  - Recommendation: run step 7 once, after Phase 2's review, peer pass and commit, from the clean tree. Its records then sit under that HEAD and the same decode serves Task 4.1's decode check (D8 wants a clean, verified commit). A run before the commit writes `<HEAD>-dirty`, which counts for Task 2.2's parity only.
  - Open points. None is a must-pause.
    - (1) On this tree the frozen kept script `sv-measure-kept.py` checks scratch R0 against the product pipeline (`premise`), so it would now fail any recording with a score in the band. Its Task 0.6 run is done; it must not be run again on Phase 2's product. The same holds for the frozen stitched mode's own parity line: Task 4.3's `--stitched --against-product` will need a stitched comparison of the built row, and `sv_stitch.py` is pinned by `sv-measure-kept.py`. That is for Task 4.3's leg: a new module, or a new freeze.
    - (2) Task 5.2's Lever B documents (the threat model's recovery mark and its learning exposure, the trim case, the number's meaning, flows 7 and 14, the clinician review guide, the findings register row) are not written in this phase.
- Executor handoff (leg sb2, 2026-11-21T22:41+11:00): the four failing `TestNoteScreenTypedEdits` cases (composer's run of sb1's step 2) are fixed. Both faults were in the tests' fixture and setup, not in the product. The product does learn from a relabelled line: the learning residue the plan records stands as written. Ruff and mypy are clean (72 files). No product file was touched in this leg. Only `desktop/tests/test_ui_screens.py` changed, and only the four new sb1 tests and their fixture; CRLF is kept.
  - Finding 1, the phrase test (learning queue empty). sb1's two fixture lines opened "My knee …". The refusal filter checks a name first at the real first word, and a capitalised opener is name-like unless it is a common segment starter (`transcription._COMMON_SEGMENT_STARTERS`) or an admitted opener (`note_config._LEARNING_ADMITTED_OPENERS`). "my" is in neither, so the phrase "my knee felt wobbly" is refused as a name. That happens for ANY speaker's line, including the practitioner's own; it is the filter working as designed, not a gap in the relabelled path. The same opener would also have made line 5's refusal read "name", not "number". Fix: both lines now open "The knee …" (`the` is a common starter), as the class's existing learnable fixture "The knee felt steady on the stairs" does. The phrase is now "the knee felt wobbly"; the lines still match no shipped cue. A comment on the fixture states the opener fact.
  - Finding 2, Save refused in the other three tests (saved 0). They leave line 5, "… locked 3 times", out of the note. Check 4 (`note_check.omission_warnings`) warns `high_risk_omission` on any segment whose number is not carried. "Acknowledge all" never clears that warning (note-routing D4: its own row), and the shared helper `_acknowledge_everything` deliberately leaves it to the tests that make one. Fix: a new helper `_acknowledge_left_out_number` asserts that the warning is present and then acknowledges it by its own row, as the class's other omission tests do. It is called after `_ratify` in the shorthand test and in both gate cases. The phrase test adds line 5, so nothing there is left out.
  - Evidence that the product's path takes a relabelled line: in sb1's failing run, the shorthand test already reached `len(rule_queue()) == 1`. Its trigger is the line's tail, so the "My" opener did not stop it. That showed a clinician-labelled patient line reaching the learner before Save.
  - Named test changes in this leg: none to an existing test. Changed: the four sb1-new tests' fixture lines and phrase, and three `_acknowledge_left_out_number` calls; one helper added. The item count is unchanged (sb1's 20 new items).
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py < /dev/null`: all pass, 0 failed (531 passed).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11176 passed, 9 skipped, 0 failed. `test_pipe_client.py::TestHostOverARealPipe::test_the_app_stopping_says_not_running` may flake as it did in sb1's run (real-pipe timing, outside this diff); if it does, re-run it alone.
    3. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 56 `[ok]` lines, `SELF-TEST: 56 passed, 0 failed`, exit 0 (sb1's step 6, not yet run).
    4. Then sb1's step 7 (Task 2.2's long run) as sb1's recommendation says: after Phase 2's review, peer pass and commit.
  - Open points: sb1's (1) and (2) stand. None is a must-pause.
- Executor handoff (leg sb3, 2026-11-21T23:01+11:00): Task 2.1 is 🟩 on the composer's runs (213 + 531 passed; full suite 11176 passed, 9 skipped; self-test 56 passed; the `test_shadow_exits.py` / `speaker_eval.py` diff empty; the frozen hashes equal). Task 2.2 stays 🟨 until its long run. Phase 2's close review, `/review-loop` cap 3:
  - Round 16: 0 CRIT / 0 HIGH / 1 MED / 1 LOW, both plan text and applied. MED-001: Task 4.3's `--stitched --against-product` does not exist and the frozen stitched and kept parity now fails on this product; dated lines on Task 0.6 (not run again) and Task 4.3 (its leg builds and hardens the built-row comparison first). LOW-001: Task 5.2's residue wording, covering both learning paths and the opener rule, which is not a control.
  - Round 17: 0 / 0 / 0 / 0. Converged.
  - No code or test changed in this leg, so the composer's green suite stands; nothing to re-run. ruff and mypy were not re-run (nothing under `desktop/` changed since leg sb2's clean runs).
  - B1-35 matches D4, D9 and Task 0.7, as checked in round 16's "Checked and clean" list. No finding changes what the practitioner sees or what the app labels.
  - Next (the composer): the codex peer pass over Phase 2 (code and plan; the scratch `sv-measure.py` named as a separate read, git-ignored). Then the Phase 2 close and commit. Then Task 2.2's long run on the practitioner's "start now", from the clean committed tree (sb1's step 7).
- Executor handoff (leg sb4, 2026-11-21T23:06+11:00): plan only. No code, test or Python changed.
  - Codex peer round 18 (pass `stage-2.p1`, peer round 1 of 5) is transcribed verbatim into the Review Findings Log, with its Review History line. It found nothing; the pass converged. Its job 3 states a scope limit: the answer hop's implementation was outside its permitted files, so it checked that part through the consumer contracts only. That is not a finding.
  - Phase 2's state: Task 2.1 🟩; Task 2.2 🟨, its long run owed after the commit. No live smoke of its own (no screen changed; the labels' live check is Task P.3's mock smoke). A Phase 2 close line is under the phase heading.
  - Overall progress is 50%: 11 of 23 tasks done and Task 2.2 half done, counting Step H as one.
  - Siblings reconciled: the top lines (Last completed step, Current in-progress step, Immediate next action); Task 2.1's Files line (the docstring "before Phase 2" and "now"); Task 2.2's status line (its self-test and the owed run). sb1's step 7 and recommendation, sb2's step 4 and sb3's "Next" are kept as written: dated records, not live instructions, and consistent with the new top lines.
  - Next (the composer): the Phase 2 close (the history check, the flush, `/document`, the local commit). Then Task 2.2's long run on the practitioner's "start now" from the clean committed tree. Then Phase 4.
- Executor handoff (leg sb5, 2026-11-22T01:17+11:00): plan only; no code, test or Python.
  - Task 2.2 is 🟩 with the composer's evidence: the command, `4c29283`, the start and end times, the totals line, the per-set counts and the records folder. Phase 2's heading reads done (`4c29283`), and its close line has a dated note. Overall progress is 52%: 12 of 23, counting Step H as one.
  - The top lines are updated: Phase 2 closed; nothing in progress; next, Phase 4 with Task 4.1 first.
  - Siblings: Task 2.2's "owed" sentence has a dated "run, PASS" note. Task 4.1 gains a dated "After Task 2.2" block. Task 4.3 already says its comparison must be built first (round 16 MED-001), and it does not assume Task 2.2 unrun. sb1 to sb4's "owed" mentions, the Review Findings Log and round 18's "remains pending" are history and stand.
  - My read of Phase 4's first leg, Task 4.1:
    - From the composer:
      - Spawn the leg to write `sv-measure.py --trace` (scratch, git-ignored, not frozen) and its self-test cases. The decode check reads Task 2.2's records at `4c29283` against Phase 0's, through the script; the leg itself never opens `sv-out/`.
      - The leg's first job is to say whether those records hold every replay input the paired trace needs. If one is missing, the sets concerned need one more decode: about 8–15 minutes a set, as in Task 2.2.
      - Before any run, `git diff 4c29283 HEAD -- desktop/` must be empty. Commit the plan first, so `git status --porcelain` shows nothing but ignored files. Then `git diff <Phase 0 commit> 4c29283` over D8's note path, which should show only Task 1.4's wording hunks.
      - Then run the self-test, and review the new mode as earlier scratch modes were.
    - From the practitioner, each on their "start now", with C9's background-and-lid-open rule:
      - The decode check and the stages-off paired trace. These read records and replay through the shipped provider, with no model; minutes rather than hours, unless a re-decode is needed.
      - The paired trace in the gate configuration (`--suggestions confirm-all --prose`) over the 31 relabelled encounters. It needs the language model; overnight, as D8 allows.
      - D8's "after" harness reports: per set, `.venv/Scripts/python.exe scripts/run-validation.py C:/sv-sets/<set> --config validation/config --rule validation/rules/rule-v6.json --set <set> --suggestions off < /dev/null`, then the gate configuration (the same command with `--suggestions confirm-all --prose`) once. The stages-off pass decodes each set again, at least Task 2.2's 93 minutes for all seven; the gate configuration is an overnight run.
    - The `--trace` command line is the leg's to write; it is not named here.
  - Task 4.2 needs nothing built. It is the practitioner's run of `.venv\Scripts\python.exe scripts\replay-kept-recordings.py <the past_sessions folder>` from a normal terminal with both builds closed, the real folder path given in chat from `AGENTS.local.md`. Only `refused`, `incomplete` or `complete` with one comparison word is recorded. I have no timing for it from this run.
  - Task 4.3's leg first builds the B1-35-against-product stitched comparison in a new scratch module under D2's custody. It is hardened (review, peer pass, `/security-review`) before the practitioner's run, and neither frozen file is edited or run (round 16 MED-001).
  - No must-pause.
- Executor handoff (leg sg1, 2026-11-22T01:43+11:00): Phase 4's scratch tooling for Tasks 4.1 and 4.3 is written. This leg ran no Python and no pytest (verify=composer). Tasks 4.1 and 4.3 are 🟨 until their runs; Task 4.2 needs nothing built.
  - Files changed (all git-ignored scratch under `.cursor/loops/`, plus this plan; nothing under `desktop/`, `scripts/`, `validation/` or `extension/`; the five frozen scratch files untouched, and `sv-measure-kept.py` not run):
    - new `sv_trace.py` (Task 4.1): the gate, the frozen pins (`sv_lib.py`, `ffl_lib.py` at Task 0.6's values), the note-path check, the decode check and the paired trace, with 7 self-test checks.
    - new `sv_stitch_product.py` (Task 4.3): the built row against the product over the stitched truth, with 5 self-test checks. It imports the frozen `sv_stitch.py` and `sv_lib.py` and uses only their building blocks. It never runs `sv_stitch`'s own mode, whose parity compares R0 with the product.
    - `sv-measure.py`: three new modes, the module docstring, the `--again` flag on Task 2.2's mode, and the self-test registration. `SELF_TEST_CHECKS` 56 → 70 (one module check and 7 checks for the trace, one and 5 for the stitched-product module); both existing count rules move with it, and each new module check carries its own.
      - `--decode-check --verified COMMIT [--only …]`.
      - `--trace --verified COMMIT --built DIR --config DIR [--stages off|gate] [--only …]`.
      - `--stitched FOLDER --against-product`.
      - `--sets --against-product --again --only <set>` (D8's one re-decode; `--again` is refused without `--only`).
  - Do Task 2.2's records hold what Task 4.1 needs? Yes, read from the code that wrote them (`against_product_encounter`, `_word`, `pass_mode`'s `evaluate`). No input is missing, so no new decode is needed while `desktop/` is unchanged since `4c29283`.
    - The decode check needs nothing more than the records hold. Each record has the spans, the text flags, the scores, all six fields of every word (text, start, end, probability, uncertain, suspect), the branch and the spectral count. It also holds scratch R0's labels, clinician and number, and the product's labels, clinician and number. Phase 0's record holds the same fields, with R0 and B1-35 under `rows`. The Whisper model sits in both `run.json` files.
    - The trace needs nothing more either. A record holds every field of the transcript that the harness's replay, the composition, the metrics and the next-patient boundary read: segment times, labels, every word field, and the stored clinician and number.
    - What is not recorded: the document's session id, creation time, sample rate and speaker-model id. A search of `note*.py`, `consultation_phrases.py`, `validation.py` and `ui/models.py` finds no reader of them. `note.transcript_digest` hashes the whole document, but its value is in no outcome field and no placement, and both sides get the same fixed values. The script copies and label tracks come from `C:\sv-sets\` (synthetic; it still exists).
  - What the decode check does (D8):
    - It refuses, with codes only, unless `git status --porcelain` is empty and `git diff --name-only <verified> HEAD -- desktop` is empty. It also refuses unless `sv_lib.py` is at its pin and Task 2.2's records exist at that commit.
    - It then compares, per encounter, every field listed above. Field codes only, for example `words:probability`. The self-test shows a word whose probability alone differs is reported as exactly that.
    - It also refuses a Task 2.2 `run.json` that is not complete, not clean, from another commit, not row B1-35, or holding errors or differences.
    - It prints and writes `sv-out/after/<verified>/decode-check.json`: the verified commit, Phase 0's commit, and the SHA-256 of `sv-measure.py`, `sv_trace.py` and `sv_lib.py` (the trace adds `ffl_lib.py`). Task P.1 reads both.
  - The note-path check (D8's `git diff <Phase 0> <verified>` over the note path, made mechanical):
    - It compares every top-level definition the replay can reach, at the two commits, with docstrings left out; comments are not in the tree.
    - The reach starts from the harness's `evaluate_encounter`, `_compose_note`, `_compose_draft` and `suggestion_pass`, a few readers, and the two stage builders in `ui/models.py`. It also covers the whole of D8's listed note modules, and it follows names and one-level `module.name` attributes across `scribe_desktop` imports.
    - The two functions the replay patches out (`transcribe_in_temporary_store`, `read_wav_pcm`) are not followed.
    - A reached definition that differs is an executable change, and the trace is then refused (D8's must-pause). Task 1.4's `LEARNING_NOT_ATTRIBUTED_NOTE` is listed as a wording constant whose hunk is read.
    - It also prints D8's files with their changed-line counts, so each hunk can be read.
    - Interpretation: `ui/note_review.py` is added to D8's list, because `build_resolutions` confirms every proposal.
  - What the paired trace does (D8):
    - It runs the decode check and the note-path check first. A set whose decode check differs is not traced.
    - For each traced encounter whose labels differ, After is the product's labelling and Before is scratch R0's, both rebuilt from the record with the record's stored clinician and number. If R0's stored attribution differs from the product's, that is listed as a finding.
    - Each side is replayed through the shipped `evaluate_encounter` (`ffl_lib.replay_encounter`, `factory=validation.extractive_provider_from_config`). With `--stages gate`, the replay uses the gate configuration's two stages: `build_suggestion_stage()` and `build_prose_stage("narrative")`, refused without the language model.
    - Per side it records:
      - the outcome, with the stage's `model_seconds` left out;
      - the final note's placements: a quoted line as section, segment and word range; a configuration line as section, provenance and proposal id;
      - the next-patient flags (the detected boundary and the script's tail);
      - the ambiguous lines.
    - A role-unresolved side with a stored clinician is composed by scratch with that clinician, through the harness's own composition and, in the gate configuration, its suggestion pass.
    - A stage that reported itself unavailable is `not evaluated`. A stage never asked (no line left out) is a completed pass, not unavailable.
    - It flags D8's two must-pause kinds:
      - next-patient material admitted: an After line flagged by the boundary or the tail, with no Before line of the same segment overlapping it;
      - a line in a clinician-owned section it was not in before: by segment, or a configuration line by its proposal.
    - It prints one table row per differing encounter and a totals line. It writes `trace-<stages>.json` beside `decode-check.json`.
    - Exit codes: 0 when complete with no must-pause; 3 when complete with a must-pause, which goes to the practitioner; 1 when a set was not traced, a side was not evaluated, a side errored, or `--only` was given.
    - Interpretations for the tail and ambiguity rules, beyond the docstring: a word is in the tail when every script line it aligns to is at or after the tail's start. A line is ambiguous when a word straddles the start, or no word aligns at all, in a script that has a tail.
  - What `--stitched --against-product` does (Task 4.3, round 16's dated lines):
    - Refusals, in order, before any audio is read, one line each, exit 2: a developer build only; the folder; the thirteen-name manifest; `sv_lib.py` and `sv_stitch.py` at their pins and imported from `.cursor/loops`; git reporting HEAD with a clean checkout; crash reports excluded for this interpreter; the app's exclusion (both builds closed). It takes no `--enrolment`.
    - Take A through the product: `record_enrolment` with `ENROLMENT_SCRIPT`'s own limits (through the frozen file-backed capture), `enrol_part`, then `combine_parts`.
      - It is compared with the frozen measurement (`sv_stitch.build_take`, `enrol`, `unit_mean`): per part, kept or left out alike, the speech seconds equal and the vector difference 0; P1 within 1e-6 per component.
      - The capture limits are compared with the frozen measurement's.
      - The product's `part_consistency` and `weakest_part` say whether the app would ask for a part again; the redo is not simulated. Its `strength_share` is shown.
    - Each of the ten dialogues is stitched in memory and decoded by the product's batch driver with the product's P1, through `transcribe_in_temporary_store(persist_key=False)` (D2). Scratch's B1-35 is applied to the same decode's assembly inputs; the labels, clinician and number must show 0 differences.
    - The decode's embedder is the plain one, so no speaker-model vector of a dialogue segment is captured. The profile vectors sit in one `ProfileHolder`, cleared at the end and on any failure, behind `vector_boundary`.
    - The pools for B1-35 are compared with Task 0.5b's pasted strings (98.6 / 100.0 / 100.0 %, 0.0 %); this line gates. R0's (96.3 / 92.8 / 76.1 %, 0.0 %) is reported only.
    - It prints numbers, the thirteen manifest names, part numbers, dialogue names, the commit and the four scratch files' SHA-256 (`sv-measure.py`, `sv_stitch_product.py`, and the frozen pair); no path and no transcript text. It ends `STITCHED-PRODUCT PARITY: EQUAL` or `NOT EQUAL (<codes>)`, then `STITCHED-PRODUCT: COMPLETE`. Exit 0 only when equal.
  - For the composer now, short checks with no model and no long decode (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`. It should print 70 `[ok]` lines, the sv-out scan's note line, then `SELF-TEST: 70 passed, 0 failed`, exit 0. It takes a few minutes: the stitched-product checks run the whole mode twice on generated recordings.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: equal to Task 0.6's five frozen values. `git diff --stat -- desktop/ scripts/ validation/ extension/`: empty.
    3. After committing this plan, so `git status --porcelain` is empty: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`. Expected: two `[provenance]` commit and hash lines, with `sv_lib.py (frozen: equal)`; `[note-path] executable changes on the note path: 0`; the wording line naming `scribe_desktop.ui.models:LEARNING_NOT_ATTRIBUTED_NOTE`; the changed files (`note.py`, `ui/models.py` at least); seven `[decode]` lines each `differences 0`; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0, in under a minute. If the note-path line shows an executable change, read the named definitions' hunks before anything else: either the reach over-includes (a fix to the scratch tool) or D8's must-pause applies.
  - Long runs, each on the practitioner's "start now" (C9: background, lid open, `C:\sv-sets\` still present):
    - (a) The stages-off paired trace, no model, over the 31 relabelled encounters; about 10–20 minutes:
      `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --trace --verified 4c29283 --built C:/sv-sets --config validation/config --stages off < /dev/null`.
      Expected: 31 `[trace]` lines, then the table and `TRACE OFF: traced 31, equal by construction 152, …`. The exit code says whether a must-pause was found (3), and differences are expected (attribution seconds at least). Any must-pause row goes to the practitioner before Phase P (D8).
    - (b) The gate-configuration trace, the language model, the same 31 encounters on both sides; overnight (several hours):
      the same command with `--stages gate`.
    - (c) D8's "after" harness reports at the verified commit. The seven sets with `--suggestions off`, about 93 minutes in all at Task 2.2's pace (8–15 minutes a set), for each set:
      `.venv/Scripts/python.exe scripts/run-validation.py C:/sv-sets/<set> --config validation/config --rule validation/rules/rule-v6.json --set <set> --suggestions off > .cursor/loops/sv-out/after/4c292833486533ba678ca4dad28e617a53aa82d7/report-<set>.md < /dev/null`.
      Then the gate configuration once (`--suggestions confirm-all --prose`), overnight. Their verdict lines are read; their SHA-256s go in the plan with the commit (`sha256sum`; no `--record-after` mode was built, an open point below).
    - (d) Only if a set's decode check differs: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --sets --against-product --again --only <set> --built C:/sv-sets < /dev/null`, 8–15 minutes a set, then the decode check again.
  - Task 4.3 before the practitioner's run:
    - First: `/review-loop`, a codex pass and `/security-review` over `sv_stitch_product.py` and the `--stitched --against-product` dispatch in `sv-measure.py`, as for Task 0.6's script.
    - Then the freeze: the SHA-256 of `sv-measure.py` and `sv_stitch_product.py` recorded in the plan, and checked again just before the run.
    - Then the practitioner's run, PowerShell form, from the repository root in a normal terminal with both builds closed and the lid open; the composer gives the folder in chat:
      `.venv\Scripts\python.exe .cursor\loops\sv-measure.py --stitched <the stronger-voice folder> --against-product`.
    - Expected time: about 30–45 minutes. It decodes the same ten dialogues as Task 0.5b, skips P0, P2 and the sub-window grid, and captures take A twice.
    - The practitioner pastes everything from `# Stronger-voice stitched parity (Task 4.3)` to `STITCHED-PRODUCT: COMPLETE`.
  - Open points (none is a must-pause):
    - (1) A freeze of `sv-measure.py` for Task 4.3 also covers Task 4.1's dispatch, so a later change to `sv-measure.py` needs a new freeze before Task 4.3's run. That is why the trace's logic lives in `sv_trace.py`.
    - (2) D8's "after" reports have no provenance mode like `--record-before`. Their hashes and commit go into the plan by hand. A `--record-after` is a small addition if the composer wants it.
    - (3) The stitched run checks its frozen pair's bytes on disk and where they were imported from, after import. A file swapped between import and check is a same-user local race on scratch files, not a check of the loaded bytes; Task 0.6's script ran verified bytes, and the hardening may ask for that here. [2026-11-22, leg sg2: closed by round 19 MED-001; the pins are now the bytes that ran.]
- Executor handoff (leg sg2, 2026-11-22T01:58+11:00): Task 4.1's decode check is recorded, and the hardening `/review-loop` has started.
  - Task 4.1: the decode check's run at `11c3827` is recorded in the task (0 differences on 7 of 7 sets, 183 encounters). On the note path, the `ui/models.py` hunks were read: one wording constant changed (`LEARNING_NOT_ATTRIBUTED_NOTE`, the message of the two learning verdicts); the rest is Phase 1's new enrolment script and text functions, which the note path does not reach. Task 4.1 stays 🟨.
  - Round 19 (`/review-loop` round 1 of 3): 0 CRIT / 0 HIGH / 1 MED / 2 LOW, all applied in scratch (the Review Findings Log has the detail).
    - MED-001: the checked load. `sv-measure.py` runs every scratch module from bytes read once and keeps their SHA-256 on the module. The pin checks (the stitched run's and the trace's) read that digest, so the check is of the code that ran (Task 0.6's rule).
    - LOW-001: the practitioner-run mode prints no traceback, warning, thread exception or unraisable, and a failure outside its inner guard is named by type.
    - LOW-002: the gate also holds `validation/` unchanged since the verified commit, and `--trace` takes only `--config validation/config`.
  - Files changed in this leg:
    - `sv-measure.py`: the checked loader and `ran_sha256`, the two hooks passing it, the trace's `--config` refusal and two docstring lines.
    - `sv_stitch_product.py`: `Env.ran_sha256`, the pin refusal, the provenance wording, `product_mode`'s quiet hooks and outer guard, and the self-test (check 1's ran digests, two new refusal cases).
    - `sv_trace.py`: `scratch_hashes` from the ran digests, `TraceHooks.ran_sha256`, `GATED_PATHS`, the gate's wording, and the self-test (check 3's real digests and two gate cases).
    - The plan: the Task 4.1 record, round 19, this bullet.
    - No product, test, rule or frozen file changed. `SELF_TEST_CHECKS` stays 70.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum` of the five frozen files: unchanged from Task 0.6's pins.
    3. The decode check again, because its gate and pin code changed. First commit the plan, so the checkout is clean; the gate refuses otherwise. Then `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`. Expect the same lines as at `11c3827`: `[provenance] sv_lib.py sha256 f53244af… (frozen: equal)`, note path 0 executable and 1 wording, and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
    4. One refusal smoke for the new `--config` rule (reads nothing, decodes nothing): `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --trace --verified 4c29283 --built C:/sv-sets --config desktop --stages off < /dev/null`. Expect one line, `[refused] --trace needs --config validation/config (the repository's own, as committed)`, exit 2.
  - Then: the composer resumes me with the output for round 20, round 2 of 3, which confirms round 19's fixes. The long runs listed in the leg sg1 bullet are unchanged and still wait on the practitioner's "start now". The trace's command is the same, with `--config validation/config`.
  - Residue (for the peer pass and `/security-review`): `sv-measure.py`'s own digest is a read of its file at its start, not the bytes Python compiled; the freeze's hash check just before the practitioner's run covers it, as for Task 0.6's script.
- Executor handoff (leg sg3, 2026-11-22T02:04+11:00): review round 20 (round 2 of 3) is done. It counted 0 CRIT / 0 HIGH / 0 MED / 2 LOW, both applied in scratch, and it confirmed round 19's three fixes against the composer's green runs.
  - LOW-001 (`sv_trace.py` `evaluate_side`): the whole side is now guarded. A failure in the scratch composition, the boundary or the alignment is that side's `error:<Type>`, and the trace goes on and writes its record. The trace's check 7 gains one assertion.
  - LOW-002 (`sv_stitch_product.py`): the outer guard and the quiet hooks are now `guarded_run` and `install_quiet_hooks`, each tested. The stitched-product check 5 gains three assertions: an environment that fails to build, a release that raises after a refusal, and the hooks installed and then restored. This closes leg sg2's untested-path open point.
  - The digest-at-start residue is kept as named, not fixed. The round 20 entry gives the reason: a file cannot pin its own hash, and the interpreter keeps no copy of a script's source bytes. The freeze's check just before the run covers it.
  - Files changed: `sv_trace.py` (`evaluate_side`, check 7) and `sv_stitch_product.py` (`install_quiet_hooks`, `guarded_run`, `product_mode`, check 5); the plan (round 20, this bullet). `SELF_TEST_CHECKS` stays 70. `sv-measure.py` is unchanged in this leg.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`. Expect 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum` of the five frozen files: unchanged.
    3. No decode check rerun is needed: neither the decode check's code nor its gate changed in this leg (`evaluate_side` is the trace's only).
  - Then: resume me with the output for round 21, the last under the cap. If it finds nothing, the review has converged, and the codex peer pass and `/security-review` follow (the composer's), then the SHA-256 freeze of `sv-measure.py` and `sv_stitch_product.py` before the practitioner's Task 4.3 run.
- Executor handoff (leg sg4, 2026-11-22T02:09+11:00): review round 21 (round 3 of 3, the cap) is done. Hardening rounds so far:
  - round 19: 0 CRIT / 0 HIGH / 1 MED / 2 LOW;
  - round 20: 0 / 0 / 0 / 2;
  - round 21: 0 / 0 / 1 / 0.

  Every finding is applied. The review reached its cap with round 21's MED-001 fixed and not yet confirmed by a further round; the codex peer pass that follows is its confirm.
  - MED-001 (`sv_trace.py`): the note path's reach was seeded only from the harness's entry points. It is now seeded as well from every package name the scratch replay itself uses (`ffl_lib.py` and `sv_trace.py`), read from the bytes that ran. Every bare string statement, a field docstring included, is left out. `ffl_lib.py` is now pinned by the decode check too.
  - Files changed: `sv_trace.py` (`_is_bare_string`, `_strip_docstrings`, `_WithScratch`, `scratch_seeds`, `note_path(scratch=)`, `REPLAY_SCRATCH`, `prepare`, `hashlib`, check 4); `sv-measure.py` (`DECODE_CHECK_FILES` with `ffl_lib.py`, `TRACE_FILES` equal to it, the docstring); the plan (round 21, this bullet). `sv_stitch_product.py` is unchanged in this leg. `SELF_TEST_CHECKS` stays 70.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum` of the five frozen files: unchanged.
    3. The decode check again, because its note-path code and its pin list changed. Commit the plan first so the tree is clean, then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`.
       - Expected: a new `[provenance] ffl_lib.py sha256 f7d2d75c… (frozen: equal)` line; `[note-path] executable changes on the note path: 0`; the wording line naming `LEARNING_NOT_ATTRIBUTED_NOTE`; the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - If the executable count is not 0, the line names the definitions. Hand them to me before anything else: either a definition the replay now reaches really changed since Phase 0 (D8's must-pause, the trace stays refused), or the reach over-includes (a scratch fix).
  - Then the composer's codex peer pass and `/security-review` over the three scratch files and the plan's Phase 4 lines, then the SHA-256 freeze of `sv-measure.py` and `sv_stitch_product.py` before the practitioner's Task 4.3 run. The long runs in the leg sg1 bullet are unchanged and still wait on the practitioner's "start now".
- Executor handoff (leg sg5, 2026-11-22T02:19+11:00): codex peer round 22 (pass `stage-4.p1`, peer round 1 of 5) is transcribed verbatim. Its two findings (0 CRIT / 0 HIGH / 2 MED / 0 LOW) are verified as labelled and applied in scratch.
  - PR-MED-4501 (`sv_trace.py`): the note-path gate now compares a module's own import bindings. Changing only which helper a caller's import binds to is now an executable change, and a whole note module's imports are seeded. The trace's check 4 gains "import-rebinding".
  - PR-MED-4502 (`sv-measure.py`): a set whose attempt failed in this run (an enrolment WAV that could not be enrolled) can no longer be counted complete from an older record. `against_product_summary(root, sets, failed)` is the summary. The totals line adds `attempts failed N`, and the exit is 0 only with none failed. Check 2b gains two assertions.
  - Files changed: `sv_trace.py` (`_references`, `reach`, check 4); `sv-measure.py` (`against_product_mode`, the new `against_product_summary`, check 2b); the plan (round 22 and its verification, this bullet). `sv_stitch_product.py` is unchanged. `SELF_TEST_CHECKS` stays 70.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean. Then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`, because the note-path code changed.
       - Expected: the same lines as at `8b424b6`, namely `ffl_lib.py … (frozen: equal)`, `[note-path] executable changes on the note path: 0`, the one wording line (`LEARNING_NOT_ATTRIBUTED_NOTE`), the same changed-file lines, seven `[decode]` lines with differences 0, and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - The note path now also compares import bindings. Of the files changed since Phase 0, none rebinds an import a reached definition uses, as far as the diff shows, so 0 is expected. Any `module:name` it lists is read before anything else.
  - Then the composer's peer round 23 as the confirm, then `/security-review` and the SHA-256 freeze. The long runs are unchanged.
- Executor handoff (leg sg6, 2026-11-22T02:31+11:00): codex peer round 23 (pass `stage-4.p1`, peer round 2 of 5) is transcribed verbatim. It counted 0 CRIT / 0 HIGH / 1 MED / 1 LOW and confirmed round 22's two fixes. Both findings are verified as labelled and applied in scratch, and the note-path gate's sweep closed five siblings (s1)–(s5) and the relative-import resolution (the round 23 entry has each, with its self-test case).
  - PR-MED-4601 (`sv_trace.py`): the module statements of every reached module, of its parent packages and of its whole package-import closure are compared, at both commits. Names bound inside module-level `if`/`try` blocks are followed, and attribute or subscript assignments count as module statements. Changed non-Python files under the package or `validation/config` count as `<data file>` changes.
  - PR-LOW-4601 (`sv-measure.py`): the stitched-product run sets a type-only `sys.excepthook` and silences thread exceptions, unraisables and warnings before any package import. The mode's own import is under a type-only guard, and the parser takes no abbreviations.
  - Files changed:
    - `sv_trace.py`: `_absolute`, `_plain_target`, `_binds_names_only`, `_nested_bindings`, `ModuleInfo.imported`, `Source.is_package` / `_alias_entries` / `info`, `_references`, `note_path(data_changes=)` and its comparison closure, `DATA_PATHS`, `prepare`, the docstring, check 4.
    - `sv-measure.py`: `TYPE_ONLY_LINE`, `stitched_product_requested`, `_type_only_excepthook`, `_quiet_hook`, `install_stitched_product_hooks` and their call at the top, `allow_abbrev=False`, the guarded import in `main`, check 13.
    - The plan: round 23, this bullet.
    - `sv_stitch_product.py` is unchanged. `SELF_TEST_CHECKS` stays 70.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean, then `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`.
       - Expected: both frozen files `equal`; seven `[decode]` lines with differences 0; `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`.
       - The note path is now much wider: the import closure's module statements and the data files. 0 executable is expected, since the diff since Phase 0 touches only `.py` files and, as far as I can see, only their definitions. But this is the first run of the wider gate.
       - If it lists any `…:<module statements>` or `…:<data file>` (exit 1), send me the names before anything else. I read each hunk: either a real module-level change on the note path (D8's must-pause, the trace stays refused) or one that does not change the replay (recorded by name, and the gate stays conservative unless the plan decides otherwise).
  - Then the composer's peer round 24 as the confirm, then `/security-review` and the SHA-256 freeze. The long runs are unchanged.
- Executor handoff (leg sg7, 2026-11-22T02:35+11:00): the composer's sg6 run gave `SELF-TEST: 69 passed, 1 failed`. The one failure was check 13's "import-failure" assertion (`detail: import-failure:1:[error] the run stopped (ModuleNotFoundError); no table is printed`). The decode check at `73ba68d` was exit 0, with the wider note-path gate listing no name.
  - Diagnosis: the fault was in the TEST, not the tool. The guard behaved as built: exit 1, exactly one type-only line, no message text. The test makes the import fail by putting `None` in `sys.modules`, and Python then raises `ModuleNotFoundError` (an `ImportError` subclass), which the guard names exactly. The assertion had expected the base class's name.
  - Fix: the assertion now expects `ModuleNotFoundError`. The guard, the start-up hooks and the exact-flag parser are unchanged. The check still fails if the guard printed a traceback, a message, another line or another exit code. `SELF_TEST_CHECKS` stays 70.
  - Files changed: `sv-measure.py` (check 13's one assertion); the plan (this bullet).
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: `SELF-TEST: 70 passed, 0 failed`, exit 0.
    2. `sha256sum` of the five frozen files: unchanged.
    3. No decode check rerun is needed: neither its code nor `sv_trace.py` changed in this leg.
  - Then peer round 24, the confirm of round 23's fixes and this one.
- Executor handoff (leg sg8, 2026-11-22T03:04+11:00): codex peer round 24 (pass `stage-4.p1`, peer round 3 of 5) is transcribed verbatim. It counted 0 CRIT / 0 HIGH / 1 MED / 1 LOW and confirmed round 23's fixes, the five sweep closures and sg7's correction. Both findings are verified as labelled and applied in scratch. The round 24 entry has each tuple, the design and the gate's guarantee and residues.
  - PR-MED-4701 (`sv_trace.py`): the class is closed, not the instance. Every loaded module's import-time code is a root of the reach, in a fixpoint across both commits.
    - What that code RUNS (a callee and its arguments, a decorator, a base or metaclass, an iterated, entered, raised, formatted or hashed value) is compared whole and followed in full.
    - What it only TOUCHES is followed as far as touching can run code.
    - A definition that is not inert by a strict grammar is compared whole.
    - Phase 1's and Phase 2's additions are all inert by that grammar, so they are not counted. They are not on the note path (D8: only `ui/models.py`'s composition helpers).
    - Check 4 gains seven cases. Four fail without the fix ("initializer-body", the peer's reproduction; "decorator-body"; "default-argument"; "class-getitem"). Three keep it from over-counting ("touched-class", the shape of `LiveTranscriberSource`; "inert-additions", Phase 1's shape; "non-inert-addition").
  - PR-LOW-4701 (`sv-measure.py`): the parser's errors raise a private exception. `main` then prints one fixed, argument-free line (`ARGUMENTS_REFUSED_LINE`) and exits 2, in every mode, so a mistyped mode flag is covered too. Check 13 gains "parse-refused" with a synthetic private-path sentinel (the folder repeated; the flag mistyped).
  - Files changed:
    - `sv_trace.py`: `ModuleInfo.roots` / `lazy`, `_INERT_DECORATORS`, `_lazy_annotations`, `_literal`, `_dataclass_decorator`, `_value_class`, `_inert_value`, `_inert_annotation`, `_inert_function`, `_inert_class`, `_inert_definition`, `Source.info`'s roots, `_passes_function`, `_import_refs`, `reach` (its loaded modules, rooted and touched items), `note_path`'s fixpoint (the round 23 closure folded into `reach`), the docstring, check 4;
    - `sv-measure.py`: `NoReturn`, `_ArgumentsRefused`, `ARGUMENTS_REFUSED_LINE`, `_QuietParser`, `main`'s parser and its refusal, check 13;
    - the plan: round 24, its Review History line, the top line, this bullet.
    - `sv_stitch_product.py` is unchanged. `SELF_TEST_CHECKS` stays 70.
  - Not run in this leg: no Python and no ruff or mypy over scratch (my grants run them over `desktop/` only). The new code is unexercised until the composer's self-test.
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0. A `[FAIL]` detail in check 4 names the case and the names it found, and one in check 13 names the case, the exit code and the printed length. Send me the line.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean. Then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`, the first run of the import-time reach.
       - Expected, as at `bd3a147`: both frozen files `equal`; `[note-path] executable changes on the note path: 0`; the one wording line (`LEARNING_NOT_ATTRIBUTED_NOTE`); the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - It may run slower than before, since every loaded module's top level is now parsed and followed, but it decodes nothing.
       - If it lists any name (exit 1), send me the names before anything else. I trace each one's import-time chain: either a real import-time dependency changed since Phase 0 (D8's must-pause, the trace stays refused), or an over-inclusion. An over-inclusion is recorded by name, and the gate keeps counting it unless the plan decides otherwise.
  - Then peer round 25 as the confirm (two rounds of the cap remain), then `/security-review` and the SHA-256 freeze. The long runs are unchanged.
- Executor handoff (leg sg9, 2026-11-22T03:14+11:00): codex peer round 25 (pass `stage-4.p1`, peer round 4 of 5) is transcribed verbatim. It counted 0 CRIT / 0 HIGH / 1 MED / 0 LOW and confirmed round 24's fixes. PR-MED-4801 is verified as labelled and applied.
  - PR-MED-4801 (`sv_trace.py`): every binding that import-time code reads (the reach's touched set) is now compared whole at both commits, besides what runs and the non-inert definitions. It is one change: `reach` returns `needed | rooted | touched`. What only runs at import is still the only thing followed through its body.
  - The stronger rule (every module-level statement of every loaded module compared whole) was not taken: it would count Phase 1's and Phase 2's additions, none of which import-time code reads (named in the round 25 entry, off the note path by D8).
  - Check 4: "condition-constant" is the peer's reproduction, expecting exactly `helpers:ENABLED`; it fails without the fix. Round 24's "touched-class" case is replaced by "touched-compared" (counted) and "touched-not-followed" (clean).
  - Files changed: `sv_trace.py` (`reach`'s return and docstring, the module docstring, check 4); the plan (round 25, its Review History line, the top line, this bullet). `sv-measure.py` and `sv_stitch_product.py` are unchanged in this leg. `SELF_TEST_CHECKS` stays 70.
  - Not run in this leg (no Python on this seat).
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0. A `[FAIL]` in check 4 names its case and the names found: send me the line.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean. Then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`.
       - Expected, as at `e7f7cf6`: both frozen files `equal`; `[note-path] executable changes on the note path: 0`; the one wording line (`LEARNING_NOT_ATTRIBUTED_NOTE`); the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - If it lists any name (exit 1), send me the names first. It would be a binding read at import that changed since Phase 0. I read its hunk: either D8's must-pause, or over-inclusion recorded by name, with the gate kept conservative.
  - Then peer round 26, the last under the cap, as the confirm; then `/security-review` and the SHA-256 freeze. The long runs are unchanged.
- Executor handoff (leg sg10, 2026-11-22T03:24+11:00): codex peer round 26 (pass `stage-4.p1`, peer round 5 of 5, the cap) is transcribed verbatim. It counted 0 CRIT / 0 HIGH / 1 MED / 0 LOW and confirmed round 25's fix. PR-MED-4901 is verified as labelled and applied.
  - PR-MED-4901 (`sv_trace.py`): each loaded module now also compares ONE ordered list, in source order, of its compared statements, package imports and module statements. Each is identified by the names it binds, not its content, which stays compared per name. A move among them counts as `<module>:<order>`.
  - Phase 1's and Phase 2's additions bind no compared name and are left out, so 0 executable is still expected at the verified commit.
  - Check 4 gains "reordered-initialization", the peer's reproduction (exactly `helpers:<order>`). It fails without the fix.
  - The round 26 entry states the gate whole: what it compares, (a) to (d), and the ten things it does not compare, as a complete list.
  - Cap verdict: accept — test-harness — PR-MED-4901 is verified and fixed with a failing-without-fix case. The gate is scratch tooling whose 0-executable result is a cross-check beside Task 2.2's and the decode check's direct 0-difference measurements, its limits are now listed in full, and `/security-review` follows.
  - Files changed: `sv_trace.py` (`ModuleInfo.order`, `Source.info`'s order keys, `note_path`'s ordered comparison, the module docstring, check 4); the plan (round 26, its Review History line, the top line, this bullet). `sv-measure.py` and `sv_stitch_product.py` are unchanged in this leg. `SELF_TEST_CHECKS` stays 70.
  - Not run in this leg (no Python on this seat).
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0. A `[FAIL]` in check 4 names its case and the names found: send me the line.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean. Then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`.
       - Expected, as at `ef5a54c`: both frozen files `equal`; `[note-path] executable changes on the note path: 0`; the one wording line (`LEARNING_NOT_ATTRIBUTED_NOTE`); the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - If it lists `<module>:<order>` or any other name (exit 1), send me the names first.
  - Then `/security-review` and the SHA-256 freeze of `sv-measure.py`, `sv_trace.py` and `sv_stitch_product.py` before the practitioner's runs. The long runs are unchanged.
- Executor handoff (leg sg11, 2026-11-22T03:32+11:00): Phase 4's H3, `/security-review` round 27, over the three scratch files with the stitched mode first. 0 CRIT / 0 HIGH / 0 MED / 1 LOW, written into the Review Findings Log with its Review History line.
  - Checked and found as built:
    - the stitched mode's refusal order, each before any audio read;
    - its print surface: numbers, names, codes and digests only; failures by type; thread, unraisable and warning output silenced; parse errors as one fixed line;
    - D2 custody: audio and vectors in memory only, the encrypted temporary stores gone, the holder and the owner cleared on every path;
    - no file written and no standard input read (C9);
    - the hash checks of the files that ran.
  - SEC-001 (LOW, fixed): `sv-measure.py` kept the scratch folder first on `sys.path`, so a stray `.py` there named like a module imported later would have run unchecked. That is a regression from Task 0.6's script, which took the folder off. The folder is now removed from `sys.path` before any other import, and the scratch modules are found only by the checked finder. Check 13 gains "scratch-folder-off-path", which fails without the fix.
  - Files changed: `sv-measure.py` (its first lines, the removed `sys.path.insert`, check 13); the plan (round 27, its Review History line, the top line, this bullet). `sv_trace.py` and `sv_stitch_product.py` are unchanged in this leg. `SELF_TEST_CHECKS` stays 70.
  - Not run in this leg (no Python on this seat).
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0. An `ImportError` or `ModuleNotFoundError` naming a scratch module would mean a scratch import missed the checked finder: send me the line.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan, so the tree is clean. Then run `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`, because `sv-measure.py` changed.
       - Expected, as at `48c4ebb`: both frozen files `equal`; `[note-path] executable changes on the note path: 0`; the one wording line; the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - The `sv-measure.py` digest line changes, which is expected.
    4. The freeze, only after 1 to 3 pass and with no further edit to the three files: `sha256sum .cursor/loops/sv-measure.py .cursor/loops/sv_trace.py .cursor/loops/sv_stitch_product.py < /dev/null`.
       - The composer records the three values as one dated line in Task 4.3's entry, under "The mode now exists (2026-11-22, leg sg1)", for example "Frozen (2026-11-22, after `/security-review` round 27): `sv-measure.py` <value>, `sv_trace.py` <value>, `sv_stitch_product.py` <value>". It commits that line.
       - At the practitioner's Task 4.3 run, the table's provenance lines (`sv-measure.py sha256 …`, `sv_stitch_product.py sha256 …`, the bytes that ran) must equal those pins. The Task 4.1 trace runs are checked against the `sv-measure.py` and `sv_trace.py` pins the same way.
       - I write no hash value here: I have not seen them.
  - Then Phase 4's remaining steps are the practitioner's runs (Task 4.1's long runs on "start now", Task 4.3, Task 4.2), each against the frozen files.
- Executor handoff (leg sg12, 2026-11-22T10:55+11:00): round 28, RUN-001 (MED), from the composer's long run (b), verified from the code and fixed. Written into the Review Findings Log with its Review History line.
  - The cause: the trace never called `benchmark.apply_offline_env()`. The gate side's language model calls `assert_offline_env()` before it loads (`language_model.py` line 283), so every side was `error:OfflineEnvError`. The harness applies it in its own `main` only (`validation.py` 4556–4557), and `sv-measure.py` only in `_numpy()`, which no `--trace` path reaches. With the stages off no model loads, which is why (a) passed.
  - The fix, in `sv_trace.py` alone: the new `offline_start()` (apply, then assert, the refusal by type) is `trace_mode`'s first statement, in both stage settings, before `prepare` and any model. Check 7 gains three assertions that fail without it. `TRACE_CHECKS` stays 7 and `SELF_TEST_CHECKS` 70.
  - `sv-measure.py` is byte-unchanged, so Task 4.3's stitched mode keeps its frozen bytes (545edf93…be6e); the fix needed nothing there, because `trace_mode` is the trace's one entry. `sv_stitch_product.py` is unchanged.
  - Task 3, `validation.main` against the trace's gate entry: the offline environment was the one missing step. Every other step is done, or not needed because nothing decodes. Each is listed in round 28.
  - Files changed: `sv_trace.py` (`import os`, `offline_start`, its call, check 7); the plan (round 28, its Review History line, the top line, this bullet).
  - Not run in this leg (no Python on this seat).
  - For the composer now (every call ends `< /dev/null`):
    1. `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`: 70 `[ok]` lines, then `SELF-TEST: 70 passed, 0 failed`, exit 0. A `[FAIL]` in check 7 naming `offline-start:<stages>:<code>:<seen>` means the start did not set the environment before `prepare`: send me the line.
    2. `sha256sum .cursor/loops/sv_lib.py .cursor/loops/ffl_lib.py .cursor/loops/ffl-measure-kept.py .cursor/loops/sv_stitch.py .cursor/loops/sv-measure-kept.py`: unchanged from Task 0.6's pins.
    3. Commit the plan (`sv_trace.py` is git-ignored scratch, pinned by its hash), so the tree is clean. Then `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`.
       - Expected, as at `c8edce3`: both frozen files `equal`; `[note-path] executable changes on the note path: 0`; the one wording line; the same changed-file lines; seven `[decode]` lines with differences 0; and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, exit 0.
       - The `sv_trace.py` digest line changes; `sv-measure.py`'s stays the frozen value.
       - The note path's scratch seeds now include `scribe_desktop.benchmark`'s three offline names (round 28's side effect); `benchmark.py` is unchanged between the two commits, so 0 is still expected. If any `benchmark:` name is listed, send me the names first.
    4. The new freeze, only after 1 to 3 pass: `sha256sum .cursor/loops/sv_trace.py .cursor/loops/sv-measure.py .cursor/loops/sv_stitch_product.py < /dev/null`. Only `sv_trace.py`'s value should differ from the `c8edce3` line.
       - The composer adds ONE new dated sub-bullet in Task 4.3's entry, directly under the "Frozen (2026-11-22, after `/security-review` round 27; …)" line, never editing it. For example: "Frozen again (2026-11-22, after round 28, RUN-001): `sv_trace.py` <value>; `sv-measure.py` and `sv_stitch_product.py` unchanged. Checked against it the same day: …". It commits that line.
       - I write no hash value here: I have not seen it.
    5. The re-run of (b), on its own, after the background gate-configuration harness reports have finished. They load the same 2.3 GiB model, and the suggestion stage's 240 s cap is wall-clock, so running both at once could make one side "not evaluated" for a reason the labels did not cause. The command is unchanged: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --trace --verified 4c29283 --built C:/sv-sets --config validation/config --stages gate < /dev/null`.
       - Expected time: overnight, several hours, as the leg sg1 bullet says. The 31 relabelled encounters are traced on both sides, 62 evaluations, each with a suggestion pass capped at 240 s and a narrative prose render, after one model load.
       - Expected: 31 `[trace]` lines, then the table and `TRACE GATE: traced 31, equal by construction 152, …` with errors 0 and not evaluated 0. A "not evaluated" side is the stage's own report: it is counted, never hidden. Exit 0, or 3 if a must-pause row is found (it goes to the practitioner before Phase P, D8).
    6. Recommended, the composer's call: re-run (a) as well (unchanged command with `--stages off`, about 10–20 minutes), so both trace records name the new `sv_trace.py` pin. The fix changes nothing on that path, so (a)'s figures should reproduce exactly.
- Executor handoff (leg sg13, 2026-11-22T22:12+11:00): the evidence and the recommendation for the second gate trace's one must-pause row. It is round 29, MP-001, `heldout-4` `h4-06`, with its Review History line. I decided nothing and changed no code.
  - The tuple, from synthetic material only (the script, Task 2.2's vector-free record for `h4-06`, and `trace-gate.json`'s entry):
    - The added line is segment 2, the single word "Great.", which is the clinician's. It is the first word of the script's clinician line "Great. You can bump the bridges up to three sets of twelve, …".
    - It scored 0.462. R0 labelled it the patient's; B1-35 labels it the clinician's. It is the only segment of the encounter whose label changed.
    - The script expects no fact on it.
    - It reached Advice / home exercise through an accepted suggestion. The changed fields are the clinician-line suggestion count and the refused count. Before, the ownership rule refused it as a patient's line; that is the consistent reading, since the record names the fields that changed, not their values.
    - With the stages off no cue routes it, so it is left out on both sides.
    - No fact, verdict or next-patient field differs.
  - Classified (i): a correct placement newly reached, B1-35's intended effect. Recommended: (a) accept. The brief is the last sub-bullet of Task 4.1, "Must-pause brief (2026-11-22, leg sg13; round 29)", in plain English with the options (a) accept, (b) accept with a Deferred follow-up, (c) decline Lever B (D9's fall-back).
  - Task 4.1 also gains the long runs' dated results: (c)'s verdicts (`h6-22` improved), the gate reports' verdicts, both traces' totals, and `heldout-4`'s gate report as pending.
  - There are three marked places for the composer: the `--suggestions off` report hashes, `heldout-4`'s gate verdict, and the gate report hashes. Each is written `[composer: … here]`.
  - Also updated: the top line and the open-blockers line (MUST-PAUSE).
  - Files changed: the plan only.
  - For the composer:
    - Record the must-pause pair and put the brief's question to the practitioner, with its options as written.
    - Fill the three marked places when `heldout-4`'s re-run ends.
    - Record the disposition as a dated line under the brief and in round 29. Task 4.1 stays 🟨 until then.
- Executor handoff (leg sg14, 2026-11-23T06:46+11:00): Phase 4 is closed. I made plan edits only, ran no Python and changed no code.
  - Task 4.3 is 🟩. The practitioner's run at `98430c0` ended `STITCHED-PRODUCT PARITY: EQUAL`, `COMPLETE`. Each Expected item is met: the capture limits, the per-part embedding, P1, the ten dialogues at 0 differences, the pools equal to Task 0.5b's, and the four digests equal to the freeze. It is recorded item by item under the task. No recording name and no audio-derived text is copied beyond the numbers.
  - Task 4.2 is 🟩: `complete`, `no check errors`, and nothing else (C1).
  - Bar B's seen-set lines were already settled at Task 0.5a and 0.5c for B1-35, and Task 2.2's parity makes them the product's. The "after" reports with `--suggestions off` confirm them against `sv-out/before/`:
    - 183 of 183 encounters confirm their clinician before and after.
    - Clinician labelled other falls in every set: pooled 35.5 → 6.2 s, 0.71 % → 0.12 %.
    - Other labelled clinician rose in scripts (+1.9 s), heldout-2 (+3.7 s), heldout-4 (+3.9 s) and heldout-5 (+2.4 s), and was unchanged in the other three. Pooled it went from 17.0 to 28.9 s, 0.60 % → 1.02 %, +0.42 point, within 0.5.
    - Met. No must-pause. Recorded under Task 4.1 ("Bar B's seen-set lines, after").
  - Phase 4 heading marked done. Progress is 68 % (15 of the 22 numbered tasks). The top lines are updated.
  - Phase 4's cadence: the only tracked change since `4c29283` is this plan (`git diff --stat 4c29283 HEAD`: one file, the plan). This leg's edits are plan text only.
    - The scratch tooling (`sv_trace.py`, `sv_stitch_product.py`, `sv-measure.py`'s new modes) is git-ignored. It was hardened by `/review-loop` rounds 19–21, the codex pass `stage-4.p1` (rounds 22–26, accept-closed at its cap) and `/security-review` round 27, with round 28's fix after them. It is frozen by SHA-256 (Task 4.3's two dated lines).
    - So no Phase 4 diff other than the plan remains unreviewed. Phase 4 changed nothing under `desktop/`, `scripts/`, `validation/` or `extension/`, so it has no product code to review and no live smoke of its own.
  - For the composer: `/document`, then the Phase 4 commit (the plan only), then Phase 5's first leg (Tasks 5.1 and 5.2, then Step H). Phase 1's held live smoke stays owed before Task P.1.
- Executor handoff (leg sv1, 2026-11-23T07:05+11:00): Tasks 5.1 and 5.2 are written and 🟨; I ran no pytest and no Python (verify=composer); ruff clean, mypy clean (72 files). Ends MUST-PAUSE on one document promise outside this task's files (brief below). Step H not started.
  - Task 5.1, version 0.4.2 (six fields in five files): `desktop/pyproject.toml`, `desktop/src/scribe_desktop/__init__.py`, `extension/package.json`, `extension/package-lock.json` (its two own-package fields), `extension/src/manifest.ts`. `.cursor/plans/plan-ui-refresh.md`: one dated line under its Phase 6 heading (0.4.2 skips 0.4.1, which stays reserved for that phase). The "two tests" are left unchanged: their "0.4.0" is docstring history, not a pin (Task 5.1's dated line).
  - Task 5.2, file by file:
    - `docs/security/threat-model.md`: title; practitioner-profile surface 1 (the guided vector, one vector, no schema change), surface 2 (THE GUIDED CAPTURE: per-part limits, at most one part's PCM at a time, numbers only between parts), surface 5 (ONE lease over the whole sequence, the four Stop checks, the busy state on the lease alone), surface 8 (new block THE RECOVERY MARK: what it does and never does, THE NUMBER, THE TRIM, THE LARGER EXPOSURE with its three consequences, the opener rule NOT a control, controls, F-174, C5), surface 10 and note-learning surface 13 restated by the label; the Phase 3A learning call site (a), the joined-answer line and the suggestion line restated; "Kept recordings" MEASUREMENT SCRATCH gains `sv-measure-kept.py` (consultation vectors in memory under C4, the two blocks, not run again) and the stitched runs (no kept recording; memory-keyed temporary store).
    - `docs/security/data-flow-map.md`: title; flow 7 (the recovery mark in the shared pass), flow 12 (the guided capture limits and memory bound), flow 13 (two places, by the label), flow 14 (the tail drain applies the mark), flow 15 (by the label), flow 27's MEASUREMENT SCRATCH (the two stronger-voice entries), the learning non-flow, the no-enrolment-audio non-flow. Its summary table has no learning statement.
    - `docs/security/retention-schedule.md`: title; a stronger-voice intro line; the voice-profile row (guided vector, part PCM dropped, speech seconds the sum); the learned-phrase row (two places) and the learned-rule row restated by the label; the config-indexing row's "own words"; a new "Stronger-voice truth recordings" row after the enrolment-WAV row.
    - `docs/design-system.md`: no change (Phase 1 wrote the guided card).
    - `docs/testing/speaker-measurement.md`: a dated paragraph (the enrolled condition's labels now include recovered segments; the `Similarity` column is the direct matches' mean) and a section "The stronger-voice measurements (2026-11, scratch)".
    - `docs/testing/kept-recordings.md`: the `sv-measure-kept.py` paragraph (pins, arguments, vectors in memory, the two blocks, only "For the record" relayed, not run again) and Task 4.2 recorded only as `complete`, `no check errors`.
    - `docs/testing/validation-harness.md`: a section "Stronger-voice measurement (stronger-voice plan, 2026-11)" with the stitched table (synthetic words, the practitioner's own voice), the seen-set lines, the kept words, the selection, bars A2 (met) and C (not met) as measured for the follow-up plan, the regression and what it cannot show. Nothing from a kept recording but words (C1).
    - `docs/release/pilot-builds.md`: "Rolling back below 0.4.2" (nothing at rest changes shape; the guided-profile case; what 0.4.0 shows differently).
    - `docs/practice/clinician-review-guide.md`: AWAITING THE PRACTITIONER'S APPROVAL — the header line "the speaker-label line added 2026-11-23 for version 0.4.2, awaiting the practitioner's approval", and one new bullet under "Reading the transcript", after "The speaker labels can be wrong…", beginning "**From version 0.4.2:** once your voice has matched clearly somewhere in the consultation, a line that sounds only a little less like you … is labelled as yours too" and ending "**Check the speaker in the transcript before you move a line into your own headings, add one there, or type over one.** The similarity number … describes your clearest matches only, not these lines."
    - `docs/pilot/findings-register.md`: F-174 (2026-11, validation, high, `patient-speculation`, `speaker-labels`, controlled).
    - `CHANGELOG.md`: a "Version 0.4.2 — stronger voice" entry (not yet a build of record), with the four earlier stronger-voice lines folded under it as sub-bullets (B1-35's "still to run" now says it passed on 2026-11-22).
    - `AGENTS.md`: the Current Status paragraph's version wording; the voice-enrolment pointer extended; one new pointer for the recovery mark and the label-reading learners.
  - Line endings: every CRLF file still CRLF and the LF files LF (checked with a CR search over each edited file).
  - For the composer, in order (every call ends `< /dev/null`):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_install_layout.py tests/test_smoke.py tests/test_pilot_settings.py tests/test_build_release.py tests/test_pilot_docs.py tests/test_validation_harness.py < /dev/null`: all pass, 0 failed (the version consistency test reads `pyproject.toml` against `__version__`, the manifest and `package.json`; `test_pilot_docs.py` checks F-174's cells).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11176 passed, 9 skipped, 0 failed (no test added or changed since Phase 2). The real-pipe flake named at leg sb2 may need a lone re-run.
    3. `cd extension && npm run qa`: green, test count unchanged (no extension source but the manifest's version).
    4. `git diff --stat -- desktop/tests/ desktop/src/`: only `desktop/src/scribe_desktop/__init__.py` (one line); `test_shadow_exits.py` untouched.
    5. `git ls-files --eol AGENTS.md CHANGELOG.md docs/security/threat-model.md docs/security/data-flow-map.md docs/security/retention-schedule.md docs/release/pilot-builds.md docs/practice/clinician-review-guide.md docs/testing/validation-harness.md docs/testing/kept-recordings.md docs/testing/speaker-measurement.md docs/pilot/findings-register.md`: `w/crlf` for all but `findings-register.md` (`w/lf`), as before.
  - MUST-PAUSE brief, for the practitioner (nothing decided here). Recommendation first: (a).
    - The finding: the patient-facing `docs/practice/privacy-information.md` (its "How we use it" section, the learning sentence) tells patients the program learns short phrases from lines the practitioner adds or moves, and shorthand from wording the practitioner types over a note line, "never from anything you said". The code learns from any line LABELLED the practitioner's. A patient's line the voice match labels the practitioner's can teach a phrase or a shorthand rule in normal mode with learning on. That was already possible with 0.4.0's rule; 0.4.2's recovery mark makes it more likely (the threat model's THE RECOVERY MARK, consequences (2) and (3); F-174). Shadow mode teaches nothing, so the pilot's shadow consultations are unaffected; the promise matters once learning runs in normal mode. Task 5.2 named only the security, testing and release documents and the clinician review guide, so this leg did not edit the patient document. `docs/practice/README.md`'s index ("the patient documents are unchanged for 0.3.6 and 0.3.7", and its per-version list of review-guide lines) also has no 0.4.2 sentence yet.
    - Options:
      - (a) Recommended: a short leg restates that sentence in plain words and adds the README's 0.4.2 sentence, both marked awaiting the practitioner's approval and the independent review, before Task P.3. Proposed wording for the patient sentence: "If your practitioner turns it on, the program learns short phrases from lines it has labelled as your practitioner's, which they add or move in a note, and shorthand from wording they type over such a line. The program tells voices apart by how they sound, so now and then a line you said can be labelled as your practitioner's and learned from; your practitioner can see and delete everything it has learned." Sets in motion: two practice-document edits, the practitioner's approval, then Step H as planned.
      - (b) Leave the patient sentence unchanged and name the gap as a residue in the threat model's THE RECOVERY MARK block, with a revisit trigger (before learning is used outside shadow mode). Sets in motion: one threat-model sentence; the patient document keeps a promise the program does not keep.
      - (c) Keep learning off for normal recordings until the two-tier label (Deferred) is built, and leave the sentence. Sets in motion: an operating rule recorded in the pilot documents; no code change here.
    - Disposition (2026-11-23, the practitioner): (a), their words "Restate it (a)" (gate-disposition 2026-11-23T07:24:52+11:00, key `patient-doc-promise`). Applied by leg sv2.
- Executor handoff (leg sv2, 2026-11-23T07:27:38+11:00): option (a) applied; Tasks 5.1 and 5.2 are 🟩 on the composer's green run (11176 passed, 9 skipped; `npm run qa` 313 passed; diff stat only `__init__.py`; line endings unchanged). I ran no pytest and no Python. Step H next.
  - `docs/practice/privacy-information.md` (CRLF kept): "How we use it"'s learning sentence restated from the brief's wording, smoothed: the program learns short phrases from lines it has labelled as the practitioner's when they add or move such a line, and shorthand from wording they type over such a line; voices are told apart by sound, so now and then a line the patient said can be labelled the practitioner's and learned from; the practitioner can see and delete everything learned (backed by the Practitioner tab's delete of a learned phrase and of a learned rule). "Never from anything you said" is gone; the shape check's next sentence now reads "a phrase taken from a line labelled as your practitioner's". A **[Reviewer: …]** marker asks the independent review to confirm the wording and the collection notice's cover. The draft line at the top records the restatement for 0.4.2, awaiting the practitioner's approval.
  - `docs/practice/README.md` (CRLF kept): the version list gains the 0.4.2 clause (the review guide's speaker-label line; the privacy information's restated sentence; both awaiting the practitioner's approval and the independent review); "the patient documents are unchanged" now covers 0.3.6 and 0.3.7, and the patient information sheet (`patient-info-v3`) for 0.4.2.
  - `CHANGELOG.md` (CRLF kept): the 0.4.2 entry names the restated privacy sentence beside the review guide's line, both awaiting approval.
  - Test pins: none. No test in `desktop/tests/` or `extension/` reads `docs/practice/` (`test_pilot_docs.py` reads `docs/pilot/` only), so no targeted re-run is owed.
  - The composer: commit Phase 5's Tasks 5.1–5.2 (leg sv1's files, the two practice documents and this plan), then Step H, H1 first.
- Executor handoff (leg sv3, 2026-11-23T07:33:24+11:00): Step H's H1, `/review-loop` round 30 (1 of 3) over `5e1e2cb..8e441a7` and the as-built code it describes: 0 CRIT / 0 HIGH / 1 MED / 1 LOW, both applied (the Review Findings Log's Round 30). Not converged: a MED was applied, so round 31 is owed to confirm it. I ran no pytest and no Python; ruff clean, mypy clean (72 files).
  - Changed: `desktop/src/scribe_desktop/ui/models.py` (`LEARNING_ON_LINE`: "Phrase learning is on: lines labelled as yours that you add or move, and shorthand you type over them, are learned when you press Save note on the Review screen.", and its comment); comments only in `note_config.py` (the learned-rules block), `ui/note_review.py` (`consider_rule_learning`'s docstring) and `ui/note.py` (the module docstring); `desktop/tests/test_enrolment.py` (`TestEnrolmentScript.test_the_learning_line_names_the_label` pins the new line and that it holds no "own lines"); `docs/security/threat-model.md` (surface 2's guided-capture sentence: the redo short at its cap keeps the first attempt; CRLF kept); this plan.
  - For the practitioner, at Phase 1's held live smoke beside round 12's wording points: the Review screen's learning-on line's new wording (MED-001; it was never a practitioner-approved string).
  - The composer runs:
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_enrolment.py < /dev/null`: all pass, 0 failed, the item count unchanged (assertions added inside an existing test).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py tests/test_ui_learned_shorthand.py < /dev/null`: all pass, 0 failed, counts unchanged (they compare against the constant by name).
    3. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11176 passed, 9 skipped, 0 failed (no item added).
    4. `git diff --stat -- desktop/tests/test_shadow_exits.py`: empty.
    5. `git ls-files --eol docs/security/threat-model.md desktop/src/scribe_desktop/ui/models.py`: `w/crlf` and `w/lf`, as before.
  - Then H1 round 31 (2 of 3) confirms round 30's fixes.
- Executor handoff (leg sv4, 2026-11-23T07:47:54+11:00): H1 `/review-loop` round 31 (2 of 3): 0 CRIT / 0 HIGH / 1 MED / 1 LOW. Round 30's two fixes are confirmed (the composer's suite, 11176 passed, 9 skipped). Not converged. Ends MUST-PAUSE on MED-001. I ran no pytest and no Python, and changed no product code or test.
  - Changed: `docs/design-system.md` (LOW-001: the learning status bullet quotes 0.4.2's "Not learned: this line is not labelled as yours …", keeping 0.4.0's words as history; CRLF kept); this plan (Round 31, its Review History line, the top lines, this bullet).
  - MED-001, for the practitioner: the clinician review guide's approved 0.3.6 line (item 7, lines 211-213) says "A line someone else said is never suggested for your assessment, diagnosis, advice or plan"; the rule reads the speaker label, so since 0.4.2 a patient's line labelled yours can be, and the guide's new 0.4.2 speaker-label line says so. Options in Round 31; recommended (a), one dated 0.4.2 line beside it, awaiting approval (lines 144, 232 and 237, the same class, are covered by the speaker-label line's general statement).
  - The known gap, recorded and unchanged: the frozen consent text (`consent-v3`, "Only your own lines are ever used — never a patient's").
  - For the composer: nothing to run for this leg (documents only). A grep check if wanted: `docs/design-system.md` holds "not labelled as yours" and no bare "not\n  attributed to you …" quote; `git ls-files --eol docs/design-system.md` reads `w/crlf`.
- Executor handoff (leg sv5, 2026-11-23T07:50:50+11:00): round 31's MED-001 applied as the practitioner's (a), "Add a 0.4.2 line (Recommended)"; documents only, no product code or test changed; I ran no pytest and no Python. Round 32 not started.
  - `docs/practice/clinician-review-guide.md` (CRLF kept): after item 7's approved sentence (unchanged), "**From version 0.4.2:** "someone else" and "of yours" here mean how the app labelled the line, not who said it. A patient's, carer's or interpreter's line labelled as yours (the speaker-label line above) can be suggested for your assessment, diagnosis, advice or plan, and adding it can teach the app a phrase. Check the speaker before you add a suggested line." The header's dated list reads "the speaker-label line and the suggested-headings label line added 2026-11-23 for version 0.4.2, awaiting the practitioner's approval".
  - `docs/practice/README.md` (CRLF kept): the 0.4.2 sentence also names that line.
  - This plan: the disposition under Round 31's MED-001 (the round closed), the top lines, this bullet.
  - Tests: none reads `docs/practice/` (searched `desktop/tests` for the file name, the folder and the word; `test_pilot_docs.py` reads `docs/pilot/` only), so no targeted re-run is owed.
  - Next: the composer spawns H1 round 32 (3 of 3, the cap).
- Executor handoff (leg sv6, 2026-11-23T07:53:02+11:00): H1 `/review-loop` round 32 (3 of 3, the cap): 0 CRIT / 0 HIGH / 0 MED / 1 LOW, applied. Round 31's two fixes confirmed. H1 CONVERGED (no CRIT, HIGH or MED in the cap round; its one LOW applied), so no cap verdict is owed. I ran no pytest and no Python; ruff clean, mypy clean (72 files).
  - Changed: `desktop/src/scribe_desktop/ui/note_review.py` (the typed-edit status line over a hand-authored config line: "Not learned: this line came from your own config, not from a transcript line labelled as yours."); `desktop/tests/test_ui_screens.py` (`TestNoteScreenTypedEdits.test_the_filters_refuse_and_the_status_names_the_class` also checks "line labelled as yours"); this plan (Round 32, its Review History line, the top lines, this bullet). Both Python files LF.
  - For the practitioner, at Phase 1's held live smoke: that line's new wording, beside the learning-on line (neither was ever practitioner-approved wording).
  - The composer runs:
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q "tests/test_ui_screens.py::TestNoteScreenTypedEdits" < /dev/null`: all pass, 0 failed, the item count unchanged.
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null`: 11176 passed, 9 skipped, 0 failed (no item added).
    3. `git diff --stat -- desktop/tests/test_shadow_exits.py`: empty.
  - Then H2 `/simplify`.
- Executor handoff (leg sv7, 2026-11-23T08:05:10+11:00): Step H's H2 and H3, both 0 findings. No product code, test or document changed; only this plan (rounds 33 and 34, their Review History lines, the top lines, this bullet). I ran no pytest and no Python.
  - H2, `/simplify` (round 33): no simplification worth a maintainer's attention; six candidates left alone by the conservatism guard, named in the round (the two cosine implementations stay apart on purpose: their float results differ in the last bits).
  - H3, `/security-review` (round 34): clean on the guided enrolment's memory bound (one part's PCM at a time, dropped in a `finally`; no traceback keeps it, as `TaskThread` emits only type and message), no audio written or logged, the one lease and every release; and on the recovery mark's two guarantees (only adds `speaker_1`; nothing relabelled without a direct match at the unchanged 0.50, no vector kept, unscored and directionless segments untouched, the stored clinician and similarity the direct matches'). Surfaces 2, 5 and 8 and flows 7, 12 and 14 match the code.
  - For the composer: nothing to run (the plan only). Then H4, the codex peer pass, code and documents as separate slices.
- Executor handoff (leg sv8, 2026-11-23T08:14:20+11:00): H4 peer round 35 verified and applied (verify-then-fix, leg 1). Documents only; no product code or test changed; I ran no pytest and no Python.
  - Verified tuples: PR-LOW-5001 — LOW, Fix-now, applied (`docs/security/retention-schedule.md`, the voice-profile row: "the kept script parts' vectors (the final attempts only; an optional part left out at its cap is absent)"). PR-LOW-5101 — LOW, Fix-now, applied (`docs/release/pilot-builds.md` the attribution sentence and point (2); `docs/testing/speaker-measurement.md` the `Similarity` sentence; sibling `docs/security/data-flow-map.md` flow 7: each now says "with a direct match" and names the unchanged no-match fallback, its cluster and mean).
  - Pending after this leg: 0. Round 36 is NOT owed: round 35's only findings are verified LOW wording in documents, applied (the docs-only-low-close rule), so pass stage-5.p1 converges.
  - Grep checks for the composer, if wanted: `docs/security/retention-schedule.md` holds "kept script parts' vectors" and no "six script parts"; `docs/release/pilot-builds.md` holds "Where the practitioner's voice matched directly" and no "0.4.0 labels only segments at or above 0.50"; `git ls-files --eol` reads `w/crlf` for the four documents.
- Executor handoff (leg sv9, 2026-11-24): the held live smoke's result recorded, and the practitioner's "Bigger text" built (fix mode). I ran no pytest and no Python; ruff clean, mypy clean (72 files).
  - The smoke (2026-11-24, relayed by the composer), the practitioner's words verbatim. The guided card: "for part b its a bit hard to read the text when walking around the table"; offered "Talk freely while moving" or "Bigger text", they chose "Bigger text"; no change to round 12's wording points (a) to (c). The two Review-screen lines: "yes it showed, both pass". Recorded as dated lines on Phase 1's close lines, on Step H's H4 line (PASSED) and on Task P.1's OWED line (the card's re-check still owed).
  - Built: `desktop/src/scribe_desktop/ui/theme.py` (role `reading` in `ROLES`; token `size_reading` = 16 in `LIGHT` and `DARK`; one rule `QLabel[role="reading"]` with the size only; `set_role`'s docstring); `desktop/src/scribe_desktop/ui/practitioner.py` (`set_role(self.passage_label, "reading")`, the passage only; still plain text, default interaction flags). Named pin change: `desktop/tests/test_ui_phase_s.py` `TestGuidedCardWidth.test_every_part_fits_across_at_150_percent` becomes `test_every_part_fits_across[150]` and `[100]`, asserting per part that the passage is in the reading size and above the cue's body size, and that the passage's height is within the scroll area's viewport; every earlier assertion kept. Documents: `docs/design-system.md` (the guided-card bullet, Type's five sizes, Emphasis's `reading` role; round 36 LOW-002's "a cue"), `CHANGELOG.md` (one sub-bullet in the 0.4.2 entry). `test_shadow_exits.py` unedited.
  - Review: round 36 (2 LOW, applied: the test's font check after the card is shown; the design system's cue wording), converged; its Review History line.
  - For the composer, from the repository root (Git Bash):
    1. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_phase_s.py::TestGuidedCardWidth tests/test_ui_theme.py tests/test_ui_shell.py < /dev/null` — all pass; `TestGuidedCardWidth` shows two cases (`[150]`, `[100]`).
    2. `cd desktop && ../.venv/Scripts/python.exe -m pytest -q tests/test_ui_screens.py -k "Practitioner or enrol" < /dev/null` — all pass (the card's flags, hidden-at-rest and part tests unchanged).
    3. The full suite, `cd desktop && ../.venv/Scripts/python.exe -m pytest -q < /dev/null` — expected 11177 passed, 9 skipped (11176 before, plus one from the parametrised card test), 0 failed.
    4. `git diff --stat -- desktop/tests/test_shadow_exits.py` — empty.
    5. Optional: `cd desktop && ../.venv/Scripts/ruff.exe check .` and `../.venv/Scripts/mypy.exe` — clean (run by this leg).
    - If the `[150]` case fails on the new height assertion alone, the passage does not fit one view at 150 % at 16 pt: that is a real decision (a smaller size, or part 3's lines shortened), so stop and bring it back as a must-pause; do not lower the size quietly.
  - For the practitioner, after the composer's green suite (the guided card's re-check; the developer build, the installed app closed):
    1. Launch the developer build (`.venv\Scripts\scribe-app.exe` from Explorer).
    2. Settings → Practitioner → "Record your voice" → Record. A new recording replaces the developer build's profile only once it saves; Stop at any point leaves the saved one as it was.
    3. At part 5 ("Move away"), read the passage while walking round the treatment table, as at the smoke. Check that it is readable from where you stand, and that parts 1 and 3 (the longest) show whole without scrolling once the card is in view.
    4. Do this with Windows display scaling at 150 % and again at 100 %.
    5. Say "pass" or what is still hard to read. A pass clears Task P.1's last owed line.
- Last plan sync: 2026-11-24
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- Run state: `/execute-loop` run `stronger-voice-20261120-200910-dc24` (isolation none, builds on `main`), started 2026-11-20; preflight done; no away grant (no away scope available: isolation none admits no merge, and the agent never drives the desktop app, so there is no live smoke tool).

## Review History
- 2026-11-20 round 1: 0 CRIT / 9 HIGH / 14 MED / 2 LOW; skew=none; action=none (codex `gpt-6.2-astra` high plan peer-review; Materiality 23 build-affecting / 2 record-only / 0 invalid, verified as labelled; all twenty-five applied as plan amendments; round 2 owed — plan mode never converges on round 1)
- 2026-11-20 round 2: 0 CRIT / 11 HIGH / 19 MED / 2 LOW; skew=mixed; action=none (codex `gpt-6.2-astra` high plan peer-review; Materiality 30 build-affecting / 2 record-only / 0 invalid, verified as labelled; about half were against round 1's own amendments; twenty-seven applied as plan amendments, five closed by the two practitioner scope decisions that move the build of Lever C and of several voice vectors to a follow-up plan; round 3 owed)
- 2026-11-20 round 3: 0 CRIT / 5 HIGH / 17 MED / 0 LOW; skew=mixed; action=none (codex `gpt-6.2-astra` high plan peer-review; Materiality 22 build-affecting / 0 record-only / 0 invalid, verified as labelled; most were against round 2's own amendments; all twenty-two applied as plan amendments, one of them by redefining the B1 rows as a recovery mark that leaves the pass mark alone; round 4 owed)
- 2026-11-20 round 4: 0 CRIT / 6 HIGH / 15 MED / 2 LOW; skew=mixed; action=none (codex `gpt-6.2-astra` high plan peer-review; Materiality 22 build-affecting / 1 record-only / 0 invalid, verified as labelled; all twenty-three applied as plan amendments, one of them by removing the speed bar, since no row adds a model call; round 5 owed, the last under the cap)
- 2026-11-20 round 5: 0 CRIT / 4 HIGH / 12 MED / 1 LOW; skew=mixed; action=escalate (codex `gpt-6.2-astra` high plan peer-review; Materiality 16 build-affecting / 1 record-only / 0 invalid, verified as labelled; all seventeen applied as plan amendments; the cap of 5 is reached without convergence — the practitioner decides whether to raise it)
- 2026-11-21 round 6: 0 CRIT / 0 HIGH / 0 MED / 3 LOW; skew=none; action=none (`/review-loop` round 1 over Task 0.6's `sv-measure-kept.py` and `sv_stitch.py`'s P1 path, executor leg svx7; the first code round of this run)
- 2026-11-21 round 7: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=same-family; action=none (`/security-review` over the same files after round 6's fixes, executor leg svx7; the one LOW is a sibling of round 6 LOW-003)
- 2026-11-21 round 8: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none (codex `gpt-6-astra` medium, Task 0.6 code peer review, pass `stage-0.p1` peer round 1 of 5; peer labels, pending the executor's leg-1 verification)
- 2026-11-21 round 9: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex `gpt-6-astra` medium, Task 0.6 code peer review, pass `stage-0.p1` peer round 2 of 5; confirms round 8's PR-LOW-3801 fix; the pass converged)
- 2026-11-21 round 10: 0 CRIT / 0 HIGH / 0 MED / 5 LOW; skew=none; action=none (`/review-loop` round 1 of 3 over Phase 0's tracked diff since `42032e1`, both plans, executor leg svx15; every recorded number matched its evidence; the five are wording, all applied)
- 2026-11-21 round 11: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 0 close documents peer review, pass stage-0.p2 peer round 1 of 5; the pass converged)
- 2026-11-21 round 12: 0 CRIT / 0 HIGH / 0 MED / 3 LOW; skew=none; action=none (`/review-loop` round 1 of 3 over Phase 1's diff, executor leg sx2; the three are a Stop during the microphone handoff, a 150 % pin for the card and the script's wording pinned whole; all applied, suite owed to the composer)
- 2026-11-21 round 13: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (`/review-loop` round 2 of 3 over Phase 1's diff, executor leg sx3; round 12's three fixes confirmed on the composer's green suite, 11155 passed; the review converged)
- 2026-11-21 round 14: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=pre-existing; action=none (codex gpt-6-astra medium, Phase 1 code peer review, pass stage-1.p1 peer round 1 of 5; PR-MED-4201, the controls enabled through the microphone handoff, verified as labelled and applied by leg sx4; suite owed to the composer, peer round 15 to confirm)
- 2026-11-21 round 15: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 1 code peer review, pass stage-1.p1 peer round 2 of 5; PR-MED-4201's fix confirmed; the pass converged)
- 2026-11-21 round 16: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none (`/review-loop` round 1 of 3 over Phase 2's diff and the scratch `--sets --against-product` mode, executor leg sb3; B1-35 matches D4 and Task 0.7; both findings are plan text, applied: Task 4.3's command does not exist yet and the frozen kept script must not be re-run, and the residue's wording for Task 5.2)
- 2026-11-21 round 17: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (`/review-loop` round 2 of 3 over Phase 2's diff, executor leg sb3; round 16's two plan-text fixes confirmed against the code; the review converged)
- 2026-11-21 round 18: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 2 code peer review, pass stage-2.p1 peer round 1 of 5; the pass converged; job 3's answer-hop check limited to its consumer contracts)
- 2026-11-22 round 19: 0 CRIT / 0 HIGH / 1 MED / 2 LOW; skew=none; action=none (`/review-loop` round 1 of 3 over Phase 4's scratch tooling — `sv_trace.py`, `sv_stitch_product.py` and `sv-measure.py`'s new modes — and the plan's Phase 4 lines, executor leg sg2; all three applied in scratch; the self-test and the decode check owed to the composer)
- 2026-11-22 round 20: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none (`/review-loop` round 2 of 3 over the same scratch tooling, executor leg sg3; round 19's three fixes confirmed on the composer's green self-test, decode check and refusal smoke; two new LOWs, both a guard's reach and its test, applied in scratch; the self-test owed to the composer)
- 2026-11-22 round 21: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=none (`/review-loop` round 3 of 3, the cap, over the same scratch tooling, executor leg sg4; round 20's two fixes confirmed on the composer's green self-test; MED-001, the note path's reach seeded from the harness only, applied in scratch; the cap is reached with that fix unconfirmed by a further executor round, the codex peer pass being its confirm; the self-test and the decode check owed to the composer)
- 2026-11-22 round 22: 0 CRIT / 0 HIGH / 2 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 4 tooling peer review, pass stage-4.p1 peer round 1 of 5; round 21's MED-001 fix present; PR-MED-4501 (an import rebinding alone missed by the note-path gate) and PR-MED-4502 (a failed `--again` attempt reporting the previous run's success) verified as labelled and applied by leg sg5; the self-test and the decode check owed to the composer, peer round 23 to confirm)
- 2026-11-22 round 23: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 4 tooling peer review, pass stage-4.p1 peer round 2 of 5; round 22's two fixes confirmed (its job 7); PR-MED-4601 (a reached module's own statements uncompared) and PR-LOW-4601 (the stitched mode's import before its quiet hooks and guard) verified as labelled and applied by leg sg6, with five siblings of the note-path gate found and closed in the same leg; the self-test and the decode check owed to the composer, peer round 24 to confirm)
- 2026-11-22 round 24: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 4 tooling peer review, pass stage-4.p1 peer round 3 of 5; round 23's fixes, the five sweep closures and sg7's correction confirmed (its job 7); PR-MED-4701 (module initialization compared as text, what it calls never followed) and PR-LOW-4701 (argparse's own diagnostics able to echo an argument) verified as labelled and applied by leg sg8, the first by closing the class: every loaded module's import-time code is a root of the reach; the self-test and the decode check owed to the composer, peer round 25 to confirm)
- 2026-11-22 round 25: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 4 tooling peer review, pass stage-4.p1 peer round 4 of 5; round 24's import-time roots, inert grammar and parser fix confirmed (its job 7); PR-MED-4801 (a binding import-time code only reads, such as a condition's constant, never compared) verified as labelled and applied by leg sg9: every binding import-time code reads is now compared whole; the self-test and the decode check owed to the composer, peer round 26 (the last under the cap) to confirm)
- 2026-11-22 round 26: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium, Phase 4 tooling peer review, pass stage-4.p1 peer round 5 of 5, the cap; round 25's fix confirmed (its job 7); PR-MED-4901 (statements compared per name, so a move across another name's statement uncounted) verified as labelled and applied by leg sg10 with one ordered comparison per loaded module, and the gate's compared and not-compared lists stated in full; executor cap verdict: accept, test-harness; the self-test and the decode check owed to the composer)
- 2026-11-22 round 27: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none (`/security-review`, Phase 4's H3, executor leg sg11, over `sv-measure.py`'s loader, start-up and four modes, `sv_trace.py` and `sv_stitch_product.py`, the stitched mode first; refusal order, print surface, D2 custody and C1/C9 as built; SEC-001 (the scratch folder left on `sys.path`, a regression from Task 0.6's precedent) fixed; the self-test owed to the composer, then the SHA-256 freeze)
- 2026-11-22 round 28: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=none; action=none (Phase 4's own run, source: composer long run (b), 2026-11-22, executor leg sg12; RUN-001, the trace never applied the offline environment, so the gate side's language model refused on all 62 sides, verified from the code and fixed in `sv_trace.py` alone (`offline_start` at the trace's start, both stage settings; check 7's three new assertions); `sv-measure.py` and `sv_stitch_product.py` byte-unchanged; the self-test, the decode check, the new `sv_trace.py` freeze and the re-run of (b) owed to the composer)
- 2026-11-22 round 29: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=escalate (Phase 4's own run, source: composer long run (b) repeated, 2026-11-22, executor leg sg13; one D8 must-pause row, MP-001: `heldout-4` `h4-06` in the gate configuration adds the clinician's own one-word "Great." to Advice / home exercise through an accepted suggestion, now that B1-35 labels it the clinician's (0.462; R0 had it the patient's); classified (i), a correct placement newly reached, no fact, verdict or next-patient change; recommendation (a) accept; the practitioner's disposition pending, brief in Task 4.1; disposed 2026-11-23: (a) Accept, the round closed)
- 2026-11-23 round 30: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=none (`/review-loop` round 1 of 3, Phase 5's H1, executor leg sv3, over `5e1e2cb..8e441a7` and the as-built code the documents describe; MED-001: Task 5.2's wording search missed the sources Phase 1's open point (6) named — the Review screen's `LEARNING_ON_LINE` ("shorthand you type over your own lines") and three code comments — applied, with a pin; LOW-001: the threat model's guided-capture sentence did not say a redo short at its cap keeps the first attempt, applied; ruff and mypy clean; the targeted tests and the suite owed to the composer)
- 2026-11-23 round 31: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=pre-existing; action=none (`/review-loop` round 2 of 3, Phase 5's H1, executor leg sv4, over round 30's fixes and Phase 5's whole diff, MED-001's class first; round 30's two fixes confirmed on the composer's green suite; MED-001: the clinician review guide's approved 0.3.6 line "A line someone else said is never suggested for your assessment, diagnosis, advice or plan" contradicts its new 0.4.2 speaker-label line — MUST-PAUSE (approved wording), recommended (a) a dated 0.4.2 line beside it; LOW-001: `docs/design-system.md` quoted 0.4.0's "not attributed to you" note, applied; documents only, no product code or test changed)
- 2026-11-23 round 32: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=pre-existing; action=triage-and-ship (`/review-loop` round 3 of 3, the cap, Phase 5's H1, executor leg sv6, over round 31's fixes and Phase 5's whole diff, the label-versus-speaker class searched once more; round 31's two fixes confirmed; LOW-001: the typed-edit status line "not from a line you said" for a hand-authored config line now names the label, with its test check, applied; H1 converged at the cap; the targeted test and the suite owed to the composer)
- 2026-11-23 round 33: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (`/simplify`, Phase 5's H2, executor leg sv7, over the stronger-voice product code as built — `enrolment.py`, `ui/practitioner.py`'s guided worker and handlers, `ui/models.py`'s enrolment block, the recovery mark and its call; no simplification worth a maintainer's attention; six candidates left alone by the conservatism guard, named in the round)
- 2026-11-23 round 34: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (`/security-review`, Phase 5's H3, executor leg sv7, portable checklist; the guided enrolment's memory bound, its one lease and every release, no audio written or logged, the failure path through `TaskThread`; the recovery mark's two guarantees and the stored figures; surfaces 2, 5 and 8 and flows 7, 12 and 14 against the code; all clean)
- 2026-11-23 round 35: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=pre-existing; action=triage-and-ship (docs-only-low-close; codex gpt-6-astra medium, Phase 5's H4, pass stage-5.p1 peer round 1 of 5, slices A and B over `5e1e2cb..444400d`; PR-LOW-5001: the retention schedule's voice-profile row said the six parts' mean where a left-out optional part is absent; PR-LOW-5101: the release and measurement documents stated 0.50 as a universal floor where the unchanged no-match fallback can confirm a cluster under it — both verified LOW wording in documents and applied, with the data-flow map's flow 7 sibling; documents only; the docs-only-low-close rule applies)
- 2026-11-24 round 36: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none (`/review-loop` round 1 of 3, executor leg sv9, over the practitioner's "Bigger text" from the held live smoke: the theme's new `reading` role and `size_reading` token (16 pt), the guided card's passage, `TestGuidedCardWidth` at 100 % and 150 % with each passage within one view's height, the design system and the CHANGELOG; LOW-001: the test's font check moved after the card is shown; LOW-002: the design system's "a cue in capitals" corrected; both applied; converged; the targeted tests and the suite owed to the composer)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log

### Round 1 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra high plan peer-review
Materiality: 23 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/stronger-voice-plan-peer-r1.log`, the last `### Round 1` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all twenty-five held as labelled. Line cites are to the plan as it stood before this round's amendments.)

#### PR-HIGH-001: `plan:C4`, `transcription.py:2523-2541`, `session.py:2311-2351` — C4 promises a cleanup a timed-out worker cannot perform
- Materiality: build-affecting (verified)
- Why it matters: `LiveTranscriber.stop` returns False on a join timeout while the worker may still hold references, and on success the data moves into a frozen `LiveResult` handed to another thread; clearing the worker's lists does not clear that.
- Proposed amendment: one owner at each handoff; cleanup tested on assembly success, exception, abandonment and eventual worker exit; the timeout refusal kept; fallback and recovery recompute from encrypted audio.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: C4 (rewritten, one owner per handoff), Key Findings ("A live stop can time out"), Task 2.1. Siblings reconciled.

#### PR-HIGH-002: `plan:D5`, `speech.py:318-347`, `transcription.py:2053,2119-2130` — assembly lacks the VAD probabilities a cut needs
- Materiality: build-affecting (verified)
- Why it matters: `segment_pcm` returns spans only and the live segmenter keeps a rolling deque, so "the lowest speech-probability frame" cannot be read at assembly.
- Proposed amendment: preserve timestamped candidate minima from window time in both drivers; define the flip anchor and tie rule; verify on an oversized batch span and both sides of a live forced cut.
- Decision: Applied 2026-11-20. Landed in: D5 (cut candidates recorded at window time from frame energy; anchor and tie rule; the two test cases), Key Findings ("Assembly has no VAD probabilities"), Task 3.1. Siblings reconciled (the "live segmenter's rule" wording removed from D5, the shared-helpers list and Task 3.1).

#### PR-HIGH-003: `plan:Task 2.1, Task 3.1`, `speaker_eval.py:779-799,1180-1197` — a successful split breaks the speaker-measurement harness
- Materiality: build-affecting (verified)
- Why it matters: `speaker_eval` raises `HarnessFaultError` when enrolled boundaries differ from plain ones, and `score_document` scores against truth aligned to the plain spans.
- Proposed amendment: check original VAD parity before splitting, align the enrolled condition to its own final spans, add a regression where one plain segment becomes two enrolled pieces.
- Decision: Applied 2026-11-20. Landed in: D5 (last bullet), Key Findings, Task 3.1. Siblings reconciled.

#### PR-HIGH-004: `plan:D4`, `transcription.py:900-934,958-979`, `ui/transcript.py:614-625` — D4 can auto-confirm a different speaker from the one the rule selected
- Materiality: build-affecting (verified)
- Why it matters: `enrolled_cluster` picks the highest mean over all scored segments of each text-bearing cluster; after adaptation or a split the winner and the shown number are undefined by the plan, and the Review radio follows them.
- Proposed amendment: define the final clinician label and displayed score for direct matches, adaptation, splits, best-of-part scoring, no matches and textless clusters; test the Review selection.
- Decision: Applied 2026-11-20. Landed in: D4 ("The clinician label and the Review screen's number"), Key Findings ("What the Review screen's number is today"), Task 2.1. Siblings reconciled (Context of the Integration Notes corrected).

#### PR-HIGH-005: `plan:D2, Task 0.5a`, `transcription.py:394-400,900-934`, `validation.py:3098-3122,3425-3453` — an attribution-only pass cannot establish the seen-set gates
- Materiality: build-affecting (verified)
- Why it matters: confirmation needs text-bearing clusters, the split veto needs words, and a harness verdict needs the note.
- Proposed amendment: decode each synthetic baseline once, reuse its marked words and timings across candidates, run the real confirmation, veto and note scoring.
- Decision: Applied 2026-11-20. Landed in: D2 (the scratch cache), Agreed Scope, Flow 1, Task 0.4, Task 0.5a. Siblings reconciled.

#### PR-HIGH-006: `plan:bars, Task 0.7`, `speaker_eval.py:827-851`, `validation.py:4756-4769` — the release can combine candidates never qualified together
- Materiality: build-affecting (verified)
- Why it matters: bar B is measured with P1; choosing several vectors changes seeds, false matches and split centres, and product parity ran only on sets with one-WAV profiles.
- Proposed amendment: qualify the exact profile, rule and split parameters together; practitioner-run product parity on the stitched recording, with a positive split when C ships.
- Decision: Applied 2026-11-20. Landed in: D9 (new), Task 0.5c (new), Task 0.7, Task 4.3 (new), Validation. Siblings reconciled.

#### PR-HIGH-007: `plan:C1, Task 4.2`, `replay_kept.py:472-490` — Task 4.2 put real-speech totals in the plan
- Materiality: build-affecting (verified)
- Why it matters: C1 forbids pooled totals in a tracked file; the replay prints session ids and pooled figures.
- Proposed amendment: keep the report in the practitioner's terminal and name the exact words that may be recorded.
- Decision: Applied 2026-11-20. Landed in: C1, Task 4.2 (status and one comparison word only). Siblings reconciled.

#### PR-HIGH-008: `plan:Accepted Assumptions`, `note.py:1688-1694`, `ui/models.py:3903-3911` — the false-match brief omitted a durable plaintext consequence
- Materiality: build-affecting (verified)
- Why it matters: phrase learning reads the same label; outside shadow mode a mislabelled patient line the practitioner adds or moves and saves can teach a phrase kept in plain config, and the ten consultations (shadow) cannot show it.
- Proposed amendment: state the normal-mode residue in the decision and the threat model; verify the normal and shadow learning paths with a synthetic mislabelled line.
- Decision: Applied 2026-11-20. Landed in: Accepted Assumptions, the Deferred item (its outcome, risk and revisit trigger), Key Findings ("What the clinician label also gates"), Task 0.7, Task 2.1, Task 5.2. Siblings reconciled.

#### PR-HIGH-009: `plan:bar C, Task 4.1`, `consultation_phrases.py:152-157,310-323` — an explained split can still be a safety regression
- Materiality: build-affecting (verified)
- Why it matters: a correct split can push a closing phrase outside the three-segment look-back, so a next patient enters the note; "explained" would have closed it.
- Proposed amendment: split-to-note and split-to-trim cases at a next-patient boundary; explicit disposition of any newly admitted next-patient or wrongly clinician-owned material.
- Decision: Applied 2026-11-20. Landed in: D8 (the must-pause kind), bar C, Key Findings ("Who counts segments"), Task 3.1, Task 4.1. Siblings reconciled.

#### PR-MED-001: `plan:D4, D5`, `transcription.py:871-896,1840-1847` — the candidates had no executable order
- Materiality: build-affecting (verified)
- Why it matters: B3 was offered both only without B2 and only with it; C needed centres on exits with no centre parameters; a missing score and a directionless vector need different treatment.
- Proposed amendment: one ordered table with deterministic ties, the update order, the exclusions, the no-centre fallback and C-only parameters; scalar scores only when no centre is used.
- Decision: Applied 2026-11-20. Landed in: D4 (rewritten as one table), D5 (centre parameters, grid order), Key Findings ("Score edge cases"). Siblings reconciled.

#### PR-MED-002: `plan:D2, bars`, `speech.py:83-87,335-347` — the stitched truth could misstate the gap and miss quiet speech
- Materiality: build-affecting (verified)
- Why it matters: VAD padding makes a nominal gap wider at the speech edges; quiet speech the VAD rejects has no denominator; a 2.5 s rule would cut part 3.
- Proposed amendment: the six-file form, gaps from unpadded spans, quiet attribution conditional on detected speech with a frozen coverage and an `unmeasured` outcome.
- Decision: Applied 2026-11-20. Landed in: D2, Task 0.3, bar C's wording. Siblings reconciled (the one-file take removed everywhere).

#### PR-MED-003: `plan:bars`, `validation.py:3125-3141,4061-4069`, `speaker_eval.py:382-392`, `validation_set.py:250-267` — the seen-set and split bars lacked scoring definitions
- Materiality: build-affecting (verified)
- Proposed amendment: freeze the cohort, denominators, pooling, cut tolerance, overlap treatment, exposure and zero-support outcomes; derive transitions from the label tracks.
- Decision: Applied 2026-11-20. Landed in: Validation ("Definitions used by the bars"), D2 (label-track truth, overlaps). Siblings reconciled.

#### PR-MED-004: `plan:D7, bar B`, `.cursor/loops/lcm-measure-kept.py:575-609` — the kept-recording gate could not say which candidate passed
- Materiality: build-affecting (verified)
- Proposed amendment: candidate-keyed direction and sanity words, the baseline, pooling and eligibility, and the undersized-run rule.
- Decision: Applied 2026-11-20. Landed in: D7 (the paste block), bar B. Siblings reconciled.

#### PR-MED-005: `plan:D7, Task 0.6`, `.cursor/loops/ffl-measure-kept.py:564-571,683-702` — the kept script lacked an input and dependency contract
- Materiality: build-affecting (verified)
- Proposed amendment: name the arguments and config source, verify the scratch dependencies, collect and discard inside each guarded pass.
- Decision: Applied 2026-11-20. Landed in: D7 (arguments, hash checks, its own guarded pass), Task 0.6. Siblings reconciled.

#### PR-MED-006: `plan:speed bar`, `speaker_embedding.py:208-225`, `transcription.py:2732-2761` — the speed bar could omit the cost it measures
- Materiality: build-affecting (verified)
- Proposed amendment: a paired warm timing on identical audio that includes every added step, the denominator, and a live backlog check.
- Decision: Applied 2026-11-20. Landed in: the Speed bar, Task 3.2. Siblings reconciled.

#### PR-MED-007: `plan:C3, D3, Task 0.7`, `enrolment.py:213-233,272-292` — the consistency threshold and the measured enrolment could change after results
- Materiality: build-affecting (verified)
- Proposed amendment: label the threshold a calibration with a frozen derivation; give measured and product profiles the same limits and skip rule.
- Decision: Applied 2026-11-20. Landed in: C3, Validation ("The part-consistency calibration"), D2 (profiles built with the product's limits), D3. Siblings reconciled.

#### PR-MED-008: `plan:Task 1.2`, `ui/practitioner.py:226-245`, `desktop/tests/test_ui_screens.py:888-897,1096-1101` — two seams missing for the guided worker's tests
- Materiality: build-affecting (verified)
- Proposed amendment: a typed per-part embed result, `enrol` kept for measurement callers, an injected cancellable wait.
- Decision: Applied 2026-11-20. Landed in: D3, Task 1.1, Task 1.2. Siblings reconciled.

#### PR-MED-009: `plan:D3`, `enrolment.py:125-135,213-233,267-287` — a capture shortfall does not show the microphone cannot hear quiet speech
- Materiality: build-affecting (verified)
- Proposed amendment: skip an optional part only on the capture-cap shortfall, name the part and what was heard, test the other failures apart.
- Decision: Applied 2026-11-20. Landed in: D3 (the left-out rule and its line), Task 1.2. Siblings reconciled (the old "too soft" line removed from D3 and Flow 2).

#### PR-MED-010: `plan:Schema, Task 1.3`, `practitioner_profile.py:196-254,403-412` — the schema-v2 tests did not establish migration and rollback
- Materiality: build-affecting (verified)
- Proposed amendment: the accepted AAD and schema pairs, bounded condition vectors, tamper refusal, both driver reads, a preserved v1 profile, the 0.4.0 path.
- Decision: Applied 2026-11-20. Landed in: Schema / Data Changes, Task 1.3. Siblings reconciled.

#### PR-MED-011: `plan:D8, Task 0.4, Task 4.1`, `validation.py:3955-3980,4434-4453` — D8 named no reproducible reports or evidence for a difference
- Materiality: build-affecting (verified)
- Proposed amendment: pin the baseline code and report identities and the full commands; explain differences from paired word, label and coordinate evidence.
- Decision: Applied 2026-11-20. Landed in: D8, Task 0.4, Task 4.1. Siblings reconciled.

#### PR-MED-012: `plan:Task 4.2`, `replay_kept.py:230-244,385-417` — the replay cannot prove pre/post word parity
- Materiality: build-affecting (verified)
- Proposed amendment: call it an archived-drift observation; use a paired comparison for any exact parity claim.
- Decision: Applied 2026-11-20. Landed in: Task 4.2 (an observation), Task 3.2 and Task 4.3 (where parity is proved, on synthetic and stitched audio). Siblings reconciled.

#### PR-MED-013: `plan:Task P.3`, `note_check.py:1684-1701` — the install smoke demanded outcomes of features that may be skipped
- Materiality: build-affecting (verified)
- Proposed amendment: universal checks, and lever-dependent ones marked required, observational or not applicable.
- Decision: Applied 2026-11-20. Landed in: Task P.3. Siblings reconciled.

#### PR-MED-014: `plan:Task 0.7, C6`, `ui/models.py:3943-3951` — Task 0.7 reopened fixed choices and had no valid consent exit
- Materiality: build-affecting (verified)
- Proposed amendment: Task 0.7 applies the frozen rules, keeps the no-labelling decision, and takes the one-vector path if several vectors would need a consent change.
- Decision: Applied 2026-11-20. Landed in: Task 0.7, Accepted Assumptions (both items). Siblings reconciled.

- **[LOW]** PR-LOW-001: `plan:D5`, `transcription.py:360-370` — "every older build reads it" reached past the rollback target — Materiality: record-only (verified); Decision: Applied 2026-11-20 (D5, Config: 0.4.0 named as the rollback target).
- **[LOW]** PR-LOW-002: `plan:C10` — the plan named an absolute folder C10 reserved for local notes — Materiality: record-only (verified); Decision: Applied 2026-11-20, differently from the proposal: C10 now covers the practitioner's own folders; the synthetic-set folder holds no private data and stays named, as in earlier plans.

### Round 2 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra high plan peer-review
Materiality: 30 build-affecting / 2 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/stronger-voice-plan-peer-r2.log`, the last `### Round 2` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all thirty-two held as labelled. Two practitioner decisions were taken on this round (2026-11-20): Lever C "Measure now, build next (Recommended)", several voice vectors "Measure now, build later (Recommended)". Line cites are to the plan as it stood before this round's amendments.)

#### PR-HIGH-001: `plan:D2, C4` — the scratch cache wrote vectors that C4 forbids writing
- Materiality: build-affecting (verified)
- Why it matters: C4 had no exception for synthetic audio, and the cache under `.cursor/loops/sv-out/` held per-segment and sub-window vectors.
- Proposed amendment: evaluate every row while an encounter's vectors are in memory; persist only comparison evidence; recompute on a restart.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: D2 (one scratch pass per encounter; what is written), C4 (scratch named), C9, Key Design Decisions, Task 0.4. Siblings reconciled (Flow 1, Task 0.5a no longer read vectors from a cache).

#### PR-HIGH-002: `plan:C4`, `session.py:1098`, `transcription.py:2515`, `ui/models.py:4806` — the receiver can keep live vectors after the worker reports cleared
- Materiality: build-affecting (verified)
- Why it matters: the receiver holds the `LiveResult` across a header read, assembly, the stop and the write; a header failure comes before assembly, and an exception can keep frame locals; batch collection can fail before assembly.
- Proposed amendment: an explicitly clearable owner; cleanup on every exit from collection to final use; the custody tests whenever vectors are collected.
- Decision: Applied 2026-11-20. Landed in: C4 (one clearable owner; batch and receiver `finally` scopes; a late window after Stop; the retained-frame case), Key Findings (the receiver), Task 2.1. Siblings reconciled (the tests run for any B2 or B3 row).

#### PR-HIGH-003: `plan:D7`, `.cursor/loops/ffl-measure-kept.py:145,195` — the kept script could run an unchecked scratch dependency
- Materiality: build-affecting (verified)
- Why it matters: the ffl frame imports `ffl_lib` from its own folder; checking the frame alone does not check that code.
- Proposed amendment: verify the whole chain, load the verified bytes, self-test a changed transitive dependency.
- Decision: Applied 2026-11-20. Landed in: D7 (second bullet), Key Findings (scratch frames), Task 0.6. Siblings reconciled.

#### PR-HIGH-004: `plan:D2, D9`, `validation.py:3414,4763` — the seen sets have no six-part profile for their synthetic clinicians
- Materiality: build-affecting (verified)
- Why it matters: P1 and P2 are built from the practitioner's take; the harness builds each synthetic clinician's profile from one passage.
- Proposed amendment: surrogate six-part profiles per synthetic voice, with the one-passage run kept as a comparison.
- Decision: Applied 2026-11-20, differently from the proposal: with several vectors moved to the follow-up plan the shipped profile is one vector, the form the sets already use, so the seen sets keep their one-passage profiles and every seen-set table says they test Lever B's rule, not the script. Landed in: D2 (the seen-sets bullet and its alternative), D9. Siblings reconciled.

#### PR-HIGH-005: `plan:D9, Task 0.5c, Task 0.7` — the release order did not reach every exit
- Materiality: build-affecting (verified)
- Why it matters: no rule for retrying C, for reaching Lever A alone, or for a declined P2; "every bar" included the report-only A1; the kept script needs ids before the order runs.
- Proposed amendment: one finite order with stable ids, the bars that apply, and an unconditional A-only last case that Task 0.7 confirms.
- Decision: Applied 2026-11-20. Landed in: D4 (fixed ids), D9 (rewritten), bars (which gate and which report), Task 0.5c, Task 0.7. Siblings reconciled (Agreed Scope, Key Design Decisions, Flow 1).

#### PR-HIGH-006: `plan:D5` — Lever C had no centre parameters when no B2 row qualifies
- Materiality: build-affecting (verified)
- Proposed amendment: a centre-parameter rule that is defined without a qualifying B2 row.
- Decision: Applied 2026-11-20 for the measurement (D5: `B2-01`'s parameters, whatever row is built); the build question is a seed of the follow-up plan (Deferred).

#### PR-HIGH-007: `plan:D7, bars` — the low-count override could not produce the words bar B needs
- Materiality: build-affecting (verified)
- Proposed amendment: a per-combination eligibility count and an override that yields a verdict on a complete run with support.
- Decision: Applied 2026-11-20. Landed in: D7 (`--allow-low-count`, the two eligibility counts, when a word is printed), bar B (`unmeasured` does not meet it). Siblings reconciled (the old "Real speech" bar line is folded into D7).

#### PR-HIGH-008: `plan:D4`, `transcription.py:455-461,922-930` — a confirmed clinician could have no defined number
- Materiality: build-affecting (verified)
- Why it matters: every seed could be without text while an adapted, text-bearing segment joined `speaker_1`; the mean of its direct matches with text was then empty.
- Proposed amendment: one outcome for an empty score set; the effective threshold and population on each branch; tests.
- Decision: Applied 2026-11-20 by a simpler rule: `enrolled_cluster` is not edited; adaptation runs only when it already returns `speaker_1` over today's labels, is discarded unless it still does over the adapted labels, and the stored clinician and number are today's. Landed in: D4, Key Findings ("How a clinician is confirmed today"), Key Design Decisions, C6, Task 2.1. Siblings reconciled (round 1's "the clinician label and the Review screen's number" paragraph removed).

#### PR-HIGH-009: `plan:bars` — bar C could pass with the two speakers reversed
- Materiality: build-affecting (verified)
- Proposed amendment: score the labels on both sides of each matched transition.
- Decision: Applied 2026-11-20 for the measurement (Validation: a matched cut with a wrong label on either side is a wrong split); the build is a seed of the follow-up plan.

#### PR-HIGH-010: `plan:D8`, `validation.py:3958,3972-3980` — equal report totals can hide a must-pause change
- Materiality: build-affecting (verified)
- Why it matters: a report embeds its commit, so bytes always differ; its counted columns can stay equal while one quoted source replaces another in a clinician-owned section.
- Proposed amendment: hashes for provenance only; always compare source-word identities, section placements and next-patient membership per encounter in both configurations.
- Decision: Applied 2026-11-20. Landed in: D8 (rewritten: the paired trace from one product decode, in both configurations), Task 4.1. Siblings reconciled (the "re-run a differing set once" rule is gone: before and after now share one decode).

#### PR-HIGH-011: `plan:Accepted Assumptions`, `ui/note.py:104-127` — a false match can also teach a durable autofill rule
- Materiality: build-affecting (verified)
- Proposed amendment: add the edit-to-rule consequence to the brief; test Add/Move and Edit through normal-mode Save and the shadow paths.
- Decision: Applied 2026-11-20. Landed in: Accepted Assumptions (consequence 3), the two-tier Deferred item, Key Findings, Task 0.7, Task 2.1, Task 5.2. Siblings reconciled.

#### PR-MED-001: `plan:D2, Task 0.4` — the premise could not check the new window-time data
- Materiality: build-affecting (verified)
- Proposed amendment: name the capture point and its inputs; a known-sample fixture for coordinates, textless spans, the empty case and the no-match branch.
- Decision: Applied 2026-11-20. Landed in: D2 (the pass and its per-segment inputs), Validation (the premise in two parts), Task 0.4.

#### PR-MED-002: `plan:D2, D7, Task P.5`, `docs/testing/kept-recordings.md:89-93` — the recording folder failed its own manifest
- Materiality: build-affecting (verified)
- Why it matters: `enrolment\me.wav` already lives there and has its own retention row.
- Decision: Applied 2026-11-20. Landed in: D2 (a new `stronger-voice\` subfolder with a thirteen-name manifest; P0 passed separately), C2, D7, Task 0.3, Task P.5 (deletion by name). Siblings reconciled.

#### PR-MED-003: `plan:D2`, `enrolment.py:198-233,272-288` — measuring from a file did not reproduce the capture limit
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (P1 through `record_enrolment` with a file-backed capture in 100 ms blocks; silence to the cap after the file ends; `enrol`'s seconds are the stored figure), D3, Key Findings (`record_enrolment`), Task 0.5b's self-test.

#### PR-MED-004: `plan:D2, Validation`, `speech.py:335-347` — the stitched truth's edges and transition counts were not reproducible
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (spans with `pad_seconds=0`, how a turn is built, one dialogue per gap value, the transition instant), Validation (one-to-one matching, the close-turn pool as whole dialogues), Task 0.5b (a hand-checkable fixture).

#### PR-MED-005: `plan:D3` — the redo could change the stored profile in more than one way
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D3 ("Consistency and the one redo": the lowest part, once per enrolment, whole replacement, a short redo keeps the first attempt, one re-score, no second redo), Task 1.1, Task 1.2, Task 4.3 (parity covers the combination and limits; the redo is covered by the suite). Siblings reconciled (Flow 2).

#### PR-MED-006: `plan:D3`, `enrolment.py:84-91`, `ui/practitioner.py:1119-1143` — a beat changed the part with no event to say so
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D3 ("Events"), Key Findings, Task 1.2.

#### PR-MED-007: `plan:D4` — B3 could flip a protected seed
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D4 (only a segment under the pass mark is ever relabelled, and only to the practitioner; the equal-distance case; no B3 when B2 did not adapt), Task 2.1.

#### PR-MED-008: `plan:D5` — the final pieces for several cuts were not determined
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20 for the measurement (D5: frame alignment, cuts in time order, the dropped-cut rules, a piece's label); both drivers and the live path's padded last frame are seeds of the follow-up plan.

#### PR-MED-009: `speaker_eval.py:795-801,1257-1258` — the measurement report would print plain counts on split rows
- Materiality: build-affecting (verified)
- Decision: Closed by the practitioner's scope decision (Lever C is not built here); recorded as a seed of the follow-up plan (Deferred).

#### PR-MED-010: `plan:D4`, `ui/transcript.py:577-587`, `ui/models.py:4632-4636` — a false "model could not load" line
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20 by removal: with PR-HIGH-008's rule this plan creates no new document without a clinician, so the copy is not changed. Landed in: D4.

#### PR-MED-011: `plan:D4`, `transcription.py:1403-1421` — a trim can leave a clinician supported only by trimmed matches
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20: the trim rule is unchanged and the case is named. Landed in: D4 (the trim bullet), C6, Task 2.1 (the test), Task 5.2 (the threat model).

#### PR-MED-012: `note_check.py:1662-1668`, `note_config.py:2067-2085,2155-2162` — a cut can change a warning or a learning refusal
- Materiality: build-affecting (verified)
- Decision: Closed by the practitioner's scope decision; a seed of the follow-up plan (Deferred).

#### PR-MED-013: `plan:Task 4.2`, `replay_kept.py:241-244,604-606` — the replay cannot take the guided profile
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 4.2 (the existing `me.wav`; a P0 drift observation).

#### PR-MED-014: `transcription.py:2463-2474,2647-2652` — the live speed check could bypass the backlog rule
- Materiality: build-affecting (verified)
- Decision: Closed by the practitioner's scope decision: this plan's built rows add no embedding, so the speed bar is an assembly-time bound (Validation); a real-time live check is a seed of the follow-up plan.

#### PR-MED-015: `plan:Schema` — a v2 profile could hold no vector to score
- Materiality: build-affecting (verified)
- Decision: Closed by the practitioner's scope decision (no schema change here); a seed of the follow-up plan.

#### PR-MED-016: `ui/models.py:4626-4693` — readiness readers have no audio to score
- Materiality: build-affecting (verified)
- Decision: Closed by the practitioner's scope decision; a seed of the follow-up plan.

#### PR-MED-017: `plan:Excluded, D7`, `note.py:1697-1709` — Phase 0 promised a routing diagnosis its tables could not give
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: the Excluded item, D7 (its last bullet), Task 0.5a (the note composed under measured and under true labels on the synthetic sets), Task 0.7.

#### PR-MED-018: `plan:Task P.3` — the install smoke could fail with no disposition before C01
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task P.3 (a mock that supplies the built row's prerequisites; unevaluable against failed; a recorded pass or disposition), Task P.4.

#### PR-MED-019: `plan:Task 5.2`, `docs/security/threat-model.md:1336-1346`, `docs/security/data-flow-map.md:636-644,734-750` — Task 5.2 left out promises the change affects
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 5.2 (practitioner-profile surface 6; flows 13, 15 and 27; statements and the register row depend on what shipped).

- **[LOW]** PR-LOW-001: `plan:Validation` — take B and the seen sets are reused selection data — Materiality: record-only (verified); Decision: Applied 2026-11-20 (D2's "Stated on every table", Validation's "Stated with the tables").
- **[LOW]** PR-LOW-002: `plan:Key Findings, Task 2.1`, `transcription.py:822` — `label_speakers` was placed in the wrong module — Materiality: record-only (verified); Decision: Applied 2026-11-20 (Key Findings; Task 2.1 no longer edits `speaker_eval.py`).

### Round 3 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra high plan peer-review
Materiality: 22 build-affecting / 0 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/stronger-voice-plan-peer-r3.log`, the last `### Round 3` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all twenty-two held as labelled. Line cites are to the plan as it stood before this round's amendments.)

#### PR-HIGH-001: `plan:D4`, `transcription.py:926-934,972-979`, `desktop/tests/test_speaker_embedding.py:75` — a B1 row could remove a practitioner label, change the clinician and change the number
- Materiality: build-affecting (verified)
- Why it matters: a lower pass mark moves a consultation between the match and no-match branches and changes the mean; the plan's "only adds" guarantee held for session adaptation alone.
- Proposed amendment: scope the guarantee to B2/B3 and give B1 its own tests, pin update, measurements and explanation.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment), differently from the proposal: the B1 rows are now a recovery mark under the same condition and guarantee as every other row, so the pass mark, its pin, `attribute_speakers` and the number are untouched and the guarantee holds for the whole table. Landed in: D4 (one condition, one guarantee, the B1 definition, the alternative), C5, C6, Key Design Decisions, Key Findings, Task 2.1. Siblings reconciled (D9, Task 0.7's records, Task 5.2).

#### PR-HIGH-002: `plan:C4`, `speaker_embedding.py:480-490`, `transcription.py:885-893`, `speaker_eval.py:1133-1145` — clearing the owner does not clear a vector held by a retained exception
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: C4 (the traceback bullet; the `R0` / B1 statement limited to the successful path), D7 (the kept script's pass), Task 2.1 (the two failure tests), Task 0.6, Task 5.2.

#### PR-HIGH-003: `plan:D8`, `transcription.py:937-944` — D8 could reproduce a regression on both sides of its comparison
- Materiality: build-affecting (verified)
- Why it matters: "before" was the after decode relabelled, so a dropped segment or moved word sat on both sides; a scratch rule that borrowed the product's constant would follow a changed constant.
- Decision: Applied 2026-11-20. Landed in: D8 (the decode check against Phase 0's record; scratch `R0` with the literal 0.50), D2 (what Phase 0 writes), Validation (the premise), Task 0.4, Task 2.2, Task 4.1.

#### PR-HIGH-004: `plan:D8`, `validation.py:3098-3122,3437-3453,2343-2350`, `ui/transcript.py:614-625` — the must-pause trace could miss a placement the app permits
- Materiality: build-affecting (verified)
- Why it matters: the harness composes no note when its truth track disagrees with the stored clinician, while Review preselects that clinician; and membership after the detected boundary misses tail lines the detection missed.
- Decision: Applied 2026-11-20. Landed in: D8 (the placement trace under the stored clinician; the script's own next-patient tail; ambiguous lines surfaced), Key Findings, Task 4.1.

#### PR-HIGH-005: `plan:D2, D5`, `speech.py:83-87,313-333` — a close-turn dialogue could give the splitter no centres at all
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (the unscored calibration preamble on the two close-turn dialogues), D5 (`unmeasured` without centres; eligible mixed seconds and attempted cuts shown), Validation, Task 0.5b.

#### PR-MED-001: `plan:C4`, `transcription.py:2503-2541,2564-2571,2781-2810` — the handover needed one defined point
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: C4 (before, at and after a successful `drain`), Key Findings, Task 2.1 (Stop after publication, Stop racing a window, a timeout followed by exit).

#### PR-MED-002: `plan:Task 2.2, 4.3, P.3`, `transcription.py:2749-2769`, `ui/models.py:4804-4826` — parity could pass while the live path still used today's rule
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 2.1 (one fixture through both drivers, a named segment that must change), Task P.3.

#### PR-MED-003: `plan:D7, bars` — bar B could credit the guided profile's gain to a row that changes nothing
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D7 (the third word, `adds` / `adds nothing`, against P1 at `R0`; "seconds labelled practitioner"), D9, Task 0.5b, Task 0.7. The order and the bars are unchanged.

#### PR-MED-004: `plan:D9, C3, Validation, Task 2.2` — the selector gave different instructions about which bars apply
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D9 (stated once: B1 rows, B2/B3 rows, `unmeasured`, a product timing miss), C3, the bars' labels, Task 2.2.

#### PR-MED-005: `plan:D2, D5, Task 0.4, 0.5a` — Task 0.5a asked for results Task 0.4 did not keep
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (the vector-free summaries and timings written by the one pass), D5 (the second measurement at the built row's settings removed), Task 0.4.

#### PR-MED-006: `plan:D2, Validation`, `speech.py:313-347` — the stitched recipe and its pools were not reproducible
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (the packing rule, the seed, an overlong span, a short tail, the other voice running out, the pools), Validation, C3, Task 0.5b.

#### PR-MED-007: `plan:Task 0.5a`, `.cursor/loops/ffl_lib.py:973-977`, `validation.py:3437-3453` — the true-label comparison had no answer for unassigned or tied speech
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 0.5a (the cohort, the mapping through the confirmed clinician, no-overlap and tied segments, counts by line identity), Validation ("labelled practitioner" defined through the confirmed clinician).

#### PR-MED-008: `plan:D2, bar A2`, `enrolment.py:224-233` — bar A2 did not isolate keeping several vectors
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (P2 is exactly P1's retained part vectors).

#### PR-MED-009: `plan:D2, Validation`, `validation_set.py:250-268,385-399` — a cut inside an excluded overlap could count as harm
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2, Validation (one mask for transitions, cuts and exposure), the premise's fixture, Task 0.5b.

#### PR-MED-010: `plan:D2, D3, Task 0.3`, `enrolment.py:63-65,163-171,194-230` — the file-backed capture needed pacing, and the reader an end cue
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (one block at a time on the progress callback; the files' minimum lengths), D3 (the fixed "keep reading" line), Key Findings, Task 0.3, Task 0.5b, Task 1.1.

#### PR-MED-011: `plan:D3, Task 1.2`, `enrolment.py:72-73,215-233` — the left-out line promised seconds the result did not carry
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D3 (the success result), Task 1.2 (the worker's last progress number; both optional parts left out).

#### PR-MED-012: `plan:Task 4.3, Validation` — Task 4.3 could not assume the guided flow skips its redo
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 4.3 (the developer source; the claim limited to capture limits, embedding, combination and the batch driver; the redo named as not claimed).

#### PR-MED-013: `plan:D8, Task 4.1`, `.cursor/loops/ffl_lib.py:1429-1452`, `validation.py:2775-2793,3482-3489` — the replay's default provider and outcome comparison did not match the claim
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D8 (the shipped provider passed explicitly; timings and stage availability left out; the `R0` shortcut stated once), Task 4.1 (its own exception removed).

#### PR-MED-014: `plan:D7, C1, Task 0.6` — the paste block and the tracked record needed different contracts
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D7 (two output blocks), Task 0.6 (what is relayed and recorded), Task 5.2.

#### PR-MED-015: `plan:Task P.3` — the smoke treated a seen wrong label as missing evidence
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task P.3 (`failed` against `unevaluable`; the quiet-line check as an end-to-end outcome).

#### PR-MED-016: `plan:Config, Task P.3`, `practitioner_profile.py:516-521` — a rollback could leave the cause of a failed smoke in place
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Config / Environment / Deployment Impact, Task P.3, Task 5.2.

#### PR-MED-017: `plan:Task 5.2`, `docs/security/retention-schedule.md:46,50`, `docs/security/threat-model.md:1485-1497`, `transcription.py:433-435` — Task 5.2 left contradicted promises in the records
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 5.2 (surface 10 and the two at-rest rows on every exit; the kept-measurement record on every exit; the similarity number's definition at its code and document sources), Task 2.1.

### Round 4 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra high plan peer-review
Materiality: 22 build-affecting / 1 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/stronger-voice-plan-peer-r4.log`, the last `### Round 4` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all twenty-three held as labelled. Line cites are to the plan as it stood before this round's amendments.)

#### PR-HIGH-001: `plan:C4`, `transcription.py:2503-2521,2565-2571,2798-2810` — a normal live shutdown would clear the vectors before `drain` could claim them
- Materiality: build-affecting (verified)
- Why it matters: on a normal seal the worker publishes its result and runs its exit clean-up before `drain` reads it; C4 read literally had that clean-up clear the owner every time.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: C4 (a normal seal leaves the owner alone; clearing before the handover only on a failure or a requested stop; `drain` and `stop` under one lock), Key Findings, Task 2.1 (the normal-seal test and the lost-lock case).

#### PR-HIGH-002: `plan:D2, Task 0.5b, Task 4.3`, `transcription.py:1751-1759`, `speaker_eval.py:884-892,1084-1097,1112-1125` — the stitched parity run writes the reconstructed audio to disk
- Materiality: build-affecting (verified)
- Proposed amendment: a memory-backed adapter at the store boundary.
- Decision: Applied 2026-11-20, differently from the proposal: the plan now says what is true. A stitched dialogue is never written in the clear; where the batch driver needs a store it uses the existing encrypted temporary store with a memory-only key, destroyed after the pass, the custody already used for a kept consultation. Landed in: D2 ("Custody of the stitched audio", the alternative), Key Findings, Task 0.5b (the destroy test), Task 4.3, Task 5.2.

#### PR-HIGH-003: `plan:D2, D8`, `transcription.py:375-380,534-545`, `note.py:319-331` — the decode check could call two decodes equal across a changed warning severity
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (every field of every word is written), D8 (the decode check compares them, the probability included), Task 4.1 (the check's self-test).

#### PR-HIGH-004: `plan:D8, Task 4.1`, `validation.py:2774-2794,3440-3469,3482-3489` — D8 could miss a newly admitted line under `confirm-all`
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D8 (the final note's placements in both configurations, unresolved-role encounters included; a side whose stage did not run is `not evaluated`, never equal), Task 4.1.

#### PR-HIGH-005: `plan:D8, D9, Task 2.2, Tasks 4.1-4.3, Step H, P.1` — a fall-back or a hardening fix could leave the release different from the verified product
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D9 (the fall-back after Lever B is built: revert, record, re-run), Task 4.1 (the verified commit recorded), Task P.1 (the release tree compared with the verified tree; what is repeated), Task 2.2. The timing fall-back itself is gone with the speed bar (PR-MED-010).

#### PR-HIGH-006: `plan:Task P.3, C10` — the smoke let the ten start without a required control
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task P.3 (four operating checks with no "proceed anyway"; the disposition limited to speaker-label observations).

#### PR-MED-001: `plan:C4`, `transcription.py:1800-1846,2722-2771` — a failure after a successful collection could keep the last vector
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: C4 (the collection helper that hands back numbers only), D7, Task 2.1 (the third failure test), Task 5.2.

#### PR-MED-002: `plan:D4`, `transcription.py:1681-1688` — a score at or above 0.50 does not prove assembly took the match branch
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D4 (the condition names the shortcut; the row's call sits in the attribution branch), D2 (the branch is written), Validation (the premise fixture), Task 2.1.

#### PR-MED-003: `plan:Task 2.1`, `transcription.py:918-934` — some required tests were unreachable and a B3 success could go untested
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D4 (the B1 acceptance invariant), Task 2.1 (the grid tested in scratch; reachable product tests per built row; a change by smoothing alone).

#### PR-MED-004: `plan:D5`, `transcription.py:1935-1940,1994-2019` — the close-turn measurement's unsplit baseline differs from the live path's
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D5 (the result named as the batch path's; segments past 30 s counted), Task 0.5b.

#### PR-MED-005: `plan:D2` — calibration audio reappeared in the scored close-turn bodies
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (reserved preamble spans; the restart skips them; the self-test's disjointness check), Task 0.5b.

#### PR-MED-006: `plan:D2`, `speech.py:318-347` — the packing rule had inputs it could not handle
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (an open turn closed when a long span arrives; one turn-target sequence for all four gaps; an empty voice file refused), Task 0.5b.

#### PR-MED-007: `plan:D2, D5, Task 0.5a`, `validation_set.py:324-333,398-399`, `.cursor/loops/ffl_lib.py:973-977` — seen-set truth and tie handling differed from the reused helper
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (two truth classes; the transition instant; the tie tested before `majority_label`), Validation, the premise fixture, Task 0.5a.

#### PR-MED-008: `plan:D5` — a piece's label was not always determined
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D5 (the profile each table's centres use; the equal-distance rule; a piece with no sub-window centre), Task 0.5b.

#### PR-MED-009: `plan:D2, D5` — Phase 0 kept too little to tell "unmeasured" from "tried and failed"
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (centre eligibility, eligible mixed seconds, mixed seconds before and after, proposed and kept cut counts).

#### PR-MED-010: `plan:Validation, D2, Task 2.2` — the speed bar had no timing of today's shipped assembly
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20 by removal: every row is arithmetic over numbers the pass already holds and adds no model call, so a timing would measure the laptop. The bar is gone; a test pins one embedder call per segment. Landed in: Validation, D9, D2, Tasks 0.5a, 2.1 and 2.2.

#### PR-MED-011: `plan:D2, D3, Validation`, `enrolment.py:215-230,272-292` — the consistency figure and the final weak-part line were underspecified
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Validation (both takes' part vectors through the capture limits, each against its own take), D2, D3 (the lowest remaining part named, the earlier on a tie), Tasks 1.1 and 1.2.

#### PR-MED-012: `plan:D3, Task 1.2`, `ui/practitioner.py:701-704,881-912,1046-1056,1143-1172` — the tab could become editable while the lease was held
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 1.2 ("Busy state"; the two new tests), Key Findings.

#### PR-MED-013: `plan:D8`, `note.py:534-543,562-593`, `validation.py:3230-3245,3257-3271` — "a note line's source words" was not a valid key
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D8 (quoted lines by segment and word coordinates; configuration lines by provenance and proposal identity; a quoted line flagged when any word is in the tail), Task 0.5a, Task 4.1.

#### PR-MED-014: `plan:D7, D9, Task 0.6, Task 4.2`, `replay_kept.py:576-589` — the kept-recording contract left output unassigned and could infer a verdict from a run that did not finish
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D7 (the status; the private block's exact fields and band edges; nothing else printed), Tasks 0.5c and 0.6, Task 4.2 (three outcomes).

#### PR-MED-015: `plan:Task 5.2`, `ui/models.py:3559-3561`, `ui/note_review.py:298-305,389-397`, `docs/security/data-flow-map.md:620-641,1723-1733`, `docs/security/threat-model.md:1697-1704,2360-2362` — the learner's real rule still contradicted the app's wording and the documents
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 1.4 (new: the app's line and two docstrings; the consent text untouched), Task 5.2 (the label-based statement on every exit; Lever B's added exposure only when shipped), Key Findings.

- **[LOW]** PR-LOW-001: `plan:Flow 2, Task P.3`, `ui/practitioner.py:834-850,907-913` — the re-enrolment steps asked for a tick that is already made — Materiality: record-only (verified); Decision: Applied 2026-11-20 (Flow 2; Task 1.2's re-record case).
- **[LOW]** PR-LOW-002: `plan:C9` — `< /dev/null` is not PowerShell — Materiality: build-affecting (verified); Decision: Applied 2026-11-20 (C9; Tasks 0.5b, 0.6 and 4.3 name the PowerShell command given in chat).

### Round 5 — 2026-11-20
Round status: Closed
Source: Codex gpt-6.2-astra high plan peer-review
Materiality: 16 build-affecting / 1 record-only / 0 invalid
(Composer-recorded: the peer ran read-only and printed its round; transcribed from `.cursor/loops/stronger-voice-plan-peer-r5.log`, the last `### Round 5` header. Each finding was verified against the code and the plan by the owning planning session before any amendment; all seventeen held as labelled. Line cites are to the plan as it stood before this round's amendments. This is the last round under the cap of 5; the pass did not converge.)

#### PR-HIGH-001: `plan:Task 1.2`, `ui/practitioner.py:786,880-883,919-928,972-996,1143-1151` — Confirm consent could overwrite a newly saved guided profile
- Materiality: build-affecting (verified)
- Why it matters: `on_confirm_consent` re-saves the cached profile; while a finished worker's result is still queued, the availability poll could enable it and the old vector would replace the new one.
- Decision: Applied 2026-11-20 (Claude Code, plan amendment). Landed in: Task 1.2 (the held lease is the one busy test for the controls and for every handler that writes or deletes a profile; the Confirm-consent test).

#### PR-HIGH-002: `plan:D8, Task P.1`, `.cursor/loops/ffl_lib.py:1443-1459`, `validation.py:3452-3476` — the paired trace could miss a new placement after a hardening change to the note path
- Materiality: build-affecting (verified)
- Why it matters: both sides of the trace run today's note code, so a change there shows on both and an encounter with identical labels is never traced.
- Decision: Applied 2026-11-20. Landed in: D8 (the note path must be the code Phase 0 ran; an executable change there is a must-pause and the before side is then replayed from the Phase 0 commit), Task 4.1.

#### PR-HIGH-003: `plan:D2, D8, Tasks 2.2, 4.1, 4.3`, `transcription.py:879-897` — parity did not show that the released row is the row that qualified
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D8 (the decode check also compares the product with the built row's own Phase 0 labels), Task 4.1 (a persistent difference requalifies the row or falls back), Task 4.3 (the pools' figures equal those pasted at Task 0.5b).

#### PR-HIGH-004: `plan:Task 4.1, Task P.1`, `validation.py:4353-4364,4383-4387` — the release comparison could certify a tree other than the one measured
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 4.1 (a clean checkout; the scratch files' hashes recorded), Task P.1 (the whole diff is read; only documents, tests and version-only hunks are exempt).

#### PR-MED-001: `plan:C4`, `transcription.py:2422-2436,2509-2517,2530-2541`, `session.py:2311-2323` — the lock's extent and the clearance verdict were underspecified
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: C4 (a short lock around the stop decision and the handover only; joins outside it; `buffers_cleared` inspects the owner), Task 2.1 (the two tests).

#### PR-MED-002: `plan:Validation, Task 2.1`, `transcription.py:1840-1847,2752-2762`, `speaker_embedding.py:480-484` — "one embedder call per segment" conflicted with both drivers
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Validation and Task 2.1 (one call per segment that can be embedded, none under 25 ms; the short-middle-slice fixture), C4 (one slot per segment).

#### PR-MED-003: `plan:D7, C4` — scratch read vectors outside the named traceback boundaries
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: C4, D7, Task 0.5b (the held-exception test).

#### PR-MED-004: `plan:D2`, `speech.py:335-347` — a recording could pass validation and leave no turn to stitch
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (whole-span reservation with its boundary rule; the turns built once; the refusal when no body turn is left), Task 0.5b.

#### PR-MED-005: `plan:D2, Validation` — zero quiet speech had two outcomes
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D2 (a silent optional part is left out and the quiet pool reads `unmeasured`; only required parts and the other voice are refused; the calibration uses the parts each take retains), Task 0.5b.

#### PR-MED-006: `plan:D5` — a cut on a word or window boundary could change bar C
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D5 (half-open pieces; a midpoint or centre on a cut goes to the later piece; the earlier of two equally near centres), Task 0.5b.

#### PR-MED-007: `plan:D4, Task 2.1` — B3 was ambiguous when B2 formed centres and changed nothing
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D4 (B3 runs whenever B2 formed its centres and passed every guard), Task 2.1 (the fixture with no B2 change anywhere).

#### PR-MED-008: `plan:Task 0.5a`, `validation.py:3051-3062,3111-3122`, `transcription.py:460-475` — the true-label comparison could build an invalid document
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 0.5a (labels given to composition directly; such an encounter counted `unevaluable`).

#### PR-MED-009: `plan:D8`, `validation.py:3300-3307,3317-3323` — a successful empty suggestion pass could be retried for ever
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D8 (a stage not asked is a completed pass; only an unavailable one is `not evaluated`).

#### PR-MED-010: `plan:D7, C1, Task 0.6` — the incomplete report could not meet its own output contract
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: D7 (two exact forms of the record block; a fixed, content-free reason code on the incomplete one).

#### PR-MED-011: `plan:Task P.3`, `ui/practitioner.py:822-826,1153-1164`, `test_ui_screens.py:1406-1424` — the installed Stop check could pass after the profile was replaced
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task 1.2 (unchanged encrypted bytes after a stopped re-record), Task P.3 (the profile file's hash before and after, recorded as equal or not).

#### PR-MED-012: `plan:Tasks P.3-P.5` — a final rollback had no route to the close and to deleting the truth recordings
- Materiality: build-affecting (verified)
- Decision: Applied 2026-11-20. Landed in: Task P.3 (a next step for each disposition), Task P.5.

- **[LOW]** PR-LOW-001: `plan:Tasks 1.4, 5.2`, `docs/security/threat-model.md:410-413,1697-1702`, `docs/security/data-flow-map.md:1723-1729`, `ui/note.py:89-92` — the search for learning promises missed claims about other speakers — Materiality: record-only (verified); Decision: Applied 2026-11-20 (Task 1.4's files; Task 5.2's search terms and the learning non-flow).

### Round 6 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: Task 0.6's `.cursor/loops/sv-measure-kept.py` (new, leg svx6; the count pin of leg svx7) and the P1-building path of `.cursor/loops/sv_stitch.py` it executes (`FileCapture`, `capture_part`, `ProfileHolder`, `build_take`, `kept_parts`, `Hooks`, `make_deps`, `profile_scores`, `_with_scores`, `manifest_problems`, `_read`). Baseline: the working tree against `7e730b1` (both are gitignored scratch, so read in full). `/review-loop` round 1 of 3, executor leg svx7 (no Python run: verify=composer). Read against D6, D7, C1, C4, C9 and Task 0.6, and against the shipped `speaker_eval.transcribe_in_temporary_store`, `replay_kept._load_models`, `PastSessionStore.read_recording`, the frame's `_kept_listing` / `_kept_in_order` and `transcription`'s `fsum` mean (the premise's exact float comparison holds).
Finding verification: 5 candidates; 2 dropped (the premise's float equality: the product's mean is the same `math.fsum` over the same values; `CaptureError` on a recording with no attributing call: the same rule as `sv-measure.py`, whose premise held on all 227 seen encounters); 0 downgraded.
Missed-issue pass: re-read `sv-measure-kept.py` whole (1–1994) and `sv_stitch.py` 134–171, 505–828, 941–977, 1248–1254; result: none beyond LOW-001–LOW-003.

- **[LOW]** LOW-001: `.cursor/loops/sv-measure-kept.py:132-151` — the scratch folder stays an import location: Python puts the script's own folder first on `sys.path`, and the frame inserts it again when it loads, so a module imported later (a stdlib, application or third-party module imported lazily) would resolve first to a same-named file in `.cursor/loops/`, executed without a hash check — against D7's "loads and runs the verified bytes" — Triage: Fix-now; Fix route: fix-on-fast; Desired: the folder taken off `sys.path` before any other import and again after the chain is loaded (the chain runs by `exec` from its checked bytes and needs no path), with the self-test's chain case checking it is off; /fix decision: Applied; /fix notes: `_off_the_path` (module top, before `threading` and every later import; `os` is loaded at interpreter start-up), called again in `load_modules`' `finally` after each module runs (the frame's own insert is undone before `sv_stitch.py` loads), the module docstring's chain paragraph says so, and the chain case gains `scratch-folder-off-the-path`; siblings: none (no other `sys.path` use in the script); not run (verify=composer); /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-002: `.cursor/loops/sv-measure-kept.py:777-778` — `RealEnv.take_names` lists files only (`is_file()`), while the stitched mode's manifest check (`sv_stitch.py:1686`, `:1715`) counts every entry, so a subfolder in `--take-a` is not counted as extra and one named like a manifest file passes the manifest check here and is refused later as `take-a-unusable` instead of `take-a-manifest` — Triage: Fix-now; Fix route: fix-on-fast; Desired: every entry's name, as the stitched mode lists it; /fix decision: Applied; /fix notes: `RealEnv.take_names` returns every entry's name, sorted; the self-test's fake lists its own thirteen names, so no case changes; siblings: none (the P1 path's other listing is the stitched mode's own, already every entry); /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-003: `.cursor/loops/sv-measure-kept.py:132` — only `sys.excepthook` is quieted; an exception in a thread or an unraisable one (a finaliser's) would still be printed by Python's default hooks to the console with its message, against D7's "nothing else is printed" (the frame and the replay tool install neither, so this is the script's own contract, not a regression) — Triage: Fix-now; Fix route: fix-on-fast; Desired: `threading.excepthook` and `sys.unraisablehook` replaced by hooks that print nothing (a block mid-run would break the two-block form; the run's own handler still names every failure of the pass by type), with the self-test's hook case checking both are installed; /fix decision: Applied; /fix notes: `_quiet_other_hook` (prints nothing) set as `threading.excepthook` and `sys.unraisablehook` right after the path is cleaned; the hook case gains `thread-and-unraisable-installed` and `other-hook-silent`; siblings: `sys.excepthook` already quiet; /fix date: 2026-11-21; /fix applied by: Claude Code
Fix-delta self-check: PASS — re-read the 4 applied hunks in `sv-measure-kept.py` (the path and hooks at the top, `load_modules`' `finally`, `take_names`, the two self-test checks) and the docstring line; the `finally` runs after the `KeyboardInterrupt` branch's `del` and before the refusal's, the fixture modules of the chain case are found in `sys.modules`, not on the path, and the case count stays 32

### Round 7 — 2026-11-21
Round status: Closed
Source: Claude Code security-review (portable checklist; executor leg svx7, no Python run)
Scope: the same files as round 6, after its fixes: `.cursor/loops/sv-measure-kept.py` and `sv_stitch.py`'s P1 path. Focus, as Task 0.6 names it: the refusals, the two output blocks against their exact lists, the hash checks, the clearing between recordings and on a failure, and that nothing in "For the record" can carry a session id, a per-recording number, a pooled total, an accent count, a path or transcript text. Trust boundaries: the command line's four paths; the Past-sessions folder and its decryption (`PastSessionStore.read_recording`, under this Windows user's keys); the scratch files executed by `exec`; the console.
Checked and clean:
- Refusals: each comes before the first `read_recording`, in D7's order (pinned by the self-test's call lists); offline before any model loads; the instance exclusion is held from before the first decryption to after the last, and released on every path (`_main`'s `finally`).
- Hash checks: all four files read once and checked before any runs; the checked bytes are the ones executed (no second read, no `.pyc`); a placeholder, a changed file, a load failure and a same-named module from other bytes each refuse; since round 6 the scratch folder is never an import location.
- The record block: built only by `record_complete` (fixed combination ids from `sv_lib.COMBINATIONS`, words from four fixed sets) and `record_incomplete` (a code from `REASONS`, else `error`), plus the start-up hook and the import-failure block, both fixed text; no session id, number, total, accent count, path or text can reach it. An exception is named by type only, in the private block.
- Clearing: per recording, the owner is cleared in `measure_recording`'s `finally` and by the boundary on a failure, the PCM is deleted after the decode, and only numbers leave; on any failure `_measure_all` clears the traceback frames (and their chained exceptions') before counting it by type, and an INCOMPLETE run keeps no recording's numbers; the P1 holder is cleared in `_run`'s `finally`; the temporary store's key is memory-only (`persist_key=False`) and a store not shown gone stops the run as `custody`. P0 (the enrolment profile) lives for the run, as in the replay tool; it is the enrolment, not an encounter's vector.
- Injection and deserialisation: no shell, no pickle, no template; the paths are used as paths. Secrets: no logger is given to the store (the replay tool's `_open_store`), so nothing is logged.
Named limit (not a finding): a native library's own writes to the console (the speech runtimes') are outside Python's control, as for the replay tool.

- **[LOW]** SEC-001: `.cursor/loops/sv-measure-kept.py:148-159` — Python's warning display is still live: a library's warning (a numerical one from the speaker or speech runtimes, for example) would be printed to the console beside the two blocks, against D7's "nothing else is printed". The product itself uses no Python warnings, so silencing the display changes no decision. 🔁 Same family as round 6 LOW-003 (the other default displays). Searched: `warnings` in `desktop/src/scribe_desktop` (no use of the module) and in the script (none). Triage: Fix-now; Fix route: fix-on-fast; Desired: `warnings.showwarning` replaced by a function that shows nothing (the filters left untouched), the self-test's hook case checking it is installed and that a warning prints nothing; /fix decision: Applied; /fix notes: `_quiet_warning` set as `warnings.showwarning` after the two other hooks (the documented replacement point; no filter changed); the module docstring's "What it prints" paragraph names the silenced displays and the native-library limit; the hook case gains `warnings-not-shown` and `warning-silent` (a warning raised under `catch_warnings` with the `always` filter, so neither the once-per-location rule nor a `-W` option can hide or raise it); siblings: round 6 LOW-003's two hooks (applied there); not run (verify=composer); /fix date: 2026-11-21; /fix applied by: Claude Code
Fix-delta self-check: PASS — re-read the 3 applied hunks (the hook at the top, the two self-test checks, the docstring lines); `catch_warnings` restores the quiet display on exit, and the case count stays 32

### Round 8 — 2026-11-21
(Composer-recorded: transcribed verbatim from `.cursor/loops/stage-0-peer-r8.log`, the last `### Round 8` header; codex rc=0, escape-check post 0, refs unchanged. The executor's leg-1 verification follows below when it lands.)
Source: Codex — codex gpt-6-astra medium — Task 0.6 code peer review (stage-0.p1, peer round 1)
Status: Closed (leg svx8: 1 applied)

Scope:

- job 1: checked the print surface and exact record forms. `record_form_ok` checks the complete and incomplete forms, including baseline positions; the self-test checks extra lines, numbers and IDs. Error, interrupt, thread, finaliser and warning handling is content-safe on the inspected paths. Default argparse help bypasses the blocks: PR-LOW-3801.
- job 2: checked all four pins and import resolution. `sv-measure-kept.py:285–305` checks every file before execution; line 322 executes those checked bytes. Placeholders and mismatches refuse; checked modules occupy their import names, and scratch-path removal prevents subsequent filesystem imports from that folder. Placeholder pins are intentional.
- job 3: checked refusal ordering, custody and clearing. Manifest validation, crash-report exclusion and the shared instance lock precede decryption; `_main` releases the lock in `finally`. `sv_stitch.py:805` supplies `persist_key=False`. Per-recording owners, profile holders and chained traceback frames are cleared on the inspected failure paths. `profile_scores` uses plain loops without the former vector-capturing generator.
- job 4: checked D4 ordering, D7 eligibility, direction, sanity, additions and low-count rules. The implementation matches the documented interpretations, including the inclusive 80% cap and baseline words. The premise compares actual product labels, clinician and similarity against scratch R0 and fails on differences (`sv-measure-kept.py:785–791`). P1 reads only take A’s six files.
- job 5: checked constraints and fixtures. Self-test audio and identities are generated or faked; the measurement accesses recording audio without opening archived transcripts or saved notes. Git reports only the plan modified among tracked files; ignored scratch changes are outside that comparison. This review wrote nothing and accessed no user data.

Findings:

- **PR-LOW-3801** (LOW, output contract, `.cursor/loops/sv-measure-kept.py:916`): Default argparse help prints outside both required blocks and exits successfully without a COMPLETE record. Requesting help reaches argparse’s built-in help action before the refusal checks; overriding `error()` does not intercept it, and `main` explicitly propagates `SystemExit`. This violates D7’s two-block contract and the documented exit-status rule, although it does not decrypt or disclose clinical content. Evidence: `parser = _Parser(description="Stronger-voice Task 0.6 real-speech measurement (scratch).")`; lines 964–965: `except SystemExit:` / `raise`. Recommendation: Fix-now — disable automatic help or handle it through the existing content-free refusal renderer; add a self-test asserting exactly two blocks and a non-success exit.

Verification:

13 files read, wholly or in scoped portions; 5 jobs evidenced. Static inspection only: no scripts or tests executed. The supplied synthetic self-test report records 32 cases, 0 failures and placeholder pins. One finding verified against its call path.

PEER-ROUND-8 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

#### LEG 1 verified tuples
(Executor leg svx8, 2026-11-21, Claude Code; verify-then-fix. Each finding re-read against the code before any edit; no Python run, verify=composer.)
- PR-LOW-3801 — verified severity: LOW; class: real (pre-existing in leg svx6's script, not fix-induced); recommendation: Fix-now; why: `_parser()` built `_Parser(...)` with argparse's default `add_help=True`, so `-h` / `--help` runs argparse's help action, which prints the usage text and raises `SystemExit(0)` from inside `parse_args`. Overriding `error()` does not reach it, `_main` catches only `_CommandLineError`, and `main` re-raises `SystemExit`. So help printed outside the two blocks and exited 0, against D7's two-block form and "exit 0 only on COMPLETE". Nothing is decrypted or disclosed (it happens before every check). The peer's call path holds as cited. Decision: Applied; fix: `_Parser(..., add_help=False)`, so `--help` and `-h` are unrecognised options and go through `error()` to the `command-line` refusal (exit 2, the two blocks). One self-test case is added to the refusal list (`--help`: exit 2, exactly the two blocks, `reason: command-line`, both forms, no external call, clean), so the count pin moves from 32 to 33 (21 refusals) and its comment with it. Siblings: no other argparse exit path is used (no version action, no `print_help` / `print_usage`; searched `print_help|print_usage|add_help|"-h"`); nothing changed in `sv_lib.py`, `sv_stitch.py`, `ffl_lib.py` or `ffl-measure-kept.py`.
Verified summary: 1 finding, 1 verified as labelled (LOW, Fix-now), 0 dropped, 0 downgraded, 0 upgraded; 1 applied.
Fix-delta self-check: PASS — re-read the 3 applied hunks (the parser, the new refusal entry, the count pin and its comment); the new entry uses the existing `refusal_case` unchanged, so 33 cases are registered and pinned

### Round 9 — 2026-11-21
(Composer-recorded: transcribed verbatim from `.cursor/loops/stage-0-peer-r9.log`, the last `### Round 9` header; codex rc=0, escape-check post 0, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Task 0.6 code peer review (stage-0.p1, peer round 2)
Status: Closed (0 pending)

Scope:

- job 1: checked output construction, refusals, failures, custody stops, interrupts, exception hooks and warnings; no new disclosure path found. Record forms restrict content to status, override, fixed combination ids and words, or a fixed reason code (`sv-measure-kept.py:393–427`). Self-tests check both forms and reject extra content. The previously documented native-library console limitation remains.
- job 2: checked all four hashes, execution and import resolution; every file is checked before execution, and execution uses those same bytes (`sv-measure-kept.py:285–329`). Placeholders and mismatches refuse. Checked modules occupy their import names; scratch-path removal prevents later unchecked imports from that folder.
- job 3: checked refusal order and custody; manifest, crash-report and shared-instance checks precede decryption, with lock release in `finally` (`sv-measure-kept.py:993–1035`). Decoding passes `persist_key=False` (`sv_stitch.py:805`). Owners and chained traceback frames are cleared on failure; recording vectors do not survive into the next recording. `profile_scores` uses plain loops without the former vector-capturing generator.
- job 4: checked D4 ordering and D7’s calculations; eligibility, pooled increases, inclusive 80% cap, additions against P1:R0, baseline interpretations and low-count rules match the plan (`sv-measure-kept.py:603–638`). Incomplete runs emit no measurement words. The premise compares actual labels, clinician and similarity (`:785–791`); P1 reads only take A’s six files (`:1129–1135`).
- job 5: checked constraints and fixtures; self-test content is generated or faked, and the measurement reads recording audio without opening archived transcripts or saved notes. Git reports only the plan modified among tracked files; ignored scratch changes cannot be established from that comparison. This review wrote nothing and accessed no user data.
- job 6: checked PR-LOW-3801; `add_help=False` routes both help spellings through `_Parser.error()` to the two-block `command-line` refusal, exit 2 (`sv-measure-kept.py:911–980`). The new refusal case is at `:1693`, with count pinned to 33 at `:2036`. No additional unintended argparse success exit found; the explicit synthetic self-test remains a separate mode.

Findings: none.

Verification:

13 files read, wholly or in scoped portions; 6 jobs evidenced. Static inspection only: no scripts, suites or network commands executed. The supplied synthetic report records 33 cases, 0 failures and placeholder pins. Prior fixes verified; no new defect substantiated.

PEER-ROUND-9 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 10 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: Phase 0's tracked diff, `git diff 42032e1 -- .cursor/plans/plan-stronger-voice.md .cursor/plans/plan-practitioner-profile.md` (Tasks 0.3 to 0.7, the svx10 to svx14 handoff bullets, the Task 0.7 sibling lines and the four dated lines on the practitioner-profile plan). `/review-loop` round 1 of 3, executor leg svx15 (no Python run). The frozen scratch code is not re-reviewed (rounds 6 to 9).
Checked against the evidence, each figure and word:
- Task 0.4: `sv-pass.log` (seven sets `errors 0, complete`, `PASS PROBLEMS: 0`, `PASS_END rc=0`, HEAD `7e730b1`, desktop clean); `sv-premise.log` (50 / 22 / 22 / 23 / 22 / 22 / 22, `PREMISE DIFFERENCES TOTAL: 0 (sets complete 7/7)`); `sv-selftest-5.txt` (the fixture cases named, `0 JSON file(s) checked`, 55 passed); `sv-selftest-6.txt` (191 JSON and 15 other files, 55 passed).
- Task 0.5a against `sv-sets-report.md`: the cohort 183, R0's two rates and seconds, every B1 figure, B2's 32 of 36 at +0.03 or +0.10 and B2-21 to B2-24 at 1.11 % (+0.51), B3 from +0.61 to +1.34, bar C's 86 encounters, 16.9 s, F3.0-W1.0's 3 kept cuts and 1 wrong split on `h5-21`, the seven left-out counts, the one tied segment on `h5-11`.
- Task 0.5b against `sv-stitched-paste.md`: every part kept and every required part at its target, the quiet pool's 25.2 s and 27.6 s, the ten dialogues on the match branch, A1 and A2, the part cosines (0.701 lowest, the rest 0.822 to 0.885) and 0.651, every row's stitched lines, bar C's 270.9 s to 9.7–22.9 s and 16 to 19 wrong splits (5.34 to 6.34 per 5 min), the four segments past 30 s, parity 0.
- Task 0.6 against `sv-kept-paste.md`: status, override and every combination's three words; its lead line's hash check is the composer's leg svx13 prompt ("18917bc5...9d15, matched").
- Task 0.5c against D9's text: the order, the three line sets of bar B as the only gating lines, `unmeasured` not met (none reads so), bars A1, A2 and C reporting only, and D9's "what the selected row adds".
- The progress figures 9 / 14 / 18 / 27 / 32 % (2, 3, 4, 6 and 7 of the 22 numbered tasks).
- C1: no session id, real-speech number, pooled real-speech total, accent count or machine path in either plan's diff (`C:\sv-sets\` is the synthetic-set folder C10 allows; `stronger-voice\` is a subfolder name D2 already gives).
- The practitioner-profile lines against the code: `ATTRIBUTION_THRESHOLD: Final = 0.50` (`speaker_embedding.py:82`); with a match `attribute_speakers` labels the matches `speaker_1` and the whole remainder `speaker_2` (`transcription.py:972-974`), and `enrolled_cluster` returns the highest-mean label with its mean (`:926-934`), so with a match the number is the mean of the direct matches.
- Line endings: both plans `i/lf w/lf` (`git ls-files --eol`).
Finding verification: 6 candidates; 1 dropped (Task P.3's mock is sized for a session-adaptation row: still enough for B1-35, which needs one direct match, so nothing contradicts); 0 downgraded.
Missed-issue pass: re-read the Goal, Agreed Scope, Deferred, Accepted Assumptions, Key Design Decisions, Flows 1 to 4, D1 to D9, C1 to C10, Validation and Phases 1 to P whole for statements the decision settles; result: LOW-002 and LOW-003.

- **[LOW]** LOW-001: `.cursor/plans/plan-practitioner-profile.md` D8's dated line — "and one redo of the weakest part" reads as a redo on every enrolment, and "the equal-weight mean of the parts" leaves out that a left-out part is not in it; stronger-voice D3 redoes only when a part scores under the calibrated figure, at most once, and stores the mean of the captured parts' final attempts — Triage: Fix-now; Fix route: fix-on-fast; Desired: the line says both as D3 does; /fix decision: Applied; /fix notes: "at most one redo, of the weakest part, when a part does not match the rest" and "the normalised equal-weight mean of the captured parts (final attempts)"; the file's LF endings kept; siblings: D3's and D13's dated lines and the D-P1 note re-read, accurate; /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-002: `.cursor/plans/plan-stronger-voice.md` Step H — H3 reads "C4's ownership and the enrolment's memory bound first", but with B1-35 no owner is built (Task 0.7's consequences); only the `R0` case is reconciled in Step H's heading — Triage: Fix-now; Fix route: fix-on-fast; Desired: a dated line under Step H saying H3's focus with B1-35; /fix decision: Applied; /fix notes: a dated sub-bullet under H3: with B1-35 no vector is kept and C4's owner is not built, so H3 covers the enrolment's memory bound and lease and the recovery mark's two guarantees (it only adds `speaker_1` labels, and nothing runs without a confirmed match); siblings: Task 2.1's B2/B3 parts (already reconciled by the Phase 2 built-row line), Task 5.2's B2/B3 documents (Task 0.7's consequences); /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-003: `.cursor/plans/plan-stronger-voice.md` the Deferred two-tier item and Task 5.2's review-guide wording — "a line matched only by the session rule (below the pass mark)" and "a line may be labelled yours from the sound of this consultation" describe session adaptation, which is not built; with B1-35 the line below the pass mark is matched by the recovery mark, on its own score, after a direct match — Triage: Fix-now; Fix route: fix-on-fast; Desired: a dated note beside each, the original words kept; /fix decision: Applied; /fix notes: one dated parenthesis at each place (Task 0.7: the recovery mark B1-35; the guide's line then says a line that scores just under the usual match may be labelled yours once your voice has matched in the consultation, still for the practitioner's approval); siblings: searched `session rule`, `sound of this consultation`, `session adaptation`, `uses the consultation`: C4's Key Design Decision and C5 and Task 5.2's "recovery mark or session rule" are generic or already settled; /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-004: `.cursor/plans/plan-stronger-voice.md` Task 0.7's brief bullet on the accepted residue — it says "Shadow mode cannot show (2) or (3)" while its three consequences carry no numbers — Triage: Fix-now; Fix route: fix-on-fast; Desired: the consequences numbered as Accepted Assumptions numbers them; /fix decision: Applied; /fix notes: "(1)", "(2)", "(3)" added before the three; no word of the summary changed otherwise (this is the plan's summary of the brief, not the words the practitioner read); siblings: Accepted Assumptions already numbered; /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-005: `.cursor/plans/plan-stronger-voice.md` the progress figure — the svx10 to svx14 bullets count "of 22 tasks", but the Tasks section holds 27 checkboxes (Step H and H1 to H4 are the other five), and the denominator is said nowhere — Triage: Fix-now; Fix route: fix-on-fast; Desired: the denominator stated once, the earlier bullets kept; /fix decision: Applied; /fix notes: stated in the svx15 handoff bullet: the figure counts the 22 numbered tasks (0.1 to 0.7, 1.1, 1.2, 1.4, 2.1, 2.2, 4.1 to 4.3, 5.1, 5.2, P.1 to P.5); Step H's five boxes are not counted; siblings: none; /fix date: 2026-11-21; /fix applied by: Claude Code
Fix-delta self-check: PASS — each of the five applied hunks found by search where it was made (the practitioner-profile plan's D8 line at :256, still four added lines in that file; the Deferred two-tier item; Task 5.2's guide wording; Task 0.7's numbered residue; H3's dated line; LOW-005's denominator in the svx15 handoff bullet); `git diff --check` clean and both plans still `i/lf w/lf`; no recorded figure, word, selection or decision changed

### Round 11 — 2026-11-21
(Transcribed verbatim by executor leg svx16 from `.cursor/loops/stage-0-peer-r11.log`, the last `### Round 11` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 0 close documents peer review (stage-0.p2, peer round 1)
Status: Closed (0 pending)

Scope:

- job 1: checked Tasks 0.5–0.7 and svx12–svx15 against the three evidence files; recorded rates, differences, seconds, counts, grid results and words match. Calibration is 0.651; lowest part is take a, part 1, at 0.701.
- job 2: checked the selection against D9 and bar B; B1-45 and B1-40 fail kept direction, and B1-35 is the first qualifying row. Its gains match +2.2/+7.2/+23.8 points and `adds`. A1, A2 and C remain report-only; `unmeasured` cannot qualify.
- job 3: checked the reviewed additions against C1 and D7; no prohibited consultation identifiers, numerical results, accent counts or personal machine paths found. Task 0.6 preserves the permitted block’s status, override and combination words.
- job 4: checked “Confirm B1-35,” the allowed decision options and sibling build instructions; consistent with Lever A plus B1-35, Lever C excluded, no consultation vector retention and version 0.4.2. Earlier handoff bullets remain historical records.
- job 5: checked the four practitioner-profile additions against stronger-voice D3/D4 and the named code symbols; consistent with the unchanged 0.50 pass mark, conditional addition of `speaker_1` labels, unchanged stored clinician and similarity, and guided enrolment’s capture contract.

Findings: none.

Verification: 7 scoped files read; 5 jobs evidenced. Round 10’s applied wording fixes checked. No files written, scripts executed, tests run or network commands issued.

PEER-ROUND-11 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 12 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: Phase 1's diff, `git diff HEAD -- desktop/ .cursor/plans/plan-stronger-voice.md` (uncommitted, on top of `8bedfc4`): `enrolment.py`, `ui/models.py`, `ui/practitioner.py`, `note.py` and `ui/note.py` (docstrings), `test_enrolment.py`, `test_ui_screens.py` and the plan. `/review-loop` round 1 of 3, executor leg sx2 (no Python run: verify=composer). The primary baseline is `8bedfc4` (the first code round of Phase 1). `ui/practitioner.py` was read whole; `main_window.py`'s close guard (:1588), lock handler (:980–989) and suspend handler (:1023), and `microphone.py`'s `stop_monitor` (:306) were read for the custody paths. Read against D3, D8, C2, C6, C7, C8 and Tasks 0.1, 1.1, 1.2 and 1.4.
Checked and clean:
- D3, as built:
  - Every passage, cue and title equals Task 0.1's approved words, with the quotation marks left off (compared word for word; now pinned whole, LOW-003).
  - Targets 30 / 15 / 12 / 15 / 12 / 15 s; caps `max(3 × target, 45)`; parts 2 and 5 not required.
  - The fixed "keep reading" line; the beat is `cancel.wait(beat_seconds)` with no stream open, 3 s in the app and 0 in tests.
  - Consistency is each part against the unit mean of the others, with `PART_CONSISTENCY_FIGURE = 0.651` (Task 0.5b's 0.701 less 0.05).
  - There is exactly one redo: of the lowest part, the earlier on a tie. It replaces the part whole; a redo short at its cap keeps the first attempt; the figures are computed once more for the weakness line.
  - An optional part is left out only on `EnrolmentTooShortError`, with the seconds from its last progress number. A required part's shortfall, an embedding with no speech, a device failure and a Stop each fail with nothing saved.
  - The strength share is leave-one-part-out at or above `ATTRIBUTION_THRESHOLD`. It is computed in the worker and carried only in `GuidedEnrolmentResult`, never stored.
  - The stored vector is `combine_parts` over the final attempts, and the seconds are their `fsum`. `PractitionerProfile` is unchanged (no schema change).
- C2 and C8 (custody):
  - One `begin_enrolment` lease covers every part, beat, embedding, the redo, the save and the result handler. It is released in both handlers' `finally`, after the re-render, and on the failed handoff after its error is shown.
  - Each part's PCM is `del`'d in `record_part`'s `finally` before the next part. `_SegmentVectorRecorder` keeps vectors only.
  - Stop, the screen lock and sleep (both press `on_stop`) end a part inside the capture, a beat at once, and the sequence at the check before each embedding and before the save.
  - Nothing new logs, writes a file or touches `wave`.
- The busy state: `is_busy` is the held lease. Every control that records, writes or deletes a profile is disabled while it is held, and every such handler returns: `on_record`, `on_confirm_consent`, `on_delete`, the phrase, rule and style handlers (:1704, :1715, :1726, :1870, :1940 after this round's fix), `on_choose_files` and `on_learn_from_notes`. `_release_lease` re-applies the enablement, so no path leaves the tab busy after the release. `_on_progress` drops every event once the lease is gone. The close guard (`main_window.py:1588`) reads `is_busy`, so a queued result still holds the close.
- The UI:
  - The four card labels are plain text with Qt's default interaction flags (not selectable; the part-start test pins the passage's flags).
  - Every card label word-wraps; at the 150 % stand-in the card now has a pin (LOW-002).
- Task 1.4: `LEARNING_NOT_ATTRIBUTED_NOTE` and the two docstrings match the code. Both learners in `ui/note_review.py` (:301 and :393) test `spoken_by_confirmed_clinician`, which compares labels only (`note.py:1688`).
- The tests:
  - Each named change in leg sx1's bullet has its reason.
  - Each new case fails on the defect it names. For example, the queued-result case fails with the old thread-running test, because Confirm consent would write the cached stale vector over `voice.enc`; the late-event case fails without the drop check ("25 s of 15 s").
  - Only the existing fakes are used (`_FakeCapture`, `FakeController`, `FakeBackend`, `_StubEmbedder`), plus two thin scripted seams, `_Step` and `_ScriptedEmbed`.
  - `test_shadow_exits.py` is untouched.
Finding verification: 5 candidates; 2 dropped (the stored vector moving from numpy float32 to plain-Python float64: the profile stores floats and every reader re-normalises, already open point (5) for Task 4.3; a "late" progress event cannot in practice follow the next part's start, because one worker emits in order: the drop check is D3's defence and is kept); 0 downgraded.
Missed-issue pass: re-read `ui/practitioner.py` 1151–1446 (the record path, the worker, the slots and both handlers) and `enrolment.py`'s part functions; result: LOW-001 (the handoff's re-entrancy, by the SEC-021 precedent).
Wording for the practitioner's live smoke, choices the plan leaves open, not findings: (a) part 6's "Do not read." cue sits above the fixed "Keep reading until the counter fills…" line, which D3 shows under every passage; (b) the self-written heading ("Part N of 6: <title>", "(again)" on the redo), the get-ready line, the redo line's "Record it once more.", the weak-part line and the strength line; (c) a required part's shortfall shows `record_enrolment`'s own text, which names no part (kept so the existing pins hold).

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/ui/practitioner.py:1174-1187` — `on_record` made the tab busy (`self._lease = lease`) before the microphone handoff, but cleared the cancel event only AFTER it. A Stop arriving during `stop_monitor` (a screen lock or sleep, delivered while the stream's stop pumps messages: the re-entrancy round 57 SEC-021 found for a device open) would be acted on, then wiped, and the enrolment would run despite the lock. 🆕 Pre-existing in shape: before Task 1.2 `on_stop` did nothing then, which ended the same way. Triage: Fix-now; Fix route: fix-on-fast; Desired: the event cleared before the lease, and the preparing line not written over "Stopping..."; /fix decision: Applied; /fix notes: `self._cancel_requested.clear()` moved to just before `self._lease = lease`, with a comment naming the re-entrancy; the preparing line is written only while the event is clear. New case `test_a_stop_during_the_handoff_stands` (`test_ui_screens.py`): a handoff that presses Stop leaves "Stopping...", then "Enrolment stopped - nothing was saved.", one capture call and no file. It fails with the old order (the six parts run and save). Siblings: no other path clears the event (searched `_cancel_requested.clear`, `cancel.clear`); not run (verify=composer); /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-002: `desktop/tests/` — nothing pinned that the guided card fits the Practitioner tab at the narrowest width the existing pins use (the 150 % stand-in, `test_ui_phase_s.py` `_at_150`). The tab's scroll area has no sideways bar, so content wider than the viewport would be cut off. Triage: Fix-now; Fix route: fix-on-fast; Desired: a laid-out pin over every part and the redo's heading; /fix decision: Applied; /fix notes: `TestGuidedCardWidth.test_every_part_fits_across_at_150_percent` in `test_ui_phase_s.py` (beside the 150 % pins, which hold `_at_150` and `_laid_out`). The main window is shown on the Practitioner tab at `_at_150`, and each part is shown through `_show_part`, with `redo` False and True. For each it asserts that the content is no wider than the viewport, and that each card label is visible, no wider than the viewport and no shorter than its `heightForWidth`. A passage that stopped word-wrapping fails it. Siblings: none (no other new widget); not run (verify=composer); /fix date: 2026-11-21; /fix applied by: Claude Code
- **[LOW]** LOW-003: `desktop/tests/test_enrolment.py` `TestEnrolmentScript.test_the_approved_wording_ships_verbatim` — the test is named for verbatim wording, but pinned the normal, numbers and away passages by their first or last words only, and the quiet passage not at all, so a changed word in the middle would pass. Triage: Fix-now; Fix route: fix-on-fast; Desired: every passage, cue and title pinned whole; /fix decision: Applied; /fix notes: the four passages are pinned whole as Task 0.1 approved them, with the six titles and the short and numbers cues; the short and own parts were already whole; siblings: the card-string test pins each line whole already; /fix date: 2026-11-21; /fix applied by: Claude Code
Fix-delta self-check: PASS — I re-read the 3 applied hunks in `ui/practitioner.py` (the clear before the lease, the old clear removed, the guarded preparing line), the new case in `test_ui_screens.py`, the new class in `test_ui_phase_s.py` and the two `test_enrolment.py` hunks. The failed-handoff path still releases the lease after its error. `ruff check .` passed and `mypy` found no issues (72 files). `git ls-files --eol` is unchanged for all four files (`practitioner.py`, `test_ui_screens.py` and `test_ui_phase_s.py` w/crlf; `test_enrolment.py` w/lf).

### Round 13 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: the same diff as round 12 (`git diff HEAD -- desktop/ .cursor/plans/plan-stronger-voice.md`, on top of `8bedfc4`), with round 12's fixes in. `/review-loop` round 2 of 3, executor leg sx3 (no Python run: verify=composer). The composer's run after round 12: the three touched test files 600 passed; the full suite 11155 passed, 9 skipped, 0 failed; the `test_shadow_exits.py` diff empty.
Round 12's fixes, confirmed:
- LOW-001: `ui/practitioner.py:1177` clears the cancel event before `self._lease = lease` (:1178), and no later clear remains. The preparing line is written only while the event is clear (:1331). The failed-handoff branch still shows its error and then releases the lease (:1188–1190). `test_a_stop_during_the_handoff_stands` passed in the composer's run.
- LOW-002: `test_ui_phase_s.py` `TestGuidedCardWidth` passed at the 150 % stand-in for all six parts, each with and without the redo heading.
- LOW-003: `test_enrolment.py` pins all six passages, cues and titles whole. I re-compared each pinned string against Task 0.1's text and against `ENROLMENT_SCRIPT`.
Re-reviewed whole, with the same focus as round 12:
- D3: the script, targets, caps, beat, figure, the one redo, the left-out rule, the in-memory strength share, one stored vector and no schema change.
- C2 and C8: the single lease, each part's PCM dropped before the next, and Stop, lock and sleep.
- The busy state: every handler that writes or deletes still checks `is_busy` (:1110, :1152, :1454, :1492, :1515, :1529, :1704, :1715, :1726, :1870, :1940).
- The UI and the Task 1.4 wording.
- The tests.
- A search for stale strings: "about a minute" and "attributed to you" no longer appear in the package or the tests (only `ml_warmup.py` keeps an unrelated "about a minute"), and no caller of the removed `_progress_text` remains.
Finding verification: 0 candidates; 0 dropped; 0 downgraded.
Round classification: 0 🆕 / 0 ⚡ / 0 🔁.
Missed-issue pass: re-read `ui/practitioner.py` 1151–1450 (the record path after the fix, the worker, the slots and both handlers), `test_ui_screens.py`'s new handoff case and `test_ui_phase_s.py`'s new class; result: none.
Findings: none. The review has converged (no CRIT, HIGH or MED, and nothing left to apply). Round 12's three wording points, (a) to (c), are still for the practitioner's live smoke. (Leg sx5, 2026-11-21: that smoke was held at the Phase 1 close and is owed before Task P.1.)

### Round 14 — 2026-11-21
(Transcribed verbatim by executor leg sx4 from `.cursor/loops/stage-1-peer-r14.log`, the last `### Round 14` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 1 code peer review (stage-1.p1, peer round 1)
Status: Closed (leg sx4: 1 applied)

Scope:

- job 1: checked custody against C2 and threat-model surfaces 1–10: one lease covers the parts, beats, redo, embedding, save and result handlers; handlers release it in `finally`. Each successful capture’s PCM is dropped before the next part. No added audio persistence or logging; only the combined profile vector is saved. Failure, Stop, lock and close paths were assessed through the permitted code and scoped tests; no additional custody defect established.
- job 2: checked lease-based busy guards, cancellation ordering, queued progress and result handling. Confirm consent, Delete and repeated Record handlers refuse while busy; result handling retains the lease after the worker finishes. Round 12’s cancellation fix stands. Found one remaining handoff interval where controls remain enabled, detailed below.
- job 3: checked all six passages against Task 0.1, targets/caps, three-second beat, calibration 0.651, optional shortfalls and single weakest-part redo. Equal-weight normalisation, final-attempt seconds and leave-one-part-out strength arithmetic match D3, including absent parts, a lone part and directionless references. Profile schema remains unchanged.
- job 4: checked `LEARNING_NOT_ATTRIBUTED_NOTE` and both files’ changed docstrings against `spoken_by_confirmed_clinician`; wording correctly describes the speaker-label test. Executable note behaviour is unchanged.
- job 5: checked changed tests’ assertions, fake capture/embed seams, layout pin and forbidden additions against `test_shadow_exits.py`. The tests distinguish the intended outcomes; no prohibited package addition found. Busy-control assertions run after `on_record` returns and therefore miss the handoff interval below.

Findings:

- **PR-MED-4201** (MED, consent/concurrency, `desktop/src/scribe_desktop/ui/practitioner.py:1178`): Controls remain enabled during the re-entrant microphone handoff despite the held lease. On first enrolment or stale consent, a consent-checkbox click processed during that handoff can untick consent; its toggle handler updates enablement but does not cancel enrolment. The worker then proceeds and can save a current consent record without rechecking the box. This also violates Task 1.2’s requirement to disable controls throughout the lease. Evidence: `:1178` sets `"self._lease = lease"`; `:1186` calls `"self._on_capture_start()"`; the consent check occurs earlier at `:1158`, while the normal busy-control update occurs only at `:1343`, `"self._update_controls()"`. The checkbox’s toggle connection at `:522` only invokes `"_update_controls()"`. Recommendation: Fix-now - Apply busy enablement immediately after assigning the lease, before the handoff; add a handoff-hook test asserting controls are already disabled and a checkbox click cannot change consent.

Verification:

- 15 scoped files read, wholly or in relevant sections; 5 jobs evidenced.
- Round 12’s three fixes rechecked; round 13’s conclusions independently assessed.
- Static review only; no files written, tests executed or network accessed. The reported 11155 passed / 9 skipped remains executor evidence.

PEER-ROUND-14 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

#### LEG sx4 verified tuples
(Executor leg sx4, 2026-11-21, Claude Code; verify-then-fix. The finding was re-read against the code before any edit. No Python was run: verify=composer.)
- PR-MED-4201 — verified severity: MED; class: real, 🆕 pre-existing. Before Task 1.2 the same interval was open under the thread-running busy test. Round 12 LOW-001 closed it for Stop only.
  - Recommendation: Fix-now.
  - Why it holds:
    - `on_record` checks the consent box at :1158. It then takes the lease (:1178) and calls `_on_capture_start` (:1186).
    - `_update_controls` ran only at the method's end (:1343). Through the handoff, every control kept its idle enablement: Record, the consent and learning boxes, the microphone, Refresh devices, Confirm consent, Delete, the learn controls and the style radios.
    - The consent box's toggle (:522) only re-renders enablement. The worker builds its consent record with no re-check, as a current one (:1315–1319).
    - So a click delivered while the handoff pumps messages could untick consent and still end in a saved current record. The handoff can pump messages: round 57 SEC-021's re-entrancy precedent, and round 12 LOW-001.
    - The learning box is read at :1192, after the handoff, so a click there would be honoured silently.
  - Handlers that act are already refused: each checks `is_busy`, which is the lease. So the gap is the widgets' own state, not a handler that writes.
  - Start on the Record page is refused by the controller's activity from `begin_enrolment` (:1164) onward.
  - The redo has no handoff: `_on_capture_start` runs once, in `on_record`, and the microphone screen's poll guard keeps the monitor closed while `controller.enrolling`.
  - Decision: Applied.
  - Fix: `self._update_controls()` right after `self._lease = lease` and before the handoff, with a comment naming the finding. That one call closes the interval for every control `_update_controls` governs, as a class: each is disabled, and Stop is shown and enabled as the escape. Every exit's `_release_lease` re-enables them. The call at the method's end stays; it is harmless and keeps Stop's state after the worker starts.
  - New case `test_the_tab_is_busy_through_the_handoff` (`test_ui_screens.py`, `@windows_only`, a first enrolment so the consent box is editable when idle). From inside the handoff hook it records every control's enablement: Record, consent, learning, microphone, Refresh devices, Confirm consent, Delete, Choose notes, Learn and each style radio. It records Stop's state, then clicks the consent and learning boxes. It asserts that all of them were disabled, that Stop was shown and enabled, and that neither box changed. The saved profile carries the current consent version and the learning choice as it stood at Record. On today's code it fails: Record and both boxes are enabled during the hook, and the click unticks consent.
  - Siblings: no other point in `on_record` runs foreign code between the lease and the first `_update_controls` (searched for calls between :1178 and the old :1343). `on_style_selected` writes only the practitioner settings, and its radios are now disabled from the lease.
Verified summary: 1 finding, 1 verified as labelled (MED, Fix-now), 0 dropped, 0 downgraded, 0 upgraded; 1 applied.
Fix-delta self-check: PASS — I re-read the applied hunk in `ui/practitioner.py` and the new case. The failed-handoff branch still releases the lease through `_release_lease`, which re-enables the controls (round 12's `test_a_failing_handoff_releases_the_lease_and_starts_nothing` still asserts Record is enabled after it). `ruff check .` passed and `mypy` found no issues (72 files). Both files' `git ls-files --eol` is unchanged (w/crlf).

### Round 15 — 2026-11-21
(Transcribed verbatim by executor leg sx5 from `.cursor/loops/stage-1-peer-r15.log`, the last `### Round 15` header; codex rc=0, escape-check clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 1 code peer review (stage-1.p1, peer round 2)
Status: Closed (0 pending)

Scope:

- job 1: checked custody against C2 and threat-model surfaces 1–10. One lease covers capture, beats, embedding, redo, save and result handling; both result handlers release in `finally`. Each captured part’s PCM is dropped before the next part. No added audio persistence, logging or stored strength/consistency figures. Stop, lock, sleep and close were assessed through the permitted code, contract and scoped tests; no additional custody defect established.
- job 2: checked every busy-governed control and lease entry/exit path. `ui/practitioner.py:1184` now refreshes the complete control set before the handoff; handlers refuse concurrent profile actions, and queued results retain the busy state. Failed handoff and result-handler exits restore enablement. Cancellation clears before the handoff and cannot overwrite a subsequent Stop; worker events cross through Qt signals. PR-MED-4201 is closed as a class.
- job 3: checked the six passages verbatim against Task 0.1, targets/caps, three-second beat, 0.651 calibration, optional-part shortfalls and single weakest-part redo. Equal-weight normalisation, final-attempt seconds and leave-one-part-out strength arithmetic match D3, including omitted/redone parts, a lone part and degenerate references. One vector is stored under the unchanged profile schema.
- job 4: checked `LEARNING_NOT_ATTRIBUTED_NOTE` and the changed `note.py` / `ui/note.py` docstrings against `spoken_by_confirmed_clinician`. They correctly describe the speaker-label predicate; executable note behaviour is unchanged.
- job 5: checked new and changed tests against their guarded defects. The handoff regression test would fail before the fix: its hook observes enabled controls, checkbox clicks change consent/learning state, and subsequent assertions detect those changes. Other cases distinguish cancellation, queued-result protection, redo replacement, shortfall handling and layout outcomes. Existing fake capture/backend/embed seams are used. No forbidden package additions found; `test_shadow_exits.py` has an empty diff.

Findings: none.

Verification:

- 15 scoped files read, wholly or in relevant sections; 5 jobs evidenced.
- Rounds 12–14 and sx1–sx4 handoffs assessed against the current diff.
- Static review only: no writes, test execution or network access. The reported 11156 passed / 9 skipped remains executor evidence.

PEER-ROUND-15 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 16 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: Phase 2's diff, `git diff HEAD -- desktop/ .cursor/plans/plan-stronger-voice.md` (uncommitted, on top of `9fb3777`): `speaker_embedding.py`, `transcription.py`, `test_attribution.py`, `test_live_transcription.py`, `test_ui_screens.py` and the plan. Also the scratch `.cursor/loops/sv-measure.py` (git-ignored): its `--sets --against-product` mode (:917–1171), the self-test's check 2b, the whole-encounter check and `phase0_product`, and the argument dispatch (:2011–2043). `/review-loop` round 1 of 3, executor leg sb3 (no Python run: verify=composer). The primary baseline is `9fb3777` (the first code round of Phase 2). The composer's runs before this round: `test_attribution.py` with `test_live_transcription.py` 213 passed; `test_ui_screens.py` 531 passed; the full suite 11176 passed, 9 skipped, 0 failed; the self-test 56 passed; the `test_shadow_exits.py` and `speaker_eval.py` diff empty; the five frozen hashes equal. Read against D4, D8, D9, C4, C6, Task 0.7's record and Tasks 2.1, 2.2, 4.3 and 5.2.
Checked and clean:
- B1-35 as built (`transcription.py` `recover_practitioner_labels`, :991–1031):
  - It runs only when some score is at or above `ATTRIBUTION_THRESHOLD` AND `enrolled_cluster` over today's labels confirms `speaker_1`; otherwise it returns today's labels.
  - The band is `RECOVERY_MARK <= s < ATTRIBUTION_THRESHOLD`: 0.35 inclusive, 0.50 exclusive. The pass mark is unchanged at 0.50 (`speaker_embedding.py:83`), and its pin is unchanged.
  - It only ever writes `speaker_1`, so no label is taken away. A `None` score is excluded explicitly; -1 sits under the band.
  - D4's acceptance check is kept. It cannot fail: in the match branch every remaining `speaker_2` scores under 0.35 or has no score (`attribute_speakers` :980–982), so its mean is under the new `speaker_1` mean, and `speaker_1` keeps its text.
- `assemble_transcript` (:1737–1747):
  - One call, in the attribution branch only. Both drivers reach it: the batch path at :1908 and the live receiver's path at :2332. These are the only two callers in the package.
  - The shortcut branch is byte-equivalent to before: all `speaker_1`, and `enrolled_cluster` only when attributing.
  - The no-profile branch is the 2-means with `enrolled = None`, as before (the old line gave `None` when not attributing).
  - The stored clinician and number are `enrolled_cluster` over today's labels, so in the match branch the number is the mean of the direct matches, as D4 says. The `TranscriptDocument` docstring (:439–443) and `assemble_transcript`'s say what the code does. Nothing new is stored in the transcript.
- The frozen items: `attribute_speakers`, `enrolled_cluster`, `label_speakers`, `transcript_before` and `speaker_eval.py` are not in the diff. No vector is kept: the rule reads one float per segment.
- `speaker_eval.py` still measures the product. Its enrolled condition scores the shipped pipeline's document (:788–793). Its `label_speakers` reproduction check covers the plain, profile-free pass only (:1181), which the mark never touches. So `measure-speakers.py --enrolment` raises no harness fault on Phase 2's product.
- The learning residue: both learners test the label (`ui/note_review.py` `consider_learning`, and `consider_rule_learning` :232, whose trigger is the replaced utterance's tail through the refusal filter). Task 2.1's line ("Add or Move then Save admits its phrase subject to the refusal filter, and a typed Edit then Save can write its shorthand rule") matches sb2's finding. The four `TestNoteScreenTypedEdits` cases pin it on the class's own fixture and `_ratify`. The one added acknowledgement is of a warning the fixture really raises, and is asserted present first. The threat model's statements are Task 5.2's, by the plan's sequence; nothing in this phase's diff touches them.
- Task 2.2's mode:
  - It decodes once through the harness's enrolled path. It applies scratch R0 and the built row to the same captured assembly inputs.
  - It compares labels (the whole list), clinician and number with the product's document, exactly. A real difference names the encounter, makes the set's difference list non-empty and sets a non-zero exit.
  - The owner holds spectral features only. Records go through `write_record` and hold no vector.
  - A refused set returns 2. A set whose enrolment fails writes no `run.json`, so `complete_sets` falls short and the exit is 1.
- The tests:
  - `TestRecoveryMark` fails on a band moved by one ULP at either edge, on a relabelled `None` or -1, on a run without a match or confirmation, and on any label taken away (3,000 generated lists, `ran > 500`).
  - `TestRecoveryInAssembly`'s first case fails if the number is recomputed from the new labels (0.65, not 0.9). Its shortcut and no-profile cases fail on any call of the rule.
  - The two-driver case fails if either driver skips the mark or embeds the short slice.
  - The radio cases fail if the screen checks another label.
  - Only the existing fakes are used (`MockSpeakerEmbedder`, `MockSpeechProvider`, `amplitude_vad`, the store fixture), plus one documented monkeypatch of `MIN_ATTRIBUTION_PCM_BYTES`.
Finding verification: 3 candidates; 1 dropped (`built_row_differences` compares the number with `!=`: the product's and scratch's means are both `math.fsum` over the same floats with the same clamp, and the self-test's check 2b and the whole-encounter check passed exactly; open point (5)'s tolerance is for vectors, not this number); 0 downgraded.
Missed-issue pass: re-read `transcription.py` :908–1031 and :1703–1760, `sv-measure.py` :917–1171 and :2011–2043, and Tasks 4.2, 4.3 and 5.2; result: MED-001, LOW-001.

#### MED-001: `plan:Task 4.3`, `.cursor/loops/sv-measure.py:2029-2031` — Task 4.3's command does not exist, and the frozen parity it would lean on now fails on this product
- Classification: 🆕 (surfaced by Phase 2's build; leg sb1's open point (1) recorded it only in its handoff bullet)
- Triage: Fix-now; Fix route: fix-on-fast (plan text)
- Why it matters: Task 4.3 tells the practitioner to run `sv-measure.py --stitched --against-product`. The dispatch refuses that pair: `--against-product` goes with `--sets` only (:2029–2031). And `--stitched` runs the frozen `sv_stitch.py`, whose whole-run parity compares scratch R0 with the product's pipeline. Since Phase 2 the product applies the mark, so that parity fails wherever a merged or quiet segment scores in the band. The frozen `sv-measure-kept.py` has the same premise check, so a re-run on this tree would refuse recordings the product now relabels. Its Task 0.6 run is done and must not be repeated; neither Task 0.6 nor Task 4.3 says so. A practitioner-run task that will be refused, or will report differences that are no defect, wastes a run of their real recordings.
- Current behaviour: the fact sits only in leg sb1's handoff bullet.
- Desired behaviour: Task 4.3 and Task 0.6 each carry a dated line: the command does not exist yet; Task 4.3's leg builds a stitched comparison of the built row against the product (a new module beside the frozen ones, or a new freeze, hardened before the practitioner's run); `sv-measure-kept.py` and `--stitched` are not run on Phase 2's product.
- Pattern siblings: searched the plan for `--stitched`, `sv-measure-kept.py` and `against-product`. Task 0.5b is done (its run is on Phase 1's product), Task 2.2 is `--sets` (exists) and Task 4.1 reads Task 2.2's records. None other.
- Scope-expansion disposition: n/a (plan text within Tasks 0.6 and 4.3; the code is Task 4.3's own).
- /fix decision: Applied; /fix notes: a dated line on Task 0.6 (not run again on Phase 2's or a later product) and on Task 4.3 (the mode is to be built and hardened by Task 4.3's leg, comparing the built row with the product; neither frozen file is edited or re-run); /fix date: 2026-11-21; /fix applied by: Claude Code

- **[LOW]** LOW-001: `plan:Task 5.2` — the Lever B residue's wording does not yet say how it really behaves on the two learning paths. Leg sb2 found that the phrase learner refuses a line whose first word is capitalised and is neither a common starter nor an admitted opener (a patient's "My knee …" is refused as name-like, as any speaker's would be). The shorthand learner's trigger is the line's last content words through the same filter. The opener rule reaches it only when that tail begins at the line's first word (`propose_rule_trigger`'s `first_in_segment`, `note_config.py:2491`), so a longer line's trigger passes the opener. Without this note, Task 5.2's threat-model text could present the opener rule as a control over the residue. Triage: Fix-now; Fix route: fix-on-fast (plan text); Desired: Task 5.2's "Only with Lever B shipped" bullet says both paths stay open, and that the opener rule is the name heuristic, not a control on who spoke; /fix decision: Applied; /fix notes: dated sentences in Task 5.2 (first drafted as "the trigger does not pass through it"; corrected before the round closed, after re-reading `propose_rule_trigger`); siblings: none (Key Findings and Accepted Assumptions state the label rule, which stands); /fix date: 2026-11-21; /fix applied by: Claude Code
Fix-delta self-check: PASS — I re-read both applied hunks in Tasks 0.6, 4.3 and 5.2. No recorded figure, word, selection or decision changed, and the plan is still LF (no `\r` in the file).

### Round 17 — 2026-11-21
Round status: Closed
Source: Claude Code
Scope: the same as round 16 (Phase 2's diff on top of `9fb3777` and the scratch `sv-measure.py`), with round 16's plan-text fixes in. `/review-loop` round 2 of 3, executor leg sb3 (no Python run: verify=composer). No code or test changed since the composer's green runs (11176 passed, 9 skipped; self-test 56 passed).
Round 16's fixes, confirmed:
- MED-001: Task 0.6 says the frozen kept script is not run again on Phase 2's or a later product, and why. Task 4.3 says its mode does not exist yet, that its leg builds and hardens the built-row comparison first, and that neither frozen file is edited or run for it. Both match the dispatch (`sv-measure.py:2029–2031`) and the frozen premise.
- LOW-001: Task 5.2's sentences match the code. The phrase learner's opener rule runs at the real first word. The trigger's tail goes through the same filter, and the opener rule reaches it only when it begins at word 0 (`note_config.py:2491`).
Re-reviewed whole, with round 16's focus:
- B1-35 against D4, D9 and Task 0.7: the guard, the band's edges, the pass mark, additions only, `None` and -1, the shortcut and no-profile branches, the one call shared by both drivers, and today's clinician and number with the docstrings.
- The frozen items and no stored vector.
- The residue and its four pins.
- Task 2.2's mode and its self-test:
  - Check 2b builds the product's document through `assemble_transcript` and asserts 0 differences, including a relabelled match case (`[s1, s1, s1, s2, s2, s2, s1]`, R0 differing).
  - The whole-encounter check asserts R0 differs at segment 2 only and the built row equals the product.
  - `phase0_product` wraps only the frozen stitched module's checks.
  - So a product without the mark, or one with it in the wrong place, fails 2b.
- The tests and fakes.
Finding verification: 0 candidates; 0 dropped; 0 downgraded.
Round classification: 0 🆕 / 0 ⚡ / 0 🔁.
Missed-issue pass: re-read `sv-measure.py` :1366–1387 and :1694–1702, Tasks 0.6, 4.3 and 5.2 after the fixes, and `transcription.py` :991–1031; result: none.
Findings: none. The review has converged (no CRIT, HIGH or MED, and nothing left to apply).

### Round 18 — 2026-11-21
(Transcribed verbatim by executor leg sb4 from `.cursor/loops/stage-2-peer-r18.log`, the last `### Round 18` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 2 code peer review (stage-2.p1, peer round 1)
Status: Closed (0 pending)

Scope:

- job 1: checked B1-35 against D4, D9 and Task 0.7; the match and confirmation guards, inclusive 0.35/exclusive 0.50 band, preservation of practitioner labels, exclusion of `None`/-1, shortcut and no-profile exclusions agree (`transcription.py:1016–1031`, `1737–1747`). Traced empty, all-in-band, no-direct-match, boundary and trim cases; no defect found.
- job 2: checked shared assembly and both drivers; exactly one recovery call preserves the pre-recovery clinician and similarity (`transcription.py:1742–1744`). Live windows post pending labels; final assembly uses the shared function (`2331–2342`, `2822–2828`). No added transcript field or retained model vector. Named frozen functions and `speaker_eval.py` are unedited.
- job 3: checked downstream behavior through permitted consumer code and UI tests: ownership and omission handling, learning gates, speaker radio selection, and harness confirmation (`validation.py:3098–3122`). Both learning paths trust the clinician label; Task 5.2 truthfully records the residue and filter limitations. Answer-hop implementation itself was outside the permitted files, so that portion was limited to scoped consumer contracts rather than independently verified.
- job 4: checked all 20 added test cases statically; assertions detect band changes, missing guards, incorrect similarity recomputation, driver divergence, learning-gate failures and radio errors. Generated cases include exact band edges; explicit tests include adjacent floating-point values. Existing fakes are used; no forbidden shadow-exit operation is added.

Findings: none.

Verification: 11 files read; 4 jobs evidenced, with the job 3 limitation stated above. No files written, tests executed, scripts run or network accessed. Reported suite result: 11176 passed, 9 skipped; not independently rerun. Task 2.2’s measurement remains pending.

PEER-ROUND-18 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 19 — 2026-11-22
Round status: Closed
Source: Claude Code
Scope: Phase 4's scratch tooling (git-ignored, read whole):
- the new `.cursor/loops/sv_trace.py` (Task 4.1);
- the new `.cursor/loops/sv_stitch_product.py` (Task 4.3);
- `.cursor/loops/sv-measure.py`'s changes since leg sg1 began: the docstring, `--again`, the self-test registration (sections 12 and 13), `_trace_hooks` and the dispatch;
- the plan's Phase 4 lines.

`/review-loop` round 1 of 3, executor leg sg2 (no Python run: verify=composer). The primary baseline is `11c3827` (the scratch files are untracked; the tracked diff is the plan only). The composer's runs before this round: the self-test 70 passed, 0 failed; the five frozen hashes equal; `git diff --stat -- desktop/ scripts/ validation/ extension/` empty; the decode check exit 0, `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`, note path 0 executable changes. Read against C1, C4, C9, D2, D8, Task 0.6's print rules (its rounds 6 to 9) and Tasks 4.1 to 4.3.
Checked and clean:
- The stitched mode's print surface (C1, Task 0.6):
  - It prints numbers, the thirteen manifest names, part numbers, dialogue names, codes, the commit and four hashes.
  - It never prints the folder's path: the not-a-folder refusal is a fixed line, and a read failure names the file by its manifest name and the error by its type (`sv_stitch._read`).
  - It prints no word, because the tallies and the comparator read labels, spans and numbers only.
  - The manifest refusal names a stray file in the folder, as the frozen Task 0.5b mode did (`sv_stitch.stitched_mode`), which D6 accepted for the practitioner's own folder.
  - A failure inside `run_and_render` prints its type name only, exit 1.
- The refusals come before any audio is read, in this order: the channel, the folder, its listing, the manifest, the pins, git, crash reports, then the exclusion. Then the models load, and only then does `run_product` read a WAV. The self-test's nine refusal cases (ten after MED-001's fix) each assert no read and one line.
- Custody (C4, D2):
  - Each dialogue is decoded through the frozen `make_deps` decode: `transcribe_in_temporary_store(..., persist_key=False)`, the store destroyed after its pass. The self-test counts exactly 10 stores, all gone, and 1 left by the armed failure, also gone.
  - The decode's embedder is the plain one (`_no_capture`). The owner holds spectral features only and is cleared in `finally`.
  - The profile vectors (each part's, both P1s and the profile) sit in one `ProfileHolder` behind `vector_boundary`, cleared in `finally` on every path. The self-test's failure case finds every embedded vector unreachable.
  - Nothing is written: no `write_record` call, no file opened for writing.
- A real difference fails the comparison:
  - Take A's parts are compared exactly. Both sides call the product's `enrol` over the same captured audio (`enrol_part` wraps `enrol` with a recorder that returns the same float32 array), so 0.0 is the honest expectation, and a different capture, embedder or mean shows as `parts`.
  - P1 is compared within 1e-6: the product's `math.fsum` mean against numpy's, open point (5).
  - The dialogues: labels (the whole list), clinician and number are compared exactly with the row over the same decode's scores. The self-test's flipped-label and renumbered cases each report their one field.
  - The pools gate against Task 0.5b's pasted strings. On fakes they differ (code 1, `NOT EQUAL (pools)`) and equal the run's own figures.
  - The limits are compared per part with the frozen measurement's, and a changed cap or required flag shows.
- The decode check and the trace (Task 4.1, D8): the comparator covers every field D8 lists, and the probability-alone case is reported as exactly `words:probability`. The gate is checked: a clean tree, `desktop/` unchanged and the verified commit resolved. The trace refuses on any executable note-path change, and its must-pause kinds are the plan's two. The sides' stored clinician and number come from the record; a stored attribution that differs between R0 and the product is listed, not hidden.
- The frozen files are not edited. `sv-measure-kept.py` is imported by nothing in these modes and is not run.

Finding verification: 4 candidates; 1 dropped (the late refusal in `run_product`, raised while the part vectors exist, did not clear its frames: it is raised inside `vector_boundary(holder)`, which clears a failure's frames and the holder before it goes further); 0 downgraded.
Round classification: 3 🆕 / 0 ⚡ / 0 🔁.
Missed-issue pass: re-read `sv_stitch_product.py` whole, `sv_trace.py` :240–282 and :898–1085, `sv-measure.py` :134–141 and :2160–2240, and Task 0.6's loader (`sv-measure-kept.py` :278–339). Result: MED-001 and LOW-002.

#### MED-001: `.cursor/loops/sv-measure.py:139`, `sv_stitch_product.py` (the pin refusal), `sv_trace.py` (`scratch_hashes`) — the pin check reads the disk, not the bytes that ran
- Classification: 🆕 (leg sg1's open point (3))
- Triage: Fix-now; Fix route: fix-on-fast (scratch)
- Why it matters:
  - The frozen pair (`sv_lib.py`, `sv_stitch.py`; for the trace, `sv_lib.py` and `ffl_lib.py`) is imported by a plain `import`, which may run a cached `.pyc`. The pin check then reads each file from the disk again.
  - A cached `.pyc` that does not match its source, or a file changed between the import and the check, would run unchecked bytes under a check that passes. Python checks a `.pyc` by its source's mtime and size, not its content.
  - Task 4.3 is to be frozen "as Task 0.6's script was". That script ran each frozen file from bytes read once and checked (`load_modules`), so the check was of the code that ran.
- Desired behaviour: every scratch module these modes import runs from bytes read once, with the SHA-256 of those bytes kept on the module. The pin checks and the printed provenance read that digest. A module not loaded that way refuses.
- Pattern siblings: the trace's and the decode check's `scratch_hashes` (fixed with it); `--record-before`'s report hashes (they hash reports, not code: n/a).
- Scope-expansion disposition: n/a (scratch, Task 4.3's own hardening).
- /fix decision: Applied.
- /fix notes:
  - `sv-measure.py` installs, before its first scratch import, a meta-path finder for `sv_lib`, `sv_stitch`, `ffl_lib`, `sv_sets`, `sv_trace` and `sv_stitch_product`. Its loader reads each file once, keeps the SHA-256 of those bytes on the module (`__sv_ran_sha256__`) and executes exactly those bytes. No `.pyc` is read or written for them.
  - `ran_sha256(name)` gives that digest, or None for a module not loaded from its checked bytes in the scratch folder. `sv-measure.py`'s own digest is read at its start; Python's own read of it is the one just before (a residue, named in the leg sg2 bullet).
  - `sv_stitch_product`'s `Env` takes `ran_sha256` in place of `file_sha256` and `loaded_from`. It refuses a file at the wrong value or not checked, and its provenance says "the bytes that ran".
  - `sv_trace.scratch_hashes` imports each listed module first, then reads the digests, so `ffl_lib.py` is checked before the trace uses it.
  - The self-tests: the stitched-product check 1 asserts that the frozen pair's digests equal their pins in the running process, and its refusals gain "not-checked" and "own-not-checked". The trace's check 3 reads the real digests of `sv_lib.py`, `ffl_lib.py`, `sv_trace.py` and `sv-measure.py`. The check counts are unchanged (70).
- /fix date: 2026-11-22; /fix applied by: Claude Code

- **[LOW]** LOW-001: `.cursor/loops/sv_stitch_product.py` (`product_mode`) — outside `run_and_render`'s guard, the practitioner-run mode could print a traceback: from `real_env`'s imports, the exclusion's acquire or release, or the tables. A library's warning, a thread's uncaught exception or a finaliser's unraisable one would also be printed. Task 0.6's script silenced all four (its rounds 6 LOW-003 and 7 SEC-001), so that its run prints its tables and nothing else. Triage: Fix-now; Fix route: fix-on-fast (scratch); Desired: `product_mode` sets `threading.excepthook`, `sys.unraisablehook` and `warnings.showwarning` to a silent function first, and names any failure outside the inner guard by type only (exit 1); /fix decision: Applied; /fix notes: as desired, frames cleared first; not self-tested, because `real_env` is the real environment (the inner guard's path is check 5); /fix date: 2026-11-22; /fix applied by: Claude Code
- **[LOW]** LOW-002: `.cursor/loops/sv_trace.py` (`gate`), `sv-measure.py` (the trace's dispatch) — the gate held only `desktop/` unchanged since the verified commit, and `--trace` took any `--config` folder. The trace composes every note with that config. A changed cue file after the verified commit, or another folder, would trace at a configuration the verified commit never had, and the record would not say so. Triage: Fix-now; Fix route: fix-on-fast (scratch); Desired: the gate also holds `validation/` unchanged; `--trace` refuses a `--config` other than the repository's `validation/config`; /fix decision: Applied; /fix notes: `GATED_PATHS = ("desktop", "validation")`. The gate's refusal names the folder (`validation-changed-since-verified:N`). The fake git filters by folder, and the trace's check 3 gains "config-moved" and "plan-only". `git diff --stat 4c29283 HEAD -- validation desktop scripts extension` is empty today, so the decode check's verdict is not expected to move; /fix date: 2026-11-22; /fix applied by: Claude Code

Fix-delta self-check: PASS.
- I re-read every applied hunk. No measured figure, comparison rule, bar or printed table changed. What changed are the refusals: a pin is now the bytes that ran, and the gate now covers `validation/` and the trace's config.
- `SELF_TEST_CHECKS` stays 70: the new assertions are inside existing checks.
- The plan is LF.

### Round 20 — 2026-11-22
Round status: Closed
Source: Claude Code
Scope: the same as round 19 (`sv_trace.py`, `sv_stitch_product.py`, `sv-measure.py`'s new modes and the plan's Phase 4 lines), with round 19's fixes in. `/review-loop` round 2 of 3, executor leg sg3 (no Python run: verify=composer). The composer's runs after round 19's fixes: self-test 70 passed, 0 failed; the five frozen hashes unchanged; with the plan committed as `72f857a` and the tree clean, the decode check exit 0 (`[provenance] sv_lib.py … (frozen: equal)`, the same note-path lines, `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`); the `--config desktop` smoke refused with its one line, exit 2.
Round 19's fixes, confirmed:
- MED-001: the checked loader (`sv-measure.py` :142–196) is in place before the first scratch import. Every module these modes import (`sv_lib`, `sv_stitch`, `ffl_lib`, `sv_sets`, `sv_trace`, `sv_stitch_product`) runs from bytes read once and carries their SHA-256, and `ran_sha256` refuses a module from another folder or one not loaded that way.
  - The green self-test is the evidence the loader works. Every one of those modules ran through it, and the stitched-product check 1 asserted `sv_lib.py` and `sv_stitch.py` at their pins as they ran.
  - The decode check's provenance line now reads the ran digest and still says `frozen: equal`.
- LOW-001: `product_mode` installs the three quiet hooks and wraps the environment and the run.
- LOW-002: the gate's `validation` path and the trace's `--config` rule, shown by the refusal smoke.

Re-reviewed whole, with the composer's focus:
- C1 and Task 0.6's print rules for the stitched mode, unchanged from round 19.
- D2's custody.
- The comparisons failing on a real difference.
- The frozen files imported only by the checked load, and never edited (the hashes are unchanged).
- The two open points:
  - The outer guard's untested path: LOW-002 below.
  - The digest-at-start residue. `sv-measure.py`'s own digest is a read of its file at its start, not of the bytes Python compiled for `__main__`. No sound check closes it inside the file: a file cannot pin its own hash, and a script's source bytes are not kept by the interpreter. Comparing a recompiled code object with the running one is not dependable across the adaptive interpreter. It stays a named residue, and the freeze's hash check just before the practitioner's run covers it, as for Task 0.6's `sv-measure-kept.py`.

Finding verification: 2 candidates; 0 dropped; 0 downgraded.
Round classification: 2 🆕 / 0 ⚡ / 0 🔁 (both outside round 19's fix hunks; neither is caused by them).
Missed-issue pass: re-read `sv_trace.py` :542–882 (the comparator, the decode check, the rebuilt document, the placements, the flags, `evaluate_side` and `compare`) and `sv_stitch_product.py`'s mode and refusal paths. Result: LOW-001 and LOW-002.

- **[LOW]** LOW-001: `.cursor/loops/sv_trace.py` (`evaluate_side`) — only the harness's replay was guarded. The scratch composition of a role-unresolved side, the next-patient boundary and the script alignment ran outside the guard. A failure in any of them would end the whole trace with a traceback and no `trace-<stages>.json`, which loses an overnight gate run, instead of counting that side as `error:<Type>` (exit 1). Triage: Fix-now; Fix route: fix-on-fast (scratch); Desired: the whole side is inside the one guard; /fix decision: Applied; /fix notes: the body after the replay moved inside the `try`. Check 7 gains "after-replay-failure": a replay whose outcome is role-unresolved, with the scratch composition's clock missing, gives the side `error:AttributeError` with `not evaluated` = `error`; /fix date: 2026-11-22; /fix applied by: Claude Code
- **[LOW]** LOW-002: `.cursor/loops/sv_stitch_product.py` (`product_mode`) — round 19 LOW-001's outer guard and quiet hooks had no test (leg sg2's open point), because `product_mode` built the real environment inline. Triage: Fix-now; Fix route: fix-on-fast (scratch); Desired: the guard and the hooks are separate functions, each exercised; /fix decision: Applied; /fix notes: `install_quiet_hooks()` and `guarded_run(folder, make_env, hooks, expected, emit)`; `product_mode` calls them with `real_env`. Check 5 gains three cases:
  - an environment that fails to build gives exactly one `[error] … (ImportError)` line, exit 1;
  - a refusal whose exclusion release raises prints its refusal line, then `[error] … (ArithmeticError)`, exit 1;
  - the three hooks are `_quiet` once installed, and are restored after the check.
  /fix date: 2026-11-22; /fix applied by: Claude Code

Fix-delta self-check: PASS.
- I re-read both applied hunks. No figure, comparison, bar, refusal order or printed table changed: a guard's reach and its test only.
- `SELF_TEST_CHECKS` stays 70: the new assertions are inside checks 5 and 7. The plan is LF.

### Round 21 — 2026-11-22
Round status: Closed (the cap; MED-001 fixed, its confirm is the codex peer pass)
Source: Claude Code
Scope: the same as rounds 19 and 20, with round 20's fixes in. `/review-loop` round 3 of 3, executor leg sg4 (no Python run: verify=composer). The composer's runs after round 20's fixes: self-test 70 passed, 0 failed, with no line other than `[ok]` and detail lines; the five frozen hashes unchanged.
Round 20's fixes, confirmed:
- LOW-001: `evaluate_side`'s whole body is inside the one guard, and the trace's check 7 "after-replay-failure" passed (a role-unresolved replay whose scratch clock is missing gives `error:AttributeError`).
- LOW-002: `install_quiet_hooks` and `guarded_run` are separate, and `product_mode` calls both. The stitched-product check 5's three new assertions passed (an environment that fails to build, a release that raises after a refusal, the hooks installed and restored).

Re-reviewed whole, with the composer's focus. The stitched mode's print surface, refusal order, custody and comparisons are unchanged since round 19's review (no hunk of round 20 touched them). The checked load is unchanged. This round went deeper into the note-path check (`sv_trace.py` :288–560): its reach, its docstring rule and its seeds, against what the trace's replay really calls.

Finding verification: 1 candidate; 0 dropped; 0 downgraded.
Round classification: 1 🆕 / 0 ⚡ / 0 🔁 (present since leg sg1; not caused by a round 19 or 20 fix).
Missed-issue pass: re-read `sv_trace.py` :288–560 and `ffl_lib.py`'s package imports and calls (:101–136 and its `validation.`, `ui_models.` and `align_segments` uses). Result: MED-001.

#### MED-001: `.cursor/loops/sv_trace.py` (`note_path`, `_strip_docstrings`) — the note path's reach was seeded only from the harness's entry points, not from what the scratch replay itself calls
- Classification: 🆕 (present since leg sg1)
- Triage: Fix-now; Fix route: fix-on-fast (scratch)
- Why it matters:
  - D8's note-path check exists so that Before (R0's labels on today's code) stands for the Phase 0 product: every package definition the replay runs must be unchanged since Phase 0, or the trace is refused (a must-pause).
  - The reach started from `REPLAY_SEEDS` (eleven validation and stage-builder names) and the eight whole note modules. But the replay runs through the frozen `ffl_lib.py`, which also calls package functions directly: `speaker_eval.align_segments`, `ui.models._flagged_end`, `_segment_line`, `_reply_turn`, `omission_anchors`, `flagged_runs`, `flagged_segments`, `note_check._omission_flag_token`, and `validation`'s metric, judging and alignment helpers. The trace's own `sv_trace.py` adds `next_patient_boundary`, `reference_tail_start` and the stage builders.
  - A change to one of those unreached names would leave the check at "0 executable changes" while the replay ran changed code: a gate that could pass a change it exists to catch.
  - For the verified commit the outcome is not expected to move. The files changed since Phase 0 (`git diff --stat 8bedfc4 4c29283 -- desktop/src`) are enrolment, note (a docstring), speaker_embedding, transcription, ui/models, ui/note and ui/practitioner, and of their changed definitions `ffl_lib.py` imports only ones whose change is a docstring (`note.spoken_by_confirmed_clinician`, Task 1.4's wording, and the transcript classes, if their docstrings moved). The decode check's rerun will show it: any name it lists is read before anything else.
  - A sibling found while fixing: `_strip_docstrings` left out only each body's FIRST string. A field docstring later in a class body (a no-op) would have counted as an executable change once the wider seeds reach such a class, which would be a false refusal.
- Desired behaviour: the reach is seeded too from every package name `ffl_lib.py` and `sv_trace.py` refer to (their imports, names and one-level `module.name` uses), read from the bytes that ran. Every bare string statement in any statement list is left out.
- Pattern siblings: the seeds' completeness for the decode check itself. It replays nothing; its note-path result is the trace's gate, so it gets the same seeds.
- Scope-expansion disposition: n/a (scratch, Task 4.1's own tooling; it changes no measured figure and no printed table, and can only add refusals).
- /fix decision: Applied.
- /fix notes:
  - `scratch_seeds(show, commit, texts)` parses each scratch module with the package's sources at that commit (`_WithScratch`) and takes every package (module, name) it refers to through the same `_references` rule. `note_path(..., scratch=)` adds them to the seeds, and both commits are reached from the same seeds.
  - `prepare` reads `ffl_lib.py` and `sv_trace.py` (`REPLAY_SCRATCH`) and refuses unless each file's SHA-256 equals the digest of the bytes that ran. So `DECODE_CHECK_FILES` now includes `ffl_lib.py` (pinned) and equals `TRACE_FILES`.
  - `_strip_docstrings` drops every bare string statement from every `body`, `orelse` and `finalbody`.
  - The trace's check 4 gains three assertions: a later bare string is not a change; a scratch module's `helpers.unused(x)` seeds `helpers:unused`; so does `from … import unused`. `SELF_TEST_CHECKS` stays 70.
  - The `sv-measure.py` docstring is updated.
- /fix date: 2026-11-22; /fix applied by: Claude Code

Fix-delta self-check: PASS.
- I re-read the applied hunks. The fix can only widen what the check reaches; it moves no figure, bar, comparison or table. The decode check's refusal list gains one line (the scratch replay's source not being the bytes that ran).
- The plan is LF.

Cap: this is round 3 of 3. The review reached its cap with MED-001 fixed and not confirmed by a further round of mine. Per the leg's instruction, the codex peer pass that follows is the confirm, and the composer records the cap transition.

### Round 22 — 2026-11-22
(Transcribed verbatim by executor leg sg5 from `.cursor/loops/stage-4-peer-r22.log`, the last `### Round 22` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 4 tooling peer review (stage-4.p1, peer round 1)
Status: Open (2 pending)

Scope:

- job 1: checked stitched output, refusals, exception guards and quiet hooks; guarded failures report types, expected refusals use controlled text, and the self-test restores all three hooks (`sv_stitch_product.py:691–723,996–1001`). No confirmed disclosure defect.
- job 2: checked refusal order, audio custody and vector cleanup; preflight refusals precede audio reads, decoding uses the encrypted temporary store with `persist_key=False`, and boundaries/finally blocks clear owners and exception frames.
- job 3: checked scratch loading and pins; modules execute the same bytes whose digest is retained (`sv-measure.py:164–170`). Both trace modes pin `ffl_lib.py`; replay-source reads must match the executed digest (`sv_trace.py:967–985`). Round 21’s changes are present.
- job 4: checked product-versus-scratch comparisons, decode fields, checkout gates and note-path analysis; probability-only differences are detected and stitched comparisons cover the required fields. Found the import-binding and retry defects below.
- job 5: checked per-side trace failures, configuration restriction and recorded fields; errors remain counted while processing continues, configuration is restricted to repository `validation/config`, and records contain synthetic placements, codes and metrics without vectors.
- job 6: checked scope and supplied verification evidence; Git status is clean, and only the plan differs from `4c29283`. The requested product/scripts/validation/extension diff is empty. Frozen-file equality is accepted from supplied evidence; no kept-recording script was invoked. Reviewed fixtures use synthetic inputs.

Findings:

- **PR-MED-4501** (MED, regression verification, `.cursor/loops/sv_trace.py:454`): The note-path gate can miss an executable change made solely by rebinding an imported dependency. Reproduction: in the existing synthetic note/helper fixture, change the caller’s import to alias another already-existing helper with different behaviour, leaving the caller and both helper definitions unchanged. Reachability includes both target definitions, but omits the caller’s local import binding; comparing their unchanged definitions therefore reports no executable change. Evidence: `"found.add((target[0], target[1]))"` bypasses the local alias, while whole-module seeding uses `"pending.extend((module, name) for name in info.defs)"` (`:478`). Although `dumps` can compare aliases (`:571–572`), this binding never reaches it. Recommendation: Fix-now - Include used import bindings in the compared reach and add an import-only rebinding regression case.

- **PR-MED-4502** (MED, retry correctness, `.cursor/loops/sv-measure.py:1194`): A failed `--again` attempt can report success using the previous run’s records. Reproduction: retain a complete successful run at the same clean HEAD, request `--again`, and make an enrolment WAV unavailable or invalid. Encounter inventory checks pass, but enrolment fails; the handler clears only the temporary attempt and continues. The final summary reads the older complete record and can return zero despite no retry decode occurring. Evidence: `"_clear_folder(part)"` followed by `"continue"` (`:1196–1197`); later, `"summary_record = _read_json(run)"` and `"complete_sets += bool(summary_record.get(\"complete\"))"` (`:1263–1266`) feed the success return at `:1271`. Recommendation: Fix-now - Track failures of the current attempt and prevent previous records from satisfying completion for a requested retry.

Verification:

- Files read: 15 unique scoped files.
- Jobs evidenced: 6/6.
- Findings verified statically: 2 MED.
- Supplied results: 70 self-tests passed; zero decode differences across 7/7 sets.
- No scripts, tests, network commands or writes performed.

PEER-ROUND-22 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 0).

Executor verification and /fix (leg sg5, 2026-11-22):
- PR-MED-4501: verified, MED as labelled.
  - The peer is right. In `_references`, a used module-level alias added only its target `(target module, name)`, never the binding `(module, local name)` itself. And `reach` seeded a whole module from its definitions only.
  - So `from scribe_desktop.helpers import unused as used`, in place of `import used`, reached two unchanged helpers and compared no binding. The result was 0 executable changes for a call that now runs other code.
  - /fix decision: Applied.
  - /fix notes:
    - A used name resolved through a module-level alias (not a function's own import, which is inside the definition's dump) also adds the binding `(module, name)`. A module alias used as `module.attr` is covered too, because its `Name` node is visited.
    - A whole note module's import bindings are seeded with its definitions.
    - `dumps` compares a binding as its `(module, name)` target, so a rebinding is an executable change of the caller's module binding.
    - The trace's check 4 gains "import-rebinding": note's `import WORDS, used` becomes `import WORDS, unused as used`, with the caller and both helpers unchanged. Expected: exactly `scribe_desktop.note:used`. Without the fix that case reports none.
    - The other check 4 cases are unchanged by the fix, because their bindings are identical at both commits.
  - /fix date: 2026-11-22; /fix applied by: Claude Code
- PR-MED-4502: verified, MED as labelled.
  - A set whose enrolment WAV fails clears its attempt and `continue`s. The summary then reads `root/<set>/run.json`, which still holds the previous complete run at that HEAD, so the exit could be 0 with no decode made.
  - The same holds for a re-run from a dirty tree, which never skips a set. A run without `--again` at a clean HEAD skips a complete set, so it cannot reach this.
  - /fix decision: Applied.
  - /fix notes:
    - `against_product_mode` keeps the sets whose attempt failed in this run (`failed`).
    - The summary is now `against_product_summary(root, sets, failed)`, which counts such a set as not complete whatever an older record says. The totals line adds `attempts failed N`, and the exit is 0 only with no failed attempt.
    - The older records are kept: they are a complete earlier run at the same commit, and the decode check still reads their differences.
    - Check 2b gains "summary:older-complete" (an older complete record counts, `(0, 1, 0)`) and "summary:failed-attempt" (the same record with that set's attempt failed counts as not complete, `(0, 0, 0)`).
  - /fix date: 2026-11-22; /fix applied by: Claude Code
- Neither fix changes a measured figure, a comparison or a printed table beyond the totals line's new count. `SELF_TEST_CHECKS` stays 70 (the new assertions are inside checks 2b and the trace's check 4). The plan is LF. Peer round 23 is the confirm.

### Round 23 — 2026-11-22
(Transcribed verbatim by executor leg sg6 from `.cursor/loops/stage-4-peer-r23.log`, the last `### Round 23` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 4 tooling peer review (stage-4.p1, peer round 2)
Status: Open (2 pending)

Scope:

- job 1: checked stitched refusals, exception handling, interrupts and quiet hooks. Measurement failures are reported by type; the self-test restores the three hooks. Found an unguarded startup-import path below.
- job 2: checked refusal order, encrypted-store custody and vector cleanup. Preflight checks precede audio reads; decoding uses `persist_key=False`; temporary-store teardown, owner clearing and chained traceback-frame clearing cover measurement failures.
- job 3: checked module loading and pins. Imported scratch modules execute the same bytes hashed by the loader (`sv-measure.py:164–170`); both trace modes pin `ffl_lib.py`, and replay-source reads must match executed digests. The main script’s separately read digest remains the explicitly accepted residue.
- job 4: checked capture limits, per-part embedding, equal-weight combination, batch-driver attribution, decode comparisons and checkout gates. Probability-only changes are detected. Found a remaining executable-change gap in the note-path gate below.
- job 5: checked trace error handling, configuration restriction and recorded data. Side failures are counted while processing continues; configuration is restricted to repository `validation/config`; the trace writes identities, codes and synthetic metrics without vectors.
- job 7: checked both round 22 fixes. Used import bindings now reach comparison; unchanged bindings compare equal. Failed attempts are excluded from completion and prevent exit 0. The new import-rebinding and failed-attempt assertions would fail without their respective fixes.
- job 6: checked scope and supplied results. Git status is clean; only the plan differs from `4c29283`; the requested product/scripts/validation/extension diff is empty. Frozen-file equality is supported by supplied evidence. No kept-recording script was invoked; reviewed fixtures are synthetic.

Findings:

- **PR-MED-4601** (MED, regression verification, `.cursor/loops/sv_trace.py:583`): The note-path gate ignores executable module-level statements in dependencies reached through individual definitions. Reproduction: extend the existing synthetic helper fixture with a module-level conditional that rebinds the used helper to the already-existing alternative implementation, leaving both function definitions and the caller’s import unchanged. The helper module’s `other` statements change, but it is not in `whole_modules`, so the checker reports no executable change although the caller’s behaviour changes. Evidence: `"result.other.append(_dump(statement))"` (`:421`); reach starts with `"whole_set = set(whole)"` (`:479`), and module statements are compared only under `"for module in sorted(whole_modules | old_whole):"` (`:583`). Recommendation: Fix-now - Compare executable initialization affecting reached dependencies, conservatively refusing unanalysed module-level changes, and add a conditional-rebinding regression case. This does not establish that the supplied zero-difference result is wrong.

- **PR-LOW-4601** (LOW, output containment, `.cursor/loops/sv-measure.py:2233`): The stitched mode imports its implementation before installing quiet hooks or entering its outer guard. A missing dependency or import failure therefore prints an unrestricted traceback and exception message instead of the prescribed fixed failure line. Reproduction: make an imported dependency unavailable and launch the stitched-product mode; failure occurs before `product_mode` is entered. Evidence: `"import sv_stitch_product"` (`:2233`) precedes the call to `product_mode` (`:2235`); `"install_quiet_hooks()"` and `"return guarded_run(...)"` occur only inside that function (`sv_stitch_product.py:718,723`). Recommendation: Fix-now - Establish the stitched startup guard and quiet hooks before mode-specific imports, and test an import failure. This path occurs before audio reads; no audio disclosure was established.

Verification:

- Files read: 15 unique scoped files.
- Jobs evidenced: 7/7.
- Findings verified statically: 1 MED, 1 LOW.
- Supplied results: 70 self-tests passed, 0 failed; 0 decode differences across 7/7 sets.
- No scripts, suites, network commands or writes performed.

PEER-ROUND-23 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1).

Executor verification and /fix (leg sg6, 2026-11-22):
- PR-MED-4601: verified, MED as labelled.
  - A module reached through one definition (`helpers` through `used`) had its non-definition statements dumped into `other` but compared only for the whole note modules. So `if True: used = unused` in `helpers` changed what `used` names while every compared definition stayed equal.
  - /fix decision: Applied, conservatively as the composer asked: an unanalysed module-level change in a reached module counts, never passes.
  - /fix notes:
    - The module statements are compared for every package module the replay reaches (any module of a reached `(module, name)`), and for each package above it, whose `__init__` runs at import.
    - A name bound inside a module-level compound statement (`if`, `try`, `with`, a loop) is filed under that whole statement. The statement is followed and compared for that name, and its imports resolve names.
    - Trace check 4 gains "conditional-rebinding" (`helpers:<module statements>` counted).
  - /fix date: 2026-11-22; /fix applied by: Claude Code
- PR-LOW-4601: verified, LOW as labelled.
  - `main` imported `sv_stitch_product` before `product_mode` installed its hooks and guard. So did `sv-measure.py`'s own package imports at the top of the file, which every mode runs.
  - An import failure printed Python's traceback and message. That happens before any audio read and holds no folder path, but it is not the run's fixed line.
  - /fix decision: Applied.
  - /fix notes:
    - At the top of `sv-measure.py`, before any package or scratch import, a run whose arguments hold `--stitched` and `--against-product` sets `sys.excepthook` to a type-only line and silences thread exceptions, unraisables and warnings. The parser now takes no abbreviations (`allow_abbrev=False`), so that check reads the exact flags.
    - In `main`'s branch the hooks are set again, and the mode's import and `_stitch_hooks()` sit under a type-only guard (exit 1).
    - The other modes keep Python's tracebacks.
    - Check 13 gains the flag predicate (four cases), the hook's line (no message text), and an import failure through `main` (exit 1 and exactly the type-only line), with the hooks restored after.
  - /fix date: 2026-11-22; /fix applied by: Claude Code

The note-path gate looked at once as a whole (the composer's step 2): five more ways the reached code could change while the compared definitions do not. Each is closed in this leg, and each has a check 4 case:
- (s1) A module-level assignment to an attribute or a subscript (`os.environ[...] = …`, `REGISTRY[key] = f`) was filed under its base name and compared only if that name was reached. It is now a module statement (`_binds_names_only`). Case: "subscript-assignment".
- (s2) A definition or an import nested in a module-level `try` or `if` was neither followed nor resolvable. Its names are now filed under the statement, and its imports resolve names (`_nested_bindings`). Case: "nested-definition".
- (s3) A package's `__init__` statements, which run on every import of its modules, were never compared. Every reached module's parent packages are now compared. Case: "package-init".
- (s4) A module imported only for its side effect (`import scribe_desktop.patch`) bound only `scribe_desktop`, and its own statements were never compared. `ModuleInfo.imported` now keeps every imported module's full name, and the statements of the reached modules' whole package-import closure, at either commit, are compared. Case: "side-effect-import".
- (s5) A data file the note path reads at run time (the shipped `config_defaults/*.json`: lexicon, connectives, cues, prefill, autofill; the harness's `validation/config`) could change between Phase 0 and the verified commit with no definition changing. `prepare` now lists every non-Python file changed under the package and `validation/config` between the two commits as an executable `<data file>` change, and a failed diff counts as one. Case: "data-file". (`git diff --stat 8bedfc4 4c29283 -- desktop/src` lists only `.py` files, so none is expected.)
- Also fixed, though no package code uses it: `_absolute` resolved a relative import inside a package's `__init__` one level too high. Case: "relative-imports". The package has no relative import today.
- Recorded as residues, not analysed:
  - access by a string: `getattr` with a computed name, and `importlib` (in the package only `ml_warmup.py` uses it, which is off the note path);
  - the third-party libraries' versions in the venv, which no commit records. The decode check covers the recogniser end to end, and both trace sides run on the same libraries.

What it costs: the gate is wider, so a real but harmless module-level change in a reached module, an imported module or a parent package now refuses the trace, by name. Which way it errs is the composer's instruction: it counts, never passes. No measured figure, comparison, bar or printed table changed; the decode check's note-path line can only list more names. `SELF_TEST_CHECKS` stays 70 (the new assertions are inside the trace's check 4 and `sv-measure.py`'s check 13). The plan is LF. Peer round 24 is the confirm.

### Round 24 — 2026-11-22
(Transcribed verbatim by executor leg sg8 from `.cursor/loops/stage-4-peer-r24.log`, the last `### Round 24` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 4 tooling peer review (stage-4.p1, peer round 3)
Status: Open (2 pending)

Scope:

- job 1: checked stitched output, refusals, exception guards, interrupts and quiet hooks. Measurement and environment failures use type-only reporting; self-tests restore hooks. Startup imports are now guarded. Argument-parser errors retain a path-disclosure route, reported below.
- job 2: checked preflight refusals, encrypted-store custody and vector cleanup. Preflight checks precede audio reads; dialogue decoding uses `persist_key=False`; teardown and vector boundaries cover failure paths, including chained traceback frames (`sv_stitch.py:802`, `sv_lib.py:305`, `sv_stitch_product.py:418,662`).
- job 3: checked scratch loading, executed-byte digests and frozen pins. The loader hashes and executes the same bytes; both trace modes include `ffl_lib.py`; subsequent replay-source reads must match the executed digest (`sv-measure.py:207–209,2265`, `sv_trace.py:1111`). The main script’s separate digest read remains the recorded residue.
- job 4: checked capture limits, per-part embedding, equal-weight combination, batch attribution, decode fields and checkout gates. Required comparisons are present, including probability-only differences. The clean-tree gate covers both `desktop/` and `validation/`. A remaining note-path dependency gap is reported below.
- job 5: checked per-side trace failures, configuration restriction and written fields. Side errors are counted while processing continues; configuration must resolve to repository `validation/config`; recorded results contain synthetic identities, codes and metrics without vectors (`sv_trace.py:982,1276,1287`, `sv-measure.py:2355`).
- job 7: checked round 23’s fixes and all five sweep cases. Direct module-statement changes, nested definitions, package initialization, side-effect imports and data-file changes have corresponding checks. The import-failure assertion correctly expects `ModuleNotFoundError`. The initialization comparison still misses dependencies called only during module initialization. Round 22’s import-binding and failed-attempt fixes remain present.
- job 6: checked scope and supplied verification evidence. Git status is clean; only the plan differs from `4c29283`; the requested product/scripts/validation/extension diff is empty. Frozen-file equality is supported by supplied evidence. No kept-recording script was invoked; inspected fixtures are synthetic.

Findings:

- **PR-MED-4701** (MED, regression verification, `.cursor/loops/sv_trace.py:704`): Module initialization is compared syntactically without following its executable dependencies, so changed initialization behaviour can still pass the note-path gate. Reproduction: extend the synthetic helper fixture at both revisions with an initialization helper and an unchanged module-level call to it. Change only that helper’s body so it rebinds the used function to the existing alternative. The used function, caller, imports and module-level call remain identical; the initializer is not reached, so its changed body is never compared. This requires neither computed-name lookup nor a third-party change. - Evidence: reach follows references only through `"for statement in info.defs[name]:"` and `"pending.extend(_references(module, statement, info, source))"` (`:592–593`); initialization comparison uses only `"if (None if a is None else a.other) != (None if b is None else b.other):"` (`:704`). Recommendation: Fix-now - Include initialization dependencies in reachability, conservatively refuse unanalysed initialization changes, and add a regression case where only the initializer’s body changes. This does not establish that the supplied decode result is wrong.

- **PR-LOW-4701** (LOW, output containment, `.cursor/loops/sv-measure.py:2301`): Stitched-product argument errors can print the measurement-folder path through argparse’s standard diagnostics. Reproduction: supply the valid stitched-product options but accidentally repeat the folder as an extra positional argument; argparse prints that path as an unrecognized argument before exiting. Quiet exception hooks do not intercept argparse’s direct stderr output or `SystemExit`. - Evidence: `"parser = argparse.ArgumentParser("` (`:2280`) uses the standard error handler, and `"args = parser.parse_args(argv)"` (`:2301`) executes before the stitched branch’s controlled refusals. Recommendation: Fix-now - Give stitched-product parsing a fixed, argument-free refusal line and test malformed arguments with a synthetic private-path sentinel. This occurs before audio reads; no audio-derived disclosure was established.

Verification:

- Files read: 15 unique scoped files.
- Jobs evidenced: 7/7.
- Findings verified statically: 1 MED, 1 LOW.
- Supplied results: 70 self-tests passed, 0 failed; zero decode differences across 7/7 sets.
- No scripts, suites, network commands or writes performed.

PEER-ROUND-24 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1).

Executor verification and /fix (leg sg8, 2026-11-22):
- PR-MED-4701: verified, MED as labelled. Tuple: (`sv_trace.py` `reach` / `note_path`, MED, verified, fix-now).
  - Round 23's fix compared a loaded module's statements as text but followed nothing they call. An unchanged `_init()` call whose `_init` body changes, a decorator, a default argument or a base class could change the note path with every compared dump equal.
  - /fix decision: Applied, closing the class (import-time code), not the instance.
  - /fix notes:
    - Every loaded module's import-time code is now a root of the reach. "Loaded" means a whole note module, the module of any reached name, a parent package, or the import closure; a module loaded at either commit counts at both, in a fixpoint.
    - What that code RUNS is followed in full: its whole definition is compared and everything it refers to is followed. That covers a callee and its arguments, a decorator, a base class or metaclass, an iterated, entered, raised, formatted or hashed value, and an assignment or deletion through an attribute or a subscript. The module statements' references are followed this way too.
    - What it only TOUCHES is followed as far as touching can run code. A name in a type alias such as `Callable[[], LiveTranscriber | None]` is touched. For a touched class, its bases and metaclass are followed in full, and so is the class itself if it defines `__class_getitem__` or has a decorator other than `dataclass`. A touched function counts only if it is decorated. A touched value has its own making re-followed.
    - A top-level definition that is not inert is compared whole. "Inert" is a strict grammar:
      - a function with only `property`, `staticmethod` or `classmethod` as decorators and inert defaults;
      - a class with no base or keyword, only standard `dataclass` decorators, and a body of literal fields and inert methods;
      - an assignment of literals, names, literal containers or calls of a fields-only data class.
      Annotations count as code unless the module has `from __future__ import annotations` (and, inside a class with a base, always). An inert definition only binds its names, so a change to it matters only to a reader by name, which the reach already follows.
    - Check 4 gains seven cases, each over a synthetic helper whose module-level code is identical at both commits:
      - "initializer-body" (the peer's reproduction: `_init()` unchanged, only `_init`'s body rebinds `used`, counted as `helpers:_init`); fails without the fix;
      - "decorator-body" (`@register`, `register`'s body changed: counted); fails without the fix;
      - "default-argument" (`def later(x=make())`, `make`'s body changed: counted); fails without the fix;
      - "class-getitem" (`KINDS = Box[int]`, `Box.__class_getitem__` changed: exactly `helpers:Box`); fails without the fix;
      - "touched-class" (`KINDS = list[Box]`, a method body changed: clean). This guards against over-counting: the shape of `ui/models.py`'s `LiveTranscriberSource`, which names `LiveTranscriber`, whose `LiveResult.assemble` calls Phase 2's changed `assemble_transcript`;
      - "inert-additions" (Phase 1's shape: a frozen data class, a tuple of its instances from literals, a dict, a negative constant, a function with a name default, a class with `@property`, `__all__`: clean);
      - "non-inert-addition" (`TABLE = Part(key=str(1))`: exactly `helpers:Part` and `helpers:TABLE`).
  - Phase 1's and Phase 2's additions and the verified commit: by the grammar, every top-level addition in the changed files is inert. In `ui/models.py`: `EnrolmentPart`, `ENROLMENT_SCRIPT`, `ENROLMENT_PART_NAMES`, the `ENROLMENT_*` lines and the `enrolment_*` functions. In `enrolment.py`: `PART_CONSISTENCY_FIGURE`, `PartEmbedding`, `_SegmentVectorRecorder` with its `@property` methods, and the five functions. In `speaker_embedding.py`: `RECOVERY_MARK`. In `transcription.py`: `recover_practitioner_labels`. Every `__all__` is inert too.
    - So none is a root. They are reached only from the Practitioner tab's methods, and from `assemble_transcript`, which the replay does not run (it reads Task 2.2's stored labels). They are therefore not on the note path, which is D8's reading too: D8 names only `ui/models.py`'s composition helpers.
    - The decode check should still read 0 executable. The one existing import-time name I found that leads towards changed code, `LiveTranscriberSource`, is touched-only (the "touched-class" case).
    - Not run here (verify=composer). If the composer's run lists any name, it comes to me: either a real import-time dependency (D8's must-pause) or an over-inclusion that the gate keeps counting until it is shown not to run.
  - What the gate now guarantees: between the Phase 0 commit and the verified commit, no package code changed among
    - the definitions the replay reaches by name (from the harness entry points, the two stage builders, the whole note modules and the scratch replay's own uses);
    - the import-time code of every module loaded on the way (its statements, its non-inert definitions and everything those run);
    - the import bindings, and the data files under the package and `validation/config`;
    except the listed wording constant and docstrings, bare strings and comments.
  - Residues, not analysed:
    - access by a computed name (`getattr`, a star import reading `__all__`, `globals()`, `importlib`; the package has no star import, `globals()` or `__getattr__` today, and `importlib` only in `ml_warmup.py`);
    - what standard-library and third-party code does with the objects it is given, for example a library calling a passed function later;
    - the trust that a name load, a literal and a standard `dataclass` decoration run no package code;
    - the third-party libraries' versions.
  - Over-inclusion, on the safe side: a definition that is run, or not inert, is compared whole, method bodies included. A body change that never runs at import can therefore still count, by name.
  - /fix date: 2026-11-22; /fix applied by: Claude Code
- PR-LOW-4701: verified, LOW as labelled. Tuple: (`sv-measure.py` `main`, LOW, verified, fix-now).
  - argparse's `error()` writes the usage and its message, which can quote an argument such as the folder given twice, to stderr. It then raises `SystemExit`, before the stitched branch's controlled refusals and outside the type-only hook. A mistyped `--against-product` has the same route, because the start-up check then does not see the mode.
  - /fix decision: Applied.
  - /fix notes:
    - The parser is `_QuietParser`, whose `error()` raises a private exception (chained from nothing). `main` prints one fixed line, `ARGUMENTS_REFUSED_LINE` ("[refused] the arguments could not be read (none is shown); give them as the plan's command shows"), and returns 2.
    - Every mode parses this way, so the mistyped-flag route is closed too. `--help` is unchanged.
    - Check 13 gains "parse-refused", with a synthetic private-path sentinel (`C:/sv-private-sentinel/measurement`). It covers the folder repeated and the flag mistyped: exit 2, exactly the fixed line on stdout, nothing on stderr, and no sentinel text on either stream. Without the fix, argparse would print the sentinel and raise `SystemExit`.
  - /fix date: 2026-11-22; /fix applied by: Claude Code

No measured figure, comparison, bar or printed table changed. The decode check's note-path line can list different names only if real import-time dependencies changed, and the parser change affects only malformed commands. `SELF_TEST_CHECKS` stays 70: the new assertions are inside the trace's check 4 and `sv-measure.py`'s check 13. The plan is LF. Peer round 25 is the confirm.

### Round 25 — 2026-11-22
(Transcribed verbatim by executor leg sg9 from `.cursor/loops/stage-4-peer-r25.log`, the last `### Round 25` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 4 tooling peer review (stage-4.p1, peer round 4)
Status: Open (1 pending)

Scope:

- job 1: checked stitched output, refusals, startup and environment failures, interrupts, thread exceptions, unraisables and warnings; controlled reporting and quiet hooks remain present, and self-tests restore hooks (`sv-measure.py:181,2178`; `sv_stitch_product.py:691,1001`). Round 24’s parser fix prints an argument-free refusal.
- job 2: checked refusal order, temporary-store custody and vector cleanup; preflight checks precede audio reads, decoding passes `persist_key=False`, and teardown, owner clearing and chained traceback-frame clearing cover measurement failures (`sv_stitch.py:804`; `speaker_eval.py:1133`; `sv_stitch_product.py:418,662`).
- job 3: checked module loading and hash gates; imported scratch modules execute the bytes hashed by the loader, both trace modes pin `ffl_lib.py`, and replay-source reads must match executed digests (`sv-measure.py:223,2300`; `sv_trace.py:1516`). The main script’s separately read digest remains the recorded residue.
- job 4: checked stitched comparisons, decode fields, retry handling and checkout gates; capture limits, part embeddings, combination, labels, clinician and number are compared. Probability-only differences are detected, failed retries cannot inherit completion, and the gate covers `desktop/` and `validation/`. The note-path gap below remains.
- job 5: checked trace failures, configuration restriction and written fields; side errors are counted while processing continues, configuration must resolve to repository `validation/config`, and output records contain synthetic identities, codes and metrics without vectors (`sv_trace.py:1387,1681`; `sv-measure.py:2394`).
- job 7: checked round 24’s import-time roots, fixed-point module closure, inert grammar and new fixtures. The initializer, decorator, default-argument and class-subscript cases now reach their dependencies; parser regression cases exercise fixed diagnostics. Phase 1/2’s inert additions remain excluded as intended. However, touched-only control dependencies are not necessarily compared, so the claimed conservative guarantee is incomplete.
- job 6: checked constraints and supplied results; Git status is clean, only the plan differs from `4c29283`, and the requested product/scripts/validation/extension diff is empty. Frozen-file equality is supported by supplied evidence. Reviewed fixtures are synthetic; no kept-recording script or user-data folder was accessed.

Findings:

- **PR-MED-4801** (MED, regression verification, `.cursor/loops/sv_trace.py:955`): An import-time condition’s constant can change initialization behaviour while every compared item stays equal. Reproduction: extend the synthetic helper fixture at both revisions with an unchanged initializer that rebinds the used helper, and an unchanged module-level conditional that calls that initializer only when a Boolean constant is true. Change only that constant between revisions. The initializer is followed, but the condition’s constant is touched-only; its literal assignment is inert and never compared. The gate therefore reports no executable change although the imported helper’s behaviour changes. This requires none of round 24’s recorded residues. - Evidence: condition handling uses `"expr(node.test)"` (`:855`); names enter `"touched_nodes.append(node)"` (`:806`); touched values only re-follow their construction through `"ran, only_touched, _passes = _import_refs(...)"` (`:982`); reach returns `"return needed | rooted, modules"` (`:1014`), excluding touched-only bindings. Recommendation: Fix-now - Compare import-time control and value dependencies, including their bindings, and add a regression case changing only the conditional’s Boolean constant. This does not establish that the supplied decode result is wrong.

Verification:

- Files read: 15 unique scoped files.
- Jobs evidenced: 7/7.
- Findings verified statically: 1 MED.
- Supplied results: 70 self-tests passed, 0 failed; zero decode differences across 7/7 sets.
- No scripts, suites, network commands or writes performed.

PEER-ROUND-25 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

Executor verification and /fix (leg sg9, 2026-11-22):
- PR-MED-4801: verified, MED as labelled. Tuple: (`sv_trace.py` `reach`, MED, verified, fix-now).
  - In round 24's design a name that import-time code only READS went to the touched set. That set decided what else to follow, but it was never compared. So `ENABLED = False` read by `if ENABLED: _init()` could become `True` with every compared item equal, and `used` would be rebound at import.
  - /fix decision: Applied, with the simplest rule that closes the class. Every binding import-time code reads (the touched set: a condition's constant, a call's argument, a default, a subscript, an alias, a handler's exception type, a name a touched value was made from) is compared whole at both commits. It joins what is run in full and the non-inert definitions. What is run is still the only thing followed through its body, because a touched class's methods do not run at import.
  - Why not the stronger rule (compare every module-level statement of every loaded module whole, docstrings left out): it would count Phase 1's and Phase 2's additions as changes. Those are `EnrolmentPart`, `ENROLMENT_SCRIPT`, `ENROLMENT_PART_NAMES`, the `ENROLMENT_*` lines, the `enrolment_*` functions and `__all__` in `ui/models.py`; `recover_practitioner_labels`, `assemble_transcript` and `__all__` in `transcription.py`; `RECOVERY_MARK` and `__all__` in `speaker_embedding.py`; and `enrolment.py`'s additions. None is read by import-time code or reached by the replay:
    - the enrolment script and its text functions are read only by the Practitioner tab's methods;
    - `recover_practitioner_labels` and `assemble_transcript` run only when audio is transcribed, which the replay patches out. It reads Task 2.2's stored labels instead;
    - `RECOVERY_MARK` is read only by `recover_practitioner_labels`.
    D8 puts them off the note path: it names only `ui/models.py`'s composition helpers. So the narrower rule, compare what import-time code reads, is the one kept.
  - /fix notes:
    - `reach` returns its touched set with the rest (`needed | rooted | touched`). No other change.
    - Check 4: "condition-constant", the peer's reproduction (`ENABLED = False` to `True` under an unchanged `if ENABLED: _init()`), expects exactly `helpers:ENABLED`. It fails without the fix.
    - Round 24's "touched-class" case is replaced by two. "touched-compared": a method body of the class `KINDS = list[Box]` names changes, now counted as `helpers:Box`. "touched-not-followed": only a function `Box`'s method calls changes, which stays clean, because a touched class is not followed through its methods.
    - At the verified commit: the touched bindings are compared whole. The one I know of that leads towards Phase 2's code, `LiveTranscriber` (named by `LiveTranscriberSource`), is unchanged since Phase 0. Its change is `assemble_transcript`, which it does not contain and which is not followed. So 0 executable is still expected.
  - What the gate now guarantees: between the Phase 0 commit and the verified commit, no package code changed among
    - the definitions the replay reaches by name (from the harness entry points, the two stage builders, the whole note modules and the scratch replay's own uses);
    - for every module loaded on the way: its module statements (as text); its non-inert definitions; everything its import-time code runs, followed in full; and every binding its import-time code reads;
    - the import bindings reached, and the data files under the package and `validation/config`;
    except the listed wording constant and docstrings, bare strings and comments.
  - Residues, not analysed (unchanged from round 24):
    - access by a computed name (`getattr`, a star import reading `__all__`, `globals()`, `importlib`; the package has no star import, `globals()` or `__getattr__` today, and `importlib` only in `ml_warmup.py`);
    - what standard-library and third-party code does with the objects it is given;
    - the trust that a name load, a literal and a standard `dataclass` decoration run no package code;
    - the third-party libraries' versions.
  - Over-inclusion, on the safe side: a binding that is run, read or not inert is compared whole, method bodies included. A body change that never runs at import can therefore still count, by name.
  - /fix date: 2026-11-22; /fix applied by: Claude Code

No measured figure, comparison, bar or printed table changed. The decode check's note-path line can list more names only if a binding read at import changed. `SELF_TEST_CHECKS` stays 70: the new assertions are inside the trace's check 4. The plan is LF. Peer round 26, the last under the cap, is the confirm.

### Round 26 — 2026-11-22
(Transcribed verbatim by executor leg sg10 from `.cursor/loops/stage-4-peer-r26.log`, the last `### Round 26` header; codex rc=0, escape-check post clean, refs unchanged.)
Source: Codex — codex gpt-6-astra medium — Phase 4 tooling peer review (stage-4.p1, peer round 5)
Status: Open (1 pending)

Scope:

- job 1: checked stitched output, startup imports, parser errors, measurement/environment failures, interrupts, warnings, thread exceptions and unraisables; type-only guards and quiet hooks remain present, and self-tests restore hooks (`sv-measure.py:181,2178`; `sv_stitch_product.py:691,1001`). No new disclosure defect confirmed.
- job 2: checked refusal order, encrypted temporary-store custody and vector cleanup; preflight checks precede audio reads, decoding uses `persist_key=False`, and teardown, owner clearing and chained traceback-frame clearing cover failures (`sv_stitch.py:804`; `speaker_eval.py:1133`; `sv_stitch_product.py:418,662`). Audio-dependent input refusals necessarily follow reading the recordings.
- job 3: checked scratch loading, pins and subsequent imports; imported scratch modules execute the bytes hashed by the checked loader, both trace modes pin `ffl_lib.py`, and replay-source reads must match executed digests (`sv-measure.py:223,2300`; `sv_trace.py:1516`). The main script’s separate digest read remains the recorded residue.
- job 4: checked capture limits, per-part embedding, equal-weight combination, batch-driver labels, clinician and number; required comparisons detect differences. Decode comparison includes word probability, and checkout gates cover `desktop/` and `validation/`. Failed retries cannot inherit successful completion. The note-path comparison has the ordering gap below.
- job 5: checked per-side trace failures, configuration restriction and written fields; errors are retained while processing continues, configuration must resolve to repository `validation/config`, and records contain synthetic identities, codes and metrics without vectors (`sv_trace.py:1393,1678,1698`; `sv-measure.py:2394`).
- job 7: checked round 25’s fix and fixtures; `needed | rooted | touched` now compares touched bindings at both commits, and the condition-constant case would fail without it (`sv_trace.py:1020,2006`). “Touched-compared” detects a changed method; “touched-not-followed” correctly excludes an uncalled method’s dependency in that fixture. Excluding the identified enrolment and decoding additions accords with D8’s replay boundary. However, compared items still lose their relative initialization order, beyond the recorded residues.
- job 6: checked constraints and supplied results; Git status is clean, only the plan differs from `4c29283`, and the requested product/scripts/validation/extension diff is empty. Frozen-file equality is supported by supplied evidence. Reviewed fixtures are synthetic; no prohibited folder was accessed and no kept-recording script was invoked.

Findings:

- **PR-MED-4901** (MED, regression verification, `.cursor/loops/sv_trace.py:1102`): The note-path gate can miss an executable change caused solely by reordering module initialization. Reproduction: in the synthetic helper fixture, assign a numeric constant, copy it into another binding used by the reached helper, then reassign the original constant. At the other revision, move only the copy below the reassignment. The helper now reads a different value, but each name’s statement list remains identical, so the gate reports no executable change. This uses no computed lookup or library behaviour. - Evidence: assignments are grouped using `"result.defs.setdefault(name, []).append(statement)"` (`:692`); comparison returns `"[_dump(s) for s in info.defs[name]]"` (`:1102`); `_dump` uses `"include_attributes=False"` (`:359`), discarding positions. The separate `other` comparison (`:1115`) cannot recover ordering between these assignments. Recommendation: Fix-now - Preserve and compare relative initialization order among relevant bindings and executable statements, with a regression fixture that moves the copy across the reassignment. This does not establish that the supplied decode result is wrong.

Verification:

- Files read: 15 unique scoped files.
- Jobs evidenced: 7/7.
- Findings verified statically: 1 MED.
- Supplied results: 70 self-tests passed, 0 failed; zero executable changes reported and zero decode differences across 7/7 sets.
- No scripts, suites, network commands or writes performed.

PEER-ROUND-26 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

Executor verification and /fix (leg sg10, 2026-11-22):
- PR-MED-4901: verified, MED as labelled. Tuple: (`sv_trace.py` `Source.info` / `note_path`, MED, verified, fix-now).
  - Each name's statements were compared as a list, so a move within one name counted. But nothing recorded where one name's statements sat against another's. Moving `COPY = BASE` from above `BASE = 2` to below it changed what a reached helper reads, with every per-name list equal.
  - /fix decision: Applied, by the simplest ordered rule.
    - Each module records every top-level statement in source order, as a key that names it without its content: `def:<names>`, `alias:<local>`, `import:<package module>`, `other:<index>`.
    - For each loaded module, ONE ordered list is compared at both commits. It holds every statement that binds a compared name, every package import and every module statement.
    - Content stays compared as before, per name and for the module statements. So the ordered list adds only the order.
    - A difference is listed as `<module>:<order>` when that module has no other counted change, because a counted change refuses the trace by itself and an added statement moves the rest.
  - At the verified commit: Phase 1's and Phase 2's additions bind no compared name, so they are left out of the list. They were inserted, never moved among compared statements. Task 1.4's wording edit changes content, not order, and no package import moved in a loaded module (`enrolment.py` and `transcription.py` kept theirs in place; the new `import math` and `Sequence` are not package names). So 0 executable is still expected.
  - Check 4 gains "reordered-initialization", the peer's reproduction (`used` reads `COPY`; only `COPY = BASE` moves below `BASE = 2`). It expects exactly `helpers:<order>` and fails without the fix.
  - /fix date: 2026-11-22; /fix applied by: Claude Code

The gate as a whole, stated once so its limits are a complete list rather than found one per round. Between the Phase 0 commit and the verified commit:
- It COMPARES:
  - (a) every definition the replay reaches by name, whole: from the harness's entry points, the two stage builders, the whole of D8's note modules (`ui/note_review.py` added) and the scratch replay's own uses, followed through names, one-level `module.name` attributes and import bindings;
  - (b) the import bindings so reached;
  - (c) for every module loaded on the way (a reached name's module, its parent packages, its package-import closure, at either commit):
    - its module statements as text;
    - the source order of its compared statements, package imports and module statements;
    - its definitions that are not inert;
    - everything its import-time code runs (followed in full);
    - every binding its import-time code reads;
  - (d) every non-Python file under the package and `validation/config` (any change counts);
  - and, through the gate before it, a clean checkout whose `desktop/` and `validation/` are unchanged since the verified commit.
- It does NOT compare (the residues):
  1. Docstrings, bare strings, comments, formatting and source positions. Code that reads them at run time would see a difference: `__doc__`, `inspect.getsource`, line numbers in a traceback. Not checked; nothing on the note path is known to read them.
  2. A definition in a loaded module that is inert (it only binds a name to a value) and that no reached or import-time code names. This is by design: Phase 1's and Phase 2's additions are of this kind (D8).
  3. What a touched-only definition's methods or body call. That code does not run at import, and run-time use by name is followed under (a).
  4. Access by a computed name: `getattr`, `globals()`, `vars()`, a star import reading `__all__`, `importlib`, `__import__`, `sys.modules`, a module `__getattr__`. The package has no star import, `globals()` or module `__getattr__` today; `importlib` is only in `ml_warmup.py`, off the note path.
  5. Standard-library and third-party behaviour: what they do with the objects they are given, their versions, the Python interpreter's version and the operating system. Both trace sides run on the same environment, and the decode check covers the recogniser end to end.
  6. The trust that a name load, a literal and the standard `dataclass` decoration run no package code.
  7. Code reached only through the two functions the replay patches out (`transcribe_in_temporary_store`, `read_wav_pcm`). The recogniser and the speaker step are measured directly instead: Task 2.2 and the decode check, 0 differences on 7 of 7 sets.
  8. Modules the replay never loads (for example `ui/practitioner.py`, `ui/note.py`, `ui/main_window.py`).
  9. Inputs outside the repository: the models folder, the built synthetic sets, environment variables. The decode check and the sets' provenance records cover the first two; the replay sets its own configuration.
  10. The scratch code itself. It is pinned by hash instead: the frozen files' SHA-256, and the digests of the bytes that ran, printed by the decode check.
- Over-inclusion, on the safe side: anything run, read or non-inert is compared whole, method bodies included, so a change that never runs can still count, by name.

Cap verdict: accept — test-harness — PR-MED-4901 is verified and fixed by one ordered comparison per loaded module, with its failing-without-fix case "reordered-initialization"; the gate is scratch tooling whose 0-executable result is a cross-check beside Task 2.2's and the decode check's direct 0-difference measurements on 7 of 7 sets; its limits are now listed in full above rather than found one per round; and `/security-review` follows this pass.

No measured figure, comparison, bar or printed table changed. `SELF_TEST_CHECKS` stays 70: the new assertion is inside the trace's check 4. The plan is LF.

### Round 27 — 2026-11-22
Round status: Closed (SEC-001 fixed; its confirm is the composer's self-test)
Source: Claude Code — `/security-review` (Phase 4's H3)
Scope:
- `.cursor/loops/sv-measure.py`: the loader, the start-up hooks, the parser and the `--decode-check`, `--trace`, `--stitched --against-product` and `--again` paths;
- `.cursor/loops/sv_trace.py`;
- `.cursor/loops/sv_stitch_product.py`, with the frozen `sv_stitch.py` and `sv_lib.py` read only where the stitched mode calls them.
Executor leg sg11 (no Python run: verify=composer). The stitched mode came first, as the one the practitioner runs over their own recordings, against Task 0.6's precedent (rounds 6 to 9) and C1, C2, C9 and D2. Before this round the composer's runs gave self-test 70 / 0 and the decode check exit 0, both at `48c4ebb`.
Checked, with what was found:
- Refusal order, each before any audio read:
  - developer channel;
  - a folder;
  - the listing, then the manifest (counts only, never a name: `sv_stitch.manifest_problems`);
  - the scratch files that ran: the frozen pair at its pins, and each of the four loaded from its checked bytes;
  - git, the commit and a clean checkout;
  - Windows crash-report exclusion for this interpreter;
  - the single-instance lock, released in `finally`.
  Each is pinned by the stitched-product check 4, which also asserts no read and one line per case. `run_product` lists the folder again and reads only the thirteen manifest names, and a WAV it cannot read is refused by its manifest name and the error's type.
- The print surface:
  - the refusal lines are fixed text plus counts, type names, part numbers, manifest names and seconds. The crash-report line names this interpreter's path, as Task 0.6's did, never the measurement folder;
  - the progress lines and tables print numbers, the manifest and dialogue names, codes, the commit and the digests;
  - any other failure prints its type name only, inside `run_and_render` and again under `guarded_run`;
  - thread exceptions, unraisables and warnings are silenced from the script's first package import (round 23) and again in `product_mode`;
  - the top-level hook prints a type only;
  - a parse error prints one fixed line (round 24).
  No `SystemExit` with text is raised on the path: the package calls `sys.exit` only under `__main__`. No logging is configured, and no package module the path uses logs at WARNING or prints.
- D2 custody:
  - the thirteen recordings and each stitched dialogue live only in memory (`sources`, `pcm`, deleted after the decode);
  - the decode goes through `transcribe_in_temporary_store(persist_key=False)`, the frozen `make_deps`, and check 3 asserts all ten stores are gone;
  - the profile vectors are in one `ProfileHolder`, cleared in `finally` and on any failure (`vector_boundary`); the dialogue owner holds spectral features only and is cleared in `finally`;
  - exception frames are cleared, chained ones included;
  - check 5 asserts no vector is reachable and no store is left after a failure part-way.
  The mode writes no file and no record, and reads no standard input (C9).
- The hash checks of every module the stitched run executes:
  - `sv_lib.py` and `sv_stitch.py` are refused unless at their pins;
  - `sv_stitch_product.py` is refused unless loaded from its checked bytes;
  - all four digests are printed for the composer to compare with Task 4.3's freeze, `sv-measure.py`'s own being read at its start (the recorded residue).
  Here SEC-001 was found.
- The other modes: `--decode-check`, `--trace` and `--again` read and write synthetic sets only (C9). `--trace` refuses a configuration other than the repository's `validation/config`. Its records were checked vector-free (round 21 and peer job 5). The trace pins `ffl_lib.py` and compares the replay scratch's bytes with the digest that ran.

Finding verification: 1 candidate; 0 dropped; 0 downgraded.
Round classification: 1 🆕 / 0 ⚡ / 0 🔁 (present since leg sg1).

#### SEC-001: `.cursor/loops/sv-measure.py` (the start of the file, `HERE` / `sys.path`) — the scratch folder stayed on `sys.path`, so a stray `.py` there named like a module imported later would run unchecked
- Severity: LOW. A same-user local file is needed, none such exists today, and the printed digests of the four checked files would still match. Classification: 🆕 (present since leg sg1). A regression from Task 0.6's precedent: its script took the scratch folder off the path (peer round 9, job 2: "scratch-path removal prevents later unchecked imports from that folder").
- Why it matters:
  - Python puts a script's own folder first on `sys.path`, and `sv-measure.py` re-inserted it.
  - The checked loader covers only the six scratch modules by name. Any other import that is not yet loaded would be looked up in `.cursor/loops/` before the standard library and the venv, and run with no hash check: the standard library's lazily imported modules, numpy and its submodules, onnxruntime, faster-whisper, and so on.
  - The freeze promises the practitioner's run executes only checked or installed code. A shadowing file would break that promise silently, in the run that holds their recordings and voice vectors.
  - Checked today: no `.py` in `.cursor/loops/` has the name of a standard-library or a used third-party module (a name-only search, no file opened).
- Desired behaviour: the scratch folder is on no `sys.path` entry from the script's first statement after its future import. Scratch modules are found only by the checked finder, at `HERE / <name>.py`.
- Pattern siblings: the frozen `sv_stitch.py`, `sv_lib.py` and `ffl_lib.py` and the new `sv_trace.py` and `sv_stitch_product.py` add nothing to `sys.path` (searched). Every scratch import in them names a checked module.
- Scope-expansion disposition: n/a. It is scratch hardening; it changes no figure, comparison, bar, table or printed line.
- /fix decision: Applied.
- /fix notes:
  - `sv-measure.py` now starts, after its future import, with `os` and `sys`, which the interpreter has already loaded at start-up, so neither is looked up on the path. It then removes every `sys.path` entry that resolves to the scratch folder (an empty entry counts as the working folder), before any other import.
  - The later `sys.path.insert(0, HERE)` is removed.
  - `scratch_folder_on_path()` reports the state. Check 13 gains "scratch-folder-off-path"; it fails without the fix, because the folder was on the path.
  - The other imports are unchanged, now marked `noqa: E402`. `SELF_TEST_CHECKS` stays 70.
- /fix date: 2026-11-22; /fix applied by: Claude Code

Residues, recorded, not fixed (unchanged from Task 0.6's precedent):
- a native library's own console output (onnxruntime, CTranslate2), which no Python hook intercepts;
- `sv-measure.py`'s own digest, read once at its start rather than from the bytes Python compiled;
- a second interrupt landing inside a `finally` cleanup could leave a temporary store's ciphertext, whose key was in memory only, so it cannot be read;
- the profile vectors are dropped and collected, not zeroed;
- the venv's own start-up files (`.pth`, `sitecustomize`) are the environment's, outside this freeze.

Fix-delta self-check: PASS.
- I re-read the applied hunks. The path removal runs before every import that could be shadowed. The checked finder still serves every scratch import, because each is one of `CHECKED_MODULES`: `sv_lib`, `sv_stitch`, `ffl_lib`, `sv_sets`, `sv_trace`, `sv_stitch_product`.
- Nothing else in the three files changed.
- The plan is LF.

### Round 28 — 2026-11-22
Round status: Closed (RUN-001 fixed; its confirm is the composer's self-test, then the re-run of (b))
Source: composer long run (b), 2026-11-22
Scope: `.cursor/loops/sv_trace.py` `trace_mode` and its gate entry, against `validation.main`, `benchmark.apply_offline_env` / `assert_offline_env` and `language_model.LanguageModel`. Executor leg sg12 (no Python run: verify=composer). A finding of Phase 4's own run, not a peer round.
What the composer saw at `c8edce3` (tree clean, `git diff 4c29283 c8edce3 -- desktop/ scripts/ validation/ extension/` empty): (a) `--stages off` exit 0, errors 0. (b) `--stages gate` exit 1 after about one minute: `TRACE GATE: traced 31, … not evaluated 31, … errors 31`, every side's status `error:OfflineEnvError`; the provenance, note-path and decode lines printed as expected first.

Finding verification: 1 candidate; 0 dropped; 0 downgraded.
Round classification: 1 🆕 / 0 ⚡ / 0 🔁 (present since leg sg1).

#### RUN-001: `.cursor/loops/sv_trace.py` `trace_mode` — the trace never set the offline environment, so the gate side's language model refused to load on every side
- Severity: MED. The planned gate-configuration trace could not run. It failed closed: every side was an error, the exit was 1, and no figure was recorded from it. Classification: 🆕 (present since leg sg1).
- Verified from the code (the tuple):
  - `benchmark.assert_offline_env` raises `OfflineEnvError` unless `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` and `HF_HUB_DISABLE_TELEMETRY` are `1` (and no `LLAMA_CPP_LIB_PATH` / `SSLKEYLOGFILE`). Only `apply_offline_env` sets them.
  - `language_model.LanguageModel.__init__` calls `assert_offline_env()` as its first statement (line 283). The prose and suggestion stages built by `build_prose_stage("narrative")` and `build_suggestion_stage()` construct it on first use, inside `ffl_lib.replay_encounter`, so the failure surfaced inside `evaluate_side`'s guard as `error:OfflineEnvError` on both sides. The stages' one remembered load failure (note-content-design D10) explains the run's one minute.
  - The harness applies it only in its own `main` (`validation.py` lines 4556–4557), which the trace never calls. `sv-measure.py` applies it only in `_numpy()` (lines 330–334), which no `--trace` path reaches. `sv-measure.py`'s `--trace` dispatch (lines 2403–2433), `sv_trace.trace_mode`, `sv_lib.py` and `ffl_lib.py` hold no other call: a search for `offline_env` finds none.
  - With the stages off no model loads, so (a) never needed it: that is why (a) passed. The self-test never loads the real model, so it did not see this.
- Desired behaviour: the trace applies and asserts the offline environment once at its start, as `validation.main` does, before any model can load, in both stage settings.
- Pattern siblings:
  - `decode_check_mode` loads no model and reads records only. It is left unchanged.
  - `sv_stitch_product.product_mode` decodes through the product's batch driver. Its models come from `hooks.models`, `sv-measure.py`'s `Models`, whose constructor calls `_numpy()` (line 821) before any model is built. Not changed.
  - The self-test calls `_numpy()` at its start (line 1479), so in that process the environment was already set: another reason it did not see this.
  - The harness reports (c) go through `validation.main` and set it themselves.
- Scope-expansion disposition: n/a. Only the trace's environment changes: the variables only the model loaders read, set to the values the harness's own `main` sets. No figure, comparison, bar, table or printed line changes, apart from the new refusal line, which cannot print after `apply_offline_env`.
- /fix decision: Applied, in `sv_trace.py` alone. `sv-measure.py` is byte-unchanged, so Task 4.3's stitched mode keeps its frozen bytes, and `sv_stitch_product.py` is unchanged.
- /fix notes:
  - The new `offline_start()` calls `apply_offline_env()` then `assert_offline_env()`, and returns the refusal's type or None. `trace_mode` calls it as its first statement, before `prepare` (git, the pins, the decode check and the note path), before `print_prepared`, before the gate side's channel and model checks and its two stage builders, and so before any model can load. A refusal prints `[refused] the offline environment could not be set (<type>)` and returns 2.
  - Check 7 (`stages_rule`) gains `offline-start:off:2:set`, `offline-start:gate:2:set` and `offline-start-reached:2`. For each stage setting it removes the three kill-switches, sets `LLAMA_CPP_LIB_PATH` to a dummy value, and runs `trace_mode` with `prepare` replaced by a stand-in. The stand-in runs the language model's own first step (`assert_offline_env()`) and returns 2. The check needs the stand-in reached with the environment set and the override gone. The environment and `prepare` are restored in `finally`. Without the fix the stand-in sees `OfflineEnvError` and the check fails. `TRACE_CHECKS` stays 7 and `SELF_TEST_CHECKS` 70 (assertions inside an existing check).
  - A side effect on the gate, by design: `sv_trace.py` now refers to `scribe_desktop.benchmark` (`apply_offline_env`, `assert_offline_env`, `OfflineEnvError`, and in the self-test `OFFLINE_ENV` and the three variable lists). So the note path's scratch seeds (round 21 MED-001) now include them. `benchmark.py` and `language_model.py` are unchanged between `8bedfc4` and `4c29283` (`git diff --stat`: empty), so the gate should still read 0. The decode check confirms it.
- /fix date: 2026-11-22; /fix applied by: Claude Code

`validation.main`'s set-up against the trace's gate entry, step by step (task 3 of leg sg12):
- `configure_output()`: done by `sv-measure.py`'s `main` (line 2341) before any dispatch.
- The developer-channel refusal: done in the gate setting (`install_layout.channel()`). With the stages off nothing reads the models folder.
- `apply_offline_env()` then `assert_offline_env()`: not done before; done now (RUN-001), in both settings.
- `--model` shape, Whisper, VAD and speaker-model availability, the enrolment WAVs, `--device`, `SileroVad`, `WhisperSpeechProvider`, `build_speaker_embedder` and the enrolments: not needed. The replay decodes nothing (`ffl_lib.replaying` patches `transcribe_in_temporary_store` and `read_wav_pcm`), the documents are the saved enrolled ones, and the enrolment is `replay_encounter`'s dummy.
- The set and config folders, the app's own config and learned content: `sv-measure.py` takes only the repository's `validation/config` (round 19 LOW-002) and loads it with `load_note_config`. The gate holds `validation/config` unchanged since the verified commit (`DATA_PATHS`).
- `load_pass_rule` and `--set`: not needed. The trace renders no verdict, it compares outcomes.
- `bind_template_profile`: a refusal-only precheck in the harness. The trace's `HarnessInputs` take the default template profile (None), as the harness does without `--template-profile`, and `evaluate_encounter` binds it per encounter. A failure would be each side's `error:<type>`, never silent.
- Language-model availability under `--prose` / `confirm-all`: done (`language_model_available()`, refused without it).
- `build_prose_stage("narrative")` and `build_suggestion_stage()`: done, the same calls with the same arguments. The harness builds them inside a type-only guard. In the trace a construction failure would reach `sv-measure.py`'s type-only top-level hook. Neither loads the model at construction.
- `find_encounters` and the incomplete encounters: done by `hooks.set_problems` (a set with any inventory problem is not traced).
- `HarnessInputs`: `replay_encounter` builds it with the same `prose_stage`, `suggestion_stage`, `attribution="enrolment"` and the config, with no provider or VAD (nothing decodes).
- `run_encounters`' per-encounter `load_script`: the scripts come from `set_problems`, which loads them.
- The custody stop (`SpeakerEvalError`) and the interrupt lines: not reached (no temporary store is made), and `sv-measure.py`'s hooks print a type only.
- `RunInfo`, `render_report` and `run_passed`: not needed (the trace writes its own record).
No other step the harness's `main` sets up is missing from the trace.

Residues, recorded, not fixed:
- Run (a)'s record (`trace-off.json`) and `sv-p4-trace-off.txt` name the pre-fix `sv_trace.py` digest. The fix changes nothing on that path (no model loads with the stages off), so (a)'s figures stand. Recommended: re-run (a), about 10–20 minutes, so both trace records name the new pin. That is the composer's call.
- The suggestion stage's 240 s cap is wall-clock. A gate trace run beside the background gate reports (two copies of the 2.3 GiB model on one processor) could hit the cap on one side and not the other, and report "not evaluated" or a difference that the labels did not cause. Recommended: run (b) alone, after the background reports finish.

Fix-delta self-check: PASS.
- I re-read the applied hunks. `offline_start` is `trace_mode`'s first statement. Its refusal is printed after its `except` block ends. The stand-in check restores `prepare` and every variable it touched.
- `import os` was added to `sv_trace.py`'s imports. Nothing else in the three files changed; `sv-measure.py` and `sv_stitch_product.py` are byte-unchanged in this leg.
- The plan is LF.

### Round 29 — 2026-11-22
Round status: Closed (2026-11-23: the practitioner's disposition (a) Accept; D8's must-pause disposed by the practitioner, never as "explained")
Source: composer long run (b) repeated, 2026-11-22
Scope: the one must-pause row of the second gate-configuration trace (`sv-p4-trace-gate-2.txt`, exit 3), `heldout-4` `h4-06`. Executor leg sg13 (no Python run; no code changed). The evidence is synthetic only: the script `validation/heldout-4/h4-06.json`, Task 2.2's vector-free record `sv-out/after/4c29283…/heldout-4/h4-06.json`, and `trace-gate.json`'s `h4-06` entry.

Finding verification: 1 candidate; 0 dropped; 0 downgraded.
Round classification: 1 🆕 / 0 ⚡ / 0 🔁 (Lever B's effect, since Phase 2).

#### MP-001: `heldout-4` `h4-06`, gate configuration — one line added in a clinician-owned section (`advice_home_exercise`, segment 2, words 0–0)
- Severity: must-pause by D8's kind (a line placed in a clinician-owned section it was not in before), not a severity grade. Classification: (i), a correct placement newly reached.
- The tuple, verified from the synthetic material:
  - Who speaks segment 2: the clinician. The decode's segment 2 is the one word "Great." (8.99–9.54 s). It is the first word of the script's line index 2, a clinician line: "Great. You can bump the bridges up to three sets of twelve, and add the leg lifts lying on your side that we tried today." The rest of that line is segments 3 and 4.
  - The relabel: segment 2 scored 0.462. Before (scratch's R0, the literal 0.50) labelled it `speaker_2`, the patient. After (the product, B1-35: at least 0.35, the clinician confirmed by direct matches) labelled it `speaker_1`, the clinician. Segment 2 is the encounter's only segment whose R0 and product labels differ. The stored clinician (`speaker_1`) and number (0.763) are the same on both sides, and `stored_attribution` is empty.
  - The script's reference: no fact on segment 2's word. Line 2's material fact ("three sets of twelve") lies in segment 3, which is labelled the clinician on both sides. The script's four facts are on line indices 1, 2, 3 and 6 (counted from 0).
  - The route: an accepted suggestion. With the stages off, the trace shows no line added or removed for `h4-06`: no cue routes "Great.", so it is left out on both sides. In the gate configuration the outcome fields that differ are `metrics.transcript_lines`, `clinician_as_other_seconds`, `suggestions.suggested_w` and `suggestions.dropped`. `suggested_u`, `wrongly_present` and `not_assessed` do not differ, and no fact, omission, next-patient or verdict field differs.
    - This is consistent with the model suggesting `advice_home_exercise` for segment 2 on both sides. Before, the chooser's ownership rule refused it, because the line was labelled the patient and the section is clinician-owned (`dropped`). After, it was accepted as the clinician's line (`suggested_w`).
    - The trace record holds the names of the fields that differ, not their values, so this reading is the consistent one, not one the record shows directly.
  - Not the answer hop: the hop joins a patient's reply after the clinician's question. Segment 2 is the clinician's own word after the patient's statement.
- Classification: (i). It is a correct placement newly reached because the clinician's own speech is labelled theirs (B1-35's intended effect), and it sits with its own line's advice. It is not (ii), a patient line relabelled as the clinician's, and it is the opposite case to Accepted Assumptions' residue (1). Named cost: a one-word acknowledgement can now be suggested into a clinician-owned section (clutter for review). In the app a suggestion is a mark the clinician acts on; the gate configuration's `confirm-all` is the upper bound.
- Recommendation: (a) Accept, recorded by name. The options and what each sets in motion are in Task 4.1's must-pause brief (2026-11-22, leg sg13): (a) accept; (b) accept with a Deferred item for the suggestion stage to leave one-word acknowledgements alone (not built here); (c) decline Lever B, the release becomes `R0` and D9's fall-back reverts Phase 2.
- Scope-expansion disposition: n/a. No code, bar, rule or figure changes; the disposition is the practitioner's.
- Disposition: pending (the practitioner). The composer records the must-pause pair and puts the question.
- Disposition (2026-11-23, the practitioner): (a) Accept, their words "Accept (a)". The clinician's own "Great." placed in Advice / home exercise by an accepted suggestion is accepted by name; no Deferred item (option (b) not chosen). Recorded as the gate-disposition for `regression-must-pause` (2026-11-23T04:36:53+11:00). Phase 4 goes on to Tasks 4.2 and 4.3 (the practitioner's runs), then Phase 5.

### Round 30 — 2026-11-23
Round status: Closed (2 applied: MED-001 and LOW-001; the targeted tests and the suite owed to the composer)
Source: Claude Code (`/review-loop` round 1 of 3, Phase 5's H1, executor leg sv3; no Python run: verify=composer)
Scope: the primary baseline is `5e1e2cb` (Phase 4's close), the changed files are `5e1e2cb..8e441a7`: the version places (`desktop/pyproject.toml`, `desktop/src/scribe_desktop/__init__.py`, `extension/package.json`, `extension/package-lock.json`, `extension/src/manifest.ts`), `.cursor/plans/plan-ui-refresh.md`, `AGENTS.md`, `CHANGELOG.md`, the security documents (threat model, data-flow map, retention schedule), the testing documents (speaker measurement, kept recordings, validation harness), `docs/release/pilot-builds.md`, `docs/pilot/findings-register.md`, the practice documents (clinician review guide, privacy information, README) and this plan. Every claim was read against the as-built code of Phase 1 (`9fb3777`) and Phase 2 (`4c29283`): `transcription.recover_practitioner_labels`, `assemble_transcript`, `enrolled_cluster`, `attribute_speakers`, `MIN_ATTRIBUTION_PCM_BYTES`; `enrolment.enrol` / `enrol_part` / `combine_parts` / `part_consistency` / `weakest_part` / `strength_share`; `ui/practitioner.py`'s guided worker (`record_part`, `work`, the Stop checks, the busy-on-lease controls); `ui/models.py` `ENROLMENT_SCRIPT` and the learning lines; `note.CLINICIAN_OWNED_SECTIONS`; `ui/transcript.py`'s confirmation line; `replay_kept.py` and `speaker_eval.py`'s path through `transcribe_session`; and 0.4.0's strings (`git diff b8dac3d 8e441a7`). Skipped with reason: `extension/package-lock.json` (generated; its two own-package version fields read). C1: no session id, per-recording number, pooled total or accent count from a kept recording in any changed document (kept-consultation results are words only; Task 4.2 is `complete`, `no check errors`).

Looks good (verified, no finding): the recovery mark's every documented guard (runs only after a direct match at 0.50 confirmed as `speaker_1`; 0.35 ≤ score < 0.50; never an unscored or directionless segment; never removes `speaker_1`; the acceptance check; the one call in the attribution branch; the stored clinician and number from the labels before it ran, the mean over the direct matches); the guided capture's targets and caps (30 / 15 / 12 / 15 / 12 / 15 s, 90 / 45 × 5 s), the 3 s beat, `del pcm` in a `finally` before the next part, the optional-part rule, the one redo, the equal-weight mean, the summed speech seconds, the in-memory strength share, the Stop checks and the residue at the final check; the busy-on-lease controls; the four clinician-owned headings in the review guide; the confirmation line's wording; the replay and speaker harness both reaching the mark through `transcribe_session`; the figures (0.71 % → 0.12 %, 0.61 % → 1.02 %, +0.42 point) against Task 4.1's lines; 0.4.0's "not attributed to you" note and "Re-record my voice" button in the rollback section; the practice documents' new lines marked awaiting approval.

Finding verification: 2 candidates; 0 dropped; 0 downgraded.

#### MED-001: `desktop/src/scribe_desktop/ui/models.py:3553` (`LEARNING_ON_LINE`), `note_config.py:1919`, `ui/note_review.py:243`, `ui/note.py:218` — the learning promise still said "your own lines" where the learners test the label
- Triage: Fix-now. Fix route: fix-on-fast (copy and comment alignment to Task 1.4's adopted wording).
- Why it matters: Task 5.2 restates every place that says only the practitioner's own lines or words are learned. Phase 1's open point (6) (leg sx1) handed exactly these sources to Task 5.2's wording search, and leg sv1 searched the documents but not them. The Review screen's line, shown whenever learning is on, said "lines you add or move, and shorthand you type over your own lines, are learned": a practitioner reading it would take a typed edit over any line, or a patient's line, as learned or not learned by who spoke, while `ui/note_review.consider_rule_learning` and `consider_learning` test `note.spoken_by_confirmed_clinician` — the label — and a patient's line labelled the clinician's (more often since B1-35) teaches. The three comments said the trigger is "the practitioner's OWN utterance".
- Current behaviour: the on-line claims "your own lines"; it also reads as if any added or moved line is learned. Desired behaviour: it names the label, as `LEARNING_NOT_ATTRIBUTED_NOTE` already does since Task 1.4.
- Pattern to follow: Task 1.4's `LEARNING_NOT_ATTRIBUTED_NOTE` ("only lines labelled as yours are learned") and its test `test_enrolment.py::...::test_the_learning_line_names_the_label`.
- Pattern siblings (searched `own lines`, `own words`, `practitioner's OWN`, `never reaches the learner`, `teaches nothing`, `never (a|from) (a )?patient's`, `only your own`, `confirmed clinician's own` over `desktop/src`, `docs/`, `PLAN.md`, `AGENTS.md`): fixed — the four above. Left, true as written: `ui/note.py:89-93` and `:113-119` (already the label; ":119" means the typed wording, which is the practitioner's own), `ui/practitioner.py:665, 695, 760` (the lists show the practitioner's own config data), `note_fill.py:379`, `note_check.py:1531`, `note.py:1030`, `ui/models.py:3472` (the practitioner's OWN config pre-fill), `data-flow-map.md:1803` (their chosen past notes), the threat model's surface 10 title (already glossed). Left by decision: `ui/models.py` `CONSENT_TEXT_V2` / `CONSENT_TEXT_V3` ("Only your own lines are ever used — never a patient's") — the consent text is frozen; the gap is the named residue (the plan's Accepted Assumptions; the threat model's THE RECOVERY MARK, consequence (2)), and changing it is a new consent version, not this fix.
- Verification: `test_enrolment.py` `test_the_learning_line_names_the_label` now pins `LEARNING_ON_LINE`'s new text and that it holds no "own lines"; every other test reads the constant by name (`test_ui_screens.py:6883, 7108, 7117, 7122, 7617`).
- Regression risk: the Review screen's learning label (`ui/note.py:1340`) and the five tests that compare against the constant; no logic changes.
- Scope-expansion disposition: n/a (inside Task 5.2's "Always" scope).
- /fix decision: Applied.
- /fix notes: `LEARNING_ON_LINE` reads "Phrase learning is on: lines labelled as yours that you add or move, and shorthand you type over them, are learned when you press Save note on the Review screen.", with a comment naming Task 5.2 and the label; the three comments name the label ("the speaker label, not proof of who spoke"). The new line is for the practitioner's eye at Phase 1's held live smoke, beside round 12's wording points (it was never a practitioner-approved string: written by the note-learning plan's leg, Task 2.3).
- /fix date: 2026-11-23; /fix applied by: Claude Code

- **[LOW]** LOW-001: `docs/security/threat-model.md` (practitioner-profile surface 2, "The guided capture") — "every other failure ends the enrolment" did not say that the one redo, short at its cap, keeps the part's first attempt (`ui/practitioner.py` `record_part`, `work`: `redone is None` keeps `parts[redo_index]`) — Triage: Fix-now; Decision: Applied (the sentence names it; CRLF kept).

Round classification: n/a (the first `/review` code round over Phase 5's work).
Missed-issue pass: re-read `ui/models.py` (the learning lines), `ui/note.py` (module docstring), `ui/note_review.py` (`consider_rule_learning`), `note_config.py` (the learned-rules block), the threat model's surfaces 2, 5 and 8 and the data-flow map's flows 7, 12 and 13; result: MED-001's siblings (above), LOW-001.
Fix-delta self-check: PASS — each hunk found by search where it was made; ruff clean; mypy clean (72 files); `test_shadow_exits.py` untouched; the threat model still CRLF, the Python files LF.

### Round 31 — 2026-11-23
Round status: Closed (2026-11-23: MED-001 disposed (a) by the practitioner and applied by leg sv5; LOW-001 applied)
Source: Claude Code (`/review-loop` round 2 of 3, Phase 5's H1, executor leg sv4; no Python run: verify=composer)
Scope: round 30's fixes (`8e441a7..be26d3d`) and a fresh pass over Phase 5's whole diff (`5e1e2cb..be26d3d`, the same files as round 30 plus round 30's four Python files, its test and the threat-model sentence), MED-001's class first. The class search (a promise that learning, or anything that reads the speaker label, uses only what the practitioner said): `your own (line|word|utterance|speech|phrase)`, `their own (line|word|utterance|speech)`, `(practitioner|clinician)'s own (line|word|utterance|speech|phrase)`, `own utterance`, `only (the )?(practitioner|clinician)'s (line|word|utterance)`, `never (from|a|learn)… patient`, `patient… never… (learn|teach|taught)`, `lines you (said|speak|spoke)`, `what you said`, `learn… (own|patient|another speaker)` and the reverse, `someone else`, `another speaker`, `not yours`, `line(s) of yours`, `you said`, over `desktop/src` and `desktop/tests` (`type: py`), `docs/` (every document Task 5.2 names, `docs/practice/`, `docs/pilot/`, the design system, the shipping gate), `PLAN.md` and `AGENTS.md`. C1 held.

Round 30's fixes, confirmed: `LEARNING_ON_LINE` reads as written and every test compares against the constant by name; the three comments name the label; `test_enrolment.py`'s pin holds (the composer's suite: 11176 passed, 9 skipped); the threat model's guided-capture sentence matches `record_part` / `work` (a redo short at its cap keeps `parts[redo_index]`). Post-fix regression check (baseline `8e441a7`): no signature, return or shape changed; the learning label's one reader (`ui/note.py:1340`) and its five test comparisons read the constant; none.

Class search, left as true or decided: the consent texts `ui/models.py` `CONSENT_TEXT_V2` / `CONSENT_TEXT_V3` ("Only your own lines are ever used — never a patient's") and their pins (`test_ui_models.py:865, 928, 954`) — frozen consent text, THE KNOWN GAP (the plan's Accepted Assumptions; the threat model's THE RECOVERY MARK, consequence (2): "although the consent text says only the practitioner's own lines are used"); a change is a new consent version, never a fix. `test_ui_screens.py` `test_a_patient_line_is_never_a_learning_candidate` — true for its fixture (the line is another speaker's by label and by script) and cited by name in `findings-practitioner-profile.md`, so not renamed. `ui/note.py:119` (the typed wording is the practitioner's own), the "your own wording" tooltips, the config pre-fill lines, the style's "own past notes", the measurement documents' "their own voice" (true: the practitioner's script recordings) — true as written. The threat model, data-flow map and retention schedule restatements (round 30) hold.

Finding verification: 2 candidates; 0 dropped; 0 downgraded.

#### MED-001: `docs/practice/clinician-review-guide.md:211-213` (item 7, "Suggested headings (from version 0.3.6)") — an approved line says "A line someone else said is never suggested for your assessment, diagnosis, advice or plan", where the rule reads the speaker label
- Triage: Fix-now, but MUST-PAUSE: the line is practitioner-approved wording (the 0.3.6 lines, approved 2026-11-10), and this leg's rules make a change to it the practitioner's.
- Why it matters: the suggestion stage's acceptance goes through the chooser's ownership rule (`note.admissible_sections`, `note.CLINICIAN_OWNED_SECTIONS` = assessment, diagnosis, advice / home exercise, management plan), which tests `spoken_by_confirmed_clinician` — the label. A patient's, carer's or interpreter's line labelled the practitioner's (more often since B1-35, F-174) can be suggested for, and added to, those four headings, and adding it teaches a phrase when learning is on. The guide's new 0.4.2 speaker-label line (item under "The speaker labels can be wrong…", awaiting approval) now says exactly that, so the guide contradicts itself: one line says such a line "is never suggested" there, the other that it "can be placed under your assessment, diagnosis, advice or plan headings with no warning". The guide is a named control on F-174 (the threat model's THE RECOVERY MARK: "the practitioner's review of the speaker labels before moving a line into their own sections (the clinician review guide)").
- Current behaviour: "A line someone else said is never suggested for your assessment, diagnosis, advice or plan. A suggestion never stops you saving, and adding a suggested line of yours teaches the app a phrase just as adding any line of yours does (when learning is on)."
- Desired behaviour: the line speaks of the label, or a dated 0.4.2 line beside it says what "someone else" and "of yours" mean since 0.4.2.
- Pattern to follow: the show-the-doubt plan's rule for a record the practitioner has read — a dated line beside it, never a rewrite of the words they approved; the guide's own header list of dated additions.
- Pattern siblings (the same guide, speaker-dependent behaviour described as who said it, all label-based in the code; approved wording, so the same disposition): `:144` (the unsure mark: "A line someone other than you said with words of doubt" — `note.text_holds_hedge` over a line not labelled the confirmed clinician's), `:232` and `:237` (the prose speaker frame: "where someone other than you said a line", "Pt tested the knee" for "your 'I tested the knee'" — the frame reads the label), `:179-181` (the left-out-line warning "A line you said is not in the note" — `clinician_line_omitted`, label-based; that is app text quoted, not a promise to change). The privacy information and the README are already label-worded (leg sv2). Searched as in Scope; no other practice-document sibling.
- Options (recommendation first):
  - (a) Recommended: one dated line after item 7's sentence, awaiting the practitioner's approval, with the header's list gaining it: "**From version 0.4.2:** "someone else" and "of yours" here mean how the app labelled the line, as everywhere in this guide: a patient's line labelled as yours (see the speaker-label line above) can be suggested for those headings, and adding it can teach a phrase." Lines 144, 232 and 237 are covered by the speaker-label line's general statement and need no line of their own. Sets in motion: one guide line and its header entry; the practitioner's approval before Task P.3.
  - (b) Reword the approved sentence itself to the label ("A line labelled as someone else's is never suggested …"), and the same for 144, 232 and 237. Sets in motion: four approved lines reworded, each needing re-approval.
  - (c) Leave them: the speaker-label line above already says a line can be labelled yours wrongly. Sets in motion: nothing; the guide keeps two lines that read as contradicting each other.
- Regression risk: none in code; `test_pilot_docs.py` reads `docs/pilot/` only, and no test reads `docs/practice/`.
- Scope-expansion disposition: n/a (Task 5.2's restatement of every promise about a patient's line, applied to the guide Task 5.2 names).
- /fix decision: Pending (the practitioner's disposition).
- Disposition (2026-11-23, the practitioner): (a), their words "Add a 0.4.2 line (Recommended)" (gate-disposition key `stage-5/r31/MED-001`). Applied by leg sv5: one "**From version 0.4.2:**" line after item 7's approved sentence, the approved words unchanged ("someone else" and "of yours" there mean how the app labelled the line; a patient's, carer's or interpreter's line labelled as yours can be suggested for the four headings and adding it can teach a phrase; check the speaker before adding a suggested line), the guide's header listing it as awaiting the practitioner's approval, and the practice README's 0.4.2 sentence naming it. /fix decision: Applied; /fix date: 2026-11-23; /fix applied by: Claude Code.

- **[LOW]** LOW-001: `docs/design-system.md:410-411` — the learning status lines quoted the old "Not learned: this line is not attributed to you …", which Phase 1's Task 1.4 changed to "… not labelled as yours …" (`ui/models.py` `LEARNING_NOT_ATTRIBUTED_NOTE`) — Triage: Fix-now; Decision: Applied (the quote names the 0.4.2 wording and the label, and keeps 0.4.0's words as history; CRLF kept). 🆕, a sibling of round 30's MED-001 in a document Task 5.2 names. Its neighbour, the queued line "Phrase learning is on: N phrases queued - press Save note on the Review screen to learn them (Cancel, Delete and Complete learn nothing).", matches `learning_queued_line`.

Round classification: 2 🆕 / 0 ⚡ / 0 🔁 (both present since Phase 1 or the note-content-design plan; surfaced by the wider search; neither caused by round 30's fixes).
Missed-issue pass: re-read `ui/models.py` (the learning lines, the consent texts), `ui/note.py` (the module docstring), `docs/design-system.md` (the learning bullets, 400-440), `docs/practice/clinician-review-guide.md` (items 5-8 and the speaker-label line), `docs/practice/privacy-information.md` and `README.md`; result: MED-001's siblings (above), LOW-001.
Fix-delta self-check: PASS — LOW-001's hunk found by search; `docs/design-system.md` still CRLF; no product code or test changed in this leg.

### Round 32 — 2026-11-23
Round status: Closed (1 applied: LOW-001; the targeted test and the suite owed to the composer)
Source: Claude Code (`/review-loop` round 3 of 3, the cap, Phase 5's H1, executor leg sv6; no Python run: verify=composer)
Scope: round 31's fixes (`be26d3d..ce423d0`: the design-system quote, the clinician review guide's item 7 line and its header entry, the practice README's 0.4.2 sentence) and a final confirming pass over Phase 5's whole diff `5e1e2cb..ce423d0`. The class search (any practitioner- or patient-facing line, or code comment, that says something depends on who actually spoke where the code reads the speaker label): `you said`, `you say`, `said by`, `someone (else|other)`, `other person`, `the patient said`, `another speaker`, `not you`, `other than you`, `who (spoke|said)`, `patient's (line|words|speech)`, `by the patient`, `from the patient` over `desktop/src/scribe_desktop` (`type: py`), and `a line you said`, `lines you said`, `someone (else|other than you) said`, `said by someone`, `not from a line you` over `docs/`; with rounds 30 and 31's searches already run over the same trees. C1 held.

Round 31's fixes, confirmed: the design system's quote matches `LEARNING_NOT_ATTRIBUTED_NOTE`; the guide's new line follows item 7's approved sentence (unchanged), points to the speaker-label line above it (item list, "The speaker labels can be wrong…"), and is true of the code — the suggestion's acceptance goes through `note.admissible_sections` over the label, so a line labelled the clinician's has the four clinician-owned headings open and can be suggested for and added to them, and learning reads the same label; the guide's header and the README name it as awaiting approval; both files CRLF. Post-fix regression check (baseline `be26d3d`): documents only; none.

Class search, left as true or decided: the left-out-line warning's app text ("A line you said is not in the note", `ui/models.py` the `clinician_line_omitted` row and hint, `ui/note.py:883`) and the flagged count line ("a line you said, an answer to a question you asked, …", `ui/models.py:3110-3112`, approved as drafted 2026-11-17) and every document that quotes them (the design system, the threat model, the release notes, the review guide's :181) — practitioner-approved or quoted app text covered by the guide's speaker-label line, as round 31 recorded for :179-181 (the threat model's THE RECOVERY MARK names the consequence: "a left-out one draws `clinician_line_omitted`"); the review guide's :144 and :237 — covered by the same line (round 31 MED-001's option (a), the practitioner's choice); the comments that already say "the confirmed clinician" or "the speaker label" (`note.py:312, 1098, 2248`, `ui/note.py:74, 91`, `ui/models.py:2292, 3202`, `prose_style.py:265`); `note_fill.py:46` (true: autofill triggers match any speaker by design); `note_suggest.py:129` (the model's speaker hint, "usually the patient's words" — a hint to the model, worded as usual, not a claim); the consent text v3 (`ui/models.py:3914, 3922`) — frozen, THE KNOWN GAP, not a finding.

Finding verification: 1 candidate; 0 dropped; 0 downgraded.

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/ui/note_review.py:262` — the status line for a typed edit over a hand-authored config line said "Not learned: this line came from your own config, not from a line you said.", where the rule learner tests the speaker label (`consider_rule_learning`: an utterance labelled the confirmed clinician's) — Triage: Fix-now; Decision: Applied ("… not from a transcript line labelled as yours.", matching `LEARNING_NOT_ATTRIBUTED_NOTE` and round 30's `LEARNING_ON_LINE`; `test_ui_screens.py` `TestNoteScreenTypedEdits.test_the_filters_refuse_and_the_status_names_the_class` keeps its "came from your own config" check and gains "line labelled as yours"). 🆕, a sibling of round 30's MED-001 in app text: written by the note-learning plan (never practitioner-approved wording); no document quotes it. For the practitioner's eye at Phase 1's held live smoke, beside the learning-on line.

Round classification: 1 🆕 / 0 ⚡ / 0 🔁 (present since the note-learning plan; surfaced by the wider search; not caused by round 31's fixes).
Missed-issue pass: re-read `ui/note_review.py` (`consider_rule_learning`, `consider_learning`), the review guide's items 5-8 and the speaker-label line, the practice README's version paragraph and the design system's learning bullets; result: LOW-001.
Termination: converged — no CRIT, HIGH or MED in this round, and its one LOW is applied; the cap (3 of 3) is reached converged, so no cap verdict is owed.
Fix-delta self-check: PASS — the string and the test hunk found by search; ruff clean; mypy clean (72 files); `test_shadow_exits.py` untouched; both Python files LF.

### Round 33 — 2026-11-23
Round status: Closed (0 findings)
Source: Claude Code simplify (Phase 5's H2, executor leg sv7; propose-only; no Python run: verify=composer)
Scope: the stronger-voice product code as built, Phase 1 (`9fb3777`), Phase 2 (`4c29283`) and Phase 5's code changes to `ebcd30e`, read in full where in scope: `enrolment.py` (`record_enrolment`, `enrol`, `PartEmbedding`, `_SegmentVectorRecorder`, `enrol_part`, `_finite_floats`, `_unit`, `_unit_mean`, `_cosine`, `combine_parts`, `part_consistency`, `weakest_part`, `strength_share`); `ui/practitioner.py` (the capture and embed seams, the worker events, `on_record` and its closures `raise_if_stopped` / `beat` / `record_part` / `work`, `_show_part`, `_reset_card`, `_on_progress`, `on_stop`, `_release_lease`, `_on_enrolment_done`, `_on_enrolment_failed`, the busy controls); `ui/models.py`'s enrolment block (`EnrolmentPart`, `ENROLMENT_SCRIPT`, `ENROLMENT_PART_NAMES` and the line builders) and the round 30 / 32 wording; `transcription.recover_practitioner_labels` and its one call in `assemble_transcript`; `speaker_embedding.RECOVERY_MARK`.

Simplifications found: none — no simplifications worth a maintainer's attention.

Consciously left alone (the conservatism guard):
- `enrolment._cosine` / `_unit` beside `transcription._cosine`: two implementations of one cosine rule. Plain-Python `fsum` against numpy `dot` differ in the last float bits (Phase 1's open point (5); Task 4.3's parity tolerance), so routing one through the other is not behaviour-preserving, and `enrolment` keeps the pipeline module out of the enrolment path.
- `part_consistency` and `strength_share` each build a leave-one-out reference with the same two lines: a shared helper saves two lines and adds a name; marginal.
- `recover_practitioner_labels` re-runs `enrolled_cluster` over the labels its caller just scored: passing the caller's result in would change the function's self-contained contract (and its standalone tests, `TestRecoveryMark`) for a cost of one linear pass; marginal.
- `ENROLMENT_PART_NAMES` beside `ENROLMENT_SCRIPT`'s keys: a field on `EnrolmentPart` would change the dataclass's shape and its pinned tests for no behaviour; marginal.
- The guided worker as closures inside `on_record` (~130 lines): the shape the D15 lease and the seams chose (one worker, its captured values fixed at Start); a split is a restructure, not a simplification.
- `_show_part` / `_reset_card` sharing the meter-and-counter reset: two lines; marginal.

Finding verification: 0 candidates surviving the guard; 6 left alone (above).

### Round 34 — 2026-11-23
Round status: Closed (0 findings)
Source: Claude Code security-review (Phase 5's H3, executor leg sv7; portable checklist in this session; propose-only; no Python run: verify=composer)
Scope and trust boundaries: the same files as round 33, plus `ui/tasks.py` `TaskThread` (the worker's exception path), `transcription.enrolled_cluster`, `attribute_speakers`, `_cosine`, `MIN_ATTRIBUTION_PCM_BYTES` and `transcript_before`, and the threat model's practitioner-profile surfaces 2, 5 and 8 and the data-flow map's flows 7, 12 and 14 read against them. The boundaries: the microphone into process memory (enrolment PCM), the worker thread to the GUI thread (events and the result), the profile store (the one write), and the speaker labels into the note and the learners.

Checked and clean:
- **The memory bound.** At most one part's PCM exists at a time: `record_enrolment` returns one `bytes` copy and clears its `buffer` and `remainder` on every exit (`finally`); `record_part` embeds it through `enrol_part` and drops it with `del pcm` in a `finally`, before the beat and the next part; `enrol` slices pieces locally and keeps none; `_SegmentVectorRecorder` keeps vectors only. On a failure the exception leaves `work`, and `TaskThread.run` emits only `"<type>: <message>"` and returns, so no traceback frame keeps a part's PCM alive past the handler; the messages carry seconds and counts, never audio. Between parts only numbers stay (`PartEmbedding`: a unit vector, speech seconds, segment vectors), dropped when `work` returns; `GuidedEnrolmentResult` carries seconds, a share, part keys and none of the vectors.
- **No audio written or logged.** `enrolment.py` and `ui/practitioner.py` hold no logger, no file open or write, no WAV writer and no temporary file (searched `logging`, `logger`, `.write(`, `open(`, `write_wav`, `wave`, `tempfile`: none); the one write is `save_profile`'s single vector.
- **ONE lease.** `begin_enrolment` is taken once in `on_record` and covers every part, each beat, the redo, the save and the result handler; the tab is busy on the lease alone from that moment. Release: a failed microphone handoff releases it after its error is shown; `_on_enrolment_done` and `_on_enrolment_failed` release it in `finally`, after the status line and the profile re-read; Stop sets the event, which ends a capture, a beat's wait or the next check, and the failure handler releases. The final `raise_if_stopped` precedes `save_profile`, so "nothing was saved" holds until that check (the documented residue).
- **The recovery mark only adds `speaker_1`.** `recover_practitioner_labels` maps each label to `SPEAKER_1` or leaves it; it never writes another label, and its acceptance check discards the change whole unless `enrolled_cluster` still confirms `speaker_1`.
- **Nothing is relabelled without a direct match at 0.50.** It returns the labels unchanged unless some similarity is at or above `ATTRIBUTION_THRESHOLD` (0.50, unchanged) and `enrolled_cluster` over today's labels confirms `speaker_1`; only `RECOVERY_MARK <= s < ATTRIBUTION_THRESHOLD` relabels; a `None` similarity (a slice under 25 ms, `MIN_ATTRIBUTION_PCM_BYTES`) is skipped; a directionless or non-finite vector scores -1 (`_cosine`), below the mark. It is called once (`assemble_transcript`'s attribution branch), so the batch and live drivers (`transcribe_session`, the live drain) share it, and never after the single-speaker shortcut or without a profile.
- **No vector kept; the stored figures are the direct matches'.** It reads one float per segment; `assemble_transcript` stores `enrolled_cluster` over the labels before the mark (`enrolled`), so the clinician and `enrolment_similarity` are the direct matches' mean; `transcript_before` drops the three attribution fields only when no kept segment with that label holds text, as the threat model's THE TRIM says.
- **The documents against the code:** surface 8 (THE RECOVERY MARK), surfaces 2 and 5 (the guided capture, the lease) and flows 7, 12 and 14 state what the code above does (round 30 read the same, and round 30 LOW-001 added the redo's shortfall).
- **Portable checklist categories:** injection, SSRF, authentication, crypto and dependencies — not reached by this change (no new input parser, network call, credential, cipher or package); resource bounds — each part's capture is capped (`max_seconds`, the bounded block queue), the redo is one, the beat is 3 s.

Finding verification: 0 candidates; nothing to drop or downgrade.

### Round 35 — 2026-11-23
Round status: Closed (2 applied: PR-LOW-5001, PR-LOW-5101; documents only)
Source: Codex — codex gpt-6-astra medium — Phase 5 peer review (H4, pass stage-5.p1, peer round 1 of cap 5), two read-only slices in one activation over `5e1e2cb..444400d`; verified and applied by Claude Code, executor leg sv8.
Scope, slice A (code and security documents; `stage-5-peer-r35-a.log`): job 1 the recovery guards, the unchanged 0.50, 0.35 ≤ score < 0.50, unscored segments, the direct-match attribution fields, both assembly callers and the trim (`transcription.py:1019, 1742, 1908, 2332, 1467`); job 2 the six parts, optional parts, lease, redo, PCM disposal, 0.651, the stored mean and the transient strength; job 3 label-based learning in normal, off and shadow mode (`note.py:1697`, `ui/note_review.py:303, 395`, `test_ui_screens.py:8254-8324`); job 4 the six version fields and the two changed tests; job 5 C1. 21 files read; 1 finding.
Scope, slice B (other documents; `stage-5-peer-r35-b.log`): job 1 the practice documents' rules, approval markers and learning and suggestion claims against the label-based code; job 2 profile compatibility, stored labels and the rollback steps against the current and 0.4.0 source; job 3 the measurement figures against the plan (0.71 % → 0.12 %, +0.42 point, 183 encounters, 31 relabelled, 0 differences over ten dialogues, `h6-22`, 0.651); job 4 F-174 against the register's vocabularies and the AGENTS pointers; job 5 C1. 23 files read; 1 finding.

Finding verification: 2 candidates; 0 dropped; 0 downgraded. Round classification: 2 🆕 / 0 ⚡ / 0 🔁 (both in Phase 5's documents since `8e441a7`; neither caused by rounds 30-34's fixes).

- **[LOW]** PR-LOW-5001: `docs/security/retention-schedule.md:45` (the voice-profile row) — said the stored vector is the mean of "the six script parts' vectors"; an optional part left out at its cap is absent from the mean (`enrolment.combine_parts`: "A left-out part is absent"; `ui/practitioner.py` `work` combines `parts[i] for i in order`, the final attempts only) — Verified: LOW, documentation accuracy; Triage: Fix-now; Decision: Applied ("the kept script parts' vectors (the final attempts only; an optional part left out at its cap is absent)"; CRLF kept). Siblings searched (`six script parts`, `six parts' vectors`, `mean of the six`): none other — the threat model's surface 1 says "the captured script parts' vectors" and flow 12 "the kept parts' vectors".
- **[LOW]** PR-LOW-5101: `docs/release/pilot-builds.md:86, 104`, `docs/testing/speaker-measurement.md:33` — stated 0.50 as a universal floor for the practitioner's label and its similarity; with NO segment at or above 0.50 the unchanged fallback (`transcription.attribute_speakers`: 2-means over every segment, the cluster `enrolled_cluster` scores higher becomes `speaker_1`, lines 983-987; the same in 0.4.0) labels segments under 0.50 as the practitioner's and stores that cluster's mean — Verified: LOW, documentation correctness (the recovery mark itself is correctly described: it never runs without a direct match); Triage: Fix-now; Decision: Applied — the release notes' attribution sentence and point (2) now say "with a direct match" and name the fallback as unchanged and shared with 0.4.0; the measurement document's `Similarity` sentence is qualified the same way, with the fallback's cluster mean "under 0.50". Siblings searched (`at or above 0.50`, `direct match`, `mean over the DIRECT`, `mean of the direct`, `only segments at or above`) over `docs/`, `AGENTS.md` and `CHANGELOG.md`: data-flow map flow 7 (line 258) applied the same qualifier ("when it runs …; with no direct match the mark does not run and the unchanged fallback's cluster and mean stand"); left as already qualified by their context — the threat model's THE NUMBER and THE TRIM ("on a relabelled transcript", the mark's own guard), `validation-harness.md:648` ("after a direct match"), `CHANGELOG.md:10` and `AGENTS.md:190, 245` (each inside "once a recording has matched … directly" or the mark's description), the clinician review guide's 0.4.2 line ("once your voice has matched clearly"). All four edited files CRLF, as before.

Missed-issue pass: re-read `transcription.attribute_speakers` and `enrolled_cluster` (the no-match branch and its swap) and the four edited paragraphs; result: none beyond the applied siblings.
Fix-delta self-check: PASS — each hunk found by search where it was made; `git ls-files --eol` reads `w/crlf` for the four documents, with no LF-only line; no product code or test changed.

### Round 36 — 2026-11-24
Round status: Closed (2 applied: LOW-001, LOW-002; the targeted test and the suite owed to the composer)
Source: Claude Code (`/review-loop` round 1 of 3, executor leg sv9; no Python run: verify=composer)
Scope: leg sv9's change against `34a1162`, the practitioner's "Bigger text" from the held live smoke of 2026-11-24: `ui/theme.py` (the new role `reading` in `ROLES`, the token `size_reading` = 16 in `LIGHT` and `DARK`, its one rule in `render_qss`, `set_role`'s docstring), `ui/practitioner.py` (`set_role(self.passage_label, "reading")` and its comment), `tests/test_ui_phase_s.py` (`TestGuidedCardWidth`, now `test_every_part_fits_across[150|100]`), `docs/design-system.md` (the guided-card bullet, Type, Emphasis), the CHANGELOG's 0.4.2 sub-bullet and this plan's smoke lines; read against `TestStylesheet.test_every_role_variant_and_shell_id_has_rules`, `TestTheCodeAndTheSheetAgree` (every literal role in `ROLES` with its selector in both sheets; no font, weight or stylesheet outside the theme), `TestTokens.test_light_and_dark_agree_on_type_spacing_and_radii`, `test_ui_shell.py` `test_every_token_colour_is_accepted` (strings only) and `test_ui_screens.py`'s card tests (the passage's interaction flags, hidden at rest). C1 held.

Checked and clean:
- **The theme rule.** The size is a token, the rule lives only in `render_qss` and the role reaches the label only through `set_role` with a literal, so the package grep and the code-and-sheet test cover it; the rule sets a size only, so the disabled-colour rule needs no `reading` entry; light and dark agree (the type-equality test).
- **Plain text, not selectable.** `setTextFormat(PlainText)` and Qt's default interaction flags are untouched; `test_ui_screens.py`'s flags assertion on `passage_label` stands; `test_shadow_exits.py` is unedited (it pins text widgets in `ui/note.py` and `ui/past_sessions.py`, not this label).
- **Scope.** Only the passage grows: the heading, the cue and the fixed "keep reading" line are read once before moving, and the passage is what the practitioner reads while walking (their words). 16 pt is 1.6 times the 10 pt body and above the 14 pt title.
- **The fit.** Across: a word-wrapped label grows down, not across, and the width assertions now run at 100 % as well as 150 %. Down: the longest passage, part 3's ten short lines, is about 16 body lines at 16 pt against the 150 % stand-in's 42-line window less the header and the Settings strip, so the new "within one view's height" assertion has room; part 1's 430 characters wrap to a handful of lines. The tab already scrolls vertically, and the card sits in the "Record your voice" group the practitioner has scrolled to in order to press Record.

Finding verification: 2 candidates; 0 dropped; 0 downgraded.

- **[LOW]** LOW-001: `desktop/tests/test_ui_phase_s.py` `TestGuidedCardWidth` — as first written this leg, the font-size assertions read `passage_label.font()` before the card was ever shown, relying on `set_role`'s explicit re-polish of a hidden label at construction for the stylesheet's size to reach `font()` — Triage: Fix-now; Decision: Applied — the size is asserted inside the loop, after `_show_part` and two `processEvents`, on the shown and polished label (the passage `== theme.LIGHT.size_reading` and above the cue's body size, per part); the role property stays asserted before. 🆕, this leg's own test.
- **[LOW]** LOW-002: `docs/design-system.md` (the guided-card bullet) — said "a cue in capitals"; the cue label is plain text set from `EnrolmentPart.cue` as written ("Sit where you consult."), with no role and no upper-casing anywhere in `ui/` (searched `.upper()`) — Triage: Fix-now; Decision: Applied ("a cue"; CRLF kept). Pre-existing since Phase 1's leg sx1; in the sentence this leg edits.

Round classification: 2 🆕 / 0 ⚡ / 0 🔁.
Missed-issue pass: re-read `_show_part` and `_reset_card` (no per-part font change, so one role covers every part and the redo), `theme._repolish`, the three other `size_*` uses in `render_qss`, and the references to the renamed test (`plan-stronger-voice.md`'s round 12 record names the old `test_every_part_fits_across_at_150_percent`, a dated record left as written; `_at_150` keeps its two other callers); result: none further.
Termination: converged — no CRIT, HIGH or MED in this round, and both LOWs are applied; no round 37 is owed. The targeted tests and the suite are owed to the composer; the card's live re-check is the practitioner's.
Fix-delta self-check: PASS — each hunk found by search where it was made; ruff clean; mypy clean (72 files); `test_shadow_exits.py` untouched; the Python files LF; `docs/design-system.md` and `CHANGELOG.md` CRLF with no LF-only line.

## Tasks

### Phase 0 — Measure (scratch only) — done 2026-11-21 (Tasks 0.1 to 0.7)
- [x] 🟩 Task 0.1: Approve the reading script   [decision]
  - Chosen: approve the six parts below as written (2026-11-20); rationale: the practitioner's answer, "Approve as written".
  - Options: approve the six parts below as written / edit any part's words or cue.
  - The script (synthetic, no patient content; each part ends when enough speech is heard, so exact words do not matter):
    1. NORMAL VOICE. Sit where you consult. "Thanks for coming in today. Before we start, tell me what has been going on and when it began. I would like to look at how you are moving, then check your strength and your range. After that I will explain what I think is happening, and we will agree on a plan together. Most people notice a change within the first two or three visits. If anything I do is uncomfortable, tell me straight away and we will ease off."
    2. SPEAK QUIETLY. As you would beside the treatment table. "Just relax your shoulders for me. Breathe in slowly, and let it go. Good. I am going to press gently here, and you tell me if it is tender. Stay nice and loose. That is it, well done. One more time, slow and easy."
    3. SHORT PHRASES. Normal voice, pause after each line. "Okay." "Right." "Good." "No worries." "And how did you sleep?" "Any pins and needles?" "Left side or right side?" "Is it worse in the morning?" "Does that ease it?" "Let us try that again."
    4. NUMBERS AND SIDES. Normal voice. "Three sets of ten, twice a day. Hold each stretch for thirty seconds. Fifteen minutes of walking, five days a week. Left shoulder, right knee, lower back, both ankles. Come back in two weeks."
    5. MOVE AWAY. Stand where you treat and keep talking as you move. "I am just going to move around to the other side. Keep your arm resting there. Now push up against my hand, and hold. And relax. Turn onto your side for me, facing the wall."
    6. YOUR OWN WORDS. Do not read. "Describe, as if to a new patient, what happens in a first visit."
  - Blocks: Task 0.3 and Phase 1.
- [x] 🟩 Task 0.2: Freeze the bars, definitions, orders, ids and measures   [decision]
  - Chosen: confirm as written (2026-11-20); rationale: the practitioner's answer, "Freeze as written". Frozen by this commit, before any new number.
  - Options: confirm Validation / Verification (the definitions, the bars, the calibration's derivation) and the tables, ids and orders of D2, D4, D5, D7 and D9 as written / change a figure now.
  - Output: one commit of this plan holding the frozen figures, before any new number (C3).
  - Blocks: Tasks 0.4 to 0.7.
- [x] 🟩 Task 0.3: Record the truth recordings   [operator]
  - The practitioner records the thirteen files of D2 in Audacity into the measurement folder's new `stronger-voice\` subfolder: each part for at least twice its target (60 / 30 / 25 / 30 / 25 / 30 s), reading the passage again when its end is reached; the computer voice for at least 120 s. The composer gives the folder path and the Windows-voice command in chat, never in a tracked file.
  - Done when the practitioner says the thirteen recordings exist.
  - Done (2026-11-21): the practitioner said all thirteen are in the `stronger-voice\` subfolder ("other.wav done, all 13 in the folder"). Their Task 0.5b run found all thirteen and kept 6 of 6 parts in each take.
- [x] 🟩 Task 0.4: Build the seen sets, decode and evaluate them once, prove the premise
  - Files: new `.cursor/loops/sv_lib.py` (D4's table with its ids, D5's grid, D7's combination table, the pure rules, scratch's `R0` with the literal 0.50), `.cursor/loops/sv-measure.py`. On the practitioner's "start now": `scripts/build-validation-set.py` for the seven sets into `C:\sv-sets\`; D2's one pass per encounter over each set, writing everything D2 lists (the per-row and per-grid-point summaries and timings included, since nothing vector-based can be recomputed later); D8's "before" harness reports with their commit id and SHA-256s.
  - Expected: the premise's two parts (Validation): 0 differences on every encounter, and the generated fixture's checks pass.
  - Verification: the 0-differences line and the fixture line; a failed premise stops the phase and is reported. `git status` shows nothing written outside `.cursor/loops/`; no file under `sv-out/` holds a vector (a size and key check in the script's own self-test).
  - Status (2026-11-21, leg svx10): all but one evidence line is in. Stays 🟨.
    - In:
      - The pass at `7e730b1` (`.cursor/loops/sv-pass.log`): every set `errors 0, complete`, `PASS PROBLEMS: 0`, `PASS_END rc=0`.
      - The premise's first part (`.cursor/loops/sv-premise.log`): 0 differences on each set (50 / 22 / 22 / 23 / 22 / 22 / 22 encounters), `PREMISE DIFFERENCES TOTAL: 0 (sets complete 7/7)`.
      - The premise's second part, the generated fixture (`.cursor/loops/sv-selftest-5.txt`, `SELF-TEST: 55 passed, 0 failed`): the sub-window and cut-candidate times at known sample positions, a segment with no text, an encounter with no segment, the no-match branch, the shortcut, three roles in two classes, an overlap beside an eligible transition, and a tie.
      - D8's before reports at `7e730b1` with the desktop clean (the sets report's provenance line).
      - `git status` clean after the freeze commit.
    - Missing: the size and key check over the pass's records. That self-test ran before the pass wrote anything, and its line reads `0 JSON file(s) checked`. The writer refuses a vector before writing, but the plan names the self-test's check over `sv-out/`.
    - The command that produces it (reads `sv-out/`, writes nothing there): `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test < /dev/null > .cursor/loops/sv-selftest-6.txt`. Task 0.4 is done when that file's `size and key check over every file already under sv-out` line reads `[ok]` with a non-zero JSON count, and it ends `SELF-TEST: 55 passed, 0 failed`.
  - Done (2026-11-21, leg svx11): the missing line is in, so every evidence line the task names is met.
    - The composer ran the self-test after the pass, as `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --self-test --config validation/config < /dev/null`. The self-test refuses without `--config validation/config`, which the command above leaves out.
    - Its output is `.cursor/loops/sv-selftest-6.txt`, exit 0. It reads `[ok] size and key check over every file already under sv-out` (`191 JSON file(s) checked; 15 other file(s) ignored`), so no file under `sv-out/` holds a vector. It ends `SELF-TEST: 55 passed, 0 failed`, the generated fixture's cases included.
    - With the pass and premise evidence above (`sv-pass.log`, `sv-premise.log`: 0 differences, 7 of 7 sets complete) and `git status` clean after the freeze commit.
- [x] 🟩 Task 0.5: The truth tables and the selection
  - 0.5a (agent): `sv-measure.py --sets` over what Task 0.4 wrote: every candidate row against bar B's seen-set lines; D5's grid against bar C's seen-set line; and the labelling-against-routing comparison. That comparison is made on the seen-set cohort only (Validation). For each encounter the note is composed, with identical cues, under `R0`'s labels and under true labels: a segment whose true class (D2) is the clinician takes the document's confirmed clinician label, any other takes the other label; a tied or non-overlapping segment keeps its measured label and is counted. The true labels are given to composition directly, with the confirmed clinician's label as the clinician; no stored attribution is rebuilt. An encounter in which the true labels leave the clinician's label on no text-bearing segment is counted `unevaluable` and left out of the three counts. Reported by line identity (segment and word coordinates), never as two pooled counts: lines added under true labels, lines removed, and clinician lines still left out under true labels.
  - 0.5b (practitioner)   [operator]: `sv-measure.py --stitched` over the truth recordings, from a normal terminal with both builds closed (the composer gives the PowerShell command in chat); the practitioner pastes its tables (D6). P0 and P1 at `R0` against bar A1; P2 against bar A2; every candidate row with P1 against bar B's stitched lines, with each row's recall difference from P1 at `R0`; D5's grid against bar C, with eligible mixed seconds, proposed and kept cuts, and the count of close-turn body segments past 30 s; the part-consistency figures. Its self-test, with generated signals and fakes, proves the script before the practitioner runs it: a hand-checkable multi-turn dialogue (truth seconds, transitions, matching, mixed seconds, the pools); a span over 8 s arriving while a turn is open, a closed turn under 1 s, the other voice running out and restarting past its reserved spans, the same turns under all four gap values, and an other-voice file with no speech refused; no source sample in both a preamble and a scored body; a close-turn dialogue whose preamble forms centres and one where none can be formed (`unmeasured`); a sub-window at an equal distance from both centres and a piece that holds no sub-window centre; a cut inside an overlap region; a full 30 s part through the file-backed capture with no wall-clock wait and no queue overflow; a short optional file and a short required file; the manifest refusals; the temporary store destroyed after a pass and after a failed pass; the reservation at a span boundary, and a voice left with no body turn refused; an optional part with no speech left out while a required one is refused; a word and a sub-window centre exactly on a cut; an exception held during second-profile and sub-window scoring, with the vector no longer reachable.
  - 0.5c (after a COMPLETE run of 0.6): D9's order is walked and its result stated; bars A2 and C are stated for the follow-up plan.
  - Expected: one table per bar with `met` / `not met` / `unmeasured`, and one selected release id (`R0` or a row id).
  - Done (agent), 2026-11-21: 0.5a. `sv-measure.py --sets` exit 0, the report `.cursor/loops/sv-sets-report.md` ends `SETS: COMPLETE`, over the pass at `7e730b1`. Synthetic sets only.
    - The cohort is 183 of 183: every encounter's clinician is confirmed at baseline, all through the match branch.
    - R0: clinician seconds labelled other 0.71 % of 5,030.1 s; other speakers' seconds labelled clinician 0.61 % of 2,830.5 s.
    - Bar B's seen-set lines. No row makes a cohort encounter stop confirming, and every row lowers the clinician-labelled-other rate. So the other-labelled-clinician line (a rise of at most 0.5 point) decides:
      - B1: all four rows meet every line. B1-45: 0.41 % / 0.68 % (+0.07). B1-40 and B1-35: 0.12 % / 1.02 % (+0.42). B1-30: 0.08 % / 1.02 % (+0.42).
      - B2: 32 of the 36 rows meet every line, at +0.03 or +0.10. B2-21 to B2-24 fail the other-labelled-clinician line: 1.11 % (+0.51).
      - B3: all 36 rows fail it, from 1.22 % (+0.61) to 1.95 % (+1.34).
    - Bar C's seen-set line (no wrong split). Every grid point has 86 encounters with centres and 16.9 s of eligible mixed speech. Five of the six points meet it. F3.0-W1.0 does not: 3 kept cuts, 1 wrong split, on `heldout-5` encounter `h5-21`.
    - Labelling against routing, on the cohort, with 0 encounters unevaluable:
      - True labels add no note line and remove none on any encounter of any set. No encounter's lines change, and no next-patient boundary moves. One tied segment kept its measured label (`heldout-5`, `h5-11`).
      - Clinician lines still left out under true labels: scripts 122, heldout 78, heldout-2 282, heldout-3 276, heldout-4 270, heldout-5 254, heldout-6 279.
      - On these sets the labels are not what leaves lines out; routing is.
    - No selection is made yet. Bar B also needs its stitched lines (0.5b, after Task 0.3's recordings) and its kept-consultation words (0.6). Bar C's stitched lines are 0.5b's too. Task 0.5 stays 🟥 until 0.5b and 0.5c.
  - Done (practitioner), 2026-11-21: 0.5b. Their `sv-measure.py --stitched` run from a normal terminal ended `STITCHED: COMPLETE`. The pasted tables are kept in `.cursor/loops/sv-stitched-paste.md`, with the 36 identical B2 rows and the 36 identical B3 rows collapsed to one line each and no value changed. Their own voice and a computer voice, synthetic words (D6, C1).
    - Recordings: all thirteen. Every take-A and take-B part was kept (6 of 6 each), and each required part reached its target. The quiet pool was measured: each take's quiet file holds 25.2 s and 27.6 s of detected speech, against 8 s needed. Ten dialogues were built and decoded, all on the match branch, with no turn dropped.
    - Bar A1 (reported; it gates nothing), at R0, as overall / quiet / close-turn recall with overall false match:
      - P1: 96.3 % / 92.8 % / 76.1 %, false match 0.0 %. A1 met.
      - P0 beside it: 91.9 % / 63.7 % / 37.2 %, false match 0.0 %. Its quiet line is not met.
    - Bar A2 (reported for the follow-up plan): P2's quiet recall is 100.0 % against P1's 92.8 % (+7.2, at least +5.0 needed), with no more false match (0.0 %). Met.
    - Part consistency: the lowest part cosine is take a part 1, 0.701; every other part is 0.822 to 0.885. The calibrated figure is 0.651 (the lowest less 0.05).
    - Bar B's stitched lines (with P1): every row meets all three. As overall / quiet / close-turn recall and overall false match:
      - B1-45: 97.5 / 92.8 / 100.0 %, 0.0 %. B1-40: 97.5 / 100.0 / 100.0 %. B1-35: 98.6 / 100.0 / 100.0 %. B1-30: 99.5 / 100.0 / 100.0 %. The B1 rows' false match is 0.0 %, and their close-turn recall is 100.0 % (+23.8 points on R0).
      - Every B2 row: 99.9 / 100.0 / 76.1 %, false match 0.0 %.
      - Every B3 row: the same recall as B2, false match 0.7 %.
    - Bar C (reported for the follow-up plan). The halving line is met at all six grid points: eligible mixed speech goes from 270.9 s to 9.7–22.9 s. The wrong-split rate line is not met at any point: 16 to 19 wrong splits in 15.0 min of single-speaker exposure, 5.34 to 6.34 per 5 min against at most 1. Four close-turn body segments run past 30 s, where the live path would force-close a span.
    - Parity: `PARITY DIFFERENCES TOTAL: 0`, scratch R0 against the pipeline's own labels, clinician and number with P1.
    - Still owed for the selection: bar B's kept-consultation words (Task 0.6, the practitioner's run), then 0.5c, D9's order walked over all three line sets. Task 0.5 stays 🟥 until 0.5c.
  - Done (agent), 2026-11-21: 0.5c, D9's order walked. A row qualifies when it meets every line of bar B: the stitched lines with P1 (0.5b), the seen-set lines (0.5a), and the kept-consultation direction and sanity words for P1 with that row (0.6). A line that reads `unmeasured` is not met; none does.
    - Step 1, B1-45: the stitched lines are met and the seen-set lines are met. Its kept direction word is `not met`, so it does not qualify.
    - Step 2, B1-40: the stitched and seen-set lines are met. Its kept direction word is `not met`, so it does not qualify.
    - Step 3, B1-35: the stitched lines are met (recall 98.6 % overall, 100.0 % quiet, 100.0 % close-turn; false match 0.0 %). The seen-set lines are met: no cohort encounter stops confirming, clinician labelled other falls from 0.71 % to 0.12 %, and other labelled clinician rises from 0.61 % to 1.02 % (+0.42, within 0.5). The kept words are direction `met` and sanity `met`. It qualifies, so the walk stops here.
    - The selected release id is B1-35, built with Lever A (Phase 2's built row; Task 0.7 confirms it).
    - What B1-35 adds over the guided profile alone (P1 at R0), per D9:
      - on the stitched pools, +2.2 points overall recall, +7.2 quiet and +23.8 close-turn, with false match unchanged at 0.0 %;
      - on kept consultations, the third word `adds`;
      - its seen-set cost is the +0.42 point of other speakers labelled clinician above.
    - Reported for the follow-up plan, gating nothing here:
      - Bar A2 is met: P2's quiet recall is 100.0 % against P1's 92.8 % (+7.2), with no more false match.
      - Bar C is met at no grid point. On the stitched recordings every point halves mixed speech but fails the wrong-split rate (5.34 to 6.34 per 5 min against at most 1). On the seen sets five of the six points have no wrong split; F3.0-W1.0 has one, on `h5-21`.
      - Bar A1 (reported) is met for P1.
    - The Expected line is met. There is one table per bar with its words (0.5a's report and 0.5b's paste, summarised above), and one selected release id, B1-35.
- [x] 🟩 Task 0.6: Real speech   [operator]
  - Files: new `.cursor/loops/sv-measure-kept.py` (D7). Hardened by `/review-loop`, a codex pass and `/security-review` (its refusals, its two output blocks against their exact lists, its hash checks, its clearing between recordings and on a failure), then frozen by SHA-256 in one commit together with `sv_lib.py`.
  - The practitioner runs it over the installed app's kept recordings with both builds closed (the PowerShell command is given in chat) and relays the "For the record" block only. A status of `INCOMPLETE` gives no words: its reason code is relayed, the cause is fixed, and the script is run again. If a word reads `unmeasured`, their own "For you only" block says why, and they may run it again with `--allow-low-count`.
  - Expected: status COMPLETE, whether the override was given, and for each combination id its three words.
  - Recorded in a tracked file: the "For the record" block's content and nothing else (C1).
  - Frozen (2026-11-21, leg svx9; after `/review-loop` round 6, `/security-review` round 7 and the codex pass `stage-0.p1`, rounds 8–9, converged): `sv-measure-kept.py` pins, by SHA-256, `sv_lib.py` `f53244af0c2393ccafd6554e0f7d54dda56ea7b429616074edc07cb0b00a63c0`, `ffl_lib.py` `f7d2d75c4e1dbac9ba91413ee7f42d546fc7fc0575e3ffe0b6aba43314d38d03`, `ffl-measure-kept.py` `36e215c5fe92e0734f7161226c99b72b0fd956235c8a8630395ccb8df25f603d` and `sv_stitch.py` `8d0677307f1072bf7c643473338a23ae0019a9b5232e44217d3c33414a6ee414`. Its own SHA-256 changed when these were filled in; the composer records it at the freeze commit, and it is checked before the practitioner's run (Validation, Phase 0).
  - Frozen script (2026-11-21, composer, at the freeze commit): `sv-measure-kept.py` `18917bc55f849f6070aa56a905c369cdb0f87ad73793efc5f847457bb9d19d15`; its self-test with the real pins: 33 cases, 0 failures, `Pinned SHA-256 values: frozen`. A change to any of the five files needs a new freeze.
  - Not to be run again (2026-11-21, review round 16 MED-001): its premise compares scratch R0 with the product's pipeline. Since Phase 2 the product applies the recovery mark, so on Phase 2's or any later product it would report a difference for every recording with a score in the band. That difference is no defect. This task's run is done.
  - Done (practitioner), 2026-11-21: the frozen script run from a normal terminal, its SHA-256 checked against the frozen value first. The "For the record" block's content:
    - status COMPLETE; override not given;
    - K0: direction baseline, sanity met, against P1:R0 baseline;
    - P1:R0: direction not met, sanity met, against P1:R0 baseline;
    - P1:B1-45 and P1:B1-40: direction not met, sanity met, against P1:R0 adds;
    - P1:B1-35 and P1:B1-30: direction met, sanity met, against P1:R0 adds;
    - every P1:B2 row (B2-01 to B2-36) and every P1:B3 row (B3-01 to B3-36): direction met, sanity met, against P1:R0 adds.
- [x] 🟩 Task 0.7: The exit   [decision]
  - The brief, in plain English: every table against its bar; the release id D9's order gives and so what is built; what the selected row adds over the guided profile alone (D9); the calibrated part-consistency figure; the labelling-against-routing comparison (synthetic sets only) and the kept-consultation words; bars A2 and C as evidence for the follow-up plan; one paragraph stating the accepted residue with its three consequences (Accepted Assumptions).
  - Options: confirm the order's result / decline Lever B, which is the `R0` case, for a reason recorded by name. Labelling a consultation is not re-opened here; no option changes the consent text, a bar or the order.
  - Decide after: Tasks 0.5 and 0.6.
  - Blocks: Phases 1 and 2.
  - Records: the dated decision lines here and on `plan-practitioner-profile.md` (D3, D8, D13; D-P1 noted as unchanged).
  - Chosen: confirm B1-35 (2026-11-21); rationale: the practitioner's answer, "Confirm B1-35", to the composer's brief, the recommended option. The other option was guided enrolment only (`R0`, with a reason recorded by name).
  - The brief put to the practitioner before that answer:
    - Every bar's result, as recorded on Tasks 0.5 and 0.6.
    - D9's order: B1-45 and B1-40 fail on their kept direction word, and B1-35 is the first row that meets every line of bar B.
    - What B1-35 adds over the guided profile alone: +2.2 / +7.2 / +23.8 points of stitched recall (overall / quiet / close-turn) and the kept third word `adds`. Its seen-set cost is +0.42 point of other speakers labelled clinician. P1 at R0's own kept direction word is `not met`.
    - The calibrated part-consistency figure is 0.651 (lowest part: take a part 1, 0.701).
    - Labelling against routing: on the synthetic sets true labels change no note line, so routing, not labelling, leaves lines out. This build is not expected to fill an empty note on its own.
    - For the follow-up plan: bar A2 is met; bar C is not met (wrong-split rate 5.34 to 6.34 per 5 min against at most 1).
    - The accepted residue and its three consequences (Accepted Assumptions): (1) a patient line in a clinician-owned section with no warning; (2) in normal mode, a phrase learned from a patient's words; (3) in normal mode, a shorthand autofill rule. Shadow mode cannot show (2) or (3), so rubric R4 on the ten is read before shadow mode is turned off.
    - The version is 0.4.2, with no profile schema change.
  - Consequences:
    - Lever A is built (Phase 1), with Lever B row B1-35 (Phase 2; Task 2.1's built row is B1-35).
    - B1-35 reads one number per segment, so no speaker-model vector is kept (D4, C4). Phase 2's B2/B3-only parts (the owner, the collection helper, the live handover and their tests) and Task 5.2's B2/B3-only documents do not apply. Task 5.2's "Only with Lever B shipped" documents do.
    - Lever C and several stored vectors are not built here (the follow-up plan, Deferred).
    - The version is 0.4.2 (Task 5.1).
  - Recorded on `plan-practitioner-profile.md`: a dated decision line at D3, D8 and D13, and a note at D-P1 that it is unchanged (B1-35 is a recovery mark; the pass mark 0.50 does not move).

### Phase 1 — Guided enrolment (Lever A) — done 2026-11-21 (Tasks 1.1, 1.2, 1.4); its live smoke HELD and owed
- Phase 1 close (2026-11-21):
  - The code, review and peer work is done. `/review-loop` rounds 12–13 converged (3 LOW applied). Codex pass `stage-1.p1`, rounds 14–15, converged (PR-MED-4201 applied).
  - The composer's last suite run: 11156 passed, 9 skipped, 0 failed; the `test_shadow_exits.py` diff empty.
- The live smoke of the guided card on the developer build was NOT performed. The practitioner's words, 2026-11-21, verbatim: "can't smoke now, put it on hold and assume it's passed for now and let's move on".
  - The composer recorded the gate's disposition as `held-assumed-pass`. The smoke-pass record is marked HELD, not performed.
  - This is NOT a pass of the card. The smoke stays OWED and blocks the build of record (Task P.1, the run's Phase 6 stage).
  - Round 12's wording points (a) to (c) are put to the practitioner at that smoke.
- The held live smoke, performed 2026-11-24 on the developer build (relayed by the composer; recorded by leg sv9). The practitioner's words, verbatim, on the guided card: "for part b its a bit hard to read the text when walking around the table". Offered "Talk freely while moving" (part 5 free speech like part 6) or "Bigger text" (keep the passage, make it larger), they chose "Bigger text". They raised no change to round 12's wording points (a) to (c).
  - Built by leg sv9: the passage in a new theme role `reading` (`size_reading`, 16 pt against the 10 pt body; `ui/theme.py`, `ui/practitioner.py`), still plain text and not selectable; `TestGuidedCardWidth` now runs at 100 % and 150 % and requires each passage within one view's height. Review round 36.
  - The guided card's smoke is still OWED: NOT a pass until the practitioner re-checks the bigger text on the developer build. It still blocks Task P.1.
  - PASSED 2026-11-24 (composer): the composer's suite at `24415e4` was green (11177 passed, 9 skipped; ruff and mypy clean; the `test_shadow_exits.py` diff empty), then the practitioner re-checked the bigger passage text on the developer build. Their word, verbatim: "Pass". The held smoke of Phases 1 and 5 is cleared (smoke-pass record, performed). Round 12's wording points (a) to (c) stand as built.
- [x] 🟩 Task 1.1: The script, strings and part logic (Qt-free)
  - Done 2026-11-21 (leg sx1; run by the composer, verify=composer): `tests/test_enrolment.py` 38 passed; full suite 11153 passed, 9 skipped (0 failed, skip count unchanged); ruff and mypy clean (72 files).
  - Files: `desktop/src/scribe_desktop/ui/models.py` (`ENROLMENT_SCRIPT`, the per-part progress text with its denominator from the part, the fixed "keep reading" line, the "get ready" line, the weak-part line, the left-out line with its seconds, the strength line); `desktop/src/scribe_desktop/enrolment.py` (a part's typed result, the equal-weight combination, the part-consistency figures and the choice of the part to redo, the strength share; `enrol` and `record_enrolment` unchanged).
  - Expected: pure functions tested as a class: a zero or non-finite mean refused; a left-out part leaves the others' weights equal; the lowest part chosen for the redo, and again for the weakness line after it, the earlier on a tie; a replaced part's old seconds and segments gone from the sum and the strength share; the strength share is leave-one-part-out. D3.
  - Verification: new cases in `test_enrolment.py`; `ruff`, `mypy`.
- [x] 🟩 Task 1.2: The guided card and its worker
  - Done 2026-11-21 (leg sx1; run by the composer): `tests/test_ui_screens.py` 522 passed; full suite 11153 passed, 9 skipped; `git diff --stat -- desktop/tests/test_shadow_exits.py` empty; ruff and mypy clean.
  - Files: `desktop/src/scribe_desktop/ui/practitioner.py` (the card inside the existing "Record your voice" group, the per-part loop under one lease, the injected wait, D3's events and their slot, the one redo, the left-out rule, the save, the success result and its strength line); the `CaptureFn` seam gains the part's two limits by keyword, and the embed seam returns the typed per-part result. The seconds a left-out part reached are taken from the worker's last progress number for that part, never parsed from an exception's text.
  - Busy state. The held enrolment lease is the one busy test. From the press of Record until the lease is released, the tab's controls (Record, the consent box, the learning box, Confirm consent, Delete) are disabled and every handler that writes or deletes a profile returns without acting; none of this reads the worker thread's running state: today a finished worker whose result is still queued looks idle to the availability poll, and Delete could then remove a profile the handler is about to report as saved, and Confirm consent could write the cached old vector over the new one. A failed microphone handoff shows its error before the lease is released, like every other exit.
  - Expected: Flow 2 as written; every exit releases the lease after the tab re-renders; a part's audio is dropped before the next part (D3, C2, C8).
  - Named test changes in `test_ui_screens.py` `TestPractitionerScreen`: the progress text, the Record button's text, `capture.calls` (one call per attempt), the stored speech seconds, the busy-state list. New cases: Stop during a part and during a beat, lock during a beat; Stop during a re-record leaves the stored profile's encrypted bytes unchanged; at a part start and at a beat start the meter and counter read zero before any audio block arrives, and a late progress event from the previous part is dropped; a weak part redone with deterministic inputs, asserting the final profile, the stored seconds and the strength line; a redo that misses again (saved, the lowest remaining part named); a redo short at its cap (the first attempt kept); two parts under the figure (only the lowest redone); an optional part left out at its cap; both optional parts left out, each line showing its own seconds; a required part short at its cap; an embedding with no usable speech; a device failure; a failed microphone handoff (the error shown, then the lease released); the availability poll firing while a finished worker's result is still queued (the controls stay disabled, and Confirm consent with an out-of-date consent and a cached old profile writes nothing); the final save under the one lease; a re-record under a current consent record (the box already ticked).
  - Verification: the suite; `git diff` of `test_shadow_exits.py` empty.
- Task 1.3 (several vectors) is not part of this plan since review round 2: see Deferred.
- [x] 🟩 Task 1.4: The learning line says what the code tests
  - Done 2026-11-21 (leg sx1; run by the composer): `tests/test_enrolment.py` 38 passed (the line's pin in `TestEnrolmentScript`); full suite 11153 passed, 9 skipped.
  - Files: `desktop/src/scribe_desktop/ui/models.py` (`LEARNING_NOT_ATTRIBUTED_NOTE`: "Not learned: this line is not labelled as yours - only lines labelled as yours are learned."); the docstrings and comments in `note.py` (near :1688) and `ui/note.py` (near :89 and :111) that say a learner reads the practitioner's own lines, or that another speaker's line teaches nothing, restated in terms of the label. The consent text is not touched (C6).
  - Expected: no behaviour change. Any test that pins the old string moves with it, as a named change. Built on every exit: the label test applies with today's rule and a guided profile too.
  - Verification: the suite.

### Phase 2 — Matching within a consult (Lever B; skipped when the release id is `R0`) — done 2026-11-22 (Tasks 2.1, 2.2; committed `4c29283`)
- Built row (Task 0.7, 2026-11-21): B1-35, a recovery mark at 0.35. Phase 2 runs. Of Task 2.1, the parts for every built row and the B1 parts apply. The B2/B3 parts do not: the owner, the collection helper, `LiveResult`, `drain` and `stop`, the receiver's `finally`, their B2/B3 tests and C4's ownership tests.
- Phase 2 close (2026-11-21, leg sb4):
  - Built, reviewed and peer-converged: `/review-loop` rounds 16–17 (round 16's 1 MED and 1 LOW were plan text, applied) and codex pass `stage-2.p1`, round 18, with 0 findings.
  - The composer's last suite: 11176 passed, 9 skipped, 0 failed; `test_shadow_exits.py` unchanged.
  - No live smoke of its own: no screen changed. The labels' live check is Task P.3's mock smoke, and the live path is proved by Task 2.1's two-driver fixture.
  - Task 2.2's long run was owed, from the clean tree after the Phase 2 commit, on the practitioner's "start now". (2026-11-22, leg sb5: committed by the composer as `4c29283`, not pushed; Task 2.2 run there, PASS, 0 differences, 7 of 7 sets. Phase 2 is done.)
- [x] 🟩 Task 2.1: The built row
  - Built (2026-11-21, legs sb1 and sb2): `recover_practitioner_labels` and `RECOVERY_MARK = 0.35`, its one call in `assemble_transcript`'s attribution branch, the similarity docstring; the tests listed in the leg sb1 and sb2 handoff bullets. The B2/B3 parts do not apply (Phase 2's built-row line).
  - Verified 2026-11-21 (run by the composer, verify=composer): `tests/test_attribution.py tests/test_live_transcription.py` 213 passed; `tests/test_ui_screens.py` 531 passed; full suite 11176 passed, 9 skipped, 0 failed; `git diff --stat -- desktop/tests/test_shadow_exits.py desktop/src/scribe_desktop/speaker_eval.py` empty; the five frozen scratch files' SHA-256 values equal Task 0.6's pins; `sv-measure.py --self-test` 56 passed, 0 failed.
  - Files: `desktop/src/scribe_desktop/transcription.py` (the pure rule for the built row beside `attribute_speakers`, its one call inside `assemble_transcript`'s attribution branch so both drivers share it, and the similarity field's docstring, which before Phase 2 called the number the final cluster's mean, and now says the mean of the direct matches); `desktop/src/scribe_desktop/speaker_embedding.py` (the row's constants with their dated decision line; `ATTRIBUTION_THRESHOLD` and its test pin unchanged). For a B2 or B3 row also: the clearable owner, the collection helper, both drivers' use of it, `LiveResult`, `drain` and `stop` in `transcription.py`, and the receiver's `finally` in `desktop/src/scribe_desktop/ui/models.py`. `attribute_speakers`, `enrolled_cluster`, `label_speakers`, `transcript_before` and `speaker_eval.py` are not edited.
  - Where the grid is tested. Scratch tests the whole table as a class (`sv-measure.py --self-test`, before Task 0.4's pass): every row's parameters, every refusal to run, the order and the count of 76. The product tests only the built row, and only cases that row can reach.
  - Product tests for every built row: the no-match branch (nothing runs); the single-speaker shortcut after an empty slice, with scores that include one at or above the pass mark (nothing runs; labels and number as today); today's rule not confirming `speaker_1` (nothing runs); a `None` score; a segment at or above the pass mark never relabelled; the stored clinician and number equal to today's; one embedder call per segment that can be embedded and none for a slice under 25 ms, as today, with a fixture on both drivers that has a too-short middle slice followed by a segment the row relabels.
  - For a B1 row: a segment just at the mark, just under it, and at the pass mark; the acceptance invariant (over generated score lists, `enrolled_cluster` over the new labels always returns `speaker_1`).
  - For a B2 or B3 row: no seed; seed speech under the floor; every segment a seed; no segment under the low bar; a directionless vector; centres too alike; the equal-distance case when the built margin is 0.00; acceptance failing (today's labels restored whole). For a B3 row also: a 1.2 s seed between two other-speaker neighbours kept; a short direct match between two other-speaker neighbours kept; B3 after a B2 that a guard stopped (nothing); and a consult in which B2 forms its centres, changes no label anywhere, and smoothing alone changes one segment.
  - Both drivers: one deterministic fixture run through the batch driver and through the live worker and its receiver, in which a named text-bearing segment under the pass mark must change label (for a B3 row, a second one that changes by smoothing alone); the final labels, clinician and number are identical on the two paths. The Review screen's actual radio selection is asserted for a direct match, a relabelled consult and the no-match branch.
  - The trim pinned: trimming away the last direct match while relabelled practitioner text remains keeps the clinician and the number (D4).
  - C4's ownership pinned by tests (a B2 or B3 row): a normal seal (after the worker thread has exited the owner still holds its vectors, and `drain` hands them over); assembly success; assembly raising; the header read failing before assembly (a drained result never assembled); an abandoned result; Stop after the worker has published its result and before `drain` (the original owner is closed in place, and a `drain` that loses the lock gets no vectors); Stop during a `drain` that is blocked on a long window (Stop signals and returns in its bounded time); `buffers_cleared` false while the worker still owns vectors; Stop racing a returning window; Discard; a join timeout followed by the worker's exit (the timeout never reports cleared; the owner is closed when the worker exits); a batch collection failure before assembly; the batch fallback and recovery recomputing. Failures, each with the exception still held by the test and a weak reference showing the vector collected: a fake embedder that raises after producing a vector; a cosine that raises; and a successful collection followed by a failure elsewhere in the driver (the recogniser's next call).
  - The learning residue pinned as it is, with a synthetic patient line labelled the clinician's: in normal mode with consent and the opt-in on, Add or Move then Save admits its phrase subject to the refusal filter, and a typed Edit then Save can write its shorthand rule; with the opt-in off neither is written; on a shadow recording neither is written. No behaviour changes; the tests record the facts the threat model states.
  - Verification: the suite.
- [x] 🟩 Task 2.2: Scratch against product
  - Done 2026-11-22: PASS, 0 differences on 7 of 7 sets. The composer ran it on the practitioner's "Start now", detached, from the clean committed tree at `4c29283` (the Phase 2 commit; not pushed).
    - Command: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --sets --against-product --built C:/sv-sets < /dev/null`.
    - Started 2026-11-21T23:42:38+11:00, ended 2026-11-22T01:15:40+11:00 (about 93 minutes), exit 0, 183 `[progress]` lines.
    - Totals line, verbatim: `AGAINST-PRODUCT DIFFERENCES TOTAL: 0 (sets complete 7/7, errors 0, row B1-35)`.
    - Per set (encounters, encounters relabelled by B1-35, differences, errors, seconds; synthetic sets):
      - `scripts`: 50, 9, 0, 0, 848 s
      - `heldout`: 22, 1, 0, 0, 500 s
      - `heldout-2`: 22, 4, 0, 0, 863 s
      - `heldout-3`: 23, 5, 0, 0, 824 s
      - `heldout-4`: 22, 3, 0, 0, 823 s
      - `heldout-5`: 22, 5, 0, 0, 797 s
      - `heldout-6`: 22, 4, 0, 0, 916 s
      - In all, 183 encounters, of which 31 were relabelled.
    - Records (vector-free, a clean-HEAD run, so Task 4.1 may read them): `.cursor/loops/sv-out/after/4c292833486533ba678ca4dad28e617a53aa82d7/<set>/`.
  - Written (2026-11-21, leg sb1), then run as above: `sv-measure.py --sets --against-product --built C:/sv-sets`; the command and its expected output are in the leg sb1 handoff bullet. Its self-test passed (56 passed, 0 failed, composer, 2026-11-21), and review rounds 16–17 and peer round 18 read it. The long run was owed then: on the practitioner's "start now", from the clean tree after the Phase 2 commit (C9: in the background, lid open; `C:\sv-sets\` must still exist). (2026-11-22: run, PASS; see "Done" above.)
  - `sv-measure.py --sets --against-product`: one decode of each set with the built product; in the same pass scratch applies the built row in memory; 0 differences on the seven sets in labels, the confirmed clinician and the number. The same decode feeds Task 4.1's decode check and trace. A parity that cannot be made to pass is D9's fall-back case.

### Phase 3 — not in this plan
- Lever C (splitting a merged line) is measured in Phase 0 and built, if at all, by the follow-up plan (Deferred). The number is kept so that earlier review records still point at the right phase.

### Phase 4 — Regression — done 2026-11-23 (Tasks 4.1, 4.2, 4.3)
- [x] 🟩 Task 4.1: The seen sets, after
  - On the practitioner's "start now": D8's decode check, then its paired trace (the gate configuration overnight where D8 requires it), and D8's "after" harness reports for provenance. They are made from a clean checkout (`git status --porcelain` shows nothing but ignored files), whose commit is recorded as the verified commit together with the SHA-256 of each scratch file used (Task P.1 reads both); a run from a tree with uncommitted changes does not count.
  - Expected: the note path shown unchanged since Phase 0 (D8); the decode check at 0 differences for every set, the built row's own Phase 0 labels included, or its finding, with the check's own self-test showing that a word whose probability alone differs is reported; then a table of every difference between before and after, by encounter and configuration: the harness's outcome fields, the final note's placements by their identities, the next-patient columns (detected boundary and script tail), ambiguous lines, any `not evaluated` side, and the count of encounters equal by construction. A difference of D8's must-pause kind is surfaced to the practitioner and its disposition recorded before Phase P; no bar is changed. A disposition not to release Lever B is D9's fall-back case. A difference between the product and the built row's Phase 0 labels that survives the second decode sends the row back: it is requalified from a fresh Phase 0 pass, or the release falls back.
  - After Task 2.2 (2026-11-22, leg sb5):
    - `--trace` is not written yet: `sv-measure.py`'s docstring reserves it for this task's leg.
    - Task 2.2 already decoded every set once with the built product, from a clean checkout at `4c29283`. Its vector-free records (`sv-out/after/4c29283…/<set>/`) hold what the decode check compares: the spans, every word field, the scores, the branch, and scratch R0's, the built row's and the product's labels, clinician and number. So the leg can build the decode check to read those records against Phase 0's, with no new decode, as Task 2.2's line intends ("The same decode feeds Task 4.1's decode check and trace").
    - Two conditions for that reuse. First, `git diff 4c29283 HEAD -- desktop/` must be empty when it runs (a plan or scratch commit alone keeps it so). Second, `4c29283` is recorded as the verified commit, with the SHA-256 of each scratch file used.
    - What still needs a decode or a long run, each on the practitioner's word:
      - D8's re-decode of a set that differs, once, at the same commit.
      - Any replay input the records do not hold. The leg checks this first and names any gap; a gap means one more `--sets`-style decode of the sets concerned, about 8–15 minutes a set at Task 2.2's pace.
      - The paired trace's gate configuration (`--suggestions confirm-all --prose`, the language model) over the 31 relabelled encounters, overnight where D8 requires it.
      - D8's "after" harness reports: the seven sets with `--suggestions off`, then the gate configuration once.
      - The stages-off trace replays through the shipped provider, with no model.
    - If a later source change moves the verified commit (a hardening fix, Task P.1's list), Tasks 2.2 and 4.1 are repeated there.
  - Tooling written (2026-11-22, leg sg1), not yet run:
    - The leg read the code that wrote Task 2.2's records and found no gap: they hold every input both the decode check and the trace read, so no new decode is needed while `desktop/` is unchanged since `4c29283`. The fields not recorded (the document's session id, creation time, sample rate, speaker-model id) are read by no note, validation or phrase function.
    - `sv-measure.py --decode-check --verified 4c29283` and `sv-measure.py --trace --verified 4c29283 --built C:/sv-sets --config validation/config --stages off|gate`, with their logic in the new scratch module `sv_trace.py`.
    - The note path is checked mechanically: every definition the replay can reach, compared at the two commits with docstrings left out. `ui/note_review.py` is added to D8's list.
    - The commands, the expected output and the long runs are in the "Executor handoff (leg sg1)" bullet.
  - The decode check, run (2026-11-22, the composer, from the clean tree at `11c3827`; `desktop/` unchanged since the verified commit `4c29283`). Its part of the Expected line is met.
    - Command: `.venv/Scripts/python.exe .cursor/loops/sv-measure.py --decode-check --verified 4c29283 < /dev/null`, exit 0, after the self-test passed (70 passed, 0 failed).
    - Totals: `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`. That is 0 differences on each set: `scripts` 50, `heldout` 22, `heldout-2` 22, `heldout-3` 23, `heldout-4` 22, `heldout-5` 22, `heldout-6` 22, 183 encounters in all, the built row's own Phase 0 labels included.
    - The note path: `[note-path] executable changes on the note path: 0`. Two files changed since Phase 0 (`8bedfc4` to `4c29283`):
      - `note.py` +5 −2: the `spoken_by_confirmed_clinician` docstring only (Task 1.4's wording), read by the composer.
      - `ui/models.py` +212 −1, read by leg sg2. The one change on the note path is the wording constant `LEARNING_NOT_ATTRIBUTED_NOTE` (Task 1.4's text and its comment). It is the message text of the two learning verdicts (`ui/note_review.py` :302, :394), shown on the Review screen; no outcome field, placement or count the harness writes reads it.
      - Everything else in `ui/models.py` is new and not on the note path: Phase 1's `EnrolmentPart`, `ENROLMENT_SCRIPT`, `ENROLMENT_PART_NAMES`, the enrolment line constants and their eight text functions, and their `__all__` names. No reached definition names any of them.
    - The full output is in the git-ignored `.cursor/loops/sg1-decode-check.txt`; its JSON is `sv-out/after/4c29283…/decode-check.json`.
    - Still owed for this task, each on the practitioner's "start now": the paired trace (stages off, then the gate configuration) and D8's "after" harness reports. Task 4.1 stays 🟨 until they have run.
  - The long runs (2026-11-22, the composer, on the practitioner's "start now"). All were made from the clean tree, with `git diff 4c29283 HEAD -- desktop/ scripts/ validation/ extension/` empty. The outputs are git-ignored, under `.cursor/loops/`.
    - D8's "after" reports with `--suggestions off`, the seven sets (`sv-out/after/4c29283…/report-<set>.md`). Every encounter's verdict equals the "before" report's, except `heldout-6` `h6-22`, which goes from FAIL (silent omission) to PASS: an improvement.
      - SHA-256 of the seven reports, the composer's to add: (composer, 2026-11-22) all seven at commit `c8edce3` (no change under `desktop/`, `scripts/`, `validation/` or `extension/` since `4c29283`): in set order `scripts` to `heldout-6` (full values: `sha256sum .cursor/loops/sv-out/after/4c292833486533ba678ca4dad28e617a53aa82d7/report-*.md`; 0379c4c2ce290b3a1aa1eb06f8803ebfe2aa1ea8a88a15cd517d4494b2eccd13, 7555a9a0785fce94c8846e94c97b1de7e29f8d0fbbb22dade9487699354d8e64, c1020802da532e2c0d5538a3a3a6ba373205f3eefbd41e473d7c7c6f6d6fb1ee, 0c800732ee7516e1533903f341dc6c9ff64e3550a421398919b69f8dd1ab2b77, 66a4e3693408f9e2b7707cc002693d2556be6b210a239bb5eebaaec3fb8b0aad, 15747f55780d7a9cfeb88d3ba587ee01c3cde3931de67cebdddc20072f9cbb9e, e737dc4f691b5dbf8bbcd4e97a63e8eaf2504c644f8ac3cfef66f1c83661392f, in that order).
    - D8's "after" reports in the gate configuration (`--suggestions confirm-all --prose`; `sv-out/after/4c29283…/gate/report-<set>.md`):
      - `scripts` PASS;
      - `heldout`, `heldout-2`, `heldout-3`, `heldout-5` and `heldout-6` FAIL. `heldout-3` and `heldout-5` have the same failing encounters and set-level lines as run 9's record (`docs/testing/validation-harness.md`);
      - `heldout-4`: PENDING. Its first run was interrupted when the laptop slept on battery (13:09 to 20:34), five minutes in, and the composer stopped it. Its clean re-run (2026-11-22, 22:11 to 22:36, no sleep event in the System log during it) ended exit 1: rule v6 FAIL on no encounter, set-level R1 2 over the ceiling of 1, set-level errors 0, no stderr; the same verdict as run 9's record for this set in `docs/testing/validation-harness.md`. The interrupted first run's partial output was overwritten by the re-run.
      - SHA-256 of the gate reports, the composer's to add: (composer, 2026-11-22) six at commit `41a2dbe` and `heldout-4`'s clean re-run at `322206b` (plan-only commits; no change under `desktop/`, `scripts/`, `validation/` or `extension/` since `4c29283`), in set order `scripts` to `heldout-6`: c5c1b05f0f4ee3d306f8a623471f86405b5d99c4dbdd815fbb8c7d4e38de7197, 93708ab3fd9ebce598e93d10418ef824dafad4e3d69bbc05fc59d17cab1dbc7c, 9d66b96e40db97702a2b90c3f5fc4d28a62a55be5c69daefa1a44181da67c535, 743bdbac53f023946561f1636d813713e18e50b6d84728a73f069aac5a53e9a4, b5574753195eb3764cac679b2fdc55881dd30cd60017e734c597c75aea4e1424, 02119de2086b86f5e484b75fe457face73351e167ae69a1f7cb5515653d0f4ad, 260ee98450de284aebb4b96114a98d16ff28f63e8c9b6564f7ae03c947c08da9 (`sha256sum .cursor/loops/sv-out/after/4c292833486533ba678ca4dad28e617a53aa82d7/gate/report-*.md`).
    - (a) The stages-off paired trace, both runs: `TRACE OFF: traced 31, equal by construction 152, differing 31, must-pause 0, not evaluated 0, ambiguous lines 0, errors 0, sets not traced 0`, exit 0. The second run, with round 28's `sv_trace.py`, is identical apart from its hash line (`sv-p4-trace-off-2.txt`).
    - (b) The gate-configuration paired trace:
      - The first run errored on every side (`OfflineEnvError`, 31 errors). That is round 28's RUN-001, fixed in `sv_trace.py` (frozen again, `41a2dbe`).
      - The second run, exit 3: `TRACE GATE: traced 31, equal by construction 152, differing 31, must-pause 1, not evaluated 0, ambiguous lines 0, errors 0, sets not traced 0` (`sv-p4-trace-gate-2.txt`; record `sv-out/after/4c29283…/trace-gate.json`).
      - The one must-pause row is `heldout-4` `h4-06`: one line added in a clinician-owned section (Advice / home exercise). Its brief follows. Under D8 it is not closed as "explained": the practitioner's disposition is recorded before any release.
  - Must-pause brief (2026-11-22, leg sg13; round 29), for the practitioner's disposition. Nothing is decided here.
    - Recommendation: (a) Accept. It is the clinician's own word, now labelled as theirs, which is what the new rule is for. It sits beside the advice it starts, and it moves no fact, verdict or next-patient line.
    - The finding:
      - The case is one synthetic consultation (`heldout-4`, `h4-06`, a hip follow-up) in the gate configuration, where every suggested line is accepted.
      - The new build adds one line to Advice / home exercise that today's build leaves out: the single word "Great.".
      - With the suggestions off, the two builds' notes are the same.
    - The evidence, in plain English:
      - Who says it. The script's third line is the clinician's: "Great. You can bump the bridges up to three sets of twelve, and add the leg lifts lying on your side that we tried today." The speech recogniser cut "Great." off as its own half-second piece.
      - How it was labelled.
        - Today's build scored that piece 0.46 against the clinician's voice, below the 0.50 pass mark, so it labelled the piece as the patient's.
        - The new build labels it as the clinician's: it scores at least 0.35, and the clinician is already confirmed in this consultation (rule B1-35).
        - By the script, the new label is the right one. No other piece of this consultation changed label.
      - What the script expects. The script expects no fact on "Great.". The same line's fact, "three sets of twelve", is in the next piece, and it is unaffected.
      - How it reached Advice / home exercise.
        - No cue phrase routes "Great.", so with the suggestions off it is left out on both sides.
        - With the suggestions on, the local model proposed a section for it. Only two counts moved: the clinician's lines added by a suggestion went up, and the suggestions refused went down. The patient-line count did not move.
        - That fits the same suggestion being refused before and accepted after. Before, a line labelled as the patient's may not be added to a clinician-owned section. After, the line is the clinician's, and the gate configuration accepts every suggestion. The record holds which counts moved, not their values.
      - What did not change: no material fact was found or lost, no fact was wrongly present, no next-patient line appeared, nothing was ambiguous, and no verdict moved. Apart from the two suggestion counts, the fields that differ are the count of quoted lines and the seconds of the clinician's speech labelled as someone else's, which is the relabel itself.
      - In the app, a suggestion is only a mark on the line chooser. The clinician adds "Great." only by choosing it. The gate configuration accepts every suggestion, so it is the upper bound.
      - Classification: (i), a correct placement newly reached because the clinician's own speech is now labelled as theirs, the intended effect of B1-35. It is not (ii), a patient's line given to the clinician. It is the opposite of the accepted residue (1) in Accepted Assumptions. The one cost is clutter: a one-word acknowledgement can now be suggested into a clinician's section.
    - The question for the practitioner: "In one practice consultation, the new build lets the note's suggestions put your own word 'Great.', the start of your exercise advice, into Advice / home exercise. Before, the word was wrongly labelled as the patient's. No fact or verdict changes. Do you accept it?"
    - The options:
      - (a) Accept (Recommended). It is the clinician's own word, now placed with its own advice, and it is recorded by name.
        - Sets in motion: this dated disposition line here and in round 29; Task 4.1 closes once `heldout-4`'s gate report is read and its hashes are added; Phase 4 goes on to Tasks 4.2 and 4.3 (the practitioner's runs), then Phase 5, releasing B1-35 as 0.4.2.
      - (b) Accept, and add a follow-up. As (a), plus a Deferred item for a later plan: the suggestion stage should leave one-word acknowledgements ("Great.", "Okay") alone. Nothing is built here.
        - Sets in motion: as (a), plus the Deferred item and a line for Task 5.2's documents.
      - (c) Decline Lever B. The release becomes guided enrolment alone (`R0`).
        - Sets in motion: D9's fall-back. Phase 2's commits are reverted; every Lever B result is recorded as measured and not released; Tasks 4.1 and 4.3 are run again on the reverted tree.
        - Cost: B1-35's measured gain is lost (+2.2 / +7.2 / +23.8 points of stitched recall, overall / quiet / close-turn), and Phase 4 is repeated.
    - Disposition (2026-11-23, the practitioner): (a) Accept, their words "Accept (a)". The clinician's own "Great." placed in Advice / home exercise by an accepted suggestion is accepted by name; no Deferred item (option (b) not chosen). Recorded as the gate-disposition for `regression-must-pause` (2026-11-23T04:36:53+11:00). Phase 4 goes on to Tasks 4.2 and 4.3 (the practitioner's runs), then Phase 5.
  - Bar B's seen-set lines, after (2026-11-23, leg sg14; synthetic sets only). Bar B is pooled over the cohort.
    - It was settled at Task 0.5a and 0.5c for B1-35. No cohort encounter stops confirming. Clinician labelled other falls from 0.71 % to 0.12 %. Other labelled clinician rises from 0.61 % to 1.02 %, +0.42 point, within 0.5. Met.
    - Task 2.2's parity (0 differences in labels, clinician and number on all 183 encounters) makes those the product's figures. The "after" reports with `--suggestions off` confirm them, against the "before" reports in `sv-out/before/`:
      - Every encounter that confirms its clinician before still does: 183 of 183 are `measured` before and after, in every set (scripts 50, heldout 22, heldout-2 22, heldout-3 23, heldout-4 22, heldout-5 22, heldout-6 22).
      - Clinician speech labelled other (the reports' TOTAL rows, seconds) did not rise in any set. Before → after: scripts 12.0 → 2.0, heldout 0.7 → 0.0, heldout-2 4.8 → 0.4, heldout-3 4.7 → 0.3, heldout-4 3.9 → 0.5, heldout-5 4.8 → 1.4, heldout-6 4.6 → 1.6. Pooled: 35.5 → 6.2 s.
      - Other speech labelled clinician rose in four sets: scripts 7.4 → 9.3 (+1.9 s), heldout-2 2.2 → 5.9 (+3.7 s), heldout-4 1.7 → 5.6 (+3.9 s), heldout-5 1.6 → 4.0 (+2.4 s). It was unchanged in heldout (0.0), heldout-3 (1.9) and heldout-6 (2.2). Pooled: 17.0 → 28.9 s (+11.9 s).
      - As points, over Task 0.5a's pooled denominators (5,030.1 s of clinician speech, 2,830.5 s of other speech): clinician labelled other 0.71 % → 0.12 %; other labelled clinician 0.60 % → 1.02 %, +0.42 point, within 0.5.
        - 0.5a's 0.61 % reads 0.60 % here only because the reports round each seconds figure to one decimal.
        - Bar B is pooled, so no per-set line gates. The reports carry no per-set denominator, so the per-set rises are given in seconds.
    - Bar B's seen-set lines: met, and confirmed on the product. No must-pause.
- [x] 🟩 Task 4.2: Kept-recordings drift, an observation   [operator]
  - The practitioner runs `scripts\replay-kept-recordings.py` on the developer build as they have before, with the existing `me.wav` where the tool takes an enrolment file. The report stays in their terminal.
  - Recorded in the plan, one of three and nothing else (C1): `refused` (the tool stopped before reading anything; fix and run again), `incomplete` (run again), or `complete` with one comparison word, `no check errors` or `check errors`. No comparison word is recorded for a run that did not complete. It observes drift under the old-style profile against the archived transcripts; it proves no parity and says nothing about the guided profile (Task 4.3 does).
  - Done (2026-11-23, the practitioner, from a normal terminal at the clean checkout `98430c0`; `desktop/`, `scripts/`, `validation/` and `extension/` unchanged since `4c29283`): `complete`, `no check errors`. Nothing else is recorded (C1). The rest of the output stays with the practitioner and the composer.
- [x] 🟩 Task 4.3: Product parity on the stitched truth   [operator]
  - The practitioner runs `sv-measure.py --stitched --against-product` from a normal terminal with both builds closed (the PowerShell command is given in chat) and pastes its table. It imports the developer checkout's source at the verified commit; no app is launched and nothing is installed. The stitched dialogues go through the encrypted temporary store of D2, destroyed after the pass.
  - Expected: 0 differences between scratch and the product's own functions for the release id: the product's capture limits, per-part embedding and equal-weight combination over take A give scratch's P1, and the product's batch driver over the stitched dialogues gives scratch's labels, clinician and number; and the pools' recall and false-match figures for the release id equal the ones pasted at Task 0.5b.
  - What it does not claim: the guided worker's redo, or the live path. If take A's weakest part is under the calibrated figure, the app would ask for that part again, and no second recording exists for it; the table says so. The redo is covered by the suite's deterministic test (Task 1.2) and the live path by the two-driver fixture (Task 2.1).
  - The mode does not exist yet (2026-11-21, review round 16 MED-001; leg sb1's open point (1)). `sv-measure.py` refuses `--against-product` without `--sets`. Its `--stitched` mode runs the frozen `sv_stitch.py`, whose whole-run parity compares scratch R0 with the product and so fails wherever a segment scores in the band on Phase 2's product.
    - Task 4.3's leg builds the comparison first: the built row against the product's own functions over the stitched dialogues, under D2's custody, in a new scratch module beside the frozen ones, or under a new freeze.
    - It is hardened (review, peer pass, `/security-review`, as Task 0.6's script was) before the practitioner runs it.
    - Neither `sv_stitch.py` nor `sv-measure-kept.py` is edited or run for it.
  - The mode now exists (2026-11-22, leg sg1), not yet run, hardened or frozen.
    - `sv-measure.py --stitched <folder> --against-product`, its logic in the new scratch module `sv_stitch_product.py`.
    - It takes no `--enrolment`: take A comes from the folder's own manifest.
    - Before the practitioner's run: review, a peer pass and `/security-review`; then a freeze by SHA-256 of `sv-measure.py` and `sv_stitch_product.py` (the mode itself checks that `sv_lib.py` and `sv_stitch.py` are at their pins).
    - The leg sg1 bullet gives the command, the expected time and what is pasted.
    - Frozen (2026-11-22, after `/security-review` round 27; peer pass `stage-4.p1` accept-closed at its cap): `sv-measure.py` 545edf9374b4f90dd57628b173f2425698fc96605ca43e7af0509f944448be6e, `sv_trace.py` 8f2c3dd8dad59cf7c0487c89bc4c1c3877e62dac8834325787cdfd8703777866, `sv_stitch_product.py` fd7424e9dabb660466e859dcae329046286c92772358ff6b49459f12779bb5f6. Checked against them the same day: self-test 70 passed, 0 failed; the decode check at `4c29283` printed the first two values, 0 executable note-path changes and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`. Any run of Task 4.1's trace or Task 4.3's stitched mode must print these values; a later edit to any of the three is a new freeze.
    - Frozen again (2026-11-22, after round 28, RUN-001): `sv_trace.py` 6125230f5a286f6b338a72d11d36285e827ccde540905a621cd2a8dd0fbbde16; `sv-measure.py` (545edf93…be6e) and `sv_stitch_product.py` (fd7424e9…b5f6) unchanged. Checked against it the same day: self-test 70 passed, 0 failed; the decode check at `4c29283` printed the new `sv_trace.py` value, 0 executable note-path changes and `DECODE DIFFERENCES TOTAL: 0 (sets passed 7 of 7, row B1-35)`; the five frozen files unchanged. Task 4.1's trace runs from here on must print this value; Task 4.3's stitched mode keeps the round-27 values.
  - Done (2026-11-23, the practitioner). The run was `sv-measure.py --stitched <folder> --against-product`, from a normal terminal with both builds closed, at the clean checkout `98430c0`; `desktop/`, `scripts/`, `validation/` and `extension/` were unchanged since `4c29283`. The paste, relayed verbatim by the composer, is in the git-ignored `.cursor/loops/sv-p4-stitched-paste.txt`: numbers only, from the practitioner's own script recordings and a computer voice. It ends `STITCHED-PRODUCT PARITY: EQUAL` and `STITCHED-PRODUCT: COMPLETE`. Against the Expected line, item by item:
    - The product's capture limits equal scratch's: all six parts' target, cap and required flag `yes` (`limits equal yes`). Met.
    - The product's per-part embedding over take A equals the frozen measurement's: six of six parts kept on both, speech seconds equal, the largest vector difference 0.00e+00 on every part (`parts equal yes`). Met.
    - The product's equal-weight combination gives scratch's P1: the largest component difference 0.00e+00 against the 1e-06 tolerance, cosine 1.000000000 (`P1 equal yes`). Met.
    - The product's batch driver over the ten stitched dialogues gives scratch's labels, clinician and number: 0 differences on each dialogue, all on the match branch, six of them relabelled by the row (`PARITY DIFFERENCES TOTAL: 0 (dialogues 10)`). Met.
    - The pools' figures for the release id equal Task 0.5b's pasted ones (`pools equal yes`). B1-35, which gates: 98.6 % overall recall, 100.0 % quiet, 100.0 % close-turn, 0.0 % overall false match. R0, reported: 96.3 % / 92.8 % / 76.1 %, 0.0 %. Met.
    - Provenance: the commit `98430c0`, the checkout clean. The four digests that ran equal the freeze above: `sv-measure.py` 545edf93…be6e, `sv_stitch_product.py` fd7424e9…b5f6, and `sv_lib.py` and `sv_stitch.py` at their frozen values (`equal`). Met.
    - What it does not claim, as the task says: the redo. The table's own line reports the lowest kept part at 0.701 against the figure 0.651, so the app would not ask for a part again. The strength share shown after saving is 73.4 %.
    - Every item of the Expected line is met.

### Phase 5 — Version, documents, hardening
- [x] 🟩 Task 5.1: Version
  - The five version places and the two tests, to 0.4.2; one dated line on `plan-ui-refresh.md` (0.4.1 stays reserved). Confirmed at Task 0.7 (2026-11-21).
  - Written (2026-11-23, leg sv1), suite owed (verify=composer): the six fields in five files read 0.4.2 (`desktop/pyproject.toml`, `desktop/src/scribe_desktop/__init__.py`, `extension/package.json`, `extension/package-lock.json` ×2, `extension/src/manifest.ts`); the dated line is under `plan-ui-refresh.md`'s Phase 6 heading. ruff and mypy clean (72 files).
  - The two tests, found from the code (a trivial plan-against-code difference, noted, not a decision): `test_ui_shell.py` (:394, "The 0.4.0 landing rule, unchanged (D5)") and `test_ui_phase_s.py` (:1, "the fixes for the 0.4.0 live smoke's findings") carry "0.4.0" as HISTORY in docstrings, not as a version pin, so they are left unchanged: rewriting them would make them false. No test pins the version literal; `test_install_layout.py` reads `pyproject.toml` and checks `__version__`, the manifest and `package.json` against it, so it moves with the five places. The Key Findings' "two tests carry the string" was a grep for the string.
  - Verified 2026-11-23 (the composer, from the working tree with leg sv1's edits): desktop suite 11176 passed, 9 skipped, rc=0; extension `npm run qa` 13 files, 313 tests passed, rc=0; `git diff --stat -- desktop/tests/ desktop/src/` only `__init__.py` (one line); line endings unchanged.
- [x] 🟩 Task 5.2: Documents
  - Always, on every exit:
    - the guided enrolment: `docs/security/threat-model.md` (practitioner-profile surfaces 1, 2, 5 and 8: the capture, its limits and its memory bound), `docs/security/data-flow-map.md` (flow 12 with the new capture limits and its no-audio non-flow), `docs/security/retention-schedule.md` (the voice-profile row; the truth recordings as their own row beside the enrolment-WAV row), `docs/design-system.md` (the guided card);
    - learning rests on the speaker label, not on who spoke. That is true today and with `R0`, so every place that says a patient's line never reaches learning, or that only the practitioner's own lines or words are learned, is restated: threat-model surface 10 and its sibling statements (found by searching each document for "own lines", "own words", "never reaches" and "teaches nothing", and for any other promise about a patient's, carer's or interpreter's line, not by line number), `docs/security/data-flow-map.md` flows 13 and 15, its summary table and its learning non-flow, the retention schedule's learned-phrase and shorthand rows, and the source wording of Task 1.4;
    - the measurements: the threat model's "Kept recordings" section and flow 27 (the new kept-consultation script holds consultation vectors in memory under C4; the stitched dialogues' encrypted temporary store), `docs/testing/speaker-measurement.md`, `docs/testing/kept-recordings.md` (the new script, its two output blocks and what may be recorded), `docs/testing/validation-harness.md` (a dated measurement section, with bars A2 and C as measured for the follow-up plan);
    - `docs/release/pilot-builds.md` (the rollback note on a guided profile), `CHANGELOG.md`, `AGENTS.md`.
  - Only with Lever B shipped: the recovery mark or session rule, the larger exposure it gives the learning residue, with the three consequences; the trim case; the similarity number's meaning on a relabelled document (the mean of the direct matches, not of every line labelled the practitioner's) in the threat model, in `docs/testing/speaker-measurement.md` and in the transcript field's docstring (Task 2.1); `docs/security/data-flow-map.md` flows 7 and 14 (the pass); `docs/practice/clinician-review-guide.md` (speaker labels: a line may be labelled yours from the sound of this consultation; check the speaker before moving a line into your own sections; the practitioner's approval; with B1-35, Task 0.7, 2026-11-21: a line that scores just under the usual match may be labelled yours once your voice has matched in the consultation); the `docs/pilot/` findings register (one row: a patient line labelled the clinician's by the matching rule, controlled). As it really behaves (2026-11-21, review round 16 LOW-001, from leg sb2): such a line can teach both a phrase (Add or Move, then Save) and a shorthand rule (a typed Edit, then Save). The refusal filter's opener rule refuses a line opening with a capitalised word that is neither a common starter nor an admitted opener, a patient's "My …" for one, as name-like. That is the name heuristic, applied to every speaker's line; it is not a control on who spoke. The shorthand trigger (the line's last content words, `note_config.propose_rule_trigger`) goes through the same filter, but the opener rule reaches it only when the tail begins at the line's first word, as on a short line. A longer line's tail starts after its opener. The documents must not present the opener rule as a control on the residue.
  - Only with a B2 or B3 row shipped: the threat model's practitioner-profile surface 6 (it says today that no model embedding outlives a window: restated with C4's owner, its collection helper, its handover, its join-timeout case and its traceback rule); the retention schedule's in-memory row.
  - With release id `R0`: the documents say Lever B was measured and not built; no register row.
  - Line endings kept per file (`git ls-files --eol`).
  - Written (2026-11-23, leg sv1; the exit is B1-35, so "Always" and "Only with Lever B shipped"; the B2/B3 and `R0` lines do not apply). File by file in the "Executor handoff (leg sv1)" bullet. Two notes:
    - `docs/design-system.md` already describes the guided card (Phase 1's leg sx1, "A guided capture is one card"); nothing to add. The data-flow map's summary table holds no learning statement; nothing to restate there.
    - The sibling search found one more promise the build does not keep, outside Task 5.2's files: the patient-facing `docs/practice/privacy-information.md` says the program learns "never from anything you said". Recorded as a MUST-PAUSE in the handoff note; not edited.
  - Disposed (2026-11-23, the practitioner): (a), their words "Restate it (a)". Applied by leg sv2: `docs/practice/privacy-information.md`'s learning sentence restated (learning from lines labelled the practitioner's; now and then a patient's line labelled that way can be learned from; the practitioner can see and delete what is learned), and `docs/practice/README.md`'s 0.4.2 sentence (that change and the review guide's speaker-label line), both marked awaiting the practitioner's approval and the independent review. No test reads either file.
  - Verified 2026-11-23 on the composer's green run (Task 5.1's line); leg sv2's two practice-document edits are outside every test's reads (searched `desktop/tests/` and `extension/`), so no re-run is owed for them.
- [x] 🟩 Step H: Hardening pass (covers what the confirmed exit built; with release id `R0`, H3 is the enrolment's memory bound and lease)
  - [x] 🟩 H1: `/review-loop` to convergence
    - Done 2026-11-23: rounds 30–32 (legs sv3–sv6), converged at round 32; round 31 MED-001 disposed (a) by the practitioner, "Add a 0.4.2 line (Recommended)"; suite 11176 passed / 9 skipped (`ebcd30e`).
  - [x] 🟩 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [x] 🟩 H3: `/security-review` — C4's ownership and the enrolment's memory bound first
    - With B1-35 (Task 0.7, 2026-11-21; review round 10 LOW-002): no vector is kept and C4's owner is not built. So H3 covers the enrolment's memory bound and lease, and the recovery mark's two guarantees: it only adds `speaker_1` labels, and nothing runs without a confirmed match.
  - [x] 🟩 H4: cross-family codex re-check, code and documents as separate slices
    - Done 2026-11-23: H2 round 33 and H3 round 34 (leg sv7, nothing to change, `444400d`); codex pass `stage-5.p1` round 35 (two parallel slices in one activation; 2 LOW wording, applied by leg sv8) closed docs-only-low-close at peer round 1 of 5 (`45f72e0`). The live smoke of the two changed Review-screen lines is HELD with Phase 1's, the practitioner's words "Hold it (Recommended)" (smoke-pass record, held, not performed), owed before Task P.1.
    - Smoke PASSED 2026-11-24 on the developer build (relayed by the composer; recorded by leg sv9). The practitioner's words, verbatim: "yes it showed, both pass". The learning-on line ("Phrase learning is on: lines labelled as yours ...") was seen on a non-shadow recording, and the typed-edit config-line message ("Not learned: this line came from your own config, not from a transcript line labelled as yours.") on a shadow recording. Both read as written.

### Phase P — Release and restart (practitioner-run; runs on every exit, Lever A alone included)
- [ ] 🟥 Task P.1: Build of record   [operator]
  - OWED before this task (2026-11-21, leg sx5): Phase 1's live smoke of the guided card on the developer build must PASS before the build of record.
    - It was held at the Phase 1 close on the practitioner's word: "can't smoke now, put it on hold and assume it's passed for now and let's move on". It was not performed, and is not a pass.
    - At that smoke the practitioner also decides review round 12's wording points: (a) part 6's "Do not read." cue above the fixed "keep reading" line; (b) the self-written heading, get-ready, redo, weak-part and strength lines; (c) a required part's shortfall not naming the part.
    - A failure or a wording change goes back through the review and the suite before this task.
    - 2026-11-24 (leg sv9): the smoke was performed. The two Review-screen lines PASSED ("yes it showed, both pass"). The guided card did not pass as built: "for part b its a bit hard to read the text when walking around the table"; the practitioner chose "Bigger text", and leg sv9 built it (review round 36). They raised no change to round 12's wording points (a) to (c). Still OWED before this task: the practitioner's re-check of the bigger passage text on the developer build, at 150 % and 100 %, once the composer's suite is green.
    - 2026-11-24 (composer): CLEARED. The suite at `24415e4` was green (11177 passed, 9 skipped), and the practitioner's re-check of the bigger passage text passed, their word "Pass".
  - First, the release tree is the verified tree. The whole of `git diff <verified commit> <release commit>` is read, not two folders of it. Documents, tests and the version-only hunks of Task 5.1's places need no repeat. Any other difference (source, a dependency or packaging line, the extension's lockfile beyond its version lines, the model manifest, a hardening fix, a fall-back revert) means the measurements it can affect are repeated at the release commit before anything is pushed: Tasks 2.2 and 4.1 for a change to transcription, matching or the note path, Task 4.3 by the practitioner, the suite always. Documents and tests alone need no repeat.
  - 2026-11-24 (composer): the diff check, `git diff 4c29283 <release commit>` read whole (`4c29283` is Task 4.1's verified commit). Outside documents and tests it holds:
    - the version-only hunks of Task 5.1's places (`desktop/pyproject.toml`, `scribe_desktop/__init__.py`, `extension/package.json`, the two version lines of `extension/package-lock.json`, `extension/src/manifest.ts`): exempt;
    - comments and docstrings only, in `note_config.py`, `ui/note.py` and `ui/note_review.py`: inert;
    - two display strings, `ui/models.py` `LEARNING_ON_LINE` and the config-line message in `ui/note_review.py` `consider_rule_learning` (review rounds 30 and 32): screen text that no measurement reads;
    - the theme's `reading` role and `size_reading` token, and the guided card's passage set to it (`ui/theme.py`, `ui/practitioner.py`; leg sv9): display only.
    - None touches transcription, matching or the note's content, so Tasks 2.2, 4.1 and 4.3 are not repeated. The suite ran green at `24415e4`; the release commit adds only this plan's records. `npm run qa` last ran at Phase 5 (313 passed), and the extension has not changed since.
  - Then, on the practitioner's word: push, the `Release` workflow, the attestation check, the row in `docs/release/pilot-builds.md`.
- [ ] 🟥 Task P.2: Install   [operator]
  - The practitioner re-verifies the download from a normal terminal and installs after the day's last Complete or Discard, shadow mode on.
- [ ] 🟥 Task P.3: Re-enrol and smoke   [operator]
  - The practitioner re-enrols with the guided flow at the consulting seat, then a mock consultation (their voice and a computer voice; the composer gives the synthetic script and the Windows-voice command in chat). The mock supplies what the built row needs: first at least 40 s of the practitioner's normal speech in long lines, then at least 20 s of the computer voice, then five quiet practitioner lines of at least 3 s each, a computer-voice line between them.
  - Four operating checks, required on every exit, with no "proceed anyway": the six parts run and the profile saves; the strength line is shown; Stop during a second recording leaves the saved profile as it was (the practitioner takes the SHA-256 of the profile file before and after, with the PowerShell command given in chat, and records only whether the two were equal); shadow mode is on before and after. If one fails, the ten do not start: it is fixed (a new build goes back through Task P.1) or the release is rolled back.
  - Speaker-label observations, which the disposition below covers:
    - `failed`, on every exit: a computer-voice line that can be told apart on the screen sits under the practitioner's label (a wrong match seen directly).
    - `unevaluable`: the evidence is missing or cannot be read: the Review screen confirms no clinician, or the two voices' lines cannot be told apart. One more take; a second unevaluable take is recorded as that.
    - Required only with Lever B and an evaluable mock: at least three of the five quiet lines are labelled the practitioner's. Fewer is `failed`. This is an end-to-end outcome; that the built rule runs on the live path is proved by Task 2.1's two-driver fixture, not by this mock (a quiet line can also be a direct match).
    - With release id `R0`: the quiet lines are observed, never required.
    - Observed, never required: a left-out practitioner line drawing its warning (it depends on the line's content and position).
  - Recorded in the plan before Task P.4: the four operating checks as passed, and for the speaker labels `pass`, or the practitioner's disposition of a `failed` or `unevaluable` observation, in their words: proceed to the ten with the reason / hold / roll back to 0.4.0. A rollback because the guided profile is suspected includes recording a new profile on 0.4.0 and repeating the mock there (Config / Environment / Deployment Impact). Each disposition has a next step: `proceed` goes to Task P.4; `hold` returns to this task for a named re-check once its cause is dealt with; a final `roll back` goes straight to Task P.5, where the truth recordings are deleted and the plan closes on what was measured, and any later restart of the ten on 0.4.0 is recorded against that build on `plan-phase3a-note-pipeline.md`.
- [ ] 🟥 Task P.4: Restart the ten   [operator]
  - Only after Task P.3's recorded pass or disposition to proceed. A fresh config hash before the first score; one dated line on `plan-phase3a-note-pipeline.md` that the ten run on this build; C01.
- [ ] 🟥 Task P.5: Close
  - Reached from Task P.4, or directly from a final rollback at Task P.3. The dated decision lines, `/document`, the lifecycle state. The practitioner deletes the thirteen truth recordings by name (the `stronger-voice\` subfolder; `enrolment\me.wav` stays) and `C:\sv-sets\`.

## Retained Follow-Up Items
(Filled at completion.)

## Follow-Up Continuation Notes
(Filled at completion.)

---
*Plan saved to: .cursor/plans/plan-stronger-voice.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
