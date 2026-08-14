# Retention Schedule (Phases 1–3A)

What the software keeps, where, for how long, and how it is destroyed.
Since Phase 2 the desktop app stores clinical data (audio, transcripts, and —
since Phase 3A — the composed note) — always encrypted at rest under
per-session keys; UNPROTECTED recovery stores are bounded by the 24-hour rule
below, while a live or under-review session is sweep-exempt from it (see the
rule). Phase 3A also adds
clinician-authored config files (plaintext, INTENDED to hold non-patient
boilerplate, deliberately outside the 24-hour rule).

| Data | Location | Retention | Destruction |
|---|---|---|---|
| Operational logs (`scribe-host.log`, `scribe-app.log`) | `%LOCALAPPDATA%\ClinikoScribe\logs\` | Rolling: 1 MB per file × 3 rotated backups (~4 MB ceiling per process) | Oldest backup overwritten automatically by rotation; whole directory deletable at any time without affecting function |
| Log content | (same) | Whitelisted metadata only — never payloads, nonces, audio, transcripts, or clinical content (structurally enforced + tripwire-tested) | n/a — excluded at write time |
| Self-test credential (`ClinikoScribe/test` / `probe`) | Windows Credential Manager | Seconds (created and deleted within the self-test / test run) | `keyring.delete_password`; idempotent |
| Session encryption keys (unwrapped) | Process memory only — but see the `key.dpapi` row: since Phase 2 a DPAPI-wrapped copy persists on disk during the active/recovery window | Lifetime of the session object | `destroy()` zeroes the bytearray and drops the key; ciphertext becomes unrecoverable (best-effort memory scrubbing — residual documented in the threat model) |
| Encrypted test payloads | Process memory only | Transient (never persisted in Phase 1) | Freed with the process; unrecoverable after key destruction |
| Registration artifacts (host manifest + copied `scribe-host.exe` + HKCU key) | `%LOCALAPPDATA%\ClinikoScribe\` + `HKCU\Software\Google\Chrome\NativeMessagingHosts\` | Until unregistered | `scripts/register-native-host.py --unregister` removes all three |
| Extension identity (`key.pem`) | `extension/key.pem` (gitignored) | Indefinite — losing it changes the extension ID and breaks registration | Manual; deliberate decision only |
| Encrypted consultation audio (`audio.enc`) | `%LOCALAPPDATA%\ClinikoScribe\sessions\<id>\` | Session lifetime; as an UNPROTECTED recovery store, recoverable after a crash until expiry — EXPIRY-ELIGIBLE at **24 h** from session creation, then destroyed by the next successful sweep (see the 24-hour rule below) — and sweep-EXEMPT while the session is live or its `queued` transcript/note is under review | Unreadable the moment `key.dpapi` is deleted (cryptographic deletion); the store itself is removed on Discard and garbage-collected by the sweep once keyless |
| DPAPI-wrapped session key (`key.dpapi`) | beside the store, `sessions\<id>\` | Until Complete, Discard, or — for an UNPROTECTED recovery store — expiry (eligible at 24 h, destroyed by the next successful sweep), whichever first (a protected live/under-review session is sweep-exempt, so its key is not destroyed at the 24 h mark) | Complete: fsync transcript → verify decrypt round-trip → delete key. Discard: key deleted FIRST, then best-effort store removal. Expiry: sweep destroys custody then the store. Plain NTFS unlink — not anti-forensic; residual accepted at the same-user boundary (threat model) |
| Encrypted transcript (`transcript.enc`) | `sessions\<id>\` | Same bound as the audio: the session sits `queued` after transcription until the explicit Complete/Discard; sweep-EXEMPT while it is the controller's live/queued session under review, and subject to the 24 h expiry rule (eligible at 24 h, destroyed by the next successful sweep) only as an UNPROTECTED recovery store (see the 24-hour rule below) | Same key custody — undecryptable after key deletion; removed with the store |
| Encrypted note artifact (`note.enc`, Phase 3A) | `sessions\<id>\` | Same bound as the audio/transcript — written under the SAME per-session key; sweep-EXEMPT while the session is live or its `queued` transcript/note is open for review, and subject to the 24 h expiry rule (eligible at 24 h, destroyed by the next successful sweep) only once it is an UNPROTECTED recovery store (see the 24-hour rule below) | Same key custody — undecryptable after key deletion; a stale `note.enc` is unlinked before a re-transcription writes; Complete verifies it (decrypt → parse → session binding → transcript-digest match) BEFORE key deletion; removed with the store |
| In-memory plaintext (capture buffers, decrypted PCM, transcript objects; since Phase 3A also the Note-tab review objects — the draft, its transcript document, config, and the finalised note, held by `ui/note.py` `_draft` / `_document` / `_config` / `_note`) | Process memory only | Transient during capture/processing (dropped per chunk/segment). During Phase-3A note review the transcript AND note plaintext PERSIST beside each other for the WHOLE review window (8.1 surface 3) — released only on the tab's clear / cancel-and-regenerate, a replacement generation, Complete/Discard, or process exit | Freed by the process; best-effort scrubbing residual documented in the threat model (LOW-009) |
| ML model cache (silero ~2 MiB; runtime default `whisper\medium` ~1.43 GiB; fallback `whisper\small` ~465 MiB; ~3.0 GiB with all four benchmark candidates) | `%LOCALAPPDATA%\ClinikoScribe\models\` | Indefinite — static program data, NO clinical content | Manual delete at any time; re-created by `scripts/setup-models.py` (run by the user, setup-time network only) |
| Clinician-authored config (`template_profiles.json`, `autofill_rules.json`, `prefill_templates.json`, Phase 3A) | `%LOCALAPPDATA%\ClinikoScribe\config\` | Indefinite — INTENDED as non-patient boilerplate; deliberately OUTSIDE the encrypted session store and the 24 h rule so it survives session destruction | Manual delete/edit only; the loader is read-only and never creates or deletes config. Patient data and secrets are prohibited by policy, but the loader validates only STRUCTURE (shape, length, control/format characters, atomic-claim shape) — it cannot detect semantic misuse, so any content a clinician hand-edits in is retained VERBATIM in plaintext. Feeds the note pipeline only as proposals |

## The 24-hour rule (Phase 2, enforced by code)

- Every session store becomes EXPIRY-ELIGIBLE at **24 h** from creation and is
  then destroyed (key custody first) by the next SUCCESSFUL scheduled sweep —
  UNLESS it is PROTECTED from the sweep. The protected set
  (`app.sweep_protected_ids` → `SessionController.custody_protected_ids`) is:
  a session live in `recording`/`paused`/`processing`; the controller's OWN
  session in ANY non-terminal state, INCLUDING a `queued` transcript/note held
  open for review (round 42 MED-001 — so review is never cut off by custody
  loss at the 24 h boundary); and a recovered session checked out for
  resume / Complete / Discard (PR round 18). A protected store SKIPS age
  evaluation entirely, so while a session is active or under review its
  retention is bounded by the review/session lifetime, NOT by 24 h — the 24 h
  cap governs UNPROTECTED recovery stores (a crashed or abandoned session no
  longer held by the controller or a recovery checkout). This is deliberate:
  the alternative — deleting a note's key mid-review at the 24 h mark — would
  destroy work in progress.
- Enforcement: a sweep at every app start (before the recovery screen lists
  anything) + a 15-minute periodic sweep while the app runs + an age filter
  on the recovery listing itself. All three consult the protected set above.
- Accepted residual — expiry at the next SUCCESSFUL sweep, not a hard deadline
  (UNPROTECTED stores only): an unprotected recovery store expires at the first
  scheduled sweep that RUNS SUCCESSFULLY after its 24 h mark — normally within
  about the 15-minute QTimer CADENCE while the app runs, and at next launch
  while it is closed (nothing can decrypt the store in the meantime without the
  user's DPAPI context). The 15 minutes is the intended INTERVAL, not a
  guaranteed bound: GUI-thread blocking, OS process suspension (sleep/hibernate),
  or a sweep that retains the store after a transient I/O error (it fails closed
  toward RETENTION and retries next cycle — below) can push actual expiry past
  one interval. A PROTECTED store is exempt from the cap for as long as it stays
  protected — potentially unbounded while a session stays active or under review.
- Timestamp handling is fail-safe: untrusted candidates (non-finite, or
  more than the clock-skew tolerance in the future) are discarded and can
  never extend retention — age is computed from the earliest TRUSTED
  candidate. If candidates exist but none is trusted, the sweep fails
  CLOSED and expires the store; if no candidate is readable at all
  (transient I/O trouble), the store is kept for that sweep and retried
  next cycle — transient filesystem errors must never trigger
  cryptographic deletion. The rule lives in exactly one place
  (`session_store.earliest_trusted_timestamp`), shared by the sweep and the
  recovery listing so the two can never disagree.
- Clock-skew tolerance (`CLOCK_SKEW_TOLERANCE`, 5 s): filesystem mtimes can
  read marginally AHEAD of a later `time.time()` — Windows' wall clock is
  coarse (~15.6 ms on Python ≤ 3.12) while NTFS records mtimes at 100 ns,
  and FAT-family volumes round mtimes up to a 2 s boundary. Treating that
  as "future = untrusted" made the sweep destroy sessions it had just
  created, so stamps within the tolerance are accepted and clamped to the
  present. A stamp beyond it is a genuine clock problem and still fails
  closed. Cost: at most 5 s of extra retention beyond the 24 h mark, on top of
  the cadence delay described above.

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
