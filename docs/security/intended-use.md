# Intended-Use Statement

**Product:** Privacy-First Cliniko Clinical Scribe (Phase 1 covers the security
foundation only; no clinical features exist yet).

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
  machine. There is no cloud fallback, silent or otherwise.
- **Not a system of record.** Cliniko remains the permanent record; this
  software retains no clinical data after successful write-back.

## Regulatory posture

Designed to be operable consistently with Ahpra/National Board guidance and
Australian privacy law, but it is **not** "Ahpra approved" and must never be
described that way. Independent privacy, legal, clinical-safety, and TGA-scope
review is required before any deployment beyond the developing practitioner
(see `PLAN.md`, Assumptions and commercial path).

## Phase 1 scope note

As of this document's writing, the implemented system is the security
foundation only: Chrome extension shell, native-messaging host, credential and
session-crypto foundations, and this documentation set. It handles **no
clinical data, no audio, and no real Cliniko API keys**.
