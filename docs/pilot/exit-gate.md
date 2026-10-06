# Exit gate — per clinic

PLAN.md Phase 7: "Proceed to routine personal use only after high-risk findings
are resolved or explicitly controlled." Routine use opens per clinic; clinic 1's
gate does not wait for clinic 2 (pilot plan D12). The consultations counted here
are only those made on the pilot build (0.2.0 or later); the shadow
consultations come after the validation run, and the reviewed ones after the
validation and shadow runs.

Read every line against its record, tick it, and sign. A line that cannot be
ticked keeps the gate closed; the gate is never signed with an exception written
beside it — an open item becomes a finding and is resolved or controlled first.

## Clinic 1

- [ ] **Validation passed.** The validation run (pilot plan Task P.3) passed
      under rule v1 (`docs/testing/validation-harness.md`, decision 3.5), over at
      least 50 encounters, from a clean, committed checkout, with the
      practitioner's own cue file in `validation\config`; its totals, commit
      and models-manifest hash are recorded under Task P.3.
- [ ] **Role-play records exist** (Task P.2): the shipping-gate scoring table,
      the speaker numbers and the speaker-labelling decision are recorded in
      their plans, with each role-play speaker's accent in broad terms (at
      least one differing from the practitioner's).
- [ ] **Role-play recordings reviewed** (decision 3.6's review date): the
      recordings are deleted, or the reason they are still needed and the next
      review date are recorded.
- [ ] **Ten shadow consultations logged** (Task P.4): ten rows with mode
      `shadow` in the pilot log, each with consent recorded in Cliniko as
      `patient-info-v2`; the audit record's export shows at least ten `shadow`
      rows on a 0.2 build, ten of them on the dates of those log rows (P.1's
      two mock shadow recordings, and any discarded shadow recording, add
      rows of their own); the R4 total over them is recorded.
- [ ] **Twenty reviewed consultations logged** (Task P.5): twenty rows with
      mode `normal` at clinic 1, and the note-learning plan's Task P.2 marked
      done within them.
- [ ] **Every high finding closed.** No row in the
      [findings register](findings-register.md) is `high` and `open`; each
      `controlled` one names its control.
- [ ] **The practice documents reviewed.** The independent review of
      `docs/practice/` is done — including the "for research purposes" wording
      of VoxCeleb, the dataset the speaker model was trained on (installation
      plan Task 0.4) — and its changes are applied.
- [ ] **The deferred timing item revisited** (the pilot plan's Deferred entry:
      in-app review timings), and its outcome recorded.

Signed (practitioner): ______________________  Date: __________

Once signed: record routine use at clinic 1 in `PLAN.md` and `AGENTS.md`
(pilot plan Task P.6).

## Clinic 2

- [ ] **Clinic 2's Cliniko API-key permission exists**, and the clinic is
      added and validated on the Clinics tab of clinic 2's computer.
- [ ] **Installed and verified** on clinic 2's computer: the current build of
      record, checked with attestation and hash before install
      (`docs/release/pilot-builds.md`), following the installation plan's
      Task P.1 steps.
- [ ] **Owed smokes done there**: the Cliniko workflow safeguards plan's P.1 and
      P.2, and the draft-write plan's test write and live write smoke, each
      marked done in its plan.
- [ ] **Validation and shadow results recorded** — the clinic 1 lines above (the
      validation run and the shadow consultations are not repeated per clinic).
- [ ] **Twenty reviewed consultations logged** at clinic 2 (Task P.7): twenty
      rows with mode `normal` and clinic `2`.
- [ ] **Every high finding closed**, as for clinic 1.
- [ ] **The practice documents reviewed**, as for clinic 1, with any change for
      clinic 2 applied.

Signed (practitioner): ______________________  Date: __________

Once signed: record routine use at clinic 2 in `PLAN.md` and `AGENTS.md`
(pilot plan Task P.7).
