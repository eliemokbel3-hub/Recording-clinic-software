# Data-Flow Map (Phases 1–3A, practitioner profile, note learning, Cliniko workflow safeguards, Cliniko draft write, privacy and professional controls, installation, pilot)

Every place data lives or moves in the implemented system. Since Phase 2 the
desktop app carries **clinical data**: consultation audio, transcripts, and —
since Phase 3A — the composed note artifact, all encrypted at rest under
per-session keys; an unprotected recovery store expires at ~24 h (eligible at
24 h, destroyed by the next successful sweep), while a live or under-review
session is sweep-exempt (flow 10; retention schedule). Since the
privacy-professional-controls plan (PLAN.md Phase 6) every non-mock Complete
copies the session's transcript, saved note and generated note — never audio —
into an encrypted Past-sessions entry kept for the practitioner's retention
setting, with the patient's name in that entry's label, and every session
leaves a content-free audit row for 7 years (flow 22). Phase 3A also adds **clinician-authored config** (plaintext,
INTENDED as non-patient boilerplate — an unenforced operational rule, flow 11).
There is
**no status file** (that design was cut in plan hardening). **Network: no
connection except Cliniko's API, and none at startup or idle** (Cliniko
workflow safeguards plan, D9; rewritten as a class at Task 1.2, 2026-09-27).
The native host has no network code at all. `scribe-app` holds exactly ONE
network-capable module, the Cliniko client (`cliniko_client.py`, flow 18):
HTTPS to `api.<shard>.cliniko.com` only, as a `GET` with no body or — since
the cliniko-draft-write plan — ONE kind of write, a `PATCH` of a
`{"content": {...}}` body to `/v1/treatment_notes/<id>` that fills an open
draft note (the transport refuses every other shape before connecting). What enforces that:
ruff's import bans (`socket`, `http`, `urllib.request`, `PySide6.QtNetwork`)
with exactly one exemption, on that module's `http.client` import, and a test
that no other module imports a network module (both in
`desktop/tests/test_cliniko_client.py`; a DYNAMIC import is outside what a
source check sees — the named residue). What the process does at runtime is
pinned separately: `desktop/tests/test_integration_no_sockets.py` asserts zero
connections from the host, from `scribe-app` at startup and idle, and during
capture, transcription and prose generation, and the offline env
kill-switches (flow 7) keep the ML stack off the network. The client has three
app callers (flow 18): the clinic registry, on a Validate or Replace key
pressed on the Clinics tab; note verification (the safeguards plan's Phase 3), on a
recovered or Unreviewed session opened for checkout or review whose encounter
record names a Cliniko note, and — through the Chrome bridge (flow 19) — on a
note report from the focused Chrome tab and on a new pipe connection under a
linked live session; and the draft write, on the Note tab's "Write draft to
Cliniko" click only (its reads, then its one `PATCH`); each runs on a
practitioner action or a Chrome report,
never on startup or a timer. The other network users are TWO explicit SETUP-TIME steps outside the
running app, the model-setup script and the one-off pinned prose-runtime
wheel install, both in flow 9, and — since the installation plan (PLAN.md
Phase 7) — the BUILD-time steps that make a release (flow 9 (c)); the
installer and the installed app download nothing (flow 23). Since that plan a
source checkout is the developer build, a separate channel with its own data
and models folder `%LOCALAPPDATA%\ClinikoScribe-dev` (flow 24): every
`%LOCALAPPDATA%\ClinikoScribe` path below is the installed (production) app's,
and a source checkout uses the same layout under `ClinikoScribe-dev`. The
installed app has been in clinical use on this computer since its Phase P
install, 2026-10-03 (0.1.2 since 2026-10-04; `docs/release/pilot-builds.md`). The note pipeline (flows 10–11) is in-process
and adds no network surface and no new logging channel, and so is the prose
rendering the language model does (flow 17). Since the pilot plan (PLAN.md
Phase 7's pilot half) a recording started while "Shadow mode (pilot)" is
ticked is a SHADOW recording, whose note never leaves the app by Copy or by
the draft write (flow 25), and the developer build carries an offline
validation harness that runs the pipeline over invented or mock recordings
outside the app's own stores (flow 26).

## Components

| Component | Process | Trust context |
|---|---|---|
| Chrome extension (`extension/`): the service worker, the side panel (an extension page) and the page script on Cliniko pages (flow 20) | Chrome's service-worker, extension-page and Cliniko-tab renderer processes | Sandboxed by Chrome; ID pinned `mbmhglgadhdohpgbmpbjnaifjagfdfid` (the developer build's own extension: `pecfiifdlmdbkifmjkbkeiaflpenfejd`, flow 24); host access `https://*.cliniko.com/*` only, no `tabs` permission |
| Native host (`scribe-host`) | Spawned by Chrome per connection | Runs as the logged-in Windows user |
| Recorder app (`scribe-app`) | Standalone PySide6 process (multi-screen: microphone / session / recovery / transcript / note / past sessions / practitioner / clinics / status); single instance per user enforced by a per-user lock file every instance must hold (`%LOCALAPPDATA%\ClinikoScribe\app.lock`, empty, held open with no sharing; unopenable → the app refuses to start; rounds 69–70; since the installation plan the SAME file for the installed app and the developer build, so only one of them runs at a time — flow 24), behind a named mutex that only refuses a normal second launch early; the Phase-3A note pipeline (compose → confirm → check → write), the practitioner-profile voice enrolment (flow 12) and the consented phrase learning (flow 13) run in-process here; its one network-capable module is the Cliniko client — reads and the one draft write (flow 18); it listens on one per-user named pipe for the native host (flow 19) | Runs as the logged-in Windows user |
| Model setup script (`scripts/setup-models.py`) | Separate explicit process, run once per machine BY THE USER from a normal terminal — for a source checkout only (the installed app's models come in its model pack, flow 23) | Runs as the logged-in Windows user; setup-time only, never at runtime |
| Prose-runtime install (`pip` over `desktop/requirements-ml-prose.txt`) | Separate explicit process, run once per machine BY THE USER from a normal terminal — for a source checkout only (the installed app is built with the runtime inside it, flow 9 (c)) | Runs as the logged-in Windows user; setup-time only, never at runtime — the app never installs, updates or checks for a runtime |
| Release build (`scripts/build-release.py`, `scripts/lock-build-requirements.py`, the `Release` workflow) | Build-time processes on a GitHub Windows runner or, for spikes and the model pack, the practitioner's own normal terminal (flow 9 (c)) | Build-time only; never on the clinic computer at run time |
| Installer (`ClinikoScribe-<version>-setup.exe`, Inno Setup) | Run once per install or upgrade by the practitioner, elevated with one administrator approval (flow 23) | Writes the install folder, an all-users Start-menu shortcut and HKLM only, nothing per user; makes no network connection; never launches the app |

## Flows

1. **Chrome ↔ native host (stdio, the ONLY browser transport).**
   Chrome spawns the registered host (`scribe-host.exe`, flow 5) and connects stdin/stdout pipes.
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
   NEVER a log destination (it carries only protocol frames). Since the
   privacy-professional-controls plan's Task 4.1 both processes replace
   Python's exception hooks: an uncaught exception reaches the log (and the
   console's stderr, when there is one) as ONE line,
   `uncaught_exception error_code=<type name>
   detail_code=main|thread|unraisable` (a thread's `SystemExit` is silent),
   never its message or traceback, and a failing log handler reports `--- Logging error (<type>)
   ---` on stderr only (flow 22, EXCLUSIONS).

3. **Desktop → Windows Credential Manager.** Durable secrets via `keyring`,
   keyed `ClinikoScribe/<clinic_id>` + secret name. Phase 1 stores only the
   transient self-test credential (`test/probe`), deleted by the test itself.
   Real Cliniko API keys are entered on the Clinics tab (the Cliniko workflow
   safeguards plan's Phase 2) and, at rest, live ONLY here, under
   `ClinikoScribe/<clinic_id>` / `cliniko_api_key` — stored only after
   Cliniko has validated them, deleted by the tab's Remove, overwritten by
   its Replace key. A Validate or Replace key reads the TYPED key (never
   this store); note verification (Phase 3) reads the stored one, once per
   logical call, on its worker thread, and so does the draft write, once
   per hop — twice per Write click (flow 18). Either way the client's own references go when the call
   ends — in memory only, and a still-live exception from the call keeps its
   frames (and so the key or token) referenced until it is dropped (flow 18).

4. **Session crypto.** AES-256-GCM keys from `os.urandom`; `destroy()`
   drops the in-memory key, making anything encrypted under it
   unrecoverable. UNWRAPPED keys exist only in process memory; since
   Phase 2 a DPAPI-wrapped copy lives on disk for the crash-recovery
   window (`key.dpapi`, flow 6) and encrypted artifacts persist under
   `sessions\<id>\` (flows 6–7) — deleting the wrapped key is the
   cryptographic deletion of those artifacts. Since the
   privacy-professional-controls plan two more DPAPI-wrapped key kinds live
   on disk, each with its own description the unwrap verifies: one per
   Past-sessions entry (`past_sessions\<id>\key.dpapi`, deleting it is that
   entry's cryptographic deletion) and one for the audit store
   (`audit\key.dpapi`) — flow 22.

5. **Registration artifacts (machine-local, outside the repo).**
   The INSTALLED app's Chrome link is the installer's: the host manifest
   `com.scribe.cliniko_host.json` beside `scribe-host.exe` in
   `C:\Program Files\ClinikoScribe`, referenced from
   `HKLM\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host`
   (flow 23). A SOURCE checkout (the developer build, flow 24) registers its
   own host with `scripts/register-native-host.py` (dev-only since the
   installation plan's Task 3.7): `%LOCALAPPDATA%\ClinikoScribe-dev\` holds
   the dev host manifest `com.scribe.cliniko_host_dev.json` and a copy of the
   venv's `scribe-host.exe`, referenced from
   `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host_dev`.
   Both contain paths and the pinned extension ID of their channel — no
   secrets. (The developer build's host folder is kept space-free as a
   conservative guard from the Phase-1 gate; a space alone is not Chrome's
   rule — the installed host links from `C:\Program Files\ClinikoScribe`,
   installation plan Task 0.2.) Chrome reads a per-user entry before the machine-wide
   one, so a per-user entry under the PRODUCTION name would shadow the
   installed link (threat model, "Installation", HKCU SHADOWING); the
   register script's `--unregister` also removes the old per-user
   production-name key and its two files in `%LOCALAPPDATA%\ClinikoScribe\`
   (`com.scribe.cliniko_host.json`, `scribe-host.exe`) that earlier builds of
   the script wrote — the installation's migration step. Since the
   privacy-professional-controls plan's Task 4.2 the script also writes three
   per-user Windows Error Reporting values (flow 22, EXCLUSIONS);
   `--unregister` removes them with the rest.

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
   or other display text; since the pilot plan (schema v2, flow 25) also the
   recording's mode, `normal` or `shadow` (a v1 record reads as `normal`; an
   unreadable one makes a recovered checkout shadow, and an Unreviewed
   adoption refuses it). AES-256-GCM under the session key, AAD
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
   like every other artifact, and is never copied into a Past-sessions
   entry; its consent time and version, `linked`, verification state and
   ids (never the patient id) are ALSO written into the session's audit row
   at Start, before the key (flow 22).
   Plaintext audio exists ONLY in transient capture/processing buffers —
   never on disk, never in logs. Deleting `key.dpapi` is the cryptographic
   deletion of the session (same-user boundary; NTFS unlink residual — see
   the threat model). The microphone screen's idle level monitor feeds the
   meter only; monitor audio is never stored. Accepted same-user
   deployment residual: a folder-redirected/UNC `%LOCALAPPDATA%` would
   place `sessions\` (and the model cache) on SMB storage — runtime
   assumes the local profile; refusing here would block recording
   entirely, unlike the model paths, which DO refuse UNC before any stat
   (cheap, report-only; the benchmark's model, audio and worker paths too
   since round 27, and its temporary folder since round 28, in every
   separator form `install_layout.is_unc_path` normalises; an extended
   `\\?\C:\…` drive path counts as local, every other device form as
   network).

7. **Local transcription (Phase 2, in-process, zero network).** On Finish,
   chunks are decrypted streamwise → silero-VAD segmentation → faster-whisper
   (CTranslate2, model `medium` per D6 as REVISED at the Step 13 gate;
   `small` stays the visible fallback when the medium snapshot is absent)
   with word timestamps, transcribed in packed ≤30 s windows (a lone VAD
   segment longer than the budget is its own oversized window) →
   uncertainty marks (low-confidence words, numbers, names) → 2-speaker
   labels → `sessions\<id>\transcript.enc`, written atomically under the
   SAME session key. The transcript renders in a display-only view; the
   explicit Complete action runs fsync → decrypt-verify → (non-mock) the
   Past-sessions entry written, verified and published under its own key →
   key deletion → directory removal (flow 22).
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
   Where it is (installation plan D5, `install_layout.models_root`): for the
   INSTALLED app, `C:\Program Files\ClinikoScribe\models\` — copied there
   from the model pack by the installer, each file checked against the
   manifest's SHA-256 before and after the copy (flow 23), and read-only to
   standard users; for a SOURCE checkout (the developer build, flow 24),
   `%LOCALAPPDATA%\ClinikoScribe-dev\models\`. (Before the installation plan a
   source run used `%LOCALAPPDATA%\ClinikoScribe\models\`; the practitioner
   copies it to the dev folder (Task 2.6) and deletes the old copy at Phase
   P, after the installed app's models verify.) Contents: `silero-vad\silero_vad.onnx`
   (~2 MiB) plus CTranslate2 whisper snapshots (runtime default
   `whisper\medium`, ~1.43 GiB, with `whisper\small` ~465 MiB as the
   visible fallback; with all four benchmark candidates those come to
   ~3.0 GiB), for voice enrolment (practitioner-profile plan),
   `speaker-embedding\wespeaker-voxceleb-resnet34-LM.onnx` (~25 MiB; promoted
   from the practitioner's digest-verified candidate at that plan's Task 0.6,
   2026-09-15) and, for the prose styles (note-learning-and-styles plan Phase
   4), `language-model\Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (~2.33 GiB; size
   and SHA-256 verified again at every load, flow 17) — so the whole cache is
   ~5.3 GiB with all four benchmark candidates and the language model (of the
   whisper models, the installed app's model pack holds only `medium`; it
   also carries the speaker model's CC BY 4.0 attribution notice). Static
   program data, no clinical content. Written ONLY by flow 9 (a source
   checkout) or the installer (flow 23); runtime processes never write
   here. The speaker model and the language model are re-verified against
   their pinned SHA-256 at every load; silero and whisper are not. The hardware benchmark additionally synthesizes its fixed
   NON-CLINICAL sample script to a transient plaintext WAV (Windows SAPI)
   inside an auto-deleted temp directory — no clinical content ever takes
   that path. Since the installation plan (D11, Task 2.5) the same hardware
   check also times the prose stage in-process over fixed NON-CLINICAL lines
   held in memory (`ui/hardware_check.py`), through the Note tab's one loaded
   language model; nothing is written, and its report holds timings only,
   never text the model wrote. A packaged build runs whisper's timing by
   starting itself as the worker (`scribe-app.exe --benchmark-worker …`); a
   source checkout starts `python -m scribe_desktop.benchmark`.

9. **The TWO setup-time network steps (separate processes the user runs;
   the app's own network use is flow 18 alone) — plus, since the installation
   plan, the build-time steps in (c).**
   (a) `scripts/setup-models.py`. Explicit one-time HTTPS downloads into
   the model cache of a source checkout (`ClinikoScribe-dev\models`, flow
   24) or, with `--root DIR`, into a staging folder for the release model
   pack (nothing under `%LOCALAPPDATA%` is then touched): silero-vad from its pinned GitHub release tag
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
   (c) BUILD TIME (installation plan D7, Tasks 3.1–3.6; none of it on the
   clinic computer at run time, and none of it run yet). `scripts/lock-
   build-requirements.py` downloads one Windows wheel per dependency from
   PyPI to write the hashed `desktop/requirements-build.txt`, pinned to the
   versions of an environment already proved (practitioner-run, normal
   terminal). `scripts/build-release.py`'s build installs that lock and the
   prose wheel (`--require-hashes`) into a clean build environment, takes
   PyInstaller from a git clone at a pinned tag that must match its pinned
   commit, and runs `npm ci` for the extension. The `Release` workflow does
   the same on a GitHub Windows runner (every action pinned to a commit, no
   restored cache), after downloading Inno Setup 6.7.3 and checking its
   SHA-256; the extension is built into the bundle BEFORE the bundle audit,
   so no npm code runs after it. It then uploads `setup.exe`, `SHA256SUMS.txt`,
   `BUILD-INFO.txt` and `models-manifest.json` and records a build-provenance
   attestation with GitHub (Sigstore). `build-release.py --write-manifest`
   and `--model-pack` read and copy local model files only — no network.
   None of these carries clinical data: they read the repository, the
   package indexes and the model files.

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
    SESSION's copy of the note along with the audio and transcript (same custody
    and retention posture as the audio and transcript — the 24 h cap governs
    unprotected recovery stores; see the retention schedule). Since the
    privacy-professional-controls plan a non-mock Complete first copies the
    note (unless the path deletes it), the transcript and the generated note
    into the session's Past-sessions entry under the entry's own key, and Save
    also writes `saved-provenance.enc` (the saved note's model ids and digest,
    no text) and the review writes `generated.enc` (the first body shown,
    replaced by each regeneration) under
    the session key (flow 22).
    Inside the app, the plaintext note and the full transcript coexist in memory
    only for the review window (threat model, Phase 3A §3) and, since the
    privacy-professional-controls plan, while an opened Past-sessions entry is
    on screen (flow 22, THE TAB), and the app never
    logs the note and never writes it outside the encrypted stores (the
    session's, then its Past-sessions entry's) — with TWO
    exceptions, both the clinician's own action on a ratified note: the Copy
    below, whose clipboard copy outlives the review and which the app does
    not hold; and, for a linked recording, "Write draft to Cliniko", which
    sends the note's text to Cliniko's API as the content of the open draft
    treatment note (flow 18), after which Cliniko holds it. The write keeps a
    record of its own beside `note.enc`, `write.enc` (ids and digests only,
    flow 18), and every Complete — the one after a confirmed write included —
    removes the session directory after the key. Copy-to-Cliniko ships enabled since the
    practitioner's 2026-09-27 decision and is offered only for a fully ratified
    note; the copied text goes to the Windows clipboard by the clinician's own
    action and is outside the app's custody from there. Since Task 8.2 every
    copy of note text — the Copy button, and the keyboard's Copy or the
    context menu's Copy over the ratified note panel's selection, and (since
    the privacy-professional-controls plan) the Past sessions tab's "Copy saved
    note", and (since pilot review round 22) the inline line editor's Copy and
    Cut of the selected text of a line being typed over, which needs the copy
    flag but is not gated on ratification — carries three registered Windows
    formats
    (`ExcludeClipboardContentFromMonitorProcessing`,
    `CanIncludeInClipboardHistory` = 0, `CanUploadToCloudClipboard` = 0) that
    Windows clipboard history and cloud clipboard sync honour, so the copy is
    not kept in history or uploaded. They do NOT stop any same-user process
    reading the current clipboard, a third-party clipboard manager may ignore
    the first of them, the note stays on the clipboard until something
    replaces it and nothing is cleared; a drag of the selected text out of the
    ratified note panel is Qt's own (no formats, no clipboard — the text lands
    where it is dropped), while the line editor starts no drag. No list or
    combo box in the app copies its rows (rounds 23–24: every list's and
    combo-box popup's Copy shortcut does nothing, so a patient's name in Past
    sessions, Recover or Unreviewed, or a transcript line's first words in the
    Note tab's "Line:" choice, never reaches the clipboard that way) — see the
    threat model, Phase 3A surface 4, and the
    retention schedule. THE SHADOW
    BRANCH (pilot plan, flow 25): for a shadow recording neither exception
    exists — every Copy route, the inline line editor's Copy, Cut and drag,
    and the placement itself refuse, the note panel is display-only (nothing
    to select or drag), and "Write draft to Cliniko" is refused before
    anything is reserved or sent; its note leaves the session only into its
    Past-sessions entry.

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
    widget (`ui/transcript.py`; a post after the view closed is dropped, and
    so is one carrying an earlier Start's token — round 57 SEC-022: a window
    the retired worker posted never reaches the next patient's view or the
    phrase rules; the view is cleared on the Session screen's Discard and replaced wholesale by
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
    chunks intact and is retried by the next Discard. Since installation plan
    round 40 LOW-002 that wait runs on a `TaskThread`, with the Session
    screen's controls, Chrome's commands and "Open for review" held until it
    ends; it is never retried automatically. The same verdict gates
    the three Complete paths and retirement on a new Start (threat-model
    surface 11). A load failure, `fell_behind`, a worker error or a drain error
    falls back to the batch stage (flow 7) with its reason on the Session
    screen. No new logging channel: the one new record is
    `live_transcriber_stop_timeout` (session id and state only). Since
    installation plan round 35 MED-001 the stack's imports (numpy,
    onnxruntime, faster-whisper) are warmed once per process at app start on
    their own thread (`ml_warmup.py`: modules only — no model file, no audio,
    no session, no connection; offline switches asserted first; logged as
    `ml_warmup` with state, duration and, on a failure, the type name).
    While it runs every Start (Session tab and Chrome) is refused as
    "still getting ready" before anything is made — no audit row, no session
    folder, no key (round 36 MED-001, the practitioner's option (b)) — for
    at most 60 s from its start; a Start admitted after that bound while it
    still runs attaches NO worker (logged `live_transcriber
    state=not_attached` with the session id) and the session takes the batch
    path at Finish, the empty live view saying why (the warm-up's imports
    still run beside such a recording — the threat model's surface 11
    residue).
    A capture failure is logged as `capture_failure` with the exception's
    type name and a fixed detail word (`audio_capture.CAPTURE_DETAIL_CODES`),
    never its message. Flows 15–16
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

18. **Cliniko API reads and the one draft write (Cliniko workflow safeguards
    plan, D9; client BUILT at Task 1.1, 2026-09-27; the draft write BUILT by
    the cliniko-draft-write plan, 2026-09-29; memory only, except the write's
    own record `write.enc`).** `scribe-app` → HTTPS →
    `https://api.<shard>.cliniko.com/v1/...` through `cliniko_client.py`, the
    app's one network-capable module. Reads (`GET`, no body): `/user`,
    `/practitioners?q[]=user_id:=<id>`, `/settings/public`, `/settings`,
    `/treatment_notes/<id>`, `/patients/<id>`, `/bookings/<id>`, and
    `/treatment_note_templates/<id>` — since D15 (2026-09-30) read only by the
    practitioner-run probe's test write, never by the app. The ONE write: `PATCH
    /treatment_notes/<id>` with a JSON body whose only top-level key is
    `content` (THE DRAFT WRITE below); the transport refuses every other
    method, path, body and header set before connecting. WHAT LEAVES the machine: the clinic's API key (HTTP Basic
    username, inside TLS), the requested ids in the path (digits only,
    validated), the practitioner's contact email in the required
    `User-Agent: Clinic Scribe (<email>)` (refused on CR/LF or a failed shape
    check), and — for a write only — the draft's content: the note's own
    re-read content with the ratified note's text added to the matched
    answers (below any answer already there — D15).
    WHAT RETURNS: the key user's role and practitioner record, the
    account subdomain, for a note its draft state, links (patient,
    practitioner, booking, template) and content, for the probe alone a
    template's sections, questions and default answers, the patient's record (the
    display name) and the booking's time; for a write, a status (and
    Cliniko's echo of the note, which nothing keeps). Every answer is held in memory
    only: the client writes nothing to disk, logs nothing and returns the parsed JSON
    object to its caller; only a 200's body is read — and, for the write, a
    422's, reduced at once to fixed field-name categories (any other status is
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
    keep its frames, and so the key or Basic token, the path, ids,
    response bytes and, for the write, the draft it was sending, referenced
    in memory until it is dropped (threat-model residue (6)). CALLERS:
    `clinics.py`, `draft_write.py` and `encounter.py` are the only app
    modules that import the client, each confined to the client names and
    methods pinned for it (`test_cliniko_client.py` `TestConfinement`,
    `TestWriteCallSites`). A Validate or Replace
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
    log or file holds and Phase 3 showed nowhere — save that a session's
    name is written, at its Complete, into its Past-sessions label (flow
    22); the note's content and
    the rest of each answer are dropped with the call. A checkout's outcome
    is dropped when the checkout ends. The practitioner-run feasibility script
    `scripts/probe-cliniko.py` (Task 1.3) is a separate process built on the
    same client that prints structure only — never a name, id value, answer
    text or the key; with no argument it only reads, and its separately
    typed `--test-write` / `--test-write-final` modes (the draft-write plan's
    Task P.1, run once per clinic on a dummy patient's note) write a test
    marker through the client's own write method, after a typed `yes`. Since Task 4.5 the Chrome bridge (flow 19) is a second
    trigger for the same call: a note report from the bound Chrome tab on an
    allow-listed host, and — once per new pipe connection — the linked live
    session's own note; the display value then reaches the pipe's `state`
    and the Session screen, for the verified note only (flow 19). The
    bridge's calls start at least one second apart, and for 60 s after a
    429 that clinic's bridge checks (Chrome reports, a reconnect's re-check,
    a clinic change) make no call and read `unverified_offline` until the
    note is checked again (round 57 SEC-009) — fewer calls, never a new
    trigger. That 60 s cooldown is one per-clinic latch shared with the
    checkout re-verification and the draft write (draft-write D13): a 429 any
    of the three sees makes the others wait too.
    THE DRAFT WRITE (cliniko-draft-write plan; threat model, "THE DRAFT
    WRITE"). Trigger: ONLY the Note tab's "Write draft to Cliniko" click on a
    saved, ratified note of a LINKED recording (live, or an Unreviewed one
    opened for review) — never at startup, idle, on a timer, a reconnect or a
    clinic change; a desktop-started (unlinked) recording and a note from the
    test provider never write, and neither does a SHADOW recording (pilot
    plan, flow 25: the click is refused as `shadow_session` right after the
    in-flight and stale checks, before any reservation, read or request, and
    recorded in the audit row like any pre-send refusal). Per click, two client calls on worker
    threads, each reading the clinic's key from Credential Manager once:
    hop 1 — ONE request, `GET /treatment_notes/<id>` (the click's own
    verification of the note; since D15 no template is read); hop 2 — the
    `PATCH`. In between, on the GUI thread, the app matches the profile to
    the note's own content, APPENDS to each matched question it writes — an
    empty answer takes the app's text; any other answer is kept byte-for-byte
    with one empty line and the app's text below it; an answer it cannot
    read refuses the write (D15) — builds the body from the re-read content
    with only the matched answers set, and writes the `attempting` record.
    What it KEEPS: in memory, for that click only — the note's re-read
    content until the body is built, the body until hop 2 returns; nothing of
    Cliniko's answers is logged or written. At rest, `sessions\<id>\write.enc`
    — one document under the session key (AES-256-GCM, AAD
    `write:<session_id>`), rewritten atomically at each step (schema v2): the
    attempt number and times, the template profile's target ids, a SHA-256 of
    the saved note, per written target a SHA-256 of its normalised expected
    final answer and of its normalised answer as read, a SHA-256 of where
    they were written, the body's SHA-256 and the outcome (`attempting` /
    `written` / `refused` + reason / `unknown`) — ids and digests only, never
    note text, a Cliniko answer or a Cliniko id. It lives and dies with its
    session (retention schedule); its transitions and any pre-send refusal
    code are also recorded, best-effort, in the session's audit row
    (attempts, last outcome, last refusal, written-at — flow 22).
    After the clinician has seen the written draft in Chrome and pressed
    Complete, the session's Past-sessions entry is published, its key is
    destroyed and its directory removed: the draft in Cliniko is the clinical
    record, the entry keeps the transcript and notes for the practitioner's
    retention setting, and the audit row keeps the write's outcome — the
    write record's digests are gone.

19. **Native host ↔ `scribe-app` over a named pipe (Cliniko workflow
    safeguards plan D2/D4; BUILT at Tasks 4.1, 4.2, 4.4 and 4.5,
    2026-09-27; memory only).** Local IPC, not a network endpoint: the
    no-sockets legs poll the app with the pipe listening AND a client
    connected (`test_scribe_app_with_the_chrome_link_open_has_no_sockets`),
    and a real host process relaying to a real app over it
    (`test_host_relays_to_an_open_app_pipe_with_no_sockets`).
    The app creates `\\.\pipe\ClinikoScribe-<user SID>` (the developer
    build's is `\\.\pipe\ClinikoScribe-dev-<user SID>`, flow 24) after its
    single-instance guard (`pipe_server.py`): first instance only (a held name
    is refused, never shared — the Session screen then says the Chrome link is
    unavailable and desktop recording still works), one instance, remote
    clients rejected, a protected DACL granting only the current user, and a
    Medium no-read-up integrity label, so no lower-integrity process can open
    it (round 57 SEC-014). If the server stops serving for any reason but the
    app's own stop, the current connection is reported lost and the Session
    screen shows the Chrome link unavailable (round 57 SEC-017); a frame for
    one connection never reaches the next (round 57 SEC-016).
    Its client is the native host (Task 4.4), which relays flow 1's v2
    messages, and which connects only after VERIFYING the server — the same
    Windows session, the same user, exactly that DACL, and the user as the
    pipe's owner, which the app sets explicitly (round 57 SEC-013; Task 4.3, decided
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
    when that session ends (and the name a Verified live re-verification of
    that session found, kept for the Past-sessions label only — never sent to
    Chrome — and dropped when the session ends); the tab the linked live session is bound to (a
    tab number, forgotten on every new connection or disconnect and when the
    session ends), its block (a reason code, while it is paused) and a
    clicked "Resume previous" (a time, lapsing after 30 seconds); the hotkey's
    status and the session id a warning was raised on (dropped when that
    recording finishes or ends); and the
    last snapshot sent, for change detection. The main window keeps the
    Unreviewed reminder index (Task 5.3: clinic id, note id and session id
    per retired linked queued session — and per recovered linked session
    whose view is replaced without a Complete or Discard, from its
    checkout's record (H1 round 53) — never persisted; rebuilt at app start
    from each Unreviewed session's `encounter.enc`, Task 5.5), which loses an
    entry when that session is completed, discarded, expires or is opened
    for review.
    Nothing is written to disk — except that a Complete writes the display
    name the app holds for that session into the Past-sessions entry's
    encrypted `label.enc` (flow 22; H3 round 35) — and nothing is logged beyond a connection's
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
    `command`s for the panel's and the block's clicks — the block's only
    Resume previous and Finish previous, never a discard (round 57 SEC-003).
    WHAT THE APP'S `state`
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

21. **RETIRED 2026-09-30 (cliniko-draft-write D15).** The own template
    defaults file under `%LOCALAPPDATA%\ClinikoScribe\config\template_defaults\`
    is no longer read by anything (the loader, the Clinics tab's setting and
    "Check file" are gone); a practitioner's file may stay on disk, unread.

22. **Audit record, Past sessions and exclusions (privacy-professional-controls
    plan, PLAN.md Phase 6; BUILT 2026-10-01; in-process, zero network, GUI
    thread only).**
    - AUDIT. At Start, BEFORE the previous session is retired and before any
      file of the new one exists, `AuditLog.begin` writes the session's row:
      `%LOCALAPPDATA%\ClinikoScribe\audit\YYYY-MM\<id>.enc` (the
      practitioner's local month), AES-256-GCM under the one audit key
      (`audit\key.dpapi`, DPAPI current-user, description `ClinikoScribe audit
      key`), AAD `audit:<id>`. Content: the session id and local date, origin,
      the consent time and text version, `linked`, the verification state, the
      app's clinic id and the Cliniko practitioner, user (from the clinic
      registry), booking and treatment-note ids, and since the pilot plan's v2
      the recording's `mode` and the app's `app_version` (flow 25) — never the
      patient id, a name or any text. A failed write refuses Start. Later, best-effort and never
      blocking: the draft write's transitions (`MainWindow._store_write_record`)
      and pre-send refusal codes (`AuditLog.record_write_refusal`, from
      `_on_write_requested` / `_prepare_attempt`), Complete's model and provider tokens
      and outcome (from `CompletionFacts`: the transcript's model ids, the
      generated note's from `generated.enc`, the saved note's from
      `saved-provenance.enc` only when its digest names the completed note),
      Discard, expiry and `orphan_gc` (from the sweep, by session id only —
      `encounter.enc` is never decrypted for it), and the Past-sessions
      events. Kept 7 years by month; pruned at start-up and every 24 h. An
      unreadable key refuses every Start until "Start a new audit record"
      renames the whole store aside (`audit.unreadable-…`) unread.
    - EXPORT. "Export audit record (CSV)" on the Past sessions tab writes every
      readable row (no event codes; a spreadsheet-formula guard on every cell)
      as UTF-8 CSV with a byte-order mark to the path the practitioner picks in a save dialog
      (starting in Documents). The file is NOT encrypted and leaves the app's
      custody: no name or text, but Cliniko ids that identify the appointment
      to anyone with that Cliniko account. Its temporary file is a fresh name
      in that folder (`.clinic-scribe-*.tmp`), removed on every path unless
      Windows refuses the removal (H3 round 35 SEC-004).
    - KEEP AT COMPLETE. The review writes `sessions\<id>\generated.enc` (the
      first note body shown — a regeneration replaces it — its provider, style and render-time model ids;
      session key, AAD `generated:<id>`); Save writes
      `sessions\<id>\saved-provenance.enc` (the saved note's model ids and
      SHA-256, no text) before `note.enc`. At a non-mock Complete,
      `complete_session` re-encrypts the transcript, `generated.enc` when
      present and readable and `note.enc` when present and not deleted by the path, byte
      for byte, under a FRESH per-entry key into `past_sessions\.staging\<id>\`,
      with `label.enc` (AAD `past-label:<id>`: dates, linked / desktop /
      unknown, the clinic id, the patient's display name or none, which
      notes are held and, since the pilot plan's v2, whether it was a shadow
      recording). The name comes from memory at the Complete click,
      matched by session id (the Chrome bridge's verified Start display, the
      name a Verified live re-verification of that session found, or a
      recovered or adopted checkout's Verified result); it was
      never persisted at Start. The staged entry is verified through its own
      key read back from disk, moved to `past_sessions\<id>\` with a
      `pending` marker, and only THEN is the session key deleted; the marker
      and the session directory are removed after it. Audio, `encounter.enc`,
      `write.enc` and `saved-provenance.enc` are never copied. Discard (live
      and `discard_recovered`), the recovery list's Discard, the sweep's expiry, a dead key's
      `orphan_gc` and a mock Complete (which keeps nothing) remove any
      unfinished entry for the id, key first, BEFORE the source key goes — a
      removal that fails, or an entry path that cannot be inspected, keeps the
      source key; reconciliation (start-up and every sweep tick) commits
      a `pending` entry once its source key is confirmed absent, and staging
      leftovers are cleaned at every start-up and tick. A linked FOLDER
      (symlink or junction) where a session, an entry, a staging copy or an
      audit month would be is never followed: not swept, keyed away,
      discarded, listed, read, written through or pruned (H3 round 35
      SEC-002/SEC-003). The three roots themselves are not checked, and a
      linked audit row FILE is read like any row (its AAD binds it to its
      session id).
    - THE TAB. Opening the Past sessions tab decrypts each entry's
      `label.enc` to list date + name ("Patient hidden" under Hide names);
      opening an entry decrypts its notes AND its transcript into memory (the
      notes shown at once, the transcript only behind "Show transcript"), in
      `NoTextInteraction` panels; leaving the tab drops all of it. "Copy saved note" places the kept SAVED note on the Windows clipboard
      through the one placement with the three history- and sync-excluding
      formats (flow 10) — never for an entry marked "(shadow recording)" or
      one whose label cannot be read (flow 25). Delete now (two clicks; worded for a recording made
      in error only) and the retention sweep (start-up, then at most hourly
      while the app runs; nothing under "Until I delete them"; 7 years
      minimum — a shorter window is refused before any read) delete the
      entry's key first, then its files, and update its audit row
      (`deleted_early` / `expired`). Settings: `config\past_sessions.json`
      (`retention_days` — null or 7 years; a removed shorter value loads as
      7 years — and `hide_names`).
    - EXCLUSIONS. For a source checkout (the developer build),
      `scripts/register-native-host.py` (run from a normal
      terminal) writes and reads back `pythonw.exe`, `scribe-app.exe` and
      `scribe-host.exe` = DWORD 1 under `HKCU\Software\Microsoft\Windows\
      Windows Error Reporting\ExcludedApplications`; `--unregister` removes
      them. For the installed app the installer writes `scribe-app.exe` and
      `scribe-host.exe` = DWORD 1 under the same key in HKLM, plus the
      backup and snapshot values for live sessions and logs (flow 23). At
      every start-up, before the window, `app.main` marks the channel's data
      folder (`%LOCALAPPDATA%\ClinikoScribe`, or `ClinikoScribe-dev`) and its
      folders not-content-indexed (best effort, folders only, links skipped)
      and runs READ-ONLY checks — the data folder's resolved location
      (OneDrive, a network path or drive, the roaming profile), the
      channel's WER values (HKLM then HKCU for the installed app, HKCU for a
      source checkout) plus the running program's name, and, installed app
      only, the two HKLM backup and snapshot values — whose warning lines
      show on the Status and Past sessions tabs and are logged by code only;
      nothing is moved and recording is never refused. Both processes install the type-name-only exception hooks
      (flow 2). Every attribute, drive-type, environment, path-resolution and
      registry call goes through one injected layer, which tests replace (C6);
      the folder walk itself uses `os.scandir` and the link checks directly.

23. **Installer → install folder and HKLM (installation plan D1, D5, D6, D8,
    C3, C4; `packaging/scribe.iss`; BUILT, compiled with Inno Setup 6.7.3;
    run on this computer at Phase P, 2026-10-03 → 2026-10-04).** No clinical data and no network
    connection. Run elevated by the practitioner (one administrator
    approval), after checking the download (`gh attestation verify`,
    `Get-FileHash` against `SHA256SUMS.txt` — `docs/release/pilot-builds.md`).
    It first refuses while `scribe-app.exe`, `scribe-host.exe` or
    `chrome.exe` runs (or when it cannot check), for any folder but
    `C:\Program Files\ClinikoScribe`, and — when the installed models do not
    already match — when the model pack beside `setup.exe` is missing or any
    of its files fails the manifest's SHA-256; a refusal changes nothing.
    WRITES: the packaged program into `C:\Program Files\ClinikoScribe`
    (`scribe-app.exe`, `scribe-host.exe`, `_internal\`, the host manifest,
    the release extension in `extension\`; an upgrade clears `_internal\` and
    `extension\` first); the models into `{app}\models\` (every copy checked
    again, a damaged one deleted where Windows allows it — one that could not
    be removed is named — the Finish page saying the app is NOT completely
    installed and Setup exiting 9); a Start-menu shortcut for all users; Inno's own
    uninstaller (`unins000.*` in `{app}`, its HKLM Uninstall entry, which
    holds whether this installer set the policy); and in HKLM only — the
    Chrome link for `com.scribe.cliniko_host`, the WER values for its two
    programs, the `ClinikoScribe` value under `BackupRestore\FilesNotToBackup`
    and `\FilesNotToSnapshot` (`$UserProfile$\AppData\Local\ClinikoScribe\
    sessions\* /s` and `...\logs\* /s`, a best-effort request — threat model
    residue (g)), and, only when ticked, the clinic-only Chrome policy
    `NativeMessagingUserLevelHosts` = 0. It writes NOTHING per user and
    never launches the app. Its own log is off (`SetupLogging=no`).
    UNINSTALL removes the program, `{app}\models` and those HKLM values (a
    policy value only if this installer set it) and never
    `%LOCALAPPDATA%\ClinikoScribe`, which it says stays. The installed app
    then reads the same data folder as before — the installation changed no
    persisted schema (the pilot's 0.2.0 schema v2 is flow 25's).

24. **The developer build (installation plan D2–D4, C8; BUILT).** Any source
    checkout (not frozen) is the DEV channel; nothing selects it but
    `sys.frozen`. Its data AND models live in
    `%LOCALAPPDATA%\ClinikoScribe-dev` (the same layout as the production
    folder), its Chrome host is `com.scribe.cliniko_host_dev` (registered per
    user, flow 5), its extension is the dev build (`npm run build -- --mode
    dev` → `extension/dist-dev`, its own key `extension/key-dev.pem`, its own
    ID; loaded in a SEPARATE Chrome profile) and its pipe is
    `\\.\pipe\ClinikoScribe-dev-<user SID>`. It reads and writes nothing in
    the production folder except the shared `app.lock` (the Components
    table: one app at a time across both channels) and, through
    `register-native-host.py --unregister` only, the two old registration
    files named in flow 5. Its "Write draft to Cliniko" is refused before any
    read or request unless the Status tab's "Allow Cliniko writes from this
    developer build" is ticked, saved as `config\dev.json` in the dev folder
    (`{"schema_version": 1, "allow_cliniko_writes": bool}`, default false);
    note verification and the Clinics tab's Validate still call Cliniko
    (flow 18). It SHARES with production the Credential Manager namespace
    `ClinikoScribe/<clinic id>` (entries apart only because clinic ids are
    random per data folder; the self-test's `test` entry is common) and the
    DPAPI key descriptions — the same Windows user either way (threat model,
    "Installation").

25. **Shadow mode (pilot plan D1–D5, D13; BUILT 2026-10-04; in-process, zero
    network).** The Status tab's "Shadow mode (pilot)" box writes
    `config\pilot.json` (`{"schema_version": 1, "shadow_mode": bool}`, at most
    4 KiB, no patient data) in the channel's data folder through the config
    folder's atomic write path. It is READ only at each Start click (desktop
    or linked) and by the Status and Session tabs; absent = off, present but
    unreadable or invalid = ON (named on the Status tab). At Start the mode is
    fixed for the recording and goes into the in-memory session,
    `encounter.enc` (flow 6) and the audit row (flow 22). Every rebuild takes
    it from the record one of the three authorised readers already decrypts
    (a recovery checkout or an Unreviewed adoption; the third reader, the
    reminder rebuild, needs no mode); an unresolved mode is shadow.
    For a shadow recording: no note text reaches the clipboard (every Copy
    route, the line editor's Copy and Cut, and the one placement refuse;
    the note panel is display-only — flow 10's shadow branch); nothing is sent
    to Cliniko (flow 18 — the click is refused before any reservation, read or
    request); a Save writes no learned phrase or rule and replaces no learned
    wording (flows 13 and 15 do not run; a demotion still does); and at
    Complete its Past-sessions entry's label records `shadow` — forced from the
    live session's mode, whatever label the caller built (review round 22) —
    so "Copy saved note" is refused for it (flow 22). Audio, transcript, notes, the entry and
    the audit row otherwise follow the normal flows. Chrome is not told the
    mode (no protocol change).

26. **The validation harness (pilot plan Phase 2, D8–D10; BUILT 2026-10-04 → 2026-10-07;
    developer build only, zero network).** Two practitioner-run tools,
    started from a normal terminal in a source checkout (both refuse a
    packaged build):
    - BUILD. `scripts/build-validation-set.py <scripts> <set-folder>` reads
      the repository's invented encounter scripts (`validation/scripts/`),
      lists the installed Windows (SAPI) voices, speaks each line into a
      temporary WAV under `%TEMP%\scribe-validation-set-*` (removed after each
      turn), resamples it with PyAV, mixes the turns with seeded noise and
      overlap, and writes `<id>.wav` (16 kHz mono PCM16), `<id>.txt` (the
      timed label track), a byte-exact `<id>.json` and the ownership mark
      `<id>.built` into the set folder — which it refuses inside the
      repository; each file is written to `<name>.tmp` and moved into place.
      A script file not named as an encounter id writes nothing and is
      reported without its name; a set folder inside either app data folder
      is refused (round 26).
      Role-play recordings (mock consultations, Task P.2) are added to the
      same folder by hand with their own scripts and label tracks — for the
      run of record the synthetic set is built into the role-plays' one
      folder (decision 3.6), or any copy of them made for a run is deleted
      after it; the enrolment WAV stays in a subfolder (only the top level is
      read), and the synthetic files are deleted from the folder after the
      run.
    - RUN. `scripts/run-validation.py <set-folder> --config <folder> --rule
      <file>` applies and asserts the offline environment, reads the rule
      file, the explicit config folder (never the app's own) and the models,
      and for each encounter reads its WAV, label track and script, then
      transcribes it in a temporary encrypted session store
      (`%TEMP%\scribe-speaker-eval-*\<id>\`: `key.dpapi`, `audio.enc`,
      `transcript.enc`, under a fresh DPAPI-wrapped key — the
      speaker-measurement store, retention schedule) torn down key-first on
      every path; the transcript document, the composed and finalised note
      and the metrics live in memory for that encounter only. It reads the
      commit from `.git` and hashes `packaging/models-manifest.json`, and
      prints a text-free Markdown report (ids, numbers, flags, closed
      vocabularies) to standard output, which the practitioner may redirect
      to a file. It reads no voice profile, and writes no audit row, no
      Past-sessions entry and nothing into either data folder. A run stopped
      with Ctrl+C prints no report and no traceback — one fixed line naming
      the temporary folder and the `scribe-speaker-eval-*` prefix for a
      left-over store (which may still hold its key) to delete.

## Explicit non-flows

- No application-generated plaintext clinical content at rest — the
  clinical artifacts this app produces (audio, transcripts, and the composed
  note `note.enc`, flow 10) exist on disk ONLY encrypted under per-session keys
  inside `sessions\<id>\`, beside `encounter.enc` (ids, flow 6) and the draft
  write's record `write.enc` (ids and digests, flow 18) — and, since the
  privacy-professional-controls plan, ONLY encrypted under per-entry keys
  inside `past_sessions\<id>\` (the kept transcript and notes, and the label
  with the patient's name), plus the content-free audit rows encrypted under
  the audit key (flow 22). The ONE plaintext export is the audit CSV, which
  holds no text or name but Cliniko ids, and lands only where the
  practitioner saves it (flow 22). Config files (flow
  11) are a SEPARATE,
  operator-authored plaintext class: INTENDED as clinician-authored non-patient
  boilerplate, but that is an operational rule the loader cannot enforce
  semantically (it validates structure only), so it is NOT a content guarantee —
  whatever a clinician hand-edits in is retained verbatim. The app itself
  writes TWO things into that class, both by consent and both reviewable and
  deletable on the Practitioner tab rather than guaranteed non-clinical:
  (1) a learned phrase (flow 13): two to four words from the start of a line
  the PRACTITIONER said and added or moved during review — structurally never
  a patient's line, and shape-filtered against names, numbers, dates and
  medication names, but the filter cannot judge meaning; (2) a learned rule
  (threat-model note-learning surface 13): its trigger is taken from the
  practitioner's OWN utterance through the same refusal filter
  (`refuse_learning_candidate`), and its wording is text the practitioner
  TYPED over a line, through the narrower `refuse_typed_wording` — numbers,
  dates and medication names refused, and NO name check (D11) — written
  only on the Note tab's Save into `autofill_rules.json`, with its metadata
  sidecar `autofill_rules.learned.json` (retention: the learned-rules row).
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
  `scribe-app`'s calls to Cliniko's API (flow 18) — reads, and the one draft
  write, which follows only a "Write draft to Cliniko" click — and none at
  startup or idle — a call follows only a practitioner action, a note
  report from Chrome, or a new Chrome link connection while a LINKED
  recording is in progress (its own note is re-checked, with or without a
  Cliniko tab open — round 54 LOW-055), so an app started while Chrome
  shows a Cliniko treatment note verifies it once that report arrives, and the no-sockets
  legs measure startup and idle with no Chrome link (no-sockets integration test on host and app, plus offline
  env kill-switches set and asserted; the during-capture/during-transcription
  poll and the network-stubbed transcription test landed with Step 13, and the
  manual completion gate's independent monitor run passed 2026-08-02; since
  the note-learning plan's Phase 4 the poll also runs inside a prose
  generation). No other destination: the client's host is built only from a
  documented Cliniko shard, and no other module may import a network module
  (flow 18). Model downloads and the prose-runtime install happen only in the
  separate setup-time processes (flow 9), the release build's network use
  only at build time (flow 9 (c)), and the installer makes no connection
  (flow 23).
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
  `unrecognised_shorthand` beside it (Phase 3, flow 16), and — since the
  privacy-professional-controls plan — the audit and archive markers
  (`past_session`, `note_provenance`, `consent_confirmed_at`,
  `generated_text`, and the patient-identifier names), so a stray
  repr or `model_dump` of a note model, of the practitioner's profile, of a
  sample note or style draft, of an audit row or of a kept generated note is
  dropped by the last-line filter. An uncaught exception logs its type name
  only (flow 2). Neither the note pipeline nor the profile
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
- Log/temp locations are user-local. Since the privacy-professional-controls
  plan the app marks its data folder not-content-indexed and WARNS (never
  refuses) at start-up when that folder resolves inside OneDrive, onto a
  network drive or into the roaming profile, and the app's programs are
  excluded from Windows Error Reporting (per user by the register script for
  a source checkout; machine-wide by the installer for the installed app —
  flow 22). Since the installation plan the installer also asks Windows
  backup and snapshot tools to leave out the installed app's live sessions
  and logs — a best-effort request that not every tool honours, covering
  nothing else in the data folder (flow 23; threat model residue (g)); a
  source checkout's folder is never covered.
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
- No real consultation in the validation harness (pilot plan Constraint 8;
  flow 26). The app never writes a consultation's audio outside its encrypted
  session store, and the harness reads only the set folder it is given. That a
  set folder holds only invented scripts' speech and mock role-plays is an
  OPERATING RULE the practitioner keeps — the harness cannot tell a mock
  recording from a real one (threat model, "The pilot", harness residue (1)).
  The filled pilot log stays off the repository and the findings register in
  the repository holds no clinical content (`docs/pilot/`).

## The Chrome side at a glance

Chrome ↔ native host over stdio (flow 1) ↔ `scribe-app` over the per-user
named pipe (flow 19), with what Chrome keeps and draws in flow 20. The
Chrome-spawned host is a thin, stateless relay; the app alone decides every
pause, Start, Resume and refusal; a patient's name crosses only for a note
Cliniko verified, lives in memory only on the Chrome side and in the app
until that session's Complete — when the app writes it, encrypted, into the
session's Past-sessions label and nowhere else (flow 22) — and reaches a
Cliniko tab only for that tab's own clinic.
