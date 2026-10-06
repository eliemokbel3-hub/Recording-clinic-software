# Privacy-First Cliniko Clinical Scribe

## Summary

Build a single-practitioner clinical scribe for two Cliniko clinics using:

- A thin Chrome extension embedded into the Cliniko workflow.
- A secure Windows desktop companion for recording and local AI processing.
- Local Whisper transcription and local `gpt-oss-20b` note generation.
- Direct writing of the reviewed note into the Cliniko draft treatment note, through Cliniko's official API (it fills the note the practitioner opened; it never creates a second one).
- No cloud processing of audio or transcripts.
- Replaceable AI providers so Azure Australia can be introduced when commercialising.

The product is documentation-only. It must not invent diagnoses, examination findings, treatment, advice, referrals, investigations or plans. The clinician reviews and finalises every note in Cliniko.

## Architecture and workflow

### Chrome companion

- Run only on authorised Cliniko domains.
- Detect the active clinic account, patient, booking, practitioner and treatment-note template.
- Add **Start recording** beside the Cliniko treatment-note workflow.
- Show a persistent recording or paused indicator.
- Open the completed Cliniko draft for review.
- Immediately pause recording when the patient, appointment, account, tab context or login state changes.

### Desktop companion

- Record the microphone independently of the browser tab.
- Communicate with Chrome through authenticated Chrome Native Messaging.
- Run voice-activity detection, speaker segmentation, Whisper transcription, clinical-content filtering and `gpt-oss` generation locally.
- Store each clinic's Cliniko API key in Windows Credential Manager.
- Encrypt active sessions using a separate per-session key.
- Provide microphone, model, hardware, clinic-connection, recovery and draft-status screens.
- Never silently fall back to cloud processing.

### Consultation flow

1. Open the patient's appointment or treatment-note page in Cliniko.
2. Select **Start recording**.
3. Show the patient, clinic and appointment in a confirmation popup.
4. Require the practitioner to tick: **I confirm the patient has consented to AI-assisted recording and documentation**.
5. Begin local recording and display an unmistakable recording indicator.
6. On **Finish consultation**, transcribe and generate the note locally.
7. Run grounding, contradiction and uncertainty checks.
8. Fill one Cliniko treatment note as a draft — the one linked to the correct patient, booking, practitioner and template. *As built (cliniko-draft-write plan, 2026-09-29): after Save, one click on the Note tab's "Write draft to Cliniko" re-reads the linked note and `PATCH`es the note's content only — the request can carry nothing that finalises, creates or moves a note — and it is refused by name, with Copy still offered, when the note is final, no longer matches, or holds an answer the app cannot read. Since 2026-09-30 (D15) it never replaces an answer: an empty question takes the app's text, and one that already holds text — typed, or the template's prompts — keeps it, with one empty line and the app's text below.*
9. Open the draft for practitioner review and finalisation. *(Met by construction since the Cliniko workflow safeguards plan for a Chrome-linked recording: it starts only from an open Cliniko treatment note, and Phase 4's draft fills THAT note, so it is already open for review. A recording started on the desktop is not linked to a note and cannot be written back.)*
10. After Cliniko confirms the write, destroy the session encryption key and delete recoverable audio/transcript data. *As built (the plan's D6, practitioner decision 2026-09-29): completion is SEEN — because saving a Cliniko editor that was already open overwrites the written draft, the app waits until the clinician has reloaded the note in Chrome, seen the draft and pressed Complete; that Complete verifies the session, deletes its key and removes its directory. After it the draft in Cliniko is the clinical record. Since Phase 6 (2026-10-01, practitioner decision, the privacy-professional-controls plan) that Complete — like every non-mock Complete — first keeps the transcript, the saved note (unless the path deletes it) and the generated note (when readable) (never the audio) in an encrypted Past-sessions entry for the practitioner's retention setting, and the session's audit row keeps the write's outcome for 7 years.*

### Forgotten patient-change protection

- Do not use appointment times to change patients.
- If Cliniko changes to another patient or appointment, pause immediately.
- Display the previous and new patient and require **Finish previous**, **Resume previous** or **Discard previous**. Discard is offered only on surfaces Cliniko's page cannot script (the side panel and the desktop); the block drawn on Cliniko's page offers Finish previous and Resume previous (practitioner decision 2026-09-28).
- Never automatically move recorded speech between patients.
- Use local semantic detection to warn when a finished conversation appears to be followed by a new greeting.
- Treat that detection only as a warning; it cannot identify or switch patients.
- Provide global keyboard and spoken pause/stop controls. *As built (Cliniko workflow safeguards plan D7, 2026-09-28): "stop" means PAUSE only — the hotkey (Ctrl+Shift+F9) pauses and asks for the guarded resume, the spoken phrase "scribe pause" only pauses; Finish and Discard always need a click.*

## Implementation changes

### Core types and interfaces

Define:

- `EncounterContext`: clinic account, patient, booking, practitioner and note-template identifiers.
- `ConsentAttestation`: encounter, practitioner and confirmation timestamp. *As built (`desktop/src/scribe_desktop/encounter.py`, 2026-09-27): `confirmed_at`, `text_version` (`recording-consent-v1`, this plan's Flow 2 step 4 wording), and the optional `practitioner_id` and `treatment_note_id` it names — absent means a recording not linked to a Cliniko note; `start()` refuses without one, and it is stored encrypted in the session's `encounter.enc` and destroyed with the session; since Phase 6 (2026-10-01) its time and text version, with the encounter's ids (never the patient id), are also written into the session's durable audit row at Start, kept 7 years.*
- `RecordingSession`: session identifier, encounter context, encryption-key reference and timestamps.
- `SessionState`: `idle`, `recording`, `paused`, `processing`, `queued`, `written`, `failed`, `discarded` or `expired`.
- `GeneratedNote`: structured Cliniko sections, grounding warnings and model/version metadata.
- `SpeechProvider`: implemented initially by local Whisper.
- `NoteModelProvider`: implemented initially by local `gpt-oss-20b`.
- `PracticeManagementConnector`: implemented initially for Cliniko.
- `SecureStorageProvider`: encrypted local storage now; Australian tenant-isolated storage later.

Chrome sends only the encounter context and recording commands to the desktop application. API credentials, models, audio and transcripts never enter extension storage.

### Phase 1 - Security foundation

- Build the Chrome Manifest V3 companion and Windows desktop shell.
- Establish authenticated Native Messaging.
- Add protected credential storage and encrypted session storage.
- Restrict Chrome permissions to Cliniko.
- Produce the intended-use statement, data-flow map, threat model, retention schedule and incident process.

**Completion:** Chrome and desktop exchange authenticated test messages without clinical data or exposed local network ports.

### Phase 2 - Local recording and transcription

- Add microphone selection and start, pause, resume, finish and discard controls.
- Encrypt audio chunks immediately using per-session authenticated encryption.
- Add crash recovery and the 24-hour maximum recovery period.
- Integrate local Whisper, voice activity and speaker segmentation.
- Preserve timestamps and mark uncertain words, numbers and names.
- Add the hardware benchmark; failed devices receive a warning and report, never cloud fallback.

**Completion:** synthetic osteopathic consultations transcribe locally with verified absence of AI network traffic.

### Phase 3 - Local note generation

- Integrate quantised `gpt-oss-20b` behind `NoteModelProvider`.
- Generate structured Cliniko template sections rather than free-form browser text.
- Treat the transcript as untrusted data so spoken instructions cannot alter system behaviour.
- Exclude irrelevant conversation while presenting uncertain potentially clinical content for review.
- Flag unsupported statements, contradictions, laterality, medications, dosages, measurements, names and numbers.
- Leave unsupported template fields blank rather than inferring content.

**Completion:** the agreed validation set contains no unsupported clinical assertions and preserves clinically material supported facts.

**Delivery note — the 3A / 3B split (2026-08).** Phase 3 was delivered in two stages. **Phase 3A (the note pipeline, COMPLETE through its internal Phase 7)** built everything AROUND the model without the model: the canonical **17-section note schema** (`note.py`, referenced by stable key, never ordinal); an assertion-centric type model where three unsafe states are UNREPRESENTABLE rather than merely validated — a `NoteProposal` (which legitimately represents a candidate awaiting confirmation) cannot be placed in a `GeneratedSection`, so unconfirmed content cannot reach a saved note; a `transcript` assertion cannot span two source intervals; and a clinician-authored assertion cannot be constructed without a confirmation decision; a per-clinic **template-mapping layer** (`note_config.py`) that maps writable canonical sections to real Cliniko template fields while explicitly tracking unmapped sections (an `intentionally_unmapped` section is silent; a populated section left unmapped by oversight raises a `mapping_drop` warning; the consent checkbox is structurally unmappable), behind a fail-closed, all-or-nothing validating config loader; **autofill and prefill** (`note_fill.py`) that turn clinician-authored config into per-atomic-assertion PROPOSALS — never insertions, and a patient-spoken trigger still only proposes; a four-check **checking stage** (`note_check.py`: reconstruction, contradiction, provenance, omission — see `docs/security/threat-model.md` for its honest limit); the two-stage **compose → confirm → check → write pipeline** writing `note.enc` under the same per-session key as the audio and transcript; and the **note review UI** (`ui/note.py`). 3A ships with an `ExtractiveNoteProvider` (verbatim transcript spans) standing in for the model, and copy-to-Cliniko was bound to the Task-9.1 shipping gate and shipped disabled — **enabled on 2026-09-27** by the practitioner's decision (Cliniko workflow safeguards plan D12, Task 1.4), offered only for a fully ratified note; the Task-9.1 run is now a quality measurement, not an enablement gate. **Phase 3B (deferred)** is the remaining bullets above: the quantised `gpt-oss-20b` `NoteModelProvider` itself, transcript-as-untrusted-data resistance AT the ML model, and the validation set that closes the completion gate. See `.cursor/plans/plan-phase3a-note-pipeline.md` for the 3A detail.

### Phase 4 - Cliniko integration

- Configure the two Cliniko accounts independently.
- Fetch authorised patients, bookings, practitioners and treatment-note templates.
- Fill draft treatment notes through the official API.
- Maintain a local write ledger mapping each session to its Cliniko note.
- Before retrying an uncertain request, reconcile by patient, booking, template and content hash to prevent duplicates.
- Queue encrypted drafts when Cliniko or the internet is unavailable.
- Never finalise notes automatically.

**Completion:** each test consultation fills exactly one draft in the correct clinic and patient record.

**Delivery note — the draft write (2026-09-29).** Built as `.cursor/plans/plan-cliniko-draft-write.md` on top of Phase 5's verified context, clinic keys and write-back guard. As built: the practitioner's test write on clinic 1 settled the design — a partial body REPLACES a Cliniko note, so the write sends the note's full re-read content with only the app's questions set; an already-open Cliniko editor's save overwrites the draft, so completion waits for the clinician's Complete after seeing it. After the batched smoke the practitioner chose to APPEND rather than refuse (D15, 2026-09-30): an answer already in the note — typed text or the template's starting prompts — is kept byte-for-byte with the app's text below it after one empty line, so no template, per-clinic setting or defaults file is read any more and the click makes one note read before its `PATCH`. The ledger is a per-session encrypted record `write.enc` (ids and digests only; it dies with the session — since Phase 6 the write's attempts, last outcome, refusal code and written-at also go into the session's durable audit row); before any retry the reconcile compares each targeted answer's normalised digest with the record's expected final answer (the earlier write landed — no second `PATCH`, so text is never appended twice) and with the answer as that attempt read it (nothing landed — a new attempt from the current read), so an uncertain request is recognised rather than repeated; drafts are NOT queued — a write needs Cliniko reachable at the click, and a failed or unknown write is retried only by another click while the session still exists (the 24-hour rule governs a recording no longer held open), or the note is copied. Clinic 2 waits on its own API-key permission and test write. What each safeguard does and does not enforce is in `docs/security/threat-model.md` ("Cliniko API client", THE DRAFT WRITE).

### Phase 5 - Workflow safeguards

- Embed Start and status controls into the Cliniko page.
- Add the consent confirmation and permanent recording indicator.
- Implement immediate pause on every patient-context change.
- Add the previous/new patient resolution panel.
- Add likely-consultation-boundary warnings and emergency controls.
- Prevent write-back whenever Cliniko context cannot be verified.

**Completion:** workflow and adversarial tests cannot attach one consultation to another patient.

**Delivery note — Phase 5 before Phase 4 (2026-09-27/28).** Phase 5 was built first, by the practitioner's decision, as `.cursor/plans/plan-cliniko-workflow-safeguards.md`, together with the parts of Phase 4 it needs READ-ONLY: the two clinic API keys (validated with Cliniko, stored in Windows Credential Manager) and a Cliniko client inside `scribe-app` that was then GET-only (Phase 4's draft write later added its one `PATCH`), so the offline contract became "no connection except Cliniko's API, and none at startup or idle" (none on its own: every call answers a practitioner action, a report from Chrome, or — for a linked recording in progress — the Chrome link reconnecting, so a note already open in Chrome is checked when the app starts). A Chrome-linked recording starts only from an open treatment note that Cliniko verifies (or, when Cliniko cannot be reached, one marked `unverified_offline`), behind the consent tick; a recording started on the desktop is not linked to a Cliniko note and cannot be written back. Chrome's side panel carries consent and every control, and a red/amber frame and a full-page block mark the Cliniko page; a linked recording pauses when its own tab changes note or patient, leaves the note or closes, when another Cliniko note is focused or the Cliniko login page shows, or when the Chrome link drops or a new client connects — switching to a separate non-Cliniko tab does not pause it — and any recording pauses on system sleep or when Windows locks the session (when Windows delivers those notifications — residue in the threat model); back-to-back consultations wait in an Unreviewed list; write-back is refused unless the context is re-verified (`writeback_context`). Writing the draft — Phase 4's fill, ledger and reconcile — followed as the next plan (Phase 4's delivery note above). The "Start beside the Cliniko workflow" and the confirmation popup are the side panel, not controls inside Cliniko's page. See `docs/security/threat-model.md` for what each safeguard does and does NOT enforce.

### Phase 6 - Privacy and professional controls

- Store a minimal audit record: consent timestamp, user, clinic, booking/note identifiers, model version, write result and deletion result.
- Never retain transcript or audio content in logs, telemetry or audit records.
- Exclude temporary data from OneDrive, roaming profiles, crash reporting and ordinary backups.
- Cryptographically delete successful sessions immediately and failed sessions after 24 hours.
- Keep the intended use limited to clinical documentation and prohibit clinical decision support.
- Prepare patient consent wording, privacy information, downtime procedure and clinician review guide.

**Delivery note — privacy and professional controls (2026-10-01).** Built as `.cursor/plans/plan-privacy-professional-controls.md`. As built, bullet by bullet:
- *Audit record:* one encrypted, content-free row per session (`audit.py`), written at Start — Start is refused if it cannot be — and updated best-effort with the models, the draft write's outcome, the deletion and the Past-sessions events; it holds the consent time and text version, `linked`, the verification state and the clinic, practitioner, user, booking and treatment-note ids, never a patient name, patient id or any text; kept 7 years, exportable as an (unencrypted) CSV from the Past sessions tab.
- *No content in logs or the audit:* by construction for the audit row; uncaught exceptions in both processes now log their type name only.
- *Exclusions:* "set and warn", per user — the register script writes Windows Error Reporting exclusions for `pythonw.exe`, `scribe-app.exe` and `scribe-host.exe`; the app marks its data folder not-content-indexed and warns at start-up (never refusing) when the folder is in OneDrive, on a network drive or in the roaming profile, or when crash reports are not excluded. Backup and snapshot exclusions need admin rights and move to Phase 7's installer.
- *Deletion — REVERSED for transcripts and notes by the practitioner's decision:* every Complete still destroys the audio and removes the session immediately, and failed sessions still go after 24 hours; but at every non-mock Complete the transcript, the saved note (except on the two delete-note paths) and the generated note (when readable) are first kept, encrypted under a per-entry key, in a **Past sessions** tab ("like Heidi"), labelled by patient name and date (with Hide names), with Copy of the saved note, a two-click Delete now (worded for a recording made in error only), and a retention setting of "until I delete them" (the default) or 7 years — a kept transcript is part of the health record and is kept for at least 7 years (practitioner decision 2026-10-02; a shorter setting saved by an earlier build reads as 7 years) — shown with a warning that says so, including that a child's transcript must be kept until they turn 25. Backup/restore of Past sessions is deferred.
- *Intended use:* the line "Documentation aid, not clinical decision support. You review and finalise every note in Cliniko." heads the Status and Past sessions tabs; `docs/security/intended-use.md` matches.
- *Practice documents:* drafts in `docs/practice/` (patient information and consent `patient-info-v1` — `patient-info-v2` since the pilot plan, below — privacy information, downtime procedure, clinician review guide), each awaiting the independent review this plan's commercial path requires.

See `docs/security/threat-model.md` ("Privacy and professional controls") for what each control does and does not enforce, and `docs/security/retention-schedule.md` for the stores.

### Phase 7 - Pilot and installation

- Validate with at least 50 synthetic or de-identified encounters covering common osteopathic appointment types, accents, noise and templates.
- Run 10 consented shadow-mode consultations where generated notes are compared but not written automatically.
- Pilot 20 reviewed consultations at the first clinic, then 20 at the second clinic.
- Install the extension, desktop companion and model files separately on both computers.
- Connect each machine only to its authorised Cliniko account or accounts.
- Proceed to routine personal use only after high-risk findings are resolved or explicitly controlled.

**Delivery note — installation COMPLETE and installed on this computer (2026-10-04); pilot IN PROGRESS.** Phase 7 is split in two plans. The installation half (bullets 4–5) is `.cursor/plans/plan-installation.md` (Completed — Follow-ups Retained; first installed 2026-10-03, build 0.1.2 in clinical use since 2026-10-04 — `docs/release/pilot-builds.md`); the pilot half (bullets 1–3 and 6) is `.cursor/plans/plan-pilot.md`, in progress (below). As built:
- *Installed separately:* a packaged desktop companion (`scribe-app.exe`, `scribe-host.exe`) and a per-machine installer that puts it in `C:\Program Files\ClinikoScribe`, a folder a standard user cannot change; the extension ships inside it and is loaded unpacked from there; the models come as a separate model pack that the installer checks file by file against hashes compiled into it, and the app never downloads anything. The installer writes the Chrome link, the crash-report exclusions and — best-effort — the backup and snapshot exclusions for live recordings and logs, all machine-wide, never launches the app, and on uninstall keeps the data folder.
- *Build of record:* a manual CI `Release` workflow on `main` with a build-provenance attestation; the build is UNSIGNED for the pilot, so every install starts with `gh attestation verify` and a hash check (`docs/release/pilot-builds.md`).
- *Developer build kept apart:* a source checkout is now a separate developer channel with its own data and models folder, Chrome link and extension, and it refuses Cliniko writes unless its own setting allows them; only one of the two runs at a time.
- *Hardware check:* the Microphone tab's benchmark now also times the local language model's prose stage, so the installed computer is benchmarked after install.
- *Authorised accounts* (bullet 5): unchanged by this plan — each clinic is added and validated on the Clinics tab; the installation records the authorised hosts at its Phase P.
- **Run on this computer (practitioner, 2026-10-03 → 2026-10-04):** the build lock, the models manifest and model pack, the Inno Setup licence question (decided 2026-10-03: continue without buying a licence, keeping Inno's own notices), the workflow's first green runs and the builds of record 0.1.0–0.1.2, then the plan's Phase P — install, the offline check, update 0.1.0 → 0.1.1, rollback, uninstall and reinstall, all PASS. Attestation needs this repository to stay public (it is, since 2026-10-03) unless it moves to GitHub Enterprise Cloud. The second clinic computer follows with the pilot (its Task P.7).

**Delivery note — pilot, IN PROGRESS (`.cursor/plans/plan-pilot.md`).** As built so far (version 0.2.0, not yet a build of record):
- *Shadow mode* (bullet 2): a "Shadow mode (pilot)" setting on the Status tab, fixed for each recording at Start; a shadow recording's note is never copied or written to Cliniko, its note text cannot be selected, and saving it teaches the app nothing. The audit row (now with the recording's mode and the app version), the encounter record and the Past-sessions label are schema v2 and read older files as normal; rolling back below 0.2.0 requires finishing or discarding every recording first (`docs/release/pilot-builds.md`).
- *Validation harness* (bullet 1, developer build only): an offline batch run of the shipped pipeline over a set folder of synthetic text-to-speech encounters built from 40 invented scripts plus mock role-plays, measured against each script through one word-level alignment and judged by a pass rule decided before any run (`docs/testing/validation-harness.md`).
- *Pilot records* (bullets 3 and 6): the pilot log template, the findings register and the per-clinic exit gate in `docs/pilot/`; the patient information sheet `patient-info-v2` adds the comparison appointments (approved by the practitioner 2026-10-07). Decision 3.5: rule v1 is option (a) unchanged — zero unsupported clinical lines, material wrong facts, silent omissions and unsurfaced expected uncertainty, no unexpected error-grade or contradiction-class checker warning, no word-error-rate ceiling — with the practitioner's own cue file, fenced-off content counted as material, and an accent other than the practitioner's among the role-plays. Decision 3.6: the role-play recordings are kept in one local folder until speaker labelling is decided and Phase 3B's gate has re-used them, with the agreement of everyone recorded other than the practitioner and a review date.
- **Still to run (practitioner):** the build of record 0.2.0, then the plan's Phase P — install, the role-plays, the validation run (at least 50 encounters), 10 shadow and 20 reviewed consultations at clinic 1 and its exit gate, then clinic 2 once its Cliniko API-key permission exists.

See `docs/security/threat-model.md` ("Installation" and "The pilot") for what each control does and does not enforce.

## Test plan and acceptance criteria

### Safety and workflow

- Recording cannot start without the consent checkbox.
- Switching patient, appointment or clinic pauses immediately.
- Context loss blocks write-back.
- A failed or retried request cannot create duplicate notes.
- The practitioner must finalise every note manually.
- Crash, restart, internet outage and Cliniko outage recovery behave safely.

### AI quality

Test history, examination, treatment, consent, advice, exercises and follow-up plans with:

- Negation and changing symptoms.
- Left/right and anatomical-region distinctions.
- Numbers, dates, medications, dosages and measurements.
- Small talk and unrelated conversation.
- Overlapping speakers, background noise and accents.
- Uncertain speech and contradictory statements.
- Spoken prompt-injection attempts.
- Apparent end-of-consultation and new-patient greetings.

Acceptance requires no unsupported clinical assertion in the validation set, all uncertainty surfaced for review, and no silent omission of content marked potentially clinically material.

### Privacy and security

- Network inspection confirms that no audio or transcript reaches OpenAI, Azure or another AI service.
- Cliniko API keys never appear in Chrome storage, logs or diagnostic files.
- Temporary files remain encrypted at rest.
- Successful write-back triggers cryptographic deletion. *As built: the clinician's Complete after seeing the draft deletes the session key (the audio and the session's files); since Phase 6 the transcript and notes are first kept, under their own key, in Past sessions for the practitioner's retention setting.*
- Unresolved recovery sessions expire within 24 hours.
- Cross-patient write-back tests must pass with zero failures.

## Assumptions and commercial path

- Both clinic computers are assumed capable of running the local models; the installer still benchmarks them.
- Windows is the first supported desktop platform. The architecture remains portable, but macOS packaging is deferred.
- Cliniko remains the permanent system of record; clinical data is not synchronised between computers by this application.
- Consent is obtained outside the treatment room, but the practitioner must confirm it in the popup before every recording.
- The product can be designed to support Ahpra, National Board, Australian privacy and Australian Commission guidance, but it must not be described as "Ahpra approved."
- Obtain an independent Australian privacy, legal, clinical-safety and TGA-scope review before selling or deploying to other practitioners.
- Commercialisation will replace or supplement the local providers with Azure Speech and Azure OpenAI in Australia, while retaining local processing as an optional privacy tier.
- Organisation accounts, billing, central administration, cloud dashboards, automatic updates and other practice-management integrations are deferred until the single-user Cliniko pilot is successful.
