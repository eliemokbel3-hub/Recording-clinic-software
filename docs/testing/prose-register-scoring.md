# Prose register scoring (rubric `register-v1`)

The practitioner's reading of the clinical register (note-content-design plan, D5 (ii); Task R.7, used at Task P.1). Since prompt `narrative-v3` the two prose styles — Narrative and Your own voice — may write a clinical shorthand from the shipped list in place of the exact phrase it stands for ("LBP" for "lower back pain", "3/52" for "three weeks"), and may open a section the patient spoke with "Pt reports" or "The patient reports" in place of "I", "my", "me" or "we". The app's check (Check 5) treats a listed shorthand as the same fact as its phrase, but it compares words, not meaning. This sheet is the clinician's reading that the register says what the lines said before it ships.

Rubric `register-v1`, dated 2026-11-08. A changed rubric is a new version with its own date, never an edit of this one after a scoring has been made under it.

## What is read

Only the fixture notes the test suite pins (`desktop/tests/test_prose_style.py`, `FIXTURE_NOTES`): invented lines, written for the tests, with no patient behind them. Twelve notes since Task R.5; the last two hold a patient's first-person lines under a confirmed clinician, so they are the notes where the speaker frame can be used. Nothing here reads a real session, a kept recording, a transcript or a Past-sessions entry.

## Procedure

1. On the developer build, with the language model downloaded (`scripts\setup-models.py`) and the prose runtime installed (`desktop\requirements-ml-prose.txt`), keep the laptop lid open and the computer otherwise quiet.
2. In **Command Prompt**, from the repository folder, make the report's folder OUTSIDE the repository (the second command cannot start without it; if the folder is already there, `mkdir` says so and nothing changes), then write the report into it:

   ```bat
   mkdir C:\prose-register
   .venv\Scripts\python.exe scripts\measure-prose-fixtures.py --verbose > C:\prose-register\report.json
   ```

   (In PowerShell a `>` writes UTF-16; use Command Prompt, or `| Out-File -Encoding utf8`.) Nothing is shown on the screen while it runs (an error, if any, is). The report file STARTS with one summary line per style — how many notes passed, how many sections used the speaker frame, and the seconds per section — and the JSON report follows them, so the file as a whole is not plain JSON: read it in a text editor. The summary numbers are Task R.5's, recorded on the plan; this sheet reads the prose.
3. Open the report in a text editor; the JSON starts after the two summary lines. For each style (`narrative`, then `own_voice`), for each note, each entry of `sections` holds the section's `inputs` (the confirmed lines), the `prose` the model wrote, its `verdict` (`passed`, or the reason it was refused), `framed` (the section holds a line the patient spoke) and `frame_used` (its prose holds "Pt" or "patient" where the lines do not — anywhere in the prose, not only at its start). A section with an `error` and no prose is counted under "Shown clean" only.
4. Read every section's prose against its inputs and count, per style:
   - **Sections read**: the sections that have prose.
   - **Invented or wrong shorthand**: each FACT in the prose that the inputs do not say — an added finding, a changed number or side, a lost or added "no" or "not" — and each shorthand used for a phrase it does not stand for (for example "3/52" for two weeks, or "B/L" for one side). Count facts, not sections. This must be 0.
   - **Reads as clinician-written**: the sections whose prose reads as a line a clinician would write in the note.
   - **Shown clean**: the sections whose `verdict` is not `passed` (the app shows them as Clean clinical, with its warning), and any section with an `error`.
   - **Frames used**: the sections with `frame_used` true. Check it equals that style's summary line at the start of the report, and that every one is `framed`.
5. Fill one row per style in the table below, dated (the day of the run), counts only. Copy the same counts onto the plan's Task P.1 line. Then delete the report and its folder (`C:\prose-register\`).

Write no prose, no input line and no quotation into the table, the plan or a finding: counts and the style name only.

## Scoring table

| Date | Style | Notes | Sections read | Invented or wrong shorthand | Reads as clinician-written | Shown clean | Frames used |
|---|---|---|---|---|---|---|---|
|  | narrative |  |  |  |  |  |  |
|  | own_voice |  |  |  |  |  |  |

## The pass line

Under `register-v1` the register passes the sheet when **Invented or wrong shorthand is 0 in both styles**. The other three counts are recorded beside it; they are what the clinician weighs, not a gate.

A count above 0 is a finding, never a reason to change the rubric or the check: enter one row per fact in the findings register (`docs/pilot/findings-register.md`: Stage `validation`, Encounter `—`, Part of the app `prose`, Category `unsupported`), and the plan re-tunes the prompt — a new prompt version, then this procedure again under the same rubric. The shipped list of shorthands changes only by the practitioner's decision, with a new prompt version.
