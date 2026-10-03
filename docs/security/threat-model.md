# Threat Model (Phases 1–3A, practitioner profile, note learning, Cliniko workflow safeguards, Cliniko draft write, privacy and professional controls, installation)

Scope: the implemented system — extension shell, native-messaging host,
registration chain, logging, credential/session-crypto foundations (Phase 1),
plus local recording, encrypted session stores with DPAPI key custody, and
local transcription (Phase 2), plus the local note pipeline — template
mapping, autofill/prefill proposals, per-assertion confirmation, content
checking, and the note review UI (Phase 3A; the ML note model itself is
Phase 3B and stays out of scope below), plus the practitioner-profile and
note-learning surfaces, plus the Cliniko workflow safeguards (PLAN.md Phase 5,
built before Phase 4): the Cliniko API client and the clinic keys,
recording consent and the encounter record, the host↔app named pipe with
protocol v2, the pause rule and the Unreviewed review, the Chrome side panel,
page frame and block, and the hands-free controls; plus the Cliniko draft
write (PLAN.md Phase 4, the cliniko-draft-write plan, built 2026-09-29): the
Note tab's "Write draft to Cliniko", the client's ONE write (a `PATCH` that
fills the open draft treatment note), the per-session write record
`write.enc`, completion after a confirmed write, and — since 2026-09-30 (D15)
— the append that keeps every answer already in the note ("THE DRAFT WRITE"
under "Cliniko API client" below); plus the privacy and professional controls
(PLAN.md Phase 6, the privacy-professional-controls plan, built 2026-10-01):
the durable audit record, the Past-sessions archive and its tab, the CSV
export, the exclusions and the exception hooks ("Privacy and professional
controls" below); plus the installation (PLAN.md Phase 7, the installation
plan, built 2026-10-02 → 2026-10-03 and NOT YET INSTALLED — no real build has
run and Phase P is the practitioner's): the packaged build and its
per-machine installer, the separately shipped model pack, the build of record,
and the developer build as a separate channel ("Installation" below). Every
`%LOCALAPPDATA%\ClinikoScribe` path in this document is the installed
(production) app's data folder; a source checkout — the developer build —
keeps the same layout under `%LOCALAPPDATA%\ClinikoScribe-dev`, plus its own
`models\` there (the installed app's models are in its install folder).
Clinical data now exists: audio,
transcripts, and the composed note artifact, encrypted at rest under
per-session keys; an UNPROTECTED recovery store expires at ~24 h (eligible at
24 h, destroyed by the next successful sweep), while a live or under-review
session is sweep-exempt (see the retention schedule for the exemption). Since
the privacy-professional-controls plan, every non-mock Complete also KEEPS
the session's transcript, saved note and generated note — never its audio —
in a Past-sessions entry under its own key, for a retention the practitioner
chooses (default: until they delete it), and every session leaves a
content-free audit row for 7 years.
Patient NAMES now exist too: in memory, fetched from Cliniko for a verified
note and shown on the desktop and in Chrome ("The Chrome link" and "The
Chrome extension" below) — and, since the privacy-professional-controls plan,
at rest in exactly one place, each Past-sessions entry's encrypted label
(written at Complete from the name the app held in memory for that session;
never in `encounter.enc`, the audit row, the CSV or a log).

## Trust boundaries

1. **Chrome ↔ native host (stdio pipe).**
   - Chrome enforces that only the extension pinned in `allowed_origins`
     (`chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`) can launch the
     registered host.
   - The host independently verifies the origin argv and refuses to enter
     protocol mode without it (exit before reading stdin).
   - **The session nonce is a session/correlation identifier, NOT
     authentication.** Any process that can reach the host's stdio already
     sees the nonce in `hello_ack`. It exists to detect mixed/stale sessions
     (wrong-nonce → disconnect), nothing more. No message-level cryptography
     is used on this pipe — deliberately: see "the same-user attacker" below.
   - Since protocol v2 the host also relays `context`, `command` and `state`
     between Chrome and `scribe-app`'s per-user named pipe; the pipe, its
     verification and its same-user residue are "The Chrome link" below.

2. **The same-user attacker (ACCEPTED RESIDUAL RISK).**
   Malware running as the logged-in Windows user owns both endpoints. It can:
   - write a per-user `HKCU\...\NativeMessagingHosts\com.scribe.cliniko_host`
     entry pointing at its own binary (registration hijack). Chrome reads a
     per-user entry BEFORE the installed machine-wide one, so this still works
     against the installed app; the Status tab warns when it sees one
     ("Installation" below, HKCU SHADOWING), and the optional clinic-only
     Chrome policy makes Chrome ignore every per-user entry;
   - read process memory, including session keys and Credential Manager
     secrets accessible to the user session.
   Against a SOURCE checkout (the developer build — since the installation
   plan the dev channel, with its own host name) it can also replace or edit
   the dev host manifest or the copied `scribe-host.exe` in
   `%LOCALAPPDATA%\ClinikoScribe-dev\`, or the venv's interpreter and
   site-packages (code hijack through the host executable): all
   user-writable. Against the INSTALLED app that launcher hijack is retired:
   the program, the host manifest and `scribe-host.exe` live in
   `C:\Program Files\ClinikoScribe`, which a standard user can read and run
   but not change ("Installation" below, THE INSTALL FOLDER).
   No extension-side or pipe-side control changes this; message-level crypto
   would be theater against an attacker who owns both endpoints. **Cheap
   tripwire in place:** the host logs its resolved executable, module, cwd,
   every registry entry for its host name in Chrome's lookup order (the
   winning one and any others), and the winning manifest's host-executable
   path at every startup, so a hijacked chain is visible in the log history.
   **Mitigation:** the admin-only install folder (built — installation plan
   D1/D-I1, installed at its Phase P), signing (deferred; the pilot build is
   unsigned), plus normal OS hygiene (up-to-date OS, AV, no untrusted
   software in the clinic user session).

3. **Extension identity.** The pinned manifest `key` gives ID *stability*,
   not secrecy — for an unpacked extension the public key is visible by
   design. `key.pem` is gitignored; losing it changes nothing (the ID comes
   from the committed public key in `extension/src/channel.ts`) — only a NEW
   key whose public half is committed means a new ID and mandatory
   re-registration (round 27). The installed app's extension is the same pinned ID,
   loaded unpacked from `C:\Program Files\ClinikoScribe\extension`; the
   developer build's extension has its own key (`extension/key-dev.pem`,
   gitignored) and ID, accepted only by the dev host (`extension/KEY.md`). A
   Chrome Web Store listing is deferred (installation plan, Excluded); it
   would assign a different ID, and `allowed_origins` would change then.

4. **Protocol robustness (untrusted peer input).** The host treats every
   frame as untrusted: length prefix bounded at 1 MB and rejected WITHOUT
   allocation when oversized, UTF-8/JSON validated, envelope schema enforced
   (unknown fields, explicit nulls, nonce presence rules, version floor),
   typed errors + disconnect on every violation, and broken-pipe-safe writes.
   This is the same posture Phase 3 will need when the *transcript* becomes
   untrusted input to the note model.

## Data-at-rest residual risks

- **Session-key zeroization is best-effort (documented residual, LOW-009).**
  `SessionCrypto.destroy()` zeroes its `bytearray` and drops the reference,
  after which decryption fails — the functional guarantee holds. However,
  immutable `bytes` copies of key material (the `os.urandom` return and the
  per-operation copies handed to the AESGCM object) are freed by Python's
  allocator, not scrubbed; fragments may persist in process memory until
  reuse. Against the same-user attacker this is subsumed by boundary 2; a
  memory-scraping attacker with user privileges wins regardless. Accepted
  for the CPython + `cryptography` stack; revisit only if the threat model
  gains a stronger-than-same-user memory adversary.
- **Log files** contain whitelisted metadata only (structural enforcement +
  tripwire, tested including the pydantic-repr misuse case). Paths logged by
  the startup tripwire are not sensitive.
- **Credential Manager** entries are protected by Windows at user-session
  granularity — same-user access is by design (`scribe-app` reads a clinic's
  Cliniko API key unattended for each Cliniko call; see "Cliniko API client"
  below).

## Phase 2: audio, transcripts, and session-key custody

All Phase-2 protections are calibrated to boundary 2 above: the defended
adversary is outside the user's Windows session; the same-user attacker
remains an accepted residual.

1. **DPAPI key custody (crash-recovery window).** Each session's AES-256-GCM
   key is wrapped with `CryptProtectData` (current-user scope, no extra
   entropy) and stored as `sessions\<id>\key.dpapi` while the session is
   active or recoverable (unprotected recovery is expiry-eligible at 24 h and
   destroyed by the next successful sweep — see §6); it is unwrapped only in
   memory. Deleting
   that blob IS the cryptographic deletion of the session's audio and of the
   SESSION's copy of its transcript and notes (deletion ordering: on every
   Complete — fsync transcript, verify a decrypt round-trip, verify the note
   when one counts, write, verify and publish the Past-sessions entry under
   its OWN fresh key for a non-mock session (privacy-professional-controls
   C1 / D4), THEN delete the key, then best-effort remove the entry's
   `pending` marker and the session directory, a failed removal leaving a
   keyless directory the sweep collects; on Discard — any unfinished
   Past-sessions entry for the id removed key-first, then the key, then
   best-effort store removal). The transcript and notes a Complete kept are
   NOT destroyed by it: they live on in the entry until Delete now or expiry
   ("Privacy and professional controls" below). Residual: any process in the user's session
   can call `CryptUnprotectData` on the blob while it exists — subsumed by
   boundary 2.
2. **NTFS unlink is not anti-forensic (ACCEPTED RESIDUAL, user decision
   2026-07-26).** `key.dpapi`, `audio.enc`, and `transcript.enc` are removed
   by plain deletion — and so are a Past-sessions entry's key and files at
   Delete now or expiry, an audit month folder at its prune, and every other
   store's files; free clusters, the USN journal, or VSS shadow copies
   may retain the wrapped key blob or ciphertext until overwritten.
   Cryptographic deletion therefore holds at the same-user boundary the
   model already accepts, not against a forensic examiner with the disk.
   No overwrite-before-delete code (weak on NTFS/SSD anyway); full-volume
   encryption (BitLocker) is the real mitigation and is OS hygiene, not app
   scope.
3. **Runtime offline enforcement (primary proof: environment, not
   polling).** The ML stack (silero-VAD ONNX, faster-whisper/CTranslate2)
   loads only explicit local paths with `local_files_only=True`;
   `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`
   are set AND asserted at startup and before every ML import; the
   real-model tests run entirely under the enforced-offline env, and the
   Phase-2 completion gate (plan Step 13) adds a test proving transcription
   succeeds with network stubbed to fail plus socket polling during capture
   and transcription. The idle-app no-sockets polling test already runs,
   but env enforcement is the primary control — short-lived telemetry
   connections can dodge a poll.
   This control keeps the ML stack off the network; it says nothing about
   the Cliniko client, which is the app's ONE network-capable module and
   has its own surface ("Cliniko API client" below). Outside the app, the
   network users are two explicit setup-time steps the user runs from a
   source checkout — `scripts/setup-models.py` (SHA-pinned downloads) and the
   pinned prose-runtime wheel install (surface 17 of the note-learning
   section) — and, since the installation plan, the BUILD-time steps that make
   a release (data-flow-map flow 9). The installer and the installed app
   download nothing: the models arrive in a separately copied, hash-checked
   model pack.
4. **Clipboard / same-user UI surface.** The transcript-inspection view is
   display-only (`NoTextInteraction`) so clinical text cannot drift into the
   Windows clipboard (clipboard history / cloud clipboard sync) through
   casual selection. This is cheap defense-in-depth, not a boundary — a
   same-user process can still read process memory (boundary 2).
5. **Single-instance guard (per-user lock file behind a named mutex) —
   convenience guard, NOT a boundary.** A second `scribe-app` shows
   "already running" and exits before it constructs a controller, sweep or
   pipe (two instances over one sessions root produced real, confusing
   split-brain state in the 2026-07-28 live smoke).

   The rule (codex rounds 69–70, PR-MED-370 and PR-MED-380): ONE exclusion
   every admitted instance shares.
   - **The lock file is required.** `%LOCALAPPDATA%\ClinikoScribe\app.lock`
     is empty, opened with no sharing and held for the process lifetime. It
     sits inside this user's profile, where another standard account can
     neither open nor create it. No instance ever starts without it. Since
     the installation plan (D3, Task 1.5) it is the SAME file for both
     channels: a developer build also holds it in the production folder
     (creating the folder if absent, and touching nothing else there), so the
     installed app and a developer build never run at once — the running
     developer app's one use of the production folder. (The other named C8
     exception is not the app: the one-time `register-native-host.py
     --unregister` migration, which deletes the old per-user registration's
     two files there — see "Installation" below.)
     - Busy (another instance holds it, after a short retry for a scanner) →
       "already running".
     - Unopenable for any other reason (permissions, path, disk) → the app
       refuses to start ("Clinic Scribe could not start"), before the
       controller, the sweep or the pipe.
     - Windows closes a crashed instance's handle, so the next launch starts.
   - **The named mutex** `Global\ClinikoScribe-app-<user>` is only the fast,
     friendly check in front of the file.
     - This user's own mutex refuses a normal second launch as before.
     - It admits nothing on its own. A mutex-only instance could otherwise run
       beside a file-only one (round 70).
     - A mutex that is another account's (round 57 SEC-015: `Global\` needs no
       privilege and the name is guessable), or that `CreateMutexW` refuses,
       neither admits nor refuses by itself; the file decides.
     - The app creates the mutex OWNED by this user with a user-only DACL.
       The name is unchanged, so an old build (mutex only) and a new one still
       exclude each other through it.
     - A launch refused after creating the mutex closes it again, so the name
       is not pinned.

   What remains, all inside boundary 2 or plain inconvenience, never a data
   exposure:
   - a same-user process can squat the mutex name or hold the lock file, and
     the app then says "already running" (denial of convenience);
   - a scanner holding the file beyond the retry reads as "already running"
     (launch again);
   - an old build started while a new instance runs on the file alone
     (another account holding the name) is refused by that foreign mutex, as
     it always was.

   Tests simulate the foreign owner and use a tmp lock path. A real second
   account's squat, and the profile ACL that keeps such an account away from
   the file, are not proved by the suite.
6. **24 h recovery cap expires at the next SUCCESSFUL sweep, not on a hard
   deadline (ACCEPTED RESIDUAL).** The cap is enforced by the startup sweep, a
   periodic sweep on a 15-minute QTimer CADENCE (`app._SWEEP_INTERVAL_MS`), and
   an age filter on the recovery listing. An UNPROTECTED recovery store expires
   at the first scheduled sweep that RUNS SUCCESSFULLY after its 24 h mark —
   normally within about the 15-minute cadence while the app runs, and at next
   launch while it is closed (the startup sweep runs before the recovery screen
   lists anything). The 15 minutes is the intended INTERVAL, not a guaranteed
   bound: the sweep is a best-effort GUI-thread timer, so GUI-thread blocking,
   OS process suspension (sleep/hibernate), or a sweep that RETAINS the store
   after a transient I/O error (it fails closed toward RETENTION and retries
   next cycle — see below) can push actual expiry past one interval. A
   PROTECTED store, meanwhile — a live session, the controller's own `queued`
   transcript/note held open for review, or a recovery checkout, all exempted
   by `app.sweep_protected_ids` BEFORE any age check — is not swept at all, so
   its retention is unbounded while it stays protected (a note under review is
   deliberately never destroyed mid-review); the 24 h cap applies only once it
   becomes an unprotected recovery store. Timestamp
   handling is fail-safe: untrusted candidates (non-finite, or beyond the
   clock-skew tolerance in the future) are discarded and can never extend
   retention — age comes from the earliest TRUSTED candidate; if candidates
   exist but none is trusted the store fails CLOSED (expires); if nothing
   is readable at all it is kept and retried next sweep — transient
   filesystem errors must never trigger cryptographic deletion. A bounded
   `CLOCK_SKEW_TOLERANCE` (5 s) accepts mtimes that read marginally ahead
   of `time.time()` — a real effect of Windows' coarse wall clock (~15.6 ms
   on Python ≤ 3.12) against 100 ns NTFS mtimes, which previously made the
   sweep cryptographically delete sessions it had just created. Beyond the
   tolerance a future stamp is still treated as a broken/tampered clock and
   fails closed. Adds ≤ 5 s to the retention beyond the 24 h mark, on top of
   the cadence delay above. The rule is
   defined once (`session_store.earliest_trusted_timestamp`) and shared by the
   sweep and the recovery listing. A session-id-named LINK (symlink or
   junction) under the sessions root is never swept, keyed away, discarded or
   listed (privacy-professional-controls H3 round 35 SEC-002; "Privacy and
   professional controls" below) — it is not a session this app made.
7. **Transcript-view availability residual (no custody impact).** The shared
   transcript view can be visually replaced if a live transcription
   finishes while a recovered session's transcript is open; the overwritten
   recovered session remains protected on disk and recoverable after
   restart. Availability-only; Complete/Discard custody ordering is
   unaffected.

## Phase 3A: the note pipeline (config input, clinician-asserted content, review-window lifetime, copy)

Phase 3A composes a draft note from the transcript, has the clinician confirm
each non-transcript line, checks the composed note, then writes it under the
session key. Like everything above, it is calibrated to boundary 2: the
defended adversary is outside the user's Windows session; the same-user
attacker remains an accepted residual, and config plaintext plus the in-memory
note inherit exactly that posture.

1. **Config as a note-content input.** Autofill rules and prefill templates are
   clinician-authored plaintext under `%LOCALAPPDATA%\ClinikoScribe\config\`
   (`template_profiles.json`, `autofill_rules.json`, `prefill_templates.json`,
   and since the practitioner-profile plan's Phase 4 `section_cues.json` — a
   ROUTING input, not a content input: its phrases never enter a note, they
   select which verbatim transcript utterance lands in which section, so a
   hand-edited cue file can misplace transcript text but cannot author note
   text; it is digest-bound like the other three),
   deliberately OUTSIDE the encrypted session store and the 24 h rule — they
   are INTENDED as boilerplate, not patient data, and must survive session
   destruction (the loader validates structure only and cannot detect patient
   data or secrets a clinician hand-edits in; that non-storage of patient data
   is an operational rule, not an enforced guarantee).
   Config text becomes PROPOSED note content, never inserted content:
   `note_fill.py` matches configured trigger phrases against the transcript and
   emits only `NoteProposal`s. The loader (`note_config.py` `load_note_config`)
   is all-or-nothing and fails CLOSED — a config file that exists but is
   unreadable or malformed raises a typed error and applies nothing, so a
   corrupt or half-edited config cannot silently drive a generation. A same-user
   attacker can of course edit these files (boundary 2); the control that
   matters is downstream — no text AUTHORED in config reaches `note.enc` without
   explicit per-assertion clinician confirmation of the exact shown wording, and
   config text rejects Unicode line/paragraph separators and bidirectional
   format controls so the confirmed wording cannot differ from what was
   digested. Amendment (note-learning-and-styles plan, D5 — BUILT in its Phase
   2): lines the practitioner's OWN config pre-fills — every hand-authored
   autofill and prefill entry, and a learned rule once its sidecar record says
   `auto_confirmed` — carry `decided_by="config"` on their
   `ConfirmationDecision` with the digest they were minted under (the type
   refuses a config decision without it — `note.py`'s `_check_decider` — and
   pins that digest to the assertion's own). The decision is MINTED at the
   emitter (`note_fill.config_decisions`), carried on the draft
   (`NoteDraft.config_decisions`, validated against the draft's own proposals
   and digest), and `finalise_note` accepts a config decision only when it is
   field-for-field one the draft carries — so the review surface can pass a
   config decision on or replace it with the clinician's own decline (Remove),
   never mint one. They are ratified by one counted Save whose button says how
   many pre-filled lines it confirms, rendered with the distinct
   `pre-filled by your config` mark by the one rendering path; a proposal the
   config did NOT decide (a learned rule under its threshold) keeps its
   per-line row and blocks Save until decided. `clinician_asserted` is not
   drawn for a config-decided line (the counted Save is its acknowledgement);
   every other check runs on it unchanged — `autofill_trigger_absent` still
   blocks a pre-filled autofill line whose trigger the transcript never spoke.
   **The app itself now writes ONE of these files (practitioner-profile plan
   Phase 5, D9 as amended 2026-09-16 — auto-learn, review later).** When a
   note is SAVED, `note_config.append_user_cues` appends learned phrases to
   the user `section_cues.json` (creating it from the shipped default if
   absent, so the practitioner keeps every shipped cue) and records each
   phrase's section and date in a sidecar `section_cues.learned.json` that
   the loader never reads; `delete_user_cue` removes one. What can be written
   is bounded by structure at five points, each a call site: (a) only the
   Note tab's add/move path enqueues a candidate (`ui/note.py`
   `_consider_learning` queues what the Qt-free
   `ui/note_review.consider_learning` decides — Task H6) and only after
   `note.spoken_by_confirmed_clinician` (tested there FIRST, before the
   learning status is read) says the utterance is the CONFIRMED clinician's —
   a patient's, carer's or interpreter's line never reaches the learner,
   whatever the settings; (b)
   only while `ui.models.learning_status` finds a READABLE profile whose
   consent record carries the CURRENT text version (`consent_is_current` —
   an older version disables learning until the practitioner re-consents on
   the Practitioner tab) with the learning opt-in ticked, read at review
   start, re-read at every add or move, and AGAIN at Save (so a practitioner
   who turns learning on or off mid-review is never gated by a stale read);
   (c) the candidate is the utterance's leading two
   to four content tokens only (`note_config.propose_learning_phrase`),
   stored normalised; (d) `note_config.refuse_learning_candidate` — the
   ENFORCING control — refuses a candidate whose SOURCE tokens (original
   case, before normalisation) include a name-like token
   (`transcription.is_name_like_token`, sentence-initial position honoured),
   a numeric token (`is_number_token`), a date-shaped token (`d/d`, `d-d`,
   `d.d`, a four-digit run, a month name) or a medication-shaped token (a
   listed drug suffix, or a dose unit within two words), pinned by test as a
   class; (e) the queue is written only on Save, after `write_note`
   committed the note — an add undone before Save, a removal, a move's
   removal leg and a cancelled or abandoned review write nothing — and the
   exact bytes are validated by the loader's own two rules before either file
   is replaced (each replace atomic; a failure leaves the file as it was and
   is reported on the tab, never un-saving the note). The honest limit,
   stated plainly (round 1 PR-HIGH-001): the filter classifies SHAPE, not
   meaning. A benign-looking phrase that IS patient-identifying in context
   passes it; so does a drug name carrying none of the listed suffixes with
   no unit within two words; and a benign word ending in a listed suffix is
   refused (two anatomical words are exempted by name — an exemption admits
   a named form only, so an unforeseen form still fails toward refusal). One
   more limit runs the SAFE way and is named because it narrows what learning
   can pick up: the name heuristic is the transcript's pinned one, which at an
   utterance's first word exempts only the common sentence openers it lists —
   plus, since the practitioner's decision of 2026-09-17 (Task 5.7), the
   learner's own fixed list of clinical and imperative openers
   (`note_config.LEARNING_OPENER_EXEMPTIONS`: keep, try, avoid, continue,
   rest, ice, heat, stretch, apply, hold, repeat, use, start, stop, your, on,
   for, with, at, in, before, after) and, since 2026-09-18 (Task 5.8), its
   list of contracted starters (`note_config.LEARNING_CONTRACTED_STARTERS`:
   we're, we'll, i'll, it's, that's, don't, can't … — the contracted forms
   of the starters and auxiliaries the transcript heuristic already exempts;
   a form carrying an apostrophe is never a given name; a typographic
   apostrophe is folded to the plain one before the lookup), both applied at
   the REAL first word only and
   to the name check only (a dose or a number after an exempted opener is
   still refused); since the note-learning plan's Task 3.7 (2026-09-19) the
   same single site carries two further admissions of the name check, both
   fail-closed: (a) a token that is EXACTLY (case-preserving) one of the
   shipped clinical abbreviations (`note_config.CLINICAL_ABBREVIATIONS` —
   `HVLA`, `Cx`, `NAD` …; the list holds no given name, pinned) is never
   name-like at any position, and (b) a capitalised REAL-first word is
   admitted when its lowercase form is in the caller's `known_common`
   evidence — which only the sample-note learner supplies (the words seen in
   lowercase anywhere in the chosen notes); the two Note-tab callers pass no
   evidence, so rule (b) never reaches the transcript-derived paths (pinned
   on the source) and a name opening an utterance is still refused there,
   while rule (a) applies to them like every caller — a listed abbreviation
   is admitted at any position on all three paths. An exemption admits
   listed forms only, so a practitioner line opening with any other
   capitalised word ("Examination
   shows…", "Margaret…") is still refused as name-like and never teaches —
   visible as a "not learned" note, a refusal rather than a leak. The
   compensating control is the after-the-fact review: every learned phrase is
   listed on the Practitioner tab by section, the twenty most recent with
   their date as well (the sidecar's entries; a phrase whose sidecar write
   failed is listed without one), one click deletes it (surface 10 of the
   practitioner-profile section), and the phrase is the practitioner's own
   words, learned under consent text v2.
   The consent-version check is itself a control: a text change is a new
   version, and no record carrying an older one can enable learning.
2. **Clinician-asserted content in a clinical record.** A confirmed
   autofill/prefill proposal becomes a `NoteAssertion` and, once the note is
   saved, ratified content in the encrypted LOCAL DRAFT (`note.enc`). It is not
   yet a signed clinical record: a fully ratified note can be COPIED for
   pasting into Cliniko (enabled since the practitioner's 2026-09-27 decision,
   D12; surface 4 — the flag plus `_copy_ready`), and, for a linked recording,
   WRITTEN by the app into the open Cliniko treatment note as DRAFT content
   (cliniko-draft-write plan; "THE DRAFT WRITE" under "Cliniko API client"
   below — the request can carry `content` only, so it cannot finalise the
   note). Either way the assertion becomes signed clinical-record content only
   after the clinician finalises the note in Cliniko. The type model keeps
   this honest: `note_fill.py`
   emits proposals ONLY (typed return surface, pinned by test); a `NoteProposal`
   is a different type from a `NoteAssertion` and cannot be placed in a
   `GeneratedSection`; and a clinician-authored assertion without a confirmed
   `ConfirmationDecision` is unconstructable. Confirmation — not trigger
   presence, role attribution, or provenance — is the only thing that turns a
   proposal into record content; provenance proves attribution, never truth.
   **Review edits (practitioner-profile plan Phase 5, D14).** The clinician can
   also ADD a whole transcript utterance to a section, REMOVE a line the
   router placed, MOVE one to another section, and UNDO any of those until
   Save (`ui/note.py` `add_line` / `remove_line` / `move_line` / `undo_line`).
   What the structure enforces: an addition is a `transcript`-provenance
   `NoteAssertion` over the whole utterance's contiguous coordinates
   (`note.whole_utterance_assertion`, id `m<segment>`), so Check 1 rebuilds
   it exactly as it rebuilds a provider line and a mutated quote is an
   unclearable error; an utterance already anywhere in the working note is
   refused; the section chooser and every move apply the router's own
   ownership rule (`note.admissible_sections` — a clinician-owned section
   admits only the confirmed clinician's non-question lines), and Check 3
   derives the role from coordinates regardless, so an edit cannot place a
   patient's or a question line in a clinician-owned section; removal only
   subtracts; every edit re-finalises the WORKING draft
   (`ui.models.working_draft`) through the one content-change path, clearing
   acknowledgements, so every check runs over the edited note and a stale
   acknowledgement cannot survive; an omission a removal creates is Check 4's
   review warning, acknowledgeable, never a block; typing over a line or a
   proposal is the Edit control of the note-learning section's surface 12
   ("Typed edits"; its text admitted by
   `check_typed_text`; a typed line draws `clinician_asserted`). Edits freeze
   at Save like proposal decisions,
   and the transcript panel stays a non-interactive text box.
3. **The extended in-memory transcript lifetime across the review window.** The
   full uncertainty-marked transcript now stays in process memory beside the
   note through the WHOLE Note-tab review (`ui/note.py`), longer than the
   Phase-2 transcript-inspection view, because the clinician must be able to see
   a phrase the note omitted on the basis of LOW CONFIDENCE — that path is
   reached by no automated check (Check 4 `omission_warnings` separately flags
   omitted HIGH-RISK TOKENS — numbers, names, medications — in
   clinician-attributed segments, but it is a scoped high-risk-token heuristic,
   not a low-confidence or materiality detector; see the honest limit below).
   Plaintext transcript and note
   therefore coexist in memory for the review duration. This is inside
   boundary 2 (a same-user process can already read process memory); the Note
   tab's transcript panel stays display-only (`NoTextInteraction`) so casual
   selection cannot drift clinical text into the Windows clipboard, and the tab's
   plaintext is cleared when a new transcript loads over a stale note. The app
   introduces no new on-disk plaintext and no new logging channel (the note
   and transcript it keeps at Complete stay ENCRYPTED in a Past-sessions
   entry — "Privacy and professional controls" below; the routes
   out of its custody are the clinician's Copy of a ratified note, whose
   clipboard residue surface 4 names, and — since the cliniko-draft-write
   plan — the clinician's "Write draft to Cliniko" of the same ratified note
   into a linked recording's own Cliniko draft, over TLS to Cliniko's API
   only: "THE DRAFT WRITE" below) —
   the note models carry registered tripwire signatures, so a stray repr/dump is
   dropped by the log filter.
4. **The ratified copyable-note change.** The generated note is the app's first
   copyable clinical surface — copy is bound to a recorded flag (`ui/models.py`
   `COPY_TO_CLINIKO_ENABLED`), which ships ENABLED since the practitioner's
   2026-09-27 decision (Cliniko workflow safeguards plan D12; the Task 9.1 run
   is now a quality measurement, not an enablement gate). The flag is
   necessary, never sufficient: copy additionally requires a fully ratified
   note (no pending proposal, no blocking error, saved, no unacknowledged
   review warning), enforced by one predicate (`ui/note.py` `_copy_ready`)
   applied to BOTH the copy button and the note panel's text-selection flags
   and re-checked at click time — disabling the button alone is insufficient
   because selectable text keeps native copy shortcuts. The transcript panel
   is never copyable regardless of the flag. **Kept out of history and sync
   (Task 8.2, practitioner decision 2026-09-27):** every copy of note text
   goes through ONE placement (`ui/note.py` `_place_note_text`): one
   `QMimeData` whose text is exactly what a plain-text copy would place, plus
   three registered Windows clipboard formats —
   `ExcludeClipboardContentFromMonitorProcessing`,
   `CanIncludeInClipboardHistory` = 0 and `CanUploadToCloudClipboard` = 0
   (`ui/models.py` `clipboard_mime_formats`). Its callers are the Copy
   button (`_copy_note`: `format_note_body`) and a copy of the ratified note
   panel's selection (`_NotePanel`: the keyboard's Copy — Ctrl+C,
   Ctrl+Insert — and the panel's own context menu, which replaces Qt's; the
   selection as Qt renders it), and each re-checks `_copy_ready` at the moment
   of copying, so nothing is placed before ratification — plus, since the
   privacy-professional-controls plan, the Past sessions tab's "Copy saved
   note" (`ui/past_sessions.py`: `format_note_body` of a kept SAVED note,
   which was ratified before it could be saved; refused with its reason when
   the copy flag is off, no saved note was kept or the note has an unresolved
   error; its panels are `NoTextInteraction`, so no keyboard copy); pinned by
   `test_ui_screens.py` and `test_ui_models.py`. Windows clipboard history and
   cloud clipboard sync honour the formats, so a copied note is not kept in
   history or uploaded. **Residue once copied (named 2026-09-27, Task 1.4;
   narrowed by Task 8.2):** a copy puts the ratified note's plaintext on the
   Windows clipboard by the clinician's own action, and from there it is
   outside the app's custody — it stays until something replaces it (nothing
   is cleared, on a timer or otherwise), any same-user process can read the
   current clipboard (boundary 2; the formats do not stop that), and a
   third-party clipboard manager may ignore
   `ExcludeClipboardContentFromMonitorProcessing`. Outside the placement: a
   DRAG of the selected text out of the panel is Qt's own drag — it carries
   no formats but does not use the clipboard, and the text lands wherever it
   is dropped; and anything on screen can be captured (a screenshot). The app
   does not detect the history or sync settings, so keeping cloud clipboard
   sync off on the clinic machine stays advised
   (`docs/security/intended-use.md`, current scope note), no longer as the
   only mitigation.
   **The draft write shares the gate (cliniko-draft-write D2, D7).** The Note
   tab's "Write draft to Cliniko" sits beside Copy and is enabled only when
   `_copy_ready` holds AND the recording is linked AND the note is not from
   the test provider (D10) AND the session's write record can be read and
   does not already read `written` (`ui/models.py` `write_control`) AND no
   write or prose rendering is in flight (`ui/note.py`); the click
   re-checks, and the main window's slot checks again. What it sends is rendered by
   the SAME per-section renderer as Copy (`note.render_section_lines`, the
   review apparatus off — no bullet, provenance tag, pre-filled mark or
   "[includes …]" line), so Copy and the write cannot drift apart
   (Constraint 11). No clipboard is involved; the note leaves the machine
   only in the write's request body, inside TLS.

**The checker's honest limit (stated plainly, not implied).** The four checks
in `note_check.py` do NOT establish that a confirmed assertion is grounded in
the transcript. Specifically:

- `transcript` assertions are rebuilt from their single cited
  `(segment, first_word, last_word)` interval against the immutable transcript
  and compared byte-for-byte (Check 1), so a quoted span is exact by coordinate
  reconstruction. Multi-interval RECOMBINATION is not detected but is
  UNREPRESENTABLE by construction — an assertion carries exactly one contiguous
  interval (Task 1.1 types) — so it is rejected structurally, not caught by a
  check.
- Clinician-authored (autofill/prefill) assertions are verified only against
  transcript CONTRADICTION (Check 2), and only when they parse to explicit
  structure (a dose / laterality / negation claim over closed lexicons). A
  confirmed assertion the transcript is merely SILENT about — neither quoted
  from it nor contradicted by it — is detectable by NO check in this phase.
- **What "parses to explicit structure" excludes** (hardening rounds 48–52
  narrowed this materially; recorded here because it cannot be inferred from
  the sentence above). Three residues fail toward SILENCE — a contradiction
  that exists but is not raised, carried by confirmation like the silent case
  above:
  - a recognised QUESTION contributes no claim of any kind, so a
    contradiction stated interrogatively is not caught;
  - a preposed subordinate negation suppresses its main clause's laterality
    ("Although no fever, right knee pain persists." yields no laterality
    claim) — recognising it needs preposed-clause grammar this phase does not
    have;
  - a dose difference hard-blocks only when a positive administration or
    schedule word is present, so bare product-strength wording
    ("Paracetamol 500 mg") grades the acknowledgeable `dose_mismatch` review
    and never blocks — deliberate, because two strengths of one product can
    be held at once.

  One residue runs the OTHER way and is stated with equal care: question
  recognition keys on a trailing `?`, a WH-opener, or an auxiliary followed by
  a PRONOUN subject, so wording like "Is the pain in your left knee" is
  treated as an assertion and CAN still yield a laterality claim. That
  direction is bounded — such a claim can only ever raise a
  `laterality_mismatch` REVIEW warning against an assertion about the other
  side (laterality differences never block; see the next paragraph), and the
  clinician's exits (decline the proposed line, or cancel and regenerate) are
  unchanged.

  **Laterality differences are REVIEW-graded, not blocking** (hardening stage,
  practitioner-ratified 2026-09-03). Five cross-family review rounds each found
  a new bilateral or correlative wording — "not only the left knee but the
  right", "the left and the right knee", "not only left but right knee" —
  that clause-splitting turned into a one-sided claim, and an error-grade
  `contradiction` then blocked Save, Copy and Complete on a note consistent
  with what was said. The parser cannot mechanically establish shared-anchor
  bilateral wording, so the line is drawn where rounds 21–24 drew it for dose:
  a differing side is surfaced as `laterality_mismatch`, which the clinician
  must ACKNOWLEDGE before saving and may then save. The responsibility
  boundary this states plainly: a wrong-side confirmed line is caught by the
  clinician's acknowledgement, not by an unclearable block. Negated-symptom
  and exclusive same-state dose differences remain error-grade.

  Each residue is recorded at its mechanism in `note_check.py`
  (`_CONTRAST_TOKENS`, the modality gate at the top of `_claims_from_tokens`,
  `_ADMINISTRATION_WITNESS`) and in the plan's Review Findings Log, rounds
  48–52.

That residual is carried by per-assertion clinician confirmation of the exact
shown wording and by the clinician's own review and finalisation of every note
at signing (`PLAN.md`, Summary: "The clinician reviews and finalises every note
in Cliniko"), NOT by any automated grounding guarantee 3A does not have. The
note-pipeline custody surface itself is recorded in the `SessionController`
docstring: a per-session custody reservation serializes every custody consumer
under the shipped single-GUI-thread, queued-signal usage, and full
arbitrary-thread custody safety is a documented bounded residue for a future
dedicated hardening.

## Practitioner profile — Phases 1–5 (surfaces 1–9 finalised at that plan's Task 3.3; surface 10 and the consent v2 amendments at Task 5.4, 2026-09-16)

The practitioner-profile plan adds two stored artefacts that are about the
PRACTITIONER, not a patient: an encrypted voice profile used to tell "the
practitioner" from "someone else" in a consultation, and — since Phase 5 —
learned phrases in the practitioner's own cue file. Phase 1 landed the
embedder, the custody store and the in-memory enrolment capture (surfaces 1–5);
Phase 2 landed the attribution path and the auto-confirm (surfaces 6–8, with
the D4 responsibility boundary); Phase 3 landed the Practitioner tab, the
first-run flow and the consent gate (surface 9, and the wiring surface 5 was
waiting for); Phase 5 landed consent text v2, re-consent, review edits and
consented phrase learning (surface 10 below; the Phase 3A section's surfaces
1 and 2 carry the note-side controls). Everything below is calibrated to
boundary 2: the defended adversary is outside the user's Windows session.

1. **The practitioner's own biometric derivative at rest
   (`%LOCALAPPDATA%\ClinikoScribe\profile\voice.enc`).** The profile holds a
   numeric speaker-embedding vector — a derivative of the practitioner's
   voice that, with the same model, can recognise that voice again — plus the
   embedder identity, timestamps, speech seconds, the device name and the
   consent record; never audio. What the structure enforces: the blob is
   AES-256-GCM under a key that exists on disk only DPAPI-wrapped
   (current-user scope) with a profile-specific description that
   `session_store.unwrap_key_from_file` VERIFIES, so a session key blob cannot
   be presented as the profile key nor the reverse; the AAD names the
   artefact and version, so a blob of another purpose or version fails
   authentication; the key is written before the blob, and an EXISTING
   REUSABLE key (present, not zero-length/truncated, and unwrappable) is kept
   — re-enrolment under it replaces only `voice.enc` by a single
   `os.replace`, so a failed re-enrolment leaves the previous profile usable
   and a fresh key is never written beside a blob that reusable key could
   still open; deletion unlinks the key FIRST, then the blob. Permitted
   states the ordering allows, none of which loses a readable profile: a key
   with no blob (a first enrolment that failed after the key write) reads as
   absent; a present but DEAD key blob is already the cryptographic death of
   the old blob (the session store's deadness rule), so a save writes a fresh
   key and then the blob — a failure of that blob write leaves the new key
   beside the old, already-unreadable blob; an interrupted deletion (key
   gone, blob unlink failed) leaves a keyless blob, typed and named.
   Every unusable state (missing/dead/foreign key, unreadable, tampered or
   truncated blob, wrong AAD, malformed content, a different embedder) is a
   typed, structural error that carries no field of the profile. Residuals:
   any process in the user's session can unwrap the key (boundary 2); NTFS
   unlink is not anti-forensic (§2 above, same acceptance); the vector is
   sensitive as a biometric derivative even though it is not a secret against
   a same-user attacker — the compensating control is the practitioner's
   consent (v2 since Phase 5, ratified; v1 records are readable but not
   current) and the visible Delete, both on the Practitioner tab
   (surface 9).
2. **No enrolment audio is ever persisted.** `enrolment.record_enrolment`
   captures into process memory over the microphone screen's monitor-stream
   shape — no session, no chunk store, no file — returns the PCM to its
   caller, and clears its own buffers and the VAD's recurrent state on every
   exit; `enrol` embeds and holds no reference afterwards. Pinned by tests
   with a mock backend and a temporary `LOCALAPPDATA` under which nothing
   exists after either outcome. Residual: the returned PCM is the caller's
   to drop — the Practitioner tab's worker (`ui/practitioner.py`) holds the
   one reference only until `enrol` returns and deletes it before the profile
   is built, so no PCM reference outlives the embedding on the app's own path —
   and plaintext scrubbing is best-effort as for session audio (data-at-rest
   residuals above).
3. **The profile never reaches a log.** No module in the profile path logs;
   the profile and consent models' field names (`embedding`,
   `enrolment_speech_seconds`, `consent_text_version`) are registered log
   tripwire signatures, so a stray repr, `model_dump` or JSON of either model
   is dropped by the last-line filter in quoted and unquoted forms. The
   tripwire's documented limit is unchanged: bare numbers with no field name
   attached would not be recognised — the primary control is that nothing
   logs them.
4. **The speaker model is pinned, not trusted by shape.** The runtime
   embedder digests the model FILE'S bytes at construction and refuses any
   file whose SHA-256 is not the pin recorded from the practitioner's own
   fetch (the same constant the setup script downloads and promotes by —
   single-sourced), BEFORE `onnxruntime` is imported; the offline
   kill-switches are asserted before that import, UNC paths and a missing
   file are refused before it, telemetry is off, and the I/O signature is
   probed with one smoke inference at load so an incompatible export fails
   there rather than on a consultation segment. Residual: a same-user
   attacker who can replace the model file can also replace the pin (boundary
   2, code hijack).
5. **Enrolment holds the microphone exclusively.** `SessionController.
   begin_enrolment` is refused while a session records, pauses or processes,
   while a discard is in flight, or while the registered activity runs —
   `MainWindow` registers the microphone screen's benchmark worker through
   `set_enrolment_blocker` at construction (Phase 3), so a benchmark in
   flight refuses an enrolment and an enrolment in flight refuses the
   benchmark; while the lease is held, Start/Resume refuse, the idle monitor
   is handed over SYNCHRONOUSLY — the tab calls the microphone screen's
   `stop_monitor` on the GUI thread right after the lease is acquired and
   before the worker can open the device, and the poll tick keeps it closed
   afterwards (the consultation Start path keeps its pre-existing tick-based
   handoff: the capture worker and the idle monitor can both hold the device
   until the next monitor poll runs — a 100 ms `QTimer` interval on the GUI
   thread, a cadence rather than a bound, since GUI-thread work delays it —
   a named residue outside this plan) — the window refuses to close, and the tab's own
   Re-record and Delete are disabled. The
   Practitioner tab acquires the lease BEFORE the capture starts and releases
   it inside its result handler — after the embedding, `save_profile` and its
   own status update — on every path (saved, failed, stopped), so the
   microphone is the enrolment's for the whole sequence. Stop is honoured
   inside the capture, again before the embedding and again after it; once
   that final check has passed, the profile is built and `save_profile`
   runs regardless of a later Stop — the one residue — and the profile is
   then written and shown, and Delete removes it.
   This is a device-ownership and correctness guard (no two readers of one
   microphone, no enrolment audio mixed into a session), not a trust
   boundary.
6. **Attribution keeps the windowed plaintext bound and adds one number per
   segment to the transcript (Phase 2, D3/D13).** With an embedder and a
   profile supplied together, `transcribe_session` embeds each VAD segment
   slice with the speaker model INSIDE the same transcription window its
   spectral embedding is computed in — windows are packed to at most 30 s,
   and a lone VAD segment longer than that budget is its own oversized
   window, exactly as before attribution — and reduces it to one float, the
   raw cosine against the enrolled vector, before the loop advances; no
   whole-session PCM and no model embedding outlives an iteration (the same
   bound the batching and oversized-window tests pin, unchanged when the
   inputs are absent — that path runs byte for byte as before). The transcript artefact gains three OPTIONAL,
   defaulted fields, set together or not at all: a cluster label
   (`enrolled_speaker`, structurally required to name a segment that has
   transcribed text — a document naming any other label is refused at
   construction, so the Transcript screen cannot be shown one), a finite
   cosine in [-1, 1] (`enrolment_similarity`) and the embedder's `model_id`.
   None of the three is clinical content; none is a field name the log
   tripwire needs, because none carries text. Old `transcript.enc` artefacts
   read unchanged. Both transcription entry points (`ui.models
   build_transcriber` / `build_recovery_runner`) resolve the inputs the same
   way, and a profile made by a different embedder (`model_id` or the
   model's verified digest), an absent model file, an unusable profile or a
   model file that refuses to load all yield NO attribution rather than a
   failed transcription — the fallback is REPORTED on the Transcript screen
   (D2), never silent, and the readiness probe that names it loads no model
   on the GUI thread. Residual: the readiness probe compares a stored profile
   against the PIN, not against bytes; a present-but-wrong model file is
   discovered by the worker at load and the screen then says only that
   attribution did not run, not why.
7. **The confirmed role stays a UI selection; the attribution field is a
   pre-check, not a label (D1).** `enrolled_speaker` never reaches
   `compose_draft`'s `clinician_speaker` from the document: the Transcript
   screen checks the matching radio and `generate()` reads the checked
   radio exactly as for a hand-chosen role; the note checker's provenance
   check keeps deriving speaker roles from coordinates, so the spoken-
   injection defence for clinician-owned sections is unchanged. A document
   with a lying `enrolled_speaker` (a label no textual segment carries)
   cannot be constructed, and a label that exists but is wrong is the D4
   boundary below, not a structural failure.
8. **Auto-confirm responsibility boundary (D4, practitioner-ratified
   2026-09-05, UNCONDITIONAL).** Whenever a profile is applied and the
   transcript holds speech, the cluster with the highest mean similarity is
   pre-checked as the clinician and the line "Clinician: confirmed from your
   voice profile (similarity 0.xx) - change" is shown; `change` reverts to the
   manual radios in one click. This is a ratified relaxation of the Phase 3A
   rule that role confirmation is explicit: the pre-check satisfies the ROLE
   predicate only — the template profile, a loadable config, no recovery in
   flight and the generation lease still gate Generate — and it is never
   hidden behind a setting. The risk it accepts: with a weak best match (the
   practitioner absent from the room, a very different microphone, a profile
   enrolled by another person on the same Windows login) a patient's
   utterances can populate clinician-owned sections until the practitioner
   clicks `change`. The compensating controls are the VISIBLE similarity
   value on the line, the note checker (which still blocks unresolved
   errors), per-assertion review and the practitioner's review at signing,
   and re-enrolment; a margin-gated auto-confirm (manual fallback when the
   best match is weak or two clusters both match) was offered and declined
   and stays the documented hardening if Phase 6's measurement finds a
   problem. This is a responsibility boundary — the practitioner's choice,
   recorded — not a control claim.
9. **Consent, first run and deletion are UI state at the same-user
   boundary, not identity (Phase 3, D10; consent v2 and re-consent at Phase
   5, Task 5.0).** What the structure enforces: the Practitioner tab shows
   the CURRENT consent text verbatim (`ui/models.py` `CONSENT_TEXT_V3`,
   version `CONSENT_TEXT_VERSION = "consent-v3"` since the note-learning
   plan's Phase 0; the v1 and v2 texts stay in the file as history, and a
   record carrying either is readable but not current)
   and the Record button is enabled only while the consent
   box is ticked (and a microphone is selected and the selected embedder and
   the VAD model are present — an absent model disables the action and names
   `setup-models.py`, D16); the profile's consent record stores the ratified
   text's version, the acceptance time and the learning opt-in as ticked when
   it was saved, so a later text is a new version; while a READABLE profile
   whose record carries the CURRENT version exists — readable AGAINST THE
   SHIPPED EMBEDDER'S IDENTITY with the model file present, which is what the
   tab's readiness probe (`attribution_readiness`) establishes, not merely
   decryptable — that record is what
   pre-ticks the box, shown ticked and disabled (`consent_is_current`) —
   withdrawing consent IS Delete, which asks for confirmation and runs
   `delete_profile` (key first); a readable record carrying an OLDER version
   is not consent to the current text: the box stays unticked and editable, a
   notice asks for a fresh tick, Record needs it, and phrase learning is off
   until re-consent; "Confirm consent" (`on_confirm_consent`) re-saves the
   SAME vector under the existing key with a current record — no
   re-recording — and is also how the learning opt-in is changed (a
   re-record saves both too); a blob that cannot be read (a keyless remainder
   of an interrupted Delete, a tampered file) is reported and deletable but
   is NOT evidence of consent — its box stays unticked and enabled, so
   recording over it needs a fresh tick (peer round 27 PR-HIGH-006). First
   run selects the tab and shows a
   banner but gates nothing: recording, transcription and note generation
   work without a profile exactly as before. Residuals: consent is a checkbox
   ticked by whoever sits at the logged-in Windows session — the app cannot
   verify that the person enrolling is the practitioner (boundary 2, the same
   same-login residual accepted for the vector in surface 1); the record is
   the version string and time, not a copy of the text; a re-consent needs
   the profile to be READABLE against the shipped embedder's identity (the
   tab's readiness probe), so a profile made by another model or with the
   model file absent is re-enrolled rather than re-consented — and while
   that is so the tab shows the D2 fallback line in place of the record,
   neither the stored consent tick nor the learning opt-in, so the opt-in
   cannot be changed there, while the LAST SAVED opt-in stays in force for
   the Note tab (`ui.models.learning_status` reads the record without the
   identity check: learning needs consent, not the speaker model) until the
   profile is re-enrolled or deleted — Delete withdraws it (round 51
   LOW-002; decoupling the tab's consent display from attribution usability
   is the recorded hardening); a Delete that
   races a transcription's profile read has two
   outcomes and neither is a wrong attribution — a read that reaches the key
   after it is gone fails typed (`load_profile`: blob, then key, then
   decrypt) and that transcript gets the visible D2 fallback, while a read
   that has already unwrapped the key completes and that one transcription
   keeps its in-memory copy of the practitioner's own just-deleted profile
   (deleting persisted custody never revokes plaintext a worker already
   holds; the copy dies with the transcription).
   **Residue — the consent text's "stored on this computer only, and nothing
   leaves it" (codex round 30 PR-MED-030; Part B DECIDED (a) by the
   practitioner on 2026-10-02 — keep consent-v3 with this residue named).**
   `CONSENT_TEXT_V3` says "Everything it learns is stored on
   this computer only, and nothing leaves it." That is true of the PROGRAM:
   it writes what it learns only under this Windows login's
   `%LOCALAPPDATA%\ClinikoScribe` and sends none of it anywhere (the offline
   contract; the Cliniko API carries no learned data). It is NOT a guarantee
   against copies made by other software: Windows Backup, Volume Shadow Copy,
   a third-party backup or sync tool, or a data folder redirected into
   OneDrive, a network drive or the roaming profile can copy those files —
   the app only WARNS about the redirected locations it can see
   ("Privacy and professional controls", EXCLUSIONS and residues (g), (k)) and
   cannot see backup tools at all. The voice profile and the learned style are
   encrypted (a copy stays bound to this login's DPAPI key); the learned
   phrases and learned shorthand rules are PLAIN TEXT in `config\`, so a copy
   of them is readable wherever it lands. The text is unchanged because a
   changed consent text is a new version (consent-v4): both consent records go
   stale, the practitioner must re-consent, and the own-voice prose stage
   refuses until they do. The practitioner DECIDED option (a) on 2026-10-02
   (the plan's handoff note, "COMPOSER stage-7 PRACTITIONER DECISIONS"): keep
   consent-v3 unchanged with this residue named here and in the retention
   schedule (rows 42 and 46); the corrected wording is folded into the next
   consent version whenever one is next needed. The historical v1 and v2 texts ("nothing leaves this
   computer") are kept verbatim as history and are not current.
10. **Learned phrases at rest — plain text, the practitioner's own words, by
    consent (Phase 5, D9 as amended).** Where: the user
    `%LOCALAPPDATA%\ClinikoScribe\config\section_cues.json` (the fourth
    clinician config file, surface 1 of the Phase 3A section) and the sidecar
    `section_cues.learned.json` beside it (`{phrase: {section, learned_at}}`,
    read only by the Practitioner tab's "Recently learned" list, never by the
    loader — it cannot affect routing or the config digest). What a phrase
    is: at most four normalised content tokens from the START of a line the
    practitioner added or moved during review — a bounded prefix, which for
    a line of two to four content words is that line's whole content — and
    never a patient's line (the ownership test in `ui/note_review.py`
    `consider_learning` over `note.spoken_by_confirmed_clinician`, pinned —
    since Task H6 the widget's `ui/note.py` `_consider_learning` only applies
    its verdict).
    The controls that bound what gets written are the five call sites listed
    at the Phase 3A section's surface 1; the two on this tab are the consent
    gate (a readable profile, the CURRENT consent version, the opt-in —
    `ui.models.learning_status`) and the after-the-fact review:
    `note_config.load_learned_phrases` lists the last 20 learned phrases with
    section and date (sidecar entries whose phrase is no longer in the cue
    file are dropped on read) and every phrase in the user file the shipped
    default does not carry, by section; Delete on either runs
    `note_config.delete_user_cue`, which removes the phrase from the cue file
    and the sidecar. Retention: until deleted (retention schedule), outside
    the 24 h rule like the rest of config. Residuals, named: the refusal
    filter is shape-only (surface 1's honest limit) — the practitioner's
    review is the control for meaning; the opener exemptions (Task 5.7's
    clinical openers and Task 5.8's contracted starters, both
    practitioner-decided) admit listed forms only at the real first word,
    so an exempted opener that IS a name in some clinic ("Rest", "Hold") is
    learnable — the review-later list is the control (the contracted forms
    carry an apostrophe and add no such homograph); the note-learning plan's
    Task 3.7 admissions (surface 1 of the Phase 3A section) reach this
    surface through rule (a) only — a shipped abbreviation is never
    name-like at any position, and the shipped list holds no given name —
    because rule (b) needs evidence the Note tab never supplies, so what
    this surface learns from a transcript widened by exactly the shipped
    abbreviations and by nothing else; on the sample-note path (surface 15 of
    the note-learning section) rule (b) admits a name the practitioner ALSO
    wrote in lowercase somewhere in their chosen notes — the review of each
    exemplar before Save and its one-click delete are the control; the cue
    file and the
    sidecar are two
    atomic writes, not one — on learning, a sidecar write that fails after
    the cue file was replaced is REPORTED on the Note tab (the phrase is
    learned, listed under "Learned phrases" without a date), never raised as
    "not learned"; on deletion, a sidecar write that fails after the cue was
    removed leaves the entry in the sidecar, the tab keeps the row for a
    retry, and the retry — or any later delete, which prunes every sidecar
    entry whose phrase is no longer in the cue file — removes it; a
    phrase the practitioner hand-edits into the cue file is indistinguishable
    from a learned one on that list (both are theirs to delete); the write
    happens on the GUI thread at Save (two small atomic replaces); and the
    same-user boundary applies to the plaintext exactly as to the other
    config files.

## Note learning and styles (surfaces 11–17; Phases 0–4 BUILT, the Task 0.5 stubs finalised at that plan's Phase H)

The note-learning-and-styles plan adds live transcription during recording,
practitioner-typed edits that can become learned rules, a learned writing style
derived from the practitioner's own past notes, and a local language model that
renders prose; boundary 2 is unchanged — the defended adversary is still outside
the user's Windows session and every new artefact inherits exactly that posture.
Phases 0–4 of that plan are BUILT (2026-09-19 → 2026-09-24: the contracts —
consent v3, note schema v2, the style store and its model, the settings file,
the two shipped vocabularies and the typed-wording filter; live transcription;
typed edits and learned rules; the writing styles and sample-note learning; the
local language model and Check 5). Each surface below states what the structure
ENFORCES with its symbol and names its residue; the Phase 0 stubs that marked
later-phase controls "planned; enforced from Phase N" were finalised at that
plan's Phase H (task H3, 2026-09-25, after the whole-surface review rounds
24–26).

11. **Live transcription worker (D1–D3; C2, C7, C8, C9).** BUILT (that plan's
    Phase 1, 2026-09-19; the custody bounds hardened through codex rounds 9–11
    and Phase H). THE TEE: `session._tee_sink` wraps the capture sink — the
    store's encrypting `append_chunk` FIRST (the system of record; its
    exception propagates and fails the session exactly as before the tee
    existed), then the SAME plaintext chunk to `LiveTranscriber.feed` inside a
    boundary that never raises into the capture thread (a worker error fails
    the worker toward the batch path); the store method is resolved per call.
    THE WORKER (`transcription.LiveTranscriber`) never holds `SessionCrypto`,
    never reads the encrypted store and never writes a file (C7): it keeps
    the open VAD span, the packed ~30 s windows and the queued chunks as
    plaintext PCM in process memory, drops the PCM per window as it is
    transcribed, and keeps per-segment embeddings and enrolment cosines for
    the session; its Whisper and silero models are built on its own thread at
    Start (D3) and released before any batch fallback, so two models are
    never resident. BOUNDS (D2 as built): the queue is capped at
    `LIVE_QUEUE_CAP_BYTES` (three windows' worth, checked in `feed` under
    the account lock — exceeding it fails the worker as `fell_behind`); an
    open span is force-closed at `LIVE_MAX_SEGMENT_SECONDS`; the drain yields
    at every ready window, so retained plaintext is at most the window in
    progress plus the open span plus one chunk; a sealed tail is finite and
    drains in full. CUSTODY (C7): `stop()` joins the thread with a bound and
    returns whether the buffers are CONFIRMED cleared — `buffers_cleared`, an
    inspected predicate over the PCM, the windows, the queue and every
    per-segment product, which every exit clears through `_drop_pcm` /
    `_clear_buffers`; `False` on a join timeout — and every path that
    destroys or drops custody consults that verdict: `discard()` (the
    unlocked 10 s stop under the custody reservation; an uncleared worker
    REFUSES `discard_session` with `LiveStopPendingError` (a
    `SessionActivityError`), routes the recording to FAILED with key + chunks
    intact, and the next Discard retries), the three Complete paths and
    `_retire_locked` on a new Start (`_stop_live_locked`, the 1 s in-lock
    bound); the one caller allowed to ignore the verdict is `_fail_locked`,
    which destroys nothing. Since installation plan round 40 LOW-002 the Session
    screen runs a Discard with a worker attached on a `TaskThread`, so the
    window is not frozen through its wait. The screen shows "Discarding -
    stopping live transcription first...". Until the wait ends, every control
    is held, and so is every Chrome command (through `is_busy`). So are the
    main window's "Open for review", whose adoption could otherwise change
    which session the discard acts on, and closing the window. The thread
    always sends a result, so the hold always ends: any `BaseException` sends
    the fixed reason. An outlasted Discard says plainly that nothing was deleted and that
    Discard can be pressed again. It is never retried automatically: a later
    destructive step waits for the practitioner's fresh confirmation. Finish seals
    only (`finish()` enqueues the sentinel); the TAIL DRAIN runs on the
    processing `TaskThread` inside the transcriber callable
    (`ui/models._live_transcript`, handed the worker by
    `claim_live_transcriber` — legal only inside `transcribe()`, where
    Discard is already refused), which writes `transcript.enc` once through
    `assemble_transcript` and consults `stop()`'s verdict before the batch
    path may build a second model. FALLBACKS (C8): a model-load failure,
    `fell_behind`, a worker error or a drain error each name their reason on
    the Session screen's status line and the consultation continues through
    the batch stage (flow 7). THE LIVE VIEW (C2): the worker posts each
    window through a queued Qt signal to the same display-only
    `NoTextInteraction` transcript widget (`ui/transcript.py`); a post after
    the view closed is dropped, and so is a post carrying an earlier Start's
    token — each Start's worker posts under its own, so a window the
    RETIRED worker emitted before it was stopped, still queued when the next
    Start opens its view, is neither drawn in the next patient's view nor
    fed to the spoken-pause and new-consultation rules (round 57 SEC-022);
    the view is cleared on the Session screen's
    Discard, the final document replaces it wholesale, and live segments
    carry `LIVE_SPEAKER_PENDING`, never a cluster label. LOGGING (C9): the
    worker holds no logger; the ONE new log record is
    `live_transcriber_stop_timeout` with the session id and state only, and
    the words of a posted window are `word_text` tripwire markers. THE
    WARM-UP (installation plan round 35 MED-001): the first recording after
    the 0.1.0 install failed at Start while the worker was making the
    process's FIRST import of the stack beside the microphone stream; the
    most likely path (the log could not name it) is an extension module's
    initialisation holding the interpreter lock the capture callback needs,
    until the device dropped frames — which fail capture by design. So
    `ml_warmup.ImportWarmup` imports numpy, onnxruntime and faster-whisper
    once at app start on its own thread (modules only — no model, audio,
    session or connection; the offline switches asserted first). While it
    runs, EVERY Start — the Session tab's and Chrome's — is REFUSED with
    "Clinic Scribe is still getting ready - start again in a moment" (round
    36 MED-001, the practitioner's option (b), 2026-10-03:
    `SessionScreen.start_held`, asked by `on_start` / `start_linked` and by
    `ChromeBridge._start` as the code `getting_ready`) BEFORE
    anything is made — no audit `begin`, no session folder, no key, and the
    desktop consent tick is kept — but only for `START_HOLD_SECONDS` (60 s)
    from the warm-up's start, so a hung warm-up never blocks recording
    longer; a failed warm-up holds nothing. A Start admitted after the bound
    while it still runs gets NO worker (the window's factory returns None
    until it finishes: `live_transcriber state=not_attached`) and goes to the
    batch path. A capture failure now logs its type name and a fixed detail
    word (`capture_failure`), never its message. The never-drop rule is
    unchanged: dropped frames at any moment, the first second included,
    still fail the session. The warm-up's own residue: the per-session model
    construction (the ONNX sessions and the Whisper model) still runs on the
    worker's thread while capture runs — a same-process retry that rebuilt
    every model recorded normally, but nothing bounds how long a third-party
    constructor may hold the interpreter lock; a voice enrolment is held the
    same way (`MainWindow._enrolment_blocker`, round 37 LOW-002); a recording
    or enrolment admitted after the 60 s bound while the warm-up still runs,
    and the Microphone tab's level meter, still overlap its imports
    (a recording that fails there keeps its audio for recovery and logs its
    type; the warm-up's length is logged as `ml_warmup duration_ms`); and
    the Chrome side panel clears its own consent tick when it sends Start, so
    a refused Chrome Start needs the panel's tick again (the extension's
    behaviour for every refusal). Residue,
    stated: ≤ 0.25 s of tail speech after a forced 30 s cut is absent from
    the LIVE document (the batch fallback keeps it); the join bounds are
    time-based, so a provider call that blocks past them leaves the worker
    ATTACHED and the key in place until the worker clears itself — the retry
    case above, logged as metadata, never a destroyed key; and the plaintext
    the worker holds is bounded in audio (the cap) and not in window count
    (short utterances 5 s apart make many small windows).
12. **Typed edits — the `clinician` provenance (D4; C3, C9).** The TYPE is
    built. In `note.py` a `clinician` assertion's typed text IS its span text
    (no second field, so the digested wording and the carried wording cannot
    name different words), its `proposal_id` is `None`, its decision names the
    line itself, and an optional `replaces` records the assertion it supersedes;
    `DRAFT_BASE_PROVENANCES = {transcript, clinician}` admits typed lines into a
    draft's base while `finalise_note` still refuses rule-authored base lines
    and requires a clinician decision on every typed one; the provider boundary
    moved to `compose_draft`'s `_confine_provider_output`, which admits
    transcript provenance only and raises `ProviderOutputError`, so a provider
    cannot fabricate a typed line with complete-looking evidence; and
    `write_note` verifies a typed line's `shown_text_digest` and `config_digest`
    exactly as it does every other authored line (C3). Typed wording is note-model
    text and carries the existing note tripwire markers, so it is not logged (C9).
    The Edit control is BUILT (Phase 2, `ui/note.py` `edit_line`): it types only
    OVER a line or proposal — the typed line inherits that target's section,
    records it in `replaces`, and subtracts it (a provider line to the removed
    set, a manual line set aside, a proposal declined at finalisation) — and its
    text is admitted by `ui.models.check_typed_text` (non-blank, bounded, the
    ONE config-text control-character validator, because the same words may
    become a learned rule's wording); the refusal filters are NOT applied to
    the note line itself — they decide what is LEARNED, never what the
    clinician may write in their own note. A typed line still draws
    `clinician_asserted`. Undo restores the replaced line; edits freeze at Save.
13. **Learned rules — trigger and wording admission (D5, D11; C5, C6).** BUILT
    (Phase 2). Admission, three refusals and no edit (C5): the trigger is the
    practitioner's OWN utterance (`spoken_by_confirmed_clinician` on the segment
    the typed line replaced — another speaker's line, or a hand-authored config
    line with no utterance behind it, teaches nothing) reduced by
    `note_config.propose_rule_trigger` to its last ≤ 6 content tokens (a
    heuristic on WHAT is learned, not a control) and passed through THE refusal
    filter `refuse_learning_candidate` with its real position context; the
    wording is the typed text through `refuse_typed_wording` — the narrower
    filter for PRACTITIONER-TYPED text, sharing the number, date and medication
    classifiers and running NO name heuristic (D11, practitioner decision
    2026-09-18; consent v3 says so). Writing (C6): `append_learned_rules` runs
    ONLY from the Note tab's Save (Cancel, Discard, Delete-and-complete and Undo
    write nothing and the exit notice names the dropped rules), validates each
    candidate as an `AutofillRule` under a fresh `learned-<ulid>` id and checks
    its trigger against every trigger the file already holds BEFORE any write
    (an invalid or duplicate candidate is skipped and reported, never written),
    validates the exact bytes by the loader's own rules, then replaces
    `autofill_rules.json` atomically and writes the metadata sidecar
    `autofill_rules.learned.json` (never read by the loader, so it can never
    move the digest); `replace_learned_rule_wording` corrects a learned rule's
    wording IN PLACE (same id, same trigger, count reset, previous wording in
    the sidecar's history — the sidecar's reset written FIRST, so a failed rules
    write leaves the old wording needing its confirmations again, never a new
    wording that pre-fills unconfirmed); `record_rule_outcomes` writes the
    sidecar only (auto-confirm at exactly `LEARNED_RULE_AUTO_CONFIRM_AFTER = 3`
    unchanged confirmations; Remove or decline resets to 0 and never deletes);
    the Practitioner tab's "Learned shorthand" lists every learned rule with
    its count and pre-filled state and deletes through `delete_learned_rule`
    (rules file first, then the sidecar; a hand-authored rule is never deleted
    there). Residue, identical to the transcript filter's: a drug name with no
    listed suffix and no dose unit passes a SHAPE filter — the review-later list
    is the control; a rule whose sidecar record was lost never auto-confirms
    (the safe direction). `typed_wording` and `previous_expansion` are tripwire
    markers (C9).
14. **Save-as-ratification and config decisions (D5; C3).** BUILT (Phase 2).
    The decision type: `ConfirmationDecision.decided_by` is `clinician`
    (default, so v1 notes read) or `config`, a `config` decision WITHOUT a
    `config_digest` is unrepresentable — `note.py`'s `_check_decider` validator
    refuses it — and the digest it carries must equal the assertion's own, so a
    config-decided line cannot name a config it was not minted under. The
    minting and the gate are as boundary 2's amendment above states:
    `note_fill.config_decisions` mints, `NoteDraft.config_decisions` carries,
    `finalise_note` accepts only a carried decision; the Note tab shows
    pre-filled lines marked with no confirm/decline row, offers Remove (the
    clinician's decline, recorded at Save) and Edit, labels the Save button with
    the count it confirms, and stays refused while any proposal the config did
    NOT decide is pending or any review warning is unacknowledged;
    `note_check.provenance_warnings` draws no `clinician_asserted` for a
    `decided_by="config"` assertion and every other warning unchanged. Residue,
    stated: the shown-text digest of a pre-filled line is the proposal's own —
    the line is rendered from the assertion's `span_text`, which IS the
    proposal's excerpt, by the one rendering path, so the two cannot name
    different words except through that path itself (the proposal-row read-back
    defence belongs to lines that have a row). Second residue (Phase H round
    24 MED-003): trigger matching is SPEAKER-AGNOSTIC (`note_fill.py`, Phase
    3A — presence gates candidacy, not truth), which was harmless while every
    autofill line had a confirm row; since D5 a matched hand-authored rule, a
    prefill seed or an auto-confirmed learned rule arrives PRE-FILLED whoever
    spoke the trigger — a PATIENT saying a learned trigger's tail (≤ 6 content
    tokens of the practitioner's own earlier utterance) pre-fills the
    practitioner's typed wording into a clinician-owned section under the D5
    mark and the counted Save alone. The alternative NOT taken — gating
    pre-fill on the CONFIRMED clinician's segment — needs voice attribution,
    which exists only after enrolment, and would demote every pre-fill to a
    proposal for an un-enrolled practitioner, reversing D5; the mark, the
    Save count and Remove (the clinician's recorded decline) are the controls.
15. **The style profile and its exemplars (D9, D10; C5, C6, C9).** Built: the
    store and the model. The learned style has its OWN root
    `%LOCALAPPDATA%\ClinikoScribe\style\` (`practitioner_profile.
    default_style_root`, a sibling of `profile\`), its own `key.dpapi` wrapped
    with the DISTINCT `STYLE_KEY_DESCRIPTION` that
    `session_store.unwrap_key_from_file` verifies before any decryption, and
    `style.enc` under `STYLE_AAD`, which refuses a blob of another purpose even
    under the right key — so the session, voice and style keys cannot open each
    other's store (pinned by
    `desktop/tests/test_style_profile.py::TestThreeKeyIsolation`);
    `save_style_profile` / `load_style_profile` / `style_profile_present` /
    `delete_style_profile` (key-first, idempotent, INDEPENDENT of
    `delete_profile`) share ONE custody implementation with the voice store
    (`_SealedStore`, `_seal`, `_open`, `_unlink_store`). The model
    `note_config.StyleProfile` carries its OWN `ConsentRecord`, at most
    `MAX_STYLE_EXEMPLARS = 30` `StyleExemplar`s from at most
    `MAX_SAMPLE_NOTES = 5` sources, hides its input in validation errors
    (`hide_input_in_errors`), and `exemplar_text` is a registered log tripwire
    signature (C9). BUILT (Phase 3), the write paths: the store is written by
    the Practitioner tab's "Learn from my notes" Save after the review —
    `ui/style_review.StyleReviewDialog` returns the ticked tokens and the
    exemplars left in place, `sample_notes.build_style_profile` assembles them
    and `practitioner_profile.save_style_profile` seals them under the style
    key (an existing key reused) — and by the "Learned style" group's per-item
    Remove, which re-saves the same profile minus one exemplar or one shorthand
    token under that same key — and, since codex round 31 PR-LOW-048, by the
    tab's "Confirm consent", which re-saves the SAME profile with only its
    consent record replaced by a current one (learned content untouched);
    nothing else writes it, and a cancelled review writes nothing (C6). The review may only REMOVE: `build_style_profile`
    raises `SampleNoteError` on a token the draft did not list as unrecognised
    or on an exemplar that is not one of the draft's own, so the review screen
    has no path that adds or edits text
    (`tests/test_sample_notes.py::TestBuildStyleProfile`). Auto-extracted
    shorthand is admitted by EXACT case-preserving membership of the shipped
    controlled vocabulary `config_defaults/clinical_abbreviations.json`
    (`note_config.CLINICAL_ABBREVIATIONS`, built and load-guarded); an
    abbreviation-SHAPED token that is NOT in it is listed as unrecognised and
    saved only when the practitioner ticks it — those rows are UNTICKED by
    default (`tests/test_ui_style_review.py`), so the default answer to the
    review is the smaller profile (D10). Deletion: the per-exemplar and
    per-token Removes above, plus the group's "Delete learned style" behind a
    confirmation dialog, which runs `delete_style_profile` key-first and is
    INDEPENDENT of the voice profile (neither Delete removes the other, and it
    works with no voice profile at all). Reading is bounded to ONE decrypt on
    the tab: `refresh_style_profile_state` is the tab's only caller of
    `load_style_profile` — at construction and after a learn, a remove, a
    delete or a consent renewal — and the summary line (`ui/models.style_profile_line`: a date and
    two counts, never a field's text) and both "Learned style" lists render
    from that one in-memory copy; the ONE other reader is the Own-voice prose
    stage (that plan's Phase 4, `ui/models.build_prose_stage`): one decrypt
    per rendering job on the Note tab's worker thread, the profile handed to
    the prompt builder as conditioning for every section call of that job and
    dropped when the job returns — and refused as conditioning when its own
    consent record is not the current text version (the same rule that turns
    phrase learning off; Phase H round 24). What that record's fields do,
    stated exactly (Phase H round 28): its `consent_text_version` gates USE
    of the learned style and the tab's summary line; its `learning_opt_in` is
    the evidence of the tick at that Save and is consulted by nothing — phrase
    and rule learning read the VOICE record's opt-in (`learning_status`), and
    withdrawing a learned artefact is its deletion, as the v3 text says. No
    5 s poll ever opens the STYLE store, and
    in steady state neither poll opens any store (the tab's
    `refresh_availability` and the microphone screen's `refresh_model_status`
    render stats — round 51 MED-001; the microphone poll re-reads the VOICE
    profile once when the speaker model's presence flips, round 55
    PR-REG-006), pinned by
    `tests/test_ui_learn_style.py::TestPollNeverDecrypts`, which holds that
    model presence steady and counts the `_open` primitive across both
    polls. The `ConsentRecord` sealed into the
    blob is the practitioner's own tick on the tab under consent text v3, taken
    at the Save that wrote it and re-checked at click time; sample learning
    needs NO voice profile and reads none (D9). Residue: an exemplar
    that passes the SHAPE filter unchanged (C5) may still be patient-identifying
    in context — the practitioner's review and one-click delete are the control
    (an Accepted Assumption of that plan); and the filter's Task 3.7 admissions
    (surface 1 of the Phase 3A section) mean a name the practitioner also wrote
    in lowercase in their chosen notes can pass as an exemplar — the review
    screen and the one-click delete are the control.
16. **Sample-note ingest (D9; C6).** Built (Phase 3):
    `sample_notes.read_sample_note` takes a chosen file or pasted text and
    reads it into memory only — a `Path` must carry a `.txt`, `.docx` or
    `.pdf` suffix (`SAMPLE_NOTE_SUFFIXES`; anything else is refused by name,
    "paste the text instead") and is bounded by `MAX_SAMPLE_NOTE_BYTES` (2 MiB
    — a stat first, then every reader's ONE rule, the capped
    `read(MAX_SAMPLE_NOTE_BYTES + 1)`, so a file that grows after the stat is
    still refused; Phase H round 24) and `MAX_SAMPLE_NOTE_CHARS` (200 000); a
    `.txt` is ONE capped read decoded utf-8-sig then cp1252, a `.docx` is
    opened through
    `python-docx` 1.2.0 (a pinned base dependency in `pyproject.toml`), and a
    `.pdf` (Phase 4 live smoke, practitioner decision 2026-09-20 — Cliniko
    exports notes as PDF) is TEXT-EXTRACTED through `pypdf` 6.19.0 (pinned,
    base, pure Python, no OCR): the bytes read through a capped request, the
    document parsed from memory, an encrypted PDF refused by name, at most
    `MAX_PDF_PAGES` (60) pages, a page yielding more than `MAX_PDF_PAGE_CHARS`
    (20 000) characters REFUSING the file by name (a refusal, never a
    truncation) and the total bounded while collected, a document whose
    pages yield no text refused by name with the paste hint, and every pypdf
    raise translated to `SampleNoteError` naming the exception TYPE only (C9).
    Residue, stated exactly: pypdf inflates each content stream in full itself
    and exposes no capped-read hook, so unlike the `.docx` path the allocation
    bound is the ≤ 2 MiB compressed input times DEFLATE's maximum ratio, not a
    cap this module sets — a hostile stream is a same-user chosen file that
    fails with nothing written (the PR-MED-020 → LOW precedent).
    The module never writes, copies, moves or renames — pinned by a before/after
    snapshot of the whole temporary tree
    (`tests/test_sample_notes.py::TestReadSampleNote::
    test_a_txt_file_is_read_into_memory_and_the_tree_is_untouched`) — and
    `SampleNote.sample_text` is `repr=False` and a registered log tripwire
    marker beside `recognised_shorthand` and `unrecognised_shorthand` (C9).
    `learn_style_profile` is pure over the texts it is handed: it reads
    nothing and writes nothing, and its draft reaches disk only through the
    review's Save (C6, surface 15). Deleting the originals is a SEPARATE
    explicit confirmation AFTER that save — `ui/style_review.
    DeleteOriginalsDialog` names the paths with "Delete these files now"
    UNTICKED by default, and only an accepted-and-ticked dialog calls
    `delete_sample_files`, which unlinks EXACTLY the listed paths, refuses a
    directory (never walks one) and reports every other failure per path
    (`tests/test_sample_notes.py::TestDeleteSampleFiles::
    test_exactly_the_listed_paths_go`) — so no ingest path removes the
    practitioner's own files as a side effect. Residue: the reader trusts the
    file's suffix and its size, not its content — a mis-chosen `.txt` that is
    not a note is learned from like any other and reviewed like any other; the
    plaintext has THREE lifetimes (peer round 18 PR-LOW-029): the review
    dialog's draft and rows are released on every exit of its runner
    (`ui/style_review._dispose`); the tab's handler drops the read texts after
    the learner and the draft after the profile is built but holds the pasted
    source string until it returns (through the save and the delete-originals
    dialog); and the paste box keeps its text on Cancel or a failed Save so the
    practitioner can retry — cleared only by a successful Save (pinned in
    `tests/test_ui_learn_style.py`) — with the same best-effort in-memory
    residual as every other plaintext in this app. The `.docx` reader's memory
    bound is its OWN (PR-LOW-027, PR-LOW-031): every member is inflated by
    this module through a capped read request (never unbounded; the stdlib
    hands the decompressor `max(MAX_DOCX_MEMBER_BYTES + 1, 4096)` as
    `max_length`, so the allowance per call is the cap plus its sentinel
    byte, 8 MiB + 1 in production; the RETURNED bytes are bounded by the
    declared size and CRC, the total by the accumulated-payload check ≤
    `MAX_DOCX_DECLARED_BYTES`; STORED / DEFLATED only, encrypted parts refused
    by their flag bit, corrupt DEFLATE data refused by name) and python-docx
    parses a bounded in-memory re-zip, never the chosen file — the declared
    sizes are a first refusal, not the ceiling; residue: the decompressor's
    window and the re-zip buffer during the parse, and python-docx's XML parse
    of a member bounded only by that member's cap.
17. **The local language model and Check 5 (D6, D7, D8; C1, C4, C8).** Built
    (that plan's Phase 4, 2026-09-20).
    THE RUNTIME. `llama-cpp-python` 0.3.35 is installed ONLY from the prebuilt
    CPU wheel pinned by URL and SHA-256 in
    `desktop/requirements-ml-prose.txt` (`--require-hashes --no-deps`, a
    GitHub release asset) — a SECOND setup-time network step beside
    `setup-models.py` (the app's own network use is the Cliniko client
    alone), run once by the practitioner from a normal terminal —
    and it is deliberately NOT in the `[ml]` extra, because PyPI carries only
    an sdist and a plain `[dev,ml]` install would BUILD it from source, which
    D8 forbids (`desktop/pyproject.toml`, the comment under
    `[project.optional-dependencies]`). What is verified, stated exactly
    (codex round 22 PR-LOW-039): the hashed install verifies the downloaded
    ARCHIVE against the pin; `tests/test_language_model_runtime.py::
    TestInstalledRuntimeGate` then reads the PEP 610 `direct_url.json` and
    requires the pinned wheel URL and hash — a check of the install RECORD
    that catches an install which took another route (an index resolve, an
    sdist build), not a measurement of the installed bytes: a same-user actor
    who forges that record over locally built bytes is inside boundary 2 and
    is not defended (it SKIPS BY NAME when the runtime is absent, so the gate
    cannot pass silently on a machine that simply has no runtime — which is
    every CI runner: the `CI` workflow installs `[dev]` / `[dev,ml]` and
    never the requirements file, so this gate is evidence from the
    practitioner's machine ONLY and a source-built copy on CI would merely
    skip; Phase H round 24 — the one exception since the installation plan is
    the `Release` workflow's build, which installs the requirements file with
    `--require-hashes` into its build environment and runs no tests). The
    runtime's own native-library override is refused at the offline contract
    (codex round 22 PR-MED-033): `llama_cpp` loads its DLL from
    `LLAMA_CPP_LIB_PATH` when that variable is set, so
    `benchmark.apply_offline_env` deletes it at app startup and
    `assert_offline_env` — the first thing `LocalLanguageModel` runs —
    refuses while it is present, naming the variable and never reading its
    value as a path (`benchmark.FORBIDDEN_NATIVE_OVERRIDES`); `CUDA_PATH` /
    `HIP_PATH` are left alone (the runtime only ADDS them as DLL search
    directories, and the CPU wheel's bundled library has no CUDA/HIP
    dependency) — named as residue, not defended.
    THE MODEL. `scribe_desktop/language_model.py` pins `LANGUAGE_MODEL_NAME =
    "Qwen3-4B-Instruct-2507-Q4_K_M"`, `LANGUAGE_MODEL_SIZE_BYTES =
    2_497_281_120` (2.33 GiB) and `LANGUAGE_MODEL_SHA256`, recorded from the
    file's Hugging Face LFS record on 2026-09-20
    (`unsloth/Qwen3-4B-Instruct-2507-GGUF` — the quantiser is a third party,
    the upstream weights are Qwen's under Apache-2.0; the same
    trust-on-first-download posture as the speaker model).
    `LocalLanguageModel` loads from the LOCAL PATH ONLY and in this order:
    `assert_offline_env()` (kept as the app-wide invariant, NOT the enforcing
    control here — see the residue), a UNC path refused, presence, size == the
    pin (checked BEFORE 2.3 GiB is hashed), the streamed SHA-256 == the pin,
    the runtime imported lazily, then — because the runtime's `verbose=False`
    path duplicates file descriptors 1 and 2 to silence the native log, which
    a windowed process (a source checkout's `scribe-app.exe` is a `pythonw`
    launcher; the installed one is a windowed PyInstaller program) cannot
    satisfy — any of the two that cannot be duplicated is given `devnull` as
    its sink (`_give_std_fds_a_sink`, Phase H round 28; a console process is
    untouched), then the load, then a short smoke generation. Every failure
    is a typed `LanguageModelError` naming the STEP and never the prompt, and
    no `from_pretrained`-style fetch exists anywhere in the module (C1). The
    download is `scripts/setup-models.py`'s `language-model` entry: streamed
    1 MiB reads into `<name>.gguf.candidate` with HTTP Range resume, a
    free-space precondition before any byte is written, every read bounded by
    the PIN rather than by the declared `Content-Length` (a longer body
    deletes the candidate), https on every redirect hop, and promotion to
    `<name>.gguf` only after size AND digest match.
    THE INPUT. `prose_style.ProseInput.from_note` is the ONLY way in and it
    takes a FINALISED `GeneratedNote`: a `TranscriptDocument` or a `NoteDraft`
    is refused by TYPE, so the model never sees transcript text and never sees
    a pending proposal (C4, D6). `build_section_prompt` takes text lines only,
    and each section is ONE model call whose prompt is the section title, the
    confirmed lines between `PROMPT_LINES_HEADER` and `PROMPT_LINES_END`, and
    `NARRATIVE_INSTRUCTION` — own voice adds the `StyleProfile`'s measures,
    shorthand and at most 30 exemplars as CONDITIONING, never training, read
    per job and never on a poll, and BUDGETED against the model's window with
    the model's OWN token count (`LanguageModel.count_tokens` — the runtime's
    tokenizer; codex round 30 PR-MED-046 replaced Phase H round 28's
    character cap): `prose_style.conditioning_allowance` reserves the fixed
    instruction, the section's user text, the completion the section may
    need and a framing margin, and the conditioning block is trimmed to what
    remains (exemplars from the end, then shorthand); a section whose lines
    alone overflow the window is refused BEFORE any call as `too_long`,
    named on the style line ("too long for the model's window") — never a
    runtime raise. An instruction-shaped line inside the note is
    DATA: the instruction says so, and the ENFORCING control is Check 5 — an
    obeyed instruction that REPLACES the line drops the section's own tokens
    (or adds new ones), fails `missing_fact` / `added_content`, and the section
    keeps `clean`; the honest limit (codex round 22 PR-LOW-037): a completion
    that repeats the line AND obeys it keeps every token and passes the token
    gate — the practitioner's reading before Save is the control, and both
    shapes are pinned in `tests/test_prose_style.py`.
    `parse_section_prose` strips a `<think>` block, refuses an unclosed one
    and an echoed marker, drops a title line or markdown heading, and bounds
    the result at `MAX_SECTION_PROSE_CHARS`.
    CHECK 5. `note_check.fidelity_warnings` (with `fidelity_verdict` /
    `fidelity_verdicts`) compares a section's confirmed inputs with its prose
    on four rules: (a) `missing_fact` — every non-connective input token is
    present; (b) `added_content` — nothing outside the inputs but the shipped
    `config_defaults/prose_connectives.json` — since Phase H rounds 24 and 28
    WITHOUT the antonym function words on/off, before/after, over/under,
    since/until, in/out, up/down and `if` (`note_check._POLARITY_BEARING_TOKENS`,
    pinned off the list), which reverse a clinical meaning when swapped or
    dropped and are therefore facts under (a) and (b): "off paracetamol" →
    "on paracetamol" fails, "weight down 2 kg" → "weight up 2 kg" fails, as
    does a dropped "if"; and WITHOUT any word that is the lower-case form of a
    shipped clinical abbreviation (`as` / `AS`, ankylosing spondylitis —
    Check 5 compares folded tokens), refused at IMPORT by
    `note_config._refuse_vocabulary_overlap` as a broken install; two such
    words swapped BETWEEN facts keep the set and pass — the
    token-not-attachment residue below; (c) `polarity`
    — the MULTISET of negation markers (`no not never denies denied without
    nil`, and any `n't`) is identical; (d) `protected` — the multiset of
    number, date, medication
    and laterality tokens is identical (the learning filters' classifiers, the
    checker's lexicon, and `left`/`right`). A failing section keeps `clean`
    and raises ONE `style_fallback` REVIEW warning. It is a GATE, NOT A
    CERTIFICATE: it compares TOKENS, not attachment or order, so sides swapped
    between two anatomy words, a negation moved to another clause, two numbers
    traded between facts and a reversed comparison all PASS — the
    practitioner's reading of the shown prose before Save is the control,
    which is why Check 5 is not part of `check_note` but is run by the prose
    stage over what it is about to show.
    CUSTODY OF A RENDERING. A failed section's `StyleRendering` carries NO
    prose (C4, the schema validator) but does carry the section's
    `input_digest`, so the same lines are never re-asked inside one review; a
    model error yields no rendering at all and a reason line.
    `note.attach_style_renderings` binds a rendering ONLY where its
    `input_digest` equals `section_input_digest(section)` NOW — a stale
    rendering is dropped before the note is displayed, before `note.enc` is
    written and before Copy — and `note_input_digest` binds a job to the note
    it started for; `render_note(note, style)` remains the ONE rendering path
    all three go through (D7, `ui/models.format_note_body`).
    ON SCREEN (C8). The stage runs on the Note tab's `TaskThread` after each
    finalisation (`ui/note.py` `_start_style_stage`); the model is built ONCE
    per process on that worker thread (`ui/models._LanguageModelCache` — a
    failed load is remembered and named, so the remedy is a restart after the
    fix, not a retry storm); the result lands on the GUI thread
    (`_on_style_done`), is bound by digest (`ui/models.bind_stage_result`),
    DISPLAYED, the style line set, and only then does `_update_controls`
    re-enable Save. Save is UNAVAILABLE while a job is in flight — the button
    is disabled AND a click re-checks and says `SAVE_WHILE_RENDERING_MESSAGE`
    (PR-MED-015: Save snapshots the note, so a disabled button alone is not
    the control) — so nothing is persisted that the practitioner has not seen.
    Every fallback names itself on the `style_label` line under the note body:
    `RENDERING_IN_FLIGHT_LINE`, `RENDERING_DONE_LINE` (how many sections show
    prose, how many are shown as Clean clinical because the fidelity check
    refused the prose, how many could not be rendered at all),
    `LANGUAGE_MODEL_LOAD_FAILED_LINE` and `STYLE_PROFILE_MISSING_LINE` (the
    Phase-3 `style_fallback_line` now appears in the info label only on a
    Note tab built without a stage provider — never in the shipped window).
    A job orphaned by `clear()` keeps its thread until
    it reports and its result is dropped; an edit during a job invalidates
    only the sections it changed and a fresh job renders those. CUSTODY
    ORDER AT THE EXITS, stated exactly (Phase H round 24 MED-002): unlike the
    live worker, whose uncleared stop REFUSES key destruction (surface 11),
    the prose job holds no session crypto and is NOT consulted by Abandon,
    Cancel, Complete or Discard — those may destroy the session key while a
    rendering runs. The BOUND: `clear()` flips the job's abort flag, which
    `ProseStyleProvider.render` consults before every section's model call,
    so an orphaned job stops after the call in progress. Stated exactly
    (codex round 31 PR-LOW-047): the abort bounds what the MODEL sees — at
    most the one section whose call is in progress, whose prompt and
    completion are cleared from the runtime at that call's end — not what
    stays REFERENCED: the suspended stage frame holds the whole note (every
    populated section's confirmed lines, as the `ProseInput`) until that
    call returns, seconds later, and only then drops it. Residue, named:
    that one call and that whole-note reference for its duration; and a new
    Start admitted while it
    runs (the benchmark has a symmetric guard, the prose stage none) puts two
    CPU-bound models side by side for its duration — a C8 `fell_behind`
    fallback at worst, never data loss. The refuse-while-rendering shape
    (Save's) was NOT taken: it would block Abandon for a whole CPU render. The
    Practitioner tab's "Writing style" group still writes
    `note_config.PractitionerSettings` (`practitioner_settings.json`, default
    `clean`, outside `NoteConfig` and outside the config digest) the moment a
    radio is picked (`ui/models.save_note_style`), but the two prose radios
    are no longer disabled by design: they ENABLE as soon as
    `ui/models.language_model_available()` is true (the runtime importable AND
    the model file present — an import probe and a stat, never a load and
    never a decrypt, which is why the tab's 5 s poll may ask it), and
    `ui/models.language_model_absent_reason()` names the remedy (from a
    source checkout `setup-models.py --only language-model` plus the
    prose-runtime install; in the installed app "reinstall Clinic Scribe" —
    installation plan Task 1.7, `install_layout.model_remedy`). A saved-but-unavailable
    style is still shown selected-and-disabled beside `style_fallback_line`,
    and Check 5's connective allow-list still ships as
    `config_defaults/prose_connectives.json` (`note_config.PROSE_CONNECTIVES`,
    refused at import by `_parse_shipped_vocabulary` if the packaged file is
    emptied, malformed or key-missing).
    LOGS (C9). `prose_text`, `style_renderings` and now `section_texts` (the
    prose input's own field) are registered tripwire signatures, so a repr or
    dump of a rendering, of a note carrying renderings, or of the stage's
    input is dropped by the last-line filter; no module on this path holds a
    logger.
    RESIDUE. (1) The model's own output is unbounded semantics, bounded only
    by Check 5's token rules and the practitioner's reading — the honest limit
    above is the whole of it. (2) `assert_offline_env` is NOT an enforcing
    control for this runtime's NETWORK posture: llama-cpp-python reads no
    kill-switch variable (it refuses only the library-path override above).
    The ENFORCING control is the no-sockets integration test, in two legs with
    different coverage (codex round 22 PR-LOW-040):
    `tests/test_integration_no_sockets.py::
    test_prose_generation_no_sockets_with_the_mock_model` runs everywhere and
    proves the STAGE's orchestration — the prompt build, the section loop,
    Check 5, the binding — opens no socket while the process is provably
    inside a model call, over `MockLanguageModel` (no native code runs there);
    `test_prose_generation_no_sockets_with_the_real_model` is the RUNTIME's
    coverage — the real library's load and one generation under continuous
    OS-level polls — and it skips BY NAME until the wheel and the file exist,
    so that evidence is conditional and the record says when it last ran. (3)
    A 2.33 GiB model is resident in process memory for the life of the
    process; one section's prompt and completion pass through it and the
    runtime's inference state — its token buffers and KV cache — is cleared
    at the end of EVERY call (`LocalLanguageModel._clear_inference_state`,
    codex round 22 PR-MED-034), so what remains is the weights plus the
    runtime's own un-enumerated scratch (batch and logits arrays), with the
    same best-effort scrubbing residual as every other plaintext here. (4)
    llama-cpp-python's native code runs outside the Python socket stub,
    exactly as onnxruntime does — the OS-level socket polls of the real leg
    are what covers it, when that leg runs.

## Cliniko API client (Cliniko workflow safeguards plan, D9; BUILT at Task 1.1, 2026-09-27; its one draft write BUILT by the cliniko-draft-write plan, 2026-09-29)

The app's offline contract is now **no connection except Cliniko's API, and
none at startup or idle**. `scribe-app` holds exactly one network-capable
module, `desktop/src/scribe_desktop/cliniko_client.py` (flow 18 of the
data-flow map); the native host has none and never imports it. It reads
(`GET`) and, since the cliniko-draft-write plan, makes ONE kind of write: a
`PATCH` that fills an open draft treatment note (THE DRAFT WRITE below). It
has three app callers, each making its client calls on a worker thread in
answer to a practitioner action or a report from Chrome, never at startup, on
a timer or while idle: the draft write (`draft_write.py`), on the Note tab's
"Write draft to Cliniko" click only — two client calls per click, the note
read then the write; the clinic registry (`clinics.py`, Phase 2) on a Validate or
Replace key press on the Clinics tab (CLINIC KEYS below), and note
verification (`encounter.py` `verify_note_context`, Phase 3) — dispatched
when the practitioner opens a recovered session for checkout or an Unreviewed
session for review and its encounter record names a Cliniko note, or when a
clinic changes while that checkout is open; and, since the safeguards plan's
Phase 4, by the Chrome bridge (`ui/bridge.py`) for a note report from the focused tab on an
allow-listed host and, once per new pipe connection, for the linked live
session's own note (NOTE VERIFICATION below; "The Chrome link" below). An
idle app with Chrome closed makes no call; a Cliniko note left open in
Chrome is verified when its report arrives, and a verified outcome is
reused for the same note for 60 s rather than re-fetched.

CONFINEMENT. Ruff TID251 bans `socket`, `http`, `urllib.request` and
`PySide6.QtNetwork` across `desktop/`; the ONE exemption is the client's
`http.client` import. `tests/test_cliniko_client.py::TestConfinement` pins the
count at exactly one, that no other module under `desktop/src` imports
`http`, `ssl`, `socket`, `urllib.request` or `PySide6.QtNetwork`, that the
native host's import closure never reaches the client, and that `clinics.py`,
`draft_write.py` and `encounter.py` are the only modules that import it. Down
the chain, `TestWriteCallSites` confines what those importers may reach: each
may import only the client names pinned for it and name only the `ClinikoCall`
methods pinned for it (the write method only in `draft_write.py`), and no
module outside the client may use a client private member except as a
class's own `self.<name>` of a member that class itself defines, call any
`x.request(…)`, subclass a client class or reach `__globals__` / `__dict__` — the
private members and the capability list are DERIVED from the client's
source, so a new one is covered with no pin change. `TestWriteSlot` pins
that a write starts only from the Note tab's button slot (THE DRAFT WRITE
below). Residue: these are SOURCE checks, so a dynamic import
(`importlib.import_module`), a name built at run time, `vars()` or
`sys.modules` is outside them, and the transport's `request` is checked in
call position only; and the banned list — ruff's, and
`TestConfinement._NETWORK_MODULES` — names the
common network modules, not every network-capable API — `asyncio`,
`ftplib` / `smtplib` / `imaplib` / `poplib`, `xmlrpc.client`,
`multiprocessing.connection`, a `ctypes` call into `ws2_32` / `winhttp` or a
COM object such as `WinHttp.WinHttpRequest` through `win32com.client` are
not banned by name (none is used: today's `ctypes` loads are `kernel32`,
`user32` and `wtsapi32` only — H1 round 53 LOW-045). The runtime check is the
no-sockets integration test (host, app startup and idle, capture,
transcription, prose), which asserts zero connections whatever API opened
them — on the practitioner's host only, since CI skips integration.

WHAT IT CAN SEND (draft-write D1, Critical Constraint 1: drafts only, by
construction). The transport's allow-list (`cliniko_client._admit`) admits
exactly two request shapes and raises `ValueError` for anything else BEFORE a
connection exists: a `GET` with no body, or a `PATCH` to a path that fully
matches `/v1/treatment_notes/<id>` whose body is UTF-8 JSON — parsed as
Cliniko will read it, so an escaped key counts as the key it spells — holding
exactly ONE top-level key, `content`, whose value is an object. Both shapes go
only to a documented API host (`api.<shard>.cliniko.com` for a shard in
`SHARDS`) under `/v1/`; the method, host, path and every header name and value
must be exactly `str` and the body exactly `bytes`, and the transport sends the
plain header snapshot it checked, so what is checked is what is sent. Header
NAMES are limited to the three the client sets — HTTP Basic auth (the key as
username, empty password), `Accept: application/json`, and
`User-Agent: Clinic Scribe (<contact email>)`, the email refused on CR/LF or a
failed shape check — each once, plus, for the `PATCH` only,
`Content-Type` exactly `application/json`. So a top-level `draft`, `title`,
patient, booking, attendee or template field cannot leave, whoever builds the
request: the write can fill a note's content but cannot finalise it, create a
note, or move one to another patient, booking or template. The method string
`"PATCH"` is written once in the module (`_WRITE_METHOD`, pinned by a source
test), and its only sender is `ClinikoCall.write_draft_note(note_id,
content: DraftContent)`, whose body model has one field, `content`, and
refuses any other (`extra="forbid"`). The host is built ONLY from a
documented shard taken from the key's `-<shard>` suffix; a missing or unknown
suffix, or a key with any character outside the key alphabet (CR/LF
included), is `InvalidKey` before a request — never defaulted to `au1`. Ids
in a path are validated as 1–19 digits with no leading zero. A body JSON
cannot hold — a lone surrogate, a NaN — raises `DraftUnencodable` before any
request. Residue: what Cliniko does with the keys INSIDE `content` is
Cliniko's (the draft write sets the targeted answers only — each the answer as
read with the app's text appended below it, or the app's text for an empty
answer — in the note's own re-read content, THE DRAFT WRITE below); and
Cliniko documents a
final note as immutable, which is what stops a `PATCH` to a note finalised
after the write's own read (P.1's finalised leg: Cliniko answered 403) — the
app's request shape cannot express finalisation, but it does not by itself
stop a content write to a final note.

TRANSPORT. One `http.client.HTTPSConnection` per request, closed after, on
port 443. Every socket step (connect, each TLS/send/receive step) times out
at 15 s; the request as a whole has a 30 s deadline, checked after the
request is sent and before every body read, and every body read is
`HTTPResponse.read1` — at most one socket receive — never `read(n)`, which
loops receives until it has `n` bytes (codex round 8 PR-MED-010). A
slow-drip body is therefore abandoned as `Unreachable` at most one receive
timeout past the deadline. Bounded only per step (the named residue): a
library call that is not a body read — the connect + handshake + send, the
status line and headers, and a chunked body's framing (chunk-size lines,
their CRLF, the trailer). No redirects (`http.client` never follows one
and a 3xx is `RedirectRefused`); no proxy (`HTTPSConnection` reads no proxy
variable and `set_tunnel` is never called); `set_debuglevel(0)` pinned, so the
library never prints a request line or header. TLS: a `PROTOCOL_TLS_CLIENT`
context (certificate and hostname verified) with a TLS 1.2 minimum and the
Windows certificate store (`load_default_certs`). It is NOT
`ssl.create_default_context`, which opens the file `SSLKEYLOGFILE` names and
appends every session's secrets to it; the client's context never reads the
variable and pins `keylog_filename = None`, and
`benchmark.apply_offline_env` deletes the variable at startup while
`assert_offline_env` refuses it by name (surface 17's handling of
`LLAMA_CPP_LIB_PATH`, same shape).

UNTRUSTED ANSWERS. A body is read ONLY for a 200 and, for the `PATCH`
alone, for a 422: every other status is
final from its status line and headers, so a 401/403/404/429/3xx/5xx whose
body stalls or is cut keeps its own named error (and a 429 its reset) rather
than becoming `Unreachable` (codex round 8 PR-MED-012); the unread body goes
with the closed connection. For the `PATCH` the STATUS LINE decides
(draft-write D5): a 200 is a write Cliniko accepted whatever its body then
does — a body that stalls, is cut or fails to parse is reported as unreadable
and the answer stays `written` — and a 422's body is reduced to FIXED
categories before any exception exists: each top-level `errors` key becomes
one of Cliniko's documented treatment-note field names (`content`, `title`,
`patient_id`, `booking_id`, `attendee_id`, `treatment_note_template_id`,
`draft`) or `other`, and no key text, value or other body byte survives;
the body is dropped before `ClinikoRejected` is raised, outside any handler,
so it has neither `__cause__` nor `__context__`. An identifier-shaped key can
itself carry data, which is why the categories are a fixed set rather than a
shape filter; this surface is bounded by that set, not residue-free. Any other
4xx but 401/403/404/429 on the `PATCH` is `ClinikoRejected` with no
categories. A 200's body is read in pieces that never ask
the library for more than what is left of `MAX_BODY_BYTES + 1` (1 MiB + 1
byte) in total, plus the stdlib reader's own buffer; a body longer than
1 MiB is `Malformed` and never parsed. The status line and headers are bounded by
`http.client`'s own limits (at most 100 header lines of at most 64 KiB
each), which are the stdlib's, not this module's. A `RawResponse`'s repr
omits the body. A body that is not UTF-8 JSON, is nested past the parser's recursion
limit, carries an integer over the interpreter's digit limit, or is not a JSON
object is `Malformed`. Statuses map to named errors: 401/403
`CredentialsRejected`, 404 `NotFound`, 429 `RateLimited` (the reset header kept
only when it is short plain text), 3xx `RedirectRefused`, 5xx `Unreachable`,
anything else but 200 `UnexpectedStatus`. Library failures are classified
from the stdlib raise set, each call wrapped on its own (construction,
request, `getresponse`, the status and header read, every body read):
`ssl.SSLCertVerificationError` is `CertificateRejected`; any other `OSError`
— DNS, refused, reset, timeout, every other `ssl.SSLError`, and
`RemoteDisconnected` / `IncompleteRead` — is `Unreachable`; any other failure
(`HTTPException`, `ValueError`, the unforeseen) is `Malformed`.

SECRETS. The key is read from its source ONCE per logical call (one
verification, one Validate, or one hop of a draft write — a Write click makes
two calls, so it reads the stored key twice, THE DRAFT WRITE below), shared by
that call's requests, and on exit
the call drops its `Authorization` value and refuses further use; the client
object never holds it. What an exception raised by the module RENDERS — its
message, its repr, its formatted traceback, a log record of it — carries no
key, path, id, email or response byte: each named error's text is a fixed
sentence, and it is raised outside the `except` block that classified the
library's exception, so there is no chained context to render (a formatted
traceback prints source lines, never local values). The module holds no
logger. All pinned by `tests/test_cliniko_client.py::TestNothingLeaks` and the
per-stage cases. The exception OBJECT is another matter — RESIDUE (6).

CLINIC KEYS (Phase 2, Tasks 2.1a–2.2, D9/D10; `clinics.py`, `ui/clinics.py`).
The key is typed or pasted into a password-masked field on the Clinics tab,
read once per Validate / Replace key press and cleared at once with
`setText("")` (which also clears the field's undo history); the tab never
shows it again and no status line carries it. The check is ONE client call
on a `TaskThread` whose key source is that typed key: `GET /user` (an active
login; its role is not read — D10 as amended 2026-09-27) → `GET /practitioners`
for that user (exactly one record, and it active — a login with no
practitioner record, such as a receptionist's, is refused) →
`GET /settings/public` for the subdomain, or — when Cliniko refuses that read
to the key — a web address the practitioner types, recorded UNCONFIRMED until
a note verifies with that key on that host. The worker never raises: every
failure is a named refusal carrying a reason code and a clinic id only. Only
a validated key is stored, and only in Credential Manager
(`ClinikoScribe/<clinic_id>` / `cliniko_api_key`); `clinics.json` holds
non-secret records and the contact email, loaded fail-closed (a damaged file
empties the registry and blocks every change rather than being overwritten).
Each clinic has an in-memory `clinic_rev`: a Replace key bumps it at dispatch
and at commit, every commit and Remove bump it, and a result commits on the
GUI thread only when its captured rev is still current — so a delayed result
after a Replace or a Remove, or a check whose key was replaced between its
requests, commits nothing and cannot restore a removed clinic. Remove takes
a second, confirming click and is refused while the live session is linked
to that clinic (its `EncounterContext` names the clinic id; an unlinked
session blocks no Remove). A key field left empty (or blank) is its own
refusal, `KEY_MISSING`, before the key-shape check, on Validate and Replace
key alike. While a draft write holds that clinic (the live linked session's),
Replace key is refused too — the Clinics tab shows the write's own
`write_in_flight` line (Remove is already refused: the writing session is the
live linked one) — and in the other arrival order a Write click is refused
while a Validate or Replace key for that clinic is in flight (`clinic_busy`)
— so both requests of a write read the same stored key (draft-write D3, D9).
THE RETIRED DEFAULT-SOURCE SETTING (draft-write D14, retired by D15 on
2026-09-30): a record written while the per-clinic `default_source` setting
existed still loads — a `ClinicRecord` before-validator drops the field when
it holds either of the setting's two values, and the next registry write
omits it; any other value still fails `extra="forbid"` and the file loads
EMPTY with its load problem set (fail-closed, as for any damaged file). An
older build (Phases 3–6) reads a file this build wrote, since the field was
optional there. Write
order, so no failure leaves a key at rest that the registry does not list: a
new clinic writes the file, then stores the key (a failed store deletes
whatever it may have written, then rewrites the file without it — if either
step fails the clinic stays listed for Remove); Remove deletes the key, then
rewrites the file. Residue: a
Replace whose file write fails leaves the NEW key in Credential Manager under
the OLD record (the rev is bumped so nothing pending commits; the stored
practitioner id is then compared with the note's practitioner link at every
note verification, so a note of the new key's practitioner is refused
`wrong_practitioner` until the clinic is re-validated); a new clinic whose key store fails and whose cleanup
(the key delete or the file rewrite) also fails stays listed — with no key,
or with whatever the failed store wrote — until Remove; the typed key has
two lifetimes, both never zeroed, as (2): as a Python `str` it is held in
the dispatched request until the result is committed and the request
dropped (the check thread's closure keeps no reference, round 15 MED-006),
and separately the line edit's own storage, which `setText("")` releases
but does not zero, may keep the bytes until Qt or the allocator reuses
them, whatever the commit does.

NOTE VERIFICATION (Phase 3, Tasks 3.1–3.6, D3/D4/D11; `encounter.py`, the
checkout in `ui/main_window.py`). `verify_note_context` runs on a worker
thread and never raises: it refuses a note whose URL host is not the clinic's
recorded host before any request, then makes ONE client call whose key source
reads Credential Manager once (`KeyStore.retrieve`; a failed or empty read is
the named refusal `key_unavailable`, not an exception). That call is
`GET /treatment_notes/<id>` — the answer's own `id` must be the requested
note's, or it is `answer_unreadable` (H3 round 47 SEC-002: an answer for one
note's URL carrying another note is never verified, and never written back
over the requested note), the note's patient link must equal the URL's
patient, the note must be an open draft (`draft` true, `finalized_at`,
`archived_at` and `deleted_at` null), its practitioner link must equal the
clinic's recorded practitioner — then `GET /patients/<id>` and, when the note
links one, `GET /bookings/<id>`. Every assumption about those answers' shape
sits in one commented block (Task P.1, clinic 1; clinic 2 owed); an answer
without it is `answer_unreadable`. Outcomes: VERIFIED (a context of ids and a
timestamp), `unverified_offline` (a connection failure, timeout, 5xx or 429 —
ids only, never a write target), or a named refusal carrying a reason code
only. The patient's display name (control and format characters replaced,
one line, at most 120 characters) and the appointment time travel as a
separate `NoteDisplay`, in memory only: no model, record, log line or file
holds them — with ONE exception since the privacy-professional-controls plan:
at Complete the display name the app holds for THAT session (matched by
session id: the bridge's verified Start display, else its live
re-verification, else a checkout's Verified result — D5) is written into the
session's Past-sessions entry label, encrypted under the entry's key, and
nowhere else ("Privacy and professional controls" below). Phase 3 showed them nowhere; since Phase 4 the Chrome bridge
shows them — on the Session screen and in `state`, for a verified note only
("The Chrome link" below). A result is applied on the GUI
thread only when it is the one the current checkout dispatched (request
identity) and, for the ledger, only for the current connection generation,
the current report run, the same target and an unmoved `clinic_rev`; its
per-note throttle reuses a VERIFIED outcome for the same note, connection
and `clinic_rev` for at most 60 s (never a refusal or an offline outcome),
and drops expired entries — with their display strings — at the next
report. THE RATE (round 57 SEC-009, practitioner decision 2026-09-28;
`ui/bridge.py`; the bridge's checks only — a checkout's one re-verification
is a practitioner action outside it): no two verification calls START less than 1 s apart — a
check inside that spacing waits in its kind's slot, where a newer check of
the same kind replaces it, and a single-shot timer starts it; nothing sleeps
on the GUI thread, a waiting check keeps the tags the stale-result guard
checks, a waiting REPORT check starts only while the ledger still awaits it
(`VerificationLedger.awaits`; codex round 65 PR-LOW-350 — a tab that closed
or moved on while it waited leaves no call behind, whether it waited inside
the spacing or behind a running check), and the window's close waits for it
like a running check. THE COOLDOWN (draft-write D13): one per-clinic
`encounter.RateLimitLatch`, owned by the main window and handed to the
bridge, is shared by the three paths that make note calls — the bridge, the
checkout re-verification and the draft write — so a 429 any of them sees
stops the others too; each reads and records it on the latch's own clock.
After a
429 the clinic's bridge checks are answered `unverified_offline` WITHOUT a call for
60 s from that 429 (a fixed window: only a real 429 starts one, the
window's own answers never extend it, and `RateLimited.reset` is not read) —
the checkout shows the same rate-limited line without a call, and a Write
click is refused `rate_limited` (at the click, and again before the write's
`PATCH`, codex round 35 PR-MED-038); the Clinics tab's Validate / Replace
key is outside the latch (a practitioner press, three GETs);
recording stays allowed, and — as with any offline answer — the outcome
stands until the note is checked again (a new run, a reconnect or a clinic
change); nothing re-checks when the minute ends. Neither timer ever starts a
call on its own: the spacing timer (a precise single-shot timer) only starts
a check a report, a reconnect or a clinic change (Replace key / Remove)
already asked for, so the offline contract (no call at startup or idle)
holds. Residue (H1 round 53 LOW-046, narrowed): the throttle still
bounds concurrency and now the rate — at most one logical call (up to three
GETs) per second — but a report for a different note still starts a new
run, an answer for a run that has moved on is still dropped before it can
be reused (SEC-008, recorded for H3a), and a refused or offline outcome is
never reused, so fast switching between notes keeps one call a second
running for as long as it lasts. The logging tripwire refuses `patient_id`, `treatment_note_id` and
`patient_display_name` field names in a log payload.

THE ENCOUNTER RECORD. `SessionController.start` refuses without a
`ConsentAttestation` (the practitioner's tick; the Session screen never
pre-ticks it and clears it after every Start) and binds it to the optional
`EncounterContext`: an unlinked consent names no note; a linked one names
exactly the context's note and, if it names a practitioner (the field is
optional, D3), the context's practitioner — `linked_consent`, the only
production constructor of a linked consent, always names it. The same rule
runs in `RecordingSession` and `EncounterRecord`, so no construction path
skips it.
Start writes `encounter.enc` (consent plus context, ids only) under the
session key with AAD `encounter:<session_id>`, after `key.dpapi` and before
any audio, for EVERY session, linked or not; a failed write refuses the
start. It is decrypted on checkout only (Critical Constraint 7) — a
recovered session opened for checkout, or an Unreviewed session opened for
review, whose adoption is its checkout (OPEN FOR REVIEW below) — plus ONCE
per Unreviewed session at app start to rebuild the reminder index (ids only
kept; the one start-up exception); the recovery listing learns only whether
the file exists, and the sweep and the periodic refresh never read it. A
missing or unreadable record reads as "consent unavailable": that session is
treated as unlinked and has no write target. The record is the
session's and goes with its key — at Complete (every Complete also removes
the session directory), Discard or expiry — and is never copied into a
Past-sessions entry. Since the privacy-professional-controls plan the
durable evidence is the session's AUDIT ROW, written at Start before
anything else of the session exists: the consent time and text version,
`linked`, the verification state and the clinic, practitioner, user, booking
and treatment-note ids — never the patient id or a name — kept 7 years, with
the write's outcome and the deletion added as they happen ("Privacy and
professional controls" below). Its
consent is the practitioner's tick on the Session screen or the panel's box
as relayed by the extension (pipe residue (1)(a) below): what it records is
that the tick was given, not that consent was gained.

THE WRITE-BACK GUARD (Constraint 6). `writeback_context` is the only route to
a `VerifiedTarget`: it needs a bound consent, a context whose clinic is
still registered with the same host and practitioner, and — for a live
session and a checked-out one alike — a re-verification of that same note,
dispatched under the clinic's CURRENT `clinic_rev`, that came back VERIFIED.
A verification made at Start or stored in `encounter.enc` is never enough on
its own (round 20 MED-012): a Replace key or Remove since then moved the rev.
Everything else is a named refusal. Its production caller is the draft
write's `draft_write.prepare_write`, which builds the guard's subject from the
live session's consent and context and the click's OWN note read (hop 1
below), so a checkout's stored result or the bridge's reconnect re-check is
never accepted (draft-write Constraint 3); `writeback_context` gains no age
bound — the freshness comes from each click making its own read. The main
window's `live_writeback_target` and `recovered_writeback_target` remain, but
nothing in production calls them; the crash-recovery checkout has no Note
tab and cannot write, and an Unreviewed session opened for review writes
through the live session's Note tab like any other. `encounter.py` itself has
no write method; the client's one write is reached only from `draft_write.py`
(CONFINEMENT above).

THE DRAFT WRITE (cliniko-draft-write plan, D1–D15; Phases 1–5 built
2026-09-29, Phase 7 — D15, append instead of refuse — built 2026-09-30;
`draft_write.py`, `ui/main_window.py` `_on_write_requested`,
`ui/note.py`). After the clinician Saves a ratified note of a LINKED
recording, one click on the Note tab's "Write draft to Cliniko" fills the
Cliniko draft treatment note the recording was started from — never a second
note, never anything but the note's `content`. What the structure enforces:
- ONE START. A write, and the reconcile of an earlier one, starts only from
  that button's slot, `MainWindow._on_write_requested` — never at startup, on
  a timer, from the sweep, on a clinic change or a reconnect (Constraint 2).
  `TestWriteSlot` pins, on the source, that the hop functions are named
  outside `draft_write.py` only there and in `_after_hop1`, that the slot is
  connected exactly once, to the Note tab's `write_requested`, and that the
  signal is emitted only by the button's click handler, which is connected
  only to the button's `clicked`. Residue: a programmatic
  `write_button.click()` or `clicked.emit()` elsewhere, and names built at run
  time, are outside a source pin — such a call still passes the handler's
  click-time checks and the slot's whole check order, so it can only write a
  saved, ratified, linked note.
- REFUSED BEFORE ANYTHING IS SENT, in the slot's order: a write already in
  flight; a click for a session that is no longer the live one; an unlinked
  (desktop-started) session; an unreadable write record, or one already
  `written`; the session lock; a recovery resume running; a Validate or
  Replace key for that clinic in flight; the clinic's 429 cooldown; a clinic
  no longer set up. Then the write RESERVATION is taken (the controller's
  existing custody reservation plus a writing marker, D9) BEFORE any worker
  starts, and — under it — a note from the test provider (`mock-…`, D10) is
  refused.
- A FRESH READ FOR EVERY CLICK, TWO REQUESTS (D3 as amended by D15). Hop 1,
  on a worker, is ONE client call with the key read once and ONE request,
  `GET /treatment_notes/<id>` — it IS the click's verification (the answer's
  own note id, the note's patient link, open-draft state and practitioner, as
  NOTE VERIFICATION
  checks them; no template, patient or booking read), so it sits as close to
  the `PATCH` as the design allows. Then, on the GUI thread, in
  `prepare_write`'s order: `writeback_context` over that read; the match on
  the note's own content; the write record's reconcile (the saved note's
  identity, then for an open attempt the match it was written under and its
  expected final answers); the repeat guard; the open-attempt retry check;
  the append and its digests; the full body. The `attempting` record is written to disk
  BEFORE hop 2 is dispatched (Constraint 5). Hop 2, on a worker, is its OWN
  client call, re-reading the same stored key (Replace key and Remove are
  refused for the writing clinic meanwhile), and makes the `PATCH` alone. The
  latch is read at the click and again before the attempt is recorded. The
  workers do network I/O only; the record, the reservation, the guard and
  every Qt call are on the GUI thread (Constraint 7), and any raise after the
  reservation releases it.
- MATCH, APPEND, BODY (D4, D7, D15). The note's own template profile is
  bound against the current config and matched to the note's OWN content by
  section and question NAME (the template itself is not read), each exactly
  once, one question per target, of the target's type; a missing, repeated or
  mistyped name, or a section the profile leaves unmapped by oversight,
  refuses `template_mismatch` and nothing is dropped silently.
  THE APPEND NEVER REPLACES AN ANSWER (D15): for each matched question the
  note writes to, an EMPTY answer — absent or null, or a string whose visible
  text is empty and that holds no content that is not text (a blank paragraph
  or whitespace is not writing) — receives the app's text; ANY OTHER string —
  typed text and the template's starting prompts alike, an image, a rule or
  an embed included — is kept BYTE-FOR-BYTE (never re-rendered or
  normalised; only the app's own text is NFC-normalised), then ONE empty line
  (`<p><br></p>` in a rich-text answer, a blank line in a plain one), then the
  app's text. The write refuses `note_unreadable` before any attempt — the
  app never appends to what it cannot read — for an answer that is neither a
  string nor null, HTML the parser cannot read, or an answer whose appended
  form would not read — to Python's HTML parser, which is the check — as
  the answer before it followed by the app's own lines (markup the parser
  sees hiding what follows it, such as an unterminated comment, or taking it
  in as its own text, such as an unterminated `<script>`; round 40 LOW-001
  and H1 round 45 LOW-001 — the record's two digests below must differ;
  markup a browser hides but the parser shows is residue (f)). A second
  recording's write into a note an
  earlier write or the clinician filled appends below it. Emptiness and every
  digest are over normalised VISIBLE text, type-aware: a `paragraph` answer
  is HTML and is decoded to visible text exactly once, a `text` answer is
  never decoded, then whitespace is collapsed, blank lines dropped and NFC
  applied. The body is the click's re-read `content` with only the matched
  answers set to their final answers (the app's rich-text part is one `<p>`
  per line, HTML-escaped, no other tag; the attestation checkbox question is
  never answered), so every other question, checkbox array, unknown field
  and untargeted answer round-trips as Cliniko sent it (confirmed on clinic
  1's template by P.1 Q4). A note with no writable content refuses
  `nothing_to_write` before any attempt; a lone surrogate refuses
  `answer_unreadable` before any attempt too.
- NO TEMPLATE, DEFAULT-SOURCE SETTING OR OWN-DEFAULTS FILE IS READ (D14
  retired by D15, 2026-09-30). The write makes no Cliniko template `GET` and
  reads no per-clinic default-source setting and no own-defaults file: the
  setting, the own-defaults loader and the Clinics tab's "Starting text"
  group are gone. What it still reads locally is the session's own records
  (`write.enc`, and the saved `note.enc` with its identity) and the current
  note config (to bind the note's template profile). An own-defaults file a practitioner made
  under `%LOCALAPPDATA%\ClinikoScribe\config\template_defaults\` is read by
  nothing; the app never wrote it and does not delete it.
- THE WRITE RECORD `write.enc` (D5; schema v2 since D15): one document per
  session, AES-GCM under the session key with AAD `write:<session_id>`,
  rewritten atomically at every transition — the attempt number, times, the
  profile's target ids, the SHA-256 of the saved note's plaintext
  (`note_identity`), per written target a SHA-256 digest of its normalised
  EXPECTED FINAL answer and one of its normalised answer AS READ by the
  attempt's click (an empty answer digests the empty text), a digest of
  where they were written (the matched labels, hashed), the body's digest and
  the outcome (`attempting`, `written`, `refused` with its reason,
  `unknown`). `prepare_write` keeps the two digests different for every
  written target; a schema-v1 record (Phases 3–6) reads as
  `record_unreadable`, fail closed. It holds ids and digests
  only — no note text, no Cliniko answer, no Cliniko id. It is written only
  through the write reservation (`with_write_custody`), and everyone else
  reads only its content-free status (`write_record_status`). The OUTCOME is
  decided by the HTTP answer alone: a 200 is `written` and never relabelled;
  a 401 is `key_rejected`; a 403 just after hop 1 verified the note with the
  same key is `finalised_before_write` (P.1's finalised leg); 404, 422 and any
  other 4xx but 429 are refused (Cliniko applied nothing), and so is a key
  that cannot be read or is refused before any request (nothing was sent); a
  429, a redirect, a 5xx, a timeout, a lost connection, a TLS failure, no
  readable status line or any unforeseen failure is `unknown`, and
  so is a trailing `attempting` left by a crash. There is NO automatic retry:
  the next click re-reads the note and, for an open attempt written under the
  same match (another — the profile changed since — is `write_uncertain`),
  first compares every targeted answer's normalised digest with the record's
  expected final digests — all equal (and at least one target) means the
  earlier write landed, recorded `written` with no second `PATCH`, so a
  resend never appends twice; all equal to the digests AS READ means nothing
  landed and nothing changed, and the next attempt is built from the CURRENT
  read; anything else is refused `write_uncertain` ("An earlier write may
  have reached Cliniko …"). A cleanly `refused` attempt (Cliniko applied
  nothing) is followed by a new attempt built from the current read, except
  as the repeat guard below says; once the click's read of the record shows an
  open attempt, the refusal lines that follow carry that sentence first (the
  lines `ui/models.py` `WRITE_UNCERTAIN_PREFIXED` names — not
  `write_in_flight`, which is that very write, nor a refusal met before the
  record read, nor the lines that already say the outcome is open). A `refused` / `finalised_before_write`
  record whose note re-reads as a DRAFT is refused `write_forbidden` before
  any `PATCH` (the repeat guard). Once any attempt exists the saved note is
  FROZEN for that session: Regenerate (including "Regenerate (replaces the
  saved note)"), a second Save and "Delete note and complete without one" are
  refused (`write_pending`; "Cancel review and regenerate" is already disabled
  once the note is saved) — decided on the Transcript screen for the live
  session, from the record's content-free status, so the controller's plain
  `complete` does not read the record itself (the enforcing gate is that
  screen, the only route a written session takes to it); an unreadable record refuses the write and shows its own
  line (`record_unreadable`), never a Cliniko rejection.
- COMPLETION IS SEEN (D6; Task 2.1 on P.1 Q5). A `written` outcome releases
  the reservation and completes NOTHING: the Note tab keeps Copy and says to
  reload the note in Chrome and press Complete once it shows there; Write
  stays disabled and no further request is made for that session. Only the
  Transcript screen's Complete, when the record reads `written` for THIS saved
  note, runs `complete_after_write`: under one controller lock it re-checks
  the reservation, the record and the saved note's identity, then fsync →
  decrypt-verify → the Past-sessions entry written, verified and published
  (privacy-professional-controls C1) → key deleted → in-memory key destroyed →
  the entry's marker and the directory removed best-effort → session refs
  forgotten — the same one store primitive every Complete path uses. Any refusal or failure keeps the key,
  the record and the queued session, and the next Complete retries. A custody
  action that fails on an error the app did not author (a disk, permission or
  store error) shows one fixed reason, "an unexpected problem on this computer
  stopped it", never the error's text or type: that text can name the
  session's directory (round 49 PR-LOW-044; `ui/models.py`
  `custody_refusal_text`, shared by every custody status line — Start, Pause,
  Resume, Finish, Save, Complete, Discard). The controller's own refusals and a
  capture error keep their authored text; a capture error adds only a device
  number and PortAudio's message, never a path.
- NAMED RESIDUES (P.1 on clinic 1, 2026-09-29, D15 and the reviews):
  (a) NO CONDITIONAL WRITE. Cliniko documents no version check on treatment
  notes, so an edit the clinician SAVES in Cliniko's editor between hop 1's
  note read and the `PATCH` — to any question, targeted or not — is
  reverted by the full body (P.1 Q6 reproduced both); for a targeted question,
  text typed in that window is lost, because the append was built from the
  earlier read. The window is kept to the time between two requests; the
  status line says to reload.
  (b) AN ALREADY-OPEN EDITOR WINS. Saving a Cliniko editor that was open
  before the write overwrites the written draft (P.1 Q5) — the reason
  completion waits until the clinician has SEEN the draft in Chrome; the app
  cannot detect it.
  (c) CLINIKO SANITISES RICH TEXT (P.1 Q1): the bytes it stores differ from
  those sent while the visible text survives one decode, so every comparison
  is over normalised visible text. It may rewrite or drop the append's empty
  separator paragraph (Task P.3 checks it by eye): if dropped, the app's text
  still lands below the answer with no gap — a format question, not a
  safety one — and reconcile is unaffected, since the digests drop blank
  lines.
  (d) "FINALISED" IS AN INFERENCE. A `PATCH` 403 is read as "the note was
  finalised before the write reached it"; a key whose Cliniko role may read
  notes but not edit them would show that line ONCE, and the repeat guard
  names it on the next click (`write_forbidden`).
  (e) AN EDIT BETWEEN AN UNKNOWN ATTEMPT AND THE RETRY. When a targeted
  answer changed after an attempt whose outcome is unknown — it reads as
  neither the expected final answer nor the answer as read — the app cannot
  tell the clinician's edit from its own write, so the retry is refused
  `write_uncertain` (fail closed); Copy remains, after the clinician checks
  the note in Cliniko.
  (f) AN ANSWER THAT HIDES OR SWALLOWS WHAT FOLLOWS IT, as Python's HTML
  parser reads it, refuses `note_unreadable` (round 40 LOW-001, H1 round 45
  LOW-001): the app's text would not show below it as its own lines, and the
  record's digests might not tell a landed attempt from one that did not
  land. The check is the parser's view, not a browser's: an element a
  browser hides but the parser reads as text — an unclosed `<div hidden>` or
  `style="display:none"` block, `<template>`, `<select>`, or (on Python
  3.12/3.13) a `<textarea>` / `<title>` left open — passes it, and the app's
  text would land inside it, unseen (H3 round 47 SEC-001). Cliniko's
  sanitised answers are not known to hold such markup, and seen completion
  (the clinician looks at the draft before Complete) is the net; the
  clinician copies instead.
  (g) AFTER COMPLETION THE SESSION IS GONE; CLINIKO HOLDS THE RECORD. The
  session — audio, transcript, `note.enc`, `encounter.enc`, `write.enc` — is
  gone with its key. What remains: the draft in Cliniko, which the clinician
  still finalises (the system of record); the session's Past-sessions entry
  (transcript, saved note, generated note — never audio or the write record)
  for the practitioner's retention setting; and its audit row, with the
  write's attempts, last outcome and written-at, for 7 years
  (privacy-professional-controls plan; "Privacy and professional controls"
  below). The write record's per-question digests do not survive Complete,
  so evidence of exactly what a write changed is Cliniko's own history.
  (h) KEPT MEANS KEPT: typed text and the template's prompts stay above the
  app's text, and the clinician removes any prompt they no longer want in
  Cliniko (the practitioner's choice, "Keep prompts, add below", D15).
  (i) The written note text leaves the machine in the request body, to
  Cliniko, inside TLS, by the clinician's click — the purpose of the feature.
  (j) The shipped template profile was corrected to clinic 1's recorded
  template (every writable question rich text); clinic 2's template is
  unverified until its own P.1, so there the write-time match is the check.

RESIDUE. (1) The TLS trust decision is the Windows store's: a root installed
there — a TLS-inspection proxy's, or a same-user attacker's — is trusted like
any other, and the key then crosses that proxy (inside boundary 2 for the
same-user case; OS hygiene otherwise). (2) The key is a Python `str` and the
Basic token is derived from it; neither can be zeroed, so "dropped" means the
module's own references go and the bytes live until the allocator reuses
them — the same residual as session keys (LOW-009); (6) lengthens that
lifetime. (3) Credential Manager access is
same-user by design (boundary 2): any process in the user's session can read
the key. (4) A key is typed or pasted into the Clinics tab; a paste passes
through the Windows clipboard, whose history and cloud sync are OS features
outside the app — the tab says so beside the field and asks the practitioner
to clear it there; the app does not clear it. (5) The contact email and the
requested ids leave the machine to Cliniko by design, inside TLS — and, for a
draft write, the note's whole re-read `content` with the ratified note's
text in its matched answers (THE DRAFT WRITE, residue (i)). (6) An
exception raised during a call keeps, through its `__traceback__`, every frame
it unwound through with that frame's locals — `raise … from None` removes the
chained CONTEXT, not the frame chain. While that exception object is alive
(bound past its `except`, stored by a caller, `sys.last_exc`, a debugger), it
references the key (an `InvalidKey` raised by `shard_of_key` before
`ClinikoClient.call` deletes its local), or the Basic token (`ClinikoCall._send`'s
local `headers`, in the traceback of every error raised through the transport
or `_interpret`), with the path, ids and response bytes — and, for an error
raised inside `write_draft_note`, the draft it was sending (`content`, and
the serialised body when the transport raised), which is note text — past
the logical call's end, until the exception is dropped (codex round 9
PR-MED-030; `draft_write.send_write` binds each one only inside its `except`
clause, which Python unbinds at the clause's end). Nothing
RENDERS them (SECRETS above); this is memory lifetime inside boundary 2, the
same class as (2). Clearing the frames in the client
(`traceback.clear_frames`) was rejected: it would also wipe the caller's
finished frames and still miss the pre-`yield` `InvalidKey`.

## The Chrome link: protocol v2, the named pipe, the bridge and the host's relay (Cliniko workflow safeguards plan D2/D4; BUILT at Tasks 4.1, 4.2, 4.4 and 4.5, 2026-09-27; Task 4.3 decided (b))

What exists: the v2 message contract, the app's pipe server, the bridge that
turns reports and commands into the app's decisions, and the native host's
two-way relay between Chrome and that pipe (data-flow map flows 1 and 19).
TASK 4.3, DECIDED (b) on 2026-09-27 under the practitioner's overnight
pre-authorisation to follow the executor's recommendation (revisable by the
practitioner): no peer-identity gate beyond the Windows session and the
user-only DACL; the same-user residue below is accepted as boundary 2. The
optional log-only tripwire was built: each end logs the other's executable
path at connect (`pipe_peer`), gating nothing.

PROTOCOL v2 (Task 4.1, both mirrors tested against `protocol/fixtures/`).
Enforced by the parsers: `context`, `command` and `state` require the nonce on
the Chrome wire and carry none on the pipe; every payload has a closed key
set (extra keys and an explicit `null` refused), strict booleans and
integers, and every string and array bounded by `meta.json`'s `limits`
(lengths in code points); Cliniko ids are digit strings matching
`^[1-9][0-9]{0,18}$`; a clinic host must be a `<subdomain>.<shard>.cliniko.com`
name. Shape rules: a host exactly on a Cliniko page, ids exactly on a
treatment-note page; `start` carries a target and the consent tick and no
session reference; `resume`, `finish`, `discard`, `resume_previous` and
`open_review` must name their session; only `discard` carries the confirming
second click; display strings only on a VERIFIED report; an unlinked live
session names no ids; an app that is not running reports nothing else.
RESIDUE: (1) these are SHAPE checks — a well-formed id can name any note,
and a well-formed host any Cliniko account; the allow-list check and the
verification are the bridge's. (2) The TypeScript mirror cannot tell `1.0`
from `1` (a JSON number); Python refuses the float.

THE PIPE (Task 4.2, `pipe_server.py`). Enforced by the OS: the name
`\\.\pipe\ClinikoScribe-<user SID>` (the developer build's is
`\\.\pipe\ClinikoScribe-dev-<user SID>`, `identity.pipe_prefix`; installation
plan D3 — its own host connects only to its own app) is created with
`FILE_FLAG_FIRST_PIPE_INSTANCE`, so a name already held — by an earlier app or
by anything else — makes creation FAIL (`PipeUnavailable("name_taken")`) and
the app never shares it; `nMaxInstances = 1`, so one client at a time;
`PIPE_REJECT_REMOTE_CLIENTS`; and a PROTECTED DACL with one entry granting the
current user (nothing inherited), with that user as the pipe's explicit
owner (round 57 SEC-013), and a Medium mandatory label with no-write-up,
no-read-up and no-execute-up, so a LOWER-integrity process of this user
cannot open it at all (round 57 SEC-014; a test proves a low-integrity
child is refused). Enforced by the code: inbound frames are
bounded at 1 MB (flow 1's framing) and must be nonce-free `context` or
`command` envelopes — anything else closes that connection; a frame queued
for one connection is never written to the next: a connection's writer only
takes its own connection's frame, and the server waits until the old writer
has ENDED before it disconnects, closes or accepts anything (round 57
SEC-016; a writer slow to be scheduled delays the next client, never
reaches it); stop is prompt in every state; a client that connects and closes
before the server's connect call does not end the server (round 57
SEC-002), a descriptor Windows refuses at creation is `create_failed` like
any creation failure (round 65), and any other end of the serve loop — a
failed connect, an unexpected error — reports the current connection lost
(a linked recording pauses) and then tells the app, whose Session screen
shows the "Chrome link unavailable" line (round 57 SEC-017). RESIDUE
(accepted under Task 4.3 (b) as boundary 2 — these are things the design
does NOT prevent, not controls): (1) the DACL admits
every process of THIS user — the same-user attacker of boundary 2 — which,
while the slot is free, can:
  (a) forge a `start` with the consent tick set — the app cannot see the
      side panel, so a forged tick is indistinguishable from a real one;
  (b) read the patient's name for a note id of its choosing through
      `state` — it reports that note on an allow-listed host, and the bridge
      verifies it with Cliniko and publishes the name;
  (c) hold the only pipe slot — the Chrome link is then down (the host sees
      the pipe busy and tells Chrome the app is not running);
  (d) drive `resume_previous` (built in Task 5.2) — it names the live
      session's reference and resumes that PAUSED session once a report
      names its own note, a report the same process can also forge; ids
      only, and the extension builds any URL from the allow-list;
  (e) read the Unreviewed banner for a note id of its choosing and send
      `open_review` for the reference it names (Task 5.5) — ids and a count,
      no name; it opens only that session on the desktop.
The same attacker already has more without the pipe: it can read the
Cliniko key from Credential Manager and query `/patients/<id>` itself, use
the microphone, and repoint the host registration. (2) A same-user process
that creates the name BEFORE the app, with the app's own DACL, PASSES the
host's verification (below: same session, same user, same DACL, same owner) — the host
then relays Chrome's reports and commands to it and its `state` to the
panel. The app, finding the name held, says the Chrome link is unavailable
on the Session screen, and both ends log the other's executable path
(`pipe_peer`) — a tripwire, not a gate. A squatter of ANOTHER user, or one
with any other DACL, fails verification: a hard error in the host. The user
check reads the token of the process id Windows recorded when the pipe was
CREATED, so another account in the same Windows session that created the
pipe with the app's DACL, handed the handle on and exited, then waited for
that id to be reused by one of this user's processes, would pass that check
— the OWNER check closes it (round 57 SEC-013): a standard account cannot
make another user's SID the owner of what it creates. (3) Administrators and SYSTEM are outside this boundary
(OS trust). (4) Since H3a (round 57 SEC-014) the pipe's Medium no-read-up
label keeps a LOW-integrity process of this user from opening it (Windows'
default label blocked only writes, so such a process could have received
`state` and held the only slot). What remains is (2)'s case for such a
process: one that creates the name BEFORE the app, with its own low label.
The host does not yet check the server's integrity level — extending Task
4.3's checks is the practitioner's, recorded for the next Task 4.3
revision.

THE HOST'S RELAY (Task 4.4, `native_host.py` + `pipe_client.py`). Enforced:
before a single frame crosses, the host VERIFIES the pipe's server — its
process runs in the host's own Windows (Terminal Services) session
(`GetNamedPipeServerSessionId` = the host's `ProcessIdToSessionId`; the
session, not the logon session — another account signed in to the same
session shares it), its
token user is the host's user SID, and the pipe's DACL is exactly the one
the app creates (protected, one ALLOW entry for that SID with no ACE flags
and the full access `GA` grants — type, flags, mask and SID all compared,
codex round 28 PR-LOW-142), and the pipe object's OWNER is the host's user
SID (round 57 SEC-013, practitioner decision 2026-09-28, extending Task 4.3
(b)'s checks; the app sets it explicitly, `O:<SID>` in `pipe_sddl`, so the
owner check adds no refusal of its own for an app started elevated — whose
default owner would be Administrators — which still meets the unchanged
user-check residue (2) below; a refusal is logged as `relay_refused` with
`state=owner`, no identifiers). A pipe that
exists but fails any check, whose check cannot be made (an elevated or
another user's server whose token the host may not query), or whose DACL
shuts the host out, is `ServerUnverified`: a typed `error` to Chrome and
exit 1, never a retry. The host opens the pipe with
`SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION`, so a server can identify
the host but never impersonate it. Chrome -> app, a `context` or `command`
is relayed only with THIS session's nonce (a wrong or missing one is the
fatal `bad_nonce`, as for `ping`), and with the nonce stripped; app ->
Chrome, only a valid nonce-free `state` is relayed, re-validated and
stamped with the nonce — anything else ends that pipe connection. A write
to the app that fails or times out ENDS that connection too (part of a frame
may be on the pipe): the message is dropped, never retried or followed on
the same stream, and the host reconnects. Only the relay thread closes the
pipe handle, after its read has settled; the host's shutdown and a failed
write only signal it (codex round 28 PR-MED-140/141) — even a shutdown
that outlives its join timeout closes nothing (the handle then goes when
the read settles or, at the latest, at process exit), and a retired or
stopped connection refuses every further write BEFORE any I/O, the retiring
write also making the link non-current at once (codex round 30
PR-LOW-160/PR-MED-161). While the
app is absent or the slot busy, the host sends `state{app_running:false}`
once and re-waits (one bounded attempt at a time); it exits on Chrome's
EOF. It logs message types, states and the peer's path — never a relayed
payload. RESIDUE: (1) pipe residue (2) — verification cannot tell this
user's programs apart. (2) An app run ELEVATED while Chrome's host is not
fails verification wherever Windows refuses the host a query of the app's
token (not measured on this host): the Chrome link then stays down with the
host's error until the app runs normally — fail closed.
(3) A message from Chrome while the app is absent is dropped, not queued;
the panel shows "not running" meanwhile.

THE BRIDGE (Task 4.5, `ui/bridge.py`). Enforced: the pipe thread only emits
queued signals, so every decision runs on the GUI thread, which alone
touches the controller and the screens; a new client or a disconnect bumps
the verification ledger's `conn_gen` and clears every report, so a result
tagged with an earlier `(conn_gen, seq, target, clinic_rev)` is dropped and
Start needs a fresh report on the new connection (D4); only the latest
focused tab's report feeds the ledger, and only a note page on an
allow-listed host is verified. `start` is refused unless its `state_rev` is
the last one sent, its target is that bound report, the report is verified
or `unverified_offline`, no session is active, no note review holds the
generation lease and a microphone is selected; an `unverified_offline` Start
records, and its note can be written only once a Write click's own read of
it verifies (Constraint 6; THE DRAFT WRITE above). `resume`, `finish`,
`discard` and `resume_previous` are refused BEFORE their slot runs unless
their `session_ref` is the live session's; `pause` needs no reference
(fail-safe); `open_review` names a RETIRED session and is refused unless its
reference resolves to a session still in the reminder index (the "Open for
review" paragraph below). Resume is governed by the pause rule's resume
check (next paragraph).
Refusals travel in `state.last_refusal`, never as `error` (Constraint 9).
The patient's name reaches `state` and the Session screen (a plain-text
label) only from a note Cliniko verified, and has TWO in-memory lifetimes
(codex round 29 PR-LOW-151): the BOUND REPORT's name is published while that
verified report stays bound — before any Start, and after a recording ends
— and is no longer published once the report changes (another note or tab,
a closed tab) or its `clinic_rev` moves; in memory it stays in the ledger's
reuse entry until that entry is pruned (at the first check dispatched after
its 60 s window) or the connection ends; the LIVE
SESSION's name (from the verification its Start used, and its reconnect
re-check's) is held for that session and goes when it ends (round 25
LOW-019). The bridge holds no logger. The reconnect re-check counts only
while its clinic is unchanged (D9): a Replace key or Remove voids it and
checks again under the current key, or reports the clinic gone (codex round
29 PR-MED-150). RESIDUE: (1) the consent tick is the extension's assertion
(pipe residue (1)(a) above). (2) The reconnect re-check of a linked live
session is shown on the Session screen only; the draft write does not read
it — each Write click makes its own note read (MED-012; Constraint 3). (3)
The name is on screen while the session records — the same exposure as
Cliniko's own page. (4) The snapshot is rebuilt every 500 ms and on every
event, so what the panel shows can trail the controller by that long; the
controller still refuses any transition that is no longer legal.

THE PAUSE RULE AND THE BLOCK (Tasks 5.1–5.3, `context_rules.py` +
`ui/bridge.py`; D5, D6). Enforced, by the app alone (Constraint 3): for a
LINKED live session, the bridge puts every report to the rule against the
tab that session is bound to — its bound tab changing note or patient,
leaving its note (any other page, including one off the allow-list) or
closing, and the focused tab reporting another note or Cliniko's login
page, each pause a recording and set the resolution block; so do pipe loss
and a new pipe client; machine suspend (`PBT_APMSUSPEND`, the main window)
and — D5 as amended by the practitioner on 2026-09-28 — the Windows session
LOCKING (`WM_WTSSESSION_CHANGE` / `WTS_SESSION_LOCK`) pause ANY recording,
linked or not (a linked one also gets the block). The Phase 5 smoke found
that a Modern Standby machine (S0 low power idle, no S3) never sent the
window the classic suspend broadcast, so the main window now registers for
both (`system_events.py`: `RegisterSuspendResumeNotification` with the
window handle, and `WTSRegisterSessionNotification` for this session) after
it exists, and gives both back on close, at quit and after a failed start;
a refused registration never raises and is shown on the status line and
the Session screen. A suspend that finds no recording — as one delivered
INSIDE a Start would, while the device opens — is looked at once more
after that dispatch returns, and pauses the recording the Start made
(round 57 SEC-021; nothing happens when there is still no recording). An
UNLOCK resumes nothing, and a suspend or lock also
ends a clicked "Resume previous" still waiting for its note's report, so no
report arriving behind a locked screen resumes. LOCKED UNTIL UNLOCK (codex
round 51 PR-MED-300): a Resume or "Resume previous" click already on its way
through Chrome when the lock arrived would otherwise be handled after the
lock's pause, so the lock message sets a flag during its own dispatch —
before the queued pause runs — and the one resume check every path runs
(the Session screen's Resume, the hotkey, Chrome's `resume`, a waiting
"Resume previous") refuses `locked` FIRST, for linked and unlinked
recordings alike, until `WTS_SESSION_UNLOCK` clears it; `resume_previous`
creates nothing while it stands, and every Start — a Chrome `start` and the
Session tab's button alike (the Session screen's start guard, installed by
the bridge) — is refused `locked` the same way (H1 rounds 53–54, MED-039 and
MED-052: a Start still on its way, or a click still queued, when the lock
arrived would otherwise begin a new recording after the lock's pause had run
at IDLE or QUEUED and done nothing). A VOICE ENROLMENT on the Practitioner
tab stops too (round 57 SEC-019, practitioner decision 2026-09-28, D5
extended to that tab; it replaces round 54 LOW-054's residue): the lock's
queued call and the suspend each press the tab's own Stop, whose worker
checks save nothing, and `begin_enrolment`'s blocker refuses a Record press
with the same `locked` / `lock_unknown` refusal from the lock message until
the unlock. The residue: a Stop that lands after the worker's final check
(the embedding done, the save begun) does not undo the save — the audio was
captured before the lock — and the tab shows the saved profile, which Delete
removes (round 28 PR-LOW-032). A
missed unlock cannot refuse Resume or Start forever: once the flag is five
seconds old a refused Resume or Start asks Windows
(`WTSQuerySessionInformationW`, `WTSSessionInfoEx` → `SessionFlags`) and
clears it only on "unlocked"; if Windows cannot say, the refusal is
`lock_unknown` and names the escape (lock and sign in again). An unlock
message is checked with Windows (round 57 SEC-020, built once this machine
was shown to read an unlocked session as unlocked): an unlock Windows
contradicts — a forged `WTS_SESSION_UNLOCK` sent by a program running as
the same user behind a locked screen — leaves the flag set, and the
re-check above clears it once Windows agrees. The residue (trust boundary
2, like the forgeable `WM_HOTKEY`; round 54 LOW-056): if Windows cannot
answer, the unlock is believed as delivered.
The young-flag window keeps a query racing the lock itself from reopening
the gap; a suspend or lock names the
block only when it starts one, so a block Chrome already put up for a
patient change keeps that reason. Every pause runs through the Session screen's slot
and shows a desktop cue. A PAUSED session only gains the block; nothing
else changes state. A tab that is neither bound nor focused never pauses,
and neither does a SEPARATE tab showing a page that is not Cliniko's (the
bound tab itself leaving its note for such a page does pause, as above;
codex round 34 PR-LOW-191). The rule never resumes. THE RESUME
CHECK: every Resume through the Session screen's slot (its button, a Chrome
`resume`, the pause hotkey) is refused, by name and before the controller
is called, for a linked session unless a pipe client is connected and the
focused tab's current report on this connection names the session's exact
clinic host, patient and note; a successful Resume clears the block and
binds the session to that tab. A tab is re-bound after pipe loss only to a
report naming those exact ids — a session is never re-bound to another
note. `resume_previous` resumes the paused session only when such a report
arrives within 30 seconds of the click on the same connection, and then
only through the same check. The Session screen's own Discard needs a second
click within 10 seconds for the same session; a Chrome `discard` carries its
second click in the protocol. A Start that retires a queued linked session
adds it to the Unreviewed reminder index (ids only, in memory, never
persisted) — even when that Start then fails to open the microphone, since
the retirement came first (H1 round 53 LOW-040) — and so does replacing a
recovered linked session's view without a Complete or Discard (from the
record its checkout already decrypted); a completion, a discard or an expiry removes that one entry and
its reference. RESIDUE: (1) the rule sees only what Chrome reports: speech
between a page change and its report — and anything said before a
navigation — is recorded into the session it was bound to (the plan's
pre-navigation-speech assumption), and a change the extension never reports
is never seen — the page-level limits (an in-page session-expiry dialog, the
report-to-pause latency, a page that hides the cue) are under "The Chrome
extension" below. (2) An UNLINKED (desktop) recording ignores
Chrome's reasons by design; only suspend, the session lock and the
hands-free reasons (the hotkey and the spoken phrase, below) pause it. (3)
Suspend and lock are Windows' notifications: a power cut, a crash or a
hibernation that sends none is crash recovery's case; a machine that sleeps
WITHOUT locking (sign-in on wake set to "Never") and without delivering the
registered suspend notification is not paused at all; there is NO suspend
flag like the lock's — no Windows signal says a person woke the machine
(`PBT_APMRESUMEAUTOMATIC` also fires on unattended wakes) — so on such a
machine a Chrome Resume or Start click in flight at the suspend can apply
after wake;
a refused lock registration sets no lock flag at all; and the audio captured
between the lock or suspend and the app handling it (the lock is a queued
call on the GUI thread; the suspend is handled in the message itself) is
recorded into the session. No automated test can prove Windows delivers
either message on a given machine — the real-dispatch tests prove only that
Qt hands a delivered one to the app; the live smoke is the proof. (4) Every report
and command is the extension's assertion (pipe residue (1)): a same-user
process on the pipe can forge the report the resume check and
`resume_previous` accept.

OPEN FOR REVIEW (Task 5.4, decided option (a): `SessionController.adopt_queued`
+ the Recovery screen's Unreviewed section + `ui/main_window.py`; D6).
Enforced: a session with a transcript is listed as Unreviewed and offers
"Open for review" and Discard — never "Resume processing", which
re-transcribes and unlinks a saved note. Opening ADOPTS it as the
controller's live queued session, so it is reviewed, saved and completed
through the one leased custody path that already exists; no second path
serves a non-live session. Adoption is refused while the generation lease
is held, while any discard holds a custody reservation, while a session is
recording, paused or processing, for a directory outside the app's sessions
root, and for the session already live; each refusal leaves the live session
untouched. The key is unwrapped once and destroyed in memory on every later
refusal. The consent and context come from `encounter.enc`, decrypted by
the adoption itself — it IS the checkout (Constraint 7); a missing or
unauthentic record refuses the opening by name, and no consent is ever
fabricated. The transcript and any saved note are read BEFORE anything is
installed, the note through `session_store.read_note` (the same verification
Complete uses): a note that fails is refused on the row and never
regenerated or overwritten. A saved note opens as it was saved, read-only;
changing it means "Regenerate (replaces the saved note)", which replaces it
only on that review's Save — and not at all once a draft write was attempted
for it (`write_pending`, THE DRAFT WRITE above). Copying it follows the
recorded copy flag and re-checks it carries no unresolved error. An adopted
linked session is re-verified with Cliniko from the record the adoption
decrypted (no second decrypt), for display only; it is written like any live
session, from the Note tab, whose click makes its own note read (MED-012) —
and a session whose record already reads `written` reopens with Write
disabled and completes only on Complete. Adopting retires a live queued or
failed session exactly as a Start does (its reminder entry and reference
kept); the adopted session's own entry leaves the index until it is retired
again. A recovered view replaced by a live transcript now releases its
checkout (scoped, by id), ending the hold-until-restart residue. THE BANNER
AND `open_review` (Task 5.5): at app start the reminder index is rebuilt by
decrypting each Unreviewed session's `encounter.enc` once (Constraint 7's
one start-up exception; its key unwrapped for that read and destroyed at
once; a record that cannot be read is skipped and the session stays on the
list), and each indexed session is given a D2 reference. While the focused
tab reports a note with indexed recordings, `state.banner` carries the
newest one's reference, the host, the note id and the count — never a
patient's name (a retired session keeps no display string). `open_review`
is refused before anything runs unless its reference still resolves in D2's
registry to a session still in the index — a click after that entry was
completed, discarded, expired or opened is refused, never redirected to "the
newest session" — and while a review holds the lease or a session is
recording, paused or processing (round 32 LOW-023: named before the window
moves); then the window comes forward (the taskbar flashes where Windows refuses focus) and exactly that
session is adopted as above. RESIDUE:
(1) while adopted, a session is the controller's own queued session and is
protected from the 24 h sweep, like any review in progress (retention
schedule, the 24-hour rule); the listing's age filter means a session whose
age is ESTABLISHED past its window is not offered for opening — one with no
readable timestamp at all is listed regardless of age (round 47 PR-LOW-001;
the sweep owns that case) and its shown expiry is provisional (codex round
34 PR-LOW-192). (2) The expiry warning and the
on-close list (the Unreviewed rows, the live queued session and an open
recovered checkout) are stat-derived (the sweep's own `session_expires_at`); they
name only an 8-character id prefix. (3) The on-close list refuses the first
close and accepts a second within 10 seconds; a Windows shutdown that
delivers one close event is refused once — the sessions stay on disk under
the 24 h rule either way. (4) The banner and `open_review` are the
extension's report and click (pipe residue (1)): a same-user process on the
pipe can learn that a note it names has an unreviewed recording (ids and a
count, no name) and open that recording on the desktop — never for another
session than the one its reference names.

HANDS-FREE AND WARNINGS (Tasks 7.1–7.3, `hotkey.py`, `voice_commands.py`,
`ui/main_window.py`, `ui/bridge.py`; D7, D8). None of the three is a new way
to act on a session: each reaches only what a Pause or Resume button already
can, or nothing. Enforced:
THE HOTKEY — Ctrl+Shift+F9 is reserved with `RegisterHotKey` for the main
window by `app.main` alone (a test's window reserves nothing; tests use a
fake registrar), and given back on close and at quit. `nativeEvent` acts only
on a `WM_HOTKEY` carrying the app's id while the chord is reserved, and
re-delivers it as a queued call, so nothing runs inside Windows' message
dispatch and nothing raises into it. A press while RECORDING pauses through
`pause_for` (the desktop cue; no block — a hands-free reason is not a context
reason); while PAUSED it asks the Session screen's guarded Resume — the
resume check above, with no bypass: a linked session resumes only on a
current report of its own note — and a refusal is shown with a taskbar
flash; in any other state it does nothing. It never starts, finishes,
discards or opens anything. A refused registration is a status: the status
line, the Session screen and `state.hotkey` (the panel says the hotkey is
unavailable) show it.
THE SPOKEN PAUSE — "scribe pause" is matched as whole words in each live
window (so "prescribe, pause" and "scribe paused" do not match) and counts
only when the phrase's FIRST word starts at or after the last Resume's
captured-audio time plus one capture chunk — never by a window's end time,
since a window can span a Pause and a Resume. It can only PAUSE, through
`pause_for` (nothing while paused, finishing or idle); the words stay in the
transcript. Whether it works for the recording (a live transcriber attached
and not failed) is shown on the Session screen and in `state.spoken_pause`.
THE WARNING — a closing phrase followed, in the same window or within three
windows, by a greeting (the lists and the count are constants in
`voice_commands.py`, pinned by tests) raises `new_consultation` once per
recording: a desktop line, a taskbar flash and `state.warnings` while that
recording is live. It never pauses, blocks, finishes or changes a session.
The panel shows only warning codes it knows, as text.
RESIDUE: (1) the hotkey is a GLOBAL input: anyone at this Windows session's
keyboard can press it from any window, and any program of this user can
send the app's window a `WM_HOTKEY`; either does exactly what the Pause and
guarded Resume buttons do, and resuming a linked session still needs its
note's current report (which a same-user process on the pipe can forge —
pipe residue (1)(d)). While the app runs, the chord is taken from every
other program (Word's Ctrl+Shift+F9 is the known clash). If Windows ever
re-created the main window's native handle, the reservation would be lost
while the status still read "on" (not observed). (2) The phrase is heard from
ANYONE in the room — the speaker is never checked — and from any audio the
microphone picks up; it can only pause. The pause comes when live
transcription reaches the phrase: a few seconds after speech stops, and up
to about half a minute plus the transcription time when speech runs on;
what is said in between is recorded. A missed or mis-transcribed phrase
does not pause (the hotkey and the buttons remain). A phrase begun within
about a second of a Resume is ignored (the cutoff's one-chunk margin), and
Whisper's word times are estimates. (3) The warning is a phrase heuristic: it misses
consultations that end or begin in other words and can fire on a goodbye
then a greeting within one consultation — a cue, never a control; the pause
rule's patient-change reasons and the practitioner's Finish are the
controls.

## The Chrome extension: service worker, page script and side panel (Cliniko workflow safeguards plan D1/D2/D13; BUILT at Tasks 6.0–6.5, 2026-09-28)

What exists: the service worker (`background.ts` wiring `hub.ts`, `context.ts`
and `connection.ts`), the page script on Cliniko pages (`page.ts`) and the
side panel (`panel.ts`, `panel-view.ts`) — data-flow map flow 20. THE
EXTENSION REPORTS AND THE APP DECIDES: nothing below is an enforcing control
for the pause, Start, Resume or write-back; those are the app's (the pause
rule and command checks above, and the write-back guard).

Enforced by the manifest (`extension/src/manifest.ts`, pinned by
`manifest.test.ts`): the permissions are `nativeMessaging`, `alarms`,
`sidePanel` and `scripting` — no `tabs` — and the only host permission is
`https://*.cliniko.com/*`, so a tab's URL is readable only while it is on a
Cliniko host; the page script is declared for that pattern in the top frame
only. Enforced by the code:
REPORTS — `ContextReporter` (`context.ts`) is inert until the app's first
`state` gives it the allow-list; it reports only tabs on an allow-listed
host, classified from the URL alone (the page's DOM is never read), sends
the page kind, host and — on a treatment-note URL — the two ids, never a URL;
a tracked tab that leaves the allow-list is reported once as `not_cliniko`
with no host, a closed one as `closed`, and a tab never on an allow-listed
host is never reported. The page script reads only `location.href`, on a
500 ms heartbeat while its host is allow-listed (the backstop for an in-page
navigation Chrome's tab events miss); the worker uses that href only when its
host equals the sender tab's own host (`hub.ts` `pageMessage`).
SENDERS — a message from a page script is taken only from this extension's
content script in the TOP frame of a tab whose URL is on a Cliniko host, and a
block command only while the app runs and that host is allow-listed; a page
script can send only Finish previous or Resume previous for a `session_ref`
and `state_rev` of the shape the protocol allows — NEVER a discard, which
the worker refuses from a page whatever it carries (round 57 SEC-003,
practitioner decision 2026-09-28; `hub.ts` `pageMessage`, `blockCommand`).
Discard comes only from the side panel (two clicks) and the desktop. The
side panel's port is accepted only from this extension's own panel page, not
a tab (`panelConnected`); Start is relayed only with the consent tick and a
target of the protocol's shape (`panelMessage`). The page script's buttons act
only on a TRUSTED click (`event.isTrusted`), and it takes slices only from
this extension's worker, never from a tab (`page.ts` `onClick`, `onMessage`).
Every command also passes the extension's own protocol mirror before it is
sent. "Resume previous" navigates only to a URL built from an allow-listed
host and two ids of the id shape (`context.ts` `noteUrl`), and navigates an
existing tab only when that tab is already on an allow-listed Cliniko page —
otherwise it opens a new tab.
PER-TAB SCOPING (D2) — `sliceFor` (`context.ts`) is the only producer of what
a page tab is told: the frame colour and, while a block stands, the block.
The recording's patient's name is in a tab's slice only when the recording
belongs to THAT tab's own clinic host; a block for another clinic's recording
names that clinic by its label and carries none of that patient's name or
ids; the name of the patient on the tab itself is added only when the bound
report is that tab's and Cliniko verified it. A page tab never receives the
report, the live session, the banner or a refusal; the side panel (an
extension page Cliniko cannot script) receives the whole snapshot.
RENDERING — every string from the app is set with `textContent`, never parsed
as HTML, in the panel and in the page script; the page script draws inside a
CLOSED shadow root on its own element, styled through the CSSOM. Nothing is
written to `chrome.storage` or any browser storage, and nothing is logged but
the host's disconnect diagnostic (no payload).
LIFECYCLE (D13) — the page script is inert (it says hello, then draws and
reports nothing) until its slice says its host is allow-listed, and returns to
inert — frame and block removed, slice and any name dropped, href reports
stopped — when the host leaves the allow-list or the app stops. After an
install or update the worker re-injects the page script into open Cliniko
tabs (`scripting`, Cliniko hosts only), and the panel says "Restoring the
safeguards on this tab…" until that tab's script says hello; an orphaned old
copy tears itself down.

RESIDUE (things the design does NOT prevent — none of them is a control):
(1) THE CUE IS NOT A CONTROL. Cliniko's own page can hide, cover or restyle the
frame and the block for as long as it likes; the heartbeat only re-attaches a
REMOVED element and never restyles one. While the block shows it takes the
pointer, but keyboard input — Cliniko's own shortcuts included — still
reaches the page. The app's pause rule and command checks are the enforcing
controls. A hidden or covered block STILL TAKES the pointer (round 57
SEC-003): a script running in a Cliniko page (an XSS in Cliniko) can raise
the block itself — a `pushState` to another note on the bound tab — hide it
or put a decoy over it, and collect real clicks on its buttons, which check
only that a click is trusted, never that the button was visible. What such
clicks can reach is now Resume previous (which resumes only once the
session's own note is reported in the focused tab, and never behind a lock)
and Finish previous (which ends the recording into review — nothing is
deleted). The block no longer carries Discard, and the worker refuses a
page's `discard` (practitioner decision 2026-09-28), so a Cliniko page can
no longer destroy a recording.
(2) DETECTABILITY. The build tool adds a `web_accessible_resources` entry for
the page-script module on `https://*.cliniko.com/*` with `use_dynamic_url:
false` (see `extension/dist/manifest.json` after a build), so a page on any
Cliniko host can tell that the extension is installed by requesting that
file; while a frame or block is drawn, the page can also see the page
script's own element (its `data-cliniko-scribe` attribute), though not the
closed shadow root's content through the DOM. The file carries no data.
That element exists only while a frame or block is drawn, and the frame is
drawn on EVERY allow-listed tab — another clinic's included — so any
allow-listed Cliniko page can watch it come and go and learn when a
recording is live or paused, though not whose (round 57 SEC-005). These
claims hold for `npm run build` only: a `vite` serve build widens the
web-accessible entry to every file on every site and loads the worker's
code from localhost, so the extension's `dev` script was removed (round 57
SEC-004).
(3) WHAT A CLINIKO PAGE CAN SEE. The closed shadow root keeps the drawn text
out of the page's DOM queries; it is not a boundary against the page — the
name is rendered on screen. Per-tab scoping is what bounds a name to the
clinic whose own Cliniko account already holds it.
(4) AN IN-PAGE SESSION-EXPIRY DIALOG does not change the URL, so it reports
nothing and pauses nothing; signing in again through it leaves the recording
bound to the same note.
(5) PRE-NAVIGATION SPEECH AND LATENCY. Speech before the next patient's note
is opened (the greeting at the door), and during the report-to-pause latency
— Chrome's tab event, the worker, the host's relay, the pipe and the app's GUI
thread; for a navigation Chrome's events miss, up to the page script's 500 ms
heartbeat more — is recorded into the session the tab was bound to. The
latency is not measured (Task P.2 observes it). Write-back still needs a
verified note, and no session is ever re-bound to another patient.
(6) THE LOGIN PAGE is recognised by the path `/users/sign_in` — UNVERIFIED on a
live account. Any other sign-in path reads as "another Cliniko page": the
recording's own tab leaving its note still pauses, but another tab brought
to the front on such a login page does not pause.
(7) ONE CHROME PROFILE. The native host is registered per Windows user, so
every Chrome profile of this user that has the extension can start a host,
but the app's pipe takes one client at a time. A second profile's host finds
the slot taken and reports `app_running: false`, so its panel says Clinic
Scribe is not running, with a hint that another Chrome profile may be
connected (the protocol carries no profile signal). When the first profile's
link ends, the second's waiting host can connect: a NEW pipe client, which
pauses a linked recording (the pause rule) and needs fresh reports. Two
profiles are refused one at a time, never mixed; using two profiles at once
is not supported (Accepted Assumption, practitioner 2026-09-27).
(8) CRASH DUMPS. Chrome's crash reporter can write a minidump of a crashed
renderer, side-panel or service-worker process into the Chrome profile; such
memory may hold a patient's name (and Cliniko's own page content), and Chrome
uploads crash reports only when the user has allowed it in Chrome's settings.
Chrome's dumps stay outside the app's custody and are not measured — an
accepted residue (privacy-professional-controls plan, Excluded, gate
disposition 2026-10-01: the extension holds display strings only, never audio,
transcripts or keys); keeping Chrome's crash-report upload off on the clinic
machine is an operating rule. `scribe-app`'s and `scribe-host`'s own crash
dumps (Windows Error Reporting) are the same class for everything those
processes hold; since that plan they are excluded per user by the register
script ("Privacy and professional controls" below, EXCLUSIONS), with its
named residues.
(9) CHROME'S MEMORY. A name lives in the worker's latest snapshot, the panel's
view and a page script's slice while it is shown (flow 20); a same-user
process that can debug Chrome, or DevTools opened on the extension, can read
it — boundary 2.
(10) The no-storage, text-only and no-logging claims are pinned by
`extension/src/sinks.test.ts`, a TEXT-MATCHING guard over the production
files that names what it cannot see (a name built at run time, other routes
to a prefix-dependent name); lint's `no-implied-eval` is the syntax-aware
check for dynamic code, and code review the control for the rest.
(11) Every report and click the extension relays is its assertion — pipe
residue (1) above.

## Privacy and professional controls (privacy-professional-controls plan, PLAN.md Phase 6; BUILT 2026-10-01)

THE REVERSAL. Until this plan, Complete destroyed everything of a session and
the draft in Cliniko was the only copy. At the practitioner's request ("like
Heidi") every non-mock Complete now KEEPS the session's transcript, saved note
(unless the path deletes it) and generated note (when readable) — never its
audio — in a Past-sessions entry, for a
retention the practitioner chooses (default: until they delete it); every
session also leaves a content-free audit row for 7 years. Two long-lived
stores of clinical and ids-only data now sit beside the session store, under
the same same-user DPAPI boundary (boundary 2).

THE PAST-SESSIONS ARCHIVE (`past_sessions.py`; D1, D3, D6; C1, C4).
- Layout: `past_sessions\<id>\` with the SAME file names a session uses
  (`transcript.enc`, `note.enc`, `generated.enc`), so the existing readers
  work unchanged, plus `label.enc` (AAD `past-label:<id>`). Each entry has a
  FRESH AES-256-GCM key, DPAPI-wrapped with the description `ClinikoScribe
  past-session key`, which the unwrap verifies: no session, audit, profile or
  style key opens an entry, and an entry key opens nothing else. Deleting the
  entry's `key.dpapi` is its cryptographic deletion (D3); there is no
  archive-wide key.
- What is kept (D6, the SOURCE-DERIVED set): the transcript always; the
  generated note whenever the session held one; the saved note whenever
  present and not deleted by the path — never on Complete without a note or
  Complete deleting the saved note. NEVER audio (C4: the source key, which
  also encrypted `audio.enc` and any superseded temporary file, is still
  deleted), `encounter.enc`, `write.enc`, `saved-provenance.enc` or an audit
  id. A MOCK session keeps nothing (audit `not_kept_mock`): the transcript's
  model, the generated note's provider or the saved note's provider starting
  with `mock`, casefolded (the mock transcriber records `MockSpeechProvider`).
  Its Complete is a destroyer too: any entry an earlier, non-mock attempt
  published for the id is removed key-first BEFORE its key goes, and a failed
  removal refuses the Complete with the archive's message, key kept (H1 round
  32 LOW-002).
- Archive before the key (C1, D4). Inside `complete_session`, after the
  transcript and note verification and BEFORE `delete_session_key`, the entry
  is staged under `.staging\<id>\`, then FULLY verified through its own key
  read back from disk — the exact file set, the label, and every plaintext's
  SHA-256 against the source bytes, through the existing readers — and only
  then moved into place, carrying the content-free marker `pending`, replacing
  any earlier entry for the id key-first. Any failure up to there raises
  `PastSessionWriteError` ("Complete failed: the Past-sessions copy could not
  be saved. No key deletion was performed — try again, or Discard."): the key,
  the QUEUED state, the lease and the write reservation are kept and Complete
  can be retried. The earlier refusals (an UNCLEARED live transcriber, a
  failed note verification) still run first. A session whose header id is not
  its directory name is refused there with the key kept (round 11 LOW-001).
  After `delete_session_key` (THE boundary) nothing is retryable: the
  in-memory key is destroyed and the controller makes its terminal transition
  whatever follows; removing the marker and the directory is best-effort, and
  a marker left behind shows "Completed. The Past-sessions copy will appear
  after the next check." (never "No key deletion was performed").
- One entry per id, and only after a Complete (C1's ordering rule). An entry
  carrying `pending` while its source `sessions\<id>\key.dpapi` exists is
  PENDING and never listed. Every NON-Complete destroyer of a source session —
  `discard()`, `discard_recovered`, the recovery list's Discard, the sweep's
  `expired`, and a DEAD key's `orphan_gc` — removes that id's entry key-first
  BEFORE it deletes the source key (`remove_pending_entry`, through the
  sweep's `before_destroy` for the sweep); a failed removal keeps the source
  key (Discard is refused: "discard refused: an unfinished Past-sessions copy
  of this session could not be removed. Nothing was deleted - try again."; the
  sweep keeps a dead key that tick). An entry path whose link status cannot
  be read counts as a FAILED removal, never as "a link, nothing to remove"
  (H1 round 32 LOW-001). So a `pending` entry whose source key is gone
  can only follow a Complete that reached its key deletion: the Complete's own
  `commit` removes the marker, and when it could not, `reconcile_pending` — at
  start-up and on every sweep tick — commits it, ONLY on a CONFIRMED-absent key
  (`FileNotFoundError`; an inaccessible key is neither absent nor dead:
  nothing is committed or deleted). `clean_staging` runs at every start-up and
  sweep tick whatever the retention setting. Links and junctions are never
  followed inside the store: refused for removal, skipped in listings and
  staging, never committed through (round 13 PR-LOW-010). The SESSIONS store
  follows the same rule since H3 round 35 (SEC-002): a session-id-named link
  under `sessions\` is never swept (`link_refused`, logged by that code), its
  key never deleted through it and Discard refused (`SessionLinkError`, key
  kept), and it is never offered on the Recovery list. Link status is read
  with `os.lstat` (a symlink, or a junction's mount-point reparse tag) —
  `is_symlink` / `is_junction` report an unreadable status as "not a link" on
  Python 3.13+ (SEC-001) — and an unreadable status refuses like a link. The
  archive ROOT and the sessions ROOT themselves are not checked — a junction there is the same-user boundary's
  residue (boundary 2), and relocating the data folder is the location
  check's question (EXCLUSIONS below).
- The generated note (`generated.enc`, D2) is the FIRST body the review
  showed, written under the generation lease and replaced on regeneration,
  with the provider, style and — captured at render time — the language-model
  id and prompt version. The saved note's model ids come from
  `saved-provenance.enc`, written first inside Save's custody action and used
  only when its digest names the note being completed (otherwise `unknown`),
  so a Complete never stamps today's constants on yesterday's note.

THE NAME (D5). The patient's name is written in ONE place at rest: the
entry's `label.enc`. It is resolved by the UI at the Complete click, matched
by session id, from what the app already holds in memory — the bridge's
verified Start display, else the name a Verified live re-verification of
that session found (remembered for the label only, until the session ends —
a later reconnect no longer loses it; it is never shown in Chrome), else its
current live re-verification, else a recovered or adopted checkout's
Verified result — never persisted at Start (`EncounterRecord`
stays ids-only), never in the audit row, the CSV or a log; otherwise the
label reads "Name not available", or "Desktop recording (no Cliniko note)" for
a desktop Start.

THE PAST SESSIONS TAB (`ui/past_sessions.py`, Qt-free lines in
`ui/past_sessions_view.py`; Flow 5). Opening the tab lists the entries
(decrypting each `label.enc` once); LEAVING it drops the opened entry's text
and every name from every panel. An opened entry shows its generated and
saved notes side by side, the write outcome read from the audit row, "Copy
saved note" — the SAVED note only, through the one clipboard placement and
its three Windows formats (Phase 3A surface 4), gated on the copy flag and no
unresolved error — and "Show transcript"; every panel is
`NoTextInteraction`. Hide names masks the LABEL with "Patient hidden".
Delete now is two clicks within 10 s on the same entry, key first, recorded
`deleted_early`; it is worded for a recording made in error only (the wrong
patient, a test, or one recorded without consent) — the wording is the limit,
nothing in the code tells an error from any other entry. THE 7-YEAR MINIMUM
(practitioner decision 2026-10-02): the retention setting is "Until I delete
them" (the default) or "7 years" — nothing shorter; a settings file holding a
shorter window an earlier build offered (1, 7, 30 or 90 days, 1 year) loads as
7 years (a before-validator mapping only a genuine integer of exactly those
values, so the strict type check still refuses `true` or `1.0`), the tab
says so until the next save writes 7 years, and any other value fails closed;
`sweep_report` refuses a window under 7 years before any read (`too_short`,
logged `retention_too_short`, nothing deleted, never a raise). The app does
not know a patient's age: the warning tells the practitioner to choose
"Until I delete them" for a patient who was a child (kept until they turn
25). Choosing 7 years from "Until I delete them" asks, saves, then sweeps;
an unreadable settings file deletes nothing by age, hides names and refuses
a Hide-names change until an explicit retention choice replaces it. Every
line carries a date, a label name and authored words only; a failure maps
to its store's authored sentence through ONE function
(`past_sessions_view.failure_reason`), and an error the app did not author
reads the one fixed line — never a code, a path or exception text (C3). The
retention sweep (start-up, then at most hourly on the 15-minute timer) uses
the app's ONE shared store, decrypts each label's date once per process,
does nothing under "Until I delete them", keeps undated and future-dated
entries, and records each deletion `expired` (C7: by session id only).

THE AUDIT RECORD (`audit.py`; D7, D8, D9; C2, C3).
- Layout: `audit\key.dpapi` — one store key, description `ClinikoScribe
  audit key` — and one row per session, `audit\YYYY-MM\<id>.enc`, AES-GCM with
  AAD `audit:<id>` (a row renamed onto another id fails), filed under the
  practitioner's LOCAL calendar month; rewritten read → change → atomic
  replace. A month folder that is a link (or whose link status cannot be
  read) is never read, written through or pruned — a Start that would write
  into one is refused (`unavailable`) and an update counted (H3 round 35
  SEC-003); a row file over 64 KiB is unreadable and never read whole
  (SEC-005).
- Content-free BY CONSTRUCTION (C3): `AuditRow` is `extra="forbid"` and every
  string is pattern-constrained — Cliniko and clinic ids, the session id,
  `Literal` outcome codes, refusal CODES and model TOKENS with no space. There
  is no field for a patient name, patient id or any text. The distinctive
  field names (`past_session`, `note_provenance`, `consent_confirmed_at`, and
  `generated.enc`'s `generated_text`) are log-tripwire markers.
- C2: `begin` writes the row at Start BEFORE `_retire_locked` and before
  anything of the session exists; the real write is the check, and its
  failure refuses Start with `AuditWriteError` (a `SessionControllerError`, so
  the screen shows its authored text and Chrome gets the existing `failed`
  refusal) with the previous QUEUED session still installed and nothing on
  disk. Every failure after a successful `begin` marks the row `start_failed`.
  Every later update — the write's durable transitions and pre-send refusal
  codes (Task 1.4), Complete's models and outcomes, Discard, expiry,
  `orphan_gc`, Past-sessions events — goes through `update`, which NEVER
  raises: a failure is counted, logged as `audit_update_failed
  detail_code=<stage>` and shown on the Past sessions tab, and the custody
  action goes ahead.
- Fail-closed store: a NEWER-schema row is kept byte for byte, never
  rewritten, and pruned only with its month; an unreadable row is counted and
  never overwritten; an unreadable, dead or missing key (with rows present)
  refuses every write — and so every Start — until "Start a new audit record"
  renames the WHOLE store to a never-existing `audit.unreadable-<stamp>-<8
  hex>` and creates a fresh key (D9; nothing is deleted, no quarantine is
  reused; a key failure after the rename leaves the store absent for the next
  Start or reset to create).
- 7 years: a month folder is pruned once the month's end + 7 years + one day
  has passed, at start-up and every 24 h.

THE CSV. Export writes every readable row (no event codes) as UTF-8 CSV with
a byte-order mark (for Excel) wherever the practitioner chooses, through a save dialog. Every cell passes a
formula guard (a leading `=`, `+`, `-`, `@`, tab or carriage return gets an
apostrophe). It holds no name or text, but it is NOT encrypted and it carries
the Cliniko treatment-note, booking, practitioner and user ids, which
identify the appointment to anyone with access to that Cliniko account; the
tab says it is not encrypted. The export's status line never names the file.
Its temporary file is a fresh name in the chosen folder
(`.clinic-scribe-*.tmp`), so a file of the practitioner's own called
`<name>.tmp` is never overwritten or deleted (H3 round 35 SEC-004); the temp
file is removed on every path unless Windows refuses that removal, when it
stays and the tab shows its one export-failed line.

EXCLUSIONS (`exclusions.py`, `scripts/register-native-host.py`; D10; since
the installation plan also `packaging/scribe.iss`, its D6/D10).
- Windows Error Reporting, by channel (installation plan D10, Task 2.4):
  - the INSTALLED app: the installer writes `scribe-app.exe` and
    `scribe-host.exe` = 1 under `HKLM\SOFTWARE\Microsoft\Windows\Windows Error
    Reporting\ExcludedApplications` (machine-wide; uninstall removes them);
    the start-up check reads HKLM, then HKCU, and is satisfied by either;
  - a SOURCE checkout (the developer build): the register script writes, and
    reads back, the per-user values `pythonw.exe`, `scribe-app.exe` and
    `scribe-host.exe` = 1 under `HKCU\Software\Microsoft\Windows\Windows
    Error Reporting\ExcludedApplications` (what
    `WerAddExcludedApplication(..., FALSE)` writes); `--unregister` removes
    only those three values. `pythonw.exe` is needed because the venv
    launchers start the BASE `pythonw.exe` as a child.
- Backup and snapshot (installation plan D6, installed app only): the
  installer writes one `REG_MULTI_SZ` value `ClinikoScribe` under each of
  `HKLM\SYSTEM\CurrentControlSet\Control\BackupRestore\FilesNotToBackup` and
  `...\FilesNotToSnapshot`, holding `$UserProfile$\AppData\Local\ClinikoScribe\
  sessions\* /s` and `...\logs\* /s` — the live sessions and the logs ONLY.
  These are REQUESTS that some Windows backup and snapshot tools honour, in
  part and not all (residue (g)); Past sessions, the audit record, the voice
  profile, the learned style and the configuration stay backup-eligible by
  the practitioner's choice, because those are long-lived records whose only
  other copy would otherwise be none. The developer build's folder is never
  covered.
- At start-up, before the window is built, `startup_exclusions` (best effort,
  never refusing start-up): marks the channel's data folder
  (`%LOCALAPPDATA%\ClinikoScribe`, or `ClinikoScribe-dev` for a source
  checkout) and every folder beneath it not-content-indexed; checks,
  READ-ONLY, where the data
  folder resolves (`realpath`) — inside `%OneDrive%` / `%OneDriveCommercial%`
  / `%OneDriveConsumer%`, on a `\\` path or a remote drive, or inside
  `%APPDATA%` each shows a warning, any other unusual place is logged by code
  only; checks the channel's WER values and the RUNNING program's file name;
  and, in the installed app only, checks that both backup values hold both
  patterns (`check_backup_exclusions`; a missing or short value is the
  warning "… not marked to be left out of Windows backups and snapshots (a
  best-effort setting) — reinstall Clinic Scribe.", an unreadable one "could
  not check").
  The warnings show on the Status tab and the Past sessions tab and never stop
  recording; each is logged by its code only. Every attribute, drive-type,
  environment, path-resolution and registry call goes through an injected
  `WindowsLayer`, and tests never reach the real one (a sentinel); the folder
  walk itself uses `os.scandir` and the link checks directly. A second
  conftest sentinel pins every test's models root (`install_layout.models_root`)
  to an empty temporary folder, so no test stats this computer's models; only
  the resolver's own tests opt out (`real_models_root`), and a real-ML leg
  re-pins to the dev models root (installation plan Task H.6).
- Exception hooks: `sys.excepthook`, `threading.excepthook` and
  `sys.unraisablehook` in BOTH processes log only `uncaught_exception
  error_code=<type name> detail_code=main|thread|unraisable` (a thread's
  `SystemExit` is silent, as Python's own hook is) — no message, traceback, `exc_info` or locals; the
  main hook drops `sys.last_*` so an uncaught exception's frames are not kept
  alive; the replaced default hooks are NOT called, so nothing prints the
  message or traceback to the console. A handler that fails while writing any
  log line reports only `--- Logging error (<type>) ---` on stderr, never the
  exception being handled (`logging_setup.QuietHandlerErrors`, round 23
  PR-MED-020). `faulthandler` is not enabled.

C5: every audit and archive call runs on the GUI thread (none on the capture
worker). C8: none of this opens a connection; the offline contract is
unchanged.

NAMED RESIDUES.
(a) THE SAME-USER BOUNDARY NOW GUARDS LONG-LIVED STORES. A Past-sessions
entry can live indefinitely and an audit row 7 years, each protected only by
DPAPI current-user custody: any process of this Windows user can unwrap their
keys while they exist (boundary 2), for as long as they exist — a far longer
window than a session's 24 h.
(b) NTFS UNLINK. Delete now, expiry and the audit prune are plain deletion,
not forensic erasure (Phase 2 item 2).
(c) "UNTIL I DELETE THEM" WITH NO BACKUP. The default keeps every entry
indefinitely on this PC and this Windows login only. A dead disk, a lost
profile or an administrator's reset of the Windows password (which breaks
DPAPI) loses every entry; the entries are then listed as unreadable — kept,
never deleted by age and never readable again (Delete now still works on
them; the tab limits it by wording to a recording made in error, round 40
PR-LOW-034). Passphrase-protected backup/restore is deferred.
(d) EXPIRY ONLY WHILE THE APP RUNS, and it trusts the wall clock: an entry
can outlive its setting while the app is closed (deleted at the next start),
and a clock jumped forward can expire entries early (as the 24 h sweep can).
An entry whose date this account cannot read is never deleted by age (the
tab says so, says it is still kept, and limits Delete now to a recording
made in error — every read-failure line carries that limit, round 40
PR-LOW-034).
(e) HIDE NAMES MASKS THE LABEL ONLY. A name spoken in the transcript or
written in a note is shown as kept. An unsaved Hide-names choice (the file
could not be written) lasts until the app closes.
(f) THE CSV IS OUTSIDE CUSTODY — unencrypted, wherever it was saved, holding
Cliniko ids that identify appointments (THE CSV above).
(g) BACKUP AND SNAPSHOT EXCLUSIONS ARE BEST-EFFORT AND PARTIAL. Since the
installation plan the installer sets HKLM `FilesNotToBackup` /
`FilesNotToSnapshot` for the live sessions and logs of the PRODUCTION folder
(EXCLUSIONS above), so those files are only MARKED to be left out. What
honours the marks: Windows Server Backup and wbadmin honour
`FilesNotToBackup`, partly by deleting matching files at restore, and System
Restore does not; `FilesNotToSnapshot` is best-effort and not applied to
`vssadmin` snapshots or Previous Versions; third-party backup tools need
honour neither. Everything else in the data folder is deliberately
NOT covered (D6), and a source checkout's `ClinikoScribe-dev` folder is never
covered. Until the app is installed (Phase P) none of this is set.
(h) THE PAGEFILE AND HIBERNATION FILE may hold anything the process held in
memory, including an opened entry's text and names (BitLocker is the
mitigation, as for NTFS residue).
(i) THE `pythonw.exe` WER BREADTH (a source checkout only — the installed
app's exclusions name only its own two programs). The exclusion stops crash
reports for EVERY pythonw program of this Windows user, not only the app's
(practitioner-accepted). The documented console launch runs `python.exe`,
which is NOT excluded, and the app says so at start-up ("Crash reports are
not excluded for this launch (python.exe) — start the app with
scribe-app.exe."). Native crashes are not Python exceptions: WER is the
control for them, the hooks are not.
(j) NOT-CONTENT-INDEXED IS FOLDERS ONLY. A file written before its folder was
first marked keeps its old attribute until it is rewritten (session, log,
profile and configuration files from before this build); links and
junctions are skipped; it is a request other tools need not honour.
(k) THE LOCATION CHECK IS READ-ONLY AND WARNS; it never moves data or
refuses recording, and a folder outside `%USERPROFILE%\AppData\Local` for any
reason other than the three named is logged, not shown.
(l) VERIFYING ANY OF THIS FROM AN AGENT SHELL PROVES NOTHING: agent shells on
this machine are MSIX-virtualized for `%LOCALAPPDATA%` and HKCU
(`docs/lessons.md`); only a run from a normal terminal counts (smoke P.3; for
the installed app, the installation plan's Task P.1).
(m) THIRD-PARTY LOGGERS: a library logger with no handler of its own falls to
Python's last-resort handler, which prints WARNING and above to stderr —
outside the app's handlers and the quiet-error rule — with the TRACEBACK of a
library's `logger.exception`; a Python `warnings` message likewise prints its
file, line and source line. Both reach only a console launch: `scribe-app.exe`
(pythonw) has no stderr, so nothing is printed there (H3 round 35). An inherited
`PYTHONFAULTHANDLER` (or `-X faulthandler`) would dump file, line and
function names (no values) on a fatal error. Apart from those, a console
launch no longer prints the traceback or message of an UNCAUGHT exception
(the installed hooks write only its type name) — a debugging cost, accepted
for C3 (the log has the type name; round 37 PR-LOW-032).
(n) CHROME'S CRASH DUMPS stay outside the app (The Chrome extension, residue
(8)).
(o) AUDIT ROWS A CRASH LEAVES OPEN OR INCOMPLETE. A process killed between
Start's row and the session directory's creation leaves that row `pending` for
ever (nothing on disk for the sweep to end). A Complete killed after its key
deletion but before its own audit update is never recorded as completed (its
outcome is not guessed): if its
keyless directory is still there, the next sweep ends the row `orphan_gc`; if
it was already removed, the deletion state stays `pending`. If the entry's
`pending` marker was still there, the next reconciliation records `archived`;
if the Complete had already removed the marker but not yet written its own
audit update, the entry is listed in Past sessions while the row's
Past-sessions state stays `none` (a later Delete now or expiry still records
over it). The same holds for a Discard, and for the 24 h expiry, killed
between the key deletion and the audit update: the row is never recorded as
`discarded` / `expired` — `orphan_gc` if the keyless directory is still there,
otherwise `pending` for ever. The sweep records its results only after its
whole pass, so a kill during a tick can leave every session that expired in
that tick `pending`.
(p) AUDIT DATES. `session_date` is the practitioner's LOCAL calendar date
(every timestamp is UTC), so the month prune waits one extra day. A system
clock wrong AT Start dates the row by that clock (a date more than seven
years back would be pruned at the next start-up). The month prune trusts the
wall clock too: a clock jumped forward by seven years or more removes every
month it has passed, at the next start-up or 24 h tick — irreversibly (a
real seven-year gap since the last use is indistinguishable, so there is no
guard). A pre-audit session's
creation time before 2026-01-01 (or missing, or in the future) is untrusted
and its row is dated by the clock of the update that creates it. A Past-sessions event on a row the audit no longer holds (pruned, or
set aside by a D9 reset) creates a `pre_audit` row — dated by the entry's
start for Delete now, its completion for expiry, and "now" for a reconciled
commit.
(q) A TOKEN IS A WORD. The token pattern admits any single word with no
space, so what a caller puts in a token field is the caller's to keep
content-free; the only producers are the persisted model and provider names
and the draft write's refusal names.
(r) THE GENERATED NOTE CAN LAG. A regeneration after Save that is then
cancelled leaves the EARLIER generation's saved note beside the LATER
generation's body, and both are kept as they stand (D2, round 11 LOW-002); a
`generated.enc` write that fails and whose stale file cannot be unlinked
leaves an earlier generation's body to be kept; an unreadable
`generated.enc` is not kept and the entry reads "Generated note not kept".
(s) A KEPT TRANSCRIPT IS A HEALTH RECORD. Its retention and access duties
(state health-records law, APP 11.2 and APP 12, subpoena) are the
practitioner's; the tab's warning says so, and `docs/practice/` carries the
research and the practitioner's 2026-10-02 answer (7 years minimum) for the
independent review. What the app enforces is the floor on the SETTING (no
choice under 7 years, a legacy shorter value read as 7 years, the sweep
refusing a shorter window). It does NOT enforce: Delete now's "made in error"
limit (wording only — any entry can still be deleted early, recorded
`deleted_early`); the child rule (the app does not know a patient's age — a
"7 years" setting deletes a child's transcript at 7 years unless the
practitioner chose "Until I delete them"); the 7 years counted from the
entry's completion, not from the patient's last contact; and residue (d)'s
forward clock jump.
(t) OLDER READERS ARE UNBOUNDED. This plan's readers are size-bounded
(`generated.enc`, `saved-provenance.enc`, audit rows, the Past-sessions
settings file — H3 round 35 SEC-005); every reader from before this plan
still reads its file whole — every store's `key.dpapi`, `transcript.enc` and
`note.enc` (including a Past-sessions entry's, read through the same readers,
and the staged copy's own verification read), `encounter.enc`, `write.enc`,
the voice-profile and style stores and the configuration files under
`config\` (H3 round 36) — so a same-user process could plant
an oversized file to exhaust memory — a denial of service inside boundary 2,
not a disclosure.

## Installation (installation plan, PLAN.md Phase 7; BUILT 2026-10-02 → 2026-10-03 on branch `installation-build`, NOT YET INSTALLED)

What exists: a packaged (PyInstaller one-folder) build of `scribe-app.exe` and
`scribe-host.exe`, a per-machine Inno Setup installer (`packaging/scribe.iss`),
a release build script with a fail-closed bundle audit
(`scripts/build-release.py`), a CI release workflow with a build-provenance
attestation (`.github/workflows/release.yml`), a separately shipped model pack
checked against a committed manifest, and the developer build split off as
its own channel (`install_layout.py`, `identity.py`). What has NOT run yet,
so nothing below is proven on a real install: the hashed build lock, the
models manifest, a real build, the workflow's pins and first run, and the
installation on this computer (the plan's Phase P, practitioner-run from a
normal terminal). Everything here is the plan's D1–D12 and C1–C10;
data-flow-map flows 23–24 and the retention schedule's "Installation" rows
describe the same surfaces.

THE CHANNEL (D2). A packaged build is the PRODUCTION channel and a source
checkout the DEV channel, decided by `sys.frozen` alone
(`install_layout.is_frozen`, never an environment variable). Every production
identity keeps its value (C2): host name `com.scribe.cliniko_host`, extension
ID, origin, pipe prefix, data folder `ClinikoScribe`, keyring prefix, every
DPAPI key description and the mutex name — so the installed app opens the
existing data, keys and clinic entries unchanged. Only per-channel accessors
differ (`identity.host_name()`, `install_layout.data_root()`, …). Tests pin
the production channel by default, so the suite tests what ships.

THE INSTALL FOLDER (D1, D-I1). `C:\Program Files\ClinikoScribe`, installed
per machine with one administrator approval; its inherited ACL gives standard
users read and execute only (measured at Task 0.3). Enforced by Windows: a
standard-user process cannot change the program, the host manifest
(`{app}\com.scribe.cliniko_host.json`, `allowed_origins` = the production
origin) or `scribe-host.exe` — which RETIRES the launcher-hijack part of
boundary 2 for the installed app. Enforced by the code: a packaged build
started from anywhere else refuses before the log file, the instance guard,
any data folder or the main window (`install_layout.outside_install_folder`,
links and junctions resolved first; the app writes one type-name line to
stderr, when it has one, and shows "Clinic Scribe is not running from
its install folder — reinstall Clinic Scribe.", the host exits with one
type-name line on stderr, which Chrome does not show — Task 2.7). The one
earlier exit is `--self-check-offline`, the build audit's check, which opens
no window, log or data folder. RESIDUE: an administrator, or malware running
elevated, can change the folder; the location check is not an integrity
check; and the build is unsigned, so Windows verifies no signature at run
time (THE BUILD OF RECORD below).

THE MODELS (D5). The installer copies the model pack (a folder
`ClinikoScribe-models-<8 hex>` beside `setup.exe`) into `{app}\models`,
read-only to users. Every file's SHA-256 is compiled into the installer from
`packaging/models-manifest.json`: all are checked BEFORE anything is copied
(any mismatch refuses, "Nothing was changed"), and every copy is checked
AFTER — a damaged copy is deleted where Windows allows it (a delete that
fails is named, "damaged, and could not be removed"), the Finish page says
"Clinic Scribe is NOT completely installed … before you open Clinic Scribe"
and Setup exits 9, never its success code. RESIDUE: a damaged copy that could
not be deleted stays in `{app}\models` until Setup is run again; whisper and
silero are not re-verified at load (below), so the practitioner must not open
the app before that rerun. An upgrade whose installed models already match
skips the copy. At run time the language model and the speaker model are
re-verified against their pinned digests at every load; whisper and silero
are not (their integrity rests on the install-time check and the admin-only
folder). Contents: silero, whisper `medium`, the speaker model with its
CC BY 4.0 attribution notice (D-I2) and the language model.

THE INSTALLER (D8, C3). It writes the install folder, an all-users Start-menu
shortcut and HKLM only, never anything per-user: the Chrome link for the
production host name, the two
WER exclusions, the two backup/snapshot values (EXCLUSIONS above) and,
only if ticked, the clinic-only policy. It never launches the app (no `[Run]`
section; the Finish page says "Open Clinic Scribe from the Start menu"), so
the app never runs elevated; `SetupLogging=no`. It refuses while
`scribe-app.exe`, `scribe-host.exe` or `chrome.exe` runs, and FAILS CLOSED when
that check cannot run (WMI); it refuses any folder but D-I1; and an upgrade
or reinstall clears `{app}\_internal` and `{app}\extension` first, so those
two folders hold exactly the audited bundle (the top-level files are replaced
by name). RESIDUES: (1) the running-process check is by program name only;
(2) those folders are cleared before the copy and Inno's rollback does not
restore them, so an upgrade that fails part-way (a full disk — nothing checks
free space first — or a Cancel during the long model copy) leaves a program
that will not start until Setup is run again to the end; the data folder is
untouched.

THE OPTIONAL CLINIC-ONLY POLICY (D8). An unticked-by-default checkbox writes
`HKLM\SOFTWARE\Policies\Google\Chrome\NativeMessagingUserLevelHosts` = 0;
Chrome then ignores EVERY per-user native host (closing HKCU shadowing below)
and shows "managed by your organization". A value already present that this
installer did not write is left alone and never removed by this run; a box
ticked over such a value writes nothing, and the Finish page says the
setting was already set by something else. An unticked value this installer
set that could not be removed is said on the Finish page, and Setup exits
10 (round 27). RESIDUES: (1) an
upgrade that unticks the box removes the value only if an earlier run of THIS
installer set it, and Inno's uninstall log keeps that earlier
`uninsdeletevalue`, so a policy someone else sets AFTER such an untick is
still removed at uninstall; (2) the app does not read the policy, so with it
set the Status tab and the host log still read the per-user entries first:
they can name a per-user entry as the winner (and its verdict — "registered"
or "NOT registered" — and the per-user warning) while Chrome ignores it and
uses the installed link; (3) it must stay unticked on a computer that also
runs the developer build, whose Chrome link is per-user.

HKCU SHADOWING (D9). Chrome looks up a native host per user before machine
wide (confirmed on this computer at Task 0.2), and in each hive the 32-bit
registry view before the 64-bit one (from Chromium's source, not observed
here). The Status tab and the host log read the entries in that order
(`exclusions.WindowsLayer.native_host_entries`) and report the winning one
and every other; in a packaged build any per-user entry for the production
host name adds "Warning: a per-user Chrome link overrides the installed
one." A manifest or launcher path on a network share — in every separator
form Windows reads as one, the mixed `\/` and `/\` included (round 27: the
one test, `install_layout.is_unc_path`, normalises first) — is never opened or
stat'ed by the app or the host (H.4: no SMB I/O from their own start-up; the
host logs `host_manifest state=network_path` and the Status tab reads it as
not registered); Chrome itself would still open it when it launches the
host — part of the planted-entry residue below. RESIDUE — THE DUAL-USE COMPUTER: on a computer that is also a
development machine, a per-user production-name entry (today's source-run
registration, until Phase P step 2 removes it with `register-native-host.py
--unregister`, or one planted by a same-user process) silently wins over the
installed link. The warning names it but gives no remedy; nothing refuses
it; a reinstall does NOT remove it (the installer writes HKLM only, C3) — the
per-user entry is removed with `register-native-host.py --unregister` from a
source checkout, or by hand in the registry, from a normal terminal; the
clinic-only policy is the only control that closes it for good, and it is
off here. The dev build registers its OWN host name, so it never shadows the
installed link.

THE BUILD OF RECORD (D7). The `Release` workflow (manual, on `main` only,
`windows-2025`) installs the hashed build lock and the hash-pinned prose
wheel into a clean environment, builds PyInstaller from source at a pinned
commit with its bootloader rebuilt, builds the release extension into the
bundle, and only then runs the bundle audit (so no third-party npm code runs
after it, H.4), which fails closed: both programs and the shipped config
present, NO Qt networking file, the packaged app's offline self-check
passing with every offline variable set wrong within a time limit, and a
Defender scan where the runner allows one (a detection fails the build; C10:
never an exclusion). It then compiles the installer and uploads it; every
action the workflow runs is pinned to a commit and no shared cache is
restored into it (H.4); a second job, the only one
holding an OIDC token and running no command of its own, downloads that
upload and attests `setup.exe` and `SHA256SUMS.txt` with GitHub's
build-provenance attestation; `BUILD-INFO.txt`
records the commit and whether the tree was clean. RESIDUES: (1) THE BUILD IS
UNSIGNED: Windows cannot vouch for it, SmartScreen may warn, and its
integrity on this computer rests ENTIRELY on the practitioner running `gh
attestation verify` and `Get-FileHash` against `SHA256SUMS.txt` before every
install (`docs/release/pilot-builds.md`) — a skipped check proves nothing;
(2) the model pack is built once by the practitioner on their own computer
(`build-release.py --model-pack`), so its integrity rests on the committed
manifest the installer checks, not on the attestation; (3) a local build is
for spikes and the model pack, never the build of record, and is marked
`tree=DIRTY` when built from uncommitted work; (4) until the action pins,
the Inno Setup installer's SHA-256, the build lock and the models manifest
land, the workflow fails closed at the first step that needs them; (5)
GitHub attests only a PUBLIC repository, or a private one on GitHub
Enterprise Cloud. This repository was checked PUBLIC on 2026-10-03 (plan
Task 3.6 step 0, round 23), so attestation is available; it stays so only
while the repository stays public (or moves to Enterprise Cloud). Made
private without that plan, the attest job fails, no build is attested and
the first install check can never pass — the build of record then needs a
decision, never a skipped check.

THE DEVELOPER BUILD (D3, D4, C8). A source checkout keeps its data AND models
in `%LOCALAPPDATA%\ClinikoScribe-dev`, registers its own host
`com.scribe.cliniko_host_dev` per user (`register-native-host.py`, dev-only
since Task 3.7), answers only its own extension (built with `npm run build --
--mode dev`, its own key and ID, loaded in a SEPARATE Chrome profile) and
listens on its own pipe. Enforced by the code: it never reads or writes the
production data folder or models, with two named exceptions: the shared
`app.lock` (the instance guard above), and `register-native-host.py
--unregister`, which deletes the old per-user production-name key and the two
files that registration wrote in the production folder
(`com.scribe.cliniko_host.json`, `scribe-host.exe` — nothing else), as Phase
P's migration step. THE DEV WRITE GUARD (D4): in the dev channel "Write draft
to Cliniko" is refused before anything is read or sent (`dev_build_writes_off`)
unless "Allow Cliniko writes from this developer build" is ticked on the
Status tab (`config\dev.json` in the dev folder, off by default); note
verification and the Clinics tab's Validate still run. A production build has
no checkbox, never reads the file, and the refusal never applies there.
RESIDUES: (1) the guard is a setting the same user can tick — it prevents an
accidental write from a developer build, not a deliberate one; (2) THE
SHARED CREDENTIAL MANAGER NAMESPACE: both channels store clinic keys under
`ClinikoScribe/<clinic id>` (the keyring prefix is kept, D3/C2); their entries
stay apart only because clinic ids are random per data folder, and the
self-test's `test` entry is common to both; (3) both channels share the
DPAPI key descriptions, so either channel's process can unwrap the other's
keys — they are the same Windows user (boundary 2).

UNINSTALL LEAVES THE DATA (C4). Uninstall refuses while the app, its host or
Chrome runs, then removes the program, `{app}\models` and every HKLM value it
wrote, and NEVER `%LOCALAPPDATA%\ClinikoScribe`; it says "Your sessions, Past
sessions and audit record were left in your Windows profile, unchanged." — no
retention period, since nothing sweeps the folder while the app is
uninstalled (round 27). RESIDUE: everything in the data folder — Past sessions, the audit record, the
voice profile, the learned style, the configuration, the logs and any
unfinished session — and the clinic keys in Credential Manager stay until the
practitioner removes them; an upgrade or a rollback never touches them.

THE OFFLINE CONTRACT (C1) is unchanged: the installer makes no network
connection and the installed app downloads nothing. `scripts/check-installed-
sockets.py` watches the installed app's process tree for connections during a
transcription and a prose render (Phase P step 10, practitioner-run).

PACKAGED-BUILD ERRORS. A missing or damaged installed file names "reinstall
Clinic Scribe" instead of a developer script (Task 1.7,
`install_layout.FROZEN_REMEDY`). The packaged hardware check spawns the app
itself as its whisper worker (`scribe-app.exe --benchmark-worker` with an
exact argument shape and an environment gate, D11), which is its own exception
boundary (one type-name line, exit 1). RESIDUE: a source run's worker
(`python -m scribe_desktop.benchmark`) still prints a Python traceback to its
stderr on an exception — developer build only.

## Out of scope (tracked in PLAN.md phases)

Transcript prompt-injection resistance of the local ML note model (Phase 3B —
3A's provenance check already derives speaker roles from COORDINATES, never the
assertion's display `speaker` field, as the spoken-injection defence for
clinician-owned sections; the ML model's own injection resistance is 3B),
clinic 2's draft write (its template is unverified until its own test write;
the write-time template match is the check there — THE DRAFT WRITE residue
(j)), backup/restore of Past sessions (deferred by the
privacy-professional-controls plan), code signing (deferred by the
installation plan: the pilot build is unsigned, D7), an enforced allow-list of
programs (deferred), a Chrome Web Store listing (excluded), Defender
exclusions or any weakening of Smart App Control (excluded, C10: a blocked
unsigned build is a signing trigger), and the second clinic computer's
installation (the pilot plan).

## Review triggers

Re-review this model when: the practitioner revises Task 4.3's decision (b)
(the Chrome link, covered above, was built on it); the transcript becomes input to the local ML note model
(Phase 3B — 3A's non-ML template/autofill pipeline is covered above); real
Cliniko keys are first stored (the Clinics tab of the Cliniko workflow
safeguards plan's Phase 2 is built; the practitioner's first Validate is the
event); a note report from Chrome first reaches note verification on a real
install (the practitioner's first live smoke of Phase 4 — the relay and the
bridge are built and described above); the extension gains a permission, a
host pattern, a web-accessible resource or any browser storage, or the page
script reads anything but `location.href`; a second Chrome profile, a second
clinic machine or another practitioner is to be supported; the first write
of a new session type (a session kind other than a live or adopted linked
recording reaching "Write draft to Cliniko" — the crash-recovery checkout,
for one, cannot write today); the client gains a request shape, a resource or
a second write, or Cliniko adds a conditional write (a version field — THE
DRAFT WRITE residue (a) could then close); clinic 2's first draft write;
or the software is installed on the
second clinic machine — the installed build on it, which may be a clinic-only
computer where the optional policy and a different HKCU picture apply. For
the installation: the first real install on this computer (Phase P — the
installed app's Status lines, the `reg query` and `icacls` results and the
socket check are its evidence), signing the build, a change of the install
folder or its ACL, a new installer write (any key, value or folder), the
installer gaining a network step or a launch of the app, a change to what the
model pack contains, or the developer build sharing anything more with the
production channel. The local language model HAS landed
(note-learning-and-styles plan Phase 4, 2026-09-20, surface 17), so the next
trigger on that surface is a change of MODEL or of RUNTIME — a new pin, a new
quantisation, a different inference library, or a runtime installed by any
route other than the pinned hashed wheel. For the privacy and professional
controls: a field added to the audit row or the Past-sessions label, a new
file kept in an entry, a backup or restore of Past sessions (deferred), the
practice relying on Past sessions as part of the health record, a change of
the retention default, a second Windows user or machine reading the stores,
or the backup and snapshot exclusions widening beyond live sessions and logs
(they are built into the installer, residue (g)).
