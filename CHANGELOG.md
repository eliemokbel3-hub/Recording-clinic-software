# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added
- Phase 3A note-pipeline foundations (its internal Phase 1 of 9, 2026-08-04): `note.py` with the canonical 17-section constant and an assertion-centric model that makes three unsafe states unrepresentable rather than merely validated — a `NoteProposal` cannot be placed in a `GeneratedSection`, a `transcript` assertion cannot span two source intervals, and a clinician-authored assertion without a `ConfirmationDecision` is rejected at construction; a single tokenisation source shared by autofill matching and the checker; `ExtractiveNoteProvider` (verbatim, exactly-reconstructing transcript spans) and `MockNoteModelProvider` (adversarial Axis-B behaviours for the Phase 5 safety matrix); the note leg of `complete_session`, which verifies decrypt, parse, session binding and transcript digest before key deletion and fails closed on any of them; 775 desktop tests
- Phase 2 local recording and transcription (completion gate passed 2026-08-02): encrypted session store writing every audio chunk as an AES-256-GCM record with a sealed finish footer; DPAPI-wrapped session-key custody with a 24-hour crash-recovery window, ordered deletion, and an expiry sweep that protects live sessions; microphone capture at 16 kHz mono with idle level monitoring, device-loss and overflow routed to a recoverable failed state; session controller with race-safe start/pause/resume/finish/discard/complete; fully local transcription on faster-whisper `medium` with clinical vocabulary priming, packed ~30-second windows, word timestamps, uncertainty marks on low-confidence words, numbers and names, and 2-speaker labels; silero-VAD segmentation; one-time model setup script as the only sanctioned network step; hardware benchmark with report panel; multi-screen desktop UI (microphone, session, recovery, transcript review); single-instance guard; extended no-network proof covering capture, transcription, model load, and a sockets-stubbed-to-fail run; end-to-end crash-recovery simulation; 537 desktop tests
- Phase 1 security foundation (gate passed 2026-07-26): Chrome MV3 extension shell with pinned identity and Cliniko-only permissions; Windows native-messaging host with authenticated handshake, binary framing, and typed protocol errors; fixture-canonical message protocol mirrored in TypeScript and Python; secure-storage foundation (Windows Credential Manager + AES-256-GCM session crypto with cryptographic deletion); structurally-enforced no-clinical-data logging; native-host registration tooling (`scripts/register-native-host.py`); minimal desktop status app with self-test; five governing security documents in `docs/security/`; 108 automated tests including a no-network-sockets integration proof

### Changed
-

### Fixed
-

### Removed
-

### Security
- Closed a clinical-content-in-logs gap in the payload tripwire (found by cross-family peer review, 2026-08-04). The filter scanned only `record.getMessage()`, but handler filters run *before* the formatter appends exception and stack rendering — so a routine `logger.exception(...)` around note construction could persist note text to the plaintext rotating log, and the module docstring claimed protection it did not provide. The filter now scans every channel `logging.Formatter` emits: message, pre-cached `exc_text`, the exact `exc_info` tuple, `stack_info`, and the remaining interpolated format fields. Four consecutive review rounds were needed because each fix was narrower than the defect class, so the scanned field list is now **derived from `LOG_FORMAT`** rather than hand-maintained — adding a field to the format scans it automatically. The docstring now states the limit it cannot cover (bare clinical text carrying no registered signature; `log_event`'s whitelist remains the primary control)
