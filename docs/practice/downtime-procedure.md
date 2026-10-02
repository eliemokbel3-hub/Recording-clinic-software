# Downtime procedure — when Clinic Scribe or Cliniko is unavailable

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); see the [practice documents README](README.md) for the sources, which
> cover every state and territory the research looked at.

Draft 1 (2026-10-01). For the practitioner. The rule behind every step: **Clinic Scribe
is a writing aid, and Cliniko is the record.** If the app is not working, write the note
in Cliniko yourself, the usual way; nothing about the patient's care waits for the app.

## Quick reference

| What you see | What to do now | Afterwards |
|---|---|---|
| The app will not open, or Chrome's icon shows grey **OFF** | Write the note in Cliniko yourself | Open the app from its usual shortcut (not from a terminal that will be closed). If it says it is already running, look for its window. |
| "Start failed: AuditWriteError: the audit record could not be saved (…). Nothing was recorded." | Do not record. Write the note yourself | See [The audit record](#the-audit-record) |
| Cliniko cannot be reached | Record from the Session tab if the patient consents; the recording is not linked to the Cliniko note | Copy the reviewed note into Cliniko by hand once Cliniko is back |
| The recording stopped (crash, power cut, restart) | Reopen the app; read the transcript from the Recovery tab and write the note yourself | Within 24 hours — see [An interrupted recording](#an-interrupted-recording) |
| "Cliniko is rate-limiting this clinic" | Wait the time it shows, or copy the note into Cliniko by hand | — |
| "An earlier write may have reached Cliniko" | Open the note in Cliniko and look before copying anything | — |
| The note went to the wrong patient or note in Cliniko | Stop. Remove the text in Cliniko before anyone finalises it; do not press Complete | Follow the incident process |
| A warning on the Status tab about OneDrive, a network drive, the roaming profile or crash reports | Recording still works | See [Start-up warnings](#start-up-warnings) |
| The computer is lost, stolen or its disk has failed | Write notes in Cliniko yourself | See [Losing the computer](#losing-the-computer) |

## Before the first patient each day

- Open the app and check the Chrome icon shows a green **OK**.
- Look at the Status tab: it should show no warning lines under the intended-use line.
- Have a way to write notes without the app (Cliniko open as usual). The patient
  information sheet (`patient-info-v1`) should be at hand.

## When the app is not available

1. Write the note in Cliniko yourself, the usual way.
2. Do not record the consultation with anything else as a substitute.
3. Note in Cliniko, if you normally record the patient's AI-scribe consent, that the
   app was not used for this appointment.

## Cliniko cannot be reached

- A recording started from a Cliniko note while Cliniko cannot be checked is marked as
  not verified. A note from it cannot be written into Cliniko until the app can check the
  note again with Cliniko.
- A recording started from the app's Session tab (not from a Cliniko note) is never
  linked to a Cliniko note and can never be written back. Use **Copy** on the Note tab and
  paste the reviewed note into the right Cliniko note yourself once Cliniko is back —
  check the patient and the appointment first.
- If the app says Cliniko is rate-limiting the clinic, wait the time it shows before
  writing again, or copy the note by hand.

## An interrupted recording

If the app or the computer stops during a recording:

1. Reopen the app. An interrupted recording is listed on the **Recovery** tab. It stays
   encrypted and can be opened **for up to 24 hours from when it started**; after that
   the app deletes it the next time it runs.
2. Open it from the Recovery tab and let the app finish transcribing it. A recovered
   recording shows its **transcript only**: the app does not draft a note from it and
   cannot write it into Cliniko. Read the transcript (it cannot be copied) and write the
   note in Cliniko yourself.
3. The end of the recording may be missing. Check the transcript's last lines against
   your memory of the consultation.
4. Then **Complete** it (the transcript is kept in Past sessions, the audio is
   destroyed) or **Discard** it (nothing is kept except the record that a recording
   happened and was discarded — no name, nothing that was said).

Recordings waiting for review after back-to-back consultations are listed as
**Unreviewed**. The app warns two hours before one would be deleted and lists them when
you close it — review them before the end of the day.

## The audit record

Every recording starts by writing a small, encrypted record of it (no name, nothing that
was said). If that record cannot be saved, **Start is refused and nothing is recorded** —
write the note yourself. Then:

- **"… its key cannot be read on this Windows account …"** or **"… its key is missing
  …"** — this happens, for example, after an administrator resets your Windows password.
  On the **Past sessions** tab press **Start a new audit record** and confirm. The old
  record is set aside, unread, in a folder beside it; nothing is deleted. Recording can
  start again straight away.
- **"… the audit folder could not be written"** or **"… could not be read"** — check the
  computer has free disk space, then close and reopen the app. If it keeps happening, stop
  using the app and investigate before recording again.
- **"N audit record updates could not be saved since Clinic Scribe started"** on the Past
  sessions tab — your recordings and notes were not affected; only the record of what
  happened to them is incomplete. If the number keeps rising, restart the app; if it still
  rises, investigate.

## Past sessions problems

- **An entry reads "Cannot be read on this Windows account".** Its key cannot be opened
  from this login — typically after an administrator password reset, or if the data was
  copied from another computer. It cannot be read again on this account, but it is still
  kept and is never deleted by age. Leave it there: **Delete now** is only for a recording
  made in error (the wrong patient, a test, or one recorded without consent) — delete an
  unreadable entry only if it was one of those, or once the reviewer question here is
  answered. **[Reviewer: whether a kept transcript that can no longer be read must still
  be kept for the 7-year minimum.]** The clinical record in Cliniko is not affected.
- **"The Past-sessions settings file cannot be read".** Nothing is deleted by age and
  names are hidden. Choose a retention setting again to replace the file; names then
  stay hidden until you untick **Hide names**.
- **"Your earlier Past-sessions setting was shorter than 7 years …"**. The app no longer
  offers a setting under 7 years (a kept transcript is kept for at least 7 years), so a
  shorter one saved earlier is read as 7 years. Choose "7 years" (or "Until I delete
  them") again to save it; the line then goes.
- **"Some past sessions older than the setting could not be deleted".** They are kept for
  now and the app tries again later while it is running. If it persists, you may delete
  them with Delete now — they are already past your retention setting, so this is the
  deletion the setting asked for, not an early one.
- **Complete says "the Past-sessions copy could not be saved"**: nothing was deleted —
  try Complete again; if it keeps failing, check disk space. You can still Discard.
- **"Completed. The Past-sessions copy will appear after the next check."** The session
  is finished; its copy appears in Past sessions after the app's next check (within
  about 15 minutes while it runs, or at the next start).

## Start-up warnings

Shown on the Status tab and the Past sessions tab. Recording still works; fix the cause
when you can.

- **"… data folder is inside OneDrive …"**, **"… on a network drive …"** or **"… in the
  roaming part of your Windows profile …"** — the app's files may be copied off this
  computer: the recordings, transcripts, notes and audit record are encrypted, but its
  settings, the short phrases it learned from your notes, the clinic list (with your
  contact email) and its logs are not. Stop and find out why the folder is there (for example, a folder
  redirection set by IT) before the next consultation; treat any copy that has already
  left the computer under the incident process.
- **"Crash reports are not excluded for Clinic Scribe …"** — on the installed app,
  reinstall Clinic Scribe with the same installer, then restart the app; on a developer
  copy, rerun its registration step from a normal terminal (not from an AI assistant's
  shell), then restart the app.
- **"Clinic Scribe's live recordings and logs are not marked to be left out of Windows
  backups and snapshots …"** (installed app only) — reinstall Clinic Scribe with the
  same installer. Even when this is set, it is a request that some backup tools ignore;
  it never covers Past sessions or the audit record, which stay backup-eligible on
  purpose.
- **"Warning: a per-user Chrome link overrides the installed one."** (installed app
  only) — Chrome is using a different Chrome link from the one the installer set up.
  If you did not set one up yourself, stop recording and follow the incident process
  before the next consultation. When the line above it also says the per-user link "is
  broken, and reinstalling does not remove it", Chrome cannot reach the app until that
  per-user link is removed; reinstalling will not help.
- **"Crash reports are not excluded for this launch (python.exe) …"** — the app was
  started from a terminal. Close it and start it with its usual shortcut.
- **"Some of Clinic Scribe's folders could not be marked to stay out of Windows
  Search."** — usually low-risk (the clinical files are encrypted, though the settings,
  learned phrases and logs are not); restart the app, and look into it if it persists.
- **"Clinic Scribe is not running from its install folder — reinstall Clinic Scribe."**
  (a box at start, instead of the window) — a copy of the installed app was started
  from somewhere else. Start it from the Start menu; if the box still shows, reinstall
  Clinic Scribe with a checked installer, and treat an unexplained copy as a possible
  incident.

## Losing the computer

- If the computer, its disk or your Windows login is lost: the kept transcripts and
  notes in Past sessions are **lost with it** — there is no backup — and so is the audit
  record. The clinical record in Cliniko is not affected.
- If the computer was lost or stolen (not just broken), the encrypted data can only be
  opened through your Windows login, but the app's plain settings, learned phrases,
  clinic list and logs can be read by anyone with the disk unless it has full-disk
  encryption (BitLocker) — treat it as a possible data breach: follow the
  incident process and assess it under the Notifiable Data Breaches scheme. **[Reviewer:
  that scheme was not part of the 2026-10-01 research — confirm the wording.]**
- Change your Windows password and your Cliniko password, and replace each clinic's
  Cliniko API key (generate a new one in Cliniko; replace it on the Clinics tab of the
  new installation).

## After any downtime

- Make sure every consultation from the period has a finalised note in Cliniko.
- Check the Recovery tab and the Unreviewed list are empty, or deal with what is there.
- Record what happened and what you did.
