# Privacy information — AI-assisted note-taking with Clinic Scribe

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); the state notes cover every state and territory the research looked at.
> See the [practice documents README](README.md) for the sources and the open questions.

Draft 1 (2026-10-01; the record of a recording and "How we use it" updated 2026-10-07 for
the pilot build, approved by the practitioner the same day; the kept recording added
2026-10-08 for version 0.3.0, awaiting the practitioner's approval).
Text for the practice's privacy policy and collection notice, describing what Clinic
Scribe does with patients' information. Fill in the bracketed parts; keep it in step with
the [patient information](patient-information-and-consent.md) (`patient-info-v3`) and
[Keeping a recording to help develop the program](development-recording-consent.md)
(`development-consent-v1`).

---

## What we collect when we use Clinic Scribe

With your consent, your practitioner may use **Clinic Scribe**, a program on their own
computer, to help write the notes of your appointment. It collects:

- **an audio recording** of the appointment, held while your practitioner prepares the
  note (and, if something interrupts that, for up to 24 hours — "How long it is kept"
  below) and deleted when the note is finished or the recording is discarded; it is
  kept after the note is finished only if you separately agree in writing ("How we use
  it" below);
- **a transcript** — the conversation turned into text;
- **a draft note** made from the transcript, which your practitioner checks, corrects and
  saves;
- **your name**, as shown in the practice's Cliniko records system, so the program can
  show your practitioner which appointment it is working on and label what it keeps;
- **a record that a recording happened**: when consent was confirmed, which Cliniko
  appointment and note it belonged to (by Cliniko's reference numbers), which versions of
  the program and of its speech and note software were used, whether it was a comparison
  appointment (one where your practitioner also wrote the note the usual way and the
  program's draft was not used), whether the note was placed in Cliniko, and what was
  later deleted — and, for a recording kept with your written consent (below), that
  consent's version, when the recording was kept or deleted and how many times it was
  copied. This record
  holds **no name and nothing that was said**.

## How we use it

Only to write the clinical notes of your appointment — and, **only if you separately
agree in writing**, to keep the recording of the appointment so that your practitioner
can check and improve how the program hears and writes (see
[Keeping a recording to help develop the program](development-recording-consent.md)):
the program keeps it encrypted on your practitioner's computer (apart from a short-lived
unencrypted copy they may make there to mark who is speaking — see below), it is used
only by them, and the program never sends it anywhere (backup and sync software are
covered under "Where it goes"). For a limited number of
appointments while the program is being checked, your practitioner also compares the
program's draft with the note they wrote themselves, to check the quality of its drafts;
the scores they keep hold no name and nothing that was said. The program does not diagnose,
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
  ignore that request, and it never covers the kept transcripts, notes and recordings. It cannot
  stop backup or sync software copying its folder. If crash reports are not excluded, or its folder is
  somewhere it can recognise as able to be copied off the computer (such as OneDrive or
  a network drive — it cannot recognise every such place), it **warns** your practitioner
  but keeps working — the practitioner must fix the cause.
  **[Practice: confirm the computer's backup and sync settings.]**

## How it is protected

- Everything the program keeps about an appointment — the recording while it exists,
  the transcript, the notes and the record that a recording happened — is **encrypted**,
  with keys that only your practitioner's Windows login on that computer can unlock
  (apart from the unencrypted copy of a kept recording your practitioner may make,
  described above). Each
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
| Audio recording | **Not kept** — unless you have separately agreed in writing to it being kept to help develop the program. Otherwise destroyed when the note is finished or the recording is discarded; if the program is interrupted, the encrypted recording is kept for up to 24 hours so the note can be finished, and deleted the next time the program runs after that. A recording kept with your written consent stays, encrypted, on your practitioner's computer until they delete it; they review it at least every 12 months, and delete it the same day if you withdraw. To mark who is speaking, your practitioner may make an unencrypted copy on the same computer (the program refuses some places it can recognise — a OneDrive folder it can find, network drives and removable drives such as USB sticks — but cannot recognise every synced folder, OneDrive included, so your practitioner keeps it on the computer's own internal drive and checks it is in no synced or shared folder) and deletes it afterwards. **[Reviewer: whether a kept recording must itself be kept like a health record — in Victoria, NSW and the ACT at least 7 years, or until 25 for a child; elsewhere APP 11.2 — see the README.]** |
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
- **Withdrawing a kept recording.** If you agreed in writing to a recording being kept to
  help develop the program, you can withdraw at any time; your kept recordings are
  deleted the same day (the transcript and notes stay, as above).

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
- Since version 0.3.0 (2026-10-08): a recording may be kept, encrypted beside its past
  session, only when the practitioner has turned on "Keep recordings for development
  (written consent only)", ticked the separate written-consent box before Start and
  then Completed the recording (a discarded recording is never kept); it is kept until
  deleted (Delete recording, any time; reviewed after 12 months), its only unencrypted
  copy is one the practitioner exports to a folder the program accepts (it refuses the
  OneDrive folders Windows tells it about, network and removable drives, but not an
  external drive Windows reports as fixed or a synced folder it cannot recognise — the
  practitioner checks), and the audit
  record notes the consent's version, when the recording was kept or deleted and how
  many times it was exported. Every other recording's audio is still destroyed at Complete or Discard.
- The app's own warning beside the retention setting (it cites the same Acts, APP 11.2
  and APP 12) — change both together.
- The audit record can be exported as a CSV for the practice's own records. The CSV holds
  no names or text, but it holds Cliniko reference numbers that identify appointments to
  anyone with access to the practice's Cliniko account, and it is **not encrypted**:
  treat it as personal information, keep it somewhere safe and delete it when done.
