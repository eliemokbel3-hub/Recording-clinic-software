# Threat Model (Phase 1)

Scope: the implemented security foundation — extension shell, native-messaging
host, registration chain, logging, credential/session-crypto foundations.
Phase 1 handles no clinical data, so consequences today are limited to the
control channel and test data; this model exists to make the boundaries
honest BEFORE clinical data arrives.

## Trust boundaries

1. **Chrome ↔ native host (stdio pipe).**
   - Chrome enforces that only the extension pinned in `allowed_origins`
     (`chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`) can launch the
     registered host.
   - The host independently verifies the origin argv and refuses to enter
     protocol mode without it (exit before reading stdin).
   - **The session nonce is a session/correlation identifier, NOT
     authentication.** Any process that can reach the host's stdio already
     sees the nonce in `hello_ack`. It exists to detect mixed/stale sessions
     (wrong-nonce → disconnect), nothing more. No message-level cryptography
     is used on this pipe — deliberately: see "the same-user attacker" below.

2. **The same-user attacker (ACCEPTED RESIDUAL RISK).**
   Malware running as the logged-in Windows user owns both endpoints. It can:
   - repoint `HKCU\...\NativeMessagingHosts\com.scribe.cliniko_host` at its
     own binary (registration hijack);
   - replace or edit the host manifest or the installed `scribe-host.exe` in
     `%LOCALAPPDATA%\ClinikoScribe\` (both user-writable);
   - modify the venv's interpreter or site-packages (code hijack through the
     host executable);
   - read process memory, including session keys and — in later phases —
     Credential Manager secrets accessible to the user session.
   No extension-side or pipe-side control changes this; message-level crypto
   would be theater against an attacker who owns both endpoints. **Cheap
   tripwire in place:** the host logs its resolved executable, module, cwd,
   registry-resolved manifest path, and the manifest's host-executable path at
   every startup, so a hijacked chain is visible in the log history. **Real
   mitigation** is Phase 7 packaging/signing plus normal OS hygiene
   (up-to-date OS, AV, no untrusted software in the clinic user session).

3. **Extension identity.** The pinned manifest `key` gives ID *stability*,
   not secrecy — for an unpacked extension the public key is visible by
   design. `key.pem` is gitignored; losing it means a new ID and mandatory
   re-registration. The Chrome Web Store will assign a different ID at
   Phase-7 publication (allowed_origins must be updated then).

4. **Protocol robustness (untrusted peer input).** The host treats every
   frame as untrusted: length prefix bounded at 1 MB and rejected WITHOUT
   allocation when oversized, UTF-8/JSON validated, envelope schema enforced
   (unknown fields, explicit nulls, nonce presence rules, version floor),
   typed errors + disconnect on every violation, and broken-pipe-safe writes.
   This is the same posture Phase 3 will need when the *transcript* becomes
   untrusted input to the note model.

## Data-at-rest residual risks

- **Session-key zeroization is best-effort (documented residual, LOW-009).**
  `SessionCrypto.destroy()` zeroes its `bytearray` and drops the reference,
  after which decryption fails — the functional guarantee holds. However,
  immutable `bytes` copies of key material (the `os.urandom` return and the
  per-operation copies handed to the AESGCM object) are freed by Python's
  allocator, not scrubbed; fragments may persist in process memory until
  reuse. Against the same-user attacker this is subsumed by boundary 2; a
  memory-scraping attacker with user privileges wins regardless. Accepted
  for the CPython + `cryptography` stack; revisit only if the threat model
  gains a stronger-than-same-user memory adversary.
- **Log files** contain whitelisted metadata only (structural enforcement +
  tripwire, tested including the pydantic-repr misuse case). Paths logged by
  the startup tripwire are not sensitive.
- **Credential Manager** entries are protected by Windows at user-session
  granularity — same-user access is by design (the host must read keys
  unattended in Phase 4).

## Out of scope for Phase 1 (tracked in PLAN.md phases)

Consent workflow and recording indicators (Phase 5), transcript
prompt-injection handling (Phase 3), audio-at-rest encryption and recovery
windows (Phase 2), OneDrive/backup exclusions and audit records (Phase 6),
packaging/signing (Phase 7).

## Review triggers

Re-review this model when: the named-pipe host↔app channel lands (Phase 2);
real Cliniko keys are first stored (Phase 4); any component starts handling
audio or transcripts (Phase 2/3); or the software is installed on the second
clinic machine (Phase 7).
