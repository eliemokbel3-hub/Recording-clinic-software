# Feature Implementation Plan
**Feature:** phase2-recording-transcription
**Overall Progress:** `15%`

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
Local recording and transcription (`PLAN.md` Phase 2): the desktop app records the microphone with immediate per-chunk encryption, survives crashes within a 24-hour recovery window, and transcribes locally (Whisper + VAD + speaker segmentation, timestamps, uncertainty marking) — with the hardware benchmark gating model choice and a verified absence of AI network traffic at runtime. No note generation, no Cliniko API, no Chrome-side commands, and no host↔app pipe yet (pipe deferred to Phase 5, its real consumer — hardening decision 2026-07-26).

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5; executor may be Opus-class; tier-gap dosing applied (decisions locked, contracts specified, per-task acceptance criteria; carried over from the Phase-1 gate answer)

### Agreed Scope (Build Now)
- Real core types from `PLAN.md`: `SessionState` (idle/recording/paused/processing/queued/written/failed/discarded/expired), `RecordingSession`; retire Phase 1's throwaway connection enum where superseded
- Audio capture: device enumeration + selection (sounddevice/WASAPI), chunked capture worker, level metering
- Encrypted session store: every audio chunk AES-256-GCM-encrypted at write time; session key DPAPI-protected at rest ONLY during the active/recovery window; key destroyed on finish-success or 24h expiry (cryptographic deletion preserved); startup + periodic expiry sweep
- Session state machine with start/pause/resume/finish/discard controls and crash recovery (resume or discard an interrupted session)
- ML stack: explicit one-time model-setup script (the ONLY sanctioned network use, separate process); silero-VAD segmentation; Whisper transcription behind the `SpeechProvider` interface with word timestamps + low-confidence marking (words, numbers, names); speaker labels per the segmentation decision task
- Hardware benchmark: real-time-factor measurement on the device, threshold report, warning on failure — never cloud fallback
- Desktop UI additions: microphone screen, session controls, recovery screen, transcript-inspection view, benchmark/model report panel (extends the Phase-1 status window; benchmark folded into a panel, not its own screen)
- Runtime no-network proof extended: recorder app during capture AND transcription keeps zero sockets (model setup script exempt, runs separately) PLUS enforced offline mode for ML libraries (env kill-switches + local-only model loading + network-stubbed test) — polling alone cannot catch short-lived telemetry calls
- Tooling/CI enablement: mypy strict overrides for untyped native/ML deps; `.github/workflows/ci.yml` updated for the `[ml]` extra (skip-if-absent), mock audio, Windows-only test marks
- Logging safety: `ALLOWED_KEYS` extended deliberately for new session events; `_PAYLOAD_SIGNATURES` extended with transcript markers; tripwire tests for both
- Explicit Phase-2 "Complete" user action (distinct from Discard) that triggers cryptographic deletion — write-back does not exist until Phase 4
- Completion gate (from `PLAN.md`): user-recorded synthetic osteopathic consultations transcribe locally with verified absence of AI network traffic

### Deferred — Actionable Later
- Named-pipe host↔app IPC (server in app, client in host, user-only DACL, Phase-1 framing over pipe handles, Python-only message set)
  - Why deferred: nothing in the Phase-2 completion gate consumes it; Chrome sees nothing new until Phase 5, whose consent/command flow is the real consumer and will shape the message set (hardening decision 2026-07-26)
  - Recommended next action: Phase 5 plan builds it, including the hardening this pass identified — `FILE_FLAG_FIRST_PIPE_INSTANCE`, `nMaxInstances=1`, host verifies server via `GetNamedPipeServerProcessId` + image-path check, bounded `WaitNamedPipe` connect contract where "pipe exists but server unverified" is a hard error (not graceful-absent)
  - Risk if deferred: minor: the Phase-1 locked topology (pipe, not sockets/files) still stands as a design note; `pywin32` arrives in Phase 2 anyway for DPAPI
  - Revisit by: Phase 5 planning
- Clinical-content filtering and note generation
  - Why deferred: `PLAN.md` Phase 3 owns them
  - Recommended next action: Phase 3 plan
  - Risk if deferred: minor: intentional staging
- Chrome-side recording commands, consent flow, and page UI
  - Why deferred: `PLAN.md` Phase 5; Phase 5 also builds the host↔app pipe (deferred above) as their transport
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
  - Why accepted for now: resolved empirically by the Step 5 spike; contingency recorded (Design Decisions)
  - Risk if assumption becomes false: desktop venv pins to 3.12 (declared floor) — contingency, not rework
  - Trigger for revisit: Step 5
- User-recorded synthetic consultations are a sufficient completion-gate corpus
  - Why accepted for now: the practitioner can record realistic two-speaker material; the formal 50-encounter validation set is Phase 7
  - Risk if assumption becomes false: gate repeats with better material
  - Trigger for revisit: Step 13 gate
- Same-user attacker remains outside the defended boundary (Phase-1 threat model carries over to the session store)
  - Trigger for revisit: Phase 7 packaging

### Key Design Decisions
- **Named-pipe transport DEFERRED to Phase 5** (see Deferred — Actionable Later). The Phase-1 locked topology (named pipe, never sockets or polled files) remains binding when it is built. The Chrome↔host protocol is UNCHANGED in Phase 2.
- **Crash-recovery key custody:** the per-session AES-GCM key is wrapped with DPAPI (CryptProtectData, current-user scope) and stored beside the session store while the session is active or recoverable; unwrapped only in memory; the wrapped blob is deleted on Complete, discard, or 24h expiry — that deletion is the cryptographic deletion of the audio *at the same-user trust boundary*.
  - Durability ordering (binding): `key.dpapi` is written atomically (temp file + fsync + `os.replace`) BEFORE the first chunk is appended; on Complete — fsync `transcript.enc`, verify a decrypt round-trip, THEN delete the key; on Discard — delete the key FIRST, then best-effort remove the rest; the sweep garbage-collects orphan session dirs with no key
  - Accepted residual (user decision 2026-07-26): plain unlink on NTFS is not anti-forensic (free clusters/USN/VSS can retain the wrapped blob); deletion security holds at the same-user boundary the threat model already accepts — Step 12 documents this residual explicitly; no overwrite code
  - Alternatives rejected: key only in memory (crash recovery impossible — violates PLAN.md); Credential Manager per-session entries (orphan cleanup messier); best-effort overwrite-before-delete (weak on NTFS/SSD anyway)
  - Still applies to follow-up work: Yes — Phase 4's queued-draft encryption reuses this custody pattern
- **Audio store format (reconciled scheme, user decision 2026-07-26):** append-only chunk file per session: fixed header (session id, created-at, format), then length-prefixed AES-GCM records — fresh RANDOM 12-byte nonce each (never counter-derived; a crash-restored counter risks catastrophic nonce reuse), chunk index as AAD (cheap reorder detection), bounded record length on read (reject-without-allocation, mirroring `framing.py`), record-count bound asserted (GCM safety margin; fail safe, never silently exceed), truncated tail tolerated as expected crash behaviour, and a sealed FOOTER record written at Finish (final count) so post-Finish truncation is detectable. Plaintext audio exists only in capture buffers. One reorder-tamper test suffices — no dedicated battery.
  - Alternatives rejected: encrypt-whole-file-at-finish (violates "encrypt immediately"); SQLite (no benefit); plain records without AAD/footer (blind to tampering for one parameter of cost); full reorder-tamper battery (exceeds threat model)
- **Concurrency model (binding):** the capture worker is the SINGLE writer to `audio.enc` (owns the file handle); `SessionState` transitions are serialized through one lock (UI via Qt signals/queued connections); the expiry sweep skips any session in `recording`/`paused`/`processing` (keyed off live state, not mtime); `SessionCrypto` access is guarded. Pause/finish/discard vs an in-flight chunk write: the chunk is either fully written or cleanly dropped — tested.
- **Runtime offline enforcement (binding):** ML model loading uses explicit local paths with `local_files_only=True`; `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` (and onnxruntime telemetry off) are set AND asserted at runtime; an integration test runs transcription with network stubbed to fail and expects success. The polling no-sockets test remains, but env enforcement is the primary proof (short-lived telemetry connections can dodge a poll).
- **Capture stack: `sounddevice` (PortAudio/WASAPI), 16 kHz mono PCM16, ~1 s chunks.** Whisper consumes 16 kHz mono; capturing at target rate avoids resampling complexity. Level metering from the same stream.
  - Alternatives rejected: pyaudio (unmaintained); WinRT APIs (heavy interop for no Phase-2 gain)
- **Model acquisition is an explicit setup step (`scripts/setup-models.py`), never runtime.** Runtime processes must stay socketless (Phase-1 Critical Constraint extended to the recorder under load); the setup script is the single sanctioned network user, run separately and documented in the data-flow map.
  - Alternatives rejected: lazy download on first transcription (breaks the no-sockets proof and can silently stall a clinical workflow)
- **Whisper backend + model size are `[decision]` tasks, decided on benchmark evidence** (Step D6). Preferred: faster-whisper (CTranslate2); fallbacks: whisper.cpp bindings, or pinning the venv to Python 3.12 if 3.14 wheels are the blocker. Uncertainty marking uses the backend's word-level probabilities.
- **Speaker segmentation is a `[decision]` task CONSTRAINED to choosing the approach** (Step D8): lightweight 2-speaker clustering over VAD segments (practitioner+patient is the dominant case) vs pyannote-class diarization (quality, but heavy + gated models vs the local-only posture). Dropping segmentation is NOT a legal option — PLAN.md Phase 2 requires it as a gate deliverable (user decision 2026-07-26). PLAN.md requires segmentation, not named identification.
- **Single-active-session invariant:** at most one session may be in `recording`/`paused`/`processing` at a time; multiple RECOVERABLE stores may coexist and are listed by the recovery screen.
- **Phase-2 "Complete" action:** since Phase 4's write-back does not exist yet, an explicit user action on the transcript-inspection view ("Complete" — distinct from Discard) triggers cryptographic deletion per the custody ordering. Until then a finished session sits `queued` with its key retained, bounded by the 24 h sweep.
- **UI extends the existing PySide6 status window** into a small multi-screen app (mic / session / recovery / transcript-inspection); the benchmark/model status is a report panel, not its own screen; no new UI framework.

## Key Findings

### Files / Symbols Involved
Existing (Phase 1 — reuse, do not rewrite): `desktop/src/scribe_desktop/{framing,protocol,identity,logging_setup,secure_storage,native_host,status,app}.py`; `protocol/fixtures/`; QA config in `desktop/pyproject.toml`.
New (planned): `scribe_desktop/session.py` (SessionState machine + RecordingSession), `audio_capture.py`, `session_store.py` (encrypted chunk store + DPAPI key custody + expiry sweep), `speech.py` (`SpeechProvider` + VAD + segmentation), `benchmark.py`, UI screens under `scribe_desktop/ui/`; repo-root `scripts/setup-models.py` (NOT `desktop/scripts/` — must sit outside desktop ruff/mypy so its network use is legal); `.github/workflows/ci.yml` edits; tests mirroring each. (Pipe modules removed — deferred to Phase 5.)

### Codebase Integration Notes — executor facts (do not rediscover)
- Phase-1 executor facts still bind (see plan-phase1-security-foundation.md): stdout purity in the host, binary stdio, registration rules (exe, space-free, fresh Chrome process), logging whitelist + tripwire (extend `ALLOWED_KEYS` deliberately, never ad hoc), no-sockets ruff bans (`socket`, `http`, `urllib.request`, `PySide6.QtNetwork`)
- **mypy is `strict = true` with NO overrides** (`desktop/pyproject.toml`): `import win32crypt`, `sounddevice`, `faster_whisper`, `onnxruntime` etc. each fail with "Cannot find implementation or library stub" — add a `[[tool.mypy.overrides]]` block (`ignore_missing_imports = true`) for the native/ML modules at first use (Step 1), or every later step is blocked
- `sounddevice` loads the PortAudio DLL at IMPORT time — import it lazily inside functions so `audio_capture.py` stays importable on CI (mock backend must not touch PortAudio at collection time)
- `SessionCrypto._key` is private with no accessor — DPAPI custody needs a key-export/wrap method (or `from_wrapped` constructor) added to the class (extend, don't fork); name it in Step 2, don't rediscover
- DPAPI and pipe APIs are Windows-only: guard pywin32 imports and mark those tests `pytest.mark.skipif(sys.platform != "win32")` (CI runners are Windows — keep it that way)
- The logging tripwire drops any record containing `payload=`/`session_nonce=`/`request_id=` — all new code logs through `log_event`; transcripts/audio must NEVER pass through logging (extend `_PAYLOAD_SIGNATURES` with transcript markers when the transcript type lands — a planned task, not an afterthought)
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
- Decrypt chunks streamwise → VAD segments → Whisper per segment (word timestamps + probabilities) → uncertainty marks on low-confidence words/numbers/names → speaker labels per segmentation decision → encrypted transcript artifact written ATOMICALLY (temp + replace) under the SAME session key → state=queued (write-back is Phase 4; Phase 2 displays the transcript on the inspection view) → on the explicit Complete action: fsync transcript → verify decrypt round-trip → delete key custody (cryptographic deletion). Crash mid-processing: recovery restarts transcription from audio (idempotent; partial transcript overwritten atomically); audio is never deleted before the transcript verifies.

### Flow 3 — Crash recovery
- App start → sweep session stores: expired (>24 h) → destroy key custody + store (state=expired); recoverable → recovery screen lists them → user chooses Resume-processing or Discard — never auto-resume recording

### Design Decisions
(Consolidated in Key Design Decisions above.)

## Schema / Data Changes
- New on-disk artifacts (all under `%LOCALAPPDATA%\ClinikoScribe\`): `sessions/<id>/audio.enc` (chunk store), `sessions/<id>/key.dpapi` (wrapped session key), `sessions/<id>/transcript.enc`, `models/` cache — all enumerated in the retention schedule update (Step 13)

## Config / Environment / Deployment Impact
- New runtime dependencies: `pywin32` (DPAPI), `sounddevice`, VAD/Whisper stack per Steps 5/D6 (ML/audio grouped under a `[ml]` extra so CI without audio/ML can still run core QA); mypy overrides block for all untyped native/ML modules
- New setup step for a fresh machine: run `scripts/setup-models.py` once (repo-root; the ONLY sanctioned network use, documented)
- Offline env kill-switches (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`) set by the app at startup and asserted in tests — enforced by env + integration test, NOT by ruff import bans (ML libs use `requests`/`httpx` transitively, which the ban list cannot see)
- CI (`.github/workflows/ci.yml`) updated in-plan (Step 11): `[ml]` extra with skip-if-import-fails guards (3.14 wheels are an open assumption), mock audio, Windows-only marks; verify the outstanding FIRST CI run is green before layering new deps

## Critical Constraints
- All Phase-1 Critical Constraints remain in force (no listening sockets, stdout purity, no custom crypto, whitelisted logging, extension permission scope)
- Plaintext audio exists ONLY in transient capture/processing memory — never on disk, never in logs; transcripts at rest are encrypted under the session key
- Deleting the DPAPI-wrapped key blob is the cryptographic deletion of the session (at the same-user boundary; NTFS forensic residual documented) — nothing else may retain the key or plaintext; deletion/durability ordering per the key-custody Design Decision is binding
- `key.dpapi` is durably written before the first audio chunk; disk-write failure (full/failing disk) transitions the session to `failed` (recoverable) — never silent data loss
- 24-hour recovery cap is enforced by code (sweep), not convention; the sweep never touches sessions in `recording`/`paused`/`processing`
- At most ONE active session at a time (single-active-session invariant)
- Runtime processes perform ZERO network I/O — model acquisition only via the explicit setup script; offline env kill-switches set AND asserted; the no-sockets test covers the recorder mid-capture and mid-transcription
- Never auto-resume RECORDING after a crash; recovery is user-initiated and limited to resume-processing or discard
- The Chrome↔host wire protocol does not change in Phase 2 (and no pipe exists until Phase 5)

## Validation / Verification
- Unit: session state machine (every legal/illegal transition, incl. Complete vs Discard); chunk store (append, one AAD-reorder tamper test, truncated tail from crash-sim, Finish footer detects post-Finish truncation, bounded record length on read, no nonce repeats across simulated restart-append, record-count bound, decrypt-stream); DPAPI custody (wrap/unwrap, delete = undecryptable, zero-length/truncated `key.dpapi` handled by the sweep); expiry sweep (fresh kept, >24 h destroyed, active sessions skipped, orphan dirs GC'd); disk-full → `failed` (recoverable); capture worker with mock backend (module importable without PortAudio); pause/finish vs in-flight chunk synchronization; logging tripwire on new keys + transcript signatures; uncertainty marking thresholds; benchmark math
- Integration: record→finish→transcribe on a bundled short PCM fixture (synthetic tone+speech clip, no network); crash-sim (kill mid-recording, restart, recover, transcribe; kill mid-processing, recovery restarts transcription); transcription succeeds with network stubbed to fail (offline enforcement proof); no-sockets poll on the recorder during capture AND transcription
- Manual completion gate: on the dev machine — record real synthetic consultations (practitioner+patient roleplay), verify transcripts (timestamps, uncertainty marks, speaker labels), observe recovery flow after a forced kill, and run the network monitor check (`netstat` + the automated poll) proving no AI-service traffic
- All existing Phase-1 suites stay green (regression bar)

## Deferred / Out of Scope
See `Planning Extraction Summary` (single source of truth).

## Current State / Handoff Note
- Last completed step: Step 2 complete (2026-07-26, P2 executor run stage-2): `session_store.py` created — chunk store (fixed 53-byte plaintext header `<4sB32sdIHH`; length-prefixed records `[u32 len][u8 type][12B random nonce + AESGCM ct]`; type 0x01=chunk AAD=`b"chunk:"+u64(index)`, 0x02=footer AAD=`b"footer"` payload=u64 final count; MAX_CHUNK_PLAINTEXT_BYTES=1 MiB, MAX_RECORDS=1_000_000 fail-safe; reject-oversized-declared-length without allocation; truncated tail tolerated; `open_for_append` truncates partial tail, verifies existing records, refuses footered stores); DPAPI custody (`wrap_key_to_file` temp+fsync+os.replace, `unwrap_key_from_file` → KeyCustodyError on missing/zero/truncated/garbage, `resolve_key_path` = the ONLY key_reference resolution per the Step-1 binding note); ordering primitives (`complete_session` fsync→verify-decrypt→delete-key; `discard_session` key-first then rmtree; `SessionChunkStore.create` REFUSES to create audio.enc unless key.dpapi exists — code-enforced key-before-first-chunk); `sweep_sessions` (24h RECOVERY_WINDOW, active ids skipped by state, orphan/zero-length/truncated-key dirs GC'd, foreign dir names untouched, logs via log_event session_id+detail_code only); `SessionCrypto` EXTENDED not forked (optional AAD on encrypt/decrypt, `export_key`, `from_key`); disk-full → StoreWriteError (recoverable→failed). QA: ruff clean, mypy clean, pytest 151 passed (103 + 48 new). Peer-loop for Step 2 closed at round 6 (2026-07-26, stage-2 continuation executor): PR-MED-005 peer-confirmed fixed; PR-MED-006 (exists()-suppressed OSError vs orphan GC) verified and Applied; final QA ruff clean, mypy clean, pytest 160 passed
- Prior step: Step 1 complete (2026-07-26, P1 executor run stage-1): `session.py` created (SessionState 9-state enum + frozen RecordingSession model + ACTIVE/RECOVERABLE/TERMINAL state groups); Phase-1 `ConnectionState` retired from `protocol.py` (zero Python usages; the extension's TS ConnectionState is its own badge type and stays); `ALLOWED_KEYS` extended deliberately with session_id/session_state/chunk_index/sample_rate/device_id + tripwire tests; `desktop/pyproject.toml` gained `pywin32>=306; sys_platform == "win32"` dep + `[[tool.mypy.overrides]]` (ignore_missing_imports) for win32crypt/win32api/win32con/win32pipe/win32file/win32security/pywintypes/sounddevice/faster_whisper/onnxruntime; pywin32 installed directly into the venv (deliberately NOT `pip install -e` — avoids invalidating the native-host registration; next full reinstall picks it up from pyproject). QA green: ruff clean, mypy clean, pytest 85 passed (72 existing + 13 new in tests/test_session_types.py)
- Current in-progress step: None — Step 1 fully closed: review-loop converged round 2 (1 LOW fixed); peer-loop converged round 3 (PR-MED-001/002/003 all MED, all applied + peer-verified). Final QA: ruff clean, mypy clean, pytest 103 passed. BINDING for Step 2: `key_reference` is the opaque literal `key.dpapi`; resolve strictly as `<sessions root>/<validated session_id>/key.dpapi`
- Immediate next action: composer commits P1; then P2 executor (Step 2). Step 11 verifies the FIRST CI run (pushed 2026-07-26, never observed; likely-if-red culprits: keyring/audio quirks on the runner, not the code)
- Open blockers / open questions: None. Fresh-session reading order: this plan top-to-bottom, then plan-phase1-security-foundation.md "Codebase Integration Notes — executor facts" (binding Chrome/logging/registration rules), then docs/security/threat-model.md
- Last plan sync: 2026-07-26
- Loop config: executor=cursor-subagent model="fable"; peer=codex model="gpt-5.6-sol" effort=xhigh; architect=off; cadence=every-phase; caps=review:3,peer:3; scope=all; autocommit=on; isolation=none; merge=off
- Run state: /execute-loop run cliniko-p2-20260726-170200-k7 preflight complete 2026-07-26 ~17:05; phase grouping: P1=Step 1, P2=Step 2 (security-isolated), P3=Steps 3–4, P4=Step 5+D6, P5=Steps 7+D8, P6=Step 9, P7=Step 10 (UI — live-smoke pause), P8=Steps 11–12, P9=Step 13 (manual gate), P10=Step H; next: spawn P1 executor

## Review History
- 2026-07-26 round 1: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none
- 2026-07-26 round 2: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none
- 2026-07-26 round 3: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=none
- 2026-07-26 round 4: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none

## Review Findings Log

### 2026-07-26 round 1 (Step 1 scope; Source: Claude Code, stage-1 P1 executor, headless)
- Status: Closed (0 pending)
- **[LOW-001]** `desktop/tests/test_session_types.py` — `test_log_event_accepts_new_session_keys` was vacuous: logger at NOTSET (effective WARNING) meant `logger.info` never reached the tripwire filter, so the drop-count assertion passed without exercising it — Triage: Fix-now (auto-disposable); Decision: Applied. Fix: `setLevel(INFO)` + NullHandler + logger-level filter (handler-level filter on NullHandler would be skipped — `NullHandler.handle` bypasses filters). Verified: full QA green (85 passed). Finding verification round 1: 3 candidates; 2 dropped (RECOVERABLE_STATES grouping matches plan Flow 3; `session_state`/`state` coexistence deliberate); 0 downgraded.

### 2026-07-26 peer round 1 (Step 1 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — block appended by executor; peer summary: 0 confirmed / 0 disputed / 2 new / 0 regression; 4 candidates / 2 dropped / 0 downgraded)
- Status: Closed (0 pending)
- **[PR-MED-001]** `logging_setup.py` — tripwire had no `encounter_context` signature: logging a populated `RecordingSession` repr would leak patient/booking identifiers past the last-line filter — Triage: Fix-now (auto-disposable); Decision: Applied 2026-07-26 by stage-1 executor. Fix: three `encounter_context` signatures (quoted/unquoted) added to `_PAYLOAD_SIGNATURES` + `test_tripwire_drops_recording_session_representations` (repr / model_dump / JSON forms). Verified by executor before applying (probe confirmed leak).
- **[PR-MED-002]** `session.py` — `session_id` accepted free-form/path-like values (`../../escape`), breaking the opaque-id assumption behind the log whitelist and the future `sessions/<id>/` path segment — Triage: Fix-now (auto-disposable); Decision: Applied 2026-07-26 by stage-1 executor. Fix: `pattern=r"^[0-9a-f]{32}$"` on the field + 8 parametrized rejection tests. Verified by executor before applying.
- Post-fix QA: ruff clean, mypy clean, pytest 94 passed (85 + 9 new).

### 2026-07-26 peer round 2 (Step 1 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — block appended by executor; peer summary: 2 applied fixes verified / 0 disputed / 1 new / 0 regression; 4 candidates / 3 dropped / 0 downgraded)
- Status: Closed (0 pending)
- Applied-fix verification: PR-MED-001 and PR-MED-002 both independently verified by the peer; ConnectionState retirement confirmed zero Python references, TS type intact.
- **[PR-MED-003]** `session.py` — `key_reference` accepted unrestricted filesystem paths (empty, traversal, absolute, patient-named), an unsafe deletion boundary once Step 2's Complete/Discard/sweep delete the referenced key — Triage: Fix-now (auto-disposable); Decision: Applied 2026-07-26 by stage-1 executor. Fix: field constrained to the literal opaque value `key.dpapi` (`pattern=r"^key\.dpapi$"`); Step 2 must resolve it strictly as `<sessions root>/<validated session_id>/key.dpapi` (binding note for Step 2). 8 rejection tests + 1 acceptance test added.
- Post-fix QA: ruff clean, mypy clean, pytest 103 passed (94 + 9 new).

### 2026-07-26 peer round 3 (Step 1 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only)
- Status: Closed — converged (zero findings)
- PR-MED-003 fix verified (traversal/absolute/whitespace/NUL/newline variants rejected); no downstream breakage; 3 candidates / 3 dropped / 0 downgraded. Peer-loop converged at round 3 of cap 3.

### 2026-07-26 round 3 (Step 2 scope; Source: Claude Code, stage-2 P2 executor, headless)
- Status: Closed (0 pending)
- **[LOW-001]** `session_store.py` `SessionChunkStore.create` — a failed header write (or `open("xb")` collision) escaped as raw OSError and could leave a headerless partial `audio.enc` behind, off the module's StoreWriteError-recoverable contract — Triage: Fix-now (auto-disposable); Decision: Applied 2026-07-26. Fix: map open/create OSError → StoreWriteError; unlink the partial file on header-write failure; `test_create_collision_maps_to_store_write_error` added. Finding verification round 3: 6 candidates; 5 dropped (full-record verify on resume is deliberate integrity policy; footer-mid-truncation / empty-chunk / wrong-key / private-attr-in-test all non-issues on re-read); 0 downgraded. Post-fix QA: ruff clean, mypy clean, pytest 152 passed.

### 2026-07-26 peer round 4 (Step 2 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — block appended by executor; peer summary: 1 confirmed (LOW-001 fix) / 0 disputed / 3 new / 0 regression; 7 candidates / 4 dropped / 0 downgraded by peer)
- Status: Closed (0 pending)
- **[PR-HIGH-001 → downgraded MED by executor]** `session_store.py` — `complete_session` deleted `key.dpapi` but left the caller's in-memory `SessionCrypto` able to decrypt retained artifacts — Triage: Fix-now; Decision: Applied 2026-07-26 by stage-2 executor. Downgrade rationale: the threat model already accepts in-memory key residual at the same-user boundary (LOW-009); marginal risk is API-contract reuse, not new at-rest exposure — at MED it is auto-disposable. Fix: `complete_session` calls `crypto.destroy()` after custody deletion; `discard_session` gains optional `crypto` param and destroys it too (None allowed for recovery-screen discards with no unwrapped key). Invariant now tested: after Complete/Discard no application-owned object can decrypt (destroyed flag + export_key raises). Verified by executor before applying.
- **[PR-MED-004]** `session_store.py` — NaN/inf/future header `created_at` defeated the 24h expiry cap (`current - NaN > x` false forever); boundary was exclusive — Triage: Fix-now (auto-disposable); Decision: Applied. Fix: `_session_created_at` now collects header created-at + key mtime, drops non-finite/future values, takes the EARLIEST trusted survivor, falls back dir-mtime→now (fail-safe: expires next window, never retained forever); expiry comparison now `>=`. Tests: NaN/inf/future parametrized + exact-boundary test. Verified by executor before applying.
- **[PR-LOW-001]** `session_store.py` — `open_for_append`'s two `open()` calls escaped as raw OSError instead of the StoreWriteError recoverable contract — Triage: Fix-now (auto-disposable); Decision: Applied. Fix: both opens mapped to StoreWriteError (create() pattern); missing-file test added. Verified by executor before applying.
- Filesystem-escape check: git status identical before/after peer (read-only peer, zero files touched). Post-fix QA: ruff clean, mypy clean, pytest 158 passed (152 + 6 new).

### 2026-07-26 peer round 5 (Step 2 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — block appended by executor; peer summary: 2 confirmed + 1 partly confirmed / 1 partially disputed / 1 new / 0 regression; 5 candidates / 4 dropped / 0 downgraded)
- Status: Closed (0 pending)
- Applied-fix verification: PR-HIGH-001(→MED), PR-LOW-001 confirmed; PR-MED-004 partly confirmed — its `now` fallback was validly disputed (see below).
- **[PR-MED-005]** `session_store.py` — all-future timestamps (header + key mtime + dir mtime, e.g. clock set ahead then corrected) made `_session_created_at` fall back to `now` on EVERY sweep → age zero forever → 24h cap defeated — Triage: Fix-now (auto-disposable); Decision: Applied 2026-07-26 by stage-2 executor. Fix: dir mtime folded into the candidate set; readable-but-untrusted (non-finite/future) candidate set now fails CLOSED (returns -inf → expires immediately; active sessions still protected by the active_session_ids exemption); nothing-readable (transient stat I/O errors) stays conservative (kept this sweep, retried next). Test: all-three-future timestamps → expired. Verified by executor before applying (peer's age-zero reproduction logic confirmed against the code).
- Filesystem-escape check: git status identical before/after peer. Post-fix QA: ruff clean, mypy clean, pytest 159 passed.

### 2026-07-26 peer round 6 (Step 2 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — block appended by stage-2 continuation executor; peer summary: 1 confirmed / 0 disputed / 1 new / 0 regression; 4 candidates / 3 dropped / 0 downgraded)
- Status: Closed (0 pending)
- Applied-fix verification: PR-MED-005 confirmed fixed by peer (`_session_created_at` candidate handling + all-future-timestamps regression test verified at session_store.py:526-556, 586-600; test_session_store.py:466-482). No disputed findings.
- **[PR-MED-006]** `session_store.py:592` — sweep used `not key_path.exists()` as confirmed-orphan custody, but on Python 3.14 `Path.exists()` suppresses OSError and returns False for inaccessible paths: a transiently inaccessible `key.dpapi` could enter the orphan-GC branch and prematurely cryptographically delete an inactive recoverable session (invariant: transient filesystem errors must never trigger cryptographic deletion) — Triage: Fix-now (auto-disposable); /fix decision: Applied 2026-07-26 by stage-2 continuation executor. Fix: single `key_path.stat()` — FileNotFoundError = confirmed orphan (GC as before); any other OSError propagates to the existing conservative `except OSError` handler → action="error", NO key/dir deletion (matches the `_session_created_at` stat-error pattern). Regression test `test_inaccessible_key_reports_error_and_deletes_nothing` (stat raises PermissionError → action=="error", key + dir remain); existing orphan/zero-length/truncated-key GC tests unchanged and passing. Verified by executor against the code before applying.
- Filesystem-escape check: git diff --check passed; peer edited nothing; ruff/mypy not independently rerun by peer (sandbox-blocked) — executor's result stands. Post-fix QA: ruff clean, mypy clean, pytest 160 passed (159 + 1 new).

### 2026-07-26 peer round 7 (Step 2 scope; Source: Codex peer-review, gpt-5.6-sol xhigh, read-only — user-authorized cap+1 confirmation round, composer-driven)
- Status: Closed (0 pending) — peer pass CONVERGED
- PR-MED-006 fix CONFIRMED: single `key_path.stat()` at session_store.py:598-614, only FileNotFoundError routes to orphan GC, other OSError reaches action="error" before any deletion branch; orphan/zero-length/truncated-key tests remain valid; new inaccessible-key test verifies error + preservation; no caller contract changed; invariant holds (transient custody-stat errors cannot trigger cryptographic deletion).
- Filesystem-escape check: peer read-only; working tree unchanged by the round.

## Tasks

- [x] 🟩 Step 1: Core types + tooling prep
  - `session.py`: real `SessionState` enum + `RecordingSession` model per PLAN.md core types (retire Phase 1's throwaway `ConnectionState` where superseded); `desktop/pyproject.toml`: `[[tool.mypy.overrides]]` (`ignore_missing_imports = true`) for `win32crypt`/`win32api`/`sounddevice`/ML modules + add `pywin32` dep; `logging_setup.py`: extend `ALLOWED_KEYS` with the new session event keys (deliberately, whitelisted) with tripwire tests
  - Verifies: types unit tests + tripwire tests; existing suites stay green
- [x] 🟩 Step 2: Encrypted session store + key custody — done 2026-07-26 (stage-2 executor); session_store.py (chunk store + DPAPI custody + ordering primitives + sweep), SessionCrypto extended (AAD + export_key/from_key); 48 new tests, QA 151 green
  - `session_store.py`: chunk store per the Audio store format Design Decision (random nonces, AAD index, bounded reads, record-count bound, truncated-tail tolerance, Finish footer); `secure_storage.py`: add a key-export/wrap method to `SessionCrypto` (extend, don't fork); DPAPI wrap/unwrap via `win32crypt` (Windows-only guards); atomic `key.dpapi` write BEFORE first chunk; deletion ordering per the key-custody Design Decision; 24 h expiry sweep (skips active, GCs orphans, handles truncated key blobs); disk-full → `failed`
  - Verifies: the full chunk-store/custody/sweep unit batteries from Validation
- [ ] 🟥 Step 3: Audio capture
  - `audio_capture.py`: lazy `sounddevice` import (module importable without PortAudio), device enumeration, 16 kHz mono PCM16 capture worker with ~1 s chunks feeding the store, level metering, mock backend for CI; device-loss mid-session → session state=failed (recoverable), never silent data loss
- [ ] 🟥 Step 4: Session state machine + controls + concurrency
  - `session.py`: transitions with start/pause/resume/finish/discard/Complete, wiring capture↔store↔custody under the Concurrency model Design Decision (single writer, serialized transitions, guarded `SessionCrypto`); single-active-session invariant enforced
  - Verifies: exhaustive legal/illegal transition tests + pause/finish-vs-in-flight-chunk test
- [ ] 🟥 Step 5: ML stack spike + model setup script
  - Repo-root `scripts/setup-models.py` (explicit downloads to `%LOCALAPPDATA%\ClinikoScribe\models\`); install-and-run spike of faster-whisper (and fallback candidates) on Python 3.14; RTF benchmark harness in `benchmark.py`; app sets + asserts the offline env kill-switches; record wheel availability findings in this plan
  - Ref: Accepted Assumption (3.14 wheels), Design Decisions (setup-step-only network, Runtime offline enforcement)
- [ ] 🟥 Step D6: Choose Whisper backend + model size          [decision]
  - Options: faster-whisper on 3.14 / faster-whisper on a 3.12-pinned venv / whisper.cpp bindings; model: distil vs small/medium/large per RTF+quality
  - Decide after: Step 5's benchmark numbers on the dev machine
  - Blocks: Steps 7–9 (pipeline + benchmark thresholds)
- [ ] 🟥 Step 7: VAD + segmentation scaffolding
  - `speech.py`: silero-VAD over decrypted chunk stream → speech segments with timestamps; `SpeechProvider` interface per PLAN.md core types
- [ ] 🟥 Step D8: Choose speaker-segmentation approach         [decision]
  - Options: 2-speaker clustering over VAD segments / pyannote-class diarization (approach choice ONLY — segmentation itself is a PLAN.md gate requirement and cannot be dropped)
  - Decide after: Step 7 segments + Step D6 backend are in place (clustering quality is testable then)
  - Blocks: Step 9's speaker labels
- [ ] 🟥 Step 9: Transcription pipeline
  - `speech.py`: segments → Whisper (word timestamps + probabilities, `local_files_only=True`, explicit local model paths) → uncertainty marks (low-confidence words, numbers, names) → speaker labels per D8 → `transcript.enc` written atomically under the session key; state processing→queued; Complete action: fsync→verify→delete-key per Flow 2; crash-mid-processing recovery restarts transcription; `_PAYLOAD_SIGNATURES` extended with transcript markers + tripwire test
  - Verifies: integration test on the bundled PCM fixture + network-stubbed-to-fail offline test
- [ ] 🟥 Step 10: Benchmark report + UI screens
  - `benchmark.py` thresholds + report per D6; PySide6 screens: microphone (device pick + level + benchmark/model report panel with failed-threshold warning), session controls, recovery list (Flow 3, resume-processing/discard only), transcript-inspection view with the Complete/Discard actions; offscreen smoke tests
- [ ] 🟥 Step 11: CI workflow update
  - `.github/workflows/ci.yml`: verify the outstanding first run is green, then add `[ml]` extra with skip-if-import-fails guards (3.14 leg may lack wheels — that's a skip, not a failure), mock-audio env, Windows-only marks honoured
- [ ] 🟥 Step 12: Docs + retention sync
  - Update `docs/security/` (data-flow map: sessions/models artifacts + the setup-script network exception + offline-enforcement note; retention schedule: session stores, transcripts, model cache, 24 h rule; threat model: DPAPI custody residual + NTFS unlink-not-anti-forensic residual + pipe-deferred note) and `AGENTS.md` (setup-models step, new deps)
- [ ] 🟥 Step 13: No-network proof + completion gate
  - Extend the integration suite: recorder polled socketless during capture AND transcription + offline env asserts; crash-sim end-to-end; then the manual gate (user records synthetic consultations; transcript inspection; forced-kill recovery; network monitor check) — results recorded in the handoff note
- [ ] 🟥 Step H: Hardening stage
  - [ ] 🟥 H1: `/review` → `/fix` to convergence
  - [ ] 🟥 H2: `/simplify` — findings logged; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — same routing (crypto custody + store format deserve it)
  - [ ] 🟥 H4: final `/review` re-check

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
- Next follow-up: Phase 3 (local note generation) — consumes the encrypted transcript artifact
- Design decisions that persist: key-custody pattern (Phase 4 queueing reuses it), pipe topology + hardening notes (Phase 5 builds it — see Deferred), setup-script-only network rule, offline env enforcement, no-sockets-at-runtime bar
- Do not rediscover: Phase-1 executor facts (referenced above) + this plan's executor facts

---
*Plan saved to: .cursor/plans/plan-phase2-recording-transcription.md*
*To resume in a new session: open a fresh Agent, run /start-session, then run /load-plan*
