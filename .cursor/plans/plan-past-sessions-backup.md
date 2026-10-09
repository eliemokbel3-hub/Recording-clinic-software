# Feature Implementation Plan
**Feature:** past-sessions-backup
**Overall Progress:** `20%` (7 of 35 tasks)

## Lifecycle State
- Active — hardened by `/review-plan` 2026-10-09 (decisions 0.1–0.6 and 0.9 taken; the same day's four-lens critique folded in) and by a five-round cross-family `/peer-loop` plan review the same day (codex `gpt-6-astra`; 35 findings, all verified and applied; accept-closed at the cap by the practitioner); ready for `/execute-loop` from Phase 1

## Completion Status
- Completion timestamp: —
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `plan-privacy-professional-controls.md` (its Deferred — Actionable Later item "Passphrase-protected backup/restore of Past sessions", disposition 2026-10-01; cited again at `plan-installation.md` Deferred and `plan-pilot.md` Deferred / Out of Scope). PLAN.md Phase 6's archive is the store this plan copies.
- Follow-up plans: None

## Goal
Let the practitioner make a passphrase-protected, encrypted backup file of the Past-sessions archive — the kept transcripts, saved and generated notes and their labels — together with the content-free audit record, onto a drive of their choosing on or attached to this computer, and restore it into Clinic Scribe on a new Windows login or a new computer after a disk failure, a Windows reinstall or a password reset that broke DPAPI. Nothing reaches a network or a cloud folder; the passphrase is never stored; the backup never holds a kept development recording unless the practitioner decides otherwise in Phase 0 (and then only under a new consent version). The agent never reads a real kept transcript, note, name or recording, and never opens a real backup. Ships as 0.4.0 and reaches the installed app through the existing release path.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — drafted by a side session on Opus 5.5 on 2026-10-09 from the code at `aeec75e`, hardened the same day by `/review-plan` on Fable 5.1 (`claude-fable-5-1`); executor Opus-class through `/execute-loop` (cross-family peer codex `gpt-6-astra`); tier-gap dosing applied (the container and manifest contract, the audit API surface, the four-hop threading split, the restore classifications, the test-pin inventory and per-task acceptance criteria are locked below so the executor designs nothing). Every Phase P step is the PRACTITIONER's, from Explorer or a normal terminal, never an agent shell (`docs/lessons.md`, MSIX). The clinic 1 smoke (`plan-clinic-smoke.md`) runs in parallel and is practitioner-paced; this plan touches none of its files until Phase 4's document edits, which are reconciled against it at that point (C11).

Planning sources: the deferred item (`plan-privacy-professional-controls.md` Deferred — Actionable Later, "Passphrase-protected backup/restore of Past sessions") and its two citations; the Past-sessions and kept-recordings sections of `docs/security/threat-model.md` (residue (c) "UNTIL I DELETE THEM WITH NO BACKUP"), `docs/security/retention-schedule.md` (rows 67 and 134, the Past sessions rule), `docs/security/data-flow-map.md` flows 22 and 27; `past_sessions.py` (2255 lines at `aeec75e`), `audit.py` (schema v3), `secure_storage.py` / `session_store.py` (`SessionCrypto`, the DPAPI key-wrap helpers), `exclusions.py` (`check_location`, `check_export_location`), `sample_notes.py` (the bounded `zipfile` pattern); the practice documents' promises (inventory in Key Findings); the practitioner's answers of 2026-10-09 (decisions 0.1–0.6, every recommended option; the four `/review-plan` questions — replace unreadable entries key-first, the ZIP container, drop the run ledger and fold Check into Restore, no scratch consumed; the deferral gate confirmed as listed). Hardened by `/review-plan` 2026-10-09 (Fable 5.1; four parallel lenses — coverage 13, practicality 11, risk 19, simplicity 7 findings — every one reconciled against the code and folded in). No `/explore` scratch was consumed (the two that exist are unrelated; declined 2026-10-09).

### Agreed Scope (Build Now)
- **A backup file** (`.csbk` — a stored-only ZIP read only through its encrypted manifest, D11; one file per backup, named by date) holding every COMMITTED, readable Past-sessions entry's ciphertext files byte for byte plus its entry key wrapped under a key derived from the practitioner's passphrase (D2, D3), and the audit record's rows plus its store key wrapped the same way (D1).
- **Back up…** and **Open a backup…** on the Past sessions tab (D8), each behind a passphrase prompt; opening shows what the file holds and offers Close (the check) or Restore; ONE status line from the audit rows — the entries not yet in any backup and the last backup's date — shown after 7 days (decision 0.6).
- **A backup location rule of its own** (`check_archive_backup_location`, D4): the encrypted file may go to a fixed or removable drive, never to a cloud-synced folder the environment names, a network drive, the roaming profile or either app data folder; a backup on the same volume as the data folder is written with a warning.
- **Restore** adds entries that are absent locally — and REPAIRS only the DPAPI key of an existing entry this login can no longer unwrap, after its content has matched the backup's hashes and been opened with the recovered key (decision 0.9 as amended: the password-reset case; every other file of that entry, recording sidecars included, stays as it is) — skipping entries whose local or backed-up audit row says they were deleted; it never overwrites a readable entry, re-wraps every entry key under this login's DPAPI, verifies each entry through the existing readers before publishing it, and re-encrypts restored audit rows under the local audit key (D5, D6).
- **Audit row v4**: a nested content-free `backup` record (`last_backed_up_at`, `restored_at`) with two CSV columns last, and the `AuditLog` export/import surface the backup needs (D6, D7). Version **0.4.0** (D9), a build of record, installed by the practitioner (Phase P).
- **Documents**: the threat model's new section, data-flow flow 28, the retention schedule's rows, the rollback rule "below 0.4.0", `patient-info-v4`, and every "no backup" / "this Windows login only" sentence in `docs/practice/`, the design system, the intended-use document and the tab's own retention warning string amended to what the code now does (D10).

### Deferred — Actionable Later
- **Kept development recordings in the backup** (decision 0.2: excluded). Why: the consent document promises "The program makes no backup of it"; including audio needs `development-consent-v2`, a re-consent of every patient whose recording is held, and a far larger file. Intended outcome: a `development-consent-v2` and a per-backup "include kept recordings" tick. Trigger: the practitioner's decision to rely on kept recordings beyond the pilot. `Risk if deferred: minor` (the recordings are development material, deletable, not the record) · `Revisit by: before the pilot's exit gate if kept recordings are still held`.
- **Scheduled or automatic backups.** Why: a backup needs the passphrase at the moment it is made (never stored), so it is a deliberate act. Intended outcome: none unless the practitioner asks for an unattended backup under a stored key — a custody change in its own right. `Risk if deferred: correctness` (a forgotten backup is a stale backup; the status line of D8 is the control) · `Revisit by: commercialisation`. Gate disposition 2026-10-09: Defer.
- **Backing up the practitioner profile, learned style, learned phrases, clinic list and settings.** Why: recreatable (re-enrol, re-add the clinic keys, re-learn) and the voice profile is a biometric the threat model keeps on this login only. Intended outcome: a separate "settings export" if the practitioner finds re-setup costly. `Risk if deferred: ux-degradation` · `Revisit by: the first real restore`. Gate disposition 2026-10-09: Defer.
- **Clinic API keys** live in Windows Credential Manager and are re-entered after a reinstall (the Clinics tab). Not a backup item: a credential never enters a file. Named in the restore procedure.

### Excluded — Revisit Only If Needed
- **Any network or cloud destination**, including a NAS or a OneDrive folder, even for an encrypted file (decision 0.4). The patient documents promise the record is on the practitioner's computer and is sent nowhere; an encrypted copy elsewhere is a new promise, not an engineering detail. Reopened only by a new practitioner decision with the documents' independent review.
- **Incremental or differential backups.** Entries are text; a full copy is small (see Accepted Assumptions) and verifiable as one unit. Gate disposition 2026-10-09: Exclude.
- **Cross-channel restore** (a developer-build backup into the installed app or the reverse). The MANIFEST names the channel (the header's copy is a pre-filter only); both refuse the other's (D5). Synthetic content must never enter the clinical archive, and a real backup must never be opened on the developer build by the agent (C1). Gate disposition 2026-10-09: Exclude.
- **Restoring a single entry.** Restore is whole-archive-add-what-is-missing; the tab's Delete now serves any unwanted entry afterwards. Gate disposition 2026-10-09: Exclude.
- **A passphrase manager, hint or recovery.** A lost passphrase is a lost backup, by design; the documents say so. Gate disposition 2026-10-09: Exclude.
- **A run ledger of backups** (`backups.enc`). Dropped at the `/review-plan` pass: the v4 audit rows give "last backup" and travel with a restore, which a ledger would not; a ledger that located a `.part` would have to hold a path (against C7).

### Accepted Assumptions — Revalidate Later
- **Backup size.** Roughly 100–300 KB per entry (transcript + two notes + label, ciphertext); 1 000 entries ≈ 0.3 GB; a full copy per backup is fine without audio. With audio ≈ 55 MB per 30-minute recording — the reason decision 0.2 excludes it. Check: the first real backup's size on P.3. Gate disposition 2026-10-09: Accept.
- **Argon2id at 256 MiB fits the clinic computers.** The app already loads a 2.3 GB language model; the parameters are stored in the header so a later build can raise them without breaking older files (D3); a `MemoryError` is caught by type and refuses by name. Gate disposition 2026-10-09: Accept.
- **The practitioner keeps the passphrase and the drive apart** — the operating rule in the documents (Task 4.2), not something the app can check. Gate disposition 2026-10-09: Accept.
- **Restore happens on an app with NO live session** and with the practitioner present; the tab refuses while a recording is live or recoverable sessions are listed, and re-checks after the confirm (D5). Gate disposition 2026-10-09: Accept.
- RESOLVED at the `/review-plan` pass: Argon2id in the frozen build — `desktop/requirements-build.txt` hash-pins `cryptography==49.0.0` (its wheel bundles OpenSSL 4.0.1, which has Argon2id) and `scripts/build-release.py` installs from that lock; Task 0.7 is therefore a pre-H5 confirmation in the release build, not a Phase 1 gate.

### Key Design Decisions
See `Design Decisions` (D1–D12). The decisions that needed the practitioner are Phase 0's `[decision]` tasks (0.1–0.6, 0.9), all taken 2026-10-09.

## Key Findings

### Files / Symbols Involved
- `desktop/src/scribe_desktop/past_sessions.py` (every line verified at `aeec75e`) — `PastSessionStore` (`list_entries` L927 decrypts labels; `_committed_dirs` L1702 defines an entry by `key.dpapi` + no `pending` — it does NOT test that the key unwraps, the root of decision 0.9; `_stage` L722 writes `pending` and `_verify_staged` L755 takes a plaintext `ArchiveSource`, so restore needs siblings, not reuse; `_publish` L810; `_remove_key_first` L2115; `_staging_linked` L658; `_wrap_entry_key` / `_unwrap_entry_key` L547–554 with `PAST_SESSION_KEY_DESCRIPTION` and the conftest's `wrap_key` / `unwrap_key` seams; `clean_staging` L895 removes EVERY `.staging\<id>` at start-up and every sweep tick — the reason restore's staging runs on the GUI thread; `ExportRow` L479 / `recover_exports` L1333 / `_remove_part` L2008 — the `.part` pattern the backup writer simplifies; `read_replay_inputs` L1494 and `kept_session_ids` L952 show a label-free reader; `PastSessionListing.recording_kept` L407 is derived from files, so a restored entry without audio reads "no recording").
- `desktop/src/scribe_desktop/audit.py` — `AuditRow` v3 (L303), `RecordingRecord` (L288, the nested-record pattern and its tripwire registration `kept_at` L282 of `logging_setup`), `_upgrade_v1` / `_upgrade_v2` / `_decode` (L389–460; `_decode` L447 hard-codes the v3 name check), `_NEWER` L382, `_PAST_SESSION_FROM` L569 (the tombstone states), `AuditLog.rows` / `row_for` / `update` / `export_csv` (L972–1078), `_update` L1143 (applies a `Change` to a found or `pre_audit` row only — NO whole-row import exists), `_open_key` L1245 (raises `key_unreadable`), `reset` L1091 (the existing "Start a new audit record"), `_find` L~1180 (two row files for one id make `row_for` / `update` raise for ever), `_row_aad` L385 = `b"audit:" + id`, `month_prune_at`, `keeps_rows_of` L1021 (takes an aware `datetime`; rows hold `session_date: date`), `wrap_key_to_file` hard-wired at L1265/1273 with NO seam (`test_audit.py` monkeypatches the module attribute at L1513 or uses real DPAPI at L153 under `tmp_path`).
- `desktop/src/scribe_desktop/session_store.py` — `wrap_key_to_file(crypto, directory, *, description, filename) -> Path` L608 and `unwrap_key_from_file(directory, *, description, filename) -> SessionCrypto` L631 (reads the file ITSELF and raises ONE `KeyCustodyError` for an `OSError`, a dead blob, a DPAPI failure and a foreign description alike — so the repair planner needs a new blob-based sibling `unwrap_key_blob(blob, *, description)` with structured outcomes, Task 1.2; calls `_require_windows()`), `key_blob_is_dead(size)` L161 (THE deadness definition — `_MIN_KEY_BLOB_BYTES = 16`), `atomic_write_bytes` L567 — the DPAPI helpers (NOT in `secure_storage.py`); `secure_storage.SessionCrypto` (AES-256-GCM, 12-byte nonce prefix, `from_key` / `export_key` / `destroy`; `_cipher` makes an unzeroable `bytes` copy — the same residue applies to `K_b`).
- `desktop/src/scribe_desktop/exclusions.py` — `check_location` L435, `check_export_location` L493–523 (returns `ExclusionWarning | None`; refuses non-`DRIVE_FIXED`), `DRIVE_REMOTE` L165 and `DRIVE_FIXED` L469 are the ONLY drive constants; `check_backup_exclusions` L638, `WindowsLayer.backup_exclusions` L270 and `BACKUP_EXCLUSION_KEYS` already mean the Windows File-History registry exclusions — hence the name `check_archive_backup_location`; `WindowsLayer` (the injected seam; the conftest makes the real one raise).
- `desktop/src/scribe_desktop/sample_notes.py` L150, L345–388 — the codebase's existing bounded `zipfile` reader: it ADMITS stored and deflated input (`_DOCX_METHODS`) and writes its bounded intermediate copy stored-only; D11's container adopts its bounds and error-handling pattern while NARROWING accepted input to stored-only (round 1 PR-LOW-012).
- `desktop/src/scribe_desktop/ui/past_sessions.py` — `PastSessionsScreen` (L161; constructed at `ui/main_window.py` L722 with NO knowledge of live or recoverable sessions — Task 3.3's `session_busy` seam), `ChooseCsvPath` / `ChooseWavPath` seams (L112–115), `on_export_recording` L765 (the location-check + `.part` + rename pattern), `on_delete_clicked` L596 (two-click), `on_export` L972 (CSV), `status_lines`, `export_recovery_lines`; `ui/past_sessions_view.py` (Qt-free decision functions; `PastSessionsAudit` Protocol L54–112 — grows with every new audit method; `unattended_write`; L216 the retention warning string "makes no backup of its own" — a CODE string in the D10 inventory); `ui/tasks.py::TaskThread` (the worker pattern; its `failed` signal emits `type: message` — backup exceptions must carry type-only messages, C3).
- `desktop/src/scribe_desktop/logging_setup.py` — `_PAYLOAD_SIGNATURES` L73 (a new nested record registers a distinctive name; `test_audit.py:232` tolerates a new one if no log key renders as it).
- `desktop/src/scribe_desktop/install_layout.py` — `channel() -> Literal["production", "dev"]` L106 (the conftest's autouse `_production_channel` pins it by `monkeypatch.setattr(install_layout, "channel", …)`); `app.py` L801–809 (`recover_exports` → `run_sweep`; `clean_staging` → `reconcile_pending` → the kept-fact repair → tidy at L446–453).
- Tests that pin the current shapes and MUST change with Phase 1: `test_audit.py:860, 901, 985, 1092` (`schema_version == 3`), `:1195, 1213, 1219` (`CSV_COLUMNS[-4:]` — the four v3 columns `development_consent_version` + three `recording.*`, header AND values — become `[-6:-2]`), `:1352` (`CSV_COLUMNS[-6:-4]` mode / app_version — becomes `[-8:-6]`); `test_schema_versions.py:568` (the v1-upgrade schema tuple → 4), `:587, 658` ("written back as v3" → v4), `:610–619` (the current-version missing-field test — extended to v4's three required names), its `AUDIT_V1` / `AUDIT_V2` `Final` literals (add `AUDIT_V3` FIRST — Task 1.1); `test_audit.py:826–842` — `_v1_document` / `_v2_document` serialise the CURRENT model and delete only the v2/v3 fields, so after `backup` exists they would build contaminated "historical" documents that the new guard rightly refuses: both must also `del document["backup"]` (round 2 PR-MED-019); `audit.py:410` — `_upgrade_v2` writes `schema_version: AUDIT_SCHEMA_VERSION`, so a bare constant bump would carry v1/v2 rows straight to 4 and skip `_upgrade_v3` (round 1 PR-MED-006); `test_install_layout.py:868` (the version pin); `test_shadow_exits.py` (counts source references to the kept-recording reader, `speech.write_wav` and `wave` — a writer copying ciphertext by file name references none; `_tab_sources()` L164 pins every text widget in the two tabs — the passphrase `QLineEdit` lives ONLY in the new `ui/backup_dialog.py`).
- `desktop/requirements-build.txt` L26 hash-pins `cryptography==49.0.0`; `scripts/build-release.py` L71 installs from it — Argon2id is in the frozen build. `packaging/scribe.iss`, `.github/workflows/release.yml`, `scripts/register-native-host.py` — unchanged.
- Documents: `docs/security/threat-model.md` (residue (c) at L3017–3023; L3769 names the "audit says a recording is held" gap; L4044, L4084, L4102 name the deferral), `docs/security/retention-schedule.md` (row 67 "NO backup (deferred…)", row 134 "NO backup", L235, L257–264), `docs/security/data-flow-map.md` (flows 22, 27; a new flow 28), `docs/security/intended-use.md` L63 ("this Windows login only, with no backup"), `docs/release/pilot-builds.md` (a "Rolling back below 0.4.0" section above "below 0.3.0"), `docs/design-system.md` L533 (the retention-warning quote) and the tab's cues at L14–31, L123–130, L646–705, `PLAN.md` L152 ("Backup/restore of Past sessions is deferred"), `AGENTS.md`.
- `docs/practice/` sentences the plan makes false, to amend in `patient-info-v4` and its siblings (D10): `patient-information-and-consent.md` L59–60 ("can only be opened from your practitioner's own Windows login on that computer"), L60–62, L75 ("makes no backup of it. If the computer fails…") and the audit-record table row; `privacy-information.md` L87, L91 ("runs no backup or file-sync software" — stays true of SOFTWARE; the app's own backup is named beside it), L119 ("stores it on one computer only and makes no backup"); `clinician-review-guide.md` L134–135; `downtime-procedure.md` L150–152, L175 ("Losing the computer … there is no backup"); `README.md` L64, L153 and its versioning rule (L18–29: a changed sheet is a new version); `development-recording-consent.md` L61, L68 — these two stay TRUE under decision 0.2 and are given a pointer, not a change. Dry-run grep for Task 0.8: `no backup|makes no backup|NO backup|there is no backup|with no backup|Windows login` over `docs`, `PLAN.md` and `desktop/src`.

### Codebase Integration Notes
- Every entry is its own compartment (a fresh key, DPAPI-wrapped). A backup that WRAPS each entry key under the passphrase-derived key, and copies the entry's files unchanged, keeps that compartment through the backup and the restore, needs no decryption of content at backup time, and lets "Open a backup" verify file integrity by SHA-256 and the passphrase by one wrapped-key decrypt — without ever decrypting a transcript. Restore re-wraps the entry key with `session_store.wrap_key_to_file` for THIS login (the only DPAPI write) and verifies the staged entry through the readers with a sibling of `_verify_staged` that takes the backup's expected names and hashes instead of a plaintext source.
- The audit record has ONE store key and per-row AAD `b"audit:" + id`. Rows are copied as ciphertext with the store key wrapped under the derived key; at restore each row is decrypted under the backed-up key and re-encrypted under the LOCAL key with the same AAD — `_NEWER` rows too (their plaintext is re-encrypted unchanged; copied as ciphertext they would read as `unreadable`, and a second row file for one id makes `row_for` / `update` raise for that id for ever). A row for an id that exists locally is kept local (D6). `AuditLog` needs three new public methods (`backup_snapshot`, `restore_row`, `row_state`) and two injected key-wrap seams mirroring the archive's — today the audit key custody has none.
- A backup is taken while the app runs and `PastSessionStore` methods run on the GUI thread (C5 of the privacy plan). Argon2id at 256 MiB takes ~1 s and a USB write seconds, so the work is split into FOUR hops (D3): A (worker) derive `K_b`; B (GUI) snapshot the committed ids, unwrap → wrap → zero each entry key, snapshot the audit key and row paths; C (worker) read ciphertext BY PATH (plain `read_bytes`, never a store method, never the whole archive in memory), write the `.part`, verify, rename, zero `K_b`; D (GUI) `record_backed_up`, the status line. `PeriodicSweep` ticks run on the GUI thread and are SKIPPED throughout a run (C12), and Start is refused (both funnels) while a backup or restore run is active, because `clean_staging` would otherwise remove a restore's staging folder mid-verify; `skipped_gone` in C therefore covers only a source file that became unavailable on its own (a yanked drive, an external deletion), never a tick (round 5 PR-LOW-035).
- `pending` and `.staging` are excluded from a backup: an entry carrying `pending` may still be a Complete in flight; a restore publishes entries WITHOUT `pending` (there is no source session to wait for), so `reconcile_pending` never touches them.
- Restore and Delete now: the tombstone is the audit row's `past_session.state` (`deleted_early` / `expired`) — kept 7 years by month, while the archive's own retention is 7 years OR indefinite ("Until I delete them"), so an entry can outlive its tombstone's month (D5's `skipped_pruned_row` and its named residue; round 5 PR-LOW-035). Restore reads the LOCAL row first (its state readable / newer / unreadable / none), then the backup's row for the id; either saying deleted → `skipped_deleted`; a local row that is `newer` or `unreadable` → `skipped_unknown_row` (the tombstone cannot be known). Named residues: a backup taken BEFORE a Delete now still holds the entry and the app cannot reach the file (decision 0.5's operating rule); a Delete now whose audit write FAILED (counted only — `record_past_session` never raises) left no tombstone, and so did a Delete now made on 0.3.0 of a row 0.4.0 had touched (`_NEWER` → the write is skipped) — such an entry comes back on restore and is deleted again (the rollback rule says so).
- The same-login DPAPI break (decision 0.9, as amended by round 1 PR-HIGH-001): after a Windows password reset every entry still has a `key.dpapi` that no longer unwraps, and the audit key is `key_unreadable`. Same id does NOT prove same bytes — `write_entry` replaces an earlier entry for an id (a retried Complete), and `unwrap_key_from_file` folds a transient read failure (`OSError`) and a DPAPI refusal into one `KeyCustodyError`. So the planner reads `key.dpapi` itself ONCE and classifies from that read through the new blob-based seam (round 2 PR-MED-015): an unreadable FILE (or any unreadable local member) is `skipped_uninspectable` (left alone; try again); a dead blob (`key_blob_is_dead`) is `skipped_dead_key`; a foreign description is `skipped_foreign_key`; only a genuine DPAPI refusal with the local CONTENT files matching the manifest's names and hashes byte for byte — the two audio sidecars admitted in any state, since the backup never holds them (round 2 PR-MED-014) — is `repaired_unreadable`: `key.dpapi` alone is replaced from the backed-up key through a staging-folder transaction with no new file name (round 2 PR-HIGH-013; D5), the content files and sidecars stay, and `audio-key.enc`, wrapped under this same entry key, becomes readable again; a DPAPI refusal with differing content or an unexplained extra member is `conflict_unreadable` — untouched, counted, named in the summary. Restore is REFUSED while `audit.key_unreadable()` with the line "Start a new audit record first" (the existing Reset). The downtime procedure says: after a password reset do NOT Delete now the unreadable entries (that writes tombstones); reset the audit record, then Restore.
- The location check: `check_export_location` positively REFUSES removable drives (a plaintext WAV must not leave the machine); a backup is ciphertext under a passphrase and removable media is its purpose. `check_archive_backup_location` is built on a private `_destination(layer, folder) -> (real_path, drive_type, findings)` extracted from `check_export_location` L493–523 (so both public functions share one detection pass), admits `DRIVE_FIXED` and the new `DRIVE_REMOVABLE`, refuses `DRIVE_REMOTE`, `DRIVE_CDROM`, `DRIVE_RAMDISK` and unknown, and WARNS when the destination's volume is the data folder's own — compared by `st_dev`, not drive letter (D4). The save dialog proposes the LAST admitted folder, never Documents (a Known-Folder-Move machine's Documents is in OneDrive and would be refused — safe but confusing).
- Nothing here opens a connection. `assert_offline_env` unchanged; the test suite's `TestConfinement` pin unaffected.

### External / API Findings
- `cryptography.hazmat.primitives.kdf.argon2.Argon2id(salt, length, iterations, lanes, memory_cost, ad=None, secret=None)` — available since `cryptography` 44 on OpenSSL ≥ 3.2; present in the venv's 49.0.0 and in the frozen build's hash-pinned 49.0.0 (checked 2026-10-09). `memory_cost` is in KiB. OWASP's minimum is m = 19 MiB, t = 2, p = 1; the plan uses m = 256 MiB (262 144), t = 3, p = 1 (≈ 1 s on a recent laptop), stored in the header.
- `zipfile` (stdlib): `ZipFile(path, "w", compression=ZIP_STORED)`; `ZipInfo.compress_type`, `.file_size`, `.compress_size`; `open(info)` streams a member; the reader must never trust `namelist()` order or member sizes beyond the manifest's — the `sample_notes.py` pattern.
- Windows `GetDriveTypeW`: `DRIVE_REMOVABLE = 2`, `DRIVE_FIXED = 3`, `DRIVE_REMOTE = 4`, `DRIVE_CDROM = 5`, `DRIVE_RAMDISK = 6` — the layer already exposes `drive_type`; only 3 and 4 are named in the code today.

## Planned Workflow Summary

### Flow 1 — Back up
Past sessions tab → **Back up…** → the passphrase dialog (enter twice; the minimum of D3; the sentence "The passphrase is never stored. Without it the backup cannot be opened by anyone, including you.") → a save dialog proposing `ClinikoScribe-backup-YYYY-MM-DD.csbk` in the last admitted folder (a same-day second backup gets `-2`, `-3`…) → `check_archive_backup_location` (refuse, or the same-volume warning in the confirm) → hop A derives the key off the GUI thread; hop B snapshots the committed readable entries (each key unwrapped, wrapped, zeroed) and the audit rows; hop C re-checks the RESOLVED destination folder through the same location seam immediately before the exclusive create (round 2 PR-MED-022 — the Export flow's own rule; a folder that now resolves elsewhere, is refused or cannot be inspected refuses the run and writes nothing), writes `<name>.csbk.part`, re-reads and verifies it in full (every member's hash, the manifest decrypts, the audit key or one entry key unwraps), `fsync`s and renames it; hop D sets `last_backed_up_at` on the rows of the ENTRIES written → "Backup written: <file name> — N entries, M audit rows. Keep the passphrase somewhere other than the drive." (with "audit record not included" when its key was unreadable). Back up is offered whenever the archive OR the audit record holds anything — an archive emptied by Delete now still has rows and tombstones to keep (round 2 PR-MED-021: a zero-entry, audit-only backup is a normal backup); with both stores empty the line says "Nothing to back up yet." An existing `.part` of the same name refuses the run: "A partial backup file is already there — delete it by hand first."

### Flow 2 — Open a backup (check, or restore)
**Open a backup…** (enabled only with no live or recoverable session and no run in progress) → open dialog → the header is pre-checked (bounds, format version, channel pre-filter) → passphrase → hop A derives the key, the manifest decrypts (its AAD binds the header bytes, so a tampered header fails here), every member's hash is verified, and the restore plan is computed → the summary dialog: "This backup opens: N entries from <date range>, made on <date> by Clinic Scribe <version> (<channel>). To add: A entries, R audit rows; already here: K; unreadable here and repaired from the backup: U; differing from the backup (left as they are): F; could not be inspected: Y; deleted since: D (not restored); unknown: X; audit provenance to recover: Z." with **Close** (nothing written — the check) and **Restore**. The classifications are computed on the GUI thread from the verified file (the worker only authenticates and verifies the file) and recomputed per entry immediately before anything is written. Refusals by name: wrong passphrase or damaged file (one line — the format cannot tell them apart before the manifest), another channel, a newer format, "Start a new audit record first" when the local audit key is unreadable.

### Flow 3 — Restore (from Flow 2's Restore button)
Live and recovery state re-checked after the dialog (its nested event loop may have processed a Chrome Start); the run flag held from before the first worker hop to the final accounting; sweep ticks skipped, Start refused and the audit Reset disabled for the run → audit rows first (each decrypted under the backed-up key, re-encrypted under the local key with the manifest's month, `restored_at` and `last_backed_up_at` set; `last_backed_up_at` only when the row's entry is in the file; local rows kept, except a BARE local `pre_audit` row — one holding no recording, deletion, past-session or write facts — replaced by the backed-up `recorded` row; a `pre_audit` row that does hold such facts is kept and reported as `conflict_row`) → per entry on the GUI thread, reclassified first: an `add` is staged under `.staging\<id>` through the archive's own path, `key.dpapi` written for this login, hash and reader verification, publish WITHOUT `pending`; a `repaired_unreadable` entry has ONLY its `key.dpapi` replaced — the new blob is written by the store's wrap seam into `.staging\<id>\` (the folder `clean_staging` already removes key-first at every start and tick, so a crash leaves nothing a destroyer does not know about), read back through the unwrap seam, then `os.replace`d over the entry's `key.dpapi` (the content files and any audio sidecar untouched) → "Restored N entries (U repaired, F left as they are). Add the clinic keys on the Clinics tab if this is a new computer."

### Flow 4 — Disaster
A new computer or login: install 0.4.0 (`docs/release/pilot-builds.md`), open Clinic Scribe, Past sessions → Open a backup… → Restore (Flows 2–3), then the Clinics tab for the API keys, the Practitioner tab for re-enrolment. The same login after a Windows password reset: do NOT Delete now the unreadable entries; Past sessions → Start a new audit record (the existing control, shown when the audit key is unreadable); then Open a backup… → Restore (an unreadable entry whose files match the backup gets its key repaired; one that differs is reported and left alone). The downtime procedure's "Losing the computer" names both sequences (Task 4.2).

## Design Decisions

- **D1 — What is backed up: every committed, readable Past-sessions entry and the whole audit record; nothing else.** Entries: `key.dpapi` is NOT copied (it is this login's); the entry key is unwrapped in memory and WRAPPED under the backup key (D2); `label.enc`, `transcript.enc`, `note.enc`, `generated.enc` byte for byte with their SHA-256. An entry whose key this login cannot unwrap, or whose label does not parse, is `skipped_unreadable` (counted, never fatal — a broken DPAPI entry is exactly what a restore is for, but it cannot be re-keyed). `pending` entries and `.staging` are excluded. Audit: every row file (readable and `_NEWER` alike — as ciphertext, with the store key) by month folder; when the audit key itself is unreadable (`AuditUnavailable`) the backup proceeds entries-only and the success line says "audit record not included"; an archive with NO committed entries still backs up its audit rows (a zero-entry, audit-only file — round 2 PR-MED-021 — whose verification unwraps the audit key as the passphrase check; a file with neither is never written: "Nothing to back up yet."). `exports.enc` (in-flight plaintext bookkeeping for this machine) excluded; kept recordings excluded (decision 0.2). Alternatives rejected: entries only (losing the audit record with the disk defeats the 7-year obligation and the restore tombstones); the whole data folder (the biometric profile, the clinic ids, the plaintext configs — and DPAPI blobs are useless elsewhere).
- **D2 — Key-wrap, not re-encryption; the manifest authenticates the header.** The backup key `K_b` is derived from the passphrase (D3). Each entry's 32-byte key is `AESGCM(K_b).encrypt(nonce, key, aad=b"csbk-entry-key:<id>")`; the audit store key likewise with `aad=b"csbk-audit-key"`; the manifest is encrypted under `K_b` with `aad=b"csbk-manifest:" + sha256(header_bytes)` — so ANY change to the plaintext header (channel, version, counts, KDF parameters) fails the manifest's decrypt, and the manifest carries its own copies of `channel`, `app_version`, `made_at` and the counts, which are the ONLY ones compared or shown (the header's are a pre-filter). The manifest lists every PAYLOAD member — the wrapped keys included — with size and SHA-256, so a member swapped between ids, truncated or appended is refused; the two ENVELOPE members, `header.json` and `manifest.enc`, are outside that list by definition (round 3 PR-MED-028 — a manifest cannot carry its own ciphertext's hash) and are authenticated instead by the AAD binding (the header's exact bytes) and the AEAD tag (the manifest itself); the ZIP's member set must EQUAL the two envelope members plus exactly the listed payload members. Content files keep their own per-entry encryption; `K_b` encrypts at most a few thousand small blobs with random 96-bit nonces, well inside GCM's bound, and is fresh per backup (fresh salt), so a wrapped key cannot be replayed into another backup. Residue (as `SessionCrypto._cipher`): `AESGCM(bytes(K_b))` makes an unzeroable copy; "zeroed in `finally`" covers the `bytearray` only. Alternatives rejected: re-encrypting every file under `K_b` (decrypts every transcript at backup time for no compartment gain); a random content key wrapped by the passphrase key (one more layer with no threat it answers); an HMAC over the header (a second key for what the AAD binding gives free).
- **D3 — The passphrase, the KDF and the four hops.** Argon2id (`cryptography` 49.0.0 — in the venv and hash-pinned in the frozen build; Task 0.7 confirms it in a release build before H5), parameters in the header: salt 16 bytes random, length 32, `iterations=3`, `lanes=1`, `memory_cost=262144` (256 MiB); a reader accepts only a FINITE envelope, checked before any derivation runs (round 1 PR-MED-009 — the header is unauthenticated until the manifest decrypts, so every work parameter needs an upper bound, not only memory): `memory_cost` 65 536 … 524 288 KiB, `iterations` 2 … 10, `lanes` 1 … 4 (`kdf_out_of_range` refuses anything else by name; the scrypt fallback's envelope is `n` 2**14 … 2**18, `r` = 8, `p` = 1), so a later build can raise the defaults inside the envelope and still open older files; a `MemoryError` during derivation is still caught by type and refused by name (the process may already hold the 2.3 GB language model). The passphrase: chosen by the practitioner, entered twice, minimum 20 characters (decision 0.3), no composition rules, never logged, never stored, never in a settings file; the `QLineEdit` is `Password` echo, cleared on every exit of the dialog; `K_b` lives in a `bytearray` zeroed in `finally`. The work is four hops — A (worker) derive; B (GUI) snapshot and key-wrap; C (worker) write and verify by path; D (GUI) record — see Integration Notes; `TaskThread.failed` carries a type-only message. Residues named: Qt's widget text and the pagefile may hold the passphrase (BitLocker, as for every secret in memory); a weak passphrase on a drive kept for years is the practitioner's risk — the 256 MiB cost is the control the app can give. Fallback only if Task 0.7 finds Argon2id missing from the release build: scrypt (`n=2**17, r=8, p=1`), the header's `kdf` field names which.
- **D4 — The backup location rule is its own check, on a shared helper.** `exclusions.check_archive_backup_location(layer, folder) -> ArchiveBackupLocation` (the name avoids the existing File-History `check_backup_exclusions` / `backup_exclusions`) with three outcomes: `refused(line)` for a OneDrive root the environment names, a network path or `DRIVE_REMOTE`, the roaming profile, either app data folder, `DRIVE_CDROM` / `DRIVE_RAMDISK` / unknown, and a path the layer cannot resolve; `warned(line)` when the destination's volume is the data folder's own by `st_dev` ("A backup on this computer's own disk does not survive that disk — use it only until you can copy to another drive"); `ok`. Both it and `check_export_location` call one private `_destination(layer, folder)` for the detections (the export rule's refusals are unchanged). Removable drives ADMITTED (the point of a backup); the file is ciphertext under D3; `DRIVE_REMOVABLE = 2`, `DRIVE_CDROM = 5`, `DRIVE_RAMDISK = 6` are added beside the two existing constants. Network drives refused by decision 0.4. Same read-only `WindowsLayer` seam; no layer injected → refused, as Export. The save dialog proposes the last admitted folder (remembered in `config\backup.json` — a folder path, the one setting this plan adds; absent → the dialog's default). Alternatives rejected: reusing `check_export_location` or a boolean parameter on it (it refuses the removable drive the practitioner will use and never warns); no check (an encrypted file in OneDrive is still "the cloud" to the patient documents).
- **D5 — Restore adds, repairs only a key this login can no longer unwrap when the files provably match, never resurrects; same channel only.** Refused while a session is live or the recovery list is non-empty (re-checked after the summary dialog), while another run is active, and while the local audit key is unreadable ("Start a new audit record first"). Order: header pre-check; passphrase; the worker authenticates and verifies the FILE (manifest and every hash); the GUI thread snapshots local archive, audit and session state and computes the classifications (round 1 PR-MED-008 — never on the worker); the summary shown; on Restore: audit rows first (so tombstones are present), then entries, each RECLASSIFIED immediately before mutation. Per entry id (pattern-bound by `validate_session_id` before any path is built): `skipped_live` if `sessions\<id>` exists; `skipped_unknown_row` if EITHER source's row for the id is `newer` or `unreadable` (round 1 PR-MED-002 — the deletion state cannot be known; absence in both is admitted and distinct); `skipped_deleted` if either source's row reads `past_session.state` `deleted_early` / `expired`; `skipped_expired` ONLY when the retention setting is "7 years" and the entry is past it (the sweep would delete it at the next tick) — under "Until I delete them" an entry of ANY age restores (round 1 PR-MED-003: archive retention is indefinite while audit months prune at 7 years, so a pruned month never blocks an entry; its row is simply not recreated — `skipped_pruned_row` — and the absence of tombstone evidence for such old entries is a named residue); then the local entry folder's OWN link state, read by `session_store.link_state(entry)` BEFORE anything under it is read (round 3 PR-MED-025 — `_committed_dirs` merely omits a linked folder, which would otherwise read as absence, and the repair path would read, hash and replace THROUGH the link into another folder's key): `None` (cannot be read) → `skipped_uninspectable`; `True` (a symlink or junction) → `skipped_linked` (untouched, counted, named; the ordinary store never lists, commits or follows it); only a confirmed ordinary folder is classified further, and a confirmed-ABSENT folder (`_absent`) is the only way to `add`; then ONE bounded read of the local `key.dpapi` classifies its custody (round 2 PR-MED-015 — `unwrap_key_from_file` re-reads the file and folds a read failure, a dead blob, a foreign description and a DPAPI refusal into one `KeyCustodyError`, so the planner never calls it here): `skipped_uninspectable` if the key file or any local member cannot be READ (`OSError` — transient, never a custody verdict); `skipped_dead_key` if `key_blob_is_dead(len(blob))` (a zero-length or truncated blob — a destroyed entry, not a DPAPI break; never repaired); `skipped_foreign_key` if the blob unwraps but its description is not `PAST_SESSION_KEY_DESCRIPTION`; `skipped_present` if the blob unwraps as this store's key; and only a genuine DPAPI refusal from the new blob-based seam `unwrap_key_blob(blob, description)` is a candidate for repair — `repaired_unreadable` if, in addition, the local CONTENT members (`label.enc`, `transcript.enc`, `note.enc`, `generated.enc`) equal the manifest's set for the id with every SHA-256 matching, where the two audio sidecars `audio.enc` / `audio-key.enc` in ANY state (kept, zeroed, deleted-residue) are admitted and preserved (round 2 PR-MED-014 — the backup never holds them) and any OTHER extra member is a conflict (decision 0.9 as amended — only then is "the same entry" PROVEN; `key.dpapi` alone is replaced from the backed-up key, the content files and sidecars untouched); `conflict_unreadable` if DPAPI refuses the key and the content members differ in set or hash or an unexplained member exists (another generation of the id) — untouched, counted, named; else `add`. For `add`: stage under `.staging\<id>` through the archive's own path (`_staging_linked`, `_remove_key_first`, `_publish`), write `key.dpapi` by the store's wrap seam for this login, copy the files, verify hashes AND read every plaintext through the existing readers (`_verify_restored`, a sibling of `_verify_staged` taking expected names and hashes), publish WITHOUT `pending`. A verification failure removes the staging key-first and counts `failed_verify`. A key repair is a custody transaction with NO new file name (round 2 PR-HIGH-013): the staging folder is refused when linked (`_staging_linked`), the entry folder's link state re-read (`False` required), `.staging\<id>` is removed key-first, the local content members are re-hashed against the manifest, the new blob is written by the store's unchanged wrap seam into `.staging\<id>\key.dpapi`, read back through the unwrap seam, and the key read back is then used to OPEN the final entry's content in place — the label through `_label_aad(id)` and its parse, `read_transcript`, `read_note` (its session binding and transcript digest), `read_generated` — exactly as `_verify_staged` proves a new entry (round 3 PR-MED-026: a hash match proves the files are the backed-up files, not that THIS key is their key; an authenticated backup whose writer paired the wrong key with an id would otherwise report a repair that stays unreadable); only then is it `os.replace`d over the entry's `key.dpapi`. The repair's cleanup is SYNCHRONOUS and load-bearing (round 3 PR-HIGH-024): in its own `finally` the staging folder is removed key-first — `_remove_key_first`, which from this plan also unlinks the atomic writer's temporary name `key.dpapi.tmp` as a second load-bearing unlink (`session_store.atomic_write_bytes` leaves it only across a crash; the committed entry's `key.dpapi` is never that writer's target here, only the `os.replace`'s, so no temporary ever sits beside the committed key) — a failed cleanup counts `failed_repair` with a log line, and whatever remains is `clean_staging`'s at the next start or tick, exactly as a crashed Complete's; a failure or crash at any step BEFORE the `os.replace` leaves the entry's old key file in place, and once the replace has committed the verified new key stays — a cleanup failure after it is reported, never rolled back (round 5 PR-LOW-035). And the ordering that makes this safe regardless of timing: `delete_entry` (Delete now and expiry both go through it) removes `.staging\<id>` through `_remove_key_first_unless_link` BEFORE it touches the committed key — the `remove_pending_entry` rule, now applied to committed entries too — and a linked `.staging`, an unreadable link state or a failed staging removal is `delete_failed` with the committed key untouched; so a successful cryptographic deletion never leaves a usable repair copy of the key anywhere this plan writes one. `failed_repair` counted; restore continues with the next entry and the summary names the counts (ids in the log only). A backup whose MANIFEST `channel` differs from `install_layout.channel()` is refused ("This backup was made by the developer build / the installed app"; the header's copy refuses earlier, before the passphrase, as a courtesy). A newer `format_version` is refused by name. Alternatives rejected: overwrite-on-restore of readable entries (a local edit — Delete now — is the newer truth); a procedure-only answer to the DPAPI break (a manual folder move at the worst moment; declined 2026-10-09); merging audit rows field by field (two sources of truth for one id).
- **D6 — The audit record restores under the local key, local rows win; three new `AuditLog` methods.** `backup_snapshot() -> (key_bytes, [RowDescriptor(month, session_id, path, size)])` — the store key's bytes for immediate wrapping and zeroing on the GUI thread, and per row a validated DESCRIPTOR (month by `_MONTH_RE`, id by `validate_session_id`, `size ≤ MAX_ROW_FILE_BYTES`, the count within the member budget), never the ciphertext itself (round 4 PR-MED-031 — the earlier `ciphertext_bytes` list would have accumulated the whole audit record on the GUI thread, against Integration Notes' "read ciphertext BY PATH"); the worker reads each row through `read_capped(path, MAX_ROW_FILE_BYTES)`, writes and hashes it and drops the buffer, a row gone or over-size in between `skipped_gone` (raises `AuditUnavailable` when the key is unreadable — D1's entries-only path); `row_state(id) -> readable | newer | unreadable | none`; `restore_row(plaintext, session_id, month, *, included, made_at, now) -> RowOutcome` — `month` is the manifest's validated source month (round 1 PR-MED-004: a `_NEWER` plaintext has no parsable `session_date`, and the archive's `completed_at` is not the audit's local session-start date) and `included` says whether the row's ENTRY is in the file's manifest (round 2 PR-MED-016): when `_decode` gives a row, its `session_id` and its `session_date`'s month must EQUAL the supplied id and month (else refused), its `backup` record is set MONOTONICALLY, None reading as absent (round 4 PR-MED-030): `last_backed_up_at` = the latest of the incoming row's own value and, ONLY when `included`, `made_at` (a row-only import never acquires this file's `made_at` — a copied row is never entry coverage — but keeps whatever coverage the incoming row already recorded); `restored_at` = the latest of the incoming row's own value and `now`; and it is re-encrypted under the local key with `b"audit:" + id` into that month folder; when it gives `_NEWER`, the plaintext is re-encrypted UNCHANGED into the supplied month (it stays `_NEWER` locally); writes ONLY when `_find(id)` is empty and `month_prune_at(month) > now` (`skipped_pruned_row` — pruning is judged by the AUDIT month, never by the archive's completion time), refusing a linked month folder as `_update` does; `MAX_ROW_FILE_BYTES` applies. A local row that exists is kept (`skipped_present_row`) — with ONE defined exception (round 1 PR-MED-010): a BARE local row whose `origin` is `pre_audit` (the sparse row start-up repair makes after an audit reset) facing a backed-up `recorded` row for the same id is REPLACED by the backed-up row (with `restored_at` and, when `included`, `last_backed_up_at`), counted `provenance_recovered` and shown in the summary — BARE meaning the local row carries NO fact the backed-up row could erase or that the two histories would have to merge: `past_session.state == "none"` (or `archived` with no `at` later than the backed-up row's), `deletion.state == "pending"`, an empty `RecordingRecord` (no `kept_at`, `deleted_at`, `exports == 0`), `write` untouched and no events (round 2 PR-MED-023 — a later export count or deletion recorded on the sparse row is local operational truth that an older row must not overwrite, and two export counts cannot be added without inventing a total); a `pre_audit` row holding ANY such fact is KEPT and counted `conflict_row`, named in the summary for the practitioner. The row's own `backup` record is NOT part of BARE but is never regressed either (round 3 PR-MED-029 — a sparse row that a later backup already covered would otherwise lose that coverage to the older file's `made_at`, or to None on a row-only import): the replacement row's `last_backed_up_at` is the LATEST of the local value, the incoming row's own value and (when `included`) `made_at`, and its `restored_at` the latest of the local value, the incoming row's own value and `now` (round 4 PR-MED-030 — the incoming row's own coverage counts too) — the one merge this plan specifies, over two timestamps that describe the same entry and cannot contradict each other; a value later than `now` is kept as is (a clock the plan does not judge); the same monotonic rule governs the ordinary writers `record_backed_up` and `record_restored` (each sets the latest of the existing value and the event's time, so a backward clock correction never regresses a recorded fact); a `pre_audit` row facing a `pre_audit` or `_NEWER` backed-up row is kept. When a kept local row's ENTRY is restored — AFTER its `add` has published or its repair's `os.replace` has committed, never before, so a skipped entry or a failure before that commit leaves the row's `restored_at` and `past_session` untouched (round 5 PR-MED-034) — `record_restored(id)` sets `restored_at` through `update` and a `past_session.state` of `none` becomes `archived` (allowed by `_PAST_SESSION_FROM`). Two injected seams `wrap_key` / `unwrap_key` on `AuditLog.__init__` mirror the archive's (today the audit key custody is hard-wired to `wrap_key_to_file`). Residue: a restored row with `recording.kept_at` set and no `deleted_at` describes a recording that was never in the backup (decision 0.2) — the threat model's L3769 gap, now systematic for restored rows, and the retention schedule's row 134 says so. Alternatives rejected: restoring the backup's audit KEY (two keys for one store; refuses the "recorded once, then remembered to restore" sequence); dropping the audit record from the backup (D1).
- **D7 — The audit facts of backup are two timestamps per row; no run ledger.** `AuditRow` v4: `backup: BackupRecord(last_backed_up_at: AwareDatetime | None, restored_at: AwareDatetime | None)`, CSV columns `backup.last_backed_up_at` / `backup.restored_at` LAST (the four v3 columns move to `[-6:-2]`, mode / app_version to `[-8:-6]`); `last_backed_up_at` is a distinctive name registered in `_PAYLOAD_SIGNATURES`. `record_backed_up(ids, at)` sets it through `update(..., create=False)` to the LATER of the existing value and `at` (never raising; `rows_absent` counted; `record_restored` likewise for `restored_at` — round 4 PR-MED-030) ONLY for the ids whose ENTRY is in the verified file's manifest — a row copied for an entry the backup skipped as unreadable marks nothing, and a row-only inclusion is never "coverage" (round 1 PR-MED-005). The tab derives "N entries not yet in any backup" from the archive's committed ids (`_committed_dirs`, no decryption) minus those whose row reads `last_backed_up_at` — an entry whose row is absent, `newer` or unreadable COUNTS as not backed up (unknown coverage is not coverage) — and "last backup <date>" from `max(last_backed_up_at)`; both travel with a restore, which a ledger would not. The run ledger of the draft is dropped (the `/review-plan` pass, 2026-10-09): its one load-bearing job, locating a `.part`, needed a path (against C7); instead the writer unlinks its `.part` in `finally` and the next backup refuses while one exists (Flow 1). Alternatives rejected: `AuditEvent` codes (evictable, not in the CSV); a per-backup pseudo-session row (the row schema is per session id); the ledger (above).
- **D8 — Two actions on the Past sessions tab and one status line.** `Back up…` and `Open a backup…` beside Export CSV (Open shows the summary with Close — the check — and Restore; Flow 2); the passphrase dialog is one Qt-free decision module plus a thin widget in the NEW file `ui/backup_dialog.py` (a `QLineEdit` in `ui/past_sessions.py` would fail `test_shadow_exits.py`'s two-tab text-widget pin), matching `ui/past_sessions_view.py`'s pattern; a progress line (counts only); ONE status line, "N entries not yet in any backup (last backup <date> / no backup yet)", shown when N > 0 and the last backup is older than 7 days (decision 0.6), from a Qt-free function `backup_status_line(committed_ids, rows, now)` that receives the archive's committed ids explicitly (round 2 PR-MED-016 — a committed entry with no readable row cannot be counted from the rows alone); it never acts. The screen gains a `session_busy: Callable[[], bool]` seam (from `MainWindow._live_session_ids` and the recovery list) that gates BOTH actions — Back up as well as Open (round 1 PR-MED-007: a live session's Complete or Discard mutates archive custody during the worker hop, and blocking new Starts alone does not exclude it) — and a run flag taken before any asynchronous work and released in every exit path (success, failure, cancel) so no control stays disabled; `PastSessionsAudit` gains the new audit methods; while a run is active the retention selector is disabled too and `on_retention_chosen` is guarded (its shorter-window path runs a sweep directly — round 2 PR-MED-017). Open a backup is enabled with an empty archive (the new-computer case); Back up is enabled whenever the archive has a committed entry OR the audit record has a row (an emptied archive's tombstones still need backing up — round 2 PR-MED-021), and shows "Nothing to back up yet." when both are empty. Alternatives rejected: a third "Check a backup…" action (the fold saves a button, a seam and a flow; declined 2026-10-09); a Status-tab home (the archive's actions belong with the archive); a reminder line separate from the count (redundant); automatic backups (Deferred).
- **D9 — Version 0.4.0, a build of record, installed by the practitioner.** The audit schema bump and the new file make it a minor. The rollback rule "below 0.4.0": 0.3.0 reads a restored entry as any entry (no `pending`, standard files), ignores `config\backup.json`, and treats a v4 audit row as `_NEWER` (kept byte for byte, omitted from its CSV, counted as newer) — so after a rollback the CSV lacks every row 0.4.0 touched until 0.4.0 runs again, its start-up `repair_kept_facts` counts an `audit_update_failed` for each such kept entry, and a Delete now or expiry on 0.3.0 of such an entry writes NO tombstone (the entry would come back on a later restore: "delete it again"); a backup file is 0.4.0's alone (0.3.0 has no reader). The build reaches the installed app through `docs/release/pilot-builds.md`'s path: CI `Release` on the tagged commit, attestation + `SHA256SUMS.txt` verified in a normal terminal, both apps closed, `setup.exe` with the existing model pack (no model changes), the extension reloaded, Chrome restarted — Phase P.1.
- **D10 — Documents describe what the code does; the patient sheet is `patient-info-v4`.** Every sentence in the inventory (Key Findings) is amended to: the practitioner can make an encrypted, passphrase-protected backup onto a drive attached to this computer and restore it on a new computer or login; the backup is never sent anywhere; a kept development recording is NOT in it (decision 0.2 — those two sentences in `development-recording-consent.md` get a pointer and stay true). "Can only be opened from your practitioner's own Windows login on that computer" becomes "…or from a backup copy, which opens only with a passphrase your practitioner keeps". Per `docs/practice/README.md`'s rule a changed sheet is a new version: `patient-info-v4`, with two reviewer questions added to the README — whether a backup copy needs fresh consent or changes the state-law custody analysis, and whether a transcript deleted as recorded in error must also be destroyed in older backups (APP 11.2). The retention schedule gains rows for the backup file (outside custody once written; the practitioner's to keep and destroy; the operating rule "newest two backups, destroy older after a Delete now"), `config\backup.json` and the v4 columns, and amends rows 67, 134 and the Past sessions rule; the threat model a section "Past-sessions backup and restore" with residues; data-flow a flow 28; `intended-use.md` L63 and the tab's own retention warning (`ui/past_sessions_view.py` L216, quoted at `design-system.md` L533) are amended together. `docs/practice/` keeps plain English (C10) — "a backup drive you keep locked away".
- **D11 — Container `.csbk` v1: a stored-only ZIP read only through its encrypted manifest.** Members: `header.json` (plaintext, ≤ 4 KiB: `format_version: 1`, `app_version`, `channel`, `made_at`, `kdf: {name, salt, iterations, lanes, memory_cost}`, `manifest_bytes` ≤ 16 MiB, `entry_count`, `row_count`), `manifest.enc`, `keys/<id>.enc`, `audit-key.enc`, `entries/<id>/<label|transcript|note|generated>.enc`, `audit/<YYYY-MM>/<id>.enc`. The manifest (pydantic, `extra="forbid"`; every id `pattern=SESSION_ID_PATTERN`, every file name a `Literal`, every month `_MONTH_RE`) lists every payload member (everything but the two envelope members `header.json` / `manifest.enc` — D2, round 3 PR-MED-028) with size and SHA-256; BEFORE `zipfile.ZipFile` parses anything, a bounded preflight reads the file's size and its end-of-central-directory record only (round 2 PR-MED-020 — `zipfile` loads the whole central directory on open, so an unauthenticated file must not get to choose how much it allocates): the file ≤ 8 GiB, no ZIP64 (`PK\x06\x06` / `PK\x06\x07` refused by name), a comment ≤ 64 KiB, the entry count ≤ 5 × `entry_count` + `row_count` + 3 (the admitted grammar exactly: per entry its wrapped key and up to four content files, per row one member, plus the header, the manifest and the optional audit key — round 3 PR-MED-027 corrected a 4-per-entry formula that refused a valid three-entry file; `entry_count` and `row_count` from a header read first, itself ≤ 4 KiB at a fixed offset as the first stored member) AND ≤ the absolute `MAX_MEMBERS = 65_535` (the 16-bit EOCD count that refusing ZIP64 already implies, stated as its own check so the bound never depends on the header) and the central-directory size ≤ 64 MiB, each a closed refusal code; then the `ZipFile` is opened and `header.json` and `manifest.enc` are read only after their directory entries show `ZIP_STORED` and declared sizes within their bounds; then the reader iterates the MANIFEST, never `namelist()`, and refuses a member that is neither an envelope member nor listed, a duplicate (an envelope member twice included), a non-`ZIP_STORED` method, a member whose size differs from the manifest's, or a member count other than the listed payload count plus two — the `sample_notes.py` bounded-reader pattern for bounds and error handling, with the accepted input NARROWED to stored-only (that reader admits deflated `.docx` input; round 1 PR-LOW-012). A wrong passphrase and a damaged manifest refuse with one line (indistinguishable before the manifest); a damaged member refuses by name. Written as `<name>.csbk.part` through one exclusive create (`O_EXCL`), re-read and verified in full, `fsync`ed, then renamed; the `.part` is unlinked in the writer's `finally` on any failure; one left by a hard kill or a yanked drive is harmless ciphertext that the next backup of the same name refuses to overwrite (Flow 1) — the residue replaces the draft's start-up recovery. Alternatives rejected: the hand-rolled record stream of the draft (more framing code and tests for the same properties; declined 2026-10-09); one file per entry (hundreds of files to lose one of); SQLite (a new dependency); compression (nothing to gain on ciphertext; a bomb surface).
- **D12 — The developer channel builds and smokes it with synthetic content; the agent never opens a real backup.** Tests use pinned roots, the archive's fake key-wrap seams and the audit's new ones, a fake `WindowsLayer` and a fast KDF parameter set admitted ONLY under a test-marked floor override (`_kdf_floor_for_tests`), never by a header field; the audit store's existing real-DPAPI tests (`@windows_only`, `tmp_path`) remain the one exception C9 already carries. The practitioner's P.2 smoke runs on the developer build with its data folder SET ASIDE (a fresh `ClinikoScribe-dev` holding ONLY the `models` folder moved over from the set-aside root — the pinned public model downloads are non-clinical and the recordings cannot be transcribed without them, round 4 PR-MED-032; the real folder's sessions, archive, audit record, profile and settings stay set aside, since it holds the clinic 1 smoke's consented consultations and a mock session keeps nothing), recording two synthetic validation scripts aloud (non-mock, synthetic content); P.3 is the FIRST real backup on the installed 0.4.0 to a removable drive, opened with Close (the check) and never restored anywhere by the agent (C1).

## Schema / Data Changes

| Store | Today | After this plan | 0.3.0 reads the new shape as | This build reads the older shape as |
|---|---|---|---|---|
| audit row (`audit.AuditRow`) | v3 | v4: + `backup: {last_backed_up_at, restored_at}` (nested, default empty); a v4 row NAMES `backup`; CSV columns `backup.last_backed_up_at`, `backup.restored_at` LAST (the four v3 columns at `[-6:-2]`, mode / app_version at `[-8:-6]`) | `_NEWER`: kept byte for byte, omitted from 0.3.0's CSV; a Delete now / expiry on 0.3.0 writes no tombstone for it | v3 → `_upgrade_v3` (empty record; refuses v3 data naming `backup`); v2/v1 chain as today |
| `config\backup.json` (NEW; the last admitted backup folder) | — | `{"schema_version": 1, "folder": "<path>"}` ≤ 4 KiB, the config folder's atomic write; unreadable → the dialog's default | ignored | — |
| `past_sessions\<id>\` (a newly ADDED entry) | — | identical to an archived entry: `key.dpapi` (this login), `label.enc`, `transcript.enc`, [`note.enc`], [`generated.enc`]; no `pending`; never `audio.enc` / `audio-key.enc` (a backup holds no recording) | an ordinary entry | — |
| `past_sessions\<id>\` (a REPAIRED existing entry) | every file as it was | `key.dpapi` alone replaced for this login; `label.enc`, `transcript.enc`, [`note.enc`], [`generated.enc`] and any `audio.enc` / `audio-key.enc` untouched (the audio key, wrapped under the same entry key, becomes readable again) | an ordinary entry | — |
| `<folder>\ClinikoScribe-backup-YYYY-MM-DD[-n].csbk` (NEW, outside custody) | — | D11 container v1 | nothing (no reader) | — |
| `past_sessions\<id>\label.enc`, `encounter.enc`, every other `config\*.json` | — | UNCHANGED | — | — |

Backfill: none. `last_backed_up_at` is None on every existing row until the first backup; "not yet in any backup" is therefore every archived entry on day one — correct. A restored row whose ENTRY was in the file carries the backup's `made_at` as its `last_backed_up_at`, so a restored archive does not read as unbacked-up; a row restored without its entry keeps None (or its own earlier value), so an entry the backup skipped is never shown as covered.

## Config / Environment / Deployment Impact
- No new dependency (`cryptography` 49.0.0 — Argon2id, scrypt, AES-GCM — and the stdlib `zipfile`). No network, no environment variable, no registry value, no installer change; `desktop/requirements-build.txt` unchanged. One new user setting file, `config\backup.json` (a folder path only).
- Version 0.4.0 in the five version places (`__init__.py`, `pyproject.toml`, `package.json`, `package-lock.json` ×2, `manifest.ts`) and `CHANGELOG`.
- The installed app receives it through the release path (D9); the developer build through `pip install -e` as usual.

## Critical Constraints

- **C1 — The agent never reads a real kept transcript, note, name or recording, and never opens a real backup file.** Every test and smoke the agent runs uses synthetic content on the developer build with its data folder set aside; Phase P's real backup is made, opened and kept by the practitioner alone; no task asks the agent to list, decrypt or describe a real archive or backup. A backup's success and summary lines carry counts, dates and a file name (a date) — never an id list, a name or text.
- **C2 — Nothing leaves this computer or its attached drives.** `check_archive_backup_location` REFUSES (never asks) a destination the code positively identifies as cloud-synced, remote, roaming or either app data folder; sync the code cannot see is the named residue, as for Export; no network code is imported; `assert_offline_env` unchanged.
- **C3 — The passphrase is never stored, logged or echoed; the derived key never touches disk.** No settings file, audit field, log line, worker signal or exception message carries it or anything derived from it except the per-file random salt inside the backup; the widget is cleared on every exit; `K_b` and every unwrapped entry key are zeroed in `finally` (the `AESGCM` object's own copy is the named residue); a failure path reports the exception TYPE only (the project's hook rule; `TaskThread.failed` included).
- **C4 — Backup is read-only on the archive and the audit store, except the one `update` of `last_backed_up_at` AFTER the file is verified.** No entry file is rewritten, no key file touched; a backup that fails verification unlinks its `.part` and updates no row (a yanked drive may defeat the unlink — the line says a partial file may remain); an unreadable audit key makes the backup entries-only, never a failure.
- **C5 — Restore never overwrites a READABLE entry, never deletes a file, never resurrects a tombstoned one.** A readable committed entry, a live session id, a deletion tombstone in either source's row, a row in EITHER source whose state cannot be read, an entry past the "7 years" retention setting, and an entry whose local files cannot be inspected each skip the id; a linked or link-state-unknown entry folder is never read or written through (`skipped_linked` / `skipped_uninspectable`, round 3 PR-MED-025); the ONLY mutation of an existing entry is a key repair — `key.dpapi` replaced from the backed-up key when DPAPI refuses the local one, every local content member matches the manifest's hashes AND the recovered key opens that content through the existing readers (decision 0.9 as amended by round 1 PR-HIGH-001 and round 3 PR-MED-026; a differing entry is a conflict, untouched); the repair's staging copy of the key is removed key-first synchronously, and `delete_entry` removes `.staging\<id>` key-first BEFORE the committed key so no successful deletion leaves a repair copy behind (round 3 PR-HIGH-024); every added entry is written to staging through the archive's own path and FULLY verified through the existing readers before it is published; a failed entry is removed key-first and counted; a local audit row is never replaced except a BARE `pre_audit` row (no recording, deletion, past-session or write facts) by a `recorded` one; a `pre_audit` row holding such facts is kept and reported `conflict_row` (D6). Named residues: an entry whose Delete now left no tombstone (a failed audit write; a Delete now on 0.3.0 of a row 0.4.0 touched) comes back and is deleted again; an entry older than the audit's 7 years restores under "Until I delete them" with no tombstone evidence possible.
- **C6 — The per-entry compartment survives.** Each entry's key is wrapped individually; no archive-wide content key exists before, inside or after a backup; a restored entry has a fresh DPAPI wrap and opens nothing else.
- **C7 — Content-free records.** The v4 audit fields are two timestamps in a nested record whose distinctive name is registered with the log tripwire; `config\backup.json` holds a folder path and nothing else; the tab's lines are counts and dates; the log names session ids and codes only.
- **C8 — The container fails closed.** A file over the size cap, a ZIP64 record, an end-of-central-directory entry count over the grammar's bound or `MAX_MEMBERS` or a central-directory size over its cap (each checked BEFORE `zipfile` parses the directory), a member set that is not exactly the two envelope members plus the manifest's payload list, a header or manifest member that is not stored or exceeds its declared bound, a header over its bound, a `format_version` other than 1, an unknown `kdf`, any KDF work parameter outside its finite envelope (memory, iterations AND lanes — checked before the derivation seam is called), a `manifest_bytes` over 16 MiB, a channel mismatch, an unlisted, duplicate, compressed or mis-sized member, a manifest id, file name or month outside its pattern, a hash mismatch or a manifest that does not decrypt (which any header change causes) each refuses by name before anything is written; `MemoryError` is caught by type; the floor is loosened only by the test seam of D12, never by the file.
- **C9 — Tests never read the host's own data, drives or DPAPI** — pinned roots for the archive, the audit store and `backup.json`; the archive's fake key-wrap seams and the audit's new ones; a fake `WindowsLayer` (the conftest sentinel makes the real one raise); the fast-KDF test floor; no test writes outside its temporary folder — with the one pre-existing exception that `test_audit.py` and `test_schema_versions.py` already exercise real DPAPI under `tmp_path` (`@windows_only`), which the new audit tests may share.
- **C10 — Plain English in `docs/practice/`** (its README): no file names or code identifiers; the draft banner stays; a changed patient sheet is a new version (`patient-info-v4`); nothing claimed the app cannot back — it cannot know where the drive is kept or whether a backup was later destroyed.
- **C11 — The clinic 1 smoke's files are not edited before Phase 4**, and Phase 4's edits to shared documents (`docs/practice/`, the threat model, the retention schedule, `AGENTS.md`) are made against the then-current `main` with that plan's state re-read, never from this plan's snapshot.
- **C12 — No run of this feature overlaps the archive's other writers.** Neither action starts while a session is live or recoverable (`session_busy` — a Complete or Discard in flight is an archive writer); the run flag is taken before the first worker hop and held to the final accounting, released on every exit; while it is held `PeriodicSweep.__call__` returns before ANY of its three steps without advancing their clocks (the one real entry point of the 24 h session sweep, the audit prune and the retention sweep — round 2 PR-MED-017; guarding `run_sweep` alone would not reach the prune), Start is refused at both funnels, the audit Reset is disabled, and the Past sessions tab's Delete now, Delete recording, Export and the retention selector are disabled, with `on_retention_chosen`'s direct sweep guarded and re-checked after its own confirm; every archive or audit READ that classifies and every WRITE runs on the GUI thread (the privacy plan's C5) — the worker hops derive the key, write the file and verify the file, holding ciphertext, wrapped keys and `K_b` only.

## Validation / Verification

- Suites (executor shapes; pytest composer-run): `cd desktop && ruff check . && mypy && pytest`; `cd extension && npm run qa` (unchanged by this plan; the version pin only). Baseline to record at Phase 1's start from `main` (Task 0.8).
- Dry-run baselines to record in Task 0.8 (read-only): `grep -rn "no backup\|makes no backup\|NO backup\|there is no backup\|with no backup\|Windows login" docs PLAN.md desktop/src` → the D10 inventory (16 sites at `aeec75e`, listed in Key Findings); `grep -n "_PAYLOAD_SIGNATURES" desktop/src/scribe_desktop/logging_setup.py`; `grep -n "DRIVE_" desktop/src/scribe_desktop/exclusions.py` (two constants today); `grep -n "schema_version == 3\|CSV_COLUMNS\[" desktop/tests/test_audit.py` and `grep -n "as v3" desktop/tests/test_schema_versions.py` (the pins Task 1.2 updates); `grep -rn "check_backup_exclusions\|backup_exclusions" desktop/src` (the name collision D4 avoids); the count of `AuditRow(` constructions in tests (two files; the v4 default keeps them valid).
- New or extended tests (each failing on the pre-change code where a guard is claimed): `test_backup_container.py` (round-trip; every C8 refusal by code — header bound, version, kdf, floor, 512 MiB cap, `manifest_bytes`, channel, unlisted / duplicate / compressed / mis-sized member, pattern-bound ids, a byte flipped in the header, the manifest, a wrapped key and an entry member; `MemoryError` by type; a same-name `.part` refuses; `-2` suffix on a same-day name); `test_backup_write.py` (D1's inclusion and exclusion set — pending, staging, unreadable, kept-recording files NOT copied, `_NEWER` rows copied; entries-only when the audit key is unreadable; `last_backed_up_at` only after verification and through `create=False`; nothing rewritten — a directory hash of the archive before and after; the hop split: no store method called off the GUI thread, asserted by a thread-recording fake); `test_restore.py` (every classification of D5 from both tombstone sources — `skipped_unknown_row` for a `newer` / `unreadable` row in EITHER source with the other absent; `skipped_uninspectable` for an unreadable key FILE (an `OSError` fake) that is never treated as a custody refusal; `repaired_unreadable` only when every local content member matches AND the recovered key opens the content (round 3 PR-MED-026), with the audio sidecar retained and `key.dpapi` the only changed file (directory hash of the rest), and a failed read-back leaving the old key file; `conflict_unreadable` for a differing member set or hash, nothing touched; an entry older than 7 years restoring under "Until I delete them" with its row NOT recreated, and `skipped_expired` under "7 years"; refused while the audit key is unreadable; verification failure removes key-first and continues; audit rows re-encrypted under the local key into the MANIFEST's month, `_NEWER` plaintext unchanged, an id or month mismatch refused, a month-boundary session, pruned months skipped, `restored_at` / `last_backed_up_at` set; a BARE `pre_audit` local + `recorded` backup → `provenance_recovered`, a `pre_audit` local row holding an export count or a deletion fact → `conflict_row` with the local row byte-identical afterwards, `pre_audit` + `pre_audit` kept; a row-only import leaves `last_backed_up_at` None and the entry counted as not backed up; a BARE `pre_audit` row already covered by a LATER backup keeps that later `last_backed_up_at` through `provenance_recovered`, with and without its entry in the file (PR-MED-029); a row-only import whose incoming row carries coverage t2 later than the local t1 keeps t2 without acquiring this file's `made_at`, the reverse ordering keeps t1, None reads as absent on either side, and `record_backed_up` / `record_restored` after a backward clock change leave the later existing value (round 4 PR-MED-030); `test_backup_write.py`: a fake `AuditLog` whose row reads raise on the GUI thread passes hop B (descriptors only), and a many-row plan is written with one row buffer live at a time, an over-size or vanished row `skipped_gone` (PR-MED-031); `test_restore.py`: with a kept local row, an injected add-verification failure, a publish failure and a pre-replace repair failure each leave `restored_at` and `past_session` byte-identical, while a successful add and a successful repair set them after the commit (round 5 PR-MED-034); `test_backup_container.py`: an entries-only file of three full entries (17 members) round-trips, the grammar bound and `MAX_MEMBERS` refuse by code, the manifest holds no envelope name and a file whose member set differs from envelope-plus-payload by one is refused (PR-MED-027, PR-MED-028); a committed entry with no readable row counts as not backed up in `backup_status_line`; the one-read custody classification — an `OSError` on the unwrap path after a successful preliminary read never reaches repair, a dead blob and a foreign description are their own outcomes, only `dpapi_refused` repairs; a local `none` row becomes `archived`; restored entries listed and readable through the tab's reader; no `pending`; a restored entry without audio reads `recording_state == none` and is left alone by `tidy_dead_recordings`; the classifications are recomputed before mutation — a tombstone written between the summary and Restore skips the entry; no store, audit or controller method runs on a worker during Open or Restore, asserted by thread-recording fakes); `test_archive_backup_location.py` (each refusal, the `st_dev` same-volume warning, removable admitted, CD-ROM / RAM disk / unknown refused, no layer → refused; `check_export_location`'s refusals unchanged through the shared helper); `test_schema_versions.py` (`AUDIT_V3` literal captured FIRST; v4 read; v5 refused; v3 data naming `backup` refused; "written back as v4"); `test_audit.py` pins updated (`schema_version == 4`; the four v3 columns' header AND value assertions at `[-6:-2]`, mode / app_version at `[-8:-6]`, NEW separate header and value assertions for `[-2:]`; `_upgrade_v2` pinned to 3 then `_upgrade_v3` — clean v1 / v2 / v3 rows become v4, every older version already naming `backup` refuses, a v3 row missing its consent or recording fields still refuses); `test_backup_write.py` also: a skipped-unreadable entry's copied row is NOT marked backed up, a row-only inclusion marks nothing, an entry with a missing or unreadable row counts as not backed up, Back up refuses while `session_busy`, a destination whose fake resolution changes to a refused or uninspectable folder between admission and the create writes nothing there, a zero-entry audit-only backup round-trips, both stores empty → `nothing_to_back_up`; `test_app.py`-style: `PeriodicSweep.__call__` runs none of its steps and advances no clock while the run flag is held, and resumes after; the retention selector's direct sweep refused while a run is active; `test_past_sessions_ui.py`-style tests for the two actions, the summary dialog's Close and Restore, the status line's states, BOTH actions disabled with `session_busy` and the run flag released on failure and cancel, the audit Reset disabled during a run, the re-check after the dialog, the passphrase widget cleared, every other tab action disabled during a run, the folder setting round trip; `test_logging_setup.py` (the new signature); `test_shadow_exits.py` unchanged in count (asserted; the dialog lives outside `_tab_sources()`); `test_pilot_docs.py` if any pilot document changes; `test_install_layout.py`'s version pin.
- Manual checks (practitioner, Phase P): P.1 install 0.4.0; P.2 the developer-build round trip on a set-aside dev data folder holding only the moved-over `models` folder, with two synthetic scripts read aloud (back up → move the archive aside → open → restore → an entry opens; the password-reset path is covered by `test_restore.py` only — the practitioner never fakes a DPAPI break by hand); P.3 the first real backup on the installed app to a removable drive, opened with Close; P.4 the documents read; P.5 the rollback rule read before any older install.
- Success: suites green; `/review-loop`, `/simplify`, `/security-review` and the codex peer pass converged at each phase boundary; 0.4.0 a build of record; P.1–P.3 PASS; `patient-info-v4` and its siblings in the independent review's queue with their amended sentences.

## Deferred / Out of Scope
See `Planning Extraction Summary` (state-once). In one line each: kept recordings in the backup, scheduled backups and a settings export are deferred with triggers; network/cloud destinations, incremental backups, cross-channel restore, single-entry restore, passphrase recovery and the run ledger are excluded; backup size, the 256 MiB cost, passphrase custody and "no live session at restore" are assumptions with named checks; Argon2id in the frozen build is resolved (hash-pinned), with Task 0.7 as the pre-release confirmation.

## Current State / Handoff Note
- 2026-10-09: drafted by a side session (Opus 5.5) from the code at `aeec75e`; the practitioner took every recommended option for decisions 0.1–0.6; hardened the same day by `/review-plan` on Fable 5.1 (four lenses; decision 0.9 and the three simplifications taken; the deferral gate confirmed). The plan file is UNCOMMITTED pending the practitioner's word (a sibling session reconciled the other plans in `c987101`; this plan's cross-references into `plan-privacy-professional-controls.md`, `plan-installation.md`, `plan-pilot.md`, `AGENTS.md` and `PLAN.md` L152 are to be added by Task 4.3, not before). The same day a five-round `/peer-loop` plan review (codex `gpt-6-astra` medium, read-only sandbox, composer-recorded rounds; 12 → 11 → 6 → 4 → 2 findings, every one verified against the code and applied as a plan amendment, 0 rejected) was accept-closed at its cap on the practitioner's word — the Findings Log carries every finding and where it landed. NEXT: `/execute-loop` from Phase 1 (Tasks 0.7 and 0.8 are the executor's first two steps; 0.7 may also run at H5). The clinic 1 smoke continues in parallel (C11).

## Tasks

Grouped into phases for `/execute-loop` (a review loop and a codex peer pass at each boundary). Paths under `desktop/src/scribe_desktop/` unless they start otherwise. A `[decision]` task is the practitioner's; the recommended option is listed first and is what the later tasks assume.

### Phase 0 — Decisions and the spike (nothing built)

- [x] 🟩 **0.1 [decision] What is backed up.** (a) RECOMMENDED: every committed readable Past-sessions entry (transcript, saved note, generated note, label) AND the whole audit record (D1). (b) Entries only. (c) The whole data folder. **DECIDED 2026-10-09 (practitioner): (a) entries + the whole audit record.**
- [x] 🟩 **0.2 [decision] Kept development recordings.** (a) RECOMMENDED: EXCLUDED from every backup; the consent document's "makes no backup of it" stays true and gets a pointer. (b) Included behind a per-backup tick under a new `development-consent-v2` (re-consent needed; a backup grows by ~55 MB per 30-minute recording; `test_shadow_exits.py`'s reader pin changes). **DECIDED 2026-10-09 (practitioner): (a) EXCLUDED; the consent document's sentence stays true with a pointer.**
- [x] 🟩 **0.3 [decision] The passphrase scheme.** (a) RECOMMENDED: a practitioner-chosen passphrase, entered twice, minimum 20 characters, Argon2id 256 MiB / t = 3 (D3). (b) A generated 8-word recovery phrase shown once and written down (stronger; nothing to choose; easier to lose). **DECIDED 2026-10-09 (practitioner): (a) chosen passphrase, twice, minimum 20 characters, Argon2id 256 MiB / t = 3.**
- [x] 🟩 **0.4 [decision] Where a backup may be written.** (a) RECOMMENDED: fixed and removable drives attached to this computer; cloud-synced folders the app can see, network drives, the roaming profile and the app's own folders REFUSED; the data folder's own volume written with a warning (D4). (b) Also admit network drives (a NAS) — needs the patient documents to say the record may be on a second computer at the practice. **DECIDED 2026-10-09 (practitioner): (a) fixed and removable drives only; cloud-synced, network, roaming and app folders refused; same-volume warned.**
- [x] 🟩 **0.5 [decision] Backups already taken when an entry is deleted.** (a) RECOMMENDED: the app cannot reach them; Delete now's confirmation and the documents state the operating rule — after a Delete now make a fresh backup and destroy older ones; keep the newest two backups otherwise (D5, D10). (b) Also record a "deleted after backup" count on the tab. **DECIDED 2026-10-09 (practitioner): (a) operating rule — fresh backup after a Delete now, destroy older, keep the newest two.**
- [x] 🟩 **0.6 [decision] The reminder.** (a) RECOMMENDED: "No backup for N days" on the tab after 7 days with at least one entry not yet backed up; never acts (D8). (b) 30 days. (c) No reminder. **DECIDED 2026-10-09 (practitioner): (a) 7 days, never acts.**
- [x] 🟩 **0.9 [decision] Restore on the same login after a Windows password reset broke DPAPI.** (a) RECOMMENDED: an entry whose local key no longer unwraps and whose row is not a tombstone is REPLACED key-first by the backup's byte-identical copy; the audit record is reset first (the existing Start a new audit record) when its key is unreadable; C5 reads "never overwrites a READABLE entry". (b) Procedure only — move the old archive aside by hand before restoring. **DECIDED 2026-10-09 (practitioner, `/review-plan`): (a) replace key-first.** *Amended 2026-10-09 by plan peer-review round 1 PR-HIGH-001 (narrower than (a), within it): the replacement is a KEY REPAIR — `key.dpapi` alone replaced (through a `.staging\<id>` transaction, round 2 PR-HIGH-013; the recovered key proven to open the content first, round 3 PR-MED-026), and only when every local ciphertext content file matches the backup's hashes byte for byte (same id does not prove same bytes; an unwrap failure can be a transient read error); a differing local entry is a reported conflict, untouched; an uninspectable one is skipped.*
- [ ] 🟥 **0.7 Confirm Argon2id in a release build (pre-H5; practitioner-run or CI).** `desktop/requirements-build.txt` already hash-pins `cryptography==49.0.0`, so this is a confirmation: add `packaging/spike/kdf_probe.py` (imports `Argon2id` and `Scrypt`, derives 32 bytes from a fixed test string, prints `argon2id ok` / `scrypt ok` and the OpenSSL version — no secrets) and run it inside a PyInstaller build made by `scripts/build-release.py` from a normal terminal, or as a step of the H5 release build. Done when: the output names both KDFs; if Argon2id is missing, D3's scrypt fallback is chosen and recorded here before H5. Verification: the printed lines pasted into this task.
- [ ] 🟥 **0.8 Record the dry-run baselines** (Validation / Verification: the six greps and the two suites' counts from `main`). Done when: the numbers are in this plan.

### Phase 1 — The container, the writer and the records (no UI)

- [ ] 🟥 **1.1 Capture 0.3.0's audit-row bytes before the model changes.** `tests/test_schema_versions.py`: an `AUDIT_V3` `Final` bytes literal beside `AUDIT_V1` / `AUDIT_V2` and a test that this build reads it as a row — written and passing BEFORE 1.2 touches the model (then extended: "…with an empty `backup` record"). Done when: the literal exists and the test passes on the unchanged model.
- [ ] 🟥 **1.2 Audit row v4 and the backup surface of `AuditLog`.** `audit.py`: `AUDIT_SCHEMA_VERSION = 4`, `AuditRow.schema_version: Literal[4]`, `BackupRecord(last_backed_up_at, restored_at)` as `backup: BackupRecord = BackupRecord()`, `_upgrade_v2`'s target PINNED to the literal 3 (today it writes `AUDIT_SCHEMA_VERSION`, so a bare bump would skip the new step — round 1 PR-MED-006), then `_upgrade_v3` (refuses v3 data naming `backup`, the `_upgrade_v2` shape) applied by the post-upgrade version, `_decode` L447's name check rewritten as ORIGINAL-version rules kept distinct from the sequential upgrades: an original v3 row must name `development_consent_version` and `recording`; an original v4 row must name those two AND `backup` (round 2 PR-MED-018 — a direct v4 document missing an inherited field must refuse, not take the model defaults), CSV columns `backup.last_backed_up_at` / `backup.restored_at` LAST; `test_audit.py`'s `_v1_document` / `_v2_document` builders also delete `backup` (round 2 PR-MED-019), with deliberately contaminated fixtures kept separate; a new `session_store.unwrap_key_blob(blob, *, description) -> SessionCrypto` sibling with structured refusals (`dead`, `dpapi_refused`, `foreign_description`, `bad_length`) that `unwrap_key_from_file` is rewritten over, plus its conftest fake beside the file-based seams (round 2 PR-MED-015); `AuditLog.__init__(…, wrap_key=, unwrap_key=)` seams (defaults `session_store.wrap_key_to_file` / `unwrap_key_from_file`); `backup_snapshot() -> (key_bytes, [RowDescriptor])` (descriptors, never ciphertext — round 4 PR-MED-031), `row_state(id)`, `restore_row(plaintext, session_id, month, *, included, made_at, now)` (the id / month binding, coverage only when `included`, the BARE-`pre_audit` → `recorded` replacement of D6 with `conflict_row` otherwise, and on that replacement the `max` merge of the two `backup` timestamps — round 3 PR-MED-029), `record_backed_up(ids, at)` (`update(create=False)`, `rows_absent` counted; called with the manifest's ENTRY ids only; monotonic — the later of the existing value and `at`), `record_restored(id)` (monotonic likewise; round 4 PR-MED-030) — all per D6/D7, none raising except `backup_snapshot`'s `AuditUnavailable`; `logging_setup._PAYLOAD_SIGNATURES` gains `last_backed_up_at`; the existing pins updated (`test_audit.py:860, 901, 985, 1092` → 4; `:1195, 1213, 1219` → `[-6:-2]` keeping the header AND value assertions; `:1352` → `[-8:-6]`; NEW `[-2:]` header and value assertions; `test_schema_versions.py:568` → 4, `:587, 658` → "as v4" — round 1 PR-MED-011). Done when: `test_schema_versions.py` reads v1 / v2 / v3 as v4, refuses v5 and any older version naming `backup`, still refuses a malformed v3; `test_logging_setup.py` drops a rendering of the record; `test_audit.py` covers the five new methods (a `_NEWER` plaintext re-encrypted unchanged into the supplied month; an id or month mismatch refused; a second row file never written; a pruned month refused; a linked month folder refused; the `pre_audit` replacement with a tombstone carried over); the CSV column order is pinned.
- [ ] 🟥 **1.3 The container module `past_sessions_backup.py` — header, KDF, manifest, reader.** `FORMAT_VERSION = 1`, `BackupHeader` (pydantic, `extra="forbid"`, ≤ 4 KiB, `channel: Literal["production", "dev"]`, `kdf` with the FINITE envelope of D3 — `memory_cost`, `iterations` and `lanes` each bounded, validated before `derive_key` is called, `kdf_out_of_range` otherwise — and `manifest_bytes` ≤ 16 MiB), `BackupManifest` (`extra="forbid"`; `members: [{name, size, sha256}]` — the PAYLOAD members only, `header.json` and `manifest.enc` refused as names (round 3 PR-MED-028) — with `name` validated against the member grammar of D11 — pattern-bound ids, `Literal` file names, `_MONTH_RE` months; `MAX_MEMBERS = 65_535` and the grammar bound `5 × entry_count + row_count + 3` (round 3 PR-MED-027); `entries: {id: {completed_at}}`, `rows: {id: month}`, `channel`, `app_version`, `made_at`, counts), `manifest_aad(header_bytes)`, `derive_key(passphrase, kdf) -> bytearray` (catches `MemoryError` → `BackupFormatError("kdf_memory")`), `_kdf_floor_for_tests` seam, `_preflight(path) -> PreflightFacts` (D11's bounded pre-`ZipFile` checks: file size, the end-of-central-directory record, ZIP64 refused, comment, entry-count and central-directory caps, the header member's offset / method / size — through an injected size-and-read seam so tests never allocate an oversized input; round 2 PR-MED-020), `open_backup(path, passphrase) -> BackupSummary` (the preflight, then the stored-only `zipfile` reader driven by the manifest: refuses an unlisted, duplicate, compressed or mis-sized member; verifies every hash; unwraps the audit key or ONE entry key as the second passphrase check — a zero-entry, audit-only file is valid, round 2 PR-MED-021), every refusal a `BackupFormatError(code)` from a closed code set. Done when: `test_backup_container.py` covers every C8 refusal by code (the preflight's through the seam, before any directory parse), a flipped byte in each region, and a zero-entry file's round trip.
- [ ] 🟥 **1.4 The writer, in hops.** `prepare_backup(store, audit, *, now, channel) -> BackupPlan` (GUI hop B: the snapshot of committed ids via `_committed_dirs`; per entry `_unwrap_entry_key` → `export_key()` → wrap under `K_b` → zero; `skipped_unreadable`; file names and sizes by path; `audit.backup_snapshot()` — the key wrapped under `K_b` and zeroed at once, the row DESCRIPTORS kept, no row ciphertext read on the GUI thread (round 4 PR-MED-031) — or entries-only on `AuditUnavailable`) and `write_backup_file(plan, k_b, destination, *, check_location) -> BackupReport` (worker hop C: the RESOLVED destination folder re-checked through the injected `check_archive_backup_location` seam immediately before the create — refused, changed or uninspectable → `destination_refused`, nothing written, round 2 PR-MED-022; `read_bytes` by path for entry members and `read_capped(path, MAX_ROW_FILE_BYTES)` for each audit row, one buffer at a time, `skipped_gone` for a member or row gone or over-size in between; a plan with no entries and no rows refuses `nothing_to_back_up` before any file exists, and one whose member count would exceed `MAX_MEMBERS` refuses `too_many_members` (the writer's limit is the reader's — round 3 PR-MED-027); the `.part` through `os.open(O_CREAT|O_EXCL)`; stored-only `zipfile`; `open_backup` re-read verification; `fsync`; rename; `.part` unlinked in `finally`; the `-n` suffix when the final name exists; refuses when a same-name `.part` exists). The `BackupReport` names the ENTRY ids actually written (the manifest's `entries`) and hop D's `record_backed_up` receives exactly that set — never the ids whose row alone was copied (round 1 PR-MED-005). Done when: `test_backup_write.py` shows the archive byte-identical before and after (directory hash), the inclusion and exclusion set of D1 (kept-recording files and `exports.enc` never copied — asserted by name, the decision 0.2 pin), entries-only with an unreadable audit key, a skipped-unreadable entry's copied row left unmarked, `.part` absent after a failure, the suffix, the same-name refusal, and that no store method runs on the worker (a thread-recording fake store).
- [ ] 🟥 **1.5 `check_archive_backup_location`.** `exclusions.py`: `DRIVE_REMOVABLE = 2`, `DRIVE_CDROM = 5`, `DRIVE_RAMDISK = 6`; the private `_destination(layer, folder)` extracted from `check_export_location` L493–523 (its behaviour unchanged, asserted by the existing tests); `ArchiveBackupLocation` (refused / warned / ok with a line) per D4 with the `st_dev` same-volume comparison; `BackupFolderSetting` in `note_config.py` beside `DevelopmentSettings` (`config\backup.json`, a bounded reader, absent or unreadable → None). Done when: `test_archive_backup_location.py` covers each branch with a fake layer and "no layer → refused"; `test_exclusions.py` unchanged in outcome.
- [ ] 🟥 **1.6 Version 0.4.0** in the five places + CHANGELOG `[Unreleased]`. Verification: `pytest -k version`.

### Phase 2 — Back up on the Past sessions tab

- [ ] 🟥 **2.1 The passphrase dialog.** `ui/backup_dialog.py` (the ONLY file with the new `QLineEdit`s): Qt-free `passphrase_decision(first, second, *, minimum) -> Accept | Refuse(reason)`; a `QDialog` with two `Password`-echo fields for Back up (one for Open), the never-stored sentence, the minimum line; `clear()` empties the fields on accept, reject and close; the passphrase is handed over as a `bytearray` the caller zeroes. Done when: tests cover the decision function and that the widget text is empty after each exit; `test_shadow_exits.py`'s count is unchanged.
- [ ] 🟥 **2.2 Back up…** `ui/past_sessions.py`: the button beside Export CSV; a `ChooseBackupPath` seam (the `ChooseWavPath` shape; the save name `ClinikoScribe-backup-YYYY-MM-DD.csbk`, suffix fixed, proposing the `backup.json` folder); `check_archive_backup_location` → refuse line / same-volume confirm; refused while `session_busy()` (a live or recoverable session — round 1 PR-MED-007) with the line "Finish or discard the current recording first"; the run flag taken BEFORE hop A and released in every exit path; the four hops over `ui/tasks.py::TaskThread` (A derive; B `prepare_backup` on the GUI thread, re-checking `session_busy` first; C `write_backup_file`; D `record_backed_up` with the report's entry ids, the folder setting saved, the status line refreshed); while the flag is held `PeriodicSweep.__call__` returns before its three steps without advancing their clocks (the flag injected as a callable into `PeriodicSweep` — round 2 PR-MED-017), both Start funnels refuse with a line, the tab's own "Start a new audit record" (`reset_audit_button`, the audit Reset — it lives on the Past sessions tab, not Status; round 5 PR-LOW-035) is disabled, and the tab's Delete now, Delete recording, Export, Open AND the retention selector are disabled, `on_retention_chosen` re-checking the flag after its confirm (C12); the button is enabled whenever the archive has a committed entry OR the audit record has a row, else it shows "Nothing to back up yet." (round 2 PR-MED-021); the success line of Flow 1 (with "audit record not included" when so); failures by type only. Done when: `test_past_sessions_ui.py`-style tests drive the flow with fakes (no real clipboard, dialog, layer or thread), including the disabled set during a run and the skipped tick.
- [ ] 🟥 **2.3 The status line and Delete now's sentence.** `ui/past_sessions_view.py`: `backup_status_line(committed_ids, rows, now) -> str | None` — N = the committed ids (from `_committed_dirs`, passed in) whose row is absent, `newer`, unreadable or has `last_backed_up_at is None`; "N entries not yet in any backup (last backup <date> / no backup yet)" when N > 0 and the last backup is older than 7 days or absent (a negative age clamps to 0); `status_lines` shows it; Delete now's confirm gains "A backup made before today still holds this entry — make a new backup and destroy the older ones." (decision 0.5); the retention warning string at L216 amended with D10's wording (the design-system quote at L533 with it — Task 4.4). Done when: the Qt-free function is tested for each state; the existing warning tests updated.

### Phase 3 — Open a backup and Restore

- [ ] 🟥 **3.1 The restore planner (GUI thread).** `past_sessions_backup.plan_restore(summary, store, audit, sessions_root, *, retention_days, now) -> RestorePlan` — runs on the GUI thread over the VERIFIED summary (it reads the archive, the audit store and the sessions root — never on a worker; round 1 PR-MED-008) and is re-run per entry inside `restore_backup` immediately before that entry is touched; per id, in D5's order: `skipped_live`, `skipped_unknown_row` (either source), `skipped_deleted` (either source), `skipped_expired` ("7 years" only), then the entry folder's `link_state` BEFORE any read under it — `None` → `skipped_uninspectable`, `True` → `skipped_linked`, confirmed absent → `add` (round 3 PR-MED-025) — `skipped_uninspectable` (an `OSError` reading the local key file or a member), `skipped_dead_key` (`key_blob_is_dead`), `skipped_foreign_key`, `skipped_present` — all four from ONE read of the blob through `unwrap_key_blob` — `repaired_unreadable` (a genuine DPAPI refusal AND the local CONTENT members equal the manifest's set with every hash matching, the two audio sidecars admitted in any state), `conflict_unreadable` (differing content or an unexplained extra member), `add`; per row: `add` / `skipped_present_row` / `skipped_pruned_row` (by the manifest's month) / `provenance_recovered` (a BARE `pre_audit` local row, `recorded` backed-up) / `conflict_row` (a `pre_audit` local row holding facts); refused as a whole while `audit.key_unreadable()` or the manifest channel differs from `install_layout.channel()`. Done when: `test_restore.py` covers every classification from both tombstone sources, both refusals, and the per-entry reclassification.
- [ ] 🟥 **3.2 The restorer.** `restore_backup(summary, plan, store, audit, *, now) -> RestoreReport` on the GUI thread: audit rows first (`restore_row` with the manifest's month; local rows kept except the `pre_audit` → `recorded` replacement), then entries, each reclassified first (Task 3.1) and — for a KEPT local row — `record_restored(id)` called only after that entry's `_publish` or its repair's `os.replace` has returned (round 5 PR-MED-034: the attempt must not become an audit fact of success; an imported row's own provenance is `restore_row`'s, above): an `add` through a new `PastSessionStore.restore_entry(session_id, key_bytes, members, expected_hashes)` — `.staging\<id>` through the archive's own path (`_staging_linked`, the key by `self._wrap_key`, the files copied, `_verify_restored` by hash AND the readers and the label parse, `_publish` WITHOUT `pending`), key-first removal of the staging on failure, `failed_verify` counted; a `repaired_unreadable` through a new `PastSessionStore.repair_entry_key(session_id, key_bytes, expected_hashes)` — refused while `.staging` is linked or the entry folder's `link_state` is not `False` (round 3 PR-MED-025); `.staging\<id>` removed key-first; the local content members re-hashed against the manifest IMMEDIATELY before the write; the new blob written by `self._wrap_key` into `.staging\<id>\` (its fixed `key.dpapi` name — no new file name anywhere), read back through `self._unwrap_key`, the final entry's content then OPENED with that key through `_verify_restored`'s reader pass over the entry folder (label parse under `_label_aad`, `read_transcript`, `read_note`, `read_generated` — round 3 PR-MED-026), then `os.replace`d over the entry's `key.dpapi`; in a `finally`, `.staging\<id>` removed key-first — `_remove_key_first` gaining `KEY_FILENAME + ".tmp"` as a second load-bearing unlink (the atomic writer's temporary) — a failed removal logged and counted `failed_repair` with the folder left to `clean_staging`; a failure or crash at any step before the `os.replace` leaves the entry's old key file, and after it the verified new key stays committed (round 2 PR-HIGH-013, round 3 PR-HIGH-024, round 5 PR-LOW-035), `failed_repair` counted; `delete_entry` extended to remove `.staging\<id>` through `_remove_key_first_unless_link` BEFORE the committed key, `delete_failed` (key untouched) when that removal fails or `.staging` is linked or unreadable — Delete now and expiry both run through it (`ui/past_sessions.py` and `sweep_report`); no other file of an existing entry is ever written or removed; counts only. Done when: `test_restore.py` shows a restored archive opens through `list_entries` / `read_entry`, a tampered member fails that entry alone, readable local entries are byte-identical afterwards (directory hash), a repaired entry opens with every file but `key.dpapi` byte-identical and its audio sidecar still present (kept, zeroed and deleted-residue variants), a conflicting entry is byte-identical afterwards, a failed read-back leaves the old key file and only a `.staging\<id>\key.dpapi` that the next `clean_staging` removes, a crash injected after the staging write and before the `os.replace` is recovered by `clean_staging` and the repair retried, Delete now (and expiry) IMMEDIATELY after a failed repair — no tick between — leaves no usable key anywhere (`.staging\<id>\key.dpapi` and `key.dpapi.tmp` both gone before the committed key) and reports `delete_failed` with the committed key intact when the staging removal is made to fail, a backup whose authenticated manifest pairs an id with another entry's key fails the repair with the old key and every file byte-identical (PR-MED-026), a junction where the entry folder would be — its target holding matching ciphertext — is `skipped_linked` with the target byte-identical and an unreadable link state `skipped_uninspectable` (PR-MED-025), no `pending` exists, a restored entry without audio reads `recording_state == none` and `tidy_dead_recordings` leaves it alone.
- [ ] 🟥 **3.3 Open a backup… on the tab.** `ui/past_sessions.py`: the button; a `ChooseBackupFile` seam; `session_busy` seam (from `MainWindow._live_session_ids` and the recovery list; enabled only when False and no run is active; re-checked after the summary dialog returns); the header pre-check, the passphrase dialog, the run flag taken before hop A, hop A and `open_backup` on the worker (the FILE only — no store, audit or controller call), then `plan_restore` on the GUI thread (round 1 PR-MED-008), the summary dialog of Flow 2 with Close and Restore (Qt-free `restore_summary_lines(summary, plan)`), `session_busy` re-checked and `restore_backup` on the GUI thread, the success line with the Clinics-tab reminder; refusals by name; `PastSessionsAudit` extended. Done when: UI tests cover the disabled states, the re-check, the summary text for each count, Close writing nothing, a developer-channel file refused on an installed-channel build (channel injected), "Start a new audit record first" when the audit key is unreadable.

### Phase 4 — Documents and the reversed promise

- [ ] 🟥 **4.1 Security documents.** `docs/security/threat-model.md`: a section "Past-sessions backup and restore (past-sessions-backup plan; 0.4.0)" — surfaces (the file outside custody; key-wrap and the header-bound manifest; the KDF and passphrase strength; the location rule and its limits; restore's classifications, the tombstones and decision 0.9's replacement; the audit v4 fields and the three new methods) and residues (a backup holds entries deleted later; a tombstone-less Delete now comes back; the passphrase in widget memory / pagefile and the `AESGCM` copy; a backup on the same disk; an unknown sync tool; a removable drive lost = ciphertext under the passphrase alone; the shell's recent-files entry names the file and drive; a `.part` left by a yanked drive; `_NEWER` rows after rollback; a restored row's `kept_at` without a recording; the audit rows carry Cliniko ids — the backup is as sensitive as the CSV); residue (c) and L3769 amended; L4044 / L4084 / L4102 updated. `data-flow-map.md`: flow 28. `retention-schedule.md`: rows for the backup file and `config\backup.json`, the v4 columns; rows 67 and 134 and L235 / L257–264 amended. `intended-use.md` L63. Done when: the Task 0.8 grep returns only intended sentences.
- [ ] 🟥 **4.2 Practice documents (C10) — `patient-info-v4`.** The D10 inventory amended in plain English (the "own Windows login" sentence included); `patient-information-and-consent.md` version line `patient-info-v4` (v3 noted as history); `downtime-procedure.md` "Losing the computer" becomes the restore procedure — the new-computer sequence and the same-login-after-a-password-reset sequence of Flow 4 (never Delete now the unreadable entries first); the operating rules (the drive kept locked away, apart from the passphrase; the newest two backups; destroy older after a Delete now; a lost passphrase is a lost backup); `development-recording-consent.md` L61 / L68 given a pointer (decision 0.2); the review banner kept; the README's open-questions list gains the two reviewer questions of D10. Done when: a read-through finds no file name or identifier in patient-facing text; `test_pilot_docs.py` passes if touched.
- [ ] 🟥 **4.3 Release and project documents, and this plan's cross-references.** `docs/release/pilot-builds.md`: "Rolling back below 0.4.0" (D9, with the no-tombstone sentence); `PLAN.md` L152 and the Phase 6/7 notes; `AGENTS.md` Current Status, Database Notes (`config\backup.json`, the backup file), the Subsystem pointer "If touching the backup…" (the four hops, C12, the manifest-driven reader, the replacement rule); the pointers into `plan-privacy-professional-controls.md` (its Deferred item), `plan-installation.md` and `plan-pilot.md` (their Deferred lines) naming this plan; `CHANGELOG`. Done when: `test_install_layout.py`'s version pin and `test_pilot_docs.py` pass.
- [ ] 🟥 **4.4 Design-system cues.** `docs/design-system.md`: the two buttons, the passphrase dialog, the summary dialog's Close and Restore, the confirm texts, the status line, Delete now's added sentence, the amended retention-warning quote (L533) — each anchored to its symbol.

### Hardening

- [ ] 🟥 **H1 `/review-loop`** over the whole diff (cap 3). — [ ] 🟥 **H2 `/simplify`.** — [ ] 🟥 **H3 `/security-review`** (the passphrase path, the manifest-driven reader and the header binding, the location rule, restore's classifications and the replacement). — [ ] 🟥 **H4 codex peer pass** (`gpt-6-astra`; slice by module if the diff exceeds ~15 files). — [ ] 🟥 **H5 build of record**: Task 0.7's probe output recorded, tag, CI `Release`, attestation and hashes recorded in `docs/release/pilot-builds.md`.

### Phase P — Practitioner-run

- [ ] 🟥 **P.1 Install 0.4.0** per `docs/release/pilot-builds.md` (both apps closed; existing model pack; extension reloaded; Chrome restarted). PASS = the Status tab names 0.4.0 and the Past sessions tab shows Back up… and Open a backup….
- [ ] 🟥 **P.2 Developer-build round trip on an isolated data folder** (both apps closed first; every step the practitioner's own, from Explorer or a normal terminal — never an agent shell, `docs/lessons.md`): rename `%LOCALAPPDATA%\ClinikoScribe-dev` aside (it holds the clinic 1 smoke's consented recordings — C1), create a fresh `ClinikoScribe-dev` and MOVE only the `models` folder into it from the set-aside root (the pinned public downloads — nothing else is copied: no sessions, archive, audit record, profile or settings; round 4 PR-MED-032); start the developer build and confirm it is ready to record (the Status tab names the models; Start is not refused as missing a model), record two synthetic validation scripts aloud and Complete them (non-mock, synthetic content); Back up… to a USB drive; close the app, move the fresh `past_sessions` folder aside; Open a backup… → the summary → Close (the check), then Open again → Restore; both entries open; close the app, move the `models` folder back into the set-aside root, delete the scratch data folder, restore the original folder's name, and confirm the developer build opens on the original folder. Numbers only pasted here.
- [ ] 🟥 **P.3 The first real backup** on the installed app to a removable drive kept apart from the passphrase; Open a backup… → the summary → Close; the status line on the tab. The agent sees only the counts the practitioner pastes (C1).
- [ ] 🟥 **P.4 Documents read** (`patient-info-v4`, the siblings, the downtime procedure's two restore sequences) and queued for the independent review.
- [ ] 🟥 **P.5 The rollback rule read** before any older install.

## Review History
- 2026-10-09 — `/review-plan` (Fable 5.1), full-plan pass over the draft: four parallel lenses (coverage 13, practicality 11, risk 19, simplicity 7 findings). Folded in: decision 0.9 (same-login DPAPI break → replace unreadable entries key-first); the header-bound manifest, bounded KDF memory and pattern-bound manifest grammar; the stdlib-ZIP container; the run ledger dropped and Check folded into Open a backup; the `AuditLog` export/import surface and its key seams; the four-hop threading split and C12; the restore classifications (`skipped_unknown_row`, `skipped_pruned`, `skipped_expired`, `replaced_unreadable`); restored rows carrying `made_at`; `patient-info-v4` and the "own Windows login" sentence; P.2 moved to an empty set-aside dev data folder; symbol corrections (`audit:` AAD, `session_store` helpers, `install_layout.channel()`, the `check_backup_*` name collision, the two existing drive constants); the eight v3 test pins named. Deferral gate: every candidate confirmed as listed. No scratch consumed.
- 2026-10-09 — `/peer-loop` plan-review round 1 (codex `gpt-6-astra` medium, read-only sandbox, composer-recorded): 12 findings (1 HIGH, 10 MED, 1 LOW; 11 build-affecting, 1 record-only), all verified against the code and applied as amendments the same day: decision 0.9 narrowed to a hash-verified key REPAIR with conflict and uninspectable outcomes (PR-HIGH-001); unknown audit state in EITHER source skips (PR-MED-002); archive retention decoupled from audit pruning — an entry of any age restores under "Until I delete them", its pruned row not recreated (PR-MED-003); `restore_row` takes the manifest's month and binds id / month (PR-MED-004); backup coverage marks only the entries actually written (PR-MED-005); `_upgrade_v2` pinned to 3 (PR-MED-006); Back up gated on `session_busy`, the run flag and the Reset lock (PR-MED-007); the planner moved to the GUI thread (PR-MED-008); a finite KDF envelope (PR-MED-009); the `pre_audit` → `recorded` provenance recovery (PR-MED-010); the CSV slices corrected to `[-6:-2]` / `[-8:-6]` with the value assertions and `test_schema_versions.py:568` (PR-MED-011); the `sample_notes.py` description corrected (PR-LOW-012). Round 2 to follow (the round-1 floor; convergence needs a round with no new build-affecting finding).
- 2026-10-09 — `/peer-loop` plan-review round 2 (codex `gpt-6-astra` medium, composer-recorded): 11 new findings (1 HIGH, 10 MED; all build-affecting), all verified and applied: the key repair became a staging-folder transaction with no new file name, recovered by `clean_staging` (PR-HIGH-013); the repair's member rule admits the two audio sidecars in any state (PR-MED-014); custody classified from ONE blob read through a new `unwrap_key_blob` seam — uninspectable / dead / foreign / DPAPI-refused (PR-MED-015); `restore_row(..., included)` and `backup_status_line(committed_ids, …)` (PR-MED-016); the run guard at `PeriodicSweep.__call__`, the retention selector disabled (PR-MED-017); original-version required-field rules for v3 and v4 (PR-MED-018); the `_v1_document` / `_v2_document` builders strip `backup` (PR-MED-019); a bounded ZIP preflight before `ZipFile` (PR-MED-020); zero-entry audit-only backups and Back up enabled on an emptied archive (PR-MED-021); the destination re-checked immediately before the exclusive create (PR-MED-022); provenance recovery only for a BARE `pre_audit` row, `conflict_row` otherwise (PR-MED-023). Round 3 to follow (not converged: new build-affecting findings).
- 2026-10-09 — `/peer-loop` plan-review round 3 (codex `gpt-6-astra` medium, composer-recorded): 8 of round 2's 11 fixes confirmed landed, 3 partial; 6 new findings (1 HIGH, 5 MED; all build-affecting), all verified and applied: `delete_entry` removes `.staging\<id>` key-first BEFORE the committed key and the repair's cleanup is synchronous, `_remove_key_first` also unlinking the atomic writer's `.tmp` (PR-HIGH-024); the entry folder's `link_state` is read before anything under it — `skipped_linked` / `skipped_uninspectable` (PR-MED-025); the repair opens the content with the recovered key before the replace (PR-MED-026); the member bound is `5 × entry_count + row_count + 3` plus `MAX_MEMBERS = 65_535` (PR-MED-027); `header.json` / `manifest.enc` are envelope members outside the manifest's payload list, the member set equal to envelope plus payload (PR-MED-028); provenance recovery merges the two `backup` timestamps by `max` (PR-MED-029). Round 4 to follow (not converged).
- 2026-10-09 — `/peer-loop` plan-review round 4 (codex `gpt-6-astra` medium, composer-recorded): 5 of round 3's 6 fixes confirmed landed, 1 partial; 4 new findings (3 MED build-affecting, 1 LOW record-only), all verified and applied: the `backup` timestamps are monotonic everywhere — the incoming row's own coverage counts in the merge, `record_backed_up` / `record_restored` take the later value (PR-MED-030); `backup_snapshot` returns row DESCRIPTORS, the worker reading each row under `MAX_ROW_FILE_BYTES` (PR-MED-031); P.2's isolated folder carries the moved-over `models` folder and confirms readiness (PR-MED-032); Agreed Scope and the schema table say key REPAIR, with a row for a repaired entry (PR-LOW-033). Round 5 to follow (not converged; the cap).
- 2026-10-09 — `/peer-loop` plan-review round 5 (codex `gpt-6-astra` medium, composer-recorded; the pass's cap): all 4 of round 4's fixes confirmed landed; 2 new findings (1 MED build-affecting, 1 LOW record-only), both verified and applied: `record_restored` for a kept local row is called only after its entry's publish or the repair's `os.replace` has committed (PR-MED-034); the Integration Notes' between-hop tick example removed, audit-vs-archive retention stated, the post-replace wording ("the new key stays committed"), and the audit Reset located on the Past sessions tab (PR-LOW-035). Tail: 12 → 11 → 6 → 4 → 2 findings (build-affecting 11 → 11 → 6 → 3 → 1); NOT converged at the cap — the cap disposition is the practitioner's (surface-and-ask).
- 2026-10-09 — `/peer-loop` pass ACCEPT-CLOSED at the cap by the practitioner's decision (option (a) of the surface-and-ask: every finding of rounds 1–5 verified against the code and applied, 0 rejected, no CRIT/HIGH since round 3, round 5's one build-affecting item a sequencing clarification with no residue). The plan is ready for `/execute-loop` from Phase 1; a fresh `/peer-loop` pass over the Phase 1 diff is that run's own first peer round.

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
