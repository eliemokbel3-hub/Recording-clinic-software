# Findings register

Every finding of the pilot — from the validation run, the clinic 1 smoke's
measured recordings, the shadow and reviewed consultations, and everyday use
while the pilot runs — with its
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
encounter is named only by a synthetic id (`syn-01` …, or a held-out `hld-01` …,
`h2-01` … or `h3-01` …); a real consultation —
shadow, reviewed, everyday, or a kept recording measured in the smoke — is `—`,
and its own detail stays in Cliniko and in your off-repository pilot log.

## Columns

- **ID** — `F-001`, `F-002` … never reused.
- **Found** — the MONTH the finding was made (YYYY-MM), never the day: a public
  row dated to the day of a shadow or reviewed consultation could let a patient
  recognise their own. The day stays in your off-repository pilot log.
- **Clinic** — `1`, `2`, or `—` (validation).
- **Stage** — `validation`, `smoke` (a kept recording's measurement in the
  clinic 1 smoke), `shadow`, `reviewed`, `everyday` or `other`.
- **Encounter** — a synthetic id (`syn-NN`; or, from the three held-out sets,
  `hld-NN` (`heldout`), `h2-NN` (`heldout-2`) or `h3-NN` (`heldout-3`)), or `—`.
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
| F-001 | 2026-10 | — | validation | syn-01 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-002 | 2026-10 | — | validation | syn-02 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-003 | 2026-10 | — | validation | syn-03 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-004 | 2026-10 | — | validation | syn-04 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-005 | 2026-10 | — | validation | syn-05 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-006 | 2026-10 | — | validation | syn-06 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-007 | 2026-10 | — | validation | syn-07 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-008 | 2026-10 | — | validation | syn-08 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-009 | 2026-10 | — | validation | syn-09 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-010 | 2026-10 | — | validation | syn-10 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-011 | 2026-10 | — | validation | syn-11 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-012 | 2026-10 | — | validation | syn-12 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-013 | 2026-10 | — | validation | syn-12 | high | uncertainty | transcription | resolved | Fixed in 0.3.3 (commit 1e5707d): a patient line holding a listed hedge is marked unsure for review; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-014 | 2026-10 | — | validation | syn-13 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-015 | 2026-10 | — | validation | syn-14 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536, the split-sentence carry) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-016 | 2026-10 | — | validation | syn-15 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-017 | 2026-10 | — | validation | syn-16 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-018 | 2026-10 | — | validation | syn-17 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-019 | 2026-10 | — | validation | syn-18 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-020 | 2026-10 | — | validation | syn-20 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-021 | 2026-10 | — | validation | syn-21 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-022 | 2026-10 | — | validation | syn-22 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-023 | 2026-10 | — | validation | syn-23 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-024 | 2026-10 | — | validation | syn-24 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-025 | 2026-10 | — | validation | syn-25 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-026 | 2026-10 | — | validation | syn-26 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-027 | 2026-10 | — | validation | syn-27 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-028 | 2026-10 | — | validation | syn-28 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-029 | 2026-10 | — | validation | syn-29 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-030 | 2026-10 | — | validation | syn-30 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-031 | 2026-10 | — | validation | syn-30 | high | wrong-dose | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-032 | 2026-10 | — | validation | syn-30 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-033 | 2026-10 | — | validation | syn-30 | high | uncertainty | transcription | controlled | Shadow mode on for every recording; doubt carried by tone, or by a hedge in another sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-034 | 2026-10 | — | validation | syn-31 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-035 | 2026-10 | — | validation | syn-32 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-036 | 2026-10 | — | validation | syn-33 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-037 | 2026-10 | — | validation | syn-34 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-038 | 2026-10 | — | validation | syn-35 | high | uncertainty | transcription | controlled | Shadow mode on for every recording; doubt carried by tone, or by a hedge in another sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-039 | 2026-10 | — | validation | syn-36 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-040 | 2026-10 | — | validation | syn-36 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-041 | 2026-10 | — | validation | syn-36 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-042 | 2026-10 | — | validation | syn-37 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-043 | 2026-10 | — | validation | syn-38 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-044 | 2026-10 | — | validation | syn-39 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-045 | 2026-10 | — | validation | syn-40 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-046 | 2026-10 | — | validation | syn-41 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-047 | 2026-10 | — | validation | syn-41 | high | uncertainty | transcription | resolved | Fixed in 0.3.3 (commit 1e5707d): a patient line holding a listed hedge is marked unsure for review; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-048 | 2026-10 | — | validation | syn-42 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-049 | 2026-10 | — | validation | syn-43 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-050 | 2026-10 | — | validation | syn-44 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-051 | 2026-10 | — | validation | syn-44 | high | uncertainty | transcription | resolved | Fixed in 0.3.3 (commit 1e5707d): a patient line holding a listed hedge is marked unsure for review; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-052 | 2026-10 | — | validation | syn-45 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-053 | 2026-10 | — | validation | syn-46 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-054 | 2026-10 | — | validation | syn-47 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-055 | 2026-10 | — | validation | syn-48 | high | omission | note-routing | resolved | Fixed in 0.3.3 (commit 1e5707d): a line opening with a self-correction follows the line it corrects; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-056 | 2026-10 | — | validation | syn-49 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-057 | 2026-10 | — | validation | syn-49 | high | uncertainty | transcription | resolved | Fixed in 0.3.3 (commit 1e5707d): a patient line holding a listed hedge is marked unsure for review; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-058 | 2026-10 | — | validation | syn-50 | high | omission | note-routing | resolved | Fixed in 0.3.1 (commit e9c1536) and re-checked by validation runs 2 and 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-059 | 2026-10 | — | validation | syn-02 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-060 | 2026-10 | — | validation | syn-02 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-061 | 2026-10 | — | validation | syn-06 | high | cross-patient | note-routing | resolved | Fixed in 0.3.3 (commit 1e5707d): the note stops at a possible next patient and a separate warning names it; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-062 | 2026-10 | — | validation | syn-08 | high | wrong-dose | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-063 | 2026-10 | — | validation | syn-08 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-064 | 2026-10 | — | validation | syn-11 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-065 | 2026-10 | — | validation | syn-11 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-066 | 2026-10 | — | validation | syn-16 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-067 | 2026-10 | — | validation | syn-16 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-068 | 2026-10 | — | validation | syn-20 | high | cross-patient | note-routing | resolved | Fixed in 0.3.3 (commit 1e5707d): the note stops at a possible next patient and a separate warning names it; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-069 | 2026-10 | — | validation | syn-22 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-070 | 2026-10 | — | validation | syn-22 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-071 | 2026-10 | — | validation | syn-28 | high | wrong-dose | transcription | controlled | Shadow mode on for every recording until a repeated validation run passes; the clinician writes their own Cliniko note | 2026-10 |
| F-072 | 2026-10 | — | validation | syn-28 | high | quality | transcription | controlled | Shadow mode on for every recording until a repeated validation run passes; the clinician writes their own Cliniko note | 2026-10 |
| F-073 | 2026-10 | — | validation | syn-28 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-074 | 2026-10 | — | validation | syn-32 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-075 | 2026-10 | — | validation | syn-32 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-076 | 2026-10 | — | validation | syn-33 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-077 | 2026-10 | — | validation | syn-38 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-078 | 2026-10 | — | validation | syn-38 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted greeting is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-079 | 2026-10 | — | validation | syn-38 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-080 | 2026-10 | — | validation | syn-42 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-081 | 2026-10 | — | validation | syn-42 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-082 | 2026-10 | — | validation | syn-46 | high | quality | transcription | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-083 | 2026-10 | — | validation | syn-46 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted greeting is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-084 | 2026-10 | — | validation | syn-46 | high | unsupported | note-routing | resolved | Spelling difference only, compared equal since the metric amendment of 2026-10-11 (commit e9c1536) and re-checked by validation run 3; shadow mode stays on until 0.3.1 is installed | 2026-10 |
| F-085 | 2026-10 | — | validation | syn-21 | high | cross-patient | note-routing | resolved | Fixed in 0.3.3 (commit 1e5707d): the note stops at a possible next patient and a separate warning names it; re-checked by validation run 5; shadow mode stays on until 0.3.3 is installed | 2026-10 |
| F-086 | 2026-10 | 1 | shadow | — | high | quality | transcription | resolved | Fixed in 0.3.2 (commit d34f685): the primer holds no example sentence and invented-looking speech is marked for review; re-checked by a music-only recording on the installed build | 2026-10 |
| F-087 | 2026-10 | — | validation | syn-22 | high | omission | transcription | controlled | The clinician reads the transcript against what was said before Save; shadow mode on for every recording until a repeated validation run passes | 2026-10 |
| F-088 | 2026-10 | 1 | other | — | medium | quality | transcription | controlled | Shadow mode on for every recording; over the next ten shadow consultations count lines marked possibly not speech on known speech; the clinician writes their own Cliniko note | 2026-10 |
| F-089 | 2026-10 | — | validation | hld-06 | high | omission | note-routing | controlled | Shadow mode on for every recording; with the voice enrolled, validation run 6 does not fail this encounter; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-090 | 2026-10 | — | validation | hld-12 | high | omission | note-routing | controlled | Shadow mode on for every recording; with the voice enrolled, validation run 6 does not fail this encounter; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-091 | 2026-10 | — | validation | hld-14 | high | quality | transcription | controlled | Shadow mode on for every recording; one misheard word; the clinician reads the transcript against what was said before Save and writes their own Cliniko note | 2026-10 |
| F-092 | 2026-10 | — | validation | hld-14 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted greeting is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-093 | 2026-10 | — | validation | hld-15 | high | omission | note-routing | controlled | Shadow mode on for every recording; with the voice enrolled, validation run 6 does not fail this encounter; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-094 | 2026-10 | — | validation | hld-19 | high | omission | note-routing | controlled | Shadow mode on for every recording; since commit 5f1e3e5 a left-out clinician line is warned, re-checked by validation run 6; not yet installed, so the clinician writes their own Cliniko note | 2026-10 |
| F-095 | 2026-10 | — | validation | hld-19 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-096 | 2026-10 | — | validation | hld-20 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-097 | 2026-10 | — | validation | hld-21 | high | quality | transcription | controlled | Shadow mode on for every recording; one misheard word; the clinician reads the transcript against what was said before Save and writes their own Cliniko note | 2026-10 |
| F-098 | 2026-10 | — | validation | hld-21 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-099 | 2026-10 | — | validation | hld-22 | high | omission | note-routing | controlled | Shadow mode on for every recording; with the voice enrolled, validation run 6 does not fail this encounter; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-100 | 2026-10 | 1 | shadow | — | high | omission | note-routing | controlled | Shadow mode on for every recording; a clinician line no cue routes can be left out without a warning; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-101 | 2026-10 | 1 | shadow | — | high | omission | note-routing | controlled | Shadow mode on for every recording; a clinician line no cue routes can be left out without a warning; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-102 | 2026-10 | — | validation | hld-07 | high | quality | transcription | controlled | Shadow mode on for every recording; one misheard word, marked for review; the clinician checks each marked word against what was said and writes their own Cliniko note | 2026-10 |
| F-103 | 2026-10 | — | validation | h2-03 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-104 | 2026-10 | — | validation | h2-04 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-105 | 2026-10 | — | validation | h2-07 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-106 | 2026-10 | — | validation | h2-08 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-107 | 2026-10 | — | validation | h2-09 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-108 | 2026-10 | — | validation | h2-11 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-109 | 2026-10 | — | validation | h2-13 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-110 | 2026-10 | — | validation | h2-14 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-111 | 2026-10 | — | validation | h2-17 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-112 | 2026-10 | — | validation | h2-18 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-113 | 2026-10 | — | validation | h2-19 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-114 | 2026-10 | — | validation | h2-20 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-115 | 2026-10 | — | validation | h2-21 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-116 | 2026-10 | — | validation | h2-22 | high | omission | note-routing | controlled | Shadow mode on for every recording; a patient line no cue routes is left out unwarned; the chooser lists it; the clinician reads the transcript against the note and writes their own Cliniko note | 2026-10 |
| F-117 | 2026-10 | — | validation | h2-03 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-118 | 2026-10 | — | validation | h2-05 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-119 | 2026-10 | — | validation | h2-08 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-120 | 2026-10 | — | validation | h2-10 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-121 | 2026-10 | — | validation | h2-12 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-122 | 2026-10 | — | validation | h2-13 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-123 | 2026-10 | — | validation | h2-15 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-124 | 2026-10 | — | validation | h2-18 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-125 | 2026-10 | — | validation | h2-21 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-126 | 2026-10 | — | validation | h2-01 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a listed hedge the recogniser split from its fact, or a bare modal, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-127 | 2026-10 | — | validation | h2-17 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a listed hedge the recogniser split from its fact, or a bare modal, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-128 | 2026-10 | — | validation | h2-18 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a listed hedge the recogniser split from its fact, or a bare modal, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-129 | 2026-10 | — | validation | h2-05 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted closing is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-130 | 2026-10 | — | validation | h3-03 | high | unsupported | transcription | controlled | Shadow mode on for every recording; a misheard number is marked for review but still fails the run as an unsupported line; the clinician checks each marked number and writes their own Cliniko note | 2026-10 |
| F-131 | 2026-10 | — | validation | h3-02 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted closing or greeting is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-132 | 2026-10 | — | validation | h3-17 | high | cross-patient | note-routing | controlled | Shadow mode on for every recording; a next patient met with an unlisted closing or greeting is not detected; the clinician checks the end of each transcript and writes their own Cliniko note | 2026-10 |
| F-133 | 2026-10 | — | validation | h3-10 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-134 | 2026-10 | — | validation | h3-12 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-135 | 2026-10 | — | validation | h3-14 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-136 | 2026-10 | — | validation | h3-20 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-137 | 2026-10 | — | validation | h3-21 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a hedge not on the frozen list, or outside the fact's sentence, is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-138 | 2026-10 | — | validation | h3-19 | high | uncertainty | checker | controlled | Shadow mode on for every recording; a bare modal verb of doubt is not marked; the clinician writes their own Cliniko note | 2026-10 |
| F-139 | 2026-10 | — | validation | h3-05 | medium | workflow | checker | controlled | Shadow mode on for every recording; a line the recogniser split draws one left-out-line warning per piece, up to ten in one note; the clinician acknowledges each | 2026-10 |
| F-140 | 2026-10 | — | validation | h3-21 | medium | workflow | checker | controlled | Shadow mode on for every recording; a line the recogniser split draws one left-out-line warning per piece, up to ten in one note; the clinician acknowledges each | 2026-10 |
