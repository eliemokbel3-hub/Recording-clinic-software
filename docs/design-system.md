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
  **Past sessions** / **Practitioner** / **Clinics** / Status —
  `desktop/src/scribe_desktop/ui/main_window.py`.
  The Clinics tab (`ui/clinics.py`) is where each clinic's Cliniko API key is added,
  replaced or removed (since 2026-09-30 it holds no draft-write setting: the
  "Starting text" group went with cliniko-draft-write D14, retired by D15). The **Past
  sessions** tab (`ui/past_sessions.py`, its Qt-free lines in `ui/past_sessions_view.py`;
  privacy-professional-controls plan Flow 5) is the look-back over completed sessions:
  the list (date + patient name, or "Patient hidden" under **Hide names**), the opened
  entry's generated note beside its saved note with the Cliniko write outcome, "Copy
  saved note" and "Show transcript", the two-click Delete now, the retention setting
  with its warning, Export audit record (CSV) and a status line. LEAVING the tab drops
  the opened entry's text and the names from every panel; opening it re-lists. Both the
  Status tab and the Past sessions tab head with the intended-use line ("Documentation
  aid, not clinical decision support. You review and finalise every note in Cliniko." —
  `ui/models.py` `INTENDED_USE_LINE`) and show the start-up exclusion warnings
  (`exclusions.py`) when there are any. No secondary
  windows beyond short confirmations: the Practitioner tab's delete questions, the
  learned-style review dialogs, and the Past sessions tab's two confirmations — lowering
  the retention setting and "Start a new audit record" — which name their buttons for
  what they do ("Delete older sessions" / "Start a new audit record" against "Keep
  things as they are", the safe one the default) — plus two file dialogs (the
  Practitioner tab's sample-note picker and Export's save dialog, which opens in
  Documents) and the start-up boxes shown before the window exists ("already
  running" and "cannot start", `app.py`; and, in the installed app only,
  "Clinic Scribe is not running from its install folder — reinstall Clinic
  Scribe." for a packaged copy started from anywhere but
  `C:\Program Files\ClinikoScribe` — `install_layout.NOT_INSTALLED_LINE`,
  installation plan Task 2.7). No new UI framework (PySide6 only, extending the Phase-1 status panel rather
  than replacing it). The Practitioner tab (`ui/practitioner.py`) is the one place the
  practitioner's OWN data is set up: consent, voice enrolment, deletion, and the learned
  phrases with their delete. A tab whose groups stack beyond one window height SCROLLS
  vertically inside a `QScrollArea` with every group at its natural height and the width
  following the window (no horizontal bar — long labels word-wrap); the Practitioner tab
  is the one that needs it today (nine groups; the Phase 4 live smoke found its lists
  collapsed to slivers at 1920×1200), the other tabs hold a handful of widgets or an
  expanding text view and do not.
- The **Note review tab** shows the generated note and the full uncertainty-marked
  transcript SIDE BY SIDE through the whole review, until copy, write or Complete —
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
  check, a Cliniko note check or a draft write to Cliniko, which has its own line
  ("A draft is being written to Cliniko. Wait for it to finish.") ahead of the generic
  one (`ui/main_window.py` `closeEvent`). With Unreviewed
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
  the Recovery list's discard by Task 5.4's decision). The Past sessions tab's **Delete
  now** follows the two-click pattern: it becomes "Confirm delete" for 10 seconds for the
  same entry with "Delete this past session now? Use Delete now only for a recording made
  in error - the wrong patient, a test, or one recorded without consent - because a kept
  transcript must otherwise be kept for at least 7 years. Its notes and transcript cannot
  be recovered. Press Confirm delete to delete it." (a selection change or the deadline
  disarms it, checked at the click), and the second click destroys the entry's key first
  (`ui/past_sessions.py`). A plain line under the button says the same limit ("Use Delete
  now only for a recording made in error: the wrong patient, a test, or one recorded
  without consent.", `DELETE_HELP`). Choosing "7 years" over "Until I delete them" is the
  other destructive choice there (the only two choices since the 7-year minimum,
  practitioner decision 2026-10-02): it asks first, names what goes ("Keep past sessions
  for only 7 years? Every kept session older than that is deleted now and cannot be
  recovered."), and a declined choice puts the setting back and writes nothing.
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
  `read_note_style`; note-learning plan Flow 3, C8). The reason NAMES THE REMEDY for
  this build (from a source checkout: run `scripts/setup-models.py --only
  language-model` from a normal terminal and install the prose runtime; in the
  installed app: reinstall Clinic Scribe — see the remedy bullet below), and since the practitioner does that outside the app, the tab's
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
  (`ui/models.py` `clinic_refusal_line`; plan D10). An empty key field is its own
  line — "Paste the clinic's Cliniko API key, then press Validate or Replace key." —
  never the bad-key line.
- **A write to a chart is one click, checked afresh, adds and never replaces, and
  never completes on its own** (cliniko-draft-write D2–D6, D15). The Note tab's
  button row carries "Write draft to Cliniko" beside Copy. The write keeps every
  answer already in the Cliniko note — typed text and the template's starting
  prompts alike — and puts the app's text below it after one empty line; an empty
  question simply takes the app's text. It is enabled only for a saved, ratified note of a LINKED
  recording (not a desktop Start, not the test provider) with no write or prose
  rendering in flight; when it is disabled, the reason is a persistent plain-text
  line under the buttons (and the tooltip), and a click that still arrives repeats
  it. A click shows "Checking the note with Cliniko …" then "Writing the draft to
  Cliniko …"; closing the window, the Transcript row, the Recovery screen and a
  Chrome Start / Discard / Open for review are refused while it runs, and the Session
  screen's Start and its consent tick are disabled (a tick already given stays ticked),
  with "A draft is being written to Cliniko. Wait for it to finish." as Start's tooltip
  (`ui/session_screen.py` `refresh`, re-run at both ends of the write). Success does
  NOT end the recording: the line becomes "Draft written to Cliniko. Reload the note
  page in Chrome; press Complete once you can see it there. If Cliniko says the note
  was updated elsewhere, choose Discard my changes." (an editor already open on the
  note holds the pre-write copy; Cliniko's own button keeps the written draft), Write
  stays disabled,
  Copy stays, and only the Transcript screen's Complete finishes the recording (the
  Session screen then reads "Draft written to Cliniko and this recording is
  complete. Past sessions shows what was kept. Review and finalise the note in
  Cliniko."). Every refusal is ONE line
  that names what happened and gives the next step — wait, try again, save, or fix
  the cause — and offers Copy where copying the note is the way forward (a refusal
  that only asks to wait, such as "A draft is being written to Cliniko. Wait for it
  to finish.", does not). Once the click has read the session's write record and it
  shows an earlier attempt whose outcome is unknown, the refusal lines that follow
  are prefixed "An earlier write may have reached Cliniko. Check the note there
  before copying anything." so a failed retry never invites a bare Copy; a refusal
  met before that read (a write already in flight, a stale click, an unlinked
  recording) and the lines that already say the outcome is open are not prefixed
  (`ui/note.py`, `ui/main_window.py`
  `_on_write_requested`; the lines are `ui/models.py` `WRITE_LINES`, Microcopy below).
  Once any write was attempted, the note is frozen: Regenerate (including
  "Regenerate (replaces the saved note)"), a second Save and "Delete note and complete
  without one" refuse with the `write_pending` line ("Cancel review and regenerate" is
  already disabled once the note is saved).
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
- **Start waits — briefly — while Clinic Scribe is getting ready.** Just after it opens,
  while the transcription software loads, every Start (the Session tab's and the side
  panel's) and a voice enrolment's Record are refused with one line, "Clinic Scribe is still getting ready - start again
  in a moment." (`START_GETTING_READY_MESSAGE`, Chrome code `getting_ready`); nothing is
  made, and the Session tab keeps its consent tick for the next press. The wait is
  bounded to 60 seconds after the loading starts (`ml_warmup.START_HOLD_SECONDS`,
  measured from the warm-up's start, which is moments after launch): after that a Start
  records even if loading has not finished, without live transcription, and the empty
  Transcript box says so without the header and without promising anything about the
  recording (`LIVE_TRANSCRIPT_NOT_READY_PLACEHOLDER`, worded like the other live
  fallback lines; installation plan rounds 35–38 MED-001, the practitioner's option
  (b)).
- **A Discard that must wait says so.** With live transcription running, a confirmed
  Discard first waits for it to stop (up to 10 seconds) so nothing is deleted while it
  still holds audio. The window stays responsive, and the Session tab shows
  "Discarding - stopping live transcription first..." above its progress bar
  (`DISCARD_STOPPING_LIVE_LINE`). Every Session control, every Chrome command (refused
  `busy`, "The app is busy with a recording - wait for it to finish."; a Start
  `session_active`), "Open for review" (`REVIEW_OPEN_DISCARDING_LINE`) and closing the
  window wait until it ends. If live transcription outlasts the wait, nothing is
  deleted. The recording has stopped and is kept, and the line says what to do:
  "Recording stopped, but live transcription did not stop in time, so nothing was
  deleted - the recording is kept. Press Discard again in a moment to delete it."
  (`DISCARD_KEPT_LIVE_STOPPING_MESSAGE`).
  It is never called a device failure. The next Discard takes the usual two clicks and
  is never retried automatically: a destructive step waits for a fresh confirmation
  (`ui/session_screen.py`; installation plan round 40 LOW-002).

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
Cliniko or be written into a linked Cliniko draft, and only once the clinician has
ratified it. The write's text comes from the same per-section renderer as Copy's
(`note.render_section_lines`) with the review apparatus switched off — no bullets,
provenance tags, pre-filled marks or "[includes …]" lines reach the chart.
- Transcript text is display-only (`NoTextInteraction`) and cleared on close —
  `ui/transcript.py`. It is never logged, never written outside the encrypted stores
  (the session, then — at Complete — its Past-sessions entry, under that entry's own
  key). The Past sessions tab shows a kept transcript only behind "Show transcript",
  also `NoTextInteraction`, and never copies it: its one Copy is "Copy saved note",
  through the same clipboard placement as the Note tab's Copy (`ui/note.py`
  `_place_note_text`), refused with its reason when no saved note was kept, the note
  has an unresolved error, or the copy flag is off.
- The generated NOTE is the copyable surface — but ONLY while the recorded copy flag is on
  AND the note is fully ratified (no pending proposal, no blocking error, saved, no
  unacknowledged review warning). Until both hold, the note panel is `NoTextInteraction`
  and Copy is disabled; the guard lives in one predicate applied to both the button and
  the text-selection flags and re-checked at click time — `ui/note.py` `_copy_allowed()`
  (`_copy_ready()` and not a shadow recording; Write reads `_copy_ready()` alone)
  (`COPY_TO_CLINIKO_ENABLED` in `ui/models.py` is the recorded flag, `True` since the
  practitioner's 2026-09-27 decision; the Task-9.1 run is now a quality measurement, not an
  enablement gate — `docs/testing/shipping-gate.md`). The transcript panel is
  never copyable. Never widen copy to only-the-flag; disabling the button alone is
  insufficient because selectable text keeps native copy shortcuts. Every copy of note
  text — the Copy button, Ctrl+C / Ctrl+Insert or the panel's own right-click Copy
  over the ratified note's selection (`ui/note.py` `_NotePanel`, whose menu replaces
  Qt's), the Past sessions tab's "Copy saved note", and the inline line editor's Copy
  and Cut of its selection (needing the copy flag but not ratification — the line is
  mid-edit; pilot review rounds 22–23) — also carries the registered Windows formats that keep it out of Windows
  clipboard history and cloud clipboard sync (`ui/models.py` `clipboard_mime_formats`,
  Task 8.2); they do not stop another program of the same user reading the clipboard,
  and the note stays there until something replaces it.
- No list or combo box copies its rows: every list in the app is `ui/lists.py`
  `NoCopyListWidget` and every combo box `NoCopyComboBox`, whose Copy shortcut does nothing
  (Qt's own would copy a row — a patient's name in Past sessions, Recover or Unreviewed, or a
  transcript line's first words in the Note tab's "Line:" popup — with a plain clipboard
  write). A new list or combo box uses them.
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
- Destructive actions are named for what they do — Complete and Discard, not OK/Cancel;
  Delete now / Confirm delete, and the confirmations' "Delete older sessions" / "Start a
  new audit record" against "Keep things as they are" (`ui/past_sessions_view.py`).
- Complete names where the session went, without claiming what one Complete kept (the
  screen does not know: a test-provider session keeps nothing, and a delete-note path
  never keeps the saved note): the tooltip "Verify the encrypted transcript, keep the
  transcript and notes in Past sessions (never the audio; a test-provider session keeps
  nothing), then delete the session and its key - the audio becomes unrecoverable.",
  the lines "Session completed: transcript verified and the session key destroyed - the
  audio cannot be recovered. Past sessions shows what was kept." and "Session completed
  without a note: transcript verified and the session key destroyed. Past sessions shows
  what was kept - never the saved note." (`ui/models.py` `COMPLETE_TOOLTIP` /
  `COMPLETE_DONE_LINE` / `COMPLETE_WITHOUT_NOTE_LINE`), and, when the copy's marker could
  not be removed after the key, "Completed. The Past-sessions copy will appear after the
  next check." (`COMPLETE_DEFERRED_LINE`).
- A Past-sessions line carries a date, the patient's name as the entry's label holds it
  (never under Hide names) and authored words — never an id, a path or exception text; a
  failure names its authored reason, and an error the app did not author reads the one
  fixed reason (`past_sessions_view.failure_reason`). The retention warning is pinned
  text: "A kept transcript becomes part of your health record - under the VIC Health
  Records Act 2001, the NSW HRIP Act 2002 and the ACT Health Records (Privacy and Access)
  Act 1997, and elsewhere APP 11.2. It can be reached by an APP 12 access request or a
  subpoena. Clinic Scribe keeps it, encrypted, only in this Windows login's data folder
  and makes no backup of its own - but backup or sync software, or a folder location it
  has warned about, can still copy the encrypted files. Cliniko stays the system of
  record. A kept transcript is kept for at least 7 years. If the patient was a child, it
  must be kept until they turn 25 - Clinic Scribe does not know a patient's age, so choose
  "Until I delete them" when that applies." (`RETENTION_WARNING`; it states the PROGRAM's
  behaviour — an encrypted copy made by other software is not prevented, only warned
  about where it can be seen; change it together with `docs/practice/`). The combo offers
  exactly "Until I delete them" and "7 years" (practitioner decision 2026-10-02). A
  settings file still holding a removed shorter setting adds the status line "Your
  earlier Past-sessions setting was shorter than 7 years, the minimum for a kept
  transcript, so past sessions are now kept for 7 years. Choose a setting below to save
  this." until a save (`RETENTION_RAISED_LINE`); a sweep refused for a window under 7
  years says "The retention setting is shorter than 7 years, so nothing was deleted by
  age." (`SWEEP_TOO_SHORT_LINE`).
- A custody action that fails on an error the app did not author (a disk, permission or
  store error) shows one fixed reason, "an unexpected problem on this computer stopped
  it", never the error's text or type: that text can name the session's directory. The
  app's own refusals and a microphone (capture) error keep their text — a capture error
  names only a device number and the audio driver's message (`ui/models.py`
  `custody_refusal_text`, shared by Start, Pause, Resume, Finish, Save, Complete and
  Discard; draft-write round 49).
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
- A missing or damaged model, runtime or Chrome link names the remedy for THIS build
  (installation plan Task 1.7, `install_layout.model_remedy` /
  `registration_remedy`): from a source checkout the developer script ("run
  scripts/setup-models.py[ --only <entry>] from a normal terminal" — the `--only`
  part when one model is named — "run
  scripts/register-native-host.py again from a normal terminal"); in the installed
  app "reinstall Clinic Scribe" — it never names a script the installed app does not
  have (so the installed Own-voice line above ends "… which is not installed -
  reinstall Clinic Scribe").
- The Status tab's link and protection lines (installation plan D9/D10/D6; no path is
  ever shown): "Registration: registered ✓ (per-user Chrome link)" or "(this
  computer's Chrome link)", with "; N other link(s) found, not used" when Chrome
  would pass over others; "Registration: NOT registered — <remedy>"; "Registration:
  not checked"; and in the installed app, when a per-user entry wins, a second line
  "Warning: a per-user Chrome link overrides the installed one." (`status.
  registration_lines`) — and when that per-user entry is also broken, the first line's
  remedy is "the per-user Chrome link that Chrome uses is broken, and reinstalling does
  not remove it", never "reinstall" (round 23: the installer writes HKLM only). The start-up warnings beside them include "Crash reports are
  not excluded for Clinic Scribe — <remedy>, then restart Clinic Scribe." and, in the
  installed app only, "Clinic Scribe's live recordings and logs are not marked to be
  left out of Windows backups and snapshots (a best-effort setting) — reinstall
  Clinic Scribe." / "… could not check whether …" — worded "marked to be left out",
  never "excluded from backups" (C5; `exclusions.py`).
- A developer build's Status tab (never the installed app's) adds the checkbox "Allow
  Cliniko writes from this developer build", off by default; a save that fails says
  "The developer build's write setting could not be saved; the box shows the setting
  in use." and re-reads the box from the file (`ui/main_window.py`
  `DEV_WRITES_CHECKBOX_TEXT` / `DEV_WRITES_SAVE_FAILED`). The developer build's
  extension is named "Clinic Scribe Companion (dev)" and is loaded in a separate
  Chrome profile.
- Shadow mode (pilot plan D1–D3, D13; both channels). The Status tab shows "Clinic
  Scribe version X.Y.Z" under its intended-use line and warnings, and has the
  checkbox "Shadow mode (pilot)", off by default; an unreadable setting reads as ON and says "The shadow-mode setting could
  not be read, so shadow mode is on. Untick the box to turn it off."; a failed save
  says "The shadow-mode setting could not be saved; the box shows the setting in use."
  and re-reads the box — or, when the file then cannot be read, shows the unreadable
  line instead (`ui/main_window.py` `SHADOW_MODE_*`). A recording takes the
  setting at Start and keeps it. The Session tab says, above Start while the setting
  is on, "Shadow mode is on: new recordings are shadow recordings - their notes cannot
  be copied or written to Cliniko.", and for a live or queued shadow recording (one
  reopened from Unreviewed included) "This is a shadow recording: its note cannot be copied or written to
  Cliniko." — the second line stays after the setting is turned off (`ui/models.py`
  `SHADOW_SETTING_LINE` / `SHADOW_RECORDING_LINE`); the Transcript tab shows that
  same second line, under the link line, for a recovered or reopened shadow recording
  (an unreadable record counts as one). The Note tab shows "This is a
  shadow recording for the pilot: its note cannot be copied or written to Cliniko, and
  saving it teaches the app nothing." under its buttons; Copy is disabled with the
  tooltip "This is a shadow recording for the pilot, so its note cannot be copied.",
  the note cannot be selected (so a keyboard or menu Copy has nothing to copy and
  places nothing), the line editor offers no Copy or Cut and no drag, Write says "This is a
  shadow recording for the pilot, so its note is not written to Cliniko. Write your
  own note in Cliniko as usual." (`shadow_session`, never `write_uncertain`-prefixed),
  and the learning line is "Not learned: shadow recording. Saving a shadow recording's
  note teaches the app nothing." — it names the recording's mode as the control,
  never a promise about Save. The Past sessions list marks the entry "(shadow
  recording)" and its Copy says "This was a shadow recording for the pilot, so its
  note cannot be copied. Read it as shown."
- The Microphone tab's hardware check reports whisper, then the prose stage
  (installation plan D11): "Prose stage (Narrative style): R of S sections, load L s
  (or model already loaded); sections W s wall, C s CPU; … per section OK|WARNING|
  FAIL", a NOTE above 5 s per section and a WARNING at 10 s or more ("They stay
  local; the Clean clinical style does not use the language model."), "Prose stage:
  not timed - <reason>" when it could not run (never an "OK"), and one verdict line
  "Hardware check: whisper medium RTF x.xx OK; prose stage y.y s per section OK". A
  slow prose stage adds "The prose writing styles are slow on this machine. They stay
  local; the Clean clinical style does not wait for them." to the warning label. Only
  timings — never text the model wrote (`benchmark.py`, `ui/microphone.py`). Run it
  with no prose rendering in flight on the Note tab: the two share the one loaded
  model, so a section's time would include the wait for the other's call and could
  read slower than the machine is (accepted, round 22).
- The installer's words (`packaging/scribe.iss`; the app never runs elevated, so
  these are the installer's own pages): a running app or Chrome refuses with "Close
  Clinic Scribe and Chrome completely, then run Setup again." plus the background-
  Chrome hint, and a check that cannot run refuses the same way; a missing or
  damaged model pack refuses with "… Nothing was changed."; the Finish page says
  "Clinic Scribe is installed." (or "updated.") with the Chrome step and "Open Clinic
  Scribe from the Start menu." — never a Launch option — or "Clinic Scribe is NOT
  completely installed." when a model copy failed (Setup then also exits 9, or 10
  when the clinic-only setting it set earlier could not be removed — never its
  success code); the clinic-only checkbox says it makes Chrome show "managed by your
  organization" and to leave it unticked on a computer you also develop on;
  uninstall ends "Your sessions, Past sessions and audit record were left in your
  Windows profile, unchanged." — no retention period is claimed there.
- A rendering in flight says what is waiting on it, not just that it is busy: "Writing
  style 'Narrative': rendering the prose now - Save note is available once the prose is
  shown."; a click on the disabled Save repeats it ("The prose is still being rendered -
  Save note is available once it is shown.").
- A fidelity fallback names what the practitioner is looking at and what to do, never
  the refused wording: "A section is shown as Clean clinical because its prose did not
  pass the fidelity check" / "Read that section as shown (its confirmed lines,
  unchanged), then acknowledge."
- The draft write's lines (`ui/models.py` `WRITE_LINES`, the ONE source; no id,
  patient or practitioner name, answer text or key is ever formatted into one). Each
  refusal gives its next step, and offers Copy where copying the note is the way
  forward; the wait-only and save-first lines do not. The `write_uncertain` prefix is
  added only to the lines `ui/models.py` `WRITE_UNCERTAIN_PREFIXED` names, and only
  once the record read shows an open attempt:
  - button and progress: "Write draft to Cliniko"; "Checking the note with Cliniko …";
    "Writing the draft to Cliniko …";
  - outcome: "Draft written to Cliniko. Reload the note page in Chrome; press Complete
    once you can see it there. If Cliniko says the note was updated elsewhere, choose
    Discard my changes." (`written_seen`); after that Complete, on the Session
    screen, "Draft written to Cliniko and this recording is complete. Past sessions
    shows what was kept. Review and finalise the note in Cliniko." (`written_done`);
    "The write did not confirm.
    Nothing is lost - press Write again to check the note before anything is sent."
    (`unknown`);
  - before the write: "Save the note first."; "This recording is not linked to a
    Cliniko note. Copy the note instead."; "This note came from the test provider and
    cannot be written to a chart."; in a developer build only (a source checkout;
    installation plan D4), "Writing to Cliniko is off in this developer build. To
    allow it, tick "Allow Cliniko writes from this developer build" on the Status
    tab, or copy the note instead." (`dev_build_writes_off`; Write disabled; it
    follows the record's own lines, and it carries the `write_uncertain` prefix
    while an earlier attempt is open, like every Copy-inviting line); "A draft is being written to Cliniko. Wait for it
    to finish."; "A recovered recording is still being processed. Wait for it to
    finish, then write."; "A key check for this clinic is running on the Clinics tab.
    Wait for it to finish, then write."; "Cliniko is rate-limiting this clinic. Try
    again in N s."; "The write stopped on this computer before anything was sent to
    Cliniko. Copy the note, or try again." (`not_sent`);
  - the note check: "The note could not be checked with Cliniko just now (<reason>).
    Copy the note, or try again." for a cause that can pass, and "Cliniko shows that
    this note cannot take the draft (<reason>). Copy the note instead." for one that
    cannot — final, archived, another patient or practitioner (the practitioner
    confirms this wording at Task P.2);
  - the note's content: "A question in the Cliniko note holds something the app cannot
    read, so nothing was written. Copy the note instead." (`note_unreadable`); "This
    note has no content that maps to the Cliniko template, so there is nothing to
    write. Copy the note instead."; "Cliniko did not take the draft (<cause>). Copy the
    note instead.";
  - Cliniko's answer: "The note was finalised in Cliniko before the write reached it,
    so the draft was not written. Copy the note instead."; "Cliniko refused the write
    although the note is still a draft - this clinic's key may not be allowed to edit
    notes. Copy the note instead.";
  - uncertainty: "An earlier write may have reached Cliniko. Check the note there
    before copying anything." (the prefix once the record read shows an open
    attempt; also its own refusal when the note re-reads as neither written nor as
    that attempt read it); "The record of
    this recording's earlier write cannot be read, so its outcome cannot be checked.
    Look at the note in Cliniko before copying anything."; "A write to Cliniko was
    attempted for this note, so it can no longer be changed or regenerated here. Copy
    it, complete the recording or discard it." (`write_pending`).
