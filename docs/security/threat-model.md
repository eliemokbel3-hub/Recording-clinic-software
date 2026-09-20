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

## Note learning and styles — Phase 0 stubs (surfaces 11–17; finalised at that plan's Phase H)

The note-learning-and-styles plan adds live transcription during recording,
practitioner-typed edits that can become learned rules, a learned writing style
derived from the practitioner's own past notes, and a local language model that
renders prose; boundary 2 is unchanged — the defended adversary is still outside
the user's Windows session and every new artefact inherits exactly that posture.
Only that plan's PHASE 0 is built (the contracts: consent v3, note schema v2,
the style store and its model, the settings file, the two shipped vocabularies
and the typed-wording filter), so each surface below states what is enforced
TODAY with its symbol and marks everything else "planned; enforced from Phase N";
these stubs are finalised at that plan's Phase H (task H3).

11. **Live transcription worker (D1–D3; C2, C7, C8, C9).** Planned; enforced
    from Phase 1 — none of it exists today, transcription runs only in the batch
    stage. What it will hold: the worker is fed plaintext PCM by a tee placed
    around the capture sink BEFORE encryption, so it never holds `SessionCrypto`,
    never reads the session store and never writes a file (C7); its per-window
    PCM, segments and embeddings stay in process memory and the PCM is dropped
    per window; Discard stops and joins the worker and confirms its buffers are
    cleared BEFORE the session key is destroyed (C7, D2); every failure — model
    load, "could not keep up", a tee error — names its reason on screen and the
    consultation falls back to the batch stage (C8); the live view is the same
    display-only transcript widget under the same `NoTextInteraction` rule and
    is cleared on Discard (C2); and no live segment reaches a log line (C9).
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
    defence belongs to lines that have a row).
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
    token under that same key; nothing else writes it, and a cancelled review
    writes nothing (C6). The review may only REMOVE: `build_style_profile`
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
    works with no voice profile at all). Reading is bounded to ONE decrypt:
    `refresh_style_profile_state` is the tab's only caller of
    `load_style_profile` — at construction and after a learn, a remove or a
    delete — and the summary line (`ui/models.style_profile_line`: a date and
    two counts, never a field's text) and both "Learned style" lists render
    from that one in-memory copy; no 5 s poll ever opens the STYLE store, and
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
    reads it into memory only — a `Path` must carry a `.txt` or `.docx` suffix
    (`SAMPLE_NOTE_SUFFIXES`; a `.pdf` is refused by name, "paste the text
    instead") and is bounded by `MAX_SAMPLE_NOTE_BYTES` (2 MiB, a stat before
    the read) and `MAX_SAMPLE_NOTE_CHARS` (200 000); a `.txt` is ONE
    `read_bytes` decoded utf-8-sig then cp1252, a `.docx` is opened through
    `python-docx` 1.2.0 (a pinned base dependency in `pyproject.toml`).
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
17. **The local language model and Check 5 (D6, D7, D8; C1, C4, C8).** Built:
    the carrier types. `note.py`'s `StyleRendering(section_key, prose_text,
    input_digest, verdict)` binds a rendering to the digest of its inputs and a
    validator refuses prose on a `failed` verdict (C4); `prose_text` and
    `style_renderings` are registered log tripwire signatures (C9);
    `note_config.PractitionerSettings` (`practitioner_settings.json`, default
    `clean`) holds the display setting outside `NoteConfig` and outside the
    config digest, and since Phase 3 the Practitioner tab's "Writing style"
    group writes it the moment a radio is picked (`ui/models.save_note_style`);
    `note.render_note(note, style)` is the ONE rendering path the display, the
    note artifact and Copy all go through (D7, `ui/models.format_note_body`),
    and with no rendering present it renders a prose style as `clean` per
    section — which is every note in this phase, since
    `ui/models.language_model_available()` is False until Phase 4, so the two
    prose radios stay disabled with their reason on screen and a saved-but-
    unavailable style is shown selected-and-disabled beside
    `style_fallback_line` (C8); and Check 5's connective allow-list ships as
    `config_defaults/prose_connectives.json` (`note_config.PROSE_CONNECTIVES`,
    refused at import by `_parse_shipped_vocabulary` if the packaged file is
    emptied, malformed or key-missing). Planned; enforced from Phase 4: the
    runtime installed ONLY as a prebuilt CPU wheel pinned by version AND SHA-256
    (`--require-hashes`, never a source build) — a second sanctioned network
    fetch beside `setup-models.py` — the ~2.5 GB instruct model pinned by
    SHA-256 and loaded from the local path only (C1), the prompt builder typed
    to refuse a `TranscriptDocument` (C4 — the model never sees transcript
    text), Check 5 as a fidelity GATE and not a certificate (a passing rendering
    is still read and ratified by the practitioner's Save), Save unavailable
    while a rendering is in flight, a stale rendering never shown, and every
    fallback named on screen (C8). The honest limit recorded in D8:
    `assert_offline_env` is NOT an enforcing control for this runtime — neither
    candidate reads a kill-switch variable — so the enforcing control will be
    the no-sockets integration test extended over a prose generation.

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
second clinic machine (Phase 7); or the local language model lands
(note-learning-and-styles plan Phase 4).
