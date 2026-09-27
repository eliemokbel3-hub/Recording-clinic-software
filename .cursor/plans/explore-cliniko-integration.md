# Exploration — Cliniko integration (PLAN.md Phase 4) and its Phase 5 prerequisite — 2026-09-27
Code baseline: main @ 33bd35e

Explored as "PLAN.md Phase 4 — Cliniko API draft creation". During the exploration the practitioner decided to build ALL of PLAN.md Phase 5 FIRST, as its own plan, followed by a separate Phase 4 plan. This scratch therefore carries (a) the Phase 5 build-now scope and (b) the Phase 4 findings and decisions for the plan that follows.

## Key Findings

### Files / symbols involved
- **Chrome extension is the Phase 1 heartbeat scaffold.** `extension/src/manifest.ts:13-14`: `permissions: ["nativeMessaging","alarms"]`, `host_permissions: ["https://*.cliniko.com/*"]`. It has no `content_scripts` ("no content scripts in Phase 1", `:3-4`) and no popup (`popup` 0 hits in `extension/src`). `background.ts` drives `connection.ts`'s `ConnectionManager`: hello/ping handshake, badge OK/OFF/ERR/"…", alarm backoff. Nothing reads the Cliniko page: no URL, DOM, patient, booking, template or subdomain code.
- **Native messaging.** `native_host.py` is a separate, stateless process (`scribe-host`, `desktop/pyproject.toml:65`). `HostSession.handle` (`:81-122`) answers only `hello` and `ping`; anything else gets an error and the host exits. The origin argv is checked against `EXPECTED_ORIGIN` (`:48-59`, exit 2). The nonce is a correlation id, not authentication (`:5`). **There is no host↔app link**: the named pipe was deferred to Phase 5 (`docs/security/data-flow-map.md:564-571`). Its hardening list is in `plan-phase2-recording-transcription.md:41-45`: `FILE_FLAG_FIRST_PIPE_INSTANCE`, `nMaxInstances=1`, `GetNamedPipeServerProcessId` + image-path check, bounded `WaitNamedPipe`, and "pipe exists but server unverified" treated as a hard error.
- **Protocol.** `protocol/fixtures/`: valid messages are `hello`, `hello_ack`, `ping`, `pong`, `error`; there are 11 invalid cases; envelope `{protocol_version,type,request_id?,session_nonce?,payload}`; frame limit 1 MiB. No message carries encounter context or recording commands. Mirrors: `extension/src/protocol.ts`, `desktop/src/scribe_desktop/protocol.py:26`.
- **Session.** `SessionState` (`session.py:82-93`) has all nine PLAN states, including `QUEUED` and `WRITTEN`. `LEGAL_TRANSITIONS` (`:215-237`) allows queued→written|discarded|expired. `RecordingSession.encounter_context: str | None` (`:170`, max_length 256) is always None. The only constructor is `RecordingSession(key_reference="key.dpapi")` (`:443`, in `start(device_id)`). No `EncounterContext` type exists. The logging tripwire drops `encounter_context` (`logging_setup.py:82-86`).
- **Key destruction today.** Only the local Complete variants (`complete`, `complete_without_note`, `complete_deleting_saved_note`, `session.py:683-785`) reach `session_store.complete_session` (fsync + decrypt-verify, then `delete_session_key`). The `note.enc`, `transcript.enc` and `audio.enc` ciphertexts are left for the next sweep's orphan GC.
- **Sweep protection.** `app.sweep_protected_ids` → `controller.custody_protected_ids()` (`session.py:1044-1063`, verified) protects only the live in-memory non-terminal session plus Discard reservations. A queued/saved session is NOT durably protected across a restart: it goes to the Recovery screen and expires at 24 h.
- **Note-to-Cliniko seam.**
  - `COPY_TO_CLINIKO_ENABLED: Final[bool] = False` (`ui/models.py:446`). Readers: `ui/main_window.py:453`, and `ui/note.py:510` (the default argument, bound at import). Copy is clipboard only (`ui/note.py:1987-2026`).
  - Save path: `NoteScreen.save` → `MainWindow._on_note_save` → `TranscriptScreen.save_note` → `controller.with_generation_custody(lease, write_note(...))`. The session stays QUEUED until the manual Complete (`ui/transcript.py:771-792`).
- **Note and template model.** `GeneratedNote` (`note.py:675-760`) holds no Cliniko or encounter ids; it has 17 canonical sections of assertions. `note_config.py` `TemplateProfile{template_profile_id, display_name, template_targets[TemplateTarget{target_id, group, field_label, target_type ∈ rich_text|plain_text|attestation_checkbox}], section_mappings, intentionally_unmapped}` (`:292-387`). The shipped `config_defaults/template_profiles.json` has one profile, `"template-a"` ("Template A, both clinics"). Its `group`/`field_label` mirror the Cliniko template's section and question names (verified), but it has no Cliniko template id and no per-clinic scoping. `target_for()` has no caller outside `note_config`, and nothing renders per target.
- **Credentials.** `SecureStorageProvider.store/retrieve/delete(clinic_id, secret_name[, value])` (`secure_storage.py:47-57`, keyring service `ClinikoScribe/<clinic_id>`) is per-clinic already ("Phase 4 needs no interface churn", `:4-6`). The only caller is the self-test (`status.py:69-74`). No Cliniko key is stored and there is no entry UI.
- **Ledger / queue / retry / idempotency:** none exists (`ledger` 0 hits). The nearest primitive is sha256-v1 `transcript_digest` / `config_digest` (`note.py:184-186`).

### Codebase integration notes (the offline contract Phase 4 changes)
- **No runtime socket guard exists.** Sockets are prevented only by tests, lint and docs:
  - the `addaudithook|socket\.socket\s*=|monkeypatch.*socket|netsh|firewall|net_connections` hits in non-.md files are all in `desktop/tests/test_integration_no_sockets.py`;
  - `apply_offline_env` / `assert_offline_env` (`benchmark.py:52-127`) are Hugging Face / llama switches only, and the docs already say "NOT an enforcing control" for network posture (`threat-model.md:1217-1218`).
- **The no-sockets tests** poll psutil `net_connections` and assert `[]` (`test_integration_no_sockets.py:141-143`) across subprocess children: host handshake, the `scribe-app` MainWindow idle poll (`:212-255`), capture, live and real Whisper, mock and real prose, crash recovery, and a socket-stub child (`:1399`). There is **no allow-list**, and CI skips the file (`SCRIBE_SKIP_INTEGRATION=1`).
- **Ruff banned-api** (`desktop/pyproject.toml:90-95`) bans `PySide6.QtNetwork`, `socket`, `http` and `urllib.request` ("neither desktop process may open a network socket"). `httpx` and `requests` are not banned.
- **Dependencies.** The base deps contain no HTTP client. `httpx` 0.28.1 is present only transitively through the optional `[ml]` extra (`huggingface_hub`). A new dependency needs a practitioner-authorisation comment, as for python-docx 1.2.0 and pypdf 6.19.0.
- **Docs that a Cliniko client would make false** (to be rewritten as a CLASS, `docs/lessons.md` 2026-08-14):
  - `data-flow-map.md:11-14` ("no network sockets on either desktop process at runtime"), `:141-142` ("TWO sanctioned network steps … never the app"), `:487-493`;
  - `threat-model.md:118-119` ("ONLY sanctioned network user is setup-models.py"), which is already stale;
  - `pyproject.toml:8,91-95`; `ui/__init__.py:9`; `language_model.py:21`;
  - `intended-use.md:21-22` ("audio and transcripts never leave"). This stays true for audio and transcript, but the note, which is derived from the transcript, will leave.
- **Docs that already anticipate Phase 4:**
  - `data-flow-map.md:49-51`: keys live only in Credential Manager;
  - `threat-model.md:76-78,1259`;
  - `intended-use.md:11-12,20` (`draft: true` is a hard rule);
  - `retention-schedule.md:97-99`: cryptographic deletion on successful write-back;
  - `incident-process.md:15-28`: key exposure is an incident and is revoked by regenerating the key in Cliniko.
  - The write ledger has 0 hits in the security docs; it appears only in `PLAN.md:117`.

### External / API findings (Cliniko public API — docs.api.cliniko.com + its OpenAPI bundle; GitHub `redguava/cliniko-api` archived 2025-05-15 = LEGACY)
- **Authentication.** HTTP Basic with the API key as username and an empty password, over TLS 1.2+. The key's `-auN` suffix selects `https://api.auN.cliniko.com/v1`; keys without a suffix use au1. A `User-Agent: APP_NAME (contact email)` header is required. Keys are per user and carry that user's permissions. The note author is the key's practitioner-user, and create has no `practitioner_id`. Revoking a key means archiving it.
- **Limits and errors.** 200 requests/min per user; 429 comes with an `X-RateLimit-Reset` header. The 422 body is `{"message":"Validation Failed","errors":{field: msg}}`.
- **Treatment notes.**
  - `POST /treatment_notes` returns 201 and accepts `patient_id`, `booking_id`, `attendee_id`, `treatment_note_template_id`, `title`, `draft`, `content`.
  - `content` = `sections[{name, description, questions[{name, type ∈ text|paragraph|date|checkboxes|radiobuttons|bodycharts, answer | answers[{value, selected}] …}]}]`. A `paragraph` answer is sanitised HTML (p, div, br, ul, ol, li, blockquote, h1, h2, b, i, u, a).
  - `PATCH` accepts the same fields, **including `draft`**, so the API CAN finalise a note. A final note cannot be edited by anyone.
  - There is no hard delete: `DELETE` is a deprecated alias for archive.
  - **No idempotency key.** Reconciling works through `q[]` filters on `booking_id`, `draft`, `patient_id`, `practitioner_id`, `treatment_note_template_id` and `created_at` (archived notes need `q[]=archived_at:*`).
- **Other endpoints.**
  - Templates: `GET /treatment_note_templates[/{id}]`, with content sections/questions like a note's but without answers.
  - `GET /user`: role and id. `GET /practitioners?q[]=user_id:=…` finds the key user's practitioner record.
  - `GET /individual_appointments` and `GET /bookings`, filterable by practitioner, patient and `starts_at` (UTC).
  - Pagination: `per_page` up to 100, following `links.next`.
  - `GET /settings/public` and `GET /settings` return `account.subdomain`, which maps a key to a clinic and to a Chrome tab. The roles allowed to call `/settings/public` are UNCONFIRMED.
  - There is no sandbox; Cliniko suggests a free trial account. The practitioner declined one.
- **Industry practice (Heidi Health).** Heidi uses a pasted per-account Cliniko API key, creates the note as a draft, updates that same draft on a re-push, and creates a new note if the first was finalised. Its processing is cloud-side. Cliniko has no native AI scribe and lists 12 third-party AI apps.
- **Regulatory context** (guidance; none of it prescribes process architecture):
  - Ahpra/National Boards AI guidance (22 Aug 2024), which covers osteopaths: the practitioner stays accountable for and checks the AI record; transparency and consent, especially for tools that record; knowing where data is stored. Code of conduct §8.3 covers health records.
  - OAIC AI-products guidance (Oct 2024): local deployment is "likely more privacy-preserving"; APP 5/6/10/11 still apply.
  - TGA digital scribes (2025): not a medical device unless it suggests a diagnosis or treatment the practitioner didn't state. The product's "documentation only, never invents" rule keeps it outside that definition.

### Search patterns recorded (by the exploration agents)
- Extension and protocol:
  - `cliniko` -i: 320 hits / 56 files
  - `booking`: 10/5
  - `EncounterContext|encounter_context`: 14/7
  - `host_permissions`: 1/1
  - `content_scripts|content script`: 6/2
  - `practitioner_id|practitionerId`: 0
  - `template_id|templateId`: 0
  - `cliniko.com/`, `/patients/`, `treatment_notes`, `api.cliniko`, `MutationObserver`: 0 hits in the repo
- Desktop `desktop/src` `*.py`:
  - `ledger`: 0
  - `api_key`: 0
  - `httpx`: 0
  - `urllib`: 0
  - `requests`: 1 (a comment)
  - `EncounterContext`: 1 (a comment)
- Offline guards: `addaudithook|socket\.socket\s*=|monkeypatch.*socket|netsh|firewall|import socket|net_connections|connections\(` in non-.md files: 22 hits, all in `test_integration_no_sockets.py`.
- Network imports: `socket|_socket|ssl|http|urllib|requests|httpx|urllib3|aiohttp|QtNetwork`: 3 hits, none in `src/`.
- Security docs, hits per doc for Cliniko / network / egress / Phase 4 / API key / ledger:
  - threat-model: 13 / 4 / 0 / 8 / 2 / 0
  - data-flow-map: 16 / 19 / 0 / 9 / 1 / 0
  - retention-schedule: 13 / 1 / 0 / 7 / 0 / 0
  - intended-use: 6 / 0 / 0 / 1 / 1 / 0
  - incident-process: 7 / 1 / 0 / 2 / 2 / 0

### Doc ↔ code contradictions (flag for `/document`)
- `PLAN.md:66` defines `EncounterContext` as a core type, but the code has only an opaque `str | None`.
- PLAN.md consultation-flow step 10 says to destroy the key after Cliniko confirms, but the code destroys it on the local Complete and leaves the ciphertexts until the sweep.
- `session_store.py:871` and `app.py:35` call a queued-under-review store "protected". That holds only while it is the controller's in-memory `_live` session, not across a restart.
- `ui/models.py:517` refers to "a reloaded `note.enc`", but `read_note` (`session_store.py:851`) has no production caller.
- "Phase 4" is ambiguous across the security docs: it can mean PLAN.md Phase 4 (Cliniko) or the note-learning plan's Phase 4 (the language model).
- `threat-model.md:118` says setup-models is the ONLY sanctioned network user, but `:1035` already adds the prose-wheel fetch.
- The shipping-gate decision below supersedes `docs/testing/shipping-gate.md`'s "a pass flips `COPY_TO_CLINIKO_ENABLED`" framing, AGENTS.md's Phase 9 wording and the note on `plan-phase3a-note-pipeline.md` Task 9.1.

### Cliniko web-app URLs (practitioner-supplied 2026-09-27; ids replaced by placeholders here — never commit real ids)
- **Host shape:** `https://<subdomain>.<shard>.cliniko.com/…`. One clinic is on shard `au2`, so the web host carries the same shard as the API key suffix (`-au2` → `api.au2.cliniko.com`). The manifest wildcard `https://*.cliniko.com/*` covers it. The runtime allow-list must match `<subdomain>.<shard>`, not the subdomain alone.
- **Calendar:** `/appointments?calendar_start_date=<YYYY-MM-DD>`. Clicking a patient or appointment there does NOT change the URL, so neither the booking id nor the patient id is readable from the URL on this page.
- **Treatment note:** `/patients/<patient_id>/treatment_notes/<treatment_note_id>/edit?page=1`. The practitioner reaches it by clicking "treatment notes" from the appointment. The URL carries the patient id and the treatment-note id, but no booking or template id. Two different patients' notes had two different patient ids, as expected. With a key, `GET /treatment_notes/<id>` returns the note's patient, booking and template links plus its draft/final state.
- The practitioner described navigating between these views without a full page load. Whether Cliniko is a single-page app that changes the URL through `history.pushState` is UNVERIFIED. It matters for pause-on-change, which needs `webNavigation.onHistoryStateUpdated` (a new permission) or an in-page URL watcher.

### Edge cases / blind spots
- **Cliniko page structure is only partly known.** The URL shapes are above; the page's DOM is unexplored. On the calendar the URL carries no patient or booking id. On the note page it carries the patient and note ids, but not the booking, template or practitioner. How navigation is signalled and the second clinic's host are unverified. This is still the biggest Phase 5 unknown.
- Group appointments (`attendee_id`), notes with no booking, cancelled or did-not-arrive appointments, and timezone handling for "today's appointments".
- Two accounts: the same person has a different user id, practitioner id and template id per account, and a separate API key, shard and subdomain for each.
- Key entry and validation UX: check the role is practitioner, find the practitioner record, check the subdomain matches the clinic and the key suffix matches its shard. Also what happens when a key is archived or rotated. `[2026-09-27 reconciliation] Superseded — the practitioner's decision after Task P.1 (their own Cliniko role is administrator): the role is NOT a gate; validation accepts an active user with exactly one ACTIVE practitioner record (plan-cliniko-workflow-safeguards D10 amendment, built in clinics.py).`
- A POST whose outcome is unknown (timeout after send): reconcile by listing before any retry; if the listing is ambiguous, stop and ask the practitioner.
- Cliniko sanitises HTML, so a content-hash comparison must be computed on our canonical rendering, not on Cliniko's echo.
- The template question structure may drift (the practitioner edits the template in Cliniko). A name mismatch between the profile and the fetched template must refuse the write, never drop content silently.
- Whether a partial `content` (only the mapped questions) is accepted is UNCONFIRMED, as is which create fields are required.
- The informed-consent attestation question must never be answered by the app, because it is structurally unmappable.
- A queued note during an outage longer than 24 h expires under the retention bound, and the practitioner writes the note by hand.
- A Credential Manager read from an Explorer-launched app is verifiable only by a live launch (MSIX lesson).
- Test strategy without network in CI: an injected transport seam. A real-API probe on the practitioner's own account is practitioner-run.
- Reading appointments brings real patient names and ids into app memory. That is a new data flow for the data-flow map and retention schedule.
- Phase 5 surfaces not yet explored in code depth:
  - the embedded Start/status UI in the Cliniko page;
  - the consent popup (the recording-consent tick, distinct from the learning consent v3);
  - the previous/new resolution panel;
  - local semantic boundary detection ("new greeting" warning);
  - global keyboard and spoken pause/stop controls;
  - the runtime subdomain allow-list (`plan-phase1-security-foundation.md:55-61`).

## Exploration Summary

### Agreed Scope (Build Now)
First plan: **PLAN.md Phase 5 — workflow safeguards, in full** (practitioner decision 2026-09-27), built BEFORE Phase 4. It also takes the read-only Cliniko API work that verifying the context needs (practitioner decision 2026-09-27):
- **Recording starts only from an open Cliniko treatment note** (`/patients/<patient_id>/treatment_notes/<note_id>/edit`). No Start is offered on the calendar or any other page.
- Host↔app **named pipe**, per the locked Phase 1 topology and the Phase 2 hardening list.
- **Protocol extension** for encounter context and recording commands, with `protocol/fixtures/` staying the canonical contract.
- **Content script(s)** on authorised Cliniko hosts that read the clinic host (`<subdomain>.<shard>`), the patient id and the treatment-note id from the note page, with a runtime **clinic-host allow-list** for the two clinics.
- **Two clinic API keys** entered and stored in Windows Credential Manager via the existing `SecureStorageProvider(clinic_id, …)`. Each key is validated: `GET /user` shows a practitioner role, `/practitioners?q[]=user_id:=…` finds the practitioner record, `/settings/public` returns the matching subdomain, and the key's shard suffix matches the clinic host. `[2026-09-27 reconciliation] Superseded — the practitioner's decision after Task P.1 (their own Cliniko role is administrator): the role is NOT a gate; validation accepts an active user with exactly one ACTIVE practitioner record (plan-cliniko-workflow-safeguards D10 amendment, built in clinics.py).`
- **A confined, read-only Cliniko API client inside `scribe-app`**, connecting only to `api.<shard>.cliniko.com`. It verifies the open note with `GET /treatment_notes/<id>`: patient matches the URL, note is still a draft, and the booking and template links are resolved. It can also fetch the templates. The no-sockets tests and ruff bans become "no connection except Cliniko API hosts", and the security-doc network claims are rewritten as a class.
- A typed **`EncounterContext`** (clinic, patient, treatment note, booking, practitioner, template — all verified against Cliniko) replaces the opaque `encounter_context: str | None` and is bound immutably at Start.
- **Start and status controls, and the consent confirmation, in a Chrome side panel beside the Cliniko note page** (the tick is required before any recording), plus a **permanent recording/paused indicator**: a red or amber frame round the Cliniko page and the extension-icon badge. See the UI design decision below.
- **Immediate pause on every patient, note, account, tab or login change** (any change of the note URL counts), and the **previous/new patient resolution panel** (Finish previous / Resume previous / Discard previous). Speech is never moved between patients.
- **Likely-consultation-boundary warnings** (local semantic detection, warning-only) and **emergency controls**: global keyboard and spoken pause/stop.
- **Write-back blocked whenever the Cliniko context cannot be verified.** This is the guard the Phase 4 plan consumes.

### Deferred — Actionable Later
- **Second plan: PLAN.md Phase 4 — writing the draft.**
  - Why deferred: the practitioner chose Phase 5 first and two plans in order (2026-09-27). The write needs Phase 5's verified context, keys and API client.
  - Intended outcome: fill the practitioner's open draft by `PATCH /treatment_notes/<note_id>`. Before each write, re-read the note and refuse if it has been finalised or already holds practitioner-typed text. Bind each template profile per clinic to the Cliniko `treatment_note_template_id`, matching section and question names. Keep a local write ledger (session → clinic, patient, note id, content hash, result) and reconcile before any retry. Complete the session automatically after a confirmed write.
  - Relevant files: `session.py` (Complete path, QUEUED→WRITTEN), `session_store.py`, `note_config.py`, `ui/models.py`, `ui/note.py`, `ui/transcript.py`, `ui/main_window.py`, `docs/security/*`, `docs/testing/shipping-gate.md`.
  - Recommended next action: `/create-plan` for Phase 4 once the Phase 5 plan closes, reusing this scratch.
- **Flipping `COPY_TO_CLINIKO_ENABLED` and reframing the shipping-gate docs** to match the gate decision below.
  - Why deferred: it is a code and doc change, and the exploration writes no code.
  - Recommended next action: a task in the Phase 5 or Phase 4 plan, or a small standalone change, plus a `/document` pass. `plan-phase3a-note-pipeline.md` Task 9.1 needs the same reframing.
- **Three-or-more-speaker labelling and diarization tuning.** Unchanged, still blocked on the shared recording set.

### Excluded — Revisit Only If Needed
- **Starting a recording from the calendar or any page other than an open note.** Declined (2026-09-27): the calendar URL carries no patient or booking id, and reading the page DOM is fragile. Revisit only if starting from an open note proves impractical in clinic.
- **Creating a new note with `POST /treatment_notes`.** Declined in favour of filling the open draft (2026-09-27), because Cliniko already creates an empty draft when the note is opened. Revisit if that draft cannot be filled through the API (see the assumptions).
- **A Cliniko free-trial account for development.** Declined (2026-09-27): testing uses the practitioner's own accounts. Revisit if an API behaviour cannot be probed safely on a real account.
- **A test-patient write guard before the shipping gate.** Declined (2026-09-27) because the practitioner reviews and finalises every draft. Revisit if the practitioner stops being the sole finaliser (commercialisation).
- **A separate network helper process.** Declined; see Key Design Decisions. Revisit if firewall-enforced isolation of `scribe-app` is wanted, for example ahead of an independent privacy/security review before commercialising.
- **A desktop appointment picker as the context source.** Superseded by the open-note design.
- **Automatic finalisation of notes.** Never (PLAN.md).

### Accepted Assumptions — Revalidate Later
- **Per the practitioner, clicking "treatment notes" from an appointment makes Cliniko create a new, empty draft note immediately and open it for editing.** Not probed through the API. Risk if wrong: the open note may be an older draft with content, which the before-write check must catch; or the note may not be linked to the booking.
- **The Cliniko web app changes the URL without a full page load when moving between notes** (likely a single-page app). UNVERIFIED. Risk if wrong: none for correctness if the content script watches every URL change. It decides whether the `webNavigation` permission or an in-page watcher is needed.
- **Cliniko API contract details, per docs.api.cliniko.com, unverified against a live account:**
  - whether PATCH with `content` fills a draft created in the web app;
  - whether PATCH on a final note is refused (the before-write re-read closes most of the window; the race is residue);
  - whether a partial `content` is accepted or the full template structure must be sent;
  - which roles may call `/settings/public`;
  - whether the auto-created draft is linked to the booking and template.

  Risk if wrong: the first write fails, or the note cannot be verified. Mitigation: a practitioner-run probe on their own account.
- **The note author is the API key's practitioner-user** (per LEGACY docs, and the spec lacks `practitioner_id`). Risk if wrong: misattribution. Mitigation: key validation checks the role and the practitioner record, and the note's practitioner link is compared to it. `[2026-09-27 reconciliation] Superseded — the practitioner's decision after Task P.1 (their own Cliniko role is administrator): the role is NOT a gate; validation accepts an active user with exactly one ACTIVE practitioner record (plan-cliniko-workflow-safeguards D10 amendment, built in clinics.py).`
- **Agent-proposed, unconfirmed — the definition of "already holds practitioner-typed text".** Every answer in the note's `content` is empty or equal to the template's blank. Risk: a template default value is misread as typed text (refusing safely) or typed text is missed (overwriting it). Needs a probe of an auto-created draft's content.
- **Agent-proposed, unconfirmed — ledger and reconcile.** With a known note id a retry is a repeat PATCH of the same content: re-read the note, report success if the content hash already matches, PATCH if the note is still an empty draft, and stop and ask the practitioner otherwise.
- **Agent-proposed, unconfirmed — HTTP stack.** Stdlib `urllib.request`/`http.client` + `ssl` in one confined module, with a ruff per-file carve-out and no new dependency, versus a pinned `httpx` (needs practitioner authorisation).
- **Agent-proposed, unconfirmed — rendering.** A `rich_text` target becomes a Cliniko `paragraph` (escaped, allowed-tag HTML); a `plain_text` target becomes `text`; the attestation checkbox is never answered.
- **Agent-proposed, unconfirmed — the offline queue lives inside the existing 24 h recovery window** (no new durable queue store). A session that fails to write is retried from the Recovery screen and expires at 24 h. Risk: an outage longer than 24 h means the practitioner writes that note manually.
- **Whether the ledger must be encrypted, and its retention row.** Open; it holds patient and note ids.

### Key Design Decisions
- **Order: all of PLAN.md Phase 5 before Phase 4, as two plans in sequence** (practitioner, 2026-09-27). Rejected alternatives: a desktop appointment picker at Start, a picker at send time, Phase 5 context-only slices, and one combined plan.
- **Recording starts only from an open Cliniko treatment note, and the finished draft fills that same note** (practitioner, 2026-09-27). The note URL gives the patient and note ids, and any URL change pauses recording. Filling it meets Phase 4's "exactly one draft" by construction, which is Heidi's pattern too. Rejected: Start from the calendar (the URL has no patient or booking id; DOM reading is fragile), and creating a second note with POST.
- **The in-Cliniko UI is a Chrome side panel plus a full-page block on patient change** (practitioner, 2026-09-27, after four mockup directions). The mockups were in-chat widgets, not files, so the chosen design is recorded here in words:
  - Consent and every control live in Chrome's own side panel (`chrome.sidePanel`, a new extension permission), not in Cliniko's DOM, so a Cliniko redesign cannot break or hide them.
  - **Panel before Start:** patient name, appointment date and time, clinic, and "Note verified with Cliniko". The consent checkbox carries the PLAN.md wording, and Start recording stays disabled until it is ticked.
  - **While recording:** a red frame around the Cliniko page is the only in-page element. The panel shows a red "Recording" block with the timer, the patient and appointment, "Consent confirmed <time>", and Pause / Finish consultation.
  - **On a patient or note change:** recording pauses at once, the frame turns amber, and a full-page block covers Cliniko. It shows "Recording belongs to <A>" beside "You opened <B>", with Finish previous (<A>) / Resume previous / Discard previous. The panel mirrors "Paused" and names both patients. Nothing is moved between patients.
  - **With the panel closed,** the frame colour and the extension-icon badge still show the state.
  - Rejected: A (a strip inserted in Cliniko's layout, the most exposed to Cliniko page changes), B alone (a small corner pill that is easy to overlook while recording), and D (desktop-led, which leaves little visible in Cliniko).
- **Clinic keys and read-only Cliniko API verification move into the Phase 5 plan; writing the draft stays in Phase 4** (practitioner, 2026-09-27). Rejected: Phase 5 trusting the URL alone.
- **Cliniko HTTPS calls run inside `scribe-app`**, in one confined module that connects only to Cliniko API hosts (`api.<shard>.cliniko.com`). The no-sockets tests become "no connection except Cliniko API hosts" (practitioner, 2026-09-27).
  - Rejected: a separate network helper process.
  - The practitioner accepted, knowing it: the API key is read into the main process's memory; a future per-program firewall rule can no longer block `scribe-app` outright; the "no network" claim becomes "only to Cliniko". Regulators (Ahpra, OAIC, TGA) do not prescribe process architecture.
- **Development and testing use the practitioner's own Cliniko accounts**, with no trial account and no test-patient guard. The practitioner finalises every draft (practitioner, 2026-09-27).
- **The shipping gate (rubric v1) changes from blocking to a quality measurement** (practitioner, 2026-09-27). Neither API drafts nor copy-to-Cliniko wait on it, and it is still run as a quality check once the shared recording set exists. This supersedes the 2026-09-05 framing in which a pass flips `COPY_TO_CLINIKO_ENABLED`.
- **The session key and recoverable data are destroyed automatically once Cliniko confirms the draft and the ledger records it** (PLAN.md flow step 10; practitioner, 2026-09-27). A failed write stays retryable within the 24 h recovery window.
- **Forced by the code or the API:**
  - **Drafts only.** The client never sends `draft: false` and never moves a note toward final, because a finalised Cliniko note is immutable. Enforce this by construction, not by an allow-list of call forms (`docs/lessons.md` 2026-08-10).
  - **Keys only in Windows Credential Manager**, per clinic, through the existing `SecureStorageProvider`.
  - **The allow-list and the key must agree on the clinic host.** The web host is `<subdomain>.<shard>.cliniko.com` and the key suffix names the same shard.
  - **The host↔app transport is a user-ACL'd named pipe**, never a socket (the locked Phase 1 topology), with the Phase 2 hardening list.
  - **`protocol/fixtures/` stays the canonical message contract.**
  - **The security-doc network claims** ("no network sockets", "ONLY sanctioned network user", the ruff-ban comment and the module docstrings) are rewritten as a CLASS and get a cross-family peer pass (`docs/lessons.md` 2026-08-14).

## P.1 findings for the Phase 4 plan (2026-09-27, clinic 1 of 2)
- On a freshly opened note, `GET /treatment_notes/<id>` answers 200 with `draft: true`, `finalized_at: null`, and patient, practitioner, booking and `treatment_note_template` links; the note's patient equals the URL's and its practitioner equals the key user's. An ARCHIVED note answers NotFound.
- The auto-created draft is NOT content-empty: the practitioner's templates default the "Presenting complaint / patient progress" answer to a prompt scaffold (Site - / Chron - / Sensory - / Agg - / Rel - / General (Occupation, Exercise, sleep, alcohol, drug) - / Assoc ssx -). The draft write's "refuse if the note already holds typed text" rule must treat a template-default answer as not typed (compare against the note template's default, reachable via `treatment_note_template.links.self`), or every auto-created draft is refused. The scaffold labels are also a candidate structure for placing presenting-complaint content (practitioner decision).
- Clinic 2 is not yet probed (the practitioner lacks API-key permission on that account).
