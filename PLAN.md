# Privacy-First Cliniko Clinical Scribe

## Summary

Build a single-practitioner clinical scribe for two Cliniko clinics using:

- A thin Chrome extension embedded into the Cliniko workflow.
- A secure Windows desktop companion for recording and local AI processing.
- Local Whisper transcription and local `gpt-oss-20b` note generation.
- Direct creation of draft treatment notes through Cliniko's official API.
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
8. Create one Cliniko treatment note with `draft: true`, linked to the correct patient, booking, practitioner and template.
9. Open the draft for practitioner review and finalisation.
10. After Cliniko confirms successful creation, destroy the session encryption key and delete recoverable audio/transcript data.

### Forgotten patient-change protection

- Do not use appointment times to change patients.
- If Cliniko changes to another patient or appointment, pause immediately.
- Display the previous and new patient and require **Finish previous**, **Resume previous** or **Discard previous**.
- Never automatically move recorded speech between patients.
- Use local semantic detection to warn when a finished conversation appears to be followed by a new greeting.
- Treat that detection only as a warning; it cannot identify or switch patients.
- Provide global keyboard and spoken pause/stop controls.

## Implementation changes

### Core types and interfaces

Define:

- `EncounterContext`: clinic account, patient, booking, practitioner and note-template identifiers.
- `ConsentAttestation`: encounter, practitioner and confirmation timestamp.
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

### Phase 4 - Cliniko integration

- Configure the two Cliniko accounts independently.
- Fetch authorised patients, bookings, practitioners and treatment-note templates.
- Create draft treatment notes through the official API.
- Maintain a local write ledger mapping each session to its Cliniko note.
- Before retrying an uncertain request, reconcile by patient, booking, template and content hash to prevent duplicates.
- Queue encrypted drafts when Cliniko or the internet is unavailable.
- Never finalise notes automatically.

**Completion:** each test consultation creates exactly one draft in the correct clinic and patient record.

### Phase 5 - Workflow safeguards

- Embed Start and status controls into the Cliniko page.
- Add the consent confirmation and permanent recording indicator.
- Implement immediate pause on every patient-context change.
- Add the previous/new patient resolution panel.
- Add likely-consultation-boundary warnings and emergency controls.
- Prevent write-back whenever Cliniko context cannot be verified.

**Completion:** workflow and adversarial tests cannot attach one consultation to another patient.

### Phase 6 - Privacy and professional controls

- Store a minimal audit record: consent timestamp, user, clinic, booking/note identifiers, model version, write result and deletion result.
- Never retain transcript or audio content in logs, telemetry or audit records.
- Exclude temporary data from OneDrive, roaming profiles, crash reporting and ordinary backups.
- Cryptographically delete successful sessions immediately and failed sessions after 24 hours.
- Keep the intended use limited to clinical documentation and prohibit clinical decision support.
- Prepare patient consent wording, privacy information, downtime procedure and clinician review guide.

### Phase 7 - Pilot and installation

- Validate with at least 50 synthetic or de-identified encounters covering common osteopathic appointment types, accents, noise and templates.
- Run 10 consented shadow-mode consultations where generated notes are compared but not written automatically.
- Pilot 20 reviewed consultations at the first clinic, then 20 at the second clinic.
- Install the extension, desktop companion and model files separately on both computers.
- Connect each machine only to its authorised Cliniko account or accounts.
- Proceed to routine personal use only after high-risk findings are resolved or explicitly controlled.

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
- Successful write-back triggers cryptographic deletion.
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
