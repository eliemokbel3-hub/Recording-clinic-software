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
**Prerequisites:** Python 3.12+ (dev machine runs 3.14), Node 20+, Google Chrome.

1. Clone the repo
2. `python -m venv .venv` then `.venv\Scripts\python.exe -m pip install -e ".\desktop[dev]"`
3. `cd extension && npm install && npm run build` (bundle lands in `extension/dist`)
4. Register the native host: `.venv\Scripts\python.exe scripts\register-native-host.py` (per Windows user; rerun after any venv move or reinstall — installs to `%LOCALAPPDATA%\ClinikoScribe`, which must stay space-free and `.exe`-based or Chrome silently reports "host not found")
5. Load `extension/dist` as an unpacked extension in `chrome://extensions` (Developer mode), pin its icon
6. **Fully restart Chrome** — window-close is not a restart when background mode is on; verify no `chrome.exe` remains before relaunching
7. Verify: pinned icon shows a green **OK** badge; `.venv\Scripts\scribe-app.exe` self-test passes 2/2
8. QA suites: `desktop:` `ruff check . && mypy && pytest` (in `desktop/`); `extension:` `npm run qa`

No `.env` needed — the project has no environment variables (secrets live in Windows Credential Manager).

Machine-specific run notes (local absolute paths, personal DB endpoints, machine-local ports) belong in a gitignored `AGENTS.local.md`, not here — and never put secrets in it.

## Current Status
**Phase 1 (security foundation) COMPLETE** — gate passed 2026-07-26. Working: Chrome MV3 extension shell (pinned ID, Cliniko-only permissions, badge connection indicator) ↔ Windows native host over authenticated Native Messaging (fixture-canonical protocol, binary framing, watchdog/backoff reconnect), secure-storage foundation (Credential Manager + AES-GCM session crypto with cryptographic deletion), structural no-clinical-data logging, five security docs in `docs/security/`, 72+36 tests incl. a no-network-sockets proof. No clinical features yet — Phases 2–7 of `PLAN.md` pending.

## Last Session
- Date: 2026-07-26
- Worked on: Phase 1 execution, review round 1 (29 findings fixed), gate debugging (three Chrome registration gotchas — see plan executor facts), gate PASSED
- Next priority: CI workflow (due before Phase 2), then /create-plan for Phase 2 (local recording + transcription; first task = named-pipe host↔app IPC)

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
