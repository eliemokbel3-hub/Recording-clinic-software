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
   digested.
   **The app itself now writes ONE of these files (practitioner-profile plan
   Phase 5, D9 as amended 2026-09-16 — auto-learn, review later).** When a
   note is SAVED, `note_config.append_user_cues` appends learned phrases to
   the user `section_cues.json` (creating it from the shipped default if
   absent, so the practitioner keeps every shipped cue) and records each
   phrase's section and date in a sidecar `section_cues.learned.json` that
   the loader never reads; `delete_user_cue` removes one. What can be written
   is bounded by structure at five points, each a call site: (a) only the
   Note tab's add/move path enqueues a candidate (`ui/note.py`
   `_consider_learning`) and only after `note.spoken_by_confirmed_clinician`
   says the utterance is the CONFIRMED clinician's — a patient's, carer's or
   interpreter's line never reaches the learner, whatever the settings; (b)
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
   still refused); an exemption admits listed forms only, so a practitioner
   line opening with any other capitalised word ("Examination shows…",
   "Margaret…") is still refused as name-like and never teaches — visible as
   a "not learned" note, a refusal rather than a leak. The
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
   review warning, acknowledgeable, never a block; free-text editing of an
   assertion does not exist. Edits freeze at Save like proposal decisions,
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
   the CURRENT consent text verbatim (`ui/models.py` `CONSENT_TEXT_V2`,
   version `CONSENT_TEXT_VERSION`; the v1 text stays in the file as history)
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
    never a patient's line (the ownership test in `ui/note.py`
    `_consider_learning` over `note.spoken_by_confirmed_clinician`, pinned).
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
    carry an apostrophe and add no such homograph); the cue file and the
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
