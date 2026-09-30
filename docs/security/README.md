# Security documentation

The five governing documents for the Cliniko clinical scribe, grounded in the
system as built (Phase 1 onward, through the Cliniko workflow safeguards —
the Cliniko client, the host↔app pipe and the Chrome side panel — and the
Cliniko draft write: the client's one write, the write record and completion
after a confirmed write):

- `intended-use.md` — intended-use statement (documentation only; no clinical decision support)
- `data-flow-map.md` — where data lives and moves (including log files; there is no status file)
- `threat-model.md` — trust boundaries, accepted residual risks, tripwires
- `retention-schedule.md` — what is kept, for how long, and how it is destroyed
- `incident-process.md` — what to do when something goes wrong
