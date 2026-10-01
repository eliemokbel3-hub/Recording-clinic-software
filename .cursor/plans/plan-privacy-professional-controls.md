# Feature Implementation Plan
**Feature:** privacy-professional-controls
**Overall Progress:** `100%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None (PLAN.md Phase 6)
- Follow-up plans: None

## Goal
Build PLAN.md Phase 6 for the single-practitioner app. The pieces:
- **Audit record.** A durable, encrypted, content-free record for every session, kept 7 years and exportable as CSV.
- **Past sessions tab.** A Heidi-like look-back holding each completed session's generated note, saved note and transcript (never audio). Encrypted with one key per entry, labelled by patient name + date, with a Hide-names toggle, Copy of the saved note, a two-step Delete now (worded for a recording made in error only), and a retention setting of "7 years" or "never" (default "never") — 7 years minimum by practitioner decision 2026-10-02 (originally 1 day to "never").
- **Exclusions.** Keep the app's data out of crash reporting, search indexing, roaming and OneDrive, warning where that can't be enforced.
- **Deletion.** Every Complete removes the session directory immediately.
- **Intended use.** A documentation-only line inside the app.
- **Practice documents.** Drafts in `docs/practice/` (patient information and consent, privacy information, downtime procedure, clinician review guide), with every security doc rewritten for the new stores as one class.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Opus 5.5 (`claude-opus-5-5`), executor the same Opus-class model (`/execute-loop` executor `claude-opus-5-5`, cross-family peer codex `gpt-6-astra`); no tier gap

### Agreed Scope (Build Now)
All confirmed by the practitioner in the 2026-10-01 planning session.
- **Audit record** (`audit.py`).
  - Contents: consent time and text version, `linked`, verification, `clinic_id`, `practitioner_id`, the clinic record's `user_id`, `booking_id`, `treatment_note_id`, model versions, write result, deletion result and Past-sessions events.
  - Never stored: patient name, patient id or any text.
  - Kept 7 years from the session date, then pruned.
  - Start is refused if its row cannot be written. Every later update is best-effort: it never blocks a write or a deletion, and a failure is counted and shown.
- **Past sessions tab.** The practitioner asked for it by name ("like Heidi"), reversing "Complete destroys everything". At every Complete the app keeps, encrypted:
  - the generated note (what the app first produced);
  - the saved note;
  - the transcript, behind "Show transcript".

  Audio is never kept. Each entry is labelled patient name + date, with a Hide-names toggle; the name is kept only in the entry, never in the audit row or the CSV. The tab offers Copy of the saved note only (through the existing clipboard-history-safe copy), a per-entry two-step Delete now, and Export CSV of the audit rows.
- **Retention setting for Past sessions**: 7 years or never — **AMENDED by practitioner decision 2026-10-02: a kept transcript is kept for 7 YEARS MINIMUM** (VIC/NSW/ACT health-records law; `docs/practice/README.md`'s first open question, answered). Originally 1 day, 7, 30 or 90 days, 1 year, 7 years, or never; the shorter choices are removed, a settings file holding one loads as 7 years (never a fail-closed reset) and the tab says so until the next save, and the sweep refuses any window under 7 years. The default is **never** (Heidi's compliance-FAQ default, checked 2026-10-01). It comes with a plain warning:
  - a kept transcript becomes part of the practitioner's health record — VIC Health Records Act 2001, NSW HRIP Act 2002, ACT Health Records (Privacy and Access) Act 1997, elsewhere APP 11.2;
  - it can be reached by an APP 12 access request or a subpoena;
  - it lives on this PC and this Windows login only, with no backup;
  - Cliniko stays the system of record;
  - (2026-10-02) it is kept for at least 7 years, and a child patient's transcript until they turn 25 — the app does not know ages, so choose "never" ("Until I delete them") then.

  Lowering the setting (never → 7 years) asks for confirmation. Delete now stays (composer recommendation; the practitioner may overrule), worded for a recording made in error only (the wrong patient, a test, or one recorded without consent).
- **Exclusions, "set + warn".**
  - The register script adds per-user Windows Error Reporting exclusions for `pythonw.exe`, `scribe-app.exe` and `scribe-host.exe`. The practitioner accepted that this also stops crash reports for any other Python GUI program under their login.
  - The app marks its data folder not-content-indexed.
  - A read-only startup check warns when the data folder is redirected, roamed, on a network path or inside OneDrive, or when the WER exclusions are missing. It never refuses recording.
  - Unhandled-exception hooks log only the exception type.
- **Every Complete removes the session directory immediately.** Failed sessions keep the existing 24 h sweep.
- **In-app intended-use line**, and `docs/security/intended-use.md` updated to match.
- **`docs/practice/`**: patient information + consent wording, privacy information, downtime procedure and clinician review guide. They are drafts, each headed "needs independent privacy/legal/clinical-safety review before use with other practitioners", and they cite every state (the product may be sold; the practitioner's clinics are in VIC).
- **The security docs, PLAN.md, AGENTS.md, design-system and code docstrings** are rewritten for the reversal as one class (see Critical Constraints C9).

### Deferred — Actionable Later
- **Passphrase-protected backup/restore of Past sessions.**
  - Why deferred: it is a feature of its own (passphrase custody, restore, backup location), and Cliniko remains the record. Practitioner disposition at the Deferral Confirmation Gate, 2026-10-01.
  - Intended future outcome: retained transcripts survive a dead disk or a lost Windows profile.
  - Relevant files / subsystems: `past_sessions.py`, the Past sessions tab, retention-schedule.md.
  - Dependencies / prerequisites: this plan's archive store.
  - Recommended next action: plan it before relying on Past sessions as part of the record, or before commercialising.
  - Risk if deferred: correctness: with the default "never", a lost disk or profile loses every retained transcript, and DPAPI-sealed data cannot be restored on another machine.
  - Revisit by: before commercialisation, or before Past sessions is relied on as part of the health record
- **Admin-only backup/snapshot exclusions** (HKLM `FilesNotToBackup` / `FilesNotToSnapshot`).
  - Why deferred: needs admin rights; the per-user app cannot set them. Gate disposition 2026-10-01.
  - Intended future outcome: an admin-run installer step sets them for `%LOCALAPPDATA%\ClinikoScribe`.
  - Relevant files / subsystems: the PLAN.md Phase 7 installer, `scripts/`.
  - Dependencies / prerequisites: PLAN.md Phase 7 (pilot and installation).
  - Recommended next action: add it to the Phase 7 installer plan.
  - Risk if deferred: minor: `%LOCALAPPDATA%` is outside Windows' default backup scope; Windows Backup / VSS may still capture it.
  - Revisit by: PLAN.md Phase 7 planning

### Excluded — Revisit Only If Needed
- **Chrome's own crash dumps.**
  - Why excluded: the extension holds only display strings (the patient name while shown), never audio, transcripts or keys. Chrome's crash reporting is a browser setting. Gate disposition: Accept, 2026-10-01.
  - When to revisit: at commercialisation.
  - Relevant files / subsystems: threat-model.md, the Chrome extension residue (8).
  - Recommended next action (if any): none; kept as a named residue.
- **A shared key for the whole archive.**
  - Why excluded: per-entry keys keep "cryptographic deletion" true for Delete now and expiry at no extra cost (see D3).
  - When to revisit: only if the per-entry layout proves slow (P.2 measures listing).
  - Relevant files / subsystems: `past_sessions.py`.

### Accepted Assumptions — Revalidate Later
- **The practice documents are drafts, not legal advice.**
  - Why accepted for now: the PLAN.md line 199 independent review is required before selling or deploying to other practitioners.
  - Risk if assumption becomes false: wording relied on without review.
  - Trigger for revisit: before any use with other practitioners.
  - Recommended next action: independent privacy/legal/clinical-safety/TGA-scope review.
- **Expiry and pruning happen only while the app runs.**
  - Why accepted for now: same as the 24 h rule today (retention-schedule "the 24-hour rule").
  - Risk if assumption becomes false: an entry outlives its setting while the app is closed.
  - Trigger for revisit: a background-task requirement.
  - Recommended next action: none; documented.
- **Deletion is a plain NTFS unlink of `key.dpapi` and the files**, not forensic erasure.
  - Why accepted for now: the existing accepted residual (`session_store.py:6-9`).
  - Risk if assumption becomes false: forensic recovery of unlinked ciphertext plus key.
  - Trigger for revisit: commercial deployment.
  - Recommended next action: none.

### Key Design Decisions
See `## Design Decisions` (D1–D14). Headlines:
- per-row audit files;
- per-entry archive keys with the same filenames;
- the archive written inside `complete_session` before the key is deleted;
- the name read from memory at Complete and matched by session id;
- the WER exclusion written with `winreg`;
- the location check done by `realpath` on environment-variable paths.

## Key Findings
Code baseline: `main` @ `bdf7eed`, verified 2026-10-01. Paths are under `desktop/src/scribe_desktop/` unless stated.

### Files / Symbols Involved
**Session custody (`session.py`).**
- `SessionController(backend, *, sessions_root=None, logger=None, live_transcriber_factory=None)` (505-512); `app.py:404` builds it. Every custody call runs on the GUI thread under `_lock`, and no new non-GUI custody caller may be added (docstring 484-503).
- `start()` (710): `bind_consent`, then `_retire_locked` at 759, then `wrap_key_to_file` 772, `write_encounter_record` 775-780, `SessionChunkStore.create` 781-783, worker start, and the cleanup `except` at 799-810 (`discard_session`).
- Complete paths:

  | Method | Line | `complete_session` call |
  |---|---|---|
  | `complete` | 1014 | 1048 |
  | `complete_without_note` | 1054 | 1086 |
  | `complete_deleting_saved_note` | 1093 | 1116 |
  | `complete_recovered` | 1492 | 1499 |
  | `complete_after_write` | 1655 | 1711, the ONLY one passing `remove_directory=True` |

- Discard: `discard()` 1122 (actual `discard_session` at 1222; an early return at 1218 for a concurrent discard), `discard_recovered` 1502/1508.
- Failure: `_fail_locked` 1809; `_on_capture_failure` 1893 (capture worker thread, holding the lock — NO audit hook there).
- Generation lease: `begin_generation` / `end_generation` / `with_generation_custody(lease, action(directory, crypto))` (1341-1389, 1531-1558). The lease requires QUEUED.

**The store (`session_store.py`).**
- `complete_session` (699-751) returns `None`. At 741 it holds `transcript_plain`, the decrypted canonical transcript bytes. `_verify_note_for_completion` (678-696) calls `_verified_note` (649-675), which returns the parsed `GeneratedNote`, but 696 throws it away. `delete_session_key` is at 745, `crypto.destroy()` at 749.
- `_resolve_session_identity` (637-646) uses the audio header and falls back to the DIRECTORY NAME.
- Other helpers:
  - `atomic_write_bytes` 535;
  - `SESSION_KEY_DESCRIPTION` 573; `wrap_key_to_file` 576 / `unwrap_key_from_file` 593 (both take `description=`);
  - `write_note` 816 (no AAD); `write_encounter` / `_encounter_aad` 889-905 (AAD pattern); `write.enc` AAD 946-948;
  - `read_note` 992; `_session_created_at` 1054; `SweepResult` 1021-1024; `sweep_sessions` 1099-1158, which skips non-session-id names at 1123.
- Docstrings that the reversal makes false: 44, 99-100, 721-726.

**Transcription (`transcription.py`).** `read_transcript(session_dir, crypto)` 1089, `transcript.enc` without AAD 1060, `TranscriptDocument.model_name` / `speaker_model_id` 359-367.

**Note (`note.py`).** `GeneratedNote` 675 (`schema_version`, `provider_name`, `template_profile_id`, `config_digest`, `style`), `render_note` 984, `NoteDraft` 2207 (never persisted).

**Encounter (`encounter.py`).** `EncounterContext` 116-129 (no user id), `ConsentAttestation` 146-155, `bind_consent` 158, `EncounterRecord` 186 (ids only), `NoteDisplay.patient_display_name` 266-271 (never persisted). `clinics.ClinicRecord.user_id` is at `clinics.py:266`.

**Model ids.** `language_model.LANGUAGE_MODEL_ID` / `SHA256` 57-70; `prose_style.PROMPT_VERSION` 103 (currently unreferenced); speaker `shipped_embedder_identity` (`speaker_embedding.py:572`).

**UI.**
- `ui/main_window.py`:
  - `StatusPanel` 198-228 (the Status tab);
  - tabs 437-445;
  - the recovered-Complete lambda 1288;
  - `_CheckoutEncounter` docstring 130-131 ("ids only", already inaccurate);
  - `_begin_checkout` 1316-1336, `_checkout.result = result` 1400, reset at 1431;
  - `_on_draft_ready` 1533;
  - write flow: `_on_write_requested` 1635, `_prepare_attempt` 1801, `_finish_write` 1856, `_store_write_record` 1901.
- `ui/transcript.py`:
  - lease `self._lease` 152, `begin_generation` 776, `save_note` 836-855 (the `with_generation_custody` + `write_note` pattern), `_release_lease` 826-830;
  - Complete calls 961 / 1003;
  - Complete strings and tooltips 276-278, 630-633, 889-890, 966-968, 1021-1025 ("Complete failed: … No key deletion was performed").
- `ui/bridge.py`: `live_reverification` 392, `_live_display` set 1031-1032 (Verified Start only) and cleared 1238-1240 in `_tick`; Start refused `"failed"` 1027-1029.
- `ui/models.py`:
  - `written_done` 310; `CHROME_REFUSALS["failed"]` 932;
  - `SessionControllerLike` protocol 1103-1204; `custody_refusal_text` 1217-1234 (only `SessionControllerError` / `AudioCaptureError` text is shown);
  - `read_for_review` 1452-1467; `format_transcript_text` 1627; `format_note_body` 1789.
- `ui/note.py`: `_place_note_text` 244 (the one clipboard placement); read-only views 446 / 527; `show_saved_note` 752-781 (a view pattern — do NOT reuse `NoteScreen`, which carries review, lease and write state); `_refinalise` 1748-1779.
- `ui/recovery.py:451` calls `discard_session(info.directory, None)` directly; `info.session_id` is available.
- `ui/session_screen.py` has the two-step Discard at 395-424 and the "Start failed: …" prefix at 330.
- `ui/__init__.py:13-14` (docstring "never written anywhere except the encrypted store").

**App and logging.**
- `app.py`: `run_sweep` 407-415 (drops its results), the sweep `QTimer` 444-456, `_SWEEP_INTERVAL_MS` 55.
- `logging_setup.py`: `ALLOWED_KEYS` 43-64, `_PAYLOAD_SIGNATURES` 72 (incl. patient identifiers 82-84), `log_event` 439.

**Other code.**
- `practitioner_profile._SealedStore` 286-413 (the sealed-store pattern and typed errors); `secure_storage.SessionCrypto` 60-115 (`encrypt` / `decrypt` take associated data at 99 / 103).
- `draft_write.is_mock_note` 1113.
- `note_config.load/save_practitioner_settings` 1018-1039 (the settings-file pattern).
- `scripts/register-native-host.py`: `register()` 65 with read-back verify 95-96, `unregister()` 108 / delete 113, `winreg` via a local import, no unit tests.
- `desktop/pyproject.toml`: gui-scripts 60-65; TID251 bans only `PySide6.QtNetwork`, `socket`, `http`, `urllib.request` (90-99), so `ctypes` / `winreg` are fine.

### Codebase Integration Notes
**Shared helpers inventory** (reuse, don't re-invent):
- `SessionCrypto`, `wrap_key_to_file` / `unwrap_key_from_file(description=…)`, `atomic_write_bytes`, the `_SealedStore` typed-error style;
- `read_for_review`, `read_transcript`, `read_note`;
- `format_note_body`, `format_transcript_text`, `_place_note_text`;
- `with_generation_custody`;
- the `note_config` settings load/save pattern;
- the two-step button pattern (`session_screen.py:395-424`);
- the Qt-free decision-module pattern (`ui/note_review.py`);
- `custody_refusal_text`;
- `log_event`.

**Tests that change** (verified):
- `test_session_store.py:596-638` — `test_the_default_keeps_the_directory` at 634 is inverted;
- `test_session_machine.py:1500` (`kwargs == {"remove_directory": True}`);
- transcript-survives-Complete assertions: `test_integration_no_sockets.py:937, 1165, 1332` and `test_transcription.py:1233`;
- tab pin `test_ui_screens.py:2966-2979` (count 8 plus the title list);
- `written_done` / Complete-string pins: `test_write_lines.py:64-65, 267` and `test_ui_screens.py:3413, 6658, 7290, 7343`;
- DPAPI description pins in `test_display_name.py:48-56` (also: no new UI text may contain "Cliniko Scribe", 36-45);
- tripwire rules `test_session_types.py:236-241, 290-293` (a new signature must not be a substring of an `ALLOWED_KEYS` rendering);
- the fake controllers implementing `SessionControllerLike` in `test_ui_screens.py` and `test_ui_prose_stage.py`.

**Construction sites.**
- `SessionController(` is built about 24–28 times across 10–11 test files (helpers `_controller(...)` in `test_session_machine.py:134`, `test_enrolment.py:449`, `test_live_session.py:228`, `test_unreviewed_review.py:124`), so new constructor parameters MUST default to `None`.
- `MainWindow(` is built in 8 test sites (`_main_window` at `test_ui_screens.py:934-958`, `test_hands_free`, `test_system_pause`, `test_ui_pause_and_unreviewed`, `test_status_and_app`, …). All must inject the new roots and a fake Windows layer.

**Isolation and confinement.**
- `test_integration_no_sockets.py:346+` spawns a child that MIRRORS `app.main` with the real `LOCALAPPDATA`. Extend the mirror to cover the new startup work, with the new roots redirected.
- `TestConfinement` (`test_cliniko_client.py:1541-1547`) already scans every source file for network imports, so no new network-guard test is needed. `test_exactly_one_tid251_noqa` forbids any new `noqa: TID251`.
- `StatusPanel.refresh_registration` already reads the real HKCU in every `MainWindow` test (`main_window.py:215-218`). Any NEW Windows reads go through the injected layer (lessons.md:109).

**Machine gotchas.**
- `docs/lessons.md:13-20`: agent shells are MSIX-virtualized for both `%LOCALAPPDATA%` and HKCU, so registry writes, read-back verifies, attribute sets and location checks prove nothing from an agent shell. Only a practitioner run from a normal terminal (P.3) counts.
- `lessons.md:121`: the venv launchers start the BASE `pythonw.exe` as a child, which is why D10 excludes `pythonw.exe`.
- `lessons.md:91`: a periodic path that newly touches a sealed store — the hourly `label.enc` decrypt — is a named H1 review target.

**Other contracts.**
- Enrolment creates no session directory, so it has no audit row.
- `complete_recovered` sessions cannot generate (`can_generate` is False, `main_window.py:1282-1284`).
- Write reservations: `complete_after_write` needs `_custody_reservations == {id: 1}` (`session.py:1690`), and the caller releases the reservation (1675-1678).

### External / API Findings
Research done 2026-10-01; cite these in `docs/practice/`.
- **Ahpra, "Meeting your professional obligations when using AI in healthcare".** It sets NO retention period for transcripts. It says: tell patients, obtain informed consent and ideally note the response in the health record, check the accuracy of records AI creates, and store data per legal requirements.
- **State health-records law.** VIC Health Records Act 2001, NSW HRIP Act 2002 and ACT Health Records (Privacy and Access) Act 1997 require at least 7 years from the last contact, or until age 25 for a minor. Other states rely on the Privacy Act APPs (APP 11.2: destroy or de-identify when no longer needed; APP 12: access).
- **AJGP 2025, "Is AI A-OK?".** Many scribes keep no audio and delete transcripts within 7–30 days. A transcript holding health information not carried into the record is in tension with the retention laws.
- **Heidi Health.** It never keeps audio. Its retention is user-set: one blog page says 1–90 days; its compliance FAQ says 1 day to "never delete", with a default of "never delete".
- **Windows Error Reporting.** The per-user exclusion is `HKCU\Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications\<exe>` = DWORD 1, which is what `WerAddExcludedApplication(..., FALSE)` writes.

## Planned Workflow Summary

### Flow 1 — Start (linked or desktop)
1. The consent is bound.
2. The new `RecordingSession` object (and so its `session_id`) is built BEFORE `_retire_locked`. The constructor is pure and has no side effect; today it runs just after the retire (`session.py:759-760`).
3. **`AuditLog.begin`** writes the new row (consent, ids, and `user_id` resolved by the caller from the clinic registry) BEFORE `_retire_locked`. A failure of the ACTUAL write, not just a writability probe, refuses Start with the previous QUEUED session still installed and nothing on disk (round 1 PR-MED-002).
4. The previous session is retired, the key is wrapped, and `encounter.enc` is written.
5. The audio store is created and the worker started. EVERY failure after a successful `begin` marks the row `start_failed` (best-effort), not only the existing cleanup `except` (799-810). That includes the retire refusal for an uncleared live transcriber (`session.py:1882-1883`, which leaves the previous session installed) and the directory-creation failure (765-768). One `try` spans everything after `begin` (round 2 PR-MED-002).

If step 3 fails, Start is refused ("Start failed: the audit record could not be saved (…). Nothing was recorded."). Chrome gets the existing `failed` refusal.

### Flow 2 — Generate, review, write
- The first rendered note body is written to `generated.enc` under the generation lease (D2), and replaced on regeneration.
- The write flow is unchanged. Every durable write-record transition updates the row's write result (best-effort), at the shared `_store_write_record` boundary: attempt, reconciled-written, finished and unknown. A pre-send `WriteRefusal` records its fixed refusal code, never the display line (round 1 PR-MED-005).

### Flow 3 — Complete (all five paths)
1. The UI resolves the keep label BEFORE calling Complete: patient name (D5), date, clinic and flags.
2. `complete_session` verifies the transcript and note as today.
3. Unless the session is mock, it writes the Past-sessions entry: fresh key, same filenames, staged, fully verified through its own key (D1), then moved into place carrying its `pending` marker.
4. It deletes the source key: the IRREVERSIBLE BOUNDARY (C1). Once `delete_session_key` has succeeded, the in-memory key is ALWAYS destroyed and the controller ALWAYS makes its terminal transition, releasing the lease and reservation as today. Marker removal (the commit) and the directory removal that follow are best-effort post-boundary steps: a failure there is left to reconciliation or `orphan_gc` and is shown truthfully ("Completed. The Past-sessions copy will appear after the next check."), never as "No key deletion was performed" (round 3 PR-MED-003).
5. It returns content-free `CompletionFacts`.

The audit row gets the models, `deletion=completed…` and the `past_session` outcome. An archive failure BEFORE the boundary (step 4) raises `PastSessionWriteError`, keeps the key, stays QUEUED and allows a retry: "Complete failed: the Past-sessions copy could not be saved. No key deletion was performed — try again, or Discard."

### Flow 4 — Discard, expiry, sweep
- Discard (controller, recovered, and the recovery list's direct call) writes `discarded`. BEFORE it deletes the source key, it also deletes, key first, any `past_sessions\<id>` or staging entry an interrupted Complete already published for that id (C1's ordering rule).
- `run_sweep` returns its `SweepResult`s. Each now also carries the session's content-free `created_at` (epoch seconds), captured BEFORE deletion, so a `pre_audit` row for a session that expires on its first post-upgrade startup keeps its true date (round 1 PR-MED-004).
- `expired` / `orphan_gc` are recorded by session id while the row is still `pending`. Expiry removes any interrupted archive entry through the sweep's `before_destroy` callback, BEFORE the source key goes. `orphan_gc` (the key already gone) leaves the entry to commit (C1). No decryption of `encounter.enc`.
- Pending-entry reconciliation (C1) runs at startup and on every sweep tick: a `pending` entry whose source key is gone is committed.
- Staging cleanup runs at every startup and sweep tick, INDEPENDENT of the retention setting (it runs under "never" too).
- The audit month prune runs at startup and every 24 h.
- The Past-sessions retention sweep runs at startup and hourly, and never when the setting is "never".

### Flow 5 — Past sessions tab
- The list shows date + name, or "Patient hidden".
- Opening an entry shows the generated note and saved note side by side, the Cliniko write outcome (from the audit row), Copy (saved note) and Show transcript.
- Delete now is two-step.
- The retention combo carries the warning and a confirmation when lowered.
- Export CSV uses a save dialog.
- A persistent status label shows audit failures and location or WER warnings.

### Flow 6 — Exclusions
- At startup the app sets NOT_CONTENT_INDEXED (best effort) and runs the location and WER checks, which produce warning lines.
- The register script writes and verifies the three WER exclusions; `--unregister` removes them.

## Design Decisions
- **D1 — Past-sessions entries use the SAME filenames** (`transcript.enc`, `note.enc`, `generated.enc`), plus `label.enc`, re-encrypted byte-for-byte under a FRESH per-entry key (DPAPI description `"ClinikoScribe past-session key"`), in a directory named exactly `<id>`.
  - Why:
    - the existing readers (`read_for_review`, `read_transcript`, `read_note` — whose identity check falls back to the directory name) work unchanged;
    - byte-identical plaintext keeps the transcript digest valid;
    - deleting the session key keeps today's "audio unrecoverable" property.
  - **Verification before the source key goes** (round 1 PR-MED-003). `read_for_review` alone is NOT sufficient: it uses the in-memory key, and it skips a missing note. `write_entry` therefore:
    1. re-opens the STAGED entry through its own `key.dpapi`, unwrapped from disk with the archive description;
    2. requires the SOURCE-DERIVED artifact set (D6): exactly the verified files the source session holds at Complete, less a deleted note;
    3. decrypts `label.enc`, `generated.enc` (when expected), `transcript.enc` and `note.enc` (when expected) with the existing readers;
    4. compares each plaintext's SHA-256 with the source bytes.

    Only then is the entry published.
  - Rejected:
    - (a) moving the session directory and keeping the session key — the key also encrypted the unlinked `audio.enc` and superseded `.tmp` files, so "no audio kept" would become "audio unlinked, key retained";
    - (b) one combined `content.enc` — new readers for no gain.
- **D2 — `generated.enc`** is a new session file, encrypted under the session key with AAD `generated:<id>` (the `_encounter_aad` pattern, `session_store.py:889-905`). It holds `{session_id, created_at, provider_name, style, language_model_id|null, prompt_version|null, text}`, where `text` is the first `format_note_body` output shown to the practitioner, before any review action. The two ids are captured at render time, `null` when no prose stage ran (round 2 PR-MED-005).
  - It is written by a new `TranscriptScreen` method on the `save_note` pattern (`with_generation_custody`), called from `MainWindow._on_draft_ready`.
  - It is replaced on regeneration. If the first prose-style render finishes before any edit, it is rewritten with that prose text.
  - Recovered sessions without it show "Generated note not kept".
  - Why: the first draft cannot be rebuilt from what is persisted — `NoteDraft` is never persisted, declined proposals never become assertions, typed replacements keep only the id, and generation depends on config and models at the time.
  - Rejected: re-running `compose_draft` at view time (not reproducible).
- **D3 — one key per archive entry**, so Delete now and expiry are cryptographic erasure per entry.
  - Rejected: one archive key (per-entry deletion would be a plain unlink of ciphertext under a surviving key).
- **D4 — the archive is written inside `complete_session`**, after verification and before `delete_session_key` (745), through an optional `keep` argument. The argument carries the label plus a writer callback, so `session_store` does not import `past_sessions` or UI code.
  - `_verify_note_for_completion` returns the verified note, so there is no second decrypt.
  - `complete_session` returns a new content-free `CompletionFacts` (model ids, note provider and style, and the past-session outcome).
  - Why: all five paths reach this one choke point under `_lock`, with the fail-closed ordering already in place.
- **D5 — the patient name is resolved in the UI before Complete**, matched on `session_id`, in this order:
  1. the bridge's Verified Start display, through a new public accessor (the bridge may be `None` when the pipe did not start);
  2. `live_reverification()`;
  3. `_checkout.result` when its outcome is `Verified`.

  Otherwise the label reads "Name not available", or "Desktop recording (no Cliniko note)" for a desktop recording. The name is never persisted at Start (`EncounterRecord` stays ids-only). The `SessionControllerLike` protocol and the fakes gain an optional label parameter.
- **D6 — what each path keeps: the SOURCE-DERIVED set** (round 2 PR-MED-004). The archive copies exactly the verified artifacts the source session holds at Complete: `transcript.enc` always; `generated.enc` whenever present (including `complete_recovered`); `note.enc` whenever present and not deleted by the path. `complete_without_note` / `complete_deleting_saved_note` therefore keep the transcript plus a generated note if one exists, never the saved note. Transcript-only Completes and adopted pre-upgrade sessions without `generated.enc` are valid, and the entry says "Generated note not kept" / "No saved note".
  - **Mock sessions** keep nothing, and the row reads `not_kept_mock`. A session is mock when ANY discriminator says so: the transcript's `model_name` identifies the mock backend; `generated.enc`'s `provider_name` starts with `mock-`; or the saved note's `provider_name` does.
  - On the two delete-note paths the early unlink at `session_store.py:728-730` is REMOVED (round 3 PR-MED-002, superseding round 2's read-before-unlink). `delete_note=True` now means the note is excluded from note verification and from the archive, while `note.enc` stays on disk until the source key is deleted and the directory removed. It is unreadable once the key is gone, and the directory is always removed (Task 1.1). Its provenance is read with the in-hand crypto on EVERY attempt, so a retry after any later failure still has it; a note that cannot be read gives `note_provenance=unknown`. This keeps the existing delete-unreadable-note escape: an unreadable note never blocks the Complete.
  - If the note is unreadable (the existing delete-unreadable-note escape), its provenance is `unknown`. The note is not archived on these paths anyway, so the decision falls to the remaining discriminators: the transcript's `model_name` and, when present, `generated.enc`'s provider. The row records `note_provenance=unknown`.
  - Discard, expiry, orphan_gc and failed sessions: never archived. Discard and expiry delete any pending entry an interrupted Complete published for that id BEFORE the source key goes; orphan_gc commits it instead (C1). A session that failed and is later recovered and Completed through `complete_recovered` IS archived: Complete, not the earlier failure, decides.
- **D7 — audit store layout.**
  - `%LOCALAPPDATA%\ClinikoScribe\audit\key.dpapi` holds one store key, description `"ClinikoScribe audit key"`.
  - Rows are `YYYY-MM\<session_id>.enc`, AES-GCM with AAD `audit:<id>`, updated by read → mutate → `atomic_write_bytes`; `update()` finds a row by globbing `*\<id>.enc`.
  - A month folder is pruned when the month's END + 7 years has passed, plus a one-day margin: the folder is the row's LOCAL calendar month, which ends up to 12 h after the UTC one in the zones west of UTC (amended round 7 LOW-008, for round 6 MED-002).
  - Rejected: one sealed blob (about 50–100 MB rewritten per update at 7 years, and one bad byte loses everything); an append-only JSONL (a new torn-line parser and compaction).
- **D8 — `AuditRow` schema** (pydantic, `extra="forbid"`, frozen, `schema_version: Literal[1]`, a before-validator reading `schema_version` first).
  - A newer-version row is kept byte-for-byte, never rewritten, listed as "newer format", and pruned only with its month.
  - An unreadable row is counted and never overwritten.
  - Fields:
    - `session_id`, `session_date` (the practitioner's LOCAL calendar date; every timestamp field is UTC — amended round 7 LOW-008, for round 6 MED-002), `origin` (`recorded` or `pre_audit`);
    - `consent_confirmed_at`, `consent_text_version`, `linked`, `verification`;
    - `clinic_id`, `practitioner_id`, `user_id`, `booking_id`, `treatment_note_id`;
    - `models`: transcription model, speaker model id, note provider, note schema version, template profile, style, language model id, prompt version.
      - **Provenance at the time it happened** (round 2 PR-MED-005). Complete never fills these from the constants in force at Complete.
        - The saved note's LM id and prompt version are captured at SAVE into a new session file `saved-provenance.enc` (session key, AAD `saved-provenance:<id>`). It is written inside the SAME `with_generation_custody` action as `note.enc` (`ui/transcript.py:850`), and carries the SHA-256 of the exact canonical note bytes (`note.to_bytes()`). It is written FIRST: `note.enc`'s replacement stays the Save commit boundary (round 4 PR-MED-001).
          - A provenance-write failure fails Save before anything is committed, exactly as a failed note write does today.
          - A provenance file left without a matching `note.enc` (the note write then failed or was interrupted) is harmless: its digest matches nothing, so Complete records `unknown`.
          - `_note_committed`, `_note_saved`, the lease, Cancel review and the Complete controls keep today's meaning, because only `note.enc` commits. A note is saved in the same process that rendered it, because renderings are persisted only at Save, so the constants then ARE the render's.
        - At Complete the ids are used only when that digest matches the `note.enc` being completed; otherwise `unknown` (round 3 PR-MED-004). The digest never leaves the session: the audit row gets only the ids. No best-effort audit update happens at Save.
        - The generated note's come from `generated.enc`.
        - The transcription and speaker ids come from the persisted `TranscriptDocument`.
        - A legacy or no-prose value is `unknown` / `none`.
        - There is no `GeneratedNote` schema change.
    - `write`: attempts, last outcome, last refusal, `written_at`;
    - `deletion`: `pending`, `completed`, `completed_without_note`, `discarded`, `expired`, `orphan_gc` or `start_failed`, with a timestamp;
    - `past_session`: `none`, `archived`, `not_kept_mock`, `deleted_early` or `expired`, with a timestamp;
    - `note_provenance`: `known` or `unknown` (an unreadable note on a delete-note path, D6);
    - `events`: capped at 32.
  - `pre_audit` rows, for sessions started before Phase 6, are dated by `_session_created_at`, made public and read BEFORE the directory is removed. On the Complete / Discard paths the caller reads it; on the sweep path `SweepResult` carries it as a new `created_at` field, captured before deletion (round 1 PR-MED-004). A missing or untrusted date (the existing clamp rules) is recorded as the sweep time, with `origin=pre_audit`.
- **D9 — unreadable audit key** (e.g. DPAPI broken by an admin password reset). Starts are refused, and the Past sessions tab offers "Start a new audit record". It renames `audit\` to a NEW, never-existing `audit.unreadable-<YYYYMMDD-HHMMSS>-<8 hex>\` (nothing is deleted; an existing quarantine directory is never overwritten or reused) and creates a fresh key (round 4 PR-LOW-002).
  - A failure creating the new key after the rename leaves `audit\` absent. The next reset or Start then creates a fresh store, and both quarantined stores stay untouched.
- **D10 — exclusions.**
  - The WER exclusions are written by `winreg` in `register-native-host.py` (DWORD 1 each for `pythonw.exe`, `scribe-app.exe`, `scribe-host.exe`), verified by read-back, and removed by `--unregister`.
  - The location check is `os.path.realpath` of the root compared with `%USERPROFILE%\AppData\Local`. It warns on:
    - containment in `%OneDrive%`, `%OneDriveCommercial%` or `%OneDriveConsumer%`;
    - a `\\` prefix or a remote drive (one `GetDriveTypeW` call);
    - containment in `%APPDATA%`.
  - `check_wer()` also checks the RUNNING interpreter (`os.path.basename(sys.executable)`, injected in tests) against the excluded names (round 2 PR-MED-006). The documented console launch (`.venv\Scripts\python.exe -m scribe_desktop.app`, AGENTS.md) runs `python.exe`, which is not excluded (breadth kept as agreed), so that launch shows a fixed warning: "Crash reports are not excluded for this launch (python.exe) — start the app with scribe-app.exe."
  - Rejected: `SHGetKnownFolderPath` (GUID marshalling for no gain) and `WerAddExcludedApplication` (needs ctypes; same registry effect).
- **D11 — the consent tick text stays `recording-consent-v1`.** The patient information document carries its own version, `patient-info-v1`.
- **D12 — a Chrome-side Start refusal reuses the existing `failed` refusal** (no protocol change). `AuditWriteError` and `PastSessionWriteError` subclass `SessionControllerError`, so `custody_refusal_text` shows their text.
- **D13 — Hide names** is persisted in the Past-sessions settings file; the default is shown.
- **D14 — the in-app intended-use line** is a constant in `ui/models.py`: "Documentation aid, not clinical decision support. You review and finalise every note in Cliniko." It is shown on the Status tab and on the Past sessions tab. There is no Session footer today, and the plan does not invent one.

## Schema / Data Changes
- **New file `audit\`**: key + monthly row files (D7, D8).
- **New file `past_sessions\<id>\`**: `key.dpapi`, `label.enc` (AAD `past-label:<id>`; date, clinic id, patient name or `None`, has-generated / has-saved flags), `transcript.enc`, `note.enc` and `generated.enc` (the source-derived set, D6), plus the content-free plaintext `pending` marker until the entry commits (C1). `SweepResult` gains `created_at` (D8). Staging goes to `past_sessions\.staging\<id>\` and is cleaned by `clean_staging()` at every startup and sweep tick, independent of retention (C1).
- **New session file `generated.enc`** (D2). It dies with the session directory.
- **New session file `saved-provenance.enc`** (D8): `{note_digest, provider_name, style, language_model_id|null, prompt_version|null}` under the session key. It is written with `note.enc`, never archived, and dies with the session.
- **New settings file `config\past_sessions.json`** `{schema_version: 1, retention_days: int|null, hide_names: bool}`. An unreadable file means nothing is deleted and the tab says so. Since H5 (practitioner decision 2026-10-02) `retention_days` is null or 2557 (7 years); a removed shorter value (1, 7, 30, 90, 365) LOADS as 2557 through a before-validator (no `schema_version` change, the read never rewrites the file, the next save writes 2557); any other value still fails closed.
- **No migration of existing sessions.** Sessions completed before this ships are gone as today. Sessions still on disk get `pre_audit` rows when first touched.

## Config / Environment / Deployment Impact
- No environment variables and no new runtime dependency (`winreg` and `ctypes` are stdlib).
- The practitioner re-runs `scripts\register-native-host.py` from a normal terminal after the update, to write the WER exclusions (P.3).
- There is no network change: the offline contract stays "no connection except Cliniko's API, and none at startup or idle".
- Rebuilding the extension is NOT needed (no protocol or extension change).

## Critical Constraints
- **C1 — Archive before the key, one entry per session id.**
  - **Ordering.** The Past-sessions entry is written, FULLY verified (D1) and moved into place BEFORE `delete_session_key`. Any archive failure BEFORE the boundary keeps the key and the QUEUED state, and allows a retry. After the boundary (the source key deleted) nothing is retryable, and Flow 3 step 4 governs. The existing refusals — the UNCLEARED live transcriber and failed note verification — still win and run first.
  - **Lifecycle** (round 1 PR-MED-001, reworked by round 2 PR-MED-001). The durable state lives IN the entry, not in whether the source directory exists:
    - **Publish.** An entry is published carrying a content-free plaintext marker file `pending`.
    - **Pending entries.** Only a Complete press ever publishes an entry, after verification. An entry whose `pending` marker is present AND whose source `sessions\<id>\key.dpapi` still exists is PENDING: Complete has not finished. It is never listed.
    - **Ordering rule, the load-bearing invariant.** Every NON-Complete destroyer of a source session — `discard()`, `discard_recovered`, `ui/recovery.py:451`, and the sweep's `expired` — removes the entry for that id, key first, BEFORE it deletes the source key. The sweep gets a `before_destroy(session_id)` callback, invoked before its `delete_session_key`.
    - **Commit.** A `pending` entry whose source key is gone can therefore only follow a Complete that reached `delete_session_key`. Reconciliation — right after `delete_session_key` inside Complete, at startup, and on every sweep tick — commits it by removing the marker.
    - **orphan_gc splits** (round 3 PR-MED-001). The real branch (`session_store.py:1139-1146`) handles BOTH an absent key and an existing dead (zero-length or truncated) key.
      - A CONFIRMED-absent key (`FileNotFoundError`) deletes nothing in the archive, and the entry commits.
      - An existing dead key is a destroyer like expiry: `before_destroy` removes the pending entry key-first BEFORE the dead key is deleted. If that removal fails, the dead key is NOT deleted this tick.
      - An inaccessible key (any other `OSError`) is neither absent nor dead: nothing is committed or deleted.
      - `reconcile_pending` commits only on a confirmed-absent source key.
    - **Retry.** A retried Complete replaces a pending entry key-first.
    - **Staging cleanup** is separate from retention and runs even under "never".
- **C2 — Audit never blocks custody.** `begin` failure refuses Start. `begin` itself runs before `_retire_locked`, so a failed row write leaves the previous QUEUED session installed (Flow 1, round 1 PR-MED-002). Every other audit update is best-effort and never raises into a write, Complete, Discard or sweep. A failure is counted and logged as `log_event(…, "audit_update_failed", detail_code=stage)`.
- **C3 — No content in the audit.** The audit row and the CSV never hold the patient name, patient id, transcript, note text or audio. New distinctive field names from `audit.py` / `past_sessions.py` are added to `_PAYLOAD_SIGNATURES`, and none may be a substring of an `ALLOWED_KEYS` rendering.
- **C4 — Audio is never archived.** The archive copies only transcript, note and generated bytes; the session key is still deleted.
- **C5 — GUI thread only.** No audit or archive call is added on a worker thread (`_on_capture_failure` stays without a hook).
- **C6 — No host state in tests.** Tests never touch the real registry, WER, `%LOCALAPPDATA%` or the clipboard. New constructor and `MainWindow` parameters default to `None` or injected fakes, and a sentinel Windows layer raises if the real one is reached in tests.
- **C7 — The sweep never decrypts `encounter.enc`** (Constraint 7). Audit updates from the sweep are keyed by session id only.
- **C8 — No new network use, no new `noqa: TID251`.**
- **C9 — The reversal is rewritten as ONE class.** Every statement the reversal makes false is changed together, and H3 greps for leftovers (`only copy`, `destroyed at Complete`, `in memory only` for names, `no durable audit`, `Phase 6` deferrals). The list:
  - `PLAN.md` 48, 67, 124, 141-146;
  - `retention-schedule.md` rows 31/33/51/52/57, 122-137 (the destruction trigger at 126-131), plus new rows for audit, past sessions, `generated.enc` and the CSV;
  - `threat-model.md` 26 ("names in memory only"), 112-117, 1684-1687, 1856-1861, 1911-1913 (residue g), 2503-2506, 2525-2529, plus a new section for the audit and past-sessions stores and their residues;
  - `data-flow-map.md` 270-275, 664-666, 888-889, plus a new flow;
  - `intended-use.md` 47-52;
  - `incident-process.md` 67-74;
  - `docs/security/README.md` (index);
  - `design-system.md` 13-14 and 462;
  - `docs/architecture/phase-history.md`;
  - `CHANGELOG.md`;
  - `AGENTS.md` pointers;
  - code docstrings `session_store.py` 44 / 99-100 / 721-726, `ui/__init__.py` 13-14, `main_window.py` 130-131, `note.py` `NoteDraft` (it is persisted as rendered text via `generated.enc`);
  - UI strings `ui/transcript.py` 276-278 / 630-633 / 889-890 / 966-968 and `ui/models.py` 310 `written_done`, with their test pins.
- **C10 — Every practice doc carries the review banner** and cites every state.

## Validation / Verification
**Baseline (planning dry-run, 2026-10-01, `main` @ `bdf7eed`):**
- `ruff check .` in `desktop/`: "All checks passed!"
- `pytest --co`: 4868 tests collected.
- Anchor greps: all cited `session.py` / `session_store.py` / `main_window.py` lines confirmed.
- `docs/practice/` does not exist yet.
- `tabs.count() == 8` is pinned at `test_ui_screens.py:2968`.

**Per task:** each task's own tests, listed on the task. **Per phase:** `desktop/`: `ruff check . && mypy && pytest` (from `desktop/`). `extension/`: `npm run qa` stays green and unchanged (no extension change).

**New test files:**
- `test_audit.py`: round trip; wrong description or AAD refused; newer row untouched; unreadable row never overwritten; month prune at the 7-year boundary; CSV formula guard; `update` never raises. Two D9 resets in one day and a key-creation failure after the rename, then retry: both quarantined stores stay untouched (round 4 PR-LOW-002).
- `test_past_sessions.py`:
  - per-entry keys independent; the entry readable by `read_for_review`;
  - the full verification refuses an unusable archive key, a missing expected saved note, and a corrupt label or generated file;
  - staging cleanup runs under "never";
  - pending entries are not listed;
  - retention sweep keeps undated and future-dated entries; "never" causes no decrypt;
  - settings unreadable → nothing deleted.
- Failure injection (round 1 PR-MED-001), at staging, at publish, at verification and at source-key deletion, each followed by retry, Discard, expiry and restart: no discarded or expired session keeps an entry; a retry leaves exactly one.
- Round-2 tests:
  - interruption right after source-key deletion (the entry commits at the next reconcile);
  - a failed or partial source-directory removal followed by `orphan_gc` (the entry commits and is NOT deleted);
  - interruption between expiry's `before_destroy` and its key deletion (no discarded content is ever committed);
  - Start failing at the retire refusal (the row reads `start_failed`; the previous session stays INSTALLED);
  - Start failing at directory creation, which runs after the retire (the row reads `start_failed`; the previous session is no longer installed, but its on-disk files stay recoverable and it stays in the Unreviewed reminder index). The installed-session guarantee belongs only to the `begin` failure and the retire refusal (round 5 PR-LOW-001);
  - a real transcript plus a mock-provider saved note through both delete-note paths (not archived), and an unreadable note there (`note_provenance=unknown`);
  - a transcript-only Complete, an adopted pre-upgrade session without `generated.enc`, and a recovered Complete with an existing `generated.enc` (all archived with the source-derived set);
  - render → restart → adopted Complete (the LM and prompt ids come from Save and `generated.enc`, not current constants);
  - `check_wer` under an injected `pythonw.exe` (clear) and `python.exe` (warning).
- Round-3 tests:
  - a pending entry with a zero-length or truncated source key (the entry is removed before the dead key is GC'd; a removal failure keeps the dead key this tick);
  - an inaccessible key is never treated as absent;
  - both delete-note paths failing after the old unlink point, then retry and restart (provenance still read; a mock saved note still not archived);
  - marker-removal failure injected on all five Complete paths (key destroyed, terminal state, lease and reservation released, truthful status, a later reconcile commits);
  - Save A → restart with changed versions → Save B → Complete (B's ids used; a digest mismatch gives `unknown`).
- An upgrade test: a pre-Phase-6 session that expires on the first startup gets a `pre_audit` row with its true date, and `encounter.enc` is never decrypted (round 1 PR-MED-004).
- `test_exclusions.py`: fake layer only; location warnings; WER check; attribute set is best-effort; exception hooks log only the type name.
- A script test for `register-native-host.py`'s WER write, read-back and unregister, loaded via importlib as `test_setup_scripts.py` does, with a fake `winreg`.

**Session tests** (additions to `test_session.py`, `test_session_machine.py`, `test_session_store.py`):
- archive-before-key ordering;
- archive failure keeps the key and QUEUED and allows a retry;
- UNCLEARED still wins;
- mock (both detectors), Discard and expiry never archive;
- every Complete removes the directory;
- Start refused on an ACTUAL audit row-write failure (not only an unwritable store) with nothing left on disk and the previous QUEUED session still installed and usable (round 1 PR-MED-002);
- `start_failed` recorded.

**UI tests** (`test_ui_screens.py`):
- the tab (Hide names, two-step Delete now, lowering retention confirms, warning text pinned, CSV save via an injected dialog, Copy through `_place_note_text` with the fake clipboard);
- the name resolution order and session-id match for live, adopted and recovered sessions, plus "Name not available";
- the tab pin updated to 9 tabs.

**Other checks:**
- The `test_integration_no_sockets.py` child mirror is extended to the new startup work, with the roots redirected.
- H3's grep over the C9 phrase list returns only intentional hits.

**Practitioner smoke** (a normal terminal, NOT an agent shell — `docs/lessons.md:13-20`):
- **P.1** A linked recording goes through Write and Complete: Past sessions shows the name, both notes, the transcript and the write outcome; Hide names and Copy work; the CSV opens in Excel with that row and no name.
- **P.2** (rewritten for H5, the 7-year minimum, 2026-10-02) On the Past sessions tab: (1) the "Keep past sessions for:" combo offers EXACTLY "Until I delete them" and "7 years"; (2) the warning under it ends with the 7-year and child lines ("… A kept transcript is kept for at least 7 years. If the patient was a child, it must be kept until they turn 25 - Clinic Scribe does not know a patient's age, so choose "Until I delete them" when that applies."); (3) choosing "7 years" from "Until I delete them" asks "Keep past sessions for only 7 years? …" with "Delete older sessions" / "Keep things as they are" (the app asks on every move to the shorter setting, whether or not older entries exist — none are 7 years old, so nothing is deleted); choose "Delete older sessions" and the line reads "Past sessions are kept for 7 years."; set it back to "Until I delete them" if that is your setting; (4) the line under Delete now reads "Use Delete now only for a recording made in error: …"; select a TEST entry, press Delete now — the message shows the made-in-error wording and the 7-year rule — then Confirm delete: the entry is gone and the CSV row reads `deleted_early`; (5) note the listing speed with the entries present. Expiry itself (an entry 7 years old deleted, recorded `expired`) is proven by the unit tests, not by hand: `test_past_sessions.py::TestRetentionSweep` (`test_only_entries_past_the_window_go`, `test_an_entry_exactly_at_the_window_goes`, `test_a_window_under_seven_years_is_refused_and_deletes_nothing`), `TestSettings::test_a_removed_shorter_window_loads_as_seven_years`, and `test_ui_screens.py::TestPastSessionsTab` (`test_lowering_retention_asks_then_sweeps_and_records_expired`, `test_the_sweep_deletes_what_the_setting_says_through_the_shared_store`, `test_a_removed_shorter_setting_reads_as_seven_years_and_says_so`, `test_a_sweep_refused_for_a_short_window_deletes_nothing_and_says_so`).
- **P.3** Re-run `register-native-host.py`: the three WER values exist under HKCU, and the startup warning clears when the app is launched with `scribe-app.exe`. Launched from a console via `python.exe -m scribe_desktop.app`, the uncovered-launch warning shows (D10).
- **P.4** Make `audit\` read-only: Start is refused with the stated line ("Start failed: AuditWriteError: the audit record could not be saved (the audit folder could not be written). Nothing was recorded." — amended round 7 LOW-009), nothing is recorded, and a queued previous session stays tracked.
- **P.5** Complete a desktop (unlinked) recording and a mock session: the first is archived as "Desktop recording (no Cliniko note)", the second is not archived.

## Deferred / Out of Scope
- **Past-sessions backup/restore.** Likely future work; see Deferred — Actionable Later. It needs the archive layout (D1/D3).
- **Admin-only backup/snapshot exclusions.** Future work for PLAN.md Phase 7's installer.
- **Chrome crash dumps.** An accepted residue, not a goal.
- **Clinic 2's P.1/P.2 from the earlier plans.** Unaffected by this plan.

## Current State / Handoff Note
- **EXECUTOR stage-7 leg r3 (2026-10-02T05:28:25+10:00) — codex round 40 (pass stage-7.p1 peer_round 1): PR-LOW-034 CONFIRMED and APPLIED as a class; round 40 Closed. ruff clean, mypy 56 files, history-check OK (40 + 40); pytest owed.**
  - **What changed (wording only, behaviour unchanged — Delete now still works on any entry):** `ui/past_sessions_view.py` — a shared tail `UNREADABLE_DELETE_LIMIT` ("Delete now is only for a recording made in error - read the downtime procedure before deleting it.") ends `ENTRY_UNREADABLE` (the selected unreadable entry — a sibling the peer did not cite), `undated_line` (1 and many; the plural says "them") and `open_failed_line` (every reason). The first two also say the entry "is still kept" and is not deleted by age; `open_failed_line` makes no "still kept" claim, because its reason may be `not_found`.
  - **Docs:** `docs/practice/downtime-procedure.md` — leave an unreadable entry; delete it only if it was a recording made in error, or once the reviewer question is answered (the question stays). The "could not be deleted" bullet now says those entries are already past the setting, so Delete now there is the deletion the setting asked for. `retention-schedule.md` (Fail toward keeping; the "Until I delete them" bullet's "can only be deleted"); `threat-model.md` residues (c) and (d).
  - **Left, checked:** the shipping gate's "delete the run's entries with Delete now" (test recordings, inside the limit); docstrings that say an unreadable entry "can still be deleted" (capability, still true); the plan's closed history.
  - **Tests:** `test_ui_screens.py` — `test_an_entry_that_fails_to_open_names_the_next_step` pin updated; NEW `test_no_read_failure_line_offers_delete_now_without_the_made_in_error_limit` (literal pins for `ENTRY_UNREADABLE`, `undated_line(1)`, `undated_line(3)`; every read-failure line, each `PAST_SESSION_REASONS` code and an unexpected error, carries the limit and never "can delete").
  - **Composer:** run `tests/test_ui_screens.py` (the only test file changed; source changed: `ui/past_sessions_view.py`). Then the round-41 confirmation is your call.
- **EXECUTOR stage-7 leg r2 (2026-10-02T05:20:57+10:00) — `/review-loop` over H5 CONVERGED at round 39 (1 of 3): 0 CRIT / 0 HIGH / 0 MED / 2 LOW, both docs-only in `docs/practice/`, applied. No code or test change since the composer's green run (5300 passed / 9 skipped); ruff clean, mypy 56 files; history-check OK (39 + 39).**
  - **Every named target held, checked from the code** (detail in the round 39 entry): the upgrade maps only a genuine `int` in the legacy set (the `type(...) is int` guard is load-bearing — `True`, `1.0` and `7.0` compare equal to members — and the invalid-file tests would catch its loss); no path deletes a committed entry younger than 7 years except Delete now (every remover enumerated; the sweep's guard runs before any read); both new status lines are constants and clear on the right saves; the old choices are gone (grep re-derived from scratch; only the legacy constant, its tests, removal descriptions and research quotes remain); each new test fails against its named regression; `ui/models.py` is unchanged since the hardening-close tree `017ae66`, so `CONSENT_TEXT_V1/V2/V3` are untouched; PR-MED-030 Part B reads DECIDED (a) in all current text.
  - **LOW-001 (applied):** the child rule ("until 25") was stated bare in the patient sheet (:51), the privacy information (:87) and the clinician guide (:122-125); the practice README's cite-every-state rule needs the states. Each now names Victoria, NSW and the ACT, with the Australian Privacy Principles elsewhere.
  - **LOW-002 (applied — composer item 3):** the practice README now says none of the drafts has been given to a patient, so pre-review changes stay within `patient-info-v1`.
  - **Not done here:** the per-round `ROLE: round` loop-log line — this leg has no granted shape that appends to `.cursor/loops/`; the composer's own log covers it (reviewer = this executor, live session, `claude-opus-5-5`, round 39).
  - **H5 stays 🟨** for the composer's codex confirmation. **Composer:** no suite owed (docs only since the green run). Smoke: P.2 as rewritten in leg g1.
- **EXECUTOR stage-7 leg g1 (2026-10-02T05:12:22+10:00) — H5, the 7-YEAR MINIMUM retention (practitioner decision (2) of 2026-10-02) BUILT; decision (1), PR-MED-030 Part B = (a), recorded. ruff clean, mypy 56 files; pytest owed by the composer.**
  - **Code (`past_sessions.py`):** `MIN_RETENTION_DAYS = 7*365+2` (:120), `RETENTION_DAYS_CHOICES = (MIN_RETENTION_DAYS,)`, `LEGACY_RETENTION_DAYS = {1,7,30,90,365}` (:124), `RAISED_CONTEXT_KEY`. The upgrade: a `mode="before"` validator `_raise_a_legacy_window` (:951) maps a value whose `type(...) is int` and is in the legacy set to 2557 BEFORE the unchanged strict check (so `true`, `1.0`, `"30"` still fail closed; any other int still fails `_a_choice`) and flags it in the validation context; `read_past_session_settings` (:984) returns `LoadedPastSessionSettings(settings, retention_raised)` (:975); `load_past_session_settings` is now its `.settings` (same signature). The read never rewrites the file; the next save writes 2557. Defence in depth: `RetentionSweepReport.too_short` (:284) and `sweep_report` refusing any window `< MIN_RETENTION_DAYS` before any read (:707) — nothing deleted, `retention_too_short` logged with no id, `problem` stays False (it is not a retry case), never raises.
  - **Code (`ui/past_sessions_view.py`):** `RETENTION_OPTIONS` = ("Until I delete them", None), ("7 years", 2557) (:144); `RETENTION_WARNING` (:151) keeps round 30's Part A wording verbatim and appends "A kept transcript is kept for at least 7 years. If the patient was a child, it must be kept until they turn 25 - Clinic Scribe does not know a patient's age, so choose "Until I delete them" when that applies."; `DELETE_HELP` (:119) and `DELETE_CONFIRM_MESSAGE` (:123) limit Delete now by wording to a recording made in error (the wrong patient, a test, or one recorded without consent) and give the 7-year reason; `RETENTION_RAISED_LINE` (:166), `SWEEP_TOO_SHORT_LINE` (:173).
  - **Code (`ui/past_sessions.py`):** the help line under Delete now (:189); `_load_settings` reads `read_past_session_settings` and keeps `_retention_raised` (:587); the status line shows `RETENTION_RAISED_LINE` while the file still holds a removed value (:788) and `SWEEP_TOO_SHORT_LINE` for a refused sweep (:790). **My call on "say once":** the line is DERIVED, shown until a save writes 7 years — never an unasked write (the file is still written only by a retention choice or a Hide names click). To make that save reachable, choosing the SAME "7 years" again now saves when (and only when) the file was raised (:635) — no confirmation (not a lowering), message "Past sessions are kept for 7 years."; a Hide names click also writes 7 years and clears the line. Delete now's behaviour (two clicks / 10 s / `deleted_early`) is unchanged.
  - **Not changed, flagged for review:** (i) "choosing 7 years asks the existing confirmation only if older entries exist" in the composer's brief does not match the code — `is_lowering` asks on EVERY never → 7 years move, entries or not; I kept the behaviour and wrote P.2 to match. (ii) The app's unreadable-entry lines (`ENTRY_UNREADABLE`, `undated_line`, `open_failed_line`) still point at Delete now for an entry that can never be read; the downtime procedure now carries a `[Reviewer: …]` mark on whether such an entry must still be kept. (iii) `patient-information-and-consent.md` is `patient-info-v1` and its retention row / spoken script changed — if v1 was ever handed to a patient, the README's own rule makes this `patient-info-v2` (practitioner to say; not bumped here).
  - **Tests (pytest owed):** `test_past_sessions.py` — every removed-value call retargeted to the 7-year window with dates shifted past it (`SEVEN`/`WINDOW`; the boundary test gained a one-second-inside sibling); `test_the_choices_are_the_offered_settings` re-pinned (2557; legacy set disjoint); NEW `test_a_window_under_seven_years_is_refused_and_deletes_nothing` (0, −1, 1, 7, 30, 90, 365, 2556: no unwrap, nothing deleted, `too_short`, two `retention_too_short` log lines, then 2557 deletes), `test_a_removed_shorter_window_loads_as_seven_years` (each legacy value × hide: loads as 2557, raised, file untouched by the read, save writes 2557, reads back not raised), and six new fail-closed blobs (2556, 2558, 0, −7, `7.0`, `"30"`, `[365]`). `test_ui_screens.py` — `_PS_SEVEN`/`_PS_WINDOW`; every removed-value site retargeted (lowering, declined, raise → now 7 years → "never" with an entry past 7 years kept, the shared-store sweep, wired signals, sweep-cannot-finish, the archive-unlistable, failing-audit, unreadable-entry, sweep-disarms-delete and C3-logging tests); `test_the_sweep_lines_follow_the_current_setting` drops the "raise" case (with two choices it is the "never" case) and its "declined" / "save_fails" cases now hand-edit to "never" then choose 7 years (declined / confirmed-but-unsaved); the warning pin updated; NEW `test_the_combo_offers_exactly_the_two_choices`, `test_the_warning_carries_the_child_rule`, `test_delete_now_is_worded_for_a_recording_made_in_error`, `test_a_removed_shorter_setting_reads_as_seven_years_and_says_so` (5 legacy × same-choice / Hide names save), `test_a_sweep_refused_for_a_short_window_deletes_nothing_and_says_so` (a 1-day setting forced past the model with `model_construct`).
  - **Grep enumeration (repo-wide: `1 day|7 days|30 days|90 days|1 year|1, 7, 30|1–90|1 day to`, then `retention setting|Until I delete them|Delete now|lowering|7 years` over docs/PLAN/CHANGELOG/AGENTS):** CHANGED — `PLAN.md:152`; `CHANGELOG.md:9` (+ a new H5 bullet); `docs/practice/README.md` (open question 1 → "Answered by the practitioner" with what the app offers; the other three questions kept); `patient-information-and-consent.md` (retention row, choices, spoken script, Delete now bullet); `privacy-information.md` (retention row, kept-transcripts paragraph, "relies on"); `clinician-review-guide.md` (the regenerate bullet no longer suggests Delete now for a poor draft; the Past sessions bullets); `downtime-procedure.md` (unreadable entry, the new raised-setting line); `docs/security/retention-schedule.md` rows 63/65 and the Past sessions "How long" rule; `threat-model.md` (THE PAST SESSIONS TAB paragraph, residue (s) rewritten with what is and is NOT enforced, PR-MED-030 Part B → DECIDED (a)); `data-flow-map.md` flow 22 THE TAB; `intended-use.md`; `incident-process.md` (the "short retention setting" sentence); `design-system.md` (Delete now, the confirmation, the warning pin, the new lines); this plan's Goal, Agreed Scope, Schema, P.2, H5, the C9 residue list, and every executor/handoff/round-status line that called Part B OPEN (:828, :831, :868, :879, :888, :2380, :2472 as numbered before this bullet was inserted — the composer bullets untouched). LEFT (research facts, not the app's choices): the AJGP "7–30 days" and Heidi "1–90 days / 1 day to never delete" lines (README, plan External Findings). LEFT (closed history): the plan's stage-3 leg c1 string list (:664) and round 16 MED-002's "kept for 30 days". Code: only `LEGACY_RETENTION_DAYS` and its comment name the old values. AGENTS.md has no listing (its Current Status is `/document`'s).
  - **`CONSENT_TEXT_V1/V2/V3` untouched. No new dependency, env var, network use or `noqa: TID251`.**
  - **Composer:** run the full desktop suite (changed source: `past_sessions.py`, `ui/past_sessions_view.py`, `ui/past_sessions.py`; changed tests: `test_past_sessions.py`, `test_ui_screens.py`). Then resume me for `/review-loop` round 39 (cap 3) over H5 only. **For the smoke:** P.2 is rewritten (Validation / Verification).
- **COMPOSER RUN-STATE (`/execute-loop` run `cliniko-ppc-20261001-065724-c0dd`, isolation=none):** preflight complete 2026-10-01 07:01 (harness probe PASS: git status, ruff, mypy in-grant; pytest composer-run). Stage map: stage-1..stage-5 = Phases 1–5, stage-6 = Hardening stage, stage-7 = Practitioner smoke. Current: stage-7 (Practitioner smoke) — PAUSED awaiting the practitioner (run-close outcome=paused, 2026-10-01 17:2x). Tree snapshots (temp-index `git write-tree`, no ref moved) per phase close in `.cursor/loops/ppc-tree-snapshots.txt` — a later phase's peer pass can diff against them (`git diff <tree> -- <files>` after a fresh write-tree) to isolate that phase's changes. Logs: `.cursor/loops/stage-<N>-*.log`; policy log `.cursor/loops/cliniko-ppc-20261001-065724-c0dd-policy.log`. Smokes batched per the practitioner's standing preference (`gate-disposition key=live-user-smoke choice=defer-batched`); every phase stays UNCOMMITTED until its smoke-pass — the batched smoke is P.1–P.5 (P.4 covers Phase 1's Start refusal; P.1/P.5 cover Complete removing the session folder). The practitioner chose to build rather than run a 6th plan peer round.
- **COMPOSER Phase 1 close (2026-10-01 08:3x):** Tasks 1.1–1.4 built by stage-1 (executor session `1a2a560d`, legs a1–a8). In-session `/review-loop` converged at round 7 (6: 2 MED + 12 LOW; 7: 17 LOW — all applied). Composer suites: 4952→4967→4978 passed with one missed/retargeted test site each time, then green — **4979 passed**, ruff clean, mypy 52 files. Codex pass `stage-1.p1` (gpt-6-astra medium) CONVERGED at peer_round 3/5 as two slices plus a confirmation: round 8 (slice A, source) clean; round 9 (slice B, tests) PR-LOW-007/008 — test-harness, Fix-now, applied (tests only); round 10 PR-LOW-009 — docs-only, Accepted-with-record (D9 harness tail; a test comment says "on disk" for the store seam). Every escape check clean, refs unchanged across every activation. NOT committed (batched smoke). Phase 1 has no open gate.
- **COMPOSER Phase 2 close (2026-10-01 12:11):** Tasks 2.1–2.3 built by stage-2 (executor session `ca134858`, legs b1–b7). Composer suites: 5082+1 failed (the `commit_deferred` audit pin — kept out of the audit deliberately) → 5083 → 5086 green. In-session `/review-loop` converged at round 12 (11: 1 MED + 2 LOW; 12: 2 LOW — applied/documented). Codex pass `stage-2.p1` (gpt-6-astra medium) CONVERGED at peer_round 3/5: round 13 (slice A, source) PR-LOW-010 (link-following key removal — class closed across every `past_sessions.py` path; junction tests run, directory-symlink variants skip on this host) and PR-LOW-011 (strict settings fields), both Fix-now applied; round 14 (slice B, tests + confirmation) PR-LOW-012/013 — plan-required coverage added (tests only); round 15 clean. Close suite **5110 passed, 4 skipped**, ruff clean, mypy 53 files. Every escape check clean, refs unchanged. NOT committed (batched smoke). Carried forward: Task 3.2 must wire the hourly sweep to the shared store's `sweep` (never `sweep_past_sessions`) and record `past_session=archived` for ids `reconcile_pending` commits (round 12 LOW-002); H3 must take the pre-existing link-following shape in `session_store.sweep_sessions` / `discard_session` (round 13 LEG 1); Task 5.2's known-limitations list gains the executor's four quirks. Phase 2 has no open gate.
- **COMPOSER Phase 3 close (2026-10-01 14:0x):** Tasks 3.1–3.3 built by stage-3 (executor session `05bf0715`, legs c1–c9). Composer suites: 6 failed (audit test double lacked the tab's surface → typed `PastSessionsAudit` Protocol) → 5140 green; after round 16, 2 failed (code→sentence split → one `failure_reason`) → 1 failed (export test fake underflow) → 5156 green. In-session `/review-loop` converged at round 17 (16: 2 MED + 19 LOW; 17: 2 LOW — all applied). Executor-reversed quirk: Hide names is now refused while the settings file is unreadable (the file is overwritten only by an explicit retention choice). Codex pass `stage-3.p1` (gpt-6-astra medium; reviewed from Phase-3-only tree diffs against the Phase 2 close snapshot) CONVERGED at peer_round 3/5: round 18 (source) PR-LOW-014 stale sweep warning → fixed; round 19 (tests + confirmation) PR-LOW-015 (round 18's class on reload routes — `_reload_settings` now always repaints status) + PR-LOW-016/017/018 test strength (click-time Delete deadline, audit failure during Delete/expiry, log-record capture) → fixed; round 20 (confirmation) PR-LOW-019 test-harness → fixed (production clearing of an open entry on expiry verified), pass closed without a further confirmation round (first harness-only round, tests-only fix). Close suite **5168 passed, 4 skipped**, ruff clean, mypy 55 files. Every escape check clean, refs unchanged. NOT committed (batched smoke) — Phase 3 is the first UI-bearing phase: the smoke must cover the Past sessions tab (see the EXECUTOR stage-3 leg c1 bullet's smoke list). Carried to Task 5.2: the design-system doc items (the tab in the tab list, its two confirmations, Delete now as a destructive action) and the named residues (Hide names masks the label only; `pre_audit` rows for pruned/reset sessions; recovered commit dated now with deletion `pending`; an unsaved Hide names choice lasts until close; wall-clock trust; undated entries never age out). Phase 3 has no open gate.
- **COMPOSER Phase 4 close (2026-10-01 14:4x):** Tasks 4.1–4.2 built by stage-4 (executor session `aa149178`, legs d1–d4). Composer suites: 5236 → 5239 → 5246 passed (4 skipped), green at every run. In-session `/review-loop` converged at round 22 (21: 1 MED — the native host now installs the same type-name-only hooks, stdout untouched — + 3 LOW; 22: clean). Codex pass `stage-4.p1` (gpt-6-astra medium, one slice from a Phase-4-only tree diff) CONVERGED at peer_round 2/5: round 23 PR-MED-020 (a failing log handler inside exception handling let the stdlib `handleError` print the original exception chain to stderr — fixed by `QuietHandlerErrors` on every handler `setup_logging` builds; class widened to every handler-failure path in both processes) + PR-LOW-021 (an older native-host test read real HKCU — stubbed); round 24 clean. Close suite **5246 passed, 4 skipped**, ruff clean, mypy 56 files. Every escape check clean, refs unchanged. NOT committed (batched smoke; P.3 = the practitioner re-runs `register-native-host.py` from a normal terminal and checks the WER values, the startup warning and the `I` attribute on new files — see the EXECUTOR stage-4 leg d1 bullet). Carried to Task 5.2: a console launch no longer prints tracebacks (AGENTS.md's "keeps console output" line), both processes run the hooks, `sys.last_*` dropped, the one-line log-failure report, and the residues (third-party loggers fall to the stdlib last-resort handler; NOT_CONTENT_INDEXED is folder-only and relies on inheritance). Phase 4 has no open gate.
- **COMPOSER Phase 5 close (2026-10-01 15:5x):** Tasks 5.1–5.2 built by stage-5 (executor session `40537e0c`, legs e1–e6). Composer suite green at 5247 passed, 4 skipped (once after the build, once after the only string change). In-session `/review-loop` converged at round 26 (25: 4 MED + 17 LOW; 26: 11 LOW — all docs). Codex pass `stage-5.p1` (gpt-6-astra medium; two slices from Phase-5-only tree diffs, then confirmations) CONVERGED at peer_round 5/5 (the cap): round 27 (security docs) 3 MED + 1 LOW overstatements (whole folder "encrypted", "destroyed at Complete" in the shipping gate, names "only in the encounter record", Past-sessions Copy omitted) → fixed as classes; round 28 (practice docs + confirmation) 2 MED + 1 LOW (absolute "nothing leaves / no crash reports", learning-filter overstatement, "first draft kept") → fixed; round 29 PR-MED-029 (the local-only class not closed: intended-use + the spoken consent script) → 81-hit sweep, fixed; round 30 PR-MED-030 (the same claim in two APP strings) → Part A the Past-sessions retention warning reworded + pinned; Part B the current practitioner consent `CONSENT_TEXT_V3` NOT changed — **OPEN PRACTITIONER DECISION** (see the executor e6 bullet, "PRACTITIONER DECISION (PR-MED-030 consent wording)": (a) recommended — keep consent-v3, residue named in the threat model and retention schedule, fix the wording at the next consent version; (b) consent-v4 now, ~30 sites in 15 files, re-consent required, phrase learning and Own voice off until then); round 31 clean. Every escape check clean, refs unchanged. NOT committed (batched smoke). Practitioner reading before the smoke: all of `docs/practice/` (open questions in its README, especially whether a kept transcript must itself be retained 7 years in VIC/NSW/ACT, and the `[Reviewer: …]` marks) and the consent decision above. Owed to `/document` at run end: AGENTS.md Current Status / Last Session / Tech Stack "Database" row, and a `docs/lessons.md` line (a console launch no longer prints tracebacks). H3 input: the pre-existing link-following shape in `session_store.sweep_sessions` / `discard_session` (round 13 LEG 1). Phase 5 has one open gate: the consent-wording decision (deferred to the batched smoke).
- **COMPOSER stage-7 SMOKE PASS + COMMIT (2026-10-02):** P.2 re-checked on the H5 build — PASS. With P.1/P.3/P.4/P.5 (above) the batched smoke P.1–P.5 PASSES. Final suite before commit: 5301 passed, 9 skipped (directory-symlink variants), ruff clean, mypy 56 files. Phases 1–5 + hardening (H1–H5) committed as ONE local commit (the per-phase tree snapshots in `.cursor/loops/ppc-tree-snapshots.txt` record each phase's end state); not pushed.
- **COMPOSER stage-7 H5 close (2026-10-02 05:3x):** H5 (7-year minimum retention) built by legs g1/r2/r3 (executor session `c8b618a5`); `/review-loop` round 39 (2 LOW docs, converged); codex pass `stage-7.p1` rounds 40 (PR-LOW-034: read-failure lines offered Delete now without the made-in-error limit — fixed as one shared `UNREADABLE_DELETE_LIMIT`, docs aligned) and 41 (clean confirmation) — CONVERGED at 2/5. Suites: full 5300 passed / 9 skipped after g1; `test_ui_screens.py` + `test_past_sessions.py` 526 passed / 8 skipped after r3; full suite re-run owed before commit. ruff clean, mypy 56 files. Escape checks clean, refs unchanged at `1e564b4`. H5 🟩. **Practitioner:** re-check P.2 on the new build (restart the app). Small follow-ups recorded: `register-native-host.py` should explain WinError 32 (host exe locked by Chrome) instead of a traceback.
- **COMPOSER stage-7 SMOKE RESULTS (2026-10-02, practitioner, normal terminal):** P.1 PASS; P.3 PASS (all six checks; step 1 first failed with WinError 32 because Chrome held `scribe-host.exe` open — passed after closing Chrome; a friendly message there is a small follow-up for `scripts/register-native-host.py`); P.4 PASS (write-deny ACL on `audit\`, removed afterwards); P.5 PASS. P.2 ran on the pre-H5 build — the practitioner re-checks P.2 steps 1–3 (two choices, child line, Delete now wording) after H5's review and codex confirmation.
- **COMPOSER stage-7 PRACTITIONER DECISIONS (2026-10-02):** (1) **PR-MED-030 Part B DECIDED (a)** — keep `CONSENT_TEXT_V3` unchanged with the residue named (threat model, retention rows 42/46); the qualified wording goes into the next consent version. No build impact. (2) **README open question 1 ANSWERED — a kept Past-sessions transcript is kept for 7 YEARS MINIMUM** (VIC/NSW/ACT health-records law). Build impact, so the run resumes with a stage-7 leg BEFORE the smoke: the retention choices shrink to "Until I delete them" (default, unchanged) and "7 years"; a settings file holding a removed shorter value loads as 7 years (no fail-closed reset of the store); the sweep refuses any window under 7 years; Delete now is KEPT (composer recommendation, practitioner may overrule) but limited by wording to a recording made in error (wrong patient, a test, or one recorded without consent), with the 7-year rule in its confirmation; the 7-years choice says a child patient's transcript must be kept until they turn 25 (the app does not know ages — choose "Until I delete them"). Docs follow (practice README question marked answered, retention schedule, threat model, design system, CHANGELOG). Smoke P.2 is rewritten to match.
- **COMPOSER Hardening close + RUN PAUSE (2026-10-01 17:2x):** H1–H3 by stage-6 (executor session `f8249b71`, legs f1–f6): H1 rounds 32–33 (13 LOW at the phase seams + 1 LOW docs), H2 round 34 (6 behaviour-neutral simplifications), H3 rounds 35–36 (7 LOW — `session_store.link_state` via `os.lstat` because Python 3.13+ `is_symlink()`/`is_junction()` return False on an unreadable folder; link refusal extended to the sessions root and the audit month folders; the CSV export's fresh temp name; size caps on audit rows, `saved-provenance.enc`, the settings file — plus 3 LOW docs). H4 = codex pass `stage-6.p1` (from hardening-only tree diffs): round 37 PR-LOW-031 (size-cap tests not proving bounded reads → `conftest.bounded_read_spy` for all five capped readers) + PR-LOW-032 (residue (m) "no tracebacks at all" → scoped to uncaught exceptions) applied; round 38 PR-LOW-033 (the staged-label read lacks a spy test; production bounded) Accepted-with-record (D9 harness tail). Suites: 5254 → 5262 (+1 test-fixture failure, fixed) → **5267 passed, 9 skipped** (all directory-symlink variants), ruff clean, mypy 56 files. Every escape check clean across the whole run, refs unchanged at `1e564b4`. **NOTHING IS COMMITTED** (batched-smoke preference). **For the practitioner, before and during the smoke:** (1) read all of `docs/practice/` — the README's open questions (above all: must a kept transcript itself be retained 7 years in VIC/NSW/ACT? if so the short retention settings and Delete now may conflict) and every `[Reviewer: …]` / `[Practice: …]` mark; (2) DECIDE PR-MED-030 Part B (consent-v3 wording): (a) recommended — keep consent-v3, residue named, fix the wording at the next consent version; (b) consent-v4 now (re-consent; phrase learning and Own voice off until then); (c) an information line on the Practitioner tab outside the consent text (no re-consent); (3) run P.1–P.5 (Validation / Verification) from a NORMAL terminal — P.3 needs `register-native-host.py` re-run there (agent shells are MSIX-virtualised; a verify from one proves nothing) and a check that new files in the data folder carry the `I` (not-content-indexed) attribute; the smoke lists in the EXECUTOR stage-3 leg c1 and stage-4 leg d1 bullets add the Past sessions tab and the startup warnings. **After a PASS:** commit Phases 1–5 + hardening (one commit per phase is no longer separable in the tree — the per-phase tree snapshots in `.cursor/loops/ppc-tree-snapshots.txt` record each phase's end state if separate commits are wanted), then `/document` (AGENTS.md Current Status / Last Session / Tech Stack "Database" row; a `docs/lessons.md` line that a console launch no longer prints UNCAUGHT-exception tracebacks; and that `Path.is_symlink()`/`is_junction()` read False on an unreadable folder on Python 3.13+), then `/retro`. Carried small follow-ups: PR-LOW-033 (a staged-publication spy test for the label read in `write_entry`); residue (t) older readers without a size cap.
- Loop config: executor=claude-p model="claude-opus-5-5" effort=high profile=default; peer=codex model="gpt-6-astra" effort=medium; architect=off; cadence=every-phase; caps=review:3,peer:5; gates=executor; cap-raise=executor; high-auto=on; peer-max=12; notify=action-only; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10; monitor-delivery=auto; verify=composer
- Last completed step: Planning complete (native Plan Mode → `/review-plan` 2026-10-01; full-plan pass, three-lens fan-out, deferral gate closed), then the cross-family plan `/peer-loop`.
  - Peer: codex `gpt-6-astra` medium, read-only, rounds 1–5.
  - Findings per round: 5 → 6 → 4 → 2 → 1, 18 in all, every one build-affecting and applied as an amendment.
  - The cap was reached: round 5's single LOW means the loop did not formally converge.
- **EXECUTOR stage-1 leg a1 (2026-10-01T07:26:06+10:00) — Phase 1 (Tasks 1.1–1.4) BUILT, ruff clean, mypy 52 files; pytest owed by the composer (verify=composer). Tasks stay 🟨 until the suite is green.**
  - **Built.**
    - Task 1.1: the new `audit.py`, with `AuditLog`, the DPAPI audit key (`AUDIT_KEY_DESCRIPTION`), the `AuditRow` schema (tokens, ids and codes only, `extra="forbid"`, a before-validator for `schema_version`), monthly row folders, the 7-year `month_prune_at` prune, the CSV export with its formula guard, and the D9 `reset` quarantine (`audit.unreadable-<stamp>-<8hex>`, never reused, an empty root removed if the new key fails).
    - Task 1.1, logging: `logging_setup` tripwire signatures added for `past_session`, `note_provenance` and `consent_confirmed_at`.
    - Task 1.2: `complete_session` now ALWAYS removes the session directory (the `remove_directory` flag is gone) and returns `CompletionFacts` (model and provider tokens from the session's own files).
    - Task 1.2, provenance: `saved-provenance.enc` (`SavedProvenance`, `write_saved_provenance` / `read_saved_provenance`) is used only when its digest names the completed note.
    - Task 1.2, sweep: `session_created_at` is now public, and `SweepResult.created_at` is set for `expired` / `orphan_gc`.
    - Task 1.3: `SessionController(audit=)`: `begin` runs before anything of the session exists and refuses Start with `AuditWriteError`; every later failure is recorded as `start_failed`. The old body moved to `_start_locked`.
    - Task 1.3, user id: taken from `set_clinic_user_resolver(window.clinic_user_id)`, registered by `app.main`, so the `SessionControllerLike` protocol is unchanged.
    - Task 1.3, startup: `app.main` prunes at startup and every 24 h, and records the sweep's results (`record_sweep_results`).
    - Task 1.4: `MainWindow._store_write_record` reports each durable `write.enc` transition AFTER it is stored. `_prepare_attempt`'s `WriteRefusal` branch records the fixed code (`record_write_refusal`).
  - **Consumers enumerated from the code.**
    - `complete_session` has 5 callers: `SessionController.complete`, `complete_without_note`, `complete_deleting_saved_note`, `complete_after_write` and `complete_recovered`. Each reads `created_at` before, and records after, the state transition. The delete-note paths record `completed_without_note`.
    - `complete_recovered` records only an id matching `SESSION_ID_PATTERN`.
    - `discard_session` has 4 callers:
      - Start's cleanup, recorded as `start_failed`;
      - `SessionController.discard`, where an already-DISCARDED early return records nothing;
      - `discard_recovered`;
      - `ui/recovery.py` `RecoveryScreen._discard` (new `audit=` parameter; nothing is recorded on a failed discard).
    - `sweep_sessions` has one caller, `app.run_sweep`.
  - **Seams left open.**
    - Task 2.1 wires `write_saved_provenance` into Save and writes `generated.enc`; the `generated_*` facts read `unknown` until then.
    - Task 2.3 owns pending-entry removal and `keep`; `past_session` is always `none` for now.
  - **Deferred to Phase 3:** DISPLAYING `AuditLog.failure_count`. The count and the `audit_update_failed detail_code=<stage>` log line exist now; the Past sessions tab's status label is Phase 3.
  - **Behaviour change the smoke will see:** a completed session's folder is now removed on every Complete path, not just after a write. Tests that asserted a surviving transcript or note were inverted (`test_integration_no_sockets.py`, `test_transcription.py`, `test_note_pipeline.py`, `test_session_store.py`).
  - **Tests.**
    - New: `test_audit.py`.
    - `TestAuditRecord` in `test_session_machine.py`, and `TestCompletionFacts` / `TestSavedProvenanceFile` in `test_session_store.py`.
    - The Task 1.4 cases in `test_ui_encounter.py` `TestDraftWrite`.
    - A Recovery discard case in `test_ui_screens.py`.
    - Wiring pins in `test_audit.py::TestAppWiring` and `test_hands_free.py`.
    - The DPAPI-backed cases are `skipif(win32)`.
    - No new dependency, env var or config file.
- **EXECUTOR stage-1 leg a2 (2026-10-01T07:32:33+10:00) — the composer's full run was 2 failed / 4952 passed.** Both failures were `test_integration_no_sockets.py::test_crash_kill_mid_recording_then_recover_transcribe_complete[False|True]`: line 1697 still asserted that the transcript survives `complete_session`, a site the leg-a1 sweep missed.
  - **Fix:** it now asserts `not session_dir.exists()`, and the import of `TRANSCRIPT_FILENAME` it no longer uses was removed.
  - **Sweep of the whole `desktop/tests` tree:**
    1. `assert \(?\w+ / (TRANSCRIPT_FILENAME|NOTE_FILENAME|SAVED_NOTE\w*|WRITE_RECORD_FILENAME|ENCOUNTER_FILENAME|AUDIO_FILENAME|"[a-z_-]+\.enc")\)?\.(is_file|exists)\(\)` found 13 hits.
       - `test_session_store.py`: 566 and 614, both on a refused Complete.
       - `test_session_machine.py`: 168, 1466–1467, 1667, 1689, 1742 and 1951. Each is before a Complete, on a refused Complete, or on a Discard fixture.
       - `test_transcription.py`: 573, 602, 1228 and 1248. None involves a Complete.
    2. `assert (session_dir|directory)\.(exists|is_dir)\(\)` found `test_session_machine.py:583` (a refused `discard_recovered`) and `test_session_store.py:632` (the rmtree-failure case, where `ignore_errors` leaves the folder by design).
    3. A multiline search for a Complete followed within 400 characters by `read_transcript` / `read_note` / `read_generated` / `read_write_record` / `listdir` / `iterdir` found 0 hits.
    4. The `complete_session(` and `.complete*(` call-site listing was read site by site: every post-Complete assertion now expects the file or folder to be gone.
  - **Result:** no other site to fix. ruff clean; mypy 52 files.
- **EXECUTOR stage-1 leg a3 (2026-10-01T07:52:20+10:00) — suite green (4954), so Tasks 1.1–1.4 are 🟩 and Overall Progress is 21% (4 of 19 tasks). `/review-loop` (cap 3) round 6 is done, and its fixes are applied.**
  - **Findings:** 0 CRIT / 0 HIGH / 2 MED / 12 LOW. The review used a two-lens subagent fan-out, verified in-session; 21 candidates, of which 3 were dropped, 5 merged and 1 downgraded. All 14 are Applied, and LOW-008 went into Task 5.2's residue list. Details are in the Findings Log.
  - **MED-001:** a DPAPI wrap error in the audit's key creation is now the authored error.
  - **MED-002:** `session_date` is the practitioner's LOCAL date, and the prune waits an extra day. This was my call as executor, not a practitioner decision; the reasoning is in the finding.
  - **Named targets:** all checked (the list is in the round header). C1's seam for Task 2.3 is clean, C3 holds as derived, and C5 holds with every audit call on the GUI thread.
  - **Not converged:** round 6 had MED findings, so round 7 follows once the composer's pytest confirms these fixes.
  - **Smoke P.4:** the Session screen's line will read "Start failed: AuditWriteError: the audit record could not be saved (…). Nothing was recorded." The type name comes from the shared `custody_refusal_text` convention; LOW-003 pins the full line.
  - **Before any practitioner run:** the key_unreadable / key_missing refusal text points at the Past sessions tab, which lands in Task 3.1 of this same run. Phase 1 alone has no in-app reset; round 6 dropped this as plan-decided.
  - **Files touched by round 6's fixes:**
    - source: `audit.py`, `session_store.py`, `ui/main_window.py`, `ui/recovery.py`, `app.py`;
    - tests: `test_audit.py`, `test_session_store.py`, `test_session_machine.py`, `test_ui_encounter.py`, `test_ui_screens.py`.
- **EXECUTOR stage-1 leg a4 (2026-10-01T07:58:38+10:00) — the composer's full run was 1 failed / 4967 passed.**
  - **The failure:** `test_session_store.py::test_read_and_complete_share_the_verification_core` spied on `_verified_note`. That became a wrapper when LOW-005 moved the core to `_verified_note_with_identity`.
  - **Not a regression:** both paths still verify through the one core, so the spy was re-pointed and there is no source change.
  - **Siblings:** no other test names the old symbol. ruff is clean; mypy 52 files.
- **EXECUTOR stage-1 leg a5 (2026-10-01T08:10:58+10:00) — `/review-loop` CONVERGED at round 7 (2 of 3 rounds: 6–7).**
  - **Round 6:** 0 CRIT / 0 HIGH / 2 MED / 12 LOW, all applied (see leg a3).
  - **Round 7:** 0 CRIT / 0 HIGH / 0 MED / 17 LOW, all applied, with `skew=mixed; action=triage-and-ship`. Of the 17, 7 ⚡ are docs, plan text or test strength around round 6's fixes (none a behavioural regression), 3 🔁 and 7 🆕.
  - **Round 7 in substance:**
    - every pre-send refusal is audited, including `mock_note`, `record_unreadable` and `already_written`;
    - a `start_failed` row stays open to the session's real end;
    - a creation time before 2026-01-01 is untrusted;
    - `begin`'s date-conversion errors, a row-walk OSError and a transiently held key are now authored refusals, and a held key never offers D9's reset;
    - one `_note_identity`;
    - one never-raising `session_store.audit_created_at`;
    - CSV columns `deletion.state` / `deletion.at` / `past_session.state` / `past_session.at`;
    - four tests tightened so they fail on the old code.
  - **Plan text amended in place (marked "amended round 7"):** D7 (the prune margin), D8 (the local `session_date`), Task 1.3 and P.4 (the screen line with `AuditWriteError:`), and Task 5.2's residue list (clock wrong at Start). These are records of already-applied behaviour, not new scope.
  - **Named targets all hold:** C1 seams for Task 2.3, C2, C3 derived, C5, every Complete / Discard / sweep path, D9, and the round-6 fixes.
  - **Next:** ruff clean, mypy 52 files; the composer's full desktop pytest confirms the final tree before the cross-family peer pass. `/peer-loop` was not run, as instructed.
- **EXECUTOR stage-1 leg a6 (2026-10-01T08:17:23+10:00) — the composer's full run was 1 failed / 4978 passed.**
  - **The failure:** `test_ui_screens.py::TestRecoveryScreen::test_discard_records_discarded_in_the_audit`.
  - **Cause:** the test's injection was too broad. It now injects after the list is built, around the Discard alone.
  - **No source change:** reasoning in round 7's LOW-014 note. ruff clean; mypy 52 files.
- **EXECUTOR stage-1 leg a7 (2026-10-01T08:27:08+10:00) — peer pass `stage-1.p1` round 9 (codex, slice B tests): both LOWs verified as test-harness and applied, round Closed.**
  - **PR-LOW-007:** the audit's failure log is proven free of exception text.
  - **PR-LOW-008:** each audit call is proven to follow its durable store, and a failed store is proven not to be audited.
  - **Tests only:** no source defect surfaced.
  - **Cap verdict:** accept (test-harness).
  - **Checks:** ruff clean; mypy 52 files; history check OK (9 + 9).
- **EXECUTOR stage-2 leg b1 (2026-10-01T09:02:47+10:00) — Phase 2 (Tasks 2.1–2.3) BUILT, ruff clean, mypy 53 files; pytest owed by the composer (verify=composer). Tasks stay 🟨 until the suite is green.**
  - **2.1:** `session_store.py` gains `generated.enc` (`GeneratedRecord`, `write_generated` / `read_generated`, AAD `generated:<id>`, 1 M-char / 8 MiB bounds, terse unreadable error) and `write_saved_note` (the provenance FIRST, naming the canonical bytes `write_note` stores; `note.enc` stays the commit boundary). `TranscriptScreen.save_note` uses it with `models.prose_model_ids`. `TranscriptScreen.keep_generated` writes the body under the held lease; the Note tab emits `generated_shown` at `begin_review` and again when the FIRST prose rendering lands before any edit (digest-matched). `MainWindow._on_generated_shown` connects them.
  - **2.2:** new `past_sessions.py` — the D1/D3 layout, `write_entry` (stage under a fresh key → full verification through the entry's own key read back from disk: the exact file set, the label, every plaintext's SHA-256, the existing readers → publish, replacing an earlier entry key-first, carrying `pending`), `commit`, `remove_pending_entry`, `reconcile_pending`, `clean_staging`, `list_entries` / `read_entry` / `delete_entry`, `sweep` / `sweep_past_sessions`, `KeepLabel` / `keep_label`, and the `config\past_sessions.json` loader/saver. The key custody is an injectable `wrap_key` / `unwrap_key` seam. The key description is pinned in `test_display_name.py`; `generated_text` is in `_PAYLOAD_SIGNATURES`.
  - **2.3:** `complete_session(..., keep=)` runs C1's order: verify → the entry published → `delete_session_key` (THE boundary) → `crypto.destroy()` → `commit` (failure → `commit_deferred`) → rmtree. Mock sessions write nothing (`not_kept_mock`). Every Complete path goes through one `SessionController._complete_locked`, mapping `ArchiveWriteError` to `PastSessionWriteError` (no chained OS text). Labels (D5) come from `MainWindow.keep_label_for` (bridge Start display → bridge re-verification → checkout's Verified result, each matched by session id) plus the new `ChromeBridge.live_display_name`. `app.sweep_with_archive` = `clean_staging` → `sweep_sessions(before_destroy=remove_pending_entry)` → `reconcile_pending`, at start-up and on every tick. Docstrings updated: `_CheckoutEncounter`, `ui/__init__.py`, `note.NoteDraft`.
  - **C1 — key consumers and destroyers, enumerated FROM THE CODE:**
    - `delete_session_key` is called only inside `complete_session`, `discard_session` and `sweep_sessions`. No other src site unlinks a session `key.dpapi` or rmtrees a session directory; every other `crypto.destroy()` is in-memory only.
    - `complete_session`'s 5 callers all go through `_complete_locked`: `complete`, `complete_without_note`, `complete_deleting_saved_note`, `complete_recovered`, `complete_after_write`.
    - `discard_session`'s 4 callers:
      - `discard()` calls `remove_pending_entry` in its first locked section, before the reservation.
      - `discard_recovered` calls it first.
      - `ui/recovery.py` `_discard` calls it first.
      - Start's own cleanup in `_start_locked` does not: the id is brand new, so no entry can exist.
    - `sweep_sessions` covers expired, dead-key `orphan_gc` and confirmed-absent `orphan_gc`. The hook runs for the first two only; its one caller is `app.run_sweep` via `sweep_with_archive`.
  - **Deviations and named residues (for review):**
    - The field is `generated_text`, not `text`, so it can serve as a tripwire signature.
    - An absent or unreadable `generated.enc` is not kept, and its `generated_*` facts read `unknown`.
    - When `keep_generated` fails, it unlinks the stale file. If that also fails, an earlier generation of the same session stays.
    - The mock rule is a casefolded `mock` prefix, applied to the transcript model, the generated provider and the note provider.
    - `remove_pending_entry` removes ANY entry for an id whose source key still exists.
    - `reconcile_pending` also removes keyless entries.
    - A failed removal refuses the Discard with the new `PastSessionCleanupError` ("Nothing was deleted - try again").
    - `write_saved_note`'s provenance lands before `write_note`'s own refusals. What is left then names no `note.enc` and reads `unknown` (D8).
  - **Tests added or retargeted:**
    - new `tests/test_past_sessions.py`;
    - `test_session_store.py` `TestWriteSavedNote` / `TestGeneratedFile`;
    - `test_session_machine.py` `TestPastSessionsThroughTheController` (windows_only; real session DPAPI, fake entry keys);
    - `test_ui_screens.py` `TestTranscriptPastSessions` / `TestGeneratedShown`, with the four `write_note` patches retargeted to `write_saved_note`;
    - `test_ui_encounter.py` `TestKeepLabel`.
  - **Smoke owed:** the Phase 2 archive is not visible until Phase 3's tab. A live Complete should leave `%LOCALAPPDATA%\ClinikoScribe\past_sessions\<id>\` with `key.dpapi`, `label.enc` and `transcript.enc` (plus the notes) and no `pending`.
- **EXECUTOR stage-2 leg b2 (2026-10-01T09:09:13+10:00) — the composer's full run was 1 failed / 5082 passed.**
  - **The failure:** `test_audit.py::TestNoContentByConstruction::test_every_model_field_is_a_completion_fact`. Its C3 pin of the facts left out of `AuditModels` did not know `commit_deferred`.
  - **Decision: `commit_deferred` is deliberately NOT an audit field.**
    - The row's `past_session` reads `archived` whether or not the marker came off, because the entry was published and fully verified before the key went.
    - A deferred marker is a transient that the next `reconcile_pending` clears. No row update follows that reconciliation, so a recorded deferral would go stale.
    - It feeds only Flow 3 step 4's status line (`COMPLETE_DEFERRED_LINE`).
    - D8's `past_session` states stay as planned.
  - **The fix:** the pin names `commit_deferred` with this reasoning in its docstring, and now also asserts `commit_deferred` is not an `AuditRow` field while `note_provenance` / `past_session` are. The derived shape of the guard is unchanged. The `CompletionFacts` docstring says the same. ruff clean; mypy 53 files.
- **EXECUTOR stage-2 leg b3 (2026-10-01T09:16:26+10:00) — the suite was green (5083), so Tasks 2.1–2.3 are 🟩 and Overall Progress is 37% (7 of 19). `/review-loop` (cap 3) round 11 is done, and its fixes are applied.**
  - **Round 11:** 1 MED + 2 LOW, all applied.
    - **MED-001:** the retention sweep now decrypts each committed label's date once per process. The in-memory cache is content-free and dropped on every write or removal.
    - **LOW-001:** a Complete no longer archives a session whose header id is not its directory name; the key is kept.
    - **LOW-002:** the regenerate-then-cancel pairing residue is now named.
  - **Named targets:** all checked, as listed in round 11's header.
  - **The four leg-b1 interpretations HOLD UP;** none needs a practitioner decision. The mock prefix is in fact required: a mock transcript records `model_name="MockSpeechProvider"`.
  - **For Task 5.2's named-residue list** (practitioner-visible):
    - LOW-002's pairing residue;
    - a failed `keep_generated` that could not unlink the stale file;
    - an unreadable `generated.enc` reads "Generated note not kept".
  - **Checks:** ruff clean; mypy 53 files; history check OK (11 + 11).
- **EXECUTOR stage-2 leg b4 (2026-10-01T09:24:55+10:00) — `/review-loop` CONVERGED at round 12 (2 of 3 rounds: 11–12).** Round 11's fixes were green at 5086.
  - **Round 12:** 0 CRIT/HIGH/MED + 2 LOW, both applied.
    - **LOW-001:** a docstring. `sweep_past_sessions` is a one-off; the periodic sweep uses the shared store's `sweep`.
    - **LOW-002:** carried into Task 3.2 (below).
  - **No regressions from round 11:** the date cache, the header-id refusal and the docstring all hold.
  - **Carried into Phase 3, for the Task 3.2 builder:**
    - (a) Wire the hourly retention sweep to `PastSessionStore.sweep` on the app's ONE shared store (the instance `app.main` builds), never `sweep_past_sessions` (round 12 LOW-001).
    - (b) The audit past-session updater Task 3.2 needs for `expired` / `deleted_early` must also record `past_session=archived` when `reconcile_pending` commits an entry after a crash between key deletion and the audit completion. `reconcile_pending` must then report the ids it committed (round 12 LOW-002). Until then this is a named residue for Task 5.2.
  - **Task 5.2's residue list gains (b), plus leg b3's three:** LOW-002's regenerate-then-cancel pairing, a failed `keep_generated` that could not unlink the stale file, and "Generated note not kept" for an unreadable `generated.enc`.
  - **Checks:** ruff clean; mypy 53 files; history check below. Since the green run, the only code change is a docstring in `past_sessions.py`.
- **EXECUTOR stage-2 legs b5–b6 (LEG 1 at 2026-10-01T09:33:00+10:00, LEG 2 at 2026-10-01T09:36:22+10:00) — codex round 13 (pass `stage-2.p1`, slice A source): both LOWs verified as production-behavioral, then Fix-now applied.**
  - **PR-LOW-010:** links are never followed anywhere in `past_sessions.py`. A link is refused in `_remove_key_first`, skipped by `_entry_dirs` and `clean_staging`, never committed through, and treated as not ours by `remove_pending_entry`. A linked `.staging` stops staging entirely. Refusals are left in place and logged only as content-free detail codes.
  - **PR-LOW-011:** the two settings fields are strict.
  - **Tests:** in `test_past_sessions.py`. Real junctions run on Windows; symlink cases skip where the host lacks the privilege.
  - **For H3 (`/security-review`), recorded rather than fixed:** `session_store.sweep_sessions` and `discard_session` share the same pre-existing link-following shape under the SESSIONS root (`is_dir()`, then `delete_session_key` through a linked child).
  - **Checks:** ruff clean; mypy 53 files.
- **EXECUTOR stage-2 leg b7 (LEG 1 at 2026-10-01T09:44:35+10:00, LEG 2 at 2026-10-01T10:00:15+10:00) — codex round 14 (slice B tests, and confirmation of round 13): both LOWs verified as test-harness, then Fix-now applied as tests only.**
  - **PR-LOW-012:** the real `write_saved_note` runs through the window's route. Failures are injected at the provenance write and at the note write, then followed by a retry or Cancel review; disk, both flags and the lease agree.
  - **PR-LOW-013:** the deferred-commit test is parametrised over the five `_complete_locked` callers, enumerated from the code.
  - **No source defect surfaced.** Round 13's fixes were confirmed closed by the peer.
  - **Checks:** ruff clean; mypy 53 files.
- **EXECUTOR stage-3 leg c1 (2026-10-01T12:43:39+10:00) — Phase 3 (Tasks 3.1–3.3) BUILT, ruff clean, mypy 55 files; pytest owed by the composer (verify=composer). Tasks stay 🟨 until the suite is green.**
  - **3.1 — the Past sessions tab.** New Qt-free `ui/past_sessions_view.py` (every line, the hide-names mask, the retention options and warning, the write-outcome line from the audit row, `retention_sweep`) and `ui/past_sessions.py` (`PastSessionsScreen`). Placed after Note (`MainWindow.past_sessions_screen`; 9 tabs). Opening the tab re-lists (`label.enc` only, one unwrap each) and re-checks the audit key; LEAVING the tab drops the opened entry's text from every panel (`close_entry`) — my call, so clinical text is held only while the tab is in front. Selecting a row opens it: generated note beside saved note, the write-outcome line, "Copy saved note" (through `ui.note._place_note_text` only, gated on `COPY_TO_CLINIKO_ENABLED` and no blocking warning), "Show transcript". Every panel is `NoTextInteraction`. Delete now is two clicks within 10 s on the same entry (selection change or the 1 s tick disarms), key first, then `audit.record_past_session(id, "deleted_early", created_at=<label start>)`. Lowering retention asks (`QMessageBox` in production, injected `confirm` in tests), saves, then sweeps; raising saves only; a declined lowering reverts the combo and writes nothing. Export CSV = `AuditLog.export_csv` via an injected save dialog (`choose_csv_path`), with the not-encrypted line beside the button and in the outcome. D9's "Start a new audit record" button shows only while `audit.key_unreadable()`; it confirms, then `audit.reset()`. Persistent status line: no archive / settings unreadable / audit key unreadable / N audit updates failed (re-read on a 1 s tick from the in-memory count — no disk).
  - **3.2 — the retention sweep.** `PastSessionsScreen.run_retention_sweep` (never raises): reload the settings (unreadable → nothing deleted, status says so), then `past_sessions_view.retention_sweep` = the ONE shared store's `sweep` + `record_past_session(id, "expired")` for each; deleted rows leave the list IN MEMORY (no re-list, so a tick decrypts only what the sweep needs; "never" decrypts nothing). `app.main` runs it after `reconstruct_reminders` and then via `retention_sweep_if_due` (≥ 1 h since the last, on the 15-min timer; `_RETENTION_SWEEP_INTERVAL_S`). Binding seams honoured: `reconcile_pending` now returns the committed ids (was an int) and `sweep_with_archive(..., audit=)` records each as `archived` (round 12 LOW-002); `clean_staging` / `reconcile_pending` still run every start-up and tick whatever the setting.
  - **Audit additions (required by the seams/Task 3.1):** `AuditLog.record_past_session(id, "archived"|"deleted_early"|"expired")` with `_PAST_SESSION_FROM` (archived only over `none`; deletions over `none`/`archived`; `not_kept_mock` and an earlier deletion never rewritten; event codes `past_session_<state>`), and `AuditLog.row_for(id)` (one row decrypted, None for no store/no row/newer/unreadable, `AuditUnavailable` for a key problem; creates nothing).
  - **3.3:** `models.INTENDED_USE_LINE` ("Documentation aid, not clinical decision support. You review and finalise every note in Cliniko.") heads the Status tab (`StatusPanel.intended_use_label`) and the Past sessions tab.
  - **Every new on-screen string** is a constant in `ui/past_sessions_view.py` (list: "Patient hidden", "Name not available", "Desktop recording (no Cliniko note)", the unreadable line; entry: "Generated note (what the app first produced)", "Saved note", "Generated note not kept", "No saved note"; retention combo "Until I delete them" / 1 day / 7 / 30 / 90 days / 1 year / 7 years, the pinned warning, the confirm/changed/kept lines; Delete now / "Confirm delete" and its message; the write-outcome lines; the export, reset and status lines). Rows read `YYYY-MM-DD HH:MM - <who>` in local time (locale-free on purpose), newest first, unreadable last.
  - **MainWindow test sites (8, enumerated from the code):** `test_ui_screens._main_window` (fake-keyed `PastSessionStore` under tmp_path), `test_hands_free` child, `test_integration_no_sockets` ×3 (the start-up mirror also runs `sweep_with_archive(..., audit=)`, the tab's retention sweep and a refresh), `test_system_pause`, `test_ui_pause_and_unreviewed`, `test_status_and_app`. Tab pin → 9.
  - **Tests added:** `test_ui_screens.py::TestPastSessionsTab` (19 cases: pinned texts, no decrypt at construction, list order, Hide names saved and masking, side-by-side entry + write line, placeholders, write-outcome lines, Copy through the fake clipboard with the three formats, two-click Delete + `deleted_early`, arming expiry, lowering asks then sweeps + `expired`, declined lowering, raising, "never" no decrypt, the shared store's date cache, unreadable settings, export via the injected dialog, D9 reset, audit failure count, no-archive window, tab open/leave in MainWindow); `test_audit.py` (past-session transitions, `row_for`, main's start-up order with reconciled `archived`, the hourly cadence by injected clock); `test_past_sessions.py` (reconcile ids; `sweep_with_archive` records `archived`). Retargeted: every `reconcile_pending(...) == n` to the id list; the two fakes return `[]`.
  - **Named residues for Task 5.2:** Hide names masks the LABEL only — a name spoken in the transcript or written in a note is not masked; a past-session event on a row the audit no longer holds (pruned, or quarantined by a D9 reset) creates a `pre_audit` row (dated by the label's start for Delete now, by now for expiry/reconcile); a reconciled commit records `archived` but leaves `deletion` `pending` (the Complete's own outcome is not guessed — a later `orphan_gc` of a leftover directory records itself); Hide names saved while the settings file is unreadable writes "never" with it (the same effective behaviour).
- **EXECUTOR stage-3 leg c2 (2026-10-01T12:50:48+10:00) — the composer's full run was 6 failed / 5132 passed / 4 skipped; one cause, fixed; ruff clean, mypy 55 files.**
  - **The failure:** all six in `test_ui_encounter.py::TestDraftWrite`. Its `_AuditRecorder` is handed to `MainWindow`, which now builds the Past sessions tab with it, and the tab read `failure_count` the recorder lacked.
  - **Fix, as a typed surface rather than a weaker tab:** `ui/past_sessions_view.PastSessionsAudit` — a `runtime_checkable` Protocol of EXACTLY what the tab and its sweep use (`failure_count`, `key_unreadable`, `reset`, `row_for`, `record_past_session`, `export_csv`). The tab and `retention_sweep` depend on it, and mypy checks `AuditLog` against it where `MainWindow` passes its log. `_AuditRecorder` implements it (inert; a reset or export fails the test), pinned by `test_the_audit_recorder_implements_the_past_sessions_surface`; `_FakePastAudit` and a real `AuditLog` are pinned the same way. Every other audit double was checked: the `RecoveryScreen` `Recorder` (no tab), `test_audit.py`'s two `FakeAudit`s (their `FakeWindow` builds no tab), `_InertAudit` in `test_hands_free.py` (its window is a pre-built `_main_window` without an audit) — `_InertAudit` gained `record_past_session` anyway, as app.main's sweep surface.
  - **Hide names while the settings file is unreadable — REVERSED from leg c1:** the toggle is now refused (box disabled; a click that still arrives is undone with "Hide names cannot be changed while the settings file cannot be read. Choose a retention setting first - that replaces the file."), and the file is left byte-for-byte. Reasoning: saving it wrote a retention the practitioner never chose over a file that may be recoverable; the plan's rule is that an unreadable file deletes nothing and "the tab says so", and D13 persists Hide names in that file — so the only write that may replace it is an explicit retention choice, which the status line now names ("…nothing is deleted by age and Hide names cannot be changed. Choose a retention setting to replace the file."). After that choice Hide names works again (tested). Leg c1's fourth residue is withdrawn.
- **EXECUTOR stage-3 leg c3 (2026-10-01T13:14:03+10:00) — suite green at 5140; Tasks 3.1–3.3 marked 🟩 (Overall 53%); `/review-loop` round 16 run and fixed (0 CRIT / 0 HIGH / 2 MED / 19 LOW, all applied); ruff clean, mypy 55 files; pytest owed by the composer.**
  - **Round 16 summary (Findings Log "Round 16"):**
    - MED-001: the Hide-names state model. An unsaved choice survives every reload. An unreadable file HIDES names (and its explicit replacement keeps them hidden). Opening the tab and the hourly sweep re-read the file.
    - MED-002: a sweep that cannot finish says so (`RetentionSweepReport`, `SWEEP_PROBLEM_LINE`).
    - The LOWs:
      - C3: the export outcome has no file name;
      - Copy reasons per cause;
      - an unlistable archive is never "none kept";
      - stale lines cleared;
      - `expired` `pre_audit` rows dated by completion;
      - `row_for` refuses a duplicate;
      - pre-1970 dates;
      - names dropped on leaving the tab (`on_left`);
      - Export disabled under an unreadable key;
      - named-button confirmations (`confirm(text, action)`);
      - next steps on unreadable entries;
      - the one unexpected-error line;
      - group-title constants and `models.__all__`;
      - the save dialog starts in Documents;
      - signal-wiring and failure-path tests;
      - `app.PeriodicSweep` (the tick, tested);
      - `MainWindow(past_sessions_confirm=, past_sessions_save_path=)`;
      - the Protocol docstring.
  - **New strings:**
    - `RETENTION_CONFIRM_ACTION` "Delete older sessions", `AUDIT_RESET_CONFIRM_ACTION` "Start a new audit record", `CONFIRM_CANCEL` "Keep things as they are";
    - `COPY_TURNED_OFF` / `COPY_NOTHING_OPEN` / `COPY_NO_SAVED_NOTE` / `COPY_UNRESOLVED` (replace `COPY_UNAVAILABLE`);
    - `ENTRY_UNREADABLE_ROW`, `LIST_UNREADABLE`, `SWEEP_PROBLEM_LINE`, `HIDE_NAMES_NOT_SAVED`;
    - the three group titles.
  - **Named residues for Task 5.2 (updated):**
    - Hide names masks the LABEL only — a name in transcript or note text is shown as kept;
    - an event on a pruned or D9-quarantined row creates a `pre_audit` row (dated by start for Delete now, by completion for expiry, by now for a reconciled `archived` — reconcile decrypts nothing);
    - a reconciled commit records `archived` but leaves `deletion` `pending`;
    - an unsaved Hide-names choice lasts until Clinic Scribe closes;
    - the retention sweep trusts the wall clock: a clock jumped forward can delete entries early (as the 24 h session sweep can).
  - **For Task 5.2 / C9 (design-system doc, not code):** add the Past sessions tab to the tab list. Note that its two confirmations are the app's sanctioned secondary windows (named buttons, the safe one default) beside "No secondary windows". Add Past sessions' Delete now to the destructive-actions paragraph (the two-click pattern).
  - **Composer:** run the full desktop suite. The new and changed tests are in:
    - `test_ui_screens.py::TestPastSessionsTab`, plus `_main_window`'s dialog fakes;
    - `test_audit.py` (`row_for` duplicate, `PeriodicSweep`);
    - `test_past_sessions.py` (`sweep_report`, unlistable archive).
  - **Then** round 17 confirms round 16's fixes and looks for what it missed (cap 18).
- **EXECUTOR stage-3 leg c4 (2026-10-01T13:20:49+10:00) — the composer's run after round 16: 2 failed / 5153 passed / 4 skipped. The two failures had one cause; fixed in the source and the tests; ruff clean, mypy 55 files.**
  - **The split:** the screen showed `str(exc)` for a `PastSessionError`, which is the store's authored sentence, while the tests passed the raw CODE through the same view helper. Neither side owned the mapping. Both store tables also fell back to echoing an unknown code (`_REASONS.get(reason, reason)`).
  - **Decision — the plain sentence on screen is right; the mapping lives in ONE Qt-free place:** `past_sessions_view.failure_reason(exc)`.
    - A known `PastSessionError`, `AuditUnavailable` or `AuditResetError` code reads its store's authored sentence, from the now-public tables `past_sessions.PAST_SESSION_REASONS`, `audit.AUDIT_REASONS` and `audit.AUDIT_RESET_REASONS`.
    - Anything else, an unknown code included, reads `CUSTODY_UNEXPECTED_REASON`. A raw code or exception text is never shown (C3).
    - `AuditResetError` now carries codes (`set_aside_failed` / `no_free_name` / `key_failed`; the same sentences as before).
    - `delete_failed_line` / `open_failed_line` / `reset_failed_line` / `export_failed_line` now take the EXCEPTION. The export maps `StoreWriteError` and `OSError` to "the file could not be written".
    - Each screen handler is now one `except Exception as exc` with no `str(exc)`.
  - **Swept:** the tab's other lines (the write outcome, the settings, the sweep, the list, Copy, the status) were already fixed constants or read row data, never exception text.
  - **Tests:**
    - The two failures, the export test and the reset test now pin the LITERAL sentences.
    - New `test_every_refusal_line_is_mapped_in_one_place_and_never_echoes` covers every code in all three tables, an unknown code per type, and foreign exceptions carrying a path; no line echoes either.
- **EXECUTOR stage-3 leg c5 (2026-10-01T13:26:40+10:00) — the composer's run after leg c4: 1 failed / 5155 passed / 4 skipped; a test-harness gap, fixed (tests only).** `test_export_goes_through_the_injected_dialog` popped a fixed list of dialog answers, sized before leg c4 added the `OSError` case. The injected dialog is now non-consuming: it returns `answer[0]` on every call and counts its calls. Every assertion is kept, plus one that the cancelled first call asked exactly once. Ruff clean, mypy 55 files.
- **EXECUTOR stage-3 leg c6 (2026-10-01T13:29:29+10:00) — the suite green at 5156; `/review-loop` round 17 (round 2 of cap 3) run and fixed: 0 CRIT / 0 HIGH / 0 MED / 2 LOW. That is CONVERGED by the loop's rule (0 CRIT/HIGH/MED survivors); round 18 is not needed.**
  - **Regression check of round 16 and legs c4–c5:** clean (Findings Log "Round 17").
  - **LOW-020:** an entry whose date this account cannot read is kept whatever the retention setting; the status line now says so, with Delete now as the way out (`RetentionSweepReport.undated`, `undated_line`).
  - **LOW-021:** a key lost mid-visit now shows D9's reset at once after a failed export or write line (`_recheck_audit_key`).
  - **Loop summary, rounds 16–17:** 2 MED + 21 LOW, all applied; legs c4 (the one code-to-sentence mapping) and c5 (a test-harness fix) between them.
  - **Named residues for Task 5.2 (now complete):**
    - Hide names masks the label only;
    - `pre_audit` rows on pruned or quarantined rows;
    - a reconciled `archived` leaves `deletion` `pending` and is dated now;
    - an unsaved Hide-names choice lasts the run;
    - a wall clock jumped forward can expire entries early;
    - an undated entry is never deleted by age (said on the tab).
  - **The design-system items for Task 5.2 / C9** are in leg c3's bullet.
  - **Composer:** run the full desktop suite; the changed tests are in `test_ui_screens.py` and `test_past_sessions.py`.
- **EXECUTOR stage-3 leg c7 (LEG 1 at 2026-10-01T13:37:50+10:00, LEG 2 at 2026-10-01T13:39:03+10:00) — codex round 18 (pass `stage-3.p1`, slice A source): PR-LOW-014 verified as production-behavioral, then Fix-now applied.**
  - **The class:** the two sweep status lines were sticky flags. They are now derived from the latest report while the retention setting it ran under is still current (`_current_sweep`). Choosing "never", raising, a hand-edit or an unreadable file drops them with no sweep.
  - **Wording:** the retry no longer promises an hour — "at a later hourly check while it is running".
  - **Checked as not stale:** the unreadable-settings line, the audit-key line, the failure count, and the partial-sweep line after a later finished sweep.
  - **Checks:** ruff clean, mypy 55 files; the composer runs `tests/test_ui_screens.py`.
- **EXECUTOR stage-3 leg c8 (LEG 1 at 2026-10-01T13:44:08+10:00, LEG 2 at 2026-10-01T13:46:58+10:00) — codex round 19 (slice B tests, and confirmation of round 18): four LOWs verified, then Fix-now applied.**
  - **PR-LOW-015:** round 18's class was closed on the derived lines but not on the VISIBLE label along the reload routes. It is now closed structurally: `_reload_settings` always repaints the status, and the enumerated writer list is complete.
  - **PR-LOW-016:** the click-time Delete deadline is tested.
  - **PR-LOW-017:** a failing audit update through Delete now and expiry is tested, as are repeated `deleted_early` / `expired` (exact event counts and timestamps).
  - **PR-LOW-018:** a `caplog` sentinel test covers the failure handlers and two failing sweeps.
  - **Checks:** ruff clean, mypy 55 files; the composer runs `tests/test_ui_screens.py` and `tests/test_audit.py`.
- **EXECUTOR stage-3 leg c9 (LEG 1 at 2026-10-01T13:50:38+10:00, LEG 2 at 2026-10-01T13:51:07+10:00) — codex round 20 (confirmation of round 19): PR-LOW-019 verified as test-harness, then applied as tests only.**
  - **Production checked first:** expiry and Delete now both clear an OPEN entry through `_drop` → `close_entry` (every panel, the heading, the write line, the selection). The audit update cannot raise past it (`update` catches everything, C2). No source change.
  - **The audit-failure test** now opens each entry, transcript shown, before its deletion or expiry, and asserts that nothing of it remains.
  - **Checks:** ruff clean, mypy 55 files; the composer runs `tests/test_ui_screens.py`.
- **EXECUTOR stage-4 leg d1 (2026-10-01T14:10:32+10:00) — Phase 4 (Tasks 4.1–4.2) BUILT, ruff clean, mypy 56 files; pytest owed by the composer (verify=composer). Tasks stay 🟨 until the suite is green.**
  - **4.1 — new `exclusions.py`.**
    - `WindowsLayer` Protocol (`environ`, `realpath`, `drive_type`, `file_attributes`, `set_file_attributes`, `wer_exclusions`) and `Win32WindowsLayer` (`os.environ`, `os.path.realpath`, ONE typed `GetDriveTypeW`, `os.stat(...).st_file_attributes`, ONE typed `SetFileAttributesW`, a read-only `winreg` read guarded by `sys.platform` as `status.py` does). No new dependency, env var, network use or `noqa: TID251`.
    - `mark_not_indexed(layer, root)`: sets NOT_CONTENT_INDEXED on `%LOCALAPPDATA%\ClinikoScribe` and EVERY FOLDER beneath it that lacks it (existing settable bits kept), best effort, returns the failure count. **My call:** folders only, not files — new files take the attribute from their folder at creation, and marking files would fail every start on the held-open `app.lock` (no sharing). Links/junctions (root included) are never followed or marked.
    - `check_location`: realpath of the root; warns inside `%OneDrive%` / `%OneDriveCommercial%` / `%OneDriveConsumer%`, on a `\\` path (incl. `\\?\UNC\`) or a `DRIVE_REMOTE` letter, and inside `%APPDATA%`. Case-insensitive, prefix-safe containment (`OneDriveBackup` is not `OneDrive`). **Interpretation of D10's "compared with `%USERPROFILE%\AppData\Local`":** D10 names only three warning causes, so a folder outside AppData\Local for any OTHER reason is LOGGED (`exclusions detail_code=location_unusual`), never shown.
    - `check_wer(layer, executable)`: a missing / non-1 value of any of the three → one line; an unreadable key → "could not check"; the running interpreter's basename (casefolded) not in the three → D10's line, verbatim for `python.exe`. A name that is not a plain file name shows as "this program".
    - `startup_exclusions(layer, *, executable, logger, root=None) -> tuple[str, ...]`: mark → location → WER; never raises, never refuses start-up (an unexpected failure reads "could not check"); each warning logged by its CODE only (`exclusions detail_code=<code>`, then `exclusions count=N state=checked`) — no path, no line text.
    - `install_exception_hooks(logger) -> restore`: `sys.excepthook`, `threading.excepthook`, `sys.unraisablehook` → `ExceptionHook` objects logging ONLY `uncaught_exception error_code=<type name> detail_code=main|thread|unraisable` (no message, traceback, `exc_info` or locals; a type name that is not a plain identifier logs `unknown`; a thread's `SystemExit` is silent as Python's own hook is). The replaced hooks are NOT chained (the defaults print the message and traceback to stderr); each hook keeps `previous`, `restore()` puts back only slots still holding ours, `remove_exception_hooks()` unwinds stacked ones. A hook never raises. **What existed before:** nothing — no module set any hook, `faulthandler` is not enabled, and no `logger.exception` / `exc_info=` / `print_exc` exists in `src` (grep); PySide6 sends an exception in a Qt slot to `sys.excepthook`, so slots are covered too.
    - **Wiring:** `app.main` installs the hooks right after `setup_logging` (kept for the process lifetime — restoring on the way out would hand a start-up failure's traceback to the default hook), and runs `startup_exclusions(Win32WindowsLayer(), executable=sys.executable, logger=logger)` after the start-up sweep, just BEFORE `MainWindow` is built. `MainWindow(exclusion_warnings=())` passes the lines to `StatusPanel` (new `exclusions_label`, under the intended-use line, hidden when empty) and to `PastSessionsScreen` (appended to the derived `status_lines()`, so every repaint carries them — no sticky flag). The window makes NO Windows call for them.
    - **C6:** a conftest autouse fixture (every test, so every `MainWindow` and `app.main` test) patches `Win32WindowsLayer.__init__` to raise "a test reached the real Win32WindowsLayer (C6)", and FAILS at teardown any test that left an `ExceptionHook` installed (after unwinding it). `app.main` test sites, enumerated from the code (5): `test_audit.py` ×2, `test_hands_free.py` ×1 (all three now patch `install_exception_hooks`, `Win32WindowsLayer`, `startup_exclusions`) and `test_status_and_app.py` ×2 (they return before the checks, so only `install_exception_hooks`). `MainWindow` sites (8: `test_ui_screens._main_window`, `test_hands_free` child, `test_integration_no_sockets` ×3, `test_system_pause`, `test_ui_pause_and_unreviewed`, `test_status_and_app`) need no layer — the window never reaches one. The no-sockets child mirror now installs the hooks and runs `startup_exclusions` through an inline fake layer over its temp root before the window, under the socket check.
  - **4.2 — `scripts/register-native-host.py`.** New `register_wer(winreg)` (HKCU `CreateKey` → three `SetValueEx` REG_DWORD 1 → read back each; returns the names that did not read back as DWORD 1) and `unregister_wer(winreg)` (deletes only the three values; the key and any other value stay). `register()` adds a `wer :` line, an ERROR on stderr naming any failed value, and `verified : FAIL` / exit 1 on any; `unregister()` lists the removed values. Names and key are imported from `scribe_desktop.exclusions` (single source). Module docstring, `--help` text and a printed `note` all say to run it from a normal terminal and that an agent shell's run or check proves nothing (lessons.md:13-20). Not run by me (never from an agent shell).
  - **Tests (new):** `test_exclusions.py` (fake layer only: the sentinel itself; location ×11 incl. junction-resolved OneDrive, prefix sibling, UNC / `\\?\UNC\` / `//`, remote letter, extended-length local, roaming, redirected roaming on a share, unusual-logged-only; WER ×12 incl. D10's verbatim line, case, full paths, unreadable registry, non-plain names; marking ×6 incl. folders-only, attribute preservation, already-marked, refusal counted, unreadable counted, real junctions (Windows) never followed; `startup_exclusions` ×5 incl. order, code-only logging, a layer broken everywhere, a broken logger; hooks ×9 incl. a real thread, a real unraisable `__del__`, previous never called, restore, never raises; on-screen ×3; the `app.main` order). `test_register_native_host.py` (importlib-loaded, fake `winreg`: write + read-back, four read-back failures, unregister only-its-three, no key, HKCU-only, `register()` OK / FAIL-loudly, `unregister()`, docs + `--help`).
  - **Warning strings (all new, all in `exclusions.py`; for the batched smoke):**
    - "Clinic Scribe's data folder is inside OneDrive, which can copy it off this computer."
    - "Clinic Scribe's data folder is on a network drive, so its files are kept off this computer."
    - "Clinic Scribe's data folder is in the roaming part of your Windows profile, which Windows can copy to other computers."
    - "Clinic Scribe could not check where its data folder is kept."
    - "Crash reports are not excluded for Clinic Scribe — run scripts/register-native-host.py again from a normal terminal."
    - "Clinic Scribe could not check whether crash reports are excluded."
    - "Crash reports are not excluded for this launch (python.exe) — start the app with scribe-app.exe." (D10 verbatim)
    - "Some of Clinic Scribe's folders could not be marked to stay out of Windows Search."
  - **For Task 5.2 (C9 docs; NOT written here):** the threat model / data-flow / retention wording must say — the three HKCU WER values and the `pythonw.exe` breadth (every pythonw process of this user); exclusions are per-user only (admin-only ones — backup/snapshot, HKLM WER — are Phase 7); the location check is read-only and warns, never refuses; NOT_CONTENT_INDEXED is best effort, folders only, so a FILE written before its folder was first marked keeps its old attribute until rewritten (a past-sessions entry or an untouched audit row from before this phase), and links/junctions are skipped; the exception hooks log the type name only and Python's default hooks are not called (so a console launch no longer prints tracebacks — a debugging cost, accepted for C3); native crashes are not Python exceptions — WER is the control there, and the console `python.exe` launch is uncovered by design (shown); `faulthandler` is off; Chrome crash dumps stay a residue; and the agent-shell rule for verifying any of it.
  - **Scope-expansion candidate (LOW, not built — outside this task's files):** `scribe-host.exe` (`native_host.py`) keeps Python's DEFAULT hooks, so an uncaught exception there prints its message and traceback to the host's stderr (which Chrome may log); the relay carries display strings (patient names). Recommended: Include in plan (H3 or a one-line `install_exception_hooks` in the host's `main`) — it is the same control on the second process, not new design.
  - **Smoke (P.3) — what the practitioner should check, from a normal terminal:** (1) re-run `scripts\register-native-host.py`: `wer :` line and `verified : OK`; `reg query "HKCU\Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"` shows the three DWORD 1 values; (2) launch with `scribe-app.exe`: the Status tab and the Past sessions status line show NO exclusion line; (3) launch with `.venv\Scripts\python.exe -m scribe_desktop.app`: the uncovered-launch line shows on both; (4) `--unregister` then launch with `scribe-app.exe`: the "Crash reports are not excluded for Clinic Scribe" line shows (re-register afterwards); (5) `attrib "%LOCALAPPDATA%\ClinikoScribe"` and a folder under it show `I` (not content indexed), and a file the app writes after this start (a new session's `key.dpapi`) shows `I` too — this confirms the folder-inheritance assumption; (6) the console launch's terminal shows no traceback text if something fails (only `uncaught_exception error_code=…` lines in the log).
- **EXECUTOR stage-4 leg d2 (2026-10-01T14:21:14+10:00) — the suite was green (5236 passed, 4 skipped), so Tasks 4.1–4.2 are 🟩 and Overall Progress is 63% (12 of 19). `/review-loop` (cap 3) round 21 is done (0 CRIT / 0 HIGH / 1 MED / 3 LOW, all applied); ruff clean, mypy 56 files; pytest owed by the composer.**
  - **MED-001 (the open item from leg d1, confirmed):** `scribe-host.exe` now installs the same hooks right after `setup_logging`. The stdout contract was checked first: the hooks write only through the logger, whose handlers are a file and stderr, never stdout. Only two production entry points exist (`app:main`, `native_host:main`), and both now install them.
  - **LOW-001:** the main hook drops `sys.last_*`, which `PyErr_Print` sets before calling it, so a Qt slot's exception no longer keeps its frames (and their locals) alive.
  - **LOW-002:** the WER line now ends "…again from a normal terminal, then restart Clinic Scribe." The lines are a start-up snapshot; this replaces leg d1's smoke-list wording for that line.
  - **LOW-003:** a test proves a console launch shows the type-name line on stderr (the composer's d1 note) and neither the message nor a traceback.
  - **Task 5.2 list, additions to leg d1's:**
    - AGENTS.md's persistent-terminal launch "keeps console output", but tracebacks are no longer printed. A failure shows one `uncaught_exception error_code=<type>` line on the console and in `scribe-app.log` / `scribe-host.log`. lessons.md should say so for debugging.
    - Both processes carry the hooks.
    - An inherited `PYTHONFAULTHANDLER` / `-X faulthandler` would dump file / line / function names only (no values).
    - `sys.last_*` is dropped.
  - **Next:** the composer runs `tests/test_exclusions.py`, `tests/test_native_host.py`, then the full desktop suite. Round 22 confirms round 21's fixes and looks for what it missed (cap 23).
- **EXECUTOR stage-4 leg d3 (2026-10-01T14:27:25+10:00) — `/review-loop` CONVERGED at round 22 (2 of 3 rounds: 21–22).** Round 21: 1 MED + 3 LOW, all applied, green at 5239 passed / 4 skipped. Round 22: no findings. It confirmed the host's hooks never reach stdout on any path (file / stderr only; a pythonw host with no handler drops the record; `test_no_stdout_handler` pins it), that the `sys.last_*` drop cannot raise out of the hook, and that the host tests install nothing process-wide. No code change since the green run. `/peer-loop` not run, as instructed. Phase 4 has no open gate. The Task 5.2 items are in legs d1 and d2; the P.3 smoke list is in leg d1, with leg d2's WER wording.
- **EXECUTOR stage-4 leg d4 (LEG 1 + LEG 2 at 2026-10-01T14:35:53+10:00) — codex round 23 (pass `stage-4.p1`): both findings verified, then Fix-now applied.** Details are in round 23's tuples and decisions.
  - **PR-MED-020 — the wider class:** any handler write failure printed the exception being handled, with its whole chain, to stderr. That covers every hook AND every ordinary `log_event` inside an `except`. It is closed structurally in `logging_setup`: every handler it builds reports one fixed type line, and a scan pins it as the only handler installer.
  - **PR-LOW-021:** the older native-host `main()` test no longer reads the real HKCU registration (tests only).
  - **Task 5.2 additions:**
    - The threat model's logging section gains the control: a log write failure shows `--- Logging error (<type>) ---` on stderr and nothing else.
    - The `logging.lastResort` residue (third-party loggers with no handler, WARNING+).
  - **Checks:** ruff clean, mypy 56 files. The composer runs `tests/test_logging_setup.py`, `tests/test_exclusions.py` and `tests/test_native_host.py`, then the full desktop suite (`logging_setup` changed).
- **EXECUTOR stage-5 leg e1 (2026-10-01T15:02:13+10:00) — Phase 5 (Tasks 5.1–5.2) BUILT, ruff clean, mypy 56 files; pytest owed by the composer (verify=composer: test pins changed). Both tasks stay 🟨 until the suite is green.**
  - **5.1 — `docs/practice/` (new):** `README.md` (index, versions, the research table — VIC/NSW/ACT Acts, the five other states and territories on the APPs with "no separate Act identified in this research", Ahpra, AJGP, Heidi — and four OPEN QUESTIONS for the independent review), `patient-information-and-consent.md` (`patient-info-v1`: patient sheet, practitioner script + what to record where, optional written form), `privacy-information.md`, `downtime-procedure.md`, `clinician-review-guide.md`. Every file carries the C10 banner ("needs independent privacy/legal/clinical-safety review before use with other practitioners") and points at the README's state table; plain English, no file names or code identifiers; each says the app never ticks or fills Cliniko's consent field. No citation beyond the plan's External Findings; where the research runs out the docs say so or leave a `[Practice: …]` / `[Reviewer: …]` placeholder (privacy contact, regulator, complaints route, the practice's retention choice).
  - **5.2 — the C9 class, statement by statement (by meaning, not the stale line numbers):**
    - `PLAN.md`: Flow step 10 ("the draft in Cliniko is the only copy"), `ConsentAttestation` ("a durable audit record is Phase 6"), the Phase 4 delivery note ("stays Phase 6"), a new Phase 6 delivery note under its six bullets (deletion bullet marked REVERSED by practitioner decision), the test-plan "Successful write-back triggers cryptographic deletion" (as-built note).
    - `retention-schedule.md`: title/intro paragraph; rows — log content (hooks, `--- Logging error`), registration artifacts (+ the three WER values, agent-shell rule), audio (never archived; removed on every Complete), key (all five Complete paths, C1 order, Discard's entry removal), transcript, note, in-memory (the tab's opened entry), clipboard (+ Copy saved note), API responses (name → label exception), encounter (audit row), `write.enc` (audit row, digests die), Chrome link (name read at Complete), crash dumps; NEW rows — `generated.enc`, `saved-provenance.enc`, Past-sessions entry, marker + staging, settings file, audit record, set-aside audit stores, exported CSV, indexing attribute; NEW rules "Past sessions" and "Audit record"; the pre-committed rules rewritten (write-back, audit BUILT, backup exclusion BUILT as set-and-warn with the unbuilt residues).
    - `threat-model.md`: title, scope paragraph, the "Patient NAMES … in memory only" sentence, Phase 2 item 1 (Complete ordering) and item 2 (NTFS unlink covers the new stores), Phase 3A §3 (no new on-disk plaintext) and surface 4 (Copy's third caller), the `NoteDisplay` paragraph (one exception), THE ENCOUNTER RECORD residue (audit row is the durable evidence), COMPLETION IS SEEN, draft-write residue (g) rewritten, Chrome residue (8) rewritten, Out of scope, Review triggers; NEW section "Privacy and professional controls" (the reversal, the archive, the name, the tab, the audit record, the CSV, exclusions + hooks, C5/C8, residues (a)–(s)).
    - `data-flow-map.md`: title + intro, components (tab list), flows 2 (hooks), 4 (the two new key kinds), 5 (WER), 6 (`encounter.enc` not archived; audit row), 7 (Complete order), 10 (the session's copy; generated/provenance; Copy's third caller), 18 (display-value exception; audit row; after-Complete sentence), NEW flow 22, non-flows (at-rest plaintext, the CSV, logs markers, the OneDrive/backup bullet), "The Chrome side at a glance".
    - `intended-use.md` (not a system of record → Past sessions + audit; new "In the app" section with D14's line; the practice docs and the consent-field sentence; scope note dated 2026-10-01); `incident-process.md` (what counts, evidence preservation, the wrong-note steps 2–3 — the audit row is the durable evidence); `docs/security/README.md`; `docs/design-system.md` (tab list + the tab's description, "No secondary windows" now names the sanctioned confirmations and the save dialog, Delete now in the two-click paragraph, the Clinical-content transcript rule, the Microcopy lines for Complete / Past sessions / the retention warning, both `written_done` quotes); `AGENTS.md` (four new subsystem pointers — audit, Past sessions, exclusions/hooks, `docs/practice/` — the Copy pointer's third caller, the launch note, and Local Run Step 5's register line); `CHANGELOG.md` (Added + two Changed entries); `docs/architecture/phase-history.md` (a new section for Phases 1–5).
    - Code: `ui/transcript.py` — the Complete tooltip (both sites) and the two success lines now come from new `ui/models.py` constants `COMPLETE_TOOLTIP` / `COMPLETE_DONE_LINE` / `COMPLETE_WITHOUT_NOTE_LINE` ("… Past sessions shows what was kept"; the screen does not know what one Complete kept, so the lines point at the tab instead of claiming it); `models.WRITE_LINES["written_done"]` gains "Past sessions shows what was kept."; `encounter.py` module docstring (the label is the one place a name is later written). The C9 docstrings in `session_store.py`, `ui/__init__.py`, `main_window.py` `_CheckoutEncounter` and `note.NoteDraft` were already true (Phases 1–2) — re-read, unchanged.
    - Test pins: `test_write_lines.py` `_EXPECTED["written_done"]`; `test_ui_screens.py` the two "Session completed without a note" literals (the Task 5.6 queued-phrase tests) and NEW `TestTranscriptPastSessions::test_the_complete_lines_name_past_sessions` (tooltip + success line, literal).
  - **Class members the C9 list MISSED (swept and changed):** `docs/testing/shipping-gate.md` "Custody" ("The only artefacts that outlive a session are the sheet's numbers…" — false now: a completed gate session leaves a Past-sessions entry and every session an audit row); retention row "Cliniko API responses" and data-flow flow 18 ("a display value that no model, record, log or file holds"); retention row "The Chrome link in the app" ("never written"); `encounter.py`'s docstring. Checked and left (true as written): `models.ChromeView` / `ReviewOpening` / transcript-rendering docstrings, `context_rules.py` reminder index, `bridge.live_display_name`, the Discard lines ("audio cryptographically deleted" — Discard keeps nothing), `shipping-gate.md:28` (audio destroyed at Complete), `lessons.md:40` and threat-model "Phase 6's measurement" (other plans' Phase 6).
  - **Leftover grep (zero unintended hits):** `only copy|destroyed at Complete|no durable audit|durable (minimal )?audit record is|is PLAN\.md Phase 6|until PLAN\.md Phase 6|a Phase 6 task|stays Phase 6|excluding crash reporting is|Complete destroys` over the repo minus `.cursor/` → only intentional hits (the reversal's own history sentences in the retention intro, phase-history and threat-model, "Complete destroys the recording's audio" in intended-use / the review guide, `shipping-gate.md:28`, an unrelated `practitioner_profile.py` docstring). `in memory only|no model, record, log` over `docs/` → only intentional hits (key and Chrome-side lifetimes, and the two sentences that now name the label exception). `Phase 6` over `docs/security/` → only the new as-built mentions. H3 re-runs the C9 grep.
  - **Task 5.2 checklist (every item from the COMPOSER close bullets and EXECUTOR legs, with where it landed — TM = threat-model "Privacy and professional controls", RS = retention schedule):**
    - [x] same-user DPAPI boundary over long-lived stores → TM (a); [x] NTFS unlink → TM (b) + Phase 2 item 2; [x] admin-only exclusions → TM (g), RS backup rule, Out of scope; [x] third-party backups / pagefile / hibernation → TM (g)(h), RS backup rule; [x] `pythonw.exe` breadth → TM (i), RS crash-dump row; [x] CSV outside custody → TM (f) + THE CSV, RS CSV row, privacy doc; [x] expiry only while running → TM (d), RS Past-sessions rule; [x] Chrome crash dumps → TM (n), Chrome residue (8), RS crash row; [x] "never" with no backup → TM (c), RS rule, privacy + downtime docs; [x] audit row `pending` for ever on a kill → TM (o), RS audit rule; [x] local `session_date` + the extra prune day → TM (p), RS; [x] clock wrong at Start / pre-2026 untrusted → TM (p), RS.
    - Phase 2: [x] regenerate-then-cancel pairing → TM (r); [x] failed `keep_generated` unlink → TM (r), RS `generated.enc` row; [x] unreadable `generated.enc` → "Generated note not kept" → TM (r); [x] reconciled `archived` with deletion `pending` → TM (o), RS; [x] leg-b1 quirks (`generated_text` marker, absent/unreadable → `unknown`, casefolded `mock` prefix, `remove_pending_entry` / keyless reconcile, `PastSessionCleanupError`, provenance before `write_note`'s refusals) → TM archive bullets, RS rows.
    - Phase 3: [x] Hide names masks the label only → TM (e), review guide; [x] `pre_audit` rows on pruned/quarantined rows → TM (p), RS audit rule; [x] recovered commit dated now, deletion `pending` → TM (o)(p); [x] unsaved Hide names lasts until close → TM (e), RS settings row; [x] wall-clock trust → TM (d), RS; [x] undated entries never age out → TM (d), RS, downtime doc; [x] design-system: the tab in the list, its two confirmations as sanctioned secondary windows, Delete now in the destructive paragraph → done.
    - Phase 4: [x] console launch prints no traceback → AGENTS launch note, CHANGELOG Changed, TM (m), RS log row; [x] both processes run the hooks → TM EXCLUSIONS, flow 2; [x] `sys.last_*` dropped → TM; [x] one-line log-failure report → TM, RS, flow 2; [x] `logging.lastResort` → TM (m); [x] NOT_CONTENT_INDEXED folders only + inheritance → TM (j), RS row; [x] inherited `PYTHONFAULTHANDLER` / faulthandler off → TM (m) + EXCLUSIONS; [x] the three HKCU values, per-user only → TM, RS registration row, flow 22; [x] location check read-only, unusual logged only → TM (k); [x] native crashes vs WER, console `python.exe` uncovered → TM (i); [x] agent-shell rule → TM (l), AGENTS step 5, RS registration row.
    - [ ] NOT done (outside this task's edit list): leg d2's "lessons.md should say so for debugging" — the AGENTS.md launch note now says it; a `docs/lessons.md` line is for the composer's `/document`.
  - **Plan-vs-code discrepancies (docs follow the code):** (1) a crash-RECOVERED session cannot generate a note or be written back (`can_generate` False on the recovery path) — the downtime procedure says to read its transcript and write the note by hand, then Complete or Discard; (2) C9 lists `written_done`, which was not false; it was changed anyway so the written path also points at Past sessions (consistency with the Transcript screen's lines); (3) the "7 years" retention option is 2557 days (`7*365+2`), described as "7 years"; (4) the audit CSV omits the event codes and `schema_version` (docs say so); (5) the plan's "(…)" in the Start refusal is one of the authored reasons — the downtime doc lists them; (6) AGENTS.md's Tech Stack "Database" row still reads "Local encrypted session storage | Per-session encryption keys" and Current Status / Last Session are untouched as instructed — both for the composer's `/document`; (7) AGENTS.md Local Run Step 5 was edited (the register script now writes WER values; agent-shell rule) — slightly beyond "pointers + launch note", kept because the step would otherwise be untrue.
  - **H3 input (NOT Task 5.2's, carried):** the pre-existing link-following shape in `session_store.sweep_sessions` / `discard_session` under the SESSIONS root (round 13 LEG 1).
  - **Practitioner READ before the smoke (Task 5.1's "practitioner read"):** all five files in `docs/practice/`, especially (a) the README's four OPEN QUESTIONS — above all whether a kept transcript is a health record that must itself be kept 7 years in VIC/NSW/ACT (then a 1-day…1-year setting and Delete now may conflict with the law; the AJGP tension) — none is decided here and none is a claim the docs make; (b) the patient sheet's "[Practice: state your setting here]" and the consent script's "[your setting]"; (c) the privacy doc's placeholders (contacts, regulator, complaints, Cliniko's own hosting page) and its sentence on past-note style learning; (d) the downtime doc's crash-recovery section (transcript only, write the note by hand). The app's retention warning and the README cite the same law; change them together.
  - **Composer:** run the full desktop suite (changed: `ui/models.py`, `ui/transcript.py`, `encounter.py` docstring; tests `test_write_lines.py`, `test_ui_screens.py`). Then resume me for `/review-loop` (next round 25).
- **EXECUTOR stage-5 leg e2 (2026-10-01T15:24:49+10:00) — the suite was green (5247 passed, 4 skipped; ruff clean, mypy 56 files), so Tasks 5.1–5.2 are 🟩 and Overall Progress is 74% (14 of 19). `/review-loop` (cap 3) CONVERGED at round 26; round 27 not needed.**
  - **Round 25** (four read-only lenses, re-verified in-session): 0 CRIT / 0 HIGH / 4 MED / 17 LOW, all doc-only and applied. MED-001: residue (o) misstated the audit row after a Complete killed past its key deletion (it ends `orphan_gc` with the directory still there; `past_session` can stay `none` with the entry listed). MED-002: a Past-sessions entry's transcript is decrypted when the entry OPENS, not at "Show transcript" (and flow 4's review-window sentence missed the tab). MED-003: the practice drafts said "everything kept is encrypted" (learned phrases and rules are plain-text config). MED-004: the patient sheet's Discard overclaimed (text already in Cliniko stays). LOWs: reconcile vs commit, the unchecked archive root, residue (p)'s examples, the CSV BOM, the WindowsLayer scope, the hook line, residue (j)'s example, `generated.enc` readability and residue (r) in the retention rows, the name sources and destroyer list, C10 beyond-research claims marked **[Reviewer: …]**, Hide-names wording, the Discard/audit-row C9 class, the consent time (Start press), the verbatim `AuditWriteError:` quote, the README's "Keeping these documents" rules.
  - **Round 26** (confirmation + a deep pass over the lighter-covered docs): 0 CRIT / 0 HIGH / 0 MED / 11 LOW, all doc-only and applied — three unfixed siblings of round-25 fixes in flows 2 and 22 and the AGENTS exclusions pointer; the patient Discard sentence (clipboard, learned phrases); residue (o)'s bound; the incident process's relaunch (start-up runs the prune, the 24 h sweep and the retention sweep before the window shows — export before closing, copy the folder aside first; verified LOW from a proposed MED); the review guide's dose-blocking example, proposals/pre-fills "not necessarily said", Delete now after deleting a note; "every Complete keeps all three" qualified as a class in six places; the design-system secondary-window list. Converged.
  - **No code, string or test changed since the green run** — every round-25/26 fix is in `docs/`, `PLAN.md`, `CHANGELOG.md`, `AGENTS.md` (the exclusions pointer only, added this phase) or the plan. `docs/architecture/phase-history.md` now names rounds 25–26.
  - **For the composer's `/document` (outside this spawn's edit scope; round 25 LOW-021):** AGENTS.md Current Status ("NEXT: PLAN.md Phase 6 … planned in Plan Mode"), Last Session ("Next priority: plan PLAN.md Phase 6") and the Tech Stack "Database" row predate the build; plus the leg-e1 `docs/lessons.md` note (a console launch prints no traceback — debug from the type name).
  - **Practitioner READ (unchanged from leg e1, plus round 25–26 additions):** the practice drafts now carry three more **[Reviewer: …]** marks (the correction right / state access rules, and the Notifiable Data Breaches scheme in the privacy and downtime drafts — none in the 2026-10-01 research).
  - **Next:** the cross-family codex pass (`/peer-loop`) per the loop config, then the Hardening stage; H3 still carries the `session_store.sweep_sessions` / `discard_session` link-following shape (round 13 LEG 1).
- **EXECUTOR stage-5 leg e3 (2026-10-01T15:32:15+10:00) — codex round 27 (pass `stage-5.p1`, slice A): LEG 1 confirmed all four (3 MED + 1 LOW, docs only); LEG 2 applied each and closed its class.** PR-MED-022: the plaintext files under `%LOCALAPPDATA%\ClinikoScribe` (logs, `clinics.json`, `config\` incl. learned phrases/rules and both settings files, `app.lock`, registration files) are now named in the incident copy step, retention row 69 and three `downtime-procedure.md` sentences. PR-MED-023: `shipping-gate.md` separates the session copy's destruction from the Past-sessions entry and audit row, and says mock CONTENT is not a test-provider session (+2 siblings on the page). PR-MED-024: retention row 54 — the patient id stays in `encounter.enc`, the name goes only to the Past-sessions label. PR-LOW-025: the shipping gate and the design-system Copy enumeration name "Copy saved note". No code, string or test changed; the green 5247 run stands.
- **EXECUTOR stage-5 leg e4 (2026-10-01T15:38:12+10:00) — codex round 28 (slice B, practice docs; round 27 confirmed closed): LEG 1 confirmed all three (2 MED + 1 LOW, docs only); LEG 2 applied each and closed its class.** PR-MED-026: the privacy draft separates the program's own network use from Windows-side protections (set-up-dependent, warn-only, no control over backup/sync); "not sent to any cloud" attributed to the program in both patient-facing docs. PR-MED-027: the privacy draft's learning paragraph now follows `CONSENT_TEXT_V3` (shape check; typed shorthand has no name check; no guarantee). PR-LOW-028: the review guide, intended-use, CHANGELOG, flows 4/22 and phase-history say a regeneration replaces the kept generated note. No code, string or test changed; the green 5247 run stands.
- **EXECUTOR stage-5 leg e5 (2026-10-01T15:42:56+10:00) — codex round 29: PR-MED-029 (PR-MED-026's class not fully closed) confirmed and fixed; the "data stays local" class closed by an exhaustive sweep (81 hits judged, listed in the round 29 tuple).** `intended-use.md`'s "Not a cloud service" and the spoken consent script now state the PROGRAM's behaviour; the patient sheet's Part A carries the backup/sync caveat; three "one computer only" sentences are attributed to the program. `patient-info-v1` kept (agreement unchanged; the draft was never issued). `RETENTION_WARNING` judged true and left (a string change would be code). No code, string or test changed; the green 5247 run stands.
- **EXECUTOR stage-5 leg e6 (2026-10-01T15:47:47+10:00) — codex round 30 (peer_round 4 of 5): PR-MED-030 confirmed. Part A applied; Part B is an OPEN practitioner decision (DECIDED (a) 2026-10-02).**
  - **Part A:** the Past sessions tab's retention warning (`ui/past_sessions_view.py` `RETENTION_WARNING`) now states the program's behaviour: "Clinic Scribe keeps it, encrypted, only in this Windows login's data folder and makes no backup of its own - but backup or sync software, or a folder location it has warned about, can still copy the encrypted files." Updated with it: the literal pin in `test_ui_screens.py` and the `docs/design-system.md` mirror. The ui/extension string sweep found no other false non-consent string.
  - **Ruff clean, mypy 56 files.** Pytest is owed by the composer: `desktop/tests/test_ui_screens.py` (the string's only pins; a full run is the safe choice).
  - **PRACTITIONER DECISION (PR-MED-030 consent wording)** — DECIDED (a) by the practitioner 2026-10-02 (see the COMPOSER stage-7 PRACTITIONER DECISIONS bullet); the record below is the history:
    - **The issue:** the current practitioner consent text (`CONSENT_TEXT_V3`, Practitioner tab) says "Everything it learns is stored on this computer only, and nothing leaves it."
      - That is true of the PROGRAM. It writes what it learns only under this Windows login's data folder and never sends it anywhere; the Cliniko API carries no learned data.
      - It is not a guarantee against copies made by backup or sync software, or by a data folder redirected into OneDrive, a network drive or the roaming profile. The app only warns about the redirected locations it can see.
      - Your voice fingerprint and learned style are encrypted, so a copy stays locked to your login. The learned phrases and shorthand rules are plain text, so a copy of them is readable.
    - **Option (a) — RECOMMENDED: accept with a record now.**
      - The residue is already written into the threat model (practitioner-profile surface 9) and the retention schedule (learned phrases and learned rules rows, 42 and 46).
      - The corrected wording ("stored only in this Windows login's data folder, and the app sends none of it anywhere — backup or sync software can still copy the files") is folded into the next consent version whenever one is next needed for another reason.
      - Nothing changes for you now.
    - **Option (b): bump to consent-v4 now with the qualified wording.**
      - **Code** (corrected H3 round 35 from the code): a new `CONSENT_TEXT_V4` and `CONSENT_TEXT_VERSION = "consent-v4"` in `ui/models.py` (the constant, the text and `__all__`), with V3 kept verbatim as history; the one code reference outside it, `ui/practitioner.py` (the line that shows the current text). `encounter.py` and `practitioner_profile.py` only MENTION the version in comments — refresh those, nothing to change in logic.
      - **Tests** (corrected): the pins in `test_ui_models.py` (the text and version pins and the not-current checks) and `test_ui_screens.py` (the Practitioner tab's shown text). `test_prose_style.py` and `test_encounter.py` are NOT affected (corrected H3 round 36: `test_prose_style.py` hard-codes `consent-v3` in a style profile, but `prose_style` never checks the version — the current-consent gate is `ui/models`; `test_encounter.py` uses `consent-v3` only as a value the per-recording consent refuses; `test_ui_learn_style.py`, `test_sample_notes.py` and `test_style_profile.py` read the constant). The comment-only mentions also include `speaker_eval.py`.
      - **Docs:** the threat model, retention rows 40, 42 and 46, data-flow flow 12/13, the design system, AGENTS.md's profile pointer, phase-history and CHANGELOG.
      - **Consequence for you:** both consent records (voice profile and learned style) read as not current. The Practitioner tab asks for a fresh tick ("Confirm consent", no re-recording). Phrase and rule learning stays off, and the Own voice style refuses, until you re-consent.
      - **Unaffected** (added H3 round 35): voice attribution keeps working; phrases and rules already learned keep applying; the per-recording consent tick (`recording-consent-v1`), the audit row's `consent_text_version` and the patient information sheet (`patient-info-v1`) do not change.
      - A build leg plus a short review; then your re-consent at the smoke.
    - **Option (c) (added H3 round 35): an information line now, no new consent version.**
      - A separate plain line on the Practitioner tab, under the consent box and outside the consent text, worded like the Past sessions tab's retention warning: the app keeps what it learns only in this Windows login's data folder and sends none of it anywhere, but backup or sync software can still copy the files (the learned phrases and shorthand rules are plain text).
      - `CONSENT_TEXT_V3` and every consent record stay as they are: no re-consent and no Own voice outage.
      - Code: one string and its placement in `ui/practitioner.py`, its literal pin in `test_ui_screens.py`, and the design-system mirror; a build leg plus a short review.
      - It corrects what you SEE now, but the text you consented to keeps the unqualified sentence until the next consent version — so fold the wording in then, as in (a).
    - **Why (a):** the claim is true of everything the app itself does. The external-copy risk is the same backup/sync residue already named for every store, and warned about at start-up. A forced re-consent and the Own voice outage buy a wording precision you can fold in at the next consent change. Choose (b) if your clinic computer has IT-managed folder redirection or a backup tool you cannot control, since then the plain-text learned phrases plausibly do leave the machine.
- **EXECUTOR stage-6 leg f1 (2026-10-01T16:11:28+10:00) — H1 `/review-loop` round 32 (1 of 3) over Phases 1–5 as ONE surface: 0 CRIT / 0 HIGH / 0 MED / 13 LOW, all applied; ruff clean, mypy 56 files; pytest owed by the composer.**
  - **Code (5):** LOW-001 `remove_pending_entry` no longer reads an uninspectable entry path as "a link, nothing to remove" (that let a destroyer delete the source key over a pending entry); LOW-002 a mock Complete removes an earlier attempt's unfinished entry key-first before the key (`ArchiveKeeper.drop_unfinished`); LOW-003 the 15-minute tick runs the audit prune and the retention sweep even when the session sweep raised (first failure re-raised for the hook); LOW-004 an unreadable label is retried a day after it failed, not unwrapped on every hourly tick, and a failed delete keeps its cached date; LOW-005 a name a Verified live re-check found is kept for that session's Past-sessions label after a later reconnect (never shown in Chrome).
  - **Tests:** `test_past_sessions.py` (+5, 1 rewritten: the round-17 "read again next tick" pin → "a day later"), `test_audit.py` (+1), `test_ui_bridge.py` (+1), `test_integration_no_sockets.py` (LOW-006: the child's order comment, `reconstruct_reminders()` added).
  - **Docs (7):** residue (o) + retention (Discard/expiry crash windows), residue (p) + retention (a forward clock jump at the prune), the retention warning paraphrase (round 30's wording), the `pre_audit` trigger list, flow 22 (refusal codes; the name sources), THE NAME, AGENTS.md's audit pointer (call sites; how `_PAYLOAD_SIGNATURES` really covers rows).
  - **For the batched smoke:** nothing new to click — LOW-005 shows only as a name instead of "Name not available" after a Chrome reconnect when the Start was made offline.
  - **Composer:** run the full desktop suite (changed source: `past_sessions.py`, `session_store.py`, `app.py`, `ui/bridge.py`). Then resume me for round 33 (a confirmation of these fixes), then H2.
- **EXECUTOR stage-6 leg f2 (2026-10-01T16:24:25+10:00) — the suite was green after round 32 (5254 passed, 4 skipped). H1 CONVERGED at round 33 (🟩, Overall 79%); H2 `/simplify` round 34 applied; pytest owed by the composer.**
  - **Round 33 (H1 confirmation, 2 of 3):** every round-32 fix re-checked against its callers; the classes swept from the code — "an inspection error read as absent before a key deletion" (closed), "a failing timer step skipping an independent one" (`PeriodicSweep` the only one), the day-later retry under clock-back / clock-jump, the re-check name (read only by `keep_label_for`; never Chrome, a log or the audit). One LOW, docs: the destroyer lists (threat model ×2, retention row 63, flow 22, AGENTS.md) now name the mock Complete's pre-boundary removal and that an uninspectable entry path keeps the key.
  - **Round 34 (H2):** 6 behaviour-preserving LOWs, all applied, none substantial — the transcript parsed once per Complete; one `_forget_dates` rule for the label-date caches; the dead `MainWindow._past_sessions` removed; `_recheck_audit_key` / `_audit_failures` reused on the tab; one `_show_completed` ending for the three Complete paths on the Transcript screen; `sorted_listings` typed `Sequence`. Nine candidates consciously left alone (listed in the round).
  - **No change for the batched smoke.**
  - **Composer:** run the full desktop suite (changed source: `session_store.py`, `past_sessions.py`, `ui/main_window.py`, `ui/past_sessions.py`, `ui/past_sessions_view.py`, `ui/transcript.py`; no test changed). Then resume me for H3 (`/security-review`, round 35).
- **EXECUTOR stage-6 leg f3 (2026-10-01T16:47:34+10:00) — the suite was green after H2 (5254 passed, 4 skipped): H2 🟩, Overall 84%. H3 `/security-review` round 35 applied (0 CRIT / 0 HIGH / 0 MED / 7 LOW); H3 🟨; ruff clean, mypy 56 files; pytest owed by the composer.**
  - **Code (5):** SEC-001 one tri-state link check (`session_store.link_state`, `os.lstat`) — `is_symlink` / `is_junction` hide errors on Python 3.13+, so round 32's "uninspectable path refuses" now really holds; SEC-002 (carried input (a), confirmed) a link under `sessions\` is never swept (`link_refused`), keyed away or discarded (`SessionLinkError`, key kept) or offered for recovery — the same guard as round 13, and a refusal behaves like the existing unlink failure (no other custody change, so no MUST-PAUSE); SEC-003 audit month folders that are links are never read, written through or pruned, `[0-9]` months; SEC-004 the CSV export's temp file is a fresh name (a user's own `<name>.tmp` is safe) with a terse error; SEC-005 bounded reads for audit rows, `saved-provenance.enc` and the Past-sessions settings file.
  - **Tests:** `test_past_sessions.py` (`TestSessionLinksAreNeverFollowed` ×2 kinds, `link_state`, the oversized settings file; the round-32 uninspectable test now patches `os.lstat`), `test_audit.py` (export temp ×2, `TestStoreBounds` — oversized row, linked month ×2 kinds). The symlink variants SKIP without Developer Mode.
  - **Docs:** residue (m) widened (SEC-006), new residue (t) (the older readers stay unbounded), flow 19 (the name reaches `label.enc`; the re-check name), flow 22, retention rows 63/66, the threat model's archive / audit / CSV / Phase 2 item 6 sentences.
  - **PR-MED-030 Part B (carried input (c)) — then OPEN; DECIDED (a) by the practitioner 2026-10-02:** the record is corrected (option (b)'s real edit sites, rows 42/46, what consent-v4 would NOT change) and an option (c) is added (an information line on the Practitioner tab, outside the consent text — no re-consent). Recommendation unchanged: **(a)**. `CONSENT_TEXT_V3` untouched.
  - **For the batched smoke:** nothing new to click.
  - **Composer:** run the full desktop suite (changed source: `session_store.py`, `past_sessions.py`, `audit.py`, `ui/models.py`; changed tests: `test_past_sessions.py`, `test_audit.py`). Then resume me for round 36 (the H3 confirmation; cap 37).
- **EXECUTOR stage-6 leg f4 (2026-10-01T16:54:16+10:00) — the round-35 suite had 1 failure (5262 passed, 8 symlink skips): a FIXTURE defect, fixed; no source change.** `test_the_recovery_list_never_offers_a_link[junction]`'s positive control listed a target made by `_aged` (2023 key mtime), which the Recovery list correctly drops as past the 24 h window. `link_state` is not over-broad: it `lstat`s only the child it is given and reads a real folder and a junction's target as not-a-link. That test now uses a fresh target, and every `TestSessionLinksAreNeverFollowed` test ends with the same target reached directly being accepted (sweep, Discard, listing), plus a direct `link_state` check of link vs target. Ruff clean, mypy 56 files. **Composer:** run the full desktop suite (changed: `test_past_sessions.py` only). Then resume me for round 36 (the H3 confirmation; cap 37).
- **EXECUTOR stage-6 leg f5 (2026-10-01T16:57:19+10:00) — H3 CONVERGED at round 36 (🟩, Overall 89%). STAGE-6 SUMMARY (H1–H3; H4 is the composer's).**
  - **H1 `/review-loop` (rounds 32–33, converged):** 13 cross-phase LOWs in round 32, then 1 LOW (docs) in round 33. Code: an uninspectable Past-sessions entry path keeps the source key; a mock Complete removes an earlier attempt's unfinished entry before its key goes; the 15-minute tick runs each of its three steps even when one fails; an unreadable label is retried a day later instead of every hour; a Verified live re-check's name survives a reconnect for the Past-sessions label only.
  - **H2 `/simplify` (round 34):** 6 behaviour-preserving LOWs (one transcript parse per Complete, one date-cache rule, a dead attribute removed, two tab helpers reused, one Complete-succeeded ending on the Transcript screen, `Sequence` typing). 9 candidates left alone, with reasons.
  - **H3 `/security-review` (rounds 35–36, converged):** 7 LOWs plus 3 docs confirmations. A single link check (`session_store.link_state`, `os.lstat`) replaced checks that hid errors on Python 3.13+. Links are refused under `sessions\` (the carried round-13 shape: sweep `link_refused`, `SessionLinkError` on key deletion or Discard, never on the Recovery list) and for audit month folders. The CSV export's temp file gets a fresh name and its error is terse. Audit rows, `saved-provenance.enc` and the Past-sessions settings file have size caps. The leg-f4 test fixed a vacuous positive control.
  - **Residues added or widened:** (m) the console launch shows a library's tracebacks and `warnings` lines (never `scribe-app.exe`); (t) every older reader stays unbounded (a same-user denial of service). The threat model now names the unchecked roots and the linked-row-file case.
  - **Suites:** 5262 passed / 8 skipped (the directory-symlink variants need Developer Mode) plus the f4 test fix (93 passed / 8 skipped in `test_past_sessions.py`); ruff clean, mypy 56 files. Round 36 changed docs and one docstring only.
  - **New for the batched smoke:** nothing to click. A CSV export into a folder that already holds `<name>.csv.tmp` leaves that file alone.
  - **PRACTITIONER DECISION — PR-MED-030 Part B (consent wording), DECIDED (a) 2026-10-02.** Final options (as offered):
    - **(a) RECOMMENDED:** accept with a record now and fold the qualified wording into the next consent version.
    - **(b):** consent-v4 now. You re-tick consent, and learning and Own voice stay off until you do.
    - **(c):** an information line on the Practitioner tab outside the consent text, with no re-consent.

    `CONSENT_TEXT_V3` is unchanged.
  - **Composer:** no suite owed (no executable change since the green run). H4, the codex pass, is yours.
- **EXECUTOR stage-6 leg f6 (2026-10-01T17:04:39+10:00) — codex round 37 (H4, pass `stage-6.p1` peer_round 1): both LOWs confirmed and applied; round 37 Closed.** PR-LOW-031 (tests only): `conftest.bounded_read_spy` plus an otherwise-valid one-byte-over / at-cap test for each of the five capped readers (audit rows, `saved-provenance.enc`, `generated.enc`, the Past-sessions label, the settings file). No reader was found unbounded. PR-LOW-032 (docs): residue (m) and the CHANGELOG headline now speak of UNCAUGHT exceptions only. Ruff clean, mypy 56 files. **Composer:** run `tests/test_audit.py tests/test_past_sessions.py tests/test_session_store.py` (`conftest.py` changed too, so a full desktop suite is the safe choice), then continue H4.
- Current in-progress step: none — every task is 🟩; the batched smoke P.1–P.5 PASSED 2026-10-02 (P.2 on the H5 build); committed by the composer (stage-7)
- Immediate next action: `/document` (AGENTS.md Current Status / Last Session / Tech Stack "Database" row; `docs/lessons.md`: a console launch prints no UNCAUGHT-exception tracebacks; on Python 3.13+ `Path.is_symlink()`/`is_junction()` read False on an unreadable folder; `register-native-host.py` fails with WinError 32 while Chrome holds `scribe-host.exe` — close Chrome first), then `/retro`. Small follow-ups: PR-LOW-033 (staged-label spy test), residue (t) (older readers without a size cap), a friendly WinError 32 message in `register-native-host.py`.
- Open blockers / open questions: None blocking. Practitioner-owned (no build impact): the remaining open questions in `docs/practice/README.md` (the first is answered — 7 years minimum), for the independent review.
- Last plan sync: 2026-10-02

## Review History
Each /review invocation appends a one-line entry here. Round numbers follow /review's **Detect review round** rule.

- 2026-10-01 round 1: 0 CRIT / 0 HIGH / 5 MED / 0 LOW; skew=none; action=plan amended (codex gpt-6-astra medium plan peer-review; 5 build-affecting, all applied)
- 2026-10-01 round 2: 0 CRIT / 0 HIGH / 6 MED / 0 LOW; skew=none; action=plan amended (codex plan peer-review; 6 build-affecting, all applied)
- 2026-10-01 round 3: 0 CRIT / 0 HIGH / 4 MED / 0 LOW; skew=none; action=plan amended (codex plan peer-review; 4 build-affecting, all applied)
- 2026-10-01 round 4: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=plan amended (codex plan peer-review; 2 build-affecting, all applied)
- 2026-10-01 round 5: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=plan amended (codex plan peer-review; 1 build-affecting, applied; cap 5 reached)
- 2026-10-01 round 6: 0 CRIT / 0 HIGH / 2 MED / 12 LOW; skew=none; action=none
- 2026-10-01 round 7: 0 CRIT / 0 HIGH / 0 MED / 17 LOW; skew=mixed; action=triage-and-ship
- 2026-10-01 round 8: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium cross-family peer, Phase 1 slice A source, pass stage-1.p1 peer_round 1)
- 2026-10-01 round 9: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=triage-and-ship (both test-harness LOWs verified and applied by the executor, leg a7; codex gpt-6-astra medium cross-family peer, Phase 1 slice B tests, pass stage-1.p1 peer_round 2; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 10: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=accept-close (codex gpt-6-astra medium cross-family peer, confirmation of round 9, pass stage-1.p1 peer_round 3; LEG 1 verified docs-only, Accepted-with-record; pass stage-1.p1 CONVERGED at peer_round 3/5)
- 2026-10-01 round 11: 0 CRIT / 0 HIGH / 1 MED / 2 LOW; skew=none; action=none
- 2026-10-01 round 12: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=mixed; action=triage-and-ship
- 2026-10-01 round 13: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=triage-and-ship (both production-behavioral LOWs verified by the executor, LEG 1, and applied, LEG 2, closing their classes; codex gpt-6-astra medium cross-family peer, Phase 2 slice A source, pass stage-2.p1 peer_round 1)
- 2026-10-01 round 14: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=triage-and-ship (both test-harness LOWs verified by the executor, LEG 1, and applied as tests only, LEG 2, with no source defect; codex gpt-6-astra medium cross-family peer, Phase 2 slice B tests + round 13 confirmation, pass stage-2.p1 peer_round 2)
- 2026-10-01 round 15: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium cross-family peer, confirmation of round 14, pass stage-2.p1 peer_round 3; pass stage-2.p1 CONVERGED at peer_round 3/5)
- 2026-10-01 round 16: 0 CRIT / 0 HIGH / 2 MED / 19 LOW; skew=none; action=none
- 2026-10-01 round 17: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=none
- 2026-10-01 round 18: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=triage-and-ship (the production-behavioral LOW verified by the executor, LEG 1, and applied, LEG 2, closing the stale-status class for both sweep lines; codex gpt-6-astra medium cross-family peer, Phase 3 slice A source, pass stage-3.p1 peer_round 1; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 19: 0 CRIT / 0 HIGH / 0 MED / 4 LOW; skew=fix-induced; action=triage-and-ship (all four verified by the executor, LEG 1, and applied, LEG 2 — PR-LOW-015 closes round 18's class structurally in `_reload_settings`, PR-LOW-016..018 as tests only; codex gpt-6-astra medium cross-family peer, Phase 3 slice B tests + round 18 confirmation, pass stage-3.p1 peer_round 2; PR-LOW-015 is round 18's class not fully closed; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 20: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=triage-and-ship (the test-harness LOW verified by the executor, LEG 1 — the production cleanup of an open entry on Delete now and expiry holds by reading — and applied as tests only, LEG 2; codex gpt-6-astra medium cross-family peer, confirmation of round 19, pass stage-3.p1 peer_round 3; first test-harness-only round; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 21: 0 CRIT / 0 HIGH / 1 MED / 3 LOW; skew=none; action=none
- 2026-10-01 round 22: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none
- 2026-10-01 round 23: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=pre-existing; action=triage-and-ship (both verified by the executor, LEG 1, and applied, LEG 2 — PR-MED-020 closed for its whole surface: every handler `setup_logging` builds reports a write failure as one fixed type line (`QuietHandlerErrors`), pinned with a source scan; PR-LOW-021 as tests only; codex gpt-6-astra medium cross-family peer, Phase 4 source + tests, pass stage-4.p1 peer_round 1; PR-MED-020 contradicts a round-22 dismissal; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 24: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium cross-family peer, confirmation of round 23, pass stage-4.p1 peer_round 2; pass stage-4.p1 CONVERGED at peer_round 2/5)
- 2026-10-01 round 25: 0 CRIT / 0 HIGH / 4 MED / 17 LOW; skew=none; action=none (Phase 5 docs truth-against-code, /review-loop 1 of 3; all doc-only, applied; LOW-021 routed to the composer's /document)
- 2026-10-01 round 26: 0 CRIT / 0 HIGH / 0 MED / 11 LOW; skew=mixed; action=triage-and-ship (Phase 5 confirmation + deeper pass, /review-loop 2 of 3; all doc-only, applied; converged)
- 2026-10-01 round 27: 0 CRIT / 0 HIGH / 3 MED / 1 LOW; skew=none; action=triage-and-ship (all four verified by the executor, LEG 1, and applied, LEG 2, each closing its class — 8 sibling sites across the security, testing and practice docs and the design system; docs only, no pytest owed; codex gpt-6-astra medium cross-family peer, Phase 5 slice A security docs + C9 + strings, pass stage-5.p1 peer_round 1; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 28: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=none; action=triage-and-ship (all three verified by the executor, LEG 1, and applied, LEG 2, each closing its class — 7 sibling sites across the practice docs, intended-use, flows 4/22, CHANGELOG and phase-history; docs only, no pytest owed; codex gpt-6-astra medium cross-family peer, Phase 5 slice B practice docs + round 27 confirmation, pass stage-5.p1 peer_round 2; round 27 confirmed closed; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 29: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=triage-and-ship (PR-MED-029 verified by the executor, LEG 1, and applied, LEG 2 — the "data stays local" class swept exhaustively over docs, PLAN, AGENTS, CHANGELOG and READMEs, 2 false sites fixed and 3 attributed to the program, every other hit judged true or unrelated; `patient-info-v1` kept; docs only; codex gpt-6-astra medium cross-family peer, confirmation of round 28, pass stage-5.p1 peer_round 3; PR-MED-027 / PR-LOW-028 confirmed; PR-MED-029 is PR-MED-026's class not fully closed; routed to the executor)
- 2026-10-01 round 30: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=fix-induced; action=triage-and-ship (Part A applied: `RETENTION_WARNING` rewritten to the program's behaviour with its literal pin, the ui/extension string sweep found no other; Part B deferred to an OPEN practitioner decision — `CONSENT_TEXT_V3` unchanged, residue named in the threat model and retention rows 42/46, executor recommends (a) accept-with-record and fold into the next consent version; codex gpt-6-astra medium cross-family peer, confirmation of round 29, pass stage-5.p1 peer_round 4 of 5; the four-document fix confirmed; PR-MED-030 reaches the shipped practitioner consent text and the retention warning string; routed to the executor for LEG 1)
- 2026-10-01 round 31: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium cross-family peer, confirmation of round 30, pass stage-5.p1 peer_round 5/5; pass stage-5.p1 CONVERGED at the cap; PR-MED-030 Part B stays an open practitioner decision)
- 2026-10-01 round 32: 0 CRIT / 0 HIGH / 0 MED / 13 LOW; skew=pre-existing; action=triage-and-ship (Hardening H1, /review-loop 1 of 3, Phases 1–5 as one surface; all 13 applied — 5 source, 1 test, 7 docs)
- 2026-10-01 round 33: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=same-family; action=triage-and-ship (Hardening H1, /review-loop 2 of 3, confirmation of round 32 + class sweeps; the LOW docs-only, applied; H1 CONVERGED)
- 2026-10-01 round 34: 0 CRIT / 0 HIGH / 0 MED / 6 LOW; skew=pre-existing; action=triage-and-ship (Hardening H2, /simplify; 6 behaviour-preserving single-module simplifications applied, none substantial)
- 2026-10-01 round 35: 0 CRIT / 0 HIGH / 0 MED / 7 LOW; skew=pre-existing; action=triage-and-ship (Hardening H3, /security-review over the whole plan surface; all 7 applied — link refusal for the sessions root and the audit months, the export's temp name, bounded reads, residue (m)/(t), flow 19 and the PR-MED-030 record; Part B stays open)
- 2026-10-01 round 36: 0 CRIT / 0 HIGH / 0 MED / 3 LOW; skew=same-family; action=triage-and-ship (Hardening H3 confirmation of round 35 + class sweeps from the code; the 3 LOWs docs + one docstring, applied; H3 CONVERGED)
- 2026-10-01 round 37: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=none; action=triage-and-ship (both verified by the executor, LEG 1, and applied, LEG 2 — PR-LOW-031 as tests only: a bounded-read spy and otherwise-valid one-byte-over / at-cap fixtures for all five capped readers, no reader found unbounded; PR-LOW-032 docs-only, residue (m) + CHANGELOG sibling; codex gpt-6-astra medium cross-family peer, H4 over the H1-H3 changes, pass stage-6.p1 peer_round 1; routed to the executor for LEG 1 verify + LEG 2 fix)
- 2026-10-01 round 38: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=accept-close (codex gpt-6-astra medium cross-family peer, confirmation of round 37, pass stage-6.p1 peer_round 2; PR-LOW-033 test-harness Accepted-with-record under the D9 harness tail; pass stage-6.p1 (H4) CONVERGED at peer_round 2/5)
- 2026-10-02 round 39: 0 CRIT / 0 HIGH / 0 MED / 2 LOW; skew=same-family; action=triage-and-ship (H5 — the 7-year minimum retention, /review-loop 1 of 3 over the H5 diff only, stage-7 executor in-session; both LOWs docs-only in `docs/practice/`, applied; code holds on every named target; H5 CONVERGED)
- 2026-10-02 round 40: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=fix-induced; action=triage-and-ship (codex gpt-6-astra medium cross-family peer, pass stage-7.p1 peer_round 1 of 5, over the H5-only tree diff; PR-LOW-034 the unreadable-entry lines still offer Delete now without the made-in-error limit; executor LEG 1 confirmed (plus the uncited sibling `ENTRY_UNREADABLE`), LEG 2 applied as a class — four app lines through one shared tail, four doc sites, pins updated)
- 2026-10-02 round 41: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (codex gpt-6-astra medium cross-family peer, confirmation of round 40, pass stage-7.p1 peer_round 2 of 5; pass stage-7.p1 CONVERGED; H5 done)

## Review Findings Log
Each /review invocation appends a detailed findings block here, with /fix updating per-finding Decision and Notes as it processes each one. Format and plan-peer-review `Source:` / `Materiality:` rules: see `.cursor/templates/implementation-plan-template.md` (canonical).

### Round 1 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the peer's stdout; read-only sandbox)
- Materiality: 5 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: bdf7eed + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-privacy-professional-controls.md` and `.agents/skills/peer-review/SKILL.md`; scoped project context in `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session_store.py`, `session.py`, `transcription.py`, `note.py`, `encounter.py`, `clinics.py`, `draft_write.py`, `logging_setup.py`, `practitioner_profile.py`, `secure_storage.py`, `note_config.py`, and `app.py`.
  - Named regions in `ui/main_window.py`, `ui/transcript.py`, `ui/bridge.py`, `ui/models.py`, `ui/note.py`, `ui/recovery.py`, and `ui/session_screen.py`.
  - `scripts/register-native-host.py`; relevant `desktop/pyproject.toml` sections; requested regions in `test_session_store.py`, `test_session_machine.py`, `test_ui_screens.py`, `test_display_name.py`, `test_session_types.py`, `test_cliniko_client.py`, and `test_integration_no_sockets.py`.
  - Cited portions of the retention schedule, threat model, data-flow map, intended-use statement, incident process, and design system.
- Finding verification: 8 candidates / 3 dropped / 0 downgraded. Duplicate candidates consolidated. Dropped concerns were already covered or lacked a concrete defect.
- Review was static and read-only. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-001 — Interrupted completion can retain an archive after subsequent Discard or expiry**

- Plan section: C1, D6, Task 2.2, Flow 4.
- Materiality: build-affecting
- Why it matters: Publishing the archive precedes deleting the original session key. If that deletion fails, or the process stops between these operations, the original session remains recoverable alongside an independently decryptable archive. Subsequent Discard or expiry currently removes only the original session. The plan adds audit updates to those paths, but no reconciliation of the previously published archive. Discarded content can therefore remain indefinitely under the default retention setting. Interrupted staging has a related gap: its cleanup is assigned to a sweep explicitly disabled when retention is “never.”
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:359`: “The Past-sessions entry is written, moved into place and verified BEFORE `delete_session_key`.”
  - `.cursor/plans/plan-privacy-professional-controls.md:313`: “Discard, expiry, orphan_gc and failed sessions: never archived.”
  - `.cursor/plans/plan-privacy-professional-controls.md:267`: “The Past-sessions retention sweep runs at startup and hourly, and never when the setting is "never".”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:625`: `(session_dir / KEY_FILENAME).unlink(missing_ok=True)`
  - `desktop/src/scribe_desktop/session_store.py:745`: `delete_session_key(session_dir)`
  - `desktop/src/scribe_desktop/session_store.py:759`: `delete_session_key(session_dir)`
  - `desktop/src/scribe_desktop/session_store.py:762`: `shutil.rmtree(session_dir, ignore_errors=True)`
  - These operations contain no archive rollback or reconciliation; an unlink failure propagates before completion finishes.
- Suggested change: Define the archive’s pending/committed lifecycle across publication and source-key deletion, including restart recovery and subsequent Discard/expiry. Separate incomplete-entry cleanup from retention expiry so it also runs with “never.” Add failure-injection tests at staging, publication, verification, and source-key deletion, followed by retry, Discard, expiry, and restart.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:745/759/762 hold no archive reconciliation). C1 now defines PENDING vs COMMITTED entries (committed once sessions\<id> is gone); Discard/expiry/orphan_gc remove a pending entry key-first (D6, Flow 4, Task 2.3); clean_staging() runs every startup and tick independent of retention (Schema, Task 2.2); failure-injection tests at staging/publish/verify/key-delete followed by retry/Discard/expiry/restart added to Validation.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-002 — A successful audit precheck does not protect the previous session from a later `begin` failure**

- Plan section: Flow 1, Task 1.3, session verification.
- Materiality: build-affecting
- Why it matters: A writable-store precheck cannot guarantee the later row write, fsync, or replacement succeeds. The proposed placement of `begin` occurs after `_retire_locked`. If the actual audit write fails, Start is refused but the previous queued session has already lost its live handle. This contradicts the explicit verification requirement.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:462`: “`start()`: the precheck before `_retire_locked` (759); `begin` after `write_encounter_record` (C2); `start_failed` in the cleanup `except` (799-810).”
  - `.cursor/plans/plan-privacy-professional-controls.md:405`: “Start refused on audit failure with nothing left on disk and the previous QUEUED session NOT retired;”
- Evidence:
  - `desktop/src/scribe_desktop/session.py:759`: `self._retire_locked(live)`
  - `desktop/src/scribe_desktop/session.py:775`: `write_encounter_record(`
  - `desktop/src/scribe_desktop/session.py:809`: `discard_session(directory, crypto)`
  - The cleanup removes the new session; it does not restore the retired session.
- Suggested change: Stage the new session’s mandatory audit write before retiring the previous session, or otherwise make retirement conditional on successful `begin`. Test a successful precheck followed by a failed actual row write, asserting that the previous queued session remains installed and usable.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session.py:759 retires before the RecordingSession/id is built at 760). Flow 1 now builds the RecordingSession and runs AuditLog.begin BEFORE _retire_locked; the separate precheck is removed (Task 1.2); C2 and Task 1.3 updated; the Validation test now fails the actual row write and asserts the previous QUEUED session stays installed and usable.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Missing verification / rollback / migration

**PR-MED-003 — `read_for_review` cannot establish that the complete archive is recoverable**

- Plan section: D1, C1, Tasks 2.2–2.3.
- Materiality: build-affecting
- Why it matters: The specified verification helper checks the transcript and an optional saved note using a supplied in-memory key. It does not reopen the archive’s DPAPI key, validate the label or generated note, or require a saved note when one was meant to be archived. Passing this check therefore does not establish the promised archive is complete and recoverable before the source key is destroyed.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:479`: “`write_entry` (staging → verify via `read_for_review` → `os.replace`, replacing an existing entry key-first)”
  - `.cursor/plans/plan-privacy-professional-controls.md:486`: “Behaviour: every non-mock Complete leaves exactly one verified entry, and the session directory is gone.”
- Evidence:
  - `desktop/src/scribe_desktop/ui/models.py:1452`: `def read_for_review(directory: Path, crypto: SessionCrypto) -> ReviewOpening:`
  - `desktop/src/scribe_desktop/ui/models.py:1457`: `document = read_transcript(directory, crypto)`
  - `desktop/src/scribe_desktop/ui/models.py:1460`: `if not (directory / NOTE_FILENAME).is_file():`
  - `desktop/src/scribe_desktop/ui/models.py:1461`: `return ReviewOpening(document, None)`
  - `desktop/src/scribe_desktop/ui/models.py:1463`: `note = read_note(directory, crypto)`
- Suggested change: Specify a full archive verification step before source-key deletion: reopen the published entry through its wrapped archive key, require the expected artifact set, and verify label/generated/transcript/note identity and readability. Reuse existing readers within that check. Add tests for an unusable archive key, missing expected saved note, and corrupt label or generated artifact.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (ui/models.py:1452-1463 uses the in-memory key and skips a missing note). D1 now specifies full verification before publish: re-open the staged entry through its own key.dpapi from disk, require the D6 artifact set, decrypt label/generated/transcript/note with the existing readers, compare SHA-256 to the source bytes; Flow 3 and Task 2.2 point to it; tests for an unusable key, a missing expected note and corrupt label/generated added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-004 — Startup expiry removes the date needed for a pre-audit row before returning its result**

- Plan section: D8, Task 1.3, migration verification.
- Materiality: build-affecting
- Why it matters: An existing session can first be touched by the startup expiry sweep. That sweep removes the session directory before returning, and its result contains no creation date. Recording results afterward cannot satisfy D8’s original-session-date requirement, potentially losing the migration row or assigning it to the wrong retention month.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:331`: “`pre_audit` rows, for sessions started before Phase 6, are dated by `_session_created_at`, made public and read BEFORE the directory is removed.”
  - `.cursor/plans/plan-privacy-professional-controls.md:465`: “Sweep: `app.run_sweep` returns and records its results (C7); the audit prune runs at startup and every 24 h on the sweep timer.”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:1021–1023`:
    ```python
    class SweepResult:
        session_id: str
        action: str  # kept | skipped_active | expired | orphan_gc | error
    ```
  - `desktop/src/scribe_desktop/session_store.py:1147–1150`:
    ```python
    elif current - _session_created_at(child, current) >= max_age.total_seconds():
        delete_session_key(child)  # key first — binding ordering
        shutil.rmtree(child, ignore_errors=True)
        action = "expired"
    ```
  - `desktop/src/scribe_desktop/session_store.py:1155`: `results.append(SweepResult(session_id, action))`
- Suggested change: Capture the content-free creation facts before deletion and carry them in the sweep result, or add a nonblocking pre-deletion audit callback. Define handling for unavailable or untrusted dates. Add an upgrade test where an existing session expires on the first startup, preserving C7’s prohibition on encounter decryption.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:1147-1155: the expired dir is removed before SweepResult(session_id, action) is appended). SweepResult gains a content-free created_at captured before deletion (D8, Flow 4, Task 1.3); an untrusted date is recorded as the sweep time; an upgrade test where a pre-Phase-6 session expires on first startup added, C7 unchanged.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Coverage

**PR-MED-005 — The write-audit hook misses successful reconciliation and pre-send attempts**

- Plan section: Task 1.4, D8, Flow 5.
- Materiality: build-affecting
- Why it matters: A previously uncertain write can be confirmed as written without `_finish_write` running. The proposed audit hook consequently leaves its durable outcome stale; Complete then destroys `write.enc`, and Past sessions displays the stale audit outcome. The same hook also omits the known pre-send attempt if the process stops before the finish callback. These are missing hook paths, not best-effort audit-write failures.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:470`: “Files: `MainWindow._finish_write` (`ui/main_window.py:1856`), after `_store_write_record`: attempts, outcome, refusal, `written_at`, best-effort (C2).”
  - `.cursor/plans/plan-privacy-professional-controls.md:271`: “Opening an entry shows the generated note and saved note side by side, the Cliniko write outcome (from the audit row), Copy (saved note) and Show transcript.”
- Evidence:
  - `desktop/src/scribe_desktop/ui/main_window.py:1842`: `if isinstance(prepared, AlreadyWritten):`
  - `desktop/src/scribe_desktop/ui/main_window.py:1847`: `self._store_write_record(job, reconciled_record(earlier, now=_utc_now()))`
  - `desktop/src/scribe_desktop/ui/main_window.py:1850`: `return models.write_line("written_seen")`
  - `desktop/src/scribe_desktop/ui/main_window.py:1776–1778`:
    ```python
    if isinstance(prepared, str):
        self._end_write(job, prepared)
        return
    ```
  - `desktop/src/scribe_desktop/ui/main_window.py:1852`: `self._store_write_record(job, attempt)  # on disk BEFORE hop 2 (Constraint 5)`
- Suggested change: Audit content-free facts at every durable write-record transition, including attempt, finish, and reconciliation; the shared `_store_write_record` boundary is a suitable candidate. Cover pre-send refusals separately where required by `last_refusal`. Preserve C2 and test unknown → reconciled-written → Complete, plus an attempt without a finish callback.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (main_window.py:1847 reconciled path and 1852 attempt never reach _finish_write). Task 1.4 moves the hook to _store_write_record (every transition: attempt, reconciled, finished, unknown) plus the WriteRefusal branch recording its fixed code (never the display line); Flow 2 updated; tests for unknown -> reconciled -> Complete, attempt without finish, and a refusal code added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

PEER-PLAN-ROUND-1 RESULT: 5 findings (CRIT 0 / HIGH 0 / MED 5 / LOW 0; build-affecting 5 / record-only 0 / invalid 0).


### Round 2 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 2)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the peer's stdout; read-only sandbox)
- Materiality: 6 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: bdf7eed + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-privacy-professional-controls.md` and `.agents/skills/peer-review/SKILL.md`; scoped context in `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session_store.py`, `session.py`, `transcription.py`, `note.py`, `encounter.py`, `clinics.py`, `draft_write.py`, `logging_setup.py`, `practitioner_profile.py`, `secure_storage.py`, `note_config.py`, and `app.py`.
  - Requested regions in `ui/main_window.py`, `ui/transcript.py`, `ui/bridge.py`, `ui/models.py`, `ui/note.py`, `ui/recovery.py`, and `ui/session_screen.py`.
  - `scripts/register-native-host.py`; relevant `desktop/pyproject.toml` sections; requested regions in `test_session_store.py`, `test_session_machine.py`, `test_ui_screens.py`, `test_display_name.py`, `test_session_types.py`, `test_cliniko_client.py`, and `test_integration_no_sockets.py`.
  - Cited portions of the retention schedule, threat model, data-flow map, intended-use statement, incident process, and design system.
- Finding verification: 10 candidates / 4 dropped / 0 downgraded. Dropped: an independent pending-entry retention race, patient-name mismatch, a required separate worker-failure event, and a content-leak claim based only on missing test wording.
- Review was static and read-only. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-001 — Directory absence cannot distinguish completed archives from discarded archives**

- Plan section: C1; Flow 4; Tasks 1.1, 2.2–2.3.
- Materiality: build-affecting
- Why it matters: Complete can publish the verified archive and destroy the source key, then leave a source directory because removal fails or the process stops. The archive remains PENDING, and the prescribed orphan-GC hook deletes the only decryptable local transcript/note copy. Conversely, expiry removes the source directory before its result-driven archive cleanup; interruption between those steps makes discarded content satisfy the COMMITTED predicate. These are consequences of the new predicate, beyond the original publication-before-key-deletion window.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:370`: “an entry is COMMITTED only once its source session directory `sessions\<id>` is gone; while that directory still exists the entry is PENDING.”
  - `.cursor/plans/plan-privacy-professional-controls.md:614`: “A failed `rmtree` leaves a keyless orphan that the sweep's `orphan_gc` removes.”
  - `.cursor/plans/plan-privacy-professional-controls.md:659`: “Pending-entry removal (C1): `discard()`, `discard_recovered`, `ui/recovery.py:451` and `app.run_sweep`'s `expired` / `orphan_gc` results call `remove_pending_entry`.”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:745`: `delete_session_key(session_dir)`
  - `desktop/src/scribe_desktop/session_store.py:749`: `crypto.destroy()`
  - `desktop/src/scribe_desktop/session_store.py:751`: `shutil.rmtree(session_dir, ignore_errors=True)`
  - `desktop/src/scribe_desktop/session_store.py:1144–1146`:
    ```python
    delete_session_key(child)
    shutil.rmtree(child, ignore_errors=True)
    action = "orphan_gc"
    ```
  - `desktop/src/scribe_desktop/session_store.py:1155`: `results.append(SweepResult(session_id, action))`
- Suggested change: Define durable operation state that distinguishes completion from Discard/expiry and survives source-directory removal. Reconcile that state at startup; directory absence alone must not establish commitment. Test interruption immediately after source-key deletion, failed/partial directory removal, and interruption between expiry’s source deletion and archive cleanup.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:745-751 and 1144-1146: a completed-then-rmtree-failed session is orphan_gc'd, and expiry removes the source before any result-driven cleanup). C1 reworked: durable state lives in the entry (a content-free plaintext `pending` marker); every non-Complete destroyer (discard, discard_recovered, recovery.py:451, the sweep's expired via a new before_destroy callback) removes the entry key-first BEFORE deleting the source key, so a pending entry whose source key is gone can only follow a Complete and is committed by reconcile_pending (right after delete_session_key, at startup, each sweep tick); orphan_gc commits instead of deleting. Flows 3-4, D6, Schema, Tasks 1.1/2.2/2.3 and Validation (three interruption tests) reconciled.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-002 — The relocated audit begin leaves two Start failures outside the specified failure hook**

- Plan section: Flow 1; C2; Task 1.3.
- Materiality: build-affecting
- Why it matters: After the new audit row is written, retirement can refuse because a live transcriber remains uncleared, or session-directory creation can fail. Both occur outside the existing cleanup branch named by the task. The row remains `pending` despite Start being refused; when no directory exists, the sweep cannot correct it.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:246`: “Any failure after `begin` marks the row `start_failed` in the existing cleanup branch (best-effort).”
  - `.cursor/plans/plan-privacy-professional-controls.md:624`: “`start()`: build the `RecordingSession` and call `begin` BEFORE `_retire_locked` (759), per Flow 1 / C2; `start_failed` in the cleanup `except` (799-810).”
- Evidence:
  - `desktop/src/scribe_desktop/session.py:765–768`:
    ```python
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StoreWriteError(f"failed creating session directory: {exc}") from exc
    ```
  - The later protected block begins at `desktop/src/scribe_desktop/session.py:771`: `try:`
  - Its handler is at `desktop/src/scribe_desktop/session.py:799`: `except Exception:`
  - `desktop/src/scribe_desktop/session.py:1882–1883`:
    ```python
    if not self._stop_live_locked(live):
        self._refuse_uncleared_live("start")
    ```
- Suggested change: Explicitly extend best-effort `start_failed` finalization across every operation after successful `begin`, including retirement and directory creation. Preserve the previous live session when retirement refuses. Add both failure cases to the validation list.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session.py:765-768 mkdir and 1882-1883 the retire refusal lie outside the 771/799 try). Flow 1 step 5 and Task 1.3: one try spans everything after a successful begin, recording start_failed on the retire refusal, directory creation and the existing cleanup; tests for both added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-003 — Delete-note completion removes the proposed mock discriminator before archive selection**

- Plan section: D4, D6; Task 2.3.
- Materiality: build-affecting
- Why it matters: Both delete-note completion paths unlink `note.enc` before the verifier from which D4 obtains the note. For a real transcript with a mock-provider saved note, the transcript detector is false and the note detector has lost its input. The proposed ordering can archive a session that D6 expressly excludes. The deleted note’s audit metadata has the same ordering problem.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:307`: “the archive is written inside `complete_session`, after verification and before `delete_session_key` (745)”
  - `.cursor/plans/plan-privacy-professional-controls.md:308`: “`_verify_note_for_completion` returns the verified note, so there is no second decrypt.”
  - `.cursor/plans/plan-privacy-professional-controls.md:321`: “Mock sessions — the note's provider starts with `mock-`, or the transcript's `model_name` identifies the mock backend: nothing is kept, and the row reads `not_kept_mock`.”
- Evidence:
  - `desktop/src/scribe_desktop/session.py:1116`: `complete_session(live.directory, live.crypto, delete_note=True)`
  - `desktop/src/scribe_desktop/session_store.py:728–730`:
    ```python
    if delete_note:
        try:
            (session_dir / NOTE_FILENAME).unlink(missing_ok=True)
    ```
  - `desktop/src/scribe_desktop/session_store.py:692–693`:
    ```python
    except FileNotFoundError:
        return
    ```
  - `desktop/src/scribe_desktop/session_store.py:744`: `_verify_note_for_completion(session_dir, crypto, transcript_plain)`
  - `desktop/src/scribe_desktop/draft_write.py:1115`: `return note.provider_name.startswith(_MOCK_PROVIDER_PREFIX)`
- Suggested change: Specify how mock identity and required metadata are captured before the note is unlinked, including retry after interruption. Preserve the explicit delete-unreadable-note escape with a defined unknown-provenance policy. Test a real transcript plus mock-provider note through both delete-note paths.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:728-730 unlinks note.enc before the 744 verification). D6: on the delete-note paths the saved note's provenance is read before the unlink; mock = any of the transcript model_name, generated.enc provider, saved-note provider; an unreadable note records note_provenance=unknown (new D8 field) and the decision falls to the other discriminators; Task 2.3 and Validation updated.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Missing verification / rollback / migration

**PR-MED-004 — The required artifact matrix rejects valid transcript-only and legacy adopted sessions**

- Plan section: D1, D2, D6; migration statement; Task 2.3.
- Materiality: build-affecting
- Why it matters: Normal Complete already permits a transcript without a generated or saved note. Adopted pre-upgrade sessions also use normal Complete but cannot contain the new `generated.enc`. Requiring D6’s complete artifact set therefore blocks valid completion. The opposite omission exists in the recovered row: it excludes `generated.enc` even when recovery finds one, losing an available artifact promised by the goal.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:291`: “requires the expected artifact set for the path (D6);”
  - `.cursor/plans/plan-privacy-professional-controls.md:318`: “Normal Complete and `complete_after_write`: generated + saved note + transcript.”
  - `.cursor/plans/plan-privacy-professional-controls.md:320`: “`complete_recovered`: transcript (+ saved note if present).”
  - `.cursor/plans/plan-privacy-professional-controls.md:302`: “Recovered sessions without it show "Generated note not kept".”
- Evidence:
  - `desktop/src/scribe_desktop/ui/models.py:2082–2083`:
    ```python
    if not state.has_note:
        return None
    ```
  - `desktop/src/scribe_desktop/session.py:1236–1239`:
    ```text
    reinstall a RETIRED session (one a Start or crash left on disk with a
    transcript) as THE live QUEUED session, so the review, the lease,
    ``with_generation_custody``, Save and Complete are the live path that
    exists. Returns the session and ``reader(directory, crypto)``'s value
    ```
  - `desktop/src/scribe_desktop/session.py:1048`: `complete_session(live.directory, live.crypto)  # raises -> stays queued`
- Suggested change: Define expected artifacts by actual generation/save history and legacy availability, as well as completion intent. Preserve generated artifacts on recovered completion when present. Test normal transcript-only Complete, an adopted pre-upgrade saved session without `generated.enc`, and recovered completion with an existing generated artifact.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session.py:1048 normal Complete accepts a transcript without a note; adopted pre-upgrade sessions have no generated.enc). D6 replaced the per-path matrix with the SOURCE-DERIVED set (transcript always; generated.enc whenever present incl. complete_recovered; note.enc when present and not deleted); D1 step 2 and Schema reconciled; tests for transcript-only, adopted pre-upgrade and recovered-with-generated added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Unstated assumptions

**PR-MED-005 — Historical prose model and prompt versions are unavailable at Complete**

- Plan section: D2, D4, D8; Tasks 1.3 and 2.1.
- Materiality: build-affecting
- Why it matters: A saved prose note can survive a restart or application update before Complete. Neither the existing saved note nor the proposed generated artifact records its language-model and prompt identifiers. Current constants at Complete would misattribute an older note; leaving the fields unpopulated does not deliver the promised provenance.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:335`: “`models`: transcription model, speaker model id, note provider, note schema version, template profile, style, language model id, prompt version;”
  - `.cursor/plans/plan-privacy-professional-controls.md:309`: “`complete_session` returns a new content-free `CompletionFacts` (model ids, note provider and style, and the past-session outcome).”
  - `.cursor/plans/plan-privacy-professional-controls.md:299`: “It holds `{session_id, created_at, provider_name, style, text}`, where `text` is the first `format_note_body` output shown to the practitioner, before any review action.”
- Evidence:
  - `desktop/src/scribe_desktop/note.py:683–684`:
    ```python
    template_profile_id: str = Field(pattern=_PROFILE_ID_PATTERN)
    provider_name: str = Field(min_length=1, max_length=64)
    ```
  - `desktop/src/scribe_desktop/note.py:694–695`:
    ```python
    style: NoteStyle = "verbatim"
    style_renderings: tuple[StyleRendering, ...] = ()
    ```
  - The persisted rendering fields at `desktop/src/scribe_desktop/note.py:658–661` are:
    ```python
    section_key: NoteSectionKey
    prose_text: str = Field(max_length=MAX_SECTION_PROSE_CHARS)
    input_digest: str
    verdict: StyleVerdict
    ```
  - These artifacts contain no language-model or prompt-version field.
- Suggested change: Capture exact identifiers when rendering occurs and persist them with a binding to the saved note. Complete must consume recorded provenance. Define unavailable provenance for legacy artifacts and no-prose paths. Test render → restart/version change → adopted or recovered Complete.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (note.py:658-661, 683-695: no LM or prompt field persisted). D2: generated.enc also holds language_model_id / prompt_version captured at render time; D8: the saved note's LM/prompt ids are recorded by a best-effort audit update at Save (renderings persist only at Save, in the rendering process); Complete never fills them from current constants; legacy = unknown; no GeneratedNote schema change; Task 1.3/2.1 and a render-restart-Complete test added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Coverage

**PR-MED-006 — The WER check can clear its warning for an uncovered supported launch**

- Plan section: D10; Tasks 4.1–4.2; P.3.
- Materiality: build-affecting
- Why it matters: The documented console launch runs the app in `python.exe`, while the planned exclusions cover `pythonw.exe` and the two launchers. Registration can therefore pass every proposed check while the running process holding clinical plaintext remains uncovered. Python exception hooks do not address native crashes. The agreed “set + warn” decision can be preserved by warning about that launch.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:343`: “The WER exclusions are written by `winreg` in `register-native-host.py` (DWORD 1 each for `pythonw.exe`, `scribe-app.exe`, `scribe-host.exe`), verified by read-back, and removed by `--unregister`.”
  - `.cursor/plans/plan-privacy-professional-controls.md:443`: “**P.3** Re-run `register-native-host.py`: the three WER values exist under HKCU and the startup warning clears.”
- Evidence:
  - `AGENTS.md:45`: “**Launching the desktop app:** double-click `.venv\Scripts\scribe-app.exe` in Explorer, or run it from a PERSISTENT terminal (`.venv\Scripts\python.exe -m scribe_desktop.app` keeps console output).”
  - `desktop/pyproject.toml:61`: `# gui-scripts (not scripts): pip generates pythonw-backed .exe launchers, so`
  - `desktop/pyproject.toml:64`: `scribe-app = "scribe_desktop.app:main"`
- Suggested change: Make `check_wer` account for the actual interpreter executable. Keep the agreed exclusions and show a fixed warning for an uncovered interpreter such as `python.exe`. Add injected GUI/console launch tests and make P.3’s warning clearance conditional on coverage of the running executable.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (AGENTS.md console launch uses python.exe; exclusions name pythonw.exe and the launchers). D10: check_wer also checks the running interpreter (injected sys.executable) and shows a fixed uncovered-launch warning for python.exe (breadth kept as agreed); Task 4.1, P.3 and Validation updated.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

PEER-PLAN-ROUND-2 RESULT: 6 findings (CRIT 0 / HIGH 0 / MED 6 / LOW 0; build-affecting 6 / record-only 0 / invalid 0).

### Round 3 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 3)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the peer's stdout; read-only sandbox)
- Materiality: 4 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: bdf7eed + working-tree plan
- Files read:
  - Full `.cursor/plans/plan-privacy-professional-controls.md` and `.agents/skills/peer-review/SKILL.md`; scoped context in `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `desktop/src/scribe_desktop/`: `session_store.py`, `session.py`, `transcription.py`, `note.py`, `encounter.py`, `clinics.py`, `draft_write.py`, `logging_setup.py`, `practitioner_profile.py`, `secure_storage.py`, `note_config.py`, and `app.py`; source-key destruction paths including `speaker_eval.py`.
  - Requested regions in `ui/main_window.py`, `ui/transcript.py`, `ui/bridge.py`, `ui/models.py`, `ui/note.py`, `ui/recovery.py`, and `ui/session_screen.py`.
  - `scripts/register-native-host.py`; relevant `desktop/pyproject.toml` sections; scoped regions in `test_session_store.py`, `test_session_machine.py`, `test_ui_screens.py`, `test_display_name.py`, `test_session_types.py`, `test_cliniko_client.py`, `test_integration_no_sockets.py`, and `test_setup_scripts.py`.
  - Cited portions of the retention schedule, threat model, data-flow map, intended-use statement, incident process, and design system.
- Finding verification: 11 candidates / 7 dropped / 0 downgraded. Duplicate candidates consolidated. Dropped candidates were covered by existing constraints, unreachable through the shipped UI, or insufficiently evidenced.
- Review was static and read-only. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-001 — Dead-key garbage collection bypasses the pending-entry removal rule**

- Plan section: C1, Flow 4, Tasks 2.2–2.3.
- Materiality: build-affecting
- Why it matters: The actual `orphan_gc` branch handles both absent keys and existing zero-length/truncated keys. Suppose Complete publishes a pending archive, but source-key deletion fails or is interrupted. If that remaining key subsequently becomes truncated, the sweep deletes it without the proposed expiry-only callback. Reconciliation then commits the archive even though Complete never successfully deleted the source key. This breaks C1’s load-bearing inference.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:383`: “It handles a keyless source directory and deletes nothing in the archive: the key was already gone, so the entry commits.”
  - `.cursor/plans/plan-privacy-professional-controls.md:877`: “`sweep_sessions` gains a `before_destroy(session_id)` callback invoked before an `expired` key deletion.”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:1139`: `key_blob_size = key_path.stat().st_size`
  - `desktop/src/scribe_desktop/session_store.py:1142`:
    ```python
    if key_blob_is_dead(key_blob_size):
        # Orphan or cryptographically-dead custody: GC.
        delete_session_key(child)
        shutil.rmtree(child, ignore_errors=True)
        action = "orphan_gc"
    ```
- Suggested change: Distinguish confirmed key absence from an existing dead key. Only confirmed absence can support the existing reconciliation inference. Before garbage-collecting an existing dead key, remove its pending archive through the same ordering used for expiry. Test pending archives with zero-length/truncated source keys, including failure of pending-entry removal; an inaccessible key must not count as absent.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:1139-1146: orphan_gc covers an existing dead key as well as an absent one). C1's orphan_gc bullet split: confirmed-absent key commits; an existing dead key is a destroyer (before_destroy removes the pending entry first; a failed removal keeps the dead key this tick); an inaccessible key is neither; reconcile_pending commits only on confirmed absence. Task 2.3's before_destroy now covers dead-key orphan_gc; tests added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-002 — Delete-note completion loses its provenance on a later failure**

- Plan section: D6, C1, Task 2.3.
- Materiality: build-affecting
- Why it matters: Reading provenance before unlink protects only that attempt. Transcript verification, archive creation, or source-key deletion can subsequently fail after `note.enc` has gone. A retry cannot reread it. For the explicitly supported legacy case of a real transcript plus a mock-provider saved note without `generated.enc`, a source-key deletion failure loses the only mock discriminator; retry can then archive a session that should keep nothing. Ordinary saved-note provenance is likewise lost.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:320`: “It is re-read on a retry because the note is not yet gone, since the unlink follows the read.”
  - `.cursor/plans/plan-privacy-professional-controls.md:319`: “A session is mock when ANY discriminator says so: the transcript's `model_name` identifies the mock backend; `generated.enc`'s `provider_name` starts with `mock-`; or the saved note's `provider_name` does.”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:728`:
    ```python
    if delete_note:
        try:
            (session_dir / NOTE_FILENAME).unlink(missing_ok=True)
    ```
  - Later verification can refuse at `desktop/src/scribe_desktop/session_store.py:738`:
    ```python
    except OSError as exc:
        raise StoreWriteError(f"transcript not durably readable: {exc}") from exc
    ```
  - Source-key deletion occurs afterward at `desktop/src/scribe_desktop/session_store.py:745`: `delete_session_key(session_dir)`
  - Its fallible operation is `desktop/src/scribe_desktop/session_store.py:625`: `(session_dir / KEY_FILENAME).unlink(missing_ok=True)`
- Suggested change: Preserve the provenance source across every retryable failure. Since completion now removes the entire source directory, the simpler option is to exclude the explicitly deleted note from verification/archive inclusion while retaining its source file until source-key destruction. Otherwise persist retry-safe provenance. Test both delete-note paths with failure after the current unlink point, followed by retry and restart, including the saved-note-only mock discriminator.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session_store.py:728 unlinks note.enc before the 738/745 fallible steps). D6: the early unlink is removed; delete_note=True excludes the note from verification and the archive, note.enc stays until the key is deleted and the directory removed, and its provenance is read on every attempt (unreadable -> note_provenance=unknown; the escape is kept). Task 2.3 and a fail-after-unlink-point retry/restart test updated.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

**PR-MED-003 — Marker-removal failure has no safe post-deletion outcome**

- Plan section: Flow 3, C1, Task 2.3, completion verification.
- Materiality: build-affecting
- Why it matters: The amendment adds a fallible filesystem operation immediately after irreversible source-key deletion, while retaining the blanket promise that archive failures keep the key and QUEUED state. If marker removal raises at that position, the existing completion primitive can exit before destroying its in-memory key, and its callers retain the queued session. The UI then reports that this action performed no key deletion. Restart reconciliation does not define safe handling of this same-process failure.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:257`: “Right after `delete_session_key`, Complete commits it by removing the marker; if that is interrupted, startup and sweep reconciliation commits it (C1).”
  - `.cursor/plans/plan-privacy-professional-controls.md:377`: “Any archive failure keeps the key and the QUEUED state, and allows a retry.”
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:745`: `delete_session_key(session_dir)`
  - `desktop/src/scribe_desktop/session_store.py:749`: `crypto.destroy()`
  - `desktop/src/scribe_desktop/session.py:1048`:
    ```python
    complete_session(live.directory, live.crypto)  # raises -> stays queued
    self._transition_locked(live, SessionState.WRITTEN)
    session = live.session
    self._live = None
    ```
  - `desktop/src/scribe_desktop/ui/transcript.py:1023`: `"No key deletion was performed by this action; if the "`
- Suggested change: Define source-key deletion as the irreversible boundary. After it succeeds, guarantee in-memory key destruction and the terminal controller transition. Treat marker-removal failure as deferred reconciliation, with truthful status, rather than a retryable pre-deletion failure. Add failure injection specifically at marker removal and verify all five Complete paths, including lease/reservation release and eventual reconciliation.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session.py:1048 treats any complete_session raise as stays-queued; transcript.py:1023 says no key deletion). Flow 3 step 4 makes delete_session_key the irreversible boundary: afterwards the in-memory key is always destroyed and the terminal transition always happens; marker/directory removal are best-effort post-boundary steps left to reconciliation/orphan_gc with a truthful status; C1 ordering, Flow 3 failure line and Task 2.3 (CompletionFacts.commit_deferred) reconciled; failure injection at marker removal across all five paths added.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Unstated assumptions

**PR-MED-004 — Best-effort Save provenance can silently describe an older saved note**

- Plan section: D8, C2, Task 1.3.
- Materiality: build-affecting
- Why it matters: Save A can successfully record its rendering identifiers. After restart with changed model/prompt versions, regeneration and Save B can succeed while the best-effort audit update fails. A later successful Complete update has no binding with which to distinguish A’s identifiers from B’s. This produces incorrect provenance, rather than an explicitly unavailable value. `generated.enc` cannot substitute reliably because regeneration replaces it before the replacement saved note is committed.
- Current plan text:
  - `.cursor/plans/plan-privacy-professional-controls.md:337`: “The saved note's LM id and prompt version are recorded by a best-effort audit update at SAVE (`TranscriptScreen.save_note`).”
  - `.cursor/plans/plan-privacy-professional-controls.md:341`: “There is no `GeneratedNote` schema change.”
  - `.cursor/plans/plan-privacy-professional-controls.md:386`: “Every other audit update is best-effort and never raises into a write, Complete, Discard or sweep.”
- Evidence:
  - `desktop/src/scribe_desktop/ui/transcript.py:850`:
    ```python
    controller.with_generation_custody(
        lease, lambda directory, crypto: write_note(directory, crypto, note, config)
    )
    self._note_committed = True  # note.enc is on disk (round 36 PR-MED-002)
    self._release_lease()
    ```
  - `desktop/src/scribe_desktop/note.py:688`:
    ```python
    transcript_digest: str
    config_digest: str
    note_sections: tuple[GeneratedSection, ...] = ()
    note_warnings: tuple[NoteWarning, ...] = ()
    # Schema v2 (D7): the writing style the note was rendered under and its
    # per-section prose. The defaults ARE the v1 shape.
    style: NoteStyle = "verbatim"
    style_renderings: tuple[StyleRendering, ...] = ()
    ```
  - The reopened-note contract at `desktop/src/scribe_desktop/ui/note.py:766` states:
    ```text
    ``session_store.read_note`` verified. Read-only: changing it means
    Regenerate on the Transcript screen, which replaces it only on that
    review's Save. Copy follows the recorded flag (``_copy_ready``);
    ```
- Suggested change: Bind the audit’s saved-note provenance to the exact persisted saved-note digest. At Complete, use those identifiers only when the digest matches; otherwise record `unknown`. Keep audit updates nonblocking. Test successful Save A → restart/version change → successful Save B with failed audit update → Complete.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (note.py:688-695 and transcript.py:850: no provenance binding to the saved note). D8: the saved note's LM/prompt ids go into a new session file saved-provenance.enc written in the SAME with_generation_custody action as note.enc, carrying the note plaintext digest; Complete uses the ids only on a digest match, else unknown; the digest never leaves the session; the Save-time audit update is removed. Schema, Tasks 1.3/2.1 and a Save A -> restart -> Save B -> Complete test updated.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

PEER-PLAN-ROUND-3 RESULT: 4 findings (CRIT 0 / HIGH 0 / MED 4 / LOW 0; build-affecting 4 / record-only 0 / invalid 0).

### Round 4 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 4)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the peer's stdout; read-only sandbox)
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: bdf7eed + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; working-tree plan, including current round 1–3 amendment notes; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `session_store.py`, `session.py`, `transcription.py`, `note.py`, `encounter.py`, `clinics.py`, `draft_write.py`, `logging_setup.py`, `practitioner_profile.py`, `secure_storage.py`, `note_config.py`, and `app.py`.
  - Named UI regions in `main_window.py`, `transcript.py`, `bridge.py`, `models.py`, `note.py`, `recovery.py`, and `session_screen.py`.
  - `scripts/register-native-host.py`, relevant `desktop/pyproject.toml` sections, and requested test regions.
  - Cited portions of the retention schedule, threat model, data-flow map, intended-use statement, incident process, and design system.
- Finding verification: 11 candidates / 9 dropped / 0 downgraded.
- Static review only. No files changed; no tests or builds run.

#### Findings

##### Practicality / feasibility / sequencing

**PR-MED-001 — Define the two-file Save commit boundary**

- Plan section: D8; Task 2.1.
- Materiality: build-affecting
- Why it matters: One custody action does not make two file replacements atomic. If `note.enc` is replaced successfully and the subsequent provenance write fails, both UI layers treat Save as unsuccessful despite the durable saved note. Cancelling review then clears the review state while `_note_committed` remains false, recreating the disk-versus-UI disagreement that the existing code explicitly prevents. The digest check protects provenance accuracy at Complete, but does not resolve this partial Save.
- Current plan text: `.cursor/plans/plan-privacy-professional-controls.md:337`:
  > It is written inside the SAME `with_generation_custody` action as `note.enc` (`ui/transcript.py:850`), and carries the SHA-256 of the saved note's plaintext.
- Evidence:
  - `desktop/src/scribe_desktop/session_store.py:885`:
    ```python
    atomic_write_bytes(note_path, crypto.encrypt(note.to_bytes()), error_label="note artifact")
    ```
  - `desktop/src/scribe_desktop/ui/transcript.py:850`:
    ```python
    controller.with_generation_custody(
        lease, lambda directory, crypto: write_note(directory, crypto, note, config)
    )
    self._note_committed = True  # note.enc is on disk (round 36 PR-MED-002)
    self._release_lease()
    ```
  - `desktop/src/scribe_desktop/ui/note.py:1999`:
    ```python
    self.message_label.setText(f"Save failed: {models.custody_refusal_text(exc)}")
    return
    self._note_saved = True
    ```
    The final assignment is outside the exception branch; a raised provenance write bypasses it.
  - `desktop/src/scribe_desktop/ui/transcript.py:610`:
    ```python
    # on disk (`_note_committed`) counts as a note even when the current
    # in-memory review was cancelled — so has_note agrees with disk and
    # "no note" is asserted only when no note.enc exists. A committed note
    ```
- Suggested change: Specify provenance-first ordering, using the digest of the exact canonical note bytes, with `note.enc` replacement as the Save commit boundary. Alternatively, make provenance failure after note commit nonblocking and report unknown provenance. Inject failures at both replacements and verify saved flags, lease handling, Cancel review, Complete controls, retry and reopen agree with durable state.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (ui/transcript.py:850-852: _note_committed is set only after the custody action returns; a raise after note.enc landed would leave disk and UI disagreeing). D8: saved-provenance.enc is written FIRST with the digest of the exact canonical note bytes; note.enc's replacement stays the Save commit boundary; a stray provenance file only ever yields unknown at Complete; Task 2.1 tests inject failures at both writes and check the saved flags, lease, Cancel review, retry and reopen.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

##### Missing verification / rollback / migration

**PR-LOW-002 — Audit reset needs a collision-safe destination**

- Plan section: D9; Task 1.2; audit verification.
- Materiality: build-affecting
- Why it matters: Two unreadable-key resets on the same date target the same quarantine directory. Preserving the first directory makes the second rename fail and leaves recording blocked. Replacing that directory would violate the promise to preserve the earlier audit record. The reset contract needs an explicit no-overwrite naming rule.
- Current plan text: `.cursor/plans/plan-privacy-professional-controls.md:349`:
  > It renames `audit\` to `audit.unreadable-<date>\` (nothing is deleted) and creates a fresh key.
- Evidence:
  - `.cursor/plans/plan-privacy-professional-controls.md:349`:
    > Starts are refused, and the Past sessions tab offers "Start a new audit record".
  - `.cursor/plans/plan-privacy-professional-controls.md:426`:
    > `test_audit.py`: round trip; wrong description or AAD refused; newer row untouched; unreadable row never overwritten; month prune at the 7-year boundary; CSV formula guard; `update` never raises.
  - The specified destination has no collision discriminator, and the verification list contains no repeated-reset or interrupted-reset case.
- Suggested change: Reserve a unique destination without overwriting any existing quarantine directory, using a date plus collision-safe suffix. Test two resets on one date and failure creating the replacement key after rename followed by retry; both earlier records must remain untouched.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (the plan's D9 destination had no collision discriminator). D9: the reset renames to a never-existing audit.unreadable-<YYYYMMDD-HHMMSS>-<8 hex> and never overwrites or reuses a quarantine directory; a key-creation failure after the rename is retried by the next reset or Start; test_audit covers two same-day resets and the retry.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

PEER-PLAN-ROUND-4 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1; build-affecting 2 / record-only 0 / invalid 0).

### Round 5 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 5)

- Round status: Closed
- Source: Codex plan peer-review
- Recorded by: composer (transcribed verbatim from the peer's stdout; read-only sandbox)
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: bdf7eed + working-tree plan
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; working-tree plan, including current amendment notes; scoped `AGENTS.md`, `PLAN.md`, and `docs/lessons.md`.
  - Named symbols in `session_store.py`, `session.py`, `transcription.py`, `note.py`, `encounter.py`, `clinics.py`, `draft_write.py`, `logging_setup.py`, `practitioner_profile.py`, `secure_storage.py`, `note_config.py`, and `app.py`.
  - Scoped UI symbols, registration script, `desktop/pyproject.toml`, named test regions, and cited security/design documentation.
- Finding verification: 6 candidates / 5 dropped / 0 downgraded
- Review was static and read-only; no tests or builds run.

#### Findings

##### Missing verification / rollback / migration

**PR-LOW-001 — Directory-creation failure cannot preserve the installed previous session under the specified ordering**

- Plan section: Validation / Verification, round-2 tests; Flow 1; Task 1.3.
- Materiality: build-affecting
- Why it matters: The required directory-creation failure assertion contradicts the planned Start ordering. Retirement has already destroyed the previous in-memory key and cleared `_live` before directory creation runs. Its files remain recoverable, but the session is no longer installed. Making the stated test pass would require an additional reorder or rollback absent from the implementation contract.
- Current plan text: `.cursor/plans/plan-privacy-professional-controls.md:443`:
  > - Start failing at the retire refusal and at directory creation (the row reads `start_failed`; the previous session stays installed);
- Evidence:
  - `.cursor/plans/plan-privacy-professional-controls.md:245`:
    > 4. The previous session is retired, the key is wrapped, and `encounter.enc` is written.
  - `desktop/src/scribe_desktop/session.py:759`:
    ```python
    self._retire_locked(live)
    ```
  - Directory creation follows at `desktop/src/scribe_desktop/session.py:766`:
    ```python
    directory.mkdir(parents=True, exist_ok=True)
    ```
  - Retirement clears the installed session at `desktop/src/scribe_desktop/session.py:1890`:
    ```python
    live.crypto.destroy()  # in-memory copy only; key.dpapi (if any) remains
    self._live = None
    ```
- Suggested change: Split the validation cases. Retirement refusal must preserve the installed previous session. Directory-creation failure must record `start_failed` and preserve the previous session’s recoverable files and reminder tracking. Keep the installed-session guarantee for `AuditLog.begin` failure.
- /fix decision: Applied (plan amended by the owning planning session, /review-plan-style; landed + siblings reconciled)
- /fix notes: Verified (session.py:759 retires and 1890 clears _live before the 766 mkdir). Validation split: the retire refusal keeps the previous session INSTALLED; a directory-creation failure (after the retire) records start_failed and keeps the previous session's files recoverable and in the Unreviewed index; the installed guarantee is scoped to the begin failure and the retire refusal. Flow 1 step 5 already scoped it correctly (sibling checked).
- /fix date: 2026-10-01
- /fix applied by: Claude Code

PEER-PLAN-ROUND-5 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1; build-affecting 1 / record-only 0 / invalid 0).

### Round 6 - 2026-10-01 - Phase 1 (Tasks 1.1–1.4) code review, /review-loop round 1 of 3 (stage-1 executor, in-session)

- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a two-lens subagent fan-out — correctness/security and plan-deviation/judgment/structure — merged, deduped and verified in the executor session)
- Primary review baseline: HEAD `1e564b4` (the plan commit; Phase 1 is the whole uncommitted tree diff)
- Changed files: `desktop/src/scribe_desktop/{audit.py (new), app.py, logging_setup.py, session.py, session_store.py, ui/main_window.py, ui/recovery.py}`; tests `desktop/tests/{test_audit.py (new), test_display_name.py, test_hands_free.py, test_integration_no_sockets.py, test_live_session.py, test_note_pipeline.py, test_session_machine.py, test_session_store.py, test_transcription.py, test_ui_encounter.py, test_ui_screens.py}`; the plan's own records
- Named targets checked: C1 seams for Task 2.3 (clean — no half-built pending-entry logic; `past_session` always `none`; `write_saved_provenance` has no production caller; the delete-note early unlink is Task 2.3's to remove, D6); C2 (only `begin` refuses — gaps MED-001 and LOW-001/LOW-002); C3 as a derived surface (the schema walk holds; the new tripwire signatures are no substring of an `ALLOWED_KEYS` rendering); C5 (every audit call is on the GUI thread — the sweep `QTimer`, the button slots, the `TaskThread` result slots; nothing on `_on_capture_failure`); the five Complete paths, `discard()` (both paths), `discard_recovered`, `ui/recovery.py` `_discard` and `run_sweep` (each records once, after the custody action, never on failure); D9 (MED-001's second site)
- Finding verification: 21 candidates; 3 dropped (the refusal text naming a tab that lands in Task 3.1 of this run — plan-decided wording, noted in the handoff; the five Complete paths' repeated three lines — the `_audit_*` helpers already exist and Task 2.3 edits each site anyway; the delete-note retry losing the note's provenance — Task 2.3 owns D6's removal of the early unlink); 5 merged as duplicates across the two lenses; 1 downgraded (the saved-note digest, MED → LOW: a mismatch only reads `unknown`)
- Missed-issue pass: re-read `audit.py` (whole), `session.py` `start` / `_start_locked` / the five Complete paths / `discard` / `discard_recovered`, `session_store.py` `complete_session` / `_completion_facts` / `sweep_sessions` / `session_created_at`, `main_window.py` `_prepare_attempt` / `_store_write_record`, `recovery.py` `_discard`, `app.py` `main`; result: LOW-009, LOW-012

#### MED-001 — A Windows key-wrap failure escapes the audit's error handling (Start shows the unauthored line; D9's reset leaks a raw error)
- File: `desktop/src/scribe_desktop/audit.py:824` (`_open_key`) and `:699` (`reset`) — `except (OSError, StoreWriteError, RuntimeError):` around `wrap_key_to_file`
- Triage: Fix-now · Fix route: fix-on-fast
- Why it matters: `wrap_key_to_file` calls `win32crypt.CryptProtectData` (`session_store.py:592`), which raises `pywintypes.error` — not OSError-rooted (the repo's own comment, `session_store.py:619`). Start is still refused (fail-closed), but the Session screen then shows `CUSTODY_UNEXPECTED_REASON` instead of D12's authored line and the fresh key object is not destroyed; `reset` raises the raw error AFTER the rename instead of `AuditResetError`, skipping its empty-folder cleanup (D9).
- Current behaviour: only OSError / StoreWriteError / RuntimeError become `AuditUnavailable("write_failed")` / `AuditResetError`.
- Desired behaviour: ANY failure creating the key becomes the authored error, with the in-memory key destroyed and (reset) the empty folder removed.
- Pattern siblings (grep `wrap_key_to_file\(` across `desktop/src`): `audit.py:698`, `audit.py:823` (both this finding); `session.py` `_start_locked` (under `except Exception` — fine); `practitioner_profile.py:378` (`try/finally` — fine). None found beyond the two.
- Verification: a test injecting a non-OSError from `wrap_key_to_file` into `begin` (→ `AuditWriteError("write_failed")`) and into `reset` (→ `AuditResetError`, the store root absent).
- /fix decision: Applied
- /fix notes: `audit.py` `reset` and `_open_key`: both key-wrap `except` clauses are now `except Exception` (noqa BLE001, naming pywintypes.error); the in-memory key is destroyed and the empty folder removed as before. Siblings: both sites (none beyond). Test `test_audit.py::TestReset::test_a_dpapi_failure_is_the_authored_error_everywhere` drives both exits with a non-OSError. ruff + mypy clean; pytest composer-run.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

#### MED-002 — `session_date` (and the month folder) is the UTC date, not the practitioner's calendar date
- File: `desktop/src/scribe_desktop/audit.py:475` (`session_date=started_at.astimezone(UTC).date()`), `:331` (`_date_from_epoch`: `datetime.fromtimestamp(stamp, UTC).date()` / `now.date()`)
- Triage: Fix-now · Fix route: fix-on-fast
- Why it matters: at UTC+10/+11 every session before 10:00 (11:00 in daylight saving) is dated the previous day — on the 1st of a month in the previous month's folder — and the CSV's `session_date` column carries no zone. The Past sessions label (Phase 2) will show the local date, so the two stores would disagree. The plan's "kept 7 years from the session date" means the clinician's date; D8 leaves the zone open, and schema-v1 rows are about to become 7-year records.
- Current behaviour: the UTC calendar date.
- Desired behaviour: the LOCAL calendar date (system zone; injectable for tests), and the prune still keeps every row at least 7 years (a one-day margin on `month_prune_at` covers a local calendar that runs behind UTC).
- Pattern siblings (grep `astimezone\(UTC\)|fromtimestamp\(.*UTC\)|now\.date\(\)` in `audit.py`): 331, 475 (this finding); 678 (the quarantine stamp — a name, fine as UTC); 879 (CSV timestamps carry `+00:00` — fine).
- Verification: an injected +10:00 zone dates an 08:00-local session on 1 Oct (22:00 UTC on 30 Sep) `2026-10-01` in folder `2026-10`; the same for a `pre_audit` row's epoch and the fallback `now`; the prune boundary tests move by the margin.
- /fix decision: Applied
- /fix notes:
  - `audit.py`: `_local_date` is used by `begin` and `_date_from_epoch`. `AuditLog(local_zone=None)` means the system zone; tests inject one. `month_prune_at` adds `_PRUNE_MARGIN` (one day), and the `AuditRow.session_date` comment and the module layout note say "local".
  - Tests: `test_audit.py`'s `_log` pins UTC, so every existing expectation stays deterministic. New `TestLocalDate` has three cases: an AEST morning session, the `pre_audit` epoch and its fallback, and the system-zone default. The prune boundaries moved by the day. `test_session_machine.py`'s upgrade test now expects the local date.
  - The residue is recorded in Task 5.2's list.
  - Executor's call (auto-disposable, MED, non-production), not a practitioner decision: the plan's "7 years from the session date" means the clinician's date, and D8 left the zone open.
  - ruff + mypy clean; pytest is composer-run.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

- **[LOW]** LOW-001: `audit.py:360-373` — `_completed` builds `AuditModels` EAGERLY, outside `update`'s guard (a fact that fails its token pattern would raise out of `record_completion` AFTER the key is gone, so the screen would claim "No key deletion was performed"), and the facts→models mapping is a hand-copied 12-field list that silently drops any fact Tasks 2.1/2.3 add — build the models inside the change from `AuditModels.model_fields`, and pin that every model field is a `CompletionFacts` field — Triage: Fix-now; Decision: Applied (`_completed` builds `AuditModels` inside the change from `AuditModels.model_fields` by name; tests `test_a_fact_the_row_refuses_is_counted_never_raised` and `test_every_model_field_is_a_completion_fact`)
- **[LOW]** LOW-002: `session_store.py:1305` / `ui/recovery.py:459-463` / `session_store.py:1387` — `session_created_at`'s `audio_path.exists()` re-raises a non-ENOENT `OSError` on Python 3.12 (a CI leg), so the recovery list's unguarded read can block a Discard for the audit's sake (C2) and the sweep's new pre-GC read can turn an `orphan_gc` into `error` — make the read itself never raise an OSError (the header read already sits in its own `try`) and guard the recovery screen's read like the controller's `_audit_created_at`. Siblings (grep `session_created_at\(`): `session.py` `_audit_created_at` (guarded), `session_store.py:1337` `session_expires_at` (fixed with the source) — Triage: Fix-now; Decision: Applied (`session_created_at` drops the `exists()` pre-check — the header read's own `try` catches FileNotFoundError; `recovery.py` `_discard` guards its read → None; tests `test_session_store.py::test_an_unreadable_header_never_raises` and the recovery Discard case with a raising date read)
- **[LOW]** LOW-003: `ui/session_screen.py:330` + `ui/models.py:1233` — D12's refusal shows as "Start failed: AuditWriteError: the audit record could not be saved (…). Nothing was recorded." (the shared `custody_refusal_text` convention adds the type name; no pin) — pin the exact line and note the type name for smoke P.4 — Triage: Fix-now; Decision: Applied (the shared convention kept — no special case; `test_audit.py::test_the_start_refusal_line_as_the_session_screen_shows_it` pins the full line; P.4's expected line noted in the handoff)
- **[LOW]** LOW-004: `audit.py:104,112` — the Cliniko-id and clinic-id patterns are copies of `encounter.py:87-88` (as `clinics.py:131-132` already copies them); a drift would refuse every linked Start as "the audit folder could not be written" — add a derived equality pin — Triage: Fix-now; Decision: Applied (`test_the_id_patterns_are_the_encounters` compares both with `encounter`'s)
- **[LOW]** LOW-005: `session_store.py` `_completion_facts` — the saved-provenance match hashes a RE-SERIALISED note (`note.to_bytes()`), a second digest definition beside `saved_note_identity`'s plaintext hash; a schema default added between Save and Complete would silently read `unknown` — hash the decrypted plaintext the verification already holds — Triage: Fix-now; Decision: Applied (`_verified_note_with_identity` is the one core, `_verified_note` its note-only wrapper for `read_note`; `_CompletedNote(note, identity)` from both the verified and the delete-note reads; test `test_the_match_is_the_saved_plaintexts_identity` on both paths with plaintext ≠ re-serialisation. Leg a4: the composer's run showed `test_read_and_complete_share_the_verification_core` spying on the old core's NAME. The invariant still holds: `read_note` reaches `_verified_note_with_identity` through the wrapper, and Complete reaches it directly. So the spy was re-pointed at the core, with no source change)
- **[LOW]** LOW-006: `ui/main_window.py:1941-1946` — a Cliniko-side refusal (`WriteRecord.refusal`, a fixed `SendRefusal` code) is not recorded, so a row can read `last_outcome=refused` with no code, or an older pre-send code — pass the code with the transition — Triage: Fix-now; Decision: Applied (`record_write(refusal=)`, set as `last_refusal` on a `refused` transition, validated by `AuditWrite` inside the guard; `_store_write_record` passes `record.refusal`; tests in `test_audit.py` and the 403 slot test)
- **[LOW]** LOW-007: `ui/main_window.py:1861,1941` — a pre-upgrade session whose first audit touch is a write gets a `pre_audit` row dated the write day (no `created_at`), which the later Complete cannot re-date — read the session's creation time through the held write custody (best-effort) and pass it — Triage: Fix-now; Decision: Applied (`_store_write_record` reads it in the SAME custody hold as the store; the refusal branch through `_write_created_at` (guarded); the module helper `_audit_created_at` never raises; `record_write` / `record_write_refusal` take `created_at`; tests in `test_audit.py` and the slot test)
- **[LOW]** LOW-008: `session.py` `start` — a process kill between `begin`'s row and the session directory's creation leaves a row `pending` forever (nothing on disk for the sweep to end) — scope-expansion: Include in plan (a named residue in Task 5.2's security-doc rewrite; a startup scan decrypting every row to close a microsecond window is not proportionate) — Triage: Fix-now; Decision: Applied (headless gate, AUTO-DISPOSABLE — LOW, non-production, do-the-work: Include in plan — added to Task 5.2's named-residue list, with MED-002's local-date note)
- **[LOW]** LOW-009: `audit.py:322,626` — `month_prune_at` raises `ValueError` for a month folder dated 9993 or later, caught by the OUTER `except`, which ends the whole prune (later folders are skipped) — skip such a folder and carry on — Triage: Fix-now; Decision: Applied (`prune` computes `month_prune_at` per folder under its own `try`; test `test_a_folder_no_date_can_hold_is_skipped_not_fatal` — not counted as a failure)
- **[LOW]** LOW-010: `test_ui_encounter.py` `test_unknown_then_reconciled_written_then_complete_reads_written` — its "Complete" is a direct `record_completion` call, so the name overclaims — name what it proves (a completion record keeps the write fields) — Triage: Fix-now; Decision: Applied (renamed `test_unknown_then_reconciled_written_survives_the_completion_record`, docstring says the completion record is called directly; its result is now asserted)
- **[LOW]** LOW-011: `test_session_machine.py` `test_a_pre_audit_session_expiring_on_first_start_up_keeps_its_date` — the "never decrypted" guard patches two module attributes a from-import consumer could bypass — also refuse any SESSION-key unwrap (no `encounter.enc` can be decrypted without one) — Triage: Fix-now; Decision: Applied (`session_store.unwrap_key_from_file` patched to raise; the audit's own key goes through `audit.py`'s binding)
- **[LOW]** LOW-012: `app.py` `periodic_sweep` — the 24 h audit prune cadence is an inline closure with no test — extract it as a small injectable function and pin it — Triage: Fix-now; Decision: Applied (`app.prune_audit_if_due(audit, last_prune, now)`; test `test_the_audit_prune_runs_once_a_day_on_the_sweep_tick`)
- Fix-delta self-check: PASS — re-read the applied hunks across `audit.py`, `session_store.py`, `ui/main_window.py`, `ui/recovery.py`, `app.py` and the six test files (no neighbouring exit path changed: a failed `store.store` still raises out of `with_write_custody` before any audit call; no test pins `with_write_custody`'s call count or source text)
- Verification owed: the composer's full desktop pytest (verify=composer); ruff clean, mypy 52 files

### Round 7 - 2026-10-01 - Phase 1 (Tasks 1.1–1.4) code review, /review-loop round 2 of 3 (stage-1 executor, in-session)

- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a fresh two-lens subagent fan-out — correctness/security incl. the round-6 fixes adversarially, and plan-deviation/test-quality/structure — merged, deduped and verified in the executor session)
- Primary review baseline: HEAD `1e564b4` (the whole Phase 1 tree diff, round-6 fixes included); regression baseline: the round-6 pre-fix tree (the fixes named in round 6's notes)
- Changed files: as round 6
- Named targets: C1 seams (clean); C2 (only `begin` refuses — gap LOW-005's raw error class at `begin`'s own date computation); C3 derived (holds); C5 (holds — every audit call on the GUI thread); every Complete / Discard / sweep path (each records once after success; LOW-003's double-failure case); D9 (holds; LOW-010 on what offers it); the round-6 fixes: the local date (no path left on UTC; no DST or naive-time path in production), the +1-day prune (every row outlives 7 years after its local date in every zone UTC−12…UTC+14, per the correctness lens; the comment's arithmetic was wrong — LOW-002), the key-creation `except Exception` (wraps only mkdir + wrap; `AuditUnavailable` still propagates), the core rename (`read_note` verifies identically; the identity is `saved_note_identity`'s definition)
- Round classification: 7 ⚡ fix-induced (LOW-002, LOW-008, LOW-009, LOW-011, LOW-012, LOW-013, LOW-015 — docs, plan text and test strength around the round-6 fixes; none a behavioural regression) / 3 🔁 same-family (LOW-001 — the pre-send refusal's sibling site; LOW-005 and LOW-006 — MED-001's raw-error class at two more sites) / 7 🆕 (LOW-003, LOW-004, LOW-007, LOW-010, LOW-014, LOW-016, LOW-017)
- Finding verification: 19 candidates; 1 dropped (an optional spy on the key's destruction in the DPAPI test — the destroy path itself is unchanged by the fix); 2 merged (the "14 h" comment and the untrusted-finite header date were each raised by both lenses); 0 downgraded
- Missed-issue pass: re-read `ui/main_window.py` `_on_write_requested` (1740-1760) for every `WriteRefusal` producer, `audit.py` `_deleted` / `_completed` / `rows` / `_open_key`, `session_store.py` the three plaintext hashes; result: LOW-001 (confirmed at 1753-1757), LOW-003

- **[LOW]** LOW-001: `ui/main_window.py:1753-1757` — the EARLY pre-send refusals (`refuse_before_read`: `mock_note`, `record_unreadable`, `already_written`) end the click with no audit record; Flow 2's "a pre-send `WriteRefusal` records its fixed refusal code" covers them too (round 1 PR-MED-005's sibling site). Siblings (grep `WriteRefusal\)|write_refusal_line\(` in `ui/main_window.py`): these two sites only — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-002: `audit.py:102-103`, `:327-328` — the margin comment says a local month "can end up to 14 h after the UTC month"; the latest is 12 h (UTC−12; UTC+14's ends 14 h BEFORE). The one-day margin stays correct — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-003: `audit.py` `_deleted` / `_completed` — a row marked `start_failed` refuses every later end record, but a Start whose cleanup `discard_session` itself failed leaves a keyed, recoverable directory whose later Discard / expiry / recovered Complete is then never recorded (D6: "Complete, not the earlier failure, decides") — accept `start_failed` as well as `pending` as a row still open to its end — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-004: `audit.py:345-349` `_date_from_epoch` — any finite PAST epoch is trusted, so a corrupt or reset-clock header (`created_at=0.0`) dates a `pre_audit` row 1970-01, which the next prune deletes (no 7 years), and a very negative one makes `fromtimestamp` raise (a counted gap) — treat a time before the audit record existed (`_EARLIEST_SESSION`, 2026-01-01) as untrusted and fall back to now; a clock that is wrong at Start itself stays a named residue (Task 5.2) — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-005: `audit.py` `begin` — `_local_date(started_at, …)` runs in a `try` that catches only `ValidationError`, so an `OSError` / `OverflowError` from the local-time conversion escapes raw (MED-001's class) — catch them into `AuditWriteError("write_failed")` — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-006: `audit.py` `rows` — the row loop's `folder.iterdir()` can raise a raw `OSError` past the documented `AuditUnavailable` (Phase 3's tab and Export CSV) — map it — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-007: `audit.py` `_open_key` — a TRANSIENT key-read failure (antivirus or backup lock: `unwrap_key_from_file`'s `read_bytes` → `KeyCustodyError` caused by an `OSError`) reads as `key_unreadable`, so `key_unreadable()` would offer D9's reset over a passing lock — an `OSError`-caused custody error is `unavailable` — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-008: plan D7 / D8 — never amended for round 6 MED-002 (D7 still "END + 7 years"; D8's `session_date` names no zone) — amend both — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-009: plan Task 1.3 / smoke P.4 — the Start-refusal line is still written without the `AuditWriteError:` type name the screen shows (round 6 LOW-003) — amend both — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-010: `test_audit.py` `test_the_default_zone_is_this_computers` — at 07:30 UTC the host's local date equals the UTC date on any host from UTC−7:30 to UTC+16:30, so it would pass if `local_zone=None` were silently UTC — start at a local time whose UTC date differs (skip at offset 0) — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-011: `test_session_store.py` `test_an_unreadable_header_never_raises` — it would pass on the pre-fix code (the old `try` already caught the patched read); the defect was the `exists()` pre-check — make `Path.exists` raise too — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-012: `test_ui_encounter.py` 403 slot test — `isinstance(created, float)` does not show the value is the session's creation time (the fake's missing `write_dir` falls back to now) — give the fake a real directory with a known time and assert it — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-013: `session_store.py:700`, `:874`, `:1237` — the note identity (`sha256(plain)`) is written out three times though the docstring calls it one definition — one `_note_identity(plain)` — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-014: `session.py` `_audit_created_at`, `ui/main_window.py` `_audit_created_at`, `ui/recovery.py` `_discard` — three copies of "the creation time, or None, never raising" — one `session_store.audit_created_at(directory)` beside `session_created_at` — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-015: `session_store.py` `_verified_note` / `_verify_note_for_completion` — the wrapper still calls itself "THE single note-verification core" and line 708 still names "the shared `_verified_note` core" — correct both docstrings (the wrapper stays: `read_note` wants the note only) — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-016: `audit.py` refusal codes — `last_refusal` must match `_CODE_PATTERN`; `WriteRefusalName` and `SendRefusal` have no derived pin, so a future name outside it would fail every such record silently — pin both `Literal`s — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-017: `audit.py` `CSV_COLUMNS` — `models.*` / `write.*` are dotted but `deletion`, `deletion_at`, `past_session`, `past_session_at` are not; fix the convention before the first export exists (`deletion.state`, `deletion.at`, `past_session.state`, `past_session.at`) — Triage: Fix-now; Decision: Applied
- /fix notes (per finding; /fix date 2026-10-01; applied by Claude Code):
  - LOW-001: `ui/main_window.py` `_on_write_requested` records `early.name` through `record_write_refusal`, dated by `_write_created_at(reservation)`, before `reservation.release()`. `_write_created_at` now takes the reservation; both refusal sites use it. Test: `test_ui_encounter.py::test_an_early_refusal_records_its_code_too` (mock note).
  - LOW-002: both comments say 12 h (UTC−12).
  - LOW-003: `audit.py` `_still_open` — `start_failed` is open to a later Complete / Discard / expiry / orphan_gc, and a Start failure only ever ends a `pending` row. Test: `test_a_start_failure_still_takes_the_sessions_real_end` (three ends, and a second `start_failed` not overwriting).
  - LOW-004: `_EARLIEST_SESSION` (2026-01-01 UTC) — an earlier creation time is untrusted in `_date_from_epoch`, which also keeps a negative epoch away from `fromtimestamp`. Tests: three new `test_a_missing_or_untrusted_date_is_the_sweep_time` cases. The clock-wrong-at-Start residue joins Task 5.2's list.
  - LOW-005: `begin` catches `ValueError` / `OverflowError` / `OSError` into `AuditWriteError("write_failed")`. Test: `test_a_date_the_platform_cannot_convert_is_the_authored_refusal`.
  - LOW-006: `rows` maps a walk `OSError` to `AuditUnavailable("unavailable")`. Test: `test_a_folder_that_cannot_be_listed_is_the_documented_refusal` (`rows` and `export_csv`).
  - LOW-007: `_open_key` — a `KeyCustodyError` whose cause is an `OSError` is `unavailable`, never `key_unreadable`. Test: `test_a_key_that_cannot_be_read_right_now_is_not_unreadable` (no reset offered; Start works once released).
  - LOW-008: plan D7 (the margin) and D8 (`session_date` local) amended in place.
  - LOW-009: plan Task 1.3 and P.4 amended with the full screen line.
  - LOW-010: the default-zone test starts at a local time whose UTC date differs, and is skipped at a UTC host.
  - LOW-011: the header test also makes `Path.exists` raise, so the removed pre-check would fail it.
  - LOW-012: the 403 slot test gives the fake custody a real directory with a known mtime and asserts that exact value.
  - LOW-013: `session_store._note_identity(plaintext)` is used by the core, the delete-note read and `saved_note_identity`.
  - LOW-014: `session_store.audit_created_at(session_dir, now=None)`, never raising, is the one copy:
    - `SessionController._audit_created_at` calls it (session.py's `time` import dropped);
    - `ui/main_window.py`'s module helper is removed;
    - `ui/recovery.py` passes its injectable clock;
    - the recovery test now patches `session_store.session_created_at`.
    - Leg a6: the composer's run showed that patch also reached the recovery LIST's `refresh`, through `session_expires_at`. Decided (a): the test's injection was too broad, and this is not a robustness gap.
      - `session_expires_at` has read the same creation time since before this plan (HEAD `1e564b4`); round 7 did not touch it.
      - The real `session_created_at` catches its own read errors (`SessionStoreError` / `OSError`) and otherwise does arithmetic only, so it has no list-time failure mode. C2 concerns the audit blocking custody; the list's expiry display is not an audit read.
      - The fault is now injected only after the list is built, around the Discard alone. No source change.
  - LOW-015: `_verified_note`'s and `_verify_note_for_completion`'s docstrings name `_verified_note_with_identity` as the core.
  - LOW-016: `test_every_refusal_code_fits_the_rows_code_pattern` derives both `Literal`s.
  - LOW-017: `CSV_COLUMNS` uses `deletion.state` / `deletion.at` / `past_session.state` / `past_session.at`, and the export test reads two of them.
  - ruff clean; mypy 52 files; pytest is composer-run.
- Fix-delta self-check: PASS — re-read the applied hunks in `audit.py` (`_still_open`, `_date_from_epoch`, `begin`, `rows`, `_open_key`, the CSV columns), `session_store.py` (`_note_identity`, `audit_created_at`, the docstrings), `session.py`, `ui/main_window.py` (both refusal sites, `_store_write_record`), `ui/recovery.py` and the tests. The early refusal's audit call cannot change the click: `_write_created_at` is guarded and `record_write_refusal` never raises. No test patched a moved name except the one updated.
- Convergence: round 7 has no CRIT / HIGH / MED and its findings are all LOW (7 ⚡ docs/plan/test strength, 3 🔁, 7 🆕), so `/review-loop` is CONVERGED at round 7 (2 of 3 rounds).

### Round 8 - 2026-10-01 - Phase 1 slice A (source), independent cross-family codex peer review (pass stage-1.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 1 Tasks 1.1–1.4; permitted source files and plan sections; all five Complete paths, Discard branches, sweep, and write-record boundary reviewed by reading only.

#### Findings

- Verification counts: 6 claims checked, 6 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
- PEER-ROUND-8 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0) — transcribed by the composer from the read-only codex stdout.

### Round 9 - 2026-10-01 - Phase 1 slice B (tests), independent cross-family codex peer review (pass stage-1.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 1 Tasks 1.1–1.4 test honesty; permitted test files, supporting source and plan sections; read-only, no tests run.

#### Findings

- **PR-LOW-007** (LOW, test-harness, `desktop/tests/test_audit.py:445`): The audit failure test does not detect exception text leaking into logs. Adding a log of the caught exception would leave this test passing; the schema and whole-row tripwire tests do not cover that leak. — Evidence: line 441 raises `RuntimeError("a change that fails")`; line 445 only asserts `"audit_update_failed detail_code=completion" in caplog.text`. Recommendation: Fix-now — Inject a distinctive sensitive exception message and assert its absence from captured records, including exception information, alongside the expected fixed event. /fix decision: Applied. /fix notes: `test_audit.py::TestRowStore::test_update_never_raises` changes:
  - Every injected failure (the refusing change and the store-write failure) carries a distinctive name-and-path secret.
  - Capture is at DEBUG on every logger.
  - The audit logger's messages must be exactly the four fixed `audit_update_failed detail_code=<stage>` events.
  - Every captured record from any logger must carry no `exc_info`, `exc_text` or `stack_info`, and hold the secret in neither its message nor any attribute.
  - Test-only: `audit.py` `_count_failure` already logs the stage code alone; no source defect. /fix date: 2026-10-01. /fix applied by: Claude Code.

- **PR-LOW-008** (LOW, test-harness, `desktop/tests/test_ui_encounter.py:1168`): The write-audit test claims to verify auditing only after durable storage, but checks only the final audit-call sequence. Moving the audit call before storage would still pass; existing storage-failure tests instantiate the window without an audit recorder. — Evidence: the docstring promises “AFTER it is on disk”; lines 1174–1180 inspect `audit.calls` after `_click`; lines 863 and 1134 construct failure cases with `store=store` but no `audit`. Recommendation: Fix-now — Assert the corresponding stored record exists when each audit callback executes, and attach an audit recorder to storage-failure cases to verify failed transitions are not audited. /fix decision: Applied. /fix notes: `test_ui_encounter.py` changes:
  - `_AuditRecorder(store)` snapshots `write.enc`'s stored outcomes AT each `record_write` call.
  - `test_the_attempt_then_the_finish_reach_the_audit` pins `[["attempting"], ["attempting", "written"]]`, so an audit call before its store would fail.
  - `test_a_finished_record_that_cannot_be_stored_reads_unknown` asserts only the stored attempt is audited.
  - `test_an_attempt_row_that_cannot_be_stored_sends_nothing` asserts nothing is audited.
  - Test-only: `ui/main_window.py` `_store_write_record` already audits after `with_write_custody` returns; no source defect. /fix date: 2026-10-01. /fix applied by: Claude Code.

- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01

#### LEG 1 verified tuples (executor, 2026-10-01T08:25:59+10:00)
- PR-LOW-007: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — `test_audit.py:441-445` raises a plain `RuntimeError` and asserts only that the fixed event is present. `audit.py` `_count_failure` logs `detail_code=stage` alone and nothing else logs in the store, so the code is sound. But a future `logger.exception(...)` would pass unseen, since no test checks the absence of exception text or exception information.
- PR-LOW-008: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — `test_ui_encounter.py:1174-1180` inspects `audit.calls` only after the click. The failure cases at `:863` (`fail_on={"written"}`) and `:1134` (`fail_on={"attempting"}`) build the window with no `audit`. So moving `record_write` above `with_write_custody` in `_store_write_record` (`ui/main_window.py`), or auditing a failed store, would pass every test.
- Cap verdict: accept — test-harness — both are test-strength LOWs over production code that already behaves as the tests should prove (the fixed-code-only log and the audit-after-store ordering); round 8 was clean on the source.
- PEER-ROUND-9 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2) — transcribed by the composer from the read-only codex stdout.

### Round 10 - 2026-10-01 - Phase 1 confirmation of round 9's test fixes, independent cross-family codex peer review (pass stage-1.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Read-only confirmation of PR-LOW-007/008, their named tests and supporting source; no tests run.

#### Findings

- **PR-LOW-009** (LOW, test-harness, `desktop/tests/test_ui_encounter.py:668`): The recorder catches audit-before-store ordering and failed-store auditing, but does not read the real stored record as requested. Its “on disk” claim remains unsupported: it snapshots an in-memory fake’s history. — Evidence: line 668 uses `self.stored_at_call.append([stored for stored, _ in self.store.stored])`; the fake’s storage implementation at lines 615–616 only executes `self.stored.append((record.outcome, self.requests()))` and `self.record = record`. Recommendation: Fix-now — Add a disk-backed confirmation that reads the actual stored write record during each audit callback, retaining the existing ordering, failure and outcome assertions. /fix decision: Accepted-with-record (composer disposition following the executor's LEG 1 rec under gates=executor, 2026-10-01; D9 harness tail — second consecutive test-harness-only round; no code change)

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01

#### LEG 1 verified tuples (executor, 2026-10-01T08:30:44+10:00)
- PR-LOW-009: materiality=docs-only severity=LOW surface=test-harness rec=Accept-with-record — the invariant is already pinned at the production seam; only the recorder's "on disk" wording overclaims. Evidence:
  - `_MemoryWriteStore.store` (`test_ui_encounter.py:612-616`) appends only after its failure check passes, as the real `WriteStore.store` returns only after its atomic write.
  - `ui/main_window.py:1950-1965` calls `record_write` only after `with_write_custody(... store.store ...)` returns.
  - So the snapshot at `:668` does pin audit-after-store, and no audit for a failed store, at the exact `store.store` seam production uses.
  - The real `write.enc`'s durability is a different property, owned by its own store tests.
  - A real-file variant would add a disk/DPAPI dependency to a Qt-slot test for no new invariant.
  - The line-650 comment says "held on disk" where it means "the store seam had stored"; a wording fix, not a coverage gap.
- Cap verdict: accept — test-harness — second consecutive test-harness-only LOW round (D9 harness-tail); the finding pins no production behaviour the tests miss, and rounds 8–9 left the source clean.
- PEER-ROUND-10 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1) — transcribed by the composer from the read-only codex stdout.

### Round 11 - 2026-10-01 - Phase 2 (Tasks 2.1–2.3) code review, /review-loop round 1 of 3 (stage-2 executor, in-session)

- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Primary review baseline: HEAD `1e564b4`. Phase 1 is in the same uncommitted diff (reviewed and converged in rounds 6–10), so this round covers Phase 2's changes, including where they alter Phase 1 code: `complete_session`, the Complete callers, Discard, the sweep, `CompletionFacts`.
- Changed files (Phase 2):
  - `desktop/src/scribe_desktop/`: `past_sessions.py` (new), `session_store.py`, `session.py`, `app.py`, `logging_setup.py`, `note.py` (docstring), `ui/{__init__.py, bridge.py, main_window.py, models.py, note.py, recovery.py, transcript.py}`;
  - tests: `test_past_sessions.py` (new), `test_session_store.py`, `test_session_machine.py`, `test_ui_screens.py`, `test_ui_encounter.py`, `test_audit.py`, `test_display_name.py`, `test_hands_free.py`, `test_integration_no_sockets.py`.
- **Named targets checked:**
  - **C1 at every crash window.** Each window leaves one of these states:
    - Staging (killed mid-write) leaves `.staging\<id>`, which `clean_staging` removes at the next start-up; the source key survives, so the Complete is retryable.
    - Publish (killed between removing the old entry key-first and the rename) leaves no entry plus a staging copy, which is cleaned.
    - Verification (killed or failed) leaves no entry.
    - Source-key deletion: a failure raises with the key and a `pending` entry kept; Discard, the recovery list, expiry and a dead-key `orphan_gc` each remove the entry first; a retry replaces it.
    - Marker removal (failed or killed) gives `commit_deferred`; the keyless source directory is collected by `orphan_gc` with no hook, and `reconcile_pending` commits the entry on a confirmed-absent key.
    - Checked against every key destroyer enumerated in the leg-b1 brief. `delete_session_key` has only 3 callers: `complete_session`'s 5 paths, all through `_complete_locked`; `discard_session`'s 4 callers; and `sweep_sessions`' 3 branches. It holds, apart from LOW-001: an id mismatch between an entry and its source directory.
  - **One entry per session id:** a retry replaces a pending entry key-first; publishing refuses while an old directory remains.
  - **C3:** no audit field was added (`commit_deferred` is deliberately left out, leg b2); `past_sessions` logs a session id and a detail code only; every error is authored text.
  - **C4:** `ArchiveSource` has no audio field.
  - **D3:** a fresh key per entry, with a description no other store's unwrap accepts. Delete now, expiry and removal all delete the key first.
  - **`reconcile_pending` / `clean_staging`:** they never raise; an inaccessible key is never treated as absent; only session-id-named folders are touched.
  - **Retention sweep:** undated and future-dated entries are kept, and "never" returns before any decrypt. MED-001 is the per-tick cost.
  - **D5:** the bridge's Start display, then its re-verification, then the checkout's Verified result, each matched by session id. All five Complete callers pass a label resolved at the click.
  - **D6:** the source-derived set holds on each path; a delete-note path never archives the note and reads it only for provenance.
  - **The mock rule:** it must be a casefolded `mock` PREFIX, because a mock-transcribed session records `model_name="MockSpeechProvider"` (`transcription.py:1311`), which the plan's literal `mock-` would miss.
- **Leg-b1 interpretations, each judged against the plan:**
  - These four HOLD UP; none needs a practitioner decision:
    - (1) `generated_text` for D2's `text` — the same content under a distinctive tripwire name;
    - (2) an absent or unreadable `generated.enc` is not kept, and its facts read `unknown` — D8's `unknown`; failing a Complete over a best-effort copy would put custody behind it;
    - (3) a failed `keep_generated` unlinks the stale file — the safe direction, with a named residue;
    - (4) the casefolded `mock` prefix — needed, as above.
  - Also holding: `remove_pending_entry` removing any entry while the source key exists (C1: such an entry cannot be committed); `reconcile_pending` removing keyless entries; `PastSessionCleanupError` (C1's "a failed removal keeps the key", applied to Discard); the provenance written before `write_note`'s own refusals (D8).
- Finding verification: 6 candidates; 3 dropped:
  - `draft_write`'s narrower `mock-` rule beside `is_mock_identity`: it gates a different act, and no provider named `Mock…` without the dash exists;
  - `PastSessionCleanupError`'s hyphen: stylistic;
  - staging left undeletable blocks a retry: fail-closed by design, and Discard remains.
- Missed-issue pass: re-read `past_sessions.py` (whole), `session_store.py` `complete_session` / `_read_generated` / `sweep_sessions`, `session.py` `_complete_locked` / `discard` / `discard_recovered`, `ui/recovery.py` `_discard`, `ui/main_window.py` `keep_label_for` / `_complete_live` / the recovered lambda, `ui/note.py` `begin_review` / `_on_style_done`, `ui/transcript.py` `keep_generated` / `abandon_note_and_complete` / `_complete_after_write`, `app.py` `sweep_with_archive`; result: LOW-001, LOW-002

#### MED-001 — The retention sweep decrypts every committed label on every tick, on the GUI thread
- File: `desktop/src/scribe_desktop/past_sessions.py` `PastSessionStore.sweep` (it called `list_entries()`, which does one DPAPI unwrap and one decrypt per entry)
- Triage: Fix-now · Fix route: fix-on-fast
- Why it matters:
  - Flow 4 runs the retention sweep at start-up and hourly, on the GUI thread (C5).
  - At a practice's volume, a 1-year or 7-year setting means thousands to tens of thousands of entries, so every tick would freeze the window for one key unwrap per entry.
  - A committed entry's `completed_at` never changes.
- Current behaviour: every tick unwraps and decrypts every label.
- Desired behaviour: each entry's date is decrypted once per process. An in-memory, content-free (date only) cache, dropped whenever this store writes, publishes or removes the id's entry. An undated entry is read again next tick, and "never" still decrypts nothing.
- Pattern siblings (grep `list_entries\(|_read_label\(` in `desktop/src`): `sweep` (this finding); `list_entries` itself (the tab's on-demand list, Phase 3, not per tick). None other.
- Verification:
  - `test_past_sessions.py::TestRetentionSweep::test_each_label_is_decrypted_once_per_process` (the unwrap count stays at 2 across ticks, a removal forgets the date, a cached date still expires);
  - `test_an_undated_entry_is_read_again_next_tick`.
- /fix decision: Applied
- /fix notes: `PastSessionStore._completed_dates`. It is filled by `sweep`, pruned to the committed ids present, and popped in `write_entry`, `remove_pending_entry`, `reconcile_pending`'s keyless removal and `delete_entry`. The docstrings say so. ruff + mypy clean; pytest is composer-run.
- /fix date: 2026-10-01
- /fix applied by: Claude Code

- **[LOW]** LOW-001: `session_store.py` `complete_session`, the `keep` branch — the entry is keyed by the audio header's id, while every other destroyer (`discard()`, `discard_recovered`, `ui/recovery.py` `_discard`, the sweep) and `reconcile_pending` name the source by its DIRECTORY. With a header id that is not the directory, an interrupted Complete's pending entry would survive that directory's Discard, then be committed as finished (C1). Reachable only through a corrupt or tampered header. — Triage: Fix-now; Decision: Applied (archiving now refuses, with the key kept, when the resolved id is not `session_dir.name`: `ArchiveWriteError("the session identity is not its directory; key retained")`; test `test_past_sessions.py::TestCompleteKeeps::test_a_header_id_that_is_not_the_directory_keeps_the_key`; a Complete without an archive is unchanged)
- **[LOW]** LOW-002: `ui/transcript.py` `keep_generated` — D2's "replaced on regeneration" means a regeneration after Save that is then cancelled (Cancel review keeps `note.enc`) leaves the EARLIER generation's saved note beside the LATER generation's body, and both are archived as they stand. This residue was unnamed. — Triage: Fix-now; Decision: Applied (named in `keep_generated`'s docstring, and carried in the handoff note for Task 5.2's residue list; the behaviour is plan-decided, D2)
- Fix-delta self-check: PASS. Re-read the applied hunks in `past_sessions.py`, `session_store.py` and `ui/transcript.py`:
  - the cache holds no name and never outlives a removal this store made;
  - the new refusal sits inside the `keep` branch, before the boundary, so it keeps the key like every archive failure;
  - no existing test archives a directory whose header names another id.
- Verification owed: the composer's `tests/test_past_sessions.py` plus the full desktop suite; ruff clean, mypy 53 files

### Round 12 - 2026-10-01 - Phase 2 (Tasks 2.1–2.3) code review, /review-loop round 2 of 3 (stage-2 executor, in-session)

- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Primary review baseline: HEAD `1e564b4` (Phase 2's changes; the same file list as round 11). Regression baseline: round 11's fixes. The full suite was green at 5086 on 2026-10-01 ~09:23.
- **Post-fix regression check** (round 11's three fixes), no regressions:
  - **MED-001's cache:** it is popped on every path this store writes, publishes or removes, and pruned to the committed ids present. `delete_entry` pops before its key removal, so a failed removal re-reads next tick. The sweep iterates a materialised directory list, so deleting during the loop is safe. "never" still returns before any read.
  - **LOW-001's refusal:** it sits inside the `keep` branch before the boundary, so the key is kept. Every production session directory is named by its id at creation (`_start_locked`, `adopt_queued`, the recovery listing), so only a corrupt or tampered header reaches it. A Complete without an archive is unchanged.
  - **LOW-002:** docstring only.
- **Targets round 11 covered only in summary, now re-read:**
  - **C1 windows:**
    - The source key is deleted, then the process dies before the controller's `_audit_completion`: the sweep records `orphan_gc` and the entry commits. That is LOW-002.
    - A recovered checkout is not in `custody_protected_ids`, so a sweep tick may expire it mid-review. This is pre-existing (24 h). With the hook, its pending entry goes first, so C1 holds.
  - **C3:** `patient_name`, `past_session` and `generated_text` are tripwire signatures (`logging_setup.py:228-275`). `past_sessions._log` passes only `session_id` and `detail_code`, both whitelisted by `log_event`.
  - **D2's emit points:**
    - `begin_review` captures the digest after `_refinalise` has started the prose job (`note.py:1801`).
    - `show_saved_note` (a reopened saved note) never emits, so a saved note is never recorded as the generated one.
    - An edit during the job clears the rewrite.
  - **D5:** `live_display_name` and `live_reverification` both require the controller's current session to be the id asked about. `adopt_queued` gives an adopted session its encounter context, so its kind and clinic resolve.
  - **D6 / mock:** unchanged since round 11.
- Finding verification: 4 candidates; 2 dropped:
  - "a reverted edit during the prose job re-emits": the content is identical, so the kept body is the same text;
  - "`discard()` removes an entry for a RECORDING session": a no-op on absent paths.
- Missed-issue pass: re-read `past_sessions.py` `sweep` / `delete_entry` / `remove_pending_entry` / `reconcile_pending` / `sweep_past_sessions`, `session_store.py` `complete_session` (the new refusal), `ui/note.py` `begin_review` / `_refinalise` / `_on_style_done` / `show_saved_note`, `ui/bridge.py` `live_display_name` / `live_reverification`, `audit.py`'s record methods, `logging_setup.py`'s signatures; result: LOW-001, LOW-002
- Round classification: 1 ⚡ (LOW-001, adjacent to round 11's cache) / 1 🆕 (LOW-002) / 0 🔁
- **[LOW]** LOW-001: `past_sessions.py` `sweep_past_sessions` — the plan-named function builds a FRESH store on every call, so round 11's per-process date cache never helps it. If Task 3.2 wires it to the hourly tick, every tick decrypts every label again. — Triage: Fix-now; Decision: Applied (the docstring says it is a one-off and that the periodic sweep calls `sweep` on the app's one shared store; the handoff note carries this into Task 3.2)
- **[LOW]** LOW-002: the gap between `delete_session_key` inside `complete_session` and the controller's `_audit_completion` — a process killed there leaves the source directory keyless and the row `pending`. The next sweep records `orphan_gc`, with `past_session` left `none`, while `reconcile_pending` commits a legitimate entry. The row then under-reports an archive that exists (best-effort audit, C2; an interruption of milliseconds). `audit.py` has no past-session updater yet: Task 3.2 must add one for `expired` / `deleted_early`. — Triage: Fix-now; Decision: Applied (headless gate: AUTO-DISPOSABLE — LOW, non-production, do-the-work: Include in plan. Carried in the handoff note as a Task 3.2 input: when `reconcile_pending` commits an entry, record `past_session=archived` on its row with Task 3.2's updater, so `reconcile_pending` must report which ids it committed. Until then it is a named residue for Task 5.2.)
- Fix-delta self-check: PASS (one docstring, no behaviour change)
- Verification: ruff clean, mypy 53 files; no test depends on the changed docstring

### Round 13 - 2026-10-01 - Phase 2 slice A (source), independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending; both applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase 2 Tasks 2.1–2.3 source: archive custody, cleanup, retention settings, provenance, and Complete/Discard wiring; read-only verification, no tests run.

#### Findings

- **PR-LOW-010** (LOW, behavioral, `desktop/src/scribe_desktop/past_sessions.py:515`): Staging cleanup can destroy a committed entry’s key through a directory junction or symlink. A session-id-named staging child pointing to a committed archive directory passes the name check; deleting its child `key.dpapi` follows that directory link outside staging. This also runs under retention “never”. — Evidence: line 515: `if _SESSION_ID_RE.fullmatch(child.name) and _remove_key_first(child):`; line 727: `(directory / KEY_FILENAME).unlink(missing_ok=True)`. Neither checks directory links before unlinking the key. Recommendation: Fix-now — Reject staging-root and staging-child junctions/symlinks before traversing them; verify cleanup preserves a committed target’s key. /fix decision: Applied (executor LEG 2, 2026-10-01T09:36:22+10:00). The CLASS is closed in `past_sessions.py`:
  - **The guard:** `_is_link` (`is_symlink()` or `is_junction()`; an error counts as a link) sits in `_remove_key_first` (a link is refused: False, untouched).
  - **Where links are refused:**
    - `_entry_dirs` skips linked children, so they are never listed, read, committed or swept;
    - `_committed` answers `not_found`;
    - `commit` never removes a marker through a link;
    - a linked `.staging` (`_staging_linked`) stops `clean_staging` and refuses `write_entry` (`write_failed`, nothing touched);
    - `remove_pending_entry` treats a link as nothing of ours to remove: True, left in place, and a linked `.staging` side is skipped, so a planted link never blocks a Discard or an expiry.
  - **Reporting:** a refusal is left in place, never followed, and not counted among the removed. It is logged only as a content-free `detail_code` (`staging_link_refused` / `link_refused`, with the id when the name is one), like the module's other failure codes, with no path or exception text (C3).
  - **Not touched:** the archive ROOT (D10, Phase 4).
  - **Tests:** `test_past_sessions.py::TestLinksAreNeverFollowed`, parametrised over a junction (real, via `_winapi.CreateJunction`, which needs no privilege; skipped off Windows) and a directory symlink (skipped where the host lacks the privilege; each skip names why). The cases are a linked staging child, `.staging` linked to the archive root, a linked entry (list, read, delete, commit, reconcile, sweep, remove), and a linked entry blocking a publish under its id. The committed target's key survives each.
  - **Recorded for H3, out of this fix:** `session_store.sweep_sessions` / `discard_session` share the pre-existing `is_dir()` → `delete_session_key` link-following shape under the SESSIONS root.

- **PR-LOW-011** (LOW, behavioral, `desktop/src/scribe_desktop/past_sessions.py:751`): The settings loader accepts JSON `retention_days: true` as integer `1`, silently selecting the shortest destructive retention period instead of rejecting an invalid setting. Pydantic’s non-strict integer conversion happens before the choice validator, so its allow-list does not prevent this. The resulting setting would authorize one-day deletion when the retention caller uses it. — Evidence: line 748: `model_config = ConfigDict(extra="forbid", frozen=True)`; line 751: `retention_days: int | None = None`; lines 754–757: `@field_validator("retention_days")` followed by `if value is not None and value not in RETENTION_DAYS_CHOICES:`; line 109 includes `1` among those choices. Recommendation: Fix-now — Require a strict integer or null and verify boolean settings raise `PastSessionSettingsError`. /fix decision: Applied (executor LEG 2, 2026-10-01T09:36:22+10:00; `PastSessionSettings.retention_days` and `hide_names` are `Field(strict=True)`, the file's two coercible fields, so JSON `true` / `1.0` / `"7"` for the retention and `"true"` / `1` for Hide names raise `PastSessionSettingsError` through the loader. `test_past_sessions.py::TestSettings::test_an_invalid_file_is_an_error_never_a_default` gained the five cases. `test_every_valid_stored_file_still_loads_under_strict` loads every offered choice and null. The label and generated records are app-written and AEAD-authenticated, so they are unchanged)

- Verification counts: 3 claims checked, 2 confirmed, 1 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T09:33:00+10:00)
- PR-LOW-010: materiality=behavioral severity=LOW surface=production rec=Fix-now. The class is WIDER than `clean_staging`:
  - **Every link-following path:** `_remove_key_first` (`past_sessions.py:~727`) unlinks `<dir>\key.dpapi` through whatever `<dir>` is. Windows resolves a junction or directory symlink mid-path, so the unlink deletes the TARGET's key. `_entry_dirs` admits a linked child, since `is_dir()` follows links. `shutil.rmtree` on 3.12+ does not descend a junction, but the key is already gone by then.
  - **Its callers, all exposed:**
    - `clean_staging` (the finding);
    - `write_entry`'s staging pre-clean;
    - `_publish`'s replace-key-first of `root\<id>`;
    - `remove_pending_entry` (staging and final);
    - `delete_entry`, and so the retention `sweep`;
    - `reconcile_pending`'s keyless rmtree, which is harmless: rmtree does not follow.
  - **The worst shape:** `.staging` ITSELF a link to the archive root. Every start-up's `clean_staging` would then destroy every committed entry's key, even under "never".
  - **Why LOW:** planting a link under `%LOCALAPPDATA%\ClinikoScribe\past_sessions` needs same-user write access, which can already delete any entry directly (the threat model's accepted same-user residue). So this is robustness against a stray or planted link, not a boundary crossing.
  - **The fix closes the class:** one guard in `_remove_key_first` plus `_entry_dirs` / `clean_staging` refusing any link (`Path.is_symlink() or Path.is_junction()`, both on the supported Python 3.12+), and `.staging` refused when it is a link. The archive ROOT itself is left alone, because relocating it is a location question (D10's check, Phase 4). Tests: a junction or symlink child under `.staging` and under the root, and `.staging` as a link; the committed target's key survives each.
  - **Pre-existing, outside Phase 2:** `session_store.sweep_sessions` / `discard_session` have the same `is_dir()` → `delete_session_key` shape under the sessions root. Recorded for H3 (`/security-review`), not folded in here.
- PR-LOW-011: materiality=behavioral severity=LOW surface=production rec=Fix-now:
  - **Confirmed:** `PastSessionSettings.retention_days: int | None` (`past_sessions.py:~751`) validates in pydantic's lax mode, where JSON `true` becomes `1` (so do `1.0` and `"1"`) BEFORE the `_a_choice` validator, which then accepts `1`. A hand-edited or corrupted settings file therefore selects the shortest, destructive retention instead of failing loudly. The loader's own docstring promises the opposite ("an unknown version or value fails loudly").
  - **Siblings checked:** the only UNTRUSTED persisted input in Phase 2 is this plaintext settings file:
    - `hide_names: bool` coerces too (`"true"`, `1`), but only between two display states, never a deletion; making it strict as well keeps the one rule;
    - `PastSessionLabel` (`has_generated` / `has_saved` / `schema_version`) and `GeneratedRecord` are app-written and AEAD-authenticated, so they are not attacker-shaped input.
  - **Fix:** `retention_days` and `hide_names` as `Field(strict=True)` (or `StrictInt` / `StrictBool`). Tests: `true`, `1.0` and `"7"` for `retention_days`, and `"true"` for `hide_names`, each raise `PastSessionSettingsError`.
- Cap verdict: accept (no raise needed: peer round 1 of the pass's cap 5) — production-behavioral — both fixes are small and confined to `past_sessions.py` plus `test_past_sessions.py`, and close their classes (every `_remove_key_first` / `_entry_dirs` caller, and the file's two coercible fields). A confirmation peer round fits well inside the remaining cap.
- PEER-ROUND-13 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2).

### Round 14 - 2026-10-01 - Phase 2 slice B (tests) and confirmation of round 13, independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending; both applied by the executor, LEG 2, tests only)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Specified Phase 2 test changes and source verification; PR-LOW-010 and PR-LOW-011 fixes confirmed for the specified cases. Read-only; no tests run.

#### Findings

- **PR-LOW-012** (LOW, test-harness, `desktop/tests/test_ui_screens.py:7190`): The Save failure test bypasses both real writes, leaving Task 2.1’s required partial-write/UI-consistency coverage absent. It cannot detect disagreement between `_note_committed`, `_note_saved` and disk after provenance succeeds but the note write fails. — Evidence: `monkeypatch.setattr("scribe_desktop.ui.transcript.write_saved_note", fail)` replaces the entire operation; assertions check only `assert not screen._note_committed` and `assert screen.is_busy`. The store’s post-provenance refusal test at `desktop/tests/test_session_store.py:1759` checks note absence without exercising the UI. Recommendation: Fix-now — Exercise real `write_saved_note` through the connected screens, inject each write failure separately, and assert disk, both flags, Cancel review, retry and reopen agree. /fix decision: Applied (executor LEG 2, 2026-10-01T10:00:15+10:00; tests only, no source defect found):
  - **New test:** `test_ui_screens.py::TestNoteWiring::test_a_save_failing_at_either_write_agrees_with_disk`, parametrised over the injection point and the follow-up.
  - **Injection point:** `session_store.write_saved_provenance`, or `session_store.write_note` after the provenance landed.
  - **Follow-up:** a retry, or Cancel review.
  - **Route:** the real `write_saved_note` through the window's own route (`NoteScreen.save` → `MainWindow._on_note_save` → `TranscriptScreen.save_note` under the held lease), against a session directory under `tmp_path` that holds the real transcript bytes.
  - **Assertions after the failure:** "Save failed", no `note.enc`, the provenance present only in the note-stage case, neither `_note_saved` nor `_note_committed`, and the lease held.
  - **After Cancel review:** the lease is released, nothing is committed, and Generate is available.
  - **After a retry:** both flags are set, the lease is released, the reopened `read_note` matches, and the provenance digest equals `saved_note_identity`.

- **PR-LOW-013** (LOW, test-harness, `desktop/tests/test_session_machine.py:2647`): Deferred-commit coverage exercises only ordinary Complete, leaving the explicitly planned post-boundary checks for the other four Complete paths unverified, including generation-lease and write-reservation release. — Evidence: `monkeypatch.setattr(store, "commit", lambda _sid: False)` is followed only by `controller.complete(label=self._label())`; the plan’s Validation / Verification requires “marker-removal failure injected on all five Complete paths”. Successful-path and pre-publication-failure tests do not exercise these callers with `commit_deferred=True`. Recommendation: Fix-now — Parameterise marker-removal failure across all five paths, asserting destroyed source custody, terminal state, released leases/reservations, deferred status and successful later reconciliation. /fix decision: Applied (executor LEG 2, 2026-10-01T10:00:15+10:00; tests only, no source defect found):
  - **The old test is replaced** by `test_session_machine.py::TestPastSessionsThroughTheController::test_a_deferred_commit_is_reported_and_reconciled_on_every_path`.
  - **Parametrised over `_COMPLETE_PATHS`,** the five callers of `_complete_locked` enumerated from `session.py`: `complete`, `complete_without_note` (under the held lease), `complete_deleting_saved_note`, `complete_recovered`, and `complete_after_write` (under the held reservation, with a `written` record).
  - **The commit is forced to fail** through the store's seam.
  - **Assertions:**
    - the source key and directory are gone;
    - for the four live paths: WRITTEN, no live session, no lease held, no write reservation;
    - for `complete_recovered`: the in-memory key is destroyed;
    - `last_complete_deferred` is set;
    - the entry is unlisted until `reconcile_pending` commits it, then listed.

- Verification counts: 3 claims checked, 2 confirmed, 1 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T09:44:35+10:00)
- PR-LOW-012: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now:
  - **Confirmed.** `TestTranscriptPastSessions::test_a_failed_save_commits_nothing_and_keeps_the_lease` replaces the whole `write_saved_note`, so neither of Task 2.1's two injection points is exercised through the screens. The failure it would miss is a Note-tab `_note_saved` or Transcript-screen `_note_committed` that diverges from disk after the provenance landed and `note.enc` did not.
  - **The source is correct by reading:** `save_note` (`ui/transcript.py:865-900`) sets `_note_committed` only after `with_generation_custody` returns. `NoteScreen.save` (`ui/note.py:2022-2029`) sets `_note_saved` only when `on_save` returns. `write_saved_note` raises out of either write.
  - **The fix:** drive the REAL `write_saved_note` through the window's own route (`_generate_through_window`) against a session directory under `tmp_path`. Inject at `session_store.write_saved_provenance`, and at `session_store.write_note` after the provenance, through module seams. Then assert disk, both flags and the lease, and follow each with a retry (the reopened `read_note` and the provenance digest agree) and with Cancel review (nothing committed, Generate available).
- PR-LOW-013: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now:
  - **Confirmed.** `TestPastSessionsThroughTheController::test_a_deferred_commit_is_reported_and_reconciled` drives only `complete()`.
  - **The five Complete paths, enumerated from the code** (the callers of `_complete_locked` in `session.py`): `complete`, `complete_without_note(lease)`, `complete_deleting_saved_note`, `complete_recovered`, `complete_after_write(reservation)`.
  - **The source already holds by reading:** `_complete_locked` sets `_last_complete_deferred` for all five, and a failed commit never raises after the boundary (`complete_session`). So each path still makes its terminal transition, consuming the lease (`complete_without_note`) or the reservation (`complete_after_write`) only after the WRITTEN transition.
  - **The fix:** parameterise over the five, asserting the source key destroyed, the terminal state (recovered: the in-memory key destroyed and the directory gone), the released lease and reservation, `last_complete_deferred`, the entry unlisted until `reconcile_pending` commits it, and then listed.
- Cap verdict: accept (no raise; peer round 2 of the pass's cap 5) — test-harness — both findings pin what the plan's Validation list already requires. Neither found a source defect; the source for each path was read and holds. The fixes are test-only, in `test_ui_screens.py` and `test_session_machine.py`.
- PEER-ROUND-14 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2).

### Round 15 - 2026-10-01 - Phase 2 confirmation of round 14's test fixes, independent cross-family codex peer review (pass stage-2.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: PR-LOW-012 and PR-LOW-013 assertion coverage confirmed against the specified source; no assertion removal found against HEAD. Exact comparison with the uncommitted round-14 test version was unavailable. Read-only; no tests run.

#### Findings

- Verification counts: 3 claims checked, 2 confirmed, 1 dropped as unverifiable
- Last reviewed: 2026-10-01
- PEER-ROUND-15 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 16 - 2026-10-01 - Phase 3 (Tasks 3.1–3.3) code review, /review-loop round 1 of 3 (stage-3 executor, in-session)

- Round status: Closed (all 21 applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with two parallel subagent lenses — correctness/security, and plan/design/tests/structure — merged and verified by the executor)
- Primary review baseline: HEAD `1e564b4` + the working tree's Phase 3 changes (`ui/past_sessions.py`, `ui/past_sessions_view.py`, `ui/main_window.py`, `ui/models.py`, `app.py`) and the Phase 1/2 code they alter (`audit.py` `record_past_session` / `row_for`, `past_sessions.py` `reconcile_pending`'s new return type and every caller, `app.py`'s sweep wiring). The full suite was green at 5140 passed / 4 skipped (composer, 2026-10-01 ~13:00).
- Integrity check: the composer's named targets, each read against the code:
  - **C5/C7:** every tab path runs on the GUI thread (signals, the 1 s tick, `app.main`'s QTimer). Construction decrypts nothing; opening lists `label.enc` only; "never" returns before any read (`sweep_report(None)`). The hourly bound is monotonic seconds, so a wall clock moving backwards or jumping forward neither skips nor repeats a sweep; the RETENTION decision itself uses the wall clock: a clock set BACK deletes nothing early (a label dated in the future is kept, `CLOCK_SKEW_TOLERANCE`), while a clock jumped FORWARD makes entries look older and can delete them early — a named residue for Task 5.2, shared with the existing 24 h session sweep (there is no trusted clock on the PC; under "never" nothing is read or deleted).
  - **C3:** no name, path or exception text reaches a log or the audit; authored reasons only. Found: the export outcome carried the file name (LOW-001), unexpected errors needed the app's one fixed line (LOW-012). The CSV formula guard is `audit.csv_cell` (Phase 1, unchanged). Hide names covers the list, the opened heading and the CSV (the CSV never holds names); the transcript/note-text residue stays named.
  - **Delete now (D3):** two clicks on the same entry within 10 s (monotonic), key first, `deleted_early` only after the deletion succeeded, the entry cleared from every panel. A sweep or reconcile cannot interleave (all GUI thread); a sweep that removes the armed entry now disarms it (tested, LOW-017).
  - **Retention:** lowering confirms, saves, then sweeps; raising saves only; an unreadable file is replaced only by an explicit retention choice. Found: the outcome hid a sweep that could not finish (MED-002), and the Hide-names state model (MED-001).
  - **`archived` / `expired` / `deleted_early`:** one row per id, `_PAST_SESSION_FROM` guards the transitions, `update` never raises (C2). Found: a duplicate row read as "no record" (LOW-006); `expired`'s `pre_audit` date (LOW-005).
  - **Clinical text, Copy, intended use, name, design system:** text is held only while the tab is in front (names too after LOW-008); Copy goes only through `_place_note_text` (the panels are `NoTextInteraction`); `INTENDED_USE_LINE` is pinned on both tabs; no "Cliniko Scribe" in any new string; design-system gaps are LOW-010 / LOW-013 / LOW-014.
- Finding verification: 31 candidates from the two lenses; 21 confirmed after merging (several lens findings were the same defect from two sides), 10 dropped:
  - "monotonic can go backwards" (it cannot, by definition);
  - "the hourly bound can be skipped by a sleep" (a sleep only delays the next tick; the bound is a minimum);
  - "Delete now races a sweep thread" (there is no thread: both on the GUI thread);
  - "reconcile can commit an entry Delete now just removed" (reconcile only touches `pending` entries; a committed one has no marker);
  - "`update` raises on a pruned row" (it creates `pre_audit`, C2, by design — a named residue);
  - and five duplicates of kept findings.
- Missed-issue pass: re-read `ui/past_sessions.py` end to end, `ui/past_sessions_view.py`, `past_sessions.py` `sweep` / `list_entries` / `_entry_dirs` / `delete_entry`, `audit.py` `row_for` / `record_past_session` / `_find`, `app.py` `main` / `sweep_with_archive` / `retention_sweep_if_due`, and `MainWindow._on_tab_changed`; result: LOW-003, LOW-007, LOW-016, LOW-018
- Round classification: 0 ⚡ / 21 🆕 / 0 🔁
- **[MED]** MED-001: the Hide-names / settings state model. (a) The hourly `run_retention_sweep` reloaded the file and discarded a Hide-names choice that could not be saved: the box unticked while the list stayed masked, and the next opening showed names. (b) An unreadable file failed OPEN (names shown), and the later explicit retention choice wrote `hide_names=False` with it. (c) `refresh()` never re-read the file, so a changed file was not seen. (d) `on_hide_names` checked a cached readability. — Triage: Fix-now; Decision: Applied:
  - `_hide_override` keeps an unsaved Hide-names choice for the run, over every reload, and is cleared by a successful save.
  - An unreadable file now reads as retention "never" with names HIDDEN (fail toward hiding), so the explicit replacement writes `hide_names=True`.
  - `_reload_settings()` (re-render the controls, and the list and opened entry when the mask changed, with no decrypt) runs in `refresh`, `run_retention_sweep`, `on_hide_names` (re-checked at the click) and `on_retention_chosen` (decides against the file as it is now).
- **[MED]** MED-002: a retention sweep that could not delete everything due was invisible, and the lowering's outcome line overstated it ("kept for 30 days", with old sessions still there). — Triage: Fix-now; Decision: Applied:
  - `PastSessionStore.sweep_report` → `RetentionSweepReport(expired=((id, completed),…), failed, complete)` with `problem`; `sweep` keeps its list.
  - The tab keeps `_sweep_problem` from the latest sweep (an exception counts) and shows `SWEEP_PROBLEM_LINE` on the status line until a sweep finishes.
  - `retention_changed_line(..., problem=)` adds it to the lowering's outcome.
- **[LOW]** LOW-001: the export outcome named the chosen file (C3: a path on screen and in screenshots). — Decision: Applied (`export_done_line(count)` — "to the file you chose")
- **[LOW]** LOW-002: one "Copy unavailable" line covered four causes. — Decision: Applied (`copy_unavailable_reason`: turned off / nothing open / no saved note / unresolved error, shown under the buttons in `copy_reason_label` and as the tooltip)
- **[LOW]** LOW-003: an archive root that exists but cannot be listed showed as "No past sessions are kept". — Decision: Applied (`_entry_dirs(strict=True)` for the listing and the sweep; the tab shows `LIST_UNREADABLE` and no placeholder; the sweep reports `complete=False`)
- **[LOW]** LOW-004: a previous visit's outcome line lingered, and the Delete-now question outlived its arming. — Decision: Applied (`refresh()` clears the line; `_disarm_delete` clears the question)
- **[LOW]** LOW-005: an `expired` event on a pruned row created a `pre_audit` row dated today. — Decision: Applied (dated by the entry's completion, from the report)
- **[LOW]** LOW-006: `row_for` read the first of two rows for one id as THE record (`update` refuses that state). — Decision: Applied (`AuditUnavailable("unavailable")`)
- **[LOW]** LOW-007: a label dated before 1970 broke the list on Windows (`astimezone` OSError). — Decision: Applied (`_local_text` falls back to UTC text)
- **[LOW]** LOW-008: listed names stayed in memory and in the list widget after leaving the tab. — Decision: Applied (`on_left()` drops the opened entry, the arming and the listing; `MainWindow._on_tab_changed` calls it; the placeholder shows only after a listing)
- **[LOW]** LOW-009: Export stayed enabled while the audit key was unreadable. — Decision: Applied (disabled, refused at the click; the key line says it cannot be exported)
- **[LOW]** LOW-010: the two confirmations were Yes/No (design-system Microcopy: named for what they do). — Decision: Applied (`confirm(text, action)`; "Delete older sessions" / "Start a new audit record" against "Keep things as they are", the safe one the default and Escape)
- **[LOW]** LOW-011: the unreadable-entry lines gave no next step. — Decision: Applied (row "Cannot be read on this Windows account"; heading and open-failure lines end "You can still delete it with Delete now.")
- **[LOW]** LOW-012: a second "unexpected" wording beside the app's one. — Decision: Applied (`UNEXPECTED_REASON = CUSTODY_UNEXPECTED_REASON`)
- **[LOW]** LOW-013: group titles were inline literals; `INTENDED_USE_LINE` was missing from `models.__all__`. — Decision: Applied (`LIST_GROUP_TITLE` / `SETTINGS_GROUP_TITLE` / `EXPORT_GROUP_TITLE`; the list and Delete now in their own group)
- **[LOW]** LOW-014: the save dialog opened in the process's working directory. — Decision: Applied (the Documents folder via `QStandardPaths`)
- **[LOW]** LOW-015: no test drove the real signals. — Decision: Applied (`test_hide_names_and_retention_are_wired_to_their_signals`)
- **[LOW]** LOW-016: the 15-minute tick's body lived inside `app.main`, untested. — Decision: Applied (`app.PeriodicSweep`, monotonic injected; `test_the_periodic_tick_runs_each_step_in_order_on_its_own_cadence`)
- **[LOW]** LOW-017: failure paths untested. — Decision: Applied (a failed delete keeps the entry and records nothing; an unreadable entry lists, opens to its next step and deletes; the open-failure line; a sweep disarms a delete for an entry it removed; the literal confirmation text)
- **[LOW]** LOW-018: `MainWindow` could not inject the tab's dialogs, so a window test could open a real one. — Decision: Applied (`past_sessions_confirm` / `past_sessions_save_path`, passed through; `_main_window` injects failing fakes)
- **[LOW]** LOW-019: the `PastSessionsAudit` docstring claimed `isinstance` checks signatures. — Decision: Applied (presence only; mypy checks the signatures)
- All 21: headless gate AUTO-DISPOSABLE (MED/LOW, non-production surface — the app is unreleased — do-the-work Fix-now).
- Fix-delta self-check: PASS — no new dependency, env var, config file or network use; files touched are Task 3.1–3.3's plus the binding seams in `past_sessions.py` / `audit.py` / `app.py` and their tests.
- Verification: ruff clean, mypy 55 files; pytest owed by the composer (full desktop suite)

### Round 17 - 2026-10-01 - Phase 3 confirmation of round 16 and legs c4–c5, /review-loop round 2 of 3 (stage-3 executor, in-session)

- Round status: Closed (both applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Primary review baseline: the working tree after legs c3–c5 (the full desktop suite green at 5156 passed / 4 skipped, composer, 2026-10-01 ~13:30). Regression baseline: round 16's 21 fixes and leg c4's mapping.
- **Post-fix regression check**, no regressions found:
  - **`failure_reason` is the one mapping:** every tab handler (`open_entry`, `_delete`, `on_export`, `on_reset_audit`) is a single `except Exception as exc` into a view line that takes the exception. No `str(exc)` remains in `ui/past_sessions.py`. `_write_line`, the list, settings, sweep, Copy and status lines are fixed constants or read row data. The three tables are the stores' own; an unknown code reads the fixed line. Outside the tab, `AuditWriteError` still formats `AUDIT_REASONS.get(reason, reason)`, but every code passed to it is authored in `audit.py`, so it is not reachable with a foreign code.
  - **Hide names:**
    - `_hide_override` is applied only over a READABLE file; an unreadable file forces hidden.
    - `on_retention_chosen` saves `self._settings.hide_names` (override included), then clears the override.
    - `on_hide_names` re-reads at the click and is refused while unreadable.
    - The file is written only by an explicit retention choice or a Hide-names click on a readable file.
    - `_reload_settings` re-renders the list and entry only when the mask changed, and the list is empty after `on_left`, so a sweep while the tab is behind shows nothing.
  - **`sweep_report`:** a failed `delete_entry` counts `failed`; any exception in the walk returns `complete=False` with what was done. The tab clears the problem on the next finished sweep.
  - **`PeriodicSweep`:** order unchanged from the old closure (sweep, reminders, recovery, prune, retention), with the monotonic clock injected; `main` seeds both stamps after the start-up runs.
  - **`row_for`:** `_find` errors → `AuditUnavailable`; duplicates refused; an unreadable or newer row reads None.
  - **`on_left`:** clears the entry, the arming and the listing, and `_listed`. Messages and status lines carry no names.
- **Targets round 16 covered only in summary, re-read:** the Delete-now arming under the monotonic clock (`0 <= elapsed <= 10 s`); the confirmations' safe default; Copy re-checked at the click; `INTENDED_USE_LINE` on both tabs; no "Cliniko Scribe" in the new strings.
- Finding verification: 4 candidates; 2 dropped:
  - "a stale `SWEEP_PROBLEM_LINE` while the settings file is unreadable": the settings line explains it, and the next readable sweep clears it;
  - "`key_unreadable()` decrypts on every opening": it unwraps the audit KEY only, which D9 needs; no row is read.
- Missed-issue pass: re-read `past_sessions.py` `sweep_report` / `_read_label`, `audit.py` `key_unreadable` / `_find` / `export_csv`, and every `ui/past_sessions.py` handler; result: LOW-020, LOW-021
- Round classification: 0 ⚡ / 2 🆕 / 0 🔁
- **[LOW]** LOW-020: an entry whose label this account cannot read has no date, so the retention sweep KEEPS it whatever its age (fail toward keeping — by design) and says nothing. The tab lists it as unreadable but never says the retention setting does not apply to it. — Triage: Fix-now; Decision: Applied (`RetentionSweepReport.undated`; the tab's status line gains `undated_line(n)` — "…cannot be read on this Windows account, so it is not deleted by age. You can delete it with Delete now." — cleared when Delete now removes one; under "never" nothing is read, so no line)
- **[LOW]** LOW-021: an audit key that goes unreadable after the tab was opened. An export (or an entry's write line) fails with "start a new audit record on the Past sessions tab", but the button only appears after leaving and reopening the tab, and Export stays enabled. — Triage: Fix-now; Decision: Applied (`_recheck_audit_key` after a failed export and a failed `row_for`: the reset button and the key line appear at once, and Export is disabled)
- Both: headless gate AUTO-DISPOSABLE (LOW, non-production, do-the-work Fix-now).
- Fix-delta self-check: PASS — confined to `past_sessions.py` (one report field), `ui/past_sessions_view.py` (one line), `ui/past_sessions.py` and their tests
- Verification: ruff clean, mypy 55 files; pytest owed by the composer (`test_ui_screens.py`, `test_past_sessions.py`)

### Round 18 - 2026-10-01 - Phase 3 slice A (source), independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending; PR-LOW-014 applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-3-only source diff and permitted current source/callees; specified plan decisions, constraints, flows, tasks and rounds 16–17. Read-only verification; no tests or network commands run.

#### Findings

- **PR-LOW-014** (LOW, behavioral, `desktop/src/scribe_desktop/ui/past_sessions.py:624`): Disabling retention after a failed sweep leaves a contradictory deletion warning until the next scheduled sweep. Choosing “Until I delete them” saves successfully but retains `_sweep_problem`, so the status still promises another deletion attempt although age-based deletion is disabled. — Evidence: `"self._render_status()"` followed by `"deleted = self.run_retention_sweep() if lowering else []"`; `status_lines` at lines 737–738 unconditionally includes `SWEEP_PROBLEM_LINE` when `_sweep_problem` is true. That line says `"Clinic Scribe tries again within the hour."` (`desktop/src/scribe_desktop/ui/past_sessions_view.py:163`), while `sweep_report(None)` immediately returns without deletion (`desktop/src/scribe_desktop/past_sessions.py:649`). Recommendation: Fix-now — Clear or suppress obsolete sweep warnings when retention is successfully disabled, without running a sweep; describe retries as occurring on a later scheduled sweep rather than guaranteeing an hour. /fix decision: Applied (executor LEG 2, 2026-10-01T13:39:03+10:00, Claude Code; the class is closed in `ui/past_sessions.py`):
  - **One derived state replaces the two sticky flags:** `_last_sweep = (retention it ran under, RetentionSweepReport)` replaces `_sweep_problem` / `_sweep_undated`. A walk that raised is stored as `complete=False`.
  - **`_current_sweep()` returns the report only while that setting is still current:** the file readable, the retention not "never", and the same days.
  - **Readers:** `status_lines` (both lines), the lowering's outcome line and Delete now's undated decrement all read it.
  - **A change drops the lines at once, with no sweep:** choosing "never", a raise, a hand-edit picked up on opening, or an unreadable file. A raise still decrypts nothing; the next sweep under the new setting re-derives them.
  - **Wording:** `SWEEP_PROBLEM_LINE` now says "tries again at a later hourly check while it is running".
  - **Test:** `test_ui_screens.py::TestPastSessionsTab::test_the_sweep_lines_follow_the_current_setting`, parametrised over never / raise / hand-edit / unreadable. Each case has both lines present after a failed sweep with an undated entry, both gone after the change, and no unwrap for never or raise. The round 16–17 sweep tests still hold. Sibling sites: the undated line (round 17) is fixed under the same derivation; none deferred.)

- Verification counts: 4 claims checked, 1 confirmed, 3 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T13:37:50+10:00)
- PR-LOW-014: materiality=behavioral severity=LOW surface=production rec=Fix-now — confirmed, and the class is wider. `_sweep_problem` and round 17's `_sweep_undated` are STICKY flags set only by a sweep, while `status_lines` shows them whatever the current setting:
  - (a) "Until I delete them" saved after a failed sweep keeps "tries again" — the finding;
  - (b) RAISING (e.g. 30 → 365 days) saves without a sweep, so the warning describes the old setting;
  - (c) a hand-edit to "never" picked up by `refresh` / the hourly reload keeps both lines;
  - (d) an unreadable settings file (nothing is swept) keeps "tries again" beside the unreadable line;
  - (e) the undated line under "never" says "not deleted by age" when nothing is.
  - **Not stale (checked):** the unreadable-settings line (re-derived at every reload and cleared by the save), the audit-key line (re-checked at refresh, reset and, since round 17, after a failed audit read), the failure count (read live on the 1 s tick), and the partial-sweep line after a LATER finished sweep (set from that report).
  - **The wording:** the retention sweep runs at most hourly on the 15-minute timer, and only while the app runs, so "within the hour" is not guaranteed.
  - **The fix:** keep the latest sweep's report together with the retention setting it ran under, and derive both lines in `status_lines` only while that setting is still the current, readable one and is not "never". Make the retry wording truthful. A change to "never" or a raise then drops the lines without a sweep (raising still decrypts nothing); the next sweep under the new setting re-derives them.
- Cap verdict: accept — production-behavioral — one LOW, with a confined fix in `ui/past_sessions.py` (derived status) and `ui/past_sessions_view.py` (the wording) plus tests; it closes the stale-status class for both sweep lines.
- PR-LOW-014 final disposition: Applied (executor LEG 2, 2026-10-01T13:39:03+10:00) — derived sweep status plus truthful retry wording; pytest owed by the composer
- Fix-delta self-check: PASS — re-read the 7 applied hunks across `ui/past_sessions.py` / `ui/past_sessions_view.py`; `days` is bound before its only use after the `try`; Delete now's decrement writes the current setting, which `_current_sweep` already matched; no drive-by edits
- PEER-ROUND-18 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

### Round 19 - 2026-10-01 - Phase 3 slice B (tests) and confirmation of round 18, independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending; all four applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-3-only test diff, round 18 fix, permitted source and plan sections; read-only verification, no tests or network commands run.

#### Findings

- **PR-LOW-015** (LOW, behavioral, `desktop/src/scribe_desktop/ui/past_sessions.py:649`): PR-LOW-014 remains reproducible after a hand-edited retention change is loaded by Hide names. After a failed sweep, hand-edit retention to “never” and toggle Hide names: the in-memory setting changes, but the visible status label retains both obsolete sweep lines. — Evidence: `on_hide_names` calls `"self._reload_settings()"`; its successful path renders settings, list and entry, but never status. `_reload_settings` at line 582 calls `"readable = self._load_settings()"` and returns without rendering status. The unchanged-choice, declined-confirmation and save-failure returns in `on_retention_chosen` have the same exposure. Recommendation: Fix-now — Repaint status whenever settings are reloaded, including early-return paths; extend the regression test to assert the actual label after these reload routes without sweeping. /fix decision: Applied (executor LEG 2, 2026-10-01T13:46:58+10:00, Claude Code):
  - **The structural fix:** `_reload_settings` ends with `_render_status()`, so every route that reloads the settings repaints the VISIBLE status from the state just read. The routes are the tab opening, the sweep, Hide names, and each exit of a retention choice: unchanged, declined, save failure and success. Its two callers that repainted on their own (Hide names' refusal, the sweep's unreadable return) no longer do.
  - **The writer list is now complete:** every writer of a status input ends in `_render_status` (LEG 1's list); the audit failure count stays on the 1 s tick.
  - **Test:** `test_the_sweep_lines_follow_the_current_setting` gains `toggle` (the peer's repro), `same_choice`, `declined` and `save_fails`. It now asserts the label text itself, not only the derived list, and that no route but opening the tab reads an entry.)

- **PR-LOW-016** (LOW, test-harness, `desktop/tests/test_ui_screens.py:8992`): The Delete expiry test does not protect the click-time deadline check when the timer has not yet disarmed the confirmation. A regression accepting any armed second click would pass this test. — Evidence: `"now[0] += view.DELETE_CONFIRM_SECONDS + 1"` is immediately followed by `"screen._tick()"` before `"screen.on_delete_clicked()"`. Production independently checks the deadline inside `on_delete_clicked` through `_delete_confirmable` (`desktop/src/scribe_desktop/ui/past_sessions.py:495`). Recommendation: Fix-now — Add an expired second-click case without calling `_tick`, and assert both entries and their keys remain. /fix decision: Applied (executor LEG 2, 2026-10-01T13:46:58+10:00, Claude Code; tests only — `test_the_delete_arming_expires_and_follows_the_selection` now makes a LATE second click with no tick first. It re-asks, both entries are listed, and both `key.dpapi` files remain, before the original tick path runs.)

- **PR-LOW-017** (LOW, test-harness, `desktop/tests/test_ui_screens.py:8584`): The Phase 3 audit tests leave deletion under audit failure and duplicate deletion outcomes unprotected. The UI double always succeeds; the outcome test pins repeated `archived` events but checks only final state for `deleted_early` and `expired`. — Evidence: the double records the call then `"return True"`; Delete checks membership with `"assert (...) in audit.calls"` at line 8972. `desktop/tests/test_audit.py:658` asserts only `"past_session.state == \"expired\""`, without repeating that outcome or checking its event count. Recommendation: Fix-now — Exercise audit updates returning false during Delete and expiry, asserting deletion and UI cleanup still finish; repeat each outcome and assert exact event counts and unchanged timestamps. /fix decision: Applied (executor LEG 2, 2026-10-01T13:46:58+10:00, Claude Code; tests only):
  - **New `test_ui_screens.py::TestPastSessionsTab::test_a_failing_audit_update_never_stops_a_deletion`:** a double whose `record_past_session` returns False and counts the failure, as `AuditLog.update` does. Delete now still removes the key and folder and clears the panels and list row; expiry still deletes and drops the row; both events were attempted; the failure line shows 1, then 2.
  - **`test_audit.py::test_past_session_outcomes_after_the_complete`:** `deleted_early` and `expired` are each repeated, with the other outcome, under an advanced clock. The event code is asserted, then the same event count and the first `past_session.at`.)

- **PR-LOW-018** (LOW, test-harness, `desktop/tests/test_ui_screens.py:9733`): The Phase 3 privacy tests check displayed strings but do not inspect emitted log records. Logging the injected path or exception while still returning the correct fixed message would pass these tests. — Evidence: the refusal test asserts `"assert secret not in line and \"no_such_code\" not in line"` at line 9769; no Phase 3 test captures log records, and `_ps_store` at line 8615 injects keys and clock but no logger. Recommendation: Fix-now — Capture logs during the actual failure handlers and sweep, inject distinct name/path/exception sentinels, and check messages, structured fields and exception information for leaks. /fix decision: Applied (executor LEG 2, 2026-10-01T13:46:58+10:00, Claude Code; tests only):
  - **New `test_no_failure_handler_or_sweep_logs_a_name_a_path_or_exception_text`, under `caplog` at DEBUG, with a store logger.** Its sentinels are a patient name in the labels, a marked archive-root path, and marked text inside every injected exception.
  - **What it drives:** the open, Delete now, export and reset failure handlers, a sweep whose walk stops on a foreign error (`sweep_failed` is logged, so the check is not vacuous), and a sweep with a refused deletion.
  - **What it asserts:** no record's message, args, `vars(record)` or formatted `exc_info` / `exc_text` holds a sentinel, and nor do the screen's lines. C6 holds: tmp_path, fake keys, no host state.)

- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T13:44:08+10:00)
- PR-LOW-015: materiality=regression severity=LOW surface=production rec=Fix-now — confirmed (round 18's class, not fully closed). Every writer of the status line's inputs (`_settings` / `_settings_unreadable`, `_last_sweep`, `_audit_key_unreadable`, the failure count), enumerated from `ui/past_sessions.py`:
  - **Already repaint at their end:**
    - `refresh` (tab show);
    - `run_retention_sweep`, both exits (start-up, periodic, lowering);
    - `on_retention_chosen` success;
    - `_delete`'s undated decrement;
    - `on_reset_audit`;
    - `_recheck_audit_key` (export failure, `row_for` failure);
    - `_tick` (the failure count);
    - the constructor.
  - **Do NOT repaint — all four through `_reload_settings`, which changes the settings and returned without repainting:**
    - `on_hide_names`' success path (the repro);
    - `on_retention_chosen`'s unchanged-choice return;
    - its declined-confirmation return;
    - its save-failure return.
  - **No status input changes:** `on_left`, the selection, open, Copy and Delete arming.
  - **Structural fix (no new call sites):** `_reload_settings` ends with `_render_status()`, so every settings reload repaints from current state. That makes the writer list complete — each state-changing path ends in `_render_status`. Its two now-redundant callers (`on_hide_names`' refusal, the sweep's unreadable return) drop their own call.
- PR-LOW-016: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — confirmed: `test_the_delete_arming_expires_and_follows_the_selection` runs `_tick()` before the late click, so `_delete_confirmable`'s click-time deadline is never the deciding check. Add a late second click with NO tick and assert both entries and their keys remain.
- PR-LOW-017: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — confirmed:
  - `_FakePastAudit.record_past_session` always returns True, and no test drives Delete now or expiry with a failing update (C2: `update` returns False and counts it, never raises).
  - `test_past_session_outcomes_after_the_complete` repeats only `archived`.
  - **Fix:** a failing double (returns False and counts) through Delete now and the sweep — the entry is still deleted, the list and panels are cleared, and the failure line shows. In `test_audit.py`, repeat `deleted_early` and `expired` with an advanced clock and assert identical event counts and `past_session.at`.
- PR-LOW-018: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — confirmed:
  - No Phase 3 test captures log records, and `_ps_store` passes no logger, so the store's `_log` (`sweep_failed` and others) is never exercised.
  - **Fix:** a `caplog` test with a store logger. It injects a patient-name sentinel in a label, a path sentinel in the archive root, and an exception-text sentinel in the injected errors. It drives the open, delete, export and reset failure handlers, a sweep whose delete fails and a sweep whose walk fails, and asserts no sentinel appears in any record's message, args, `exc_info` / `exc_text` or extra fields (C6: tmp_path, fake keys, no host state).
- PR-LOW-015..018 final dispositions: all Applied (executor LEG 2, 2026-10-01T13:46:58+10:00) — PR-LOW-015 in `ui/past_sessions.py` (one structural line plus two redundant calls removed); PR-LOW-016..018 tests only; pytest owed by the composer
- Fix-delta self-check: PASS — re-read the 3 source hunks (`_reload_settings` now repaints; `on_hide_names` and `run_retention_sweep` rely on it) and the 4 test hunks. `_reload_settings` is never called from the constructor (that path calls `_load_settings`, then repaints at its end), so no widget is rendered before it exists. The status repaint is idempotent; no drive-by edits.
- Cap verdict: accept — production-behavioral (PR-LOW-015; the rest test-harness) — four LOWs. PR-LOW-015's fix is one structural line in `_reload_settings`, closing the writer list. The three test findings add coverage the plan's Validation already implies (C2, C3, D3's deadline). The fixes are confined to `ui/past_sessions.py`, `test_ui_screens.py` and `test_audit.py`.
- PEER-ROUND-19 RESULT: 4 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 4).

### Round 20 - 2026-10-01 - Phase 3 confirmation of round 19's fixes, independent cross-family codex peer review (pass stage-3.p1)

- Round status: Closed (0 pending; applied by the executor, LEG 2, tests only)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-19 fix diff, Round-19 findings and permitted source; read-only confirmation of status rendering, regression assertions, logging capture and host isolation. No tests or network commands run.

#### Findings

- **PR-LOW-019** (LOW, test-harness, `desktop/tests/test_ui_screens.py:9585`): The audit-failure test still does not protect panel cleanup during expiry: the previously opened entry has already been deleted, and the expiring entry is never opened. A regression leaving expired content displayed would pass this new expiry case. Delete now also checks only the saved-note panel. — Evidence: line 9577 asserts `"screen._open_entry is None and screen.saved_view.toPlainText() == \"\""` before the sweep; line 9585 runs `"assert screen.run_retention_sweep() == [expiring]"` without selecting `expiring`, and subsequent assertions check storage, row count, audit calls and status only. Recommendation: Fix-now — Open the expiring entry before sweeping, populate the transcript panel, and assert the opened entry and all content panels clear after expiry despite audit failure; apply the same panel assertions to Delete now. /fix decision: Applied (executor LEG 2, 2026-10-01T13:51:07+10:00, Claude Code; tests only — the production cleanup was verified correct by reading, LEG 1):
  - **Both cases now open the entry first:** `test_a_failing_audit_update_never_stops_a_deletion` opens the entry about to be deleted, AND the entry about to expire, each with the transcript shown, every content panel, the heading and the write line non-empty.
  - **After Delete now, and after the sweep expires the OPEN entry, despite the failing audit update,** it asserts: `_open_id` / `_open_entry` None; the generated, saved and transcript panels empty; heading and write line empty; the transcript hidden and its button reset; no list selection; Copy disabled.)

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T13:50:38+10:00)
- PR-LOW-019: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — the test gap is confirmed (the expiring entry is never opened; Delete now checks one panel). The PRODUCTION behaviour was checked first and holds by reading:
  - **Both paths clear everything:** expiry (`run_retention_sweep` → `_drop`) and Delete now (`_delete` → `_drop`) call `close_entry` when the open id is among those deleted. That clears `_open_id`, `_open_entry`, the heading, the write line, and the generated, saved and transcript panels; it hides the transcript and resets its button. `_render_list` then rebuilds the list without the row and re-selects only `_open_id`, which is now None, so nothing stays selected.
  - **The audit failure cannot skip it:** `AuditLog.record_past_session` → `update` catches every exception and returns False (C2), so `retention_sweep`'s audit loop never raises and `_drop` always runs. In `_delete` the audit call comes before `_drop` and cannot raise either.
  - **So no source defect** (no C3 / clinical-text-lifetime gap). The fix is the stronger test.
- Cap verdict: accept — test-harness — production verified correct by reading; the fix is test-only, in `test_ui_screens.py`
- PR-LOW-019 final disposition: Applied (executor LEG 2, 2026-10-01T13:51:07+10:00) — tests only; no source defect; pytest owed by the composer

### Round 21 - 2026-10-01 - Phase 4 (Tasks 4.1–4.2) code review, /review-loop round 1 of 3 (stage-4 executor, in-session)

- Round status: Closed (all 3 applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Primary review baseline: HEAD `1e564b4` + the working tree's Phase 4 changes — `exclusions.py` (new), `app.py` (`main`'s hooks and checks), `ui/main_window.py` (`StatusPanel`, `MainWindow(exclusion_warnings=)`), `ui/past_sessions.py` (`status_lines`), `scripts/register-native-host.py`, `tests/conftest.py`, the new `test_exclusions.py` / `test_register_native_host.py` and the `app.main` / no-sockets test sites. Phases 1–3 in the same diff are reviewed and closed (rounds 6–20). Full suite green at 5236 passed / 4 skipped (composer, 2026-10-01 ~14:16).
- Integrity check — the composer's named targets, each read against the code:
  - **C6:** the conftest autouse fixture covers EVERY test. It patches `Win32WindowsLayer.__init__` on the class, so every import binding is covered. No module-level real layer or import-time call exists (`app.main` builds it inside `main`; `_kernel32` is a lazy cache that only the real layer's methods reach). A test calling an UNBOUND real method (`Win32WindowsLayer.wer_exclusions(None)`) would bypass it; none does — a contrived residue, not a gap in what the sentinel claims. Any `ExceptionHook` left installed fails the test at teardown (after unwinding). Sites: 5 `app.main` sites (all patch the hooks; the 3 that reach the checks also patch the layer and `startup_exclusions`); 8 `MainWindow` sites need nothing (the window makes no Windows call for the lines); the script test uses a fake `winreg` via `sys.modules` and `tmp_path` install paths; the no-sockets child uses an inline fake layer. Found: the host's `main()` is called by `test_native_host.py` — wired with the fix below.
  - **C3:** every hook path logs `uncaught_exception error_code=<identifier or unknown> detail_code=<where>` — no message, args, traceback, `exc_info` or locals. Covered: main thread and Qt slots (PySide sends a slot's exception through `PyErr_Print` → `sys.excepthook`), `threading.excepthook` (a real thread tested), `sys.unraisablehook` (a real `__del__` tested). `faulthandler` is not enabled anywhere; only an inherited `PYTHONFAULTHANDLER` / `-X faulthandler` would enable it, and its dump carries file, line and function names only (a Task 5.2 note). No `logger.exception`, `exc_info=` or `print_exc` in `src`. The hooks never chain to the defaults and restore only their own slots. Found: `sys.last_*` retention (LOW-001), the second process (MED-001), and no proof that a console launch shows anything (LOW-003).
  - **Location check:** `_normalised` folds case and separators, strips `\\?\` and maps `\\?\UNC\` to `\\`; an unset or empty `%OneDrive*%` / `%APPDATA%` is skipped; a junctioned data folder is judged by its `realpath`; a mapped network drive is `\\?\UNC\…` after `realpath` or `DRIVE_REMOTE` by letter. A `\\?\Volume{…}` path (a mount with no letter) reads local and only logs `location_unusual` — accepted, no warning is owed for it.
  - **WER check:** missing, value 0 or 2, wrong type (the real layer keeps only `REG_DWORD`), and an unreadable key are all covered. Launch forms: `scribe-app.exe` runs the venv's `pythonw.exe`, which starts the base `pythonw.exe`; `sys.executable` reads the venv `pythonw.exe` (covered). The console `python.exe` gets D10's line. A base pythonw started directly is covered. A renamed launcher does not change `sys.executable`. An empty name reads "this program".
  - **`register()` / `unregister()`:** read-back of all three values (value AND type), a loud stderr ERROR naming each failed value, then `verified : FAIL` and exit 1. A raising `CreateKey` / `SetValueEx` propagates (loud, exit 1). Idempotent (a re-run rewrites 1; a second unregister removes nothing). Unregister removes only its three values — the key and other values stay. HKCU only. The agent-shell caveat is in the docstring, `--help` and the printed note.
  - **Warning lines:** fixed constants; no data path. The WER line names the repo script, as the Status tab's registration line already does. Shown on `StatusPanel.exclusions_label` (hidden when none) and appended in the derived `PastSessionsScreen.status_lines()`, so every repaint carries them. The window makes no Windows call. They are a START-UP snapshot: LOW-002 makes the WER line say so.
  - **NOT_CONTENT_INDEXED, folders only:** new files take the attribute from their folder; a file written before its folder was first marked keeps its old attribute until rewritten. Named in the module docstring, carried to Task 5.2, and checked by P.3 item (5).
- Finding verification: 7 candidates; 3 dropped:
  - "the WER line shows a path" — it names the repo script, not a data location, matching the existing registration line;
  - "a Qt worker thread escapes the hooks" — `TaskThread.run` catches `Exception` itself (`ui/tasks.py:36-39`); anything that still escapes a QThread's Python `run` goes through `PyErr_Print` → `sys.excepthook`, the main hook, which is correct;
  - "`mark_not_indexed` walks a huge model tree" — folders only, `scandir` with no following; bounded and start-up-only.
- Missed-issue pass: re-read `exclusions.py` end to end, `app.main`, `native_host.main` / `run_host` and its threads, the `StatusPanel` and `past_sessions.status_lines` hunks, `register-native-host.py`, `conftest.py`; result: MED-001, LOW-001
- Round classification: n/a (first code round on Phase 4)
- **[MED]** MED-001: `native_host.py:546` `main()` — `scribe-host.exe` kept Python's DEFAULT exception hooks. An uncaught exception in its main loop, its stdin reader thread or the relay's pipe thread printed the message and traceback to stderr, which Chrome may log. The relay handles display strings (patient names), and a pydantic error's text carries input values. This is the same C3 class as Task 4.1's hooks, on the second process. — Triage: Fix-now (scope-expansion, Fold-in to Task 4.1 — the composer pre-authorised closing it in this phase; headless gate AUTO-DISPOSABLE: MED, do-the-work, not production-impacting). Stdout contract checked first: the hooks write only through the host's logger, whose handlers are a file and stderr (`setup_logging` never attaches stdout — pinned), so stdout stays framed protocol bytes. — /fix decision: Applied
  - /fix notes: `native_host.main` now calls `install_exception_hooks(logger)` right after `setup_logging`, before any other step; the module's startup contract says so. `test_native_host.py`: the existing `main()` test patches the hooks (C6), and a new test pins the order — hooks with the host's own logger, then the registration paths, then the origin check. Pattern siblings (every production entry point): grep `setup_logging\(` outside tests finds exactly `app.py:516` and `native_host.py:550`, and `pyproject.toml`'s gui-scripts name exactly `scribe-app` → `app:main` and `scribe-host` → `native_host:main` — both now install the hooks; none found beyond them. ruff, mypy clean.
  - /fix date: 2026-10-01
  - /fix applied by: Claude Code
- **[LOW]** LOW-001: `exclusions.py` `ExceptionHook` — `PyErr_Print` (the route of a Qt slot's exception) stores the exception in `sys.last_exc` / `last_type` / `last_value` / `last_traceback` BEFORE calling the hook. That keeps the traceback, and every frame's locals (possibly transcript or note text), alive until the next uncaught exception. — Triage: Fix-now; Decision: Applied (the main hook drops the four `sys.last_*` attributes after logging, in its own `try`; the docstring says so; `test_the_main_hook_drops_the_interpreters_last_exception`)
- **[LOW]** LOW-002: `exclusions.py` `WER_NOT_EXCLUDED` — the lines are a start-up snapshot, so after re-running the script the line stays until the app restarts, and the line did not say so. — Triage: Fix-now; Decision: Applied ("…again from a normal terminal, then restart Clinic Scribe.")
- **[LOW]** LOW-003: `test_exclusions.py` — no test proved that a console launch still SHOWS something (the composer's d1 note). The type-name line must reach `setup_logging`'s stderr handler, and neither the message nor a traceback may. — Triage: Fix-now; Decision: Applied (`test_a_console_launch_shows_the_one_line_on_stderr_and_nothing_else` — a real `setup_logging` with stderr and a `tmp_path` log file)
- All 4: headless gate AUTO-DISPOSABLE (MED/LOW, non-production, do-the-work Fix-now).
- Fix-delta self-check: flagged-and-fixed in-leg — LOW-001's first placement dropped `sys.last_*` before logging inside the same `try`, so a failed drop would have skipped the log line. It now runs after the log, in its own `try`. Otherwise PASS: re-read the 4 applied hunks across `exclusions.py`, `native_host.py`, `test_native_host.py` and `test_exclusions.py`.
- Verification: ruff clean, mypy 56 files; pytest owed by the composer (`tests/test_exclusions.py`, `tests/test_native_host.py`, then the full desktop suite)

### Round 22 - 2026-10-01 - Phase 4 confirmation of round 21, /review-loop round 2 of 3 (stage-4 executor, in-session)

- Round status: Closed (no findings)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Primary review baseline: HEAD `1e564b4` + the working tree's Phase 4 changes, after round 21's fixes. The full suite was green at 5239 passed / 4 skipped (composer, 2026-10-01 ~14:26). Regression baseline: round 21's four applied hunks.
- **Post-fix regression check** (the composer's three named points); no regressions found:
  - **The host's hooks never write to stdout, on any path:**
    - They log only through the host's logger. `setup_logging` attaches a rotating file and `sys.stderr`, never stdout (pinned by `test_logging_setup.py::test_no_stdout_handler`), and sets `propagate = False`.
    - If the log file cannot be opened, the `OSError` branch leaves stderr only.
    - Under a pythonw launcher (`sys.stderr` None) with no file handler, the logger has no handler. `logging.lastResort` then drops an INFO record (its level is WARNING), and `Handler.handleError` writes only to a truthy `sys.stderr`.
    - Before `setup_logging` returns, Python's default hooks are still in place, and they write to stderr, not stdout.
    - The hooks themselves never `print`, and the stdout `write_frame` path is untouched.
  - **Dropping `sys.last_*` cannot raise out of the hook:** it runs after the log call, in its own `try` (`exclusions.py:419-428`), and only for the main hook. A thread's silent `SystemExit` returns before it, as intended (not the main slot).
  - **The host test installs nothing process-wide:** `test_main_installs_the_exception_hooks_first_with_its_own_logger` replaces `nh.install_exception_hooks`, `setup_logging`, `_log_registration_paths` (so it also avoids the real HKCU read) and `verify_origin`. The older `main()` test patches the hooks too. The conftest teardown would fail either test if a real `ExceptionHook` stayed installed — and none did (suite green).
- **Targets from the d2 brief not covered by round 21, re-read:**
  - the location check's `\\?\Volume{…}` case (it reads local and is logged only — accepted in round 21);
  - `register_wer` raising on `CreateKey` (propagates: loud, exit 1);
  - the Past sessions status line's visibility (`_render_status` keys on `bool(lines)`, which now includes the exclusion lines);
  - `test_hands_free` / `test_system_pause` / `test_ui_pause_and_unreviewed` children that assert no "Traceback" on stderr (they install no hooks, so they are unaffected);
  - the integration host child runs `run_host`, not `main` (no hooks; unaffected).
- Finding verification: 1 candidate; 1 dropped — "a logging failure inside the hook prints a traceback via `handleError`". That trace shows the logging module's own frames and the record's content-free message, never the uncaught exception's message or locals.
- Missed-issue pass: re-read `native_host.main`, `exclusions.py` `_drop_last_exception` / `ExceptionHook` / `install_exception_hooks`, `logging_setup.setup_logging`, the new tests in `test_native_host.py` and `test_exclusions.py`; result: none
- Round classification: 0 ⚡ / 0 🆕 / 0 🔁 — CONVERGED (0 CRIT / HIGH / MED survivors)
- Fix-delta self-check: SKIP — no fix applied this round
- Verification: no code change since the green run (5239 passed / 4 skipped); ruff clean, mypy 56 files
- Fix-delta self-check: PASS — re-read the 2 test hunks; both helper assertions run on each path (Delete now, then expiry of the open entry); the source is unchanged since round 19
- PEER-ROUND-20 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

### Round 23 - 2026-10-01 - Phase 4 source and tests, independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending; both applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-4-only source and test diffs, current affected files and necessary callees, specified plan sections and lessons; read-only review, no tests executed.

#### Findings

- **PR-MED-020** (MED, behavioral, `desktop/src/scribe_desktop/exclusions.py:411`): A logging failure inside the thread exception hook can print the original exception’s message and traceback to stderr, violating crash hygiene. The outer catch cannot prevent output already emitted by logging’s internal error handler. Contrary to round 22’s dismissal, the logging error can carry the original exception through `__context__`. — Evidence: the hook calls `log_event(self.logger, "uncaught_exception", ...)`; `desktop/src/scribe_desktop/logging_setup.py:441` installs the stock `logging.handlers.RotatingFileHandler`. Python invokes the thread hook inside `except:` (`C:/Python314/Lib/threading.py:1083`), and its logging handler calls `traceback.print_exception(exc, limit=None, file=sys.stderr)` (`C:/Python314/Lib/logging/__init__.py:1076`), with `chain=True` by default (`C:/Python314/Lib/traceback.py:120`). A file-write or rollover failure while handling a clinical exception therefore exposes that exception’s chain. Recommendation: Fix-now — suppress logging’s traceback-producing failure handler for both production loggers, and add a regression using a failing log sink during a real thread exception containing sentinel clinical text; assert no message, traceback or stdout output escapes. /fix decision: Applied (executor LEG 2, 2026-10-01T14:35:53+10:00, Claude Code):
  - **The fix:** `logging_setup.QuietHandlerErrors` overrides `handleError`. It counts the failure (`handler_error_count`) and writes ONE fixed stderr line, `--- Logging error (<type>) ---`, gated like the stock one on `raiseExceptions and sys.stderr`. It prints no traceback, chain, stack, message or arguments, never writes stdout, keeps no reference and never raises. Both handlers `setup_logging` builds are subclasses carrying it (`_QuietRotatingFileHandler`, `_QuietStreamHandler`).
  - **One type-name helper:** `exception_type_name` moved to `logging_setup` (the identifier-or-`unknown` rule), and `exclusions` imports it.
  - **Docs:** the `exclusions` module docstring and the hook section name the control.
  - **Tests:**
    - `test_logging_setup.py`: every handler `setup_logging` builds is quiet; a text scan pins `logging_setup.py` as the only module naming `getLogger(` / `addHandler(` / `basicConfig(` / `lastResort` / `raiseExceptions` / `qInstallMessageHandler`, with its blind spots named; a failing FILE handler and a failing STDERR handler each hit by an ordinary `log_event` inside an `except` carrying clinical text, `capfd` (fd-level).
    - `test_exclusions.py`: the main, thread and unraisable hooks, each with the real file handler's rollover raising while an exception carrying clinical text is handled.
    - What every case asserts: stdout empty; the fixed line present; no sentinel, "Traceback", logging-error message or "Message:"; and the failure path really ran (the counter).
  - **Residue for Task 5.2 / H3:** a third-party logger with no handler falls to Python's `logging.lastResort` (WARNING+), which is not one of the app's handlers.
  - Pattern siblings: every handler-building site in `src` — only `logging_setup.setup_logging` (grep, then pinned by the scan).

- **PR-LOW-021** (LOW, test-harness, `desktop/tests/test_native_host.py:60`): The existing native-host `main()` test still reaches the real HKCU registry and can read the installed manifest; redirecting `LOCALAPPDATA` and patching exception hooks does not isolate this path. The new Windows-layer sentinel cannot intercept direct `winreg` calls. — Evidence: the test patches only `install_exception_hooks` before `assert nh.main() == 2`; `desktop/src/scribe_desktop/native_host.py:562` calls `_log_registration_paths(logger)` before checking the origin. That callee uses `winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)` at line 540 and `Path(manifest_path).read_text(...)` at line 543. The adjacent new test already patches this callee at `desktop/tests/test_native_host.py:76`. Recommendation: Fix-now — inject a fake registration-path logger into the older test too, preserving its stdin-refusal assertion without reading host state. /fix decision: Applied (executor LEG 2, 2026-10-01T14:35:53+10:00, Claude Code; tests only — `test_main_refuses_without_origin_before_reading_stdin` patches `_log_registration_paths` with a recorder and asserts it ran once; the stdin-refusal assertion is unchanged. Siblings: the only `nh.main()` callers in tests are this test and the round-21 test, which already patches it)

- Verification counts: 4 claims checked, 2 confirmed, 2 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T14:33:53+10:00)
- PR-MED-020: materiality=behavioral severity=MED surface=production rec=Fix-now — confirmed, and the class is wider than the thread hook.
  - **The stdlib path:** `Handler.handleError` (gated on `raiseExceptions and sys.stderr`) prints `traceback.print_exception(sys.exception())` — `chain=True`, so every `__context__` follows — then the call stack, then `record.msg` / `record.args`, all to stderr.
  - **Who reaches it:** every `emit` failure — a file write, a rollover, a formatting error, a broken stream — in BOTH handlers `setup_logging` installs (`RotatingFileHandler`, `StreamHandler(sys.stderr)`). Their `emit` methods catch `Exception` → `handleError`.
  - **When content escapes:** whenever an exception is being handled at that moment, its message and traceback print as the chain. That covers the thread hook (Python calls it inside `except:`), the main hook when called inside an `except`, the unraisable hook when the `__del__` runs inside an `except`, and EVERY ordinary `log_event` made inside an `except` block anywhere in the app or the host — not only the hooks.
  - **Enumerated surface:** grep `getLogger` / `addHandler` / `basicConfig` / `lastResort` / `raiseExceptions` in `src` finds only `logging_setup.py:428/446/457`. There is no Qt message bridge (`qInstallMessageHandler` absent). Both production loggers (`scribe-app`, `scribe-host`) come from `setup_logging` with `propagate=False`.
  - **Structural fix chosen:** a quiet `handleError` mixin on EVERY handler `setup_logging` builds — it counts the failure and writes ONE fixed stderr line naming the error's TYPE (an identifier, else `unknown`), with no traceback, chain, call stack, message or arguments, and never stdout. A source scan pins `logging_setup.py` as the only installer.
  - **Rejected:** `logging.raiseExceptions = False`. It is process-global, so it would change pytest's own and third-party handlers too, and it would silence the content-free diagnostic entirely.
  - **Named residue:** a third-party library logger with no handler of its own falls to Python's `logging.lastResort` for WARNING+ records. That handler is outside the app's handlers (a Task 5.2 / H3 note).
- PR-LOW-021: materiality=behavioral severity=LOW surface=test-harness rec=Fix-now — confirmed. `test_main_refuses_without_origin_before_reading_stdin` reaches `_log_registration_paths` (`native_host.py:526-543`): a real HKCU `winreg.OpenKey` and, if registered, a read of the installed manifest. The sentinel guards only `Win32WindowsLayer`; patch the callee as the adjacent test does.
- Cap verdict: accept — production-behavioral — PR-MED-020 is a real C3 escape on a failure path, closed for its whole surface (every handler of both production loggers, pinned) rather than at the thread hook; PR-LOW-021 is a test-only isolation fix.
- Fix-delta self-check: PASS — re-read the applied hunks in `logging_setup.py` (the mixin, the two handler classes, `setup_logging`), `exclusions.py` (the import and docstring) and the three test files. No drive-by changes: the scan's banned words appear in `src` only in `logging_setup.py`, and the stdout contract is unchanged (the override writes only `sys.stderr`).
- PEER-ROUND-23 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1).

### Round 24 - 2026-10-01 - Phase 4 confirmation of round 23's fixes, independent cross-family codex peer review (pass stage-4.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-23 fix diff, Round-23 findings and verification tuples, permitted current source and stdlib logging paths; read-only confirmation of handler coverage, regression assertions, cleanup and registry isolation. No tests or network commands run.

#### Findings

- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
- PEER-ROUND-24 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 25 - 2026-10-01 - Phase 5 (Tasks 5.1–5.2) docs truth-against-code review, /review-loop round 1 of 3 (stage-5 executor, in-session)

- Round status: Closed (all 21 applied; one routed to the composer's `/document` by the spawn's edit scope)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a four-lens read-only subagent fan-out — threat model vs code; retention + flow 22 + cross-doc; practice and product docs incl. C10 and quoted strings; the widened C9 leftover grep — every candidate re-verified in-session against the code before triage)
- Primary review baseline: HEAD `1e564b4` + the working tree's Phase 1–5 changes; the suite green at 5247 passed / 4 skipped (composer, 2026-10-01). Scope: every new or changed doc statement of Phase 5, the changed UI strings and their pins.
- Findings (all doc-only; no code or string changed):
- **[MED]** MED-001: threat-model residue (o) and the retention schedule's Audit-record residues said a Complete killed after its key deletion is recorded `archived` with deletion left `pending`. Code: `complete_session` deletes the key, then `commit`s the marker, then removes the directory (`session_store.py:1302-1313`); the audit update follows in the controller. A keyless directory left behind is `orphan_gc`'d by the next sweep WITHOUT `before_destroy` (`session_store.py:1754-1766`) and `record_sweep_results` closes the still-`pending` row as `orphan_gc` (`app.py:392-393`, `audit._still_open`); a kill after `commit` but before the audit update leaves an entry listed while the row's `past_session` stays `none` (`reconcile_pending` sees no marker). — Triage: Fix-now; Decision: Applied (both docs restate the three crash points exactly; the row's later Delete now / expiry still records over `none`, `_PAST_SESSION_FROM`)
- **[MED]** MED-002: the retention in-memory row and flow 22 said an opened Past-sessions entry's transcript is decrypted at "Show transcript"; `PastSessionStore.read_entry` decrypts it on every open (`past_sessions.py:611`) and the tab holds it in `_open_entry` until close (`ui/past_sessions.py:395`). Flow 4's "coexist in memory only for the review window" missed the tab too (C9 class). — Triage: Fix-now; Decision: Applied (all three decrypted at open, "Show transcript" only displays; flow 4 names the opened entry)
- **[MED]** MED-003: `privacy-information.md` and the patient sheet said "Everything the program keeps is encrypted"; learned phrases and learned rules are plain-text config (retention rows 42/46), as are the settings files. — Triage: Fix-now; Decision: Applied (scoped to what is kept about an appointment; the privacy draft names the practitioner's plain-text learned phrases)
- **[MED]** MED-004: the patient document's withdrawal step said Discard destroys "everything made from it"; a draft already written to Cliniko, or pasted text, stays in Cliniko. — Triage: Fix-now; Decision: Applied ("destroyed on this computer"; anything already in Cliniko is removed there by hand)
- **[LOW]** LOW-005: threat model — "`reconcile_pending` — inside the Complete…"; the Complete calls `keep.commit`, `reconcile_pending` runs only from `sweep_with_archive` (`app.py:421`). — Decision: Applied
- **[LOW]** LOW-006: threat model — "Links and junctions are never followed anywhere in the store"; the archive ROOT is not checked (`past_sessions.py:346`). — Decision: Applied ("inside the store"; the root named as a boundary-2 residue and the location check's question)
- **[LOW]** LOW-007: residue (p) and the retention Audit rule — "a year before the audit existed would be pruned at the next start-up" (only a date > 7 years back is), and an untrusted pre-audit date is "the sweep's clock" (it is the creating update's `now`, `audit._date_from_epoch`). — Decision: Applied (both docs)
- **[LOW]** LOW-008: threat model listed `generated_text` among the AUDIT ROW's field names (it is `GeneratedRecord`'s). — Decision: Applied
- **[LOW]** LOW-009: THE CSV said "UTF-8"; it is UTF-8 with a BOM (`audit.py:790`). — Decision: Applied
- **[LOW]** LOW-010: EXCLUSIONS said "Every Windows call goes through an injected `WindowsLayer`"; the folder walk uses `os.scandir` and link checks directly. — Decision: Applied (the layer's calls named)
- **[LOW]** LOW-011: the hook line omitted `detail_code=main|thread|unraisable` and the silent thread `SystemExit`. — Decision: Applied
- **[LOW]** LOW-012: residue (j) and retention row 69 named "a Past-sessions entry or an untouched audit row from before this build" — both stores are new in this build. — Decision: Applied (session, log, profile and configuration files)
- **[LOW]** LOW-013: retention rows 61/63 and flow 22 said `generated.enc` is kept "whenever present"; an unreadable one is dropped (`session_store.py:1270-1273`), and row 61 omitted residue (r)'s regenerate-then-cancel lag. — Decision: Applied ("present and readable"; both residues named)
- **[LOW]** LOW-014: the retention Chrome-link row named one name source (the code and flow 22 use three), row 63 named only "Discard and expiry" as pre-key removers (also `discard_recovered`, the recovery list and a dead key's `orphan_gc`), and flow 22 omitted `discard_recovered`. — Decision: Applied
- **[LOW]** LOW-015: C10 — the privacy draft cited the state Acts for ACCESS, a correction right and the Notifiable Data Breaches scheme, none in the plan's research; the patient sheet's Cliniko row cited only VIC/NSW/ACT. — Decision: Applied (beyond-research items marked **[Reviewer: …]** in the privacy and downtime drafts; the patient row adds "Elsewhere in Australia, the Australian Privacy Principles apply")
- **[LOW]** LOW-016: the downtime draft said names stay hidden "until you choose a retention setting again"; the retention save keeps `hide_names=True` (`ui/past_sessions.py:574,630`). — Decision: Applied (names stay hidden until Hide names is unticked)
- **[LOW]** LOW-017: C9 class — the downtime draft ("Discard … nothing is kept") and CHANGELOG ("Discard and expiry never keep anything") miss the audit row (`session.py` `record_deletion`). — Decision: Applied (both name the content-free row)
- **[LOW]** LOW-018: the consent script said the app keeps "the time you ticked it"; `unlinked_consent` / `linked_consent` stamp the Start press (`encounter.py:174-185`). — Decision: Applied
- **[LOW]** LOW-019: the downtime quick-reference quoted the Start refusal without the `AuditWriteError:` type name the screen shows. — Decision: Applied (verbatim; the README's identifier rule now allows a word-for-word screen quote)
- **[LOW]** LOW-020: AGENTS.md's practice pointer says the README states the documents' rules (banner, every state, plain English, no unbacked claim); it did not. — Decision: Applied (README "Keeping these documents")
- **[LOW]** LOW-021: AGENTS.md Current Status ("NEXT: PLAN.md Phase 6 … planned in Plan Mode"), Last Session ("Next priority: plan PLAN.md Phase 6") and the Tech Stack "Database" row predate the build. — Triage: Routed (the spawn forbids rewriting Current Status / Last Session; the composer's `/document` after the smoke — already e1 discrepancy (6)); Decision: Recorded, no edit
- Checked TRUE (coverage): the entry layout, key description, AADs, label fields, mock rule, C1 ordering and both error lines, the non-Complete destroyer list in the threat model, reconcile on a confirmed-absent key only, `clean_staging` under "never", name resolution and fallbacks, the tab's NoTextInteraction / Copy gating / Hide names / two-click Delete now / lowering confirmation / unreadable-settings behaviour, `failure_reason`, the retention options (2557 days) and sweep cadence, the audit layout / fields / `extra="forbid"` / begin-vs-update / reset name / prune, CSV columns and formula guard, the three WER values and `--unregister`, the location and WER checks and their exact lines, `QuietHandlerErrors`' line, faulthandler, `lastResort`; the banner on all five practice docs; `recording-consent-v1` / `patient-info-v1` consistent repo-wide; the consent tick text verbatim (`encounter.py:86`, `panel-view.ts:35`); no "Cliniko Scribe"; `RETENTION_WARNING`, the intended-use line, the Complete lines, `PAST_SESSION_WRITE_FAILED_TEXT`, the Delete-now and confirmation buttons and every quoted exclusion line verbatim; the changed UI constants used at every call site and pinned literally. Widened C9 grep (≈25 terms + ≈25 variants over docs/, PLAN, AGENTS, CHANGELOG, `desktop/src`, `extension/src`): ≈140 hits judged true; only LOW-017 / MED-002's flow-4 sentence / LOW-021 false; `extension/src` has no Past-sessions or audit text.
- Finding verification: 27 candidates; 4 merged (the (o) residue from two lenses, the C9 Discard hits, the name-source / destroyer-list nits, the dating nit from two lenses), 2 dropped (the design-system "behind Show transcript" line describes DISPLAY and is true; the README's "APP 12 access applies everywhere" is backed by the plan's Goal line 47)
- Round classification: 4 ⚡ / 17 🆕 / 0 🔁 — not yet converged (4 MED)
- Fix-delta self-check: PASS — re-read every applied hunk in `threat-model.md`, `retention-schedule.md`, `data-flow-map.md`, `docs/practice/*.md` and `CHANGELOG.md`; each new claim re-checked against the cited code line; no code, string or test changed (the green run stands)
- Verification: docs only since the green run; no pytest needed

### Round 26 - 2026-10-01 - Phase 5 confirmation of round 25 + deeper pass over the lighter-covered docs, /review-loop round 2 of 3 (stage-5 executor, in-session)

- Round status: Closed (all applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with two read-only subagent lenses — (1) every round-25 fix re-checked against the code, with residue (o) walked through each crash point of `complete_session` and the start-up order `clean_staging` → `sweep_sessions` → `reconcile_pending` → `record_sweep_results`; (2) a deep truth pass over `clinician-review-guide.md`, `intended-use.md`, `incident-process.md`, `PLAN.md`, `phase-history.md` and `design-system.md` — every candidate re-verified in-session)
- Post-fix regression check: round 25's 20 applied fixes confirmed correct against the code (residue (o): kill A → `orphan_gc` + `archived`; kill B → `orphan_gc` + `none`, entry listed; kill C → `pending` + `none` (or `archived` when the commit was deferred) — both docs say exactly this; the sweep/reconcile order does not change it). No regression; three fixes had unfixed SIBLINGS (LOW-022..024 below).
- Findings (all doc-only):
- **[LOW]** LOW-022: flow 22 still said "Every Windows call goes through one injected layer" (round 25 LOW-010's sibling); AGENTS.md's exclusions pointer (added this phase, so in scope) said the same. — Decision: Applied (both name the layer's calls; the walk uses `os.scandir`)
- **[LOW]** LOW-023: flow 22 still said "UTF-8 CSV" (LOW-009's sibling). — Decision: Applied (byte-order mark)
- **[LOW]** LOW-024: flow 2's hook line still lacked `detail_code` and the silent thread `SystemExit` (LOW-011's sibling). — Decision: Applied
- **[LOW]** LOW-025: the patient sheet's Discard sentence still overclaimed "everything made from it" — a note already copied stays on the clipboard, and phrases learned from an already-saved note stay in the plain-text settings (retention rows 42/46). — Decision: Applied (audio, transcript and notes on this computer; the Cliniko text, the clipboard and the learned phrases named)
- **[LOW]** LOW-026: residue (o)'s first clause and its retention sibling were unbounded ("a Complete killed after its key deletion is never recorded as completed" — a kill after `record_completion` is recorded). — Decision: Applied ("… but before its own audit update")
- **[LOW]** LOW-027 (verified LOW; proposed MED): `incident-process.md` told the reader to close `scribe-app` then reopen it to export the audit CSV — but start-up runs `audit.prune()`, the 24 h sweep and the Past-sessions retention sweep BEFORE the window shows (`app.py:573-574`, `:602`), which can delete the incident's entry under a short setting and expire the session holding `write.enc`; the wrong-note step 2 ("leave it on the Transcript screen") did not say the app's close bounds that to the 24 h expiry. LOW because the evidence that matters most (the audit row, Cliniko's history) survives a relaunch. — Decision: Applied (export BEFORE closing; what a relaunch runs; copy the data folder aside as encrypted evidence first when the entry or session matters; the wrong-note step names the 24 h bound)
- **[LOW]** LOW-028: the review guide's blocking example "a dose that does not match the transcript" — only an EXCLUSIVE-state dose conflict blocks; most dose differences are review-graded (`note_check.py:69-74`). — Decision: Applied
- **[LOW]** LOW-029: the review guide said "The app only takes words from the transcript" and "never fills in … that was not said" — proposals and config pre-fills need not have been said (`ui/note.py:76-82`). — Decision: Applied (both qualified)
- **[LOW]** LOW-030: the review guide's "delete the note and write it yourself" did not say Past sessions still keeps the transcript and first draft (`session_store.py:1258-1294`); the Complete bullet omitted that retention deletes run only while the app runs. — Decision: Applied (Delete now named; the while-running clause added)
- **[LOW]** LOW-031: "every Complete keeps the transcript, the saved note and the generated note" stated unqualified in `intended-use.md`, PLAN.md (lines 48, 152), CHANGELOG, the threat model's REVERSAL and the retention intro (a delete-note path keeps no saved note; an unreadable `generated.enc` is not kept; a mock keeps nothing). — Decision: Applied (class swept by grep `(every|each|all) (non-mock )?Complete … (saved note|the notes)`; all six qualified)
- **[LOW]** LOW-032: design-system "No secondary windows beyond…" missed the Practitioner tab's sample-note file picker (`ui/practitioner.py:1184`) and the two start-up boxes (`app.py:348,353`). — Decision: Applied
- Noted for convergence (not a finding): `phase-history.md`'s Phase 5 line names no review rounds — added with the loop's final counts.
- Checked TRUE: every round-25 fix (list in the confirmation lens); all quoted UI strings in the six docs verbatim; the intended-use line on both tabs; Save's refusal rules; the Past-sessions tab behaviour; the audit fields; phase-history's round and suite numbers against Review History and the COMPOSER close bullets; no internal identifiers in the practice docs beyond the verbatim `AuditWriteError:` screen quote.
- Finding verification: 12 candidates; 1 merged (AGENTS pointer into LOW-022), 0 dropped; LOW-027 downgraded MED → LOW (reasoned above)
- Round classification: 0 ⚡ / 8 🆕 / 3 🔁 (LOW-022..024 are round-25 fixes' unfixed siblings, not fix-induced regressions) — CONVERGED (0 CRIT / HIGH / MED survivors)
- Fix-delta self-check: PASS — re-read each applied hunk; every new claim checked against its cited code line; no code, string or test changed
- Verification: docs only since the green run; no pytest needed

### Round 27 - 2026-10-01 - Phase 5 slice A (security docs, C9 rewrite, strings), independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (all four applied by the executor, LEG 2, each closing its class; docs only)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Phase-5 slice A documentation, C9 reversal statements, changed strings and literal pins, verified against the scoped implementation; read-only, no tests or network.

#### Findings

- **PR-MED-022** (MED, docs-only, `docs/security/incident-process.md:80`): The evidence-copy instructions overstate encryption of the entire application folder; the indexing row repeats the same overstatement. — Evidence: the incident instructions say the whole folder copy “holds encrypted files only”; `docs/security/retention-schedule.md:69` says “the files it covers are already encrypted.” However, `desktop/src/scribe_desktop/logging_setup.py:469` places logs at `Path(base) / "ClinikoScribe" / "logs"`, and lines 500–501 create `_QuietRotatingFileHandler(... encoding="utf-8")` without encryption. `desktop/src/scribe_desktop/past_sessions.py:875` also serialises settings as plaintext JSON: `(self.model_dump_json(indent=2) + "\n").encode("utf-8")`. Recommendation: Fix-now — limit the encryption claim to encrypted stores and explicitly acknowledge plaintext files in the whole-folder evidence copy and indexing scope. /fix decision: Applied (executor LEG 2, 2026-10-01T15:32:15+10:00): `incident-process.md` step 4 now names the encrypted stores AND the plaintext files a whole-folder copy carries (logs, `clinics.json`, everything under `config\` incl. the learned phrases/rules and both settings files, `app.lock`, the registration files; `models\` may be left out) and says to keep the copy as carefully as the original; retention row 69 says most covered files are encrypted but the logs, `clinics.json` and `config\` are plaintext, so the attribute is their only indexing control. Class siblings (practice docs): `downtime-procedure.md`'s location warning ("the app's encrypted files may be copied off"), its indexing warning ("harmless (the files are encrypted)") and its lost-computer bullet now name the plain settings, learned phrases, clinic list and logs (readable from the disk without full-disk encryption). Plaintext set enumerated from the code: `logging_setup.py:469` (logs), `clinics.py:335` (`clinics.json`), `note_config.py:914` (`config\`: clinician config, cue/rule files and sidecars, `practitioner_settings.json`), `past_sessions.py:106` (`config\past_sessions.json`), `app.py:252` (`app.lock`), plus `models\` (static) and the register script's manifest/host copy; encrypted: `sessions\`, `past_sessions\<id>\`, `audit\`, `profile\`, `style\`. Checked and left: the patient sheet / privacy draft (scoped in round 25 to what is kept about an appointment — true).

- **PR-MED-023** (MED, docs-only, `docs/testing/shipping-gate.md:19`): The preparation instructions retain the old promise that Complete destroys the transcript and note, contradicting the amended custody section. — Evidence: “the session's audio, transcript and note live under its session key and are destroyed cryptographically at Complete or Discard.” In `desktop/src/scribe_desktop/session_store.py:1293`, the archive source retains `transcript_plain=transcript_plain` and, at lines 1294–1295, the saved/generated note bytes; line 1298 calls `keep.write(source)` before line 1302 calls `delete_session_key(session_dir)`. Mock consultation content processed with real providers does not make this a mock-provider session. Recommendation: Fix-now — distinguish destruction of the session copy from the transcript and notes retained in Past sessions, including consented recordings used for this gate. /fix decision: Applied (executor LEG 2, 2026-10-01T15:32:15+10:00): `shipping-gate.md:19` now says the SESSION copy is destroyed at Complete or Discard, a Complete first keeps transcript and notes in Past sessions and every session leaves an audit row, and mock CONTENT is not a test-provider session (a consented recording used for the gate is kept until Delete now or expiry). Class siblings on the same page: Custody's "Complete or Discard destroys it" → "destroys that session store"; Custody's "a mock session keeps no entry" (ambiguous between mock content and the test provider) → a mock-content session ended by Discard keeps none, one Completed does, only a `mock-…` provider keeps nothing. Swept (grep `(transcript|note)… (destroyed|deleted|gone) … Complete` and `Complete (or|and|/) Discard` over docs, PLAN, AGENTS, `desktop/src`): no other false hit — `shipping-gate.md:28` and `speaker-measurement.md:11` name the AUDIO only (true); AGENTS.md:61 is Current Status history (true, and out of edit scope).

- **PR-MED-024** (MED, docs-only, `docs/security/retention-schedule.md:54`): The encounter-record row incorrectly confines every patient name to a session-lifetime record. — Evidence: the row concludes “the patient id and every name stay only here,” while its opening correctly says the encounter record contains “never a name or other display text.” `desktop/src/scribe_desktop/past_sessions.py:400` instead sets `patient_name=label.patient_name` in the archive label, which is encrypted into `LABEL_FILENAME` at line 416. Recommendation: Fix-now — state that the patient id remains in the encounter record, while the display name can persist separately in the Past-sessions label under archive retention. /fix decision: Applied (executor LEG 2, 2026-10-01T15:32:15+10:00): retention row 54 now ends "the patient id stays only here, and this record never holds a name: the patient's display name, held in memory for the session, is written at its Complete only into the Past-sessions entry's encrypted label". Class swept (grep `every name|name… only|only in (memory|encounter)|name… never (written|persisted|stored|kept)|display value that no` and every `patient('s)? name` line in `docs/security/`): the threat model's scope note (35-40), THE NAME, intended-use 117-119, retention rows 50/58/63 and flows 18/22 already name the label as the one place at rest; no other sibling.

- **PR-LOW-025** (LOW, docs-only, `docs/testing/shipping-gate.md:13`): The copy-flag description omits its new Past-sessions surface. — Evidence: “The flag never widens what is copyable beyond the single ratified note on the Note tab.” Yet `desktop/src/scribe_desktop/ui/past_sessions.py:477` gates archive copying with `copy_enabled=models.COPY_TO_CLINIKO_ENABLED`, and line 488 copies `_place_note_text(models.format_note_body(entry.saved_note))`. Recommendation: Fix-now — include copying a kept saved note from Past sessions and its existing eligibility checks. /fix decision: Applied (executor LEG 2, 2026-10-01T15:32:15+10:00): `shipping-gate.md:13` now names the Past sessions tab's "Copy saved note" under the same flag, its three refusal reasons (`past_sessions_view.copy_unavailable_reason`: flag off, no saved note, unresolved error; the button disabled with the reason as tooltip, `ui/past_sessions.py:801-802`) and its display-only panels, and bounds the flag to "a ratified note: the one on the Note tab, or a kept saved note". Class swept (grep `copyable|single ratified note|every cop(y|ies) of note text|only cop(y|ies)` over docs, PLAN, AGENTS, CHANGELOG): threat-model surface 4 (476-486), retention row 38 and the AGENTS Copy pointer already list the third caller; `design-system.md`'s "Every copy of note text — …" enumeration omitted it → added; CHANGELOG 152/174 and phase-history 11 are dated history (true when written).

- Verification counts: 4 claims checked, 4 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T15:32:15+10:00)
- PR-MED-022: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed: the logs (`logging_setup.py:469`, plain UTF-8 handlers), `config\past_sessions.json` (`past_sessions.py:875`), `clinics.json` (`clinics.py:335`, ids + contact email) and the learned phrases/rules under `config\` (`note_config.py:914`) are plaintext; an incident copy described as "encrypted files only" would be mishandled. Class: 2 security-doc + 3 practice-doc sites.
- PR-MED-023: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed: `complete_session` writes the archive (`session_store.py:1293-1300`) before `delete_session_key` (1302); the mock test is the provider name's casefolded `mock` prefix (`_is_mock_session`), not the content, so a gate session Completed with `extractive-v1` is kept. Class: 2 more sites on the same page.
- PR-MED-024: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed: `past_sessions.py:400` writes `patient_name` into the label, encrypted at 416; the row contradicted its own opening and the Past-sessions row. Class: no other sibling.
- PR-LOW-025: materiality=behavioral severity=LOW surface=docs rec=Fix-now — confirmed: `ui/past_sessions.py:477` passes `COPY_TO_CLINIKO_ENABLED` to `copy_unavailable_reason`, and 488 places `format_note_body(entry.saved_note)`. Class: 1 more site (design-system enumeration).
Cap verdict: accept — docs-only — four confirmed doc truth fixes plus their in-class siblings (5 + 2 + 0 + 1), every one checked against the cited code line; no code, string or test changed, so the green 5247 run stands; slice B (the practice docs) and a confirmation of these fixes follow from the composer.
- PEER-ROUND-27 RESULT: 4 findings (CRIT 0 / HIGH 0 / MED 3 / LOW 1).

### Round 28 - 2026-10-01 - Phase 5 slice B (practice documents) and confirmation of round 27, independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (all three applied by the executor, LEG 2, each closing its class; docs only)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Five practice documents against scoped research and implementation; PR-MED-022/023/024 and PR-LOW-025 fixes confirmed closed within the reviewed scope; read-only, no tests or network.

#### Findings

- **PR-MED-026** (MED, docs-only, `docs/practice/privacy-information.md:54`): The privacy notice promises prevention of external copying and crash reporting where the agreed protection only warns and permits continued recording. — Evidence: “Nothing else leaves the computer” and “Windows does not collect crash reports about it.” However, `.cursor/plans/plan-privacy-professional-controls.md:55` specifies a check that “warns” about redirected storage and missing exclusions and “never refuses recording”; `docs/practice/downtime-procedure.md:112` likewise says “Recording still works.” Recommendation: Fix-now — describe the app’s own restricted network use separately from Windows protections, which depend on successful setup and resolving warnings. /fix decision: Applied (executor LEG 2, 2026-10-01T15:38:12+10:00): `privacy-information.md`'s "Where it goes" bullet now separates "the program itself sends nothing anywhere else" from Windows and other software: the crash-report exclusion and the indexing request hold once it is set up; it cannot stop backup or sync software; a missing exclusion or a redirected folder only WARNS and recording continues — the practitioner must fix the cause; a **[Practice: …]** placeholder for the computer's backup/sync settings. Class siblings: the patient sheet's and the privacy draft's "They are not sent to any cloud or online AI service" are now attributed to the program ("The program does not send them …"), since a OneDrive-redirected folder would sync the encrypted files. Swept (grep `nothing (else )?leaves|never leaves|does not collect crash|never indexed|not indexed|never backed up|out of Windows Search` + WER/crash-report absolutes over docs and PLAN): the security docs already state the warn-only, per-user, set-up-dependent shape (threat model EXCLUSIONS and residues (g)–(k), flow 22, retention rows 31/60/69 and the backup rule); `design-system.md:406` ("never leaves the app") is about the transcript's copy surface, true.

- **PR-MED-027** (MED, docs-only, `docs/practice/privacy-information.md:39`): The learning description overstates automatic exclusion of patient names and omits the weaker protection for practitioner-typed shorthand. — Evidence: “each phrase is checked automatically to leave out names, numbers, dates and medicine names.” The shipped consent text in `desktop/src/scribe_desktop/ui/models.py:2918`–`2920` explicitly says “wording you type yourself is refused only for numbers, dates and medication names, so keeping patient names out of your own shorthand is up to you.” Lines 2916–2918 also describe a shape check, not guaranteed removal. Recommendation: Fix-now — distinguish learned speech from typed shorthand and explain that the checks cannot guarantee exclusion of identifying information. /fix decision: Applied (executor LEG 2, 2026-10-01T15:38:12+10:00): `privacy-information.md` "How we use it" now follows `CONSENT_TEXT_V3` — phrases from lines the practitioner adds or moves, shorthand from wording they type; a shape check, not a meaning check; phrases from speech refused for names, numbers, dates and medicine names, typed wording only for numbers, dates and medicine names, so keeping patient names out of shorthand is the practitioner's; the check cannot guarantee nothing identifying is kept; style exemplars pass the same check unchanged and are shown first. Class swept (grep `names?, numbers?, dates|leave out names|refus… names|checked automatically` over docs and PLAN): data-flow flow 22's config paragraph (938-948), retention rows 42/46 and the threat model surfaces already state both filters and the no-name-check for typed wording; no other practice-doc description.

- **PR-LOW-028** (LOW, docs-only, `docs/practice/clinician-review-guide.md:101`): The regeneration instructions incorrectly promise preservation of the original rejected draft. — Evidence: “generate again” is followed by “Past sessions still keeps the transcript and the app’s first draft”; lines 107–108 repeat “what the app first produced.” In `desktop/src/scribe_desktop/session_store.py:919`–`930`, `write_generated` replaces the existing artifact: “a regeneration’s first body replaces the previous generation’s.” Completion copies that current artifact at lines 1271 and 1295. Recommendation: Fix-now — explain that Past sessions keeps the initial draft from the latest generation, when available, and regeneration replaces the earlier draft. /fix decision: Applied (executor LEG 2, 2026-10-01T15:38:12+10:00): the review guide's "If something looks wrong" bullet says generating again replaces the earlier draft and Past sessions keeps the most recent generation's draft (when it could be read back); its "Looking back" paragraph says the generated note is the draft as first shown in the most recent generation, an earlier generation is not kept, and "Generated note not kept" shows when there was none or it could not be read back (`ui/past_sessions.py:425-428` → `GENERATED_NOT_KEPT`). Class siblings: `intended-use.md` ("the note the app first generated"), CHANGELOG ("the note it first generated"), data-flow flows 4 and 22 and phase-history ("the first note body shown") now say a regeneration replaces it. Checked and left: threat model THE ARCHIVE ("replaced on regeneration") and retention row 61 (its lifetime column says so); the patient sheet's "the draft the program made" claims no "first".

- Verification counts: 8 claims checked, 7 confirmed, 1 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T15:38:12+10:00)
- PR-MED-026: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed: plan line 55 / `exclusions.startup_exclusions` only WARN (never refuse) on a redirected folder or missing WER values, the exclusions exist only once the register script ran from a normal terminal, and a `python.exe` launch is not excluded; "Nothing else leaves the computer" / "Windows does not collect crash reports" were absolute. Class: +2 practice-doc sentences.
- PR-MED-027: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed: `ui/models.py:2916-2920` (`CONSENT_TEXT_V3`) — a shape check; typed wording refused only for numbers, dates and medication names (`refuse_typed_wording`, no name check). Class: no other overclaiming site.
- PR-LOW-028: materiality=behavioral severity=LOW surface=docs rec=Fix-now — confirmed: `write_generated` replaces atomically (`session_store.py:919-932`); Complete copies the current file (1271, 1295); absent or unreadable shows `GENERATED_NOT_KEPT`. Class: +5 sites (intended-use, CHANGELOG, flows 4/22, phase-history).
Cap verdict: accept — docs-only — three confirmed practice-doc truth fixes plus 7 in-class siblings, each checked against the consent text, `exclusions.py` or `session_store.py`; no code, string or test changed (the green 5247 run stands); a codex confirmation round follows from the composer.
- PEER-ROUND-28 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 1).

### Round 29 - 2026-10-01 - Phase 5 confirmation of round 28's fixes, independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (applied by the executor, LEG 2, the class swept exhaustively; docs only)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-28 fix diff, current hunk contexts, practice/security class sweep and permitted implementation checks; PR-MED-027 and PR-LOW-028 fixes confirmed; PR-MED-026 remains incomplete as a class. Read-only; no tests or network.

#### Findings

- **PR-MED-029** (MED, docs-only, `docs/security/intended-use.md:34`): Absolute local-only assurances remain in intended-use and the spoken consent script, contradicting the corrected privacy notice’s distinction between program networking and Windows-side copying. — Evidence: “Audio and transcripts never leave the local machine”; `docs/practice/patient-information-and-consent.md:85` says “The recording stays on my computer — it isn't sent to the cloud”. However, `docs/practice/privacy-information.md:62` now acknowledges “It cannot stop backup or sync software copying its folder”; `docs/security/data-flow-map.md:1021` says the app “WARNS (never refuses)” for redirected storage, matching `desktop/src/scribe_desktop/exclusions.py:267` and `:354`. Recommendation: Fix-now — qualify both remaining assurances as the program’s own behaviour and preserve the setup-dependent Windows protections distinction. /fix decision: Applied (executor LEG 2, 2026-10-01T15:42:56+10:00):
  - `intended-use.md` "Not a cloud service": "The app never sends audio or transcripts off the local machine", then what it cannot control — Windows Backup, Volume Shadow Copy or a sync tool may copy its encrypted folder; it WARNS, never refuses, on OneDrive / network / roaming (threat-model residues (g), (k); flow 22).
  - The spoken consent script: "The program doesn't send it to the cloud, and the audio is deleted once I've finished the note." — short to say aloud; the caveat is carried by the written sheet.
  - Part A of the patient sheet: after the encryption bullet, "The program cannot stop the computer's own backup or file-sync software from copying these encrypted files; it warns your practitioner if its folder is in a place that is synced or shared, such as OneDrive or a network drive."
  - Siblings attributed to the program: the patient sheet's "The program keeps the transcript on that one computer only and makes no backup of it"; the privacy draft's "The program stores it on one computer only and makes no backup"; the review guide's "the app keeps it on this computer only, with no backup of its own (your own backup or sync software may still copy the encrypted files …)".
  - **`patient-info-v1` kept.** What the patient agrees to is unchanged: recording, local processing, audio deleted, transcript and notes kept encrypted for the set period, practitioner review. The edit narrows an assurance to the program's own behaviour, and Part A already said so after round 28. The document is a draft that has never been issued (its banner forbids use before review), so no patient holds a v1 that differs.
  - **Left unchanged:** the app's `RETENTION_WARNING` (`ui/past_sessions_view.py:145`, "It is kept on this PC and this Windows login only, with no backup") is judged TRUE as a statement about the program. The program stores the transcript only there and makes no backup, and a third-party copy stays encrypted under keys bound to this Windows login. Residue (g) names those copies. Changing that string would be a code and pin change, so no MUST-PAUSE is needed.

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T15:42:56+10:00)
- PR-MED-029: materiality=behavioral severity=MED surface=docs rec=Fix-now — confirmed. `exclusions.py:267`/`:354` only warn, the location check cannot see Windows Backup, VSS or third-party tools (residue (g)), and both quoted sentences were absolute.
  - The sweep covered the composer's term list plus `stays? local|kept locally|computer only|this PC|only on (this|that|one|your)|lives on this computer|offline`, over `docs/**`, `PLAN.md`, `AGENTS.md`, `CHANGELOG.md` and `README*`: 70 + 11 hits.
  - FALSE, fixed: `intended-use.md:34-35` and `patient-information-and-consent.md:85-86` (the two named).
  - TRUE, wording attributed to the program anyway (patient/practitioner-facing "stored on one computer only"): `patient-information-and-consent.md:53`, `privacy-information.md:92`, `clinician-review-guide.md:119`.
  - TRUE as the PROGRAM's behaviour, left unchanged:
    - `AGENTS.md:4` and `PLAN.md:11` ("No cloud processing");
    - `data-flow-map.md:979` ("No cloud AI services; no telemetry");
    - `threat-model.md:1979` (ids to Cliniko by design);
    - every "offline" hit — the offline contract and env kill-switches in the threat model, data-flow map, PLAN, AGENTS, CHANGELOG, intended-use:99, incident-process:53, design-system:344, speaker-measurement:22 and phase-history;
    - "this PC and this Windows login only" (the Past-sessions storage and no-backup statements) in `intended-use.md:53`, retention rows 63/150/168, `threat-model.md:2761` (residue (c), with (g) beside it) and `design-system.md:478` (the verbatim `RETENTION_WARNING`).
  - UNRELATED, left unchanged: `CHANGELOG.md:60`/`retention-schedule.md:38`/`intended-use.md:148`/`data-flow-map.md:322`/patient-sheet `:116` (clipboard "stays on"); `threat-model.md:2332` (a session "stays on" the list); `design-system.md:392`/`:406`; `CHANGELOG.md:75`/`:130`; `threat-model.md:2317`; the cloud-HOST notes in `lessons.md:60`, `phase-history.md:19` and `AGENTS.md:56`; `cross-agent-orchestration.md`.
  - The app's user-facing strings and the shipped consent texts make no absolute claim (composer pre-check, re-checked: `ui/models.py`, `extension/src/`).
Cap verdict: accept — docs-only — the two named sites fixed and the class closed by an exhaustive sweep with every hit judged. Three more sentences were attributed to the program; no UI string, consent text or pin changed. `patient-info-v1` is kept (the agreement is unchanged and the draft was never issued). The green 5247 run stands.
- PEER-ROUND-29 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

### Round 30 - 2026-10-01 - Phase 5 confirmation of round 29's fix, independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed for the build (Part A applied, string + pin; Part B — the current consent text — an OPEN practitioner decision, residue named; see the handoff note's "PRACTITIONER DECISION (PR-MED-030 consent wording)"). Part B DECIDED (a) by the practitioner 2026-10-02.
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-29 diff, current hunk contexts, permitted wording sweep and implementation checks. The four-document fix aligns the network/backup distinction with the data-flow map; the spoken script remains natural, introduces no internal identifier, and retaining `patient-info-v1` is consistent with the recorded unissued-draft status. The unchanged-assurances verdict is not confirmed. Read-only; no tests or network.

#### Findings

- **PR-MED-030** (MED, behavioral, `desktop/src/scribe_desktop/ui/models.py:2910`): PR-MED-029 remains incomplete as a class: the current practitioner consent and documented retention warning still make absolute local-only assurances. Their wording does not distinguish program behaviour from external copying, and encryption restricts access rather than preventing copies. — Evidence: current `CONSENT_TEXT_V3` says “Everything it learns is stored on this computer only, and nothing leaves it.” `docs/design-system.md:478` quotes the retention warning: “It is kept on this PC and this Windows login only, with no backup.” Yet `desktop/src/scribe_desktop/exclusions.py:90` explicitly warns that a network location means “its files are kept off this computer”; `:269` only appends that warning. `docs/security/data-flow-map.md:1025` also states that the app does not exclude itself from Windows Backup, Volume Shadow Copy or third-party backup tools. These contradict round 29’s assertion that the shipped consent makes no absolute claim and its justification for leaving the retention warning unchanged. Recommendation: Fix-now — qualify the current consent and retention warning as the program’s own processing/storage and absence of an app-managed backup, acknowledge external copying and redirected storage, update their documentation mirrors, and apply the established consent-version procedure when changing the shipped consent. /fix decision: Applied (Part A) / Deferred to practitioner decision (Part B: CONSENT_TEXT_V3 unchanged, residue named) — executor LEG 2, 2026-10-01T15:47:47+10:00:
  - **Part A, applied.** `ui/past_sessions_view.py` `RETENTION_WARNING` now reads "… request or a subpoena. Clinic Scribe keeps it, encrypted, only in this Windows login's data folder and makes no backup of its own - but backup or sync software, or a folder location it has warned about, can still copy the encrypted files. Cliniko stays the system of record." The literal pin `test_ui_screens.py` (the Past sessions intended-use / retention-warning test, ~8767) was updated in the same change, and the label test (`retention_warning_label.text() == view.RETENTION_WARNING`) is unchanged. The `docs/design-system.md` mirror is updated and notes that the warning states the PROGRAM's behaviour. Its law citations are unchanged, so `docs/practice/` needs no change.
  - **Part A sweep.** Every user-facing string in `desktop/src/scribe_desktop/ui/` and `exclusions.py`, and `extension/src/` (non-test), was checked once more against wide terms: "this PC", "this computer", "this Windows login", "only on", "no backup", "nothing leaves", "never leaves", "stored on", "stays on", "the cloud", "offline", "not/never/nothing … sent/uploaded/leave", "locally".
    - Fixed: none other.
    - True as the program's behaviour: `exclusions.py:87`/`:90` (warnings that themselves say the folder can be copied off / is kept off this computer); `style_review.py:76` ("Saving writes the learned style, encrypted, on this computer"); `ui/clinics.py:133`; `models.py:366`, `:869`, `:1232`, `:1566` ("Unreviewed recordings stay on this computer until their 24-hour window closes" — the program's own retention); `models.py:3970`; `microphone.py:116`/`:380` ("Transcription is always local … no cloud fallback" — processing location); `models.py:2932` (the consent checkbox label: where the program stores the fingerprint; consent UI, left with Part B).
    - Historical, not to be edited: `models.py:2880`/`:2896` (`CONSENT_TEXT_V1`/`V2`, kept verbatim as history).
    - `extension/src/`: no hit.
  - **Part B, deferred.** `CONSENT_TEXT_V3` (`models.py:2910`) is unchanged. The residue is written into the threat model's practitioner-profile surface 9 and the retention rows for learned phrases (42) and learned rules (46). The sentence is true of the program, which writes learned data only under this login's `%LOCALAPPDATA%\ClinikoScribe` and sends none of it anywhere. It does not guard against copies made by backup or sync software, or by a folder that has been redirected. The learned phrases and rules are plain text, so such a copy is readable. The option brief is in the handoff note.

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T15:47:47+10:00)
- PR-MED-030: materiality=behavioral severity=MED surface=production rec=Part A: Fix-now — confirmed. The retention warning said "It is kept on this PC and this Windows login only, with no backup". `exclusions.py:90` itself warns that a network-drive folder keeps the files off this computer, the check only warns (`:269`), and nothing excludes Windows Backup, VSS or third-party tools (`data-flow-map.md` non-flows). Round 29's "true for the program" verdict was too generous for a user-facing absolute: encryption limits who can read a copy, not whether a copy is made. Part B: practitioner decision, recommend (a) — `CONSENT_TEXT_V3`'s "Everything it learns is stored on this computer only, and nothing leaves it" is likewise absolute, and the plain-text learned phrases and rules make an external copy readable. But the sentence is true of the PROGRAM's own storage and network behaviour. Correcting it means consent-v4: both stores' records go stale, the practitioner must re-consent, and own-voice refuses until they do (30 `consent-v3` / `CONSENT_TEXT_V3` hits across 15 files: `ui/models.py`, `practitioner_profile.py`, `encounter.py`, `ui/practitioner.py`, four test files and seven docs). A single-practitioner install whose redirection and WER state the app already warns about does not justify that cost now. Name the residue (done) and fold the corrected wording into the next consent version.
Cap verdict: accept — production-behavioral — Part A is a one-string user-facing fix with its literal pin updated (ruff clean, mypy 56 files; composer pytest owed: `test_ui_screens.py`), and the sweep found no other non-consent string. Part B is not a build defect left open: it is a practitioner wording decision, with the residue recorded in the threat model and retention schedule and surfaced at the batched smoke. Peer_round 4 of 5.
- PEER-ROUND-30 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

### Round 31 - 2026-10-01 - Phase 5 confirmation of round 30's fix, independent cross-family codex peer review (pass stage-5.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-30 fix diff and current hunk contexts, permitted UI-string sweep, and specified plan entries. Part A’s qualified warning, literal pin and documentation mirror agree. Part B records the encryption/plaintext distinction, external-copy residue and both practitioner options, including re-consent consequences; that decision remains open. No new issue verified within the permitted reads. No files written, tests run or network commands used.

#### Findings

- Verification counts: 2 claims checked, 2 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
- PEER-ROUND-31 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 32 - 2026-10-01 - Hardening H1: Phases 1–5 as ONE surface, /review-loop round 1 of 3 (stage-6 executor, in-session)

- Round status: Closed (all 13 applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a four-lens read-only subagent fan-out over the cross-phase seams — (A) C1 ordering end to end over every key-destroying path and every crash window, with the sweep-vs-Complete concurrency question; (B) C2 over every audit call, `app.main`'s start-up order and each step's failure, the periodic sweep, the hourly `label.enc` decrypt and the shared store; (C) D5 name-to-session matching, Hide names and the D6 path matrix with D1's verification; (D) docs vs code at the seams after the post-doc code fixes of rounds 21–24 and 30 — every candidate re-verified in-session against the cited lines before triage)
- Primary review baseline: HEAD `1e564b4` + the working tree's Phase 1–5 changes (the whole plan surface: `git diff HEAD` and the untracked `audit.py`, `past_sessions.py`, `exclusions.py`, `ui/past_sessions.py`, `ui/past_sessions_view.py`, `docs/practice/`, their tests); the suite green at 5247 passed / 4 skipped.
- Findings:
- **[LOW]** LOW-001: `past_sessions.py:839-843` — `_remove_key_first_unless_link` routed through `_is_link`, whose "an error counts as a link" made an UNINSPECTABLE entry path "not ours, nothing to remove" → True, the non-Complete destroyer's go-ahead to delete the SOURCE key while a `pending` entry stayed for `reconcile_pending` to commit (a discarded session listed for ever). Reachable where `Path.is_symlink` re-raises non-ENOENT errors (Python 3.12, which `requires-python` admits and CI runs). — Triage: Fix-now; Decision: Applied (its own tri-state check: an error → False, the key stays; a confirmed link → True untouched; else `_remove_key_first`). Siblings searched (`_is_link\(`): the other six uses fail toward skip / refuse / `not_found`; the staging-side call is harmless (staging is never committed).
- **[LOW]** LOW-002: `session_store.py:1276-1279` — a MOCK Complete deleted the key without removing an entry an earlier NON-mock attempt for the same id had published (its key deletion then failed): reconciliation would commit it, breaking "one entry per id" and leaving the row `not_kept_mock` beside a listed entry. Latent (no shipped UI builds a mock note provider, and the transcript's model is fixed), but a C1 destroyer hole. — Triage: Fix-now; Decision: Applied (`ArchiveKeeper.drop_unfinished` → `remove_pending_entry`, key-first BEFORE the key; False raises `ArchiveWriteError`, key retained). Siblings (`keep is not None|past_session = `): the only other no-write branch is `keep is None` (tests only).
- **[LOW]** LOW-003: `app.py:477-492` — `PeriodicSweep.__call__` ran its steps unguarded: `sweep_sessions`' `root.iterdir()` (outside its own `try`, `session_store.py:1735`) raising on an unlistable sessions root skipped the audit prune AND the Past-sessions retention deletion (a privacy control) for as long as the error lasted. — Triage: Fix-now; Decision: Applied (each of three steps — session sweep + reminders + re-list, audit prune, retention — runs whatever an earlier one raised; the first failure is raised again for the type-name hook). Sibling: start-up `run_sweep()` raising ends the process before the window — pre-existing fail-closed, unchanged.
- **[LOW]** LOW-004: `past_sessions.py:660-665` — the lessons.md:91 class: an entry whose label cannot be read was unwrapped again on EVERY hourly tick (D9's broken DPAPI makes that every entry, on the GUI thread; a corrupt label puts its entry key in memory each hour); and `delete_entry` dropped the cached date BEFORE a failing key removal, so a stuck entry was re-decrypted each tick. — Triage: Fix-now; Decision: Applied (`_undated` remembers the failure; retried after `UNDATED_RETRY_INTERVAL` = 24 h, or at once if the wall clock went back; still counted undated — kept — every tick; dropped with the date cache's rule; the date popped only after a successful delete). The round-17 pin `test_an_undated_entry_is_read_again_next_tick` became `…_a_day_later` + a clock-back test + a failed-delete test. Retention-schedule "Fail toward keeping" updated.
- **[LOW]** LOW-005: `ui/bridge.py:663-672` — D5: a name found by a mid-recording Verified re-check (Start made `unverified_offline`) was lost once the session was QUEUED and another reconnect (or a Replace key) ran `_reverify_live`, which clears `_live_check` outside the capturing states — the entry read "Name not available". Never the wrong name (all matched on session id). — Triage: Fix-now; Decision: Applied (`_recheck_display`, set when a live re-check is accepted Verified, read by `live_display_name` after the Start display, cleared in `_tick` when its session ends; never published to Chrome; `_live_check` / write-back semantics unchanged). Threat model THE NAME and flow 22 updated.
- **[LOW]** LOW-006: `test_integration_no_sockets.py:349,364-368` — the child's comment said the hooks go in "first, as app.main"; the child sets the offline env first, and it omitted `window.reconstruct_reminders()`. — Triage: Fix-now; Decision: Applied (comment states the real order and why it is socket-neutral; the call added)
- **[LOW]** LOW-007: residue (o) and the retention Audit-record residues named only the Start and Complete crash windows; a Discard / `discard_recovered` / recovery-list Discard (`session.py:1438-1443`, `:1734-1737`, `ui/recovery.py:477-486`) or a 24 h expiry (`record_sweep_results` after the whole pass, `app.py:562-569`) killed between key and audit update is never recorded as such. — Triage: Fix-now; Decision: Applied (both docs)
- **[LOW]** LOW-008: `audit.prune` (`audit.py:753-770`) trusts the wall clock; a clock jumped forward ≥ 7 years removes every month at the next start-up or 24 h tick, irreversibly — unnamed (residue (p) named only a clock wrong AT Start). No guard: a real 7-year gap is indistinguishable. — Triage: Fix-now (docs); Decision: Applied (residue (p) + the retention Audit rule)
- **[LOW]** LOW-009: `retention-schedule.md:146-152` paraphrased the pre-round-30 warning ("this PC and this Windows login only with no backup"), contradicting `RETENTION_WARNING` (`ui/past_sessions_view.py:141-149`) and the design system. — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-010: AGENTS.md's audit pointer — "a new field must be pattern-constrained and its name added to `_PAYLOAD_SIGNATURES`": only `past_session`, `note_provenance`, `consent_confirmed_at` are registered (`logging_setup.py:252-267`); the rest are tripwired through those whole-row names. — Triage: Fix-now; Decision: Applied (states the real mechanism and when a new name is needed)
- **[LOW]** LOW-011: AGENTS.md's audit pointer missed `record_sweep_results`, `_on_write_requested`, the tab's Delete now and `past_sessions_view.retention_sweep`. — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-012: flow 22 attributed the pre-send refusal codes to `_store_write_record`; they go through `AuditLog.record_write_refusal` from `_on_write_requested` (`ui/main_window.py:1883`) and `_prepare_attempt` (`:2001`). — Triage: Fix-now; Decision: Applied
- **[LOW]** LOW-013: the retention `pre_audit` rule said a row is made when a session is "first completed, discarded or swept"; any first update creates it, incl. a draft-write transition or refusal (`audit.py:610-615`, `ui/main_window.py:2083-2098`). — Triage: Fix-now; Decision: Applied
- Checked TRUE (coverage, per lens): every key-deleting path enumerated from the code (`delete_session_key|discard_session|before_destroy|remove_pending_entry|reconcile_pending|clean_staging|complete_session\(|rmtree`) — Start-failure cleanup (fresh id), `discard()` (entry removed under the same lock before the reservation), `discard_recovered`, the recovery list, sweep `expired` and dead-key `orphan_gc` (both `before_destroy` first, False/raise → `error`, key kept), confirmed-absent `orphan_gc` (no callback, commits); all five Completes through `_complete_locked` → `complete_session` with UNCLEARED and note verification first; post-boundary never raises; retry replaces key-first; reconcile commits on `FileNotFoundError` only; directory name vs header id refused; C5 — the start-up sweep and `PeriodicSweep` run on the GUI thread, every Complete/Discard caller is a GUI slot (Chrome via `QueuedConnection`), so `clean_staging` / reconcile / retention cannot interleave a `write_entry`. C2 — `begin` is the only raising call (`session.py:830`), `record_start_failed` inside `except BaseException`, every `record_*` builds only a closure before `update`'s guard, `prune` catches everything, the tab wraps `key_unreadable` / `row_for` / `export_csv` / `reset`. Start-up order (`app.py:516-635`) matches the docs; unreadable audit key / archive root / settings each skip nothing they must not. ONE `PastSessionStore` shared by controller, window, tab, recovery and the sweep; `sweep_past_sessions` never called in `src`; "never" decrypts nothing; cadence on `monotonic`. D5 — every source matched on session id; label resolved at the click before the lock; adopted / recovered / back-to-back cannot cross names; a None bridge guarded; the name only in `label.enc`. Hide names masks list rows and the opened heading; the opened entry is cleared on Delete now, expiry, leaving the tab and refresh. D6 matrix and D1 verification as planned (three mock discriminators via casefolded `mock` prefix). Docs: `QuietHandlerErrors`' line, native-host hooks, faulthandler, exclusions conditions and lines, WER values, audit layout/fields/CSV, Past-sessions strings verbatim, residues (o)/(p) against the code paths, `docs/practice/` claims.
- Round classification: 0 ⚡ / 13 🆕 / 0 🔁 — every finding is a cross-phase seam no per-phase round could see (pre-existing); 0 CRIT / HIGH / MED, so the loop's convergence rule is met — a confirmation round 33 of the fixes follows the composer's suite (lessons.md:92: never close a hardening fix on the fix alone).
- Finding verification: 14 candidates; 0 dropped; 1 merged (LOW-004's failed-delete sibling into LOW-004); 0 downgraded. Lens A's 3.12 version boundary for `Path.is_symlink` is unconfirmed from the stdlib here — the fix is correct either way.
- Fix-delta self-check: PASS — re-read every hunk: `past_sessions.py` (`_remove_key_first_unless_link`, `_undated` + `UNDATED_RETRY_INTERVAL`, `delete_entry` order, `_EntryKeeper.drop_unfinished`), `session_store.py` (`ArchiveKeeper.drop_unfinished`, the mock branch, docstring), `app.py` (`PeriodicSweep` split), `ui/bridge.py` (`_recheck_display`); ruff clean, mypy 56 files clean.
- Verification: pytest owed by the composer — new/changed tests in `test_past_sessions.py` (6), `test_audit.py` (1), `test_ui_bridge.py` (1), `test_integration_no_sockets.py` (child script).

### Round 33 - 2026-10-01 - Hardening H1: confirmation of round 32 + class closure, /review-loop round 2 of 3 (stage-6 executor, in-session)

- Round status: Closed (1 applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's full suite after round 32: 5254 passed / 4 skipped, ruff clean, mypy 56 files)
- Post-fix regression check (baseline: the round-32 pre-fix tree): every round-32 hunk re-read against its callers. LOW-001 — `Path.is_junction` exists from 3.12 (the floor); a missing entry still reads False → `_remove_key_first` → True. LOW-002 — `drop_unfinished` has ONE implementer (`_EntryKeeper`; `def commit\(self` has no test fakes); the mock refusal reuses `ArchiveWriteError` → `PastSessionWriteError` (wording "the copy could not be saved" is loose for a mock, which is unreachable in the shipped UI — not a finding). LOW-003 — a raise inside `_session_sweep` skips only the reminder prune and re-listing, which depend on it; `clean_staging` runs first and never raises; reconcile is skipped with it, but on an unlistable root its `_absent` would commit nothing anyway. LOW-004 — a clock jumped back re-reads at once and then waits again from the new time (no repeated reads); a forward jump only re-reads sooner; `undated` is still counted every tick, so the tab's kept-by-age line and LOW-020's decrement after Delete now (which pops `_undated`) are unchanged. LOW-005 — `_recheck_display` is read ONLY by `live_display_name` (grep `_recheck_display|live_display_name`: `ui/bridge.py` 4 sites, `ui/main_window.py:1639`), set only on the GUI-thread `_apply_result` for the current check and session, cleared by `_tick`; never in `_live_state` / `_block_state` / `view()` (Chrome) or a log; `KeepLabel` stays `repr=False`.
- Class sweeps: (1) "an inspection error read as absent / nothing-to-remove before a key deletion" — every key-deleting precondition re-enumerated: `sweep_sessions` (`stat` → `FileNotFoundError` only is absent; other `OSError` → `error`, key kept), `_remove_key_first` (`_is_link` error → refuse), `remove_pending_entry`'s staging side (`_staging_linked` error → staging skipped; a staging copy is never committed — only `_publish` renames, inside `write_entry`), `reconcile_pending` (`_exists` error → present; `_absent` `FileNotFoundError` only), `delete_session_key` (`missing_ok`, no precondition) — closed. (2) "a failing earlier step skips a later independent one" in the timers — `PeriodicSweep` is the only multi-step custody timer; `sweep_with_archive`'s `clean_staging` and `reconcile_pending` never raise; the start-up `run_sweep()` raise stays fail-closed (pre-existing). (3) "this PC / this Windows login only" (LOW-009's wording family) — 14 hits; all but the two consent-text sites state the PROGRAM's own keeping (round 29 PR-MED-029's judged class; the consent text is PR-MED-030 Part B, open) — no new finding.
- Findings:
- **[LOW]** LOW-001 (🔁 of round 32 LOW-001/002, docs follow code): the destroyer lists — threat model THE PAST-SESSIONS ARCHIVE (the mock line and the one-entry-per-id bullet), retention row 63, flow 22, AGENTS.md's Past-sessions pointer — did not name the mock Complete's pre-boundary removal, nor that an uninspectable entry path keeps the source key. — Triage: Fix-now; Decision: Applied (all five sites)
- Finding verification: 1 candidate; 0 dropped; 0 downgraded
- Round classification: 0 ⚡ / 0 🆕 / 1 🔁 — CONVERGED (0 CRIT / HIGH / MED; the round-32 fixes hold and their classes are closed)
- Fix-delta self-check: PASS — docs only; each sentence checked against `session_store.complete_session`'s mock branch and `past_sessions._remove_key_first_unless_link`
- Verification: docs only since the green run; no pytest needed

### Round 34 - 2026-10-01 - Hardening H2: /simplify over Phases 1–5 as one surface (stage-6 executor, in-session)

- Round status: Closed (all 6 applied as Fix-now; none substantial — no plan task added)
- Source: Claude Code simplify (`/execute-loop` executor `claude-opus-5-5`; two read-only subagent lenses — (1) the stores and controller: `audit.py`, `past_sessions.py`, the plan's parts of `session_store.py` / `session.py` / `app.py`; (2) the UI and exclusions: `ui/past_sessions.py`, `ui/past_sessions_view.py`, `exclusions.py`, `logging_setup.py`, `native_host.py`, `register-native-host.py`, the plan's parts of `ui/main_window.py` / `ui/transcript.py` / `ui/recovery.py` / `ui/note.py` / `ui/models.py` / `ui/bridge.py` — every candidate re-verified in-session under the conservatism guard)
- Findings (all LOW, behaviour-preserving, single-module):
- **[LOW]** SIMP-001: `session_store.py:1116` + `:1284` — `complete_session` parsed the whole `TranscriptDocument` twice per Complete (`_completion_facts` and the mock check), under the controller lock on the GUI thread. — Triage: Fix-now; Decision: Applied (parsed once; `_completion_facts` takes the `(model_name, speaker_model_id)` pair — its one caller; `_transcript_model_name` is pure and never raises)
- **[LOW]** SIMP-002: `past_sessions.py` — the date caches' drop rule (`_completed_dates.pop` + `_undated.pop`) hand-copied at four sites (write, remove-pending, keyless reconcile, delete). Pattern siblings searched (`_completed_dates\.pop|_undated\.pop`): those four; the sweep's own `_undated.pop` after a successful read and the whole-dict pruning are different operations. — Triage: Fix-now; Decision: Applied (`_forget_dates`, each call at its old position — `delete_entry`'s still after the successful key removal)
- **[LOW]** SIMP-003: `ui/main_window.py:300-304` — `MainWindow._past_sessions` was set and never read (grep `\._past_sessions\b` over src and tests: only the controller's and the recovery screen's own attributes); the store reaches the recovery list and the tab as constructor arguments. The `_audit` comment also claimed the recovery list reports through MainWindow's attribute. — Triage: Fix-now; Decision: Applied (attribute removed; comment says the recovery list and the tab are handed both directly)
- **[LOW]** SIMP-004: `ui/past_sessions.py:310-311`, `742-743` repeated `_recheck_audit_key`'s exact body; `:777`, `784`, `812` repeated the audit failure-count expression. — Triage: Fix-now; Decision: Applied (both sites call `_recheck_audit_key`; `_audit_failures()`)
- **[LOW]** SIMP-005: `ui/transcript.py` — the Complete-succeeded ending (clear, the deferred line or the path's line — Flow 3 step 4 — then `closed.emit`) hand-copied in `abandon_note_and_complete`, `on_complete` and `complete_written` (grep `COMPLETE_DEFERRED_LINE`: exactly these three). — Triage: Fix-now; Decision: Applied (`_show_completed(line, closed_as)`; `abandon_note_and_complete` now reads the deferred flag before `_clear()` instead of after — the same read, since only the controller's completion sets it and `_clear` completes nothing)
- **[LOW]** SIMP-006: `ui/past_sessions_view.py:293` — `sorted_listings` typed `Iterable` but iterates its argument twice (a generator would silently drop the unreadable entries); its one caller passes a list. — Triage: Fix-now; Decision: Applied (typed `Sequence`, the docstring says why)
- Consciously left alone: `reconcile_pending`'s `_exists` then `_absent` on a keyless entry (a redundant stat, but the explicit "confirmed absent" read is C1's legibility); `sweep_past_sessions` and `PastSessionStore.sweep` with no production caller (plan-named API, round 12 LOW-001's documented one-off; tests use `sweep`); `audit._start_failed` single-use wrapper (parallel to its siblings); `past_sessions._read_capped` vs `session_store._read_capped` (would import a private name and change the chained cause); the two `record_write_refusal` blocks (two sites; the None-guard order matters); `keep_label_for`'s step 2 `live_reverification()` (now subsumed by `_recheck_display` in production, but D5 names it, a test pins it, and it guards drift); the two linked/desktop derivations in `keep_label_for`; `_plain_label` / `_utc_now` per-module helpers (codebase convention); `UNEXPECTED_REASON` alias (pinned); `on_copy`'s type-narrowing checks; `register_wer` read-back vs `wer_exclusions` (different error handling); the interval-gate pair in `app.py` (individually pinned); moving `record_sweep_results` into `sweep_with_archive` or the audit call into `_complete_locked` (ordering changes); `CSV_COLUMNS` / `_csv_values` as one table (a restructure); `_require_same` hashing (D1 specifies SHA-256).
- Finding verification: 15 candidates; 9 left alone (above); 0 downgraded
- Fix-delta self-check: PASS — re-read every hunk; ruff clean, mypy 56 files clean; no text, signal, ordering, logging or custody change.
- Verification: pytest owed by the composer — changed source `session_store.py`, `past_sessions.py`, `ui/main_window.py`, `ui/past_sessions.py`, `ui/past_sessions_view.py`, `ui/transcript.py` (no test changed).

### Round 35 - 2026-10-01 - Hardening H3: /security-review over the whole plan surface (stage-6 executor, in-session)

- Round status: Closed (all 7 applied as Fix-now; PR-MED-030 Part B's decision record corrected — the decision stays OPEN and `CONSENT_TEXT_V3` is unchanged). Part B DECIDED (a) by the practitioner 2026-10-02.
- Source: Claude Code security-review (`/execute-loop` executor `claude-opus-5-5`; two read-only subagent lenses — (1) the two long-lived stores, the CSV and the carried link-following input (a); (2) the exception hooks, the one-line log-failure report, the exclusions, the C9 leftover grep plus the Phase-5 "local only" class, and the PR-MED-030 options — every candidate re-verified in-session against the code)
- Carried inputs: (a) the sessions-root link-following shape (round 13 LEG 1) — CONFIRMED and closed as SEC-002 with round 13's guard shape (refuse to follow; no other custody change: a refusal behaves exactly like the pre-existing unlink failure — key kept, the Complete or Discard fails before THE boundary). (b) third-party loggers and the last-resort handler — confirmed as residue (m) and widened (SEC-006). (c) PR-MED-030 Part B — the options reviewed for completeness: (b)'s edit sites and docs list corrected, its unaffected parts named, and an option (c) added (SEC-007); recommendation unchanged (a).
- Findings (all LOW):
- **[LOW]** SEC-001: `past_sessions.py` `_is_link` / `_remove_key_first_unless_link` — `Path.is_symlink()` / `is_junction()` swallow an `OSError` and answer False on Python 3.13+ (the dev machine runs 3.14), so round 32 LOW-001's "an uninspectable entry path refuses" was dead code there, and its test patched `Path.is_symlink` to raise, which the real method never does. — Triage: Fix-now; Decision: Applied (`session_store.link_state` — a tri-state `os.lstat` read: `S_ISLNK`, or the junction's `IO_REPARSE_TAG_MOUNT_POINT`; `FileNotFoundError` → False; any other `OSError` → None; every link check in the plan's surface uses it; the test now patches `os.lstat` by path, plus a real-folder / missing / error test)
- **[LOW]** SEC-002 (carried (a)): `session_store.sweep_sessions`, `delete_session_key` / `discard_session` and `ui/models.list_recoverable_sessions` followed a session-id-named link under the SESSIONS root — Windows resolves a junction mid-path, so the sweep's expiry or a Discard would delete ANOTHER folder's `key.dpapi` (a Past-sessions entry's, or another session's). Same-user only (boundary 2); the class round 13 PR-LOW-010 closed for `past_sessions\`. — Triage: Fix-now; Decision: Applied (the sweep records `link_refused` and logs that code; `delete_session_key` raises the content-free `SessionLinkError` (an `OSError`) on a link or an unreadable status, before any unlink; the recovery list skips it; `TestSessionLinksAreNeverFollowed`, junction + symlink, `tmp_path` only)
- **[LOW]** SEC-003: `audit.py` — a month folder that is a link was read (`_month_folders` → `_find` / `_row_paths`), written through (`begin` / `_update` after `mkdir(exist_ok=True)`) and handed to `prune`; `_MONTH_RE`'s `\d` admitted non-ASCII digits. — Triage: Fix-now; Decision: Applied (`_month_folders` yields only `link_state(child) is False` folders; `begin` refuses `unavailable` and `_update` raises `AuditUnavailable` (counted) when the target month folder is a link or uninspectable; `[0-9]`; `TestStoreBounds::test_a_linked_month_folder_is_never_followed`, junction + symlink)
- **[LOW]** SEC-004: `audit.export_csv` wrote through `atomic_write_bytes`, whose temp file is the FIXED `<name>.tmp` beside the target — in a folder the user chose, an existing `export.csv.tmp` of theirs was overwritten and then deleted; the failure text carried the OS error (with the path). — Triage: Fix-now; Decision: Applied (`_write_export`: a fresh `mkstemp` name in that folder, fsync, `os.replace`, the temp removed on every path, a terse `StoreWriteError("failed writing audit export")` with no cause; two tests)
- **[LOW]** SEC-005: unbounded whole-file reads in the plan's new readers — the audit row (`_read`), `saved-provenance.enc` and the Past-sessions settings file — a same-user process could plant a huge file to exhaust memory. — Triage: Fix-now; Decision: Applied (`session_store.read_capped` made the one public bounded read: rows 64 KiB, provenance 64 KiB, settings 4 KiB through `past_sessions`' own capped read; over the bound reads as unreadable / not valid; `generated.enc` was already bounded; the older key / transcript / note readers are NAMED as residue (t) — pre-existing, outside the plan's surface)
- **[LOW]** SEC-006: residue (m) understated the console launch — a library's `logger.exception` reaching the last-resort handler prints its TRACEBACK, and a `warnings` message prints file, line and source line; neither reaches `scribe-app.exe` (pythonw has no stderr). — Triage: Fix-now; Decision: Applied (docs: residue (m) widened; no code — the console launch is the documented debugging path and C3's log stays content-free)
- **[LOW]** SEC-007: docs vs code — flow 19 said "Nothing is written to disk" of the bridge's display name, which a Complete now writes into `label.enc`, and omitted the re-check name round 32 LOW-005 keeps; the PR-MED-030 decision record named wrong edit sites for option (b) (`encounter.py` / `practitioner_profile.py` are comments only; `test_prose_style.py` / `test_encounter.py` unaffected), omitted retention rows 42/46 and the parts consent-v4 leaves unchanged, and offered no option between "record only" and a re-consent. — Triage: Fix-now; Decision: Applied (flow 19's two sentences; the record corrected, the unaffected parts listed, option (c) — an information line outside the consent text — added; recommendation (a) unchanged; `CONSENT_TEXT_V1/V2/V3` untouched)
- Docs follow code: threat model (Phase 2 item 6, THE PAST-SESSIONS ARCHIVE, THE AUDIT RECORD, THE CSV, residues (m) and (t)), flow 19, flow 22 (link rule, export temp), retention rows 63 and 66.
- Checked clean: the register script (writes only the three named values; reads back; `--unregister` removes only those), `check_location` (read-only; codes only), the three exception hooks in both processes (type name only, `sys.last_*` dropped, defaults not chained), `QuietHandlerErrors` (one fixed type line), the log tripwire's row signatures, the CSV formula guard, C7 (the sweep still never decrypts `encounter.enc`; `link_state` is a stat), C8 (no connection, dependency, env var or `noqa: TID251`), no "Cliniko Scribe" text, and the C9 grep (the plan's leftover phrases plus the Phase-5 "local only" class) — the only new hit was flow 19 (SEC-007). `exclusions.mark_not_indexed`'s except branch is unreachable in practice but harmless (it only sets an attribute) — left.
- Also applied (hygiene, below LOW): `PastSessionLabel.patient_name` is `repr=False`, so a label's repr never shows the name (the log tripwire already dropped any rendering of it).
- Finding verification: 10 candidates; 1 hygiene (above); 2 dropped (the `reset` key re-check and rows not bound to their month — both inside the same-user boundary with no custody effect, the AAD already binds a row to its id); 0 downgraded
- Fix-delta self-check: PASS — ruff clean, mypy 56 files; every new refusal is content-free and happens BEFORE any key deletion; `delete_session_key` still deletes exactly `key.dpapi` in the ordinary case; THE boundary comment in `complete_session` still holds (the refusal raises before it).
- Verification: pytest owed by the composer — changed source `session_store.py`, `past_sessions.py`, `audit.py`, `ui/models.py`; changed tests `test_past_sessions.py`, `test_audit.py` (full desktop suite).
- Composer's run (leg f4): 1 failed / 5262 passed / 8 skipped (the symlink variants, no privilege). The failure was the recovery-list test's POSITIVE control: its target came from `_aged` (key mtime 2023), so `list_recoverable_sessions` dropped it as past the 24 h window — a FIXTURE defect, not an over-broad `link_state` (which reads only the child it is given, through `os.lstat`, and answers False for a real folder and a junction's target). Fixed: that test's target is a fresh session; every test in `TestSessionLinksAreNeverFollowed` now ends with a positive control on the same target reached directly (the sweep expires it, `discard_session` removes it, the listing offers it), plus `test_link_state_reads_the_link_and_never_its_target`. The other controls were not vacuous (they asserted the target's key survived), but none had shown the direct path accepted. No source change; ruff clean, mypy 56 files.

### Round 36 - 2026-10-01 - Hardening H3: confirmation of round 35 + class closure (stage-6 executor, in-session)

- Round status: Closed (3 applied, docs + one docstring); H3 CONVERGED
- Source: Claude Code security-review confirmation (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's suite after leg f4: full run 5262 passed / 8 skipped with only the fixed test failing, then `test_past_sessions.py` 93 passed / 8 skipped; ruff clean, mypy 56 files)
- Post-fix regression check: every round-35 hunk re-read against its callers. `delete_session_key`'s refusal raises BEFORE THE boundary in `complete_session` (the "nothing below raises" comment still holds) and behaves at its three other callers (live `discard`, `discard_recovered`, the recovery list's Discard via `discard_session`; the start-failure cleanup) exactly like the pre-existing unlink `OSError`; the recovery list maps it through `custody_refusal_text` (the fixed line, C3). `link_refused` is ignored by `record_sweep_results` (only `expired` / `orphan_gc` are recorded) and logged as a `detail_code`. The audit `begin` refusal is inside the existing `try` and `AuditWriteError` is not an `OSError`, so it is not re-mapped to `write_failed`; `crypto.destroy()` still runs once in `finally`. The export's any-exception path is mapped by `export_failed_line` (`StoreWriteError` or `OSError` → `EXPORT_WRITE_FAILED`).
- Class sweeps (from the code): (1) "is this a link" — `grep is_symlink|is_junction|islink|link_state|_is_link`: every check before a delete, decrypt, list or write in `session_store.py` (1), `past_sessions.py` (6, all through `_is_link` / `link_state`), `audit.py` (3) and `ui/models.py` (1) goes through `link_state`; the only other is `exclusions.py` (`os.path.islink` / `isjunction` / `DirEntry.is_junction`), which only sets a not-indexed attribute (residue (j)) — out of the class. Every directory walk that then deletes or decrypts (`iterdir` / `scandir` / `rmtree` / `glob`) was enumerated: `sweep_sessions`, `list_recoverable_sessions`, `clean_staging`, `_entry_dirs` / `_committed_dirs`, `reconcile_pending` (its `sessions\<id>` stat can only DEFER or EARLY-COMMIT a pending entry, never delete a key), the audit month walk and prune — closed; `speaker_eval.py` is the practitioner-run measurement tool, outside the surface. (2) "an on-disk file read without a bound" — `grep read_bytes|read_text|open("rb")`: the plan's readers are bounded; residue (t) named only three older reader families (LOW-001). (3) the CSV export — terse error held; the "removed on every path" claim was too strong (LOW-003).
- Findings:
- **[LOW]** LOW-001 (🔁 of SEC-005, docs follow code): residue (t) enumerated only the key, transcript and note readers; the unbounded older readers also include `encounter.enc`, `write.enc` (`_read_or_none`, `read_write_record`), the voice-profile and style stores (`practitioner_profile`), the configuration files under `config\` (`note_config`), and the Past-sessions entry's own transcript / note reads and staged-copy verification. `clinics.json` is already bounded. — Triage: Fix-now; Decision: Applied (residue (t) lists every family)
- **[LOW]** LOW-002 (🔁 of SEC-002/003, docs): flow 22 said "a link under `sessions\`, `past_sessions\` or `audit\` is never … read" — but only linked FOLDERS are refused; a linked audit row FILE is read like any row (AAD-bound to its id, so harmless) and the three roots are not checked. — Triage: Fix-now; Decision: Applied (flow 22 names folders, the unchecked roots and the row-file case)
- **[LOW]** LOW-003 (🔁 of SEC-004, docstring + docs): `_write_export`'s docstring ("`StoreWriteError` on any failure") and the threat model / flow 22 ("removed on every path") overclaimed — when Windows refuses the temp file's removal, that `OSError` propagates and the `.clinic-scribe-*.tmp` stays. The user's own `<name>.tmp` is still never touched, and the tab shows the same export-failed line. — Triage: Fix-now; Decision: Applied (the docstring and both docs state the exception)
- PR-MED-030 Part B, reviewed once more: options (a) / (b) / (c) complete; one correction to (b)'s test list (`test_prose_style.py` hard-codes `consent-v3`, but `prose_style` never checks the version — unaffected for that reason, not because it reads the constant; `speaker_eval.py` is a further comment-only mention). `CONSENT_TEXT_V1/V2/V3` unchanged. Recommendation (a).
- Finding verification: 3 candidates; 0 dropped; 0 downgraded
- Round classification: 0 ⚡ / 0 🆕 / 3 🔁 — CONVERGED (0 CRIT / HIGH / MED; every round-35 fix holds and its class is closed from the code)
- Fix-delta self-check: PASS — docs plus one docstring (`audit._write_export`); no executable line changed since the green run; ruff clean, mypy 56 files.
- Verification: no pytest owed (no executable change since the green run).

### Round 37 - 2026-10-01 - Hardening stage (H1-H3 changes), independent cross-family codex peer review (pass stage-6.p1, H4)

- Round status: Closed (2 applied)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Hardening-only source, test and documentation diffs, current hunk context and relevant callees; specified plan constraints, decisions and rounds 32–36. Read-only verification; no tests or network commands run.
- Fix-delta self-check: PASS — re-read the 6 applied hunks across `conftest.py`, `test_audit.py`, `test_past_sessions.py`, `test_session_store.py`, the threat model and CHANGELOG: the spy wraps only `mode == "rb"` opens of the one file name (the fake key unwrap's `read_bytes` on `key.dpapi` is untouched); every monkeypatched cap is a module global read at call time (`_read`, `_read_generated`, `read_saved_provenance`, `_decode_label`); `rows()` and `list_entries()` read each file once per call, so `[size, size + 1]` is exact; the padded settings JSON is valid (trailing whitespace); no drive-by edits.

#### Findings

- **PR-LOW-031** (LOW, test-harness, `desktop/tests/test_audit.py:954`): The new size-cap tests would still pass if their readers reverted to unbounded whole-file reads. The audit fixture already fails authentication, and the settings fixture already fails JSON parsing; neither asserts a bounded read. — Evidence: `row_path.write_bytes(b"\0" * (audit_mod.MAX_ROW_FILE_BYTES + 1))`, followed by `assert (listing.rows, listing.unreadable) == ((), 1)`; sibling `desktop/tests/test_past_sessions.py:827` uses `oversized = b" " * (past_sessions.MAX_SETTINGS_FILE_BYTES + 1)` and expects `"is not valid"`. Recommendation: Fix-now — Add a file-stream spy that rejects unbounded reads and verifies the requested limit, alongside otherwise-valid oversized fixtures and an accepted small-file control. /fix decision: Applied — /fix notes: `conftest.bounded_read_spy` (records every `read` size on a `Path.open("rb")` stream for one file name; a size-less or negative read fails the test — what `Path.read_bytes` does); one test per capped reader the plan added, each on an OTHERWISE-VALID file — one byte over the cap refused, exactly at the cap accepted, and the each recorded read exactly `cap + 1` bytes for the cap in force: audit rows (`test_audit.py`, replacing the padded-row test), `saved-provenance.enc` and `generated.enc` (`test_session_store.py`; the `generated.enc` oversize test has the same flaw, a sibling), the Past-sessions label (`test_past_sessions.py`, a sibling), and the settings file (valid JSON padded with whitespace, which parses). The encrypted files' caps are lowered by monkeypatch to their real size − 1 (padding would break authentication). Both bounded-read implementations (`session_store.read_capped`, `past_sessions._read_capped`) are exercised. No reader was found unbounded; no source change. Verified: ruff clean, mypy 56 files; pytest owed by the composer. /fix date: 2026-10-01; /fix applied by: Claude Code

- **PR-LOW-032** (LOW, docs-only, `docs/security/threat-model.md:2857`): Residue (m) still promises that console launches print no tracebacks, contradicting the third-party traceback exception added immediately above it. — Evidence: Lines 2852–2855 describe “the TRACEBACK of a library's `logger.exception`” reaching a console launch; lines 2857–2859 then state “A console launch no longer prints tracebacks at all”. Recommendation: Fix-now — Limit the latter statement to uncaught exceptions handled by the installed application hooks, preserving the documented library and faulthandler exceptions. /fix decision: Applied — /fix notes: residue (m)'s last sentence is now limited to an UNCAUGHT exception's traceback and message, "apart from" the library, `warnings` and faulthandler cases; sibling CHANGELOG.md:165 (the same absolute headline) limited the same way, with the residue named. Swept and left true: AGENTS.md's launch note and the retention schedule's log row (both say "an uncaught exception"); `docs/practice/` and `docs/lessons.md` have no such sentence. The plan's leg-e1 note asking the composer's `/document` for a lessons.md line "a console launch prints no traceback" should be worded the same way (uncaught exceptions only) when it is written. Historical leg bullets left as records. /fix date: 2026-10-01; /fix applied by: Claude Code

- Verification counts: 5 claims checked, 2 confirmed, 3 dropped as unverifiable
- Last reviewed: 2026-10-01
#### LEG 1 verified tuples (executor, 2026-10-01T17:04:39+10:00)
- PR-LOW-031: materiality=test-harness severity=LOW surface=desktop/tests (test_audit.py, test_past_sessions.py, test_session_store.py, conftest.py) rec=Fix-now — confirmed: the padded audit row fails authentication and the all-space settings file fails JSON parsing, so both tests passed with an unbounded read; the same flaw in siblings `test_session_store.py::test_absent_is_none_and_oversize_is_unreadable` (generated) and no bound test at all for `saved-provenance.enc` or the label; every reader itself is bounded (`stream.read(cap + 1)`) — applied
- PR-LOW-032: materiality=docs-only severity=LOW surface=docs/security/threat-model.md residue (m) + CHANGELOG.md:165 rec=Fix-now — confirmed: "A console launch no longer prints tracebacks at all" contradicts the library-traceback sentence above it; CHANGELOG.md:165 carried the same absolute headline; AGENTS.md and retention row 27 are scoped to uncaught exceptions and true — applied
Cap verdict: accept — test-harness + docs-only — no production reader was unbounded (each new test passes only through `read(cap + 1)`), no source line changed; both closed in this leg, so no extra round is needed beyond the composer's suite
- PEER-ROUND-37 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2).

### Round 38 - 2026-10-01 - Hardening stage confirmation of round 37's fixes, independent cross-family codex peer review (pass stage-6.p1, H4)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-37 fix diff, current hunk context, Round 37 findings and specified capped readers; read-only verification, no tests or network commands.

#### Findings

- **PR-LOW-033** (LOW, test-harness, `desktop/tests/test_past_sessions.py:856`): The staged-label verification read remains outside the new bounded-read coverage. Replacing that call alone with `Path.read_bytes()` would leave the new tests passing; production currently remains bounded. — Evidence: `sid = _published(store)` runs before `sizes = bounded_read_spy(monkeypatch, LABEL_FILENAME)` at lines 856–858; `_published` invokes `store.write_entry(source, LINKED)` at line 142. The separate staged reader at `desktop/src/scribe_desktop/past_sessions.py:478` calls `_read_capped(staging / LABEL_FILENAME, MAX_LABEL_FILE_BYTES)`, whereas the instrumented assertions exercise subsequent `store.list_entries()` calls. Recommendation: Fix-now — Add a staged-verification boundary test with the spy active during publication, checking an otherwise-valid label at and over the cap and the requested read size. /fix decision: Accepted-with-record (composer, gates=executor, D9 harness tail: the second consecutive round whose survivors are test-harness/docs only; the peer itself confirms production is bounded — `past_sessions.py:478` reads the staged label through `_read_capped`; the missing staged-publication spy test is carried as a one-line follow-up for the next change that touches `write_entry`)

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-01
#### Composer disposition (2026-10-01)
- PR-LOW-033: materiality=test-harness severity=LOW surface=test-harness rec=Accept-with-record — D9 harness tail (round 37 survivors were test-harness + docs; round 38 is test-harness only); production verified bounded by the peer; no executor leg spent.
- Cap verdict: accept — test-harness — pass stage-6.p1 CONVERGED at peer_round 2/5.
- PEER-ROUND-38 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

### Round 39 - 2026-10-02 - H5: the 7-year minimum retention, /review-loop round 1 of 3 over the H5 diff only (stage-7 executor, in-session)

- Round status: Closed (2 applied; docs only)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's suite after leg g1: 5300 passed / 9 skipped (directory-symlink variants), ruff clean, mypy 56 files)
- Scope: the H5 diff — `past_sessions.py`, `ui/past_sessions_view.py`, `ui/past_sessions.py`, `test_past_sessions.py`, `test_ui_screens.py`, and the docs leg g1 touched (`docs/practice/*`, the five security docs, `design-system.md`, CHANGELOG, PLAN.md, this plan).
- Named targets, each checked from the code:
  - **The upgrade never fails closed for a removed value and admits nothing else.** `_raise_a_legacy_window` (`past_sessions.py:951`, `mode="before"`) maps only `type(value) is int` and in `LEGACY_RETENTION_DAYS`; everything else reaches the unchanged strict field and `_a_choice`. `True`/`1.0`/`7.0` compare equal to legacy members, so an `isinstance` or `in`-only check would admit them — the `type(...) is int` guard is the load-bearing part, and the invalid-file parametrization (`true`, `1.0`, `7.0`, `"7"`, `"30"`, `[365]`, 0, −7, 2556, 2558, 5) would fail on that regression. The context flag reaches the caller (the suite's `retention_raised is True` assertions pass, so pydantic hands the same dict through). The read never writes; the loader is the only reader (`load_past_session_settings` / `read_past_session_settings`, grep over src: `ui/past_sessions.py` only; `app.py` reads no settings).
  - **Nothing younger than the window is deleted except Delete now.** Every committed-entry remover enumerated (`_remove_key_first(`, `shutil.rmtree`, `delete_entry`): `delete_entry` (Delete now; `sweep_report`), `sweep_report` (guarded `< MIN_RETENTION_DAYS` at `:707` before any read, then `now - completed < window` keeps), `sweep` / `sweep_past_sessions` / `view.retention_sweep` / `run_retention_sweep` (start-up `app.py:621`, `PeriodicSweep`, a lowering) all through `sweep_report`; the settings model holds only None or 2557 (`model_construct` is the only bypass, test-only). The other removers touch no live committed entry: `remove_pending_entry` runs only while the SOURCE key exists (C1: no finished entry for that id), `reconcile_pending` removes only keyless leftovers, `_publish` replaces the same id's earlier copy at a retried Complete, `clean_staging` only staging. Residues (d) (forward clock jump) and (s) (Delete now's wording-only limit, the child rule) are named in the threat model.
  - **The status lines carry no content and clear correctly.** `RETENTION_RAISED_LINE` / `SWEEP_TOO_SHORT_LINE` are constants. `_retention_raised` is re-derived on every reload, cleared only after a successful save (a retention choice, including the same "7 years" — the only same-choice save — or a Hide names click); a failed save keeps it (the file still holds the old value); an unreadable file sets it False. `SWEEP_TOO_SHORT_LINE` is derived through `_current_sweep`, so it drops with any setting change like the other sweep lines.
  - **The old choices are gone** — the grep re-derived from scratch (`\b(1|7|30|90) ?days?\b|\b1 ?year\b|one year|\b365\b|retention_days…=(1|7|30|90|365)|retention_index\((…)\)|retention_*_text/line/label\((…)` over src, tests, docs, PLAN, CHANGELOG, AGENTS, README, extension/src, protocol, scripts): only `LEGACY_RETENTION_DAYS` and its comment in code; tests that pin the legacy set or parametrize it; descriptions of the removal (CHANGELOG, README, threat model, retention schedule); the AJGP/Heidi research quotes. The wording family (`short(er)? (retention|setting|window)`) holds only the new upgrade sentences and the plan's history.
  - **The new tests fail on the regressions they name** — read against a reverted guard each: the store refusal test (a removed `< MIN` check deletes `old` and unwraps), the upgrade test (a removed before-validator raises), the tab test (a removed same-choice save leaves the legacy value in the file; a removed Hide-names clear leaves the line), the forced 1-day UI test (deletes and shows no line), the two-choice combo, Delete now and child-line pins (literal).
  - **`CONSENT_TEXT_V1/V2/V3` untouched** — `ui/models.py` is not in `git diff --stat 017ae66` (the hardening-close tree snapshot).
  - **PR-MED-030 Part B is DECIDED (a) wherever current text called it open** — threat model surface 9 residue, the plan's executor bullets and handoff lines, round statuses 30 and 35; the remaining "open" phrasings are the composer's own bullets (left untouched by rule) and closed Review History / Findings Log narrative.
- Findings:
- **[LOW]** LOW-001: `docs/practice/patient-information-and-consent.md:51`, `privacy-information.md:87`, `clinician-review-guide.md:122-125` — leg g1 stated the child rule ("until you turn 25") as a bare rule; it is the VIC/NSW/ACT Acts' rule, and the practice README's C10 rule ("every document that states a record-keeping rule cites every state and territory, from the research below only") requires the states (and APP 11.2 elsewhere). — Triage: Fix-now; Decision: Applied (each line now names Victoria, NSW and the ACT and says the Australian Privacy Principles apply elsewhere; the guide says "at least until they turn 25")
- **[LOW]** LOW-002: `docs/practice/README.md:20-25` — the README's own rule ("if the patient information changes, give it a new version") read as requiring `patient-info-v2` for leg g1's edits; the drafts have never been given to a patient (composer, 2026-10-02). — Triage: Fix-now; Decision: Applied (one line: none of the drafts has been given to a patient yet, so pre-review changes stay within `patient-info-v1`)
- Finding verification: 2 candidates; 0 dropped; 0 downgraded
- Round classification: 0 ⚡ / 2 🆕 / 0 🔁 — CONVERGED (0 CRIT / HIGH / MED; both LOWs docs-only)
- Fix-delta self-check: PASS — re-read the four doc hunks; each state claim matches the README's research table (VIC/NSW/ACT: at least 7 years from the last contact, or until 25 for a child; elsewhere APP 11.2, no fixed period); no code, string or test changed
- Verification: docs only since the green run (5300 passed / 9 skipped); no pytest needed

### Round 40 - 2026-10-02 - H5 (7-year minimum retention), independent cross-family codex peer review (pass stage-7.p1)

- Round status: Closed (1 applied — executor LEG 2)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: H5-only diff, current affected code and tests, permitted sweep call paths, documentation and specified plan sections; read-only verification, no tests or network commands.

#### Findings

- **PR-LOW-034** (LOW, behavioral, `desktop/src/scribe_desktop/ui/past_sessions_view.py:393`): Unreadable-entry guidance still presents Delete now as a remedy for a read failure, contradicting H5’s new “recording made in error” restriction. The new confirmation limits the impact, but the preceding advice remains inconsistent. — Evidence: line 393 says “by age. You can delete it with Delete now.”; the plural sibling at line 397 repeats this, and `open_failed_line` at lines 444–445 says “You can still delete it with Delete now.” `docs/practice/downtime-procedure.md:97` repeats that advice; its reviewer question does not qualify the instruction. `desktop/tests/test_ui_screens.py:9991` pins the old wording. Recommendation: Fix-now — qualify both unreadable-entry messages and the downtime guidance with the made-in-error limit, update the test pin, and reconcile the corresponding Delete-now pointers in `docs/security/retention-schedule.md:176` and `docs/security/threat-model.md:2835`. /fix decision: Applied (executor LEG 2, 2026-10-02T05:28:25+10:00) — the class, enumerated by grep (`with Delete now|still delete|points at Delete now|can only be deleted|cannot be read on this Windows account` over `desktop/src`, `docs/`, PLAN.md, the plan's current sections): code — `ENTRY_UNREADABLE` (`ui/past_sessions_view.py:80`, a sibling the peer did not cite), `undated_line` both counts, `open_failed_line` (every reason, so no "still kept" claim there — the reason may be `not_found`), all now ending in one constant `UNREADABLE_DELETE_LIMIT` ("Delete now is only for a recording made in error - read the downtime procedure before deleting it."; the plural line says "them"), and the first two also say the entry "is still kept"; docs — `downtime-procedure.md` (the unreadable entry: leave it, delete only if made in error or once the reviewer question is answered; the "could not be deleted" bullet now says those are past the setting, so Delete now there is the deletion the setting asked for), `retention-schedule.md` (Fail toward keeping, and the "Until I delete them" bullet's "can only be deleted"), `threat-model.md` residues (c) and (d). Left, checked: the shipping gate's "delete the run's entries with Delete now" (test recordings — inside the limit); docstrings that say an unreadable entry "can still be deleted" (`past_sessions.py:635`, `ui/past_sessions.py:388` — a statement of capability, still true); the plan's closed history. Behaviour unchanged (Delete now still works on any entry). Tests: the open-failure pin updated (`test_an_entry_that_fails_to_open_names_the_next_step`); NEW `test_no_read_failure_line_offers_delete_now_without_the_made_in_error_limit` pins `ENTRY_UNREADABLE` and `undated_line(1)`/`(3)` literally and checks every read-failure line (each `PAST_SESSION_REASONS` code and an unexpected error) carries the limit and no "can delete". ruff clean, mypy 56 files.

- Verification counts: 1 claims checked, 1 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-02
#### LEG 1 verified tuples (executor, 2026-10-02T05:28:25+10:00)
- PR-LOW-034: materiality=behavioral severity=LOW surface=ui/past_sessions_view.py (ENTRY_UNREADABLE :80, undated_line :393/:397, open_failed_line :445) + docs/practice/downtime-procedure.md + retention-schedule.md + threat-model.md rec=Fix-now — confirmed: all four app lines offered Delete now as the remedy for a read failure with no made-in-error limit, contradicting H5's DELETE_HELP / DELETE_CONFIRM_MESSAGE; the peer missed ENTRY_UNREADABLE; this is the item I raised as leg g1 review item 2
Cap verdict: accept — production-behavioral — four authored strings (one shared tail constant) plus their pins and four doc sites, wording only, no logic change; within cap at peer_round 1 of 5 (whether to run a confirmation round is the composer's call)

PEER-ROUND-40 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

### Round 41 - 2026-10-02 - H5 confirmation of round 40's fix, independent cross-family codex peer review (pass stage-7.p1)

- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Reviewer: codex gpt-6-astra (medium)
- Scope: Round-40 fix diff and current hunk context; desktop/src Delete-now wording sweep; read-failure truthfulness, test-pin coverage and preservation of earlier assertions; downtime procedure, retention schedule and threat-model residues (c)/(d). Read-only verification; no tests or network commands.

#### Findings

- Verification counts: 3 claims checked, 3 confirmed, 0 dropped as unverifiable
- Last reviewed: 2026-10-02

PEER-ROUND-41 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

## Tasks

### Phase 1 — Custody foundation: directory removal and the audit record
- [x] 🟩 1.1: Remove the session directory on EVERY Complete.
  - Files: `session_store.py` `complete_session` (drop the `remove_directory` flag; always remove); `session.py` 1048 / 1086 / 1116 / 1499 / 1711; the docstrings at `session_store.py` 44 / 99-100 / 721-726.
  - Behaviour: after any Complete the session directory is gone. A failed `rmtree` leaves a keyless orphan that the sweep's `orphan_gc` removes; any archive entry for it then commits (C1).
  - Tests: invert `test_session_store.py:634`, update `test_session_machine.py:1500`, and rewrite the transcript-survives assertions (`test_integration_no_sockets.py:937/1165/1332`, `test_transcription.py:1233`). Own verification.
- [x] 🟩 1.2: The audit store `audit.py`.
  - Contents: `AuditRow` (D8), `AuditLog` (`begin` raising `AuditWriteError` — the real write is the check, there is no separate precheck; `update` never raising, `rows`, `prune`, `export_csv`), the D7 layout, the D9 "start a new audit record" rename, and `_session_created_at` made public in `session_store.py`.
  - Reuses the shared helpers (Key Findings, Integration Notes).
  - Also: add the key description to `test_display_name.py`, and the distinctive field names to `_PAYLOAD_SIGNATURES` (C3).
  - Behaviour: rows round-trip encrypted, and the store keeps its fail-closed rules.
  - Tests: `test_audit.py` (see Validation).
- [x] 🟩 1.3: Audit wiring in the controller and the store.
  - `SessionController(audit=None)`, wired in `app.main` with a test pinning the wiring.
  - `start()`: build the `RecordingSession` and call `begin` BEFORE `_retire_locked` (759), per Flow 1 / C2. `start_failed` is recorded on EVERY failure after `begin`: one `try` spanning the retire refusal, directory creation (765-768) and the existing cleanup `except` (799-810) (Flow 1 step 5).
  - Model provenance: `saved-provenance.enc` is written in `save_note`'s custody action and read at Complete with the digest match (D8). This is Task 2.1's file; Task 1.3 only consumes it. `user_id` is passed in by the caller from the clinic registry.
  - `complete_session` returns `CompletionFacts` (D4). All five Complete paths update `models`, `deletion` and `past_session`.
  - Discard: `discard()` (both its paths, including the 1218 early return, which records nothing new), `discard_recovered`, and `ui/recovery.py:451` (given the audit log, passing `info.session_id`).
  - Sweep: `app.run_sweep` returns and records its results (C7); the audit prune runs at startup and every 24 h on the sweep timer.
  - `SweepResult` gains `created_at`, captured before deletion (D8, round 1 PR-MED-004).
  - The pending-entry removal on Discard / expiry / orphan_gc (C1) is wired in Task 2.3, once `past_sessions.py` exists.
  - `AuditWriteError` subclasses `SessionControllerError` (D12), with "Start failed: the audit record could not be saved (…). Nothing was recorded." On the Session screen it reads "Start failed: AuditWriteError: the audit record could not be saved (…). Nothing was recorded." The type name comes from the shared `custody_refusal_text` convention and is pinned by round 6 LOW-003 (amended round 7 LOW-009).
  - Behaviour: every lifecycle event lands in the row; an audit failure refuses only Start.
  - Tests: listed under Validation (session tests).
- [x] 🟩 1.4: The write result into the audit.
  - Files: `MainWindow._store_write_record` (`ui/main_window.py:1901`), the one boundary every durable write-record transition passes through: attempt (1852), reconciled-written (1847), finished (1878), unknown (1885-1894). Record attempts, outcome and `written_at`, best-effort (C2).
  - Also: the `WriteRefusal` branch of `_prepare_attempt` (1840) records the refusal's fixed code as `last_refusal`, never the display line (round 1 PR-MED-005).
  - Tests: attempt then finish; unknown → reconciled-written → Complete (the row reads written); an attempt with no finish callback (the row shows the attempt); a pre-send refusal code; an audit failure does not change the write outcome.

### Phase 2 — The Past-sessions archive
- [x] 🟩 2.1: `generated.enc` (D2).
  - Files: `session_store.py` (`write_generated` / `read_generated` with AAD `generated:<id>`); a new `TranscriptScreen` method on the `save_note` pattern; its call from `MainWindow._on_draft_ready` (1533) and on regeneration; the prose-first rewrite rule; the `NoteDraft` docstring in `note.py`.
  - Behaviour: the first rendered body is kept under the session key, with its provider, style, LM id and prompt version captured at render time (D2), and dies with the session.
  - Also: `saved-provenance.enc` (D8), written in `save_note`'s `with_generation_custody` action with the saved note's digest.
  - Tests: written first, then the note; digest mismatch → `unknown`; never archived; failure injected at the provenance write (Save fails, nothing committed) and at the note write after provenance (Save fails; `_note_committed` / `_note_saved`, Cancel review, retry and reopen agree with disk) (round 4 PR-MED-001).
  - Tests: written under the lease; replaced on regeneration; refused without the lease; removed at Complete and Discard.
- [x] 🟩 2.2: The archive store and settings `past_sessions.py`.
  - Contents:
    - the D1/D3 layout;
    - `write_entry`: staging → the full D1 verification (own key from disk, the expected artifact set, every plaintext digest) → `os.replace`, replacing an existing entry key-first;
    - `list_entries`: decrypts `label.enc` only; lists COMMITTED entries only, meaning no `pending` marker (C1);
    - `reconcile_pending(sessions_root)`: commits every `pending` entry whose source `key.dpapi` is gone;
    - `read_entry`, `delete_entry` (key first);
    - `remove_pending_entry(session_id)` for Discard and expiry, called BEFORE the source key is deleted;
    - `clean_staging()`, run every startup and sweep tick whatever the retention setting;
    - `sweep_past_sessions(root, retention, now)`: keeps undated and future-dated entries; does nothing when the setting is "never";
    - the `config\past_sessions.json` loader/saver (the `note_config` pattern; unreadable → nothing deleted).
  - Also: add the key description to `test_display_name.py` and the field names to `_PAYLOAD_SIGNATURES`.
  - Tests: `test_past_sessions.py`.
- [x] 🟩 2.3: Archive at Complete.
  - Files: `complete_session`'s optional `keep` argument (D4) and C1's ordering; `_verify_note_for_completion` returns the verified note; D6's per-path contents and mock detection; `PastSessionWriteError(SessionControllerError)` for failures BEFORE the key boundary, with "Complete failed: the Past-sessions copy could not be saved. No key deletion was performed — try again, or Discard."; after the boundary, marker or directory removal failures never raise into the controller (Flow 3 step 4), and `CompletionFacts` carries `commit_deferred` for the truthful status line.
  - Name resolution (D5): a new `MainWindow.keep_label_for(session_id)` plus a public bridge accessor; the optional label threaded through the five controller methods, `SessionControllerLike` and the fakes; the Complete callers at `ui/transcript.py` 961 / 1003, `abandon_note_and_complete`, `main_window.py:933` and the 1288 lambda.
  - Docstrings: `_CheckoutEncounter` (130-131) and `ui/__init__.py` (13-14).
  - Pending-entry removal (C1): `discard()`, `discard_recovered` and `ui/recovery.py:451` call `remove_pending_entry` BEFORE their `discard_session`. `sweep_sessions` gains a `before_destroy(session_id)` callback, invoked before an `expired` key deletion AND before a dead-key `orphan_gc` deletion (C1's orphan_gc split). Complete removes the marker right after `delete_session_key`. `reconcile_pending` is wired at startup and on the sweep tick.
  - Delete-note paths (D6): the early unlink at `session_store.py:728-730` is removed; `delete_note=True` excludes the note from verification and the archive, and its provenance is read on every attempt; the mock decision uses all three discriminators.
  - Behaviour: every non-mock Complete leaves exactly one verified, committed entry, and the session directory is gone. An interrupted Complete followed by Discard or expiry leaves no entry.
  - Tests: listed under Validation (session and UI tests).

### Phase 3 — The Past sessions tab and the intended-use line
- [x] 🟩 3.1: The Past sessions tab.
  - Files: `ui/past_sessions_view.py` (Qt-free: labels, the hide-names mask, retention options and pinned warning text, CSV rows, the write-outcome line from the audit row) and `ui/past_sessions.py` (widgets).
  - Placement: added after Note in `main_window.py:437-445`; roots and the settings path injected in all 8 `MainWindow` test sites; the tab pin updated to 9.
  - Features (Flow 5): Copy of the saved note only via `_place_note_text`; two-step Delete now (the `session_screen.py:395-424` pattern, recording `deleted_early`); a confirmation when retention is lowered, then the sweep runs; Export CSV via an injected save dialog with the "not encrypted" line; the persistent status label.
  - UI rules: follow `docs/design-system.md`; no "Cliniko Scribe" text.
  - Tests: listed under Validation (UI tests).
- [x] 🟩 3.2: The retention sweep in `app.py`: at startup, and at most hourly on the 15-min timer. It records `expired` into the audit row.
  - Tests: timer cadence with an injected clock; no decrypt when the setting is "never".
- [x] 🟩 3.3: The intended-use line (D14).
  - Files: the constant in `ui/models.py`, shown on `StatusPanel` and the Past sessions tab.
  - Tests: the text is pinned.

### Phase 4 — Exclusions and crash hygiene
- [x] 🟩 4.1: `exclusions.py`.
  - Contents: an injected `WindowsLayer` (a real one via `os.environ` / `os.path.realpath`, one `GetDriveTypeW`, `SetFileAttributesW` for NOT_CONTENT_INDEXED, a `winreg` read of the WER values); `check_location()` and `check_wer()` returning warning lines (D10; `check_wer` also checks the running interpreter from an injected `sys.executable`); best-effort `mark_not_indexed(root)`; `install_exception_hooks(logger)` (`sys.excepthook`, `threading.excepthook`, `sys.unraisablehook`, each logging only `error_code=type(exc).__name__`).
  - App wiring: in `app.main` before the window is built; warnings shown on `StatusPanel` and the Past sessions label; the no-sockets child mirror extended.
  - Tests: `test_exclusions.py`, plus an autouse sentinel for every `MainWindow` test (C6).
- [x] 🟩 4.2: `scripts/register-native-host.py`.
  - `register()` writes the three WER DWORDs and verifies them by read-back; `unregister()` deletes them.
  - The docs say that a verify from an agent shell proves nothing (lessons.md:13-20).
  - Tests: a new importlib-loaded script test with a fake `winreg`.

### Phase 5 — Practice documents and the security-doc class rewrite
- [x] 🟩 5.1: `docs/practice/`.
  - Files: `README.md`; `patient-information-and-consent.md` (`patient-info-v1`); `privacy-information.md`; `downtime-procedure.md`; `clinician-review-guide.md`.
  - Content per Agreed Scope and External Findings: every state cited; the review banner (C10); the Ahpra points; no audio kept; the Past-sessions retention and the "never" consequences; the app never ticks Cliniko's consent box.
  - Verification: H3 grep plus practitioner read.
- [x] 🟩 5.2: The C9 class rewrite. Every listed statement changes; new rows and flows are added for the audit, Past sessions, `generated.enc`, the CSV and the exclusions, with the named residues:
  - the same-user DPAPI boundary now guarding indefinitely-kept stores;
  - NTFS unlink;
  - admin-only exclusions;
  - third-party backups, the pagefile and hibernation;
  - the `pythonw.exe` WER breadth;
  - the CSV outside custody;
  - expiry only while the app runs;
  - Chrome crash dumps;
  - "never" retention with no backup (and, since H5, the 7-year minimum's unenforced parts — residue (s));
  - an audit row left `pending` forever by a process kill between `begin`'s row and the session directory's creation (nothing on disk for the sweep to end; round 6 LOW-008);
  - `session_date` is the practitioner's LOCAL calendar date (every timestamp column is UTC), and the month prune waits one extra day for it (round 6 MED-002);
  - a system clock that is wrong AT Start dates the row by that clock (a year before the audit existed would be pruned at the next start-up); a pre-audit row's creation time before 2026-01-01 is untrusted and dated by the sweep's clock instead (round 7 LOW-004).

  Also: `intended-use.md` (D14), `incident-process.md` (the audit record is now the durable evidence), `AGENTS.md` subsystem pointers (audit, Past sessions, exclusions, `docs/practice/`), `CHANGELOG.md`, phase-history.
  - Verification: the C9 grep in H3.

### Hardening stage
- [x] 🟩 H1: `/review-loop` over Phases 1–5 as one surface to convergence (rounds 32–33, converged 2026-10-01). Named targets: C1 ordering, C2 never-blocks, the hourly `label.enc` decrypt (lessons.md:91), name-to-session matching, the D6 path matrix.
- [x] 🟩 H2: `/simplify`: log findings; trivial → `/fix`, substantial → scoped `/review-plan`. (Round 34: 6 trivial, applied, suite green at 5254; none substantial.)
- [x] 🟩 H3: `/security-review` (the two new long-lived stores, the CSV, the exception hooks, the C9 grep): log findings with the same routing. (Rounds 35–36, converged 2026-10-01: 7 LOW applied + 3 LOW docs confirmations; suite green at 5262 + the leg-f4 test fix.)
- [x] 🟩 H4: the cross-family codex pass (`gpt-6-astra`; slice passes over ~15 files, per `codex-window-pacing`) until a clean confirmation. (Pass `stage-6.p1`, rounds 37–38, converged 2026-10-01: 2 LOW applied, then 1 test-harness LOW Accepted-with-record under the D9 harness tail; suite green at 5267 passed, 9 skipped.)
- [x] 🟩 H5: 7-year minimum retention (practitioner decision 2026-10-02; Agreed Scope amended). Built by stage-7 leg g1: the retention choices are "Until I delete them" and "7 years" only (`past_sessions.MIN_RETENTION_DAYS`, `RETENTION_DAYS_CHOICES`, `ui/past_sessions_view.RETENTION_OPTIONS`); a settings file holding a removed value (`LEGACY_RETENTION_DAYS` 1/7/30/90/365) loads as 7 years through a before-validator, the tab's status says so (`RETENTION_RAISED_LINE`) until a save writes 7 years, any other value still fails closed; `sweep_report` refuses a window under 7 years (`too_short`, `SWEEP_TOO_SHORT_LINE`); Delete now kept, worded for a recording made in error (`DELETE_HELP`, `DELETE_CONFIRM_MESSAGE`); `RETENTION_WARNING` gains the 7-year and child lines; docs as one class; P.2 rewritten. Composer suite green (5300 passed / 9 skipped); `/review-loop` CONVERGED at round 39 (2 LOW docs, applied). Codex pass `stage-7.p1` rounds 40–41 CONVERGED (PR-LOW-034 fixed: `UNREADABLE_DELETE_LIMIT`).

### Practitioner smoke
- [x] 🟩 P.1–P.5: see Validation / Verification (from a normal terminal; the practitioner owns it). ALL PASS 2026-10-02 (P.2 re-checked on the H5 build).

## Retained Follow-Up Items
(Populated at completion.)

## Follow-Up Continuation Notes
- Next after this plan: the deferred Past-sessions backup/restore (before commercialising), and PLAN.md Phase 7 (pilot and installation, carrying the admin-only exclusions).
- Still applies: D1/D3 (entry layout and per-entry keys), D7/D8 (audit layout and schema), C1–C3.
- Do not rediscover: the Ahpra and state-law research (External Findings); why the generated note needs `generated.enc` (D2); why the WER exclusion names `pythonw.exe` (D10, lessons.md:121).

---
*Plan saved to: .cursor/plans/plan-privacy-professional-controls.md*
*To resume in a new session: run /start-session, then /load-plan*
