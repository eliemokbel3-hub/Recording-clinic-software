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
   This control keeps the ML stack off the network; it says nothing about
   the Cliniko client, which is the app's ONE network-capable module and
   has its own surface ("Cliniko API client" below). Outside the app, the
   network users are two explicit setup-time steps the user runs:
   `scripts/setup-models.py` (SHA-pinned downloads) and the pinned
   prose-runtime wheel install (surface 17 of the note-learning section).
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
   plaintext is cleared when a new transcript loads over a stale note. The app
   introduces no new on-disk plaintext and no new logging channel (the one
   route out of its custody is the clinician's Copy of a ratified note, whose
   clipboard residue surface 4 names) —
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
   is never copyable regardless of the flag. **Residue once copied (named
   2026-09-27, Task 1.4):** a copy puts the ratified note's plaintext on the
   Windows clipboard by the clinician's own action, and from there it is
   outside the app's custody — it stays until something replaces it, any
   same-user process can read it (boundary 2), and Windows clipboard history
   and cloud clipboard sync, when the user has turned them on, keep it past
   the next copy or send it to the user's Microsoft account. The app neither
   clears the clipboard nor detects those settings, so keeping cloud clipboard
   sync off on the clinic machine is an operating rule for the clinician
   (`docs/security/intended-use.md`, current scope note), not a control.

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
    REFUSES `discard_session` with `SessionActivityError`, routes the
    recording to FAILED with key + chunks intact, and the next Discard
    retries), the three Complete paths and `_retire_locked` on a new Start
    (`_stop_live_locked`, the 1 s in-lock bound); the one caller allowed to
    ignore the verdict is `_fail_locked`, which destroys nothing. Finish seals
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
    the view closed is dropped, the view is cleared on the Session screen's
    Discard, the final document replaces it wholesale, and live segments
    carry `LIVE_SPEAKER_PENDING`, never a cluster label. LOGGING (C9): the
    worker holds no logger; the ONE new log record is
    `live_transcriber_stop_timeout` with the session id and state only, and
    the words of a posted window are `word_text` tripwire markers. Residue,
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
    every CI runner: CI installs `[dev]` / `[dev,ml]` and never the
    requirements file, so this gate is evidence from the practitioner's
    machine ONLY and a source-built copy on CI would merely skip; Phase H
    round 24). The
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
    a windowed process (`scribe-app.exe` is a `pythonw` launcher) cannot
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
    `LANGUAGE_MODEL_ABSENT_REASON` names the remedy (`setup-models.py --only
    language-model` plus the prose-runtime install). A saved-but-unavailable
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

## Cliniko API client (Cliniko workflow safeguards plan, D9; BUILT at Task 1.1, 2026-09-27)

The app's offline contract is now **no connection except Cliniko's API, and
none at startup or idle**. `scribe-app` holds exactly one network-capable
module, `desktop/src/scribe_desktop/cliniko_client.py` (flow 18 of the
data-flow map); the native host has none and never imports it. It has two
app callers, each making ONE client call on a worker thread in answer to a
practitioner action, never at startup, on a timer or while idle: the clinic
registry (`clinics.py`, Phase 2) on a Validate or Replace key press on the
Clinics tab (CLINIC KEYS below), and note verification (`encounter.py`
`verify_note_context`, Phase 3) — dispatched today only when the
practitioner opens a recovered session for checkout and its encounter record
names a Cliniko note, or when a clinic changes while that checkout is open
(NOTE VERIFICATION below). The Chrome-driven verification of a note report is
Phase 4's pipe; its GUI-thread ledger is built and unwired.

CONFINEMENT. Ruff TID251 bans `socket`, `http`, `urllib.request` and
`PySide6.QtNetwork` across `desktop/`; the ONE exemption is the client's
`http.client` import. `tests/test_cliniko_client.py::TestConfinement` pins the
count at exactly one, that no other module under `desktop/src` imports
`http`, `ssl`, `socket`, `urllib.request` or `PySide6.QtNetwork`, that the
native host's import closure never reaches the client, and that `clinics.py`
and `encounter.py` are the only modules that import it. Residue: these are SOURCE checks, so a dynamic import
(`importlib.import_module`) is outside them; the runtime check is the
no-sockets integration test (host, app startup and idle, capture,
transcription, prose), which asserts zero connections.

WHAT IT CAN SEND. `GET` only: `HTTPSTransport.request` refuses any other
method before a connection exists, the client passes only `GET`, and the
module has no write method (Critical Constraint 1: drafts only, by
construction, and this plan writes nothing). The host is
`api.<shard>.cliniko.com`, built ONLY from a documented shard taken from the
key's `-<shard>` suffix; a missing or unknown suffix, or a key with any
character outside the key alphabet (CR/LF included), is `InvalidKey` before a
request — never defaulted to `au1`. Ids in a path are validated as 1–19
digits with no leading zero. Headers are fixed: HTTP Basic auth (the key as
username, empty password), `Accept: application/json`, and
`User-Agent: Clinic Scribe (<contact email>)` with the email refused on CR/LF
or a failed shape check.

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

UNTRUSTED ANSWERS. A body is read ONLY for a 200: every other status is
final from its status line and headers, so a 401/403/404/429/3xx/5xx whose
body stalls or is cut keeps its own named error (and a 429 its reset) rather
than becoming `Unreachable` (codex round 8 PR-MED-012); the unread body goes
with the closed connection. A 200's body is read in pieces that never ask
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
verification or one Validate), shared by that call's requests, and on exit
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
session blocks no Remove). Write
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
`GET /treatment_notes/<id>` — the note's patient link must equal the URL's
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
holds them, and this phase shows them nowhere. A result is applied on the GUI
thread only when it is the one the current checkout dispatched (request
identity) and, for the ledger, only for the current connection generation,
the current report run, the same target and an unmoved `clinic_rev`; its
per-note throttle reuses a VERIFIED outcome for the same note, connection
and `clinic_rev` for at most 60 s (never a refusal or an offline outcome),
and drops expired entries — with their display strings — at the next
report. The logging tripwire refuses `patient_id`, `treatment_note_id` and
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
start. It is decrypted in one place — a recovered session opened for
checkout (Critical Constraint 7) — and the recovery listing learns only
whether the file exists. A missing or unreadable record reads as "consent
unavailable": that session is treated as unlinked and has no write target.

THE WRITE-BACK GUARD (Constraint 6). `writeback_context` is the only route to
a `VerifiedTarget`: it needs a bound consent, a context whose clinic is
still registered with the same host and practitioner, and — for a live
session and a checked-out one alike — a re-verification of that same note,
dispatched under the clinic's CURRENT `clinic_rev`, that came back VERIFIED.
A verification made at Start or stored in `encounter.enc` is never enough on
its own (round 20 MED-012): a Replace key or Remove since then moved the rev.
Everything else is a named refusal. Nothing calls it for a write yet (Phase
4's draft write is the next plan, and brings the pre-write re-verification);
`encounter.py` has no write method and the client stays GET-only.

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
requested ids leave the machine to Cliniko by design, inside TLS. (6) An
exception raised during a call keeps, through its `__traceback__`, every frame
it unwound through with that frame's locals — `raise … from None` removes the
chained CONTEXT, not the frame chain. While that exception object is alive
(bound past its `except`, stored by a caller, `sys.last_exc`, a debugger), it
references the key (an `InvalidKey` raised by `shard_of_key` before
`ClinikoClient.call` deletes its local), or the Basic token (`ClinikoCall._get`'s
local `headers`, in the traceback of every error raised through the transport
or `_interpret`), with the path, ids and response bytes — past the logical
call's end, until the exception is dropped (codex round 9 PR-MED-030). Nothing
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
practitioner): no peer-identity gate beyond the logon session and the
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
`\\.\pipe\ClinikoScribe-<user SID>` is created with
`FILE_FLAG_FIRST_PIPE_INSTANCE`, so a name already held — by an earlier app or
by anything else — makes creation FAIL (`PipeUnavailable("name_taken")`) and
the app never shares it; `nMaxInstances = 1`, so one client at a time;
`PIPE_REJECT_REMOTE_CLIENTS`; and a PROTECTED DACL with one entry granting the
current user (nothing inherited). Enforced by the code: inbound frames are
bounded at 1 MB (flow 1's framing) and must be nonce-free `context` or
`command` envelopes — anything else closes that connection; a frame queued
for one connection is never written to the next; stop is prompt in every
state. RESIDUE (accepted under Task 4.3 (b) as boundary 2 — these are
things the design does NOT prevent, not controls): (1) the DACL admits
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
host's verification (below: same session, same user, same DACL) — the host
then relays Chrome's reports and commands to it and its `state` to the
panel. The app, finding the name held, says the Chrome link is unavailable
on the Session screen, and both ends log the other's executable path
(`pipe_peer`) — a tripwire, not a gate. A squatter of ANOTHER user, or one
with any other DACL, fails verification: a hard error in the host.
(3) Administrators and SYSTEM are outside this boundary (OS trust).

THE HOST'S RELAY (Task 4.4, `native_host.py` + `pipe_client.py`). Enforced:
before a single frame crosses, the host VERIFIES the pipe's server — its
process runs in the host's own logon session
(`GetNamedPipeServerSessionId` = the host's `ProcessIdToSessionId`), its
token user is the host's user SID, and the pipe's DACL is exactly the one
the app creates (protected, one ALLOW entry for that SID with no ACE flags
and the full access `GA` grants — type, flags, mask and SID all compared,
codex round 28 PR-LOW-142). A pipe that
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
records with write-back blocked (Constraint 6). `resume`, `finish`,
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
session is shown on the Session screen only; the write-back guard does not
read it and still requires its own current re-verification (MED-012). (3)
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
pauses any recording. Every pause runs through the Session screen's slot
and shows a desktop cue. A PAUSED session only gains the block; nothing
else changes state. A tab that is neither bound nor focused never pauses,
and neither does a SEPARATE tab showing a page that is not Cliniko's (the
bound tab itself leaving its note for such a page does pause, as above;
codex round 34 PR-LOW-191). The rule never resumes. THE RESUME
CHECK: every Resume through the Session screen's slot (its button, a Chrome
`resume`, Phase 7's hotkey) is refused, by name and before the controller
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
persisted); a completion, a discard or an expiry removes that one entry and
its reference. RESIDUE: (1) the rule sees only what Chrome reports: speech
between a page change and its report — and anything said before a
navigation — is recorded into the session it was bound to (the plan's
pre-navigation-speech assumption), and a change the extension never reports
is never seen; until the Phase 6 extension reports pages, only pipe loss, a
new client and suspend act. (2) An UNLINKED (desktop) recording ignores
Chrome's reasons by design; only suspend (and Phase 7's hands-free
reasons) pause it. (3) Suspend is Windows' broadcast: a power cut, a crash
or a hibernation that sends none is crash recovery's case. (4) Every report
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
only on that review's Save. Copying it follows the recorded copy flag and
re-checks it carries no unresolved error. An adopted linked session is
re-verified with Cliniko from the record the adoption decrypted (no second
decrypt); its write-back goes through the live entry, which still needs its
own current re-verification (MED-012). Adopting retires a live queued or
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

## Out of scope for Phases 1–3A (tracked in PLAN.md phases)

Transcript prompt-injection resistance of the local ML note model (Phase 3B —
3A's provenance check already derives speaker roles from COORDINATES, never the
assertion's display `speaker` field, as the spoken-injection defence for
clinician-owned sections; the ML model's own injection resistance is 3B),
consent workflow and recording indicators (Phase 5; the host↔app named pipe
and the host's relay they ride on are covered above), OneDrive/backup
exclusions and audit records (Phase 6),
packaging/signing (Phase 7).

## Review triggers

Re-review this model when: the practitioner revises Task 4.3's decision (b)
(the Chrome link, covered above, was built on it); the transcript becomes input to the local ML note model
(Phase 3B — 3A's non-ML template/autofill pipeline is covered above); real
Cliniko keys are first stored (the Clinics tab of the Cliniko workflow
safeguards plan's Phase 2 is built; the practitioner's first Validate is the
event); a note report from Chrome first reaches note verification on a real
install (the practitioner's first live smoke of Phase 4 — the relay and the
bridge are built and described above);
or the software is installed on the
second clinic machine (Phase 7). The local language model HAS landed
(note-learning-and-styles plan Phase 4, 2026-09-20, surface 17), so the next
trigger on that surface is a change of MODEL or of RUNTIME — a new pin, a new
quantisation, a different inference library, or a runtime installed by any
route other than the pinned hashed wheel.
