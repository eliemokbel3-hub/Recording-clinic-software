# Feature Implementation Plan
**Feature:** phase2-recording-transcription
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: plan-phase1-security-foundation.md (foundation; Completed — Follow-ups Retained)
- Follow-up plans: None (Phases 3–7 of `PLAN.md` will become their own plans)

## Goal
Local recording and transcription (`PLAN.md` Phase 2): the desktop app records the microphone with immediate per-chunk encryption, survives crashes within a 24-hour recovery window, and transcribes locally (Whisper + VAD + speaker segmentation, timestamps, uncertainty marking) — with the hardware benchmark gating model choice and a verified absence of AI network traffic at runtime. Builds the named-pipe host↔app channel from the locked Phase-1 topology. No note generation, no Cliniko API, no Chrome-side commands yet.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5; executor may be Opus-class; tier-gap dosing applied (decisions locked, contracts specified, per-task acceptance criteria; carried over from the Phase-1 gate answer)

### Agreed Scope (Build Now)
- Named-pipe host↔app IPC (Phase-1 locked topology): pipe server in the long-lived app, client in the thin host; user-only DACL; reuses the Phase-1 framing + envelope over pipe handles; Python-only message set (both ends are Python — no TS mirror)
- Real core types from `PLAN.md`: `SessionState` (idle/recording/paused/processing/queued/written/failed/discarded/expired), `RecordingSession`; retire Phase 1's throwaway connection enum where superseded
- Audio capture: device enumeration + selection (sounddevice/WASAPI), chunked capture worker, level metering
- Encrypted session store: every audio chunk AES-256-GCM-encrypted at write time; session key DPAPI-protected at rest ONLY during the active/recovery window; key destroyed on finish-success or 24h expiry (cryptographic deletion preserved); startup + periodic expiry sweep
- Session state machine with start/pause/resume/finish/discard controls and crash recovery (resume or discard an interrupted session)
- ML stack: explicit one-time model-setup script (the ONLY sanctioned network use, separate process); silero-VAD segmentation; Whisper transcription behind the `SpeechProvider` interface with word timestamps + low-confidence marking (words, numbers, names); speaker labels per the segmentation decision task
- Hardware benchmark: real-time-factor measurement on the device, threshold report, warning on failure — never cloud fallback
- Desktop UI additions: microphone screen, session controls, recovery screen, benchmark/model screen (extends the Phase-1 status window)
- Runtime no-network proof extended: recorder app during capture AND transcription keeps zero sockets (model setup script exempt, runs separately)
- Completion gate (from `PLAN.md`): user-recorded synthetic osteopathic consultations transcribe locally with verified absence of AI network traffic

### Deferred — Actionable Later
- Clinical-content filtering and note generation
  - Why deferred: `PLAN.md` Phase 3 owns them
  - Recommended next action: Phase 3 plan
  - Risk if deferred: minor: intentional staging
- Chrome-side recording commands, consent flow, and page UI
  - Why deferred: `PLAN.md` Phase 5; the pipe built here is their transport when they arrive
  - Recommended next action: Phase 5 plan
  - Risk if deferred: minor: intentional staging
- Cliniko API, write-back, queueing (`PracticeManagementConnector`)
  - Why deferred: Phase 4
  - Risk if deferred: minor: intentional staging
- Full diarization quality tuning beyond the chosen segmentation approach
  - Why deferred: acceptance only requires speaker segmentation adequate for note drafting; tuning belongs with Phase 3's quality validation set
  - Risk if deferred: ux-degradation: transcripts may occasionally mis-attribute speakers until tuned
  - Revisit by: Phase 3 validation set construction

### Excluded — Revisit Only If Needed
- GPU-specific acceleration work (CUDA/DirectML tuning)
  - Why excluded: clinic machines are CPU-first until the benchmark says otherwise; the benchmark task records what the hardware offers
  - When to revisit: if the benchmark shows CPU RTF is unacceptable on a clinic machine
- Streaming/real-time transcription during recording
  - Why excluded: `PLAN.md` transcribes on Finish; streaming adds large complexity with no Phase-2 requirement
  - When to revisit: only if Finish-time latency proves clinically unacceptable in the pilot

### Accepted Assumptions — Revalidate Later
- Python 3.14 has usable wheels for the chosen ML stack (sounddevice, onnxruntime/silero, Whisper backend)
  - Why accepted for now: resolved empirically by the Step 6 spike; contingency recorded (Design Decisions)
  - Risk if assumption becomes false: desktop venv pins to 3.12 (declared floor) — contingency, not rework
  - Trigger for revisit: Step 6
- User-recorded synthetic consultations are a sufficient completion-gate corpus
  - Why accepted for now: the practitioner can record realistic two-speaker material; the formal 50-encounter validation set is Phase 7
  - Risk if assumption becomes false: gate repeats with better material
  - Trigger for revisit: Step 14 gate
- Same-user attacker remains outside the defended boundary (Phase-1 threat model carries over to the session store)
  - Trigger for revisit: Phase 7 packaging

### Key Design Decisions
- **Pipe transport reuses Phase-1 framing/envelope; message set is Python-only.** Both pipe ends are Python, so the fixtures-canonical TS/py mirroring is unnecessary; pipe messages live in `scribe_desktop.pipe_protocol` with their own fixture files under `protocol/pipe-fixtures/`. The Chrome↔host protocol is UNCHANGED in Phase 2.
  - Alternatives rejected: extending the shared TS/py fixtures (drags the extension into churn it cannot observe)
  - Still applies to follow-up work: Yes — Phase 5 adds Chrome-visible messages to the SHARED fixtures and relays them over this pipe
- **Pipe security:** named pipe `\\.\pipe\ClinikoScribe.host` created by the app with an explicit DACL granting only the current user SID; host connects as client; first message is a hello carrying the pipe protocol version. Not a network socket — the no-sockets constraint stands.
  - Alternatives rejected: localhost sockets (violates constraint); shared files (Phase-1 hardening already rejected polling files)
- **Crash-recovery key custody:** the per-session AES-GCM key is wrapped with DPAPI (CryptProtectData, current-user scope) and stored beside the session store while the session is active or recoverable; unwrapped only in memory; the wrapped blob is deleted on finish-success, discard, or 24h expiry — that deletion IS the cryptographic deletion of the audio.
  - Alternatives rejected: key only in memory (crash recovery impossible — violates PLAN.md); Credential Manager per-session entries (2560-byte blobs fine, but orphan cleanup is messier than a file beside the store)
  - Still applies to follow-up work: Yes — Phase 4's queued-draft encryption reuses this custody pattern
- **Audio store format:** append-only chunk file per session: fixed header (session id, created-at, format), then length-prefixed AES-GCM records (fresh 12-byte nonce each, chunk index as associated data so records cannot be reordered undetected). Plaintext audio exists only in capture buffers.
  - Alternatives rejected: encrypt-whole-file-at-finish (violates "encrypt immediately"); SQLite (no benefit for append-only streams)
- **Capture stack: `sounddevice` (PortAudio/WASAPI), 16 kHz mono PCM16, ~1 s chunks.** Whisper consumes 16 kHz mono; capturing at target rate avoids resampling complexity. Level metering from the same stream.
  - Alternatives rejected: pyaudio (unmaintained); WinRT APIs (heavy interop for no Phase-2 gain)
- **Model acquisition is an explicit setup step (`scripts/setup-models.py`), never runtime.** Runtime processes must stay socketless (Phase-1 Critical Constraint extended to the recorder under load); the setup script is the single sanctioned network user, run separately and documented in the data-flow map.
  - Alternatives rejected: lazy download on first transcription (breaks the no-sockets proof and can silently stall a clinical workflow)
- **Whisper backend + model size are `[decision]` tasks, decided on benchmark evidence** (Step 7). Preferred: faster-whisper (CTranslate2); fallbacks: whisper.cpp bindings, or pinning the venv to Python 3.12 if 3.14 wheels are the blocker. Uncertainty marking uses the backend's word-level probabilities.
- **Speaker segmentation is a `[decision]` task** (Step 9). Candidates: lightweight 2-speaker clustering over VAD segments (practitioner+patient is the dominant case) vs pyannote-class diarization (quality, but heavy + gated models vs the local-only posture). PLAN.md requires segmentation, not named identification.
- **UI extends the existing PySide6 status window** into a small multi-screen app (mic / session / recovery / benchmark); no new UI framework.

## Key Findings

### Files / Symbols Involved
Existing (Phase 1 — reuse, do not rewrite): `desktop/src/scribe_desktop/{framing,protocol,identity,logging_setup,secure_storage,native_host,status,app}.py`; `protocol/fixtures/`; QA config in `desktop/pyproject.toml`.
New (planned): `scribe_desktop/pipe_protocol.py`, `pipe_transport.py` (server+client), `session.py` (SessionState machine + RecordingSession), `audio_capture.py`, `session_store.py` (encrypted chunk store + DPAPI key custody + expiry sweep), `speech.py` (`SpeechProvider` + VAD + segmentation), `benchmark.py`, UI screens under `scribe_desktop/ui/`; `scripts/setup-models.py`; `protocol/pipe-fixtures/`; tests mirroring each.

### Codebase Integration Notes — executor facts (do not rediscover)
- Phase-1 executor facts still bind (see plan-phase1-security-foundation.md): stdout purity in the host, binary stdio, registration rules (exe, space-free, fresh Chrome process), logging whitelist + tripwire (extend `ALLOWED_KEYS` deliberately, never ad hoc), no-sockets ruff bans (`socket`, `http`, `urllib.request`, `PySide6.QtNetwork`)
- **Named pipes are NOT sockets:** `pywin32`'s `win32pipe`/`win32file` or `multiprocessing.connection` — but `multiprocessing.connection.Listener` does not expose DACLs; use pywin32 (`CreateNamedPipe` with an explicit `SECURITY_ATTRIBUTES`) — add `pywin32` to dependencies
- The framing module reads/writes `BinaryIO`; pipe handles need a thin file-like adapter (pywin32 returns handles, not streams)
- The logging tripwire drops any record containing `payload=`/`session_nonce=`/`request_id=` — pipe code must log through `log_event` like everything else; transcripts/audio must NEVER pass through logging (extend `_PAYLOAD_SIGNATURES` with transcript markers when the transcript type lands)
- `SessionCrypto` (secure_storage.py) is per-session-in-memory; Phase 2's DPAPI custody wraps ITS key — extend, don't fork, the class
- DPAPI via `win32crypt.CryptProtectData` (pywin32) — current-user scope, no extra entropy needed for this threat model (documented residual: same-user attacker)
- The no-sockets integration test (`test_integration_no_sockets.py`) is the pattern to extend: poll full `net_connections()` on the recorder during capture AND transcription
- Model caches live under `%LOCALAPPDATA%\ClinikoScribe\models\` (space-free, already-excluded tree); record sizes in the retention schedule
- CI (`.github/workflows/ci.yml`) runs desktop QA on 3.12 + 3.14 — ML deps must install on CI or be guarded behind an extra (`[ml]`) with skip-if-absent tests; audio-device tests need a null/mock backend on CI (no sound hardware)

### External / API Findings
- N/A — no external APIs in Phase 2 (the model-setup script's downloads are the only network activity, isolated by design)

## Planned Workflow Summary

### Flow 1 — Record a session
- App running → mic screen shows devices → Start → `RecordingSession` created (state=recording), session key generated + DPAPI-wrapped beside the store → capture worker streams 1 s chunks → each chunk AES-GCM-encrypted and appended → Pause/Resume flip state; Finish → state=processing → transcription flow; Discard → key + store deleted (state=discarded)

### Flow 2 — Transcribe on finish
- Decrypt chunks streamwise → VAD segments → Whisper per segment (word timestamps + probabilities) → uncertainty marks on low-confidence words/numbers/names → speaker labels per segmentation decision → encrypted transcript artifact written under the SAME session key → state=queued (write-back is Phase 4; Phase 2 displays the transcript for inspection) → on explicit completion: key custody deleted (cryptographic deletion)

### Flow 3 — Crash recovery
- App start → sweep session stores: expired (>24 h) → destroy key custody + store (state=expired); recoverable → recovery screen lists them → user chooses Resume-processing or Discard — never auto-resume recording

### Flow 4 — Host↔app pipe
- App creates the user-ACL'd pipe at startup → host (spawned by Chrome) connects when present → pipe hello/version → host may query `session_status` → host badge-relevant state becomes available to Phase 5 (Chrome sees nothing new in Phase 2)

## Design Decisions
(Consolidated in Key Design Decisions above.)

## Schema / Data Changes
- New on-disk artifacts (all under `%LOCALAPPDATA%\ClinikoScribe\`): `sessions/<id>/audio.enc` (chunk store), `sessions/<id>/key.dpapi` (wrapped session key), `sessions/<id>/transcript.enc`, `models/` cache — all enumerated in the retention schedule update (Step 13)

## Config / Environment / Deployment Impact
- New runtime dependencies: `pywin32`, `sounddevice`, VAD/Whisper stack per Step 6/7 (grouped under a `[ml]` extra so CI without audio/ML can still run core QA)
- New setup step for a fresh machine: run `scripts/setup-models.py` once (network use, documented)
- No env vars, no hosting impact; CI needs mock-audio + ml-extra guards (executor facts)

## Critical Constraints
- All Phase-1 Critical Constraints remain in force (no listening sockets, stdout purity, no custom crypto, whitelisted logging, extension permission scope)
- Plaintext audio exists ONLY in transient capture/processing memory — never on disk, never in logs; transcripts at rest are encrypted under the session key
- Deleting the DPAPI-wrapped key blob is the cryptographic deletion of the session — nothing else may retain the key or plaintext
- 24-hour recovery cap is enforced by code (sweep), not convention
- Runtime processes perform ZERO network I/O — model acquisition only via the explicit setup script; the no-sockets test covers the recorder mid-capture and mid-transcription
- Never auto-resume RECORDING after a crash; recovery is user-initiated and limited to processing or discard
- The Chrome↔host wire protocol does not change in Phase 2

## Validation / Verification
- Unit: pipe protocol fixtures (valid+invalid); pipe transport round-trip + DACL check (second-user access denied is not CI-testable — assert the DACL contents instead); session state machine (every legal/illegal transition); chunk store (append, tamper via AAD reorder, truncated tail from crash-sim, decrypt-stream); DPAPI custody (wrap/unwrap, delete = undecryptable); expiry sweep (fresh kept, >24 h destroyed); capture worker with mock backend; uncertainty marking thresholds; benchmark math
- Integration: record→finish→transcribe on a bundled short PCM fixture (synthetic tone+speech clip, no network); crash-sim (kill mid-recording, restart, recover, transcribe); no-sockets poll on the recorder during capture AND transcription
- Manual completion gate: on the dev machine — record real synthetic consultations (practitioner+patient roleplay), verify transcripts (timestamps, uncertainty marks, speaker labels), observe recovery flow after a forced kill, and run the network monitor check (`netstat` + the automated poll) proving no AI-service traffic
- All existing Phase-1 suites stay green (regression bar)

## Deferred / Out of Scope
See `Planning Extraction Summary` (single source of truth).

## Current State / Handoff Note
- Last completed step: Planning complete (2026-07-26); session handed off same day — no execution started, all 15 tasks 🟥
- Current in-progress step: None
- Immediate next action: `/review-plan` hardening pass recommended (non-trivial: crypto custody, concurrency, ML stack), then `/execute` or `/execute-loop`. Also verify the FIRST CI run passed (GitHub Actions tab — pushed 2026-07-26, never observed; likely-if-red culprits: keyring/audio quirks on the runner, not the code)
- Open blockers / open questions: None for planning. Fresh-session reading order: this plan top-to-bottom, then plan-phase1-security-foundation.md "Codebase Integration Notes — executor facts" (binding Chrome/logging/registration rules), then docs/security/threat-model.md
- Last plan sync: 2026-07-26

## Review History
- (no reviews yet)

## Review Findings Log
- (no findings logged yet)

## Tasks

- [ ] 🟥 Step 1: Pipe protocol + core types
  - `pipe_protocol.py`: pipe envelope (reusing framing), message set (`pipe_hello`, `pipe_hello_ack`, `session_status` request/response, `error`), real `SessionState` enum + `RecordingSession` model; fixtures under `protocol/pipe-fixtures/` (valid+invalid), fixture-driven tests
  - Ref: Key Design Decision (Python-only pipe protocol)
- [ ] 🟥 Step 2: Named-pipe transport
  - `pipe_transport.py`: pywin32 server (app side, explicit current-user-only DACL, file-like handle adapter for framing) + client (host side, connect-if-present, non-blocking); add `pywin32` dep; round-trip + DACL-content tests
  - Ref: executor facts (pywin32, framing adapter)
- [ ] 🟥 Step 3: Host session_status passthrough
  - `native_host.py`: on `session_status`-relevant state, host queries the app over the pipe when connected and degrades gracefully when not (app-absent is NOT an error); unit tests with a fake pipe. Chrome wire protocol untouched
- [ ] 🟥 Step 4: Encrypted session store + key custody
  - `session_store.py`: chunk store per Design Decision (AAD chunk index, crash-tolerant truncated tail), DPAPI wrap/unwrap via `win32crypt` extending `SessionCrypto`, delete-custody = cryptographic deletion, 24 h expiry sweep; the full unit batteries from Validation
  - Ref: Key Design Decisions (store format, key custody)
- [ ] 🟥 Step 5: Audio capture
  - `audio_capture.py`: sounddevice enumeration, 16 kHz mono PCM16 capture worker with ~1 s chunks feeding the store, level metering, mock backend for CI; device-loss mid-session → session state=failed (recoverable), never silent data loss
- [ ] 🟥 Step 6: Session state machine + controls
  - `session.py`: `SessionState` transitions with start/pause/resume/finish/discard, wiring capture↔store↔custody; exhaustive transition tests (legal and illegal)
- [ ] 🟥 Step 7: ML stack spike + model setup script
  - `scripts/setup-models.py` (explicit downloads to `%LOCALAPPDATA%\ClinikoScribe\models\`); install-and-run spike of faster-whisper (and fallback candidates) on Python 3.14; produce the RTF benchmark harness in `benchmark.py`; record wheel availability findings in this plan
  - Ref: Accepted Assumption (3.14 wheels), Key Design Decision (setup-step-only network)
- [ ] 🟥 Step D8: Choose Whisper backend + model size          [decision]
  - Options: faster-whisper on 3.14 / faster-whisper on a 3.12-pinned venv / whisper.cpp bindings; model: distil vs small/medium/large per RTF+quality
  - Decide after: Step 7's benchmark numbers on the dev machine
  - Blocks: Steps 9–11 (pipeline + benchmark thresholds)
- [ ] 🟥 Step 9: VAD + segmentation scaffolding
  - `speech.py`: silero-VAD over decrypted chunk stream → speech segments with timestamps; `SpeechProvider` interface per PLAN.md core types
- [ ] 🟥 Step D10: Choose speaker-segmentation approach        [decision]
  - Options: 2-speaker clustering over VAD segments / pyannote-class diarization / defer speaker labels to Phase 3 with `Risk if deferred: ux-degradation`
  - Decide after: Step 9 segments + Step D8 backend are in place (clustering quality is testable then)
  - Blocks: Step 11's speaker labels
- [ ] 🟥 Step 11: Transcription pipeline
  - `speech.py`: segments → Whisper (word timestamps + probabilities) → uncertainty marks (low-confidence words, numbers, names) → speaker labels per D10 → encrypted `transcript.enc` under the session key; state processing→queued; integration test on the bundled PCM fixture
- [ ] 🟥 Step 12: Benchmark + UI screens
  - `benchmark.py` thresholds + report per D8; PySide6 screens: microphone (device pick + level), session controls, recovery list (Flow 3, resume-processing/discard only), benchmark/model screen with the failed-device warning + report; offscreen smoke tests
- [ ] 🟥 Step 13: Docs + retention sync
  - Update `docs/security/` (data-flow map: sessions/models artifacts + the setup-script network exception; retention schedule: session stores, transcripts, model cache, 24 h rule; threat model: DPAPI custody residual) and `AGENTS.md` (setup-models step, new deps)
- [ ] 🟥 Step 14: No-network proof + completion gate
  - Extend the integration suite: recorder polled socketless during capture AND transcription; crash-sim end-to-end; then the manual gate (user records synthetic consultations; transcript inspection; forced-kill recovery; network monitor check) — results recorded in the handoff note
- [ ] 🟥 Step H: Hardening stage
  - [ ] 🟥 H1: `/review` → `/fix` to convergence
  - [ ] 🟥 H2: `/simplify` — findings logged; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — same routing (crypto custody + pipe DACL deserve it)
  - [ ] 🟥 H4: final `/review` re-check

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
- Next follow-up: Phase 3 (local note generation) — consumes the encrypted transcript artifact
- Design decisions that persist: pipe transport + custody pattern (Phase 4 queueing reuses it), setup-script-only network rule, no-sockets-at-runtime bar
- Do not rediscover: Phase-1 executor facts (referenced above) + this plan's executor facts

---
*Plan saved to: .cursor/plans/plan-phase2-recording-transcription.md*
*To resume in a new session: open a fresh Agent, run /start-session, then run /load-plan*
