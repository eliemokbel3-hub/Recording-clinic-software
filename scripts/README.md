# Scripts

Every script here is run by the practitioner from a normal PowerShell at the
repository root (agent shells on this machine are MSIX-virtualized, so their
`%LOCALAPPDATA%` and registry writes prove nothing — `docs/lessons.md`). Since
the installation plan a source checkout is the DEVELOPER build: these scripts
set up and build it, and make releases; the installed app needs none of them.

## The developer build

- `register-native-host.py` (plan Step 6; dev-only since installation plan
  Task 3.7) — registers the DEVELOPER build's Chrome link: copies the venv's
  `scribe-host.exe` and writes the host manifest for `com.scribe.cliniko_host_dev`
  (the dev extension's origin only) into `%LOCALAPPDATA%\ClinikoScribe-dev\`,
  then writes and verifies the HKCU registry entry, plus the three per-user
  Windows Error Reporting exclusions. `--unregister` reverses it and also
  removes what earlier versions wrote under the PRODUCTION name (the per-user
  `com.scribe.cliniko_host` key and its two files in
  `%LOCALAPPDATA%\ClinikoScribe\` — nothing else there). On a computer whose
  everyday app is still that source-run registration it is the live Chrome
  link, so run `--unregister` only as the installation's step (Phase P step
  2; done on this computer 2026-10-03). The installed app's Chrome link is
  its installer's, never this script's.
- `setup-models.py [--only NAME] [--root DIR]` — downloads the pinned models
  (setup-time network) into the developer build's
  `%LOCALAPPDATA%\ClinikoScribe-dev\models\`, or with `--root DIR` into a
  staging folder for the release model pack (then nothing under
  `%LOCALAPPDATA%` is touched).
- `generate-extension-key.py [--out PATH]` or documented openssl commands (plan
  Step 3) — an extension identity keypair: `extension/key.pem` (the release
  extension) by default, `--out extension/key-dev.pem` for the developer
  build's extension; any other `--out` is refused before a key is read or
  written. Both private keys are gitignored and never committed;
  `extension/KEY.md` records both IDs.

## Making a release (installation plan, D7)

- `lock-build-requirements.py --constraints <freeze>` (Task 3.1) — writes the
  hashed build lock `desktop/requirements-build.txt` from an environment
  already proved (build-time network: one wheel per dependency from PyPI).
  Commit the lock it writes.
- `build-release.py` (Tasks 3.3 and 3.5) — four modes:
  `--write-manifest --models DIR` writes `packaging/models-manifest.json`
  (commit it); `--model-pack --models DIR --out DIR` copies the manifest's
  files into `ClinikoScribe-models-<8 hex>\`; `--audit DIST` checks a
  PyInstaller bundle (fails closed, a Defender detection included); and the
  build itself, `--pyinstaller-src DIR --out DIR` (a clean environment from
  the lock, PyInstaller from a clean clone at its pinned commit, built with
  the locked hatchling backend and no build isolation, the bundle
  audit, the release extension, Inno Setup 6.7.3, `BUILD-INFO.txt` and
  `SHA256SUMS.txt`). The build of record is the CI `Release` workflow's; a
  local build is for spikes and the model pack. See `docs/release/pilot-builds.md`.
- `check-installed-sockets.py --seconds N` (Task 3.8) — watches the INSTALLED
  app's processes for network connections during a transcription and a prose
  render (Phase P step 10); prints connections only, never app text.

## Measurement and checks

- `measure-speakers.py <recordings-dir>` (Phase 3A Task 2.3a) — thin launcher for
  `scribe_desktop.speaker_eval`: speaker-cluster and clinician-role accuracy on
  labelled recordings (`<name>.wav` 16 kHz mono 16-bit + `<name>.txt` Audacity
  label track), before and after Task 2.1, through the shipped pipeline over a
  temporary encrypted store torn down key-first (any teardown failure or residue
  is reported by path). Run by the practitioner from a normal terminal; prints a
  Markdown table for Task 2.3, never transcript text.
- `build-validation-set.py <scripts-dir> <set-folder> [--only <id> ...]` and
  `run-validation.py <set-folder> --config <folder> --rule <file>` (pilot plan
  Phase 2) — thin launchers for `scribe_desktop.validation_set` and
  `scribe_desktop.validation`. The first speaks each synthetic script with the
  installed Windows voices into `<id>.wav` + `<id>.txt` plus a copy of
  `<id>.json`, with an `<id>.built` ownership mark (needs three voices in the
  current voice baseline's order — slots 0, 1 and 2 — and PyAV
  from the `[ml]` extra; the set folder must be outside the repository and
  holds synthetic files only since the clinic 1 smoke retired the role-plays;
  a recorded ("role-play") encounter in it — its `<id>.json`, or its WAV or
  label track without the mark — is never overwritten); the
  second runs every encounter through the shipped pipeline in a temporary
  encrypted store torn down key-first and prints a text-free report, pass or
  fail against the rule. Developer build only, from a normal terminal; see
  `docs/testing/validation-harness.md`.
- `replay-kept-recordings.py <past_sessions folder> [--only <session id> ...]
  [--enrolment <wav>] [--model <name>]` (development-recordings plan Phase 4) —
  thin launcher for `scribe_desktop.replay_kept`: replays every recording kept
  for development in the Past-sessions folder you name through the current
  pipeline (a temporary encrypted store whose key is never written to disk) and
  prints session ids, DRIFT numbers and model names (and the folder given) — no
  transcript, note or name text — the new transcript against the
  kept one, and a note regenerated under the shipped default config against the
  clinician's saved note. Reads the folder and writes nothing there; holds the
  app's single-instance lock for its run (close Clinic Scribe first). Developer
  build only, from a normal terminal; see `docs/testing/kept-recordings.md`.
- `speaker-embedding-smoke.py --model <path> <wav> [<wav> ...]` (practitioner-profile
  plan Task 0.3) — loads a speaker-embedding ONNX model from an explicit path (the
  `SileroVad` contract: offline kill-switches asserted before onnxruntime is
  imported, UNC refused, load failures typed) — so it can read the promoted
  `<name>.onnx` or an un-promoted `<name>.onnx.candidate` (what an UNPINNED
  candidate fetch leaves; the entry is pinned since Task 0.5, so
  `setup-models.py --only speaker-embedding` now verifies and promotes) — embeds
  each 16 kHz mono 16-bit WAV through the SHIPPED front-end (since Task 1.1 the
  script imports `scribe_desktop.speaker_embedding`'s Kaldi-style 80-bin fbank
  and load contract — Povey window by default, `--window hamming` reproduces the
  Task 0.4 matrix), and prints the model's I/O shapes, the embedding dimension
  and the cosine matrix. Text-free: file names, durations and numbers only. Run
  by the practitioner from a normal terminal (Task 0.4).
- `probe-cliniko.py` (Cliniko workflow safeguards plan Task 1.3, run at Task
  P.1) — read-only feasibility check of one clinic through the app's own Cliniko
  client (`scribe_desktop.cliniko_client`: GET only, host pinned from the key's
  shard). Asks for the contact email, the open treatment note's URL and the API
  key (the key via `getpass` only — never an argument or environment variable),
  then prints ONLY structure: each call's status, field names with values
  reduced to their kind, and yes/no facts (draft state, links, practitioner and
  patient matches, whether `/settings/public` answered). Never a name, id value,
  answer text, the URL, the email or the key. Run by the practitioner from a
  normal terminal at the repo root with a treatment note open in Cliniko.
