# Practice documents

> **DRAFT — needs independent privacy/legal/clinical-safety review before use with other
> practitioners.** These are working drafts written for the developing practitioner's own
> clinics (in Victoria). They are not legal advice. Before Clinic Scribe is used by anyone
> else, or sold, each one needs an independent privacy, legal, clinical-safety and
> TGA-scope review.

Plain-English documents for running Clinic Scribe in a practice. They describe what the
app does as built on 2026-10-01; where a document and the app disagree, the app's
behaviour is what happens, and the document must be corrected.

| Document | For | Version |
|---|---|---|
| [Patient information and consent](patient-information-and-consent.md) | Patients, and the practitioner asking for consent | `patient-info-v1` |
| [Privacy information](privacy-information.md) | The practice's privacy policy and collection notice | draft 1 |
| [Downtime procedure](downtime-procedure.md) | The practitioner, when something stops working | draft 1 |
| [Clinician review guide](clinician-review-guide.md) | The practitioner, before saving and finalising a note | draft 1 |

The patient information document carries its own version, `patient-info-v1`. The tick
the practitioner gives in the app before every recording ("I confirm the patient has
consented to AI-assisted recording and documentation") is a separate wording with its own
version in the app; changing one does not change the other. If the patient information
changes, give it a new version (`patient-info-v2`, …) and record in Cliniko which version
a patient was given. None of these drafts has been given to a patient yet, so changes made
before the independent review (such as the 7-year retention of 2026-10-02) stay within
`patient-info-v1`.

## Keeping these documents

- Every document keeps the review banner at its top until the independent review is done.
- Every document that states a record-keeping rule cites every state and territory, from
  the research below only; anything the research does not cover is marked
  **[Reviewer: …]** rather than stated.
- Plain English for the practitioner and for patients: no file names, program names
  from inside the app or technical identifiers — except where a line quotes the app's
  own screen word for word, so it can be matched.
- No promise the app cannot keep — for example, the app never ticks or fills Cliniko's
  consent field, and nothing it keeps has a backup.
- The patient information's version (`patient-info-v1`) and the app's consent tick are
  versioned separately (above).

## What the drafts rely on

The research behind these drafts was done on 2026-10-01. Nothing here goes beyond it;
where it runs out, the documents say so.

- **Ahpra, "Meeting your professional obligations when using AI in healthcare".** It sets
  no retention period for transcripts. It asks practitioners to tell patients about the
  AI tool, to obtain informed consent and ideally note the patient's response in the
  health record, to check the accuracy of records the AI creates, and to store data as
  the law requires.
- **State and territory health-records law.**

  | Where | Law | Keeping health records |
  |---|---|---|
  | Victoria | Health Records Act 2001 | At least 7 years from the last contact, or until the patient turns 25 if they were a child |
  | New South Wales | Health Records and Information Privacy Act 2002 | At least 7 years from the last contact, or until 25 for a child |
  | Australian Capital Territory | Health Records (Privacy and Access) Act 1997 | At least 7 years from the last contact, or until 25 for a child |
  | Queensland, South Australia, Western Australia, Tasmania, Northern Territory | No separate private-sector health-records Act was identified in this research; the Privacy Act 1988 (Cth) Australian Privacy Principles apply | APP 11.2: destroy or de-identify information that is no longer needed. APP 12: patients can ask for access. The research found no fixed minimum period for these places |

  APP 12 access applies everywhere. The research did not cover public-sector rules,
  professional-board record-keeping codes beyond Ahpra's AI guidance, or the law
  outside Australia.
- **AJGP 2025, "Is AI A-OK?".** Many AI scribes keep no audio and delete transcripts
  within 7–30 days. It points out that a transcript holding health information that is
  not carried into the record sits in tension with the retention laws above.
- **Heidi Health** (a comparison point, not an authority). It never keeps audio. Its
  retention is set by the user: one of its blog pages says 1–90 days; its compliance FAQ
  says 1 day to "never delete", with "never delete" as the default (checked 2026-10-01).
  Clinic Scribe's default — keep past sessions until the practitioner deletes them —
  follows that FAQ.

The app's own warning beside the retention setting cites the same Victorian, NSW and ACT
Acts, APP 11.2 and APP 12, says a kept transcript is kept for at least 7 years, and says a
child's transcript must be kept until they turn 25. If the law cited here changes, change
the app's warning and these documents together.

## Answered by the practitioner

- **Is a kept transcript a health record that must itself be kept for the state minimum?**
  Answered by the practitioner on 2026-10-02: **yes — a kept transcript is kept for at
  least 7 years**, the Victorian, NSW and ACT minimum. What the app now offers:
  - The Past sessions setting has two choices only: "Until I delete them" (the default)
    and "7 years". The shorter choices it once offered (1, 7, 30 or 90 days, 1 year) are
    gone; a setting saved with one of them is read as 7 years, and the Past sessions tab
    says so until the setting is saved again.
  - The app does not know a patient's age. For a patient who was a child, the transcript
    must be kept until they turn 25, so the practitioner chooses "Until I delete them"
    when that applies — the app's warning says so.
  - **Delete now** stays, but only for a recording made in error: the wrong patient, a
    test, or one recorded without consent. Its confirmation says so.
  - **[Reviewer: confirm the 7-year minimum for a kept transcript, and whether a
    recording made in error may be deleted early; and whether a patient's request to
    delete a kept transcript can be granted early.]**

## Open questions for the independent review

- **Consent for people who cannot consent for themselves** (children, people with
  impaired capacity) and for other people in the room (a parent, carer, interpreter or
  student).
- **Whether the audit record's Cliniko identifiers** (treatment note, appointment,
  practitioner and user ids — no names, no text) make the exported CSV personal
  information in the practice's hands. These drafts treat it as such.
- **Wording for each state** if the product is sold outside Victoria.
