# Feature Implementation Plan
**Feature:** past-sessions-backup
**Overall Progress:** `30%` (13 of 44 tasks)

## Lifecycle State
- Active — REWRITTEN 2026-11-25 as one clean body (the practitioner: "Yes, rewrite it"). It replaces the October 2026 body and the two correction layers (D13, D14) that plan peer-review rounds 6 and 7 added; it folds in every verified finding of rounds 1–8 and three simplifications the practitioner chose that day (decisions 0.10–0.12), and three more taken during the review of this body (0.13–0.15). Nothing is built. NOT ready to build until a fresh cross-family plan peer pass over this body converges (Current State / Handoff Note).
- Reading notes: "the Past sessions page" is the page of the navigation rail (the October text said "tab"); "Settings, Status" is the Status tab of the Settings strip. The Review Findings Log (rounds 1–8) cites the OLD numbering — its D1–D14, Tasks 1.1–1.7 and P.3 / P.4 / P.4b; this body's numbering is new, and the log is a record, not an instruction.

## Completion Status
- Completion timestamp: —
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `plan-privacy-professional-controls.md` (its Deferred — Actionable Later item "Passphrase-protected backup/restore of Past sessions", disposition 2026-10-01; cited again at `plan-installation.md` Deferred and `plan-pilot.md` Deferred / Out of Scope). PLAN.md Phase 6's archive is the store this plan copies.
- Follow-up plans: None

## Goal
Let the practitioner make a passphrase-protected, encrypted backup file of the Past-sessions archive — the kept transcripts, saved and generated notes and their labels — together with the content-free audit record, onto a drive on or attached to this computer, and restore it into Clinic Scribe on a new Windows login or a new computer after a disk failure, a Windows reinstall or a password reset that broke DPAPI. Nothing reaches a network or a cloud folder; the passphrase is never stored; a backup never holds a kept development recording. The agent never reads a real kept transcript, note, name or recording, and never opens a real backup. Ships as 0.5.0 through the existing release path, installed only after the tenth Task 9.1 consultation.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable (`claude-fable-5-1` in October, `claude-fable-5-2` for this rewrite); executor Opus-class (`claude-opus-5-5`) through `/execute-loop`, cross-family peer codex. Tier-gap dosing applied: the container and manifest contract, the audit surface, the hop split, the restore classifications, the run gate, the test-pin inventory and per-task acceptance criteria are fixed below so the executor designs nothing. Every Phase P step is the PRACTITIONER's, from Explorer or a normal terminal, never an agent shell (`docs/lessons.md`, MSIX). Two things run beside this plan: the stronger-voice run (`plan-stronger-voice.md`, builds on `main`) and the ten Task 9.1 consultations on installed 0.4.2 (C13).

Planning sources: the parent plan's deferred item; the October plan and its five peer rounds; the reconciliation of 2026-11-25 against `5d63ed6` and peer rounds 6–8 of the same day (88 findings, every one verified against the code); the Past-sessions and kept-recordings sections of `docs/security/threat-model.md`, `docs/security/retention-schedule.md`, flows 22 and 27 of `docs/security/data-flow-map.md`; `past_sessions.py`, `audit.py`, `session_store.py`, `secure_storage.py`, `exclusions.py`, `sample_notes.py`, `app.py`, `ui/past_sessions.py`, `ui/past_sessions_view.py`, `ui/main_window.py`, `ui/bridge.py`, `ui/recovery.py`, `ui/tasks.py`; the practice documents; the practitioner's answers (Phase 0). No `/explore` scratch was consumed (the two that exist are unrelated).

### Agreed Scope (Build Now)
- **A backup file** (`.csbk`, D2): a stored-only ZIP read only through its encrypted manifest, one file per backup, named by date. It holds every committed Past-sessions entry that opens — its ciphertext files byte for byte and its entry key wrapped under a key derived from the practitioner's passphrase — and the audit record's rows with its store key wrapped the same way (D1).
- **Back up…** and **Open a backup…** on the Past sessions page (D10), each behind a passphrase prompt. A backup proves that every session it holds opens, and says what it left out (decision 0.11, 0.12). Opening a backup shows what the file holds and offers Close (the check) or Restore.
- **One status line** (decision 0.10): the last backup's date and how many sessions were kept since, shown after 7 days. The date lives in the backup settings file; the audit record's format does NOT change.
- **A location rule of its own** (D7): fixed and removable drives only; a cloud-synced folder the app can see, a network location, the roaming profile and the app's own folders are refused; the data folder's own volume is warned. The same rule admits the file chosen in Open a backup.
- **Restore** (D8) only ADDS: sessions and audit rows that are absent here. A session that is present here in any form is never touched, and a deleted one is never brought back. Restored audit rows are re-encrypted under the local audit key (D9).
- **Set aside** (D8; decision 0.15, 2026-11-25): after a Windows password reset this login can no longer open the sessions it holds. One button on the page moves those sessions — and only those — unread into a folder beside Past sessions, with nothing deleted and no deletion recorded; Restore then adds them from a backup exactly as on a new computer. It REPLACES October's key repair (decision 0.9).
- **A session that holds a kept recording is never backed up** (D12; decision 0.13, 2026-11-25): its entry key also unlocks the recording, and the consent says the recording can be opened only from the practitioner's own Windows login on that computer. The session becomes eligible once its recording is deleted. Deletion itself does not change.
- **A run gate** (D11): while a backup or restore runs, nothing else in the app can write the archive or the audit record.
- Version **0.5.0** (D13), a build of record, installed by the practitioner (Phase P).
- **Documents** (D14): the threat model's new section, data-flow flow 30, the retention schedule's rows, the rollback rule "below 0.5.0", a `patient-info-v4` draft, and every sentence in the documents and the app that says there is no backup or that a deletion cannot be recovered.

### Deferred — Actionable Later
- **Kept development recordings in the backup** (decision 0.2: excluded). Why: the consent document promises "The program makes no backup of it"; including audio needs `development-consent-v2`, a re-consent of every patient whose recording is held, and a far larger file. Intended outcome: a `development-consent-v2` and a per-backup "include kept recordings" tick. Trigger: the practitioner's decision to rely on kept recordings beyond the pilot. `Risk if deferred: minor` · `Revisit by: before the pilot's exit gate if kept recordings are still held`.
- **Scheduled or automatic backups.** Why: a backup needs the passphrase at the moment it is made (never stored), so it is a deliberate act. `Risk if deferred: correctness` (a forgotten backup is a stale backup; the status line is the control) · `Revisit by: commercialisation`. Gate disposition 2026-10-09: Defer.
- **Backing up the practitioner profile, learned style, learned phrases, clinic list and settings.** Why: recreatable, and the voice profile is a biometric the threat model keeps on this login only. Intended outcome: a separate "settings export" if re-setup proves costly. `Risk if deferred: ux-degradation` · `Revisit by: the first real restore`. Gate disposition 2026-10-09: Defer.
- **Backup and restore dates in the audit record** (the October design's audit row v4). Dropped 2026-11-25 (decision 0.10) for the one last-backup date. Intended outcome if ever wanted: a dated plan of its own, since it changes the audit record's format. `Risk if deferred: minor` (the audit CSV shows no backup dates) · `Revisit by: commercialisation`.
- **Clinic API keys** live in Windows Credential Manager and are re-entered after a reinstall (the Clinics tab). Not a backup item: a credential never enters a file. Named in the restore procedure.

### Excluded — Revisit Only If Needed
- **Any network or cloud destination**, including a NAS or a OneDrive folder, even for an encrypted file (decision 0.4). Reopened only by a new practitioner decision with the documents' independent review.
- **Incremental or differential backups.** Entries are text; a full copy is small and verifiable as one unit. Gate disposition 2026-10-09: Exclude.
- **Cross-channel restore** (a developer-build backup into the installed app or the reverse). The manifest names the channel and each build refuses the other's. Gate disposition 2026-10-09: Exclude.
- **Restoring a single entry.** Restore adds whatever is missing; Delete now serves any unwanted entry afterwards. Gate disposition 2026-10-09: Exclude.
- **A passphrase manager, hint or recovery.** A lost passphrase is a lost backup, by design; the documents say so. Gate disposition 2026-10-09: Exclude.
- **A run ledger of backups.** Dropped in October; the one date of decision 0.10 is all the app remembers.
- **An entries-only backup when the audit record cannot be read.** Dropped 2026-11-25: Back up refuses until the audit record reads again (D1). The October fallback made a file whose deletion history could not be known.
- **The app calling a backup "complete" or "safe", or saying when one may be destroyed.** It reports what a backup holds and what it left out, and — when a backup is opened — what is and is not on this computer, as counts. It gives no verdict. When older backups may be destroyed is ONE rule for the practitioner, written in the documents with its limits named (decision 0.14, D14).
- **Repairing a session's key in place** (October's decision 0.9). Dropped 2026-11-25 (decision 0.15) for the set-aside: a rule that changes an existing entry could not be made safe against a surviving deletion record, an interrupted run and a rollback (peer rounds 12–15).

### Accepted Assumptions — Revalidate Later
- **Backup size.** Roughly 100–300 KB per entry; 1 000 entries ≈ 0.3 GB. One backup file is capped at 1 GiB (D2), about 3 000–10 000 entries. Check: the first real backup's size at P.5. Gate disposition 2026-10-09: Accept (the cap added 2026-11-25).
- **Argon2id at 256 MiB fits the clinic computers** (the app already loads a 2.3 GB language model); a `MemoryError` refuses by name. Gate disposition 2026-10-09: Accept.
- **The practitioner keeps the passphrase and the drive apart** — an operating rule in the documents, not something the app can check. Gate disposition 2026-10-09: Accept.
- **A backup or restore happens with no recording live, none waiting on the Recovery page, and the practitioner present.** The app refuses otherwise (D11). A clinician with an unreviewed recording must review or discard it before backing up. Gate disposition 2026-10-09: Accept.
- **Changes made to the app's files from OUTSIDE the app during a run** (another program of the same Windows user) are the threat model's accepted same-user risk. The run gate excludes the app's own writers; the checks named in D5, D6 and D8 catch an outside change where a cheap check exists; the executor adds no further race hardening. Accepted 2026-11-25.
- **A removable drive may use FAT32 or exFAT**, where file numbers and timestamps are coarse. So no check that can REFUSE a backup, an Open or a Restore depends on a file number or timestamp of the `.csbk` file, whether it is being written or opened: its bytes are bound by SHA-256 (D6, D8). The one use of a file number there — removing this run's own `.part` after a failure — fails safe: when the number cannot be confirmed the file is left. (The archive's own files, on the data folder's volume, ARE bound by size, time and file number between hops B and C, D5.)

### Key Design Decisions
See `Design Decisions` (D1–D15). The practitioner's decisions are Phase 0's `[decision]` tasks: 0.1–0.6 and 0.9 (2026-10-09; 0.9 superseded by 0.15) and 0.10–0.15 (2026-11-25), with five more answers of 2026-11-25 recorded where they apply — "0.5.0 (Recommended)" (D13), "After the tenth (Recommended)" (C13), "Keep pop-ups (Recommended)" (D10), "Add it to the plan (Recommended)" (superseded the same day by decision 0.13, D12), "Before the first real backup (Recommended)" (Phase P).

## Key Findings

### Files / Symbols Involved
Verified at `5d63ed6` (2026-11-25). Find every symbol by name; a line number here is a hint, never an anchor.
- `desktop/src/scribe_desktop/past_sessions.py` — `PastSessionStore`. `_entry_dirs(strict=)` / `_committed_dirs(strict=)`: an entry is a folder holding `key.dpapi` and no `pending`; non-strict listing swallows an unlistable root, and an id-shaped child whose link state cannot be read is silently omitted. `_read_label`, `_parse_label`, `_label_aad(id)`, `generated_aad(id)`; `PastSessionLabel` carries `completed_at`, `has_saved`, `has_generated`, `shadow`. `_stage` writes a fresh key per staging (so each generation of an id has its own key), `_verify_staged` proves a staged entry through `read_transcript`, `read_note`, `read_generated` and takes a PLAINTEXT source — restore needs a sibling. `_publish(staging, final)` REMOVES `final` key-first and then renames (a retried Complete's rule): restore must not use it. `clean_staging` removes every `.staging\<id>` at start-up and on each sweep tick. `delete_entry` is `_committed` → `_remove_key_first` → `_forget_dates`. `_remove_key_first(directory)` unlinks `key.dpapi`, then `audio-key.enc` best-effort, then `rmtree(ignore_errors=True)`, and returns True once the key is gone whatever the rest did. `delete_recording` zeroes `audio-key.enc` in place (link check, `r+b`, `_is_own_key_file`, zeros, flush, `fsync`, read back). `_audio_key_state` → `absent | zeroed | live | unknown`; `_is_own_key_file` needs a regular file, link count 1, 1–60 bytes, so an EMPTY key file is `unknown`. `_recording_state` → `none | kept | gone`, and returns `none` for a live key whose `audio.enc` is missing. `_remove_part` / `PartKernel` open their own exclusive handle and delete by file identity (Export's pattern). `_forget_dates` drops the cached completion dates and the cached unreadable-label mark for an id.
- `desktop/src/scribe_desktop/audit.py` — `AuditRow` v3 (unchanged by this plan), `_NEWER`, `_row_aad(id)` = `b"audit:" + id`, `_MONTH_RE` (digits only: it admits a month 13), `month_prune_at`, `AuditLog.rows` / `row_for` / `update` / `_update` / `_find` (two row files for one id are ambiguous and make `row_for` / `update` raise), `_open_key(create=)` (a missing key beside rows raises `AuditUnavailable("key_missing")`; `_NoKey` only for a store with no key and no rows; `key_unreadable`; `unavailable`), `key_unreadable()`, `reset()` (quarantines the old store and starts a fresh key), `record_past_session` → `_past_session_recorded`, which on `deleted_early` / `expired` sets `recording.deleted_at` whenever `recording.kept_at` is set. The key custody is hard-wired to `wrap_key_to_file` / `unwrap_key_from_file` with no seam. No whole-row import exists.
- `desktop/src/scribe_desktop/session_store.py` — `wrap_key_to_file`, `unwrap_key_from_file` (reads the file itself and folds a read error, a dead blob, a DPAPI refusal and a foreign description into one `KeyCustodyError`), `key_blob_is_dead`, `atomic_write_bytes` (its temporary is `<name>.tmp`), `link_state` (an `lstat`: False / True / None), `read_capped`. `secure_storage.SessionCrypto` (AES-256-GCM; `export_key()` returns immutable `bytes`).
- `desktop/src/scribe_desktop/exclusions.py` — `check_export_location` (fixed drives only; resolves the path BEFORE it looks for a network location), `WindowsLayer` (`environ`, `realpath`, `drive_type(root)`, `file_attributes`; no volume identity; the conftest makes the real one raise), the constants `DRIVE_REMOTE` and `DRIVE_FIXED` only, and the unrelated File-History names `check_backup_exclusions` / `backup_exclusions` (hence this plan's `check_archive_backup_location`).
- `desktop/src/scribe_desktop/sample_notes.py` — the codebase's bounded `zipfile` reader (its bounds and error handling are the pattern; it admits deflated input, which D2 does not).
- `desktop/src/scribe_desktop/app.py` — `PeriodicSweep.__call__` (the one entry point of the 24 h session sweep, the audit prune and the retention sweep); the start-up order `recover_exports` → `clean_staging` → `reconcile_pending` → the kept-fact repair → tidy → `run_retention_sweep`; `run_offline_self_check` behind `--self-check-offline` (exit 0 / 1 / 2), which `scripts/build-release.py --audit` runs inside the frozen bundle and whose failure text names codes 1 and 2.
- `desktop/src/scribe_desktop/ui/past_sessions.py` + `ui/past_sessions_view.py` — the page and its Qt-free decisions: `refresh` (lists on entry, each label decrypted once), `on_left` (drops every name), `on_delete_clicked` (reads `store.recording_state` ONCE, records the kept or already-deleted fact BEFORE `delete_entry`, then `record_past_session("deleted_early")`), the retention sweep's `before_held_delete` callback (same order; for a LIVE recording the deletion goes ahead whatever the callback returns or raises, while an already-gone recording whose deletion it did not record is held and counted as not deleted) and `RetentionSweepReport.kept` (the expired ids whose one read found a recording held), `DELETE_CONFIRM_MESSAGE`, `retention_confirm_text`, `delete_failed_line` ("…Nothing else changed - try again."), `RETENTION_WARNING` ("makes no backup of its own"), `PastSessionsAudit` (the Protocol that grows with each audit method), `ChooseCsvPath` / `ChooseWavPath` (the dialog seams), `reset_audit_button`.
- `desktop/src/scribe_desktop/ui/main_window.py` — builds `self.rail` (`NavigationRail`), `self.settings_strip`, the pages and every screen; `_live_session_ids()` = `controller.custody_protected_ids()`; `closeEvent` refuses branch by branch, then calls `note_screen.prepare_close()`, then a generic busy check that lists seven screens and NOT the Past sessions page. `ui/recovery.py` — `protected_session_ids()` (a recovered transcript awaiting Complete or Discard is in neither list), `is_busy`, `refresh`. `ui/bridge.py` — `_refuse(action, reason)` (clears the development tick for every refused Start but the warm-up hold's), `_situation(action)` (a refusal is kept while this tuple is unchanged), `publish()`. `ui/tasks.py::TaskThread` — `succeeded(object)`, `failed(str)` carrying `Type: message`, catching `Exception` only. `ui/models.py` — `chrome_refusal_message`, `START_GETTING_READY_MESSAGE`. The refusal codes are desktop-side strings; nothing under `extension/` or `protocol/` lists them.
- Tests that pin today's shapes and change with this plan, each a NAMED change: `test_install_layout.py` `_NON_PATH_LITERALS` (every non-path `ClinikoScribe` literal by owner; checked both ways) and its version check (derived from `pyproject.toml`); `test_ui_screens.py`'s exact-text tests of the Delete now confirmation, the shorter-retention confirmation and the delete-done line; the tests of `RETENTION_WARNING`. `test_shadow_exits.py` stays UNEDITED: it pins text widgets only in `ui/note.py` and `ui/past_sessions.py`, and package-wide every selectable-text flag, plain list, item view, combo box, clipboard or drag call — so the new dialogs live in their own file and hold none of those. `test_audit.py` and `test_schema_versions.py` need no pin change (the audit row is unchanged).
- `desktop/pyproject.toml` requires `cryptography>=43`; Argon2id arrived in 44; `desktop/requirements-build.txt` hash-pins 49.0.0 for the frozen build.
- Documents the feature makes false (the grep of Task 0.8 is the authority; these are today's known places): `docs/practice/patient-information-and-consent.md` ("can only be opened from your practitioner's own Windows login", "makes no backup of it", "cannot be undone"), `privacy-information.md`, `clinician-review-guide.md` (its Past-sessions sentence and "for good"), `downtime-procedure.md` ("Losing the computer … there is no backup"; "Past sessions problems": "cannot be read again on this account"), `docs/practice/README.md` ("nothing it keeps has a backup"), `development-recording-consent.md` (two sentences that stay TRUE under decision 0.2); `docs/security/threat-model.md` (residue (c) "UNTIL I DELETE THEM", the deferral notes, "the encrypted name label … nowhere else"), `retention-schedule.md` (the Past-sessions and kept-recording rows), `data-flow-map.md` (flow 22, the "ONLY encrypted under per-session keys" non-flow, the Chrome summary's "its Past-sessions label and nowhere else"), `intended-use.md` ("this Windows login only, with no backup"); `docs/design-system.md` (the retention-warning quote, the shorter-retention confirmation's quote, "No secondary windows beyond short confirmations"); `PLAN.md` ("Backup/restore of Past sessions is deferred"). The highest data-flow number is 29, so the new flow is 30. The patient sheet in use is `patient-info-v3`. The printable handouts are the git-ignored `practice-handouts/`.

### Codebase Integration Notes
- Every entry is its own compartment (a fresh key, DPAPI-wrapped). Wrapping each entry key under the passphrase-derived key and copying the entry's files unchanged keeps that compartment through backup and restore. Restore re-wraps the entry key for THIS login (the only DPAPI write) and proves the staged entry through the existing readers.
- The audit record has ONE store key and per-row AAD. Rows are copied as ciphertext with the store key wrapped; at restore each row is decrypted under the backed-up key and re-encrypted under the LOCAL key — `_NEWER` rows too, their plaintext unchanged (copied as ciphertext they would be unreadable here, and a second row file for one id breaks that id for ever).
- `PastSessionStore` and `AuditLog` methods run on the GUI thread (the privacy plan's C5). Argon2id takes about a second and a USB write several, so a run is split into hops (D5, D6, D8): workers derive the key, read and write files and verify; the GUI thread does every store and audit call. `clean_staging` would remove a restore's staging folder, which is one reason sweep ticks are skipped for the whole run (D11).
- A backup never copies `key.dpapi` (this login's), `pending` entries, `.staging`, `audio.enc`, `audio-key.enc` or the export ledger.
- Restore and deletion: the tombstone is the audit row's `past_session.state` (`deleted_early` / `expired`). Restore reads the LOCAL row first, then the backup's. The archive may keep entries for ever while audit months prune at 7 years, so an entry can outlive its row's month.
- The same-login DPAPI break (decision 0.15): after a Windows password reset every entry still has a `key.dpapi` that this login's DPAPI refuses, and the audit key is unreadable. The audit record already has a control for that state — `AuditLog.reset` renames the whole store aside, unread, nothing deleted ("Start a new audit record"). The archive gets the same kind of control, but per entry, because sessions completed AFTER the reset are readable and must stay: the set-aside (D8). An unwrap failure can also be a passing read error or a DPAPI fault, so the set-aside judges a key blob only from bytes it has read, through a new blob-based seam, and only while a fresh DPAPI round trip works.
- Nothing here opens a connection. `assert_offline_env` and the `TestConfinement` pin are unaffected.

### External / API Findings
- `cryptography.hazmat.primitives.kdf.argon2.Argon2id(salt, length, iterations, lanes, memory_cost, ad=None, secret=None)` — since `cryptography` 44 on OpenSSL ≥ 3.2; `memory_cost` is in KiB. OWASP's minimum is m = 19 MiB, t = 2, p = 1; this plan uses m = 256 MiB, t = 3, p = 1 (about 1 s on a recent laptop).
- `zipfile` (stdlib): `ZipFile(fileobj, "w", ZIP_STORED, allowZip64=False)` writes over an open read-write file object and raises `LargeZipFile` past the classic limits (2 GiB offsets, 65 535 members). On READ it builds one object per central-directory record until the directory's declared BYTE length is consumed, whatever the count field says — hence D2's own directory walk before `ZipFile` is constructed.
- Windows: `GetDriveTypeW` (`DRIVE_REMOVABLE = 2`, `DRIVE_FIXED = 3`, `DRIVE_REMOTE = 4`, `DRIVE_CDROM = 5`, `DRIVE_RAMDISK = 6`); `GetVolumePathNameW` gives the mount point of the volume holding a path and `GetVolumeNameForVolumeMountPointW` that volume's GUID name, which is the same whichever drive letter or mounted folder reaches it. `os.rename` never replaces an existing file or directory on Windows. On FAT32 / exFAT a file's number can change when it is renamed.

## Planned Workflow Summary

### Flow 1 — Back up
Past sessions page → **Back up…** → the admission check (D11; a refusal line and nothing else) → the passphrase dialog (twice, minimum 20 characters, "The passphrase is never stored. Without it the backup cannot be opened by anyone, including you.") → a save dialog proposing `ClinikoScribe-backup-YYYY-MM-DD.csbk` in the last admitted folder → the location rule (refused, or a same-volume warning to confirm) → the run begins (admission re-checked and the gate taken in one step) → hop A derives the key (worker) → hop B snapshots the archive and the audit record (GUI thread) → hop C reads, proves, writes and verifies the file (worker) → hop D records the last-backup date and shows the success line → the run ends. The success line: "Backup written: <file name> - N sessions, M audit rows. Nothing eligible was left out. Keep the passphrase somewhere other than the drive." — its middle sentence shown ONLY when no eligible session and no audit row was left out and the file's `not_restorable` is 0; "eligible" is every session whose recording key is confirmed absent or zeroed (D12); the sentence describes THIS file against what the app could read today, and says nothing about what an older backup holds or about anything this computer has lost (D14's rule and its named limits); otherwise the middle sentence is "Left out: X sessions, Y audit rows. Cannot be restored by this version: V." (a zero part omitted; no advice — decision 0.14). Sessions left out ONLY because their recording key is live do not count here (they are in no backup, old or new, D12); when there are any, one more sentence says so, in words that are true whether or not the audio file is still there: "H sessions are not in a backup because a kept recording or its key is still present." With nothing to back up: "Nothing to back up yet."

### Flow 2 — Open a backup (the check)
**Open a backup…** → the admission check → an open dialog → the SOURCE rule (D7; a refused file is never read) → the header pre-check (bounds, format version, channel) → the passphrase dialog (once) → the run begins → hop A (worker) derives the key, authenticates the manifest, verifies every member's hash and proves every session opens → the restore plan is computed (GUI thread) → the summary dialog: what the file holds, what it left out when it was made and what Restore would do here (counts only, no verdict — D10), with **Close** (nothing written — the check; the default button) and **Restore** → Close ends the run.

### Flow 3 — Restore (from Flow 2's Restore button)
The whole file is verified again against what Open verified (worker) → audit rows first, then entries, each reclassified immediately before it is written (GUI thread, D8) → the last-backup date is advanced to the file's date if later (a failure to save it adds "The backup date could not be saved." to the report and stops nothing) → the run ends → the page re-lists → the final report line (D10).

### Flow 4 — Disaster
A new computer or login: install 0.5.0, open Clinic Scribe, set the retention period and Shadow mode as they were (a fresh login starts at "Until I delete them" with shadow mode off; the retention period decides what Restore adds), Past sessions → Open a backup… → Restore, then the Clinics tab for the API keys and the Practitioner tab to re-enrol. The same login after a Windows password reset, where the page lists sessions that "Cannot be read on this Windows account": do NOT Delete now those sessions (a Delete now records a deletion, and a deleted session is never restored); Past sessions → Start a new audit record (the existing control, shown when the audit key is unreadable); then Set aside sessions that cannot be opened… (D8: they are moved unread beside Past sessions, nothing deleted); then Open a backup… — its summary shows how many sessions Restore can add on this computer (it counts every session of the backup that is not here, and does not say which of them were set aside; one whose deletion is recorded, or that is older than the retention period, is not added) — → Restore. If the set-aside's line said some sessions were not moved because of a recording file, and that recording had already been deleted: close and reopen Clinic Scribe after the Restore, then Set aside and Restore once more. (At that start the app clears the files of a recording that was already deleted. Where the Restore brought that session's audit row back first, the deletion is recorded on it; where the app's own start-up or periodic sweep ran between Start a new audit record and the Restore, it found no row, recorded nothing and cleared the files, and the row restored afterwards shows the recording as kept with no deletion date — D12's named residue, peer round 17.) A session completed after that backup was made is in no backup: it stays set aside and unreadable. The downtime procedure names both sequences.

## Design Decisions

- **D1 — What is backed up: every committed Past-sessions entry that opens, and the whole audit record; nothing else (decisions 0.1, 0.2, 0.11).** Per entry: `label.enc`, `transcript.enc`, and `note.enc` / `generated.enc` when the label says they exist, byte for byte; and the entry key wrapped under the backup key (D2). `key.dpapi`, `pending` entries, `.staging`, `audio.enc`, `audio-key.enc`, the export ledger and everything outside the archive and the audit store are never copied. An entry is LEFT OUT, counted by reason and never fatal, when it is: `holds_recording` (its recording key is live — D12; counted apart from the other reasons, and never a reason to keep an older backup), `unreadable` (its key does not unwrap or its label does not open), `incomplete` (a file its label calls for is missing, or it holds a content file its label does not call for), `damaged` (a file does not authenticate under the entry's key), `changed` (it changed between the snapshot and the copy), or `uninspectable` (its folder or a file cannot be inspected, or is a link). The audit record: every row file whose bytes authenticate under the store key and that is IMPORTABLE — `audit.row_importable(plaintext, session_id, month)`, a pure function: the plaintext decodes to a row whose own session id and session-date month are the file's, or it is `_NEWER` — as ciphertext with the store key wrapped; a row that cannot be copied is left out, counted, and its id listed in the manifest as unknown (D9). Back up is REFUSED while the audit record cannot be read (`AuditUnavailable`, any code): "The audit record cannot be read - see Past sessions problems in the downtime procedure." A shadow recording's entry is included as any entry and stays a shadow entry (C14). Alternatives rejected: entries only (the audit record is the 7-year obligation and the deletion history); the whole data folder (a biometric, plaintext configs, and DPAPI blobs useless elsewhere); an entries-only fallback (Excluded).
- **D2 — The container: `.csbk` v1, a stored-only classic ZIP read only through its encrypted manifest (the practitioner's choice of the ZIP, 2026-10-09).**
  - Members: `header.json`; `manifest.enc`; `audit-key.enc` (present when the audit store has a key); `keys/<id>.enc`; `entries/<id>/<label|transcript|note|generated>.enc`; `audit/<YYYY-MM>/<id>.enc`. The file-name prefix exists once, as `past_sessions_backup.BACKUP_FILENAME_PREFIX = "ClinikoScribe-backup-"`.
  - `header.json` (plaintext, the first member at offset 0, ≤ 4 KiB; pydantic, `extra="forbid"`): `format_version: 1`, `app_version`, `channel`, `made_at`, `kdf: {name, salt, iterations, lanes, memory_cost}`, `max_entries`, `max_rows`. The two counts are the PLANNED numbers from the snapshot: upper bounds for the pre-filter, never shown. The header holds nothing the writer learns only while it copies: it is written first and never rewritten (the manifest's own size is bounded in the preflight, below).
  - `manifest.enc`: AES-GCM under the backup key `K_b` with `aad = b"csbk-manifest:" + sha256(header_bytes)`, so any change to the header fails the manifest. The manifest (pydantic, `extra="forbid"`) is ONE structure, so its parts cannot disagree: `channel`, `app_version`, `made_at`; `entries: {id: {key: {size, sha256}, files: {label, transcript, [note], [generated]: {size, sha256}}}}`; `audit_key: {size, sha256} | null`; `rows: {id: {month, size, sha256}}`; `rows_unknown: [id]`; `left_out: {entries: {reason: count}, rows: count}`; `not_restorable: count` (entries whose audit row this build cannot read, D5). Ids match `SESSION_ID_PATTERN`; `label` and `transcript` are required; a month is a real calendar month for which `month_prune_at` computes. The counts shown anywhere are the lengths of these maps.
  - Key wraps: an entry key is `AESGCM(K_b)` over the 32 bytes with `aad = b"csbk-entry-key:" + id`; the audit key with `aad = b"csbk-audit-key"`. `K_b` is fresh per backup (fresh salt).
  - Limits, each a closed refusal code: the whole file ≤ 1 GiB (`MAX_BACKUP_BYTES`; no ZIP64 anywhere); ≤ 65 535 members; an entry file ≤ 64 MiB (the label by its existing cap); a row by `MAX_ROW_FILE_BYTES`.
  - The reader, in this order, refusing by name at the first failure and writing nothing: (1) the PREFLIGHT, before `zipfile` is used at all, through an injected size-and-read seam: the file's size; the end record found in the last 64 KiB + 22 bytes; no ZIP64 record; an empty archive comment; the declared member count ≤ 65 535; the central directory's size ≤ 256 bytes × that count; then the preflight reads the directory and WALKS its records itself (`struct` only): their number equals the declared count, every name is ASCII, ≤ 128 bytes and UNIQUE in the directory, no record has an extra field or a comment, every method is stored with equal sizes, the first record is `header.json` at offset 0, ≤ 4 KiB, and exactly one record is named `manifest.enc`, its size ≤ 16 MiB; then each record's LOCAL header is read at its offset and checked the same way — the signature, the stored method, no data-descriptor flag, the directory's name and sizes, and NO extra field (a ZIP64 field can hide there alone). (2) the header parsed and bounded; `format_version` 1; the KDF name known and every work parameter inside D3's envelope BEFORE any derivation. (3) the channel pre-filter (the header's copy; a courtesy refusal before the passphrase). (4) the key derived; the manifest decrypted — a wrong passphrase and a damaged manifest give ONE line. (5) the manifest's own `channel` compared; its counts no greater than the header's bounds; the ZIP's member set EXACTLY the two envelope members plus the names the manifest's structure implies; every member stored, its size the manifest's; every SHA-256 verified. (6) the OPEN CHECK: `audit-key.enc` unwraps and every row authenticates under it and is classified by `audit.row_importable`; every entry key unwraps and that entry opens (`past_sessions.entry_opens`, D5), which also yields each entry's completion date for the summary and the plan — dates only, no key and no text leave the worker. The reader iterates the manifest, never the ZIP's own listing.
  - Alternatives rejected: a hand-rolled record stream (declined 2026-10-09); one file per entry; SQLite; compression (nothing to gain on ciphertext; a bomb surface); ZIP64 (a second format to bound for an archive that will not reach 1 GiB).
- **D3 — The passphrase and the KDF (decision 0.3).** Chosen by the practitioner, entered twice, minimum 20 characters, no composition rules; never logged, never stored, never in a settings file. Argon2id, parameters in the header: salt 16 bytes random, length 32, `iterations = 3`, `lanes = 1`, `memory_cost = 262144` (256 MiB). A reader accepts only a FINITE envelope, checked before any derivation (the header is unauthenticated until the manifest decrypts): `memory_cost` 65 536 … 524 288 KiB, `iterations` 2 … 10, `lanes` 1 … 4 (`kdf_out_of_range` otherwise), so a later build can raise the defaults and still open older files. A `MemoryError` during derivation is caught by type and refused by name. `desktop/pyproject.toml`'s floor becomes `cryptography>=44`. The frozen build proves Argon2id on every build (Task 1.7); if that proof ever fails, the fallback is a DATED DECISION to use scrypt (`n = 2**17, r = 8, p = 1`; envelope `n` 2**14 … 2**18), named by the header's `kdf.name` — it is not built now. Residues named: Qt's widget text and the pagefile may hold the passphrase (BitLocker, as for every secret in memory); a weak passphrase on a drive kept for years is the practitioner's risk.
- **D4 — One object owns a run's secrets and its gate: `ArchiveRun` (GUI thread).** Created when the passphrase dialog is accepted. It holds the passphrase buffer and the derived key `K_b` as `bytearray`s, and — once the run begins — the run gate (D11). Its `close()` is idempotent: it zeroes both buffers, releases the gate, re-enables the window and refreshes what the gate held back; it is called on EVERY exit — a cancelled save or open dialog, a refused or declined location, a refused admission, a failed dispatch, any hop's failure, Close, and success. Each worker's `finished` signal is connected as a fallback: a worker that ends with neither result signal is treated as `unexpected` and closes the run. Hop A's worker writes the derived key INTO the run object; no Qt signal ever carries a key, a passphrase or anything derived from them, and a worker's result is key-free data only. The passphrase buffer is zeroed as soon as hop A returns; nothing after hop A needs it. Every worker body catches `Exception` and reports a closed code (`BackupFormatError(code)` / `BackupRunError(code)`), so `TaskThread.failed` carries a type and a code; anything unforeseen is `unexpected`, with the exception's TYPE name logged and nothing else. For Open and Restore the run also owns a `BackupReader` (the path, the authenticated manifest, the whole file's SHA-256); the GUI-thread planner and restorer take it explicitly and unwrap one entry key or the audit key at a time into a `bytearray` zeroed after use. Residues named: `SessionCrypto.export_key()` and `AESGCM` each make an immutable copy that cannot be zeroed — "zeroed" means the `bytearray`s, and the tests assert exactly those.
- **D5 — Reading the archive for a backup: a snapshot on the GUI thread, then a proved copy on the worker.**
  - Hop B, GUI thread. `PastSessionStore.backup_snapshot()`: a STRICT listing (an archive that exists but cannot be listed refuses the run, `archive_unreadable`); for each id-shaped child — a link, or a link state that cannot be read → left out `uninspectable`; `key.dpapi` CONFIRMED absent → not an entry (the leftover folder of a key-first deletion, which `reconcile_pending` removes), skipped silently; a `key.dpapi` or `pending` marker whose presence cannot be told → `uninspectable`; `pending` → not an entry, skipped silently; the recording-key custody, read once BEFORE any content is looked at (`_audio_key_state`, D12): `live` → left out `holds_recording` whatever else is wrong with the entry; `unknown` → `uninspectable`; only `absent` or `zeroed` goes on; then `key.dpapi` checked as an ordinary single-link file and unwrapped ONCE through the store's seam, and the label decoded with that same key (`_decode_label`) → either failing is `unreadable`; the REQUIRED file set from the label (`label`, `transcript`, `note` when `has_saved`, `generated` when `has_generated`) → a required file missing, or a content file the label does not call for, is `incomplete`; per required file its size, modification time (ns), file number and device, and the SHA-256 of `label.enc` as read. A file that is itself a link — `key.dpapi`, the label or any required file, by its own `link_state` read BEFORE it is opened — makes the entry `uninspectable`. `prepare_backup(store, audit, run)` wraps each entry key under `K_b` at once and zeroes the plain bytes. `AuditLog.backup_snapshot()` (D9) gives the store key (wrapped at once, zeroed) and row descriptors; `AuditUnavailable` refuses the run. For each included entry `audit.row_state(id)` is read: `newer` or `unreadable` adds to `not_restorable` (the entry is still copied). The planned sizes are summed: over `MAX_BACKUP_BYTES` or 65 535 members refuses the run (`too_large`) before any file exists. Nothing at all to plan — a readable archive with no committed entry AND a readable audit store with no row — is `nothing_to_back_up`.
  - Hop C, worker; no store or audit method is called here. Per entry, ONE entry in memory at a time: the entry folder's `link_state` is `False`; its recording-key state, read again, is still `absent` or `zeroed` (else `changed`); each required file's own `link_state` is `False` (a handle check alone would follow a file link), it is then opened once, and on that handle it is a regular file with link count 1 whose size, modification time, file number and device equal the snapshot's; the bytes read from that handle are the bytes hashed and written; `label.enc`'s hash equals the snapshot's. Then the open check: the entry key is unwrapped from its wrap with `K_b` into a `bytearray`, and `past_sessions.entry_opens(session_id, key, files)` — a pure function, no disk — authenticates and decrypts the label under `_label_aad(id)`, parses it, requires its own `session_id` to be the id (as `_decode_label` does) and its `has_saved` / `has_generated` to match the files present, and then accepts the transcript, the saved note and the generated note by the SAME validation the three readers apply — the transcript parsed (`TranscriptDocument.from_bytes`), the saved note's session binding and transcript digest (`_verified_note`'s checks), the generated record decoded under `generated_aad(id)` with its schema, size and session id — through bytes-level functions extracted from `read_transcript`, `read_note` and `read_generated`, which those readers then call with unchanged outcomes. So an entry a backup accepts is one `_verify_restored` accepts. The plaintext is discarded at once and the key zeroed. Any identity difference leaves the entry out as `changed`; an open-check failure as `damaged`; nothing of a left-out entry is written, and `not_restorable` is FINALISED at the end of hop C: the entries actually written whose audit row could not be read at the snapshot (`newer`, `unreadable`) or whose row ended in `rows_unknown` during the copy. Rows likewise: a path that is not a link (its own `link_state` `False`), opened once as an ordinary single-link file of the descriptor's size, authenticated under the audit key with `b"audit:" + id` and importable (D1); a failure leaves the row out, counts it and lists its id in `rows_unknown`.
  - This is the one place the plan decrypts content at backup time (decision 0.11): in the worker's memory, one entry at a time, never written anywhere. The threat model names it.
- **D6 — Writing the file: one handle from create to verified, and bytes bound by hash.** In hop C, immediately before the create, the RESOLVED destination folder is checked again through the location seam (refused, changed or uninspectable → `destination_refused`, nothing written). The name collides with nothing: it is the first of the date name, `-2`, `-3`… for which neither `<name>.csbk` nor `<name>.csbk.part` exists, and an existing file of either kind is never touched, refused over or removed (a `.part` already there may be a whole backup). `<name>.csbk.part` is made by ONE exclusive create — a create that finds the name taken moves to the next suffix — (`os.open` with `O_CREAT | O_EXCL`, read-write) and that handle is kept: `header.json` first, the payload, `manifest.enc` last, through `zipfile` in stored mode with ZIP64 off; flush and `fsync`; then the file is VERIFIED BY READING BACK THROUGH THE SAME HANDLE — the whole reader of D2 (so what is verified is what this run wrote) plus the whole file's SHA-256. The handle is closed and the file published by `os.rename` to its final name (the next free suffix if that name appeared meanwhile; the rename never replaces). The name is ALWAYS the app's own — the prefix, the date, the suffix — and only the FOLDER chosen in the save dialog is used, as Export does, so a name typed in the dialog never reaches the drive (C1); the writer returns the published name with its counts. The final path is then read once more and its SHA-256 must equal the verified one; otherwise the run fails (`publish_unverified`), nothing is recorded, and the final path is left alone. Only then does hop D run. On any failure before the rename the handle is closed FIRST and the `.part` then removed through the identity-checked `_remove_part` (Export's pattern, with the identity saved from the handle at create); the failure line ends "A partial backup file may remain on the drive." UNLESS that removal confirmed it removed this run's own file with the destination folder still listable afterwards — Export's helper counts a missing folder as gone because Export admits only fixed drives, and the writer does not take that answer for a removable drive that may have been pulled; where the identity cannot be confirmed the file is left. If hop C ends with no entry and no row written, the run is `nothing_could_be_read`: the `.part` is removed, nothing is published, and the line gives the left-out counts. Hop D, GUI thread: `config\backup.json` gets `last_backup_at = made_at` and the folder (D10); the success line; the status line refreshed. If that settings write fails the backup stands: the success line is shown with "The backup date could not be saved - the reminder will not know about this backup." added, and nothing else changes. Named residue: between the close and the rename the file is addressed by path, as every atomic write in the app is; a `.part` left by a power cut or a pulled drive may be a whole backup under another name — the documents tell the practitioner to treat such files as backups (D14).
- **D7 — The location rule, for a destination and for a source (decision 0.4).** `WindowsLayer` gains `volume_of(path) -> tuple[str, int]`: the GUID name of the volume holding `path` and that volume's drive type. One private helper `_destination(layer, folder)` does the detections in this order, for both the export rule and the new one: FIRST, from the path's text and the drive root alone — a UNC path, or a drive whose `drive_type` is remote, is refused before any call that touches the file system — and only then `realpath` and the rest. `check_archive_backup_location(layer, folder) -> ArchiveBackupLocation`: `refused(line)` for a OneDrive root the environment names, a network location, the roaming profile, either app data folder, a CD-ROM, a RAM disk, an unknown type, and anything the layer cannot resolve or inspect; `warned(line)` when the destination's volume GUID equals the data folder's ("A backup on this computer's own disk does not survive that disk - use it only until you can copy to another drive."); `ok`. Removable drives are admitted. No layer injected → refused, as Export. `check_export_location` keeps its own refusals (fixed drives only) and its outcomes are unchanged. `check_backup_source(layer, file)`, for Open a backup: the same text-first refusal; then the chosen path must be an ordinary file and not a link (`link_state` False); then its RESOLVED folder must pass the destination rule's refusals (no same-volume warning for a source); refused: "Copy the backup to a drive attached to this computer first." A refused source receives no read of its bytes. The save and open dialogs propose the last admitted folder (`config\backup.json`) only when it still passes this rule at that moment — checked, text-first, BEFORE the dialog is given it, since a drive letter can have become a network drive since the last run; otherwise the dialog starts at the system drive's root. Never Documents. Named residues: sync the code cannot see (as for Export); a virtual disk is judged as the volume it presents, not by where its backing file lives.
- **D8 — Restore only ADDS what is absent here; a session this login can no longer open is first SET ASIDE by the practitioner; a deleted entry is never brought back (decision 0.15, which replaces 0.9).**
  - The whole file is refused when the manifest's channel is not this build's ("This backup was made by the developer build / the installed app") or its format is newer. With the LOCAL audit key unreadable, Open still verifies the file and shows the summary, with Restore disabled and the line "Start a new audit record first". The same holds while the Past-sessions settings file cannot be read (the page's existing `_settings_unreadable`; today that state deletes nothing by age, and here it must add nothing by age either): Open verifies and shows the summary without the age-dependent counts, with Restore disabled and the line "Choose how long past sessions are kept first." — `retention_days` reaches `plan_restore` only from a settings file that read.
  - THE SET-ASIDE: `PastSessionStore.set_aside_refused() -> SetAsideReport`, GUI thread, behind the page's button and its one confirmation (D10) and the admission of D11. It mirrors `AuditLog.reset`, per entry. In this order: (a) THE PROBE — `session_store.dpapi_round_trip() -> bool`, reached through a new store seam `dpapi_probe`: a fresh random 32-byte value is protected and unprotected by DPAPI IN MEMORY (no file is written) and must come back equal; False, or any exception, refuses the whole action (`dpapi_unavailable`) with nothing moved, so a key blob is judged only while DPAPI demonstrably works for this login. (b) A STRICT listing of the archive; one that cannot be listed refuses with nothing moved. (c) Per id-shaped child, in this order: FIRST the child's own `link_state`, before anything beneath it is looked at (Windows resolves a junction mid-path, so `<link>\key.dpapi` would be ANOTHER folder's key) — a link, or a link state that cannot be read, counts it `left`, and nothing under it is opened or tested; THEN a `key.dpapi` CONFIRMED absent is a keyless leftover — not an entry, skipped and not counted (as in a backup, D5); THEN it must have no `pending` marker (confirmed), and `key.dpapi` must itself not be a link and be read ONCE as an ordinary single-link file — any of those failing, or a read error, counts the entry `left`; the store's blob classifier — a second new seam, `classify_key_blob(blob) -> str`, by default `session_store.unwrap_key_blob` (D9) under the archive's key description with the unwrapped key destroyed at once — then answers ONE of `ok`, `dead`, `dpapi_refused`, `dpapi_error`, `foreign_description`, `bad_length`: `ok` means this login opens the key, so the entry is not a candidate and is NOT counted (whether or not its content opens); `dead`, `dpapi_error`, `foreign_description` and `bad_length` count it `left`; ONLY `dpapi_refused` — DPAPI itself refusing the blob, after the size check and a probe that passed, by one of the two error codes D9 names and no other — goes on. That answer establishes THAT this login cannot open the blob, never WHY: a master key lost at a password reset and a damaged blob can draw the same code, and the plan claims no proof that the blob is intact. Either way the session cannot be read here, it is moved and not deleted, and a backup that holds it restores it. (The store's existing `wrap_key` / `unwrap_key` seams take a folder and fold every failure into one error, so they cannot serve here; the two new seams are constructor arguments beside them, faked in tests.) A `dpapi_refused` entry QUALIFIES only when it holds NO recording file at all — `audio-key.enc` and `audio.enc` each CONFIRMED absent; otherwise it is counted `held` and stays (D12: a kept recording stays where Delete recording reaches it; and a zeroed key, or audio left beside a missing key, is the evidence `record_deleted_recordings` still needs to record that deletion — once `record_deleted_recordings` has cleared the id and `tidy_dead_recordings` has removed the files, the session qualifies; D12 (3) names what that repair records when no audit row is left). (d) When at least one entry qualifies, ONE new folder is made beside the archive by `os.mkdir` — `past_sessions.unreadable-<YYYYMMDD-HHMMSS>-<8 hex>`, the audit set-aside's naming and its never-an-existing-name loop. A folder that cannot be made (any `OSError` from `os.mkdir`, or no free name after the loop's tries) refuses the whole action with NOTHING moved (`set_aside_unavailable`; `AuditLog.reset` treats the same two failures as `set_aside_failed` and `no_free_name`). Then each qualifying entry is moved into it by ONE `os.rename` of its folder (same volume: atomic, and it never replaces). A rename that fails leaves that entry in place, counts it `failed`, and the rest are still tried; a set-aside folder left empty is removed again, best effort (`rmdir`, only ever the empty folder made just now; one that cannot be removed stays, empty, and changes no count). (e) The store forgets its cached dates and unreadable-label marks for the moved ids. NOTHING is deleted, decrypted or rewritten; NO audit row is written or changed, so no deletion is recorded and the moved sessions are restored from a backup by the same rules as on a new computer (their rows, where the local audit record still holds them, go on reading `archived`); and no archive listing, restore, retention sweep, deletion, export or reader of clinical content ever reaches a set-aside folder again — the one thing that still visits it is the existing start-up walk that marks every folder under the data folder not-content-indexed (`mark_not_indexed`: it sets a folder attribute and opens no file). Named residues: a set-aside session that NO backup holds (completed after the last backup, or holding a kept recording when that backup was made — D12) stays set aside and unreadable, and only the old Windows password, were it ever recovered, could open it — moving a folder back is a manual act outside the app; an entry whose key file is damaged in another way (`dead`, wrong length), whose key Windows could not judge (`dpapi_error`) or whose label does not open is not set aside, so Restore skips it and it stays a row that cannot be read; the set-aside folder is outside the retention period, Delete now and the audit record, and is KEPT under D14's rule.
  - `plan_restore(reader, store, audit, sessions_root, *, retention_days, now)`, GUI thread. It takes the store's own listing ONCE (`list_entries()`, strict — an archive that exists but cannot be listed refuses the plan, `archive_unreadable`) and then decides each entry id of the manifest through ONE per-id function, `classify_entry(session_id, listing_by_id, …)`, which takes that listing as an argument and never lists the archive itself, in this order: (1) `skipped_live` — `sessions\<id>` exists; (2) the local path `past_sessions\<id>` itself, from its `link_state` and one existence check: a link state that cannot be read, or an existence check failing for any reason but not-found → `skipped_uninspectable`; a link → `skipped_linked`. (3) Something IS at that path — decided without looking at any audit row, and Restore never reads further and never writes there: the listing shows the id with a label that opens → `skipped_present`; the listing shows it with a label that does NOT open (the row the page shows as "Cannot be read on this Windows account", and so the state in which the set-aside button is visible) → `skipped_not_readable`; a path the listing does not show at all (a `pending` entry, a keyless leftover — what the next start tidies) → `skipped_leftover`. Restore does not ask why, never compares the local files with the backup's and never replaces them; the summary counts them and points to the set-aside (D10). (4) NOTHING is at that path, and the audit rows decide: `skipped_unknown_row` — the local row is `newer` or `unreadable`, or the id is in the manifest's `rows_unknown`, or the backup's own row for it is `_NEWER` or not importable; `skipped_deleted` — either row reads `deleted_early` or `expired`; `skipped_expired` — only when the retention setting is "7 years" and the label's completion date is past it (under "Until I delete them" an entry of any age restores); otherwise `add`. Per audit row: `add_row`; `skipped_present_row` (a local row that READS); `skipped_unreadable_row` (a local row file that exists but is `newer` or `unreadable` here — kept, never replaced); `skipped_pruned_row` (by the manifest's month); `skipped_undecodable_row` (the backup's row is not importable: it does not decode, or it names another id or month — the planner's name for both); `provenance_recovered` and `conflict_row` (D9).
  - `restore_backup(reader, plan, store, audit, *, now)`. FIRST a worker verifies the whole file again with the held key: its SHA-256 must equal the one Open verified; a difference is `source_changed` and nothing is written. Then on the GUI thread: audit rows first (so tombstones are present), then entries, each RECLASSIFIED immediately before it is written — by `classify_entry` again, with the SAME listing the plan took (the archive is listed once per Open, never once per entry: a listing unwraps a key and opens a label for every session) and a fresh look at that id's own path and audit rows. The recheck can only WITHDRAW a write: an id is written only when the plan AND the recheck both say `add` (a row: `add_row` or `provenance_recovered`), so nothing the summary did not show as to be added is ever added; every member is read through the reader, which checks its size and SHA-256 against the in-memory manifest at that read (`source_changed` stops the run; rows and entries already restored, each individually verified, stay).
  - An `add`: `PastSessionStore.restore_entry(session_id, key, files)` — THE STAGING RULE: `.staging` itself must be confirmed an ordinary folder or absent (`link_state` False; linked or unreadable refuses the whole restore before anything is written, `staging_unusable`), and `.staging\<id>` must be confirmed not a link (a linked or uninspectable child is that entry's `skipped_uninspectable`, never removed and never written through); a present ordinary child is removed key-first; the key wrapped for this login by the store's seam; the files written; then `_verify_restored`: the file set, each SHA-256, the label opened under `_label_aad(id)` and parsed, naming this id, with `has_saved` / `has_generated` matching, and `read_transcript`, `read_note`, `read_generated` each accepting what they will later read. Published WITHOUT `pending` through `_publish_new(staging, final)`: `final` must be CONFIRMED absent, then one `os.rename`; `final` is never removed on any path. A destination that appeared after staging is `skipped_collision` (staging removed key-first, the destination byte-identical); a verification failure is `failed_verify` (staging removed key-first). After the publish the store forgets its cached dates for the id, and a KEPT local audit row whose `past_session.state` is `none` is recorded `archived` (`record_past_session(…, create=False)`: restore never makes a row for an entry). The SAME write is made for an entry reclassified `skipped_present` whose local row still reads `none` — so a retry after an interruption completes it, and a second Restore of a finished backup changes nothing. A write that fails is counted on its own (`audit_update_failed`), whatever that session's own outcome was.
  - One table in the code maps every planner and execution outcome to exactly one count, and a test walks it. The SUMMARY's counts (the plan): `add` → To add; `skipped_present` → Already here; `skipped_not_readable` → Here but cannot be read; `skipped_live`, `skipped_leftover` → In progress or left over here; `skipped_uninspectable`, `skipped_linked` → Could not be inspected; `skipped_deleted` → Deleted since; `skipped_expired` → Older than the retention period; `skipped_unknown_row` → Cannot be restored by this version; `add_row` → audit rows to add; `provenance_recovered` → Audit provenance to recover; `skipped_present_row`, `skipped_pruned_row` → Audit rows already here or past their 7 years; `conflict_row`, `skipped_undecodable_row`, `skipped_unreadable_row` → Audit rows different or unreadable. The FINAL REPORT's counts (what happened to the items the plan set out to WRITE — `add`, `add_row`, `provenance_recovered` — each ending in exactly one of them; an item the plan already skipped is not written and is NOT counted in the report, because the summary showed it, so a second Restore of a finished backup reports "Restored 0 sessions and 0 audit rows." and no other count): entries published → sessions restored; rows written or recovered → audit rows restored; `skipped_collision` and any entry or row whose reclassification no longer writes → Left as they are; `failed_write` (an `add` whose staging write or publish failed for an ordinary reason such as a full disk: staging removed key-first, the destination never made), `failed_row_write` (an audit row whose write, or the local audit key's creation, failed), `failed_verify`, `row_mismatch` (`restore_row`'s own refusal, should a row reach it that the planner did not see), the item whose read raised `source_changed` and whatever was not attempted after it → Not restored; a row or entry whose own write fails does NOT stop the run — it is counted and the next is tried, and everything committed before it stays counted as restored; `audit_update_failed` → a sentence, counted apart from the sessions published. No object is counted twice: the table gives every planner outcome exactly one SUMMARY count and every outcome of a planned write exactly one REPORT count.
  - Alternatives rejected: overwrite-on-restore of readable entries (a local Delete now is the newer truth); a key repair in place (October's decision 0.9, dropped by decision 0.15: it changed an existing entry, and four review rounds could not make that safe); setting sessions aside inside Restore itself (one act that both moves and adds is harder to stop half-way and to explain than two); a procedure-only answer to the DPAPI break (declined 2026-10-09 — the set-aside is an app action); merging audit rows field by field.
- **D9 — The audit record: its format is unchanged; it gains an export and import surface.** `AuditLog.__init__(…, wrap_key=, unwrap_key=)` seams (defaults: today's functions). `session_store.unwrap_key_blob(blob, *, description) -> SessionCrypto` with structured refusals (`dead`, `dpapi_refused`, `dpapi_error`, `foreign_description`, `bad_length`) — `dpapi_refused` ONLY when `CryptUnprotectData` raises `pywintypes.error` whose `winerror`, compared as an unsigned 32-bit value, is `NTE_BAD_KEY_STATE` (0x8009000B, "Key not valid for use in specified state": this login's master key cannot open the blob) or `ERROR_INVALID_DATA` (13: Windows answers that the data is invalid for this login — the plan does not claim to know whether the blob or the key behind it is at fault); EVERY other exception from that call is `dpapi_error` (Windows could not do the call just now, or answered something unrecognised), which never qualifies an entry for the set-aside — the fail-safe direction if a code is ever wrong is that nothing is moved — which `unwrap_key_from_file` is rewritten over (same outcomes), plus its conftest fake; it is also the set-aside's classifier (D8).
  - `backup_snapshot() -> (key_bytes, [RowDescriptor(month, session_id, path, size)], unknown_ids)`: non-creating and strict. `_NoKey` (no key and no rows) is an EMPTY audit record: no key, no rows. A missing key beside rows, an unreadable or unavailable key, an unlistable store or month folder → `AuditUnavailable` (Back up refuses, D1). The inventory is today's (`_row_paths`): a file whose name is not a valid session id plus the row suffix is not a row and is ignored, as everywhere else in the audit store. Per row: the month a real calendar month for which `month_prune_at` computes and the size within `MAX_ROW_FILE_BYTES`; an id with MORE THAN ONE row file, a row file that is a link, or a row failing those checks, goes to `unknown_ids` and is not described. Never the ciphertext itself (the worker reads each row by path).
  - `row_state(id) -> readable | newer | unreadable | none` (an uninspectable month folder is `unreadable`, never `none`).
  - `restore_row(plaintext, session_id, month, *, now) -> RowOutcome`: `month` is the manifest's validated month. When the plaintext decodes to a row, its `session_id` and the month of its `session_date` must equal the supplied id and month (`row_mismatch`, refused); a `_NEWER` plaintext is re-encrypted UNCHANGED into the supplied month; a plaintext that is neither (`_decode` raises) is not written — `skipped_undecodable_row`, counted, and no other row or entry is held up by it. It writes only when no local row file exists for the id and `month_prune_at(month) > now` (`skipped_pruned_row`), refusing a linked month folder as `_update` does; on a computer with no audit store yet it creates one, as any first audit write does. A local row that exists is kept — `skipped_present_row` when it reads, `skipped_unreadable_row` when it is `newer` or `unreadable` here — with ONE exception: a BARE local row whose `origin` is `pre_audit`, lying in the SAME month folder, facing a backed-up `recorded` row, is replaced by the backed-up row (`provenance_recovered`). BARE means the local row holds no fact the backed-up row could erase: `past_session.state` is `none` (or `archived` with no `at` later than the backed-up row's), `deletion.state` is `pending`, the recording record is empty (no `kept_at`, no `deleted_at`, `exports == 0`), `write` untouched and no events. A `pre_audit` row holding any such fact, or lying in another month folder, is KEPT and counted `conflict_row`. A retry leaves exactly one readable row for the id. A `_NEWER` row that Restore wrote is counted restored, and reads `skipped_unreadable_row` when the same file is opened again: both are true — it is here, and this version cannot read it — and neither line gives advice (D10).
  - Residue: a restored row can show a recording as kept with no deletion date — the recording was deleted before the backup and that fact had not yet been recorded. The entry is restored without it, and the existing rule (`_past_session_recorded`) dates the recording's deletion at the session's own deletion. The threat model and the retention schedule say so. `record_past_session` is NOT changed.
- **D10 — The page: two buttons, two dialogs, one status line, and the set-aside button (decisions 0.6, 0.10, 0.15; "Keep pop-ups (Recommended)").**
  - `Back up…` and `Open a backup…` beside Export CSV. Both are always enabled, subject only to the run gate: Back up on an empty store answers "Nothing to back up yet." from its own strict snapshot, never from the page's listing, and that answer permits nothing (D14); Open a backup serves the new-computer case. A THIRD button, `Set aside sessions that cannot be opened…`, is VISIBLE only while the page's listing holds at least one session whose label cannot be read (the row "Cannot be read on this Windows account") — as the audit record's "Start a new audit record" button is visible only while its key is unreadable. It asks ONE short confirmation in the page's existing confirm pattern (no new dialog): "Set aside the sessions this Windows login can no longer open? They are moved, unread, to a folder beside Past sessions, and nothing is deleted. Open a backup then shows how many sessions it can add back; a session that is in no backup stays set aside and cannot be read. A session that still has a recording file is not moved. Press Set aside to go on." Then the admission of D11, `set_aside_refused()` (D8), the page re-listed, the page's cached sweep report lowered by the number moved (its `undated` count, never below 0 — as Delete now already lowers it by one for an unreadable entry — so the status line that counts sessions that "cannot be read on this Windows account" does not go on counting sessions that have left the archive), and the report line below.
  - The dialogs live in the NEW file `ui/backup_dialog.py`: a Qt-free `passphrase_decision(first, second, *, minimum)` and a thin `QDialog` (two `Password`-echo fields for Back up, one for Open; cleared on accept, reject and close; the fields' own signals blocked from construction (`blockSignals(True)`: `textChanged` and `textEdited` would carry the text) and the accepted values read synchronously; the text handed over as a `bytearray`), and the summary dialog (Close the default button; parented to the main window, never to a page). Neither holds selectable text, a list, an item view or a combo box. With the fake clipboard, Copy and Cut by shortcut and by context menu on a passphrase field place nothing — asserted, not assumed from the echo mode. No colour, font weight or stylesheet outside `ui/theme.py` (`set_role`, `set_variant`, `mark_card`); both dialogs are exercised in light and dark through `force_scheme`; the page's button row is pinned to fit at 150 % and at the narrowest supported width. The design system's rule "No secondary windows beyond short confirmations" gains these two dialogs by name.
  - The settings file `config\backup.json` (`note_config.BackupSettings`; the config folder's bounded reader and atomic writer): `{"schema_version": 1, "folder": <path or null>, "last_backup_at": <time or null>}`; absent or unreadable → no folder and no date.
  - The status line, from the Qt-free `backup_status_line(last_backup_at, completion_dates, now) -> str | None`: N = the listed entries completed after `last_backup_at` (every dated entry when there is no date; an entry whose date cannot be read is not counted). Shown when N > 0 and 7 days have passed since `last_backup_at` — or, with no backup ever, since the OLDEST such entry was completed: "Last backup <date> - N sessions kept since." / "No backup date recorded - N sessions kept." (the app cannot tell a missing date from no backup, so it never says there is none) It never acts. `last_backup_at` is set to a backup's `made_at` when its file is published, and advanced to a restored file's `made_at` when that is later.
  - The summary dialog's lines (`restore_summary_lines(reader_summary, plan)`, counts and dates only, and NO verdict — decision 0.14): "This backup opens: N sessions from <date range> and M audit rows, made on <date> by Clinic Scribe <version> (<channel>)." (with no session: "This backup opens: no sessions and M audit rows, made on …") / "Left out when it was made: X sessions, Y audit rows." (omitted when both are 0; X does not count `holds_recording`) / "Not in it because a kept recording or its key was present: H." (omitted when 0) / "To add: A sessions, R audit rows. Already here: K. Here but cannot be read: U. Could not be inspected: I. Deleted since: D (not restored). Older than the retention period: E (not restored). In progress or left over here: L. Cannot be restored by this version: V. Audit provenance to recover: Z. Audit rows already here or past their 7 years: P. Audit rows different or unreadable: Q." (a zero part omitted) / when U > 0, one more line: "Restore never replaces a session that is here. If this Windows login can no longer open those sessions, press Close, then Set aside sessions that cannot be opened, and open this backup again." The final report, `restore_report_line(report)`: "Restored N sessions and R audit rows. Left as they are: F. Not restored: X." (a zero part after the first sentence omitted), then "S sessions could not be marked in the audit record - open this backup and Restore again to finish." when an `archived` write failed, then "Add the clinic keys on the Clinics tab if this is a new computer." Neither the summary nor the report says whether this or any other backup may be kept or destroyed: that is D14's rule, under which a backup that has been restored from is kept. The set-aside's line, `set_aside_line(report)`: "Set aside N sessions that this Windows login can no longer open. Nothing was deleted. Open a backup to see how many sessions it can add back." (with N = 0: "No session was set aside."), then "H were not moved: a recording file is still present, or could not be ruled out." / "L others were left as they are: they could not be safely assessed." / "F could not be moved." (a zero part omitted; a session this login can open is never counted). Its refusals: the admission's line (D11); "Windows could not verify a test value just now - nothing was moved. Try again later." (`dpapi_unavailable`: the probe can fail at either half of its round trip); "The set-aside folder could not be made - nothing was moved." (`set_aside_unavailable`); the page's existing list-unreadable line when the archive cannot be listed.
  - Wording that changes because a backup exists (decisions 0.5, 0.12; exact-text tests and the design system's quotes move in the same task): Delete now's confirmation ends "…Its notes and transcript are deleted from Past sessions. An earlier backup may still hold them - the downtime procedure says when older backups may be destroyed. Press Confirm delete to delete it." (the rule itself is stated once, in the documents, D14); the shorter-retention confirmation: "Keep past sessions for only <period>? Kept sessions older than that are deleted now from Past sessions; one whose completion date cannot be read, or whose deletion fails, is kept and counted. An earlier backup may still hold them."; the delete-done line (`DELETE_DONE`, which today says the key was destroyed — a backup may still hold it): "Session deleted from Past sessions."; the retention warning's "makes no backup of its own" sentence amended to D14's wording.
  - Alternatives rejected: a third "Check a backup…" action (folded into Open, 2026-10-09); a home on the Status tab; automatic backups (Deferred).
- **D11 — The run gate: during a backup or a restore nothing else can write the archive or the audit record.** One owner, in `MainWindow`:
  - Admission, `archive_run_refusal() -> str | None`: the Recovery page is refreshed first; then a refusal line, checked in this order: when a Cliniko draft write is in flight (`is_writing` — FIRST, because its reservation is also one of `_live_session_ids()`; the existing line `models.write_line("write_in_flight")`), when `_live_session_ids()` is non-empty ("Finish or discard the current recording first."), when `recovery_screen.protected_session_ids()` is non-empty or either Recovery list has a row ("Review or discard the recordings on the Recovery page first."), when a voice enrolment is running — `controller.enrolling` or the Practitioner screen busy ("Voice enrolment is running - wait for it to finish, or Stop it, first."), or when any screen or the Chrome link is busy — the generic list `closeEvent` uses, plus the Past sessions page itself ("Wait for the current work to finish."). The rule: every state for which `closeEvent` refuses a close because work is in progress refuses a run too, so the gate never disables a control that work needs (enrolment's Stop). The set-aside (D8) uses this same admission and nothing more: it is one GUI-thread call that runs to its end without yielding to the event loop, so no other writer of the app can run beside it and it takes no gate.
  - `begin_archive_run(run) -> str | None` is called AFTER the flow's last dialog before its first worker, on the GUI thread: it evaluates the admission and takes the gate in one call with no event-loop yield between the two. Taking the gate disables the navigation rail, the Settings strip and every page (one call), so no control of the app can be pressed during a worker hop; the summary dialog, a child of the window itself, stays usable. The gate is held to the end of the run — for Open a backup, through the summary dialog — and released only by `ArchiveRun.close()`, which re-enables the window, refreshes the Recovery page and calls `chrome_bridge.publish()`.
  - While the gate is held: `PeriodicSweep.__call__` returns before ANY of its three steps without advancing their clocks (the gate is injected into it as a callable); `ChromeBridge` refuses every command that starts, adopts, discards or opens a review of a recording with the reason `backup_running` (`models.START_BACKUP_RUNNING_MESSAGE`: "A backup or restore is running - wait for it to finish.") — never `getting_ready` — and the gate's state is one more field of `_situation` for every action, so the refusal disappears when the run ends without another command (the existing `_refuse` already clears an armed development tick for this reason); `closeEvent` gains a branch BEFORE `note_screen.prepare_close()`: "A backup or restore is running - wait for it to finish before closing."
  - The hotkey and the spoken commands act only on a live recording, and admission guarantees none is live; the sleep and lock handlers likewise. Cliniko note checks (reads only) may continue.
  - A normal close never destroys a worker; a force-kill leaves at worst a `.part` (D6) or a `.staging` folder that `clean_staging` removes.
  - Alternatives rejected: checking a flag at each writer's entry point (the October design and its corrections: every new writer was another place to forget); a modal progress window (a third dialog).
- **D12 — A session that holds a kept recording is never in a backup (decision 0.13, 2026-11-25: "Leave those sessions out (Recommended)").** The development-recording consent tells the patient the recording "can be opened only from your practitioner's own Windows login on that computer" and that "the program makes no backup of it". An entry's key also wraps that entry's recording key, so a backup holding the entry key would make the first sentence untrue. So an entry is backed up only when its recording key is CONFIRMED `absent` or `zeroed` — `_audio_key_state(entry / "audio-key.enc")`, the existing module function over one path, read in hop B and again in hop C (D5); a `live` key leaves the entry out as `holds_recording`, counted apart; a key whose state is `unknown` leaves it out as `uninspectable`. Consequences, each relied on elsewhere: (1) no backup ever holds a key that can open a recording the app currently holds (a former recording key that a disk snapshot or journal may retain after Delete recording is the threat model's existing forensic residue, which Task 4.1 restates for a backed-up entry key) — a recording exists from an entry's creation or never (a retried Complete publishes a new generation under a fresh key), so an entry that was backed up cannot gain one; (2) Delete now, expiry and Delete recording treat a recording exactly as today, and no rollback step concerns recordings (D13); (3) the set-aside never moves a session that holds any recording file, or one whose absence cannot be confirmed (D8), so Delete recording keeps reaching every recording the app holds, a pending record of a deletion is left to the existing start-up and sweep repair exactly as today, and Restore never touches a present entry at all — named residue (peer round 17): for a session whose label cannot be read that repair writes only on an EXISTING row (`unattended_write`, `create=False`), so after Start a new audit record it finds no row, records nothing and clears the files, and a row that Restore brings back later for that session shows the recording as kept with no deletion date (the residue Task 4.1 names as a restored row's `kept_at` without a recording); (4) such sessions are in NO backup, old or new, so they are never a reason to keep an older backup, and the app says how many there are (Flow 1, D10); (5) while a recording is kept, that session's transcript and notes have no backup, as today — the documents say so, and Delete recording makes the session eligible for the next backup. Deletion does not change at all: `delete_entry`, `delete_recording`, `_remove_key_first` and the retention sweep are untouched by this plan. Named residue (peer round 15): an entry whose recording key is live while its `audio.enc` is missing — the app zeroes the key before it unlinks the audio, so this needs interference from outside the app — reads as holding no recording, Delete recording refuses it, and it stays out of every backup and every set-aside; so the lines that count such sessions speak of "a kept recording or its key" (D10), and the downtime procedure's Past sessions problems names the case. This decision REPLACES the same day's earlier answer "Add it to the plan (Recommended)" (zeroing a held recording key before the entry key at deletion), which nothing needs any more. Alternatives rejected by the practitioner: backing such sessions up and deleting the recording at a repair; a new consent version.
- **D13 — Version 0.5.0, a build of record, installed by the practitioner ("0.5.0 (Recommended)").** A new file format and a new kind of copy make it a minor; 0.4.1 stays reserved for the UI refresh's Phase 6. The version is set in the five version files (six values: `__init__.py`, `pyproject.toml`, `package.json`, `package-lock.json` twice, `manifest.ts`) and the CHANGELOG. The rollback rule "below 0.5.0" is short because nothing at rest changes shape and a recording is deleted as before (D12): an older build ignores `config\backup.json`, has no reader for a backup file, reads an added entry as any entry, never looks at a set-aside folder (it lies beside the archive, as the audit record's does), and reads every audit row as before; no step is needed before the older installer runs, and no existing rollback section is amended. The section says one thing more: an older build's deletion messages ("cannot be recovered", "its key was destroyed") describe Past sessions on this computer only — a backup made on 0.5.0 may still hold the session, and the downtime procedure's steps still govern those backups. The older rollback sections' substantiated limits still apply cumulatively (0.3.7 is not one: 0.3.6 reads every 0.3.7 entry). The new section goes above "Rolling back below 0.4.2".
- **D14 — Documents describe what the code does; the patient sheet's next version is `patient-info-v4`, a DRAFT until approved.**
  - Every sentence in the inventory (Key Findings; the grep of Task 0.8 is the authority) is amended to: the practitioner can make an encrypted, passphrase-protected backup onto a drive attached to this computer and restore it on a new computer or login; the backup is never sent anywhere; a kept development recording is NOT in it, and neither is any session that still holds one (its transcript and notes are backed up once the recording has been deleted).
  - The practice documents record each changed line as dated, "awaiting the practitioner's approval", then "approved by the practitioner on <date>" (the 0.4.2 lines are the precedent). `patient-info-v4` is written as a clearly marked DRAFT beside the approved v3 text: v3's version line, the consent example, the form to sign and every sentence naming the current sheet stay v3 until P.3, whose approval is ONE commit that makes v4 current in all of those places together. The development-recording consent document is NOT edited at all — the practice README makes any change to it a new version of it, and the app ships its wording verbatim under `development-consent-v1`. Its opening paragraph names `patient-info-v3`; a dated sentence in the practice README, added in P.3's commit, says that this means the patient sheet current at the time. And the note that a backup never holds a recording goes in the practice README and the practitioner-facing notes, outside the consent text.
  - The operating rules, in plain English (decisions 0.5, 0.14), each stated ONCE: keep the drive locked away and apart from the passphrase; a lost passphrase is a lost backup; keep the newest two backups; write down the counts each backup's line gives. ONE rule says when an OLDER backup may be destroyed, and the practitioner applies it — the app reports facts and gives no verdict: an older backup is destroyed only when the NEWEST backup's line said "Nothing eligible was left out", AND nothing on this computer has been lost, become unreadable, been set aside, been restored or been started anew since that older backup was made. When any of those has happened: restore first (Flow 4), KEEP every backup made before it happened — such a backup may hold something no later backup can — and apply the rule again only to backups made afterwards. What the practitioner checks before destroying anything: the Past sessions page lists no session that cannot be read and shows no line saying the audit record cannot be read; and the newest backup does not hold fewer sessions or audit rows than the one before it, beyond what was deleted or has expired in between. When in doubt, keep. After a Delete now the same rule applies: once it lets the older backups go, no remaining backup holds that session. NOTHING ELSE is a reason to destroy a backup — not "Nothing to back up yet", not an empty Past sessions page, not a restore's summary or report, not an Open that failed. A file on the drive whose name ends `.csbk.part` is a backup that did not finish being checked, and may be a whole one: it is KEPT as a backup of unknown content and is never destroyed because it would not open — a mistyped passphrase and a damaged file give the same refusal (D2), so a failed Open proves nothing; to try it, a COPY is renamed to end `.csbk` and opened; it goes only when the one rule lets older backups go. The set-aside folder (D8) is KEPT: it holds clinical records that cannot be read, and for a session no backup holds it is the only copy. It comes under the downtime procedure's existing rule for a session that "Cannot be read on this Windows account" — not destroyed until the reviewer question there is answered (whether a kept transcript that can no longer be read must still be kept for the 7-year minimum) — and the README names the set-aside folder in that question. It is NOT the audit record's set-aside rule: that folder holds no clinical content. THE RULE'S LIMITS, named for the independent review (the threat model lists them; the downtime procedure says them in plain words): (i) the app cannot see what this computer has lost — a Past sessions folder or an audit record that is gone, or started anew, makes the next backup smaller and still clean — so the rule rests on the practitioner noticing, by the counts and the page; (ii) apart from the one provenance-recovery case of D9 (a bare `pre_audit` row replaced by a backed-up `recorded` one), Restore does not reconcile the facts of two audit rows that both read — the present row is kept as it is — so an older backup can hold a fact a present row lacks (an export count, a later date), which is why backups made before a restore are kept; (iii) a backup kept under this rule goes on holding sessions deleted since; (iv) a session completed since the last backup, and one that still holds a kept recording, is in no backup.
  - The downtime procedure's "Losing the computer" becomes the two restore sequences of Flow 4 — each saying: restore from ONE backup, the NEWEST, and afterwards delete again any session that was deleted after that backup was made. An OLDER backup is restored on top only to recover something the newest lacks, never as routine: the app cannot know every deletion (an audit row may not have been copied or imported, and an audit reset may lie between the two backups), so an older backup can bring back sessions deleted since — after using one, the practitioner checks the restored sessions against their own records and deletes again what should not be there — and "Past sessions problems" points to the set-aside, says what it cannot bring back, and names the stuck recording key of D12.
  - The README gains three reviewer questions and extends a fourth: whether a backup copy needs fresh consent or changes the state-law custody analysis; whether a transcript deleted as recorded in error must also be destroyed in older backups (APP 11.2) — including in a backup kept because it was made before a restore or an audit reset; whether the one rule for destroying older backups, with its four named limits, is an adequate procedure; and — joined to the existing question about a kept transcript that can no longer be read — whether a set-aside folder may ever be destroyed.
  - What a lost drive shows WITHOUT the passphrase, stated exactly in the threat model, the retention schedule and (in plain words) the downtime procedure: that the file is a Clinic Scribe backup, when and by which version and channel it was made, the planned counts, each archive entry's session id, each audit row's session id and its stored audit month (including sessions that have only an audit row), each member's kind and size, and — to someone holding two backups — which members changed between them. Everything else needs the passphrase.
  - The threat model gains a section "Past-sessions backup and restore"; the data-flow map a flow 30; the retention schedule rows for the backup file (outside custody once written; the practitioner's to keep and destroy), `config\backup.json` and the set-aside sessions folder (never pruned, opened or deleted by the app; kept by the practitioner under the unreadable-session rule above — unlike the audit record's set-aside folder it holds clinical content); `intended-use.md`, the design system and `PLAN.md` their amended sentences. `docs/practice/` keeps plain English (C10).
- **D15 — Tests and the developer smoke use synthetic content only; the agent never opens a real backup.** Tests use pinned roots, the archive's fake key-wrap seams and the audit's new ones, a fake `WindowsLayer`, the reader's size-and-read seam, and a fast KDF admitted ONLY under a test-marked floor override (`_kdf_floor_for_tests`), never by a header field. The practitioner's P.2 smoke runs on the developer build with its data folder set aside. P.5 is the first real backup, on the installed app, never opened by the agent (C1).

## Schema / Data Changes

| Store | Today | After this plan | An older build reads it as |
|---|---|---|---|
| audit row (`audit.AuditRow`) | v3 | UNCHANGED (v3) | — |
| `config\backup.json` (NEW) | — | `{"schema_version": 1, "folder": <path or null>, "last_backup_at": <time or null>}`, ≤ 4 KiB, the config folder's atomic write | ignored |
| `past_sessions\<id>\` (an ADDED entry) | — | identical to an archived entry: `key.dpapi` (this login), `label.enc`, `transcript.enc`, [`note.enc`], [`generated.enc`]; no `pending`; never `audio.enc` / `audio-key.enc` | an ordinary entry |
| `past_sessions.unreadable-<YYYYMMDD-HHMMSS>-<8 hex>\<id>\` (NEW; a SET-ASIDE session, beside the archive) | `past_sessions\<id>\` | the same folder moved by one rename, every file byte-identical; never opened, restored from, swept or deleted by the app (the start-up not-indexed walk visits its folders, as it does every folder's) | ignored (an older build never looks beside the archive) |
| `<folder>\ClinikoScribe-backup-YYYY-MM-DD[-n].csbk` (NEW, outside custody) | — | D2's container v1 | nothing (no reader) |
| `label.enc`, `encounter.enc`, every other `config\*.json`, the extension, the protocol | — | UNCHANGED | — |

Backfill: none. With no `last_backup_at` the status line counts every dated entry and appears once the oldest is 7 days old.

## Config / Environment / Deployment Impact
- No new dependency; `desktop/pyproject.toml`'s `cryptography` floor rises to 44 (the frozen build's pin, 49.0.0, is unchanged). No network, no environment variable, no registry value, no installer change. One new settings file, `config\backup.json`.
- The frozen self-check gains a KDF step with exit code 3 (Task 1.7); `scripts/build-release.py`'s failure text explains it.
- Version 0.5.0 (D13). The installed app receives it through the release path; the developer build through `pip install -e` as usual.
- `config\backup.json` is one of the `config\*.json` files the shipping gate fingerprints, which is one reason the install waits for the tenth consultation (C13).

## Critical Constraints

- **C1 — The agent never reads a real kept transcript, note, name or recording, and never opens a real backup file.** Every test and smoke the agent runs uses synthetic content on the developer build; Phase P's real backup is made, opened and kept by the practitioner alone. A backup's lines carry counts, dates and a file name (a date) — never an id list, a name or text.
- **C2 — Nothing leaves this computer or its attached drives.** The location rule REFUSES (never asks) a destination or source the code positively identifies as cloud-synced, remote, roaming or an app data folder, and refuses a recognisable network location before touching it; no network code is imported; `assert_offline_env` unchanged.
- **C3 — The passphrase is never stored, logged or echoed; the derived key never touches disk or a signal.** No settings file, audit field, log line, signal or exception message carries either, or anything derived from them except the per-file salt inside the backup. The run object owns and zeroes the mutable buffers on every exit (D4). A failure reports a closed code; anything unforeseen its type name only.
- **C4 — A backup is read-only on the archive and the audit store.** No entry file or row is rewritten and no key file touched; the only things a backup writes are its own file and `config\backup.json`, the latter only after the published file is verified.
- **C5 — Restore never overwrites a readable entry, never deletes a file of an entry, never brings back a deleted one.** Restore makes NO change to an existing entry or to anything else at an entry's path; the set-aside (D8) moves a whole entry folder unread, changes no byte of it and records no deletion. Every added entry is fully verified in staging before it is published, and publishing never removes a destination. A local audit row is never replaced except a bare `pre_audit` row in the same month by a `recorded` one (D9). Named residues: the guarantee holds only where tombstone evidence survives — a session deleted AFTER the newest surviving backup was made comes back when that backup is restored on a new computer or login (no surviving record says it was deleted), and restoring an OLDER backup before a newer one can bring back a session the newer one records as deleted (a local row, once present, is kept); an audit row the newest backup could not copy may have been a deletion's only record, so an older backup restored on top of it can bring that session back; so the downtime procedure says to restore the NEWEST backup first and then to delete again whatever was deleted after it was made (D14); an entry whose Delete now left no tombstone (a failed audit write) comes back and is deleted again; an entry older than the audit's 7 years restores under "Until I delete them" with no tombstone evidence possible.
- **C6 — The per-entry compartment survives.** Each entry's key is wrapped individually; no archive-wide content key exists before, inside or after a backup; a restored entry has a fresh DPAPI wrap and opens nothing else.
- **C7 — Content-free records.** `config\backup.json` holds a folder path and a time; the page's lines are counts and dates; the log names session ids and codes only. The audit row gains no field.
- **C8 — The container fails closed.** Every check of D2's reader refuses by name before anything is written; `MemoryError` is caught by type; the KDF floor is loosened only by the test seam, never by the file.
- **C9 — Tests never read the host's own data, drives or DPAPI** — pinned roots, fake seams, a fake `WindowsLayer` (the conftest sentinel makes the real one raise), the fast-KDF test floor; no test writes outside its temporary folder. The one existing exception stands: `test_audit.py` and `test_schema_versions.py` already exercise real DPAPI under `tmp_path` (`@windows_only`), which the new audit tests may share; `test_past_sessions.py`'s existing `TestRealEntryKeys` does the same, and the set-aside's one real-DPAPI test joins it. Every new test runs under the conftest's autouse fixtures (theme, channel, models root, the layer and exception-hook sentinels) and through `scripts/lint-held-out-set.py` in CI.
- **C10 — Plain English in `docs/practice/`** (its README): no file names or code identifiers; the review banner stays; a changed patient sheet is a new version; nothing is claimed that the app cannot back — it cannot know where a drive is kept or whether a backup was later destroyed.
- **C11 — Shared documents are edited against the then-current `main`.** Phase 4's edits to `docs/practice/`, the threat model, the retention schedule, `AGENTS.md` and `CHANGELOG.md` are made with the clinic 1 smoke's, the stronger-voice run's and Task 9.1's own edits re-read, never from this plan's snapshot.
- **C12 — No run overlaps another writer.** D11's gate is the whole rule: admission, the disabled window, the bridge's refusal, the skipped sweep, the refused close. The set-aside runs under the same admission as one GUI-thread call that never yields. Every archive or audit read that classifies and every write runs on the GUI thread; workers derive, read and write files and verify, holding ciphertext, wrapped keys, `K_b` and — one at a time, for the open check — an entry key and its plaintext in memory.
- **C13 — No install during the ten ("After the tenth (Recommended)").** The ten Task 9.1 consultations all run on installed 0.4.2, with `patient-info-v3` the sheet in use and the config fingerprints taken before the first and after the tenth. So: the build runs in its own worktree (`/execute-loop` with `isolation=worktree`; the stronger-voice run builds on `main`); the MERGE to `main` waits until the tenth consultation is scored, its after-fingerprints taken and Task 9.1's one commit landed; the build of record (H5) is made from `main` after that merge; P.1 installs it.
- **C14 — A restored shadow entry is still a shadow entry.** `label.enc` is copied byte for byte and read only through the existing readers, so the shadow mark survives and "Copy saved note" refuses a restored shadow entry exactly as before. A backup file is a new place where a shadow recording's note exists, as ciphertext under the passphrase; the threat model's "The pilot" names it. `test_shadow_exits.py` is unedited: the writer copies ciphertext by file name and calls no placement, clipboard or reader of note text.
- **C15 — No real backup before the documents and the existing-records decision ("Before the first real backup (Recommended)").** Every transcript kept so far was recorded under `patient-info-v3`, which says the program makes no backup. P.5 may run only when P.3 records every line approved and P.4 records option (a). This gate is the practitioner's procedure: the installed app shows the Back up button from P.1.

## Validation / Verification

- Suites (executor shapes; pytest composer-run): `cd desktop && ruff check . && mypy && pytest`; `cd extension && npm run qa` (the extension changes only its version). Baselines recorded at Phase 1's start from the run's own worktree (Task 0.8).
- Dry-run baselines for Task 0.8 (read-only): the document grep `no backup|makes no backup|NO backup|there is no backup|with no backup|Windows login|cannot be recovered|cannot be undone|for good|lost with it|nowhere else|cannot be read again|nothing it keeps has a backup` over `docs`, `PLAN.md` and `desktop/src` (the D14 inventory); `grep -n "DRIVE_" desktop/src/scribe_desktop/exclusions.py` (two constants today); `grep -rn "check_backup_exclusions\|backup_exclusions" desktop/src` (the name D7 avoids); `grep -n "_NON_PATH_LITERALS" -A25 desktop/tests/test_install_layout.py`; `grep -n "cryptography" desktop/pyproject.toml`; the two suites' counts.
- New or extended tests, each failing on the pre-change code where a guard is claimed:
  - `test_backup_container.py` — a round trip; every refusal of D2's reader by code, the preflight's through the size-and-read seam with `ZipFile` never called (file size, the end record, ZIP64, a comment, the member count, the directory size, a directory whose record count differs from the declared count, an over-long or non-ASCII name, a member name that occurs twice, an extra field, a ZIP64 extra field present only in a member's local header, a local header whose name or sizes differ from the directory's, a compressed member, a header not first or over its bound); `format_version`, an unknown KDF, each KDF parameter outside its envelope before the derivation seam is called; a `manifest.enc` record missing, doubled or over 16 MiB, refused in the preflight; the channel; a member set differing from the manifest's by one in either direction; a mis-sized member; a pattern-breaking id; a month 13; a byte flipped in the header, the manifest, a wrapped key, a row and each entry file; a wrong passphrase and a damaged manifest giving the same code; `MemoryError` by type; manifest counts above the header's bounds; an entry whose label says `has_saved` with no note member, and the reverse; an entry whose authentic label names another id refused by the open check; an audit-only file (no entries) and an entries-with-empty-audit file both round-trip.
  - `test_backup_write.py` — D1's inclusion and exclusion set by name (`key.dpapi`, `pending` entries, `.staging`, `audio.enc`, `audio-key.enc` and the export ledger never copied); an entry with a live recording key left out as `holds_recording` — the success line still saying nothing was left out, with its extra sentence —, one with a zeroed key backed up without its audio files, one whose recording key cannot be inspected `uninspectable`, and one whose key state differs at hop C `changed`; each left-out reason (`unreadable` — including an authentic label that names another id, which hop B's label decode rejects —, `incomplete` both ways, `damaged` — ciphertext corrupted before the snapshot, and an authentic saved note beside another revision's transcript —, `changed` — a same-size replacement between hops B and C —, `uninspectable` — a linked folder, a hard-linked file, a file that is a symlink to an ordinary file, an unreadable link state); a keyless leftover folder holding a locked file skipped silently, the backup still saying nothing was left out; an unlistable archive refuses; `AuditUnavailable` of each code refuses with nothing written; a row with two files, a month 13, a row that does not authenticate, one that authenticates but does not decode and one naming another id or month are each left out and listed unknown, and an audit-only archive holding only such a row is `nothing_could_be_read`; `_NEWER` rows copied; `not_restorable` counted, including for an entry whose row read at the snapshot and failed during the copy; `too_large` before any file exists; `nothing_to_back_up` against `nothing_could_be_read`; a live recording key beside a missing transcript left out as `holds_recording`, not `incomplete`; the archive and the audit store byte-identical before and after (directory hashes); no store or audit method on the worker (a thread-recording fake); the destination re-check refusing between admission and create; a pre-existing `.part` and a pre-existing `.csbk` of the same name each survive byte-identical while the run takes the next suffix; the file verified through the writing handle; a final file whose bytes differ after the rename → `publish_unverified`, nothing recorded; `.part` absent after a failure and left alone when its identity cannot be confirmed; the "may remain" sentence shown when the folder is gone after a failure and not shown after a confirmed removal; the `-2` suffix, reported back as the published name; a file name typed in the dialog ignored.
  - `test_restore.py` — every classification of D8 in its order, from both tombstone sources; `rows_unknown` → `skipped_unknown_row` on an empty destination; `skipped_present` for a listed entry whose label opens, whatever the audit rows say; `skipped_not_readable` for a listed entry whose key is refused and one whose label does not open, and `skipped_leftover` for a `pending` entry and a keyless leftover — every file of each byte-identical after a Restore, with nothing written under `.staging` for it; an id moved by the set-aside restoring as `add` from a backup that holds it, and reading `skipped_deleted` when a deletion row for it survives; a local row file that does not decrypt → `skipped_unreadable_row`, kept; `skipped_uninspectable` when the entry path's link state or existence cannot be read; an unlistable archive refusing the plan; an `add` verified through the readers and published without `pending`; a destination introduced after staging keeps its key and every byte (`skipped_collision`); a backup pairing an id with another entry's key refused at Open with no staging folder made; `failed_verify` (staging gone) reached by a staged write or a key read-back made to differ after a valid Open, and `failed_write` by a write made to fail; a junction where the entry folder would be → `skipped_linked` with its target byte-identical; a `.staging` that is a junction refusing the whole restore (`staging_unusable`) and a `.staging\<id>` that is one skipping that entry, each with its target's key byte-identical; an entry older than 7 years restoring under "Until I delete them" and `skipped_expired` under "7 years"; the whole file refused for another channel and a newer format; the summary computed with Restore disabled while the local audit key is unreadable, and while the retention setting cannot be read; the second whole-file verification refusing a file changed after Open before any write, and a member changed mid-restore stopping the run with earlier entries intact and the report's totals exact (the first restored, the one that raised and the rest Not restored); rows re-encrypted under the local key into the manifest's month, `_NEWER` plaintext unchanged, an authenticated row that does not decode skipped and counted with every other row and entry still restored, `row_mismatch`, a pruned month, a linked month folder, `provenance_recovered` only for a bare same-month `pre_audit` row, `conflict_row` for one holding facts or lying in another month, a retry leaving one readable row; a kept local row's `none` becoming `archived` only after the publish, an interruption between the two completed by a retry (the entry `skipped_present`, the row then `archived`), and a failed write counted; the outcome table walked; a restored shadow entry reading `label.shadow` true and refusing "Copy saved note", and a v1 label still reading as normal (C14); a restored entry without audio reading `recording_state == none` and left alone by `tidy_dead_recordings`; `list_entries` called exactly once per Open however many entries are restored, and an id the plan skipped never written even where its recheck would say `add`; a second Restore of a finished backup returning a report with every count zero; after an audit reset, the deletion repair run with no row (nothing recorded, the files cleared) and the older row then imported reading `kept_at` set and `deleted_at` empty — asserted as D12's named residue; no store, audit or controller method on a worker during Open or Restore.
  - `test_past_sessions.py` (extended) — the set-aside: an entry whose key blob DPAPI refuses is moved, every file byte-identical under the new folder, and is no longer listed; nothing moved and `dpapi_unavailable` when the probe round trip fails; an unlistable archive refusing with nothing moved; left exactly as they are and counted `left` — a linked entry folder (including a junction whose target holds NO `key.dpapi`, with nothing under it opened) and one whose link state cannot be read, a `pending` entry, a key file that is a link, a key read raising `OSError`, a `dead`, a `dpapi_error` (after a probe that passed), a foreign-description and a wrong-length blob; left and NOT counted — a keyless leftover, an entry whose key unwraps but whose label does not open, and a readable entry; a refused-key entry with a live recording key, one with a zeroed key, one with `audio.enc` beside a missing key and one whose recording files cannot be inspected each not moved and counted `held`, and the zeroed-key one moved once `record_deleted_recordings` has recorded the deletion on its existing row and `tidy_dead_recordings` has removed the files; a rename made to fail counted `failed` with that entry intact and the others moved; the set-aside folder a new name on every call, never an existing one, and not left behind when nothing qualifies or every rename fails (where its `rmdir` succeeds; with `rmdir` made to fail the empty folder stays and the report is unchanged); `os.mkdir` made to fail, and no free name, each refusing `set_aside_unavailable` with nothing moved; no audit method called and no row changed (a recording fake); the store's cached dates and unreadable marks forgotten for the moved ids; `delete_entry`, `delete_recording`, `_remove_key_first` and the retention sweep untouched (their tests unedited); every classifier answer asserted with INJECTED errors (a fake `CryptUnprotectData` raising each of the two qualifying codes, as a signed and as an unsigned `winerror`, and other codes and exception types), never from what a damaged real blob happens to draw; one `@windows_only` test with real DPAPI under `tmp_path` — a real blob unwraps (`ok`) and the probe round-trips, and one with a flipped byte answers one of the closed set of results and raises nothing (the test does not assume which).
  - `test_audit.py` (extended) — the two key seams; `unwrap_key_blob`'s five refusals — `dpapi_refused` for each of the two named error codes and `dpapi_error` for any other — and `unwrap_key_from_file` unchanged in outcome (one `KeyCustodyError` for all five); `backup_snapshot` for a fresh store, a missing key beside rows, an unreadable key, an unlistable month, duplicate row files and a month 13, creating nothing in every case; `row_state` including an uninspectable month; `restore_row` (above); `record_past_session` unchanged.
  - `test_archive_backup_location.py` — each refusal; a UNC path and a mapped remote drive refused with NO file-system call on the path (a layer fake that fails on `realpath`, `lstat` and `volume_of`); the same-volume warning by GUID through a drive letter and a mounted folder of one volume; removable admitted; CD-ROM, RAM disk, unknown and uninspectable refused; no layer → refused; `check_export_location`'s outcomes unchanged; a remembered folder whose drive has become remote, or is absent or uninspectable, never handed to a dialog; `check_backup_source` refusing a link, a file whose resolved folder is refused, and reading no byte of a refused file.
  - `test_archive_run.py` — admission's refusals — a live recording; the Recovery page, including a recovered transcript awaiting Complete or Discard and a Recovery row made visible only by the admission's own refresh; a voice enrolment alone, its Stop still enabled; a reserved draft write giving the write line, not the recording line; the generic busy list and the page itself (the admission function alone: that each of those states stops a set-aside from moving anything is asserted with the button, in Task 3.4's UI tests); the gate taken with no yield after the last dialog; rail, strip and pages disabled while held and enabled after every exit (a cancelled dialog, a refused location, each hop's failure, a worker ending with no result signal, Close, success); both buffers zeroed on each of those exits; `PeriodicSweep.__call__` running none of its steps and advancing no clock while held, and resuming after; the bridge refusing start, adopt, discard and open-review with `backup_running` and never `getting_ready`, an armed development tick cleared and announced by a refused Start, and each refusal gone after the run ends with no further command; `closeEvent` ignored with the run line while held, without `prepare_close` having run, and accepted after.
  - UI tests for the two actions and dialogs (fakes only — no real clipboard, dialog, layer or thread): both buttons enabled on a fresh store, Back up there answering "Nothing to back up yet." from the snapshot; the success line's two forms, naming the published file with its suffix; `config\backup.json` written only after the writer reported a verified published file; "Nothing to back up yet."; the summary's lines for each count, Close writing nothing and being the default; an audit-only backup's summary and final report (no session, every row restored); the final report after a failed `archived` write following an add and an already-present entry (counted apart from the sessions published), a second Restore of a finished backup changing no audit row, after a destination write failing once one entry was already published, after an audit row's write failing once an earlier row was committed (the earlier counted, the rest still tried), after the date could not be saved (the page still re-listed and the report shown), the summary for an old entry on a fresh computer set to "7 years"; no verdict and no keep-or-destroy sentence in any summary, any report or either form of the backup success line (their strings pinned exactly); an audit-only backup holding a newer-schema row restored on a fresh login and opened again — counted restored, then counted under rows different or unreadable; the summary's set-aside hint shown only when a session is here but cannot be read; the set-aside button visible only while the listing holds a session that cannot be read, its confirmation text, each form of its report line and each refusal (`set_aside_unavailable` included), each admission refusal of D11 leaving every entry where it was, the page re-listed before the line shows, and under "7 years" the page's count of sessions that cannot be read on this Windows account lowered by the number moved (the line gone when it reaches 0); the final report of an all-skipped second Restore reading exactly "Restored 0 sessions and 0 audit rows."; a developer-channel file refused on an installed-channel build; the passphrase decision function; the widget text empty after each exit; Copy and Cut on each passphrase field placing nothing on the fake clipboard; neither text signal of a passphrase field delivering a value to a connected slot; no selectable-text flag, list or combo box in either dialog; light and dark renders under `force_scheme` in a `try/finally`; the button row at 150 % and at the narrowest supported width; the page re-listed after a restore before its line shows; `backup_status_line` on the first day, at the 7-day boundary, with and without a last-backup date, with an undated entry, and after a restore advanced the date; the `config\backup.json` round trip and its unreadable case; a settings write that fails after a published backup showing the success line with its added sentence; the exact text of the changed strings of D10.
  - `test_app.py`-style: the self-check's KDF step returning exit code 3 when Argon2id is unavailable (the derivation seam made to raise) and 0 otherwise; `scripts/build-release.py`'s failure text naming code 3.
  - Pins: `test_install_layout.py`'s `_NON_PATH_LITERALS` gains `BACKUP_FILENAME_PREFIX` by owner in the SAME task that defines it; `git diff` of `test_shadow_exits.py`, `test_schema_versions.py` and the audit row's schema pins empty; `test_pilot_docs.py` passes if a pilot document changes.
- Manual checks (practitioner, Phase P): P.1 the install; P.2 the developer-build round trip on an isolated data folder (the set-aside itself has no manual check — a real refusal needs a Windows password reset — and rests on its tests, the real-DPAPI one included); P.3 the documents read and approved; P.4 the existing-records decision; P.5 the first real backup, opened with Close; P.6 the rollback rule read before any older install.
- Success: suites green; `/review-loop`, `/simplify`, `/security-review` and the codex peer pass converged at each phase boundary; 0.5.0 a build of record; P.1–P.5 PASS; `patient-info-v4` approved and in the independent review's queue.

## Deferred / Out of Scope
See `Planning Extraction Summary` (state-once). In one line each: kept recordings in the backup, scheduled backups, a settings export and backup dates in the audit record are deferred; network and cloud destinations, incremental backups, cross-channel restore, single-entry restore, passphrase recovery, a run ledger, an entries-only backup, a key repair in place and any verdict about a backup are excluded; backup size, the 256 MiB cost, passphrase custody, "no recording pending" and the same-user and removable-drive assumptions are accepted with named checks.

## Current State / Handoff Note
- 2026-10-09: drafted from the code at `aeec75e`; decisions 0.1–0.6 and 0.9 taken; hardened by `/review-plan` and five codex plan rounds (35 findings applied). Never built.
- 2026-11-25: reconciled against `5d63ed6` ("0.5.0 (Recommended)", "After the tenth (Recommended)", "Keep pop-ups (Recommended)"), then three codex plan rounds (rounds 6–8: 27, 36 and 25 findings, every one verified). Rounds 6 and 7 were applied as two correction layers; round 8 showed that most new findings were defects in those layers, so the practitioner chose a rewrite ("Yes, rewrite it") with three simplifications: decisions 0.10 ("One last-backup date (Recommended)"), 0.11 ("Yes, open each one (Recommended)") and 0.12 ("Only if nothing left out (Recommended)"). This body is that rewrite. The superseded layers are kept as a record in the Review Findings Log.
- What the rewrite changed against October, in one place: no audit-format change (the audit row stays v3; one date in `config\backup.json` instead); a backup proves every session opens and reports what it left out, and never calls itself complete; Back up refuses while the audit record cannot be read; one run gate that disables the window instead of a check at every writer; a session that holds a kept recording is never in a backup (decision 0.13), so deletion does not change; files are bound by SHA-256, not by file number, wherever a removable drive is involved; a 1 GiB cap; the manifest is one structure; the documents stay v3 until approved and no real backup is made before that.
- 2026-11-25 (later): five codex rounds on the rewritten body (rounds 9–13: 13, 12, 10, 10 and 6 findings, every one verified and applied IN PLACE, no layer) and decision 0.13 ("Leave those sessions out (Recommended)": a session that still holds a kept recording is never in a backup, which removed the deletion change). The pass reached its cap of five WITHOUT a clean round; round 13's reviewer still judged the body not ready. The practitioner decides what happens next (Review History).
- 2026-11-25 (evening): the practitioner raised the cap by three rounds ("Up to three more rounds (Recommended)"). Rounds 14 and 15 returned 6 and 8 findings; most of round 15's came from round 14's own change (a verdict line and a three-step rule) and from the key repair. The practitioner then cut both: decision 0.14 ("Simple rule, limits named (Recommended)") and decision 0.15 ("Set aside, then restore (Recommended)"). The body was amended in place for both, which also removed every change to deletion. Round 16 is the last approved round.
- The plan file is UNCOMMITTED since the reconciliation; commit only on the practitioner's word.
- 2026-11-25 (night): round 16 returned 10 findings (2 HIGH, 5 MED, 3 LOW), every one verified and applied in place; all ten concern the set-aside written that evening or wording left from earlier rounds. The pass ENDED at its raised cap WITHOUT a clean round (eight rounds on this body: 13, 12, 10, 10, 6, 6, 8, 10); round 16's amendments are unreviewed.
- 2026-11-26: the practitioner chose "One focused round": round 17, limited to the set-aside and the add-only restore (the set-aside has had one review). With no HIGH finding the plan goes to build; with one it comes back to the practitioner.
- 2026-11-26: round 17 (focused) returned 9 findings — 0 HIGH, 7 MED, 2 LOW — every one verified and applied in place; the reviewer judged the set-aside and the add-only restore ready to build under the practitioner's rule. Round 17's amendments are themselves unreviewed; the build loop's per-phase reviews check the code against this body.
- NEXT: by the practitioner's rule the plan goes to build. The commit of this plan file and the start of the build wait for their word. When the plan is built: `/execute-loop` from Task 0.8 in its own worktree (C13); the wizard takes the more-than-one-Active-plan path (Custom), since `plan-stronger-voice.md` and `plan-ui-refresh.md` are Active too.

## Tasks

Grouped into phases for `/execute-loop` (a review loop and a codex peer pass at each boundary). Paths are under `desktop/src/scribe_desktop/` unless they start otherwise. A `[decision]` task is the practitioner's. An `[operator]` task is a release act or a practitioner-run step the executor never takes.

### Phase 0 — Decisions and baselines

- [x] 🟩 **0.1 [decision] What is backed up.** **DECIDED 2026-10-09 (practitioner): every committed readable Past-sessions entry and the whole audit record** (D1). Rejected: entries only; the whole data folder.
- [x] 🟩 **0.2 [decision] Kept development recordings.** **DECIDED 2026-10-09 (practitioner): EXCLUDED from every backup; the consent document's sentence stays true.** Rejected: included behind a tick under a new `development-consent-v2`.
- [x] 🟩 **0.3 [decision] The passphrase scheme.** **DECIDED 2026-10-09 (practitioner): a chosen passphrase, entered twice, minimum 20 characters, Argon2id 256 MiB / t = 3** (D3). Rejected: a generated 8-word recovery phrase.
- [x] 🟩 **0.4 [decision] Where a backup may be written.** **DECIDED 2026-10-09 (practitioner): fixed and removable drives only; cloud-synced, network, roaming and app folders refused; the data folder's own volume warned** (D7). Rejected: also network drives.
- [x] 🟩 **0.5 [decision] Backups already taken when an entry is deleted.** **DECIDED 2026-10-09 (practitioner): an operating rule — a fresh backup after a Delete now, destroy older ones, keep the newest two.** Refined by 0.12 and 0.14.
- [x] 🟩 **0.6 [decision] The reminder.** **DECIDED 2026-10-09 (practitioner): on the page after 7 days with at least one session not yet backed up; it never acts.** Its basis is 0.10.
- [x] 🟩 **0.9 [decision] Restore on the same login after a Windows password reset broke DPAPI.** **DECIDED 2026-10-09 (practitioner): repair in place.** As amended the same day by the peer rounds, within that choice: a KEY REPAIR — `key.dpapi` alone replaced, only when every local content file matches the backup's hashes and the recovered key opens that content; a differing entry is a reported conflict, untouched. SUPERSEDED 2026-11-25 by decision 0.15 (set aside, then restore); nothing of the repair is built.
- [x] 🟩 **0.10 [decision] How the reminder knows what is backed up.** **DECIDED 2026-11-25 (practitioner): "One last-backup date (Recommended)"** — one date in the backup settings; the audit record's format does not change (D10). Rejected: per-session dates in the audit record (the October audit row v4).
- [x] 🟩 **0.11 [decision] Proving a backup opens.** **DECIDED 2026-11-25 (practitioner): "Yes, open each one (Recommended)"** — every session in a backup is unlocked in memory to prove it opens, and one that does not is left out and counted (D5, D2). Rejected: comparing bytes only.
- [x] 🟩 **0.12 [decision] When older backups may be destroyed.** **DECIDED 2026-11-25 (practitioner): "Only if nothing left out (Recommended)"** — the app never calls a backup complete; older backups are destroyed only when the new one left nothing out, and a backup made before "Start a new audit record" is kept until restored from (D14). Refined in review the same day (rounds 10–14), for the practitioner's approval with the documents at P.3: an older backup is destroyed only after it has ITSELF been opened and the app has said nothing in it is missing from this computer, and a new backup made after that left nothing eligible out (D14's three steps); a backup made before an audit reset therefore passes only once restored from, as chosen. That refinement (the verdict line and the three steps) was WITHDRAWN the same day by decision 0.14; the choice itself stands as 0.14 restates it.
- [x] 🟩 **0.13 [decision] A session that still holds a kept development recording.** **DECIDED 2026-11-25 (practitioner): "Leave those sessions out (Recommended)"** — such a session is backed up only once its recording has been deleted, so the consent's sentence that a recording can be opened only from the practitioner's own Windows login on that computer stays exactly true (D12). Raised by peer round 12 (PR-HIGH-159). Rejected: backing the session up and deleting the recording at a key repair; a new consent version with fresh written consent. It replaces the same day's "Add it to the plan (Recommended)".
- [x] 🟩 **0.14 [decision] How the rule for destroying older backups works.** **DECIDED 2026-11-25 (practitioner): "Simple rule, limits named (Recommended)"** — the app only reports facts about each backup and gives no verdict; the documents give ONE rule (an older backup is destroyed only when the newest says nothing eligible was left out, and never while anything on this computer is lost or unreadable: restore first); the rare double failures the rule cannot cover are named limits for the independent review (D14). It withdraws round 14's verdict line and three steps, which round 15 showed could not be made true in every state (PR-HIGH-181, PR-MED-184, PR-MED-185, PR-LOW-188). Within that choice, for approval with the documents at P.3: backups made BEFORE a loss, a set-aside, a restore or a new audit record are kept, and the rule applies again only to backups made afterwards. Rejected: more checks in the app to make a verdict airtight.
- [x] 🟩 **0.15 [decision] Recovery after a Windows password reset.** **DECIDED 2026-11-25 (practitioner): "Set aside, then restore (Recommended)"** — the app moves the sessions this login can no longer open into a set-aside folder, nothing deleted, and Restore brings them back from a backup as on a new computer (D8). It REPLACES decision 0.9's repair in place, which review rounds 12–15 could not make safe (PR-HIGH-182, PR-MED-186). Within that choice, for approval with the documents at P.3: a session that still holds a kept recording is not moved (Delete recording must keep reaching it), and a session completed after the last backup stays set aside and unreadable. Rejected: keeping the repair with more checks.
- [ ] 🟥 **0.8 Record the dry-run baselines** (Validation / Verification) from the run's own worktree before Task 1.1. Done when: the grep results and the two suites' counts are in this task.

### Phase 1 — Custody, the container and the writer (no UI)

- [ ] 🟥 **1.1 The key-blob seam and the set-aside (D8, D9).** `session_store.py`: `unwrap_key_blob(blob, *, description)` with its five structured refusals, `unwrap_key_from_file` rewritten over it (same outcomes), `dpapi_round_trip()`, and their conftest fakes. `past_sessions.py`: the two constructor seams `classify_key_blob` and `dpapi_probe`; `PastSessionStore.set_aside_refused() -> SetAsideReport` — the probe, the strict listing, the per-entry rule, one rename per entry into a new folder beside the archive, the forgotten caches. NOTHING about deletion or recordings changes: `delete_entry`, `delete_recording`, `_recording_state`, `_audio_key_state`, `_remove_key_first`, `record_past_session`, the two callers' audit order and the retention sweep are untouched. Done when: Validation's `test_past_sessions.py` items pass, `unwrap_key_from_file`'s existing tests pass unedited, and `test_shadow_exits.py` is unedited.
- [ ] 🟥 **1.2 The audit record's export and import surface (D9).** `AuditLog`'s `wrap_key` / `unwrap_key` seams (the blob seam is Task 1.1's); `backup_snapshot`, `row_state`, `restore_row`, the pure `row_importable`; `PastSessionsAudit` extended. The audit row, its schema version and the CSV are NOT touched. Done when: Validation's `test_audit.py` items pass and `git diff` of the schema pins is empty.
- [ ] 🟥 **1.3 The container module `past_sessions_backup.py` (D2, D3, D4).** `FORMAT_VERSION`, `BACKUP_FILENAME_PREFIX` (and its `_NON_PATH_LITERALS` entry in `test_install_layout.py`, here), `MAX_BACKUP_BYTES`, the member caps; `BackupHeader`, `BackupManifest`; `manifest_aad`; `derive_key(passphrase, kdf) -> bytearray` with the envelope check first, `MemoryError` → `kdf_memory`, and the `_kdf_floor_for_tests` seam; the preflight with its directory walk behind the size-and-read seam; `verify_backup(fileobj_or_path, k_b) -> BackupFacts` (every step of D2's reader except the derivation — 1 to 3, the manifest's decryption, 5 and 6 — and the whole-file SHA-256, taking the derived key — it serves the writer's read-back, Open and Restore's second pass); `BackupReader` (`read_member` with its size-and-hash check, `unwrap_entry_key`, `unwrap_audit_key`); `open_backup(path, passphrase)` as derive plus verify, for tests; the closed code set of `BackupFormatError` / `BackupRunError`; `past_sessions.entry_opens(session_id, key, files)` (the pure open check, beside the label code it uses) and the bytes-level validation it shares with `read_transcript` (`transcription.py`), `read_note` and `read_generated` (`session_store.py`), extracted from those readers with their outcomes and tests unchanged. `desktop/pyproject.toml`: `cryptography>=44`. Done when: `test_backup_container.py` passes.
- [ ] 🟥 **1.4 The location rule and the settings file (D7, D10).** `exclusions.py`: `DRIVE_REMOVABLE`, `DRIVE_CDROM`, `DRIVE_RAMDISK`; `WindowsLayer.volume_of`; the shared `_destination` with the text-first refusal; `check_archive_backup_location`; `check_backup_source`; `check_export_location` unchanged in outcome. `note_config.py`: `BackupSettings` with its bounded reader and atomic writer beside `DevelopmentSettings`. Done when: `test_archive_backup_location.py` passes, `test_exclusions.py` is unchanged in outcome, and the settings round trip is tested.
- [ ] 🟥 **1.5 The writer (D1, D5, D6).** `past_sessions.py`: `PastSessionStore.backup_snapshot()`. `past_sessions_backup.py`: `prepare_backup(store, audit, run) -> BackupPlan` (hop B) and `write_backup_file(plan, k_b, destination, *, check_location) -> BackupReport` (hop C: the proved copy, the one-handle write, the read-back verification, the publish and its check, the `.part` rules). The report carries counts and the published file's name. Done when: `test_backup_write.py` passes.
- [ ] 🟥 **1.6 Version 0.5.0** in the five version files and CHANGELOG `[Unreleased]`. Verification: `pytest -k version`.
- [ ] 🟥 **1.7 The frozen build proves Argon2id.** `app.py`: the `--self-check-offline` path gains one step — derive 32 bytes with Argon2id from a fixed non-secret string at small fixed parameters through `past_sessions_backup`'s derivation seam; a failure exits `SELF_CHECK_KDF = 3`. `scripts/build-release.py`: the failure text explains code 3. Done when: the two unit tests of Validation's `test_app.py` line pass. (The frozen proof itself is H5's: the `Release` run's installer-build step passing.) Uses Task 1.3's derivation seam.

### Phase 2 — Back up on the Past sessions page

- [ ] 🟥 **2.1 The run gate (D4, D11).** `ui/main_window.py`: `ArchiveRun`, `archive_run_refusal`, `begin_archive_run`, the disabled window, the `closeEvent` branch. `app.py`: the gate injected into `PeriodicSweep`. `ui/bridge.py`: the `backup_running` refusal and the gate in `_situation`. `ui/models.py`: `START_BACKUP_RUNNING_MESSAGE` and its `chrome_refusal_message` case. Done when: `test_archive_run.py` passes.
- [ ] 🟥 **2.2 The dialogs (D10).** `ui/backup_dialog.py` (the ONLY file with the new `QLineEdit`s): `passphrase_decision`, the passphrase dialog, the summary dialog. Done when: their Validation items pass and `test_shadow_exits.py` is unedited.
- [ ] 🟥 **2.3 Back up… (Flow 1).** `ui/past_sessions.py`: the button; a `ChooseBackupPath` seam (the `ChooseWavPath` shape); admission; the passphrase dialog; the location rule; `begin_archive_run`; the four hops over `ui/tasks.py::TaskThread`; hop D's settings write; the success line's two forms and each refusal line. Done when: the UI tests drive the whole flow with fakes, including every exit of Validation's `test_archive_run.py` line for this flow.
- [ ] 🟥 **2.4 The status line and the changed wording (D10).** `ui/past_sessions_view.py`: `backup_status_line`, shown by `status_lines`; the Delete now confirmation, the delete-done line, the shorter-retention confirmation and the retention warning as D10 gives them (the delete-failed line keeps today's words: deletion does not change). Done when: the Qt-free function is tested for each state and the exact-text tests are updated in this task.

### Phase 3 — Open a backup and Restore

- [ ] 🟥 **3.1 The restore planner (D8).** `past_sessions_backup.plan_restore(reader, store, audit, sessions_root, *, retention_days, now) -> RestorePlan`, GUI thread, run ONCE per Open, and its per-id rule `classify_entry`, which the restorer calls again for each id with the same listing (never a second listing of the archive); the outcome table. Done when: `test_restore.py`'s classification items pass.
- [ ] 🟥 **3.2 The restorer (D8, D9).** `PastSessionStore.restore_entry`, `_publish_new`, `_verify_restored`; `past_sessions_backup.restore_backup(reader, plan, store, audit, *, now) -> RestoreReport`. Done when: the rest of `test_restore.py` passes.
- [ ] 🟥 **3.3 Open a backup… (Flows 2 and 3).** `ui/past_sessions.py`: the button; a `ChooseBackupFile` seam; admission; `check_backup_source`; the header pre-check; the passphrase dialog; `begin_archive_run`; hop A with `verify_backup` on the worker; `plan_restore`; the summary dialog; on Restore the second verification on a worker, then `restore_backup`, the last-backup date, the page re-listed, the outcome line. Done when: the UI tests cover each state of the summary, Close writing nothing, every refusal by name, and every exit of the run.
- [ ] 🟥 **3.4 The set-aside button (D8, D10).** `ui/past_sessions.py`: the button, visible only while the listing holds a session whose label cannot be read; its one confirmation in the page's existing confirm pattern; the admission of D11 (`archive_run_refusal`); `set_aside_refused()`; the page re-listed and the cached sweep report's `undated` count lowered by the number moved. `ui/past_sessions_view.py`: `set_aside_line` and the confirmation text. Done when: the UI tests cover the button's visibility, each admission refusal moving nothing, each form of the report line, each refusal, the re-list and the lowered count. Uses Task 1.1's store method and Task 2.1's admission.

### Phase 4 — Documents

- [ ] 🟥 **4.1 Security documents (D14).** `docs/security/threat-model.md`: the section "Past-sessions backup and restore (0.5.0)" — the file outside custody; the key wrap and the header-bound manifest; the KDF and passphrase strength; the open check and its in-memory plaintext; the location rule and its limits; the run gate; restore's classifications (it only adds) and the set-aside (what qualifies, the probe, the two qualifying DPAPI error codes, that nothing is deleted or recorded, and that nothing in the app opens a set-aside session again); why a session that holds a kept recording is never backed up and never set aside (its entry key also wraps the recording key, and the consent says where a recording can be opened) — and its residues (a backup holds entries deleted later; a deleted recording's former key in a disk snapshot or journal, openable by a later backup's entry key — the existing forensic-residue paragraph amended; a tombstone-less Delete now comes back; the passphrase in widget memory and the pagefile, the immutable key copies; a backup on the same disk; an unseen sync tool; a virtual disk; a lost drive and exactly what it shows; a `.part` that is a whole backup; a restored row's `kept_at` without a recording (including a recording whose pending deletion the app cleared with no row to record it on, after a new audit record was started); a set-aside session that no backup holds, and the set-aside folder outside every control of the app; a recording key left live beside missing audio; the four named limits of the rule for destroying older backups (D14); changes from outside the app during a run); residue (c), the deferral notes, the name-label sentence and "The pilot" (C14) amended. `data-flow-map.md`: flow 30, and the three sentences of the inventory. `retention-schedule.md`: rows for the backup file, `config\backup.json` and the set-aside sessions folder; the Past-sessions and kept-recording rows amended. `intended-use.md`. Done when: the Task 0.8 grep returns only intended sentences in `docs/security/`.
- [ ] 🟥 **4.2 Practice documents (D14, C10).** The inventory amended as dated lines awaiting approval; the `patient-info-v4` DRAFT beside the approved v3; the downtime procedure's two restore sequences, its "Past sessions problems" and the operating rules; the README's reviewer questions (three new, one extended) and its note on the development consent; the clinician review guide's dated line. The development-recording consent document untouched (the README's sentence about the sheet it names is P.3's). Done when: a read-through finds no file name or identifier in patient-facing text, v3 is still named current everywhere, and `test_pilot_docs.py` passes if touched.
- [ ] 🟥 **4.3 Release and project documents, and this plan's cross-references.** `docs/release/pilot-builds.md`: "Rolling back below 0.5.0" (D13) above "below 0.4.2". `PLAN.md`'s deferred-backup sentence. `AGENTS.md`: Current Status, Database Notes (`config\backup.json`, the backup file, the set-aside folder), a Subsystem pointer "If touching the backup…". Pointers into `plan-privacy-professional-controls.md`, `plan-installation.md` and `plan-pilot.md` (their Deferred lines) naming this plan; one dated line on `plan-ui-refresh.md` that 0.4.1 stays reserved. `CHANGELOG`. All against the then-current `main` (C11). Done when: `test_install_layout.py` and `test_pilot_docs.py` pass.
- [ ] 🟥 **4.4 Design-system cues.** `docs/design-system.md`: the two buttons, the set-aside button and its confirmation, the two dialogs by name under the secondary-windows rule, the status line, the success and summary lines, and the changed strings' quotes — each anchored to its symbol.

### Hardening

- [ ] 🟥 **H1 `/review-loop`** over the whole diff (cap 3).
- [ ] 🟥 **H2 `/simplify`.**
- [ ] 🟥 **H3 `/security-review`** (the passphrase and key path, the manifest-driven reader and its preflight, the location rule, the run gate, restore's classifications, the set-aside and its probe, the recording-key check that keeps a session out of a backup and out of a set-aside).
- [ ] 🟥 **H4 codex peer pass** (slice by module if the diff exceeds about 15 files).
- [ ] 🟥 **H5 Build of record** `[operator]` — after the merge to `main`, which waits for the tenth consultation (C13); the push and the `Release` workflow on the practitioner's word. Recorded in `docs/release/pilot-builds.md`: the `main` commit, the `Release` run id with its installer-build step passing (that step runs the frozen self-check, Task 1.7), the attestation and the hashes.

### Phase P — Practitioner-run

- [ ] 🟥 **P.1 Install 0.5.0** `[operator]` — only after the tenth Task 9.1 score and its after-fingerprints (C13); the download re-verified from a normal terminal, after the day's last Complete or Discard, shadow mode left as it was, per `docs/release/pilot-builds.md`. PASS = Settings, Status names 0.5.0 and the Past sessions page shows Back up… and Open a backup…. No backup is made yet (C15).
- [ ] 🟥 **P.2 Developer-build round trip on an isolated data folder** `[operator]` — both apps closed first; every step the practitioner's own, from Explorer or a normal terminal. Rename `%LOCALAPPDATA%\ClinikoScribe-dev` aside (it holds consented recordings — C1); create a fresh `ClinikoScribe-dev` and MOVE only the `models` folder into it. Start the developer build; tick Shadow mode in Settings (a fresh folder starts with it off); record two synthetic scripts (the computer voice may speak them), save a note in at least one, and Complete both. Back up… to a USB drive. Close the app; move BOTH `past_sessions` and `audit` aside. Open a backup… → the summary → Close; Open again → Restore. Check: both entries open, show the shadow mark, and refuse "Copy saved note". Close the app, move `models` back, delete the scratch folder, restore the original folder's name, and confirm the developer build opens on it. Numbers only pasted here.
- [ ] 🟥 **P.3 Documents read and approved** `[operator]` — `patient-info-v4`, its siblings, the downtime procedure's restore sequences, and the app's own changed strings (D10): each dated line approved or sent back. The approval is the one commit that makes v4 current (D14); the practitioner confirms the v4 sheet and form are the ones in use and unused v3 handouts are withdrawn (signed v3 forms are kept as records). Queued for the independent review.
- [ ] 🟥 **P.4 Existing records and the backup** `[decision]` `[operator]` — every entry kept so far was recorded under `patient-info-v3`. With the independent reviewer's answer to the fresh-consent question if there is one, the practitioner chooses: (a) existing entries are backed up once v4 is approved and in use; (b) no real backup until the reviewer has answered; (c) only entries recorded under v4 are backed up — which needs its own approved design (it must also settle the audit record's scope) and a new build. The recommendation is written in the decision brief from what is known then. Done when: the choice is recorded here in the practitioner's words.
- [ ] 🟥 **P.5 The first real backup** `[operator]` — ONLY when P.3 records every line approved and P.4 records (a) (C15). On the installed app, to a removable drive kept apart from the passphrase; then Open a backup… → the summary → Close. Recorded here, numbers only: the counts, what was left out, the file's size, and whether the status line then shows. The agent sees only what the practitioner pastes (C1).
- [ ] 🟥 **P.6 The rollback rule read** `[operator]` before any older install.

## Review History
- 2026-10-09 — `/review-plan` (Fable 5.1), full-plan pass over the draft: four parallel lenses (coverage 13, practicality 11, risk 19, simplicity 7 findings). Folded in: decision 0.9 (same-login DPAPI break → replace unreadable entries key-first); the header-bound manifest, bounded KDF memory and pattern-bound manifest grammar; the stdlib-ZIP container; the run ledger dropped and Check folded into Open a backup; the `AuditLog` export/import surface and its key seams; the four-hop threading split and C12; the restore classifications (`skipped_unknown_row`, `skipped_pruned`, `skipped_expired`, `replaced_unreadable`); restored rows carrying `made_at`; `patient-info-v4` and the "own Windows login" sentence; P.2 moved to an empty set-aside dev data folder; symbol corrections (`audit:` AAD, `session_store` helpers, `install_layout.channel()`, the `check_backup_*` name collision, the two existing drive constants); the eight v3 test pins named. Deferral gate: every candidate confirmed as listed. No scratch consumed.
- 2026-10-09 — `/peer-loop` plan-review round 1 (codex `gpt-6-astra` medium, read-only sandbox, composer-recorded): 12 findings (1 HIGH, 10 MED, 1 LOW; 11 build-affecting, 1 record-only), all verified against the code and applied as amendments the same day: decision 0.9 narrowed to a hash-verified key REPAIR with conflict and uninspectable outcomes (PR-HIGH-001); unknown audit state in EITHER source skips (PR-MED-002); archive retention decoupled from audit pruning — an entry of any age restores under "Until I delete them", its pruned row not recreated (PR-MED-003); `restore_row` takes the manifest's month and binds id / month (PR-MED-004); backup coverage marks only the entries actually written (PR-MED-005); `_upgrade_v2` pinned to 3 (PR-MED-006); Back up gated on `session_busy`, the run flag and the Reset lock (PR-MED-007); the planner moved to the GUI thread (PR-MED-008); a finite KDF envelope (PR-MED-009); the `pre_audit` → `recorded` provenance recovery (PR-MED-010); the CSV slices corrected to `[-6:-2]` / `[-8:-6]` with the value assertions and `test_schema_versions.py:568` (PR-MED-011); the `sample_notes.py` description corrected (PR-LOW-012). Round 2 to follow (the round-1 floor; convergence needs a round with no new build-affecting finding).
- 2026-10-09 — `/peer-loop` plan-review round 2 (codex `gpt-6-astra` medium, composer-recorded): 11 new findings (1 HIGH, 10 MED; all build-affecting), all verified and applied: the key repair became a staging-folder transaction with no new file name, recovered by `clean_staging` (PR-HIGH-013); the repair's member rule admits the two audio sidecars in any state (PR-MED-014); custody classified from ONE blob read through a new `unwrap_key_blob` seam — uninspectable / dead / foreign / DPAPI-refused (PR-MED-015); `restore_row(..., included)` and `backup_status_line(committed_ids, …)` (PR-MED-016); the run guard at `PeriodicSweep.__call__`, the retention selector disabled (PR-MED-017); original-version required-field rules for v3 and v4 (PR-MED-018); the `_v1_document` / `_v2_document` builders strip `backup` (PR-MED-019); a bounded ZIP preflight before `ZipFile` (PR-MED-020); zero-entry audit-only backups and Back up enabled on an emptied archive (PR-MED-021); the destination re-checked immediately before the exclusive create (PR-MED-022); provenance recovery only for a BARE `pre_audit` row, `conflict_row` otherwise (PR-MED-023). Round 3 to follow (not converged: new build-affecting findings).
- 2026-10-09 — `/peer-loop` plan-review round 3 (codex `gpt-6-astra` medium, composer-recorded): 8 of round 2's 11 fixes confirmed landed, 3 partial; 6 new findings (1 HIGH, 5 MED; all build-affecting), all verified and applied: `delete_entry` removes `.staging\<id>` key-first BEFORE the committed key and the repair's cleanup is synchronous, `_remove_key_first` also unlinking the atomic writer's `.tmp` (PR-HIGH-024); the entry folder's `link_state` is read before anything under it — `skipped_linked` / `skipped_uninspectable` (PR-MED-025); the repair opens the content with the recovered key before the replace (PR-MED-026); the member bound is `5 × entry_count + row_count + 3` plus `MAX_MEMBERS = 65_535` (PR-MED-027); `header.json` / `manifest.enc` are envelope members outside the manifest's payload list, the member set equal to envelope plus payload (PR-MED-028); provenance recovery merges the two `backup` timestamps by `max` (PR-MED-029). Round 4 to follow (not converged).
- 2026-10-09 — `/peer-loop` plan-review round 4 (codex `gpt-6-astra` medium, composer-recorded): 5 of round 3's 6 fixes confirmed landed, 1 partial; 4 new findings (3 MED build-affecting, 1 LOW record-only), all verified and applied: the `backup` timestamps are monotonic everywhere — the incoming row's own coverage counts in the merge, `record_backed_up` / `record_restored` take the later value (PR-MED-030); `backup_snapshot` returns row DESCRIPTORS, the worker reading each row under `MAX_ROW_FILE_BYTES` (PR-MED-031); P.2's isolated folder carries the moved-over `models` folder and confirms readiness (PR-MED-032); Agreed Scope and the schema table say key REPAIR, with a row for a repaired entry (PR-LOW-033). Round 5 to follow (not converged; the cap).
- 2026-10-09 — `/peer-loop` plan-review round 5 (codex `gpt-6-astra` medium, composer-recorded; the pass's cap): all 4 of round 4's fixes confirmed landed; 2 new findings (1 MED build-affecting, 1 LOW record-only), both verified and applied: `record_restored` for a kept local row is called only after its entry's publish or the repair's `os.replace` has committed (PR-MED-034); the Integration Notes' between-hop tick example removed, audit-vs-archive retention stated, the post-replace wording ("the new key stays committed"), and the audit Reset located on the Past sessions tab (PR-LOW-035). Tail: 12 → 11 → 6 → 4 → 2 findings (build-affecting 11 → 11 → 6 → 3 → 1); NOT converged at the cap — the cap disposition is the practitioner's (surface-and-ask).
- 2026-10-09 — `/peer-loop` pass ACCEPT-CLOSED at the cap by the practitioner's decision (option (a) of the surface-and-ask: every finding of rounds 1–5 verified against the code and applied, 0 rejected, no CRIT/HIGH since round 3, round 5's one build-affecting item a sequencing clarification with no residue). The plan is ready for `/execute-loop` from Phase 1; a fresh `/peer-loop` pass over the Phase 1 diff is that run's own first peer round.
- 2026-11-25 — `/review-plan` (Fable 5.2), a full-plan reconciliation against `5d63ed6` (the code had moved from 0.3.0 to 0.4.2). Read: the whole plan body, `git diff aeec75e HEAD` over every file it names, the Start funnels, `PeriodicSweep`, `closeEvent`, the design system's dialog rule, the document grep and the data-flow numbering. Result: no design decision moved (the archive, audit, exclusions and container sources are unchanged or changed inside existing lines). Amended: the version (0.5.0) and the flow number (30) throughout the body; the Key Findings re-verification bullet (shifted lines, today's document anchors, the one `schema_version` pin correction); D1, D8 (i)–(v), D9, D10; C11, the new C13 (no install during the ten; its own worktree) and C14 (shadow entries); the validation line; `[operator]` on H5 and Phase P; Tasks 0.7, 0.8, 2.1, 2.2, 3.2, 3.3, 4.1–4.3. Critique: coverage — four gaps closed (close during a run, the Start refusal at each funnel, shadow entries, the theme rules); practicality — the tasks build as written on today's files; simplicity — no simpler path found (the pop-ups were re-asked and kept). Deferral gate: no new candidate; October's dispositions stand. The Findings Log below is the October record and is unedited (it says 0.4.0 and flow 28 where the body now says 0.5.0 and flow 30).
- 2026-11-25 — `/peer-loop` plan-review round 6 (codex `gpt-6.2-astra` high, composer-recorded; round 1 of a new pass after the reconciliation): 27 findings (9 HIGH, 16 MED, 2 LOW; 26 build-affecting, 1 record-only as labelled; verified the same, 0 invalid), all applied the same day as D13 (a)–(z): deletion destroys a held audio key first (PR-HIGH-036, the practitioner's choice); a no-overwrite publish for restore (037); ordinary files only, bound to the opened handle (038); `session_busy` covers a recovered transcript and the flag is taken after the last dialog without a yield (039, 040); the key's path between hops and closed failure codes (041); the source admitted before any read (042); strict listing and whole entries (043); documents approved and the existing-records decision before any real backup, the merge held for the ten (044, the practitioner's choice); `.part` cleanup by identity (045); the audit month and the different-month conflict (046); a non-creating coverage path (047); coverage after a restore (048); the audit fixture inventory (049); the file-name prefix's one owner (050); the development tick (051); Chrome's refusal ending with the run (052); Task 0.7 as the frozen self-check (053); Delete now's wording (054); six more document passages (055); the metadata a lost drive shows (056); P.2's explicit shadow mode and empty audit store (057); Task 3.2's five failure outcomes (058); the volume seam (059); the rollback wording (060); P.3's record (061); the reference corrections (062). Round 7 to follow (round 1 never converges a plan pass).
- 2026-11-25 — `/peer-loop` plan-review round 7 (codex `gpt-6.2-astra` high, composer-recorded; round 2 of the pass): 36 findings (15 HIGH, 19 MED, 2 LOW; 35 build-affecting, 1 record-only as labelled; verified the same, 0 invalid), all applied the same day as D14 (1)–(28): a backup states whether it is complete (063); `delete_entry`'s one read, three results and whole sequence in Task 1.7 (064, 065, 095); the pre-rollback step (066); the snapshot bound to one generation with the label's required members (067, 078); own files only (068); the file admitted and re-authenticated before Restore's first write (069, 070); the writer's handle held to publish (071); the repair bound to the classified blob (072); uncopied rows kept unknown and duplicate rows detected (073, 082); coverage granted per entry, with separate times (074, 084); the run flag at every writer's entry point (075); one run-owned authenticated reader (076); P.3 conditional on real approval (077); header counts as bounds and the empty result (079); the directory walk (080); the volume's GUID name (081); `absent` against `unavailable` (083); every outcome named and counted, the repair cleanup check (085, 086); one cleanup owner (087); a check while the audit record needs attention (088); the reminder's first seven days (089); the page refreshed after a restore (090); the deletion wording (091); v4 a draft until approval (092); the visible metadata stated exactly (093); the dependency floor (094); Task 0.7 against H5 (096); the rollback boundary (097); four stale instructions (098). Not converged; round 8 to follow.
- 2026-11-25 — `/peer-loop` plan-review round 8 (codex `gpt-6.2-astra` high, composer-recorded; round 3 of the pass): 25 findings (7 HIGH, 15 MED, 3 LOW; 22 build-affecting, 3 record-only as labelled; verified the same, 0 invalid). skew=fix-induced (17 of 25 are defects in D13 / D14, the two rounds' own amendments; 8 pre-existing: 101, 102, 105, 107, 108, 110, and in part 106 and 116) action=escalate. No amendment applied: the pass is paused at round 3 of 5 for the practitioner's choice between a consolidation rewrite and a third correction layer.
- 2026-11-25 — CONSOLIDATION REWRITE (Fable 5.2, on the practitioner's "Yes, rewrite it"): the body above the Review History was replaced by one clean body. It folds in every verified finding of rounds 1–8 and three simplifications the practitioner chose first — decision 0.10 "One last-backup date (Recommended)" (the audit row stays v3; the October audit row v4, its CSV columns and its coverage rules are gone), 0.11 "Yes, open each one (Recommended)" (a backup proves every session opens), 0.12 "Only if nothing left out (Recommended)" (no "complete" verdict) — and four design simplifications made in the rewrite: Back up refuses while the audit record cannot be read (no entries-only file); one run gate that disables the window; file bytes bound by SHA-256 instead of file numbers where a removable drive is involved; the manifest as one structure with a 1 GiB file cap. The numbering changed (D1–D15, C1–C15, Tasks 0.8, 0.10–0.12, 1.1–1.7, 2.1–2.4, 3.1–3.3, 4.1–4.4, H1–H5, P.1–P.6). Round 8's 25 held findings are applied by it (their landing places are listed under Round 8's dispositions); the superseded layers D13 and D14 are kept in the log as a record. 40 tasks, 10 done (the decisions). A fresh peer pass follows as Round 9.
- 2026-11-25 — /peer-loop plan review, Round 9 (codex gpt-6.2-astra high; round 1 of the pass over the rewritten body): 13 findings (4 HIGH / 9 MED), all 13 verified build-affecting against the code, 0 record-only, 0 invalid; skew=mixed (12 new; half of PR-MED-132 fix-induced — the `held` set the self-check added duplicated the sweep's existing `kept`); action=none. Applied IN PLACE in the body, no layer: the success line and the destroy rule (124); the open check sharing the readers' validation (125); the staging parent and child rule (126); a rollback rule that destroys no recording (127); no end-known field in the header (128); the retryable `archived` write (129); the row inventory and an undecodable row (130); the summary and final report with every outcome counted (131); the sweep's existing `kept` and its two callback outcomes (132); admission covering enrolment and a draft write (133); a keyless leftover not an entry (134); the development consent's pointer to the sheet (135); "No backup date recorded" and a failed settings write (136). Landed and siblings swept.
- 2026-11-25 — /peer-loop plan review, Round 10 (codex gpt-6.2-astra high; round 2 of the pass): 12 findings (4 HIGH / 7 MED / 1 LOW); verified 11 build-affecting, 1 record-only (PR-HIGH-138, a residue inherent to any backup, named), 0 invalid; skew=mixed (9 new; PR-MED-145 and PR-MED-146 fix-induced by round 9's amendments, PR-LOW-148 by round 9's admission wording); action=none. Applied IN PLACE: the pre-reset backup's keep rule and a confirmation that states no partial rule (137); deletions the surviving backup does not know, and newest-first (138); one row importability check (139); a build with no Delete recording (140); the outcome table counting what reached the disk (141); unique member names (142); the label naming its own id (143); the writer naming what it published (144); where `failed_verify` is reachable (145); the development consent document left unedited (146); a source file that is itself a link (147); the admission order (148). Landed and siblings swept.
- 2026-11-25 — /peer-loop plan review, Round 11 (codex gpt-6.2-astra high, strict grading; round 3 of the pass): 10 findings (3 HIGH / 5 MED / 2 LOW); verified 9 build-affecting, 1 record-only (PR-LOW-158), 0 invalid; skew=mixed (PR-HIGH-149 and PR-MED-153 from rounds 9–10's rule for destroying older backups, PR-MED-154 from round 10's test wording; 7 new); action=none. Applied IN PLACE, with ONE simplification of the family that produced a finding in every round: the rule for destroying an older backup is now a single rule with no exception to another (only a newer backup's "Nothing was left out"; a pre-reset backup kept for the 7 years; nothing else is a reason), so 124, 137, 149 and 153 share one sentence. Also: both buttons always enabled; a failed row write and unattempted work counted, the date's save failure a sentence (150); a `.part` never refused over or reported gone unconfirmed, the name taking the next free suffix (151); `not_restorable` finalised from what was written (152); the wrong-id label caught where it can be (154); the delete-done line, the shorter-retention confirmation and the repair sentence (155–157); a fresh login's two settings (158). Landed and siblings swept.
- 2026-11-25 — /peer-loop plan review, Round 12 (codex gpt-6.2-astra high, strict grading; round 4 of the pass): 10 findings (3 HIGH / 6 MED / 1 LOW); verified 10 build-affecting, 0 record-only, 0 invalid; skew=mixed (PR-MED-164, 165, 166 and PR-LOW-168 from earlier amendments; 6 new); action=escalate for PR-HIGH-159 — a decision for the practitioner (a kept development recording's consent says it can be opened only from the practitioner's Windows login on that computer, and a backup holds the key that wraps its recording key): HELD, nothing changed for it. The other nine applied IN PLACE: the backup restored from is kept while anything is unrecovered (160); when an older backup may be layered (161); the remembered folder checked before a dialog is given it (162); per-file link checks for the repair's local reads (163); the `archived` write shared by add, repair and already-present, counted apart (164); the planner's name for a non-importable row and the item that raised `source_changed` (165); deletion wording that claims only Past sessions (166); the passphrase fields' own signals blocked (167); `_remove_key_first`'s contract stated as it can be kept (168). Landed and siblings swept.
- 2026-11-25 — DECISION 0.13 (the practitioner, on PR-HIGH-159): "Leave those sessions out (Recommended)". Applied IN PLACE as a simplification: D12 is now the rule that a session with a live recording key is never in a backup (read in hop B and again in hop C; `holds_recording`, counted apart); the deletion change of the same day is REMOVED (no recording-key step in `delete_entry`, no `delete_failed_recording_gone`, no `recording_held`, no recording step in the rollback rule, no amendment of the below-0.3.0 section), `delete_entry` keeping only the staging-copy removal; a key repair refuses beside a live or uninspectable recording key; the success line and the summary say how many such sessions there are. 41 tasks, 11 done. Landed and siblings swept.
- 2026-11-25 — /peer-loop plan review, Round 13 (codex gpt-6.2-astra high, strict grading; round 5 of the pass — the CAP): 6 findings (3 HIGH / 2 MED / 1 LOW); verified 5 build-affecting, 1 record-only (PR-LOW-174), 0 invalid; skew=mixed (PR-HIGH-169 and 170 from round 12's rules, PR-MED-173 from decision 0.13's wording; 3 new); action=escalate (cap reached without a clean round: 13, 12, 10, 10, 6). Applied IN PLACE: what keeps the source backup after a restore (169); an older backup on top of the newest, as a procedure that claims no proof (170); `missing` — a kept session the archive no longer holds (171); local headers checked for ZIP64 (172); "Nothing eligible was left out" (173); what D12 proves, and the forensic residue (174). The cap decision is the practitioner's.
- 2026-11-25 — CAP RAISED by the practitioner ("Up to three more rounds (Recommended)"). /peer-loop plan review, Round 14 (codex gpt-6.2-astra high, strict grading; round 6 of the pass): 6 findings (2 HIGH / 2 MED / 2 LOW); verified 4 build-affecting, 2 record-only, 0 invalid; skew=fix-induced for 175–177 (round 13's keep sentence and its `missing` count); action=strengthen-siblings — the family "when may an older backup be destroyed" had drawn a finding in EVERY round (124, 137, 149, 153, 160, 169, 171, 175, 176), each time because a line about a NEW backup was asked to prove something about an OLD one. Applied IN PLACE as one change of approach: the app says it directly — opening a backup shows the verdict line "Nothing in this backup is missing from this computer." only when every planned outcome is benign (here and fully opening, or deleted or expired), and D14's rule is three steps (open the older backup → then a new backup that left nothing eligible out → then destroy). `missing` is withdrawn (171, 177); `skipped_present` now needs the whole local entry to open, with `conflict_damaged` and `skipped_unreadable_row` beside it (175); a lost audit record is caught by step 1, not by the success line (176); recording custody is read before content (178); the two record-only wordings applied (179, 180). Landed and siblings swept.
- Round 15 — 2026-11-25 — codex `gpt-6.2-astra` high plan peer-review (consolidated body, round 7; the second of three extra rounds): 0 CRIT / 3 HIGH / 4 MED / 1 LOW (7 build-affecting, 1 record-only), every one verified. Five came from round 14's own change of approach (the verdict line and the three-step rule) or from the key repair, so the composer did not patch them: it put two questions to the practitioner, who answered "Simple rule, limits named (Recommended)" (decision 0.14) and "Set aside, then restore (Recommended)" (decision 0.15). Applied IN PLACE: the verdict line, the benign set, the keep-this-backup sentence and the three steps WITHDRAWN (the app gives counts and no verdict; D14 states ONE rule with four named limits); the key repair REMOVED with everything that existed for it (the blob classification in the planner, `repair_entry_key`, five outcome classes, the staging step in `delete_entry`, the `_remove_key_first` change, the changed delete-failed line) — Restore only adds, a present path is never touched, and a new set-aside (`set_aside_refused`, the third button) moves unread, beside the archive, the sessions whose key this login's DPAPI refuses; `.csbk.part` is kept after a failed Open; the kept-recording lines reworded. Tasks 0.14, 0.15 and 3.4 added, Task 1.1 re-scoped (44 tasks, 13 done). skew=fix-induced action=simplify-by-decision. One approved round remains (16).
- Round 16 — 2026-11-25 — codex `gpt-6.2-astra` high plan peer-review (consolidated body, round 8; the LAST approved round): 0 CRIT / 2 HIGH / 5 MED / 3 LOW (10 labelled build-affecting), every one verified against the code. NOT clean, so the pass ENDS here without convergence and goes back to the practitioner. All ten are about the set-aside written that evening or wording left from earlier rounds; none reopens the container, the writer, the run gate, the open check or the add path. Applied IN PLACE: the set-aside folder is KEPT under the existing unreadable-session rule (189); a session with any recording file is not moved, so a pending deletion record is finished in place (190); `dpapi_refused` only for two named error codes, anything else `dpapi_error` and left (191); Restore disabled while the retention setting cannot be read (192); the set-aside's lines reworded and a readable session never counted (193); an unlisted present folder is `skipped_leftover`, and Flow 4 no longer promises every moved session comes back (194); no advice in the success line (195); D14's limit (ii) names the provenance-recovery comparison (196); the not-indexed start-up walk acknowledged (197); two restore assertions moved to Task 3.2 and the real-DPAPI test admitted under C9 (198). skew=fix-induced action=surface-and-ask.
- Round 17 — 2026-11-26 — codex `gpt-6.2-astra` high plan peer-review (consolidated body, round 9; a FOCUSED round on the set-aside and the add-only restore, on the practitioner's word "One focused round", with their rule: no HIGH finding → build): 0 CRIT / 0 HIGH / 7 MED / 2 LOW (9 labelled build-affecting), every one verified against the code at `5d63ed6` and applied IN PLACE: the link check before anything under an entry folder is looked at; no claim that a refused blob is intact, and the classifier tested with injected errors; a refusal when the set-aside folder cannot be made; ONE archive listing per Open with a per-id `classify_entry` and a recheck that can only withdraw a write; the final report counting only planned writes, and the leftover label; the lines that promised "which" reworded to "how many"; the page's cached unreadable count lowered after a set-aside; the deletion repair after an audit reset named as a residue; one test moved from Task 2.1 to Task 3.4. The reviewer's closing judgement: ready to build under the round's rule. skew=mixed action=none. The amendments of this round are unreviewed.

## Review Findings Log

### Round 1 - 2026-10-09 - past-sessions-backup plan, independent cross-family codex plan peer-review (round 1)
Recorded by: the orchestrating session (composer-recorded round — the peer ran in a read-only sandbox and printed the block; transcribed verbatim from `.cursor/loops/past-sessions-backup-peer-r1.log` lines 3568–3767)
Source: plan peer-review
Peer: codex gpt-6-astra medium, read-only sandbox
Scope: as above
Materiality summary: 11 build-affecting; 1 record-only; 0 invalid
Severity summary: 1 HIGH; 10 MED; 1 LOW
Round status: Closed — 12 verified, 12 applied as plan amendments 2026-10-09 (0 rejected)
Verification: 15 candidates considered; 3 dropped; 0 downgraded; 12 retained after evidence checks.
Validation performed: static inspection only; no writes, test suites, builds, or access to application data.

#### Findings

**PR-HIGH-001 — Replacement is neither proven identical nor lossless**

- Materiality: build-affecting
- Lens: Unstated assumptions; simpler / safer alternatives
- Plan: D5, C5, decision 0.9, Task 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:82,107,111,143,200`; `desktop/src/scribe_desktop/past_sessions.py:673,725,747,810,2125`; `desktop/src/scribe_desktop/session_store.py:644`; `desktop/src/scribe_desktop/audit.py:1274`.
- Defect: Matching session ids and a failed unwrap do not establish byte identity: the writer can replace an entry using a fresh key, and an unwrap failure can be a transient file-read error. Whole-entry replacement also deletes local audio sidecars deliberately excluded from the backup, even where the backed-up entry key could recover them.
- Concrete amendment: “Distinguish unavailable key files from failed custody; unavailable or uninspectable entries remain untouched. For an existing entry, verify the backed-up key and expected ciphertext against the local entry before mutation; where they match, repair the DPAPI wrap in place and preserve local sidecars. Classify differing generations or unverified local files as conflicts, without deleting them. Recheck immediately before mutation; remove the unconditional ‘byte-identical, lossless’ claim.”
- Pattern to follow: `AuditLog._open_key` distinguishes transient read failure; archive verification precedes destructive publication.
- Verification: Synthetic cases for transient read failure, a different entry generation, matching text with retained audio, and failure during key repair; original content survives every refused recovery.
- Regression risk: Recovery must not restore a deleted audio key or bypass either audit tombstone.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Flow 2-4, Integration Notes, decision 0.9's amendment note, Tasks 3.1-3.2 (`repaired_unreadable` by hash match, `conflict_unreadable`, `skipped_uninspectable`, `repair_entry_key` with read-back)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-002 — Backup-side unknown audit states do not block restoration**

- Materiality: build-affecting
- Lens: Unstated assumptions
- Plan: D1, D5, Task 3.1.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:107,111,199`; `desktop/src/scribe_desktop/audit.py:436,1192`.
- Defect: D1 includes newer audit rows, but D5 skips unknown deletion state only for the local row. With no local row, an uninterpretable backed-up row can accompany an entry selected for restoration even though its deletion state cannot be established.
- Concrete amendment: “Evaluate readable / newer / unreadable / absent separately for both audit sources. A newer or unreadable row in either source produces `skipped_unknown_row`; absence remains a distinct condition.”
- Pattern to follow: D5’s existing local unknown-state refusal.
- Verification: An absent local row combined with a newer or unreadable backed-up row never restores the associated entry.
- Regression risk: Keep entries-only backups distinguishable from backups containing unreadable audit evidence.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Task 3.1 (`skipped_unknown_row` for EITHER source)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-003 — Audit pruning prevents recovery of indefinitely retained entries**

- Materiality: build-affecting
- Lens: Coverage
- Plan: Goal, D5, C5, Task 3.1.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:17,107,111`; `desktop/src/scribe_desktop/past_sessions.py:1543,1573`; `desktop/src/scribe_desktop/audit.py:1033`; `docs/security/retention-schedule.md:257`.
- Defect: The archive retains entries indefinitely under “Until I delete them,” whereas audit months expire independently. D5 nevertheless refuses every sufficiently old entry, so D1 backs up records that disaster recovery cannot restore.
- Concrete amendment: “Separate archive-retention eligibility from audit-row pruning. Indefinitely retained entries remain recoverable without recreating pruned audit rows; explicitly document and test the resulting absence of old tombstone evidence. If a seven-year recovery limit is intended instead, obtain a specific practitioner decision and narrow the backup promise and UI accordingly.”
- Pattern to follow: The existing separation between archive retention and audit pruning.
- Verification: Restore an entry older than seven years under indefinite retention; do not recreate its pruned audit row. Keep the seven-year archive-retention case separate.
- Regression risk: The older-record tombstone limitation must be explicit rather than silently weakening the deletion rule.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Task 3.1 (`skipped_pruned` dropped for entries; `skipped_expired` only under "7 years"; `skipped_pruned_row` by audit month; residue named)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-004 — Opaque audit rows lack the metadata required by the restore API**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing
- Plan: D6, Tasks 1.2 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:112,185,186`; `desktop/src/scribe_desktop/audit.py:436,461,465,757`.
- Defect: `_decode` returns the `_NEWER` singleton before parsing a session date, but `restore_row` receives no source month while being required to choose a month folder and enforce pruning. The archive’s completion date is also not the audit’s local session-start date.
- Concrete amendment: “Pass the manifest’s validated source month into `restore_row`. Use that month for opaque-row placement and pruning; for understood rows, validate the supplied id and month against the decoded row. Preserve newer plaintext unchanged, and use the audit month—not archive completion time—for audit-age decisions.”
- Pattern to follow: Existing month-folder pruning and `_read`’s session-id binding.
- Verification: Newer rows retain their original month and bytes; pruned months refuse; known-row id/month mismatches refuse; cover a session crossing a month boundary.
- Regression risk: Do not create a second row for an existing id.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, Tasks 1.2 and 3.2 (`restore_row(..., month, ...)` with id / month binding; pruning by the audit month)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-005 — Row-only backups falsely mark skipped archive entries as backed up**

- Materiality: build-affecting
- Lens: Coverage; missing verification
- Plan: D7, D8, Tasks 1.4 and 2.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:107,113,114,187,195`; `desktop/src/scribe_desktop/audit.py:807,1159`.
- Defect: D7 timestamps an id when either its entry or its audit row was included. An unreadable entry skipped by D1 therefore disappears from the “not yet in any backup” count merely because its audit row was copied.
- Concrete amendment: “For archive-backup status, record coverage only for entries actually included in the verified file. Keep row-copy success separate from entry coverage, and represent missing/unreadable audit evidence as unknown coverage rather than proof of backup. Count committed entries whose coverage cannot be established.”
- Pattern to follow: Audit facts describe completed operations, not attempted inclusion.
- Verification: A skipped entry with a successfully copied audit row remains unbacked-up; a missing row is not silently counted as covered; a later successful entry backup clears the warning.
- Regression risk: Retain `create=False`; do not recreate pruned rows to support the reminder.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D7, Tasks 1.4 and 2.2 (`record_backed_up` with the manifest's entry ids only; unknown coverage counts as not backed up)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-006 — The version bump bypasses the proposed v3 migration guard**

- Materiality: build-affecting
- Lens: Missing verification / rollback / migration
- Plan: Task 1.2, schema migration table.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:124,185`; `desktop/src/scribe_desktop/audit.py:400,410,438,447`.
- Defect: `_upgrade_v2` currently targets `AUDIT_SCHEMA_VERSION`, so changing the constant to 4 sends v1/v2 rows directly to v4 and bypasses `_upgrade_v3`. An older row already naming `backup` can consequently evade the intended contamination refusal.
- Concrete amendment: “Pin `_upgrade_v2`’s target to literal version 3, then apply `_upgrade_v3` according to the post-upgrade version. Preserve each original version’s required-field checks, including v3’s development-consent and recording fields.”
- Pattern to follow: Sequential, version-specific upgrades with refusal of prematurely named fields.
- Verification: Clean v1/v2/v3 rows become v4; every older version already naming `backup` refuses; malformed v3 rows remain refused.
- Regression risk: Valid historical byte fixtures must continue to decode unchanged in meaning.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Task 1.2, Key Findings (`_upgrade_v2` pinned to 3; `_decode`'s v3 check kept, v4 check added)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-007 — Blocking new Starts does not exclude existing archive writers**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; simpler / safer alternatives
- Plan: D3, C12, Task 2.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:79,150,194`; `desktop/src/scribe_desktop/past_sessions.py:578,673,834`; `desktop/src/scribe_desktop/ui/main_window.py:1418`.
- Defect: Backup is not gated on existing live/recoverable sessions, although C12 promises no overlap with archive writers. Blocking new Starts and Past-sessions buttons leaves an existing session’s Complete or Discard able to mutate archive custody during the worker phase.
- Concrete amendment: “Apply the existing `session_busy` guard to Back up as well as Open, acquire the run guard before asynchronous work, and recheck custody state before snapshotting. Keep the guard through final accounting and exclude audit reset during the run.”
- Pattern to follow: The existing Open/Restore busy-state seam.
- Verification: Backup refuses with live or recoverable custody; guarded callbacks cannot Complete, Discard, reset audit custody, or start another run during the operation; failures release the guard.
- Regression risk: Avoid leaving recording controls disabled after cancellation or worker failure.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D8, C12, Flow 3, Task 2.2 (Back up gated on `session_busy`; run flag before hop A, released on every exit; audit Reset disabled during a run)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-008 — Task 3.3 places local restore classification on a file-only worker**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing
- Plan: C12, Tasks 3.1 and 3.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:150,199,201`; `desktop/src/scribe_desktop/past_sessions.py:1707`; `desktop/src/scribe_desktop/audit.py:997`.
- Defect: Task 3.3 explicitly runs `plan_restore` on a worker with no store calls, but Task 3.1 requires that function to inspect local entries, unwrap keys, inspect audit rows, and classify session custody. Those instructions cannot both hold.
- Concrete amendment: “The worker authenticates and verifies the backup file only. The GUI thread snapshots local archive/audit/session state and computes the restore classifications; revalidate them after the summary dialog and immediately before mutation.”
- Pattern to follow: The backup’s explicit GUI snapshot hop.
- Verification: Extend thread-recording fakes to Open and Restore, asserting that no store, audit, or controller method runs on a worker.
- Regression risk: Revalidation must preserve tombstone and readable-entry protections across the modal dialog.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C12, Flow 2, Tasks 3.1 and 3.3 (`plan_restore` on the GUI thread; the worker authenticates and verifies the file only; per-entry reclassification before mutation)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-009 — Unauthenticated KDF work has no upper time bound**

- Materiality: build-affecting
- Lens: Unstated assumptions; missing verification
- Plan: D3, C8, Task 1.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:109,146,186`.
- Defect: The reader caps memory but accepts any iteration count above the floor, before it can authenticate the manifest. A modified header can therefore request excessive derivation work while remaining within the memory cap; header binding detects the modification only afterward.
- Concrete amendment: “Define finite accepted ranges for every KDF work parameter, including iterations and lanes, and validate their combinations before invoking the KDF. Define equivalent bounds if the scrypt fallback is selected; reject unsupported higher-cost profiles by a closed refusal code.”
- Pattern to follow: C8’s existing pre-derivation memory refusal.
- Verification: Out-of-range work parameters refuse without calling the derivation seam; ordinary supported profiles remain compatible.
- Regression risk: Document the supported parameter envelope so future increases do not imply unlimited acceptance.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D3, C8, Task 1.3 (finite envelope for memory, iterations and lanes; scrypt envelope; `kdf_out_of_range` before derivation)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-010 — Sparse local audit rows can permanently suppress recoverable provenance**

- Materiality: build-affecting
- Lens: Coverage; missing verification / migration
- Plan: D6, Task 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:112,200`; `desktop/src/scribe_desktop/audit.py:330,1091,1161`; `desktop/src/scribe_desktop/app.py:432,458,809`.
- Defect: After audit loss/reset, startup repairs can create sparse `pre_audit` rows for surviving entries. “Local rows win” then permanently excludes a backed-up `recorded` row containing consent and provenance that the sparse local row never held.
- Concrete amendment: “Define a separate restore outcome for local `pre_audit` versus backed-up `recorded` rows. Preserve local tombstones and later recording facts, but do not silently report complete audit recovery when provenance was skipped; specify either a narrowly validated provenance-recovery operation or an explicit unresolved conflict shown in the restore summary.”
- Pattern to follow: Existing `origin` distinction and tombstone precedence.
- Verification: Reset audit custody, allow a synthetic startup repair, then restore a complete older audit row; recoverable provenance is recovered or explicitly reported unresolved, and deletion facts survive.
- Regression risk: Never replace a deletion tombstone with an older archived state.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, C5, Flow 3, Tasks 1.2 and 3.1-3.2 (`provenance_recovered`: a `pre_audit` local row replaced by a `recorded` backed-up row with deletion facts carried over)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-011 — The test-pin instructions contain wrong slices and omit assertions**

- Materiality: build-affecting
- Lens: Missing verification / rollback / migration
- Plan: Task 1.2, schema table, Validation / Verification.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:124,156,185`; `desktop/tests/test_audit.py:1195,1213,1219,1352`; `desktop/tests/test_schema_versions.py:568`.
- Defect: Four recording-related columns become `[-6:-2]`, not `[-6:-4]`, while the existing mode/version pair becomes `[-8:-6]`. The inventory also omits two CSV-value assertions and the v1-upgrade schema tuple.
- Concrete amendment: “Preserve the recording header/value assertions at test_audit.py:1195,1213,1219 using `[-6:-2]`; move the mode/version assertion at :1352 to `[-8:-6]`; add separate backup header/value assertions at `[-2:]`. Update test_schema_versions.py:568 to version 4 and correct the plan’s matching inventories.”
- Pattern to follow: Existing header and value coverage for each appended schema group.
- Verification: All historical column groups retain their values and order; the two new columns are separately verified.
- Regression risk: Do not replace established recording-column coverage with backup-only assertions.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Task 1.2, Key Findings, Schema table, Validation (`[-6:-2]` with header and value assertions, `[-8:-6]`, new `[-2:]` assertions, `test_schema_versions.py:568`)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-LOW-012 — The cited ZIP reader is not stored-only**

- Materiality: record-only
- Lens: Practicality / feasibility / sequencing
- Plan: Key Findings, D11.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:67,117`; `desktop/src/scribe_desktop/sample_notes.py:150,360,379,388`.
- Defect: The plan describes the existing reader as `ZIP_STORED`-only, but it admits stored and deflated input and writes its bounded intermediate copy as stored-only. The backup’s deliberate stored-only restriction remains valid.
- Concrete amendment: “Describe sample_notes.py as a bounded stored/deflated input reader that produces a stored-only intermediate package; state that the backup reader adopts its bounds/error-handling pattern while narrowing accepted input to stored-only.”
- Pattern to follow: Accurate separation of input validation and output encoding.
- Verification: Documentation inspection against `_DOCX_METHODS`; no additional runtime test required.
- Regression risk: None; do not broaden the backup format’s accepted compression methods.
- Triage: Include in plan
- Fix route: fix-on-fast
- /fix decision: Applied as a plan amendment
- /fix notes: Key Findings and D11 (`sample_notes.py` admits stored and deflated input; the backup reader narrows to stored-only)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

#### Lens coverage

- Coverage: PR-MED-003, PR-MED-005, PR-MED-010.
- Practicality / feasibility / sequencing: PR-MED-004, PR-MED-007, PR-MED-008, PR-LOW-012.
- Unstated assumptions: PR-HIGH-001, PR-MED-002, PR-MED-009.
- Simpler / safer alternatives: custody repair in PR-HIGH-001; shared busy-state gating in PR-MED-007.
- Missing verification / rollback / migration: PR-MED-003 through PR-MED-011 as specified above.
- No additional finding established for the manifest’s header binding, the `st_dev` same-volume comparison, D9’s stated 0.3.0 newer-row behavior, or C1’s agent-access boundary. The frozen-build KDF probe remains required; the dependency pin alone does not establish its result.

### Round 2 - 2026-10-09 - past-sessions-backup plan, independent cross-family codex plan peer-review (round 2)
Recorded by: the orchestrating session (composer-recorded round — read-only sandbox; transcribed verbatim from `.cursor/loops/past-sessions-backup-peer-r2.log` lines 2920–3119)
Source: plan peer-review
Peer: codex gpt-6-astra medium, read-only sandbox
Scope: as above
Round 1 PR-HIGH-001: partial — destructive replacement removed; repair still has custody, classification and member-set gaps.
Round 1 PR-MED-002: landed — unknown audit state in either source blocks entry restoration.
Round 1 PR-MED-003: landed — archive retention and audit pruning are separated.
Round 1 PR-MED-004: landed — restore receives and validates the source month.
Round 1 PR-MED-005: partial — backup accounting uses entry ids; restore accounting and the status-function contract remain inconsistent.
Round 1 PR-MED-006: partial — sequential upgrades specified; direct v4 input loses an inherited required-field check.
Round 1 PR-MED-007: partial — busy/run guards added; direct retention changes and the actual periodic-prune entry point remain uncovered.
Round 1 PR-MED-008: landed — local classification runs on the GUI thread and is repeated before mutation.
Round 1 PR-MED-009: landed — finite KDF work bounds precede derivation; ZIP preprocessing has a separate remaining gap.
Round 1 PR-MED-010: partial — provenance recovery specified, but preservation covers deletion facts rather than all later recording facts.
Round 1 PR-MED-011: partial — requested slices and assertions corrected; historical-document builders still need amendment.
Round 1 PR-LOW-012: landed — stored/deflated input and stored-only intermediate output are accurately distinguished.
Materiality summary: 11 build-affecting; 0 record-only; 0 invalid
Severity summary: 1 HIGH; 10 MED
Round status: Closed — 11 verified, 11 applied as plan amendments 2026-10-09 (0 rejected)
Verification: 14 candidates considered; 3 dropped; 11 retained after evidence checks.
Validation performed: static inspection only; no writes, test suites, builds, or application-data access.

#### Findings

**PR-HIGH-013 — Repair introduces an additional key without a deletion or crash-recovery contract**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; missing verification / rollback / migration
- Plan: D5, C5, Task 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:200`; `desktop/src/scribe_desktop/past_sessions.py:547–552,895–923,2115–2135`.
- Defect: A crash after writing `key.dpapi.new` leaves another usable entry key outside the staging cleanup. A subsequent Delete now or expiry removes the canonical key and treats directory removal as best-effort, so the alternate key can survive an operation considered cryptographic deletion; additionally, the existing injected entry-key seams cannot select the proposed alternate filename.
- Concrete amendment: “Define repair as an explicit custody transaction with filename-aware injected wrap/unwrap seams, link refusals, and restart/failure cleanup. Every entry destroyer must remove all repair-key custody before declaring cryptographic deletion successful; a cleanup failure must preserve the failure state. An interrupted repair must be safely retryable without treating its temporary key as an unexplained content member.”
- Pattern to follow: Key-first deletion and staging cleanup already make custody removal load-bearing.
- Pattern siblings: Repair failure, restart cleanup, Delete now, retention expiry, and unfinished-entry removal.
- Verification: Interrupt before and after temporary-key read-back and before rename; then retry, delete and expire the entry. Inject directory-removal failure and verify no alternate usable key survives a reported successful deletion.
- Regression risk: Preserve the old canonical key on failed repair and refuse linked or uninspectable repair paths.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Task 3.2, Integration Notes (the repair's temporary key is staged under `.staging\<id>` — the folder `clean_staging` already removes key-first at start-up and every tick — and `os.replace`d over `key.dpapi`; no new file name exists outside the destroyers' reach; a linked staging refuses; the seams are unchanged)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-014 — Exact member equality prevents the promised repair with retained audio**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing
- Plan: D1, D5, Tasks 3.1–3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:107,111,199–200`; `desktop/src/scribe_desktop/past_sessions.py:30–36`.
- Defect: The backup excludes both audio sidecars, but repair requires the local member set to equal the manifest’s set. An entry holding a kept recording therefore becomes a conflict, contradicting the explicit acceptance case requiring repair while preserving its audio.
- Concrete amendment: “Compare the exact set and hashes of the backed-up content members. Explicitly permit and preserve the two known local audio sidecars, including deleted-audio residue; exclude custody transaction files under the separately defined repair rules, and refuse other unexpected members.”
- Pattern to follow: D1’s explicit content-file allowlist and the existing distinction between entry content and audio custody.
- Verification: Repair matching text entries with intact audio, no audio, and deleted-audio residue; differing backed-up content or an unexplained extra member remains untouched.
- Regression risk: Never recreate or replace an audio key from the backup.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, Task 3.1 (the repair compares the CONTENT members against the manifest and additionally admits `audio.enc` / `audio-key.enc` in any state; any other extra member is a conflict)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-015 — Pre-reading the key file does not distinguish DPAPI refusal from a second read failure**

- Materiality: build-affecting
- Lens: Unstated assumptions
- Plan: Integration Notes, D5, Task 3.1.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:82,111,199`; `desktop/src/scribe_desktop/session_store.py:156–166,631–660`; `desktop/src/scribe_desktop/past_sessions.py:551–552`.
- Defect: The existing unwrap seam reads the file again and folds that read’s failure, a dead/truncated blob, wrong-purpose custody and DPAPI failure into `KeyCustodyError`. A successful preliminary read therefore does not establish the plan’s required “DPAPI refused” classification.
- Concrete amendment: “Classify custody from one bounded blob read, using a blob-based unwrap seam or structured failure reasons. Read failures remain uninspectable; dead/truncated and wrong-purpose blobs receive explicit non-DPAPI outcomes. Only the defined eligible custody-refusal outcome may enter repair, after the remaining content checks.”
- Pattern to follow: `key_blob_is_dead` is the existing shared dead-blob definition.
- Verification: Cover failure on the unwrap path after a successful preliminary read, zero-length/truncated custody, wrong-purpose custody, and genuine DPAPI refusal; verify only the intended case becomes repairable.
- Regression risk: Do not interpret transient I/O failure as permission to overwrite custody.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, Task 3.1, Key Findings, Task 1.2 (one bounded blob read classifies: `OSError` → `skipped_uninspectable`; `key_blob_is_dead` → `skipped_dead_key`; a new `session_store.unwrap_key_blob(blob, description)` seam reports wrong description → `skipped_foreign_key` and DPAPI failure → the only repairable outcome; the conftest gains the blob seam)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-016 — Restore still mistakes row inclusion for entry-backup coverage**

- Materiality: build-affecting
- Lens: Coverage; missing verification
- Plan: D6, D7, schema backfill paragraph, Tasks 1.2 and 2.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:107,112–113,130,185,195`; `desktop/src/scribe_desktop/audit.py:972–995`.
- Defect: D6 sets `last_backed_up_at = made_at` on every imported readable row because the row is in the file, including rows whose entries were skipped. Separately, `backup_status_line(rows, now)` cannot count committed entries missing from the audit listing, as D7 requires.
- Concrete amendment: “Pass manifest entry inclusion into row restoration. Set coverage to `made_at` only when that entry is included; row-only imports preserve previously established coverage or None. Pass committed archive ids explicitly to `backup_status_line`, and count ids without readable coverage as unbacked-up.”
- Pattern to follow: D7’s corrected distinction between entry coverage and row-copy success.
- Pattern siblings: D6 import, schema backfill wording, Flow 3 accounting, and Task 2.3’s function contract.
- Verification: Restore a row-only backup beside an unreadable local entry with no local row; it must remain unbacked-up. Test a committed entry absent from all returned audit rows.
- Regression risk: Continue using `create=False`; do not recreate pruned rows for reminders.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, D7, D8, Schema backfill, Tasks 1.2 and 2.3 (`restore_row(..., included)` sets `last_backed_up_at` only for an included entry; `backup_status_line(committed_ids, rows, now)`; Flow 3 accounting)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-017 — Retention changes bypass the run guard, and the timer gate is underspecified**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; simpler / safer alternatives
- Plan: C12, Task 2.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:150,194`; `desktop/src/scribe_desktop/ui/past_sessions.py:867–901,1086`; `desktop/src/scribe_desktop/app.py:601–608`.
- Defect: Lowering retention directly invokes a sweep while the retention selector remains outside the disabled set. Guarding `run_sweep` or the tab’s refresh tick also does not explicitly guard `PeriodicSweep.__call__`, which independently invokes audit pruning and retention deletion.
- Concrete amendment: “Use the shared run guard at `PeriodicSweep.__call__` before all three steps, without advancing skipped sweep clocks. Disable the retention selector and guard its callback and direct retention-sweep entry point, including a recheck after confirmation.”
- Pattern to follow: One shared run guard covering mutation entry points, rather than only visible buttons.
- Pattern siblings: Direct retention change, direct retention sweep, periodic session cleanup, audit prune and periodic retention sweep.
- Verification: During a backup worker hop, attempt a retention reduction and trigger a due periodic audit prune; neither may mutate the stores. Verify normal operation resumes on every run exit.
- Regression risk: A failed or cancelled run must not permanently suppress retention or pruning.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: C12, Task 2.2, D8 (the shared run guard at `PeriodicSweep.__call__` before all three steps without advancing its clocks; the retention selector disabled and `on_retention_chosen` guarded with a re-check after its confirm; the audit Reset guarded)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-018 — Direct v4 rows lose the inherited required-field check**

- Materiality: build-affecting
- Lens: Missing verification / rollback / migration
- Plan: Task 1.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:185`; `desktop/src/scribe_desktop/audit.py:347–348,440–453`; `desktop/tests/test_schema_versions.py:610–619`.
- Defect: The amended task retains the consent/recording name check specifically for version 3 and adds a v4 check requiring only `backup`. Direct v4 data missing either inherited field can consequently acquire the model defaults instead of being refused.
- Concrete amendment: “Require `development_consent_version` and `recording` on original v3 and v4 rows, and require `backup` additionally on original v4 rows. Keep these original-version checks distinct from the sequential historical upgrades.”
- Pattern to follow: Stored bytes must name required fields; construction defaults do not prove a valid stored record.
- Verification: Direct v4 input missing each inherited field refuses; clean v1/v2/v3 upgrades and the existing current-version missing-field test continue to pass.
- Regression risk: Do not weaken historical contamination checks while preserving valid upgrades.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Task 1.2 (an original v3 row must name consent + recording; an original v4 row those two AND `backup`; the sequential upgrades kept distinct)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-019 — Historical test builders retain the newly introduced backup field**

- Materiality: build-affecting
- Lens: Missing verification / rollback / migration
- Plan: Key Findings test inventory, Task 1.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:71,185`; `desktop/tests/test_audit.py:826–842,896–903,982–989,1087–1094`.
- Defect: `_v1_document` and `_v2_document` serialize the current model and remove only fields introduced through v3. After adding `backup`, these purported valid historical fixtures retain it and are correctly rejected by the newly required contamination guard.
- Concrete amendment: “Update both historical-document builders to remove `backup` when constructing valid v1/v2 documents. Keep separate deliberately contaminated fixtures that retain it, and preserve the existing historical decode and disk-update coverage.”
- Pattern to follow: The fixed historical byte literals remain independent of the current model shape.
- Verification: Valid historical helper output upgrades successfully; the equivalent output with `backup` deliberately added refuses.
- Regression risk: Do not ‘fix’ these failures by relaxing the production decoder.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Task 1.2, Key Findings (`_v1_document` / `_v2_document` strip `backup` too; deliberately contaminated fixtures kept separate)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-020 — Manifest bounds arrive after unbounded ZIP-directory parsing**

- Materiality: build-affecting
- Lens: Unstated assumptions; missing verification
- Plan: D11, C8, Task 1.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:117,146,186`; `desktop/src/scribe_desktop/sample_notes.py:360–382`.
- Defect: The specified bounds depend on opening the ZIP and then authenticating its manifest, but the cited pattern parses the central directory before inspecting member counts. An oversized directory can therefore drive substantial unauthenticated allocation before the manifest’s size or member-set checks help.
- Concrete amendment: “Define finite pre-authentication limits for central-directory bytes and member count, enforced before constructing the normal ZIP reader through a bounded preflight; explicitly admit or refuse ZIP64. Bound and validate the header and manifest members’ declared sizes and methods before reading them, then perform the authenticated manifest checks.”
- Pattern to follow: D3’s corrected rule that unauthenticated input must not select unbounded work.
- Verification: Oversized directory/count and oversized or compressed header/manifest cases refuse before normal directory parsing, derivation or large member reads; test through injected seams without allocating oversized inputs.
- Regression risk: Choose documented limits that admit the supported full-backup size and remain compatible with the writer.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D11, C8, Task 1.3 (a bounded ZIP preflight before `ZipFile`: file size cap, EOCD read, ZIP64 refused, entry count and central-directory size caps, header and manifest members' declared sizes and methods checked before they are read)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-021 — Empty archives cannot back up their remaining audit record**

- Materiality: build-affecting
- Lens: Coverage
- Plan: Goal, D1, D8.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:18,107,114`; `desktop/src/scribe_desktop/ui/past_sessions.py:657,671,972–983`.
- Defect: D8 makes Open the only enabled action when the archive is empty. Deleting the final entry leaves audit rows and tombstones that still require backup, so this state cannot satisfy D1’s whole-audit-record promise.
- Concrete amendment: “Back up remains available with an empty archive when audit rows exist, subject to the same busy/run guards. Support zero-entry audit-only backups and restoration; define an explicit no-data outcome when both stores are empty.”
- Pattern to follow: Existing audit CSV export is independent of whether archive entries exist.
- Verification: Delete the final synthetic entry, back up the remaining audit record, and restore its tombstone into a fresh store.
- Regression risk: Zero-entry verification must not require an entry key; the manifest and audit-key path must suffice.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D1, D8, Task 2.2, Task 1.3 (Back up enabled with an empty archive when audit rows exist; a zero-entry backup is verified through the manifest and the audit key; both stores empty → an explicit no-data line)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-022 — The backup writer does not repeat the destination check before creation**

- Materiality: build-affecting
- Lens: Unstated assumptions; simpler / safer alternatives
- Plan: Flow 1, D4, Tasks 1.4 and 2.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:94,110,187,194`; `desktop/src/scribe_desktop/ui/past_sessions.py:765–772,789–803`.
- Defect: Backup checks the destination before confirmation and asynchronous derivation, then its worker writes by path without a specified recheck. If that path resolves differently before creation, the writer can bypass C2’s destination refusal; the existing recording-export flow expressly repeats the check at creation time.
- Concrete amendment: “Pass an injected destination-check seam into the writer and revalidate the resolved folder immediately before exclusive creation. Refuse a changed or uninspectable destination; use the admitted resolved destination for the write, verification and publication.”
- Pattern to follow: Recording export’s check after the dialog and immediately before file creation.
- Verification: Change the fake destination resolution between admission and the write to a refused or uninspectable location; no backup member or partial file is written there.
- Regression risk: Preserve the plaintext-export rule’s existing behavior while sharing detection code.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Flow 1, D4, Tasks 1.4 and 2.2 (`write_backup_file` takes the location-check seam and re-checks the resolved folder immediately before the exclusive create, as Export does)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-023 — Provenance recovery can erase later local recording facts**

- Materiality: build-affecting
- Lens: Coverage; missing verification / migration
- Plan: D6, Flow 3, Tasks 1.2 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:100,112,185,200`; `desktop/src/scribe_desktop/audit.py:288–300,1161–1166`; `desktop/src/scribe_desktop/ui/past_sessions.py:807–809`.
- Defect: The replacement rule carries over local deletion facts only. After an audit reset, a local `pre_audit` row can accumulate recording-export facts; replacing it with an older `recorded` row can discard those facts despite Round 1’s requested preservation of later recording evidence.
- Concrete amendment: “Define provenance recovery’s treatment of every local `RecordingRecord` field, including kept evidence and export counts, rather than preserving only deletion. Where the two histories cannot be combined without inventing totals or chronology, preserve the local row and report an explicit unresolved provenance conflict instead of silently replacing it.”
- Pattern to follow: Local operational facts remain authoritative; recovered provenance must not erase subsequent activity.
- Verification: Create a sparse row after reset, record a later export, then restore an older recorded row. Verify the later fact survives or the operation reports a conflict without changing the local row; retain the deletion-precedence tests.
- Regression risk: Do not add potentially overlapping export counts or manufacture a complete history from incomplete sources.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, Task 1.2, Task 3.2 (provenance recovery replaces ONLY a bare `pre_audit` row — no recording, deletion, past-session or write facts; otherwise the local row is kept and `conflict_row` is reported)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

#### Lens coverage

- Coverage: PR-MED-016, PR-MED-021, PR-MED-023.
- Practicality / feasibility / sequencing: PR-HIGH-013, PR-MED-014, PR-MED-017.
- Unstated assumptions: PR-MED-015, PR-MED-020, PR-MED-022.
- Simpler / safer alternatives: shared mutation guards in PR-MED-017; reuse of the destination-recheck pattern in PR-MED-022.
- Missing verification / rollback / migration: PR-HIGH-013 and the verification amendments above, particularly PR-MED-018 and PR-MED-019.
- No additional finding established for D1’s entries-only path, the `st_dev` comparison as a same-volume test, D9’s stated rollback behavior, D10/D12’s agent-exposure boundary, or Phase 0/Phase 1 sequencing. The frozen-build KDF probe remains required; the dependency pin alone does not prove its result.

### Round 3 - 2026-10-09 - past-sessions-backup plan, independent cross-family codex plan peer-review (round 3)
Recorded by: the orchestrating session (composer-recorded round — the peer ran in a read-only sandbox and printed the block; transcribed verbatim from `.cursor/loops/past-sessions-backup-peer-r3.log`)  
Source: plan peer-review  
Peer: codex gpt-6-astra medium, read-only sandbox  
Scope: as above  
Round 2 PR-HIGH-013: partial — staging is used, but committed-entry destroyers do not require its custody removal; the atomic writer also creates temporary custody.  
Round 2 PR-MED-014: landed — both audio sidecars and their deletion residues are explicitly admitted and preserved.  
Round 2 PR-MED-015: landed — custody classification uses one blob read and an injectable unwrap seam with distinct refusals.  
Round 2 PR-MED-016: landed — entry inclusion controls coverage, and the status function receives committed ids.  
Round 2 PR-MED-017: landed — the periodic entry point, retention changes and audit Reset are covered by the shared guard.  
Round 2 PR-MED-018: landed — original v3 and v4 inputs retain their respective required-field checks.  
Round 2 PR-MED-019: landed — historical builders remove `backup`, with contaminated fixtures kept separate.  
Round 2 PR-MED-020: partial — preflight precedes ZIP parsing, but its member-count formula rejects supported writer output.  
Round 2 PR-MED-021: landed — audit-only backups, zero-entry verification and the no-data outcome are specified.  
Round 2 PR-MED-022: landed — destination resolution is rechecked immediately before exclusive creation.  
Round 2 PR-MED-023: partial — recording, deletion and write facts are protected, but the explicit bare-row predicate omits the new backup facts.  
Materiality summary: 6 build-affecting; 0 record-only; 0 invalid  
Severity summary: 1 HIGH; 5 MED  
Round status: Closed — 6 verified, 6 applied as plan amendments 2026-10-09 (0 rejected)  
Verification: 11 candidates considered; 5 dropped; 0 downgraded; 6 retained after evidence checks.  
Validation performed: static inspection only; no writes, test suites, builds, payload execution or application-data access.

#### Findings

**PR-HIGH-024 — Staged repair custody can survive a successful entry deletion**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; missing verification / rollback / migration.
- Plan: D5, C5, Task 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:111,200`; `desktop/src/scribe_desktop/past_sessions.py:895–923,1519–1529,1642–1647,2115–2135`; `desktop/src/scribe_desktop/session_store.py:576–586,627`.
- Defect: A failed repair may leave a usable staging key, but Delete now and expiry remove only the committed entry’s key; deletion can succeed before staging cleanup succeeds. Moreover, the unchanged wrap helper creates `key.dpapi.tmp`, whose removal is only best-effort under `_remove_key_first`, so a crash during wrapping can leave custody even when staging cleanup reports success.
- Concrete amendment: “Removal of every repair-custody file, including the atomic writer’s temporary key, is load-bearing before committed-entry deletion or expiry reports success. Define synchronous failure cleanup and restart recovery; failed or uninspectable custody cleanup must preserve a failure state and prevent successful deletion accounting.”
- Pattern to follow: `remove_pending_entry` already makes removal of both custody locations a prerequisite for destroying the source key.
- Pattern siblings: Failed repair, crash during wrapping, `clean_staging`, Delete now, retention expiry and unfinished-entry removal.
- Invariant: Successful cryptographic deletion leaves no usable local repair copy of the entry key.
- Verification: Inject failed read-back followed immediately by Delete now; crash during the atomic key write followed by failed directory removal; retry and expiry. Assert that no operation reports successful deletion while alternate custody remains.
- Regression risk: Preserve the canonical key when required cleanup fails; do not follow linked cleanup paths.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Task 3.2, Validation (the repair's cleanup is synchronous in its own `finally`, `_remove_key_first` also unlinks the atomic writer's `key.dpapi.tmp` load-bearingly, and `delete_entry` — Delete now and expiry — removes `.staging\<id>` through `_remove_key_first_unless_link` BEFORE the committed key, `delete_failed` otherwise: the `remove_pending_entry` ordering applied to committed entries; the committed key is only ever the `os.replace`'s target, never the atomic writer's)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-025 — Direct key repair bypasses the final-entry directory’s link refusal**

- Materiality: build-affecting
- Lens: Unstated assumptions.
- Plan: D5, Tasks 3.1 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:111,199–200`; `desktop/src/scribe_desktop/past_sessions.py:810–815,1696–1700,1707–1715,2115–2124`.
- Defect: The repair contract explicitly checks staging links but then reads, hashes and replaces through the final entry path without requiring its link state. A final-entry junction targeting matching ciphertext can therefore reach the new direct replacement path, bypassing the refusals used by enumeration, committed lookup and ordinary publication.
- Concrete amendment: “Before local classification and again immediately before repair publication, require the final entry directory to be positively identified as an ordinary, inspectable directory. Refuse symlinks, junctions and unknown link state without reading or modifying their targets; omission from archive enumeration does not establish absence.”
- Pattern to follow: `_committed` and `_remove_key_first` refuse linked final directories.
- Pattern siblings: Restore classification, repair publication and absent-entry admission.
- Invariant: Restore never repairs custody through a linked or uninspectable entry directory.
- Verification: A synthetic final-entry junction with matching target ciphertext is refused, with the target byte-identical afterward; unknown link state also refuses.
- Regression risk: Preserve the legitimate fresh-store add path through an explicit confirmed-absence check.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Tasks 3.1 and 3.2, Validation (the entry folder's `link_state` is read before anything under it: `None` → `skipped_uninspectable`, `True` → `skipped_linked`, confirmed absent → `add`; `repair_entry_key` refuses unless `False` immediately before its work)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-026 — Repair does not verify that the recovered key opens the matching content**

- Materiality: build-affecting
- Lens: Missing verification / rollback / migration.
- Plan: D5, Tasks 1.3 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:111,186,200`; `desktop/src/scribe_desktop/past_sessions.py:755–800`.
- Defect: Open verifies hashes and unwraps the audit key or one entry key; repair then verifies its new DPAPI wrap without authenticating the entry content using that recovered key. An authenticated but internally inconsistent backup can associate the wrong key with matching ciphertext and produce a reported successful repair that remains unreadable.
- Concrete amendment: “Before publishing a repaired key, use that proposed key to authenticate the label and all expected content through the existing readers, including their session and content bindings. Only then replace canonical custody; any failure preserves the old key and reports `failed_repair`.”
- Pattern to follow: New-entry restore and `_verify_staged` verify content through the key read back from custody.
- Pattern siblings: New-entry verification already covers this requirement; repair needs equivalent coverage.
- Invariant: A successful repair produces an entry the ordinary readers can open.
- Verification: Use synthetic, authenticated backup metadata with an incorrect entry-key association; repair must fail without changing canonical custody or content.
- Regression risk: Verify text content only; excluded recording content must not become a backup-verification dependency.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D5, C5, Task 3.2, Validation (the key read back from staging must open the final entry's content through `_verify_restored`'s reader pass — label, transcript, note, generated — before the `os.replace`; a failure keeps the old key, `failed_repair`)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-027 — The ZIP member cap rejects valid entries-only backups**

- Materiality: build-affecting
- Lens: Coverage; practicality / feasibility / sequencing.
- Plan: D1, D11, Tasks 1.3 and 1.4.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:107,117,186–187`; `desktop/src/scribe_desktop/past_sessions.py:21–27,734–743`.
- Defect: D11 budgets four ZIP members per entry, but a full entry contributes five: its wrapped key plus label, transcript, saved note and generated note. An explicitly supported entries-only backup with three full entries contains 17 members against the specified cap of 16, so mandatory self-verification rejects valid writer output.
- Concrete amendment: “Derive the member-count bound from the admitted grammar: at most five members per entry, one per audit row, plus the header, manifest and optional audit key. Also impose an independent absolute preauthentication member cap, with writer limits matching the reader.”
- Pattern to follow: Bounds must admit every supported inclusion combination while remaining finite before authentication.
- Pattern siblings: Entries-only, audit-only and mixed backups; writer self-verification.
- Verification: Round-trip an entries-only backup containing several entries with both optional note files; cover audit-only and mixed boundary cases.
- Regression risk: Do not replace the incorrect formula with an unbounded header-controlled limit.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D11, C8, Tasks 1.3 and 1.4, Validation (the member bound is `5 × entry_count + row_count + 3` AND `MAX_MEMBERS = 65_535`; the writer refuses `too_many_members` by the same limit; a 17-member entries-only file round-trips in the tests)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-028 — The manifest’s “every member” rule requires a self-hash**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; simpler / safer alternatives.
- Plan: D2, D11, Task 1.3.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:108,117,186`.
- Defect: The manifest must list every ZIP member with its hash, while `manifest.enc` is itself a ZIP member and unlisted members are refused. Taken literally, this requires the encrypted manifest to contain its own final ciphertext hash, making the specified writer and verifier contract circular.
- Concrete amendment: “Define `header.json` and `manifest.enc` as the two envelope members outside the manifest’s hashed payload list. Authenticate the exact header bytes through manifest AAD and the manifest through AEAD; require the ZIP member set to equal those two envelope members plus exactly the manifest-listed payload members.”
- Pattern to follow: D2 already provides independent authentication for both envelope components.
- Pattern siblings: Manifest construction, exact-member verification, duplicate detection and member-count calculations.
- Verification: Assert successful construction without a self-hash, exact envelope-plus-payload membership, and rejection of extra or duplicate envelope members.
- Regression risk: Exempting envelope members from payload hashing must not exempt them from bounds, uniqueness or authentication.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D2, D11, C8, Task 1.3, Validation (`header.json` and `manifest.enc` are envelope members outside the manifest's payload list, authenticated by the AAD binding and the AEAD tag; the member set must equal envelope plus payload; the manifest refuses the envelope names)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-029 — Provenance recovery’s bare-row predicate omits backup history**

- Materiality: build-affecting
- Lens: Coverage; missing verification / migration.
- Plan: D6, D7, Tasks 1.2 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:112–113,185,200`; `desktop/src/scribe_desktop/audit.py:363–368,1143–1188`.
- Defect: A `pre_audit` row satisfying the explicit bare predicate can acquire `backup.last_backed_up_at` through a successful backup and still satisfy that predicate. Restoring an older recorded row then regresses that local timestamp to the older file’s date, or erases it on a row-only import.
- Concrete amendment: “The bare-row predicate additionally requires an empty `BackupRecord`. Local backup or restoration evidence makes the row `conflict_row` and leaves it unchanged, unless a separately specified merge preserves that evidence without inventing history.”
- Pattern to follow: The amended rule preserves later local recording facts instead of silently replacing them.
- Pattern siblings: `last_backed_up_at`, `restored_at`, entry-included provenance recovery and row-only provenance recovery.
- Invariant: Recovering provenance must not erase later local operational evidence.
- Verification: Back up an eligible sparse row at a later date, then restore an older recorded source, both with and without its entry. The later coverage survives or the local row remains byte-identical with `conflict_row`.
- Regression risk: Continue recovering provenance for genuinely bare rows.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, Task 1.2, Validation (the `backup` record is not part of BARE but is never regressed: on provenance recovery `last_backed_up_at` and `restored_at` are each the later of the local value and the incoming one — the one specified merge)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

#### Lens coverage

- Coverage: PR-MED-027 and PR-MED-029.
- Practicality / feasibility / sequencing: PR-HIGH-024, PR-MED-027 and PR-MED-028.
- Unstated assumptions: PR-MED-025.
- Simpler / safer alternatives: explicit envelope-versus-payload membership in PR-MED-028; reuse of existing custody and reader checks in PR-HIGH-024 and PR-MED-026.
- Missing verification / rollback / migration: PR-HIGH-024, PR-MED-026 and PR-MED-029, with the verification amendments above.
- No additional finding established for Phase 0/Phase 1 sequencing, the historical schema/CSV amendments, C1’s agent-exposure boundary or D10’s practice-document amendment scope. The frozen-build KDF probe remains required before release.

### Round 4 - 2026-10-09 - past-sessions-backup plan, independent cross-family codex plan peer-review (round 4)
Recorded by: the orchestrating session (composer-recorded round — the peer ran in a read-only sandbox and printed the block; transcribed verbatim from `.cursor/loops/past-sessions-backup-peer-r4.log`)  
Source: plan peer-review  
Peer: codex gpt-6-astra medium, read-only sandbox  
Scope: as above  
Round 3 PR-HIGH-024: landed — synchronous cleanup, temporary-key custody and staging-first committed deletion are specified.  
Round 3 PR-MED-025: landed — final-entry link classification precedes reads and is rechecked for repair.  
Round 3 PR-MED-026: landed — the recovered key must authenticate the entry content before publication.  
Round 3 PR-MED-027: landed — the corrected grammar bound and absolute member cap cover the supported inclusion combinations.  
Round 3 PR-MED-028: landed — envelope members are excluded from payload hashing and included in exact membership and duplicate checks.  
Round 3 PR-MED-029: partial — later local timestamps survive provenance recovery, but incoming row-only history can still be lost.  
Materiality summary: 3 build-affecting; 1 record-only; 0 invalid  
Severity summary: 0 CRIT; 0 HIGH; 3 MED; 1 LOW  
Round status: Closed — 4 verified, 4 applied as plan amendments 2026-10-09 (0 rejected; 1 record-only)  
Verification: 10 candidates considered; 6 dropped; 0 downgraded; 4 retained after evidence checks.  
Validation performed: static inspection only; no writes, test suites, builds, payload execution or application-data access.

#### Findings

**PR-MED-030 — Timestamp preservation omits incoming coverage and sibling writers**

- Materiality: build-affecting
- Lens: Coverage; missing verification / migration.
- Plan: D6, D7, Task 1.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:112,113,185,841`; `desktop/src/scribe_desktop/audit.py:363–368,1147,1170–1188`.
- Defect: For row-only provenance recovery, D6’s explicit merge considers the local coverage timestamp but omits the incoming row’s existing coverage, contradicting both its row-only preservation rule and Round 3’s fix notes. The ordinary `record_backed_up` and `record_restored` assignments also lack the monotonic rule needed to preserve timestamps after a clock correction.
- Concrete amendment: “Treat None as absent. Incoming coverage is the latest of the incoming row’s existing `last_backed_up_at` and, only when included, the file’s `made_at`. Provenance recovery preserves the latest local and incoming coverage; `restored_at` preserves the latest local value, incoming value and `now`. Ordinary `record_backed_up` and `record_restored` also retain the latest existing or event timestamp.”
- Pattern to follow: Preserve operational evidence when recovering provenance; `AuditLog.update` applies the supplied change and does not supply monotonicity itself.
- Pattern siblings: Provenance recovery with and without entry inclusion; ordinary backup accounting; ordinary restoration accounting.
- Invariant: Importing older or incomplete evidence never erases a later known backup or restoration timestamp.
- Verification: A bare local row has coverage at t1; an incoming recorded row has coverage at t2 > t1, but its entry was omitted from this file. Row-only provenance recovery must retain t2. Cover the reverse ordering, None values and ordinary updates after a backward clock change.
- Regression risk: Row-only inclusion must not acquire the current file’s `made_at` as new entry coverage.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, D7, Task 1.2, Validation (every `backup` timestamp is set monotonically with None as absent: `restore_row` takes the latest of the incoming row's own value and — only when `included` — `made_at`, and of the incoming value and `now`; provenance recovery takes the latest of local, incoming and those; `record_backed_up` / `record_restored` take the later of the existing value and the event's time; the row-only t1/t2 cases and the backward-clock case are in the tests)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-031 — Audit snapshot materializes the payload before the bounded worker flow**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; simpler / safer alternatives.
- Plan: Integration Notes, D6, C12, Task 1.4.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:79,112,150,187`; `desktop/src/scribe_desktop/audit.py:972–995,1198–1199`.
- Defect: D6 explicitly returns a list containing every audit row’s ciphertext bytes from the GUI-thread snapshot, while the integration contract promises row paths and worker-side reads without loading the whole archive. Following that API accumulates the audit payload before the writer’s limits apply and can stall or exhaust the GUI process.
- Concrete amendment: “`backup_snapshot` returns the audit key material for immediate wrapping and bounded, validated row descriptors `(month, id, path, size)`, rather than accumulated ciphertext bytes. The worker reads each row under `MAX_ROW_FILE_BYTES`, copies and verifies it, then releases its buffer; descriptor enumeration enforces the applicable count and size limits.”
- Pattern to follow: The existing audit reader caps individual reads; the plan already selects path-based worker I/O.
- Pattern siblings: D6’s return type, hop B’s snapshot, hop C’s input and Task 1.4’s acceptance tests.
- Invariant: GUI snapshotting does not accumulate the complete audit ciphertext payload.
- Verification: A fake snapshot refuses payload reads during GUI enumeration; a many-row test verifies bounded worker reads and release of each row buffer.
- Regression risk: Preserve GUI-thread ownership of store classification and key custody, including key zeroing and entries-only fallback.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, Tasks 1.2 and 1.4, Validation (`backup_snapshot() -> (key_bytes, [RowDescriptor(month, session_id, path, size)])` — validated descriptors, never ciphertext; hop B wraps and zeroes the key at once; hop C reads each row through `read_capped(path, MAX_ROW_FILE_BYTES)` one buffer at a time, `skipped_gone` for a vanished or over-size row; a GUI-thread row read fails the test)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-MED-032 — The isolated practitioner smoke also removes its required models**

- Materiality: build-affecting
- Lens: Unstated assumptions; missing verification / rollback.
- Plan: D12, Validation / Verification, Task P.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:118,157,217`; `AGENTS.md:44`.
- Defect: P.2 renames the entire developer data root aside and then immediately requires recording and completing synthetic consultations. The documented model directory is inside that root, so the fresh folder lacks the local transcription models needed to perform the smoke.
- Concrete amendment: “With both apps closed, set aside the original developer data root, create the isolated smoke root and provision only the required non-clinical model assets there before launch. The practitioner performs this preparation and verifies model readiness; no original sessions, archive, profile or settings are copied. Teardown removes only the scratch root and restores the original root.”
- Pattern to follow: Preserve C1’s isolation while explicitly provisioning the dependencies required by the verification procedure.
- Pattern siblings: D12’s smoke description, the manual-check summary and P.2’s setup and teardown.
- Invariant: The isolated smoke is executable without exposing or modifying existing clinical data.
- Verification: P.2 records model readiness before the two synthetic recordings and confirms restoration of the original developer folder afterward.
- Regression risk: Keep preparation practitioner-run; never solve the missing-model problem by reopening the original clinical data root.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D12, Validation (manual checks), Task P.2 (the fresh `ClinikoScribe-dev` holds ONLY the `models` folder moved over from the set-aside root; readiness confirmed before recording; the models moved back and the original root restored at teardown; every step the practitioner's own, never an agent shell)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-LOW-033 — Scope and schema still describe whole-entry replacement**

- Materiality: record-only
- Lens: Coverage.
- Plan: Agreed Scope; Schema / Data Changes.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:32,111,126,200`.
- Defect: Agreed Scope still describes replacing an unreadable entry key-first, and the schema table says a “RESTORED or REPLACED” entry never contains recording sidecars. D5 and Task 3.2 instead specify key-only repair that preserves existing sidecars.
- Concrete amendment: “Restore adds absent entries or repairs only an existing entry’s DPAPI key after matching and authenticating its content. Distinguish newly added entries, which contain no recording sidecars, from repaired existing entries, whose other files—including recording sidecars—remain unchanged.”
- Pattern to follow: The detailed D5 and Task 3.2 contract.
- Pattern siblings: Agreed Scope’s replacement sentence and the archive schema row.
- Verification: Both summaries agree with the key-only repair contract; no implementation or test change.
- Regression risk: None.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Agreed Scope, Schema / Data Changes (Restore ADDS absent entries or REPAIRS only an existing entry's key after matching and opening its content; the schema table now has one row for a newly added entry — no recording sidecars — and one for a repaired entry whose other files, sidecars included, are untouched)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

#### Lens coverage

- Coverage: PR-MED-030 and PR-LOW-033.
- Practicality / feasibility / sequencing: PR-MED-031; no additional finding in Phase 0 / Phase 1 sequencing.
- Unstated assumptions: PR-MED-032.
- Simpler / safer alternatives: PR-MED-031 resolves the snapshot contradiction using the already-selected path-based flow; no separate alternative retained.
- Missing verification / rollback / migration: PR-MED-030 and PR-MED-032, with the verification amendments above.
- No additional verified finding in the scoped custody destroyers, repaired-key verification, link refusals, container membership amendments, schema migration pins, C1’s agent-exposure boundary or D10’s document-amendment scope. The frozen-build KDF probe remains required before release.

### Round 5 - 2026-10-09 - past-sessions-backup plan, independent cross-family codex plan peer-review (round 5)
Recorded by: the orchestrating session (composer-recorded round — the peer ran in a read-only sandbox and printed the block; transcribed verbatim from `.cursor/loops/past-sessions-backup-peer-r5.log`)  
Source: plan peer-review  
Peer: codex gpt-6-astra medium, read-only sandbox  
Scope: as above  
Round 4 PR-MED-030: landed — incoming, local and event timestamps are preserved monotonically, including row-only imports.  
Round 4 PR-MED-031: landed — the audit snapshot returns descriptors; bounded payload reads belong to the worker.  
Round 4 PR-MED-032: landed — P.2 provisions the isolated root with models and restores them at teardown.  
Round 4 PR-LOW-033: landed — Agreed Scope and the schema distinguish added entries from key-only repairs.  
Materiality summary: 1 build-affecting; 1 record-only; 0 invalid  
Severity summary: 0 CRIT; 0 HIGH; 1 MED; 1 LOW  
Round status: Closed — 2 verified, 2 applied as plan amendments 2026-10-09 (0 rejected; 1 record-only)  
Verification: 9 candidates considered; 7 dropped; 0 downgraded; 2 retained after evidence checks.  
Validation performed: static inspection only; no writes, test suites, builds, payload execution or application-data access.

#### Findings

**PR-MED-034 — The restorer task places entry-success accounting before entry publication**

- Materiality: build-affecting
- Lens: Practicality / feasibility / sequencing; missing verification.
- Plan: D6; Task 3.2; Validation / Verification.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:112,157,201`; `desktop/src/scribe_desktop/audit.py:569–573,1170–1188`.
- Defect: Task 3.2 places `record_restored` inside “audit rows first” before “then entries”, whereas D6 conditions that update on the local row’s entry having been restored. Following the task’s ordering can stamp `restored_at` and change `none` to `archived` before an add or repair subsequently fails.
- Concrete amendment: “Import backed-up audit rows first. For a kept local row, call `record_restored` only after its entry has successfully published or its verified replacement key has committed. A skipped entry or a failure before that commit leaves the kept row’s restoration timestamp and archive state unchanged. Imported-row provenance remains governed separately by `restore_row`.”
- Pattern to follow: Record an operation’s success after its commit, as backup accounting already follows successful file publication.
- Pattern siblings: Added-entry publication and existing-entry key repair; distinguish both from successful audit-row import.
- Invariant: An attempted entry restore must not become an audit fact of successful entry restoration.
- Verification: With an existing local row, inject add-verification, publication and pre-commit repair failures; assert unchanged `restored_at` and `past_session`. Successful add and repair perform the monotonic update after commitment.
- Regression risk: Preserve audit-first tombstone import and legitimate row-only restoration accounting; do not roll back a committed repair because later cleanup fails.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: D6, Task 3.2, Validation (`record_restored(id)` for a KEPT local row moves out of the audit-first clause: it is called only after that entry's `_publish` or its repair's `os.replace` has returned; a skipped entry or any failure before the commit leaves `restored_at` and `past_session` untouched; an imported row's provenance stays `restore_row`'s; the failure-order tests named)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

**PR-LOW-035 — Remaining summaries contradict the settled execution and recovery contracts**

- Materiality: record-only
- Lens: Coverage; practicality / feasibility / sequencing.
- Plan: Integration Notes; Flow 4; D5; Tasks 2.2 and 3.2.
- Evidence: `.cursor/plans/plan-past-sessions-backup.md:79,81,103,111,151,195,201`; `desktop/src/scribe_desktop/past_sessions.py:1536–1546`; `desktop/src/scribe_desktop/ui/past_sessions.py:236–237,990–1004`; `desktop/src/scribe_desktop/session_store.py:567–586`.
- Defect: The summaries still describe a sweep between guarded hops, equate audit retention with archive retention, and promise preservation of the old key after failure “at any step”, including after replacement has committed. Flow 4 and Task 2.2 also locate audit Reset on Status, although the existing control belongs to Past sessions.
- Concrete amendment: “Remove the between-hop sweep example: ticks are suppressed throughout the run, while independently unavailable source files remain `skipped_gone`. State that audit retention is seven years while archive retention may be indefinite. Failures before successful key replacement preserve the old key; after replacement the verified new key remains committed, with cleanup failures reported under the existing rule. Refer to Past sessions → Start a new audit record wherever the existing Reset control is named.”
- Pattern to follow: The detailed C12 run guard, D5 retention and repair transaction, and the existing `PastSessionsScreen` control.
- Pattern siblings: Integration Notes’ threading and retention summaries; D5 and Task 3.2’s failure wording; Flow 4 and Task 2.2’s Reset location.
- Verification: Reconcile these sentences against the existing detailed contracts and control location; no additional implementation or test gate.
- Regression risk: Do not introduce post-commit key rollback, change retention, or move the Reset control.
- Triage: Include in plan
- Fix route: premium-only
- /fix decision: Applied as a plan amendment
- /fix notes: Integration Notes (the between-hop tick example removed — ticks are skipped throughout, `skipped_gone` is an independently unavailable source; audit months 7 years vs the archive's 7 years or indefinite), D5 and Task 3.2 (the old key is preserved for a failure BEFORE the `os.replace`; after it the verified new key stays committed and a cleanup failure is reported, never rolled back), Flow 4 and Task 2.2 (the audit Reset is the Past sessions tab's own "Start a new audit record", `reset_audit_button` — not a Status-tab control)
- /fix date: 2026-10-09
- /fix applied by: the orchestrating session (Fable 5.1), verified against the code first

#### Lens coverage

- Coverage: PR-LOW-035; no additional scope gap verified.
- Practicality / feasibility / sequencing: PR-MED-034 and PR-LOW-035; no new Phase 0 / Phase 1 sequencing finding.
- Unstated assumptions: no new finding verified; P.2’s model prerequisite is addressed.
- Simpler / safer alternatives: no separate material alternative verified.
- Missing verification / rollback / migration: PR-MED-034’s failure-order tests; no additional migration or rollback finding.
- No new build-affecting finding verified in custody cleanup, key authentication, link refusals, GUI snapshot boundaries, schema/CSV migration, C1 or D10. The frozen-build KDF confirmation remains required before release.

### Round 6 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (reconciliation pass, round 1)

Source: Codex gpt-6.2-astra high plan peer-review

`plan` below means `.cursor/plans/plan-past-sessions-backup.md`. Desktop source paths are relative to `desktop/src/scribe_desktop/`.

**PR-HIGH-036 — A backup changes what it takes to destroy a kept recording.**
Materiality: build-affecting
D2 backs up the same entry key that protects `audio-key.enc`. Delete now and expiry currently count deletion as successful once the local entry key is gone. Removing the audio key and the remaining directory is best-effort. If a lock or crash leaves both audio sidecars, an earlier backup still supplies the key that opens them. This affects the recording even though neither sidecar enters the backup. `plan:117,120,214`; `past_sessions.py:1058–1077,1788–1796,2115–2136`; `docs/security/retention-schedule.md:140`.
Amendment: Require verified destruction of a surviving wrapped audio key before reporting whole-entry deletion as successful, test interrupted and locked-sidecar cases, and document the limitation on rollback to a build with the old deletion path.

**PR-HIGH-037 — Restore’s add operation calls a destructive publisher.**
Materiality: build-affecting
Task 3.2 checks that the destination is absent, stages and verifies the entry, then calls `_publish`. That method deliberately removes the destination key-first before renaming. A directory that appears during verification can therefore be destroyed by an operation promised only to add missing entries. `plan:120,153,214`; `past_sessions.py:810–815`.
Amendment: Give restore a no-overwrite directory rename and test that a destination introduced after staging retains its key and every byte.

**PR-HIGH-038 — The writer can copy bytes from outside the archive into a readable ZIP member.**
Materiality: build-affecting
Task 1.4 reads entry members by path and stores their bytes verbatim. `_committed_dirs` checks the entry directory for links, while the member read follows the filename. Audit enumeration and `read_capped` likewise follow the leaf. Hashing the bytes after reading them establishes what was copied, not that they came from the intended encrypted file. `plan:116,126,201`; `past_sessions.py:1696–1705`; `audit.py:1222–1231`; `session_store.py:1000–1008`.
Amendment: Require each copied member to be an ordinary file belonging to the checked directory, bind the check to the opened file, and verify with synthetic linked and replaced members that outside bytes never enter the ZIP.

**PR-HIGH-039 — An open recovered transcript can still Complete or Discard during backup.**
Materiality: build-affecting
Recovery removes its protected checkout from both visible lists. After Resume succeeds, the worker stops but the checkout remains protected. `_live_session_ids()` does not include that checkout, and its Review buttons still call `complete_recovered` and `discard_recovered`, which write the archive or audit. A run admitted from the two sources named by D8 can therefore overlap a real writer during hop A or C. `plan:123,160,208,215`; `ui/recovery.py:196–217,322–325,395–402`; `ui/main_window.py:1548–1561,1756–1785`; `session.py:1850–1855,1874–1896`.
Amendment: Wire the shared admission check in Task 2.2, include protected checkouts and both recovery lists alongside controller reservations, and test both backup actions while a recovered transcript awaits Complete or Discard.

**PR-HIGH-040 — A recording can start between admission and the first worker.**
Materiality: build-affecting
Both flows open dialogs before acquiring the run flag. A Chrome Start delivered during a passphrase or confirmation dialog can succeed. Backup rechecks at hop B, after derivation has already started, and Open specifies its next check after the summary. Both violate C12 before the later check can help. `plan:103,106,160,208,215`; `ui/bridge.py:1055–1107`.
Amendment: On the GUI thread, recheck the complete busy state and acquire the flag without yielding before starting either worker, and test a dialog that admits a session before returning.

**PR-HIGH-041 — The specified worker interfaces cannot transfer the key under C3.**
Materiality: build-affecting
`prepare_backup(store, audit, *, now, channel)` must wrap keys but receives no `K_b`. The writer receives `K_b` but must call `open_backup(path, passphrase)` to verify its output. Returning the derived key from hop A through `TaskThread` would put it in `succeeded`, and an uncaught worker exception puts its message in `failed`. `SessionCrypto.export_key()` also returns immutable `bytes`, which the promised cleanup cannot zero. `plan:118,151,200–201,207–208`; `ui/tasks.py:24–25,36–42`; `secure_storage.py:87–97`.
Amendment: Specify run-owned key storage, pass the derived key explicitly to wrapping and verification, emit only completion or closed error codes, and distinguish wipeable buffers from immutable copies in the cleanup tests and threat model.

**PR-HIGH-042 — Open reads a file before checking whether it is local.**
Materiality: build-affecting
Flow 2 goes straight from the selected path to a header read. Opening a UNC or mapped-network file can initiate SMB traffic, and opening an online-only cloud file can hydrate it. This happens before a wrong passphrase, damaged header or Close can end the operation. The repository already has a test seam for detecting network-path I/O. `plan:18,93,106,119,215`; `exclusions.py:426–450`; `desktop/tests/conftest.py:550–575`.
Amendment: Admit the selected source before reading its header, keep verification and restore bound to the admitted file, and test that refused sources receive no file reads.

**PR-HIGH-043 — A partial archive can pass the backup-success checks.**
Materiality: build-affecting
Task 1.4 names `_committed_dirs` without its strict option. An unlistable archive then looks empty and a healthy audit store can produce an apparently successful audit-only backup. The same task skips a *member* that disappears mid-copy, without specifying how to remove the rest of that entry from an already-started ZIP or prevent its ID being credited. The existing store uses strict enumeration when an unreadable archive must be distinguished from an empty one. `plan:103,116,200–201`; `past_sessions.py:927–940,1684–1705`.
Amendment: Use strict enumeration and make inclusion atomic per entry, with tests proving that an unreadable root or missing required member cannot yield a successful full-backup claim or entry coverage.

**PR-HIGH-044 — The first clinical backup precedes the plan’s own consent decision.**
Materiality: build-affecting
P.3 backs up all readable entries before P.4 approves the amended documents. D10 itself leaves open whether existing records need fresh consent. The ten consultations use `patient-info-v3`, which explicitly promises no backup. An early merge can also replace the current patient sheet before the tenth consultation even while the installed executable stays at 0.4.2. `plan:125,161,220,232–233`; `docs/practice/patient-information-and-consent.md:75,141,174`; `docs/practice/README.md:54–61`; `docs/testing/shipping-gate.md:110`; `docs/pilot/README.md:150–156`.
Amendment: Keep approved v3 available and current throughout the ten, prepare v4 as a distinct draft including its charting example and signed form, and obtain the practitioner’s disposition for existing v3 records before P.3.

**PR-MED-045 — Failure cleanup can delete someone else’s `.part`.**
Materiality: build-affecting
D11 says to unlink the pathname in `finally` on any failure. Exclusive creation can fail because the partial file already belonged to an earlier run, and a removable drive or its file can be replaced after a successful create. The existing export helper checks file identity through the deletion handle for precisely this reason. `plan:103,126,201`; `past_sessions.py:1277–1282,2008–2021`.
Amendment: Clean up only a file exclusively created by this run whose identity still matches, and test preservation of both a pre-existing partial and a replacement.

**PR-MED-046 — Sparse audit-row recovery can create two rows for one ID.**
Materiality: build-affecting
D6 permits replacement by ID, then requires writing in the incoming manifest month. A local `pre_audit` row can legitimately occupy another month because an unavailable creation date falls back to the current date. Writing the recovered row into its original month leaves both files, after which reads and updates refuse that ID. Also, `_MONTH_RE` alone accepts month values that `month_prune_at` cannot use. `plan:121,199,213`; `audit.py:128,465–472,822–828,1011–1014,1042–1051,1149–1169`.
Amendment: Classify a different-month sparse row as `conflict_row`, validate the calendar month and pruning date before mutation, and test that retry leaves exactly one readable row.

**PR-MED-047 — `update(create=False)` can create a key and cannot report an absent row.**
Materiality: build-affecting
D7 requires counting `rows_absent` while C4 forbids backup from modifying custody. At HEAD, `_update` calls `_open_key()` with creation enabled before checking for a row. On an empty audit store it can create the directory and DPAPI key, then return success for an absent row. That success is indistinguishable from an actual update to the caller. `plan:122,152,199`; `audit.py:825–836,1147–1160,1245–1268`.
Amendment: Give backup accounting a non-creating existing-row operation with an explicit absent outcome, and test an archive with entries and no audit store for both the count and unchanged filesystem.

**PR-MED-048 — A successfully restored entry can still be reported as never backed up.**
Materiality: build-affecting
When the local audit row already exists, Task 3.2 updates `restored_at` after publishing the entry but leaves an empty `last_backed_up_at` untouched. D7 then counts the restored entry as uncovered despite having just read it from a verified backup. This can recur on every refresh. `plan:121–122,140,214`.
Amendment: After successful publication or repair against a kept readable row, advance coverage monotonically using the verified backup’s `made_at`, and test the same row on both failed and successful publication.

**PR-MED-049 — The audit migration pin inventory still misses failing tests.**
Materiality: build-affecting
The four cited assertions exist, but two more expect version 3 at `desktop/tests/test_audit.py:940–943,994–997`. The same file uses version 4 as *future* input at lines 487, 762, 766–767, 962 and 1039. The shared future-document helper also injects 4 for audit tests. After the bump these cases exercise malformed current documents instead of `_NEWER`. `plan:65,80,167,199`; `desktop/tests/test_schema_versions.py:202–209,605,663–667`.
Amendment: Inventory decoded, serialized and future-version fixtures by behavior, use v5 for future audit rows while preserving other schemas’ boundaries, and capture the synthetic v3 bytes from the unchanged pre-bump writer at HEAD.

**PR-MED-050 — The prescribed backup filename trips a separate installation test.**
Materiality: build-affecting
A literal `ClinikoScribe-backup-…` in the writer or UI is caught by the package-wide install-layout scan. It matches `clinikoscribe` inside ordinary strings and f-strings, including non-directory names. Conversely, the version test derives its expected value from `pyproject.toml` and needs no literal update. `plan:67,103,144,203,208`; `desktop/tests/test_install_layout.py:468–489,570–575,583–615,907–922`.
Amendment: Give the filename prefix one named owner and account for it in the existing narrow allowlist, while leaving the version-equality test intact.

**PR-MED-051 — The new Start refusal needs an explicit consent-tick outcome.**
Materiality: build-affecting
The warm-up helper deliberately retains the written-development-consent tick. Every other refused Start must clear it and announce the clearing. Chrome’s `_refuse` already does that for `backup_running`, but copying the warm-up branch into direct desktop or linked Start would preserve a tick for a later recording. The validation line checks only the message. `plan:123,170,208`; `ui/session_screen.py:405–418,519–555`; `ui/bridge.py:899–907`; `docs/practice/development-recording-consent.md:145–153`.
Amendment: Specify and test clearing an armed development tick on each backup refusal, with warm-up remaining the sole exception.

**PR-MED-052 — Chrome’s backup-running message can outlive the backup.**
Materiality: build-affecting
`ChromeBridge` retains a refusal while its tab, target, verification and session state match. Completing a backup on an otherwise idle, verified note changes none of those values. The side panel can continue telling the practitioner to wait after the operation has finished. `plan:123,170`; `ui/bridge.py:908–936,1279–1286`; `extension/src/panel-view.ts:310`.
Amendment: Invalidate and republish a `backup_running` refusal when the flag clears, and verify the same Chrome note loses the message without another Start.

**PR-MED-053 — Task 0.7’s probe has no frozen entry point or single owner.**
Materiality: build-affecting
Adding `packaging/spike/kdf_probe.py` does not make the production bundle execute it. The release script builds a fixed spec with two windowed executables, and the existing frozen self-check communicates by exit code. The same task assigns writing the probe to the executor while carrying an `[operator]` marker that the headless executor skips. `plan:55,193,226`; `packaging/scribe.spec:128,147,168,183`; `scripts/build-release.py:814–834`; `app.py:661–685`; `.agents/skills/execute/SKILL.md:38`.
Amendment: Make frozen-probe implementation executor-owned, give the build audit a callable frozen check with observable results, and reserve `[operator]` for the actual practitioner invocation if that route is chosen.

**PR-MED-054 — The Delete now confirmation would give two incompatible instructions.**
Materiality: build-affecting
Task 2.3 appends “A backup made before today” to text that already says the notes and transcript “cannot be recovered”. A backup made earlier the same day also retains them. The clinician guide says deletion is “for good”, and the patient sheet says it “cannot be undone”. Those phrases escape the proposed grep. `plan:103,190,209`; `ui/past_sessions_view.py:183–187`; `docs/practice/clinician-review-guide.md:332–334`; `docs/practice/patient-information-and-consent.md:165–168`.
Amendment: Replace the irreversible-deletion wording at all three sites and apply the fixed destruction rule to every backup made **before this deletion**, including one made today.

**PR-MED-055 — The documentation inventory misses live recovery, custody and CSV claims.**
Materiality: build-affecting
The downtime procedure separately says a DPAPI-broken entry cannot be read again on this account. The data-flow map says the archive is the only disk location and the patient name is written to its label “and nowhere else”. Its audit flow still places the four v3 columns last. Adding flow 30 and editing “Losing the computer” leaves these instructions in force. `plan:71,167,219–220`; `docs/practice/downtime-procedure.md:103–112`; `docs/practice/README.md:93–95`; `docs/security/data-flow-map.md:1192–1195,1761–1771,1968–1973`; `docs/security/threat-model.md:4623–4629`.
Amendment: Add these passages to the acceptance inventory, cross-reference the key-repair procedure at the unreadable-entry message, and reconcile existing custody and CSV descriptions with flow 30.

**PR-MED-056 — The lost-drive disclosure omits metadata readable without the passphrase.**
Materiality: build-affecting
D11 places stable session IDs, audit month folders and content filenames in the ZIP directory. Their presence and sizes are visible independently of the encrypted manifest. Task 4.1 describes the lost drive as ciphertext under the passphrase alone. `plan:126,219`; `session_store.py:178–182`.
Amendment: Keep the agreed ZIP format and document exactly which identifiers, dates, member types and sizes remain visible and which content requires the passphrase.

**PR-MED-057 — P.2 does not create or verify the shadow case it claims.**
Materiality: build-affecting
An **absent** `pilot.json` means shadow off. Only an existing unreadable setting fails closed to shadow on. Mode is fixed at Start, and simply opening two restored entries proves neither their mode nor the reason Copy is disabled. Moving only `past_sessions` aside also leaves both original audit rows present. `plan:127,170,231`; `note_config.py:1227–1239`; `ui/session_screen.py:579–592`; `ui/past_sessions_view.py:772–787`.
Amendment: Turn shadow mode on explicitly in the isolated developer folder before both Starts, save at least one synthetic note, and verify the restored shadow mark, shadow-specific Copy refusal and restoration into an empty synthetic audit store.

**PR-MED-058 — Task 3.2 gives contradictory expected results for verification failures.**
Materiality: build-affecting
D5 requires synchronous key-first cleanup in `finally`, but Task 3.2 expects an ordinary failed read-back to leave a staging key for the next sweep. It also expects a tampered member to fail only its entry, although C8 requires Open to reject a hash mismatch before restore writes anything. These are different failure points with different correct outcomes. `plan:120,156,168,200,214`.
Amendment: Separate tests for whole-file authentication failure, entry-reader failure after authentication, ordinary repair failure with successful cleanup, cleanup failure and process death before cleanup.

**PR-MED-059 — The destination seam cannot establish the promised volume facts as written.**
Materiality: build-affecting
`WindowsLayer` exposes `drive_type(root)` but no volume-identity operation for the `st_dev` comparison. The export implementation also explicitly documents that checking the drive letter reports the containing drive’s type for a volume mounted beneath it. Reusing that result can admit a destination of a type D4 requires the backup to refuse. `plan:92,119,157,202`; `exclusions.py:239–257,493–515`.
Amendment: Add injectable lookup of the resolved destination volume’s identity and type, preserve Export’s existing behavior, and test a mounted volume and an uninspectable volume without examining real drives.

**PR-MED-060 — The rollback instructions overstate compatibility and misdescribe repair failures.**
Materiality: build-affecting
The v4 audit-row behavior holds through 0.4.2. Archive *content* still has older compatibility limits: 0.3.0 can list but cannot open some entries containing 0.3.2-or-later transcript or note marks. Startup repair visits entries holding recordings, skips unreadable labels and pruned months, and attempts two audit writes for each qualifying entry. A normal audio-free restored entry causes neither attempt. `plan:124,131–136,221`; `docs/release/pilot-builds.md:292–301,316–324`; `app.py:487–510`; `audit.py:831–835`.
Amendment: Describe rollback to 0.4.2 directly, retain the cumulative older-content warnings, and state when startup repair can increment the failure count.

**PR-LOW-061 — P.3 asks for a reminder a successful backup normally clears.**
Materiality: build-affecting
The reminder is shown only with uncovered entries and an absent or stale backup. P.3 asks the practitioner to observe it immediately after the first real backup, yet omits the numeric file-size check assigned to P.3 under Accepted Assumptions. `plan:51,123,209,232`.
Amendment: Have P.3 record counts, file size, successful Open/Close and the expected reminder state, with the seven-day reminder exercised on synthetic data.

**PR-LOW-062 — Several “re-verified” source references still point to the wrong evidence.**
Materiality: record-only
The Past sessions UI diff is six added lines and one removed, for a net five, including the saved-note formatting change. Its handlers now start at lines 601, 770 and 977. `_refuse_while_held` starts at 549, with its condition at 551. `AuditLog._find` is at 1233. The deferred promise in `PLAN.md` is at 156. The theme guard checks colors, font weights, stylesheets and named Qt classes/setters, but does not check every numeric size or spacing literal. `plan:63–69,73,77,82,123`; `ui/past_sessions.py:592–595,601,770,977`; `ui/session_screen.py:549–551`; `audit.py:1233`; `desktop/tests/test_ui_theme.py:399–442`; `PLAN.md:156`.
Amendment: Correct the source inventory and distinguish the visual properties covered by static tests from dimensions covered by layout tests or review.

**Spot-checked cites and results**

- **Repository and line shifts.** HEAD was `5d63ed6`. The reconciled plan was the sole working-tree change. `git diff aeec75e HEAD` confirmed the listed unchanged storage, exclusions, sample-note, task-thread, schema-test and requirements files. `audit.py` and `test_audit.py` have substitutions without line shifts. The six corrected `session_store.py` anchors are 171, 577, 618, 641, 677 and 1000. `install_layout.channel` is at 107. The log-signature additions total 28 lines.
- **Start and Chrome.** `app.py:847` supplies `warmup.holds_start`, `ui/main_window.py:593` installs it on `SessionScreen`, and the bridge queries that screen. A second callable can be wired after the Past sessions page is constructed at `ui/main_window.py:760`. Desktop protocol reasons are pattern-constrained strings. The extension accepts the reason and displays the desktop-authored message. `getting_ready` has no fixture or extension-source match. No new protocol fixture or extension logic is needed for `backup_running`; the release still rebuilds the extension for its version. `protocol.py:130,325–328`; `extension/src/protocol.ts:196,486–490`; `extension/src/panel-view.ts:310`; `extension/src/panel.ts:198–201`.
- **Other activity and close.** Hotkey and resume paths require an existing session. Voice enrolment uses `_enrolment_blocker`; the benchmark and level monitor have separate entry points and do not write this archive or audit. The generic close guard enumerates screens and omits Past sessions. Put the run check before `note_screen.prepare_close()` so a refused close has no suggestion-job side effect. Test an actual close during a worker or nested summary dialog. A close queued during synchronous GUI-thread restore normally runs after control returns to Qt. `ui/main_window.py:908–921,1482–1495,1563–1644`; `ui/bridge.py:638–660`; `ui/microphone.py:273–300,357–387`.
- **Sweep and custody.** `recover_exports` runs before the startup sweep. Staging cleanup, session expiry, pending reconciliation, kept/deleted recording facts and tidy run through `app.py:449–464,823–826`. Guarding `PeriodicSweep.__call__` before its three steps covers the periodic writers, while retention changes have their own direct sweep. Trim, suggestion processing and live Chrome Discard do not provide a second idle archive writer. The concrete exception is the protected recovered checkout in PR-HIGH-039.
- **Shadow and test boundaries.** A non-mock shadow Complete writes an ordinary entry with a v2 `label.shadow`. V1 labels default to normal. Copy reads the opened label and checks again at click time. A mock Complete leaves no archive entry but does retain its content-free audit record. No shadow pin counts encrypted note-member copies. The two-tab widget scan excludes `ui/backup_dialog.py`; package-wide selectable-text, clipboard, drag, item-view and plaintext-audio pins still apply. Password echo has an existing precedent, but the static pins do not establish how Copy and Cut behave in a new dialog. A clipboard-sentinel UI check should verify that neither exports the passphrase. `session.py:232–242`; `session_store.py:1427–1439`; `past_sessions.py:336–380`; `ui/past_sessions.py:566–595`; `ui/clinics.py:102–103`; `desktop/tests/test_shadow_exits.py:163–168,207–250,276,516,555,896`.
- **Fixtures and CSV consumers.** The channel, model roots, pilot settings, real Windows layer, exception hooks, blind-set admission and theme have existing fixtures. They permit synthetic worker tests, a reduced test KDF and the named temporary-directory DPAPI tests. CI uses the held-out lint runner. I found positional suffix assertions in `test_audit.py`, and no replay, measurement or pilot-document code that consumes the audit CSV by a fixed column count. `desktop/tests/conftest.py:135–172,272–350,489–505`; `.github/workflows/ci.yml:82`; `desktop/tests/test_audit.py:1195–1219,1338–1352`; `desktop/tests/test_schema_versions.py:641–645`.
- **Release and documents.** The five version files contain six product-version values. `Release` dispatches only on `refs/heads/main`. The loop can hand open `[operator]` tasks back after merge, so H5 has a feasible ordering. A CI build alone cannot add `backup.json` to the installed configuration. The after-fingerprints belong after the tenth eligible score and before P.1. An early release does change which build clinic 2’s “current build of record” instruction names. Flow 29 is the highest numbered flow, flow 30 is free, `patient-info-v4` is next, and “Rolling back below 0.4.2” is the correct insertion point. `desktop/tests/test_install_layout.py:907–922`; `.github/workflows/release.yml:24,36`; `.agents/skills/execute-loop/references/s21-termination.md:10`; `docs/testing/shipping-gate.md:110,119–120`; `docs/pilot/exit-gate.md:95–105`; `docs/security/data-flow-map.md:1681`; `docs/release/pilot-builds.md:71`; `docs/practice/README.md:54–61`.

Materiality: 26 build-affecting / 1 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block as its final message; transcribed unchanged from `.cursor/loops/past-sessions-backup-plan-peer-r6.log`, last `### Round 6` header). Peer round 1 of this pass (cap 5). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 6 (2026-11-25, the orchestrating session on Fable 5.2; each finding verified against the code at `5d63ed6` before any amendment)

Verified materiality: 26 build-affecting / 1 record-only / 0 invalid (as labelled). Every finding: Triage Include in plan; /fix decision Applied as a plan amendment; landed and siblings reconciled as listed.

- PR-HIGH-036 — verified (`_remove_key_first` unlinks `audio-key.enc` best-effort after the entry key; `delete_entry` reports success on the entry key alone). The practitioner: "Add it to the plan (Recommended)". Landed: D13 (a), new Task 1.7, D5 and D9 pointers, Task 4.1, Task 4.3.
- PR-HIGH-037 — verified (`_publish` removes `final` key-first, `past_sessions.py` L810–815). Landed: D13 (b), D5 pointer, Task 3.2.
- PR-HIGH-038 — verified (`_entry_dirs` refuses a linked folder, not a linked member). Landed: D13 (c), Task 1.4.
- PR-HIGH-039 — verified (`_on_recovered` leaves the id in `_protected`, which the lists exclude; the Review buttons call `complete_recovered` / `discard_recovered`). Landed: D13 (e), D8 and C12 pointers, Task 2.2.
- PR-HIGH-040 — verified against the plan's own order (dialogs before the flag). Landed: D13 (e), Tasks 2.2 and 3.3.
- PR-HIGH-041 — verified (`prepare_backup`'s signature had no key; `TaskThread.failed` emits `type: message`; `export_key()` returns `bytes`). Landed: D13 (f), D3 pointer, Tasks 1.3, 1.4, 2.2, 3.3, 4.1.
- PR-HIGH-042 — verified against Flow 2. Landed: D13 (g), D4 pointer, Flow 2, Tasks 1.3 and 3.3.
- PR-HIGH-043 — verified (`_committed_dirs` is non-strict by default; `list_entries` passes `strict=True`). Landed: D13 (d), Task 1.4.
- PR-HIGH-044 — verified (`patient-info-v3` says the program makes no backup; P.3 came before P.4). The practitioner: "Before the first real backup (Recommended)". Landed: D13 (z), C13 (the merge hold required), new Task P.4b, P.3's order, Task 4.2.
- PR-MED-045 — verified against D11's wording and Export's `_remove_part`. Landed: D13 (h), D11 pointer, Task 1.4.
- PR-MED-046 — verified (`_MONTH_RE` is four digits, a hyphen, two digits; a `pre_audit` row is dated by now when its creation date is missing). Landed: D13 (i), D6 pointer, Tasks 1.2 and 3.1.
- PR-MED-047 — verified (`_update` calls `_open_key()` with creation enabled before `_find`; `elif not create: return`). Landed: D13 (j), D7 pointer, Task 1.2.
- PR-MED-048 — verified against D6 / D7. Landed: D13 (k), Task 3.2.
- PR-MED-049 — verified (the listed lines; `_newer` writes version 4). Landed: D13 (l), Tasks 1.1 and 1.2.
- PR-MED-050 — verified (`_NON_PATH_LITERALS`, `_NAME = "clinikoscribe"`). Landed: D13 (m), D11 pointer, Tasks 1.4 and 1.6.
- PR-MED-051 — verified (`disarm_development_tick`'s rule; `_refuse_while_held` keeps both ticks). Landed: D13 (n), Task 2.2.
- PR-MED-052 — verified (`_situation` holds tab, target, outcome type, session ref and state). Landed: D13 (o), Task 2.2.
- PR-MED-053 — verified (`SELF_CHECK_FLAG`, exit codes 0–2; the audit runs it). Landed: D13 (p), Task 0.7 replaced; the reconciliation's `[operator]` on 0.7 withdrawn.
- PR-MED-054 — verified (`DELETE_CONFIRM_MESSAGE`). Landed: D13 (q), Tasks 2.3 and 4.2, Task 0.8's grep.
- PR-MED-055 — verified (each passage read). Landed: D13 (r), Tasks 4.1 and 4.2.
- PR-MED-056 — verified against D11's member names. Landed: D13 (s), D11 pointer, Tasks 4.1 and 4.2.
- PR-MED-057 — verified (`read_pilot_settings`: absent is shadow off). The reconciliation's own claim was wrong and is corrected. Landed: D13 (t), C14 pointer, P.2.
- PR-MED-058 — verified against D5, C8 and Task 3.2. Landed: D13 (u), Task 3.2, Validation.
- PR-MED-059 — verified (`WindowsLayer` has `drive_type(root)` and no volume identity; Export's docstring names the mounted-volume residue). Landed: D13 (v), D4 pointer, Task 1.5.
- PR-MED-060 — verified (`repair_kept_facts` iterates `kept_entries()` and makes two audit writes each). Landed: D13 (w), D9 pointer, Task 4.3.
- PR-LOW-061 — verified against D8's status-line rule. Landed: D13 (x), P.3.
- PR-LOW-062 — verified (each line read); record-only. Landed: the Key Findings re-verification bullet and D8 (iii).

### Round 7 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (reconciliation pass, round 2)

Source: Codex gpt-6.2-astra high plan peer-review

PR-HIGH-063 — A partial backup can be mistaken for a safe replacement for older backups.
Materiality: build-affecting
D13(c–d) deliberately allows entries and audit rows to be omitted. Flow 1 reports the counts written, while D13(q) tells the practitioner to destroy every earlier backup after a deletion. If an unrelated entry has become unreadable, those earlier files may contain its only recoverable copy. `plan-past-sessions-backup.md:103,116,131–132,145,219`.
Proposed amendment: Report omissions and audit availability explicitly, distinguish a complete replacement from a partial backup, and give the practitioner a recovery step before retiring older media under decision 0.5.

PR-HIGH-064 — The recording state selected for deletion loses information that D13(a) requires.
Materiality: build-affecting
`_recording_state` returns only `kept`, `gone`, or `none`. A live audio key beside missing audio returns `none`, and an uninspectable key can return either `kept` or `none`. Delete now and the retention sweep also read this state before calling `delete_entry`, so adding another read inside that method gives the audit and destruction decisions different observations. `past_sessions.py:1852–1896`, `ui/past_sessions.py:643–662`, `past_sessions.py:1621–1643`, `plan:129,233`.
Proposed amendment: Use one custody observation that retains the underlying audio-key state for both the audit and the destruction decision, test a key without audio, and document how the practitioner handles a persistently uninspectable key without declaring it destroyed.

PR-HIGH-065 — A failed Delete now can already have destroyed the recording.
Materiality: build-affecting
The overwrite can partly succeed before verification fails. It can also fully succeed before removal of `key.dpapi` fails. In the latter case the transcript remains and the recording is gone. Task 1.7 promises every file is untouched, and the existing failure line tells the practitioner that nothing else changed. `plan:129,233`, `past_sessions.py:1072–1077,1095–1104,1524–1529`, `ui/past_sessions_view.py:791–792`.
Proposed amendment: Distinguish a failed overwrite from verified audio destruction followed by failed entry deletion, preserve the appropriate audit evidence, and test the retry and user message at both failure points.

PR-HIGH-066 — The rollback instruction cannot protect recordings from automatic expiry.
Materiality: build-affecting
“Delete recording first, then Delete now” covers a manual deletion. On 0.4.2 the startup retention sweep runs before the clinician can use the window, and the timer can expire entries later. Both reach the older key-first deletion path. `plan:129,151,251`, `app.py:632–636,857–863`, `past_sessions.py:1643,2115–2135`.
Proposed amendment: Add a pre-downgrade procedure that also handles held recordings due for unattended expiry, and verify it against the first startup of the rollback build.

PR-HIGH-067 — Hop C can copy a different generation from the one whose key hop B wrapped.
Materiality: build-affecting
Hop B records names and sizes. D13(c) compares the opened file with its current path in hop C. A same-size replacement made before that open matches its own path and passes. The archive writer uses a fresh entry key for each generation, so the resulting file can pass every backup hash check and still fail to restore. `plan:131–132,229–230`, `past_sessions.py:725–739,810–815`.
Proposed amendment: Bind the snapshot’s key, label and expected members to one generation, carry the identity evidence into hop C, and test a same-size replacement between hops.

PR-HIGH-068 — An ordinary-file check does not prove that the file belongs to the checked folder.
Materiality: build-affecting
A hard-linked file satisfies the regular-file and matching-identity tests in D13(c). A changed parent directory is also shared by both sides of the comparison. This matters because the ZIP stores the bytes it reads verbatim. The existing audio-key custody code checks link count, and the archive separately checks directory junctions before following children. `plan:117,131,230`, `session_store.py:677–692`, `past_sessions.py:658–664,1840–1849`.
Proposed amendment: Apply an owned-file rule to the snapshot key and payload reads, including the containing directory’s identity, reparse state and single-link requirement, and verify that an outside file is omitted.

PR-HIGH-069 — Open admits the containing folder without establishing where the selected file resides.
Materiality: build-affecting
A file link inside an admitted folder can resolve to a disallowed location. Its device, file number and size may remain unchanged throughout Open, so D13(g)’s identity check does not fix the initial admission. `plan:106,135,245`, `exclusions.py:493–521`, `session_store.py:677–692`.
Proposed amendment: Admit the selected ordinary file and its resolved location before reading its header, and cover a refused file inside an otherwise admitted folder.

PR-HIGH-070 — File identity and length do not preserve the verified bytes through Restore.
Materiality: build-affecting
D13(g) rechecks device, file number and size on reopen. An in-place change can preserve all three while the summary dialog is open. Restore imports audit rows before staging entries, so the later entry hash check cannot protect the first local write. `plan:106,109,121,135,243–245`.
Proposed amendment: Keep a verified source handle that excludes modification through Restore, or reauthenticate the complete source before the first mutation and bind every subsequent read to it.

PR-HIGH-071 — The writer’s successful publish lacks the ownership protection specified for cleanup.
Materiality: build-affecting
D13(h) concerns the failure `finally`. The success path verifies the `.part` by path and later renames by path. The plan does not ensure that the renamed file is the verified one. Comparing a remembered ID after closing every handle is also weaker on removable media, where file IDs can be reused. `plan:103,126,134,136,230`, `past_sessions.py:1915–1936,2008–2043`. [Windows file identity semantics](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information)
Proposed amendment: Keep ownership through verification, sync and no-replace publication, apply same-handle deletion on failure, and credit entries only after the verified file has been published.

PR-HIGH-072 — Restore protects an add against a late destination change but leaves key repair exposed to the same change.
Materiality: build-affecting
Repair rechecks the content and proves the recovered key opens it. Those checks do not prove that the destination `key.dpapi` still contains the failing blob classified earlier. A key repaired independently during that interval would be overwritten by the unconditional `os.replace`, contrary to C5. `plan:120,130,180,244`.
Proposed amendment: Bind the repair commit to the original entry directory and failing key blob, abort on a changed target, and test a local key becoming readable after classification.

PR-HIGH-073 — Dropping an unreadable audit row can change a restore refusal into permission to add an entry.
Materiality: build-affecting
D5 distinguishes an absent row from one whose deletion state cannot be determined. D13(c) drops an uninspectable row as `skipped_gone` while allowing its entry to remain in the manifest. A fresh destination then sees an absent row in both sources and can add the entry. `plan:90,120–121,131–132,229,243`.
Proposed amendment: Preserve a content-free unknown-row indication for a known row that could not be copied, and test that the corresponding entry retains its `skipped_unknown_row` protection on a fresh destination.

PR-HIGH-074 — An imported audit row can confer coverage on different local content.
Materiality: build-affecting
D13(k) fixes the timing for a *kept local row*. D6 still sets coverage during a new-row import or bare-row replacement based on the entry ID appearing in the file. If a readable local entry has that ID but different bytes, it is skipped as present after its row has already acquired coverage. The plan itself establishes that an ID can have more than one generation. `plan:91,109,121–122,139,167`, `past_sessions.py:673–677,810–815`.
Proposed amendment: Separate imported row history from evidence of coverage for the current local entry, granting that coverage only after add, repair, or a verified match to the existing generation.

PR-HIGH-075 — Recovery can acquire an archive writer after the run flag is taken.
Materiality: build-affecting
The two Recovery lists are snapshots. A temporarily uninspectable session is omitted, and navigation or Chrome can refresh the lists during a worker hop. Recovery can then adopt or discard the newly visible session. Discard removes archive state and writes the audit. The page also has distinct CSV and recording Export controls, and recording export writes the audit after its dialogs. `plan:133,187,238`, `ui/models.py:1505–1515`, `ui/main_window.py:1264–1285,1334–1338`, `ui/recovery.py:454–488`, `ui/past_sessions.py:791–815,1095–1110`.
Proposed amendment: Consult the shared run flag at Recovery resume, adopt and discard, including Chrome adoption, and at recording export after its final dialog, with a test that makes a row visible only after backup admission.

PR-HIGH-076 — Open and Restore have no complete contract for ownership of the derived key.
Materiality: build-affecting
Task 3.3 specifies hop A and `open_backup(path, passphrase)`, while D13(f) defines that function as derivation plus verification and wipes the passphrase after hop A. The planner and restorer receive a `summary` but no authenticated reader or key with which to consume the wrapped entry and audit keys. Returning such a capability in the worker result would send it through `TaskThread.succeeded`. `plan:134,229,243–245`, `ui/tasks.py:24–25,36–42`.
Proposed amendment: Derive once into a run-owned authenticated reader, pass that reader explicitly to the GUI planner and restorer, and send only key-free completion data through Qt signals.

PR-HIGH-077 — The consent decision can be recorded while the first real backup remains unauthorized.
Materiality: build-affecting
P.4 allows wording to be sent back. P.4b is complete once a choice is recorded, including “wait for the reviewer” and “only entries recorded under v4.” Neither state authorizes P.3 on the installed all-entry build. The app records the recording-consent tick version, while the patient-sheet version is recorded in Cliniko. A cutoff for entries also leaves the whole-audit decision unresolved. `plan:154,215,260–264`, `docs/practice/README.md:54–61`, `encounter.py:84,167`.
Proposed amendment: Make P.3 conditional on actual approval and an executable disposition, keeping it on hold for returned wording, an outstanding reviewer answer, or a restricted scope that requires a separately approved design and build.

PR-MED-078 — The partial-entry rule can accept a note that was already missing when the snapshot began.
Materiality: build-affecting
D13(d) requires every member *named in the snapshot*. A directory listing alone cannot distinguish a legitimately absent optional note from a missing saved note. The authenticated label has `has_saved` and `has_generated`, while `read_entry` accepts an absent saved-note file as `None`. `plan:116,132,229–230`, `past_sessions.py:717–718,734–744,1480–1485`.
Proposed amendment: Derive the required member set from the authenticated label, bind it to the manifest and its completion date, and refuse coverage when a required file was already missing at hop B.

PR-MED-079 — The writer needs a finalization step for counts and an empty result.
Materiality: build-affecting
D11 puts the header first and binds its exact bytes to the manifest. D13(d) allows the actual counts and manifest size to change during writing. Task 1.4 checks for an empty *plan*, leaving the case where every entry and row disappears during hop C unspecified. `plan:116–117,126,132,229–230`.
Proposed amendment: Specify how the writer finalizes the first header from the surviving members before sealing the manifest, and require `nothing_to_back_up` with no published file when none survive.

PR-MED-080 — The ZIP preflight does not enforce its member-allocation limit.
Materiality: build-affecting
D11 validates the count declared in the end record. Python 3.14’s `ZipFile` constructs entries until it has consumed the declared central-directory **byte length**. Checking the count field alone therefore does not enforce `MAX_MEMBERS` before object allocation, which is the reason the plan introduced preflight. `plan:126,183,229`, `sample_notes.py:377–387`. [CPython 3.14 ZIP reader](https://github.com/python/cpython/blob/3.14/Lib/zipfile/__init__.py#L1467-L1475)
Proposed amendment: Count the actual bounded directory records before constructing `ZipFile`, require agreement with the end record, and test the refusal occurs before the library parser runs.

PR-MED-081 — A volume mount point is a path, so equality of mount points is insufficient for the same-volume warning.
Materiality: build-affecting
D13(v) compares two mount-point strings. Windows permits the same volume to be accessible through both a drive letter and a mounted folder. The backup location can therefore pass as a different volume while residing on the data volume. Drive type also describes the exposed volume and does not establish where a virtual disk’s backing file resides. `plan:119,150,231`, `exclusions.py:504–516`. [Windows volume naming](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-volume)
Proposed amendment: Have the injected seam identify the underlying volume consistently across aliases, test two mount paths for one volume, and state the custody limit for virtual-disk backing storage.

PR-MED-082 — The manifest cannot represent two source audit rows for the same ID.
Materiality: build-affecting
`backup_snapshot` enumerates row files, while the manifest uses `rows: {id: month}`. HEAD explicitly handles two files for one ID as ambiguous, and its tests construct that state. Selecting either month silently loses a row and can select the wrong deletion history. The writer’s regex-only month check can likewise accept a month that D13(i) later refuses to restore. `plan:121,137,228–229`, `audit.py:1009–1015,1041–1051,1222–1237`, `test_audit.py:762–767`.
Proposed amendment: Detect duplicate IDs and uncomputable calendar months during snapshot and verification, and define a visible outcome that preserves the ambiguity before the file is presented as restorable.

PR-MED-083 — A missing audit key beside existing rows is classified incorrectly.
Materiality: build-affecting
D13(j) says a missing key means all IDs are `absent`. `_open_key(create=False)` raises `key_missing` when rows remain and `_NoKey` only for a genuinely fresh store. Conflating them hides a custody failure. The same distinction matters when taking a read-only audit snapshot for an entries-only backup. `plan:121,138,179,228`, `audit.py:1245–1265,1285–1286`, `test_audit.py:437–446`.
Proposed amendment: Return `unavailable` for rows behind a missing or unusable key, reserve `absent` for confirmed absence, and test both snapshot and coverage paths without creating a store.

PR-MED-084 — D13(k) records the backup date as the restore date.
Materiality: build-affecting
D13(k) advances both fields to the file’s `made_at`. D6 uses `now` for `restored_at`, so the same restore can have different audit dates depending on whether its local row already existed. The planned `record_restored(id)` signature also cannot carry both times. `plan:109,121,139,228,244`.
Proposed amendment: Pass `made_at` and the restore event time separately, apply the monotonic rule independently to each field, and test restoring an older file into both an existing and a fresh row.

PR-MED-085 — Some restore outcomes still have no faithful classification or count.
Materiality: build-affecting
Task 1.2 defines `bad_length` for a successful DPAPI unwrap yielding the wrong number of bytes, but Task 3.1 gives it no outcome. D13(u)(3) likewise omits the report code for a failed repair whose cleanup succeeds. D13(b) counts any late destination as `skipped_present`, even though D5 gives that name to a verified local key and the new destination can be an empty directory. `plan:106,120,130,149,228,243–245`, `session_store.py:662–670`.
Proposed amendment: Give each case a non-mutating disposition and map every planner and execution outcome to a summary or final-report count, distinguishing an unverified destination collision from a readable entry.

PR-MED-086 — Repair cleanup uses a return value that cannot prove the staging folder is gone.
Materiality: build-affecting
`_remove_key_first` returns true after removing the key and ignores directory cleanup errors. D13(u) requires the staging folder to be gone after successful cleanup. Making `.tmp` a second load-bearing unlink on this shared helper also changes ordinary deletion semantics if the canonical key has already gone when that second unlink fails. `plan:120,149,244`, `past_sessions.py:1524–1529,2115–2136`.
Proposed amendment: Give repair staging a cleanup result that distinguishes key removal, directory removal and a previously committed repair, and test a locked temporary file and failed directory removal without changing ordinary deletion’s contract.

PR-MED-087 — Secret cleanup starts too late and can miss worker termination.
Materiality: build-affecting
The passphrase leaves its dialog before the save picker, same-volume confirmation and final busy check. Each can exit before hop A starts. Failure in GUI hop B or dispatch of hop C can also strand the derived key. `TaskThread` catches only `Exception`, and the existing Discard worker documents why an abnormal exit otherwise leaves every control held. `plan:103,123,133–134,237–238`, `ui/tasks.py:36–42`, `ui/session_screen.py:745–765`.
Proposed amendment: Assign one cleanup owner from dialog acceptance through terminal accounting, with an unconditional worker-finished fallback and tests for cancellation, refused admission, dispatch failure and abnormal termination.

PR-MED-088 — A valid entries-only backup can fail both checks required by P.3.
Materiality: build-affecting
D1 permits a successful backup when the audit key is unreadable. Task 3.1 then refuses the local restore plan before the Open-and-Close summary, and Task 2.3 can correctly show the reminder because no coverage row was updated. D13(x) nevertheless requires a successful check and an absent reminder. `plan:106,116,138,152,239,243–245,264`, `audit.py:1079–1089`.
Proposed amendment: Allow file-only verification with Restore disabled when the local audit needs attention, and make P.3 record the reminder expected from the actual coverage outcomes.

PR-MED-089 — The first-ever reminder bypasses the agreed seven-day delay.
Materiality: build-affecting
Task 2.3 shows the reminder immediately whenever the last backup date is absent. Its inputs contain only committed IDs, audit rows and `now`, so for an entry without a row the function has no date from which to measure the initial seven days. `plan:30,123,220,239`.
Proposed amendment: Define the first-backup grace-period anchor and its unknown-date behavior without introducing a run ledger, and test the first day and the seven-day boundary.

PR-MED-090 — Restore can report success while the visible archive and retention cache still show the old state.
Materiality: build-affecting
The page re-lists on entry, and its timer does not re-list after a restore. The store also caches failed label reads and can continue treating a repaired entry as undated. Task 3.3 specifies a success line but neither refresh. `plan:244–245`, `ui/past_sessions.py:379–412,1117–1128`, `past_sessions.py:615–634,1589–1606`.
Proposed amendment: Invalidate the affected store caches at commit and refresh the visible page before showing the outcome, preserving the existing rule that a hidden page retains no names.

PR-MED-091 — The amended deletion wording is still false for an admitted destination.
Materiality: build-affecting
D13(q) says the entry is deleted “from this computer for good,” although D4 allows an older backup on the same computer. A separate shortening-retention confirmation still says expired entries cannot be recovered, and its wording has an exact test and design-system quote. `plan:119,145,239,252`, `ui/past_sessions_view.py:184–189,310–314`, `ui/past_sessions.py:886–889`, `test_ui_screens.py:11762`, `docs/design-system.md:250`.
Proposed amendment: Scope the deletion statement to the active Past sessions archive and update the shortening-retention dialog, its exact test and its design-system quote in the same task.

PR-MED-092 — Merge and approval leave different patient sheets authoritative.
Materiality: build-affecting
C13 protects the ten consultations, but Task 4.2 makes v4 the primary sheet at merge and P.4 approval follows release, installation and smoke. The practice README keeps the previous sheet in use until approval. The consent example, signable form and sibling current-sheet instructions still name v3. Edits inside the separate development consent also engage its rule that the signed document and app tick share a version. `plan:125,154,250,260–263`, `docs/practice/README.md:54–61,75–79`, `patient-information-and-consent.md:141,174`, `development-recording-consent.md:12–19`, `downtime-procedure.md:36`, `privacy-information.md:15`.
Proposed amendment: Keep the approved sheet available and explicitly current until P.4, switch the form and active instructions together, include the practitioner-facing screen wording in sign-off, and place the backup explanation outside the approved development-consent text unless its shared version is deliberately changed.

PR-MED-093 — The lost-drive disclosure understates which audit information is visible.
Materiality: build-affecting
D13(s) says every audit field requires the passphrase. The ZIP member name discloses the exact audit `session_id` and the year and month of `session_date`, including sessions represented only by an audit row. The threat model also independently says the encrypted patient-name label exists nowhere else. `plan:126,146–147,249`, `audit.py:325–329`, `docs/security/threat-model.md:2883–2889`.
Proposed amendment: Identify the audit ID and month as visible metadata in all three disclosures and update the separate patient-name custody statement to include encrypted backup copies.

PR-MED-094 — The supported source dependency range includes a release without Argon2id.
Materiality: build-affecting
The frozen lock pins `cryptography==49.0.0`, but the desktop package permits `cryptography>=43`, and the plan itself identifies 44 as the first release providing `Argon2id`. A passing frozen self-check does not establish that a dependency-valid developer installation can run the feature. `plan:96,118,144,170`, `desktop/pyproject.toml:19`, `desktop/requirements-build.txt:26`.
Proposed amendment: Raise the source dependency floor to a release supporting the selected KDF and verify the developer entry point as well as the frozen self-check.

PR-MED-095 — Task 1.7 depends on a deletion step first assigned to Task 3.2.
Materiality: build-affecting
Task 1.7 must destroy the audio key *after* repair-staging removal. At HEAD, `delete_entry` goes directly to `_remove_key_first(entry)`. Task 3.2 is where the plan first assigns the staging-removal change, after the Phase 1 implementation and review gate. `plan:129,233,244`, `past_sessions.py:1519–1530`.
Proposed amendment: Assign the complete staging-before-audio-before-entry deletion sequence and its failure tests to Task 1.7, and make Task 3.2 consume that established contract.

PR-MED-096 — H5 still asks for evidence the replacement self-check cannot produce.
Materiality: build-affecting
D13(p) makes the check exit-code-only. H5 still requires the old probe output, Task 0.7’s completion also depends on H5, and the build diagnostic explains only exit codes 1 and 2. The Release workflow does invoke the real frozen check and already fails a nonzero return. `plan:144,205,222,256`, `app.py:665–702`, `scripts/build-release.py:473–486,834–837`, `.github/workflows/release.yml:82`.
Proposed amendment: Close Task 0.7 on implementation and unit verification, assign the frozen proof to H5 using its CI run and exit status, and add the code-3 explanation to the build diagnostic and its test.

PR-LOW-097 — D13(w) identifies an incorrect rollback compatibility boundary.
Materiality: build-affecting
D13(w) instructs the release document to say builds below 0.3.7 cannot open some later entries. The release record explicitly confirms that 0.3.6 reads every 0.3.7 Past-sessions entry, including a note with a joined answer. `plan:151,251`, `docs/release/pilot-builds.md:151–164`.
Proposed amendment: List only substantiated persisted-content boundaries and describe 0.3.7’s display and generation differences separately.

PR-LOW-098 — Several current instructions still point executors to superseded contracts.
Materiality: record-only
The decision index ends at D12. Integration Notes still specify `read_bytes` and unconditionally assign key destruction to hop C. C3 still promises zeroing beyond the mutable buffers D13(f) identifies. C13 retains a pre-tenth H5 possibility that its mandatory merge hold makes unreachable. The validation override at line 198 **does** reconcile the manual-check order. `plan:58,88,128,134,178,188,196–198`.
Proposed amendment: Update the decision index and these active instructions to point directly to D13 while preserving the dated Review History.

**Spot-checked cites**

- `HEAD` was `5d63ed6`. The plan was the sole tracked difference. I reviewed the body and Review History through line 277. The progress figure is correct at **7 of 37**, including the five hardening tasks on line 256.
- `past_sessions.py:673–696,722–753,817–923,1123–1155` and `session.py:1232–1241` support the pending-generation distinction. In the ordinary Complete, retry, Discard and trim paths, staging uses a fresh key and remains ineligible for backup until commit. I found no second ordinary destruction path for an already-backed-up committed recording there.
- `past_sessions.py:810–815` and `audit.py:1103–1114` support the separate no-overwrite publish. Python documents that Windows `os.rename` refuses an existing destination, including an empty directory. The empty-directory replacement behavior applies on Unix. [Python 3.14 `os.rename`](https://docs.python.org/3.14/library/os.html#os.rename)
- `past_sessions.py:1915–1936,2027–2043` identifies and deletes the reopened `.part` through one exclusive handle. The previous CPython FAT32/exFAT `fstat` failure was fixed. I found no basis for claiming that Python 3.14 categorically rejects either filesystem, and did not establish real-device behavior for this host. [CPython FAT32/exFAT fix](https://github.com/python/cpython/issues/111856)
- `exclusions.py:239–255,493–523` and `desktop/tests/conftest.py:333–347` confirm that the real Windows layer is blocked in tests and an injected volume seam is feasible.
- `ui/main_window.py:1526–1561,1568–1629`, `ui/bridge.py:899–937`, and `ui/session_screen.py:405,519–551` support the proposed close-guard position and development-tick rule. Draft-write and Discard reservations already contribute custody protection. I found no independent archive write by the benchmark or voice enrolment. A visible Unreviewed row blocking backup is consistent with the chosen admission rule.
- `app.py:501–510,817–826,857–863` and `ui/past_sessions_view.py:634–653` confirm the startup ordering and conditional kept-fact writes. An audio-free restored entry does not trigger those two writes.
- `test_audit.py:437–446,762–767,940–943,994–997,1195–1219` and `test_schema_versions.py:568–619,646–664` support the audit migration and CSV changes. Both audit uses of the shared future-version helper need the audit-specific next version. `test_install_layout.py:470,589–615` supports adding the filename prefix by its owning symbol.
- `note_config.py:1220–1239` supports explicitly enabling shadow mode in the fresh P.2 folder. `docs/testing/shipping-gate.md:110,118–120` supports retaining v3 through the tenth eligible consultation and recording the after-fingerprints and scoring commit before the merge.
- This was a static review. No files were changed, no tests or builds were run, and no clinical data, model or backup file was opened.

Materiality: 35 build-affecting / 1 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 7 (2026-11-25, the orchestrating session on Fable 5.2; each finding verified against the code at `5d63ed6` and the plan's text before any amendment)

Verified materiality: 35 build-affecting / 1 record-only / 0 invalid (as labelled). Every finding: Triage Include in plan; /fix decision Applied as a plan amendment; landed and siblings pointed as listed. Findings 067–072 assume a file changed from outside the app during a run (the run flag excludes the app's own writers); each fix is small and follows a rule the code already uses, so they are built rather than named as residues.

- PR-HIGH-063 — verified against D13 (c), (d), (q) and decision 0.5. Landed: D14 (1); Flow 1; D8, D10, D11 pointers; Tasks 1.3, 2.2, 4.2.
- PR-HIGH-064 — verified (`_recording_state` returns `none` for a live key without `audio.enc`; both callers read it before `delete_entry`). Landed: D14 (2); Task 1.7.
- PR-HIGH-065 — verified by the sequence itself and `delete_failed_line`'s wording. Landed: D14 (2); Task 1.7's Done-when.
- PR-HIGH-066 — verified (`run_retention_sweep` at start-up and on the hourly tick, `app.py`). Landed: D14 (3); D9 pointer; Task 4.3.
- PR-HIGH-067 — verified against hops B and C and `_stage`'s fresh key per generation. Landed: D14 (4); Task 1.4.
- PR-HIGH-068 — verified (`_is_own_key_file` checks the link count for the audio key only). Landed: D14 (5); Tasks 1.4, 4.1.
- PR-HIGH-069 — verified against D13 (g) (the folder, not the file). Landed: D14 (6); Tasks 1.5, 3.3.
- PR-HIGH-070 — verified against Flow 3's order (rows before entries). Landed: D14 (6); Flow 3; Task 3.2.
- PR-HIGH-071 — verified against D11's write, verify, rename by path. Landed: D14 (7); Task 1.4.
- PR-HIGH-072 — verified against D5's repair transaction. Landed: D14 (8); Task 3.2.
- PR-HIGH-073 — verified against D5's unknown-row rule and D6's `skipped_gone`. Landed: D14 (9); Tasks 1.2, 1.3, 3.1.
- PR-HIGH-074 — verified against D6's `included` rule and `skipped_present`. Landed: D14 (10); D6, D7 pointers; Flow 3; Tasks 1.2, 3.2; Validation.
- PR-HIGH-075 — verified (`RecoveryScreen._discard` checks its own busy state and live work only). Landed: D14 (11); Task 2.2.
- PR-HIGH-076 — verified against D13 (f) and Tasks 3.1–3.3's signatures. Landed: D14 (12); Tasks 1.3, 3.1, 3.2, 3.3.
- PR-HIGH-077 — verified against P.4 and P.4b's Done-when. Landed: D14 (28); P.3.
- PR-MED-078 — verified (`has_saved` / `has_generated` on the label; `_stage` writes the two optional files by them). Landed: D14 (4); Task 1.4.
- PR-MED-079 — verified against D11 and D13 (d). Landed: D14 (14); Tasks 1.3, 1.4.
- PR-MED-080 — verified against D11's preflight (a 64 MiB directory bound and the count field); the reader's behaviour as the peer cites it. Landed: D14 (15); Task 1.3.
- PR-MED-081 — verified against D13 (v). Landed: D14 (16); Tasks 1.5, 4.1.
- PR-MED-082 — verified (`_find` treats two files for one id as ambiguous). Landed: D14 (9); Task 1.2.
- PR-MED-083 — verified (`_open_key`: `key_missing` beside rows, `_NoKey` only for a fresh store). Landed: D14 (17); D13 (j) corrected; Task 1.2; Validation.
- PR-MED-084 — verified against D6 and D13 (k). Landed: D14 (10); Task 1.2.
- PR-MED-085 — verified against Tasks 1.2, 3.1 and D13 (b), (u). Landed: D14 (18); Tasks 3.1, 3.2.
- PR-MED-086 — verified (`_remove_key_first` returns True once the key is gone, whatever `rmtree` did). Landed: D14 (18); D5 pointer; Task 1.7.
- PR-MED-087 — verified (`TaskThread.run` catches `Exception` only). Landed: D14 (13); Tasks 2.2, 3.3.
- PR-MED-088 — verified against D1, Task 3.1 and D13 (x). Landed: D14 (19); P.3.
- PR-MED-089 — verified against decision 0.6 and Task 2.3. Landed: D14 (20); Task 2.3; Validation.
- PR-MED-090 — verified (the page re-lists only on entry; the store caches dates and unreadable labels). Landed: D14 (21); Tasks 3.2, 3.3.
- PR-MED-091 — verified (`retention_confirm_text` says "cannot be recovered"). Landed: D14 (22); D13 (q) corrected; Tasks 2.3, 4.4.
- PR-MED-092 — verified against Task 4.2 and the practice README's versioning rule. Landed: D14 (23); D10 pointer; Task 4.2; P.4.
- PR-MED-093 — verified against D11's member names. Landed: D14 (24); D13 (s) corrected; Task 4.1.
- PR-MED-094 — verified (`desktop/pyproject.toml` L19 `cryptography>=43`). Landed: D14 (25); Task 1.3.
- PR-MED-095 — verified (`delete_entry` at HEAD goes straight to `_remove_key_first`). Landed: D14 (2); Tasks 1.7, 3.2.
- PR-MED-096 — verified (`build-release.py`'s diagnostic names codes 1 and 2). Landed: D14 (26); Task 0.7; H5.
- PR-LOW-097 — verified (`docs/release/pilot-builds.md`: 0.3.6 reads every 0.3.7 entry). Landed: D14 (27); D13 (w) corrected; Task 4.3.
- PR-LOW-098 — verified; record-only. Landed: the decision index, the hop bullet of Key Findings, C3 and C13 edited directly.

### Round 8 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (reconciliation pass, round 3)

Source: Codex (gpt-6.2-astra high) plan peer-review

`plan` below refers to `.cursor/plans/plan-past-sessions-backup.md`. Python source citations are relative to `desktop/src/scribe_desktop/`.

**PR-HIGH-099 — “Complete backup” can authorize destroying the last restorable copy.**
Materiality: build-affecting
Evidence: At `plan:156`, zero omissions and audit inclusion authorize retirement of older backups. At `plan:159` and `plan:260`, a transcript already damaged before the snapshot passes the size, identity and freshly computed hash checks. The first check that its entry key actually opens it comes during Restore at `plan:275`. HEAD makes this distinction explicit in `past_sessions.py:779–800`. There is also a valid-data case: a copied `_NEWER` row counts as included, but `plan:120` requires Restore to skip its entry even on an empty computer.
Proposed amendment: Before advising retirement, require a read-only recoverability check for the entries being relied on, report any entries this build cannot restore, and test both pre-existing ciphertext damage and a copied newer row.

**PR-HIGH-100 — A complete backup of a reset audit store can discard seven years of recoverable history.**
Materiality: build-affecting
Evidence: `audit.py:1091–1129` moves the old store into quarantine and creates a fresh key. After a reset, a new backup can faithfully copy every row in the active store and satisfy `plan:156` while an older backup still holds the only usable copies of pre-reset rows. No source corruption or concurrent writer is needed. This matters directly to the password-reset procedure at `plan:112`.
Proposed amendment: Make recovery and reconciliation of pre-reset audit history an explicit prerequisite for retiring older backups after a reset, and cover a fresh readable audit store containing fewer rows than its predecessor.

**PR-HIGH-101 — Strict root listing does not establish a complete inventory.**
Materiality: build-affecting
Evidence: `past_sessions.py:1684–1705` raises for an unlistable root but silently omits an ID-shaped child whose link state cannot be inspected. An inspection error on its `pending` marker also hides it because `_exists` returns true on `OSError` at `past_sessions.py:2082–2091`. Likewise, `audit.py:1207–1236` skips an uninspectable month. These cases disappear before the omission counters required by `plan:132`, `plan:156` and `plan:164` are populated. An inaccessible month can also hide a local tombstone from `_find`.
Proposed amendment: Give backup inventory and restore-side tombstone lookup an indeterminate result for an uninspectable child or month, and test that it prevents a complete verdict or a confirmed-absent row verdict respectively.

**PR-HIGH-102 — A wholly unavailable source audit store loses the distinction between unknown and absent.**
Materiality: build-affecting
Evidence: `plan:164` protects IDs of individual omitted rows, but `plan:172` switches to entries-only on `AuditUnavailable`. If the store cannot be enumerated, it supplies neither IDs for `rows_unknown` nor a defensible numeric count for `omitted_rows`. On an empty destination, `plan:120` admits an entry when both rows appear absent. HEAD distinguishes an empty store, a missing key beside rows, and an enumeration failure at `audit.py:1239–1261`.
Proposed amendment: Preserve whole-store uncertainty in the manifest and summary, distinguish it from a confirmed empty store, and require Restore to skip an entry whose source tombstone status could not be established.

**PR-HIGH-103 — Historical coverage can be assigned to a different local generation.**
Materiality: build-affecting
Evidence: With a local entry and no local audit row, `plan:165` imports an incoming row’s non-null `last_backed_up_at` before comparing entry content. If the local entry differs, or the backup is row-only, the timestamp stays. The reminder at `plan:270` then counts the local bytes as covered. Different generations of one ID are expressly supported by `plan:91` and `past_sessions.py:810–815`.
Proposed amendment: Separate an imported row’s historical timestamp from verified coverage of the current local entry, and test both a row-only import and a differing `skipped_present` entry after an audit reset.

**PR-HIGH-104 — The proposed deletion result cannot preserve the existing pre-deletion audit rule.**
Materiality: build-affecting
Evidence: At `plan:157`, a successful return reports only whether this invocation destroyed a live audio key. A previously zeroed key, an absent key beside `audio.enc`, and a never-recorded entry all return false. HEAD distinguishes these states at `past_sessions.py:1877–1896`. The sweep must record an already-gone recording **before** removing its evidence and must count the entry as failed and retain it if that write fails. Delete now has a different hold rule. See `past_sessions.py:1621–1649`, `ui/past_sessions_view.py:798–822`, and `ui/past_sessions.py:643–676`. A return value received after removal cannot implement the callback.
Proposed amendment: Pass one classified custody state through a pre-deletion callback and the deletion transaction, preserving each caller’s hold rule and testing already-gone, newly destroyed, partial failure, and never-held outcomes.

**PR-HIGH-105 — Deleting a restored text-only entry can fabricate an audio-deletion timestamp.**
Materiality: build-affecting
Evidence: `plan:121` deliberately restores historical `recording.kept_at` even though a newly added entry has no audio. `audit.py:576–596` then sets `recording.deleted_at` on an entry tombstone whenever that historical `kept_at` is present. Thus deleting or expiring the restored entry says the recording was destroyed on that date, even if it remains on the original computer. D14(2)’s new custody result does not reach this audit change.
Proposed amendment: Make the recording-deletion fact depend on observed local recording custody while recording the entry tombstone independently, and test Delete now and expiry on a restored text-only entry with historical `kept_at`.

**PR-MED-106 — Some ordinary damaged audio-key files permanently disable Delete now.**
Materiality: build-affecting
Evidence: `plan:157` gives “close the program holding it, or use Delete recording” as the remedy for `unknown`. An empty ordinary `audio-key.enc` remains `unknown` after every handle closes because `past_sessions.py:1840–1869` requires a positive size. Delete recording uses the same predicate at `past_sessions.py:1088–1094`, and the UI refuses that action altogether when the listing shows no recording at `ui/past_sessions.py:705–712`.
Proposed amendment: Distinguish a confirmed empty ordinary key file from a locked, aliased or otherwise uninspectable file, and specify a usable recovery path for persistent malformed files without claiming that a live key was destroyed.

**PR-MED-107 — The manifest’s authenticated inventories can disagree.**
Materiality: build-affecting
Evidence: `plan:126`, `plan:164`, `plan:169` and `plan:260` validate member names, payload hashes, header bounds and the ZIP member set. They do not require the separate `entries`, `rows`, `rows_unknown` and actual counts to describe that same set. Nor does the restore contract explicitly bind the manifest’s retention date and optional note members to the decrypted label. HEAD’s label carries `completed_at`, `has_generated` and `has_saved` at `past_sessions.py:353–365`. An authentic writer error is already within the plan’s verification scope at `plan:149`.
Proposed amendment: Validate the manifest maps and counts against the payload inventory before showing the summary, then bind the entry date and required member set to its authenticated label before publication or repair.

**PR-MED-108 — An unwrappable key and a usable local entry are different checks.**
Materiality: build-affecting
Evidence: `plan:120`, `plan:165` and `plan:173` allow `skipped_present` when the local DPAPI blob yields a 32-byte key with the right store description. Every entry shares that description at `past_sessions.py:547–554`. A key belonging to another entry on the same login passes that check, while the bound label fails to open at `past_sessions.py:1729–1738`. With matching ciphertext, the summary can say “already here” for an entry the clinician cannot open.
Proposed amendment: Verify that the local key opens the ID-bound label before reporting a usable present entry, and classify a same-store wrong key as an untouched conflict under the fixed repair rule.

**PR-MED-109 — Restore accounting loses the actual commit point.**
Materiality: build-affecting
Evidence: `plan:165` advances `restored_at` for matching `skipped_present` content even when the local row was kept and no entry was added or repaired. Conversely, `plan:173` and `plan:275` give the same `failed_repair` result to failures before replacement and cleanup failures after a successful replacement. Only the latter committed a repair, so an outcome-only caller cannot correctly decide both timestamp updates and cache invalidation.
Proposed amendment: Carry entry-commit status independently of cleanup status, grant coverage alone on a verified no-op, and test timestamp and cache effects on both sides of `os.replace`.

**PR-MED-110 — The stated archive budget exceeds what the selected writer can publish.**
Materiality: build-affecting
Evidence: `plan:126`, `plan:170` and `plan:261` combine an 8 GiB outer limit, Python’s `zipfile` writer and rejection of every ZIP64 end record and directory extra. CPython 3.14 emits ZIP64 when the central-directory offset exceeds `2³¹−1`, or raises `LargeZipFile` with ZIP64 disabled. An archive can cross that boundary below the member-count limit and fail only after a lengthy USB write. [CPython 3.14 ZIP writer](https://github.com/python/cpython/blob/3.14/Lib/zipfile/__init__.py)
Proposed amendment: Set and preflight one supported classic-ZIP output budget including container overhead, give an over-budget archive a specific operator outcome, and test the boundary through the size seam.

**PR-MED-111 — The specified failure cleanup conflicts with Windows handle sharing.**
Materiality: build-affecting
Evidence: `plan:162` calls for `.part` cleanup through the still-open writer’s identity. The referenced `_remove_part` implementation opens a second handle with DELETE access and share mode zero at `past_sessions.py:1949–1968` and `past_sessions.py:2027–2043`. That exclusive open conflicts with the outstanding writer. On rename failure, the writer has already been closed.
Proposed amendment: Save the writer’s identity and close it before invoking identity-checked `_remove_part`, or acquire delete access on the original handle and delete through it, with verification-failure and rename-failure tests.

**PR-MED-112 — Rejecting a network source can itself perform network filesystem I/O.**
Materiality: build-affecting
Evidence: `plan:161` requires `link_state` and resolved-folder admission before reading file bytes. `session_store.py:677–689` implements `link_state` with `os.lstat`. The proposed shared location helper starts from code that calls `realpath` before checking the network at `exclusions.py:307–308` and `exclusions.py:441–449`. On an explicitly remote path, either operation can contact the share. A test that counts only payload reads misses this.
Proposed amendment: Reject recognizable network paths and mapped remote drives before application-initiated file inspection or resolution, and make the refusal test fail on metadata access as well as payload reads.

**PR-MED-113 — Restore’s second full-file verification has conflicting thread assignments.**
Materiality: build-affecting
Evidence: `plan:161` requires another whole-file verification after Restore is selected. `plan:167` and `plan:275–276` place the restorer on the GUI thread, while `plan:216` assigns file verification to workers. Following the restorer task literally can freeze the window for an entire second USB read before any restoration progress is shown.
Proposed amendment: Assign the post-confirmation full-file pass to a worker owned by the same run, then recheck admission and dispatch GUI-thread writes only after the manifest matches.

**PR-MED-114 — The reminder can permanently deny a backup the practitioner just verified.**
Materiality: build-affecting
Evidence: Under indefinite archive retention, `audit.py:1033–1056` can legitimately prune the month of an entry that remains readable. Its next backup can contain and verify that entry, but `plan:172` forbids creating a coverage row, `plan:175` treats its missing date as old enough, and `plan:270` displays “not yet in any backup.” Repeating Back up never changes that result. A persistently unreadable entry also gets counted without identifying why another backup cannot help.
Proposed amendment: Keep the seven-day rule and distinguish missing coverage evidence or an unreadable entry from a confirmed outstanding backup, with a test immediately after backing up an entry whose audit month has been pruned.

**PR-MED-115 — The post-deletion rule has no completion path for a genuinely empty store.**
Materiality: build-affecting
Evidence: `plan:156` permits retirement of pre-deletion copies only after a new backup says it is complete. `plan:116` and `plan:169` prohibit publishing any file when there are zero entries and zero rows. Both stores can legitimately be empty once the last entry is gone and the last audit month has been pruned at `audit.py:1033–1056`.
Proposed amendment: Define the practitioner’s retirement procedure for a positively verified empty inventory, keeping that outcome distinct from a run where all candidates were unavailable or omitted.

**PR-MED-116 — The deletion procedure overlooks partial files that contain a complete backup.**
Materiality: build-affecting
Evidence: At `plan:126` and `plan:162`, a fully written and verified `.csbk.part` still exists immediately before rename. A power loss at that point leaves a restorable copy under the temporary name. The warning at `plan:103` detects only a same-name collision, so a backup made on a later date need never surface it. The disposal rule at `plan:156` and `plan:281` names older backups without telling the practitioner that identified partial files can retain the deleted entry too.
Proposed amendment: Include the practitioner’s known pre-deletion partial files in the drive-retirement instructions while preserving the rule that the app never deletes an unowned file.

**PR-MED-117 — A Chrome refusal can remain visible after the backup finishes.**
Materiality: build-affecting
Evidence: `plan:143` allows an implementation that adds the run flag only to the Start situation. `plan:166` now requires `open_review` and Discard to refuse during the run as well. `ui/bridge.py:899–936` retains each refusal against its own action’s situation, and `extension/src/panel-view.ts:310` displays the retained message. Finishing the backup changes none of the existing situation fields for those actions.
Proposed amendment: Expire and republish every `backup_running` refusal when the run ends, and test unchanged-target Open review and Discard alongside Start.

**PR-MED-118 — P.4 can approve v4 while the practice continues handing out v3.**
Materiality: build-affecting
Evidence: `plan:178` and `plan:293–295` switch the tracked wording in one commit. `AGENTS.md:81` and `.gitignore:48` identify separate printable handouts, and `docs/practice/downtime-procedure.md:35–37` requires the current sheet to be at hand. An unused v3 copy still explicitly promises no transcript backup at `docs/practice/patient-information-and-consent.md:75`.
Proposed amendment: Have the practitioner confirm at P.4 that the v4 sheet and form are in use and unused v3 stock has been withdrawn, while preserving historical signed records.

**PR-MED-119 — Both new deletion confirmations make unconditional claims the app cannot establish.**
Materiality: build-affecting
Evidence: At `plan:177`, “a backup made before this deletion still holds them” includes files made before the entry existed and incomplete backups that omitted it. The shorter-retention confirmation says every older entry is deleted immediately, although `past_sessions.py:1543–1571` explicitly retains unreadable and uncleared entries, and `plan:157` adds another deletion refusal. These are exact UI strings pinned at `desktop/tests/test_ui_screens.py:11243–11247` and `:11759–11763`.
Proposed amendment: Say that an older backup **may** hold the entry and that the app will attempt to delete eligible older sessions, with the sweep result reporting what actually happened.

**PR-LOW-120 — Task 1.3 introduces a literal whose required test change is deferred to Task 1.6.**
Materiality: build-affecting
Evidence: `plan:141` and `plan:260` put `BACKUP_FILENAME_PREFIX` in the new container module, but `plan:263` delays its `_NON_PATH_LITERALS` entry. `desktop/tests/test_install_layout.py:589–615` checks both directions: the unlisted literal fails, and an allow-list entry without its literal fails. The two changes form one verifiable unit.
Proposed amendment: Move the named allow-list change into the same task as the prefix definition.

**PR-LOW-121 — Two standalone plan summaries still give the superseded behavior.**
Materiality: record-only
Evidence: Flow 2 at `plan:106` still lists an unreadable local audit key among Open’s refusals, whereas `plan:174` requires a verified summary with Restore disabled. The schema backfill paragraph at `plan:196` still assigns `made_at` based on entry inclusion, whereas `plan:165` requires a committed add, committed repair or matching present content. Neither summary carries the Round 7 pointer promised at `plan:155`.
Proposed amendment: Update those two summaries to state the effective preview and coverage rules directly.

**PR-LOW-122 — The lost-drive disclosure misidentifies one date and omits change visibility across copies.**
Materiality: record-only
Evidence: `plan:179` describes the exposed audit folder as the month of the session. For a sparse row without a trusted creation date, `audit.py:482–487` and `audit.py:1162–1169` use the later date on which the row was made. Also, `plan:116` and `plan:126` deliberately copy stored ciphertext unchanged, so someone holding two files can tell which corresponding members changed even when their sizes match.
Proposed amendment: Describe the visible date as the stored audit month and disclose that corresponding encrypted members can be compared across backups.

**PR-LOW-123 — H5 names release evidence the workflow does not produce separately.**
Materiality: record-only
Evidence: `plan:124`, `plan:181` and `plan:287` refer to a tagged release and an audit-step exit status. `.github/workflows/release.yml:24–36` dispatches on `refs/heads/main`, and `:80–82` runs one installer-build step. `scripts/build-release.py:834` executes the bundle audit inside that step. A successful build proves the audit passed, but there is no separately reported audit-step status.
Proposed amendment: Record the `main` commit, Release run ID, successful installer-build step and attestation as H5’s evidence.

**Spot-checked cites**

- `git rev-parse --short HEAD`, `git --no-optional-locks status --short` and `git diff --name-only HEAD` confirmed `5d63ed6` with only the named plan modified. Review scope ended at `plan:309`. Verification was static.
- `past_sessions.py:642–648`, `:810–866`, `:895–923` and `:1123–1165` confirm that `_forget_dates` clears all three date/retry caches, ordinary `_publish` can replace a destination, interrupted Complete copies remain subject to pending cleanup, and tidy acts only on confirmed dead recording evidence. `_publish_new` is appropriately a new operation.
- `past_sessions.py:1058–1121`, `:1840–1896` and `:2115–2153` confirm the four audio-key states, the zero/flush/sync/read-back order, the distinction between an absent key and a prior deletion, and the helper’s key-removal success despite best-effort directory cleanup.
- `audit.py:416–460`, `:465–472`, `:997–1019`, `:1079–1089` and `:1245–1284` confirm newer-row handling, the two-argument month-prune calculation, duplicate-ID refusal, and the `_NoKey` versus `key_missing` distinction. `desktop/tests/test_audit.py:487` and `desktop/tests/test_schema_versions.py:202–209` confirm the future-version fixture dependency.
- `session_store.py:618–670`, `:677–692` and `secure_storage.py:87–107` confirm file-based DPAPI unwrap, tri-state link inspection and the immutable exported key copy. The planned blob classifier and mutable-buffer cleanup have distinct jobs.
- `exclusions.py:435–452`, `:493–523` and `desktop/tests/conftest.py:331–347` confirm the current location checks and real-layer sentinel. A read-write exclusive create supports handle readback. FAT’s single-link count and coarse modification time do not by themselves reject ordinary files, and the `.part` rename shortens the name. I found no basis for a blanket FAT rename rejection. The volume GUID API accepts drive-letter and mounted-folder roots. These are platform-contract checks, not a physical-media smoke. [Windows file identity and timestamps](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information) · [Windows volume GUID lookup](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumenameforvolumemountpointw)
- `ui/tasks.py:22–42`, `ui/main_window.py:1548–1563`, `:1612–1621`, `ui/recovery.py:314–326`, `:363`, `:434–460`, and `ui/bridge.py:899–936` confirm the task result signals, recovery protections and action entry points, close-guard placement, and retained-refusal behavior. `app.py:604–638` confirms that guarding `PeriodicSweep.__call__` reaches all three timed operations.
- `app.py:487–510`, `:665–702`, `scripts/build-release.py:473–487`, `desktop/pyproject.toml:19`, and `desktop/requirements-build.txt:26` confirm the limited kept-fact repair, available self-check code 3, existing release diagnostic, and difference between the developer dependency floor and the frozen pin.
- `docs/practice/README.md:54–61`, `desktop/tests/test_schema_versions.py:325–331` and `desktop/tests/test_pilot_docs.py:208–240` support staging the draft patient sheet beside v3 while preserving the separate development-consent tick. `note_config.py:1227–1239` confirms that a missing pilot setting means shadow off. `docs/testing/shipping-gate.md:110`, `:119–120` supports the tenth-score and fingerprint hold.
- `plan:246–296` contains **37 tasks, seven complete**, counting H1–H5 individually on line 287. The Phase P labels and order match the fixed practitioner decisions. P.3 has an operator gate requiring every P.4 approval and P.4b option (a). P.1 installs the available feature earlier, so that gate is procedural.

Materiality: 22 build-affecting / 3 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 8 (2026-11-25, the orchestrating session on Fable 5.2; each finding verified against the code at `5d63ed6` and the plan's text)

Verified materiality: 22 build-affecting / 3 record-only / 0 invalid (as labelled). Triage for every finding: Include in plan. /fix decision: HELD — verified, not yet applied; escalated to the practitioner (fix-induced skew). Each is to be folded into the plan at the consolidation, or applied as a further correction if the practitioner chooses to keep layering.

- PR-HIGH-099 — verified (a hash made at backup time proves nothing about whether the entry opens; `_verify_staged` is the code's own statement of the difference; a `_NEWER` row makes its entry unrestorable by this build). Fix-induced by D14 (1).
- PR-HIGH-100 — verified (the audit Reset quarantines the old store and starts a fresh key). Fix-induced by D14 (1).
- PR-HIGH-101 — verified (`_entry_dirs` drops an id-shaped child whose link state cannot be read; `_exists` reads an error on `pending` as present; the audit listing skips an uninspectable month). Pre-existing.
- PR-HIGH-102 — verified against D14 (9) and (17) (entries-only on `AuditUnavailable` gives no ids for `rows_unknown`). Pre-existing, sharpened by D14 (9).
- PR-HIGH-103 — verified against D14 (10) (an imported row's own coverage date stays whatever the local entry holds). Fix-induced.
- PR-HIGH-104 — verified (the retention sweep calls `before_held_delete` with `recording_gone` BEFORE `delete_entry`, and holds the entry when that write fails; a return value comes too late). Fix-induced by D14 (2).
- PR-HIGH-105 — verified (`_past_session_recorded` sets `recording.deleted_at` whenever `kept_at` is set, and a restored row keeps `kept_at`). Pre-existing since D6.
- PR-MED-106 — verified (`_is_own_key_file` needs 1–60 bytes, so an empty key file is `unknown` for ever; Delete recording uses the same rule). Fix-induced by D14 (2).
- PR-MED-107 — verified against D11 and D14 (9), (14). Pre-existing.
- PR-MED-108 — verified (every entry's key shares one DPAPI description; only the id-bound label proves the key is this entry's). Pre-existing.
- PR-MED-109 — verified against D14 (10) and (18). Fix-induced.
- PR-MED-110 — verified against D11 (an 8 GiB limit with ZIP64 refused; the standard writer needs ZIP64 once the directory starts beyond 2 GiB). Pre-existing.
- PR-MED-111 — verified (`_remove_part` opens its own handle with no sharing, so it cannot run while the writer's handle is open). Fix-induced by D14 (7).
- PR-MED-112 — verified (`link_state` is an `lstat`, and the location helper resolves the path before it checks for a network location). Fix-induced by D14 (6).
- PR-MED-113 — verified against D14 (6), (12) and Task 3.2. Fix-induced.
- PR-MED-114 — verified against D14 (17), (20) (an entry whose audit month was pruned can never gain a coverage row). Fix-induced.
- PR-MED-115 — verified against D14 (1), (14). Fix-induced.
- PR-MED-116 — verified against D11 and D14 (7). Pre-existing in part.
- PR-MED-117 — verified against D13 (o) and D14 (11). Fix-induced.
- PR-MED-118 — verified (the printable handouts are a separate git-ignored folder; the downtime procedure requires the current sheet at hand). Fix-induced by D14 (23).
- PR-MED-119 — verified against D14 (22) and the retention sweep's held entries. Fix-induced.
- PR-LOW-120 — verified (`test_install_layout.py` checks the allow-list both ways). Fix-induced by D13 (m).
- PR-LOW-121 — verified; record-only (Flow 2 and the schema paragraph carry no round-7 pointer).
- PR-LOW-122 — verified; record-only.
- PR-LOW-123 — verified; record-only (`release.yml` has one installer-build step).

#### Round 8 — applied at the consolidation rewrite (2026-11-25)

The HELD findings above were applied by the rewrite of the plan body, not as a third layer. Where each landed (new numbering):

- PR-HIGH-099 — D5 (the open check: a damaged entry is left out; `not_restorable` counted) and D14's rule for older backups; decision 0.11.
- PR-HIGH-100 — D14's operating rules (a backup made before an audit reset is kept until restored from); decision 0.12.
- PR-HIGH-101 — D5 (a strict listing; an uninspectable child is left out and counted) and D9 (`backup_snapshot` strict; `row_state` reads an uninspectable month as `unreadable`).
- PR-HIGH-102 — D1 (Back up refuses while the audit record cannot be read; the entries-only file is Excluded).
- PR-HIGH-103, PR-MED-109 (its timestamp half), PR-MED-114 — decision 0.10: no per-row coverage exists; D10's date-based status line counts dated entries only.
- PR-HIGH-104 — D12 (the two callers' read-then-record order is unchanged; no return value carries a fact).
- PR-HIGH-105 — D9 (`record_past_session(recording_held=)`), Task 1.1.
- PR-MED-106 — D12 (an empty ordinary key file blocks nothing; a key file that stays uninspectable is the downtime procedure's step).
- PR-MED-107 — D2 (the manifest is one structure; the open check binds the label to the member set).
- PR-MED-108 — D8 (`skipped_present` only when the key opens the id-bound label; `conflict_wrong_key`).
- PR-MED-109 — D8 (`repaired` with `repair_cleanup_failed` beside it; `failed_repair` only when the replace did not commit).
- PR-MED-110 — D2 (1 GiB, no ZIP64) and D5 (`too_large` before any file exists).
- PR-MED-111 — D6 (the handle is closed first, then the identity-checked removal).
- PR-MED-112 — D7 (the text-first refusal before any file-system call).
- PR-MED-113 — D8 (the second whole-file verification runs on a worker).
- PR-MED-115 — D5 (`nothing_to_back_up` against `nothing_could_be_read`) and D14's rule for an empty archive.
- PR-MED-116 — D6's named residue and D14's rule for `.csbk.part` files.
- PR-MED-117 — D11 (the gate's state is a field of `_situation` for every action).
- PR-MED-118 — P.3 (the v4 sheet in use, unused v3 handouts withdrawn).
- PR-MED-119 — D10 (both confirmations reworded).
- PR-LOW-120 — Task 1.3 (the prefix and its allow-list entry in one task).
- PR-LOW-121 — the Flows and the schema section, rewritten.
- PR-LOW-122 — D14 (the stored audit month; members comparable across two backups).
- PR-LOW-123 — H5 (the `main` commit, the run id with its installer-build step, the attestation).

Rounds 6 and 7, where the rewrite changed how a finding is met: the audit-row findings (PR-MED-046 … 049, 083, 084, and the coverage half of 048 and 074) are moot or reduced under decision 0.10, with the month check, the same-month rule and the `absent` / `unavailable` split kept in D9; the per-writer flag checks (PR-HIGH-039, 040, 075, PR-MED-051, 052) are replaced by D11's one gate; the file-number checks on a destination or a backup source (PR-HIGH-071, D13 (g), (h)) are replaced by SHA-256 binding in D6 and D8; PR-MED-088 and D14 (19)'s entries-only case no longer exists (D1). Every other round 6–7 finding is carried into the body under its own decision.

#### Superseded correction layers D13 and D14 — kept as a record (they are NOT instructions; the body above replaces them)

- **D13 — Round 6's corrections (2026-11-25; plan peer-review round 6, PR-HIGH-036 … PR-LOW-062, each verified against the code at `5d63ed6`).** Where a sentence above or a task below differs from an item here, THIS item is the instruction; each such place carries a "Round 6" pointer.
  - **(a) Deleting an entry that holds a kept recording (PR-HIGH-036; the practitioner: "Add it to the plan (Recommended)").** A backup holds each entry's key, and that key also wraps the entry's `audio-key.enc`, so removing `key.dpapi` no longer destroys a recording whose two sidecars outlive a failed unlink. `delete_entry` (Delete now and expiry) therefore, after the `.staging\<id>` removal of D5 and BEFORE `_remove_key_first`: reads the entry's recording state once (`_recording_state`); when a live audio key is held it overwrites `audio-key.enc` with zeros in place, flushed, synced and read back, through ONE private helper extracted from `delete_recording` (that method's behaviour unchanged); an overwrite that cannot be completed and verified, or a recording state that cannot be read, is `delete_failed` with `key.dpapi` and every other file untouched (retryable). The audit facts follow the existing rules (the kept fact before, the deletion after). Rollback: a build below 0.5.0 deletes the old way, so its rule reads "Delete recording first, then Delete now" for an entry that was ever backed up. Round 7 (2026-11-25): the mechanics are D14 (2), the rollback step D14 (3).
  - **(b) Restore's add never calls `_publish` (PR-HIGH-037).** `_publish` removes its destination key-first (a retried Complete's rule). `restore_entry` publishes through a new `_publish_new(staging, final)`: `final` must be CONFIRMED absent (`link_state` and an `lstat` answering not-found; anything else refuses), then one `os.rename`, which on Windows fails when the destination exists; no removal of `final` on any path. A destination that appeared after staging is counted `skipped_present`, the staging removed key-first, the destination byte-identical. Round 7 (2026-11-25): a late destination is `skipped_collision` (D14 (18)).
  - **(c) The writer copies only ordinary files of the checked folder (PR-HIGH-038).** For every entry member and audit row: `link_state(path)` is False, the file is opened once, and on the opened handle `os.fstat` says a regular file with the same device and file number as `os.lstat(path)`; the bytes hashed and written are the bytes read from that handle, capped (`MAX_ROW_FILE_BYTES` for a row; a per-member cap for an entry file). Any other state skips the ENTRY whole (`skipped_unreadable`) or the row (`skipped_gone`). A linked or replaced member never puts outside bytes into the ZIP. Round 7 (2026-11-25): D14 (4), (5); a row left out is recorded as unknown (D14 (9)).
  - **(d) Strict listing and whole entries (PR-HIGH-043).** `prepare_backup` enumerates with `_committed_dirs(strict=True)`; an archive that exists but cannot be listed refuses the run (`archive_unreadable`), never an audit-only "success". Hop C holds ONE entry's members at a time and writes them only once every member named in the snapshot has been read; an entry with a member gone or changed is left out whole — not in the manifest, not counted, not credited by `record_backed_up`. Round 7 (2026-11-25): the required set comes from the label and the counts from D14 (4), (14), (1).
  - **(e) One admission, with no yield (PR-HIGH-039, PR-HIGH-040).** `session_busy()` is built in `MainWindow` and is True when ANY of these holds: `_live_session_ids()` is non-empty; `recovery_screen.protected_session_ids()` is non-empty (a recovered transcript awaiting Complete or Discard is in neither list); `recovery_screen.is_busy`; either Recovery list has a row. Each flow, AFTER its last dialog has returned and on the GUI thread, re-evaluates `session_busy()` and takes the run flag in one call with no event-loop yield between the two, and only then starts its first worker; busy refuses with the line and starts nothing. Hop B's and Restore's later re-checks stay as a second line. Round 7 (2026-11-25): D14 (11).
  - **(f) Key transfer and failure text (PR-HIGH-041).** A run-owned object on the GUI thread (`BackupRun`) holds `k_b: bytearray | None`. Hop A's worker writes the derived key into it; no signal carries a key. `prepare_backup(store, audit, k_b, *, now, channel)`. The writer's re-read verification is `verify_backup_file(path, k_b)` — the reader's core taking the derived key; `open_backup(path, passphrase)` is derive plus that core — so the passphrase buffer is zeroed as soon as hop A returns and is never kept for verification. Every worker body catches `Exception` and reports a closed code (`BackupFormatError(code)` / `BackupRunError(code)`), so `TaskThread.failed`'s `type: message` is a type and a code; anything unforeseen is `unexpected`, with its type name logged and nothing else. `SessionCrypto.export_key()` returns immutable `bytes` and `AESGCM` keeps its own copy: "zeroed in `finally`" means the `bytearray`s (`k_b`, the passphrase buffer), and the tests assert exactly those; the immutable copies are named residues. Round 7 (2026-11-25): Open and Restore are D14 (12); the cleanup owner is D14 (13).
  - **(g) Open admits the source before reading it (PR-HIGH-042).** The chosen file's folder goes through `check_archive_backup_location` BEFORE one byte is read (the same refusals; the same-volume warning is not shown for a source); refused: "Copy the backup to a drive attached to this computer first." The admitted file's identity (device, file number, size) is recorded at admission and re-checked whenever the file is re-opened; a difference refuses (`source_changed`). Test: a refused source receives no file read (the conftest's network-path seam). Round 7 (2026-11-25): D14 (6).
  - **(h) The `.part` cleanup removes only this run's file (PR-MED-045).** The `finally` unlinks only when THIS run's exclusive create succeeded and the path still names that file (the create handle's identity against the path's, the `_remove_part` / `PartKernel` pattern of Export). A `.part` that was already there (the refusal) and a file that replaced ours are never removed. Round 7 (2026-11-25): the success path is D14 (7).
  - **(i) The audit row's month (PR-MED-046).** `restore_row` first validates `month` as a real calendar month for which `month_prune_at` computes (`_MONTH_RE` alone admits a month 13); `bad_month` refuses before any write. The BARE-`pre_audit` replacement of D6 applies only when the local row's file is in the SAME month folder; a sparse local row in another month (a `pre_audit` row is dated by today when its creation date is missing) is `conflict_row`, kept. Test: a retry leaves exactly one readable row for the id. Round 7 (2026-11-25): the writer validates it too (D14 (9)).
  - **(j) Coverage writes never create (PR-MED-047).** `record_backed_up` and `record_restored` do NOT go through `update(create=False)` (today `_update` opens the key with creation enabled before it looks for the row, and returns the same success for an absent row). They use a non-creating path — `_open_key(create=False)`; a store with no key and no rows means every id is `absent` and nothing is created (round 7, D14 (17): a missing key beside rows is `unavailable`) — and return one outcome per id (`updated`, `absent`, `unavailable`). Test: entries and no audit store → the absent count, the filesystem unchanged.
  - **(k) A restored entry is covered (PR-MED-048).** After an entry's publish or its repair's `os.replace` has committed, a kept readable local row gets `restored_at` AND `last_backed_up_at` advanced monotonically to the file's `made_at`; on any failure before the commit, neither. Round 7 (2026-11-25): the two times and the three cases are D14 (10).
  - **(l) The audit test fixtures (PR-MED-049).** Decoded-v3 expectations: `test_audit.py` L860, L901, L940–943, L985, L994–997, L1092. Fixtures that write version 4 as a FUTURE row today: L487, L762, L766–767, L962, L1039, and `test_schema_versions._newer` (L202–209). After the bump the future audit row is version 5; `_newer` is shared, so the audit use gets its own value and every other schema's boundary stays. Task 1.1 captures the v3 bytes from the unchanged writer at HEAD.
  - **(m) The file-name prefix has one owner (PR-MED-050).** `past_sessions_backup.BACKUP_FILENAME_PREFIX = "ClinikoScribe-backup-"` is the only place the string exists; it is added BY NAME to `test_install_layout.py`'s `_NON_PATH_LITERALS` (a named pin change: a file-name prefix, no folder is built). That test's version check derives from `pyproject.toml` and needs no literal edit.
  - **(n) The development tick on a backup refusal (PR-MED-051).** Every Start refused for a run clears an armed development tick and announces it (`disarm_development_tick(announce=True)`); the consent tick is kept, as in the discard branch. The warm-up hold stays the one refusal that keeps both.
  - **(o) Chrome's refusal ends with the run (PR-MED-052).** The bridge keeps a refusal while its situation is unchanged, and a finished backup changes none of today's situation values. The run flag's state joins the Start situation (or the bridge drops a `backup_running` refusal and republishes when the flag clears). Test: the same note loses the line with no second Start.
  - **(p) Task 0.7 is the frozen self-check (PR-MED-053).** The packaged app's existing `--self-check-offline` path (`app.run_offline_self_check`, run by `scripts/build-release.py --audit`, exit code only) gains one step: derive 32 bytes with Argon2id from a fixed non-secret string at small fixed parameters; a failure is exit `SELF_CHECK_KDF = 3`. Every build's audit then proves Argon2id in the frozen bundle. The executor writes it with a unit test; there is no `packaging/spike` file and no `[operator]` step. A failed audit stops the build, and D3's scrypt fallback is then a dated decision.
  - **(q) Delete now's wording (PR-MED-054).** `DELETE_CONFIRM_MESSAGE` no longer says "cannot be recovered": (round 7: the sentence is D14 (22)) The rule covers EVERY backup made before the deletion, one made today included. The clinician review guide's "for good" and the patient sheet's "cannot be undone" are amended in the same sense (Task 4.2). Task 0.8's grep adds `cannot be recovered|cannot be undone|for good|lost with it|nowhere else|cannot be read again|nothing it keeps has a backup`.
  - **(r) More sentences the feature makes false (PR-MED-055).** `docs/practice/downtime-procedure.md` "Past sessions problems" (an unreadable entry "cannot be read again on this account": now points to the key repair); `docs/practice/README.md` ("nothing it keeps has a backup"); `docs/security/data-flow-map.md` flow 22 (the four v3 columns "exported last"), the non-flow "exist on disk ONLY encrypted under per-session keys" and the Chrome summary's "its Past-sessions label and nowhere else"; the threat model's AUDIT V3 paragraph ("four columns LAST").
  - **(s) What a lost drive shows without the passphrase (PR-MED-056).** The ZIP directory and the header are readable by anyone: that the file is a Clinic Scribe backup, when and by which version and channel it was made, the counts, each entry's session id, the audit months, and each member's kind and size. Transcripts, notes, names and every other audit field need the passphrase (round 7, D14 (24): the audit rows' session ids and months are visible too). The threat model, the retention schedule and (in plain words) the downtime procedure say exactly that; the container format stays as decided.
  - **(t) P.2 and shadow mode (PR-MED-057).** An ABSENT `pilot.json` is shadow OFF (only a present, unreadable file fails closed to on), so a fresh data folder records in normal mode. P.2 therefore ticks Shadow mode in Settings before the first Start, saves a note in at least one of the two recordings, and before restoring moves BOTH `past_sessions` and `audit` aside, so the restore runs into an empty synthetic audit store. It then checks the restored entries open, show the shadow mark, and refuse "Copy saved note" with the shadow reason.
  - **(u) Task 3.2's failures, one outcome each (PR-MED-058).** (1) A tampered member is a hash mismatch at Open (C8): the whole file is refused before anything is written. (2) An authentic file whose entry the readers refuse (a wrong key paired with an id): that entry alone is `failed_verify`, its staging removed key-first. (3) A repair whose read-back or open fails, cleanup succeeding: the old key file stays and `.staging\<id>` is GONE. (4) The cleanup itself fails: `failed_repair`, the folder left to `clean_staging`. (5) The process dies before the cleanup: `clean_staging` removes the folder at the next start and the repair can be retried. Round 7 (2026-11-25): the codes and the cleanup check are D14 (18).
  - **(v) The volume seam (PR-MED-059).** `WindowsLayer` gains `volume_of(path) -> tuple[str, int]`: the mount point of the volume holding `path` (`GetVolumePathNameW`) and that volume's `GetDriveTypeW`. `check_archive_backup_location` judges the drive type by it (a volume mounted into a folder is judged as itself) and "same volume" as equal mount points of the destination and the data folder; a volume that cannot be inspected is refused. No `st_dev`, no direct `os.stat` of a drive. `check_export_location` keeps its drive-letter rule and its named residue. Round 7 (2026-11-25): the return value is D14 (16).
  - **(w) The rollback rule's wording (PR-MED-060).** It describes rolling back to 0.4.2: a v4 row is `_NEWER` there (kept, left out of its CSV, never overwritten). Start-up `repair_kept_facts` attempts two audit writes only for a committed entry that HOLDS A KEPT RECORDING, whose label reads and whose month is not pruned; each fails on a `_NEWER` row and adds to the failure count. An audio-free restored entry causes none. The older sections' substantiated content limits still apply cumulatively (round 7, D14 (27): 0.3.7 is not one of them).
  - **(x) P.3's record (PR-LOW-061).** Counts, the file's size, that Open then Close succeeded, and that the status line is ABSENT after the backup. The 7-day reminder is exercised on synthetic data in the tests. Round 7 (2026-11-25): D14 (19).
  - **(y) The close and the passphrase field (the round's spot-checks).** The `closeEvent` branch of D8 (v) goes BEFORE `note_screen.prepare_close()`, so a refused close has no suggestion-job side effect; the generic worker check does not list the Past sessions page, so the branch is needed. With the fake clipboard, Copy and Cut by shortcut and by context menu on a passphrase field place nothing: asserted by a test, not assumed from the echo mode.
  - **(z) Documents and consent before any real backup (PR-HIGH-044; the practitioner: "Before the first real backup (Recommended)").** Every kept transcript so far was recorded under `patient-info-v3`, which says the program makes no backup. So: the merge that carries the amended patient sheet lands on `main` only after the tenth Task 9.1 consultation is scored (C13 — required, not only recommended), so v3 stays the sheet in use throughout the ten; Phase P runs P.1, P.2, then P.4 (the documents read and each dated line approved), then the decision P.4b, and only then P.3. No real backup is made before P.4 and P.4b are recorded.
- **D14 — Round 7's corrections (2026-11-25; plan peer-review round 7, PR-HIGH-063 … PR-LOW-098, each verified against the code at `5d63ed6`).** Same rule as D13: where any sentence elsewhere — a D13 item included — differs from an item here, THIS item is the instruction; each such place carries a "Round 7" pointer.
  - **(1) A backup says whether it is complete (PR-HIGH-063).** The manifest carries content-free counts of what the run left out: `omitted_entries` (unreadable, incomplete, changed or gone) and `omitted_rows`, and `audit_included`. The success line and Open's summary say "Complete backup" only when both counts are 0 and the audit record is included; otherwise "This backup is NOT complete: N entries and M audit rows could not be included. Keep your older backups." Decision 0.5's operating rule is worded everywhere (Delete now's confirmation, the documents) as: make a new backup, and destroy the older ones only once the new one says it is complete.
  - **(2) `delete_entry`: one custody read, three results (PR-HIGH-064, PR-HIGH-065, PR-MED-095; replaces D13 (a)'s mechanics, keeps its decision).** Task 1.7 owns the whole sequence, in this order: (i) remove `.staging\<id>` through `_remove_key_first_unless_link` (the step D5 describes; a no-op until Phase 3 creates such folders); (ii) read `_audio_key_state(entry / AUDIO_KEY_FILENAME)` ONCE — not `_recording_state`, which returns `none` for a live key whose `audio.enc` is missing; `live` → overwrite with zeros through the helper extracted from `delete_recording`; `zeroed` or `absent` → nothing to do; `unknown` → `PastSessionError("delete_failed")` with nothing touched; (iii) `_remove_key_first(entry)`. Results: the overwrite could not be completed and verified → `delete_failed` (the line says the entry was not deleted and to try again; it no longer says nothing changed); the overwrite was verified and step (iii) then failed → `PastSessionError("delete_failed_recording_gone")`, its own line ("The recording was deleted. The rest of this entry could not be deleted - try again."), and the caller records the recording's deletion fact as it does for a `gone` recording; success → `delete_entry` returns whether it destroyed a live audio key, and the two callers (Delete now, the retention sweep) take that fact from the return value, never from their own earlier read. A persistently `unknown` key file (held by another program) is documented in the downtime procedure: close the program holding it, or use Delete recording, then Delete now; it is never reported as destroyed. Tests: a live key with no `audio.enc`; a locked sidecar; the overwrite verified then the entry key's removal failing, and the retry.
  - **(3) Before rolling back below 0.5.0 (PR-HIGH-066; with D13 (w)).** A build below 0.5.0 runs its retention sweep at start-up and hourly, deleting the old way with no audio-key step. The rollback section therefore opens with a step done on 0.5.0 BEFORE the older installer runs: for every entry that holds a recording, Delete recording (or, to keep the recordings, set retention to "Until I delete them" so the older build expires nothing); then on the older build the manual rule stays "Delete recording first, then Delete now". The section says plainly that this matters only for an entry that was ever in a backup.
  - **(4) The snapshot binds one generation of each entry (PR-HIGH-067, PR-MED-078).** Hop B (which already unwraps the key and reads the label) records per entry: the SHA-256 of `label.enc`'s bytes as it read them, the REQUIRED member set derived from the authenticated label — `label.enc`, `transcript.enc`, `note.enc` when `has_saved`, `generated.enc` when `has_generated` — and each required member's size, modification time (ns) and file identity. An entry with a required member missing at hop B, or holding a content member the label does not call for, is `skipped_incomplete` (omitted, counted, never credited). Hop C compares each opened member's `fstat` with the snapshot and `label.enc`'s hash with the recorded one; any difference omits the entry whole as `skipped_changed`. Test: a same-size replacement of an entry between hops B and C is not in the file.
  - **(5) Only the store's own files are copied (PR-HIGH-068; extends D13 (c)).** Every member read for a backup — and `key.dpapi` in hop B — must also have a link count of 1 (the `_is_own_key_file` rule the audio key already uses), and in hop C the entry folder's `link_state` is re-read as `False` before any member under it is opened. A hard-linked member or a re-pointed folder omits the entry; an outside file's bytes never enter the ZIP (tested).
  - **(6) Open admits the FILE, and Restore re-authenticates it (PR-HIGH-069, PR-HIGH-070; extends D13 (g)).** Before any byte is read: the chosen path must be an ordinary file, not a link (`link_state` False), and the folder that its RESOLVED path sits in must pass the location rule; a link, or a resolved location that is refused, is refused with the D13 (g) line. The authenticated manifest stays in memory from Open to the end of the run. Restore's first act — before any audit row is written — is to verify the whole file again with the held key (no second derivation) and require a manifest identical to the one shown; after that every member is hash-checked against that manifest at the very read that feeds a write. A mismatch is `source_changed`: the run stops, nothing further is written, and rows or entries already restored (each individually verified) stay. Device, file number and size are only a quick first check.
  - **(7) The writer owns its file from create to publish (PR-HIGH-071; extends D13 (h)).** ONE handle, opened read-write by the exclusive create, is kept for the whole of hop C: written, flushed, synced, then verified by reading back THROUGH THAT HANDLE (so what is verified is what this run wrote), then closed and published by `os.rename`, which on Windows never replaces an existing file. After the rename the final path's identity must equal the handle's recorded identity; if not, the run fails (`publish_unverified`), nothing is credited, and the final path is left alone. `record_backed_up` runs only after that check. On failure the `.part` is removed through the still-open handle's identity (D13 (h)). Named residue: between the close and the rename the file is addressed by path, as every atomic write in the app is.
  - **(8) A key repair replaces only the blob it classified (PR-HIGH-072).** Immediately before the repair's `os.replace`, the entry folder's link state is re-read (`False`) and the destination `key.dpapi` is read once more and must equal, byte for byte, the blob the planner classified as refused; any difference abandons the repair for that entry (`skipped_changed`, staging cleaned), and the local key is untouched. Test: a local key that becomes readable after classification is not overwritten.
  - **(9) Audit rows the backup could not copy stay 'unknown' (PR-HIGH-073, PR-MED-082).** `backup_snapshot` validates each row's month as a real calendar month for which `month_prune_at` computes, and detects an id with more than one row file. A row that cannot be copied — unreadable file, over-size, changed, two files for one id, uncomputable month — is left out, counted in `omitted_rows`, and its id is listed in the manifest's `rows_unknown` (ids only). At restore an id in `rows_unknown` reads as an `unreadable` row from the backup's side, so its entry is `skipped_unknown_row` on any destination. The manifest's `rows: {id: month}` therefore never has to hold two rows for one id.
  - **(10) Coverage follows the entry, never the row import (PR-HIGH-074, PR-MED-084; replaces the `included` rule of D6 and extends D13 (k)).** `restore_row` drops its `included` parameter: an imported or replacing row keeps the latest of the local and incoming rows' OWN `last_backed_up_at` and never receives this file's `made_at`; its `restored_at` is the latest of the two rows' own values and `now`. This file's coverage is granted per entry by `record_restored(id, *, made_at, at)` — `last_backed_up_at` advanced monotonically to `made_at`, `restored_at` to `at` (the restore's own time), each field by its own rule — and only (i) after an `add` has published, (ii) after a repair's replace has committed, or (iii) for a `skipped_present` entry whose local content members match the manifest's names and hashes (the same generation). A present entry that differs gains nothing.
  - **(11) The run flag is consulted wherever the archive or the audit record is written (PR-HIGH-075; extends D13 (e)).** `session_busy` is an admission snapshot; a session can become visible after it. So each of these also consults the run flag at the moment it acts, after its own last dialog, and refuses with the run line: Recovery's Resume, Open review, Discard and Discard unreviewed; Chrome's adoption of a queued recording and Chrome-side Discard; on the Past sessions page Delete now, Delete recording, Export recording, Export CSV, the audit Reset and the retention selector (the last two already named in D8). Test: a Recovery row made visible only after the backup's admission cannot be discarded or adopted until the run ends.
  - **(12) Open and Restore: one authenticated reader, owned by the run (PR-HIGH-076; extends D13 (f)).** Hop A of Open derives the key into the run object and builds a `BackupReader` there: the path, the authenticated manifest, the held key. The worker's signal carries only a key-free summary (counts, dates, version, channel, the plan's inputs). `plan_restore(reader, …)` and `restore_backup(reader, plan, …)` run on the GUI thread and take the reader explicitly; the reader unwraps one entry key or the audit key at a time into a `bytearray` zeroed after use. `open_backup(path, passphrase)` as a single call remains only as the test and tool convenience.
  - **(13) One cleanup owner for the secrets (PR-MED-087).** The run object is created when the passphrase dialog is accepted and owns the passphrase buffer, the key and the run flag. Its `close()` — idempotent — zeroes both buffers and releases the flag, and is called on EVERY exit: a cancelled save or open dialog, a refused or declined location, a busy refusal, a failed dispatch, any hop's failure, Close, and success. Each worker's `finished` signal is connected as a fallback: a worker that ends with neither result signal (an exit `TaskThread` does not catch) is treated as `unexpected` and closes the run. Tests for each exit.
  - **(14) Header counts are upper bounds; the manifest's are the facts (PR-MED-079).** `header.json` is written first and carries the PLANNED counts from hop B; they serve only the preflight's bound. The manifest carries what was actually written, and the reader requires the manifest's counts to be no greater than the header's. If hop C ends with no entry and no row written, the run is `nothing_to_back_up`: the `.part` is removed and no file is published.
  - **(15) The preflight walks the directory itself (PR-MED-080).** `zipfile` builds one object per central-directory record until the declared byte length is consumed, whatever the count field says. So before `ZipFile` is constructed the preflight reads the central directory (its size already bounded, and now also ≤ 256 bytes × the declared count), walks its records with the standard library's `struct` only, and refuses unless the number of records equals the end record's count, every name is ≤ 128 bytes and no record has an extra field or comment. Test: the refusal happens with `ZipFile` never called.
  - **(16) `volume_of` names the volume, not a path to it (PR-MED-081; replaces D13 (v)'s return value).** The layer returns the volume's GUID name (`GetVolumeNameForVolumeMountPointW` on the mount point) and its drive type; "same volume" is equal GUID names, so a drive letter and a mounted folder of one volume compare equal (tested with a fake layer). Named residue: a virtual disk is judged as the volume it presents, not by where its backing file lives.
  - **(17) `absent` means confirmed absent (PR-MED-083; corrects D13 (j)).** `_open_key(create=False)` raises `_NoKey` only for a store with no key AND no rows; a missing key beside rows is `AuditUnavailable("key_missing")`. So: `_NoKey`, or a readable store with no row for the id → `absent`; `key_missing`, `key_unreadable`, `unavailable`, or a row that is `newer` or unreadable → `unavailable`. The same split applies to `backup_snapshot` (entries-only on `AuditUnavailable`, with `audit_included` false). Tested both ways with nothing created.
  - **(18) Every outcome has a name and a count (PR-MED-085, PR-MED-086; corrects D13 (b), (u)).** A key that unwraps to something other than a 32-byte key (`bad_length`) is `skipped_foreign_key`. A destination that appears after staging is `skipped_collision` (never `skipped_present`, which means a verified local key). D13 (u) cases (3) and (4) both count `failed_repair`; (4) also logs `repair_cleanup_failed`. The repair's cleanup decides between them by checking that `.staging\<id>` no longer exists after `_remove_key_first` returns (that helper reports the key's removal, not the folder's). In `_remove_key_first` the temporary name `key.dpapi.tmp` is unlinked BEFORE `key.dpapi`, so a failure there returns False with the committed key still present — ordinary deletion's contract ("False: nothing else touched") is unchanged. One table in the code maps every planner and execution outcome to exactly one summary or final-report count, and a test walks it.
  - **(19) Checking a backup while the audit record needs attention (PR-MED-088).** With the local audit key unreadable, Open still verifies the file and shows the summary, with Restore disabled and the line "Start a new audit record first". After an entries-only backup the status line follows the real coverage (no row was updated, so it may show at once). P.3 records the reminder state that the run's own outcomes predict, whatever it is.
  - **(20) The reminder's first seven days (PR-MED-089; within decision 0.6).** With no backup ever recorded, the line shows only once the OLDEST not-backed-up entry is more than 7 days old by its audit row's date; an entry with no readable row date counts as old enough (unknown is shown, not hidden). `backup_status_line` therefore takes each row's date; no ledger. Tested on the first day and at the seven-day boundary.
  - **(21) After a restore the page shows the new state (PR-MED-090).** `_publish_new` and the key repair drop the store's cached dates and its cached unreadable-label mark for the id (the existing rule for any write). When the run ends the page, if visible, re-lists BEFORE the outcome line is shown (re-listing clears the message); a hidden page still holds no names.
  - **(22) The deletion wording (PR-MED-091; replaces D13 (q)'s sentence).** Delete now: "…Its notes and transcript are deleted from Past sessions for good. A backup made before this deletion still holds them - make a new backup and, once it says it is complete, destroy the older ones. Press Confirm delete to delete it." The shorter-retention confirmation: "…Every kept session older than that is deleted now from Past sessions for good; a backup made earlier still holds it." Its exact-text test (`test_ui_screens.py`) and the design system's quote change in the same task (2.3, with 4.4).
  - **(23) The approved sheet stays current until P.4 (PR-MED-092; with D13 (z)).** Task 4.2 writes `patient-info-v4` as a clearly marked DRAFT beside the approved v3 text; v3's version line, the consent example, the form to sign and every sibling sentence naming the current sheet stay v3. P.4's approval is one commit that makes v4 current in all of those places together. The app strings a patient or the practitioner reads (the confirmations of (22), the retention warning) are listed in P.4 and approved there too. The development-recording consent's wording, which the app ships verbatim under `development-consent-v1`, is NOT edited: the note that a backup never holds a recording goes in the practice README and the practitioner-facing notes, outside the consent text.
  - **(24) What a lost drive shows, stated exactly (PR-MED-093; corrects D13 (s)).** Readable without the passphrase: each archive entry's session id, each AUDIT row's session id and the year and month of its session — including sessions that have only an audit row — the member kinds and sizes, and the header. Everything else needs the passphrase. The threat model's sentence that the encrypted name label exists nowhere else gains "and in backup files".
  - **(25) The dependency floor (PR-MED-094).** `desktop/pyproject.toml` requires `cryptography>=44` (the first release with Argon2id; today it says `>=43`), changed in Task 1.3; the self-check step's unit test runs in the developer environment too.
  - **(26) Task 0.7 and H5 (PR-MED-096; with D13 (p)).** Task 0.7 is done when the self-check step, its exit code 3, the code-3 explanation in `scripts/build-release.py`'s diagnostic and their unit tests are in. The frozen proof belongs to H5: the `Release` run's audit step passing is the record (a run id and its exit status); there is no probe output to paste.
  - **(27) The rollback boundaries (PR-LOW-097; corrects D13 (w)'s last sentence).** The release document lists only the substantiated limits of persisted content; 0.3.6 reads every 0.3.7 entry, so 0.3.7 is not such a boundary (its differences are in what is displayed and generated).
  - **(28) P.3 needs an actual approval (PR-HIGH-077; with D13 (z)).** P.3 may run only when P.4 records every line approved (none sent back) AND P.4b records option (a). Wording sent back, option (b) while the reviewer's answer is outstanding, or option (c) each leave P.3 on hold; (c) needs its own approved design, which must also settle the audit record's scope, and a new build.

### Round 9 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 1)

Source: Codex gpt-6.2-astra high plan peer-review

`plan` below refers to `.cursor/plans/plan-past-sessions-backup.md`. Source references are against HEAD `5d63ed6`.

**PR-HIGH-124 — The app can direct the practitioner to destroy the only usable older backup.**
Materiality: build-affecting
At `plan:101` and `plan:152`, zero omissions is enough to display “Nothing was left out” and satisfy the Delete now instruction. An entry with an authenticated newer-schema audit row is copied, increments `not_restorable`, and is skipped on restore (`plan:126`, `plan:133`). Both omission counts can therefore be zero while an older backup is still needed. Separately, `plan:166` permits destruction on “nothing to back up,” although a successful audit reset creates precisely such an empty audit store and the same paragraph says to retain its predecessor. See `desktop/src/scribe_desktop/audit.py:1091` and `:1119`.
Proposed amendment: Make the backup result and Delete now wording use D14’s full rule, show `not_restorable` from the final manifest, and state that an empty store or an unresolved pre-reset restore gives no permission to destroy an older backup.

**PR-HIGH-125 — A session can pass the backup’s open check and fail to open in Past sessions.**
Materiality: build-affecting
D5 parses the label but specifies only authentication for the transcript, saved note and generated note (`plan:127`). The real readers also parse the transcript, verify the saved note’s session binding and transcript digest, and validate the generated record’s schema, size and session ID. Two individually authentic files can fail those checks together. The writer and Open would accept them, then the staged restore at `plan:135` would reject them. See `desktop/src/scribe_desktop/transcription.py:1434`, `desktop/src/scribe_desktop/session_store.py:1012`, `:1728` and `desktop/src/scribe_desktop/past_sessions.py:763`.
Proposed amendment: Share the readers’ byte-level validation with `entry_opens` and test that an authentic saved note paired with the wrong transcript revision is counted as damaged before publication.

**PR-HIGH-126 — Staging cleanup can reach another entry’s key.**
Materiality: build-affecting
The add and delete paths check `.staging\<id>` without requiring `.staging` itself to be safe (`plan:135`, `plan:161`). An ordinary child reached through an existing parent junction passes that child check. HEAD checks the parent separately for this reason. Moreover, `_remove_key_first_unless_link` explicitly returns **True** for a linked child, the opposite of D12’s required refusal. Neither case requires a file to change during the run. See `desktop/src/scribe_desktop/past_sessions.py:658`, `:860` and `:2139`.
Proposed amendment: Require a confirmed safe staging parent and a strict child check before add, repair or delete touches staging, preserve the existing helper’s caller contract, and verify that a pre-existing parent junction leaves its target’s key untouched.

**PR-HIGH-127 — Routine rollback requires irreversible destruction of recordings the practitioner intends to keep.**
Materiality: build-affecting
D13 directs the practitioner to delete every held recording whose entry was ever backed up before even reinstalling 0.4.2 (`plan:162`, `plan:284`). None of those recordings can be recovered from the backup (`plan:114`). On 0.4.2 the risk arises when an entry is subsequently deleted or expires. Its dedicated Delete recording action already zeroes and verifies the recording key. See `desktop/src/scribe_desktop/past_sessions.py:1058`, `:1536` and `:2115`.
Proposed amendment: For rollback to 0.4.2, suspend automatic expiry for the duration of the downgrade, require Delete recording before an intentional deletion of an entry holding audio, and reinstate the previous retention setting on return to 0.5.0.

**PR-MED-128 — The first ZIP member depends on a length the writer learns only at the end.**
Materiality: build-affecting
The header carries `manifest_bytes` and its exact bytes bind the manifest (`plan:117`, `plan:118`). D6 writes that header first, while D5 discovers the final members, hashes and omissions as it reads and writes the payload (`plan:127`, `plan:129`). A failed entry check changes the final manifest length. The reader also needs a bound on the actual `manifest.enc` member before reading it.
Proposed amendment: Define the header field as an upper bound or remove it, and independently enforce the 16 MiB limit on the actual manifest member before reading or decrypting it.

**PR-MED-129 — Publishing an entry and recording `archived` can fail between steps with no retry path.**
Materiality: build-affecting
D8 publishes without `pending`, then updates a local audit row from `none` to `archived` (`plan:135`). The public audit update can return `False`, and a power loss can also intervene. On retry the planner classifies the published entry as `skipped_present` (`plan:133`). Startup repairs newly reconciled pending entries and entries with recording evidence. This restored entry has neither. See `desktop/src/scribe_desktop/audit.py:815`, `:831` and `desktop/src/scribe_desktop/app.py:456`, `:487`.
Proposed amendment: Define a retryable audit update for an already-published matching entry whose local row still says `none`, report a failed update, and test interruption immediately after publication.

**PR-MED-130 — Some audit inputs have no representable disposition.**
Materiality: build-affecting
D9 sends a row that fails ID validation to `unknown_ids`, but D2 requires every manifest ID to match `SESSION_ID_PATTERN` (`plan:118`, `plan:141`). HEAD excludes invalid filenames from its row inventory (`desktop/src/scribe_desktop/audit.py:1222`). A second gap occurs for a valid ID and authenticated plaintext that fails `_decode`. D8 knows to skip its entry, but the row-first importer defines outcomes only for a decoded row or `_NEWER` (`plan:133`, `plan:143`). `_decode` has a third result in practice: it raises `ValueError` (`desktop/src/scribe_desktop/audit.py:416`, `:458`).
Proposed amendment: Specify the inventory treatment of invalid filenames and a counted disposition for authenticated undecodable rows, then verify that neither case prevents unrelated valid rows and entries from being recovered.

**PR-MED-131 — An audit-only restore has no accurate final report.**
Materiality: build-affecting
The plan explicitly tests a backup with audit rows and zero sessions (`plan:216`). Its summary requires a session date range, and its final line reports only sessions, repaired keys and differences (`plan:107`, `plan:151`). A fresh computer can recover every audit row and display only “Restored 0 sessions.” The same text cannot account for actual row conflicts, skipped months, or committed repairs with cleanup failures as required by `plan:136` and `plan:138`.
Proposed amendment: Define the zero-session summary and final lines for actual entry and audit outcomes, then drive an audit-only restore and a partially successful restore through the UI tests.

**PR-MED-132 — The sweep contract describes the wrong failure behavior and duplicates an existing result.**
Materiality: build-affecting
`plan:78` and `plan:161` say the sweep holds an entry when the preceding audit write fails. HEAD proceeds for a **live** recording and holds an entry for an unrecorded **already-gone** recording. It also already returns `RetentionSweepReport.kept`, populated from the same single read that `plan:144` and Task 1.1 propose to record in a new `held` field. See `desktop/src/scribe_desktop/past_sessions.py:437`, `:1561`, `:1621`, `:1647` and `desktop/tests/test_past_sessions.py:2220`.
Proposed amendment: Preserve and test the two existing callback failure outcomes, and pass `session_id in report.kept` to the expiry audit write.

**PR-MED-133 — Backup admission can disable Stop during voice enrolment.**
Materiality: build-affecting
D11 defines busy admission using `closeEvent`’s generic list plus Past sessions (`plan:155`, `plan:222`). Voice enrolment is checked in a separate branch before that list. It has an active Stop control and can be running with no protected session ID. Navigation to Past sessions is available, so the archive gate can disable the page containing Stop. See `desktop/src/scribe_desktop/ui/main_window.py:1176`, `:1588`, `:1613` and `desktop/src/scribe_desktop/session.py:1812`, `:1835`.
Proposed amendment: Include the existing controller and practitioner-screen enrolment checks in admission and test that enrolment alone refuses the archive run while Stop remains available.

**PR-MED-134 — A successfully deleted entry can be reported as a session omitted from the next backup.**
Materiality: build-affecting
D5 attempts the key check for each non-pending ID-shaped child and counts a failed key read as `unreadable` (`plan:126`). HEAD defines a committed entry by the presence of `key.dpapi`. Successful deletion removes that key first and permits a directory to remain after best-effort cleanup. The next backup, specifically requested after Delete now, can encounter that ordinary residue and tell the practitioner to keep an older copy containing the deleted session. See `desktop/src/scribe_desktop/past_sessions.py:868`, `:1702` and `:2115`.
Proposed amendment: Skip a confirmed keyless cleanup remainder while continuing to count an uninspectable key, and test a backup immediately after successful key deletion with a locked residual file.

**PR-MED-135 — Promoting v4 leaves the separate consent pointing to the withdrawn sheet.**
Materiality: build-affecting
D14 requires every current-sheet reference to move to v4 at P.3, while Task 4.2 leaves the development-consent wording untouched (`plan:165`, `plan:283`, `plan:299`). Its practitioner-facing preamble explicitly requires the ordinary consent described in `patient-info-v3` (`docs/practice/development-recording-consent.md:16`). The verbatim app test pins the development consent tick and version, not that cross-reference (`desktop/tests/test_schema_versions.py:324`).
Proposed amendment: Include the preamble’s ordinary-sheet reference in the P.3 promotion, preserving the approved development tick, signed form and `development-consent-v1` identifier.

**PR-MED-136 — A missing date is displayed as proof that no backup exists.**
Materiality: build-affecting
D10 treats missing and unreadable settings identically, then displays “No backup yet” (`plan:149`, `plan:150`). D6 publishes and verifies the file **before** writing the settings (`plan:129`). An ordinary settings-write failure can therefore leave a usable backup on the drive and a subsequent status line denying its existence.
Proposed amendment: Use “No backup date recorded” for an unknown date, distinguish a published backup from a failed settings update in the immediate result, and test both together without adding a ledger.

**Spot-checked citations**

- `plan:3`, `plan:243`–`302` — 10 checked tasks out of 40 is correct. P.5 requires P.3 approval and P.4 option (a). P.1 explicitly stops before making a backup, and P.2 uses synthetic sessions.
- `desktop/src/scribe_desktop/past_sessions.py:755`, `:810`, `:895` — existing staged verification uses the actual readers, existing `_publish` can remove its destination, and startup cleans staging. A separate add-only publisher is justified.
- `desktop/src/scribe_desktop/session_store.py:641`, `:677` — the existing unwrap combines file I/O and DPAPI classification. `link_state` returns `False` for confirmed absence as well as for an ordinary path, so restore still needs a separate existence check.
- `desktop/src/scribe_desktop/audit.py:997`, `:1079`, `:1091`, `:1245` — duplicate rows are ambiguous, a missing key beside rows is distinct from an empty store, and reset quarantines the old store and creates a fresh key. Public `update` counts failures and returns `False`.
- `desktop/src/scribe_desktop/exclusions.py:493`, `:511` — the current export rule resolves the folder before testing the drive. D7’s text-first refusal is a real implementation change.
- `desktop/src/scribe_desktop/ui/recovery.py:196`, `:322`, `desktop/src/scribe_desktop/ui/bridge.py:899`, `:915`, and `desktop/src/scribe_desktop/ui/tasks.py:21` — the Recovery lists and protected IDs, bridge refusal state, and worker result/error signals exist at the named integration points.
- `desktop/pyproject.toml:19`, `desktop/requirements-build.txt:26`, `desktop/src/scribe_desktop/app.py:665`, and `scripts/build-release.py:485` — the declared cryptography floor is 43, the frozen pin is 49.0.0, and exit code 3 requires corresponding changes to the self-check and release diagnostic.
- `desktop/tests/test_install_layout.py:470`, `desktop/tests/test_ui_screens.py:11175`, `:11234`, `:11733`, `:12234`, and `docs/release/pilot-builds.md:71` — the literal inventory, wording tests and rollback-section insertion point exist. Verification was static at the user’s request.

Materiality: 13 build-affecting / 0 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 9 (2026-11-25, verified by the planning session against `5d63ed6`)

Every finding verified `build-affecting` and applied in place in the body (no correction layer).

- PR-HIGH-124 — VERIFIED (plan text: `not_restorable` could be non-zero under "Nothing was left out"; `AuditLog.reset` leaves an empty store). Applied: Flow 1's success line, D5 hop C (`not_restorable` counts written entries), D14's rule for "nothing to back up".
- PR-HIGH-125 — VERIFIED (`read_transcript` parses, `read_note` checks the session binding and transcript digest through `_verified_note`, `read_generated` decodes the record). Applied: D5's `entry_opens`, Task 1.3, `test_backup_write.py`.
- PR-HIGH-126 — VERIFIED (`_staging_linked`, `remove_pending_entry` checks the parent first; `_remove_key_first_unless_link` returns True for a confirmed-link child). Applied: D8's staging rule for add and repair, D12 step 1 in `remove_pending_entry`'s shape, the tests.
- PR-HIGH-127 — VERIFIED (plan text; `delete_recording` zeroes the key on the older build too). Applied: D13's rollback step.
- PR-MED-128 — VERIFIED (plan text: the header is written first, the manifest's length known last). Applied: `manifest_bytes` removed from the header; the preflight bounds the `manifest.enc` record; the test list.
- PR-MED-129 — VERIFIED (`AuditLog.update` returns False without raising; `repair_kept_facts` covers only entries holding a recording). Applied: D8's `archived` write and its retry, `test_restore.py`.
- PR-MED-130 — VERIFIED (`_row_paths` ignores a non-id file name; `_decode` raises `ValueError`). Applied: D9's inventory and `skipped_undecodable_row`, D8's row list, `test_restore.py`.
- PR-MED-131 — VERIFIED (plan text). Applied: D8's outcome table with both mappings, D10's summary and final report lines, Flow 3, the UI tests.
- PR-MED-132 — VERIFIED (`RetentionSweepReport.kept` exists; the sweep proceeds for a live recording and holds a gone one whose deletion was not recorded). Applied: D9, D12, Key Findings, Task 1.1, `test_past_sessions.py`; the `held` set removed.
- PR-MED-133 — VERIFIED (`closeEvent`'s enrolment and `is_writing` branches precede the generic list). Applied: D11's admission, `test_archive_run.py`.
- PR-MED-134 — VERIFIED (`reconcile_pending` treats a keyless folder as a key-first removal's leftover). Applied: D5 hop B, `test_backup_write.py`.
- PR-MED-135 — VERIFIED (`docs/practice/development-recording-consent.md` names `patient-info-v3` in its opening paragraph). Applied: D14, Task 4.2.
- PR-MED-136 — VERIFIED (plan text). Applied: D10's status line wording, D6 hop D, the UI tests.

### Round 10 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 2)

Source: Codex gpt-6.2-astra high — plan peer-review

Round status: Open (12 pending)

**PR-HIGH-137 — The destruction rule can discard the only recoverable pre-reset audit history.**
Materiality: build-affecting
D10 tells the practitioner to destroy older backups once a new one says nothing was left out. D14 protects a pre-reset backup only until it has been “restored from.” A restore can preserve a conflicting local row or stop partway through. The next backup can then copy every current row while the earlier recorded facts still exist only in the pre-reset file. Reset quarantines the entire old audit store. `plan-past-sessions-backup.md:101,134,143,152,166`; `desktop/src/scribe_desktop/audit.py:1091`
Proposed amendment: Make the confirmation, restore report and downtime procedure say to retain the pre-reset file while any still-required earlier history remains unrecovered, and verify the rule with a partial restore and a conflicting row.

**PR-HIGH-138 — A successful Delete now can be reversed after a disk failure.**
Materiality: build-affecting
Take a backup, delete a session successfully, then lose the disk before making its replacement. On a fresh login, neither the local store nor the surviving backup contains the later tombstone, so D8 classifies the session as `add`. Restoring an older backup first can also defeat a surviving newer tombstone because D9 keeps the local recorded row and Restore leaves readable entries in place. C5 names failed audit writes and pruning as exceptions, but neither occurred here. `plan-past-sessions-backup.md:34,109,133,143,199`
Proposed amendment: Bound the deletion guarantee to surviving tombstone evidence, direct disaster recovery to use the newest suitable backup first, and test and document how the practitioner reconciles deletions made after that backup.

**PR-HIGH-139 — An audit-only backup can give the clean success line even when its row cannot be restored.**
Materiality: build-affecting
D1 copies every authenticated row. D5 increments `not_restorable` only for an included **entry**. A file containing one authenticated but undecodable audit row and no session therefore says “Nothing was left out,” although D9 skips its only row. A decoded row whose ID or month disagrees with its descriptor also fails import, and D8 does not classify that binding failure as unknown deletion history for an associated entry. HEAD distinguishes undecodable rows from `_NEWER` and separately checks the embedded ID. `plan-past-sessions-backup.md:101,118,126,133,143`; `desktop/src/scribe_desktop/audit.py:416,1192`
Proposed amendment: Share one row-importability check across Back up, Open and Restore, retain authenticated ciphertext as decided, count non-importable rows independently of entries, and treat a binding mismatch as unknown history for the associated entry.

**PR-HIGH-140 — The rollback deletion procedure cannot be followed on 0.2.0.**
Materiality: build-affecting
D13 directs the practitioner to use Delete recording first on an older build. The existing rollback guide explicitly says 0.2.0 hides kept recordings, has no Delete recording action, and relies on entry-key destruction during Delete now. Once a backup holds that entry key, the guide’s assurance that this destroys the recording no longer holds if sidecars survive cleanup. Disabling automatic expiry covers only one of the two deletion paths. `plan-past-sessions-backup.md:161,162,284`; `docs/release/pilot-builds.md:345–359`
Proposed amendment: Extend the below-0.3.0 instructions to defer manual entry deletion until a build capable of verified recording-key destruction is running, while retaining D13’s rule that rollback itself deletes no recording.

**PR-MED-141 — The restore outcome table can misreport what reached disk.**
Materiality: build-affecting
A published entry whose subsequent `archived` update fails counts both as a restored session and under “Not restored.” The table also accounts for remaining work after `source_changed` but gives no outcome for an ordinary destination write or publish failure after earlier rows committed. HEAD distinguishes staging-write, verification and publication failures and cleans staging on each path. Separately, the summary calls an entry excluded solely by a fresh computer’s seven-year setting “Deleted since,” although no deletion occurred. `plan-past-sessions-backup.md:133–138,151,218`; `desktop/src/scribe_desktop/past_sessions.py:673–700`
Proposed amendment: Define counts for committed objects, secondary audit failures, failed or unreached writes, and retention exclusions, then pin the displayed results for a failed audit update, a destination failure after one commit, and an old entry on a fresh computer.

**PR-MED-142 — Duplicate ZIP member names can pass the manifest’s member-set check.**
Materiality: build-affecting
D2 explicitly requires one `manifest.enc`, but compares the remaining member **set** with the names implied by the manifest. Two directory records bearing the same payload name leave that set unchanged. Reading once by manifest name cannot verify both physical members, contrary to Open’s claim that it verified every member. The repository’s existing bounded ZIP reader distinguishes individual directory records when it opens them. `plan-past-sessions-backup.md:104,121,216`; `desktop/src/scribe_desktop/sample_notes.py:381,411–419`
Proposed amendment: Require unique names across the entire central directory during preflight and add a duplicate payload-name refusal test.

**PR-MED-143 — The backup’s label check omits an identity check used by Past sessions.**
Materiality: build-affecting
D5 and D8 require decryption under `_label_aad(id)`, schema parsing and agreement on optional files. HEAD additionally requires `label.session_id == entry.name` after parsing. A label authenticated under the expected AAD can still contain a different ID. The specified Open check can accept it while `read_entry` rejects it as unreadable. `plan-past-sessions-backup.md:121,127,135`; `desktop/src/scribe_desktop/past_sessions.py:1480,1729–1751`
Proposed amendment: Share the embedded-ID check with the bytes-level label decoder used by Open and staged verification, and test a validly authenticated label carrying the wrong ID.

**PR-MED-144 — The writer cannot tell the page which backup it published.**
Materiality: build-affecting
Hop C chooses the collision suffix, Task 1.5 restricts its report to counts, and hop D must display the actual filename. On a second backup that day the page knows the proposed name but cannot tell which suffix won. The existing recording-export dialog also shows how to preserve C1’s date-only naming rule when someone types a different basename. The settings-write assertion assigned to Task 1.5 belongs to hop D, which Task 2.3 builds. `plan-past-sessions-backup.md:101,129,195,217,263,271`; `desktop/src/scribe_desktop/ui/past_sessions.py:794,1161–1166`
Proposed amendment: Let the writer use the selected parent and return its generated published basename alongside the counts, then have Task 2.3 verify the displayed collision suffix and the post-publication settings write.

**PR-MED-145 — The wrong-entry-key restore test cannot reach staging.**
Materiality: build-affecting
Validation expects a backup pairing an ID with another entry’s key to yield `failed_verify` and staging cleanup. D2 must already reject that file during Open, before a restore plan or staging directory exists. HEAD’s staging verification uses the key read back from the destination, which provides a separate, reachable failure point. `plan-past-sessions-backup.md:104,121,134,218`; `desktop/src/scribe_desktop/past_sessions.py:773–787`
Proposed amendment: Expect Open to refuse the mispaired backup without creating staging, and exercise `failed_verify` by injecting a bad staged write or local key read-back after a valid Open.

**PR-MED-146 — The development-consent pointer change conflicts with its versioning rule.**
Materiality: build-affecting
D14 and P.3 change the ordinary-sheet reference inside `development-recording-consent.md` while keeping `development-consent-v1`. The practice README expressly says a change to either that document or its tick creates a new shared version. Keeping the signed Parts and tick intact does not settle how the introductory edit is versioned. `plan-past-sessions-backup.md:165,283,299`; `docs/practice/development-recording-consent.md:19`; `docs/practice/README.md:76–81`
Proposed amendment: Have P.3 explicitly approve and record a narrow exception for this introductory cross-reference edit, preserving the fixed v1 consent wording and tick.

**PR-MED-147 — The specified file checks can follow an existing source-file link.**
Materiality: build-affecting
D1 assigns linked files to `uninspectable`. D5 checks the entry **directory**, then verifies a payload through its opened handle. A file link to an ordinary singly linked target can satisfy that handle check. This requires no change during the run. HEAD’s label decoder opens the pathname, and the audit inventory uses `path.is_file()`. The existing recording-key code demonstrates why it checks the pathname’s link state before checking the handle. `plan-past-sessions-backup.md:114,126–127,217`; `desktop/src/scribe_desktop/past_sessions.py:1088–1094,1729–1735`; `desktop/src/scribe_desktop/audit.py:1222–1231`
Proposed amendment: Require a confirmed non-link pathname before the first source-file read, including the label and audit rows, and test a file symlink separately from the existing directory-junction and hard-link cases.

**PR-LOW-148 — Admission gives the wrong instruction during a draft write.**
Materiality: build-affecting
D11 checks `_live_session_ids()` first, and HEAD includes draft-write reservations in that set. A real reserved write therefore gets “Finish or discard the current recording first.” If the dedicated `is_writing` branch is reached, D11 assigns it the voice-enrolment instruction, including “Stop.” HEAD already has the appropriate write-in-flight message. `plan-past-sessions-backup.md:155,222`; `desktop/src/scribe_desktop/session.py:1835–1855`; `desktop/src/scribe_desktop/ui/main_window.py:1601–1606`
Proposed amendment: Check `is_writing` before the generic live-ID refusal, use the existing write-in-flight message, and verify it with a reserved write.

**Spot-checked cites and results**

- `HEAD` resolved to `5d63ed6`. The tracked diff named only `.cursor/plans/plan-past-sessions-backup.md`. The body ends before `## Review History` at line 304. Its 40 task checkboxes include 10 checked, so 25% is correct.
- `past_sessions.py:1088–1104,1621–1650,1840–1896` and `ui/past_sessions.py:643–676` confirm the zero-in-place operation, the distinction between empty and zeroed keys, the sweep’s two callback outcomes, and the source of `report.kept`.
- `session_store.py:641–670,764–791,1037` and `transcription.py:1434` confirm the custody refusal paths and the existing saved-note, generated-record and transcript readers. `past_sessions.py:810–815` confirms why restore needs its own publisher.
- `audit.py:465,997–1019,1079–1096,1148–1188,1245–1279` confirms month pruning, duplicate-row ambiguity, reset eligibility, local row-write checks, and the distinction between a fresh store and a missing key beside existing rows.
- `ui/recovery.py:196–219`, `ui/bridge.py:899–936` and `app.py:604–637` confirm the two Recovery lists, refusal invalidation mechanism, and single gate point before the three periodic sweep steps.
- `exclusions.py:493–523` confirms that Export currently checks the resolved drive letter and documents the mounted-folder limitation. D7’s volume identity is new work. `app.py:665–702`, `scripts/build-release.py:474–487`, `desktop/pyproject.toml:19` and `desktop/requirements-build.txt:26` confirm the existing self-check codes, frozen invocation and cryptography versions.
- `docs/practice/patient-information-and-consent.md:9,141,174` confirms the three v3 references P.3 must move together. Plan lines 297–301 keep P.2 synthetic and gate the first real backup on P.3 approval and P.4(a).

Materiality: 12 build-affecting / 0 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 10 (2026-11-25, verified by the planning session against `5d63ed6`)

- PR-HIGH-137 — VERIFIED build-affecting (plan text; `AuditLog.reset` quarantines the old store). Applied: D14's keep rule; D10's Delete now confirmation now points to the documents.
- PR-HIGH-138 — VERIFIED record-only (inherent to a backup older than a deletion; no code can know). Applied as a named residue in C5 and the newest-first rule in D14.
- PR-HIGH-139 — VERIFIED build-affecting (`_decode` raises for an authentic non-row; `_read` binds the id by AAD only). Applied: `audit.row_importable` in D1, D5, D2 step 6, D8 step 2, Task 1.2, the tests.
- PR-HIGH-140 — VERIFIED build-affecting (`docs/release/pilot-builds.md`, the below-0.3.0 section: 0.2.0 has no Delete recording and says Delete now destroys the recording). Applied: D13.
- PR-MED-141 — VERIFIED build-affecting (plan text). Applied: `failed_write`, `audit_update_failed` as a sentence, `skipped_expired` its own count; D10's lines; the UI tests.
- PR-MED-142 — VERIFIED build-affecting (a set comparison cannot see a doubled name). Applied: D2's preflight, the test list.
- PR-MED-143 — VERIFIED build-affecting (`_decode_label` requires `label.session_id == entry.name`). Applied: D5's `entry_opens`, D8's `_verify_restored`, the tests.
- PR-MED-144 — VERIFIED build-affecting (Export uses only the chosen folder and names the file itself). Applied: D6, Task 1.5, the tests moved to their owners.
- PR-MED-145 — VERIFIED build-affecting, fix-induced (round 9's open check makes the old test unreachable). Applied: `test_restore.py`'s item.
- PR-MED-146 — VERIFIED build-affecting, fix-induced (`docs/practice/README.md`: a change to the document or the tick is a new version). Applied: the consent document is not edited; a README sentence at P.3.
- PR-MED-147 — VERIFIED build-affecting (`delete_recording` checks the path's link state before the handle for this reason). Applied: D5 hops B and C, D9's inventory, the tests.
- PR-LOW-148 — VERIFIED build-affecting, fix-induced (`custody_protected_ids` includes draft-write reservations). Applied: D11's order and the existing write line.

### Round 11 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 3)

Source: Codex gpt-6.2-astra high plan peer-review

**PR-HIGH-149 — The empty-store rule can authorize destruction of a pre-reset backup after a partial restore.**
Materiality: build-affecting
`plan-past-sessions-backup.md:166` says to keep the backup for seven years if a restore left an audit row or failed to restore something. The same line exempts only a backup “that has not been restored from” when the current store is empty. A restore attempted against an empty store can leave it empty. The practitioner then has two opposite instructions for the same file. The final report at `plan-past-sessions-backup.md:151` also pools unchanged sessions and rows, while the disposal instruction asks specifically about audit rows.
Proposed amendment: Use one pre-reset retention rule in both branches and show the actual number of source audit rows imported out of the total, so the practitioner can apply it after a partial restore.

**PR-HIGH-150 — Restore has no reportable outcome for an ordinary audit-row write failure.**
Materiality: build-affecting
At `plan-past-sessions-backup.md:138`, `failed_write` covers a session add and `audit_update_failed` covers marking an existing row `archived`. Neither covers writing an imported row. In an audit-only restore, the first row can commit and the second fail on a full disk. Both local key creation and the row write are fallible at `audit.py:1262` and `audit.py:1184`. A later failure saving the reminder date can likewise interrupt Flow 3 after the data has reached disk. `plan-past-sessions-backup.md:129` handles that settings failure only for Back up.
Proposed amendment: Count a failed row import and any unattempted work in the final report, preserve earlier committed counts, and make failure to save the reminder date a separate warning that still allows the page to refresh and display the report.

**PR-HIGH-151 — The partial-file instructions can destroy or conceal a surviving backup.**
Materiality: build-affecting
`plan-past-sessions-backup.md:129` tells the practitioner to delete a pre-existing `.part` before retrying. The same decision recognizes that it can contain a whole backup, and `plan-past-sessions-backup.md:166` puts its destruction under the older-backup rule. Also, the specified cleanup helper treats a missing parent folder as successful removal specifically because Export admits only fixed drives. Pulling a USB drive can leave the partial file on that drive while cleanup reports it gone. See `past_sessions.py:2023`.
Proposed amendment: Direct the practitioner to choose another admitted folder when a `.part` already exists, and report that a partial backup may remain whenever cleanup cannot confirm the original volume, folder, and file identity.

**PR-MED-152 — A session can become unrestorable after the writer has calculated `not_restorable`.**
Materiality: build-affecting
At `plan-past-sessions-backup.md:126`, the count comes from `audit.row_state(id)` during the snapshot. At `plan-past-sessions-backup.md:127`, a later read failure can put that row in `rows_unknown` while its session is successfully copied. Restore then necessarily skips the session at `plan-past-sessions-backup.md:133`. The success line can report one omitted audit row and omit the warning that its session cannot be restored. This requires only a failed read.
Proposed amendment: Finalize `not_restorable` from the entries actually written and their final row classifications, with a test where the row reads during the snapshot and fails during the copy.

**PR-MED-153 — The practitioner lacks a defined way to obtain the authoritative empty-store result.**
Materiality: build-affecting
`plan-past-sessions-backup.md:147` gives Back up a committed-entry-or-audit-row enablement condition and explicitly allows Open on an empty store. Yet `plan-past-sessions-backup.md:101` delivers “Nothing to back up yet” through Back up, and `plan-past-sessions-backup.md:166` makes that result grounds for a disposal decision. A disabled button or empty page listing cannot establish that both stores were successfully inspected.
Proposed amendment: Keep Back up available on an apparently empty store so the strict snapshot can return the authoritative result, and test that path from the button on a fresh store.

**PR-MED-154 — The wrong-id label test demands an outcome the writer cannot reach.**
Materiality: build-affecting
`plan-past-sessions-backup.md:217` requires `damaged` for an authentic label naming another session. Hop B at `plan-past-sessions-backup.md:126` requires `unreadable` when `_decode_label` rejects the label. `past_sessions.py:1738` returns `None` for exactly that id mismatch, so the entry never reaches hop C.
Proposed amendment: Expect `unreadable` in the writer test and separately test the id-binding rejection in `entry_opens` during Open.

**PR-MED-155 — The successful Delete now message still says the entry key was destroyed.**
Materiality: build-affecting
`ui/past_sessions.py:686` displays `DELETE_DONE` after deletion. Its literal at `ui/past_sessions_view.py:189` says “its key was destroyed.” After a backup, the same key remains recoverable from the wrap specified at `plan-past-sessions-backup.md:119`. Task 2.4 updates the confirmation and failure wording but misses the success message.
Proposed amendment: Change `DELETE_DONE` to “Past session deleted from this computer’s Past sessions.” and include that result in Task 2.4’s wording checks.

**PR-MED-156 — The shorter-retention confirmation promises to keep entries the sweep can delete.**
Materiality: build-affecting
`plan-past-sessions-backup.md:152` says a session “that cannot be read or deleted is kept and counted.” At `past_sessions.py:1483`, a damaged transcript makes the session unreadable on the page. The sweep needs only a known completion date, which may already be cached, and can delete that same entry at `past_sessions.py:1589` and `past_sessions.py:1643`. This matters when the practitioner is confirming immediate deletion.
Proposed amendment: Say that a session whose completion date is unknown, or whose deletion fails, is kept and counted, and pin that wording in the confirmation test.

**PR-LOW-157 — The repair report guarantees cleanup at the next start.**
Materiality: build-affecting
The dictated line at `plan-past-sessions-backup.md:151` says “the next start removes it.” At `past_sessions.py:908`, startup cleanup can skip an inaccessible staging folder, and `past_sessions.py:2135` removes remaining files best-effort. A lock that survives restart makes the displayed promise false.
Proposed amendment: Use “A repaired key left a temporary folder. Clinic Scribe will try to remove it at the next start.”

**PR-LOW-158 — The new-computer procedure omits two settings that revert to defaults.**
Materiality: record-only
Flow 4 at `plan-past-sessions-backup.md:110` names clinic keys and voice re-enrolment. A fresh login also starts with unlimited retention and shadow mode off, as confirmed at `past_sessions.py:2164` and `note_config.py:1227`. The former affects what Restore will add, and the latter affects the next consultation. Phase 4 and P.3 can settle the operating wording.
Proposed amendment: Have the downtime procedure tell the practitioner to select the intended retention period before Restore and check shadow mode before the next consultation.

**Other cites spot-checked at HEAD `5d63ed6`**

- `past_sessions.py:755`, `transcription.py:1434`, and `session_store.py:764` support sharing the existing reader checks. `past_sessions.py:810` confirms restore needs its own publisher because the existing publisher removes the destination.
- `ui/past_sessions.py:643`, `past_sessions.py:1621`, and `audit.py:576` support D12’s caller ordering and `recording_held` change. The sweep proceeds after a failed callback for a live recording and retains a gone recording whose deletion could not be recorded.
- `audit.py:416`, `audit.py:1192`, and `audit.py:1245` confirm the newer-row case, the existing id check, and the distinction between a fresh store and a missing key beside rows. The proposed importability check adds the month comparison.
- `exclusions.py:493`, `conftest.py:331`, and `sample_notes.py:376` confirm the fixed-drive Export baseline, fake Windows-layer requirement, and bounded ZIP-reader precedent. Removable-drive publication and Qt dialog behavior remain runtime checks for implementation.
- `ui/main_window.py:1156`, `ui/main_window.py:1601`, `ui/recovery.py:196`, `ui/bridge.py:899`, and `ui/tasks.py:24` support the proposed gate placement, write-first admission, separate protected-recovery check, bridge refusal, and worker signal handling.
- `docs/practice/README.md:54`, `docs/practice/README.md:75`, and `test_schema_versions.py:330` support drafting v4 beside v3 while preserving the separate development-consent text. Plan lines 209 and 301 explicitly gate the first real backup on P.3 approval and P.4(a).
- `desktop/pyproject.toml:19`, `desktop/requirements-build.txt:26`, `app.py:665`, and `scripts/build-release.py:485` match the dependency and frozen self-check baselines. The plan has **10 checked tasks out of 40**. This was a static review under the requested read-only constraints.

The body needs amendment before it is ready to build, chiefly because the current instructions can authorize destruction of a surviving backup and the restore report can lose track of committed work.

Materiality: 9 build-affecting / 1 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 11 (2026-11-25, verified by the planning session against `5d63ed6`)

- PR-HIGH-149 — VERIFIED build-affecting, fix-induced (two sentences of D14's rule disagreed after a partial restore). Applied: D14's one rule; decision 0.12's refinement line; the README question.
- PR-HIGH-150 — VERIFIED build-affecting (`AuditLog` row writes and key creation can fail). Applied: `failed_row_write`, the continue-on-failure rule, Flow 3's date sentence, the UI tests.
- PR-HIGH-151 — VERIFIED build-affecting (`_remove_part` returns True for a missing folder; the plan itself calls a `.part` a possible whole backup). Applied: D6's naming, its cleanup sentence, the tests.
- PR-MED-152 — VERIFIED build-affecting (plan text: the count was fixed at the snapshot). Applied: D5 hop C, the test.
- PR-MED-153 — VERIFIED build-affecting, fix-induced (the enablement rule hid the answer D14 relied on). Applied: both buttons always enabled; D14's rule no longer relies on that answer.
- PR-MED-154 — VERIFIED build-affecting, fix-induced (`_decode_label` returns None for an id mismatch, so hop B reports `unreadable`). Applied: the two test items.
- PR-MED-155 — VERIFIED build-affecting (`DELETE_DONE` = "Past session deleted (its key was destroyed)."). Applied: D10's wording, Task 2.4.
- PR-MED-156 — VERIFIED build-affecting (the sweep deletes by a cached completion date). Applied: D10's shorter-retention confirmation.
- PR-LOW-157 — VERIFIED build-affecting (`clean_staging` is best-effort). Applied: D10's sentence.
- PR-LOW-158 — VERIFIED record-only. Applied all the same: Flow 4 names the two settings.

### Round 12 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 4)

Source: codex gpt-6.2-astra high — Codex plan peer-review

**PR-HIGH-159 — The backup makes a surviving development recording recoverable under another Windows login.**
Materiality: build-affecting
The approved consent says the recording can be opened only from the practitioner’s Windows login on that computer. At HEAD, the entry key alone unwraps the recording key. D2 puts that entry key in the backup, and D8 repairs it under the current login when the original archive files survive. A Windows reinstall with the data volume intact is enough to expose the difference. Excluding both audio files from the backup keeps the no-audio-backup promise, but the original-login promise also matters. `docs/practice/development-recording-consent.md:58`, `desktop/src/scribe_desktop/past_sessions.py:1811`, `past_sessions.py:1830`, `plan-past-sessions-backup.md:119,136,165`.
Proposed amendment: Add a practitioner decision before implementation that either preserves independent login-bound custody for existing recordings or versions the development consent and settles how already-consented recordings will be handled before their entry keys are backed up.

**PR-HIGH-160 — Rotation after a partial restore can destroy the only recoverable copy.**
Materiality: build-affecting
On a replacement computer, a row can import successfully while its session fails to publish because the disk fills. A later backup of that computer can truthfully say “Nothing was left out.” Its snapshot inventories the entries present locally, so the missing session contributes no omission. After two such backups, following the keep-two rule can destroy the recovery source containing that session. This needs neither an audit reset nor an outside writer. `plan-past-sessions-backup.md:101,126,138,166`.
Proposed amendment: Require the practitioner to retain the recovery source while any intended session or row remains unrecovered, and include that instruction in the partial-restore report.

**PR-HIGH-161 — Restoring newest first does not preserve an unknown deletion history across backups.**
Materiality: build-affecting
Suppose a session was deleted before the newest backup, but its audit row was unreadable when that backup was made. The newest manifest carries the ID in `rows_unknown` and correctly prevents restoring it. Restore writes no local marker for that ID. Opening an older backup next can therefore add the session from its older, readable `archived` row. The prescribed check for deletions *after* the newest backup misses this case even when the practitioner follows the specified order. `plan-past-sessions-backup.md:118,127,133,143,167,199`.
Proposed amendment: Make the recovery procedure stop before layering an older backup when the newer file reported omitted audit rows, until the practitioner can reconcile the missing deletion history.

**PR-MED-162 — The file chooser can touch a newly remote drive before the location check.**
Materiality: build-affecting
Both dialogs start in the remembered folder. Between runs, a drive letter previously assigned to a USB disk can become a mapped network drive. Passing that initial location to the native chooser lets it navigate there before D7 checks the selection, even if the practitioner cancels. The existing chooser passes its proposed path directly to Qt. `plan-past-sessions-backup.md:101,104,130,196`, `desktop/src/scribe_desktop/ui/past_sessions.py:1172`.
Proposed amendment: Revalidate the remembered folder before supplying it to either chooser, with a known local starting location when its drive is remote, absent or uninspectable.

**PR-MED-163 — Repair checks the entry directory but can follow a linked file inside it.**
Materiality: build-affecting
D5 checks each file before opening it. D8 checks the local entry directory, then reads `key.dpapi`, opens `label.enc` and hashes the content files. An ordinary directory can already contain a file symlink. The existing label reader opens the supplied path, and the custody reader uses `read_bytes()`. Repair can consequently read a target outside the archive or report success while a content file still points elsewhere. This is a pre-existing layout, independent of any race. `plan-past-sessions-backup.md:126,133,136`, `desktop/src/scribe_desktop/past_sessions.py:1729`, `desktop/src/scribe_desktop/session_store.py:653`.
Proposed amendment: Apply the ordinary-file and link checks to each local key or content file D8 will read, and verify that a linked label or key is skipped without opening its target.

**PR-MED-164 — The `archived` update and its report disagree across add, repair and retry.**
Materiality: build-affecting
An imported row can legitimately say `none`. D8 marks it `archived` after an add and on a `skipped_present` retry, but omits that step after a successful key repair. Opening the same backup a second time can therefore change the audit result of a supposedly finished repair. Conversely, if the audit update fails on a `skipped_present` retry, D8 says the session counts as restored even though this run published zero entries. HEAD permits the `none` → `archived` transition. `plan-past-sessions-backup.md:135,136,138,151`, `desktop/src/scribe_desktop/audit.py:569`, `audit.py:867`.
Proposed amendment: Share the noncreating audit update across successful add, successful repair and eligible already-present entries, and report its failures independently of the counts of sessions published and keys repaired.

**PR-MED-165 — Two specified restore outcomes still have no applicable count.**
Materiality: build-affecting
An authenticated row that decodes but names the wrong ID or month is `row_mismatch` at execution. The summary table omits it, and `skipped_undecodable_row` explicitly covers a different case. In the final report, if the second of two entries triggers `source_changed` during its member read, the first was restored and the second was attempted. Counting only items *not attempted after* the stop leaves the second entry out of the total. `plan-past-sessions-backup.md:121,133,134,138,143,218`.
Proposed amendment: Give `row_mismatch` a nonwriting summary count and count the uncommitted item that triggered `source_changed` together with the unattempted remainder, with exact totals in both tests.

**PR-MED-166 — The prescribed deletion result overstates what disappeared from the computer.**
Materiality: build-affecting
“Past session deleted from this computer” can be false immediately after a successful Delete now. D7 expressly admits a backup on a fixed local drive, and deletion changes only the Past-sessions store. The two confirmations’ “for good” wording also conflicts with C5’s documented case where the entry reappears after disaster recovery. `plan-past-sessions-backup.md:130,152,199`, `desktop/src/scribe_desktop/ui/past_sessions.py:662`, `ui/past_sessions.py:686`.
Proposed amendment: Use “Session deleted from Past sessions” for success and describe removal from Past sessions in both confirmations, retaining their earlier-backup warning.

**PR-MED-167 — Password echo mode leaves the passphrase in Qt text signals.**
Materiality: build-affecting
D4 and C3 explicitly prohibit a Qt signal from carrying the passphrase. A `QLineEdit` in `Password` echo mode still emits its actual value in `textEdited(QString)` and `textChanged(QString)` during entry. The specified clipboard and post-dialog clearing tests would both pass. The project already uses `blockSignals` where widget signals must be suppressed. `plan-past-sessions-backup.md:124,148,197,223`, `desktop/src/scribe_desktop/ui/clinics.py:102`, `ui/past_sessions.py:425`.
Proposed amendment: Block the password fields’ text signals throughout editing and clearing, read the accepted values synchronously, and verify that neither text-bearing signal delivers a value.

**PR-LOW-168 — The revised key-removal order cannot preserve its stated failure contract.**
Materiality: build-affecting
D8 requires `_remove_key_first` to unlink `key.dpapi.tmp` before `key.dpapi` while preserving “False: nothing else touched.” If the first unlink succeeds and Windows refuses the second, the committed key remains but the temporary is gone. The specified test exercises failure of the *first* unlink only. `plan-past-sessions-backup.md:137,219,259`, `desktop/src/scribe_desktop/past_sessions.py:2115`.
Proposed amendment: Define `False` to guarantee that the committed key remains, allow the temporary to have been removed, and pin the second-unlink failure case.

**Spot-checks at `5d63ed6`**

- `past_sessions.py:722,755,810,868,895` — staging uses a fresh key, verification uses the existing readers, `_publish` removes its destination first, and reconciliation and staging cleanup have the separate roles assumed by the plan. Restore needs `_publish_new`.
- `transcription.py:1434`, `session_store.py:755,789,1021`, `past_sessions.py:1729` — transcript parsing, saved-note digest and session binding, generated-record size and identity, and label identity all have existing checks that the bytes-level open check can share.
- `past_sessions.py:1058,1621,1840,1877`, `ui/past_sessions.py:643`, `ui/past_sessions_view.py:855` — the zero-in-place operation, empty-key distinction, pre-delete recording-state read and sweep’s two callback outcomes match D12. The sweep already exposes the `kept` set needed by D9.
- `audit.py:416,465,1079,1091,1192,1222,1245` — newer rows, calendar-month pruning, reset, row identity and the fresh-store versus missing-key distinction support the planned audit surface. The existing row reader checks the ID, so D9’s additional month check matters.
- `ui/main_window.py:1143,1548,1588,1609`, `ui/recovery.py:196,322`, `ui/bridge.py:899,915`, `app.py:604`, `ui/tasks.py:21` — the window can disable its central controls while a window-parented dialog remains usable. Recovery’s protected IDs, the write and enrolment checks, the refusal state and the periodic sweep provide the proposed gate points.
- `exclusions.py:239,298,493`, `desktop/tests/conftest.py:344`, `sample_notes.py:400`, `past_sessions.py:2008` — the Windows layer is injectable, the real layer is guarded in tests, and bounded member reads and identity-checked partial-file removal have precedents. Windows removable-drive and Qt runtime behavior were reviewed statically.
- `desktop/pyproject.toml:19`, `desktop/requirements-build.txt:26`, `app.py:665`, `scripts/build-release.py:485`, `desktop/tests/test_install_layout.py:470`, `desktop/tests/test_shadow_exits.py:207` — the dependency floor, frozen pin, self-check codes, release failure text and named test pins match the plan’s starting assumptions.
- `docs/practice/README.md:54,76`, `patient-information-and-consent.md:141,174`, `docs/release/pilot-builds.md:351`, `plan-past-sessions-backup.md:297,299,300,301` — the v4 draft and later approval commit fit the patient-sheet version rules. P.5 explicitly requires P.3 approval and P.4(a). The rollback paragraph identified for amendment exists. The progress line reconciles to 10 checked tasks out of 40.

In my judgment, the body needs amendment before build, chiefly because the portable entry key changes an approved recording-custody promise and the recovery procedure can discard the only surviving copy of a session.

Materiality: 10 build-affecting / 0 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 12 (2026-11-25, verified by the planning session against `5d63ed6`)

- PR-HIGH-159 — VERIFIED build-affecting (`docs/practice/development-recording-consent.md` Part A: "can be opened only from your practitioner's own Windows login on that computer"; `_audio_chunks` unwraps the recording key with the entry key alone; D2 puts the entry key in the backup and D8's repair re-wraps it for the current login). HELD — a `[decision]` for the practitioner; no body text changed for it in this round.
- PR-HIGH-160 — VERIFIED build-affecting (plan text: a backup inventories only what is present). Applied: D14's keep rule for the backup restored from; the report's sentence.
- PR-HIGH-161 — VERIFIED build-affecting (plan text: `rows_unknown` leaves no local marker). Applied: D14's downtime wording; C5's residue.
- PR-MED-162 — VERIFIED build-affecting (`_ask_wav_path` hands its start path straight to Qt). Applied: D7; the test.
- PR-MED-163 — VERIFIED build-affecting (`_decode_label` and `unwrap_key_from_file` open the path given). Applied: D8 step 7; the test.
- PR-MED-164 — VERIFIED build-affecting, fix-induced. Applied: D8's shared write; the table; the test.
- PR-MED-165 — VERIFIED build-affecting, fix-induced. Applied: the planner's row outcome; the stop's accounting; the test.
- PR-MED-166 — VERIFIED build-affecting, fix-induced (D7 admits a backup on this computer's own disk). Applied: the three strings.
- PR-MED-167 — VERIFIED build-affecting (`QLineEdit` emits its text in `textChanged` / `textEdited` in any echo mode). Applied: D10's dialog; the test.
- PR-LOW-168 — VERIFIED build-affecting, fix-induced. Applied: the contract's wording; the test.
- PR-HIGH-159 — DECIDED 2026-11-25 by the practitioner: "Leave those sessions out (Recommended)" (decision 0.13). Applied in place: D12, D13, D1, D5, D8, D9, D10, Flow 1, the schema table, Task 1.1 and the tests. Findings PR-HIGH-127 and PR-HIGH-140 (the rollback rule and recordings) and PR-HIGH-105 / PR-MED-132's `recording_held` half are moot under it: deletion no longer changes.

### Round 13 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 5)

Source: Codex gpt-6.2-astra high plan peer-review

**PR-HIGH-169 — A restore can report zero “Not restored” while the backup holds the only readable copy.**
Materiality: build-affecting
On a fresh login, a valid backup can contain a session alongside a newer-schema audit row. Restore imports the opaque row and skips the session as `skipped_unknown_row`. The final table gives that persistent skip no explicit outcome. Counting it under “Left as they are” suppresses the keep-source warning. A subsequent backup can contain just the audit row and report “Nothing was left out,” allowing the practitioner eventually to destroy the only copy of the session. The same reporting gap applies to an unresolved key-repair conflict. `plan-past-sessions-backup.md:127,133,138,150,165`; `desktop/src/scribe_desktop/audit.py:436`.
Proposed amendment: Map persistent unresolved skips explicitly to a count that keeps the source backup, and test the final report for a newer-schema row on a fresh login and a conflicting unreadable entry on the original login.

**PR-HIGH-170 — The rule for layering an older backup can revive a deleted session.**
Materiality: build-affecting
Zero audit rows omitted **when the newest file was made** does not establish that its deletion records are present **after restore**. A deletion row can fail to write, after which Restore continues. An audit reset between backups can also remove that deletion from the newest file’s source inventory altogether. In either case an older backup can supply both the pre-deletion row and the session. The instruction to delete again anything deleted *after* the newest backup misses both cases. `plan-past-sessions-backup.md:133,138,143,166,197`; `desktop/src/scribe_desktop/audit.py:1091,1188`.
Proposed amendment: Require successful recovery of the newest backup’s deletion evidence before layering an older file, and require independent reconciliation if an audit reset separates the two backups or a relevant row failed to import.

**PR-HIGH-171 — A missing archive can produce an audit-only backup that authorizes disposal of older copies.**
Materiality: build-affecting
If the Past-sessions folder is lost before Back up starts but the audit store survives, the audit can still contain an in-retention `archived` row. Hop B checks audit state for each entry it *finds*. It never checks the reverse discrepancy. Hop C can therefore publish an audit-only file with zero omissions, even though the app has evidence of an archived session and an older backup may be its only surviving copy. This requires no change to a file during the run. `plan-past-sessions-backup.md:101,126,127,165`; `desktop/src/scribe_desktop/audit.py:552,569`; `desktop/src/scribe_desktop/ui/past_sessions.py:662,676`.
Proposed amendment: Withhold the disposal-authorizing sentence when a readable `archived` row has no corresponding entry or accounted-for exclusion, and test a missing archive beside a surviving archived row.

**PR-MED-172 — The specified preflight does not enforce “no ZIP64 anywhere.”**
Materiality: build-affecting
D2 checks the end record and walks the central directory. A small stored member can have a ZIP64 extra field in its **local** header while its central-directory record uses ordinary sizes and has no extra field. The prescribed directory walk and payload hashes do not establish the promised format restriction. The repository’s existing ZIP tests already distinguish local-header data from directory data. `plan-past-sessions-backup.md:120,121,214`; `desktop/tests/test_sample_notes.py:293`.
Proposed amendment: Have the bounded preflight check each referenced local header for the permitted classic format and add a local-header-only ZIP64 refusal test.

**PR-MED-173 — The success line says a session was both included and excluded.**
Materiality: build-affecting
When a session is excluded solely because it holds a kept recording, Flow 1 requires “Nothing was left out” followed by “H sessions that hold a kept recording are not in a backup.” The test explicitly pins that combination. The eligibility decision is sound, but the first sentence makes an unqualified claim about the file that the second sentence contradicts. `plan-past-sessions-backup.md:101,114,160,215`.
Proposed amendment: Use “Nothing eligible for backup was left out” as the success marker in the app, its test, and the disposal procedure, while retaining the separate count of sessions holding recordings.

**PR-LOW-174 — D12 overstates what deletion proves about historical recording-key copies.**
Materiality: record-only
The two custody checks establish that the live entry has no usable recording-key file when its entry key is backed up. Delete recording leaves the entry key unchanged, however, and the existing threat model explicitly recognizes that a snapshot or journal can retain the former wrapped recording key. A later backup changes the custody of the entry key relevant to that already-accepted residue. `plan-past-sessions-backup.md:160,281`; `desktop/src/scribe_desktop/past_sessions.py:1096,1811`; `docs/security/threat-model.md:4943`.
Proposed amendment: Qualify D12’s guarantee to the recording material the app currently holds and update the existing forensic-residue paragraph to account for the later passphrase-wrapped entry key.

**Spot-checks at `5d63ed6`**

- `past_sessions.py:729,748,810,1852,1896` — A retried Complete stages a fresh entry key. `_audio_key_state` distinguishes absent, zeroed, live and unknown, including a live key whose audio file is missing. D12 uses the correct predicate for both backup and repair.
- `past_sessions.py:834,895,1519,2139`; `session_store.py:586,659,677` — The staging-child rule matches the existing link-aware cleanup pattern. The atomic writer uses `key.dpapi.tmp`, and file-read failure can be distinguished from DPAPI refusal before repair.
- `past_sessions.py:773,1738`; `transcription.py:1434`; `session_store.py:787,1027` — The shared open check has concrete validation to reuse for label identity, transcript parsing, saved-note binding and generated-note identity.
- `audit.py:465,867,1005,1079,1213,1245` — Month pruning, non-creating reads, duplicate-row ambiguity, the unreadable-key reset and the `create=False` audit update match the cited code.
- `exclusions.py:493`; `conftest.py:347`; `app.py:685`; `scripts/build-release.py:483`; `test_build_release.py:462` — The existing export rule is fixed-drive-only, tests can inject the Windows layer, and the frozen self-check has a release-message pin that can cover exit code 3. Windows volume and rename behavior was assessed statically.
- `ui/main_window.py:1150,1548,1588,1601`; `ui/recovery.py:196,322`; `ui/bridge.py:899,915`; `app.py:604` — The central widget can be disabled while a dialog parented to the main window remains usable. The admission checks, bridge refusal and sweep gate have identifiable integration points.
- `docs/practice/README.md:54,78`; `development-recording-consent.md:58`; `test_shadow_exits.py:167,238`; `plan-past-sessions-backup.md:296–300` — The v4 draft and approval sequence is compatible with the existing version rules. P.2 uses synthetic sessions, and P.5 is gated on P.3 approval and P.4(a). The progress count is correct at 11 of 41.

The body is not ready to build until the recovery, disposal, and format checks above are reconciled.

Materiality: 5 build-affecting / 1 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 13 (2026-11-25, verified by the planning session against `5d63ed6`)

- PR-HIGH-169 — VERIFIED build-affecting, fix-induced (round 12's sentence keyed on Not restored only). Applied: D10's keep-this-backup condition, D14's rule, the UI tests.
- PR-HIGH-170 — VERIFIED build-affecting, fix-induced (the layering rule claimed more than a backup's summary can prove). Applied: D14's downtime wording, as a procedure with the practitioner's own check.
- PR-HIGH-171 — VERIFIED build-affecting (hop B looked only from entries to rows). Applied: `missing` in D5, D2's manifest, Flow 1, D10's summary, the tests.
- PR-MED-172 — VERIFIED build-affecting (a local header can carry an extra field its directory record lacks). Applied: D2's preflight, the test list.
- PR-MED-173 — VERIFIED build-affecting, fix-induced. Applied: the marker is "Nothing eligible was left out" in the app, the tests and the rule.
- PR-LOW-174 — VERIFIED record-only. Applied: D12's consequence (1) qualified; Task 4.1's residue list.

### Round 14 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 6)

Source: Codex gpt-6.2-astra high plan peer-review

**PR-HIGH-175 — Restore can suppress “Keep this backup” when the backup holds the only readable copy.**
Materiality: build-affecting
D8 assigns `skipped_present` once the local key opens the label. D10 then omits the keep instruction. A local label can open while its transcript is corrupt, in which case opening the session on the Past sessions page fails. The same defect affects an audit-only restore when a local row file exists but cannot be decrypted. A live or pending directory likewise does not establish that the archived content is readable. Evidence: `.cursor/plans/plan-past-sessions-backup.md:133`, `:143`, `:150`, `:165`; `desktop/src/scribe_desktop/past_sessions.py:1470–1492`; `desktop/src/scribe_desktop/audit.py:1192–1205`, `:1233–1237`.
Proposed amendment: Preserve the no-overwrite classifications, but require positive evidence of local readability before suppressing the keep instruction for an existing item, with tests for an intact label beside a corrupt transcript and an audit-only backup beside an unreadable local row.

**PR-HIGH-176 — Losing the audit store can produce the success line used to retire the last backup containing its history.**
Materiality: build-affecting
Consider a disk failure that leaves recently completed entries intact but loses the `audit` directory. D9 correctly treats the missing key and absent rows as an empty store. In D5, `row_state == none` contributes nothing to `not_restorable`, and `missing` looks only for surviving audit rows whose entries are absent. The resulting entries-only backup can therefore say “Nothing eligible was left out.” After two such backups, the D14 rotation rule can retire the only copy of the earlier audit rows. No audit reset occurred, so the pre-reset protection does not apply. Evidence: `.cursor/plans/plan-past-sessions-backup.md:101`, `:126`, `:141`, `:165`, `:214`; `desktop/src/scribe_desktop/audit.py:1245–1262`.
Proposed amendment: Keep entries-only backups available, but withhold the rotation sentence when an in-retention session has no audit row and earlier audit coverage cannot be established, and test the case of a lost audit directory beside surviving recent entries.

**PR-MED-177 — Calculating `missing` reopens audit rows the strict snapshot excluded.**
Materiality: build-affecting
D5 calls `AuditLog.rows()` to find archived sessions. At HEAD that method enumerates files with `Path.is_file()` and opens them through `read_capped`. A pre-existing row-file symlink therefore has its target opened even after D9 classified that row as unknown. The generic reader also checks the decoded id but not its month, so a row D1 rejects can supply an `archived` fact. Neither case requires a file to change during the run. Evidence: `.cursor/plans/plan-past-sessions-backup.md:114`, `:126–127`, `:141`; `desktop/src/scribe_desktop/audit.py:972–988`, `:1192–1205`, `:1222–1231`.
Proposed amendment: Derive `missing` from the rows admitted and authenticated by the backup’s own inventory, finalise the count after those reads, and test that the target of an excluded row link is never opened.

**PR-MED-178 — The order of the snapshot checks can misreport a session that holds a recording.**
Materiality: build-affecting
D5 checks the entry key, label and required files before checking recording-key custody. A committed session with a live recording key and a missing transcript therefore exits as `incomplete`. Flow 1 counts it as an eligible omission and tells the practitioner to keep older backups. D12 explicitly assigns that session to the separate `holds_recording` count. HEAD can establish this fact without opening the entry key, label or transcript. Evidence: `.cursor/plans/plan-past-sessions-backup.md:101`, `:126`, `:160`, `:215`; `desktop/src/scribe_desktop/past_sessions.py:1852–1871`.
Proposed amendment: Once the ordinary entry directory and its committed status are established, classify recording-key custody before validating content, and test a live recording key beside a missing transcript.

**PR-LOW-179 — The `_remove_key_first` failure guarantee assumes a committed key already exists.**
Materiality: record-only
An interrupted first wrap can leave only `key.dpapi.tmp` in staging. If its unlink fails, the planned implementation correctly returns `False`, although there was never a committed `key.dpapi` to remain. The prescribed unlink order is sound. Evidence: `.cursor/plans/plan-past-sessions-backup.md:137`, `:217`, `:259`; `desktop/src/scribe_desktop/past_sessions.py:729–734`; `desktop/src/scribe_desktop/session_store.py:586–592`, `:633–637`.
Proposed amendment: State the guarantee as “On `False`, this call did not remove `key.dpapi`, and any committed key present on entry remains.”

**PR-LOW-180 — The rollback note omits what the older deletion confirmation will say.**
Materiality: record-only
After rolling back to 0.4.2, Delete now again tells the practitioner that the notes and transcript “cannot be recovered.” A `.csbk` made before rollback can still hold them. D14 already supplies the operating rule, so a cross-reference in the rollback section is sufficient. Evidence: `.cursor/plans/plan-past-sessions-backup.md:151`, `:161`, `:165`, `:284`; `desktop/src/scribe_desktop/ui/past_sessions_view.py:183–189`, `:310–314`.
Proposed amendment: Tell the practitioner in “Rolling back below 0.5.0” that the older deletion messages describe the local archive and that the downtime procedure still governs existing backups.

**Other cites spot-checked**

- `past_sessions.py:725–753`, `:1058–1121`, `:1821–1871` — a retried Complete stages a fresh entry key, and Delete recording zeroes and verifies the recording-key file before cleanup. D12’s custody test uses the correct primitive.
- `past_sessions.py:810–815`, `:834–866`, `:895–923`, `:1642–1647` — `_publish` removes an existing destination, staging cleanup has separate link handling, and expiry calls `delete_entry`. These support a separate non-replacing restore publish and one shared deletion change.
- `session_store.py:764–791`, `:1012–1034`; `past_sessions.py:1729–1738` — the saved-note digest and session binding, generated-record validation, and label-id check exist as described.
- `exclusions.py:493–523`; `ui/past_sessions.py:1161–1179`; `past_sessions.py:2008–2053` — the current export rule is fixed-drive-only, its save dialog uses only the chosen folder, and its cleanup helper treats a missing folder as gone. D7 and D6 identify the required differences for removable drives.
- `ui/main_window.py:1563–1622`; `ui/recovery.py:196–219`, `:322–325`; `ui/bridge.py:899–936`; `app.py:604–635` — the admission branches, protected Recovery ids, refusal invalidation and single periodic-sweep entry point support the proposed gate.
- `docs/practice/README.md:54–81`; `docs/practice/patient-information-and-consent.md:9`; `.cursor/plans/plan-past-sessions-backup.md:297–301` — the draft and approval sequence respects the separate consent versions. P.2 uses synthetic sessions, and P.5 requires both approval and decision P.4(a).
- `desktop/pyproject.toml:19`, `desktop/requirements-build.txt:26`, `app.py:665–702`, `scripts/build-release.py:472–486` — the dependency floor, frozen pin and existing self-check exit path match the plan.
- `.cursor/plans/plan-past-sessions-backup.md:242–302` — 11 checked tasks and 30 open tasks confirm 11 of 41. Verification was static at HEAD `5d63ed6`.

The body is not ready to build until the two backup-retention decisions and the two snapshot classification defects are corrected.

Materiality: 4 build-affecting / 2 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 14 (2026-11-25, verified by the planning session against `5d63ed6`)

- PR-HIGH-175 — VERIFIED build-affecting (`read_entry` fails on a corrupt transcript while the label opens; `_read` returns None for a row that does not decrypt). Applied: D8's presence branch (`skipped_present` needs the whole entry to open; `conflict_damaged`; `skipped_unreadable_row`), D9, the benign set, D10's keep sentence, the tests.
- PR-HIGH-176 — VERIFIED build-affecting (a store with no key and no rows reads as empty). Applied: no change to the success line's meaning — D14's step 1 (open the older backup; its verdict line) is what shows an older backup to be the only copy; Flow 1 says the success line claims nothing about older backups.
- PR-MED-177 — VERIFIED build-affecting, fix-induced. Applied: `missing` withdrawn from D5, the manifest, Flow 1, D10 and the tests (round 13's PR-HIGH-171 is met by D14's step 1 instead).
- PR-MED-178 — VERIFIED build-affecting (`_audio_key_state` needs no key, label or transcript). Applied: hop B's order; the test.
- PR-LOW-179 — VERIFIED record-only. Applied: the contract's wording.
- PR-LOW-180 — VERIFIED record-only. Applied: D13's sentence for the rollback section.

### Round 15 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 7)

Source: Codex gpt-6.2-astra high plan peer-review

**PR-HIGH-181 — A readable audit row can lack a fact held only in the older backup.**
Materiality: build-affecting
After a disk failure, the practitioner restores the available backup. A second backup recovered later holds the same `recorded` row with one recording export, while the restored row shows zero. Both rows read. D8 and D9 classify the local row as `skipped_present_row` without comparing their facts. Opening the second backup therefore gives the verdict, the next backup faithfully copies zero exports and reports that nothing eligible was left out, and destruction removes the only record of the export. This follows all three steps without a race. The export count is a real mutable audit fact. Evidence: `.cursor/plans/plan-past-sessions-backup.md:133`, `:143`, `:150`, `:165`; `desktop/src/scribe_desktop/audit.py:645`; `desktop/tests/test_audit.py:1159`.
Proposed amendment: Count a readable local row as benign only when it demonstrably preserves the backed-up facts, keep the local row untouched and report a conflict otherwise, and test the three steps with differing export counts.

**PR-HIGH-182 — Key repair can make a session readable despite a surviving deletion record.**
Materiality: build-affecting
Consider a recovered archive folder with matching ciphertext and a key the new login cannot unwrap. The newest backup has supplied a `deleted_early` row for that ID. Opening an older backup to recover other sessions selects `repair` because D8 decides every *present* folder before consulting either audit row. Restore then replaces the key and makes the deleted session readable again. C5 expressly promises protection wherever tombstone evidence survives, and importing rows first does not help when repair ignores them. Evidence: `.cursor/plans/plan-past-sessions-backup.md:133`, `:134`, `:136`, `:197`; `desktop/src/scribe_desktop/audit.py:569`, `:576`.
Proposed amendment: Preserve the whole-entry check for a readable local copy, but apply the tombstone and unknown-row checks before authorizing a key repair and test that a surviving deletion row leaves the broken key byte-identical.

**PR-HIGH-183 — One failed Open can authorize destruction of a recoverable `.csbk.part`.**
Materiality: build-affecting
A power cut after verification and before rename can leave a whole backup under the partial filename. D14 directs the practitioner to destroy it if it does not open. A mistyped passphrase produces exactly the same refusal as a damaged manifest, so this instruction can destroy the only good copy. Evidence: `.cursor/plans/plan-past-sessions-backup.md:121`, `:129`, `:165`, `:214`.
Proposed amendment: Tell the practitioner to retain a `.csbk.part` after an inconclusive Open, retry with the correct build and passphrase, and apply the ordinary three-step rule once it opens.

**PR-MED-184 — The summary can give the verdict while Restore still owes an audit write.**
Materiality: build-affecting
The plan explicitly supports retry after an entry was published but its `archived` update failed. If the backup and local row both read `none`, the entry and row are both benign, even under an equality check for PR-HIGH-181. Open therefore gives the verdict although pressing Restore performs the outstanding `none` → `archived` write. This contradicts Flow 2’s condition that nothing remains for Restore to do, on the very retry path the plan requires. Evidence: `.cursor/plans/plan-past-sessions-backup.md:104`, `:133`, `:135`, `:150`, `:216`; `desktop/src/scribe_desktop/audit.py:569`, `:596`.
Proposed amendment: Represent a pending `archived` update in the restore plan, show it in the summary, and test that the verdict first appears after the retry succeeds.

**PR-MED-185 — A successfully imported newer-schema row receives opposite keep advice on immediate reopen.**
Materiality: build-affecting
An audit-only backup may hold an authenticated `_NEWER` row. On a fresh login Restore writes its plaintext unchanged under the local key and counts it as restored, suppressing the final “Keep this backup” sentence. Immediately reopening the same file classifies that local row as `skipped_unreadable_row` and withholds the verdict. Nothing changed between those observations. The planned newer-schema UI test includes a session, whose separate refusal masks the audit-only case. Evidence: `.cursor/plans/plan-past-sessions-backup.md:133`, `:143`, `:150`, `:215`, `:221`; `desktop/src/scribe_desktop/audit.py:436`.
Proposed amendment: Count the opaque row as successfully written while keeping its unreadable status for the final advice, and test Restore followed by Open with a newer-schema audit row alone.

**PR-MED-186 — Rollback can bypass the staging-key protection added to Delete now.**
Materiality: build-affecting
An interrupted repair can leave a usable DPAPI key or its temporary file in staging. D13 says no action is needed before rollback. At HEAD, startup cleanup is best effort, a cleanup refusal permits startup to continue, and `delete_entry` subsequently removes only the committed entry’s key. If the staged key still cannot be removed, the older build can report a successful deletion while that second key survives. This is the reason D12 changes deletion in 0.5.0, and it applies to an entry without any recording. Evidence: `.cursor/plans/plan-past-sessions-backup.md:136`, `:137`, `:160`, `:161`; `desktop/src/scribe_desktop/past_sessions.py:895`, `:921`, `:1519`, `:2135`.
Proposed amendment: Make rollback after an interrupted repair conditional on confirming its staged key and key temporary are gone, and cover that condition in P.6 without changing recording deletion.

**PR-MED-187 — The kept-recording count can tell the practitioner a recording exists when the app has none to delete.**
Materiality: build-affecting
D5 correctly excludes an entry whose recording key is live even when `audio.enc` is missing. Flow 1 nevertheless says that session *holds a kept recording*. In this exact state HEAD reports `recording_state == "none"` and `delete_recording` refuses with `recording_not_kept`. The exclusion is correct, but the specified UI explanation is false and the practitioner cannot resolve it with the advertised action. Evidence: `.cursor/plans/plan-past-sessions-backup.md:72`, `:101`, `:126`, `:150`, `:160`; `desktop/src/scribe_desktop/past_sessions.py:1079`, `:1887`, `:1896`.
Proposed amendment: Keep the custody check and use wording true for both cases, such as “H sessions were left out because their recording keys are still present,” with a wording test for missing audio.

**PR-LOW-188 — The pre-reset explanation claims Open can prove which file was restored.**
Materiality: record-only
Two pre-reset backups can contain identical entries and rows. After restoring one, the other passes every comparison without ever having been restored from. The contents are accounted for, so this counterexample loses no data, but D14 and decision 0.12 say the check can pass only after restoring from that particular file. The app deliberately keeps no run ledger. Evidence: `.cursor/plans/plan-past-sessions-backup.md:53`, `:165`, `:253`; `desktop/src/scribe_desktop/audit.py:1091`.
Proposed amendment: Describe the verdict as evidence about recovered contents, and state any requirement to restore from a particular pre-reset file as a practitioner step.

**Other cites spot-checked**

- `desktop/src/scribe_desktop/past_sessions.py:725`, `:747`, `:810`, `:1063`, `:1852` — a retried Complete stages a fresh entry key, and recording deletion zeroes the recording key before unlinking. Checking recording-key custody in both backup hops supports decision 0.13.
- `desktop/src/scribe_desktop/past_sessions.py:755`, `:1729`; `desktop/src/scribe_desktop/session_store.py:641`, `:677`, `:764`, `:1037`; `desktop/src/scribe_desktop/transcription.py:1434` — the label ID, transcript parse, saved-note binding and generated-record checks have concrete existing implementations for `entry_opens` and staged verification to share.
- `desktop/src/scribe_desktop/audit.py:465`, `:1011`, `:1184`, `:1207`, `:1245` — pruning is month-based, duplicate rows are ambiguous, writes check the month folder, and a missing key beside rows differs from a fresh store.
- `desktop/src/scribe_desktop/exclusions.py:239`, `:493`; `desktop/tests/conftest.py:331` — the existing layer and fixed-drive export rule provide the proposed integration points and a test sentinel. The one-handle ZIP and volume-GUID paths received static review only.
- `desktop/src/scribe_desktop/ui/recovery.py:196`, `:322`; `ui/main_window.py:1588`, `:1601`, `:1612`; `ui/bridge.py:899`, `:915`, `:929`; `ui/tasks.py:36`; `desktop/src/scribe_desktop/app.py:604` — the two Recovery lists, protected IDs, write and enrolment guards, bridge refusal lifetime, worker signals and single periodic-sweep entry point support D11.
- `desktop/tests/test_ui_screens.py:11175`, `:11234`; `desktop/tests/test_shadow_exits.py:219`; `desktop/tests/test_install_layout.py:470`; `docs/practice/README.md:54`, `:79`; `desktop/tests/test_pilot_docs.py:209` — the named UI and literal pins exist. A marked v4 draft alongside current v3 is compatible with the practice versioning rule. P.2 uses synthetic sessions, and C15 and P.5 place the first real backup after approval and the existing-records decision.
- `.cursor/plans/plan-past-sessions-backup.md:3`, `:244`, `:302` — the body contains 41 task checkboxes, 11 checked. Review was read-only at `5d63ed6`; no tests or builds ran.

The body is not ready to build because the three-step rule can lose an audit fact, and key repair can reverse a recorded deletion.

Materiality: 7 build-affecting / 1 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 15

Every finding was read against the plan body and the code at `5d63ed6`. All eight are VERIFIED as stated (the reviewer's materiality accepted: 7 build-affecting, 1 record-only). Five of them are consequences of two parts of the design, so they were not patched: the practitioner cut those parts (decisions 0.14 and 0.15) and the body was amended in place.

- **PR-HIGH-181** — verified (`_apply`/`record_export` keep a mutable `exports` count on the row; D9 compares nothing for a row that reads). /fix decision: RESOLVED BY DECISION 0.14 — no verdict line exists to be wrong; D14's one rule keeps every backup made before a restore, and names the uncompared-row case as limit (ii).
- **PR-HIGH-182** — verified (the round-14 planner decided a present folder before any audit row). /fix decision: RESOLVED BY DECISION 0.15 — the key repair is removed; Restore never touches a present path; a set-aside session restores only through the absent-entry path, where a surviving deletion row gives `skipped_deleted` (tested).
- **PR-HIGH-183** — verified (D2 gives one refusal code for a wrong passphrase and a damaged manifest). /fix decision: APPLIED — D14: a `.csbk.part` is kept as a backup of unknown content and is never destroyed because an Open failed; a copy is renamed to try it.
- **PR-MED-184** — verified. /fix decision: RESOLVED BY DECISION 0.14 — the verdict line is withdrawn; the pending `archived` write is still completed by a retry and reported by its own sentence.
- **PR-MED-185** — verified. /fix decision: RESOLVED BY DECISION 0.14 for the advice (neither line advises any more), and APPLIED for the record — D9 says a restored newer-schema row is counted restored and reads as unreadable on reopen, both true; a test covers the audit-only case.
- **PR-MED-186** — verified (`clean_staging` is best effort; an older build's `delete_entry` removes only the committed key). /fix decision: RESOLVED BY DECISION 0.15 — no repair, so `.staging` never holds a key for an entry that exists; `delete_entry` and `_remove_key_first` are untouched and the rollback rule needs no step.
- **PR-MED-187** — verified (`_recording_state` is `none` and `delete_recording` refuses `recording_not_kept` when the key is live and the audio is missing). /fix decision: APPLIED — the lines say "a kept recording or its key"; D12 names the stuck state as a residue the downtime procedure covers; the custody check is unchanged.
- **PR-LOW-188** — verified, record-only. /fix decision: RESOLVED BY DECISION 0.14 — no line claims which file was restored; the rule keeps every backup made before an audit reset or a restore.

/fix notes: amendments confirmed on disk (a non-empty diff for each edit; the script asserts each replaced string occurred exactly once). Siblings reconciled: the Agreed Scope and Excluded bullets, the Key Findings' DPAPI note, Flows 1, 2 and 4, D8–D14, the schema table, C5 and C12, the Validation lists (`test_restore.py`, `test_past_sessions.py`, `test_archive_run.py`, the UI tests, the manual checks), the handoff note, decisions 0.5, 0.9 and 0.12, Tasks 1.1, 1.2, 2.4, 3.2, 4.1–4.4 and H3, and the progress line. Two design details were added inside decision 0.15 and one inside 0.14, each marked for the practitioner's approval at P.3: a session that still holds a kept recording is not set aside; a session completed after the last backup stays set aside; backups made before a loss, a set-aside, a restore or a new audit record are kept.

### Round 16 - 2026-11-25 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 8)

Source: Codex gpt-6.2-astra high plan peer-review

**PR-HIGH-189 — The disposal rule can destroy the only copy of a set-aside clinical record.**
Materiality: build-affecting
D8 accepts that a session completed after the last backup stays set aside. D14 then directs the practitioner to destroy the folder once the old password cannot be recovered and everything *in a backup* has been restored. Both conditions can be true while the folder still holds the only copy of yesterday’s consultation. The cited precedent covers a content-free audit store. The existing practice procedure expressly leaves destruction of an unreadable clinical entry pending independent review. Evidence: `plan-past-sessions-backup.md:135,166`, `docs/security/retention-schedule.md:74,253`, `docs/practice/downtime-procedure.md:105–112`.
Proposed amendment: Keep a set-aside folder containing any unaccounted-for clinical entry under the existing unreadable-record retention procedure and carry its disposal question to independent review.

**PR-HIGH-190 — Set-aside can strand the evidence of a recording deletion before the audit retry succeeds.**
Materiality: build-affecting
Delete recording deliberately leaves the zeroed key in place when its audit write fails. Startup retries the write and gives tidy the IDs it has positively cleared. After a DPAPI break, that first retry can fail. Flow 4 then resets the audit and moves the entry, including its zeroed key, outside every later retry. Restore can subsequently import an audit row saying the recording was kept with no deletion date, even though the evidence needed to correct it survived on this computer. The plan explicitly tests for moving those sidecars. Evidence: `plan-past-sessions-backup.md:112,135,145,218`, `past_sessions.py:1105–1118,1129–1136`, `app.py:513–529,549–552`, `test_past_sessions.py:1926`.
Proposed amendment: Leave entries with outstanding recording-deletion evidence in the active archive until the existing audit reconciliation clears them, and test audit reset, row import, reconciliation, set-aside and restore in that order.

**PR-MED-191 — A successful DPAPI probe does not classify a later operational failure.**
Materiality: build-affecting
The existing unwrap catches every exception from `CryptUnprotectData` at the same site. The proposed classifier has an outcome for DPAPI refusing a blob but none for Windows being temporarily unable to perform that particular call. A probe can succeed before the call on a readable entry fails. Carrying the existing catch-all into `dpapi_refused` would move that entry, potentially the only copy since the last backup. Evidence: `session_store.py:654–670`, `plan-past-sessions-backup.md:92,135,141,218`.
Proposed amendment: Specify which DPAPI errors qualify an entry for moving, leave it in place on operational or unrecognised errors, and test a successful probe followed by a transient per-entry failure.

**PR-MED-192 — Restore cannot distinguish unreadable retention settings from a deliberate choice to keep sessions indefinitely.**
Materiality: build-affecting
At HEAD the page sets `retention_days=None` when the settings file is unreadable and separately remembers `_settings_unreadable`. That fallback prevents deletion. D8 passes only `retention_days` to the planner, where `None` authorises adding an entry of any age. Consequently, an old backup can reintroduce a session beyond the practitioner’s seven-year setting while that setting cannot be read. Evidence: `ui/past_sessions.py:820–835`, `past_sessions.py:2216–2235`, `plan-past-sessions-backup.md:112,136,280`.
Proposed amendment: Preserve the settings-read result through Open, allow file verification, and require a readable retention choice before Restore can add age-dependent entries.

**PR-MED-193 — The set-aside report makes two claims its counters cannot support.**
Materiality: build-affecting
D8 counts every normally readable entry under `left`. D10 describes all of them as sessions that cannot be read. D8 also counts an uninspectable recording key under `held`, while D10 says a recording or key is present. A mixed archive after a reset is enough to make the first line false, and a failed inspection establishes no fact about presence. Evidence: `plan-past-sessions-backup.md:135,151,218`, `past_sessions.py:1852–1871`.
Proposed amendment: Report `left` as other entries left in place and describe `held` as entries whose recording key was present or whose absence could not be confirmed.

**PR-MED-194 — The recovery instructions can point to a hidden button and promise a restore the planner will skip.**
Materiality: build-affecting
A keyless leftover counts as `skipped_not_readable`, but the store omits it from the listing used to show the set-aside button. If it is the only occupied path, Open tells the practitioner to press a button that is absent. Separately, Flow 4 says Restore adds every moved session the backup holds, while the plan’s own test requires a moved ID with a surviving tombstone to be skipped. The seven-year cutoff also still applies. Evidence: `past_sessions.py:927–941,1702–1705`, `plan-past-sessions-backup.md:112,136,147,151,218`.
Proposed amendment: Show the button hint only when the action is available, and have Flow 4, the confirmation and the result direct the practitioner to Open to see which moved sessions Restore can add.

**PR-MED-195 — The backup success line still gives a keep instruction.**
Materiality: build-affecting
Flow 1’s partial-success line ends “Keep your older backups.” Task 2.3 instructs the executor to implement that line. Decision 0.14 assigns this judgment to the practitioner using D14 and limits the app to reporting facts. The exact-string test covers summaries and reports but leaves this success line exposed. Evidence: `plan-past-sessions-backup.md:56,103,166,222,257,275`.
Proposed amendment: End the partial-success line after its counts and extend the facts-only wording assertion to both forms of backup success.

**PR-LOW-196 — D14’s account of present audit rows contradicts the provenance-recovery rule.**
Materiality: build-affecting
The prescribed document says the app “never compares a present audit row with a backed-up one.” D9 requires precisely that comparison for a local `pre_audit` row, including its month, origin, facts and timestamp, and can replace it. This matters when explaining what a restore changed in the local audit record. Evidence: `plan-past-sessions-backup.md:139,144,166,287`.
Proposed amendment: Describe the narrow provenance-recovery comparison and state that Restore does not otherwise reconcile the facts in two readable audit rows.

**PR-LOW-197 — Startup does list the set-aside folder.**
Materiality: build-affecting
D8, the schema table and Task 4.1 promise that nothing in the app ever lists the folder again. On every startup, `mark_not_indexed` descends into ordinary directories beneath the data root using `os.scandir` and may set directory attributes. The archive readers and sweep can ignore the moved records while this existing protection continues to visit their directories. Evidence: `plan-past-sessions-backup.md:135,180,287`, `app.py:827–835`, `exclusions.py:659–685,703–705`.
Proposed amendment: Scope the promise to opening clinical content, archive listing, restore, retention and deletion, and acknowledge the existing startup directory-attribute walk.

**PR-LOW-198 — Task 1.1 cannot meet its acceptance criteria in the stated order.**
Materiality: build-affecting
Task 1.1 requires all set-aside validation items to pass, including restoring a moved ID and skipping one with a tombstone. Tasks 3.1–3.2 supply that planner and restorer. The same validation block requires a real-DPAPI test in `test_past_sessions.py`, while C9 names only two other files as exceptions. HEAD already provides an appropriate real-entry-key test class under `tmp_path`. Evidence: `plan-past-sessions-backup.md:202,218,263,280–281`, `test_past_sessions.py:1453–1465`.
Proposed amendment: Give Task 1.1 the store and blob-classification tests, explicitly permit its existing Windows-only fixture under C9, and assign the two restore integration assertions to Task 3.2.

**Spot-check results**

- `past_sessions.py:722–751,755–815,1840–1871` — each staged generation gets a fresh entry key, and recording-key inspection distinguishes `absent`, `zeroed`, `live` and `unknown`. The existing Complete publisher removes its destination, confirming the need for a separate add-only publisher.
- `transcription.py:1434–1448`, `session_store.py:764–791,1012–1035`, `past_sessions.py:1728–1751` — the named transcript, saved-note, generated-note and label checks exist. They provide the validation that backup verification and staged restore can share.
- `audit.py:416–437,997–1019,1079–1128,1148–1188,1245–1280` — newer rows, duplicate IDs, missing keys beside rows, reset-by-rename and the non-creating read are distinguishable at HEAD.
- `app.py:449–464,823–826`, `ui/main_window.py:1548–1561,1563–1622`, `ui/recovery.py:196–219`, `ui/bridge.py:899–945` — the startup order, recovery lists, busy states and Chrome refusal lifetime match the integration points named in D11.
- `docs/practice/README.md:48–61,75–81`, `plan-past-sessions-backup.md:302–306` — a marked v4 draft can coexist with approved v3. P.2 uses an isolated synthetic store, and P.5 explicitly requires both document approval and decision P.4(a).
- HEAD was `5d63ed6`. The tracked diff named only the plan. Its body ends at line 308 and contains 13 checked tasks out of 44. Verification was static, with no tests, builds, model loads or clinical-data access.

The body is **not ready to build** until it preserves pending deletion evidence, corrects the set-aside disposal procedure, and resolves the remaining restore, wording and test-contract conflicts above.

Materiality: 10 build-affecting / 0 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 16

Every finding was read against the plan body and the code at `5d63ed6`. All ten are VERIFIED. The composer's own grading: 189–192 and 194–195 build-affecting as labelled; 193 build-affecting (a line the app shows would be false); 196–198 are true and were applied, though each is closer to record-only (a document sentence, a promise worded too widely, a task's Done-when).

- **PR-HIGH-189** — verified (`downtime-procedure.md` "Past sessions problems" leaves the destruction of an unreadable entry to a reviewer question; the retention schedule's set-aside row is for the content-free audit store). /fix decision: APPLIED — D14 keeps the set-aside folder under that existing rule and extends the reviewer question to it; the retention row and D8's residue say KEPT.
- **PR-HIGH-190** — verified (`delete_recording` keeps the zeroed key when its audit record fails; `record_deleted_recordings` and `tidy_dead_recordings` finish it at the next start or tick, on the existing row when the label cannot be read). /fix decision: APPLIED — an entry qualifies only with `audio-key.enc` and `audio.enc` both confirmed absent; anything else is `held`; Flow 4 gives the order (restore the rows, restart, set aside again); tested.
- **PR-MED-191** — verified (`unwrap_key_from_file` catches every exception of `CryptUnprotectData` at one site). /fix decision: APPLIED — D9 names the two qualifying `winerror` codes; every other exception is `dpapi_error`, counted `left`; tested after a passing probe. Fail-safe if a code is wrong: nothing is moved.
- **PR-MED-192** — verified (`_load_settings` sets no retention and `_settings_unreadable` on a file that cannot be read). /fix decision: APPLIED — Restore is disabled, with its own line, while the settings file cannot be read.
- **PR-MED-193** — verified. /fix decision: APPLIED — a key that unwraps is not counted; `left` and `held` lines reworded to what the counters establish.
- **PR-MED-194** — verified (`_committed_dirs` omits `pending` and keyless folders, so the page's listing and the button never see them). /fix decision: APPLIED — `skipped_leftover` for an unlisted present path (counted In progress here); the hint therefore shows only where the button does; Flow 4, the confirmation and the report send the practitioner to Open to see what can be restored.
- **PR-MED-195** — verified. /fix decision: APPLIED — the partial-success line ends after its counts; the exact-string test covers both forms.
- **PR-LOW-196** — verified. /fix decision: APPLIED — limit (ii) names the provenance-recovery case and says no other reconciliation is made.
- **PR-LOW-197** — verified (`mark_not_indexed` walks every folder under the data root at start-up). /fix decision: APPLIED — the promise is scoped to opening, listing by the archive, restore, retention, deletion and export; the walk is acknowledged in D8 and the schema table.
- **PR-LOW-198** — verified (`TestRealEntryKeys` already uses real DPAPI under `tmp_path`). /fix decision: APPLIED — the two restore assertions moved to `test_restore.py` (Task 3.2); C9 admits the set-aside's real-DPAPI test, which no longer assumes which refusal a damaged blob gives.

/fix notes: amendments confirmed on disk (each replaced string asserted to occur exactly once). Siblings reconciled: D8's set-aside bullet (rewritten whole), D9, D10's confirmation and lines, D12 (3), D14 and its retention row, Flows 1 and 4, the schema table, C9, the Validation lists and Tasks 1.1, 4.1 and 4.2. The pass ended at its raised cap (eight rounds on this body: 13, 12, 10, 10, 6, 6, 8, 10) without a clean round; the round-16 amendments are UNREVIEWED. What happens next is the practitioner's decision.

### Round 17 - 2026-11-26 - past-sessions-backup plan, independent cross-family codex plan peer-review (consolidated body, round 9, focused)

Source: Codex (gpt-6.2-astra high) plan peer-review

**PR-MED-199 — A sweep between audit reset and Restore can clear the evidence of a recording deletion.**
Materiality: build-affecting
Flow 4 and D12 say the deletion record finishes in place (`plan-past-sessions-backup.md:112`, `:135`, `:161`). After reset, an unreadable label selects `create=False`. With no local row, the audit update returns success without writing one. A restart or ordinary sweep between the two practitioner actions can then remove the zeroed key and remaining audio file. Importing an older row afterwards can leave `kept_at` populated and `deleted_at` empty, with nothing for a second restart to discover (`ui/past_sessions_view.py:649`, `audit.py:825`, `audit.py:1159`, `app.py:549`, `past_sessions.py:1154`). This affects the audit fact. The recording had already been deleted.
**Proposed amendment.** Keep deletion unchanged, qualify Flow 4 and D12’s guarantee, and cover reset → sweep with no row → import in the restore tests so the resulting audit state is explicit.

**PR-MED-200 — Task 3.1 calls for the entire restore plan to run again for each entry.**
Materiality: build-affecting
D8 takes the listing once and requires each item to be reclassified immediately before its write, but Task 3.1 says to rerun `plan_restore` per entry (`plan-past-sessions-backup.md:136`, `:137`, `:282`). The real listing unwraps a key and decrypts a label for every committed entry (`past_sessions.py:927`, `:936`, `:1718`). Restoring 1,000 entries onto an empty computer as Task 3.1 directs would cause 499,500 repeat label unwraps on the disabled GUI thread.
**Proposed amendment.** Run the full planner once, share a single-ID classifier with the pre-write recheck, and verify that restoring more entries does not increase the number of whole-archive listings.

**PR-MED-201 — The set-aside checks for a child key before checking whether the child is a junction.**
Materiality: build-affecting
D8 explicitly orders the key-absence check first (`plan-past-sessions-backup.md:135`). Inspecting `child\key.dpapi` already traverses a directory junction. If its target has no key, D8 silently skips the child as a keyless leftover, while Validation requires a linked child to count as `left` (`:218`). HEAD checks the child itself first and explains why a junction in the middle of a path matters (`past_sessions.py:1696`, `session_store.py:695`).
**Proposed amendment.** Classify a linked or uninspectable child as `left` before accessing anything beneath it, and test a junction whose target has no key.

**PR-MED-202 — Refusing a DPAPI blob does not establish that the blob was intact.**
Materiality: build-affecting
D8 describes the qualifying blob as “intact, full-size,” while D9 expressly qualifies `ERROR_INVALID_DATA`, including for damaged bytes (`plan-past-sessions-backup.md:135`, `:141`). HEAD’s size check only rules out blobs shorter than 16 bytes (`session_store.py:168`). The Windows API also allows several outcomes for damaged data, so Validation’s arbitrary flipped-byte case cannot establish a universal classifier result (`plan-past-sessions-backup.md:218`). This does not establish that a readable session would move. [Microsoft’s `CryptUnprotectData` contract](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata)
**Proposed amendment.** Define qualification by the observed allowlisted refusal after the size check and successful probe, remove the claim of proven integrity, and use deterministic injected errors for the classifier assertions.

**PR-MED-203 — Failure to create the set-aside folder has no report outcome.**
Materiality: build-affecting
D8 covers a failed per-entry rename, and D10 covers a failed probe or listing. Neither covers `mkdir` failing before the first rename, for example on a full disk (`plan-past-sessions-backup.md:135`, `:151`, `:218`). The cited audit-reset precedent explicitly handles destination creation or naming failure and treats removal of an empty folder as best effort (`audit.py:1103`, `:1118`, `:1123`).
**Proposed amendment.** Give folder-creation failure a content-free refusal stating that nothing moved, and make the empty-folder cleanup assertion conditional on `rmdir` succeeding.

**PR-MED-204 — The final report omits items skipped on both passes.**
Materiality: build-affecting
D8 maps a collision and an item whose reclassification *no longer* writes to “Left as they are.” It gives no final bucket to an item already planned as `skipped_present`, `skipped_deleted` or `skipped_pruned_row` that remains so (`plan-past-sessions-backup.md:139`). On an immediate second Restore, every item can be in that position. The summary also calls a keyless leftover “In progress here” (`:136`, `:151`), although HEAD declares deletion successful once its key is gone and can leave locked files behind (`past_sessions.py:2115`, `:2134`).
**Proposed amendment.** Map unchanged planned skips explicitly to “Left as they are,” use a summary label that covers both live sessions and leftover files, and assert exact totals for an all-skipped retry.

**PR-MED-205 — Open cannot show which set-aside sessions it can restore.**
Materiality: build-affecting
Flow 4, the confirmation and the success line all make this promise (`plan-past-sessions-backup.md:112`, `:147`, `:151`). The planner counts all manifest IDs and never consults the set-aside folder (`:135`, `:136`). If the moved session postdates the backup and one unrelated session is missing locally, “To add: 1” refers entirely to the unrelated session. Two other report phrases exceed their evidence. A pending entry counts as `left` before its key is tested, and the probe can fail during unprotection after protection succeeded (`:135`, `:151`, `:218`).
**Proposed amendment.** Say that Open shows how many sessions the backup can add on this computer, describe `left` as entries that could not be safely assessed, and describe a probe failure as Windows being unable to verify the test value.

**PR-LOW-206 — Re-listing leaves the page’s unreadable-session warning stale.**
Materiality: build-affecting
Under seven-year retention, the page keeps a separate `_last_sweep` report. Refreshing the listing after set-aside or Restore, as Tasks 3.3 and 3.4 specify, does not invalidate it (`plan-past-sessions-backup.md:284`, `:285`, `ui/past_sessions.py:379`, `:1013`). After every moved entry has been restored and opens, the page can still say those sessions cannot be read. The existing Delete action already adjusts this cached count (`ui/past_sessions.py:679`, `:1041`, `ui/past_sessions_view.py:708`).
**Proposed amendment.** Invalidate or reconcile the cached sweep report after archive membership changes, and verify the warning clears after set-aside and restore under seven-year retention.

**PR-LOW-207 — Task 2.1 requires an integration assertion whose action is wired in Task 3.4.**
Materiality: build-affecting
Task 2.1 requires all of `test_archive_run.py` to pass. That file must prove each admission refusal prevents a set-aside from moving anything, but the call connecting admission to `set_aside_refused()` belongs to Task 3.4 (`plan-past-sessions-backup.md:221`, `:275`, `:285`). Testing the admission function alone cannot prove that the button obeys it.
**Proposed amendment.** Keep the admission decision tests in Task 2.1 and assign the end-to-end “refused set-aside moves nothing” assertions to Task 3.4.

**Cites spot-checked**

- **Revision and progress.** HEAD is `5d63ed6`. The plan was the only modified tracked file. Its body ends at line 310 and contains 13 checked tasks out of 44.
- **Set-aside custody.** The archive has its own key description, `_forget_dates` clears all three date caches, and reconciliation and retention enumerate children of the active archive. The sibling folder stays outside those operations. The indexing walk visits directories and sets attributes. `past_sessions.py:547`, `:642`, `:868`, `:1586`, `:1684`, `exclusions.py:659`.
- **DPAPI error boundary.** pywin32 routes a failed `CryptUnprotectData` call through its Windows API error mechanism. Neither the repository nor Microsoft’s API contract establishes one guaranteed error for a real administrator password reset. Under D9, an unrecognised error leaves the entry in place. The repository example using the signed value is a fake for **protect**, so it is not evidence of an actual reset outcome. `session_store.py:661`, `desktop/tests/test_audit.py:1530`. [pywin32 wrapper](https://github.com/mhammond/pywin32/blob/main/win32/src/win32crypt/win32cryptmodule.cpp) · [Microsoft API reference](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata)
- **Fresh login and disabled Restore.** A missing settings file returns valid defaults. An unreadable file sets the page flag, and explicitly selecting even the displayed choice can replace it. An empty audit store does not offer reset. A missing key beside rows does. Both disabled states have an exit. `past_sessions.py:2216`, `ui/past_sessions.py:881`, `:895`, `audit.py:1079`, `:1257`.
- **Add-only publication and audit rows.** The existing `_publish` removes its destination, so the separate `_publish_new` is necessary. Existing staged verification reads the key back from disk. The `archived` transition accepts only `none`, and `create=False` preserves an absent row. D8’s pre-write tombstone check and no-replace publication are compatible with those contracts. `past_sessions.py:755`, `:777`, `:810`, `audit.py:569`, `:867`, `:1159`.
- **Review limits.** This was a static review. No tests, builds, model loads, clinical-data reads or file changes were performed.

The set-aside and add-only restore are ready to proceed to build under the practitioner’s Round 17 rule: I found no HIGH or CRIT defect.

Materiality: 9 build-affecting / 0 record-only / 0 invalid

Recorded by: the orchestrating session (composer-recorded round: the peer ran in a read-only sandbox and printed this block; transcribed verbatim from its log). Dispositions follow below once each finding is verified against the code.

#### Dispositions — Round 17

Every finding was read against the plan body and the code at `5d63ed6`. All nine are VERIFIED. The composer's own grading agrees with the reviewer's severities (no HIGH); 207 is closer to record-only (a task's Done-when) and was applied all the same.

- **PR-MED-199** — verified (`unattended_write` gives `create=False` for a session with no readable label; `AuditLog._update` returns without writing when there is no row and `create` is False; `app.record_deleted_recordings` then clears the id and `tidy_dead_recordings` unlinks the files). /fix decision: APPLIED — deletion and the repair are unchanged; Flow 4 and D12 (3) no longer say the record is always finished; the case is a named residue (D12, Task 4.1) with a test in `test_restore.py`.
- **PR-MED-200** — verified (`list_entries` unwraps a key and reads a label for every committed entry; Task 3.1 said the planner is re-run per entry). /fix decision: APPLIED — one listing per Open; `classify_entry` takes it as an argument and is the recheck; the recheck can only withdraw a write; tested by a call count.
- **PR-MED-201** — verified (`_entry_dirs` checks `_is_link(child)` before anything else, and `SessionLinkError`'s note says why). /fix decision: APPLIED — D8 (c) puts the child's `link_state` first; a junction whose target has no key is tested as `left`.
- **PR-MED-202** — verified (D8 said "intact, full-size" while D9 read code 13 as a blob that is not intact; `key_blob_is_dead` only rules out a short or zeroed blob). /fix decision: APPLIED — the rule is the observed allowlisted refusal after the size check and the probe, with no claim about why; classifier assertions use injected errors; the real-DPAPI test assumes no particular answer for a damaged blob. Both codes still qualify: either way the session cannot be read here and nothing is deleted.
- **PR-MED-203** — verified (`AuditLog.reset` raises `set_aside_failed` and `no_free_name`; the plan gave the store's version no outcome). /fix decision: APPLIED — `set_aside_unavailable` with its own line; the empty-folder removal is best effort; both tested.
- **PR-MED-204** — verified (the table gave an unchanged planned skip no report count; `_remove_key_first` returns True once the key is gone, so a keyless folder is the remains of a deletion as well as a session in progress). /fix decision: APPLIED, by the composer's rule and not the reviewer's proposed one — the final report counts only what the plan set out to write, so a planned skip is not counted again (calling a deleted or expired session "left as it is" would be untrue); the summary label reads "In progress or left over here"; an all-skipped second Restore is pinned exactly.
- **PR-MED-205** — verified (the summary is counts over every manifest id; the planner never looks at a set-aside folder). /fix decision: APPLIED — Flow 4, the confirmation and the report say "how many sessions"; `left` is "could not be safely assessed"; the probe line says "verify".
- **PR-LOW-206** — verified (`_last_sweep` is kept across a re-list; Delete now lowers its `undated` count by hand at `ui/past_sessions.py` about line 681). /fix decision: APPLIED — the set-aside lowers the same count by the number moved; tested under "7 years". A Restore adds only readable sessions and changes no such count.
- **PR-LOW-207** — verified. /fix decision: APPLIED — `test_archive_run.py` tests the admission function; the button's "nothing moved" assertions belong to Task 3.4.

/fix notes: amendments confirmed on disk (each replaced string asserted to occur exactly once). Siblings reconciled: Flow 4, D8's set-aside, planner, restorer and table bullets, D9, D10's button and lines, D12 (3), the Validation lists for `test_restore.py`, `test_past_sessions.py`, `test_archive_run.py` and the UI tests, the handoff note, and Tasks 3.1, 3.4 and 4.1. No practitioner decision is changed. New since their last reading, for approval at P.3 with the rest of the wording: the reworded set-aside confirmation and report lines, the summary label "In progress or left over here", and the second Restore's short report.
