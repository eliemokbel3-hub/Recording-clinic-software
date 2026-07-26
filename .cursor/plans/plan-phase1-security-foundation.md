# Feature Implementation Plan
**Feature:** phase1-security-foundation
**Overall Progress:** `92%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None (derived from `PLAN.md` Phase 1 — Security foundation; hardened by /review-plan 2026-07-23)
- Follow-up plans: None (Phases 2–7 of `PLAN.md` will become their own plans)

## Goal
Build the security foundation for the Cliniko clinical scribe: a Chrome MV3 extension shell restricted to Cliniko domains and a Windows desktop companion shell (Python + PySide6), talking exclusively over Chrome Native Messaging, with credential storage in Windows Credential Manager, an encrypted-session-storage foundation, and the five governing security documents. No clinical features, no audio, no Cliniko API calls yet.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5; executor may be Opus-class; tier-gap dosing applied (design decisions locked, protocol contract specified, per-task acceptance criteria, executor-facts block)

### Agreed Scope (Build Now)
- Monorepo scaffolding with QA tooling: `extension/` (TypeScript + Vite + CRXJS pinned versions, Manifest V3), `desktop/` (Python 3.12 + PySide6, src layout, two entry points `scribe-app` / `scribe-host`), `protocol/` (canonical shared fixtures), `scripts/`, `docs/security/`
- Versioned message protocol with **shared JSON fixtures as the canonical contract**, hand-mirrored TS types and pydantic models each tested against the same fixtures; envelope: `protocol_version`, `type`, `request_id?`, `session_nonce?`, `payload`; messages: `hello`, `hello_ack`, `ping`, `pong`, `error`; per-message-type nonce presence rules and a minimum-supported-version floor encoded in the fixtures
- Stable extension identity: generated RSA keypair, `key` pinned in the manifest, derived extension ID recorded and used in `allowed_origins`
- Native host: binary-mode stdio framing (Windows `O_BINARY` fix), hardened edge-case handling, origin verification from bare argv, hello handshake with version floor and session nonce (a session *identifier*, not authentication)
- Structural no-clinical-data logging: whitelisted-metadata wrapper + content-scanning tripwire filter + rotation; never stdout
- Registration tooling: `register-native-host.py` with `--unregister`, regenerating manifest + launcher from the current interpreter path, verifying the registry write
- Extension shell: badge-based connection state, full MV3 service-worker lifecycle handling (reconnect on wake/restart, `chrome.alarms` backoff, fresh handshake per reconnect), unit-tested with mocked `chrome.runtime`
- Minimal desktop window: registration status + "run self-test" button only (no host↔UI live-state plumbing in Phase 1)
- Secure storage foundation: keyring→Windows Credential Manager keyed by `(clinic_id, secret_name)` (test credential only), AES-256-GCM per-session keys with explicit destruction
- No-network-sockets integration test covering BOTH processes, polling full `net_connections()` during a live handshake
- The five security documents in `docs/security/`, grounded in the built architecture and enumerating accepted residual risks
- Phase-1 completion gate (from `PLAN.md`): authenticated test messages exchanged, no clinical data, verified absence of exposed local network ports

### Deferred — Actionable Later
- Phases 2–7 of `PLAN.md` (recording/transcription, note generation, Cliniko API integration, workflow safeguards, privacy controls, pilot)
  - Why deferred: `PLAN.md`'s own phased roadmap; each phase becomes its own plan
  - Intended future outcome: one `/create-plan` per phase, anchored on `PLAN.md`
  - Relevant files / subsystems: all — Phase 1 lays their foundation
  - Dependencies / prerequisites: Phase 1 completion gate passed
  - Recommended next action: `/create-plan` for Phase 2 after this plan completes
  - Risk if deferred: minor: intentional staging, not a gap
- Host↔app named-pipe IPC (the locked Phase-2 topology's relay channel)
  - Why deferred: nothing to relay in Phase 1; the pipe's real requirements (recording commands, state streaming) are Phase 2's — user-confirmed 2026-07-23
  - Intended future outcome: user-ACL'd Windows named pipe between the thin host relay and the long-lived recorder app; still zero network sockets
  - Relevant files / subsystems: `desktop/src/scribe_desktop/native_host.py`, future recorder service
  - Dependencies / prerequisites: Phase 2 plan; Design Decision "Process topology" below
  - Recommended next action: first task of the Phase 2 plan
  - Risk if deferred: minor: host is built stateless/thin against this topology, so no rework is expected
- Runtime clinic-subdomain allowlist (beyond the manifest wildcard)
  - Why deferred: no page UI exists in Phase 1 to enforce it (content scripts arrive in Phase 5); the manifest wildcard `https://*.cliniko.com/*` still bounds the extension — user-confirmed 2026-07-23
  - Intended future outcome: desktop-configured allowlist of the two clinics' subdomains, enforced when page UI lands
  - Relevant files / subsystems: extension background/content scripts (Phase 5), desktop clinic-connection screen
  - Dependencies / prerequisites: real subdomains recorded at install time
  - Recommended next action: fold into the Phase 5 plan
  - Risk if deferred: minor: Phase 1 exchanges no clinical data, so wildcard-wide exposure is nil
- Full `SessionState` enum from `PLAN.md` core types
  - Why deferred: Phase 1's connection state is a deliberate, separate throwaway enum (connecting/connected/disconnected/error); the real `SessionState` (idle→recording→…→expired) belongs to Phase 2's recording lifecycle — user-confirmed 2026-07-23
  - Intended future outcome: `SessionState` defined with its true states when recording exists
  - Relevant files / subsystems: `desktop/src/scribe_desktop/protocol.py`
  - Dependencies / prerequisites: Phase 2 plan
  - Recommended next action: define in Phase 2 alongside `RecordingSession`
  - Risk if deferred: minor: nothing consumes it yet
- PyInstaller packaging + installer for the desktop app
  - Why deferred: `PLAN.md` Phase 7 handles installation; dev-mode launcher suffices until then
  - Intended future outcome: signed, packaged desktop app installed on both clinic machines — also the real mitigation for the venv/launcher-hijack residual risk in the threat model
  - Relevant files / subsystems: `desktop/`, `scripts/register-native-host.py`
  - Dependencies / prerequisites: Phases 2–6 features stable
  - Recommended next action: fold into the Phase 7 plan
  - Risk if deferred: minor: dev machines run from source meanwhile; residual risk documented in threat model
- GitHub Actions CI (lint/type/test on push)
  - Why deferred: remote now exists (added 2026-07-23) but CI adds most value once Task 1's QA suites exist
  - Intended future outcome: workflow running both QA suites from Task 1
  - Relevant files / subsystems: `.github/workflows/`
  - Dependencies / prerequisites: Task 1 complete
  - Recommended next action: add a workflow after Task 1, or before Phase 2 at latest
  - Risk if deferred: minor: repo is now backed up off-machine; only automated checks are missing
  - Revisit by: before Phase 2 begins

### Excluded — Revisit Only If Needed
- Edge/Brave/other Chromium browsers
  - Why excluded: `PLAN.md` and user confirmed Chrome only (2026-07-23); each browser adds its own native-messaging registration + test surface
  - When to revisit: if a clinic machine standardises on Edge
  - Relevant files / subsystems: `scripts/register-native-host.py`, host manifest
  - Recommended next action (if any): add the Edge registry path alongside Chrome's
- Content-script page UI on Cliniko pages (including the Phase-1 indicator stub)
  - Why excluded: cut in plan hardening (user-confirmed 2026-07-23) — the badge proves connectivity; injecting code into live clinical pages before Phase 5 owns embedded UI adds risk with no gate value
  - When to revisit: Phase 5 (workflow safeguards) introduces content scripts with their real requirements
  - Relevant files / subsystems: `extension/src/`
  - Recommended next action (if any): none now
- Host→UI live-state plumbing (status file or otherwise)
  - Why excluded: cut in plan hardening (user-confirmed 2026-07-23) — the reviewed status-file design was spoofable, stale-prone, and unneeded by the completion gate
  - When to revisit: Phase 2, via the named-pipe topology (see Deferred)
  - Relevant files / subsystems: `desktop/src/scribe_desktop/app.py`
  - Recommended next action (if any): none now
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
- Manifest wildcard `https://*.cliniko.com/*` is acceptable for Phase 1 (user-confirmed 2026-07-23)
  - Why accepted for now: exact clinic shard subdomains not yet recorded; runtime allowlist deferred to Phase 5 (see Deferred)
  - Risk if assumption becomes false: if Cliniko moves off `*.cliniko.com`, the manifest needs updating
  - Trigger for revisit: install time (Phase 7) records the real subdomains
  - Recommended next action: capture the two subdomains in `AGENTS.md` when known
- Same-user local malware is outside the defended boundary in Phase 1
  - Why accepted for now: a same-user attacker can repoint the HKCU registration, replace the launcher, or read process memory — no extension-side or host-side control changes that; real mitigation is Phase 7 packaging/signing plus OS hygiene
  - Risk if assumption becomes false: n/a — this is a documented residual risk, enumerated in `docs/security/threat-model.md` (Task 11) with cheap tripwires (startup path logging) in place
  - Trigger for revisit: Phase 7 packaging
  - Recommended next action: none in Phase 1

### Key Design Decisions
- Desktop stack = Python 3.12 + PySide6 (user-confirmed 2026-07-23)
  - Why: later phases need faster-whisper / llama.cpp-family bindings, first-class in Python; PySide6 covers the settings screens; `keyring` reaches Windows Credential Manager
  - Alternatives rejected: .NET/WPF (would force a Python sidecar for ML anyway); Rust/Tauri (immature ML bindings, slower delivery)
  - Still applies to follow-up work: Yes
- Extension stack = TypeScript + Vite + CRXJS with **pinned versions**; WXT is the recorded fallback if CRXJS breaks on the chosen Vite major (CRXJS has a maintenance-gap history)
  - Why: type-checked message contracts; standard MV3 tooling
  - Alternatives rejected: plain JS (loses contract checking); WXT now (CRXJS suffices; fallback recorded)
  - Still applies to follow-up work: Yes
- **Process topology (locked for Phase 2, user-confirmed 2026-07-23): a long-lived desktop app owns recording; the Chrome-spawned native host is a thin, stateless relay.** They will connect via a user-ACL'd Windows named pipe (local IPC — not a network socket). Phase 1 therefore builds the host with no session state beyond the live handshake and no assumption of outliving its stdio connection.
  - Why: `PLAN.md` requires recording to survive browser crash/close ("Record the microphone independently of the browser tab"), but Chrome terminates the host on port disconnect — so the recorder cannot live in the host process
  - Alternatives rejected: host owns recording (dies with Chrome — violates PLAN.md safety); localhost socket between host and app (violates no-network-ports)
  - Still applies to follow-up work: Yes — this is the foundation Phase 2 builds on
- Native Messaging is the ONLY browser transport; neither desktop process may ever open a listening network socket
  - Why: `PLAN.md` security requirement; stdio channel is spawned per-extension by Chrome and scoped by `allowed_origins`
  - Alternatives rejected: localhost WebSocket/HTTP server (exposes a port any local process could probe)
  - Still applies to follow-up work: Yes — the Phase-2 named pipe preserves it
- Authentication and trust model: `allowed_origins` pins the extension ID (Chrome enforces which extension can launch the host); the host verifies the origin argv as defense-in-depth and refuses to enter protocol mode without a valid origin. The hello handshake negotiates a version (with a minimum floor) and issues a random per-session **nonce, which is a session/correlation identifier — NOT an authentication mechanism** (any process able to reach the host's stdio already sees it; a same-user attacker owns both endpoints regardless). The threat model documents this honestly, and enumerates HKCU-registration/manifest/launcher hijack by same-user code as accepted residual risk, with the host logging its resolved manifest, launcher, and executable paths at startup as a cheap detection tripwire.
  - Why: right-sized to the real boundary; no ceremony crypto on a local stdio pipe
  - Alternatives rejected: mutual TLS / signed messages over stdio (adds nothing against the actual threat)
  - Still applies to follow-up work: Yes
- Protocol contract = **shared fixtures in `protocol/fixtures/` are canonical**; TS types and pydantic models are hand-mirrored and each side's tests validate against the same fixture files (drift = test failure). No JSON Schema file; codegen only if the message set grows in later phases.
  - Why: three artifacts (schema + two mirrors) was over-machinery for five messages; fixtures make the contract executable
  - Alternatives rejected: JSON Schema source of truth (decorative unless validated — dropped in plan hardening)
  - Still applies to follow-up work: Yes — revisit codegen at Phase 2 if the message set grows
- Envelope carries `request_id?` from day one (unused beyond echo tests in Phase 1)
  - Why: Phase 4's retry-and-reconcile and Phase 2's command/response flows need correlation; retrofitting an envelope field after both sides ship is churn
  - Alternatives rejected: adding it later (cheap now, annoying then)
  - Still applies to follow-up work: Yes
- Ephemeral session keys: AES-256-GCM via `cryptography`, `os.urandom(32)`, in-memory only, destroyed explicitly; durable secrets in Windows Credential Manager via `keyring`, keyed `(clinic_id, secret_name)` from the start
  - Why: matches `PLAN.md` per-session encryption + cryptographic deletion; two clinics are a known Phase-4 requirement, so the storage key is namespaced now to avoid interface churn — but the interface stays minimal (store/retrieve/delete + key lifecycle; no queueing or migration hooks)
  - Alternatives rejected: DPAPI-only; custom key files on disk; un-namespaced keys (Phase-4 churn)
  - Still applies to follow-up work: Yes
- Logging is structured, clinical-data-free, and **structurally enforced**: code logs only through a wrapper that accepts a whitelisted metadata schema (message type, protocol version, byte sizes, timings, state names); a last-line tripwire filter scans formatted records for protocol-payload signatures and drops + counts violations; a lint rule bans interpolating `message`/`payload`/`envelope` identifiers into logging calls
  - Why: a field-name blocklist is bypassed by any `log.info(f"{message}")`; `PLAN.md` Phase 6 forbids payload content in logs — enforcement must be structural
  - Alternatives rejected: field-name filter alone (trivially bypassed); ad-hoc logging until Phase 6
  - Still applies to follow-up work: Yes
- Host name is locked: `com.scribe.cliniko_host` (used in the manifest, registry key, and `connectNative` call — never re-derived)

## Key Findings

### Files / Symbols Involved
All new — the repo currently contains only documentation and workflow tooling (verified: no application code). Planned layout:
- `protocol/fixtures/*.json` — canonical protocol contract (envelope + five Phase-1 messages, valid and invalid cases)
- `extension/vite.config.ts` + `extension/src/manifest.ts` (CRXJS `defineManifest`, pinned `key`), `extension/src/background.ts`, `extension/src/protocol.ts`, `extension/src/background.test.ts`
- `desktop/pyproject.toml`; `desktop/src/scribe_desktop/`: `app.py` (PySide6 entry), `native_host.py` (stdio framing + handshake state machine), `protocol.py` (pydantic models + throwaway connection-state enum), `secure_storage.py`, `logging_setup.py`
- `scripts/register-native-host.py` (register/`--unregister`; generates manifest + launcher), generated `scripts/dev-host-launcher.bat`
- `scripts/generate-extension-key.py` or documented openssl commands; `extension/KEY.md` recording the derived ID
- `docs/security/intended-use.md`, `data-flow-map.md`, `threat-model.md`, `retention-schedule.md`, `incident-process.md`

### Codebase Integration Notes — executor facts (do not rediscover)
- **Host name:** `com.scribe.cliniko_host` everywhere (lowercase alphanumerics + `.` + `_`; no leading/trailing/consecutive dots)
- **Framing:** 4-byte **native-byte-order** length prefix (LE on our x64 target) + UTF-8 JSON. Limits: host→Chrome 1 MB (platform); Chrome→host up to 4 GB (platform) — **this project enforces 1 MB both directions as policy**
- **Windows binary-stdio fix (classic killer):** Python opens stdio in text mode on Windows; the host MUST set `O_BINARY` on stdin/stdout (`msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)`, same for stdout) and read/write via `sys.stdin.buffer` / `sys.stdout.buffer`, or `\n`→`\r\n` translation corrupts frames
- **Origin argv:** Chrome passes the caller as the bare first argument `chrome-extension://<id>/` (no `--origin=` flag) and appends `--parent-window=<HWND>` on Windows; the launcher must forward `%*`
- **Registry:** `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host`, default value = absolute path to the host manifest JSON; `allowed_origins` entries are exact `chrome-extension://<id>/` strings (trailing slash, no wildcards); manifest `path` may point to a `.bat`
- **Registration changes need a genuinely FRESH Chrome browser process.** Chrome's background mode keeps `chrome.exe` alive after the last window closes, and a reopened window attaches to the stale process — which keeps reporting `Specified native messaging host not found` for registrations it didn't see at startup. Closing windows is NOT a restart; verify no `chrome.exe` remains (or `taskkill /IM chrome.exe /F`) before relaunching. This was the reproducible trigger behind the Phase-1 gate failures (confirmed 2026-07-26: identical registration flipped from all-not-found to full hello_ack on the first truly fresh process). When debugging resolution, launch Chrome with `--enable-logging --v=1` and read `chrome_debug.log` rather than guessing
- **Registration must live at a SPACE-FREE path, and the host must be an `.exe`** — both were learned the hard way at the Phase-1 gate, and both fail *silently*: Chrome reports only `Specified native messaging host not found`, spawns nothing, and the extension sees a bare disconnect. A manifest under `C:\Recording clinic software\...` is never resolved (note every working native host on a normal Windows machine sits at a space-free path); `.bat`/`.cmd` hosts are likewise not launched. Registration therefore installs into `%LOCALAPPDATA%\ClinikoScribe\`: a copy of `scribe-host.exe` (pip **gui-scripts** entry point — windowless, receives Chrome's bare origin argv plus `--parent-window`; the copy still runs repo code because the launcher embeds the venv interpreter path) plus the host manifest. `register-native-host.py` refuses to install to a spaced path, and `test_registration_chain_is_chrome_resolvable` enforces both rules against the live registration. Rerun registration after any venv move or `pip install -e desktop`
- **Extension identity:** manifest `key` = base64 DER SubjectPublicKeyInfo of an RSA public key (`openssl genrsa 2048 > key.pem; openssl rsa -in key.pem -pubout -outform DER | openssl base64 -A`); the ID is derived from SHA-256 of the public key (first 16 bytes → a–p). Commit the public key + derived ID (`extension/KEY.md`); keep `key.pem` out of the repo (gitignore it); note: an unpacked extension's `key` gives ID *stability*, not secrecy — and the Chrome Web Store assigns its own ID at Phase-7 publication (migration noted there)
- **MV3 service-worker lifecycle:** an active native-messaging port extends SW lifetime (Chrome ≥ ~116), but the SW still dies on browser restart/update/crash; `setTimeout` does not survive suspension — reconnect logic must run at SW top level and in `onDisconnect`/`onStartup`/`onInstalled`, with `chrome.alarms` for backoff intervals
- **keyring→Credential Manager:** generic-credential blob limit is 2560 bytes (~1280 chars via keyring's UTF-16) — Cliniko API keys fit with huge margin
- **psutil:** use `Process.net_connections()` (`connections()` is deprecated in psutil 6); no elevation needed for own child processes; assert while the handshake keeps the host alive
- `.env.example` documents zero env vars — correct; nothing in Phase 1 introduces one

### External / API Findings
- No Cliniko API usage in Phase 1 (first API call is Phase 4)
- Cliniko shards live under `*.cliniko.com`; the two clinics' subdomains get recorded at install time

## Planned Workflow Summary

### Flow 1 — Authenticated handshake (the Phase-1 deliverable)
- Chrome (extension loaded) → service worker top-level runs connect logic → `chrome.runtime.connectNative("com.scribe.cliniko_host")` → Chrome launches the registered host → host sets binary stdio, logs its resolved paths, verifies origin argv (exits non-zero before reading stdin if missing/unknown) → extension sends `hello {protocol_version, request_id}` → host validates version ≥ floor, replies `hello_ack {protocol_version, session_nonce}` → `ping`/`pong` echo the nonce → badge shows connected. Any violation → typed `error` + clean disconnect. On disconnect from any cause, the extension badge changes, backoff (via `chrome.alarms`) schedules reconnect, and every reconnect is a full fresh handshake with a new nonce.

### Flow 2 — Secure storage round-trip (test data only)
- Desktop app "run self-test": store a dummy credential under `(clinic_id="test", secret_name="probe")` via `SecureStorageProvider` → visible in Windows Credential Manager → retrieve, compare, delete → session-key path: generate key, encrypt test payload, decrypt, destroy key, verify decryption now fails

## Design Decisions
(Consolidated in Key Design Decisions above.)

## Schema / Data Changes
N/A — no database in Phase 1.

## Config / Environment / Deployment Impact
- No env vars introduced (Credential Manager holds secrets)
- Registration is **per Windows user** (HKCU) and must be rerun after any venv move — `register-native-host.py` regenerates the manifest from the *current* interpreter's `scribe-host.exe` and verifies the registry value after writing (never hand-edit); `pip install -e desktop` must run first so the exe exists; record this in `AGENTS.md` Local Run Steps (Task 12)
- Second-machine replication (Phase 7 preview, documented in Task 11's docs): per-machine registration run, Developer-Mode unpacked loading until Web Store publication, per-machine venv paths
- No hosting/deploy impact — local-only project (Hosting: none, user-confirmed 2026-07-23)

## Critical Constraints
- NEITHER desktop process (`scribe-host`, `scribe-app`) may ever open a listening network socket — and the Task 10 test asserts the **entire `net_connections()` list is empty** (not just LISTEN), polled during a live handshake; `QtNetwork` and `socket` server APIs are import-banned in lint
- Native-host stdout carries ONLY framed protocol bytes; stdio must be in binary mode; all logging to file/stderr
- No clinical data, audio, transcripts, or real Cliniko API keys anywhere in Phase 1 — test data only
- No custom cryptography — `cryptography` AES-256-GCM only; keys from `os.urandom`
- Logs contain whitelisted metadata only (structural enforcement per Key Design Decisions); log files get rotation and appear in the retention schedule
- Extension host permissions limited to `https://*.cliniko.com/*` + `nativeMessaging`; no `<all_urls>`, no broad optional permissions, no content scripts in Phase 1
- `key.pem` (extension keypair) never enters the repo; oversized declared frame lengths are rejected WITHOUT allocation

## Validation / Verification
- `extension/`: `tsc --noEmit`, `eslint`, `vitest` — protocol encode/decode vs shared fixtures; background handshake/reconnect state machine with mocked `chrome.runtime` (connect, hello_ack validation, nonce echo, disconnect → badge + alarm-scheduled reconnect → fresh handshake)
- `desktop/`: `ruff`, `mypy --strict`, `pytest` — framing (0-byte, 1 MB boundary, truncated stream, oversized declared length rejected without allocation, invalid UTF-8, malformed JSON → typed error, back-to-back messages in one read); handshake state machine (version below floor → typed error + disconnect; wrong/missing nonce → disconnect; missing/unknown origin argv → exit non-zero before reading stdin); logging (wrapper accepts only whitelisted schema; `logger.info(f"{envelope}")`-style misuse is dropped + counted; rotation works); AES-GCM round-trip + tamper detection + post-destruction failure; keyring store/retrieve/delete under `(clinic_id, secret_name)`
- Both sides validate against the SAME `protocol/fixtures/` files — fixture drift is a test failure
- Integration (Task 10): spawn the real host over real pipes, complete the full handshake, assert empty `net_connections()` on host AND a launched `scribe-app` during the exchange; assert the first stdout bytes are a valid length prefix (launcher stdout-purity)
- Manual completion gate (mirrors `PLAN.md` Phase 1): load unpacked extension in Chrome on a Cliniko page → badge connected → ping/pong in host log → self-test passes → Credential Manager shows then loses the test credential → `netstat -ano` on both PIDs shows no LISTEN entries → kill host mid-session and watch badge + automatic reconnect
- Success = all automated suites green + every manual gate item observed and recorded in the handoff note

## Deferred / Out of Scope
See `Planning Extraction Summary` → Deferred / Excluded / Accepted Assumptions (single source of truth; all dispositions user-confirmed 2026-07-23 during plan hardening).

## Current State / Handoff Note
- Last completed step: Step 12 gate debugging RESOLVED (2026-07-26): live Chrome↔host session confirmed (hello_ack + 1-min pings in host log). Three real fixes landed en route (exe host, space-free install dir, fresh-process requirement — see executor facts); probe diagnostics removed
- Current in-progress step: Step 12 — remaining manual gate items (user at Chrome: badge observed green, self-test, kill-host reconnect, netstat)
- Immediate next action: user confirms remaining gate observations; then completion pass (AGENTS.md/CHANGELOG update, 100%, lifecycle decision)
- Open blockers / open questions: None — connection proven live from the host log
- Last plan sync: 2026-07-24
- Open blockers / open questions: None
- Last plan sync: 2026-07-24

## Review History
Each /review invocation appends a one-line entry here. /review uses
this section to detect which round it is. Ignore the placeholder line
when counting rounds.

- 2026-07-24 round 1: 1 CRIT / 3 HIGH / 7 MED / 18 LOW; skew=none; action=none

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
/fix reads from this section when a round has pending decisions.

### Round 1 — 2026-07-24
Round status: Closed
Source: Claude Code

#### CRIT-001: `extension/src/manifest.ts:13` — missing "alarms" permission kills the service worker
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: background.ts registers chrome.alarms listeners at SW top level; without the "alarms" permission chrome.alarms is undefined in real Chrome, the top-level addListener throws, and the entire service worker dies — no connect, no badge, no reconnect. Mocked unit tests cannot catch this.
- Current behaviour: permissions = ["nativeMessaging"] only
- Desired behaviour: permissions include "alarms"
- Verification: rebuild; dist/manifest.json contains "alarms"; Step 12 in-Chrome gate loads without SW error
- Regression risk: none — additive manifest change
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### HIGH-001: `extension/src/manifest.ts` — missing "action" key breaks all badge calls
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: chrome.action is undefined without an "action" manifest key; setBadge throws inside ConnectionManager.setState, aborting connect() — and the badge is the Phase-1 gate's primary connectivity indicator.
- Current behaviour: no action key in manifest
- Desired behaviour: "action": {} (with default_title) declared
- Verification: rebuild; dist/manifest.json contains action; badge renders at Step 12 gate
- Regression risk: none — additive
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### HIGH-002: `extension/src/connection.ts:58-72` — no handshake timeout; manager wedges in "connecting" forever
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: a host that opens the port but never sends hello_ack leaves state="connecting" permanently: connect() early-returns in that state, ping() no-ops, no alarm is scheduled on entering connecting, and the open port keeps the SW alive — nothing ever fires again. Permanent "…" badge until browser restart.
- Current behaviour: no watchdog on the connecting state
- Desired behaviour: a handshake-timeout alarm scheduled on entering connecting; unanswered hello → fail() → backoff reconnect
- Invariant: from every reachable ConnectionManager state, some listener or alarm eventually fires that can advance or reset the state.
- Verification: unit test — connect, deliver no ack, fire the timeout alarm, assert error state + reconnect scheduled
- Regression risk: connect()/onMessage paths used by background.ts top level, onStartup, onInstalled, both alarms
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### HIGH-003: `desktop/src/scribe_desktop/logging_setup.py:44-51` — tripwire misses unquoted-key (pydantic repr) leaks
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: the promised misuse case — logger.info(f"{envelope}") with a pydantic Envelope — renders as protocol_version=1 type='ping' session_nonce='…' payload={} (unquoted keys). All _PAYLOAD_SIGNATURES are JSON-quoted style, so nothing matches and the real nonce reaches the log. The existing test uses json.dumps of a dict, which passes while the promised case leaks.
- Current behaviour: only quoted-key signatures detected
- Desired behaviour: unquoted signatures (session_nonce=, payload=, protocol_version=) also trip; test logs an actual Envelope via f-string
- Pattern siblings: none found (single tripwire site)
- Verification: new test with a real Envelope f-string is dropped + counted
- Regression risk: legit operational lines containing "count=" etc. must not false-positive — log_event's whitelisted keys must stay disjoint from signature strings
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-001: both protocol mirrors — error-code taxonomy divergence (version_below_floor dead; bad_nonce vs malformed)
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: version_below_floor is unreachable on BOTH sides (ge=1 / <1 checks fire first while floor==1) yet the plan promises "version below floor → typed error"; a missing required nonce yields bad_nonce in TS but malformed in Python; explicit "session_nonce": null is accepted by pydantic, rejected by TS. Round-one drift in the exact taxonomy the fixtures-canonical decision exists to prevent.
- Current behaviour: same wire input classified differently per side; floor code dead
- Desired behaviour: aligned codes on both mirrors; floor violation emits version_below_floor from run_host; explicit null rejected in Python; tests assert codes, not just type=="error"
- Verification: tightened fixture/loop tests asserting payload code on both sides
- Regression risk: extension treats any error as fail(), so behaviour-compatible; fixture tests on both sides
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-002: `desktop/src/scribe_desktop/native_host.py:128,169` — double setup_logging leaves an orphaned open handler; Windows rotation breaks
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: setup_logging clears handlers without closing them; main() + run_host() both configure "scribe-host", leaving two open handles on the same log file — on Windows the rotation rename at 1 MB fails (file locked) and rotation stops.
- Current behaviour: duplicate configuration, unclosed replaced handlers
- Desired behaviour: run_host accepts a configured logger (main passes its own; tests pass tmp-dir loggers); setup_logging closes handlers it clears
- Verification: rollover test (tiny maxBytes) passes; single handler set after main-path setup
- Regression risk: run_host's test callers use logger_name — keep that path working
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-003: `desktop/src/scribe_desktop/native_host.py:138-159` — unguarded write_frame calls in run_host
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: if the peer dies mid-session (exactly when error-reply paths run), write_frame raises BrokenPipeError/OSError uncaught — traceback to stderr, no clean log event, ungraceful exit.
- Current behaviour: replies written without exception handling
- Desired behaviour: protocol-loop writes wrapped; whitelisted log event; non-zero return
- Verification: unit test with a broken output stream
- Regression risk: run_host callers (entry point, tests); stdout purity unaffected
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-004: `scripts/register-native-host.py:24-27` + siblings — identity constants re-declared as literals in four places
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: HOST_NAME/EXTENSION_ID/EXPECTED_ORIGIN/REGISTRY_KEY exist independently in register-native-host.py, native_host.py, status.py, protocol.py, and the integration test; drift in EXTENSION_ID silently breaks the allowed_origins/origin-check pairing — the "never re-derived" invariant the plan locks.
- Current behaviour: four literal copies
- Desired behaviour: one canonical module (scribe_desktop.protocol or .identity) imported everywhere; the script runs inside the venv so it can import it
- Pattern siblings: `desktop/tests/test_integration_no_sockets.py:29` (hard-coded origin), `desktop/src/scribe_desktop/status.py:17`
- Verification: grep shows one definition site; all tests green
- Regression risk: registration script import path (runs from repo root inside venv)
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-005: `extension/src/connection.ts:75-79` — ping liveness cannot detect a silently-dead host
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: a pong that never arrives is never noticed (no outstanding-ping tracking), so a hung host keeps the badge "OK" forever; only a wrong pong triggers fail(). Also makes the beyond-plan PING_ALARM actually load-bearing (documented in plan note).
- Current behaviour: each ping overwrites pingRequestId; silence = healthy
- Desired behaviour: if the next PING_ALARM fires with the previous ping unanswered → fail()
- Verification: unit test — ping, no pong, next alarm → error + reconnect scheduled
- Regression risk: ping()/onAlarm callers; connection tests
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-006: `protocol/fixtures/invalid/` — no fixture exercises an unknown extra envelope key
- Triage: Fix-now
- Fix route: fix-on-fast (mechanical fixture + both suites already glob the dir)
- Why it matters: TS ENVELOPE_KEYS rejection vs pydantic extra="forbid" symmetry — the exact drift the fixtures-canonical design exists to catch — is untested by the shared suite.
- Current behaviour: extra-key rejection tested on neither side via fixtures
- Desired behaviour: invalid/extra_envelope_key.json with a stray field; both suites pick it up automatically
- Verification: both fixture suites reject the new file
- Regression risk: none
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### MED-007: `desktop/src/scribe_desktop/native_host.py:169-172` — startup tripwire logs less than the plan claims
- Triage: Fix-now
- Fix route: premium-only
- Why it matters: the plan's trust-model decision and Step 5's completion note promise logging of the resolved MANIFEST and LAUNCHER paths (the hijack tripwire); main() logs only executable, module, and cwd.
- Current behaviour: registry-resolved manifest path and launcher path never logged
- Desired behaviour: read the HKCU value at startup, log the manifest path and its "path" entry via log_event
- Verification: unit test with a registry stub or the real registered machine; log contains both paths
- Regression risk: none (additive logging via whitelisted "path" key)
- /fix decision: Applied
- /fix notes: applied and verified in the round-1 fix pass 2026-07-24 (both QA suites green: 71 desktop + 36 extension tests); pattern siblings touched where listed
- /fix date: 2026-07-24
- /fix applied by: Claude Code

#### LOW-001: `desktop/tests/test_protocol.py:45` — vacuous assertion (`… or True`) — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-002: desktop test files — frame/builder helpers copy-pasted across three files; consolidate in conftest — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-003: `scripts/register-native-host.py:61` — ascii encode crashes on non-ASCII paths; cmd reads OEM codepage — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-004: `extension/src/background.ts:7` — dead re-export of HOST_NAME — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-005: `desktop/tests/test_integration_no_sockets.py:29,78` — hard-coded origin + magic nonce length 64 — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-006: `extension/src/background.ts:10` — onDisconnect never reads chrome.runtime.lastError (loses "host not found" diagnostic) — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-007: `extension/src/connection.ts:124-142` — fail() + queued onDisconnect can double-increment backoff — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-008: `desktop/src/scribe_desktop/framing.py:68-72` — prefix read should use _read_exact (short-read robustness) — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-009: `desktop/src/scribe_desktop/secure_storage.py` — zeroization is best-effort (immutable copies survive); document residual in threat model at Step 11 — Triage: Fix-now-if-tied (Step 11); Decision: Applied; applied by: Claude Code (2026-07-24 — documented in docs/security/threat-model.md "Data-at-rest residual risks")
#### LOW-010: `desktop/src/scribe_desktop/status.py:37-41` — only FileNotFoundError caught; PermissionError crashes scribe-app at launch — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-011: `desktop/src/scribe_desktop/secure_storage.py:41-51` — secret_name never validated (empty accepted) — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-012: `desktop/src/scribe_desktop/logging_setup.py:89` — unguarded mkdir; unwritable LOCALAPPDATA crashes host before origin check — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-013: plan Step 2 note overclaims "6 valid fixtures / 18 tests each" (5 valid; 17 protocol tests/side) — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-014: `desktop/tests/test_logging_setup.py:58-61` — rotation asserted by configuration only; add a real rollover test — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-015: `desktop/tests/test_integration_no_sockets.py:31-34` — silent auto-skip hides the no-sockets proof on fresh clones/CI — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-016: `desktop/tests/test_status_and_app.py:10-18` — registration test vacuous when machine unregistered — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-017: `extension/src/connection.test.ts:174-176` — comment claims a stale-nonce-rejection scenario the test never exercises — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)
#### LOW-018: generated launcher silently substitutes pythonw.exe for the plan's "python" — document the choice in the plan/AGENTS.md — Triage: Fix-now; Decision: Applied; applied by: Claude Code (2026-07-24)

## Tasks

- [x] 🟩 Step 1: Scaffolding + QA tooling — done 2026-07-24; dev machine runs Python 3.14.6 (plan targeted 3.12; `requires-python = ">=3.12"`, all deps installed clean — revalidate ML wheels at the Phase 2 benchmark); pinned: CRXJS 2.7.1, Vite 8.1.5, TS 6.0.3, vitest 4.1.10, eslint 10.7.0
  - `extension/` (Vite + CRXJS pinned exact versions, TS strict, eslint, vitest), `desktop/` (pyproject with PySide6, pydantic, cryptography, keyring, psutil; ruff + mypy --strict + pytest; entry points `scribe-app`, `scribe-host`), `protocol/fixtures/`, `scripts/`, `docs/security/` skeletons; one trivial passing test per side; lint rules: `QtNetwork`/socket-server import ban, no `message`/`payload`/`envelope` interpolation in logging calls
  - Done when: `npm run build` yields an unpacked MV3 bundle, `pip install -e desktop` succeeds, one documented command per side runs its full QA suite green
- [x] 🟩 Step 2: Protocol contract — done 2026-07-24; 5 valid + 11 invalid fixtures (2 added in round-1 fixes) + meta.json; both mirrors fixture-tested (count corrected per LOW-013)
  - Author `protocol/fixtures/*.json` (canonical): envelope `protocol_version`/`type`/`request_id?`/`session_nonce?`/`payload`; messages `hello`, `hello_ack`, `ping`, `pong`, `error`; per-type nonce presence rules; version floor; valid AND invalid cases. Mirror as `extension/src/protocol.ts` and `desktop/.../protocol.py` (pydantic + throwaway connection-state enum), each tested against the same fixtures
  - Ref: Key Design Decision (fixtures-canonical protocol)
- [x] 🟩 Step 3: Extension identity — done 2026-07-24; ID `mbmhglgadhdohpgbmpbjnaifjagfdfid` pinned + recorded in `extension/KEY.md`; key.pem gitignored; in-Chrome load check deferred to Step 12 gate
  - Generate the RSA keypair (commands in executor facts), pin `key` in the CRXJS manifest, record the derived extension ID in `extension/KEY.md`, gitignore `key.pem`
  - Done when: two consecutive unpacked loads yield the same extension ID, and that ID is recorded for Step 5's `allowed_origins`
- [x] 🟩 Step 4: Logging + stdio framing (host core) — done 2026-07-24; framing in `framing.py` (11 edge tests), logging tripwire proven against f-string misuse
  - `logging_setup.py`: structural wrapper + tripwire filter + rotation per the logging Design Decision; `native_host.py`: binary-mode stdio (`O_BINARY` + `.buffer`), 4-byte native-order framing with the 1 MB policy bound and all framing edge cases from Validation
  - Ref: executor facts (binary-stdio fix); Critical Constraints (stdout purity)
- [x] 🟩 Step 5: Handshake + origin verification — done 2026-07-24; state machine + loop + origin-refusal-before-stdin all unit-tested (14 new tests)
  - Host startup: log resolved manifest/launcher/executable paths; verify bare-argv origin (`chrome-extension://<id>/`, tolerate `--parent-window=`), exit non-zero before reading stdin when missing/unknown; hello → hello_ack (version floor check, `os.urandom` nonce) → ping/pong nonce echo; typed `error` + clean exit on every violation; full state-machine unit tests
  - Ref: Key Design Decision (authentication and trust model)
- [x] 🟩 Step 6: Registration tooling — done 2026-07-24; REVISED TWICE on 2026-07-25 at the Step 12 gate, both from the same silent Chrome error (`Specified native messaging host not found`): (a) `.bat` hosts are not launched → switched to the gui-scripts `scribe-host.exe`; (b) **the real blocker** — a manifest under the repo's spaced path `C:\Recording clinic software\...` is never resolved by Chrome → registration now installs manifest + exe copy into `%LOCALAPPDATA%\ClinikoScribe\`. Script refuses spaced install dirs; `test_registration_chain_is_chrome_resolvable` enforces both rules against the live registration; repo-side artifacts removed
  - `scripts/register-native-host.py`: generates the host manifest (pinned `allowed_origins` from Step 3) and `dev-host-launcher.bat` (`@echo off`, absolute venv python, explicit cwd, `%*` forwarding) from the CURRENT interpreter path; writes + verifies the HKCU registry value; `--unregister` removes key + generated files
  - Ref: executor facts (registry, launcher rules)
- [x] 🟩 Step 7: Extension shell — done 2026-07-24; ConnectionManager unit-tested (10 tests: handshake, foreign nonce, backoff growth+reset, fresh-handshake-per-reconnect); note: executed AFTER this, Step 9 was built BEFORE Step 8 (self-test button consumes secure_storage) — ordering adaptation only, no scope change
  - CRXJS manifest: pinned `key`, `https://*.cliniko.com/*` + `nativeMessaging` only, NO content scripts; `background.ts`: connect at SW top level, full handshake with hello_ack/nonce validation, badge state per connection-state enum, `onDisconnect`/`onStartup`/`onInstalled` reconnect, `chrome.alarms` backoff, fresh handshake + discarded stale nonce on every reconnect; vitest with mocked `chrome.runtime`
  - Ref: executor facts (MV3 service-worker lifecycle)
- [x] 🟩 Step 8: Desktop window (minimal) — done 2026-07-24; logic split into GUI-free `status.py`; offscreen smoke test passes; self-test PASS on dev machine
  - `app.py`: PySide6 window with host-registration status (reads registry + manifest existence, informational only) and a "run self-test" button executing Flow 2; no host↔UI live-state plumbing (excluded)
  - Done when: self-test passes end-to-end on the dev machine
- [x] 🟩 Step 9: Secure storage foundation (pulled ahead of Step 8) — done 2026-07-24; keyring namespacing, AES-GCM tamper + post-destruction tests, real Credential Manager round-trip verified
  - `secure_storage.py`: minimal `SecureStorageProvider` keyed `(clinic_id, secret_name)` over keyring; AES-256-GCM session-key lifecycle with explicit destruction; unit tests incl. tamper detection and post-destruction decryption failure
  - Ref: Key Design Decision (ephemeral session keys)
- [x] 🟩 Step 10: No-network-sockets integration test — done 2026-07-24; hello→ping via real launcher, stdout-purity assertion, full net_connections() empty on host tree AND scribe-app, polled mid-session
  - Spawn the real host through the real launcher over real pipes; complete the full handshake; assert first stdout bytes are a valid length prefix; poll `net_connections()` on the host AND a launched `scribe-app` throughout — both must stay empty
  - Ref: Critical Constraints (no listening sockets)
- [x] 🟩 Step 11: Security documents — done 2026-07-24; five docs written grounded in the built system (threat model covers stdio boundary, same-user residual risks, tripwires, LOW-009 zeroization residual, Phase-2 topology; data-flow map + retention enumerate log files/rotation); AGENTS.md pointers added
  - Write the five `docs/security/` docs grounded in the built system. Threat model MUST cover: the stdio trust boundary (nonce = session identifier, not auth), same-user residual risks (HKCU/manifest/launcher/venv hijack) with the startup path-logging tripwire, and the Phase-2 named-pipe topology. Data-flow map + retention schedule MUST enumerate log files (rotation/retention) — there is no status file. Add `AGENTS.md` Subsystem Documentation pointers
- [ ] 🟥 Step 12: Completion gate
  - Run every manual item in Validation / Verification; update `AGENTS.md` (stack rows, Local Run Steps incl. per-user registration + venv-move rule, Current Status) and `CHANGELOG.md`; record results in the handoff note
  - Done when: all automated suites green and every manual gate item observed

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
- Next follow-up: Phase 2 (local recording + transcription) via its own `/create-plan` — its first task is the named-pipe host↔app IPC per the locked topology
- Remain out of scope: everything under Deferred / Excluded above
- Design decisions that persist: all Key Design Decisions — especially the process topology, fixtures-canonical protocol, structural logging, and the no-network-sockets rule
- Do not rediscover: everything in "Codebase Integration Notes — executor facts"

---
*Plan saved to: .cursor/plans/plan-phase1-security-foundation.md*
*To resume in a new session: open a fresh Agent, run /start-session, then run /load-plan*
