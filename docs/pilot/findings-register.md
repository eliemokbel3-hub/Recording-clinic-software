# Findings register

Every finding of the pilot — from the validation run, the role-plays, the shadow
and reviewed consultations, and everyday use while the pilot runs — with its
severity, its status and the control that closes it. The exit gate
([exit-gate.md](exit-gate.md)) is read against this register: routine use at a
clinic opens only when every high-severity finding is `resolved` or `controlled`.

Clinical-safety incidents are entered here too; the security incident process
(`docs/security/incident-process.md`) says what to do first, and its record
links to the finding by id.

## The rule for every row

This register is in the repository, which is public. A row holds **no clinical
content**: no name, no date of birth, nothing that was said or written in a note,
no Cliniko id and no session id. Describe what the app did in terms of the app —
its category, the part of the app and the control — never the patient. An
encounter is named only by a synthetic id (`syn-01` …) or a neutral role-play id
(`rp-01` …); a real consultation is `—`, and its own detail stays in Cliniko and
in your off-repository pilot log.

## Columns

- **ID** — `F-001`, `F-002` … never reused.
- **Found** — the MONTH the finding was made (YYYY-MM), never the day: a public
  row dated to the day of a shadow or reviewed consultation could let a patient
  recognise their own. The day stays in your off-repository pilot log.
- **Clinic** — `1`, `2`, or `—` (validation and role-plays).
- **Stage** — `validation`, `role-play`, `shadow`, `reviewed`, `everyday` or
  `other`.
- **Encounter** — a synthetic or role-play id, or `—`.
- **Severity** — `high`, `medium` or `low` (below).
- **Category** — one of:
  - the rubric's R4 kinds: `wrong-side`, `wrong-dose`, `negation-flipped`,
    `patient-speculation` (patient speculation in a clinician-owned section);
  - `cross-patient` (a recording, note or draft that reached the wrong patient
    or note, or a name shown on the wrong tab);
  - `privacy` (anything said or written that left the app's custody when it
    should not have, or a name or note text where the app promises none — a
    log, the audit record, the export);
  - `custody` (audio, a transcript or a note kept past its rule, or a key that
    outlived its session);
  - `unsupported` (a clinical line the validation run counted unsupported),
    `omission` (a silent omission of a material fact), `uncertainty` (an
    uncertain fact not surfaced), `checker` (an unexpected checker warning),
    `role` (the clinician's speech not identified);
  - `quality` (anything else about the note) or `workflow` (anything else about
    using the app).
- **Part of the app** — `transcription`, `speaker-labels`, `note-routing`,
  `proposals`, `checker`, `prose`, `copy`, `write`, `session`, `past-sessions`,
  `audit`, `install` or `other`.
- **Status** — `open`, `resolved` (fixed in a named build and re-checked) or
  `controlled` (not fixed, but made safe by a stated control).
- **Control or fix** — a build version (`0.2.1`) or a short commit hash (7 to
  15 characters; the register's check refuses an all-digit one, so name the
  build instead), a setting (for example shadow mode left on for everyday use),
  or a written procedure — about the app, never about a patient: at most 200
  characters, no quotation marks, nothing shaped like an id. This is the
  register's one free-text cell, and nothing but you keeps a name or a note's
  words out of it. Empty while `open`.
- **Closed** — the MONTH it became `resolved` or `controlled` (YYYY-MM), for the
  same reason as "Found": a finding controlled on the day it was found would
  give that day away.

## Severity

- **High** — any R4 kind that survived review (or would have, in a shadow note);
  any `cross-patient`, `privacy` or `custody` finding; each encounter that fails
  the validation run under the ratified pass rule (decision 3.5, rule v1 in
  `docs/testing/validation-harness.md`); and anything that put, or could have
  put, wrong content into a Cliniko draft.
- **Medium** — a quality or workflow problem that cost real review time or could
  mislead a hurried review, with no wrong content surviving it.
- **Low** — a nuisance, a wording problem or a cosmetic fault.

When unsure between two severities, choose the higher. A high finding is never
downgraded to close it; it is `resolved` or `controlled`.

While any high finding is open, consider ticking "Shadow mode (pilot)" for
everyday use too until it is closed (the pilot plan's accepted assumption on
everyday use, D-A): a shadow recording's note is never copied or written to
Cliniko.

## Register

| ID | Found | Clinic | Stage | Encounter | Severity | Category | Part of the app | Status | Control or fix | Closed |
|---|---|---|---|---|---|---|---|---|---|---|
