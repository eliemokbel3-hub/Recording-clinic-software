# Intended-Use Statement

**Product:** Privacy-First Cliniko Clinical Scribe (in development; see the
current scope note at the end for what is built).

## What this software is for

A **documentation assistant** for a single practitioner across two Cliniko
clinics. When complete, it records a consultation locally (with confirmed
patient consent), transcribes and drafts a treatment note **on the local
machine**, and — once the clinician has reviewed and saved it — writes it,
on the clinician's click, into the Cliniko treatment note the recording was
started from, as **draft** content, via the official API. The clinician
reviews and finalises every note in Cliniko.

## What this software is NOT for

- **Not clinical decision support.** It must not invent, suggest, or infer
  diagnoses, examination findings, treatments, advice, referrals,
  investigations, or plans. Unsupported template fields stay blank.
- **Not an autonomous writer.** No note is ever finalised automatically, and
  nothing is written to Cliniko without the clinician's click. The app's one
  write can only fill the CONTENT of an open draft treatment note: the request
  it can send has no field that finalises a note, creates one, or moves one to
  another patient (threat model, "Cliniko API client"). It refuses the write
  when its own read of the note, just before writing, finds text beyond the
  note's starting text in any question it fills; an edit saved in Cliniko in
  the moment between that read and the write, or later from a Cliniko editor
  that was already open, is the named exception (threat model, THE DRAFT
  WRITE residues (a) and (b)).
- **Not a cloud service.** Audio and transcripts never leave the local
  machine, and transcription and note drafting run on it. There is no cloud
  fallback, silent or otherwise. The app's only network use is Cliniko's own
  API: reads (validating a clinic's key, checking the treatment note a
  recording belongs to, and, for a write, reading that note and its template
  again), and the one draft write, which sends the clinician's reviewed note
  into that Cliniko note. It makes no connection at startup or while idle on its own:
  every call answers a practitioner action, a report from Chrome, or — for a
  linked recording still in progress — the Chrome link reconnecting. So a
  Cliniko treatment note already open in Chrome is checked when the app
  starts or the link reconnects, and a linked recording's own note is
  checked again on every reconnect even with no Cliniko tab open (see the
  threat model's "Cliniko API client" and the data-flow map, flow 18).
- **Not a system of record.** Cliniko remains the permanent record. After a
  draft is written, the clinician checks it in Chrome and presses Complete;
  the software then destroys that recording's data, so the draft in Cliniko is
  the only copy. Recordings not written or completed follow the retention
  schedule (encrypted, and destroyed within the 24-hour recovery rule once
  nothing holds them open).

## Regulatory posture

Designed to be operable consistently with Ahpra/National Board guidance and
Australian privacy law, but it is **not** "Ahpra approved" and must never be
described that way. Independent privacy, legal, clinical-safety, and TGA-scope
review is required before any deployment beyond the developing practitioner
(see `PLAN.md`, Assumptions and commercial path).

## Current scope note (2026-09-29)

Built: the security foundation (Chrome extension shell, native-messaging host,
credential and session-crypto foundations), local recording and transcription,
the local note pipeline with clinician confirmation, the practitioner's voice
profile and learned writing style, a Cliniko API client (reads, and one draft
write), the
Clinics tab where each clinic's API key is validated with Cliniko and stored in
Windows Credential Manager, and the Cliniko workflow safeguards (PLAN.md
Phase 5): a Chrome-linked recording starts from an open treatment note that
Cliniko verifies (or, when Cliniko cannot be reached, one marked unverified
offline), behind a per-recording consent tick, with a Chrome side panel, a
page frame and a full-page block when the patient changes; a recording
started on the desktop is not linked to a Cliniko note and cannot be written
back. A pause rule pauses a linked recording when its own tab changes note or
patient, leaves the note or closes, when another Cliniko note is focused or
the Cliniko login page shows, or when the Chrome link drops or a new client
connects — switching to a separate non-Cliniko tab does not pause it — and
any recording pauses on system sleep or when Windows locks the session —
when Windows delivers those notifications and accepted the app's
registration for them (the threat model's pause-rule residue names when it
does not). Also built: back-to-back consultations
with an Unreviewed list, and a pause hotkey and spoken pause.
The app therefore handles **clinical data** — audio, transcripts and draft
notes, encrypted at rest on this machine — **patient names** fetched from
Cliniko for display (in memory only, on the desktop and in Chrome), and, once
the practitioner adds them, **the clinics' Cliniko API keys**. Its calls to
Cliniko are the key checks the practitioner starts on the Clinics tab, the
checks of the treatment note a recording belongs to, and — since 2026-09-29
(PLAN.md Phase 4, the cliniko-draft-write plan; tested against clinic 1's
template — clinic 2's template is unverified until its own test write, so
there the write-time template match is the only check) — the draft write:
after Save, "Write draft to Cliniko" on the Note tab reads the linked note
and its template again and fills the note's draft content with the reviewed
note. It is refused, by name and with Copy still offered, when the recording
is not linked, the note is final or archived, it already holds typed text,
its patient, practitioner or template no longer match, or its template does
not match the app's template setup;
after a write the clinician reloads the note in Chrome and presses Complete
once the draft shows there. Each clinic chooses, on the Clinics tab, where
the note's untyped starting text is read from: the Cliniko template (the
default) or a file the practitioner writes (`docs/own-template-defaults.md`).
A note can still be moved into Cliniko by hand: since 2026-09-27
(practitioner decision) a fully ratified note can be copied from the Note tab
and pasted into the Cliniko treatment note. The copy goes through the Windows
clipboard, which is outside the app. Since 2026-09-28 every copy of the note
(the Copy button, or Ctrl+C / right-click Copy on the selected note) is
marked so that Windows clipboard history and cloud clipboard sync leave it
out. The marks do not stop other programs reading the clipboard, and a
third-party clipboard manager may ignore them; the copy stays on the
clipboard until something else replaces it (the app never clears it); and
dragging the selected text out of the note carries no marks (it does not go
through the clipboard, and lands wherever it is dropped). So keeping Windows cloud clipboard sync off on the
clinic machine stays advised, though it is no longer the only mitigation
(threat model, Phase 3A surface 4).
