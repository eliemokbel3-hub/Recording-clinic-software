# Scripts

- `register-native-host.py` (plan Step 6) — generates the Chrome native-messaging
  host manifest and `dev-host-launcher.bat` from the current interpreter path,
  writes and verifies the HKCU registry entry; `--unregister` reverses it.
- `generate-extension-key.py` or documented openssl commands (plan Step 3) —
  extension identity keypair; `key.pem` is gitignored and never committed.
- `measure-speakers.py <recordings-dir>` (Phase 3A Task 2.3a) — thin launcher for
  `scribe_desktop.speaker_eval`: speaker-cluster and clinician-role accuracy on
  labelled recordings (`<name>.wav` 16 kHz mono 16-bit + `<name>.txt` Audacity
  label track), before and after Task 2.1, through the shipped pipeline over a
  temporary encrypted store torn down key-first (any teardown failure or residue
  is reported by path). Run by the practitioner from a normal terminal; prints a
  Markdown table for Task 2.3, never transcript text.
