# Retention Schedule (Phase 1)

What the software keeps, where, for how long, and how it is destroyed.
Phase 1 stores no clinical data; this schedule covers everything that exists
today and pre-commits the rules later phases must honour.

| Data | Location | Retention | Destruction |
|---|---|---|---|
| Operational logs (`scribe-host.log`, `scribe-app.log`) | `%LOCALAPPDATA%\ClinikoScribe\logs\` | Rolling: 1 MB per file × 3 rotated backups (~4 MB ceiling per process) | Oldest backup overwritten automatically by rotation; whole directory deletable at any time without affecting function |
| Log content | (same) | Whitelisted metadata only — never payloads, nonces, audio, transcripts, or clinical content (structurally enforced + tripwire-tested) | n/a — excluded at write time |
| Self-test credential (`ClinikoScribe/test` / `probe`) | Windows Credential Manager | Seconds (created and deleted within the self-test / test run) | `keyring.delete_password`; idempotent |
| Session encryption keys | Process memory only | Lifetime of the session object | `destroy()` zeroes the bytearray and drops the key; ciphertext becomes unrecoverable (best-effort memory scrubbing — residual documented in the threat model) |
| Encrypted test payloads | Process memory only | Transient (never persisted in Phase 1) | Freed with the process; unrecoverable after key destruction |
| Registration artifacts (host manifest + HKCU key; host exe lives in the venv) | `scripts/` + `HKCU\Software\Google\Chrome\NativeMessagingHosts\` | Until unregistered | `scripts/register-native-host.py --unregister` removes both |
| Extension identity (`key.pem`) | `extension/key.pem` (gitignored) | Indefinite — losing it changes the extension ID and breaks registration | Manual; deliberate decision only |

## Pre-committed rules for later phases (from PLAN.md)

- **Audio / transcripts (Phase 2+):** encrypted at rest with per-session
  keys; cryptographically deleted immediately on successful Cliniko
  write-back; failed/unresolved sessions expire within **24 hours**.
- **Audit records (Phase 6):** minimal metadata only (consent timestamp,
  user, clinic, booking/note IDs, model version, write result, deletion
  result) — never transcript or audio content.
- **Backup exclusion (Phase 6):** temporary data excluded from OneDrive,
  roaming profiles, crash reporting, and ordinary backups. Until then, note
  that `%LOCALAPPDATA%` is normally outside OneDrive's default sync scope.
