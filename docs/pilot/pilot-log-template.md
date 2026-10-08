# Pilot log — template

Copy this table into a file of your own, outside this repository and outside any
synced or shared folder, and add one row per pilot consultation after you have
finalised the note in Cliniko (README, "What is kept where"). Keep this template
here unfilled.

Every cell is a date, a number, a fixed word or yes/no. There is deliberately no
column for a name, a Cliniko or session id, or anything that was said or written:
something worth keeping in words is a finding — enter it in the
[findings register](findings-register.md), described in terms of the app, and
count it in this row's last column.

## Columns

- **Row** — 1, 2, 3 … in the order the consultations happened.
- **Date** — the consultation's date (YYYY-MM-DD).
- **Clinic** — `1` or `2`.
- **Mode** — `shadow` or `normal`: the mode the recording had at Start. Once
  the session is completed, its Past sessions entry is marked "(shadow
  recording)" for a shadow one, and the audit record's export shows the mode in
  its `mode` column.
- **App version** — as the Status tab shows it ("Clinic Scribe version …").
- **Kept** — `yes` when Complete said "The recording was kept for development."
  (the patient consented in writing, `development-consent-v1`), else `no`.
- **R1 – R5** — the shipping-gate rubric (`docs/testing/shipping-gate.md`, rubric
  v1), scored at its one scoring point: after every proposal is decided and
  every warning acknowledged, before Save. Write each ratio as `n/m`:
  - **R1** routing — assertions in the right section / assertions in the note.
  - **R2** coverage — material spoken items in the note / material items
    spoken.
  - **R3** noise — assertions that must be deleted / assertions in the note.
  - **R4** safety — the count of items surviving review that are wrong-side,
    wrong-dose, negation-flipped, or patient speculation in a clinician-owned
    section. Expected 0; every one is also a high-severity finding.
  - **R5** accelerators — proposals confirmed / proposals offered.
- **R6** — faster than writing the note from scratch? `yes` / `no`.
- **Minutes** — minutes spent reviewing the note, to the nearest minute.
- **Missed (shadow only)** — the count of clinically material items in your own
  note that the app's note did not carry. Leave empty for a normal row.
- **Would sign (shadow only)** — would you have signed the app's note after your
  review? `yes` / `no`. Leave empty for a normal row.
- **Findings** — how many findings this consultation added to the register.

## Table

| Row | Date | Clinic | Mode | App version | Kept | R1 | R2 | R3 | R4 | R5 | R6 | Minutes | Missed | Would sign | Findings |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | | | | | | |

## Totals (for the exit gate)

Per clinic, and separately for shadow and normal rows: the number of rows, the
R1 and R3 totals over the set (sum of numerators over sum of denominators, as the
rubric's pass rule does), the R4 total, the number of `yes` answers for R6, the
median minutes, and — for shadow rows — the Missed total and the number of `yes`
answers for Would sign.

| Clinic | Mode | Rows | R1 total | R3 total | R4 total | R6 yes | Median minutes | Missed total | Would sign yes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | shadow | | | | | | | | |
| 1 | normal | | | | | | | | |
| 2 | normal | | | | | | | | |

## Kept recordings — review

Why a recording is still kept (development-recordings plan D9). A year (365
days) after a kept recording's Complete, the Past sessions tab says it is due for
review: press **Delete recording**, or keep it and add one row here saying why.
Add a row too when you delete one at its review. A row is never edited later —
a later review adds a new row. A kept recording the tab cannot read ("Cannot be
read on this Windows account") is never shown as due: review it with the others
(`docs/practice/development-recording-consent.md`, "The 12-month review").

- **Row** — the pilot-log row of that consultation (above), or `—` for a recording kept
  outside the pilot log (then the next column identifies it), or `unreadable` for a
  kept recording the tab cannot read.
- **Consulted** — the consultation's date and time (YYYY-MM-DD HH:MM), exactly as the
  Past sessions tab's row shows it; `—` for an unreadable one. Two kept recordings
  showing the same minute are reviewed together and given the same outcome.
- **Reviewed** — the review's date (YYYY-MM-DD).
- **Outcome** — `deleted` or `kept`.
- **Kept for** — `labelling` (speaker labelling not finished), `replay` (kept to
  replay through later versions of the program and compare the drift) or
  `measurement` (needed for a speaker measurement still to run — never the validation
  harness, which takes no real consultation); `—` when deleted.

| Row | Consulted | Reviewed | Outcome | Kept for |
|---|---|---|---|---|
| | | | | |
