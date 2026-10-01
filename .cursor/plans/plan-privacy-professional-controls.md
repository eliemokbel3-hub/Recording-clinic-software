# Feature Implementation Plan
**Feature:** privacy-professional-controls
**Overall Progress:** `100%`

## Lifecycle State
- Completed — Follow-ups Retained

## Completion Status
- Completion timestamp: 2026-10-02 (smoke P.1–P.5 PASS; committed `97d922e`)
- Main implementation complete: Yes
- Ready for archive: No (follow-ups retained)

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
- Materiality: 5 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".


### Round 2 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 2)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 6 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 3 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 3)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 4 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 4 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 4)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 2 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Materiality: build-affecting
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 5 - 2026-10-01 - privacy-professional-controls plan, independent cross-family codex plan peer-review (round 5)
- Round status: Closed
- Source: Codex plan peer-review
- Materiality: 1 build-affecting / 0 record-only / 0 invalid
- Materiality: build-affecting
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 6 - 2026-10-01 - Phase 1 (Tasks 1.1–1.4) code review, /review-loop round 1 of 3 (stage-1 executor, in-session)
- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a two-lens subagent fan-out — correctness/security and plan-deviation/judgment/structure — merged, deduped and verified in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 7 - 2026-10-01 - Phase 1 (Tasks 1.1–1.4) code review, /review-loop round 2 of 3 (stage-1 executor, in-session)
- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a fresh two-lens subagent fan-out — correctness/security incl. the round-6 fixes adversarially, and plan-deviation/test-quality/structure — merged, deduped and verified in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 8 - 2026-10-01 - Phase 1 slice A (source), independent cross-family codex peer review (pass stage-1.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 9 - 2026-10-01 - Phase 1 slice B (tests), independent cross-family codex peer review (pass stage-1.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 10 - 2026-10-01 - Phase 1 confirmation of round 9's test fixes, independent cross-family codex peer review (pass stage-1.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 11 - 2026-10-01 - Phase 2 (Tasks 2.1–2.3) code review, /review-loop round 1 of 3 (stage-2 executor, in-session)
- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 12 - 2026-10-01 - Phase 2 (Tasks 2.1–2.3) code review, /review-loop round 2 of 3 (stage-2 executor, in-session)
- Round status: Closed
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 13 - 2026-10-01 - Phase 2 slice A (source), independent cross-family codex peer review (pass stage-2.p1)
- Round status: Closed (0 pending; both applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 14 - 2026-10-01 - Phase 2 slice B (tests) and confirmation of round 13, independent cross-family codex peer review (pass stage-2.p1)
- Round status: Closed (0 pending; both applied by the executor, LEG 2, tests only)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 15 - 2026-10-01 - Phase 2 confirmation of round 14's test fixes, independent cross-family codex peer review (pass stage-2.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 16 - 2026-10-01 - Phase 3 (Tasks 3.1–3.3) code review, /review-loop round 1 of 3 (stage-3 executor, in-session)
- Round status: Closed (all 21 applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with two parallel subagent lenses — correctness/security, and plan/design/tests/structure — merged and verified by the executor)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 17 - 2026-10-01 - Phase 3 confirmation of round 16 and legs c4–c5, /review-loop round 2 of 3 (stage-3 executor, in-session)
- Round status: Closed (both applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 18 - 2026-10-01 - Phase 3 slice A (source), independent cross-family codex peer review (pass stage-3.p1)
- Round status: Closed (0 pending; PR-LOW-014 applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 19 - 2026-10-01 - Phase 3 slice B (tests) and confirmation of round 18, independent cross-family codex peer review (pass stage-3.p1)
- Round status: Closed (0 pending; all four applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 20 - 2026-10-01 - Phase 3 confirmation of round 19's fixes, independent cross-family codex peer review (pass stage-3.p1)
- Round status: Closed (0 pending; applied by the executor, LEG 2, tests only)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 21 - 2026-10-01 - Phase 4 (Tasks 4.1–4.2) code review, /review-loop round 1 of 3 (stage-4 executor, in-session)
- Round status: Closed (all 3 applied; pytest owed by the composer)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 22 - 2026-10-01 - Phase 4 confirmation of round 21, /review-loop round 2 of 3 (stage-4 executor, in-session)
- Round status: Closed (no findings)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review`, sequential lenses in the executor session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 23 - 2026-10-01 - Phase 4 source and tests, independent cross-family codex peer review (pass stage-4.p1)
- Round status: Closed (0 pending; both applied by the executor, LEG 2)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 24 - 2026-10-01 - Phase 4 confirmation of round 23's fixes, independent cross-family codex peer review (pass stage-4.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 25 - 2026-10-01 - Phase 5 (Tasks 5.1–5.2) docs truth-against-code review, /review-loop round 1 of 3 (stage-5 executor, in-session)
- Round status: Closed (all 21 applied; one routed to the composer's `/document` by the spawn's edit scope)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a four-lens read-only subagent fan-out — threat model vs code; retention + flow 22 + cross-doc; practice and product docs incl. C10 and quoted strings; the widened C9 leftover grep — every candidate re-verified in-session against the code before triage)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 26 - 2026-10-01 - Phase 5 confirmation of round 25 + deeper pass over the lighter-covered docs, /review-loop round 2 of 3 (stage-5 executor, in-session)
- Round status: Closed (all applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with two read-only subagent lenses — (1) every round-25 fix re-checked against the code, with residue (o) walked through each crash point of `complete_session` and the start-up order `clean_staging` → `sweep_sessions` → `reconcile_pending` → `record_sweep_results`; (2) a deep truth pass over `clinician-review-guide.md`, `intended-use.md`, `incident-process.md`, `PLAN.md`, `phase-history.md` and `design-system.md` — every candidate re-verified in-session)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 27 - 2026-10-01 - Phase 5 slice A (security docs, C9 rewrite, strings), independent cross-family codex peer review (pass stage-5.p1)
- Round status: Closed (all four applied by the executor, LEG 2, each closing its class; docs only)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 28 - 2026-10-01 - Phase 5 slice B (practice documents) and confirmation of round 27, independent cross-family codex peer review (pass stage-5.p1)
- Round status: Closed (all three applied by the executor, LEG 2, each closing its class; docs only)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 29 - 2026-10-01 - Phase 5 confirmation of round 28's fixes, independent cross-family codex peer review (pass stage-5.p1)
- Round status: Closed (applied by the executor, LEG 2, the class swept exhaustively; docs only)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 30 - 2026-10-01 - Phase 5 confirmation of round 29's fix, independent cross-family codex peer review (pass stage-5.p1)
- Round status: Closed for the build (Part A applied, string + pin; Part B — the current consent text — an OPEN practitioner decision, residue named; see the handoff note's "PRACTITIONER DECISION (PR-MED-030 consent wording)"). Part B DECIDED (a) by the practitioner 2026-10-02.
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 31 - 2026-10-01 - Phase 5 confirmation of round 30's fix, independent cross-family codex peer review (pass stage-5.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 32 - 2026-10-01 - Hardening H1: Phases 1–5 as ONE surface, /review-loop round 1 of 3 (stage-6 executor, in-session)
- Round status: Closed (all 13 applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`; `/review` with a four-lens read-only subagent fan-out over the cross-phase seams — (A) C1 ordering end to end over every key-destroying path and every crash window, with the sweep-vs-Complete concurrency question; (B) C2 over every audit call, `app.main`'s start-up order and each step's failure, the periodic sweep, the hourly `label.enc` decrypt and the shared store; (C) D5 name-to-session matching, Hide names and the D6 path matrix with D1's verification; (D) docs vs code at the seams after the post-doc code fixes of rounds 21–24 and 30 — every candidate re-verified in-session against the cited lines before triage)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 33 - 2026-10-01 - Hardening H1: confirmation of round 32 + class closure, /review-loop round 2 of 3 (stage-6 executor, in-session)
- Round status: Closed (1 applied)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's full suite after round 32: 5254 passed / 4 skipped, ruff clean, mypy 56 files)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 34 - 2026-10-01 - Hardening H2: /simplify over Phases 1–5 as one surface (stage-6 executor, in-session)
- Round status: Closed (all 6 applied as Fix-now; none substantial — no plan task added)
- Source: Claude Code simplify (`/execute-loop` executor `claude-opus-5-5`; two read-only subagent lenses — (1) the stores and controller: `audit.py`, `past_sessions.py`, the plan's parts of `session_store.py` / `session.py` / `app.py`; (2) the UI and exclusions: `ui/past_sessions.py`, `ui/past_sessions_view.py`, `exclusions.py`, `logging_setup.py`, `native_host.py`, `register-native-host.py`, the plan's parts of `ui/main_window.py` / `ui/transcript.py` / `ui/recovery.py` / `ui/note.py` / `ui/models.py` / `ui/bridge.py` — every candidate re-verified in-session under the conservatism guard)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 35 - 2026-10-01 - Hardening H3: /security-review over the whole plan surface (stage-6 executor, in-session)
- Round status: Closed (all 7 applied as Fix-now; PR-MED-030 Part B's decision record corrected — the decision stays OPEN and `CONSENT_TEXT_V3` is unchanged). Part B DECIDED (a) by the practitioner 2026-10-02.
- Source: Claude Code security-review (`/execute-loop` executor `claude-opus-5-5`; two read-only subagent lenses — (1) the two long-lived stores, the CSV and the carried link-following input (a); (2) the exception hooks, the one-line log-failure report, the exclusions, the C9 leftover grep plus the Phase-5 "local only" class, and the PR-MED-030 options — every candidate re-verified in-session against the code)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 36 - 2026-10-01 - Hardening H3: confirmation of round 35 + class closure (stage-6 executor, in-session)
- Round status: Closed (3 applied, docs + one docstring); H3 CONVERGED
- Source: Claude Code security-review confirmation (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's suite after leg f4: full run 5262 passed / 8 skipped with only the fixed test failing, then `test_past_sessions.py` 93 passed / 8 skipped; ruff clean, mypy 56 files)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 37 - 2026-10-01 - Hardening stage (H1-H3 changes), independent cross-family codex peer review (pass stage-6.p1, H4)
- Round status: Closed (2 applied)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 38 - 2026-10-01 - Hardening stage confirmation of round 37's fixes, independent cross-family codex peer review (pass stage-6.p1, H4)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 39 - 2026-10-02 - H5: the 7-year minimum retention, /review-loop round 1 of 3 over the H5 diff only (stage-7 executor, in-session)
- Round status: Closed (2 applied; docs only)
- Source: Claude Code (`/execute-loop` executor `claude-opus-5-5`, in-session; the composer's suite after leg g1: 5300 passed / 9 skipped (directory-symlink variants), ruff clean, mypy 56 files)
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 40 - 2026-10-02 - H5 (7-year minimum retention), independent cross-family codex peer review (pass stage-7.p1)
- Round status: Closed (1 applied — executor LEG 2)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

### Round 41 - 2026-10-02 - H5 confirmation of round 40's fix, independent cross-family codex peer review (pass stage-7.p1)
- Round status: Closed (0 pending)
- Source: independent cross-family codex peer review
- Compacted 2026-10-02 → findings-privacy-professional-controls.md — full per-finding blocks live in that sidecar; treat a missing or partial sidecar as an error, never as "no findings".

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
- **Independent review of `docs/practice/`** — the README's three remaining open questions (consent for people who cannot consent and others in the room; whether the audit CSV's Cliniko ids make it personal information; per-state wording), the `[Reviewer: …]` / `[Practice: …]` marks, and whether an entry this Windows account cannot read must still be kept 7 years (downtime procedure). The patient information stays `patient-info-v1` until first issued; any change after issue is a new version. `Risk if deferred: correctness: the drafts are unreviewed practice documents` · `Revisit by: before the first patient is given the information sheet`
- **PR-LOW-033** — a staged-publication spy test for the label read inside `past_sessions.write_entry` (production is bounded; only the proof is missing). `Risk if deferred: minor` · `Revisit by: next change to past_sessions.py`
- **Residue (t)** — the older readers (pre-plan session files) have no size cap; a same-user denial of service only. `Risk if deferred: minor` · `Revisit by: next hardening pass over session_store.py`
- **`register-native-host.py` on a locked host exe** — WinError 32 (Chrome holds `scribe-host.exe`) prints a raw traceback; it should say "close Chrome and Clinic Scribe, then run this again" and exit non-zero. Seen in the 2026-10-02 smoke. `Risk if deferred: ux-degradation` · `Revisit by: next change to the register script or PLAN.md Phase 7's installer`
- **The consent wording (PR-MED-030 Part B, decided (a))** — fold the qualified local-only wording into the next consent version; do not bump consent for it alone. `Risk if deferred: minor` · `Revisit by: the next consent-text change`

## Follow-Up Continuation Notes
- Next after this plan: the deferred Past-sessions backup/restore (before commercialising), and PLAN.md Phase 7 (pilot and installation, carrying the admin-only exclusions).
- Still applies: D1/D3 (entry layout and per-entry keys), D7/D8 (audit layout and schema), C1–C3.
- Do not rediscover: the Ahpra and state-law research (External Findings); why the generated note needs `generated.enc` (D2); why the WER exclusion names `pythonw.exe` (D10, lessons.md:121).

---
*Plan saved to: .cursor/plans/plan-privacy-professional-controls.md*
*To resume in a new session: run /start-session, then /load-plan*
