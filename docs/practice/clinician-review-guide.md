# Clinician review guide — checking a Clinic Scribe note

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); see the [practice documents README](README.md) for the sources, which
> cover every state and territory the research looked at.

Draft 1 (2026-10-01; the shadow-recording lines added 2026-10-07 for the pilot build,
approved by the practitioner the same day; the kept-recording line added 2026-10-08 for
version 0.3.0, awaiting the practitioner's approval). For the practitioner, before saving a note and before finalising it
in Cliniko.

**Why this matters.** Ahpra's guidance on AI in healthcare ("Meeting your professional
obligations when using AI in healthcare") makes you responsible for checking the accuracy
of any record an AI tool creates. Clinic Scribe is a **documentation aid, not clinical
decision support** — it never decides anything about care. You review and finalise every
note in Cliniko, and what you finalise is your record.

## Before you record

- Ask for consent every time (see [Patient information and consent](patient-information-and-consent.md)),
  then tick the box above Start. Record the patient's response in Cliniko yourself — the
  app never does.
- Check the side panel or the Session tab names the right patient and appointment before
  you start. A recording started on the Session tab, not from a Cliniko note, is not linked
  and can only be copied into Cliniko by hand.
- If someone else is in the room (a parent, carer, interpreter or student), the
  transcript will still show only two speakers: their words will be labelled as yours or
  the patient's. Check attribution with extra care.

## Reading the transcript

The transcript sits beside the note for the whole review. Use it as the evidence, not the
note.

- Words the speech software was unsure of — and numbers and names — are marked like
  `[word?]`. Check every mark that matters clinically against what you remember.
- The speaker labels can be wrong, especially when people talk over each other.
- If the recording was interrupted, the end may be missing.
- Something said quietly or off-microphone may be missing entirely.

## Reviewing the draft note

The app builds the note from what was said, under your template's headings, and shows
where each line came from: the transcript, something you typed, or your own pre-set text.

1. **Confirm or decline every proposed line.** Proposals are lines the app suggests from
   your own templates and shorthand. Each shows the exact words that will go in. Decline
   anything that does not apply to this patient.
2. **Read every line against the transcript.** Apart from proposals and your own
   pre-filled text (steps 1 and 3), which were not necessarily said, the app only takes
   words from the transcript — it does not invent findings — but a line can land under the wrong
   heading, miss context (for example "not" said earlier), or carry a mis-heard word.
   Move, remove or edit lines until the note says what happened.
3. **Pre-filled lines** from your own settings are marked as pre-filled. Remove any that
   are not true for this appointment; Save confirms the rest.
4. **Blocking warnings must be fixed** before you can save — for example a symptom the
   transcript negates, or a dose in clear conflict with it. **Review warnings must be
   read and acknowledged** — for example most other dose differences, a left/right
   difference, or a number, name or medicine in
   your part of the transcript that the note left out. The checks are a safety net, not
   a guarantee: they look for particular kinds of mismatch and cannot tell you the note
   is complete or correct.
5. **Writing styles.** If you use a prose style (Narrative or Own voice), the app turns
   your confirmed lines into sentences on this computer and checks each section against
   them; a section that fails the check is shown as plain lines instead, and you
   acknowledge it. Read the prose as carefully as the lines — the check is not a
   certificate that the meaning survived.
6. **Fill the gaps yourself.** Headings the app had nothing for stay empty. Beyond your
   own proposals and pre-filled text, it never fills in examination findings, a
   diagnosis, treatment or advice that was not said.
7. **Save** only when the note is right. Save is what makes the note copyable and
   writable to Cliniko.

## Writing it into Cliniko

- **Write draft to Cliniko** (linked recordings only) adds the saved note to the Cliniko
  note as a **draft**. It never replaces what is already there: anything already in a
  question — your typing or the template's prompts — stays, and the app's text goes below
  it after an empty line. Delete any template prompt you no longer want in Cliniko.
- **Do not edit the note in Cliniko while a write is running** — an edit saved in that
  moment is lost.
- After the write, **reload the note page in Chrome** and check the draft is there. If
  Cliniko says the note was updated elsewhere, choose **Discard my changes** (that keeps
  the written draft).
- Then press **Complete** in the app. Complete destroys the recording's audio and the
  session; the transcript and the notes are kept in **Past sessions** for your retention
  setting (old entries are deleted only while the app is running — at start-up and then
  about hourly). The one exception is a recording the patient consented in writing to
  keep for development, with its box ticked before Start (see
  [Keeping a recording to help develop the program](development-recording-consent.md)):
  its audio is kept with the past session until you delete it, and Complete says "The
  recording was kept for development." If it says so for a patient who did not sign
  that form, press **Delete recording** on the Past sessions tab at once.
- **Finalise the note in Cliniko** yourself, after reading it there in full. The app
  never finalises a note.
- If you **copy** the note instead, paste it into the right patient's note and check the
  patient before pasting. The copy is kept out of Windows clipboard history, but stays on
  the clipboard until something replaces it.
- **A shadow recording** (a pilot comparison appointment, started while "Shadow mode
  (pilot)" was ticked on the Status tab): Write and Copy are refused with the reason
  shown, the note's text cannot be selected (a line you open to edit can be changed, but
  not copied or cut), and saving it teaches the app nothing. Review
  and score it as the pilot asks, then write your own note in Cliniko the usual way.

## If something looks wrong

- **Wrong patient or note in Cliniko:** stop; remove the app's text from that Cliniko
  note before anyone finalises it; do not press Complete; follow the incident process.
- **"An earlier write may have reached Cliniko":** look at the note in Cliniko before
  copying or writing anything.
- **A note that misrepresents the consultation:** do not save it. Cancel the review and
  generate again, or delete the note and write it yourself. Generating again replaces
  the earlier draft; at Complete, Past sessions still keeps the transcript and the draft
  from the most recent generation (when it could be read back), for at least 7 years like
  any kept transcript. **Delete now** there is only for a recording made in error (the
  wrong patient, a test, or one recorded without consent), not for a poor draft.

## Looking back: Past sessions

The **Past sessions** tab shows each completed session's **generated note** (the draft as
the app first showed it in the most recent generation — an earlier generation is not
kept; "Generated note not kept" when there was none or it could not be read back) beside the **saved
note** (what you saved), with the transcript behind
"Show transcript" and whether the note was written to Cliniko.

- Use it to see how much you changed the app's draft — a check on how far to trust it.
- **Hide names** masks the patient's name in the list. It does not hide a name spoken in
  the transcript or written in a note.
- **Copy saved note** copies the note you saved; the transcript cannot be copied. An
  entry marked "(shadow recording)" — a pilot comparison appointment — cannot be copied
  at all: read it as shown.
- A kept transcript is part of your health record. It can be reached by an access request
  or a subpoena, and the app keeps it on this computer only, with no backup of its own
  (your own backup or sync software may still copy the encrypted files — see the start-up
  warnings in the downtime procedure). It is kept for at least 7 years: the retention
  setting is "Until I delete them" (the default) or "7 years". In Victoria, NSW and the
  ACT a child's health record must be kept at least until they turn 25 (elsewhere the Australian
  Privacy Principles apply, with no fixed period); the app does not know a patient's
  age, so choose "Until I delete them" when that applies. **Cliniko stays the
  record**.
- **Delete now** (press twice) deletes an entry for good — with its kept recording, if it
  has one. Use it only for a recording made in error: the wrong patient, a test, or one
  recorded without consent.
- An entry marked "(recording kept)" also holds its recording, kept with the patient's
  written consent for development. **Delete recording** (press twice) deletes the
  recording alone — when the patient withdraws, or at its 12-month review — and the
  transcript and notes stay; **Export recording (WAV)** makes an unencrypted copy for
  labelling who is speaking, to delete when you have finished. See
  [Keeping a recording to help develop the program](development-recording-consent.md).
