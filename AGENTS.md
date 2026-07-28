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
2. `python -m venv .venv` then `.venv\Scripts\python.exe -m pip install -e ".\desktop[dev,ml]"` and `.venv\Scripts\python.exe -m pip install sounddevice` (the `[ml]` extra = faster-whisper/onnxruntime/huggingface_hub; `sounddevice` is deliberately not in pyproject — the test suite is absent-safe without it, but recording needs it)
3. Download the local ML models (one-time, the ONLY sanctioned network step): `.venv\Scripts\python.exe scripts\setup-models.py` — **run this YOURSELF from a normal terminal (PowerShell/cmd), never from an agent shell**: agent shells on this machine are MSIX-virtualized and their `%LOCALAPPDATA%` writes land in a package-private location invisible to user-launched apps (`docs/lessons.md`). ~3.0 GiB with all four benchmark candidates; silero + whisper `small` alone ≈ 470 MiB
4. `cd extension && npm install && npm run build` (bundle lands in `extension/dist`)
5. Register the native host: `.venv\Scripts\python.exe scripts\register-native-host.py` (per Windows user; rerun after any venv move or reinstall — installs to `%LOCALAPPDATA%\ClinikoScribe`, which must stay space-free and `.exe`-based or Chrome silently reports "host not found")
6. Load `extension/dist` as an unpacked extension in `chrome://extensions` (Developer mode), pin its icon
7. **Fully restart Chrome** — window-close is not a restart when background mode is on; verify no `chrome.exe` remains before relaunching
8. Verify: pinned icon shows a green **OK** badge; `.venv\Scripts\scribe-app.exe` self-test passes 2/2
9. QA suites: `desktop:` `ruff check . && mypy && pytest` (in `desktop/`); `extension:` `npm run qa`

**Launching the desktop app:** double-click `.venv\Scripts\scribe-app.exe` in Explorer, or run it from a PERSISTENT terminal (`.venv\Scripts\python.exe -m scribe_desktop.app` keeps console output). NEVER launch it from an ephemeral terminal (e.g. a chat Run button) — the closing terminal kills the GUI child (`docs/lessons.md`). Only one instance runs per user: a second launch shows "already running" and exits (named-mutex guard).

No `.env` needed — the project has no environment variables (secrets live in Windows Credential Manager; the offline ML kill-switches are set by the app itself).

Machine-specific run notes (local absolute paths, personal DB endpoints, machine-local ports) belong in a gitignored `AGENTS.local.md`, not here — and never put secrets in it.

## Current Status
**Phase 1 (security foundation) COMPLETE** — gate passed 2026-07-26. **Phase 2 (local recording + transcription) implementation COMPLETE through Step 12** — live user smoke PASSED 2026-07-28; remaining before phase close: Step 13 (extended no-network proof + manual completion gate) and the hardening stage. Working now: multi-screen desktop app (microphone / session / recovery / transcript / status) recording 16 kHz mono with immediate per-chunk AES-256-GCM encryption; DPAPI key custody with a 24 h crash-recovery window and cryptographic deletion (Complete / Discard / expiry sweep, ≤15-min sweep granularity); fully-local transcription (silero-VAD + faster-whisper `small` CPU int8, word timestamps, uncertainty marks on low-confidence words/numbers/names, 2-speaker labels) with offline env kill-switches set AND asserted (`scripts/setup-models.py` is the only sanctioned network user, run by the USER from a normal terminal); hardware benchmark panel (all four candidates RTF ≤ 0.5 on the dev machine); single-instance named-mutex guard; 481 desktop + 36 extension tests; CI (3.12 + 3.14, windows-latest) with best-effort `[ml]`/audio install. Not yet: note generation (Phase 3), Cliniko write-back (Phase 4), Chrome-side recording UI + host↔app pipe (Phase 5).

## Last Session
- Date: 2026-07-28
- Worked on: Phase 2 Steps 11–12 (stage-8 executor): CI workflow updated for the ML stack (best-effort `[ml]` + sounddevice, offline env, first CI run verified GREEN — but note all three green runs predate the Phase 2 commits, which are still unpushed); security docs synced to Phase 2 (threat model, data-flow map, retention schedule — DPAPI custody, NTFS unlink, clipboard, sweep-granularity, transcript-view residuals); single-instance named-mutex guard implemented with tests (peer-18 PR4, raised priority)
- Next priority: push + watch both CI matrix legs, then P9 (Step 13: extended no-network proof + manual completion gate), then Step H hardening

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
