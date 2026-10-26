# Clinician review guide — checking a Clinic Scribe note

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); see the [practice documents README](README.md) for the sources, which
> cover every state and territory the research looked at.

Draft 1 (2026-10-01; the shadow-recording lines added 2026-10-07 for the pilot build,
approved by the practitioner the same day; the kept-recording line added 2026-10-08 for
version 0.3.0, awaiting the practitioner's approval; the background-music, marked-line and
number lines added 2026-10-12 for version 0.3.2, awaiting the practitioner's approval; the
next-patient, removing-lines, self-correction and "unsure" lines added 2026-10-13 for
version 0.3.3, approved by the practitioner on 2026-10-22; the left-out-line, wider-doubt and
shorter next-patient-mark lines added 2026-10-24 for version 0.3.4, awaiting the
practitioner's approval; the longer goodbye-and-greeting list lines added 2026-10-26 for
version 0.3.5, awaiting the practitioner's approval). For the practitioner, before saving
a note and before finalising it in Cliniko.

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
- **Turn background music off, or as low as practical.** The speech software can mistake
  music — singing especially — and other background sound for speech, and write down
  words nobody said. The app marks what it suspects (below), but it cannot catch
  everything.

## Reading the transcript

The transcript sits beside the note for the whole review. Use it as the evidence, not the
note.

- Words the speech software was unsure of — and numbers and names — are marked like
  `[word?]`. Check every mark that matters clinically against what you remember.
- A line that starts `[possibly not speech]` holds a short burst of words the app
  suspects may be music or noise, not speech — for example a few words packed in faster
  than ordinary talk that the software was also unsure of.
  Check it against what you remember. A real line can be marked too, and invented words
  can go unmarked. While you are still recording, the live view is provisional: the
  note is drawn from the transcript as it stands when you finish.
- The speaker labels can be wrong, especially when people talk over each other.
- **"A possible next patient starts at line N [time]."** If the recording heard a goodbye
  and then a greeting, the Transcript tab says where a new patient may have arrived — the
  line's number, and the time shown at the start of that line in the transcript — and the
  note will stop before that line (below). If those lines really are the next patient's —
  you forgot to stop or switch the recording — press **Remove lines N-end from this
  recording...** before you generate the note, and confirm. They are taken out of this
  recording's transcript for good, so no note, Past-sessions copy or replay holds them,
  and the recording's audio will not be kept for development even if the patient agreed
  to that. It cannot be undone, so check the line number first; if the goodbye and
  greeting were part of this consultation (a phone call, someone at the door), choose
  **Keep the whole transcript**. You can only remove lines while no note is open for
  review and none is saved: if a note is open, use **Cancel review and regenerate** on
  the Note tab first. If the removed lines held every line matched to your voice, the
  app says so; choose the clinician speaker yourself before you generate (opened again
  later, that transcript may say voice attribution "did not run" — the speaker model is
  not at fault).
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
   words from the transcript — it adds no findings of its own — but the transcript itself
   can hold words nobody said (background sound written down as speech), and a line can
   land under the wrong heading, miss context (for example "not" said earlier), or carry a
   mis-heard word. Move, remove or edit lines until the note says what happened. When
   someone corrects themselves straight after a line the app placed, starting with
   "actually", "I mean", "I meant" or "correction", perhaps after "well" ("Actually,
   it's better"), the correction is
   usually placed with that line, so both are in the note, in order: remove the one that
   was taken back. It is not placed there under the assessment, diagnosis, advice or
   management plan headings, and a correction said any other way may be left out — the
   transcript shows it.
3. **Pre-filled lines** from your own settings are marked as pre-filled. Remove any that
   are not true for this appointment; Save confirms the rest.
4. **Marked lines.** A line quoted from the transcript that holds a number is marked
   `[check: number]`, and one holding words marked as possibly not speech is marked
   `[check: possibly not speech]` — after the line in the Clean clinical style, inside its
   label in Verbatim, and at the front of its row when you edit the note (a prose style
   says how many of a section's lines are marked). Check each one against the transcript:
   remove anything that was not said, keep the rest. Each kind has its own review warning
   ("A quoted line contains a number", "A quoted line may be music or noise, not
   speech") that **"Acknowledge all review warnings" does not clear** — press its own
   Acknowledge. Most notes quote a number, so most notes need that click before you can
   save. A line someone other than you said with words of doubt ("I think", "probably",
   "maybe", "I guess", "I'm not sure", "I don't know", "I reckon" and others) is marked
   `[check: unsure]` the same way, with
   the review warning "A quoted line says the speaker was unsure": check that the note
   does not state as fact what they were unsure of. When the speech software split one
   sentence of theirs into two lines at a comma (or a semicolon, colon or long dash), and the
   words of doubt are in one half, both halves are marked. "Acknowledge all review
   warnings" does clear that one. Doubt said in other words (for example "not too sure" or
   "I dunno"), or shown only by tone, is not marked, and words of doubt in a separate
   sentence (after a full stop) mark only their own line. The copied note and the draft written to Cliniko leave the check marks out.
5. **The note stops where a new patient may have arrived.** When the Transcript tab
   named a possible next patient (above) and you generated anyway, the note leaves out
   every line from there on, and the review warning "The note stops where a new patient
   may have arrived" is shown. In the line list under **Edit the note**, those lines are
   marked `[next patient?]`. If any of them belongs to this patient — the
   goodbye and greeting were part of this consultation — add it back with **Add line to
   section**. If they are another patient's, use **Cancel review and regenerate**, then
   remove them on the Transcript tab. This warning, too, is cleared only by its own
   Acknowledge. The app recognises only a set list of common goodbyes and greetings, so a
   next patient greeted in other words is not caught: check the end of every transcript.
   From version 0.3.5 the list is longer and includes everyday words you may also say
   during a visit, such as "thank you", "see you" and "how are you doing", so a goodbye
   and then a greeting within one consultation may stop the note early more often. A
   single greeting can now do it too: if someone joins you partway through and you say
   "Oh, nice to see you, come on in", the note may stop there. Add those lines back as
   above. The warning shown while you record that a new consultation may have started
   uses the same list, so it can appear more often too — for example after "Nice to see
   you, come on in" at the start of a visit. It changes nothing by itself, and it
   appears only once per recording: if it has already appeared, it will not appear
   again for a later new patient in the same recording.
6. **Blocking warnings must be fixed** before you can save — for example a symptom the
   transcript negates, or a dose in clear conflict with it. **Review warnings must be
   read and acknowledged** — for example most other dose differences, a left/right
   difference, or a side, number, dose, "not" or medicine someone said (or a name you
   said) that the note left out; that last warning, too, is cleared only by its own
   Acknowledge, and it ignores words marked as possibly not speech. A whole line you said,
   with none of those words, that the note leaves out — advice, a plan, a safety-net line that none of your
   headings' phrases picked up — has its own review warning, "A line you said is not in
   the note", also cleared only by its own Acknowledge. Tick **Show flagged lines only**
   under **Edit the note** to find these lines (each is marked `[flagged]`), and add any
   that belongs with **Add line to section**. A short reply such as "okay" can raise it
   too: acknowledge it once you have looked. A line of yours that the app labelled as the
   other speaker's raises no such warning, and neither does a line whose words are all
   marked as possibly not speech, so still read the transcript through. The
   checks are a safety net, not a guarantee: they look for particular kinds of mismatch
   and cannot tell you the note is complete or correct.
7. **Writing styles.** If you use a prose style (Narrative or Own voice), the app turns
   your confirmed lines into sentences on this computer and checks each section against
   them; a section that fails the check is shown as plain lines instead, and you
   acknowledge it. Read the prose as carefully as the lines — the check is not a
   certificate that the meaning survived.
8. **Fill the gaps yourself.** Headings the app had nothing for stay empty. Beyond your
   own proposals and pre-filled text, it never fills in examination findings, a
   diagnosis, treatment or advice that is not in the transcript — but words the speech
   software invented over background sound are in the transcript (step 2), so check
   every line, marked or not.
9. **Save** only when the note is right. Save is what makes the note copyable and
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
