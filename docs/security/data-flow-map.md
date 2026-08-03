# Data-Flow Map (Phases 1–2)

Every place data lives or moves in the implemented system. Since Phase 2 the
desktop app carries **clinical data**: consultation audio and transcripts,
encrypted at rest under per-session keys and bounded by a 24-hour recovery
window. There is **no status file** (that design was cut in plan hardening)
and **no network sockets** on either desktop process at runtime (enforced by
`desktop/tests/test_integration_no_sockets.py`, ruff import bans, and the
offline env kill-switches in flow 7) — the ONLY sanctioned network user is
the explicit model-setup script (flow 9).

## Components

| Component | Process | Trust context |
|---|---|---|
| Chrome extension (`extension/`) | Chrome renderer/service worker | Sandboxed by Chrome; ID pinned `mbmhglgadhdohpgbmpbjnaifjagfdfid` |
| Native host (`scribe-host`) | Spawned by Chrome per connection | Runs as the logged-in Windows user |
| Recorder app (`scribe-app`) | Standalone PySide6 process (multi-screen: microphone / session / recovery / transcript / status); single instance per user enforced by a named mutex | Runs as the logged-in Windows user |
| Model setup script (`scripts/setup-models.py`) | Separate explicit process, run once per machine BY THE USER from a normal terminal | Runs as the logged-in Windows user; setup-time only, never at runtime |

## Flows

1. **Chrome ↔ native host (stdio, the ONLY browser transport).**
   Chrome spawns the registered launcher and connects stdin/stdout pipes.
   Framed JSON (4-byte native-order length prefix + UTF-8, ≤1 MB per frame,
   project policy both directions). Phase-1 messages: `hello`, `hello_ack`,
   `ping`, `pong`, `error`. Contains: protocol version, request IDs, a random
   per-session nonce. Contains NO secrets, NO clinical data.

2. **Host/app → log files.** `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-host.log`
   and `scribe-app.log`, rotating at 1 MB with 3 backups. Content is
   structurally restricted to whitelisted metadata (event names, message
   types, versions, byte sizes, states, error codes, filesystem paths, PIDs)
   via `logging_setup.py`'s wrapper + tripwire filter. Protocol payloads and
   nonces are actively dropped if ever formatted into a record. Stdout is
   NEVER a log destination (it carries only protocol frames).

3. **Desktop → Windows Credential Manager.** Durable secrets via `keyring`,
   keyed `ClinikoScribe/<clinic_id>` + secret name. Phase 1 stores only the
   transient self-test credential (`test/probe`), deleted by the test itself.
   Real Cliniko API keys arrive in Phase 4 and live ONLY here.

4. **Session crypto.** AES-256-GCM keys from `os.urandom`; `destroy()`
   drops the in-memory key, making anything encrypted under it
   unrecoverable. UNWRAPPED keys exist only in process memory; since
   Phase 2 a DPAPI-wrapped copy lives on disk for the crash-recovery
   window (`key.dpapi`, flow 6) and encrypted artifacts persist under
   `sessions\<id>\` (flows 6–7) — deleting the wrapped key is the
   cryptographic deletion of those artifacts.

5. **Registration artifacts (machine-local, outside the repo).**
   `%LOCALAPPDATA%\ClinikoScribe\` holds the host manifest and a copy of
   `scribe-host.exe`, referenced from
   `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host`.
   Contain paths and the pinned extension ID — no secrets. (Chrome resolves
   the manifest only from a space-free path — see the threat model.)

6. **Microphone → encrypted session store (Phase 2).** `scribe-app` captures
   16 kHz mono PCM16 (sounddevice/WASAPI, ~1 s chunks). Each chunk is
   AES-256-GCM-encrypted IN MEMORY and appended to
   `%LOCALAPPDATA%\ClinikoScribe\sessions\<id>\audio.enc` (fresh random
   nonce per record, chunk index as AAD, sealed footer at Finish). The
   per-session key is DPAPI-wrapped (current-user) at
   `sessions\<id>\key.dpapi`, written durably BEFORE the first chunk.
   Plaintext audio exists ONLY in transient capture/processing buffers —
   never on disk, never in logs. Deleting `key.dpapi` is the cryptographic
   deletion of the session (same-user boundary; NTFS unlink residual — see
   the threat model). The microphone screen's idle level monitor feeds the
   meter only; monitor audio is never stored. Accepted same-user
   deployment residual: a folder-redirected/UNC `%LOCALAPPDATA%` would
   place `sessions\` (and the model cache) on SMB storage — runtime
   assumes the local profile; refusing here would block recording
   entirely, unlike the model paths, which DO refuse UNC before any stat
   (cheap, report-only).

7. **Local transcription (Phase 2, in-process, zero network).** On Finish,
   chunks are decrypted streamwise → silero-VAD segmentation → faster-whisper
   (CTranslate2, model `medium` per D6 as REVISED at the Step 13 gate;
   `small` stays the visible fallback when the medium snapshot is absent)
   with word timestamps, transcribed in packed ≤30 s windows →
   uncertainty marks (low-confidence words, numbers, names) → 2-speaker
   labels → `sessions\<id>\transcript.enc`, written atomically under the
   SAME session key. The transcript renders in a display-only view; the
   explicit Complete action runs fsync → decrypt-verify → key deletion.
   Offline enforcement: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
   `HF_HUB_DISABLE_TELEMETRY=1` set AND asserted at startup and before every
   ML import; models load from explicit local paths with
   `local_files_only=True`; the real-model tests run entirely under the
   enforced-offline env. The Phase-2 Step 13 proof suite added the
   network-stubbed-to-fail transcription test and socket polling during
   capture and transcription (landed; the manual completion gate passed
   2026-08-02). Env enforcement is the primary proof — socket polling
   alone can miss short-lived telemetry.

8. **Model cache (read-only at runtime).**
   `%LOCALAPPDATA%\ClinikoScribe\models\` — `silero-vad\silero_vad.onnx`
   (~2 MiB) plus CTranslate2 whisper snapshots (runtime default
   `whisper\medium`, ~1.43 GiB, with `whisper\small` ~465 MiB as the
   visible fallback; with all four benchmark candidates the cache is
   ~3.0 GiB). Static program data, no clinical content. Written ONLY by
   flow 9; runtime processes never write here. The hardware benchmark
   additionally synthesizes its fixed NON-CLINICAL sample script to a
   transient plaintext WAV (Windows SAPI) inside an auto-deleted temp
   directory — no clinical content ever takes that path.

9. **The ONE sanctioned network flow: `scripts/setup-models.py`
   (setup-time, separate process).** Explicit one-time HTTPS downloads into
   the model cache: silero-vad from its pinned GitHub release tag
   (SHA-256-verified) and whisper snapshots from Hugging Face pinned to
   immutable commit SHAs. Idempotent; never invoked by the app; runtime
   processes stay socketless. It must be run BY THE USER from a normal
   terminal — agent/MSIX-virtualized shells write to a package-private
   location invisible to user-launched processes (see `docs/lessons.md`).

## Explicit non-flows

- No plaintext clinical content at rest — audio and transcripts exist on
  disk ONLY encrypted under per-session keys inside `sessions\<id>\`.
- No network traffic from either desktop process at runtime (no-sockets
  integration test on host and app, plus offline env kill-switches set and
  asserted; the during-capture/during-transcription poll and the
  network-stubbed transcription test landed with Step 13, and the manual
  completion gate's independent monitor run passed 2026-08-02). Model
  downloads happen only in the separate setup script.
- No cloud AI services; no telemetry (HF telemetry disabled; onnxruntime
  telemetry off).
- No clinical content in logs — the whitelist + tripwire now also drops
  transcript-model markers (`transcript_segments`/`transcript_words`/
  `word_text`) and `encounter_context`.
- No data in Chrome extension storage (plan: credentials/models/audio never
  enter extension storage); no Chrome-side recording surface at all until
  Phase 5.
- Log/temp locations are user-local; exclusion from OneDrive/backup sweep is
  a Phase 6 task (`PLAN.md`), noted in the retention schedule.

## Phase 5 preview (locked topology — pipe deferred)

The Chrome-spawned host stays a thin, stateless relay; nothing new crosses
the Chrome boundary in Phase 2. The host↔app link — a user-ACL'd Windows
**named pipe** (local IPC, still zero network sockets) — was deliberately
deferred to Phase 5, whose consent/command flow is its real consumer; the
pipe-hardening notes live in the Phase 2 plan. This map must be updated when
that flow exists.
