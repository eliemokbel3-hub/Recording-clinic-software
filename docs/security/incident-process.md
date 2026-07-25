# Incident Process (Phase 1)

Who: the practitioner-developer (single-user product until commercialisation).
When in doubt, stop using the software and investigate before resuming.

## What counts as an incident

- Suspected compromise of the clinic machine or Windows user account
- Unexpected change to the registration chain: the startup tripwire log
  (`host_manifest` / `host_launcher` (the host exe) / `host_start` paths in
  `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-host.log`) shows a path you did
  not set, or registration verification fails
- Any sign of payload content in log files (the tripwire also counts drops —
  a nonzero drop count means misuse of the logger somewhere)
- A Cliniko API key exposed anywhere outside Windows Credential Manager
  (Phase 4+), or an unexpected Credential Manager entry under `ClinikoScribe/`
- Extension behaving on non-Cliniko pages, or an extension ID mismatch
- (Phase 2+) any indication audio/transcripts persisted beyond their
  retention window or reached the network

## Immediate steps

1. **Stop the software.** Close Chrome (kills the host), close `scribe-app`.
2. **Disconnect the channel:** `scripts/register-native-host.py --unregister`
   and remove/disable the unpacked extension in `chrome://extensions`.
3. **Revoke secrets (Phase 4+):** regenerate the affected clinic's Cliniko
   API key(s) in Cliniko itself, then delete the local entries from Windows
   Credential Manager.
4. **Preserve evidence:** copy `%LOCALAPPDATA%\ClinikoScribe\logs\` somewhere
   safe BEFORE reinstalling anything; note the time and what you observed.

## Assess

- Compare tripwire-logged paths against the expected repo paths; inspect the
  registry key, manifest, and launcher contents.
- Check `git status` / `git log` for unexpected repo modifications.
- If clinical data may have been exposed (Phase 2+), treat it as a notifiable
  privacy matter: assess against the Australian Privacy Act's Notifiable Data
  Breaches scheme and seek advice — do not self-clear serious breaches.

## Recover

1. Rebuild trust bottom-up on a machine you trust: fresh `git pull` from
   GitHub, fresh venv, `pip install -e desktop`, re-run
   `scripts/register-native-host.py`, reload the extension, and confirm the
   Step-12 gate checks (badge connects, self-test passes, `netstat` clean).
2. Re-enter secrets only after the machine is trusted again.
3. Record what happened and what changed in `CHANGELOG.md` (Security) and,
   if it revealed a systemic gap, add it to the threat model.
