# Data-Flow Map (Phases 1–3A)

Every place data lives or moves in the implemented system. Since Phase 2 the
desktop app carries **clinical data**: consultation audio, transcripts, and —
since Phase 3A — the composed note artifact, all encrypted at rest under
per-session keys; an unprotected recovery store expires at ~24 h (eligible at
24 h, destroyed by the next successful sweep), while a live or under-review
session is sweep-exempt (flow 10; retention schedule). Phase 3A also adds **clinician-authored config** (plaintext,
INTENDED as non-patient boilerplate — an unenforced operational rule, flow 11).
There is
**no status file** (that design was cut in plan hardening) and **no network
sockets** on either desktop process at runtime (enforced by
`desktop/tests/test_integration_no_sockets.py`, ruff import bans, and the
offline env kill-switches in flow 7) — the ONLY sanctioned network user is the
explicit model-setup script (flow 9). The note pipeline (flows 10–11) is
in-process and adds no network surface and no new logging channel.

## Components

| Component | Process | Trust context |
|---|---|---|
| Chrome extension (`extension/`) | Chrome renderer/service worker | Sandboxed by Chrome; ID pinned `mbmhglgadhdohpgbmpbjnaifjagfdfid` |
| Native host (`scribe-host`) | Spawned by Chrome per connection | Runs as the logged-in Windows user |
| Recorder app (`scribe-app`) | Standalone PySide6 process (multi-screen: microphone / session / recovery / transcript / note / status); single instance per user enforced by a named mutex; the Phase-3A note pipeline (compose → confirm → check → write) runs in-process here | Runs as the logged-in Windows user |
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

10. **Note pipeline (Phase 3A, in-process, zero network).** After transcription,
    `scribe-app` composes a draft note from the immutable transcript
    (`note.py` `compose_draft`: verbatim transcript spans under canonical
    headings, plus autofill/prefill PROPOSALS from config, flow 11). The
    clinician then confirms or declines each non-`transcript` line in the Note
    review tab (`ui/note.py`), the exact rendered wording is digested from the
    widget, and `note_check.py` runs four pure, digest-gated, LOG-FREE checks
    over the confirmed note (reconstruction, contradiction, provenance,
    omission — see the threat model for what each does and does NOT establish).
    On save, `session_store.write_note` encrypts the note to
    `%LOCALAPPDATA%\ClinikoScribe\sessions\<id>\note.enc` under the SAME
    per-session key as the audio and transcript (via `atomic_write_bytes`, no
    AAD), re-verifying every non-`transcript` assertion's confirmation evidence
    and refusing any unresolved `error`. `write_transcript` unlinks a stale
    `note.enc` FIRST (and fails closed if it cannot) so a note can never
    describe a superseded transcript. Complete verifies `note.enc` when one
    exists (decrypt → parse → session binding → transcript-digest match) BEFORE
    key deletion, so deleting `key.dpapi` is the cryptographic deletion of the
    note along with the audio and transcript (same custody and retention posture
    as the audio and transcript — the 24 h cap governs unprotected recovery
    stores; see the retention schedule).
    Plaintext note and the full transcript coexist in memory only for the review
    window (threat model, Phase 3A §3); the note is never logged and never
    written outside the encrypted store. Copy-to-Cliniko is gated (Task 9.1) and
    ships DISABLED — see the threat model.

11. **Config load (Phase 3A, read-only, plaintext, intended non-patient boilerplate — unenforced).**
    `note_config.load_note_config` reads clinician-authored config from
    `%LOCALAPPDATA%\ClinikoScribe\config\` — `template_profiles.json`
    (canonical-section → Cliniko-template-field mapping), `autofill_rules.json`,
    and `prefill_templates.json` — falling back to shipped package defaults per
    filename. It is INTENDED as non-patient boilerplate, deliberately OUTSIDE
    the encrypted session store and the 24 h rule so it survives session
    destruction. Patient data and secrets are prohibited by policy, but the
    loader validates only STRUCTURE (schema, length, control/format characters,
    atomic-claim shape) and cannot detect semantic misuse — so this is an
    operational rule, not an enforced guarantee: whatever a clinician hand-edits
    in is retained verbatim in plaintext. The load is all-or-nothing and fails
    CLOSED (a malformed or unreadable user file raises a typed error and applies
    nothing — never a silent partial apply of the shipped default). `config_digest` over
    the resolved config binds a generation run to the exact config that drove
    it. Config text feeds the note pipeline (flow 10) only as PROPOSALS; nothing
    from it reaches `note.enc` without per-assertion clinician confirmation.

## Explicit non-flows

- No application-generated plaintext clinical content at rest — the
  clinical artifacts this app produces (audio, transcripts, and the composed
  note `note.enc`, flow 10) exist on disk ONLY encrypted under per-session keys
  inside `sessions\<id>\`. Config files (flow 11) are a SEPARATE,
  operator-authored plaintext class: INTENDED as clinician-authored non-patient
  boilerplate, but that is an operational rule the loader cannot enforce
  semantically (it validates structure only), so it is NOT a content guarantee —
  whatever a clinician hand-edits in is retained verbatim.
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
  `word_text`) and `encounter_context`, and the Phase-3A note-model markers
  (`note_sections`/`note_assertions`/`note_spans`/`span_text`/`note_excerpt`/
  `note_warnings`/`note_warning_code`/`note_confirmation`), so a stray repr or
  `model_dump` of a note model is dropped by the last-line filter. The note
  pipeline itself opens no logging channel.
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
