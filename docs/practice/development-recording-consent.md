# Keeping a recording to help develop the program — information and consent

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); the state notes cover every state and territory the research looked at.
> See the [practice documents README](README.md) for the sources and the open questions.
> Until that review is done, keep recordings for development only occasionally and with
> care.

**Document version: `development-consent-v1`** (2026-10-08; approved by the practitioner
on 2026-10-09). Record this version in the patient's Cliniko record when they sign Part C. The
tick in the program carries the same version name.

This is a **separate, second** consent. It is asked for only after the patient has agreed
to the ordinary AI-assisted note-taking described in the
[patient information and consent](patient-information-and-consent.md) sheet
(`patient-info-v3`), and only in writing. It has three parts: an information sheet for the
patient (Part A), what the practitioner does (Part B), and the written consent form
(Part C).

---

## Part A — Information for patients

### What are we asking?

Normally the recording of your appointment is deleted once your practitioner has
finished your note; only the written-out conversation (the "transcript") and the notes
are kept, as the main information sheet explains.

With your **written** permission, your practitioner would like to **keep the recording
itself** as well, to help develop the program. Saying no is completely fine and makes no
difference to your care.

### What would be kept

- The **recording** of this appointment.
- The transcript and the notes, which the program already keeps (see the main
  information sheet).

### Why

To check and improve how well the program hears speech, tells speakers apart and drafts
notes. For example, your practitioner may play a kept recording through a newer version
of the program on the same computer and compare the results with the notes they wrote.
The results they keep from such a comparison are numbers only — no name and nothing that
was said.

The recording is **not** used to make any decision about your care, and it is not given
to anyone else. **[Reviewer: whether the patient must be told that the program may later
be offered to other practitioners, and whether a research-ethics step applies — see the
README's open questions.]**

### Where it is kept

- On your **practitioner's own computer only**, encrypted, so that it can be opened only
  from your practitioner's own Windows login on that computer.
- The program **never sends it anywhere**: not to the cloud, not to an online AI service
  and not to anyone else. The program makes no backup of it.
- To mark who is speaking in a recording, your practitioner may make an **unencrypted
  copy on the same computer**. The program refuses to save that copy in some places it
  can recognise — a OneDrive folder it can find, a network drive, or a removable drive
  such as a USB stick — but it cannot recognise every synced or shared folder, OneDrive
  included. So your practitioner checks that the copy is not in any synced, shared or
  backed-up folder, and deletes it as soon as they have finished with it.
- Like everything on the computer, the recording — and an unencrypted copy while it
  exists — can be copied by backup or file-sync software the practice runs on the
  computer, which the program cannot stop. **[Practice: confirm the computer's backup and
  sync settings.]**

### Who can use it

Only your practitioner.

### How long it is kept

Until your practitioner deletes it. Your practitioner **reviews every kept recording at
least every 12 months** and deletes it when it is no longer needed for this purpose. If
the computer fails, the recording is lost; nothing in your care depends on it.
**[Reviewer: whether a kept recording is itself part of the health record that
Victoria, NSW and the ACT require to be kept for at least 7 years from the last contact
(or until 25 for a child) — elsewhere in Australia APP 11.2 applies (destroy or
de-identify it once it is no longer needed) — see the README.]**

### Your choices

- **You can say no.** Nothing about your care changes, and the appointment can still use
  AI-assisted note-taking in the usual way (the recording is then deleted as usual).
- **You can withdraw at any time**, now or later, by telling your practitioner or the
  practice. **Your kept recordings are deleted the same day.** The transcript and the
  notes stay,
  because they are part of the health information the practice keeps, as the main
  information sheet explains. **[Reviewer: confirm a kept recording may be deleted on
  withdrawal — see the README.]**
- **You can ask** whether a recording of yours is kept.

### Questions or concerns

**[Practice: name, phone and email for privacy questions; how to make a complaint.]**

---

## Part B — For the practitioner

### When to ask

- **After** the ordinary recording consent (Part B of the main sheet), and **separately**
  — never as one question. The patient must be free to agree to the note-taking and say
  no to this.
- Only when you want this particular recording kept. Most recordings should not be.
- The **written form (Part C) is required.** A verbal yes is not enough: if there is no
  signed form, do not keep the recording.
- Ask everyone else in the room too (a parent, carer, interpreter or student): their
  voices would be kept as well. **[Reviewer: confirm the approach for children and for
  people who cannot consent for themselves.]**

### What to say (suggested)

> "Separately — and it's completely fine to say no — I'm also checking how well the
> program works. Would you be happy for me to keep the recording of today's appointment
> for that? It's kept encrypted on my computer — I may make a short-lived unencrypted
> copy there to mark who's speaking, then delete it — the program never sends it
> anywhere, and I review it at least once a year and delete it when I no longer need it. You can change
> your mind at any time and I'll delete it that day. It doesn't affect your care either
> way. If you're happy, I'll ask you to sign this form."

Give them Part A to read or take home.

### What to do in Clinic Scribe

1. On the **Status** tab, tick **"Keep recordings for development (written consent
   only)"**. This setting stays on until you untick it; on its own it keeps nothing. If
   the Status tab says the setting could not be read, no recording is kept until you
   tick it again.
2. **For a recording started from Chrome** (the usual way): open the patient's
   treatment note in Chrome FIRST. Then, on the desktop **Session** tab, tick the second
   box above Start: **"I confirm the patient has consented in writing to this recording
   being kept for developing the program"** — it is tied to the note Chrome shows at that
   moment. Then give the ordinary consent in Chrome's side panel and press Start there.
   **For a recording started on the desktop**: tick the ordinary consent box and the
   second box on the Session tab, then press Start. The Session tab says "Next recording
   will be kept for development" while the box is ticked, and "This recording is being
   kept for development" while it records.
3. Like the ordinary consent box, the second box is never ticked in advance and clears
   after every Start, so it is given for each recording. If it was ticked while Chrome
   showed a treatment note, it also clears when Chrome shows a different note or leaves
   that note, or if Chrome's link to the app drops. It also clears if the computer locks
   or sleeps (unless the Session tab says "Lock pause unavailable" or "Sleep pause may
   not work"), or if a Start is refused (except "still getting ready", which keeps it)
   — the Session tab then says "The keep-for-development tick was cleared …" — and when
   the Status-tab setting is turned off. Tick it again before Start if the patient
   consented in writing. A box ticked while Chrome shows no treatment note is tied to no
   patient: moving to other pages in Chrome, another patient's included, does not clear
   it (opening a treatment note does), so it can carry over to the next Start, whoever
   that is for — if that patient does not go ahead, untick it yourself.
4. When you press **Complete**, the message ends "The recording was kept for
   development." only when it actually was. If that sentence appears for a patient who
   did not sign Part C, delete the recording at once (below). If it does not appear, the
   recording was not kept and nothing more is needed. A recording that is discarded, or
   never completed, is never kept.
5. A comparison appointment (shadow mode) may be kept like any other.

### What to record in Cliniko

> "Consented in writing to the recording being kept for development
> (development-consent-v1)."

Write it in the treatment note of **each** appointment whose recording is kept, so the
patient's notes in Cliniko list the date of every kept recording. Keep the signed form
with the practice's other consent forms.

### If the patient withdraws

Find every kept recording of the patient: the patient's notes in Cliniko give the date
of each (above), and a patient who agreed for future appointments may have several. On
the **Past sessions** tab, untick **Hide names**; each row shows the appointment's date
and time, then the patient's name — or "Desktop recording (no Cliniko note)" or "Name not
available", which you match by the date and time — and ends "(recording kept)". A row
that says "Cannot be read on this Windows account" shows no date or name: if it may be
this patient's, delete its recording too — a kept recording is never part of anyone's
care. Select each one, press **Delete
recording**, then **Confirm delete recording** within 10 seconds. The app
says "Recording deleted."; the transcript and the notes stay. Do this the same day. If you
made an unencrypted copy, delete that too, and empty the Recycle Bin. Record the
withdrawal in Cliniko, and do not tick the second box for that patient again.

Delete recording destroys the recording's own key, so the program can no longer open it.
It is a little less thorough than **Delete now** (which destroys the key of the whole
past session): someone with forensic tools and access to this computer might in
principle recover a trace of the deleted key from the disk. Full-disk encryption
(BitLocker) on the computer limits this.

### The 12-month review

A year (365 days) after you pressed Complete for a kept recording, the Past sessions tab
says so ("1 kept recording is due for review - delete it or note in the pilot log why it
is kept.", or the same for several) and the session's own line says "Review due." Delete
the recording, or note in the pilot log's review table why it is still needed. The app
keeps saying "Review due." after a recording you chose to keep; review it again 12 months
after its last review row.

A kept recording whose row says "Cannot be read on this Windows account" never shows
"Review due." and is not counted in that line, because the program cannot read its date.
Review such a row yourself whenever you review the others: if you cannot tell whose
recording it is or why it is kept, press **Delete recording**; otherwise note in the
pilot log's review table why it is kept.

### Making an unencrypted copy to label speakers

**Export recording (WAV)** on the Past sessions tab saves an unencrypted copy, for
marking who is speaking — make one only when you need it, and keep at most one at a
time. The program refuses the places it can recognise — a folder inside OneDrive (only
where Windows tells it where OneDrive is), a network drive, a roaming folder, a removable
or unrecognised drive (such as a USB stick), and the program's own data folders —
choose a folder on this computer's own internal drive. Everything it cannot detect is
your responsibility: an external USB hard disk or SSD may not be refused, so never
export to one; a folder that is really another drive attached inside a folder of this
one is not detected either; and no sync software is reliably detected, OneDrive
included — check yourself that the folder is not synced, shared or backed up. For a comparison appointment it asks
first, because the copy holds the whole consultation. Delete the copy, and empty the
Recycle Bin, as soon as you have finished labelling it.

---

## Part C — Written consent form

**Keeping my recording to help develop the program — consent** (`development-consent-v1`)

I have read, or had read to me, the information about keeping the recording of my
appointment. I understand that:

- this is separate from my consent to AI-assisted note-taking, and I can say no to it
  with no effect on my care;
- the recording will be kept, encrypted, on my practitioner's computer only, the program
  will never send it anywhere, and it will be used only by my practitioner to check and
  improve how the program works;
- my practitioner may make an unencrypted copy on the same computer to mark who is
  speaking, and will delete it afterwards;
- the recording is kept until my practitioner deletes it, and is reviewed at least every
  12 months;
- I can withdraw at any time, and my kept recordings will then be deleted that day; the
  transcript and the notes stay as part of my health information.

I agree to the recording being kept for (tick one):

- [ ] this appointment only
- [ ] this and future appointments, until I say otherwise (my practitioner will still
  check with me each time)

Patient name: ______________________  Signature: ______________________  Date: __________

If signed on someone's behalf — name and relationship: ______________________

Others in the room who agree to their voice being kept — name and signature:
______________________

Practitioner: ______________________  Date: __________
