# Speaker measurement (Task 2.3 harness)

How the practitioner measures speaker-cluster and clinician-role accuracy on their own labelled recordings, before and after the Task 2.1 cepstral mean normalisation, through the shipped transcription pipeline — and, since the practitioner-profile plan's Task 2.4, with the voice profile applied (the `enrolled` condition). Built as Phase 3A Task 2.3a (2026-09-04); the numbers it produces are what Task 2.3 records, what decision D-S1 (estimated-k speaker counting) is decided on, and what the practitioner-profile plan's Phase 6 re-checks the attribution threshold against. Code: `desktop/src/scribe_desktop/speaker_eval.py`, launcher `scripts/measure-speakers.py`, tests `desktop/tests/test_speaker_eval.py`.

## Preparing a recording

1. Record or export the consultation as a WAV file: **16 kHz, mono, 16-bit PCM**. In Audacity: Project Rate 16000, Tracks ▸ Mix ▸ Mix Stereo Down to Mono, File ▸ Export Audio ▸ WAV 16-bit PCM. Any other rate, channel count or sample width is refused per file with the conversion recipe; a header-only, truncated or partial-frame data chunk is refused too. The harness does not resample (practitioner decision 2026-09-03).
2. In Audacity, add one label per stretch of speech with a **role name** as the label text (`clinician`, `patient`, `parent`, `carer`, `interpreter`, …), never a real name. Exactly one distinct label must be `clinician`; case variants of any role name are refused, with the spellings named, rather than silently merged. File ▸ Export ▸ Labels writes the tab-separated track; save it as `<name>.txt` beside `<name>.wav`. Point labels and Audacity's `\`-prefixed spectral rows are ignored and counted.
3. Put every pair in one directory. A WAV without its label track, or vice versa, is reported and skipped.

Recordings must be mock or consented (a real consultation cannot be retained — the app destroys session audio at Complete); where they live and for how long is the practitioner's retention decision, still open in the plan. The harness never writes, moves or deletes the WAV or label files.

## Running it

From a normal terminal (never an agent shell — those cannot see the model cache, see `docs/lessons.md`), with the models already downloaded by `scripts/setup-models.py`:

```bash
.venv\Scripts\python.exe scripts\measure-speakers.py <recordings-dir>
.venv\Scripts\python.exe scripts\measure-speakers.py <recordings-dir> --enrolment <me.wav>
```

It applies and asserts the offline kill-switches before constructing silero-VAD and the resolved Whisper model, then evaluates each pair in turn. Output is a Markdown table on stdout, headed by the resolved Whisper model name, ready to paste into the plan's Task 2.3. Progress and error lines name files and exception types only; nothing from a recording is printed or logged, and the result types carry no transcript words. Exit status is 0 only when every pair was scored and no error occurred; a failing recording is reported and the run continues.

### The enrolled condition (practitioner-profile plan Task 2.4)

`--enrolment <wav>` takes a **16 kHz mono 16-bit PCM** WAV of the practitioner reading aloud (about 30 s of speech; the same format rule as the recordings, refused otherwise). The harness runs the shipped `enrolment.enrol` over it with the shipped speaker embedder (the pinned WeSpeaker model — an absent model is an error under this flag, with the setup-models remedy) and wraps the vector in an **in-memory** profile that is never written anywhere: the harness imports no profile store and owns none, so the custody statement below is unchanged. Each recording is then run through the shipped `transcribe_session` a second time with that embedder and profile over the same temporary store — the first pass's window transcriptions are replayed from memory, so no second Whisper run is paid — and its labels are the `enrolled` condition. All-`speaker_1` there is not "merged": it is scored like any other output, because it may mean every segment matched the profile (the false-positive case the condition exists to measure) or a degenerate clustering after no segment matched — the labels alone do not say which; the `Auto-confirm` verdict and the `Similarity` column do. The legacy two conditions keep their merged semantics. A second pass that segments the store differently is reported as a harness fault, never a number.

Without `--enrolment`, given two or more pairs, the documented fallback enrols each recording **leave-one-out** from the clinician-labelled spans of the *other* recordings (a recording never contributes to its own enrolment); with one pair and no enrolment WAV the condition is absent and the run says so. The fallback is a stand-in — its enrolment audio comes from consultation recordings rather than a read-aloud — so the dedicated enrolment WAV from the plan's Task 6.1 is what Phase 6 records.

The enrolled condition adds two verdicts to the table: `Auto-confirm` — CORRECT when the cluster the voice profile confirmed (the transcript's `enrolled_speaker`, exactly what the Transcript screen pre-checks under D4) has `clinician` as its duration-weighted majority true label, WRONG otherwise, NONE when the document carries no attribution — with the confirmed label beside it, and `Similarity`, that cluster's mean raw cosine against the enrolment vector (the number the practitioner sees on the confirmation line). The heuristic `Role` verdict is still computed for the enrolled labels, so the manual path's suggestion can be compared with the auto-confirm on the same recording.

## What is measured

Each recording is written into a fresh temporary encrypted session store under `%TEMP%` with a real DPAPI-wrapped key and run through `transcribe_session` unchanged — its speaker labels are the **after** condition, exactly what the app would show. The **before** condition re-embeds the same VAD segments with `label_speakers(..., cepstral_mean_normalisation=False)`, so the two conditions differ by precisely the Task 2.1 line; a self-check confirms the harness's re-embedding of the after condition reproduces the pipeline's labels, and a mismatch is reported as a harness fault rather than a number.

Alignment: a VAD segment's ground truth is the label with the largest overlap against `[start, end)`; a segment with no overlap is unlabelled (excluded, counted); one whose majority label covers under 80 % of its overlapped duration is mixed (scored by majority, counted); an exact duration tie is no majority. Both counts bound the achievable accuracy and are printed.

Metrics per condition: cluster accuracy under the best injective mapping from predicted clusters to true roles (duration-weighted and by count); the seconds confusion matrix predicted × true, where a third voice's merge into two clusters becomes visible; per-cluster purity; predicted versus true speaker count; and the role outcome — CORRECT when the preselected clinician cluster's majority true speaker is `clinician`, WRONG otherwise (including no majority), NONE when `speaker_role` makes no preselection — with the margin and the clinician's talk-time share, which Task 2.2 flagged for this measurement to confirm or reverse. Every reported number is computed from the multiset of per-pair durations through one correctly-rounded summation, so renaming or reordering labels cannot move it.

## Custody of the temporary store

Teardown runs key-first on every path — unlink `key.dpapi`, destroy the in-memory key, remove the session directory, remove the temporary root — with every leg attempted whatever the earlier legs did. It returns normally only when the root is positively gone, the key is destroyed and no leg failed; otherwise it raises a fault naming the temporary path, the key state and every leg failure, chained to whatever exception was already in flight. What it cannot do is delete or inspect what the OS refuses: that residue is named for by-hand removal, never hidden. The exact contract is the module docstring of `speaker_eval.py`; `docs/security/retention-schedule.md` carries the row.
