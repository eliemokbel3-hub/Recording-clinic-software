# Threat Model (Phases 1–3A)

Scope: the implemented system — extension shell, native-messaging host,
registration chain, logging, credential/session-crypto foundations (Phase 1),
plus local recording, encrypted session stores with DPAPI key custody, and
local transcription (Phase 2), plus the local note pipeline — template
mapping, autofill/prefill proposals, per-assertion confirmation, content
checking, and the note review UI (Phase 3A; the ML note model itself is
Phase 3B and stays out of scope below). Clinical data now exists: audio,
transcripts, and the composed note artifact, encrypted at rest under
per-session keys; an UNPROTECTED recovery store expires at ~24 h (eligible at
24 h, destroyed by the next successful sweep), while a live or under-review
session is sweep-exempt (see the retention schedule for the exemption).

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

2. **The same-user attacker (ACCEPTED RESIDUAL RISK).**
   Malware running as the logged-in Windows user owns both endpoints. It can:
   - repoint `HKCU\...\NativeMessagingHosts\com.scribe.cliniko_host` at its
     own binary (registration hijack);
   - replace or edit the host manifest or the installed `scribe-host.exe` in
     `%LOCALAPPDATA%\ClinikoScribe\` (both user-writable);
   - modify the venv's interpreter or site-packages (code hijack through the
     host executable);
   - read process memory, including session keys and — in later phases —
     Credential Manager secrets accessible to the user session.
   No extension-side or pipe-side control changes this; message-level crypto
   would be theater against an attacker who owns both endpoints. **Cheap
   tripwire in place:** the host logs its resolved executable, module, cwd,
   registry-resolved manifest path, and the manifest's host-executable path at
   every startup, so a hijacked chain is visible in the log history. **Real
   mitigation** is Phase 7 packaging/signing plus normal OS hygiene
   (up-to-date OS, AV, no untrusted software in the clinic user session).

3. **Extension identity.** The pinned manifest `key` gives ID *stability*,
   not secrecy — for an unpacked extension the public key is visible by
   design. `key.pem` is gitignored; losing it means a new ID and mandatory
   re-registration. The Chrome Web Store will assign a different ID at
   Phase-7 publication (allowed_origins must be updated then).

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
  granularity — same-user access is by design (the host must read keys
  unattended in Phase 4).

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
   that blob IS the cryptographic deletion of the session's audio and
   transcript (deletion ordering: on Complete — fsync transcript, verify a
   decrypt round-trip, THEN delete the key; on Discard — key first, then
   best-effort store removal). Residual: any process in the user's session
   can call `CryptUnprotectData` on the blob while it exists — subsumed by
   boundary 2.
2. **NTFS unlink is not anti-forensic (ACCEPTED RESIDUAL, user decision
   2026-07-26).** `key.dpapi`, `audio.enc`, and `transcript.enc` are removed
   by plain deletion; free clusters, the USN journal, or VSS shadow copies
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
   The ONLY sanctioned network user is `scripts/setup-models.py`, a separate
   explicit setup process (SHA-pinned downloads).
4. **Clipboard / same-user UI surface.** The transcript-inspection view is
   display-only (`NoTextInteraction`) so clinical text cannot drift into the
   Windows clipboard (clipboard history / cloud clipboard sync) through
   casual selection. This is cheap defense-in-depth, not a boundary — a
   same-user process can still read process memory (boundary 2).
5. **Single-instance guard (named mutex) — convenience guard, NOT a
   boundary.** A per-user `Global\ClinikoScribe-app-<user>` mutex makes a
   second `scribe-app` show "already running" and exit before it constructs
   a controller or sweep (two instances over one sessions root produced
   real, confusing split-brain state in the 2026-07-28 live smoke). The
   guard fails OPEN on unexpected mutex errors, and a same-user process can
   squat the name — that is a denial-of-convenience inside boundary 2, not
   a data exposure.
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
   sweep and the recovery listing.
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
   (`template_profiles.json`, `autofill_rules.json`, `prefill_templates.json`),
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
   matters is downstream — nothing from config reaches `note.enc` without
   explicit per-assertion clinician confirmation of the exact shown wording, and
   config text rejects Unicode line/paragraph separators and bidirectional
   format controls so the confirmed wording cannot differ from what was
   digested.
2. **Clinician-asserted content in a clinical record.** A confirmed
   autofill/prefill proposal becomes a `NoteAssertion` and, once the note is
   saved, ratified content in the encrypted LOCAL DRAFT (`note.enc`). It is not
   yet a signed clinical record: copy-to-Cliniko is Phase 4+ and currently ships
   disabled, so in 3A the assertion becomes signed clinical-record content only
   after the clinician later finalises the note in Cliniko. The type model keeps
   this honest: `note_fill.py`
   emits proposals ONLY (typed return surface, pinned by test); a `NoteProposal`
   is a different type from a `NoteAssertion` and cannot be placed in a
   `GeneratedSection`; and a clinician-authored assertion without a confirmed
   `ConfirmationDecision` is unconstructable. Confirmation — not trigger
   presence, role attribution, or provenance — is the only thing that turns a
   proposal into record content; provenance proves attribution, never truth.
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
   plaintext is cleared when a new transcript loads over a stale note. No new
   on-disk plaintext and no new logging channel are introduced —
   the note models carry registered tripwire signatures, so a stray repr/dump is
   dropped by the log filter.
4. **The ratified copyable-note change.** The generated note is the app's first
   copyable clinical surface — but copy is bound to the Task 9.1 shipping gate
   and currently ships DISABLED (`ui/models.py`
   `COPY_TO_CLINIKO_ENABLED = False`). Even once that flag flips, copy
   additionally requires a fully ratified note (no pending proposal, no blocking
   error, saved, no unacknowledged review warning), enforced by one predicate
   (`ui/note.py` `_copy_ready`) applied to BOTH the copy button and the note
   panel's text-selection flags and re-checked at click time — disabling the
   button alone is insufficient because selectable text keeps native copy
   shortcuts. The transcript panel is never copyable regardless of the flag.

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

That residual is carried by per-assertion clinician confirmation of the exact
shown wording and by the clinician's own review and finalisation of every note
at signing (`PLAN.md`, Summary: "The clinician reviews and finalises every note
in Cliniko"), NOT by any automated grounding guarantee 3A does not have. The
note-pipeline custody surface itself is recorded in the `SessionController`
docstring: a per-session custody reservation serializes every custody consumer
under the shipped single-GUI-thread, queued-signal usage, and full
arbitrary-thread custody safety is a documented bounded residue for a future
dedicated hardening.

## Out of scope for Phases 1–3A (tracked in PLAN.md phases)

Transcript prompt-injection resistance of the local ML note model (Phase 3B —
3A's provenance check already derives speaker roles from COORDINATES, never the
assertion's display `speaker` field, as the spoken-injection defence for
clinician-owned sections; the ML model's own injection resistance is 3B),
consent workflow and recording indicators (Phase 5), the host↔app named pipe
(deferred from Phase 2 to Phase 5 — its consent/command flow is the real
consumer; the locked topology and pipe-hardening notes are recorded in the
Phase 2 plan), OneDrive/backup exclusions and audit records (Phase 6),
packaging/signing (Phase 7).

## Review triggers

Re-review this model when: the named-pipe host↔app channel lands (Phase 5,
deferred from Phase 2); the transcript becomes input to the local ML note model
(Phase 3B — 3A's non-ML template/autofill pipeline is covered above); real
Cliniko keys are first stored (Phase 4); or the software is installed on the
second clinic machine (Phase 7).
