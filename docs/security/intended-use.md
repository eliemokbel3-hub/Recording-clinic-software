# Intended-Use Statement

**Product:** Privacy-First Cliniko Clinical Scribe (in development; see the
current scope note at the end for what is built).

## What this software is for

A **documentation assistant** for a single practitioner across two Cliniko
clinics. When complete, it records a consultation locally (with confirmed
patient consent), transcribes and drafts a treatment note **on the local
machine**, and creates that note in Cliniko as a **draft** via the official
API. The clinician reviews and finalises every note in Cliniko.

## What this software is NOT for

- **Not clinical decision support.** It must not invent, suggest, or infer
  diagnoses, examination findings, treatments, advice, referrals,
  investigations, or plans. Unsupported template fields stay blank.
- **Not an autonomous writer.** No note is ever finalised automatically;
  `draft: true` is a hard rule (Phase 4).
- **Not a cloud service.** Audio and transcripts never leave the local
  machine, and transcription and note drafting run on it. There is no cloud
  fallback, silent or otherwise. The app's only network use is Cliniko's own
  API: read-only calls (validating a clinic's key, checking the treatment
  note a recording belongs to), and — in a later phase — creating the draft
  note there. It makes no connection at startup or while idle (see the
  threat model's "Cliniko API client" and the data-flow map, flow 18).
- **Not a system of record.** Cliniko remains the permanent record; this
  software retains no clinical data after successful write-back.

## Regulatory posture

Designed to be operable consistently with Ahpra/National Board guidance and
Australian privacy law, but it is **not** "Ahpra approved" and must never be
described that way. Independent privacy, legal, clinical-safety, and TGA-scope
review is required before any deployment beyond the developing practitioner
(see `PLAN.md`, Assumptions and commercial path).

## Current scope note (2026-09-27)

Built: the security foundation (Chrome extension shell, native-messaging host,
credential and session-crypto foundations), local recording and transcription,
the local note pipeline with clinician confirmation, the practitioner's voice
profile and learned writing style, and a read-only Cliniko API client that no
part of the app calls yet. The app therefore handles **clinical data** — audio,
transcripts and draft notes, encrypted at rest on this machine — but stores
**no real Cliniko API keys** and makes **no call to Cliniko** yet: the clinic
keys, note verification and the recording safeguards are the Cliniko workflow
safeguards plan, and writing the draft into Cliniko is the plan after it.
Until then the clinician moves a note into Cliniko by hand: since 2026-09-27
(practitioner decision) a fully ratified note can be copied from the Note tab
and pasted into the Cliniko treatment note. The copy goes through the Windows
clipboard, which is outside the app — keep Windows cloud clipboard sync off
on the clinic machine, or the copied note can leave it (threat model, Phase
3A surface 4).
