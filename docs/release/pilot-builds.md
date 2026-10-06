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
