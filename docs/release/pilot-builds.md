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
| | | | | | | No build recorded yet. |

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
re-checks it before the first run. If no attestation can be made, the first
check above can never pass, and the build of record needs a decision — never an
install without that check.
