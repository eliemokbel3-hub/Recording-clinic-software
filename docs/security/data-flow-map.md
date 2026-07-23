# Data-Flow Map (Phase 1)

Every place data lives or moves in the implemented system. Phase 1 carries
**no clinical data** — flows below carry protocol control messages and test
data only. There is **no status file** (that design was cut in plan hardening)
and **no network sockets** on either desktop process (enforced by
`desktop/tests/test_integration_no_sockets.py` and ruff import bans).

## Components

| Component | Process | Trust context |
|---|---|---|
| Chrome extension (`extension/`) | Chrome renderer/service worker | Sandboxed by Chrome; ID pinned `mbmhglgadhdohpgbmpbjnaifjagfdfid` |
| Native host (`scribe-host`) | Spawned by Chrome per connection | Runs as the logged-in Windows user |
| Status app (`scribe-app`) | Standalone PySide6 process | Runs as the logged-in Windows user |

## Flows

1. **Chrome ↔ native host (stdio, the ONLY browser transport).**
   Chrome spawns the registered launcher and connects stdin/stdout pipes.
   Framed JSON (4-byte native-order length prefix + UTF-8, ≤1 MB per frame,
   project policy both directions). Phase-1 messages: `hello`, `hello_ack`,
   `ping`, `pong`, `error`. Contains: protocol version, request IDs, a random
   per-session nonce. Contains NO secrets, NO clinical data.

2. **Host/app → log files.** `%LOCALAPPDATA%\ClinikoScribe\logs\scribe-host.log`
   and `scribe-app.log`, rotating at 1 MB with 3 backups. Content is
   structurally restricted to whitelisted metadata (event names, message
   types, versions, byte sizes, states, error codes, filesystem paths, PIDs)
   via `logging_setup.py`'s wrapper + tripwire filter. Protocol payloads and
   nonces are actively dropped if ever formatted into a record. Stdout is
   NEVER a log destination (it carries only protocol frames).

3. **Desktop → Windows Credential Manager.** Durable secrets via `keyring`,
   keyed `ClinikoScribe/<clinic_id>` + secret name. Phase 1 stores only the
   transient self-test credential (`test/probe`), deleted by the test itself.
   Real Cliniko API keys arrive in Phase 4 and live ONLY here.

4. **Session crypto (in-memory only).** AES-256-GCM keys from `os.urandom`
   exist only in process memory; `destroy()` drops the key, making anything
   encrypted under it unrecoverable. Phase 1 encrypts test payloads only;
   nothing encrypted is persisted to disk.

5. **Registration artifacts (machine-local, gitignored).**
   `scripts/com.scribe.cliniko_host.json` (host manifest) and
   `scripts/dev-host-launcher.bat`, referenced from
   `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.scribe.cliniko_host`.
   Contain paths and the pinned extension ID — no secrets.

## Explicit non-flows

- No audio, transcripts, or clinical content anywhere (Phase 2+ concerns).
- No network traffic from either desktop process (tested, not just asserted).
- No cloud AI services; no telemetry.
- No data in Chrome extension storage (plan: credentials/models/audio never
  enter extension storage).
- Log/temp locations are user-local; exclusion from OneDrive/backup sweep is
  a Phase 6 task (`PLAN.md`), noted in the retention schedule.

## Phase 2 preview (locked topology)

Recording will live in a long-lived desktop app; the Chrome-spawned host
stays a thin, stateless relay. They will connect via a user-ACL'd Windows
**named pipe** (local IPC — still zero network sockets). This map must be
updated when that flow exists.
