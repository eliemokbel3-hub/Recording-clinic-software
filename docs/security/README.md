# Security documentation

The five governing documents for the Cliniko clinical scribe, grounded in the
system as built (Phase 1 onward, through the Cliniko workflow safeguards —
the Cliniko client, the host↔app pipe and the Chrome side panel — the
Cliniko draft write: the client's one write, the write record and completion
after a confirmed write — and the privacy and professional controls of
PLAN.md Phase 6: the audit record and its CSV, the Past-sessions archive and
tab, the exclusions and the exception hooks — and, from PLAN.md Phase 7, the
installation and the pilot: shadow mode, schema v2 and the validation
harness):

- `intended-use.md` — intended-use statement (documentation only; no clinical decision support; the in-app intended-use line)
- `data-flow-map.md` — where data lives and moves (including log files; there is no status file; flow 22 is the audit record, Past sessions and the exclusions; flows 25–26 are shadow mode and the validation harness)
- `threat-model.md` — trust boundaries, accepted residual risks, tripwires ("Privacy and professional controls" for the Phase 6 stores and their named residues; "The pilot" for shadow mode and the harness)
- `retention-schedule.md` — what is kept, for how long, and how it is destroyed (the Past sessions and Audit record rules; the "Pilot" rows)
- `incident-process.md` — what to do when something goes wrong (the audit row is the durable evidence; clinical-safety incidents also go in the pilot's findings register)

The practice-facing drafts — patient information and consent, privacy
information, downtime procedure and clinician review guide — are in
`docs/practice/`, each awaiting independent privacy/legal/clinical-safety
review before use with other practitioners. The pilot's own records — the run
order, the pilot log template, the findings register and the exit gate — are in
`docs/pilot/`.
