# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added
- Phase 2 local recording and transcription (completion gate passed 2026-08-02): encrypted session store writing every audio chunk as an AES-256-GCM record with a sealed finish footer; DPAPI-wrapped session-key custody with a 24-hour crash-recovery window, ordered deletion, and an expiry sweep that protects live sessions; microphone capture at 16 kHz mono with idle level monitoring, device-loss and overflow routed to a recoverable failed state; session controller with race-safe start/pause/resume/finish/discard/complete; fully local transcription on faster-whisper `medium` with clinical vocabulary priming, packed ~30-second windows, word timestamps, uncertainty marks on low-confidence words, numbers and names, and 2-speaker labels; silero-VAD segmentation; one-time model setup script as the only sanctioned network step; hardware benchmark with report panel; multi-screen desktop UI (microphone, session, recovery, transcript review); single-instance guard; extended no-network proof covering capture, transcription, model load, and a sockets-stubbed-to-fail run; end-to-end crash-recovery simulation; 537 desktop tests
- Phase 1 security foundation (gate passed 2026-07-26): Chrome MV3 extension shell with pinned identity and Cliniko-only permissions; Windows native-messaging host with authenticated handshake, binary framing, and typed protocol errors; fixture-canonical message protocol mirrored in TypeScript and Python; secure-storage foundation (Windows Credential Manager + AES-256-GCM session crypto with cryptographic deletion); structurally-enforced no-clinical-data logging; native-host registration tooling (`scripts/register-native-host.py`); minimal desktop status app with self-test; five governing security documents in `docs/security/`; 108 automated tests including a no-network-sockets integration proof

### Changed
-

### Fixed
-

### Removed
-

### Security
-
