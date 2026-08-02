# Retention Schedule (Phases 1–2)

What the software keeps, where, for how long, and how it is destroyed.
Since Phase 2 the desktop app stores clinical data (audio, transcripts) —
always encrypted at rest, always bounded by the 24-hour rule below.

| Data | Location | Retention | Destruction |
|---|---|---|---|
| Operational logs (`scribe-host.log`, `scribe-app.log`) | `%LOCALAPPDATA%\ClinikoScribe\logs\` | Rolling: 1 MB per file × 3 rotated backups (~4 MB ceiling per process) | Oldest backup overwritten automatically by rotation; whole directory deletable at any time without affecting function |
| Log content | (same) | Whitelisted metadata only — never payloads, nonces, audio, transcripts, or clinical content (structurally enforced + tripwire-tested) | n/a — excluded at write time |
| Self-test credential (`ClinikoScribe/test` / `probe`) | Windows Credential Manager | Seconds (created and deleted within the self-test / test run) | `keyring.delete_password`; idempotent |
| Session encryption keys (unwrapped) | Process memory only — but see the `key.dpapi` row: since Phase 2 a DPAPI-wrapped copy persists on disk during the active/recovery window | Lifetime of the session object | `destroy()` zeroes the bytearray and drops the key; ciphertext becomes unrecoverable (best-effort memory scrubbing — residual documented in the threat model) |
| Encrypted test payloads | Process memory only | Transient (never persisted in Phase 1) | Freed with the process; unrecoverable after key destruction |
| Registration artifacts (host manifest + copied `scribe-host.exe` + HKCU key) | `%LOCALAPPDATA%\ClinikoScribe\` + `HKCU\Software\Google\Chrome\NativeMessagingHosts\` | Until unregistered | `scripts/register-native-host.py --unregister` removes all three |
| Extension identity (`key.pem`) | `extension/key.pem` (gitignored) | Indefinite — losing it changes the extension ID and breaks registration | Manual; deliberate decision only |
| Encrypted consultation audio (`audio.enc`) | `%LOCALAPPDATA%\ClinikoScribe\sessions\<id>\` | Session lifetime; recoverable after a crash for at most **24 h** from session creation | Unreadable the moment `key.dpapi` is deleted (cryptographic deletion); the store itself is removed on Discard and garbage-collected by the sweep once keyless |
| DPAPI-wrapped session key (`key.dpapi`) | beside the store, `sessions\<id>\` | Until Complete, Discard, or 24 h expiry — whichever first | Complete: fsync transcript → verify decrypt round-trip → delete key. Discard: key deleted FIRST, then best-effort store removal. Expiry: sweep destroys custody then the store. Plain NTFS unlink — not anti-forensic; residual accepted at the same-user boundary (threat model) |
| Encrypted transcript (`transcript.enc`) | `sessions\<id>\` | Same bound as the audio: the session sits `queued` after transcription until the explicit Complete/Discard, capped by the 24 h rule | Same key custody — undecryptable after key deletion; removed with the store |
| In-memory plaintext (capture buffers, decrypted PCM, transcript objects) | Process memory only | Transient — dropped per chunk/segment during processing; task references released after Complete/Discard | Freed by the process; best-effort scrubbing residual documented in the threat model (LOW-009) |
| ML model cache (silero ~2 MiB; `whisper\small` ~465 MiB; ~3.0 GiB with all four benchmark candidates) | `%LOCALAPPDATA%\ClinikoScribe\models\` | Indefinite — static program data, NO clinical content | Manual delete at any time; re-created by `scripts/setup-models.py` (run by the user, setup-time network only) |

## The 24-hour rule (Phase 2, enforced by code)

- Every session store is destroyed (key custody first) at **24 h** from
  creation unless the session is live in `recording`/`paused`/`processing`.
- Enforcement: a sweep at every app start (before the recovery screen lists
  anything) + a 15-minute periodic sweep while the app runs + an age filter
  on the recovery listing itself.
- Accepted residual — sweep granularity: while the app is running, worst-case
  retention overshoot is ≤ ~15 min past the 24 h cap; while the app is
  closed, expiry executes at the next launch (nothing can decrypt the store
  in the meantime without the user's DPAPI context).
- Timestamp handling is fail-safe: untrusted candidates (non-finite, or
  more than the clock-skew tolerance in the future) are discarded and can
  never extend retention — age is computed from the earliest TRUSTED
  candidate. If candidates exist but none is trusted, the sweep fails
  CLOSED and expires the store; if no candidate is readable at all
  (transient I/O trouble), the store is kept for that sweep and retried
  next cycle — transient filesystem errors must never trigger
  cryptographic deletion. The rule lives in exactly one place
  (`session_store.trusted_timestamps`), shared by the sweep and the
  recovery listing so the two can never disagree.
- Clock-skew tolerance (`CLOCK_SKEW_TOLERANCE`, 5 s): filesystem mtimes can
  read marginally AHEAD of a later `time.time()` — Windows' wall clock is
  coarse (~15.6 ms on Python ≤ 3.12) while NTFS records mtimes at 100 ns,
  and FAT-family volumes round mtimes up to a 2 s boundary. Treating that
  as "future = untrusted" made the sweep destroy sessions it had just
  created, so stamps within the tolerance are accepted and clamped to the
  present. A stamp beyond it is a genuine clock problem and still fails
  closed. Cost: at most 5 s of extra retention in the worst case, on top of
  the sweep-granularity overshoot below.

## Pre-committed rules for later phases (from PLAN.md)

- **Cliniko write-back (Phase 4):** cryptographic deletion immediately on
  successful write-back replaces today's explicit Complete action as the
  happy-path destruction trigger; the 24 h cap stays.
- **Audit records (Phase 6):** minimal metadata only (consent timestamp,
  user, clinic, booking/note IDs, model version, write result, deletion
  result) — never transcript or audio content.
- **Backup exclusion (Phase 6):** temporary data excluded from OneDrive,
  roaming profiles, crash reporting, and ordinary backups. Until then, note
  that `%LOCALAPPDATA%` is normally outside OneDrive's default sync scope.
