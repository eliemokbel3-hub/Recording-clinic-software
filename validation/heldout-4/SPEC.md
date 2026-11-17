# Held-out set 4 — the author's brief (validation-run7 plan, Task 0.8, 2026-10-26)

You are writing a small set of INVENTED, synthetic physiotherapy consultation scripts. Nobody real is in them: invent every name, detail and conversation. A text-to-speech program speaks each script aloud in two or three computer voices; a speech recogniser transcribes the audio; a clinical scribe app turns the transcript into a draft treatment note; a test harness then checks the note against the facts you list in each script. Your scripts are a HELD-OUT test: nobody who builds the app reads them before the app is finished, and they are never edited to make the app pass. Write what real consultations sound like, in your own words, not what you guess the app expects.

Work only in this folder. Write each script as `h4-NN.json` here (`h4-01.json`, `h4-02.json`, …), **20 to 25 scripts**, and one file `AUTHOR-NOTES.md` (described at the end). There is nothing else to read: this brief and the format example in it are all you get.

## What the app does, in behaviour terms

1. **The note.** The app puts a line of the transcript into a section of the note when the line contains one of the section's cue phrases (listed below). It also has a broader built-in phrase layer you cannot see. A clinician's line that contains no cue can be left out of the note altogether — that is the main gap this set measures. Anyone else's line must carry its clinical facts with a cue phrase (rule 1).
2. **The next patient.** Sometimes the recording keeps running after a consultation ends: the clinician sends one patient off, then welcomes the next one, and the next patient starts talking. The next patient's role is `next_patient`. The app should stop the note where the first consultation ends, so nothing the next patient says reaches the first patient's note.
3. **A speaker fixing what they just said.** A speaker states something, then puts it right in their very next line. The note should keep the fixed version together with the line it fixes.
4. **Doubt.** When a patient (or anyone who is not the clinician) is unsure of what they are reporting, the note should mark that line so the clinician checks it. A clinician who hedges is giving the clinician's own judgement and is not marked.
5. **Numbers.** Medicine doses and other numbers must reach the note exactly as said.

## What the set must cover (spread across the 20–25 scripts; one script can cover several)

- **Uncued clinician lines** that matter clinically: advice, the plan, safety-netting (what to do if things get worse), home exercise descriptions in your own words, findings described without any cue phrase. At least 8 scripts, several such lines in total, each carrying a material fact.
- **The next patient** — at least 6 scripts where, after the first consultation ends, the clinician welcomes a NEW person who then says something clinical (their own complaint). Vary how people end a consultation and how they welcome someone: everyday, formal, brief, regional, by name, with or without small talk in between. The next person is a third role, `next_patient` (see the format).
- **Negatives for the next patient** — at least 5 scripts where it must NOT be treated as a new patient: a consultation that ends with no one new being welcomed; the same patient coming back after leaving ("oh, one more thing"); words people use to welcome someone, used mid-consultation for another purpose; time-of-day words used clinically ("morning stiffness", "evening pain"); a partner or receptionist joining who is not a new patient.
- **Doubt** — at least 6 scripts with a patient voicing doubt about something they report, in varied everyday ways of your own (not one stock phrase; one way of voicing doubt per line that carries it). Include doubt carried in a SEPARATE short line after the fact, and doubt placed in the middle of a long line. Also include confident lines that contain words which can look like doubt but are not, and at least 2 clinician lines where the clinician hedges.
- **A speaker fixing what they just said** — at least 4 scripts: a fix of a side (left/right), of a number, and of a time; at least one fix that opens with a filler word such as "um" or "er"; at least one line that is NOT a fix even though it starts like a fix.
- **A dose read aloud** — at least 3 scripts where the clinician reads a medicine, strength and frequency aloud (say numbers the way people say them; write digits for strengths, e.g. "400 milligrams").
- **An afterthought clause** — at least 3 scripts where a material fact sits only in a short clause tacked onto the end of a line after a comma (the kind of clause a speaker trails off on).
- Mix appointment types and body regions; some scripts short (5–7 lines), some long (15–25 lines). Each script lists 3 to 6 facts.

## The cue phrases (the note's own layer)

A line goes to the FIRST section, in this order, whose cue phrase it contains as consecutive words (case and punctuation ignored). The four sections marked **(clinician only)** admit only the clinician's lines that are not questions; every other section admits anyone's line.

| Section | Cue phrases |
|---|---|
| presenting complaint | coming in with |
| history of the complaint | did it start |
| progress since last visit | from last time; since last time |
| past medical history | previous surgery; previous surgeries |
| red flags | any numbness; tingling; going to the toilet |
| examination | have a look |
| outcome measures | (none) |
| assessment **(clinician only)** | pretty tight; reduced range |
| diagnosis **(clinician only)** | i think you have; i think what's going on |
| treatment performed | massage; needles; cups |
| response to treatment | moving a bit better |
| advice and home exercise **(clinician only)** | send you some exercises; exercises |
| management plan **(clinician only)** | going to take |
| consent | for a crack |
| referrals | see a gp |
| precautions | no running; no lifting |
| follow-up | see you next week |

## Rules every script must meet (checked mechanically after you finish)

1. **Anyone but the clinician states a clinical fact with a cue phrase.** Split the line at every `.` `?` `!` `,` `;` followed by a space. Two kinds of fact must lie inside at least one clause that contains a cue phrase of a section that speaker is admitted to (a patient line can never route to the four clinician-only sections; nor can a clinician's question): every fact marked `expect_uncertain`, and every fact with `"material": true` of kind `present`, `negation`, `laterality` or `dose` on a line spoken by anyone other than the clinician. In plain words: when anyone other than the clinician says something clinically important, say it with one of the cue phrases of a section open to that speaker. The clinician's own lines need no cue. The words carrying the doubt can be anywhere in the line, or in a separate line.
2. **Never say these word runs** anywhere, in any line: "standard strapping", "usual pain relief", "standard advice sheet" (filler words like "um" do not break a run).
3. **A fact never borders a repeat of its own edge word.** Reading all the lines' words in order as one stream, the word just before a fact must not equal the fact's first word, and the word just after it must not equal the fact's last word (e.g. not "left left knee" across a line break).
4. **Synthetic conditions are always present** (see the format), and every script has at least one fact with `"material": true`.
5. Each file's name is its `encounter_id` plus `.json`; ids are `h4-01`, `h4-02`, … with no gaps.
6. **The next patient's role.** The role `next_patient` is used for the new person in a next-patient script and for no one else, and only in a script tagged `end_and_new_patient`. Every fact on the next patient's first line, or on any line after it, is `absent`.
7. **Size.** 20 to 25 scripts; each script lists 3 to 6 facts.

## The format

Each script is one JSON object:

- `schema_version`: `1`.
- `encounter_id`: `"h4-NN"`.
- `appointment_type`: one of `initial`, `follow_up`, `acute`, `chronic`, `post_operative`, `discharge`.
- `axes`: one or more tags naming what the script tests, from `negation`, `laterality`, `numbers`, `small_talk`, `uncertain`, `contradictory`, `scribe_instruction`, `end_and_new_patient`, `noise`, `overlap`, `rate` (unique). `noise`, `overlap` and `rate` must match the conditions (below) exactly: tag `noise` if and only if `snr_db` is set, `overlap` if and only if `overlap_lines` is set, `rate` if and only if `rate` is not 0.
- `lines`: in speaking order, each `{"role": ..., "text": ...}`. Roles are lower-case words with underscores. One role must be `clinician`; the patient is `patient`; the new person in a next-patient script is `next_patient`; any other third person has a role that says who they are (`partner`, `receptionist`, …). At most three roles per script.
- `facts`: what the harness checks, each `{"kind", "tokens", "line", "material"}` and optionally `"expect_uncertain": true`.
  - `line` is the 0-based index of the line holding the fact.
  - `tokens` are the fact's words exactly as they appear consecutively in that line, each lower-cased with leading and trailing punctuation removed (an inner apostrophe stays: `"it's"`), and without the filler words um, uh, uhm, erm, er, ah, mm, mmm, hmm, mhm. 1 to 12 words.
  - `kind`: `laterality` (a side), `dose` (a medicine dose), `negation` (something denied, e.g. "no numbness"), `present` (any other clinical fact that must reach the note), `absent` (words that must NOT reach the note: small talk, the next patient's complaint, an instruction spoken to the scribe).
  - `material`: `true` for anything clinically important, including the next patient's complaint (an `absent` fact). `false` for a minor detail or small talk.
  - `expect_uncertain`: `true` only when the speaker voices doubt about that very fact. Never on an `absent` fact.
- `expected_warnings`: leave it out.
- `conditions`: always present.
  - `voice_slots`: **the clinician is always voice 0**, the patient voice 2, any third role voice 1 (a different number per role; nothing above 2).
  - optional: `rate` (−10 to 10, speaking speed; 0 = normal), `snr_db` (0 to 60: background noise, lower is noisier), `overlap_seconds` (up to 5) with `overlap_lines` (the line indices that start that many seconds before the previous line ends; ascending, never two consecutive indices, never a line that continues the same role as the line before). Use these on a few scripts only.

### The one format example (do not reuse its wording or scenario)

```json
{
  "schema_version": 1,
  "encounter_id": "example-01",
  "appointment_type": "follow_up",
  "axes": ["laterality", "numbers", "small_talk", "uncertain"],
  "lines": [
    {"role": "clinician", "text": "How has the ankle been since last time?"},
    {"role": "patient", "text": "Since last time it swells up in the evenings, though I couldn't swear it's every evening."},
    {"role": "clinician", "text": "Let me have a look. The left ankle is puffy around the outside bone."},
    {"role": "patient", "text": "My daughter's wedding is on Saturday, so I need it to behave."},
    {"role": "clinician", "text": "You're going to take ibuprofen 200 milligrams three times a day with food for one week."},
    {"role": "clinician", "text": "No running until the swelling settles."}
  ],
  "facts": [
    {"kind": "present", "tokens": ["swells", "up", "in", "the", "evenings"], "line": 1, "material": true, "expect_uncertain": true},
    {"kind": "laterality", "tokens": ["left", "ankle"], "line": 2, "material": true},
    {"kind": "absent", "tokens": ["daughter's", "wedding"], "line": 3, "material": false},
    {"kind": "dose", "tokens": ["ibuprofen", "200", "milligrams", "three", "times", "a", "day"], "line": 4, "material": true},
    {"kind": "present", "tokens": ["until", "the", "swelling", "settles"], "line": 5, "material": false}
  ],
  "conditions": {"voice_slots": {"clinician": 0, "patient": 2}}
}
```

## `AUTHOR-NOTES.md`

One short paragraph per script: what it tests; the 0-based line where the next patient starts (or "none"); the lines where a speaker fixes what they just said, each with the line it fixes; the lines where someone other than the clinician voices doubt; and anything you were unsure how to encode. These notes are read only after the app is built.

When every file is written, reply with one line: `DONE <number of scripts>`.
