# Pilot builds

The record of every Clinic Scribe installer built for the pilot (installation
plan Task 3.9, D7). The build of record is the GitHub `Release` workflow's
artifact: a manual run on `main`, attested by GitHub. The build is unsigned
for the pilot, so the two checks below are what prove a download is that
build. Run both before every install.

Add one row per build, newest first, when the run is green. The model pack is
built once by the practitioner and changes only when a model pin changes; its
row names the manifest it was checked against.

| Version | Commit | CI run | Installer SHA-256 | Model-pack manifest SHA-256 | Date | Notes |
|---|---|---|---|---|---|---|
| 0.1.0 | `e730cd552e937149104db6261dd083a7cc78767d` | [37081519723](https://github.com/eliemokbel3-hub/Recording-clinic-software/actions/runs/37081519723) | `e48a6602a08b6bfd43834937a713542896e607a290f7a511f5410677e880ac99` | `10a834937fe8c783d3e387dcdb4c2b74c3c290db97c626e38be4deba3fa9930a` | 2026-10-03 | First build of record. `BUILD-INFO.txt` says `tree=clean`; `gh attestation verify` passed for the installer and `SHA256SUMS.txt` (composer, 2026-10-03); the hash matches `SHA256SUMS.txt`. Installed on this computer 2026-10-03 (Phase P.1). |
| 0.1.1 | `f9f7642903524d9475a6652d0388fe97ff5d3dab` | [37108950093](https://github.com/eliemokbel3-hub/Recording-clinic-software/actions/runs/37108950093) | `4c5b7455861946c96a7e832f68f4da8adb1d9bbe84f497d40cd848f246b04d9d` | `10a834937fe8c783d3e387dcdb4c2b74c3c290db97c626e38be4deba3fa9930a` | 2026-10-03 | The first-recording fix (plan rounds 35–39). `BUILD-INFO.txt` says `tree=clean`; `gh attestation verify` passed for the installer and `SHA256SUMS.txt` (composer, 2026-10-03); the hash matches `SHA256SUMS.txt`; models manifest unchanged from 0.1.0. Task P.3 passed on it (upgrade, rollback, uninstall, reinstall), 2026-10-03. |
| 0.1.2 | `a6a66db1332d7f5757f94af94a159a95810b839f` | [37117373944](https://github.com/eliemokbel3-hub/Recording-clinic-software/actions/runs/37117373944) | `c24af1e6aa75781b2799f8850710d7204de9ff9eefb3acdc69a19531243a2dda` | `10a834937fe8c783d3e387dcdb4c2b74c3c290db97c626e38be4deba3fa9930a` | 2026-10-03 | The Finish-page and Discard fixes (plan rounds 40–43). `BUILD-INFO.txt` says `tree=clean`; `gh attestation verify` passed for the installer and `SHA256SUMS.txt` (composer, 2026-10-03); the hash matches `SHA256SUMS.txt`; models manifest unchanged. Installed on this computer 2026-10-04. |
| 0.2.0 | `a8fdd157a5dfa866285abfd1a73b11800111fa57` | [37546310076](https://github.com/eliemokbel3-hub/Recording-clinic-software/actions/runs/37546310076) | `1f211f0323eec4a2156c0b18c34c30a6fa50c74a1d27e85a219c32df3f5482ab` | `10a834937fe8c783d3e387dcdb4c2b74c3c290db97c626e38be4deba3fa9930a` | 2026-10-07 | The pilot build (pilot plan Phases 1–3 and hardening H1–H4, review rounds 6–28): shadow mode, schema v2 for the encounter record, audit row and Past-sessions label, the line editor's Copy and Cut out of clipboard history, lists and drop-downs that refuse Copy. Read "Rolling back below 0.2.0" before installing any older build afterwards. `BUILD-INFO.txt` says `tree=clean`; `gh attestation verify` passed for the installer and `SHA256SUMS.txt` (composer, 2026-10-07; source `refs/heads/main` at `a8fdd15`, run 37546310076); the hash matches `SHA256SUMS.txt`; models manifest unchanged, so the existing model pack serves it. CI run 37546301715 green on the same commit. Not yet installed (pilot plan Phase P). |

- **Version**: the `AppVersion` the installer shows; it comes from `desktop/pyproject.toml`.
- **Commit**: the full commit the run built. The run's `BUILD-INFO.txt` names it too, and must say `tree=clean`; a build that says `DIRTY` or `unknown` is never recorded here.
- **CI run**: the run's link.
- **Installer SHA-256**: the `.exe` line of the run's `SHA256SUMS.txt`.
- **Model-pack manifest SHA-256**: the `models-manifest.json` line of the same file. Its first 8 characters name the model pack folder (`ClinikoScribe-models-<first 8>`) that goes beside `setup.exe`.

## Verifying a download

From a normal PowerShell, in the folder holding the downloaded `setup.exe` and
`SHA256SUMS.txt`:

1. Check GitHub's provenance attestation (needs the GitHub CLI, signed in):

   ```powershell
   gh attestation verify .\ClinikoScribe-<version>-setup.exe --repo eliemokbel3-hub/Recording-clinic-software --signer-workflow eliemokbel3-hub/Recording-clinic-software/.github/workflows/release.yml --source-ref refs/heads/main
   ```

   It must report that the attestation is verified. The two extra options make
   the check itself refuse an attestation from any other workflow, or from a run
   of any branch but `main`, so you do not have to read that from the output.

2. Check the file's SHA-256 against the run's list and this table:

   ```powershell
   Get-FileHash .\ClinikoScribe-<version>-setup.exe -Algorithm SHA256
   ```

   The hash must equal the `.exe` line of `SHA256SUMS.txt` and this table's row.
   `Get-FileHash` prints it in capitals and `SHA256SUMS.txt` in small letters:
   compare the letters and digits, ignoring capitals.

If either check fails, do not run the installer.

GitHub can attest a build only for a public repository, or a private one on
GitHub Enterprise Cloud. This repository was checked public on 2026-10-03, so
attestation is available; it stays so only while the repository stays public
(or moves to Enterprise Cloud). The installation plan's Task 3.6 step 0
checked it before the first run; check it again before a release run whenever
the repository's visibility may have changed. If no attestation can be made, the first
check above can never pass, and the build of record needs a decision — never an
install without that check.

## Rolling back below 0.3.0

From 0.3.0 (the development-recordings build) a recording the patient
consented in writing to keep for developing the program keeps its audio,
encrypted, in its Past-sessions entry (`audio.enc` beside `audio-key.enc`),
and the encounter record and the audit row are schema v3. A build older than
0.3.0 (0.2.0) reads 0.3.0's data as follows:

- **A kept recording's Past-sessions entry**: 0.2.0 opens its transcript and
  notes as usual and simply does not show the recording (it ignores the two
  files). Its **Delete now**, and its retention expiry, still destroy the
  recording too, because the recording's key is wrapped under the entry's key.
  A kept recording therefore cannot be deleted ALONE on 0.2.0 — a patient's
  withdrawal needs Delete recording, so install 0.3.0 or later again to honour
  it the same day. Never use Delete now for a withdrawal: it is only for a
  recording made in error, and it would also delete the transcript and notes,
  which are kept as health information.
- **An unfinished recording started on 0.3.0** (its `encounter.enc` is v3):
  0.2.0 cannot read the record, so it opens the session through Recovery as
  UNLINKED and SHADOW, and refuses it from the Unreviewed list
  (`consent_unavailable`). A 0.2.0 Complete keeps no audio.
- **The audit record**: a v3 row is NEWER to 0.2.0 — kept byte for byte, its
  updates fail (counted on the Past sessions tab) and it is OMITTED from 0.2.0's
  CSV, so a 0.2.0 Complete of a 0.3.0-started session is not recorded in that
  row. And EVERY row 0.3.0 has updated is v3, not only the rows of
  0.3.0-started sessions: an update re-writes the row it read, upgraded — a
  write, a Discard, a Complete, Delete now, an expiry or the start-up repair of a
  0.2.0-started session — so 0.2.0 also omits those rows from its CSV and fails
  its own later updates of them.
- **The files 0.2.0 ignores**: `config\development.json` (the "Keep recordings
  for development" setting), and the export ledger `past_sessions\exports.enc`
  with its key `past_sessions\exports-key.dpapi` — so 0.2.0 never resolves an
  export that was interrupted (a `<session id>.wav.part` file, the recording
  unencrypted, left in the folder it was being exported to).

**The rule: before installing any build older than 0.3.0, take TWO steps.**

1. **Finish (Complete) or Discard every recording** — nothing on the Recovery
   tab and nothing in the Unreviewed list.
2. **Start 0.3.0 once more and let it open** — its start-up removes any
   interrupted export's partial file without comment, and names on the Past
   sessions tab any it could not remove (delete that one by hand) — **then close
   it.** Then, **always** — whatever the tab said, and also when 0.3.0 cannot
   run — look in every folder you have ever exported a recording to (attach
   any external drive you exported to first) for a `<session id>.wav.part`
   file, delete it by hand, then empty the Recycle Bin. The start-up cannot
   find every one: a partial file on a drive that was unplugged at an earlier
   start, or listed in a record of exports that was later started again, is
   forgotten by the app but still on that drive.

Finishing the recordings alone does not satisfy the rule. Nothing enforces it
(development-recordings plan D14; threat model, "Kept recordings"). Below
0.2.0, the rule that follows applies as well. Installing 0.3.0 or later again
reads everything as before, the kept recordings included.

## Rolling back below 0.2.0

From 0.2.0 (the pilot build) the app records each recording's mode — normal or
shadow — in its encounter record, its audit row and its Past-sessions label, as
schema v2. A build older than 0.2.0 cannot read those v2 files as they are
meant: it treats an unfinished recording's encounter record as unavailable, so
a SHADOW recording awaiting recovery opens as an unlinked recording whose note
CAN be copied, and it cannot open an Unreviewed recording made on 0.2.0; it
lists a 0.2.0 Past-sessions entry as unreadable, and keeps 0.2.0 audit rows
untouched without updating them.

**The rule: before installing any build older than 0.2.0, finish (Complete) or
Discard every recording** — nothing on the Recovery tab and nothing in the
Unreviewed list. Nothing enforces this (pilot plan Accepted Assumptions; threat
model, "The pilot"). Installing 0.2.0 or later again reads everything as before.
