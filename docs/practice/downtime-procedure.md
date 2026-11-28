# Downtime procedure — when Clinic Scribe or Cliniko is unavailable

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** Not legal advice. Written for the developing practitioner's own clinics
> (in Victoria); see the [practice documents README](README.md) for the sources, which
> cover every state and territory the research looked at.

Draft 1 (2026-10-01; the patient-information version and the shadow-recording line
updated 2026-10-07 for the pilot build, approved by the practitioner the same day; the
kept recording added 2026-10-08 for version 0.3.0, and the terminal-launch crash-report
line updated the same day, both approved by the practitioner on 2026-10-09; the backup
and restore lines — [Backups](#backups-from-version-050), the quick reference's "From
version 0.5.0" row, the first point and the two restore sequences under
[Losing the computer](#losing-the-computer), the 0.5.0 line under
[The audit record](#the-audit-record) and the "From version 0.5.0" lines under
[Past sessions problems](#past-sessions-problems) — added 2026-11-28 for version
0.5.0, **awaiting the practitioner's approval**). For
the practitioner. The rule behind every step: **Clinic Scribe
is a writing aid, and Cliniko is the record.** If the app is not working, write the note
in Cliniko yourself, the usual way; nothing about the patient's care waits for the app.

## Quick reference

| What you see | What to do now | Afterwards |
|---|---|---|
| The app will not open, or Chrome's icon shows grey **OFF** | Write the note in Cliniko yourself | Open the app from its usual shortcut (not from a terminal that will be closed). If it says it is already running, look for its window. |
| "Start failed: AuditWriteError: the audit record could not be saved (…). Nothing was recorded." | Do not record. Write the note yourself | See [The audit record](#the-audit-record) |
| Cliniko cannot be reached | Record from the Record page if the patient consents; the recording is not linked to the Cliniko note | Copy the reviewed note into Cliniko by hand once Cliniko is back |
| The recording stopped (crash, power cut, restart) | Reopen the app; read the transcript from the Recovery page and write the note yourself | Within 24 hours — see [An interrupted recording](#an-interrupted-recording) |
| "Cliniko is rate-limiting this clinic" | Wait the time it shows, or copy the note into Cliniko by hand | — |
| "An earlier write may have reached Cliniko" | Open the note in Cliniko and look before copying anything | — |
| The note went to the wrong patient or note in Cliniko | Stop. Remove the text in Cliniko before anyone finalises it; do not press Complete | Follow the incident process |
| A warning on the Status tab about OneDrive, a network drive, the roaming profile or crash reports | Recording still works | See [Start-up warnings](#start-up-warnings) |
| The computer is lost, stolen or its disk has failed | Write notes in Cliniko yourself | See [Losing the computer](#losing-the-computer) |
| From version 0.5.0 (awaiting the practitioner's approval): Past sessions lists sessions that "Cannot be read on this Windows account" (for example after a Windows password reset) | Do **not** press Delete now on them. Recording still works once the audit record can be written | See [Past sessions problems](#past-sessions-problems) |

## Before the first patient each day

- Open the app and check the Chrome icon shows a green **OK**.
- Look at the Status tab (Settings, then Status): it should show no warning lines under
  the intended-use line.
- Have a way to write notes without the app (Cliniko open as usual). The patient
  information sheet (its current version: `patient-info-v3`) should be at hand, and the
  development-recording consent form (`development-consent-v1`) if you may ask for one.

## When the app is not available

1. Write the note in Cliniko yourself, the usual way.
2. Do not record the consultation with anything else as a substitute.
3. Note in Cliniko, if you normally record the patient's AI-scribe consent, that the
   app was not used for this appointment.

## Cliniko cannot be reached

- A recording started from a Cliniko note while Cliniko cannot be checked is marked as
  not verified. A note from it cannot be written into Cliniko until the app can check the
  note again with Cliniko.
- A recording started from the app's Record page (not from a Cliniko note) is never
  linked to a Cliniko note and can never be written back. Use **Copy note** on the Review
  screen and
  paste the reviewed note into the right Cliniko note yourself once Cliniko is back —
  check the patient and the appointment first. (A shadow recording's note — a pilot
  comparison appointment — cannot be copied either: write your own note.)
- If the app says Cliniko is rate-limiting the clinic, wait the time it shows before
  writing again, or copy the note by hand.

## An interrupted recording

If the app or the computer stops during a recording:

1. Reopen the app. An interrupted recording is listed on the **Recovery** page. It stays
   encrypted and can be opened **for up to 24 hours from when it started**; after that
   the app deletes it the next time it runs.
2. Open it from the Recovery page and let the app finish transcribing it. A recovered
   recording shows its **transcript only**: the app does not draft a note from it and
   cannot write it into Cliniko. Read the transcript (it cannot be copied) and write the
   note in Cliniko yourself.
3. The end of the recording may be missing. Check the transcript's last lines against
   your memory of the consultation.
4. Then **Complete** it (the transcript is kept in Past sessions; the audio is
   destroyed, unless the patient consented in writing to it being kept for development
   and you ticked that box before Start — then it is kept with the past session and
   Complete says "The recording was kept for development.") or **Discard** it (nothing
   is kept except the record that a recording happened and was discarded — no name,
   nothing that was said — even for a recording you had ticked to keep).

Recordings waiting for review after back-to-back consultations are listed as
**Unreviewed**. The app warns two hours before one would be deleted and lists them when
you close it — review them before the end of the day.

## The audit record

Every recording starts by writing a small, encrypted record of it (no name, nothing that
was said). If that record cannot be saved, **Start is refused and nothing is recorded** —
write the note yourself. Then:

- **"… its key cannot be read on this Windows account …"** or **"… its key is missing
  …"** — this happens, for example, after an administrator resets your Windows password.
  On the **Past sessions** page press **Start a new audit record** and confirm. The old
  record is set aside, unread, in a folder beside it; nothing is deleted. Recording can
  start again straight away. **From version 0.5.0** (awaiting the practitioner's
  approval): keep every backup made before you did this
  ([Backups](#backups-from-version-050)); if Past sessions also lists sessions that
  "Cannot be read on this Windows account", follow
  [Past sessions problems](#past-sessions-problems) next.
- **"… the audit folder could not be written"** or **"… could not be read"** — check the
  computer has free disk space, then close and reopen the app. If it keeps happening, stop
  using the app and investigate before recording again.
- **"N audit record updates could not be saved since Clinic Scribe started"** on the Past
  sessions page — your recordings and notes were not affected; only the record of what
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

  **From version 0.5.0** (awaiting the practitioner's approval): such sessions can be
  brought back from a backup, in this order — the second sequence under
  [Losing the computer](#losing-the-computer):
  1. Do **not** press Delete now on them: a deletion is recorded, and a deleted session
     is never restored.
  2. If the Past sessions page shows **Start a new audit record**, press it first
     ([The audit record](#the-audit-record)): Restore stays off ("Start a new audit
     record first.") until the audit record can be read.
  3. Press **Set aside sessions that cannot be opened...** and confirm. Only the sessions
     this Windows login can no longer open are moved, unread, into a folder beside Past
     sessions; nothing is deleted and nothing is recorded as deleted. Keep that folder
     (see [Backups](#backups-from-version-050)).
  4. **Open a backup...** (the newest), read its summary, then **Restore**.

  What this cannot bring back: a session completed after that backup was made, and a
  session that still held a kept recording when it was made (neither is in it). Those
  stay set aside and cannot be read. Set aside never moves a session that still has a
  recording file, or whose recording file it cannot rule out, and its line says how many
  it did not move. If that recording had already been deleted, close and reopen Clinic
  Scribe after the Restore so the app can finish clearing the deleted recording's files,
  then press Set aside and Restore once more (if the line still says a session was not
  moved, wait for the next start and try again). A session whose recording is still kept
  is not moved and is in no backup, so Restore cannot bring it back: it stays in Past
  sessions and cannot be read on this login. (Where a recording was deleted before Start
  a new audit record, the restored audit record can show it as kept with no deletion
  date; the recording itself is gone.)
- **From version 0.5.0** (awaiting the practitioner's approval): **"The audit record
  cannot be read - see Past sessions problems in the downtime procedure."** when you press
  Back up. No backup is made while the audit record cannot be read. If this follows a
  Windows password reset, follow the steps above; otherwise see
  [The audit record](#the-audit-record). Starting a new audit record is a change that
  older backups must be kept for ([Backups](#backups-from-version-050)).
- **From version 0.5.0** (awaiting the practitioner's approval): **"Nothing was
  restored: Clinic Scribe could not prepare the Past sessions folder - see Past sessions
  problems in the downtime procedure."** Nothing was written. Close and reopen the app and
  try again; if it keeps happening, stop and investigate — something other than Clinic
  Scribe may have changed its Past sessions folder.
- **From version 0.5.0** (awaiting the practitioner's approval): a session that every
  backup line counts as "not in a backup because a kept recording or its key is still
  present", but that Delete recording cannot reach (the page does not show it as holding
  a kept recording). Its recording's file is missing while the recording's key is still
  there — something other than Clinic Scribe has changed its files. That session's
  transcript and notes are in no backup and it is never set aside. Treat it under the
  incident process.
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
- **"A partial export file … .wav.part could not be removed from the folder you chose -
  delete it by hand."** (or "… may remain in a folder you exported to …") — an export
  of a kept recording was interrupted, and the half-written copy is **not encrypted**.
  Find the file by that name in the folder you exported to, delete it, and empty the
  Recycle Bin.

## Start-up warnings

Shown on the Status tab (under Settings) and the Past sessions page. Recording still works; fix the cause
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
- **"Crash reports are not excluded for this launch (<a program's name>) …"** — the app
  was started from a terminal in an unusual way. Close it and start it with its usual
  shortcut.
- **"Some of Clinic Scribe's folders could not be marked to stay out of Windows
  Search."** — usually low-risk (the clinical files are encrypted, though the settings,
  learned phrases and logs are not); restart the app, and look into it if it persists.
- **"Clinic Scribe is not running from its install folder — reinstall Clinic Scribe."**
  (a box at start, instead of the window) — a copy of the installed app was started
  from somewhere else. Start it from the Start menu; if the box still shows, reinstall
  Clinic Scribe with a checked installer, and treat an unexplained copy as a possible
  incident.

## Losing the computer

- If the computer, its disk or your Windows login is lost: before version 0.5.0 the kept
  transcripts and notes in Past sessions are **lost with it** — there is no backup — and
  so are any recordings kept for development and the audit record. The clinical record in
  Cliniko is not affected.
- **From version 0.5.0** (awaiting the practitioner's approval): the kept transcripts,
  notes and audit record are lost only as far as your newest backup does not hold them
  ([Backups](#backups-from-version-050)). Recordings kept for development are never in a
  backup, so they are lost with the computer either way. Restore from **one** backup, the
  **newest**:
  - **A new computer, or a new Windows login:** install Clinic Scribe 0.5.0 or later and
    open it. Before restoring, set the Past-sessions retention setting and Shadow mode as
    they were (a fresh login starts at "Until I delete them" with Shadow mode off, and the
    retention setting decides what Restore adds). Then Past sessions → **Open a
    backup...** → read the summary → **Restore**. Afterwards add each clinic's Cliniko
    API key on the Clinics tab (a key is never in a backup) and record your voice again on
    the Practitioner tab.
  - **The same login after a Windows password reset** (Past sessions lists sessions that
    "Cannot be read on this Windows account"): follow the steps under
    [Past sessions problems](#past-sessions-problems) — Start a new audit record, Set
    aside sessions that cannot be opened..., then Open a backup... and Restore. Never
    Delete now those sessions first.
  - **After either:** delete again, with Delete now, every session you deleted after that
    backup was made — the backup still holds it, and Restore brings it back when no
    surviving record says it was deleted. Restore an **older** backup on top only to
    recover something the newest one lacks, never as routine: the app cannot know every
    deletion, so an older backup can bring back sessions deleted since. After using one,
    check the restored sessions against your own records and delete again what should not
    be there.
- If the computer was lost or stolen (not just broken), the encrypted data can only be
  opened through your Windows login, but the app's plain settings, learned phrases,
  clinic list and logs — and any exported copy of a kept recording you had not yet
  deleted, or a partial export file (`.wav.part`) left behind, which are not encrypted
  at all — can be read by anyone with the disk unless it
  has full-disk encryption (BitLocker) — treat it as a possible data breach: follow the
  incident process and assess it under the Notifiable Data Breaches scheme. **[Reviewer:
  that scheme was not part of the 2026-10-01 research — confirm the wording.]**
- Change your Windows password and your Cliniko password, and replace each clinic's
  Cliniko API key (generate a new one in Cliniko; replace it on the Clinics tab of the
  new installation).

## Backups (from version 0.5.0)

Added 2026-11-28 for version 0.5.0, **awaiting the practitioner's approval**. Each rule
here is stated once; the app's own lines point here.

**What a backup is.** On the Past sessions page, **Back up...** writes one encrypted
file, protected by a passphrase you choose, onto a drive attached to this computer: the
kept transcripts and notes of every past session it can read and the whole audit
record. It never holds a recording kept for development, and never a session that still
holds one — once that recording is deleted, the next backup holds the session's
transcript and notes. It never holds your voice profile, learned phrases or style,
settings, clinic list or Cliniko API keys. The app sends it nowhere. A backup is a
deliberate act: the app never makes one by itself, and after 7 days with sessions kept
since the last one, the Past sessions page says so ("Last backup <date> - N sessions kept
since.").

**Operating rules.**
- Keep the backup drive locked away, and keep the passphrase somewhere else — never on
  the drive or with it.
- A lost passphrase is a lost backup: nobody, you included, can open it without the
  passphrase.
- Keep the newest two backups.
- Write down the counts each backup's line gives ("N sessions, M audit rows", and what was
  left out), in your own records.

**The one rule for destroying an older backup.** Destroy an older backup only when
**both** of these are true:
1. the **newest** backup's line said "Nothing eligible was left out."; and
2. since that older backup was made, nothing on this computer has been lost, become
   unreadable, been set aside, been restored or been started anew (a new audit record).

When any of those has happened: restore first ([Losing the computer](#losing-the-computer)),
**keep every backup made before it happened** — it may hold something no later backup
can — and apply this rule again only to backups made afterwards. Before destroying
anything, check that the Past sessions page lists no session that "Cannot be read on this
Windows account" and shows no line saying the audit record cannot be read, and that the
newest backup does not hold fewer sessions or audit rows than the one before it, beyond
what was deleted or has expired in between. **When in doubt, keep.** After a Delete now
the same rule applies: once it lets the older backups go, no remaining backup holds that
session.

Nothing else is a reason to destroy a backup — not "Nothing to back up yet.", not an
empty Past sessions page, not a restore's summary or report, and not a backup that would
not open (a mistyped passphrase and a damaged file give the same message, so a failed
Open proves nothing).

**A file whose name ends in `.csbk.part`** on the backup drive is a backup that did not
finish being checked — after a power cut or a pulled drive, for example, or when the app
said "A partial backup file may remain on the drive." It may be a whole backup. Keep it
as a backup of unknown content; never destroy it because it would not open. To try it,
copy it, rename the copy so its name ends in `.csbk`, and open the copy. It goes only
when the one rule above lets older backups go.

**The folder of set-aside sessions** (made by Set aside sessions that cannot be opened...,
beside Past sessions) holds clinical records that this login cannot read. For a session
no backup holds, it is the only copy. Keep it: it comes under the rule for a session that
"Cannot be read on this Windows account" ([Past sessions problems](#past-sessions-problems))
and is not destroyed until that reviewer question is answered. (The audit record's own
set-aside folder, made by Start a new audit record, holds no clinical content.)

**If the backup drive is lost or stolen.** Without the passphrase the file shows only:
that it is a Clinic Scribe backup; when, and by which version and which build (the
installed app or the developer build), it was made; how many sessions and audit rows it
was planned to hold; the program's own reference number for each session it holds and
for each audit row, with the month each audit row is filed under (including sessions
that have only an audit row); the kind and size of each part; and, to someone holding two
backups, which parts changed between them. No name and nothing that was said can be read
without the passphrase. Treat a lost drive under the incident process.

**What this rule cannot see** (named for the independent review):
1. The app cannot see what this computer has lost: a Past sessions folder or an audit
   record that is gone, or started anew, makes the next backup smaller and still say
   "Nothing eligible was left out." The rule rests on you noticing, by the counts and the
   page.
2. Restore keeps a present audit record entry as it is, apart from noting that its
   session is now in Past sessions: it does not combine two records of the same session
   that can both be read (apart from one narrow case: a bare record the app made later,
   for a session it then had no record of, is replaced by the backup's record made when
   the recording started). So an older backup can hold a fact the present record lacks —
   a later date, an export count — which is why backups made before a restore are kept.
3. A backup kept under this rule goes on holding sessions deleted since.
4. A session completed since the last backup, and one that still holds a kept recording,
   is in no backup.

## After any downtime

- Make sure every consultation from the period has a finalised note in Cliniko.
- Check the Recovery page and the Unreviewed list are empty, or deal with what is there.
- Record what happened and what you did.
