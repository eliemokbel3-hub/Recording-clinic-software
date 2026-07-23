# Feature Implementation Plan
**Feature:** phase1-security-foundation
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None (derived from `PLAN.md` Phase 1 — Security foundation)
- Follow-up plans: None (Phases 2–7 of `PLAN.md` will become their own plans)

## Goal
Build the security foundation for the Cliniko clinical scribe: a Chrome MV3 extension shell restricted to Cliniko domains and a Windows desktop companion shell (Python + PySide6), talking exclusively over authenticated Chrome Native Messaging, with credential storage in Windows Credential Manager, an encrypted-session-storage foundation, and the five governing security documents. No clinical features, no audio, no Cliniko API calls yet.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5; executor may be Opus-class; tier-gap dosing applied (design decisions locked, protocol contract specified, per-task acceptance criteria)

### Agreed Scope (Build Now)
- Monorepo scaffolding: `extension/` (TypeScript + Vite + CRXJS, Manifest V3), `desktop/` (Python 3.12 + PySide6), `protocol/` (shared message-schema source of truth), `scripts/` (dev tooling), `docs/security/` (governance docs)
- Chrome MV3 extension shell: host permissions `https://*.cliniko.com/*` only, minimal service worker + content-script stub, no UI injection into Cliniko pages yet beyond a connectivity indicator
- Desktop companion shell: PySide6 status window (connection state, protocol version), structured logging with a clinical-data-redaction filter from day one
- Versioned message protocol: JSON envelope with `protocol_version`, `type`, `payload`; TypeScript types and Python pydantic models generated/mirrored from one canonical definition; Phase-1 message set = `hello`, `hello_ack`, `ping`, `pong`, `error`
- Native Messaging host: manifest generation pinning the extension ID in `allowed_origins`, HKCU registry registration script, origin verification on the desktop side, hello handshake with version negotiation and per-session nonce
- Credential storage: `keyring`-backed `SecureStorageProvider` interface writing to Windows Credential Manager (exercised with a test credential only — no real Cliniko keys in Phase 1)
- Encrypted session storage foundation: AES-256-GCM per-session keys (in-memory only), encrypt/decrypt round-trip of test data, key-destruction semantics
- Security documents in `docs/security/`: intended-use statement, data-flow map, threat model, retention schedule, incident process
- QA tooling: `ruff` + `mypy` + `pytest` (desktop), `eslint` + `tsc` + `vitest` (extension); integration test proving the desktop process opens no listening network sockets
- Phase-1 completion gate (from `PLAN.md`): Chrome and desktop exchange authenticated test messages with no clinical data and verified absence of exposed local network ports

### Deferred — Actionable Later
- Phases 2–7 of `PLAN.md` (recording/transcription, note generation, Cliniko API integration, workflow safeguards, privacy controls, pilot)
  - Why deferred: `PLAN.md`'s own phased roadmap; each phase becomes its own plan
  - Intended future outcome: one `/create-plan` per phase, anchored on `PLAN.md`
  - Relevant files / subsystems: all — Phase 1 lays their foundation
  - Dependencies / prerequisites: Phase 1 completion gate passed
  - Recommended next action: `/create-plan` for Phase 2 after this plan completes
  - Risk if deferred: minor: intentional staging, not a gap
- PyInstaller packaging + installer for the desktop app
  - Why deferred: `PLAN.md` Phase 7 handles installation; dev-mode launcher script suffices until then
  - Intended future outcome: signed, packaged desktop app installed on both clinic machines
  - Relevant files / subsystems: `desktop/`, `scripts/register-native-host.py`
  - Dependencies / prerequisites: Phases 2–6 features stable
  - Recommended next action: fold into the Phase 7 plan
  - Risk if deferred: minor: dev machines run from source meanwhile
- GitHub remote + CI (lint/type/test on push)
  - Why deferred: repo has no remote yet; CI needs one
  - Intended future outcome: GitHub Actions running the QA suite from Task 2
  - Relevant files / subsystems: `.github/workflows/`
  - Dependencies / prerequisites: user creates the GitHub repo
  - Recommended next action: add remote, push, then add a workflow reusing the QA commands
  - Risk if deferred: blocked-work: no off-machine backup of the repo until a remote exists
  - Revisit by: before Phase 2 begins

### Excluded — Revisit Only If Needed
- Edge/Brave/other Chromium browsers
  - Why excluded: `PLAN.md` and user confirmed Chrome only (2026-07-23); each browser adds its own native-messaging registration + test surface
  - When to revisit: if a clinic machine standardises on Edge
  - Relevant files / subsystems: `scripts/register-native-host.py`, host manifest
  - Recommended next action (if any): add the Edge registry path alongside Chrome's
- macOS support, Azure/cloud AI providers, org accounts/billing/central admin
  - Why excluded: `PLAN.md` commercial path defers these until the single-user pilot succeeds
  - When to revisit: commercialisation
  - Relevant files / subsystems: provider interfaces keep these portable
  - Recommended next action (if any): none now

### Accepted Assumptions — Revalidate Later
- Both clinic machines run Windows 11 and will later handle local Whisper + `gpt-oss-20b`
  - Why accepted for now: Phase 2's hardware benchmark validates this; Phase 1 has no model workloads
  - Risk if assumption becomes false: model quality/latency degrades; never cloud fallback per `PLAN.md`
  - Trigger for revisit: Phase 2 benchmark task
  - Recommended next action: none in Phase 1
- Wildcard `https://*.cliniko.com/*` manifest permission + runtime allowlist of the two clinic subdomains is acceptable (user-confirmed 2026-07-23)
  - Why accepted for now: exact clinic shard subdomains not yet recorded; wildcard keeps installs shard-change-proof
  - Risk if assumption becomes false: if Cliniko moves off `*.cliniko.com`, the manifest needs updating
  - Trigger for revisit: install time (Phase 7) records the real subdomains into the runtime allowlist
  - Recommended next action: capture the two subdomains in `AGENTS.md` when known

### Key Design Decisions
- Desktop stack = Python 3.12 + PySide6 (user-confirmed 2026-07-23)
  - Why: later phases need faster-whisper / llama.cpp-family bindings, which are first-class in Python; PySide6 covers the settings screens; `keyring` reaches Windows Credential Manager
  - Alternatives rejected: .NET/WPF (better OS integration but would force a Python sidecar for ML anyway); Rust/Tauri (immature ML bindings, slower delivery)
  - Still applies to follow-up work: Yes
- Extension stack = TypeScript + Vite + CRXJS (user-confirmed 2026-07-23)
  - Why: type-checked message contracts shared with the protocol definition; standard MV3 tooling
  - Alternatives rejected: plain JS (loses contract checking)
  - Still applies to follow-up work: Yes
- Native Messaging is the ONLY transport; the desktop app must never open a listening network socket
  - Why: `PLAN.md` security requirement ("no exposed local network ports"); stdio channel is spawned per-extension by Chrome and scoped by `allowed_origins`
  - Alternatives rejected: localhost WebSocket/HTTP server (exposes a port any local process could probe)
  - Still applies to follow-up work: Yes — Phase-2+ audio/data stays on this channel or in-process
- Authentication model: pin the extension ID in the host manifest's `allowed_origins`; desktop verifies the `--origin`/argv extension origin Chrome passes at launch; hello handshake negotiates `protocol_version` and exchanges a per-session random nonce echoed on subsequent messages
  - Why: Chrome's native-messaging model already guarantees the host binary is launched only for pinned extensions; the handshake adds version safety and a session identifier without inventing custom crypto on a local stdio pipe (threat model documents this boundary)
  - Alternatives rejected: mutual TLS / signed messages over stdio (no added protection against the actual threat — a local attacker with user privileges already owns both endpoints)
  - Still applies to follow-up work: Yes
- Protocol schema lives in `protocol/` as the single source of truth; both sides carry `protocol_version` from message one
  - Why: prevents extension/desktop drift across the six later phases; version negotiation in `hello` allows staged upgrades
  - Alternatives rejected: duplicating type definitions per side (guaranteed drift)
  - Still applies to follow-up work: Yes
- Ephemeral session keys: AES-256-GCM via the `cryptography` library, generated with `os.urandom(32)`, held only in memory, destroyed explicitly; durable secrets go to Windows Credential Manager via `keyring`
  - Why: matches `PLAN.md`'s per-session encryption + cryptographic-deletion requirements; standard, audited primitives only
  - Alternatives rejected: DPAPI-only (no per-session key destruction semantics); custom key files on disk (violates cryptographic-deletion goal)
  - Still applies to follow-up work: Yes
- Logging is structured and clinical-data-free from day one, enforced by a redaction filter
  - Why: `PLAN.md` Phase 6 forbids transcript/audio content in logs; building the discipline into the first line of code is cheaper than retrofitting
  - Alternatives rejected: ad-hoc print logging until Phase 6 (retrofit risk)
  - Still applies to follow-up work: Yes

## Key Findings

### Files / Symbols Involved
All new — the repo currently contains only documentation and workflow tooling (verified: no `package.json`, no application code). Planned layout:
- `protocol/messages.schema.json` — canonical envelope + Phase-1 message definitions
- `extension/manifest.json` (generated by CRXJS from `extension/vite.config.ts`), `extension/src/background.ts`, `extension/src/protocol.ts`, `extension/src/content/indicator.ts`
- `desktop/pyproject.toml`, `desktop/src/scribe_desktop/app.py` (PySide6 entry), `desktop/src/scribe_desktop/native_host.py` (stdio framing + handshake), `desktop/src/scribe_desktop/protocol.py` (pydantic models), `desktop/src/scribe_desktop/secure_storage.py` (`SecureStorageProvider`, keyring + AES-GCM session crypto), `desktop/src/scribe_desktop/logging_setup.py`
- `scripts/register-native-host.py` — generates host manifest + HKCU registry entry; `scripts/dev-host-launcher.bat` — venv launcher the manifest points at
- `docs/security/intended-use.md`, `data-flow-map.md`, `threat-model.md`, `retention-schedule.md`, `incident-process.md`

### Codebase Integration Notes
- Chrome native messaging framing: 4-byte little-endian length prefix + UTF-8 JSON, ≤1 MB per message host→Chrome; the host reads stdin/writes stdout — stdout must carry ONLY framed protocol bytes, so all logging goes to file/stderr, never stdout
- The native host process is spawned by Chrome; it is a separate process from the PySide6 UI app. Phase 1 keeps them as one Python package with two entry points (`scribe-host`, `scribe-app`); the host relays state to the UI app in a later phase — Phase 1's UI reads a shared status file or simply runs standalone (see Task 8)
- Registry key for Chrome: `HKCU\Software\Google\Chrome\NativeMessagingHosts\<host_name>` → path to the host manifest JSON; host name must be lowercase dot-separated (e.g. `com.scribe.cliniko_host`)
- Unpacked-extension IDs change unless a `key` field is pinned in the manifest — generate a keypair once in dev and pin `key` so `allowed_origins` stays stable across machines
- `.env.example` currently documents zero env vars — correct; nothing in Phase 1 introduces one (keys go to Credential Manager)

### External / API Findings
- No Cliniko API usage in Phase 1 (deliberate — first API call is Phase 4)
- Cliniko shards live under `*.cliniko.com` subdomains; the two clinics' actual subdomains get recorded at install time (accepted assumption above)

## Planned Workflow Summary

### Flow 1 — Authenticated handshake (the Phase-1 deliverable)
- User opens Chrome with the extension loaded → service worker calls `chrome.runtime.connectNative("com.scribe.cliniko_host")` → Chrome launches the registered host → host verifies the calling origin against the pinned extension ID → extension sends `hello {protocol_version}` → host replies `hello_ack {protocol_version, session_nonce}` → subsequent `ping`/`pong` echo the nonce → extension badge/indicator shows "connected"; any mismatch produces a typed `error` message and a clean disconnect

### Flow 2 — Secure storage round-trip (test data only)
- Desktop app stores a dummy credential via `SecureStorageProvider` → visible in Windows Credential Manager → retrieved and compared → session-key path: generate key, encrypt test payload, decrypt, destroy key, verify decryption now impossible

## Design Decisions
(See Key Design Decisions above — consolidated there to avoid duplication.)

## Schema / Data Changes
N/A — no database in Phase 1.

## Config / Environment / Deployment Impact
- No env vars introduced (Credential Manager holds secrets)
- New dev-machine setup steps (document in `AGENTS.md` Local Run Steps when built): create venv + `pip install -e desktop`, `npm install` in `extension/`, run `scripts/register-native-host.py`, load unpacked extension
- No hosting/deploy impact — local-only project (Hosting: none, user-confirmed 2026-07-23)

## Critical Constraints
- The desktop app must NEVER open a listening network socket — enforced by the Task 10 integration test, not just convention
- Native-host stdout is protocol-only; logging must never write to stdout
- No clinical data, audio, transcripts, or real Cliniko API keys anywhere in Phase 1 — test data only
- No custom cryptography — `cryptography` library AES-256-GCM only; keys from `os.urandom`
- Logs must contain no message payloads — envelope metadata (type, version, sizes) only
- Extension host permissions limited to `https://*.cliniko.com/*`; no `<all_urls>`, no broad optional permissions

## Validation / Verification
- `extension/`: `tsc --noEmit`, `eslint`, `vitest` (protocol encode/decode round-trip tests)
- `desktop/`: `ruff check`, `mypy`, `pytest` — unit tests for framing (length prefix edge cases: 0-byte, 1 MB boundary, truncated stream), handshake state machine (version mismatch → typed error; wrong nonce → disconnect), AES-GCM round-trip + tamper detection (auth tag), keyring store/retrieve/delete
- Integration: `pytest` test launching the host process, performing the full hello/ping exchange over real stdio pipes, and asserting via `psutil` that the process has zero listening sockets
- Manual completion-gate check (mirrors `PLAN.md` Phase 1): load unpacked extension in Chrome on a Cliniko page, observe connected indicator, exchange ping/pong, confirm Credential Manager shows the test credential, run `netstat -ano` filtered to the host/app PIDs showing no LISTEN entries
- Success = all automated suites green + manual gate observed on the dev machine

## Deferred / Out of Scope
See `Planning Extraction Summary` → Deferred / Excluded / Accepted Assumptions (single source of truth; nothing additional arose during planning).

## Current State / Handoff Note
- Last completed step: Planning complete
- Current in-progress step: None
- Immediate next action: `/review-plan` hardening pass recommended, then `/execute`
- Open blockers / open questions: None
- Last plan sync: 2026-07-23

## Review History
Each /review invocation appends a one-line entry here. /review uses
this section to detect which round it is. Ignore the placeholder line
when counting rounds.

- (no reviews yet)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
/fix reads from this section when a round has pending decisions.

- (no findings logged yet)

## Tasks

- [ ] 🟥 Step 1: Repo scaffolding
  - Create `extension/` (Vite + CRXJS + TS strict), `desktop/` (pyproject, src layout, PySide6 + pydantic + cryptography + keyring + psutil deps), `protocol/`, `scripts/`, `docs/security/` skeletons
  - Done when: `npm run build` produces an unpacked MV3 bundle and `pip install -e desktop` succeeds with both entry points (`scribe-app`, `scribe-host`) registered
- [ ] 🟥 Step 2: QA tooling
  - Configure `eslint` + `vitest` (extension), `ruff` + `mypy --strict` + `pytest` (desktop); one trivial passing test each side
  - Done when: a single documented command per side runs the full suite green
- [ ] 🟥 Step 3: Protocol definition
  - Author `protocol/messages.schema.json` (envelope: `protocol_version`, `type`, `session_nonce?`, `payload`; messages: `hello`, `hello_ack`, `ping`, `pong`, `error`); mirror as `extension/src/protocol.ts` and `desktop/src/scribe_desktop/protocol.py` (pydantic); round-trip encode/decode tests on both sides against shared JSON fixtures
  - Done when: the same fixture files validate on both sides (drift is a test failure)
- [ ] 🟥 Step 4: Desktop logging foundation
  - `logging_setup.py`: structured file/stderr logging, never stdout; redaction filter rejecting any record containing a `payload` field; unit test proving payload content cannot reach a log line
  - Ref: Critical Constraints (stdout purity, no-payload logging)
- [ ] 🟥 Step 5: Native host stdio framing
  - `native_host.py`: 4-byte LE length-prefixed read/write loop with 1 MB bound, clean EOF handling; unit tests for the framing edge cases listed in Validation
- [ ] 🟥 Step 6: Handshake + origin verification
  - Host validates launch origin argv against the pinned extension ID; implements hello → hello_ack (version negotiation, `os.urandom` session nonce) → ping/pong (nonce echo); typed `error` + exit on any mismatch; state-machine unit tests
  - Ref: Key Design Decision (authentication model)
- [ ] 🟥 Step 7: Extension shell
  - Manifest via CRXJS: pinned `key`, host permissions `https://*.cliniko.com/*`, `nativeMessaging` permission; `background.ts` connects, runs the handshake, retries with backoff, sets badge state; minimal content-script indicator stub on Cliniko pages
  - Ref: Critical Constraints (permission scope)
- [ ] 🟥 Step 8: Desktop status app
  - `app.py`: PySide6 window showing host registration state, last-handshake result and protocol version (read from the host's status file in `%LOCALAPPDATA%`), and a "run self-test" button triggering the storage round-trip of Step 9
  - Done when: window reflects a real handshake performed by Chrome
- [ ] 🟥 Step 9: Secure storage foundation
  - `secure_storage.py`: `SecureStorageProvider` interface; keyring-backed durable store (test credential only); AES-256-GCM session crypto with explicit key destruction; unit tests incl. tamper detection and post-destruction decryption failure
  - Ref: Key Design Decision (ephemeral session keys)
- [ ] 🟥 Step 10: Registration script + no-open-ports integration test
  - `scripts/register-native-host.py` writes the host manifest + HKCU registry key (Chrome only) targeting `scripts/dev-host-launcher.bat`; integration test drives the host over real pipes through the full handshake and asserts zero listening sockets via `psutil`
  - Ref: Critical Constraints (no listening sockets)
- [ ] 🟥 Step 11: Security documents
  - Write the five `docs/security/` documents grounded in the implemented architecture (data-flow map and threat model must reference the real components/boundaries built above, incl. the stdio-trust-boundary rationale); add pointers to them in `AGENTS.md` Subsystem Documentation
- [ ] 🟥 Step 12: Completion gate
  - Run the full manual completion-gate check from Validation / Verification on the dev machine; update `AGENTS.md` (stack rows, Local Run Steps, Current Status) and `CHANGELOG.md`
  - Done when: every item in Validation / Verification is observed and recorded in this plan's handoff note

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
- Next follow-up: Phase 2 (local recording + transcription) via its own `/create-plan`
- Remain out of scope: everything listed under Deferred / Excluded above
- Design decisions that persist: all Key Design Decisions (stack, transport, auth model, protocol versioning, crypto rules, logging discipline)
- Do not rediscover: the stdio-trust-boundary rationale (no custom crypto on the pipe), the stdout-purity rule, and the pinned-`key` extension-ID technique

---
*Plan saved to: .cursor/plans/plan-phase1-security-foundation.md*
*To resume in a new session: open a fresh Agent, run /start-session, then run /load-plan*
