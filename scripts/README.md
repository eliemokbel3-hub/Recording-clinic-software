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
