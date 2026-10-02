# Privacy information — AI-assisted note-taking with Clinic Scribe

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); the state notes cover every state and territory the research looked at.
> See the [practice documents README](README.md) for the sources and the open questions.

Draft 1 (2026-10-01). Text for the practice's privacy policy and collection notice,
describing what Clinic Scribe does with patients' information. Fill in the bracketed
parts; keep it in step with the [patient information](patient-information-and-consent.md)
(`patient-info-v1`).

---

## What we collect when we use Clinic Scribe

With your consent, your practitioner may use **Clinic Scribe**, a program on their own
computer, to help write the notes of your appointment. It collects:

- **an audio recording** of the appointment, while it is in progress;
- **a transcript** — the conversation turned into text;
- **a draft note** made from the transcript, which your practitioner checks, corrects and
  saves;
- **your name**, as shown in the practice's Cliniko records system, so the program can
  show your practitioner which appointment it is working on and label what it keeps;
- **a record that a recording happened**: when consent was confirmed, which Cliniko
  appointment and note it belonged to (by Cliniko's reference numbers), which versions of
  the program's speech and note software were used, whether the note was placed in
  Cliniko, and what was later deleted. This record holds **no name and nothing that was
  said**.

## How we use it

Only to write the clinical notes of your appointment. The program does not diagnose,
suggest treatment or make decisions about your care, and your practitioner reviews and
finalises every note. No AI model is trained on your information. If your practitioner
turns it on, the program learns short phrases from lines **your practitioner** adds or
moves in a note, so that later notes are filed under the right headings, and shorthand
from wording your practitioner types over a note line — never from anything you said.
An automatic check looks at the shape of words, not their meaning: a phrase taken from
what your practitioner said is refused if it looks like it contains a name, a number, a
date or a medicine name, but wording your practitioner types is checked only for
numbers, dates and medicine names, so keeping patient names out of their own shorthand
is up to your practitioner. The check cannot guarantee that nothing identifying is ever
kept. It can also learn your practitioner's writing style from past notes they choose to
give it; the example sentences it keeps pass the same check unchanged and are shown to
your practitioner first. **[Reviewer: confirm this use of past notes is covered by the
practice's existing collection notice.]**

## Where it goes

- The recording, transcript and draft note are processed **on your practitioner's
  computer**. The program does **not send them to any cloud or online AI service**.
- The program connects only to **Cliniko**, the practice's clinical records system: to
  check which appointment note it is working on, and — when your practitioner chooses —
  to place the checked note into that note in Cliniko as a draft, which your practitioner
  then finalises. Cliniko is the practice's permanent clinical record. **[Practice: link
  to or name Cliniko's own privacy and data-hosting information.]**
- The program itself sends nothing anywhere else. Windows and other software on the
  computer are a separate matter, and the program's protections there depend on it
  being set up correctly: once set up, Windows does not collect crash reports about it,
  and it asks Windows not to index the contents of its folder. Once installed, it also
  asks Windows backup tools to leave out recordings in progress and its logs; some tools
  ignore that request, and it never covers the kept transcripts and notes. It cannot
  stop backup or sync software copying its folder. If crash reports are not excluded, or its folder is
  somewhere that could be copied off the computer (such as OneDrive or a network drive),
  it **warns** your practitioner but keeps working — the practitioner must fix the cause.
  **[Practice: confirm the computer's backup and sync settings.]**

## How it is protected

- Everything the program keeps about an appointment — the recording while it exists,
  the transcript, the notes and the record that a recording happened — is **encrypted**,
  with keys that only your practitioner's Windows login on that computer can unlock. Each
  recording, and each kept past session, has its own key, so one can be deleted without
  affecting the others. (The short phrases your practitioner's notes teach it, described
  above, are kept as your practitioner's own plain-text settings on the same computer.)
- **[Practice: describe your computer's own protections — for example full-disk
  encryption (BitLocker), a password-protected Windows login, screen lock, and who else
  can use the computer.]**
- The program cannot protect against software running under your practitioner's own
  Windows login, so the computer must be kept free of untrusted software.

## How long it is kept

| What | How long |
|---|---|
| Audio recording | **Not kept.** Destroyed when the note is finished or the recording is discarded. If the program is interrupted, the encrypted recording is kept for up to 24 hours so the note can be finished, and deleted the next time the program runs after that. |
| Transcript, the draft the program made, and the saved note ("Past sessions") | On your practitioner's computer, encrypted, for at least 7 years, like other health records — in Victoria, NSW and the ACT the law requires at least 7 years, or until you turn 25 if you were a child (the Acts in the row below); elsewhere the Australian Privacy Principles apply (APP 11.2): **[Practice: your setting — the program offers 7 years, or until deleted; its default is until deleted. Choose until deleted for a patient who was a child.]** A kept transcript is deleted early only when the recording was made in error (the wrong patient, a test, or recorded without consent). |
| Record that a recording happened | 7 years. |
| Your clinical record in Cliniko | As the practice keeps all clinical records — in Victoria, NSW and the ACT at least 7 years after your last visit, or until you turn 25 if you were a child (Health Records Act 2001 (Vic); Health Records and Information Privacy Act 2002 (NSW); Health Records (Privacy and Access) Act 1997 (ACT)). Elsewhere, the Australian Privacy Principles apply (APP 11.2). |

**About kept transcripts.** A kept transcript becomes part of the health information the
practice holds about you. The program stores it on one computer only and makes **no
backup**: if that
computer or its Windows login is lost, the transcript is lost too (your clinical record in
Cliniko is not affected). If the practice keeps transcripts "until deleted", they build up
on that computer until someone deletes them. The practice keeps a kept transcript for at
least 7 years, as it keeps other health records. **[Reviewer: confirm the 7-year minimum
and the early deletion of a recording made in error — see the README.]**

## Your rights

- **Access.** You can ask to see the health information the practice holds about you,
  including a kept transcript (APP 12). **[Practice: how to ask, and how long it
  takes.]**
- **Correction.** You can ask us to correct information about you. **[Practice: how.]**
  **[Reviewer: the correction right, and any state Act's own access rules, were not part
  of the 2026-10-01 research — confirm the wording.]**
- **Courts.** A kept transcript, like any part of a health record, could be requested by
  a court, for example by subpoena.
- **Saying no.** You can decline AI-assisted note-taking at any appointment, or ask your
  practitioner to stop it, with no effect on your care.

## If something goes wrong

If we believe your information may have been seen by someone who should not have seen
it, we will assess it under the Notifiable Data Breaches scheme of the Privacy Act and tell
you if the law requires it. **[Practice: your data-breach response contact.]**
**[Reviewer: the Notifiable Data Breaches scheme was not part of the 2026-10-01
research — confirm the wording.]**

## Questions and complaints

**[Practice: privacy contact — name, phone, email. How to complain, and the regulator you
may complain to if you are not satisfied with our response.]**

---

### For the practice: what this document relies on

- The app's behaviour as built on 2026-10-01 (the retention choices as changed on
  2026-10-02): no audio kept; transcript and notes kept per the Past-sessions setting —
  7 years or until deleted, with no shorter setting (Delete now is for a recording made in
  error); the content-free audit record kept 7 years; the only
  network use is Cliniko's own API.
- The app's own warning beside the retention setting (it cites the same Acts, APP 11.2
  and APP 12) — change both together.
- The audit record can be exported as a CSV for the practice's own records. The CSV holds
  no names or text, but it holds Cliniko reference numbers that identify appointments to
  anyone with access to the practice's Cliniko account, and it is **not encrypted**:
  treat it as personal information, keep it somewhere safe and delete it when done.
