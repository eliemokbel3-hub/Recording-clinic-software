# Feature Implementation Plan
**Feature:** privacy-professional-controls
**Overall Progress:** `0%`

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
- **Past sessions tab.** A Heidi-like look-back holding each completed session's generated note, saved note and transcript (never audio). Encrypted with one key per entry, labelled by patient name + date, with a Hide-names toggle, Copy of the saved note, a two-step Delete now, and a retention setting from 1 day to "never" (default "never").
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
- **Retention setting for Past sessions**: 1 day, 7, 30 or 90 days, 1 year, 7 years, or never. The default is **never** (Heidi's compliance-FAQ default, checked 2026-10-01). It comes with a plain warning:
  - a kept transcript becomes part of the practitioner's health record — VIC Health Records Act 2001, NSW HRIP Act 2002, ACT Health Records (Privacy and Access) Act 1997, elsewhere APP 11.2;
  - it can be reached by an APP 12 access request or a subpoena;
  - it lives on this PC and this Windows login only, with no backup;
  - Cliniko stays the system of record.

  Lowering the setting asks for confirmation.
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
  - A month folder is pruned when the month's END + 7 years has passed.
  - Rejected: one sealed blob (about 50–100 MB rewritten per update at 7 years, and one bad byte loses everything); an append-only JSONL (a new torn-line parser and compaction).
- **D8 — `AuditRow` schema** (pydantic, `extra="forbid"`, frozen, `schema_version: Literal[1]`, a before-validator reading `schema_version` first).
  - A newer-version row is kept byte-for-byte, never rewritten, listed as "newer format", and pruned only with its month.
  - An unreadable row is counted and never overwritten.
  - Fields:
    - `session_id`, `session_date`, `origin` (`recorded` or `pre_audit`);
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
- **New settings file `config\past_sessions.json`** `{schema_version: 1, retention_days: int|null, hide_names: bool}`. An unreadable file means nothing is deleted and the tab says so.
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
- **P.2** Set retention to 1 day and backdate or wait a day: the entry expires and the row reads `expired`. Delete now works. Note the listing speed with the entries present.
- **P.3** Re-run `register-native-host.py`: the three WER values exist under HKCU, and the startup warning clears when the app is launched with `scribe-app.exe`. Launched from a console via `python.exe -m scribe_desktop.app`, the uncovered-launch warning shows (D10).
- **P.4** Make `audit\` read-only: Start is refused with the stated line, nothing is recorded, and a queued previous session stays tracked.
- **P.5** Complete a desktop (unlinked) recording and a mock session: the first is archived as "Desktop recording (no Cliniko note)", the second is not archived.

## Deferred / Out of Scope
- **Past-sessions backup/restore.** Likely future work; see Deferred — Actionable Later. It needs the archive layout (D1/D3).
- **Admin-only backup/snapshot exclusions.** Future work for PLAN.md Phase 7's installer.
- **Chrome crash dumps.** An accepted residue, not a goal.
- **Clinic 2's P.1/P.2 from the earlier plans.** Unaffected by this plan.

## Current State / Handoff Note
- Last completed step: Planning complete (native Plan Mode → `/review-plan` 2026-10-01; full-plan pass, three-lens fan-out, deferral gate closed), then the cross-family plan `/peer-loop`.
  - Peer: codex `gpt-6-astra` medium, read-only, rounds 1–5.
  - Findings per round: 5 → 6 → 4 → 2 → 1, 18 in all, every one build-affecting and applied as an amendment.
  - The cap was reached: round 5's single LOW means the loop did not formally converge.
- Current in-progress step: None
- Immediate next action: the practitioner's choice — one more confirmation round (round 6), or Phase 1, Task 1.1 via `/execute` or `/execute-loop`
- Open blockers / open questions: None
- Last plan sync: 2026-10-01

## Review History
Each /review invocation appends a one-line entry here. Round numbers follow /review's **Detect review round** rule.

- 2026-10-01 round 1: 0 CRIT / 0 HIGH / 5 MED / 0 LOW; skew=none; action=plan amended (codex gpt-6-astra medium plan peer-review; 5 build-affecting, all applied)
- 2026-10-01 round 2: 0 CRIT / 0 HIGH / 6 MED / 0 LOW; skew=none; action=plan amended (codex plan peer-review; 6 build-affecting, all applied)
- 2026-10-01 round 3: 0 CRIT / 0 HIGH / 4 MED / 0 LOW; skew=none; action=plan amended (codex plan peer-review; 4 build-affecting, all applied)
- 2026-10-01 round 4: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=none; action=plan amended (codex plan peer-review; 2 build-affecting, all applied)
- 2026-10-01 round 5: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=none; action=plan amended (codex plan peer-review; 1 build-affecting, applied; cap 5 reached)

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

## Tasks

### Phase 1 — Custody foundation: directory removal and the audit record
- [ ] 🟥 1.1: Remove the session directory on EVERY Complete.
  - Files: `session_store.py` `complete_session` (drop the `remove_directory` flag; always remove); `session.py` 1048 / 1086 / 1116 / 1499 / 1711; the docstrings at `session_store.py` 44 / 99-100 / 721-726.
  - Behaviour: after any Complete the session directory is gone. A failed `rmtree` leaves a keyless orphan that the sweep's `orphan_gc` removes; any archive entry for it then commits (C1).
  - Tests: invert `test_session_store.py:634`, update `test_session_machine.py:1500`, and rewrite the transcript-survives assertions (`test_integration_no_sockets.py:937/1165/1332`, `test_transcription.py:1233`). Own verification.
- [ ] 🟥 1.2: The audit store `audit.py`.
  - Contents: `AuditRow` (D8), `AuditLog` (`begin` raising `AuditWriteError` — the real write is the check, there is no separate precheck; `update` never raising, `rows`, `prune`, `export_csv`), the D7 layout, the D9 "start a new audit record" rename, and `_session_created_at` made public in `session_store.py`.
  - Reuses the shared helpers (Key Findings, Integration Notes).
  - Also: add the key description to `test_display_name.py`, and the distinctive field names to `_PAYLOAD_SIGNATURES` (C3).
  - Behaviour: rows round-trip encrypted, and the store keeps its fail-closed rules.
  - Tests: `test_audit.py` (see Validation).
- [ ] 🟥 1.3: Audit wiring in the controller and the store.
  - `SessionController(audit=None)`, wired in `app.main` with a test pinning the wiring.
  - `start()`: build the `RecordingSession` and call `begin` BEFORE `_retire_locked` (759), per Flow 1 / C2. `start_failed` is recorded on EVERY failure after `begin`: one `try` spanning the retire refusal, directory creation (765-768) and the existing cleanup `except` (799-810) (Flow 1 step 5).
  - Model provenance: `saved-provenance.enc` is written in `save_note`'s custody action and read at Complete with the digest match (D8). This is Task 2.1's file; Task 1.3 only consumes it. `user_id` is passed in by the caller from the clinic registry.
  - `complete_session` returns `CompletionFacts` (D4). All five Complete paths update `models`, `deletion` and `past_session`.
  - Discard: `discard()` (both its paths, including the 1218 early return, which records nothing new), `discard_recovered`, and `ui/recovery.py:451` (given the audit log, passing `info.session_id`).
  - Sweep: `app.run_sweep` returns and records its results (C7); the audit prune runs at startup and every 24 h on the sweep timer.
  - `SweepResult` gains `created_at`, captured before deletion (D8, round 1 PR-MED-004).
  - The pending-entry removal on Discard / expiry / orphan_gc (C1) is wired in Task 2.3, once `past_sessions.py` exists.
  - `AuditWriteError` subclasses `SessionControllerError` (D12), with "Start failed: the audit record could not be saved (…). Nothing was recorded."
  - Behaviour: every lifecycle event lands in the row; an audit failure refuses only Start.
  - Tests: listed under Validation (session tests).
- [ ] 🟥 1.4: The write result into the audit.
  - Files: `MainWindow._store_write_record` (`ui/main_window.py:1901`), the one boundary every durable write-record transition passes through: attempt (1852), reconciled-written (1847), finished (1878), unknown (1885-1894). Record attempts, outcome and `written_at`, best-effort (C2).
  - Also: the `WriteRefusal` branch of `_prepare_attempt` (1840) records the refusal's fixed code as `last_refusal`, never the display line (round 1 PR-MED-005).
  - Tests: attempt then finish; unknown → reconciled-written → Complete (the row reads written); an attempt with no finish callback (the row shows the attempt); a pre-send refusal code; an audit failure does not change the write outcome.

### Phase 2 — The Past-sessions archive
- [ ] 🟥 2.1: `generated.enc` (D2).
  - Files: `session_store.py` (`write_generated` / `read_generated` with AAD `generated:<id>`); a new `TranscriptScreen` method on the `save_note` pattern; its call from `MainWindow._on_draft_ready` (1533) and on regeneration; the prose-first rewrite rule; the `NoteDraft` docstring in `note.py`.
  - Behaviour: the first rendered body is kept under the session key, with its provider, style, LM id and prompt version captured at render time (D2), and dies with the session.
  - Also: `saved-provenance.enc` (D8), written in `save_note`'s `with_generation_custody` action with the saved note's digest.
  - Tests: written first, then the note; digest mismatch → `unknown`; never archived; failure injected at the provenance write (Save fails, nothing committed) and at the note write after provenance (Save fails; `_note_committed` / `_note_saved`, Cancel review, retry and reopen agree with disk) (round 4 PR-MED-001).
  - Tests: written under the lease; replaced on regeneration; refused without the lease; removed at Complete and Discard.
- [ ] 🟥 2.2: The archive store and settings `past_sessions.py`.
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
- [ ] 🟥 2.3: Archive at Complete.
  - Files: `complete_session`'s optional `keep` argument (D4) and C1's ordering; `_verify_note_for_completion` returns the verified note; D6's per-path contents and mock detection; `PastSessionWriteError(SessionControllerError)` for failures BEFORE the key boundary, with "Complete failed: the Past-sessions copy could not be saved. No key deletion was performed — try again, or Discard."; after the boundary, marker or directory removal failures never raise into the controller (Flow 3 step 4), and `CompletionFacts` carries `commit_deferred` for the truthful status line.
  - Name resolution (D5): a new `MainWindow.keep_label_for(session_id)` plus a public bridge accessor; the optional label threaded through the five controller methods, `SessionControllerLike` and the fakes; the Complete callers at `ui/transcript.py` 961 / 1003, `abandon_note_and_complete`, `main_window.py:933` and the 1288 lambda.
  - Docstrings: `_CheckoutEncounter` (130-131) and `ui/__init__.py` (13-14).
  - Pending-entry removal (C1): `discard()`, `discard_recovered` and `ui/recovery.py:451` call `remove_pending_entry` BEFORE their `discard_session`. `sweep_sessions` gains a `before_destroy(session_id)` callback, invoked before an `expired` key deletion AND before a dead-key `orphan_gc` deletion (C1's orphan_gc split). Complete removes the marker right after `delete_session_key`. `reconcile_pending` is wired at startup and on the sweep tick.
  - Delete-note paths (D6): the early unlink at `session_store.py:728-730` is removed; `delete_note=True` excludes the note from verification and the archive, and its provenance is read on every attempt; the mock decision uses all three discriminators.
  - Behaviour: every non-mock Complete leaves exactly one verified, committed entry, and the session directory is gone. An interrupted Complete followed by Discard or expiry leaves no entry.
  - Tests: listed under Validation (session and UI tests).

### Phase 3 — The Past sessions tab and the intended-use line
- [ ] 🟥 3.1: The Past sessions tab.
  - Files: `ui/past_sessions_view.py` (Qt-free: labels, the hide-names mask, retention options and pinned warning text, CSV rows, the write-outcome line from the audit row) and `ui/past_sessions.py` (widgets).
  - Placement: added after Note in `main_window.py:437-445`; roots and the settings path injected in all 8 `MainWindow` test sites; the tab pin updated to 9.
  - Features (Flow 5): Copy of the saved note only via `_place_note_text`; two-step Delete now (the `session_screen.py:395-424` pattern, recording `deleted_early`); a confirmation when retention is lowered, then the sweep runs; Export CSV via an injected save dialog with the "not encrypted" line; the persistent status label.
  - UI rules: follow `docs/design-system.md`; no "Cliniko Scribe" text.
  - Tests: listed under Validation (UI tests).
- [ ] 🟥 3.2: The retention sweep in `app.py`: at startup, and at most hourly on the 15-min timer. It records `expired` into the audit row.
  - Tests: timer cadence with an injected clock; no decrypt when the setting is "never".
- [ ] 🟥 3.3: The intended-use line (D14).
  - Files: the constant in `ui/models.py`, shown on `StatusPanel` and the Past sessions tab.
  - Tests: the text is pinned.

### Phase 4 — Exclusions and crash hygiene
- [ ] 🟥 4.1: `exclusions.py`.
  - Contents: an injected `WindowsLayer` (a real one via `os.environ` / `os.path.realpath`, one `GetDriveTypeW`, `SetFileAttributesW` for NOT_CONTENT_INDEXED, a `winreg` read of the WER values); `check_location()` and `check_wer()` returning warning lines (D10; `check_wer` also checks the running interpreter from an injected `sys.executable`); best-effort `mark_not_indexed(root)`; `install_exception_hooks(logger)` (`sys.excepthook`, `threading.excepthook`, `sys.unraisablehook`, each logging only `error_code=type(exc).__name__`).
  - App wiring: in `app.main` before the window is built; warnings shown on `StatusPanel` and the Past sessions label; the no-sockets child mirror extended.
  - Tests: `test_exclusions.py`, plus an autouse sentinel for every `MainWindow` test (C6).
- [ ] 🟥 4.2: `scripts/register-native-host.py`.
  - `register()` writes the three WER DWORDs and verifies them by read-back; `unregister()` deletes them.
  - The docs say that a verify from an agent shell proves nothing (lessons.md:13-20).
  - Tests: a new importlib-loaded script test with a fake `winreg`.

### Phase 5 — Practice documents and the security-doc class rewrite
- [ ] 🟥 5.1: `docs/practice/`.
  - Files: `README.md`; `patient-information-and-consent.md` (`patient-info-v1`); `privacy-information.md`; `downtime-procedure.md`; `clinician-review-guide.md`.
  - Content per Agreed Scope and External Findings: every state cited; the review banner (C10); the Ahpra points; no audio kept; the Past-sessions retention and the "never" consequences; the app never ticks Cliniko's consent box.
  - Verification: H3 grep plus practitioner read.
- [ ] 🟥 5.2: The C9 class rewrite. Every listed statement changes; new rows and flows are added for the audit, Past sessions, `generated.enc`, the CSV and the exclusions, with the named residues:
  - the same-user DPAPI boundary now guarding indefinitely-kept stores;
  - NTFS unlink;
  - admin-only exclusions;
  - third-party backups, the pagefile and hibernation;
  - the `pythonw.exe` WER breadth;
  - the CSV outside custody;
  - expiry only while the app runs;
  - Chrome crash dumps;
  - "never" retention with no backup.

  Also: `intended-use.md` (D14), `incident-process.md` (the audit record is now the durable evidence), `AGENTS.md` subsystem pointers (audit, Past sessions, exclusions, `docs/practice/`), `CHANGELOG.md`, phase-history.
  - Verification: the C9 grep in H3.

### Hardening stage
- [ ] 🟥 H1: `/review-loop` over Phases 1–5 as one surface to convergence. Named targets: C1 ordering, C2 never-blocks, the hourly `label.enc` decrypt (lessons.md:91), name-to-session matching, the D6 path matrix.
- [ ] 🟥 H2: `/simplify`: log findings; trivial → `/fix`, substantial → scoped `/review-plan`.
- [ ] 🟥 H3: `/security-review` (the two new long-lived stores, the CSV, the exception hooks, the C9 grep): log findings with the same routing.
- [ ] 🟥 H4: the cross-family codex pass (`gpt-6-astra`; slice passes over ~15 files, per `codex-window-pacing`) until a clean confirmation.

### Practitioner smoke
- [ ] 🟥 P.1–P.5: see Validation / Verification (from a normal terminal; the practitioner owns it).

## Retained Follow-Up Items
(Populated at completion.)

## Follow-Up Continuation Notes
- Next after this plan: the deferred Past-sessions backup/restore (before commercialising), and PLAN.md Phase 7 (pilot and installation, carrying the admin-only exclusions).
- Still applies: D1/D3 (entry layout and per-entry keys), D7/D8 (audit layout and schema), C1–C3.
- Do not rediscover: the Ahpra and state-law research (External Findings); why the generated note needs `generated.enc` (D2); why the WER exclusion names `pythonw.exe` (D10, lessons.md:121).

---
*Plan saved to: .cursor/plans/plan-privacy-professional-controls.md*
*To resume in a new session: run /start-session, then /load-plan*
