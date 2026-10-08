# The pilot

PLAN.md Phase 7 asks for a pilot before Clinic Scribe goes into routine use at a
clinic: a validation run over at least 50 synthetic or mock encounters, 10
consented shadow consultations, 20 reviewed consultations per clinic, and routine
use only once every high-risk finding is resolved or explicitly controlled. The
plan that builds it is `.cursor/plans/plan-pilot.md`; this folder holds the
documents the pilot is run and judged with.

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
2. **The role-play set (P.2).** About 10 mock consultations with a second
   person as the patient, recorded live in the app and scored on the
   shipping-gate rubric (`docs/testing/shipping-gate.md`), captured in parallel
   as labelled WAVs for the speaker measurement
   (`docs/testing/speaker-measurement.md`) and the validation run. Before
   recording (decision 3.6): every person other than you whose voice is
   recorded — the second person, and the third voice in the one three-voice
   role-play — agrees that their voice recordings are kept for this purpose —
   in one folder on the clinic computer,
   outside the repository and any synced folder — and deleted at the end point
   (D-S1 decided and Phase 3B's gate has re-used them), with a review at the
   clinic 1 exit gate or 12 months after recording, whichever comes first.
   At least one role-play speaker's accent differs from yours (rule v1, call 3);
   record each speaker's accent in broad terms (no name) with the task's
   records.
3. **The validation run (P.3).** Under rule v1 (decision 3.5, recorded in
   `docs/testing/validation-harness.md` and never adjusted after a run), on the
   developer build from a clean, committed checkout with the installed app
   closed: at least 50 encounters, with `--rule
   validation\rules\option-a-proposed.json`. First (rule v1, call 1): write
   your own cue file into `validation\config` — fresh, never copied from the
   app's config folder; cue phrases only, as the repository is public —
   commit it, and have the scripts' routing checks re-run. The harness reads
   one set folder: build the synthetic set INTO the role-play folder of step
   2, so the role-play recordings stay in their one folder (decision 3.6) — or
   delete any copy of them made for the run once it is done. Keep the
   enrolment WAV in a subfolder there (the harness reads only the top level;
   a lone WAV would fail the run), and after the run delete the synthetic
   `syn-*` files from the folder (they are rebuilt from the repository).
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
   and add one log row. Untick the box afterwards.
5. **Twenty reviewed consultations at clinic 1 (P.5).** Shadow mode off; the
   consultation runs as everyday use does. One log row each.
6. **The clinic 1 exit gate (P.6).** Read and sign [exit-gate.md](exit-gate.md).
7. **Clinic 2 (P.7).** Once clinic 2's Cliniko API-key permission exists:
   install, its owed safeguards and draft-write smokes, twenty reviewed
   consultations and its own gate. Clinic 1 does not wait for it.

## Who does what

- **The practitioner** runs every step above, scores every note, keeps the
  filled pilot log, enters and closes findings, decided 3.5 and 3.6
  (2026-10-07) and signs each gate.
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
- **Synthetic encounter ids** (`syn-01` …) and neutral role-play ids (`rp-01` …)
  may appear in the register; they identify invented content only.
- **Real consultations are never fed to the validation harness** (pilot plan
  Constraint 8). Since 0.3.0 a real consultation's recording may be kept with
  the patient's written consent (`docs/practice/development-recording-consent.md`)
  and exported to a WAV for speaker labelling — on this computer's own
  drive, in its own folder (never the role-play folder or a validation set
  folder), deleted when the labelling is done; Constraint 8 records that
  reconciliation (2026-10-08). Each kept recording's 12-month review goes in the
  pilot log's "Kept recordings — review" table. The audit record's CSV export, which shows
  each recording's mode and app version, stays outside the repository too (it
  carries Cliniko ids).
