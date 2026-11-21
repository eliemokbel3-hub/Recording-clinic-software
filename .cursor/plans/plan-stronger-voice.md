# Feature Implementation Plan
**Feature:** stronger-voice (guided enrolment and matching within a consult; line splitting and several voice vectors measured for a follow-up plan)
**Overall Progress:** `50%`

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
- Last completed step: Phase 2's build and review (2026-11-21, legs sb1 to sb4): Task 2.1 (row B1-35) is 🟩 on the composer's green suite (11176 passed, 9 skipped). The `/review-loop` converged at round 17 (round 16: 1 MED and 1 LOW, both plan text, applied). The codex pass `stage-2.p1` converged at round 18 with 0 findings. Task 2.2's scratch mode is written and its self-test passes (56 passed), but its long run is owed, so Task 2.2 stays 🟨. Phase 2 has no live smoke of its own: no screen changed, and the labels' live check is Task P.3's mock smoke. Before that, Phase 1 (2026-11-21): Tasks 1.1, 1.2 and 1.4 are 🟩. The review converged at round 13 and the codex pass `stage-1.p1` at round 15. The suite passed: 11156 passed, 9 skipped. Its live smoke was HELD on the practitioner's word, not performed, and is owed before Task P.1. Before that, Phase 0 (2026-11-21): every Phase 0 task is done. Task 0.7's decision was "Confirm B1-35": Lever A is built with Lever B row B1-35, Lever C is not built, and the version is 0.4.2. Earlier: planning complete (Plan Mode with Fable, then `/review-plan`, 2026-11-20); codex plan peer-review rounds 1 to 5 applied (2026-11-20). Round 2 reduced the scope by two practitioner decisions: Lever C and several voice vectors are measured here and built by a follow-up plan.
- Current in-progress step: the Phase 2 close (2026-11-21). Phase 2's code is built, reviewed and peer-converged but not yet committed. Task 2.2's long run is owed. The product learns from a relabelled line (leg sb2). Phase 1 is closed and committed (`9fb3777`); the Phase 0 close is `8bedfc4`.
- Immediate next action: the composer's Phase 2 close: the history check, the flush, `/document` and the local commit. Then Task 2.2's long run on the practitioner's "start now", from the clean committed tree (`sv-measure.py --sets --against-product --built C:/sv-sets`, leg sb1's step 7). Then Phase 4. Phase 1's live smoke is HELD and OWED: it must pass before Task P.1 (see the Phase 1 close lines and Task P.1). The earlier entry, kept for the record: the practitioner chose to build ("Start the build", 2026-11-20) after the plan review reached its cap (findings per round 25, 32, 22, 23 and 17, none critical).
- Open blockers / open questions: Tasks 4.2 and 4.3 are the practitioner's runs. Tasks 0.1, 0.2 and 0.7 (decisions) and 0.3, 0.5b and 0.6 (runs) are done.
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
- Last plan sync: 2026-11-21
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

### Phase 2 — Matching within a consult (Lever B; skipped when the release id is `R0`)
- Built row (Task 0.7, 2026-11-21): B1-35, a recovery mark at 0.35. Phase 2 runs. Of Task 2.1, the parts for every built row and the B1 parts apply. The B2/B3 parts do not: the owner, the collection helper, `LiveResult`, `drain` and `stop`, the receiver's `finally`, their B2/B3 tests and C4's ownership tests.
- Phase 2 close (2026-11-21, leg sb4):
  - Built, reviewed and peer-converged: `/review-loop` rounds 16–17 (round 16's 1 MED and 1 LOW were plan text, applied) and codex pass `stage-2.p1`, round 18, with 0 findings.
  - The composer's last suite: 11176 passed, 9 skipped, 0 failed; `test_shadow_exits.py` unchanged.
  - No live smoke of its own: no screen changed. The labels' live check is Task P.3's mock smoke, and the live path is proved by Task 2.1's two-driver fixture.
  - Task 2.2's long run is owed, from the clean tree after the Phase 2 commit, on the practitioner's "start now".
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
- [ ] 🟨 Task 2.2: Scratch against product
  - Written (2026-11-21, leg sb1), not yet run: `sv-measure.py --sets --against-product --built C:/sv-sets`; the command and its expected output are in the leg sb1 handoff bullet. Its self-test passed (56 passed, 0 failed, composer, 2026-11-21), and review rounds 16–17 and peer round 18 read it. The long run is owed: on the practitioner's "start now", from the clean tree after the Phase 2 commit (C9: in the background, lid open; `C:\sv-sets\` must still exist).
  - `sv-measure.py --sets --against-product`: one decode of each set with the built product; in the same pass scratch applies the built row in memory; 0 differences on the seven sets in labels, the confirmed clinician and the number. The same decode feeds Task 4.1's decode check and trace. A parity that cannot be made to pass is D9's fall-back case.

### Phase 3 — not in this plan
- Lever C (splitting a merged line) is measured in Phase 0 and built, if at all, by the follow-up plan (Deferred). The number is kept so that earlier review records still point at the right phase.

### Phase 4 — Regression
- [ ] 🟥 Task 4.1: The seen sets, after
  - On the practitioner's "start now": D8's decode check, then its paired trace (the gate configuration overnight where D8 requires it), and D8's "after" harness reports for provenance. They are made from a clean checkout (`git status --porcelain` shows nothing but ignored files), whose commit is recorded as the verified commit together with the SHA-256 of each scratch file used (Task P.1 reads both); a run from a tree with uncommitted changes does not count.
  - Expected: the note path shown unchanged since Phase 0 (D8); the decode check at 0 differences for every set, the built row's own Phase 0 labels included, or its finding, with the check's own self-test showing that a word whose probability alone differs is reported; then a table of every difference between before and after, by encounter and configuration: the harness's outcome fields, the final note's placements by their identities, the next-patient columns (detected boundary and script tail), ambiguous lines, any `not evaluated` side, and the count of encounters equal by construction. A difference of D8's must-pause kind is surfaced to the practitioner and its disposition recorded before Phase P; no bar is changed. A disposition not to release Lever B is D9's fall-back case. A difference between the product and the built row's Phase 0 labels that survives the second decode sends the row back: it is requalified from a fresh Phase 0 pass, or the release falls back.
- [ ] 🟥 Task 4.2: Kept-recordings drift, an observation   [operator]
  - The practitioner runs `scripts\replay-kept-recordings.py` on the developer build as they have before, with the existing `me.wav` where the tool takes an enrolment file. The report stays in their terminal.
  - Recorded in the plan, one of three and nothing else (C1): `refused` (the tool stopped before reading anything; fix and run again), `incomplete` (run again), or `complete` with one comparison word, `no check errors` or `check errors`. No comparison word is recorded for a run that did not complete. It observes drift under the old-style profile against the archived transcripts; it proves no parity and says nothing about the guided profile (Task 4.3 does).
- [ ] 🟥 Task 4.3: Product parity on the stitched truth   [operator]
  - The practitioner runs `sv-measure.py --stitched --against-product` from a normal terminal with both builds closed (the PowerShell command is given in chat) and pastes its table. It imports the developer checkout's source at the verified commit; no app is launched and nothing is installed. The stitched dialogues go through the encrypted temporary store of D2, destroyed after the pass.
  - Expected: 0 differences between scratch and the product's own functions for the release id: the product's capture limits, per-part embedding and equal-weight combination over take A give scratch's P1, and the product's batch driver over the stitched dialogues gives scratch's labels, clinician and number; and the pools' recall and false-match figures for the release id equal the ones pasted at Task 0.5b.
  - What it does not claim: the guided worker's redo, or the live path. If take A's weakest part is under the calibrated figure, the app would ask for that part again, and no second recording exists for it; the table says so. The redo is covered by the suite's deterministic test (Task 1.2) and the live path by the two-driver fixture (Task 2.1).
  - The mode does not exist yet (2026-11-21, review round 16 MED-001; leg sb1's open point (1)). `sv-measure.py` refuses `--against-product` without `--sets`. Its `--stitched` mode runs the frozen `sv_stitch.py`, whose whole-run parity compares scratch R0 with the product and so fails wherever a segment scores in the band on Phase 2's product.
    - Task 4.3's leg builds the comparison first: the built row against the product's own functions over the stitched dialogues, under D2's custody, in a new scratch module beside the frozen ones, or under a new freeze.
    - It is hardened (review, peer pass, `/security-review`, as Task 0.6's script was) before the practitioner runs it.
    - Neither `sv_stitch.py` nor `sv-measure-kept.py` is edited or run for it.

### Phase 5 — Version, documents, hardening
- [ ] 🟥 Task 5.1: Version
  - The five version places and the two tests, to 0.4.2; one dated line on `plan-ui-refresh.md` (0.4.1 stays reserved). Confirmed at Task 0.7 (2026-11-21).
- [ ] 🟥 Task 5.2: Documents
  - Always, on every exit:
    - the guided enrolment: `docs/security/threat-model.md` (practitioner-profile surfaces 1, 2, 5 and 8: the capture, its limits and its memory bound), `docs/security/data-flow-map.md` (flow 12 with the new capture limits and its no-audio non-flow), `docs/security/retention-schedule.md` (the voice-profile row; the truth recordings as their own row beside the enrolment-WAV row), `docs/design-system.md` (the guided card);
    - learning rests on the speaker label, not on who spoke. That is true today and with `R0`, so every place that says a patient's line never reaches learning, or that only the practitioner's own lines or words are learned, is restated: threat-model surface 10 and its sibling statements (found by searching each document for "own lines", "own words", "never reaches" and "teaches nothing", and for any other promise about a patient's, carer's or interpreter's line, not by line number), `docs/security/data-flow-map.md` flows 13 and 15, its summary table and its learning non-flow, the retention schedule's learned-phrase and shorthand rows, and the source wording of Task 1.4;
    - the measurements: the threat model's "Kept recordings" section and flow 27 (the new kept-consultation script holds consultation vectors in memory under C4; the stitched dialogues' encrypted temporary store), `docs/testing/speaker-measurement.md`, `docs/testing/kept-recordings.md` (the new script, its two output blocks and what may be recorded), `docs/testing/validation-harness.md` (a dated measurement section, with bars A2 and C as measured for the follow-up plan);
    - `docs/release/pilot-builds.md` (the rollback note on a guided profile), `CHANGELOG.md`, `AGENTS.md`.
  - Only with Lever B shipped: the recovery mark or session rule, the larger exposure it gives the learning residue, with the three consequences; the trim case; the similarity number's meaning on a relabelled document (the mean of the direct matches, not of every line labelled the practitioner's) in the threat model, in `docs/testing/speaker-measurement.md` and in the transcript field's docstring (Task 2.1); `docs/security/data-flow-map.md` flows 7 and 14 (the pass); `docs/practice/clinician-review-guide.md` (speaker labels: a line may be labelled yours from the sound of this consultation; check the speaker before moving a line into your own sections; the practitioner's approval; with B1-35, Task 0.7, 2026-11-21: a line that scores just under the usual match may be labelled yours once your voice has matched in the consultation); the `docs/pilot/` findings register (one row: a patient line labelled the clinician's by the matching rule, controlled). As it really behaves (2026-11-21, review round 16 LOW-001, from leg sb2): such a line can teach both a phrase (Add or Move, then Save) and a shorthand rule (a typed Edit, then Save). The refusal filter's opener rule refuses a line opening with a capitalised word that is neither a common starter nor an admitted opener, a patient's "My …" for one, as name-like. That is the name heuristic, applied to every speaker's line; it is not a control on who spoke. The shorthand trigger (the line's last content words, `note_config.propose_rule_trigger`) goes through the same filter, but the opener rule reaches it only when the tail begins at the line's first word, as on a short line. A longer line's tail starts after its opener. The documents must not present the opener rule as a control on the residue.
  - Only with a B2 or B3 row shipped: the threat model's practitioner-profile surface 6 (it says today that no model embedding outlives a window: restated with C4's owner, its collection helper, its handover, its join-timeout case and its traceback rule); the retention schedule's in-memory row.
  - With release id `R0`: the documents say Lever B was measured and not built; no register row.
  - Line endings kept per file (`git ls-files --eol`).
- [ ] 🟥 Step H: Hardening pass (covers what the confirmed exit built; with release id `R0`, H3 is the enrolment's memory bound and lease)
  - [ ] 🟥 H1: `/review-loop` to convergence
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — C4's ownership and the enrolment's memory bound first
    - With B1-35 (Task 0.7, 2026-11-21; review round 10 LOW-002): no vector is kept and C4's owner is not built. So H3 covers the enrolment's memory bound and lease, and the recovery mark's two guarantees: it only adds `speaker_1` labels, and nothing runs without a confirmed match.
  - [ ] 🟥 H4: cross-family codex re-check, code and documents as separate slices

### Phase P — Release and restart (practitioner-run; runs on every exit, Lever A alone included)
- [ ] 🟥 Task P.1: Build of record   [operator]
  - OWED before this task (2026-11-21, leg sx5): Phase 1's live smoke of the guided card on the developer build must PASS before the build of record.
    - It was held at the Phase 1 close on the practitioner's word: "can't smoke now, put it on hold and assume it's passed for now and let's move on". It was not performed, and is not a pass.
    - At that smoke the practitioner also decides review round 12's wording points: (a) part 6's "Do not read." cue above the fixed "keep reading" line; (b) the self-written heading, get-ready, redo, weak-part and strength lines; (c) a required part's shortfall not naming the part.
    - A failure or a wording change goes back through the review and the suite before this task.
  - First, the release tree is the verified tree. The whole of `git diff <verified commit> <release commit>` is read, not two folders of it. Documents, tests and the version-only hunks of Task 5.1's places need no repeat. Any other difference (source, a dependency or packaging line, the extension's lockfile beyond its version lines, the model manifest, a hardening fix, a fall-back revert) means the measurements it can affect are repeated at the release commit before anything is pushed: Tasks 2.2 and 4.1 for a change to transcription, matching or the note path, Task 4.3 by the practitioner, the suite always. Documents and tests alone need no repeat.
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
