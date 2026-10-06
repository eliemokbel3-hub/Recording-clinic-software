# Incident Process

Who: the practitioner-developer (single-user product until commercialisation).
When in doubt, stop using the software and investigate before resuming.

## What counts as an incident

- Suspected compromise of the clinic machine or Windows user account
- Unexpected change to the registration chain: the startup tripwire log
  (`host_manifest` / `host_manifest_other` / `host_launcher` (the host exe) /
  `host_start` paths in `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-host.log`;
  a developer build's in `ClinikoScribe-dev\logs\`) shows a path you did
  not set, a `host_manifest state=network_path` line (a link pointing at a
  network share — the app and host never open it, but Chrome would), or
  registration verification fails. For the INSTALLED app the
  expected paths are all under `C:\Program Files\ClinikoScribe`, reached
  through the machine-wide (HKLM) link; the Status tab's "Warning: a
  per-user Chrome link overrides the installed one." means a per-user entry
  now wins — investigate it unless you know you made it (installation plan:
  the old source-run registration was one; on this computer it was removed
  at Phase P step 2, 2026-10-03, so a per-user entry here is unexpected)
- (Installation) a downloaded installer that fails `gh attestation verify` or
  whose SHA-256 does not match `SHA256SUMS.txt` and `docs/release/pilot-builds.md`
  (do not run it); a Defender detection in a build; the box "Clinic Scribe is
  not running from its install folder" when you started it from the Start
  menu; or the installed program folder found changed or writable by a
  standard user
- Any sign of payload content in log files (the tripwire also counts drops —
  a nonzero drop count means misuse of the logger somewhere)
- A Cliniko API key exposed anywhere outside Windows Credential Manager
  (clinic keys are stored from the Clinics tab — the Cliniko workflow
  safeguards plan's Phase 2), or an unexpected Credential Manager entry under
  `ClinikoScribe/` (one `cliniko_api_key` per clinic listed on the Clinics tab
  is expected)
- Extension behaving on non-Cliniko pages, or an extension ID mismatch
- (Cliniko workflow safeguards) the Session screen says the Chrome link is
  unavailable because the pipe name is taken while no other `scribe-app` runs,
  or a `pipe_peer` log line names an executable you did not expect (threat
  model, "The Chrome link" — a same-user squatter); a recording that ended up
  under the wrong patient or note; or a patient's name shown on another
  clinic's Cliniko tab
- (Phase 2+) any indication audio/transcripts persisted beyond their
  retention window or reached the network — since PLAN.md Phase 6 that
  includes audio found anywhere after Complete, a Past-sessions entry still
  present after Delete now or after its retention setting expired it while
  the app was running, an entry for a session that was discarded, a
  patient's name or any note text in the audit record or its CSV, or a Past
  sessions tab showing the wrong patient's name on an entry
- (PLAN.md Phase 6) the Past sessions tab says audit updates could not be
  saved, or Start is refused because the audit record could not be saved —
  not an incident on its own (recording and notes are unaffected; see
  `docs/practice/downtime-procedure.md`), but a run of them, or an audit
  key that suddenly cannot be read without a Windows password reset, is worth
  investigating as a possible tamper; a start-up warning that the data folder
  is inside OneDrive, on a network drive or in the roaming profile means
  clinical data may have left this computer — assess it as below
- (Cliniko draft write) a draft written into the wrong Cliniko note or the
  wrong patient's note; text in a Cliniko note that nobody's "Write draft to
  Cliniko" click put there; text already in a Cliniko note — typed by you, or
  the template's starting prompts — changed or removed by a write, or the
  app's text added twice to one question by one recording (outside the named
  residues: an edit saved in the moment between the write's check and its
  request, or from a Cliniko editor that was already open — threat model,
  THE DRAFT WRITE); or a note finalised, created or moved by the app
- Any network connection from `scribe-host`, or from `scribe-app` to anything
  other than `api.<shard>.cliniko.com:443`, or from `scribe-app` at startup or
  while idle with no practitioner action, no Cliniko note open in Chrome and
  no linked recording in progress (the offline contract: no connection
  except Cliniko's API, and none at startup or idle; a note open in Chrome is
  verified when its report arrives, and a linked recording's own note is
  re-checked whenever the Chrome link reconnects); or any write to Cliniko
  (a `PATCH`) that no "Write draft to Cliniko" click started
- (Pilot) a clinical-safety incident: a wrong-side, wrong-dose or
  negation-flipped item, or patient speculation in a clinician-owned section,
  that survived review into a draft or a finalised Cliniko note; or a shadow
  recording's note found on the clipboard or in a Cliniko note (shadow mode
  refuses Copy and Write for it — threat model, "The pilot"). Each is ALSO a
  `high` finding in the pilot's findings register (below)

## Clinical-safety incidents and the pilot findings register

While the pilot runs (`docs/pilot/`), every incident above that touches what
a note says, or which patient or note it reached, is entered in the findings
register, `docs/pilot/findings-register.md`, as a `high` finding — category
`wrong-side`, `wrong-dose`, `negation-flipped`, `patient-speculation`,
`cross-patient`, `privacy` or `custody` — and keeps its id (`F-…`) in your own
incident notes, so the two records point at each other. The register is in the
public repository: its row holds no name, nothing said or written, no Cliniko
id and no session id (the register's own rule); the evidence below stays
where this process keeps it. Act first — correct the note in Cliniko and
follow the steps below — then enter the finding. The clinic's exit gate
(`docs/pilot/exit-gate.md`) stays closed while any `high` finding is `open`.

## Immediate steps

1. **Stop the software.** Close Chrome (kills the host); export the audit
   record first if `scribe-app` is still open (step 4), then close it.
2. **Disconnect the channel:** remove/disable the unpacked extension in
   `chrome://extensions`. For a developer build (a source checkout) also run
   `scripts/register-native-host.py --unregister` from a normal terminal.
   For the installed app, uninstalling it (Windows Settings > Apps) removes
   its Chrome link and keeps the data folder; do that only after step 4's
   evidence is copied, and keep the installer you used.
3. **Revoke secrets (once clinic keys are stored):** regenerate the affected clinic's Cliniko
   API key(s) in Cliniko itself, then delete the local entries from Windows
   Credential Manager.
4. **Preserve evidence:** copy `%LOCALAPPDATA%\ClinikoScribe\logs\` somewhere
   safe BEFORE reinstalling anything; note the time and what you observed.
   Since PLAN.md Phase 6 also export the audit record (Past sessions tab,
   "Export audit record (CSV)") — it is the durable, content-free account of
   every session's consent, links, write outcome and deletion. Export it
   BEFORE closing `scribe-app` if it is still open. Reopening it (with Chrome
   closed, recording nothing, closing it after) runs the start-up sweeps
   BEFORE the window shows: the audit month prune, the 24 h expiry of every
   unprotected session (with its `write.enc`) and the Past-sessions retention
   sweep — under the "7 years" setting (the only one shorter than "Until I
   delete them" since the 7-year minimum, 2026-10-02) that deletes the
   incident's Past-sessions entry only once it is 7 years old, or sooner if
   the clock was jumped forward. If that entry or session matters, copy the whole
   `%LOCALAPPDATA%\ClinikoScribe\` folder aside as evidence before reopening
   — for a developer build, `%LOCALAPPDATA%\ClinikoScribe-dev\`, whose
   sessions, Past sessions and audit record are its own —
   (on this machine, under this account; a `models\` folder, static program
   data of several GiB, can be left out — the installed app keeps its models
   in its install folder instead; the app never reads the copy). The copy is
   NOT all encrypted: beside the encrypted stores (`sessions\`,
   `past_sessions\` entries, `audit\`, `profile\`, `style\`) it holds
   plaintext files — the logs, `clinics.json` (ids and the contact email),
   everything under `config\` (the clinician config, the learned phrases and
   rules with their sidecars, `practitioner_settings.json`,
   `past_sessions.json`), `app.lock` and the registration files — so keep it
   as carefully as the original and delete it when the incident is closed.
   Do not move or delete `audit\`, `audit.unreadable-…\` or
   `past_sessions\`: their keys are bound to this Windows account and
   machine, so a copy elsewhere cannot be read, and an administrator's reset
   of this account's password makes them unreadable here too.

**A draft written into the wrong note or patient** (Cliniko draft write):
1. In Cliniko, open that note and delete the written text — or archive the
   note — BEFORE anyone finalises it; the app never finalises a note, so a
   wrongly written draft stays editable until a person finalises it. The
   write ADDS text: in a question that already held text, the app's text
   sits below it after one empty line, so delete only that added part and
   keep what was there before.
2. Do NOT press Complete for that recording in the app yet: Complete after a
   written draft destroys the session — its audio and the write's record
   (`write.enc`, with its per-question digests) — keeping only the
   transcript and notes in Past sessions and the outcome in the audit row.
   Leave it on the Transcript screen or in the Unreviewed list, and note its
   time — once the app is closed it lasts only until the 24 h expiry, run at
   the next start-up (Immediate steps, step 4).
3. Evidence: Cliniko's own history of the note (who changed it and when);
   while the session still exists, the session's `write.enc` (the attempt,
   its times and outcome, and digests of each question's answer as read and
   as expected after the write; ids and digests only, no note text) under
   `%LOCALAPPDATA%\ClinikoScribe\sessions\`, which dies with its session (at
   Complete, Discard or the 24 h expiry); and — durable since 2026-10-01
   (PLAN.md Phase 6) — the session's AUDIT ROW, kept 7 years: the consent's
   time and text version, whether the recording was linked and how it was
   verified, the clinic, practitioner, user, booking and treatment-note ids it
   was linked to, the models, the write's attempts, last outcome, last
   refusal code and written-at, and what was deleted when. Export it from the
   Past sessions tab ("Export audit record (CSV)"); the CSV is not encrypted
   — keep it with the incident evidence and delete it when done. The
   session's Past-sessions entry, once completed, holds the transcript and
   notes as they were saved.
4. Assess how the note was chosen — the recording is linked to the note it
   was started from in Chrome, and the write re-reads that same note — and
   whether the wrong patient's data was disclosed (Assess, below).

## Assess

- Compare tripwire-logged paths against the expected ones (the installed
  app: `C:\Program Files\ClinikoScribe`; a developer build: the repo's venv
  and `%LOCALAPPDATA%\ClinikoScribe-dev`); inspect the registry keys (HKCU
  and HKLM), manifest, and launcher contents.
- For the installed app, `icacls "C:\Program Files\ClinikoScribe"` should
  show standard users with read and execute only; compare `Get-FileHash` of
  the installer you used with `docs/release/pilot-builds.md`.
- Check `git status` / `git log` for unexpected repo modifications.
- If clinical data may have been exposed (Phase 2+), treat it as a notifiable
  privacy matter: assess against the Australian Privacy Act's Notifiable Data
  Breaches scheme and seek advice — do not self-clear serious breaches.

## Recover

1. Rebuild trust bottom-up on a machine you trust. The installed app:
   download the build of record again, check it (`gh attestation verify` and
   `Get-FileHash` against `SHA256SUMS.txt` and `docs/release/pilot-builds.md`),
   reinstall it with the model pack beside it, reload the extension from the
   install folder, and confirm the Status tab names this computer's Chrome
   link with no per-user warning. A developer build: fresh `git pull` from
   GitHub, fresh venv, `pip install -e desktop`, re-run
   `scripts/register-native-host.py`, reload the dev extension. Then confirm the
   Step-12 gate checks (the badge shows **OK** with the app running, self-test passes, and —
   with Chrome closed, so no Cliniko note report arrives, and no practitioner
   action such as a Validate or a "Write draft to Cliniko" — `netstat` shows
   no connection from either desktop process while the app is idle; a note
   open in Chrome is verified with Cliniko when its report arrives, which is
   expected).
2. Re-enter secrets only after the machine is trusted again.
3. Record what happened and what changed in `CHANGELOG.md` (Security) and,
   if it revealed a systemic gap, add it to the threat model.
