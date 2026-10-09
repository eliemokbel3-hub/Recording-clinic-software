# The pilot

PLAN.md Phase 7 asks for a pilot before Clinic Scribe goes into routine use at a
clinic: a validation run over at least 50 synthetic or mock encounters (here,
the 50 synthetic scripts — the mock role-play set was retired on 2026-10-09), 10
consented shadow consultations, 20 reviewed consultations per clinic, and routine
use only once every high-risk finding is resolved or explicitly controlled. The
plan that builds it is `.cursor/plans/plan-pilot.md`; the clinic 1 smoke that
replaced the role-plays is `.cursor/plans/plan-clinic-smoke.md`. This folder
holds the documents the pilot is run and judged with.

| Document | What it is | Filled where |
|---|---|---|
| [Pilot log template](pilot-log-template.md) | One row per pilot consultation: date, clinic, mode, app version, rubric scores, minutes, findings count | A copy OFF the repository (below) |
| [Findings register](findings-register.md) | Every finding of the pilot, with its severity, status and control | In the repository, here |
| [Exit gate](exit-gate.md) | The per-clinic checklist and signature line that opens routine use | In the repository, here |

## The run order

Every step is the practitioner's, from a normal terminal or Explorer (never an
agent shell — `docs/lessons.md`). Each step is a Phase P task of the plan, and its
result is recorded there as a dated RUN line.

1. **Install the pilot build (P.1).** The build of record 0.2.0 or later
   (`docs/release/pilot-builds.md`), verified before install. Check the Status
   tab shows the version and the "Shadow mode (pilot)" box (unticked), that an
   existing Past-sessions entry still opens and copies, and that the audit
   export has the two new columns with earlier rows as `normal`; then one
   shadow recording from the desktop and one from a disposable Cliniko draft
   (the plan's Task P.1 lists every check).
2. **The clinic 1 smoke (P.2).** The mock role-play set is retired
   (2026-10-09): no role-play is recorded. Its measurements come instead from
   real consultations of steps 4 and 5 whose recordings are kept with the
   patient's written consent (Part C of
   `docs/practice/development-recording-consent.md`). The target is about ten
   measured consultations — more than that document's "only occasionally"
   banner suggests, which your own review of 2026-10-09 settled for your own
   clinics (keeping recordings for development never ships to other
   practitioners).
   - **Before the first:** initial the shipping-gate addendum
     (`docs/testing/shipping-gate.md`); make a measurement folder on this
     computer's internal drive, outside your user profile and outside File
     History, Windows Backup and any synced folder, with two subfolders,
     `enrolment` and `audacity-temp`; set Audacity's temporary folder
     (Preferences, Directories) to `audacity-temp`, restart Audacity and check
     the setting; record yourself reading alone into `enrolment` (the
     reference for `--enrolment`); re-run the register script once
     (`AGENTS.md` run step 5).
   - **Who may be kept:** a recording is kept only if every person heard on it
     signed Part C. Someone who declines, or who joined after Start and was
     never asked, means Delete recording the same day, never Export. No
     recording of a child, or of someone who cannot consent for themselves, is
     kept while the consent document's reviewer note on them is open; if no
     consented recording with a third adult in the room comes along, the
     three-voice measurement is recorded as not measured, not as failed.
   - **One recording at a time** (the consent allows one unencrypted copy at a
     time): on the Past sessions tab export ONE kept recording to the
     measurement folder; after the success line rename it `k-01.wav` (then
     `k-02` …); label its speakers in Audacity and export the labels as
     `k-01.txt`; close Audacity WITHOUT saving a project, check that
     `audacity-temp` is empty, and never accept Audacity's crash recovery for
     a real recording; from the developer checkout with the installed app
     closed, run `scripts\measure-speakers.py` on the folder with
     `--enrolment` naming the WAV in `enrolment`
     (`docs/testing/speaker-measurement.md`); note the aggregate in your
     pilot log; delete the WAV and its labels, empty the Recycle Bin and clear
     Audacity's and Explorer's recent files; then write one line in your
     pilot log linking `k-01` to its log row and saying the export was
     deleted. A second export of the same consultation reuses its number and
     replaces its earlier result.
   - **Accents:** note in your pilot log, as ONE count over the measured
     recordings, how many had a speaker whose accent differs from yours —
     never per recording, and never in the repository.
   - **At the end:** confirm and freeze the measured set, give the composer
     the totals (the speaker numbers are written once, in the plans), decide
     D-S1, then delete the enrolment WAV and empty the Recycle Bin.
3. **The validation run (P.3).** Under rule v1 (decision 3.5, recorded in
   `docs/testing/validation-harness.md` and never adjusted after a run; its
   accent call amended on 2026-10-09), on the developer build from a clean,
   committed checkout with the installed app closed: the synthetic set only —
   the 50 scripts, `syn-41`…`syn-50` (added first, with a third installed
   voice as their patient) included — with `--rule
   validation\rules\option-a-proposed.json`. First (rule v1, call 1): write
   your own cue file into `validation\config` — fresh, never copied from the
   app's config folder; cue phrases only, as the repository is public —
   commit it, and have the scripts' routing checks re-run; the run is made
   from that commit or a later one. Before building, list the installed
   voices and go on only if every voice the scripts use matches the recorded
   baseline (`docs/testing/validation-harness.md`, step 1). Build the set
   into an empty folder outside the repository: it holds synthetic files
   only, never a kept recording or a copy of one (pilot plan Constraint 8);
   delete it after the run (it is rebuilt from the repository).
   Record the totals and pass or fail; enter every
   failure in the findings register. A fail stops the pilot here until its
   findings are resolved or controlled and the run is repeated.
4. **Ten shadow consultations at clinic 1 (P.4).** After P.3 passes (the
   consent sheet `patient-info-v2`,
   `docs/practice/patient-information-and-consent.md`, was approved on
   2026-10-07; its successor `patient-info-v3`, for 0.3.0's kept recordings,
   approved on 2026-10-09, replaces it). Tick "Shadow mode
   (pilot)" on the Status tab; for each consultation obtain consent with the
   current sheet and record its version in Cliniko, let the app draft its note, score it
   on the rubric at the scoring point, write your own note in Cliniko as usual,
   and add one log row. Untick the box afterwards. Check the writing style is
   `clean` before each Start: these ten scores are the Task 9.1 measurement
   (`docs/testing/shipping-gate.md`, its 2026-10-09 addendum — which also asks
   for the config hashes before the first and after the tenth); an attempt
   scored under another style, and P.1's two mock rows, are not among the ten.
5. **Twenty reviewed consultations at clinic 1 (P.5).** Shadow mode off; the
   consultation runs as everyday use does. One log row each.
6. **The clinic 1 exit gate (P.6).** Read and sign [exit-gate.md](exit-gate.md).
7. **Clinic 2 (P.7).** Once clinic 2's Cliniko API-key permission exists:
   install, its owed safeguards and draft-write smokes, twenty reviewed
   consultations and its own gate. Clinic 1 does not wait for it.

## Who does what

- **The practitioner** runs every step above, scores every note, keeps the
  filled pilot log, enters and closes findings, decided 3.5 and 3.6
  (2026-10-07; on 2026-10-09 the clinic 1 smoke superseded 3.6 and amended
  3.5's accent call) and signs each gate.
- **The developer (and the build agents)** build and fix the app, keep these
  templates and the register's format, and record each build of record. A
  finding's fix is a change to the app, a setting or a procedure — never a
  change to a past log row or a relaxed pass rule.
- **An independent reviewer** reviews `docs/practice/` before the first gate
  (P.6).

## What is kept where

- **The filled pilot log stays off the repository.** Copy the template into a
  file of your own — outside this repository and outside any synced or shared
  folder — and fill it there. It holds no name, no Cliniko or session id and
  nothing that was said, but it is your record of the pilot, not the
  repository's.
- **The findings register lives here, in the repository**, which is public. It
  holds no clinical content: no name, nothing said or written in a note, no
  Cliniko id and no session id. Describe what the app did in terms of the app
  (its category and the part of the app), never the patient.
- **Synthetic encounter ids** (`syn-01` …) may appear in the register; they
  identify invented content only. A real consultation's encounter is `—`, and
  a smoke measurement's `k-01` … name stays in your pilot log.
- **Real consultations are never fed to the validation harness** (pilot plan
  Constraint 8). Since 0.3.0 a real consultation's recording may be kept with
  the patient's written consent (`docs/practice/development-recording-consent.md`)
  and exported to a WAV for speaker labelling — on this computer's own
  drive, in the smoke's measurement folder (never a validation set folder),
  one copy at a time, deleted in its cycle (step 2); Constraint 8 records that
  reconciliation (2026-10-08). Each kept recording's 12-month review goes in the
  pilot log's "Kept recordings — review" table. The audit record's CSV export, which shows
  each recording's mode and app version, stays outside the repository too (it
  carries Cliniko ids).
