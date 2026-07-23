# Project: Privacy-First Cliniko Clinical Scribe

## What This App Does
A single-practitioner clinical scribe for two Cliniko clinics: a thin Chrome extension embedded in the Cliniko workflow plus a secure Windows desktop companion that records consultations, runs local Whisper transcription and local `gpt-oss-20b` note generation, and creates draft treatment notes through Cliniko's official API. No cloud processing of audio or transcripts; the clinician reviews and finalises every note in Cliniko. See `PLAN.md` for the full product plan.

## Tech Stack
| Layer | Technology | Notes |
|---|---|---|
| Frontend | Chrome extension (Manifest V3) | Runs only on authorised Cliniko domains; UI embedded in the treatment-note workflow |
| Backend | Windows desktop companion | Talks to Chrome via authenticated Native Messaging; local Whisper transcription + local `gpt-oss-20b` note generation |
| Database | Local encrypted session storage | Per-session encryption keys; Cliniko is the permanent system of record — no clinical data synced between machines |
| Hosting | None (local-only) | Chrome extension + local Windows desktop app; may move to a hosting platform later when commercialising; source=user-confirmed:2026-07-23 |
| DNS | | Only if used |

## Links
- GitHub: https://github.com/eliemokbel3-hub/Recording-clinic-software
- Production:
- Dev database:
- Live URL:

## Environment Variables
| Variable | Purpose | Local | Production |
|---|---|---|---|
| _None yet_ | Cliniko API keys are stored in Windows Credential Manager, not env vars; add rows here if env vars are introduced | — | — |

## Database Notes
[List the main tables, key entities, or schema notes here.]

## Local Run Steps
**Prerequisites:** [runtime and tooling versions, e.g. Node 20+, Python 3.12, pnpm 9]

1. Clone the repo
2. Create `.env` from `.env.example`
3. Install dependencies: `[e.g. npm install]`
4. Run the development server: `[e.g. npm run dev]`
5. Verify it's running: open `[local URL, e.g. http://localhost:3000]` — `[what a healthy response looks like, e.g. the login page renders]`

Machine-specific run notes (local absolute paths, personal DB endpoints, machine-local ports) belong in a gitignored `AGENTS.local.md`, not here — and never put secrets in it.

## Current Status
Planning stage — `PLAN.md` holds the product plan; no application code exists yet.

## Last Session
- Date: 2026-07-23
- Worked on: Bootstrap FULL INSTALL (workflow rules, commands, and Skills)
- Next priority: Explore/plan the first implementation slice from PLAN.md

## Known Issues / Next Tasks
- [ ]

## Subsystem Documentation
Add concise "if working on X, read Y" pointers here for any subsystem that has focused documentation.
These pointers are treated as required reading by the agent before planning or modifying work in that area.

- Before planning or building any feature, read `PLAN.md` (product spec: architecture, phased roadmap, safety and test requirements, commercial path).
- If touching security, crypto, logging, the native-messaging channel, or data handling, read `docs/security/threat-model.md` and `docs/security/data-flow-map.md` first (trust boundaries, accepted residual risks, enforced constraints).
- If changing what data is kept or for how long, read `docs/security/retention-schedule.md`.
- If working on the message protocol, the canonical contract is `protocol/fixtures/` (both mirrors are tested against it — see `protocol/fixtures/README.md`).

<!-- Example entries:
- If working on bank feeds, read `docs/integrations/aciss-bank-feeds.md`
- If changing E2E flows, read `docs/testing/playwright-e2e.md`
- If touching auth, read `docs/architecture/auth.md`
-->

## Documentation Status
- Structure version: v22
- Last reviewed: 2026-07-23
