# Data-Flow Map (Phases 1–3A, practitioner profile, note learning, Cliniko workflow safeguards)

Every place data lives or moves in the implemented system. Since Phase 2 the
desktop app carries **clinical data**: consultation audio, transcripts, and —
since Phase 3A — the composed note artifact, all encrypted at rest under
per-session keys; an unprotected recovery store expires at ~24 h (eligible at
24 h, destroyed by the next successful sweep), while a live or under-review
session is sweep-exempt (flow 10; retention schedule). Phase 3A also adds **clinician-authored config** (plaintext,
INTENDED as non-patient boilerplate — an unenforced operational rule, flow 11).
There is
**no status file** (that design was cut in plan hardening). **Network: no
connection except Cliniko's API, and none at startup or idle** (Cliniko
workflow safeguards plan, D9; rewritten as a class at Task 1.2, 2026-09-27).
The native host has no network code at all. `scribe-app` holds exactly ONE
network-capable module, the read-only Cliniko client (`cliniko_client.py`,
flow 18): HTTPS `GET` to `api.<shard>.cliniko.com` only. What enforces that:
ruff's import bans (`socket`, `http`, `urllib.request`, `PySide6.QtNetwork`)
with exactly one exemption, on that module's `http.client` import, and a test
that no other module imports a network module (both in
`desktop/tests/test_cliniko_client.py`; a DYNAMIC import is outside what a
source check sees — the named residue). What the process does at runtime is
pinned separately: `desktop/tests/test_integration_no_sockets.py` asserts zero
connections from the host, from `scribe-app` at startup and idle, and during
capture, transcription and prose generation, and the offline env
kill-switches (flow 7) keep the ML stack off the network. The client has two
app callers (flow 18): the clinic registry, on a Validate or Replace key
pressed on the Clinics tab, and note verification (the plan's Phase 3), on a
recovered or Unreviewed session opened for checkout or review whose encounter
record names a Cliniko note, and — through the Chrome bridge (flow 19) — on a
note report from the focused Chrome tab and on a new pipe connection under a
linked live session; each runs on a practitioner action or a Chrome report,
never on startup or a timer. The other network users are TWO explicit SETUP-TIME steps outside the
running app, the model-setup script and the one-off pinned prose-runtime
wheel install, both in flow 9. The note pipeline (flows 10–11) is in-process
and adds no network surface and no new logging channel, and so is the prose
rendering the language model does (flow 17).

## Components

| Component | Process | Trust context |
|---|---|---|
| Chrome extension (`extension/`): the service worker, the side panel (an extension page) and the page script on Cliniko pages (flow 20) | Chrome's service-worker, extension-page and Cliniko-tab renderer processes | Sandboxed by Chrome; ID pinned `mbmhglgadhdohpgbmpbjnaifjagfdfid`; host access `https://*.cliniko.com/*` only, no `tabs` permission |
| Native host (`scribe-host`) | Spawned by Chrome per connection | Runs as the logged-in Windows user |
| Recorder app (`scribe-app`) | Standalone PySide6 process (multi-screen: microphone / session / recovery / transcript / note / practitioner / status); single instance per user enforced by a named mutex; the Phase-3A note pipeline (compose → confirm → check → write), the practitioner-profile voice enrolment (flow 12) and the consented phrase learning (flow 13) run in-process here; its one network-capable module is the read-only Cliniko client (flow 18); it listens on one per-user named pipe for the native host (flow 19) | Runs as the logged-in Windows user |
| Model setup script (`scripts/setup-models.py`) | Separate explicit process, run once per machine BY THE USER from a normal terminal | Runs as the logged-in Windows user; setup-time only, never at runtime |
| Prose-runtime install (`pip` over `desktop/requirements-ml-prose.txt`) | Separate explicit process, run once per machine BY THE USER from a normal terminal | Runs as the logged-in Windows user; setup-time only, never at runtime — the app never installs, updates or checks for a runtime |

## Flows

1. **Chrome ↔ native host (stdio, the ONLY browser transport).**
   Chrome spawns the registered launcher and connects stdin/stdout pipes.
   Framed JSON (4-byte native-order length prefix + UTF-8, ≤1 MB per frame,
   project policy both directions). Phase-1 messages: `hello`, `hello_ack`,
   `ping`, `pong`, `error`. Contains: protocol version, request IDs, a random
   per-session nonce — the handshake itself carries NO secrets and NO
   clinical data. Since protocol v2 (Cliniko workflow safeguards plan Tasks
   4.1 and 4.4, D2) the same wire also carries `context`, `command` and
   `state`, which the host RELAYS to and from `scribe-app`'s pipe (flow 19,
   which says what they contain — patient and note ids, and in `state` a
   verified patient's display name); the host stamps and checks this
   session's nonce on them and strips it toward the app. The host
   originates one message of its own, `state{app_running:false}`, while the
   app's pipe is absent. A v1 extension is refused at `hello`
   (`version_below_floor`).

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
   Real Cliniko API keys are entered on the Clinics tab (the Cliniko workflow
   safeguards plan's Phase 2) and, at rest, live ONLY here, under
   `ClinikoScribe/<clinic_id>` / `cliniko_api_key` — stored only after
   Cliniko has validated them, deleted by the tab's Remove, overwritten by
   its Replace key. A Validate or Replace key reads the TYPED key (never
   this store); note verification (Phase 3) reads the stored one, once per
   logical call, on its worker thread. Either way the client's own references go when the call
   ends — in memory only, and a still-live exception from the call keeps its
   frames (and so the key or token) referenced until it is dropped (flow 18).

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
   Between the key and `audio.enc`, Start writes `sessions\<id>\encounter.enc`
   (Cliniko workflow safeguards plan, D11; every session, linked or not): the
   practitioner's recording-consent attestation (time, text version, and the
   note and practitioner it names, if any) and, for a linked recording, the
   encounter context — clinic id and web host, patient, treatment note,
   booking, template and practitioner ids, and how it was verified; no name
   or other display text. AES-256-GCM under the session key, AAD
   `encounter:<session_id>`; a failed write refuses the start. It is
   decrypted ONLY when a recovered session is opened for checkout, or an
   Unreviewed session is opened for review (Task 5.4: the controller's
   `adopt_queued` decrypts it once — the adoption is the checkout — and the
   consent and context live on the in-memory session until it completes, is
   discarded or is retired again), plus ONCE per Unreviewed session at app
   start to rebuild the reminder index (Task 5.5: the key unwrapped for that
   one read and destroyed at once; only the clinic, note and session ids are
   kept, in memory). The recovery listing reads only whether the file
   exists; the sweep and the periodic refresh never read it. It goes with the session's key
   like every other artifact.
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
   visible fallback; with all four benchmark candidates those come to
   ~3.0 GiB), for voice enrolment (practitioner-profile plan),
   `speaker-embedding\wespeaker-voxceleb-resnet34-LM.onnx` (~25 MiB; promoted
   from the practitioner's digest-verified candidate at that plan's Task 0.6,
   2026-09-15) and, for the prose styles (note-learning-and-styles plan Phase
   4), `language-model\Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (~2.33 GiB; size
   and SHA-256 verified again at every load, flow 17) — so the whole cache is
   ~5.3 GiB with all four benchmark candidates and the language model. Static
   program data, no clinical content. Written ONLY by flow 9; runtime processes never write
   here. The hardware benchmark additionally synthesizes its fixed
   NON-CLINICAL sample script to a transient plaintext WAV (Windows SAPI)
   inside an auto-deleted temp directory — no clinical content ever takes
   that path.

9. **The TWO setup-time network steps (separate processes the user runs;
   the app's own network use is flow 18 alone).**
   (a) `scripts/setup-models.py`. Explicit one-time HTTPS downloads into
   the model cache: silero-vad from its pinned GitHub release tag
   (SHA-256-verified), whisper snapshots from Hugging Face pinned to
   immutable commit SHAs, the speaker-embedding model (WeSpeaker
   VoxCeleb ResNet34-LM ONNX export, `Wespeaker/wespeaker-voxceleb-resnet34-LM`
   on Hugging Face) pinned by SHA-256 exactly like silero — a
   trust-on-first-download digest recorded from the practitioner's own
   candidate fetch (practitioner-profile plan Tasks 0.4–0.5, 2026-09-15) —
   and, since the note-learning-and-styles plan's Phase 4 (2026-09-20), the
   local language model `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` from
   `unsloth/Qwen3-4B-Instruct-2507-GGUF` (2 497 281 120 bytes, ~2.33 GiB),
   pinned by SIZE and SHA-256 in `scribe_desktop.language_model` and fetched
   as streamed 1 MiB reads into `language-model\<name>.gguf.candidate` with
   HTTP Range resume, a free-space precondition (needed bytes + a 256 MiB
   margin) before any byte is written, and every read bounded by the PIN —
   the declared `Content-Length` is checked but never trusted as an
   allocation bound, and a longer body deletes the candidate. A digest
   mismatch refuses the bytes and promotes nothing; promotion to the real
   filename happens only after size AND SHA-256 match. The
   speaker-embedding and language-model downloads — candidate and pinned
   alike — must be https on every redirect hop: a redirect to http is
   refused before it is fetched (the same handler class serves both; silero-
   vad and the whisper snapshots rely on their pre-existing pins, not on a
   redirect guard). Idempotent; never invoked by the app, and the app never
   downloads a model. It must be run BY THE USER from a normal
   terminal — agent/MSIX-virtualized shells write to a package-private
   location invisible to user-launched processes (see `docs/lessons.md`).
   (b) The prose runtime's wheel install, `pip install --require-hashes
   --no-deps -r desktop\requirements-ml-prose.txt`. ONE requirement: the
   prebuilt CPU wheel `llama_cpp_python-0.3.35-py3-none-win_amd64.whl` as a
   GitHub release asset, pinned by URL AND SHA-256 (`--require-hashes`, so
   pip refuses anything else), followed by its two pure-Python dependencies
   from PyPI as wheels only (`--only-binary=:all:`) and a `pip check`. It is
   deliberately NOT part of the `[ml]` extra: PyPI carries only an sdist for
   this package, so a plain `[dev,ml]` install would BUILD it from source
   (forbidden by that plan's D8). An installed copy whose PEP 610
   `direct_url.json` does not name the pinned URL and hash is refused by
   `desktop/tests/test_language_model_runtime.py::TestInstalledRuntimeGate`.
   Run once per machine BY THE USER from a normal terminal, exactly like
   (a); the app never installs, updates or checks for a runtime, and never
   downloads a model.

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
    Inside the app, the plaintext note and the full transcript coexist in memory
    only for the review window (threat model, Phase 3A §3), and the app never
    logs the note and never writes it outside the encrypted store — with ONE
    exception the app does not hold: the clinician-initiated Copy below, whose
    clipboard copy outlives the review. Copy-to-Cliniko ships enabled since the
    practitioner's 2026-09-27 decision and is offered only for a fully ratified
    note; the copied text goes to the Windows clipboard by the clinician's own
    action and is outside the app's custody from there. Since Task 8.2 every
    copy of note text — the Copy button, and the keyboard's Copy or the
    context menu's Copy over the ratified note panel's selection — carries
    three registered Windows formats
    (`ExcludeClipboardContentFromMonitorProcessing`,
    `CanIncludeInClipboardHistory` = 0, `CanUploadToCloudClipboard` = 0) that
    Windows clipboard history and cloud clipboard sync honour, so the copy is
    not kept in history or uploaded. They do NOT stop any same-user process
    reading the current clipboard, a third-party clipboard manager may ignore
    the first of them, the note stays on the clipboard until something
    replaces it and nothing is cleared; a drag of the selected text is Qt's own
    (no formats, no clipboard — the text lands where it is dropped) — see the
    threat model, Phase 3A surface 4, and the retention schedule.

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
    the CURRENT text's version, `consent-v3` since the note-learning plan's
    Phase 0 (`consent-v2` was current from Phase 5 until then; a `consent-v1`
    or `consent-v2` record is readable but not current: the tab asks for a
    fresh tick and phrase learning stays off until re-consent), acceptance
    time, learning
    opt-in). The lease is
    released after the tab's own status update, on every path. Re-record
    replaces `voice.enc` under the existing key; "Confirm consent" (Phase 5)
    re-saves the SAME vector under the existing key with a current consent
    record and the learning opt-in as ticked — one atomic replace of
    `voice.enc`, no microphone, no lease; Delete (confirmed) unlinks the
    key first, then the blob. Read back by flow 7 (attribution, inside the
    transcription worker), by the readiness probe that renders the tab's
    status and the microphone screen's voice-profile report line (a stat and
    one profile read on the GUI thread; no model is loaded there — the tab
    reads at construction and after each of its own actions, the microphone
    screen at construction, on a device refresh, when the tab reports a
    change and, from its 5 s model-file poll, only when the speaker model's
    presence has flipped since the last read — the line names that presence,
    so an install or removal is one re-read, a steady poll none), and by the
    Note tab's
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
    review, as config plaintext, by their consent (text v3 — the current
    version; v2 was current when this flow was built); nothing here is
    logged (the phrase is shown on the local UI only).

14. **Capture → live transcription worker → live view (note-learning-and-styles
    plan, D1–D3; BUILT, Phase 1, 2026-09-19; in-process, zero network).** The
    capture sink is `session._tee_sink`: the store's encrypting `append_chunk`
    runs FIRST (its failure fails the session as before), then the SAME
    plaintext chunk goes to `LiveTranscriber.feed` inside a boundary that
    never raises into the capture thread — so the worker never holds
    `SessionCrypto`, never reads the encrypted store and never writes a file.
    In the worker the PCM lives as the open VAD span, the packed ~30 s windows
    and the queued chunks (capped at `LIVE_QUEUE_CAP_BYTES`, three windows'
    worth — over the cap the worker fails itself as `fell_behind`), dropped
    per window as it is transcribed; VAD segments with their embeddings and
    enrolment cosines stay in process memory for the session. Each transcribed
    window is posted through a queued Qt signal to the display-only transcript
    widget (`ui/transcript.py`; a post after the view closed is dropped; the
    view is cleared on the Session screen's Discard and replaced wholesale by
    the final document). The same queued signal also reaches the main
    window's phrase rules (Cliniko workflow safeguards plan Tasks 7.2–7.3,
    `voice_commands.py`) while the recording is live: they read each window's
    words in memory to pause on "scribe pause" or raise the new-consultation
    warning, change no word, write nothing and log nothing; between windows
    they keep only the last normalised word of the latest window that held
    words (for a phrase split across two) until the next Resume or Start, the
    resume cutoff (a number of seconds) and a window count. Finish seals capture as before and the TAIL DRAIN
    (the last open span and any queued windows) runs on the processing
    `TaskThread` inside the transcriber callable (`ui/models._live_transcript`
    via `claim_live_transcriber`), never on the GUI thread, and writes
    `transcript.enc` once through `assemble_transcript`; the worker's models
    are released before the batch fallback builds its own. Discard stops and
    joins the worker and requires its buffers CONFIRMED cleared
    (`buffers_cleared`) BEFORE the session key is destroyed — an uncleared
    stop refuses the key deletion, routes the recording to FAILED with key +
    chunks intact and is retried by the next Discard; the same verdict gates
    the three Complete paths and retirement on a new Start (threat-model
    surface 11). A load failure, `fell_behind`, a worker error or a drain error
    falls back to the batch stage (flow 7) with its reason on the Session
    screen. No new logging channel: the one new record is
    `live_transcriber_stop_timeout` (session id and state only). Flows 15–16
    and the note-learning non-flows below are likewise BUILT — the Phase 0
    stubs were finalised at that plan's Phase H (task H3, 2026-09-25).

15. **Typed edit → typed line → (on Save) learned rule (note-learning-and-styles
    plan, D4, D5, D11; in-process, zero network).** Phase 0 BUILT the carriers:
    a `clinician`-provenance assertion in `note.py` whose span text is the typed
    text, with `proposal_id = None`, its decision naming the line itself and an
    optional `replaces`; `compose_draft`'s `_confine_provider_output` keeps a
    provider to transcript provenance; `write_note` verifies a typed line's
    `shown_text_digest` and `config_digest`; and `note_config.
    refuse_typed_wording` (numbers, dates, medication tokens; NO name
    heuristic) with `LEARNED_RULE_AUTO_CONFIRM_AFTER = 3`. Phase 2 BUILT the
    flow: the Note tab's Edit control (`ui/note.py` `edit_line`) produces the
    typed line over a note line or proposal (in memory, beside the draft — the
    same review-window plaintext as the rest of the tab); when the replaced
    line is the confirmed clinician's own utterance the trigger (its tail
    through `refuse_learning_candidate`) and the typed wording (through
    `refuse_typed_wording`) are QUEUED in memory and written by the Save-time
    writer `append_learned_rules` — and only by it — into
    `%LOCALAPPDATA%\ClinikoScribe\config\autofill_rules.json` with the metadata
    sidecar `autofill_rules.learned.json` (two atomic replaces, rules file first,
    as flow 13 does for cues; every candidate validated as an `AutofillRule` and
    duplicate-checked before any write); an edit over a LEARNED rule's own line
    queues an in-place wording replacement instead (`replace_learned_rule_wording`,
    sidecar first); each Save also counts the learned rules whose lines stood
    (`record_rule_outcomes`, the sidecar only). Next generation,
    `note_fill.config_decisions` reads the sidecar (fail-safe: an unreadable
    sidecar means every learned rule proposes) and pre-fills an auto-confirmed
    learned rule's wording with a `decided_by="config"` decision carried on the
    draft. The Practitioner tab reads both files (`load_learned_rules`) and
    deletes through `delete_learned_rule`. Nothing in this flow is logged: typed
    wording is note-model text and carries the note tripwire markers (flow 2),
    and the learned-rule carriers' `typed_wording` / `previous_expansion` are
    registered markers too. No network, no new channel.

16. **Sample notes → learner → `style\style.enc` (note-learning-and-styles plan,
    D9, D10; in-process, zero network).** Phase 0 BUILT the destination:
    `%LOCALAPPDATA%\ClinikoScribe\style\key.dpapi` (DPAPI-wrapped, current-user,
    with the style-specific description the unwrap verifies) and `style.enc`
    (AES-256-GCM under that key, its own AAD), written and read by
    `practitioner_profile.save_style_profile` / `load_style_profile` and removed
    key-first by `delete_style_profile`, independently of the voice profile
    (flow 12); the session, voice and style keys cannot open each other's store.
    Phase 3 BUILT the flow into it. The Practitioner tab's "Learn from my
    notes" group reads 1–5 chosen `.txt`/`.docx`/`.pdf` files (a `.pdf` — the
    Cliniko export — text-extracted by `pypdf`, never OCR'd; Phase 4 live
    smoke, practitioner decision 2026-09-20) and/or one pasted note
    through `sample_notes.read_sample_note` — into memory only, never copied
    and never moved (a whole-tree before/after snapshot test pins it) — and
    `learn_style_profile`, pure over those texts, derives the section order and
    headings, the shorthand split by exact membership of
    `note_config.CLINICAL_ABBREVIATIONS`, simple count measures and up to
    `MAX_STYLE_EXEMPLARS = 30` exemplar sentences, each one passed UNCHANGED to
    `refuse_learning_candidate` and dropped whole on any refusal class.
    `ui/style_review.run_style_review` then shows the draft for review
    (unrecognised abbreviations as tick-to-keep rows, unticked by default;
    per-sentence remove) and only its Save writes: `build_style_profile` —
    which refuses anything the draft did not itself list, so the review can
    only remove — plus a fresh `ConsentRecord` under text v3 from the tab's
    consent tick (no voice profile needed or read), sealed by
    `save_style_profile` under the style key. AFTER a successful save, and only
    when files were the source, a SEPARATE confirmation names the paths with
    "Delete these files now" unticked by default
    (`ui/style_review.DeleteOriginalsDialog`); a ticked, accepted dialog calls
    `delete_sample_files`, which unlinks exactly those paths and reports every
    failure. The tab's learned-style summary and lists come from ONE decrypt
    (`refresh_style_profile_state` → `load_style_profile`, re-run after a learn,
    a remove, a delete or a consent renewal — "Confirm consent" re-saves the
    same profile with a current consent record, content untouched — and on no
    timer), each per-item Remove re-saves the
    profile under the same key, and "Delete learned style" removes the store
    key-first through `delete_style_profile`, independently of the voice
    profile. Nothing in this flow is logged (`sample_text`,
    `recognised_shorthand`, `unrecognised_shorthand` and `exemplar_text` are
    registered tripwire markers and none of these modules holds a logger).
    No network, no new channel. Since Phase 4 the prose stage READS this
    profile (per job, never on a poll) as conditioning for the Own-voice
    style — the style profile and confirmed assertion text only, never the
    transcript (flow 17).

17. **Prose rendering (note-learning-and-styles plan Phase 4, D6, D7, D8;
    in-process, zero network).** Input: the confirmed assertion TEXTS of a
    FINALISED note, grouped by section — never the transcript and never a
    pending proposal, refused BY TYPE (`prose_style.ProseInput.from_note`
    takes a `GeneratedNote`; a `TranscriptDocument` or a `NoteDraft` raises).
    The Note tab starts ONE stage job per finalisation on its `TaskThread`
    (`ui/note.py` `_start_style_stage`; `ui/models.build_prose_stage`): the
    model is built once per process on that worker thread from the LOCAL file
    only — `assert_offline_env`, UNC refused, presence, size and SHA-256
    against the pins in `scribe_desktop.language_model`, then a smoke
    generation — and for Own voice the style profile is decrypted per job
    through `load_style_profile` (flow 16), never on a poll. Each section is
    ONE call: the prompt is the section title, its confirmed lines between
    `PROMPT_LINES_HEADER` / `PROMPT_LINES_END` and a fixed narrative
    instruction (plus the profile's measures, shorthand and ≤ 30 exemplars as
    conditioning for Own voice). The completion goes through
    `prose_style.parse_section_prose` and then Check 5
    (`note_check.fidelity_warnings` — missing fact, added content, polarity,
    protected tokens); a refused section's prose is DROPPED before the result
    is built and the section is shown as Clean clinical with a review warning.
    What survives is a `StyleRendering` bound to that section's input digest,
    attached only while the digest still matches
    (`note.attach_style_renderings`), displayed and persisted through
    `note.render_note` with the rest of the note in `note.enc` under the SAME
    per-session key (flow 10) — so a rendering has exactly the note's custody,
    lifetime and deletion, and Copy shows the same bytes. In memory only, with
    the lifetimes stated exactly (codex round 22 PR-MED-034): one section's
    prompt and completion for that `complete` call, at whose end the runtime's
    inference state — token buffers and KV cache — is cleared
    (`LocalLanguageModel._clear_inference_state`); every section's parsed
    prose, refused prose included, for the one `render` call that judges the
    batch (the refused text is dropped before the result is built); the loaded
    model stays resident for the life of the process (~2.5 GiB of process
    memory) and is freed with it.
    Nothing here is written outside `note.enc`, nothing is logged
    (`section_texts`, `prose_text` and `style_renderings` are registered
    tripwire markers), and no socket is opened — pinned by the prose legs of
    `desktop/tests/test_integration_no_sockets.py`.

18. **Cliniko API reads (Cliniko workflow safeguards plan, D9; client BUILT
    at Task 1.1, 2026-09-27; memory only).** `scribe-app` → HTTPS `GET` →
    `https://api.<shard>.cliniko.com/v1/...` through `cliniko_client.py`, the
    app's one network-capable module. Resources: `/user`,
    `/practitioners?q[]=user_id:=<id>`, `/settings/public`, `/settings`,
    `/treatment_notes/<id>`, `/patients/<id>`, `/bookings/<id>` — reads only;
    the transport refuses any method but `GET` and the module has no write
    method. WHAT LEAVES the machine: the clinic's API key (HTTP Basic
    username, inside TLS), the requested ids in the path (digits only,
    validated), and the practitioner's contact email in the required
    `User-Agent: Clinic Scribe (<email>)` (refused on CR/LF or a failed shape
    check). WHAT RETURNS: the key user's role and practitioner record, the
    account subdomain, and for a note its draft state, links (patient,
    practitioner, booking, template) and content, the patient's record (the
    display name) and the booking's time. Every answer is held in memory
    only: the client writes nothing, logs nothing and returns the parsed JSON
    object to its caller; only a 200's body is read (any other status is
    classified from its status line and headers), and a body over 1 MiB is
    refused unread past 1 MiB + 1 byte. Controls (threat-model "Cliniko API
    client"): the host only from a documented shard (an unknown or missing
    key suffix is refused, never defaulted), TLS 1.2+ verified against the
    Windows certificate store, a 15 s per-step timeout and a 30 s request
    deadline over the body read (one socket receive per read), no redirects,
    no proxy, `http.client` debug output pinned off, `SSLKEYLOGFILE` removed
    at startup and refused, the key read once per logical call and never in a
    log line, the client's state, or any exception's rendered text (message,
    repr, formatted traceback) — a still-live exception from the call does
    keep its frames, and so the key or Basic token, the path, ids and
    response bytes, referenced in memory until it is dropped (threat-model
    residue (6)). CALLERS: `clinics.py` and `encounter.py` are the only app
    modules that import the client (pinned by `test_cliniko_client.py`). A Validate or Replace
    key on the Clinics tab is ONE client call on a worker thread, with the
    key the practitioner just typed: `GET /user`, `GET /practitioners` for
    that user and `GET /settings/public`. What it keeps: on success, the
    key (Credential Manager only, flow 3) and a non-secret record in
    `clinics.json` — the clinic id, the name the practitioner typed, the
    subdomain and shard, the key user's user and practitioner ids, the
    validation time, whether the subdomain is confirmed, and the contact
    email; on a refusal by Cliniko or a local check, nothing. A failed
    Credential Manager store or file write can leave the partial states the
    threat model's CLINIC KEYS paragraph names (a listed clinic with no key;
    a replaced key under the old record). The role, the practitioner list and the
    rest of each answer are dropped with the call. Nothing calls the client
    at startup, on a timer or while idle (the registry's construction reads
    `clinics.json` only). NOTE VERIFICATION (Phase 3, `encounter.py`
    `verify_note_context`) is ONE client call on a worker thread with the
    key read once from Credential Manager: `GET /treatment_notes/<id>`,
    `GET /patients/<id>` and, when the note links one, `GET /bookings/<id>`.
    It runs when the practitioner opens a recovered session for checkout, or
    an Unreviewed session for review, whose encounter record (flow 6) names a
    note, again if a clinic changes while that checkout is open, and for the
    Chrome triggers below. What it keeps: an outcome in memory — ids,
    a verification state and time, or a reason code — and, beside it, a
    separate display value (the patient's name, cleaned to one line of at
    most 120 characters, and the appointment time) that no model, record,
    log or file holds and Phase 3 showed nowhere; the note's content and
    the rest of each answer are dropped with the call. A checkout's outcome
    is dropped when the checkout ends. The practitioner-run feasibility script
    `scripts/probe-cliniko.py` (Task 1.3) is a separate process built on the
    same client that prints structure only — never a name, id value, answer
    text or the key. Since Task 4.5 the Chrome bridge (flow 19) is a second
    trigger for the same call: a note report from the bound Chrome tab on an
    allow-listed host, and — once per new pipe connection — the linked live
    session's own note; the display value then reaches the pipe's `state`
    and the Session screen, for the verified note only (flow 19).

19. **Native host ↔ `scribe-app` over a named pipe (Cliniko workflow
    safeguards plan D2/D4; BUILT at Tasks 4.1, 4.2, 4.4 and 4.5,
    2026-09-27; memory only).** Local IPC, not a network endpoint: the
    no-sockets legs poll the app with the pipe listening AND a client
    connected (`test_scribe_app_with_the_chrome_link_open_has_no_sockets`),
    and a real host process relaying to a real app over it
    (`test_host_relays_to_an_open_app_pipe_with_no_sockets`).
    The app creates `\\.\pipe\ClinikoScribe-<user SID>` after its
    single-instance guard (`pipe_server.py`): first instance only (a held name
    is refused, never shared — the Session screen then says the Chrome link is
    unavailable and desktop recording still works), one instance, remote
    clients rejected, and a protected DACL granting only the current user.
    Its client is the native host (Task 4.4), which relays flow 1's v2
    messages, and which connects only after VERIFYING the server — the same
    logon session, the same user, and exactly that DACL (Task 4.3, decided
    (b): any process of this user can still connect or squat the name — the
    threat model's accepted residue). Frames are flow 1's framing, WITHOUT a
    nonce (the host strips and stamps it), and only `context` and `command`
    are accepted inbound — any other frame, a framing fault or an invalid
    payload closes that connection; the host likewise relays only a valid
    `state` back.
    WHAT CROSSES, inbound: a `context` report per Chrome tab (a sequence
    number, tab and window numbers, focus, the page kind, and for a Cliniko
    page its host, plus the patient and note ids on a treatment-note page —
    never a URL) and a `command` (the action, the snapshot revision it
    answers, the session reference it acts on, and for `start` the target
    ids and the panel's consent tick). Outbound, one `state` snapshot, sent on
    change and in full to every new connection: the allow-list of clinic
    hosts, the bound report (ids, the verification state or refusal code, the
    clinic's label, and ONLY for a note Cliniko verified the patient's display
    name and the appointment time), the live session (an opaque 24-character
    reference — never the session id — its phase, recorded seconds, consent
    time, and when linked its ids, verification and clinic label, plus the
    patient's name when that session was started from a verified note), the
    resolution block while a linked session is paused by the pause rule
    (Task 5.1–5.2: the reason code, the live session's reference, its OWN
    clinic host and label, and that same session's name under the same
    rule), the Unreviewed banner while the focused tab reports a note that
    has retired recordings (Task 5.5: the newest one's reference, the host,
    the note id and the count — no patient's name), a notice code, the
    last refusal (a code and a fixed message), and the hands-free status
    (Phase 7: whether the pause hotkey is reserved and its chord's name,
    whether the spoken pause works for the live recording, and the
    `new_consultation` warning code while the recording it was raised on is
    live — codes and a key name, never a word of the transcript).
    Every field is bounded by `protocol/fixtures/meta.json`'s `limits`, and
    ids match `^[1-9][0-9]{0,18}$`. WHAT IS KEPT: in the bridge's memory only —
    the latest report per open tab and the bound tab, cleared on every new
    connection or disconnect; the bound report's verification outcome (flow
    18's display value beside it); the live session's display name, dropped
    when that session ends; the tab the linked live session is bound to (a
    tab number, forgotten on every new connection or disconnect and when the
    session ends), its block (a reason code, while it is paused) and a
    clicked "Resume previous" (a time, lapsing after 30 seconds); the hotkey's
    status and the session id a warning was raised on (dropped when that
    recording finishes or ends); and the
    last snapshot sent, for change detection. The main window keeps the
    Unreviewed reminder index (Task 5.3: clinic id, note id and session id
    per retired linked queued session, never persisted; rebuilt at app start
    from each Unreviewed session's `encounter.enc`, Task 5.5), which loses an
    entry when that session is completed, discarded, expires or is opened
    for review.
    Nothing is written to disk, and nothing is logged beyond a connection's
    state or close reason with its connection number (`pipe_client`), the
    server's own state (`pipe_server`), a failed connect's Windows error
    code and, at each end, the OTHER end's executable path (`pipe_peer`,
    Task 4.3's tripwire) — never a frame. The host is a pass-through: it
    keeps no message, and its log holds message types, relay states and that
    path only (`scribe-host.log`). `patient_name` and `note_id` are
    registered tripwire markers. What Chrome does with `state` is flow 20.

20. **`state` inside Chrome: the service worker, the page script and the side
    panel (Cliniko workflow safeguards plan D1/D2/D13; BUILT at Tasks
    6.0–6.5, 2026-09-28; memory only).** WHAT CHROME READS: the URL of a tab
    only while it is on a `*.cliniko.com` host (the extension holds no `tabs`
    permission), and — from the page script — that page's `location.href`;
    never Cliniko's DOM or content. The service worker turns those into
    `context` reports (flow 19; no URL leaves Chrome) and sends the app's
    `command`s for the panel's and the block's clicks. WHAT THE APP'S `state`
    BECOMES: the service worker keeps the LATEST snapshot of the current
    connection (`ConnectionManager.appState`) — so, while the app publishes
    them, the verified patient's name and appointment time of the bound
    report and of the live or blocked session — and a table of open tabs
    (ids, window, whether active, and a Cliniko tab's URL), plus the report
    it last sent for each tracked tab and the text of the slice it last sent
    to each Cliniko tab (for change detection — so it may hold that tab's
    clinic's patient name; dropped when the tab closes, on a resync or when
    the tab's page script says hello). From that it sends: to the SIDE PANEL
    (this extension's own page), the whole snapshot with the focused tab's
    kind, over a port the worker accepts only from that page; to EACH page
    tab on an allow-listed host, only that tab's slice (`context.ts`
    `sliceFor`): the frame colour and, while a block stands, the block —
    naming the recording's patient only when the recording belongs to that
    tab's own clinic host (else that clinic's label only, with no name or ids
    of that patient), and the patient on the tab itself only when the app's
    bound report is that tab's and Cliniko verified it. A page tab never
    receives the report, the live session, the banner or a refusal. The panel
    and the page script draw every string with `textContent` (the page script
    inside a closed shadow root); the side panel also keeps, while its Ready
    layout stands, that note's key (the tab number, host, patient and note
    ids and the verification state) so that any change clears the consent
    tick. WHAT IS KEPT: memory
    only — the worker's snapshot until the next one, a disconnect or the
    worker's stop; the panel's view until it closes; a page script's slice
    until the next slice, its return to inert (its host leaves the
    allow-list, the app stops) or the page unloads. Nothing is written to
    `chrome.storage` or other browser storage and nothing is logged but the
    native host's disconnect diagnostic (no payload) — pinned by
    `extension/src/sinks.test.ts`, a text-matching guard with named limits.
    OUTSIDE THE APP'S CUSTODY: a Chrome crash dump of those processes may
    hold what they held (threat model, "The Chrome extension" residue (8)),
    and a Cliniko page can see the page script's own element and detect the
    installed extension through its web-accessible module (residue (2)).

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
  Since the note-learning-and-styles plan's Phase 0 there is a SECOND encrypted
  practitioner store beside the voice profile: `style\style.enc` under its own
  DPAPI-wrapped key (`practitioner_profile.save_style_profile`; the session,
  voice and style keys cannot open each other's store). Since Phase 3 it holds
  what the learner derived from the practitioner's OWN chosen past notes —
  headings, shorthand, measures and up to 30 practitioner-reviewed exemplar
  sentences that passed the shape filter unchanged — under the practitioner's
  consent (text v3), never under a session key and never a copy of a chosen
  note; it is written only by the Practitioner tab's Save after the review, by
  that tab's per-item Remove re-saving the same profile (flow 16), and by its
  "Confirm consent" re-saving the same profile with a current consent record
  (content untouched; codex round 31 PR-LOW-048).
- No network traffic from either desktop process at runtime EXCEPT
  `scribe-app`'s read-only calls to Cliniko's API (flow 18), and none at
  startup or idle — a call follows only a practitioner action or a note
  report from Chrome, so an app started while Chrome shows a Cliniko
  treatment note verifies it once that report arrives, and the no-sockets
  legs measure startup and idle with no Chrome link (no-sockets integration test on host and app, plus offline
  env kill-switches set and asserted; the during-capture/during-transcription
  poll and the network-stubbed transcription test landed with Step 13, and the
  manual completion gate's independent monitor run passed 2026-08-02; since
  the note-learning plan's Phase 4 the poll also runs inside a prose
  generation). No other destination: the client's host is built only from a
  documented Cliniko shard, and no other module may import a network module
  (flow 18). Model downloads and the prose-runtime install happen only in the
  separate setup-time processes (flow 9).
- No cloud AI services; no telemetry (HF telemetry disabled; onnxruntime
  telemetry off).
- No clinical content in logs — the whitelist + tripwire now also drops
  transcript-model markers (`transcript_segments`/`transcript_words`/
  `word_text`) and `encounter_context`, and the Phase-3A note-model markers
  (`note_sections`/`note_assertions`/`note_spans`/`span_text`/`note_excerpt`/
  `note_warnings`/`note_warning_code`/`note_confirmation`), and — since the
  practitioner-profile plan's Phase 1 — the voice-profile markers
  (`embedding`/`enrolment_speech_seconds`/`consent_text_version`), and — since
  the note-learning-and-styles plan — the learned-style markers `exemplar_text`
  (Phase 0) with `sample_text`, `recognised_shorthand` and
  `unrecognised_shorthand` beside it (Phase 3, flow 16), so a stray
  repr or `model_dump` of a note model, of the practitioner's profile or of a
  sample note or style draft is
  dropped by the last-line filter. Neither the note pipeline nor the profile
  path opens a logging channel, and none of `sample_notes.py`,
  `ui/style_review.py` or the Practitioner tab holds a logger. The Phase-2 attribution fields on the
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
- No data in Chrome extension storage: credentials, models, audio,
  transcripts and patient names never enter `chrome.storage` or any browser
  storage (flow 20; `extension/src/sinks.test.ts`, a text-matching guard).
  The Chrome-side recording surface — the side panel, the page frame and the
  block — holds what it shows in memory only; the Cliniko API key never
  reaches Chrome at all (no protocol field carries it).
- Log/temp locations are user-local; exclusion from OneDrive/backup sweep is
  a Phase 6 task (`PLAN.md`), noted in the retention schedule.
- No uploaded sample note on disk (note-learning-and-styles plan, D9; BUILT,
  Phase 3): the 1–5 notes the practitioner chooses are read into memory by
  `sample_notes.read_sample_note`, never copied and never moved — pinned by a
  before/after snapshot of the whole temporary tree
  (`tests/test_sample_notes.py::TestReadSampleNote::
  test_a_txt_file_is_read_into_memory_and_the_tree_is_untouched`) — and only
  the derived, reviewed style profile is written (flow 16). Deletion of the
  originals is a separate explicit confirmation naming the paths, unticked by
  default, and unlinks exactly the listed paths through
  `sample_notes.delete_sample_files` (a directory is refused, never walked;
  `TestDeleteSampleFiles::test_exactly_the_listed_paths_go`).
- No transcript text to the language model (note-learning-and-styles plan, D6,
  D8; BUILT, Phase 4). The prose stage's ONLY input is
  `prose_style.ProseInput.from_note`, which takes a FINALISED `GeneratedNote`
  and refuses a `TranscriptDocument` or a `NoteDraft` BY TYPE — so neither
  transcript text nor a pending proposal can reach the model — and
  `build_section_prompt` takes text LINES only (a section title, the confirmed
  lines, the fixed narrative instruction, and for Own voice the style
  profile's measures, shorthand and exemplars as conditioning). Flow 17.
- No network from the prose runtime (note-learning-and-styles plan, D8; BUILT,
  Phase 4). The runtime is installed ONCE, by the practitioner, from the
  pinned hashed wheel (flow 9b); the app process opens no socket during a
  prose generation. `assert_offline_env` is NOT the enforcing control here —
  llama-cpp-python reads no kill-switch variable (the contract does refuse its
  `LLAMA_CPP_LIB_PATH` library override, threat-model surface 17) — the
  enforcing control is `desktop/tests/test_integration_no_sockets.py` in two
  legs (codex round 22 PR-LOW-040): the mock-model leg polls the OS socket
  table while the process is inside a model call and covers the STAGE's
  orchestration (no native code runs there); the real-model leg covers the
  RUNTIME — the real library's load and one generation under continuous polls
  — and skips BY NAME until the wheel and the file exist, so that evidence is
  conditional.

## The Chrome side at a glance

Chrome ↔ native host over stdio (flow 1) ↔ `scribe-app` over the per-user
named pipe (flow 19), with what Chrome keeps and draws in flow 20. The
Chrome-spawned host is a thin, stateless relay; the app alone decides every
pause, Start, Resume and refusal; a patient's name crosses only for a note
Cliniko verified, lives in memory only on both sides, and reaches a Cliniko
tab only for that tab's own clinic.
