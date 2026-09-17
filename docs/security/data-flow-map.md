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
| Recorder app (`scribe-app`) | Standalone PySide6 process (multi-screen: microphone / session / recovery / transcript / note / practitioner / status); single instance per user enforced by a named mutex; the Phase-3A note pipeline (compose → confirm → check → write), the practitioner-profile voice enrolment (flow 12) and the consented phrase learning (flow 13) run in-process here | Runs as the logged-in Windows user |
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
   with word timestamps, transcribed in packed ≤30 s windows (a lone VAD
   segment longer than the budget is its own oversized window) →
   uncertainty marks (low-confidence words, numbers, names) → 2-speaker
   labels → `sessions\<id>\transcript.enc`, written atomically under the
   SAME session key. The transcript renders in a display-only view; the
   explicit Complete action runs fsync → decrypt-verify → key deletion.
   Since the practitioner-profile plan's Phase 2 the SAME in-process flow
   optionally applies the practitioner's voice profile: the worker reads
   `profile\voice.enc` (flow 12, mapped at that plan's Task 3.3) and loads
   the speaker model from the cache (flow 8) INSIDE the transcription call,
   each VAD segment slice is embedded by that model inside the same
   transcription window as its spectral embedding (packed to ≤30 s; a lone
   longer VAD segment is its own oversized window) and reduced to one cosine
   against the enrolled vector before the window is dropped, labels become
   practitioner-vs-others (`speaker_1` is the practitioner, `speaker_2` is
   everyone else — one label for the whole remainder until D-S1 estimates
   the speaker count; D13 as amended 2026-09-16), and the
   transcript artefact carries three additional non-content fields (a
   cluster label, a cosine, a model id) under the same key — the recovery
   path (resume-processing) applies the profile identically. No profile, an
   absent model or a profile made by another model leaves this flow exactly
   as before and the Transcript screen names the fallback; nothing about the
   profile is written back and no audio or embedding is retained.
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
   ~3.0 GiB) and, for voice enrolment (practitioner-profile plan),
   `speaker-embedding\wespeaker-voxceleb-resnet34-LM.onnx` (~25 MiB; promoted
   from the practitioner's digest-verified candidate at that plan's Task 0.6,
   2026-09-15). Static program data, no clinical content. Written ONLY by flow 9; runtime processes never write
   here. The hardware benchmark additionally synthesizes its fixed
   NON-CLINICAL sample script to a transient plaintext WAV (Windows SAPI)
   inside an auto-deleted temp directory — no clinical content ever takes
   that path.

9. **The ONE sanctioned network flow: `scripts/setup-models.py`
   (setup-time, separate process).** Explicit one-time HTTPS downloads into
   the model cache: silero-vad from its pinned GitHub release tag
   (SHA-256-verified), whisper snapshots from Hugging Face pinned to
   immutable commit SHAs, and the speaker-embedding model (WeSpeaker
   VoxCeleb ResNet34-LM ONNX export, `Wespeaker/wespeaker-voxceleb-resnet34-LM`
   on Hugging Face) pinned by SHA-256 exactly like silero — a
   trust-on-first-download digest recorded from the practitioner's own
   candidate fetch (practitioner-profile plan Tasks 0.4–0.5, 2026-09-15); a
   digest mismatch refuses the bytes and promotes nothing. The
   speaker-embedding download — candidate and pinned alike — must be https
   on every redirect hop: a redirect to http is refused before it is
   fetched (the guard is installed for that helper only; silero-vad and the
   whisper snapshots rely on their pre-existing pins, not on a redirect
   guard). Idempotent; never invoked by the app;
   runtime processes stay socketless. It must be run BY THE USER from a normal
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
    `prefill_templates.json` and, since the practitioner-profile plan's Phase 4,
    `section_cues.json` (the phrases that route a transcript utterance into a
    canonical section) — falling back to shipped package defaults per
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
    it — the cue set included, so a note is bound to the cues that routed it.
    Autofill and prefill text feeds the note pipeline (flow 10) only as
    PROPOSALS; nothing from those files reaches `note.enc` without per-assertion
    clinician confirmation. Cue phrases never enter a note at all: they select
    which VERBATIM transcript utterance is placed in which section (a
    `transcript`-provenance assertion, reconstructed exactly by Check 1), so a
    hand-edited cue file can misplace transcript text but cannot add text to
    the note. The loader itself stays read-only; since the practitioner-profile
    plan's Phase 5 the app WRITES the cue file through one path of its own —
    flow 13 — and reads it back only through this loader.

12. **Voice enrolment → profile store (practitioner-profile plan Phase 3,
    in-process, zero network).** On the Practitioner tab (`ui/practitioner.py`),
    with the consent box ticked, `enrolment.record_enrolment` opens the capture
    backend's stream for the chosen microphone on a worker thread under
    `SessionController.begin_enrolment` and buffers the read-aloud as PCM IN
    PROCESS MEMORY — VAD-gated to 30 s of speech, capped at 90 s of audio; only
    numbers (speech seconds, seconds captured, a level) reach the tab, over a Qt
    signal. `enrolment.enrol` embeds each VAD segment with the pinned speaker
    model (flow 8) and averages one L2-normalised vector; the worker then drops
    its PCM reference, and `practitioner_profile.save_profile` writes
    `%LOCALAPPDATA%\ClinikoScribe\profile\key.dpapi` (first enrolment only —
    DPAPI-wrapped, current-user, with the profile description) and `voice.enc`
    (AES-256-GCM under that key: the vector, the embedder identity, the
    creation time, speech seconds, the device name and the consent record —
    the CURRENT text's version, `consent-v2` since Phase 5 (a `consent-v1`
    record is readable but not current: the tab asks for a fresh tick and
    phrase learning stays off until re-consent), acceptance time, learning
    opt-in). The lease is
    released after the tab's own status update, on every path. Re-record
    replaces `voice.enc` under the existing key; "Confirm consent" (Phase 5)
    re-saves the SAME vector under the existing key with a current consent
    record and the learning opt-in as ticked — one atomic replace of
    `voice.enc`, no microphone, no lease; Delete (confirmed) unlinks the
    key first, then the blob. Read back by flow 7 (attribution, inside the
    transcription worker), by the readiness probe that renders the tab's
    status and the microphone screen's report lines (a stat and one profile
    read on the GUI thread; no model is loaded there), and by the Note tab's
    learning-status read (flow 13). Nothing about the
    profile is logged (flow 2's tripwire markers), and no audio from this flow
    touches disk (the non-flow below).

13. **Review edit → queued phrase → Save → cue file + sidecar (practitioner-
    profile plan Phase 5, D9 as amended; in-process, zero network).** On the
    Note tab (`ui/note.py`), the clinician adds a whole transcript utterance
    to a section, or moves a routed line to another section, through the
    "Edit the note" controls (the transcript panel stays display-only). If
    the utterance is the CONFIRMED clinician's (`note.spoken_by_confirmed_
    clinician` — any other speaker's line stops here) and the learning
    status — read at review start and re-read at this add or move
    (`ui.models.learning_status`: a readable profile, the current consent
    version, the opt-in) — says learning is on, the utterance's leading two
    to four content tokens
    (`note_config.propose_learning_phrase`) are checked by
    `note_config.refuse_learning_candidate` — a name-like, numeric,
    date-shaped or medication-shaped source token refuses the candidate with
    a "not learned" note on the tab's status line — and an accepted phrase is
    QUEUED in memory on the screen with its section. Undo drops it; Cancel,
    Delete-and-complete and a new transcript clear the queue. On Save, after
    `write_note` has committed `note.enc` (flow 10), the status is re-read
    and `note_config.append_user_cues` reads the user `section_cues.json` (or
    the shipped default when there is none), appends the normalised phrases
    (duplicates under the loader's normalisation skipped), validates the
    exact bytes by the loader's rules, and replaces `%LOCALAPPDATA%\
    ClinikoScribe\config\section_cues.json` atomically (`session_store.
    atomic_write_bytes`), then the sidecar `section_cues.learned.json`
    (`{phrase: {section, learned_at}}`) the same way. The Practitioner tab
    lists the sidecar's recent entries and every non-shipped phrase in the
    cue file (`note_config.load_learned_phrases`) and deletes one from both
    files (`delete_user_cue`). Only the practitioner's own words leave the
    review, as config plaintext, by their consent (text v2); nothing here is
    logged (the phrase is shown on the local UI only).

## Explicit non-flows

- No application-generated plaintext clinical content at rest — the
  clinical artifacts this app produces (audio, transcripts, and the composed
  note `note.enc`, flow 10) exist on disk ONLY encrypted under per-session keys
  inside `sessions\<id>\`. Config files (flow 11) are a SEPARATE,
  operator-authored plaintext class: INTENDED as clinician-authored non-patient
  boilerplate, but that is an operational rule the loader cannot enforce
  semantically (it validates structure only), so it is NOT a content guarantee —
  whatever a clinician hand-edits in is retained verbatim. The one thing the
  app writes into that class itself is a learned phrase (flow 13): two to
  four words from the start of a line the PRACTITIONER said and added or
  moved during review, by consent — structurally never a patient's line, and
  shape-filtered against names, numbers, dates and medication names — but
  the filter cannot judge meaning, so a learned phrase is reviewable and
  deletable on the Practitioner tab rather than guaranteed non-clinical.
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
  `note_warnings`/`note_warning_code`/`note_confirmation`), and — since the
  practitioner-profile plan's Phase 1 — the voice-profile markers
  (`embedding`/`enrolment_speech_seconds`/`consent_text_version`), so a stray
  repr or `model_dump` of a note model or of the practitioner's profile is
  dropped by the last-line filter. Neither the note pipeline nor the profile
  path opens a logging channel. The Phase-2 attribution fields on the
  transcript (`enrolled_speaker` / `enrolment_similarity` /
  `speaker_model_id`) are a cluster label, a number and a model name — no
  content, so they register no marker; a transcript repr is still caught by
  the transcript markers it already carries. (The profile store and the
  enrolment flow are flow 12; the custody and attribution surfaces are in the
  threat model.)
- No enrolment audio on disk. The Practitioner tab's read-aloud (flow 12) is
  buffered in process memory only — never a session store, a chunk file, a
  WAV or a temp file — and the buffers, the VAD's recurrent state and the
  worker's PCM reference are all dropped before the profile is written; the
  only artefacts a completed enrolment leaves are `key.dpapi` and `voice.enc`.
  Pinned with a mock backend under a temporary `LOCALAPPDATA`
  (`desktop/tests/test_enrolment.py`) and at the tab level with a fake capture
  over a temporary profile root (`desktop/tests/test_ui_screens.py`).
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
