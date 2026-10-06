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
  another patient (threat model, "Cliniko API client"). It never replaces
  what its own read of the note, just before writing, finds in a question it
  fills: the text there is kept and the app's text goes below it (D15), and a
  question it cannot read refuses the write. Two named exceptions (threat
  model, THE DRAFT WRITE residues (a) and (b)): an edit saved in Cliniko in
  the moment between that read and the write is reverted by the write; and
  saving a Cliniko editor that was already open before the write overwrites
  the app's draft — which is why the app asks the clinician to reload the
  note and see the draft before pressing Complete.
- **Not a cloud service.** The app never sends audio or transcripts off the
  local machine, and transcription and note drafting run on it. There is no
  cloud fallback, silent or otherwise. What the app cannot control is other
  software on the machine: Windows Backup, Volume Shadow Copy or a sync tool
  may copy its (encrypted) data folder — it WARNS, never refuses, when that
  folder resolves into OneDrive, a network drive or the roaming profile
  (threat model, "Privacy and professional controls", residues (g) and (k);
  data-flow flow 22). The app's only network use is Cliniko's own
  API: reads (validating a clinic's key, checking the treatment note a
  recording belongs to, and, for a write, reading that note again), and the
  one draft write, which sends the clinician's reviewed note
  into that Cliniko note. It makes no connection at startup or while idle on its own:
  every call answers a practitioner action, a report from Chrome, or — for a
  linked recording still in progress — the Chrome link reconnecting. So a
  Cliniko treatment note already open in Chrome is checked when the app
  starts or the link reconnects, and a linked recording's own note is
  checked again on every reconnect even with no Cliniko tab open (see the
  threat model's "Cliniko API client" and the data-flow map, flow 18).
- **Not a system of record.** Cliniko remains the permanent record. After a
  draft is written, the clinician checks it in Chrome and presses Complete.
  Every Complete destroys the recording's audio and the session itself; since
  2026-10-01 (PLAN.md Phase 6, the privacy-professional-controls plan) it
  first keeps the transcript, the saved note (unless that Complete deletes
  it) and the note the app first showed in its most recent generation (when readable; a regeneration replaces the earlier one) — never the audio,
  and nothing for a test-provider session — in **Past sessions**, encrypted on this PC
  and this Windows login only, with no backup, for as long as the
  practitioner's retention setting says — at least 7 years: "7 years" or
  until they delete them, the default (practitioner decision 2026-10-02;
  Delete now is for a recording made in error). Past sessions is a look-back for the practitioner, not the record:
  a kept transcript becomes part of the practitioner's health record and can
  be reached by an access request or a subpoena (the tab's warning;
  `docs/practice/`), but the note the patient's care relies on is the one
  finalised in Cliniko. A content-free audit row per session (consent,
  Cliniko ids, models, the write's outcome and what was deleted — never a
  name or text) is kept 7 years. Recordings not written or completed follow
  the retention schedule (encrypted, and destroyed within the 24-hour recovery
  rule once nothing holds them open).

## In the app

Since 2026-10-01 (D14) the app states its intended use in one line at the top
of the Status tab and of the Past sessions tab: "Documentation aid, not
clinical decision support. You review and finalise every note in Cliniko."
(`ui/models.py` `INTENDED_USE_LINE`; change it together with this document).

## Regulatory posture

Designed to be operable consistently with Ahpra/National Board guidance and
Australian privacy law, but it is **not** "Ahpra approved" and must never be
described that way. Independent privacy, legal, clinical-safety, and TGA-scope
review is required before any deployment beyond the developing practitioner
(see `PLAN.md`, Assumptions and commercial path). The practice documents in
`docs/practice/` (patient information and consent, privacy information,
downtime procedure, clinician review guide) are drafts under the same
condition: each carries "needs independent privacy/legal/clinical-safety
review before use with other practitioners". The app never records consent
in Cliniko and never ticks a Cliniko consent field; its per-recording tick
records only that the practitioner confirmed consent, with the time, in the
session and its audit row.

## Current scope note (2026-10-01)

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
with an Unreviewed list, and a pause hotkey and spoken pause. And, since
2026-10-01 (PLAN.md Phase 6): the Past sessions tab and its archive, the
content-free audit record with its CSV export, the per-user crash-report
exclusions, the not-indexed data folder with a start-up location check that
warns, type-name-only crash logging, and the intended-use line.
The app therefore handles **clinical data** — audio, transcripts and draft
notes, encrypted at rest on this machine, and the kept transcripts and notes
of Past sessions — **patient names** fetched from Cliniko for display (in
memory, on the desktop and in Chrome; at rest only in each Past-sessions
entry's encrypted label), and, once
the practitioner adds them, **the clinics' Cliniko API keys**. Its calls to
Cliniko are the key checks the practitioner starts on the Clinics tab, the
checks of the treatment note a recording belongs to, and — since 2026-09-29
(PLAN.md Phase 4, the cliniko-draft-write plan; tested against clinic 1's
template — clinic 2's template is unverified until its own test write, so
there the write-time template match is the only check) — the draft write:
after Save, "Write draft to Cliniko" on the Note tab reads the linked note
again and adds the reviewed note to its draft content. Since 2026-09-30
(practitioner decision D15) it never replaces anything already in the note:
an empty question takes the app's text, and a question that already holds
text — typed by the clinician, or the template's starting prompts — keeps it
exactly, with one empty line and the app's text below it. It is refused, by
name and with Copy still offered, when the recording is not linked, the note
is final or archived, its patient or practitioner no longer match, its
template does not match the app's template setup, or a question it would
add to holds something the app cannot read;
after a write the clinician reloads the note in Chrome and presses Complete
once the draft shows there. An edit saved in Cliniko during the moment
between the app's read and its write is lost, so the clinician does not
edit the note in Cliniko while a write runs (threat model, THE DRAFT WRITE
residue (a)).
A note can still be moved into Cliniko by hand: since 2026-09-27
(practitioner decision) a fully ratified note can be copied from the Note tab
and pasted into the Cliniko treatment note. The copy goes through the Windows
clipboard, which is outside the app. Since 2026-09-28 every copy of the note
(the Copy button, or Ctrl+C / right-click Copy on the selected note — and,
since the pilot's review round 22, the line editor's Copy and Cut while a
line is typed over) is marked so that Windows clipboard history and cloud clipboard sync leave it
out. The marks do not stop other programs reading the clipboard, and a
third-party clipboard manager may ignore them; the copy stays on the
clipboard until something else replaces it (the app never clears it); and
dragging the selected text out of the note carries no marks (it does not go
through the clipboard, and lands wherever it is dropped). So keeping Windows cloud clipboard sync off on the
clinic machine stays advised, though it is no longer the only mitigation
(threat model, Phase 3A surface 4).
