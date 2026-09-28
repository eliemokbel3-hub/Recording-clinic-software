# Design system — desktop app

The desktop companion's UI conventions, as built in Phase 2 and extended by the Phase-3A
note review UI, plus the Chrome-side UI of the Cliniko workflow safeguards plan (the side
panel, the page frame and the block — "Chrome side" below), which follows the same
interaction posture in a different toolkit. Each cue points at the code that owns it; the
code wins on any disagreement.

Suggested sections as this grows: surfaces & layout · dialogs · menus · forms & inputs ·
view patterns · tokens · microcopy.

## Surfaces & layout
- One window, tabbed: Microphone / Session / Recovery / Transcript / **Note** /
  **Practitioner** / **Clinics** / Status — `desktop/src/scribe_desktop/ui/main_window.py`.
  The Clinics tab (`ui/clinics.py`) is where each clinic's Cliniko API key is added,
  replaced or removed. No secondary
  windows; no new UI framework (PySide6 only, extending the Phase-1 status panel rather
  than replacing it). The Practitioner tab (`ui/practitioner.py`) is the one place the
  practitioner's OWN data is set up: consent, voice enrolment, deletion, and the learned
  phrases with their delete. A tab whose groups stack beyond one window height SCROLLS
  vertically inside a `QScrollArea` with every group at its natural height and the width
  following the window (no horizontal bar — long labels word-wrap); the Practitioner tab
  is the one that needs it today (nine groups; the Phase 4 live smoke found its lists
  collapsed to slivers at 1920×1200), the other tabs hold a handful of widgets or an
  expanding text view and do not.
- The **Note review tab** shows the generated note and the full uncertainty-marked
  transcript SIDE BY SIDE through the whole review, until copy or Complete —
  `ui/note.py`. This is presentational coverage of anything cue routing dropped: the
  clinician can always see a low-confidence phrase the note omitted; no automated
  check detects low-confidence or materiality omission (Check 4 `omission_warnings`
  separately flags omitted high-risk TOKENS — numbers, names, medications — in
  clinician-attributed segments, a different scoped heuristic).
- GUI-free view logic lives in `ui/models.py` (state→controls maps, list rendering,
  transcript rendering, readiness reports). Widgets stay thin so the logic is testable
  offscreen — every screen has offscreen tests, no real audio or ML in CI.
- Long work never blocks the UI thread: `ui/tasks.py` `TaskThread` with indeterminate
  progress (transcription, benchmark runs) or, for the voice enrolment capture, numbers
  marshalled back over a Qt signal (a level and a speech-seconds counter —
  `ui/practitioner.py`).

## Interaction posture
- **State drives enablement.** Controls are enabled/disabled from the session state
  machine, not from ad-hoc flags — `ui/models.py` state→controls map, applied in
  `ui/session_screen.py`. A control that would be invalid in the current state is
  disabled, not merely error-handling a bad click.
- **Refuse destructive actions during live work, with a reason.** Closing the window is
  refused while recording or paused, while a voice enrolment is in flight, and while any
  worker runs — transcription, note generation, prose rendering, a benchmark, a clinic key
  check or a Cliniko note check (`ui/main_window.py` `closeEvent`). With Unreviewed
  recordings, the first close is refused and lists each one's expiry time; a second close
  within 10 seconds quits (`models.CLOSE_CONFIRM_SECONDS`). The benchmark is refused while a session is active or an enrolment runs,
  and an enrolment is refused while a session or benchmark runs (`ui/microphone.py`,
  `session.py` `begin_enrolment`). The failure being prevented is lost consultation audio
  or a destroyed worker, so refusal beats a confirmation dialog.
- **First-run surfaces ask, never block.** With no voice profile the app opens on the
  Practitioner tab with a one-line banner saying what setting it up gains and that
  recording works without it; every other screen behaves as before (`ui/main_window.py`,
  `ui/models.py` `FIRST_RUN_BANNER`; plan D10). Consent is a visible checkbox directly
  above the action it gates, under the FULL ratified text shown verbatim
  (`ui/models.py` `CONSENT_TEXT_V3`, the current version; v1 and v2 are history); the action is disabled, not
  error-handled, until the box is ticked, and withdrawing consent is the visible Delete,
  not an un-tick (`ui/practitioner.py`). Only a READABLE profile's own consent record,
  carrying the CURRENT text version, pre-ticks the box — readable against the shipped
  speaker model's identity with the model file present (the tab's readiness probe); with
  the model absent or the profile made by another model the tab shows the fallback line
  and the record is neither shown nor changeable there (re-enrol or Delete) — a stored
  blob the app cannot read never does — presence is not consent — and a record for an
  OLDER text leaves the
  box unticked with a one-line notice asking for a fresh tick (`CONSENT_STALE_NOTICE`),
  with "Confirm consent" saving the new consent (and the learning opt-in) without a
  re-record.
- **Recording consent is per recording and never pre-ticked** (Cliniko workflow safeguards
  plan, Task 3.3; PLAN.md Flow 2 step 4). The Session screen's box, directly above Start
  under the verbatim text (`ui/models.py` `RECORDING_CONSENT_LABEL`), starts unticked,
  Start is disabled until it is ticked, and every Start press clears it — the explicit
  exception to "a stored consent record pre-ticks the box" above, because this consent
  belongs to one patient's recording and nothing stored may stand in for it. Above the
  box a plain-text line says whether the recording is linked to a Cliniko note; a desktop
  Start is always "Not linked to a Cliniko note", with a line saying it cannot be written
  back. No id is ever shown there, and a patient's name only from a note Cliniko verified
  (the Chrome link line, `ui/bridge.py`). A recovered session names its link
  status only after it is opened (the listing says "Cliniko link checked when opened").
  The side panel's box follows the same rule (Chrome side below).
- **Discard of a live recording takes two clicks.** The Session screen's Discard becomes
  "Confirm discard" for 10 seconds for the same session (`ui/session_screen.py`); the
  side panel's Discard previous becomes "Confirm discard" with the line
  "Discard this recording? This cannot be undone. Press Confirm discard to delete it." for
  15 seconds, and the second click travels to the app as `confirmed: true`
  (`extension/src/panel.ts`). The page block on Cliniko's page has NO Discard (round 57
  SEC-003, practitioner decision 2026-09-28): a script in Cliniko's page could collect
  clicks on a hidden block, so discarding stays on surfaces Cliniko cannot script — the
  side panel and the desktop. A disarmed button reverts silently; none of these
  deletes on one click. THREE desktop Discards act on ONE click, on a stopped session the
  practitioner has already selected or opened (round 60 PR-LOW-332): the Transcript
  screen's Discard (`ui/transcript.py`), and the Recovery tab's Discard in both its lists —
  the recoverable list and the Unreviewed list (`ui/recovery.py`; the Unreviewed one reuses
  the Recovery list's discard by Task 5.4's decision).
- **Edits over whole lines, with typing only OVER a line.** The Note tab's "Edit the note"
  group offers Add line / Remove line / Move / Edit / Undo: Add/Move/Remove work over whole
  transcript utterances under the router's ownership rule as before; Edit opens a one-line
  inline editor in the row (Enter applies, Escape cancels) and replaces that line or
  proposal with the clinician's own wording as a `clinician`-provenance line labelled
  `typed (clinician-authored)`, Undo restoring the original; there is still no free-text
  area — a typed line always stands in for a specific line, records what it replaced, and
  carries the clinician's own decision; the transcript panel stays a non-interactive text
  box; edits freeze at Save.
- **Pre-filled lines are marked, counted and ratified by one Save.** A line the
  practitioner's own config pre-filled renders with `[pre-filled by your config - …]` in
  the note body and in the line editor — under a prose style, where the line has become
  part of a paragraph, the section's prose block ends with `[includes N lines pre-filled
  by your config]` instead (`note.prefilled_section_mark`; the editor rows still name the
  lines) — has no confirm/decline row, offers Remove and Edit,
  and the Save button reads `Save - confirms the N pre-filled lines shown` while any stand
  (plain `Save note` otherwise); Remove is recorded as the clinician's decline at Save and
  demotes a learned rule to proposing (`ui/note.py`, `ui/models.py`; note-learning plan D5).
- **Say what was learned, and what was not, on the spot — and name the control that
  writes it.** After an add or a move the edit group's status line says either "Will
  learn '<phrase>' for <section> when you press Save note on this tab", "Not learned:
  contains a name/number/date/medication (<class>)", "Not learned: this line is not
  attributed to you …", or the one-line reason learning is off (naming the Practitioner
  tab) — a status line, never a modal, never a prompt (plan D9 as amended: auto-learn,
  review later). A typed shorthand the rules file would refuse is told so at the edit in
  the clinician's words per class — "Not learned: the typed wording reads as more than
  one claim (a dash, ';' or ':' between words, or several sentences) - keep one plain
  statement per line to learn it", "… is longer than a shorthand rule may hold (2,000
  characters at most)" (`note_config.plain_rule_problem`) — never the rules file's
  authoring message (a rule id, an entry position, the JSON override, "Value error"),
  which stays in the writer's record and the logs; the same check covers a correction
  to an already-learned shorthand (Phase H live smoke, 2026-09-26). While phrases are queued the learning line above it reads "N phrases
  queued - press Save note on this tab to learn them (Cancel, Delete and Complete learn
  nothing)": the live smoke of 2026-09-17 showed a queued phrase read as the outcome and
  the review left by another exit. On Save the same status line reports what was written,
  why the write failed, or — when lines were added but nothing queued — why nothing was
  learned. And when a review IS left by another exit with phrases still queued (Cancel,
  Delete-and-complete, Discard), the Transcript screen's status line — where the
  practitioner lands — gains "N queued phrases were not learned - only Save note on the
  Note tab learns them." after the exit's own message (plan Task 5.6; window close is
  exempt by practitioner decision: it already drops the whole unsaved draft). The "Not
  learned … (name)" note does not fire for a line opening with one of the practitioner's
  listed clinical openers ("Keep …", "Try …", "Ice …" — `LEARNING_OPENER_EXEMPTIONS`,
  Task 5.7) or with a listed contracted starter ("We're …", "I'll …", "Don't …" —
  `LEARNING_CONTRACTED_STARTERS`, Task 5.8); any other capitalised opener still does,
  and the transcript panel's own `[We're?]` mark is a different surface and stays.
- **What the app learned is listed where it can be deleted.** The Practitioner tab
  shows "Recently learned" (the last 20 phrases with section and date, newest first)
  and every learned phrase by section, each with a one-click Delete; the empty state
  says "No learned phrases yet." rather than hiding the lists (`ui/practitioner.py`).
- **A choice the app cannot honour yet is shown disabled with its reason, never
  hidden — and it enables itself the moment the reason goes away.** The Practitioner
  tab's "Writing style" radios list all four styles
  (Verbatim, Clean clinical, Own voice, Narrative); Own voice and Narrative are disabled
  with a one-line reason under the group — the local language model is not installed,
  and Own voice also needs a learned style — rather than omitted, and a saved style that
  is currently unavailable stays selected-but-disabled with the line saying notes are
  shown as Clean clinical until then; the choice is saved the moment a radio is picked
  and the status line says so (`ui/practitioner.py`, `ui/models.py` `style_options` /
  `read_note_style`; note-learning plan Flow 3, C8). The reason NAMES THE REMEDY (run
  `scripts/setup-models.py --only language-model` from a normal terminal and install
  the prose runtime), and since the practitioner does that outside the app, the tab's
  5 s availability poll re-checks `models.language_model_available()` — an import probe
  plus a stat of the model file, never a load and never a decrypt — and re-computes the
  options when that presence CHANGES, so the two prose radios enable without a restart
  (note-learning plan Task 4.4).
- **Learning from your own notes shows what will be kept before anything is saved,
  and asks about the originals separately.** The Practitioner tab's "Learn from my
  notes" group takes up to five `.txt`/`.docx`/`.pdf` files (a Cliniko PDF export is
  read as text; a scanned PDF is refused with "paste the text instead") or one pasted
  note, reads them (never copies them), and opens a review dialog listing the section
  headings found,
  the recognised shorthand, the unrecognised abbreviations as tick-to-keep rows
  (unticked by default) and the example sentences that passed the check unchanged
  with per-sentence remove; only that dialog's Save writes the learned style, under
  the consent box ticked above it — no voice profile needed. A SECOND dialog then
  lists the file paths with "Delete these files now" unticked by default; leaving it
  unticked keeps the files (`ui/style_review.py`, `ui/practitioner.py`; note-learning
  plan Flow 4, D9, D10).
- **What the app learned from your notes is listed where it can be removed, one item
  or all of it.** The "Learned style" group shows a one-line summary (learned date,
  source count, sentence count — never the text in the summary), the kept example
  sentences by section and the kept shorthand, each with Remove, and a confirmed
  "Delete learned style" that removes the whole store and leaves the voice profile
  alone; the summary and lists refresh after a learn, a remove, a delete or a consent
  renewal ("Confirm consent" re-seals the learned style with the current consent
  record, content untouched), never on a timer (`ui/practitioner.py`).
- **A confirmation line replaces a choice the app made for you, with a one-click way
  back.** When the clinician role is auto-confirmed from the voice profile, the manual
  radios are replaced by ONE plain-text line stating what was decided and the evidence
  (`Clinician: confirmed from your voice profile (similarity 0.xx) - change`) with a
  link-styled `change` that restores the manual controls (`ui/transcript.py`; plan D4).
  The line is always shown when the decision was made — never hidden behind a setting —
  and the value that justifies it sits on the line. When the decision could NOT be made
  (no model, a stale profile), a status line outside the controls says why and names the
  remedy, on every view that could show the transcript (`ui/models.py`, the D2 reason
  constants).
- **A secret is entered once and never shown again.** The Clinics tab's API-key field
  is password-masked, read once when Validate or Replace key is pressed and cleared at
  once (`setText("")`, which also clears its undo history); no list row or status line
  carries the key, and a line beside the field says that a PASTED key stays in Windows
  clipboard history until the practitioner clears it there (`ui/clinics.py`,
  `ui/models.py` `CLINIC_KEY_CLIPBOARD_ADVICE`). Nothing on the tab talks to Cliniko
  until one of those two buttons is pressed. Remove asks for a second click on the same
  button, relabelled "Confirm remove" (changing the selection disarms it), and is
  refused — with the reason, "Finish or discard the recording for <clinic> first." —
  while the live recording is linked to that clinic; every refusal names what to do
  (`ui/models.py` `clinic_refusal_line`; plan D10).
- **Never auto-resume recording.** Recovery offers resume-processing or discard only —
  `ui/recovery.py`. Restarting a microphone without the clinician's say-so is out of
  bounds.
- **Say what to do, not just what failed.** A dead input stream surfaces the actual
  remedy ("check Windows Settings > Privacy & security > Microphone"), and a silent-but-
  open stream surfaces a distinct "No signal" hint — `ui/microphone.py`. Latch such
  messages; do not hammer a retry loop.
- **Self-refreshing status.** Readiness panels poll rather than rendering once at
  construction (model report every 5 s, level meter at 100 ms, failure watcher at 500 ms).
  A panel that reports state must not be able to show a stale truth indefinitely — this
  cost a live debugging session when it did.
- **Confirmation shows exactly what will be inserted.** Each note proposal renders the
  exact insertable text, one bullet per assertion (never assembled prose), and the digest
  of what will be written is read from the RENDERED widget's text — never copied from the
  proposal — so a rendering bug is refusable at write time rather than silently saved
  (`ui/note.py`; the `_rendered_excerpt` / `shown_text_digest` path).
- **Group and summarise warnings; keep blocking distinct from advisory.** Review warnings
  are grouped by code and summarised, and blocking errors are presented distinctly from
  review warnings with each blocking state naming the action it blocks and how to clear it
  — warning fatigue is a real failure mode (`ui/models.py` `summarise_warnings` /
  `WARNING_COPY` / `complete_block_reason`).
- **Guard live custody with a controller lease, not a button flag.** A destructive or
  view-swapping action during a live generation/review is refused through the controller-
  owned `GenerationLease` (`session.py`), which spans the whole compose→review→write — a
  button-enabled flag cannot prevent a worker/GUI interleaving. Always offer a
  non-destructive escape (Cancel review and regenerate — keeps the queued transcript and
  key) alongside any destructive one (Delete note and complete without one).
- **Prose is rendered after the note is finalised, and Save waits for it.** With a
  prose style chosen, generating a note starts ONE rendering job and the style line
  under the note body says so — "Writing style 'Narrative': rendering the prose now -
  Save note is available once the prose is shown." — with Save disabled meanwhile and a
  click on it saying the same thing, because a note must never be saved with wording the
  practitioner has not read. When the job lands, the prose is DISPLAYED first and the
  line becomes "… prose shown for N sections, M sections shown as Clean clinical (the
  fidelity check refused the prose) …". A section whose prose failed the check stays as
  Clean clinical — its confirmed lines, unchanged — the line says so, and the review
  warning "A section is shown as Clean clinical because its prose did not pass the
  fidelity check" must be acknowledged like every other review warning. Editing a line
  re-renders only the section it changed. The language model failing to load, or Own
  voice with no learned style, is said on the SAME line and the note is shown as Clean
  clinical (`ui/note.py` `style_label`;
  `ui/models.py` `RENDERING_IN_FLIGHT_LINE` / `RENDERING_DONE_LINE` /
  `LANGUAGE_MODEL_LOAD_FAILED_LINE` / `STYLE_PROFILE_MISSING_LINE` /
  `SAVE_WHILE_RENDERING_MESSAGE`; note-learning plan Task 4.4, C8).
- **Live transcript is an append-only display under a header.** While recording, the
  Transcript tab shows the header `Live — updates while recording` and appends each
  transcribed window's lines (timestamps and `[word?]` marks, no speaker — attribution
  runs only when the recording ends) into the SAME non-interactive box; Discard clears it
  and the final transcript replaces it wholesale (`ui/transcript.py`, `ui/models.py`
  `format_live_segments`; note-learning plan Task 1.4).

## Chrome side (Cliniko workflow safeguards plan D1, D13; Phase 6)
The extension REPORTS and the app DECIDES: every button becomes a command the app may
refuse, and a refusal comes back as a line in the panel, never an error dialog.
- **The side panel carries consent and every control; Cliniko's page carries only the
  cue.** Chrome's global side panel (opened from the pinned icon) shows one of five
  layouts (`extension/src/panel-view.ts` `panelModel`, drawn by `panel.ts`):
  **Message** ("Clinic Scribe is not running — open it to record", with the hint that
  another Chrome profile may be connected; "Connecting to Clinic Scribe…"; "This clinic
  is not set up — add its key in Clinic Scribe's Clinics tab"; "Open a patient's
  treatment note to record"; "Save or cancel <patient>'s note review to start";
  "Restoring the safeguards on this tab…"; "Cliniko did not verify this note: <reason>.");
  **Checking** ("Checking with Cliniko…"); **Ready** — the patient, the appointment in
  local time with its zone ("No linked appointment" when none), the clinic, the
  verification line ("Note verified with Cliniko. It is checked again before anything is
  written back." or the could-not-be-reached wording — also the answer for a note checked in
  the minute after Cliniko says "too many requests", when that clinic's checks make no
  call; like any offline answer it stays until the note is checked again (open another
  note and come back), never clearing by itself; round 57 SEC-009), the consent box and
  Start;
  **Live** — "Recording" / "Paused" with a timer, the patient, "Consent confirmed
  <time>", Pause or Resume, Finish consultation and the hands-free lines, or
  "Finishing <patient>…" with NO timer; **Blocked** — mirrors the page block, plus the two-click Discard previous only the panel offers, and names
  both patients, the one "On screen" only while that note's tab is the one in front
  ("No Cliniko note in front" otherwise — round 60 PR-LOW-331). The **banner** "Unreviewed note for <patient> — Open for review" (or
  "Unreviewed recording for this note", or a count) shows only over Message or Ready
  and only while a Cliniko tab is in front. Ready shows only for the note in FRONT of the
  practitioner. A queued session shows "The last recording is waiting for review in
  Clinic Scribe." and never a timer.
- **The panel keeps its controls under the practitioner's hand.** While recording, the
  timer's text changes in place each second; the buttons are not redrawn, so keyboard
  focus on Pause or Finish consultation stays and a click in progress lands. Any other
  change redraws the panel, and focus returns to the same button only for the same
  session (`panel.ts`; round 60 PR-MED-330).
- **Recording consent in the panel is never pre-ticked** — the same explicit exception
  as the Session screen's box (Interaction posture above): the box sits directly above
  Start under PLAN.md's verbatim text, Start is disabled until it is ticked, and the tick
  is cleared by every Start press, whenever the note it was given for changes, and when
  the Ready layout goes away (`panel.ts`). Nothing stored ever ticks it.
- **The frame is a cue: red while recording, amber while paused or blocked.** A 3 px
  border round the Cliniko page, drawn by the page script in a closed shadow root
  (`extension/src/page.ts`). It is not a control — Cliniko's page can hide or cover it —
  and nothing depends on it being seen.
- **A patient change blocks the whole page until the practitioner chooses.** The block
  dims the page and shows a card: "Recording paused", the reason in plain words ("The
  recording's tab opened a different treatment note.", "The computer went to sleep.", "The computer
  was locked.", …), the two
  patients side by side (the recording's and this tab's — for a recording in another
  clinic only "Recording belongs to a patient in <clinic>"), and **Resume previous** and
  **Finish previous** — never Discard, which stays in the side panel's Blocked layout and on
  the desktop (round 57 SEC-003). Its buttons act only on a real click.
- **The machine's own pauses say so on the desktop, and waking or unlocking resumes
  nothing** (D5 as amended 2026-09-28). Sleep and the Windows session locking pause any
  recording, with the same desktop cue as every pause — the status line, the Session
  screen's message and a taskbar flash: "Paused - the computer went to sleep." / "Paused -
  the computer was locked.", followed by "Press Resume to carry on recording." (or, for a
  linked recording, the resume-on-its-own-note line). Resume stays a deliberate press.
  Between a lock and signing back in, every Resume — the Session tab's, the hotkey's and
  the side panel's — and every Start (the Session tab's and the side panel's) are refused by name: "The computer is
  locked - sign in, then press it again." (or, if the app cannot confirm the unlock, "…lock
  it and sign in again (Windows key + L), then press it again."); the panel shows the app's own refusal line
  (`CHROME_REFUSALS["locked"]` / `["lock_unknown"]`). A voice enrolment on the Practitioner
  tab stops on sleep or a lock as if Stop were pressed — "Enrolment stopped - nothing was
  saved." — and Record is refused while locked with "Cannot record now - voice enrolment
  refused: The computer is locked - sign in, then press it again." (round 57 SEC-019). If Windows refuses either notification, the Session screen says so in plain words and
  names what to do instead ("Pause the recording before you leave the computer.")
  (`ui/models.py` `PAUSE_CUES`, `SYSTEM_PAUSE_FAILED_LINES`).
- **The toolbar badge reflects the APP, not only the link**: green **OK** while it runs
  idle, grey **OFF** while it is closed, red **REC** while recording, amber **PAUSED**
  while paused or blocked, red **!** when the link drops under a live recording, **ERR**
  when the link failed, "…" while connecting (`extension/src/connection.ts` `badgeFor`).
- **Every string from the app is text.** The panel and the page script set every display
  string with `textContent`; a note-refusal or block-reason code the panel does not know
  shows a fallback line and an unknown warning code shows nothing — never the code itself
  (`panel-view.ts` `lookUp`); a refused command shows the app's own one-line message.

## Clinical-content rules (non-negotiable)
The two clinical surfaces are deliberately ASYMMETRIC, and the rationale drives every
rule below. The **transcript is raw evidence** — the model's best-effort record of what
was said, uncertainty marks and all — so it is DISPLAY-ONLY and never leaves the app: it
is not the artefact the clinician signs. The **note is ratified content** — every
non-transcript line confirmed by the clinician against the exact shown wording and passed
through the checking stage (`note_check.py`) — so it, and only it, may become copyable to
Cliniko, and only once the clinician has ratified it.
- Transcript text is display-only (`NoTextInteraction`) and cleared on close —
  `ui/transcript.py`. It is never logged, never written outside the encrypted store.
- The generated NOTE is the copyable surface — but ONLY while the recorded copy flag is on
  AND the note is fully ratified (no pending proposal, no blocking error, saved, no
  unacknowledged review warning). Until both hold, the note panel is `NoTextInteraction`
  and Copy is disabled; the guard lives in one predicate applied to both the button and
  the text-selection flags and re-checked at click time — `ui/note.py` `_copy_ready()`
  (`COPY_TO_CLINIKO_ENABLED` in `ui/models.py` is the recorded flag, `True` since the
  practitioner's 2026-09-27 decision; the Task-9.1 run is now a quality measurement, not an
  enablement gate — `docs/testing/shipping-gate.md`). The transcript panel is
  never copyable. Never widen copy to only-the-flag; disabling the button alone is
  insufficient because selectable text keeps native copy shortcuts. Every copy of note
  text — the Copy button, and Ctrl+C / Ctrl+Insert or the panel's own right-click Copy
  over the ratified note's selection (`ui/note.py` `_NotePanel`, whose menu replaces
  Qt's) — also carries the registered Windows formats that keep it out of Windows
  clipboard history and cloud clipboard sync (`ui/models.py` `clipboard_mime_formats`,
  Task 8.2); they do not stop another program of the same user reading the clipboard,
  and the note stays there until something replaces it.
- Provenance is visibly distinguished in the note — transcript-derived vs
  clinician-authored vs autofill/prefill — so the clinician can see the source of every
  line at a glance (`ui/note.py` / `ui/models.py` rendering).
- Uncertainty is visible, not hidden: low-confidence words, numbers, and names render as
  `[word?]` — `ui/models.py`. The clinician must be able to see what the model was unsure
  about at a glance.
- Speaker labels render per segment alongside timestamps. Today TWO speakers only — the
  diarizer clusters VAD segments into exactly two voices, so a third person in the room
  (parent, carer, interpreter, student) is silently merged into one of the two labels and
  the clinician fixes attribution at review. Decision D-S1 (estimate the speaker count
  instead of assuming two) is UNRESOLVED — it is blocked on the practitioner-supplied
  labelled recordings for Task 2.3 — so this stays two-speaker today; see the retained
  follow-up in `AGENTS.md`.

## Microcopy
- Plain clinical English, no jargon, no exclamation marks. Name the artefact the user
  cares about ("recording did not finish cleanly; the tail may be missing") rather than
  the internal cause (a missing store footer).
- Destructive actions are named for what they do — Complete and Discard, not OK/Cancel.
- A typed line's learning status names the trigger and the wording: "Will learn shorthand:
  '<trigger>' -> '<wording>' for <Section> when you press Save note on this tab"; a
  not-learned reason names the class ("the trigger contains a name/number/date/medication
  (<class>)", "the typed wording contains a number/date/medication (<class>)").
- A learning outcome names what was kept and what happened to the sources: "Learned
  style saved from 2 notes: 5 example sentence(s), 4 shorthand token(s). The original
  notes were kept." / "… Deleted 2 original file(s)."
- A disabled writing style names what it needs AND how to get it: "Own voice needs the
  local language model, which is not installed - run scripts/setup-models.py --only
  language-model from a normal terminal and install the prose runtime (AGENTS.md Local
  Run Steps); needs a learned style - teach the scribe your note style below first." —
  the reason, then the remedy.
- A rendering in flight says what is waiting on it, not just that it is busy: "Writing
  style 'Narrative': rendering the prose now - Save note is available once the prose is
  shown."; a click on the disabled Save repeats it ("The prose is still being rendered -
  Save note is available once it is shown.").
- A fidelity fallback names what the practitioner is looking at and what to do, never
  the refused wording: "A section is shown as Clean clinical because its prose did not
  pass the fidelity check" / "Read that section as shown (its confirmed lines,
  unchanged), then acknowledge."
