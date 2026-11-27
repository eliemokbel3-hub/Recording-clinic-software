# Feature Implementation Plan
**Feature:** capture-overflow
**Overall Progress:** `75%` (15 of 20 tasks)

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `plan-installation.md` (its retained follow-up "a larger PortAudio input buffer", recorded 2026-10-03, round 35 MED-001; this plan is that follow-up, triggered by its own trigger).
- Follow-up plans: None

## Goal
A short stall of the microphone callback no longer ends a recording, and the next overflow says in numbers what kind it was. Version 0.4.3, a patch build ahead of 0.5.0. The rule that dropped frames end a recording with a clear message, never a silent gap, is kept.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable (`claude-fable-5-2`); executor Opus-class (`claude-opus-5-5`) through `/execute` in one session; cross-family peer codex. Tier-gap dosing applied: the design decisions, the log-line contract, the measurement rule, the edge-case inventory and per-task acceptance criteria are fixed below so the executor designs nothing.

### Agreed Scope (Build Now)
- A practitioner-run measurement of this computer's microphone stream, under a rule frozen in this plan before the run (Phase 0).
- One constant, `audio_capture.INPUT_LATENCY_SECONDS`, passed as the recording stream's `latency=` on MME, with a one-retry fallback to today's behaviour (D1, D2, D5).
- Numbers-only diagnostics for recordings: the largest recent callback gap on a capture failure; an opened line, a closed line and a line for a close that lands inside a stall (D4).
- The Microphone list shows MME entries only (D8; the practitioner's "Include in plan (Recommended)", 2026-11-26).
- Version 0.4.3, its documents, a build of record, the install during the ten Task 9.1 consultations (D6).

### Deferred — Actionable Later
- **Hold Pause and Finish until audio waiting behind a stalled callback has arrived** (the practitioner's "Defer (Recommended)", 2026-11-26).
  - Why deferred: it changes the pause and stop barrier in `CaptureWorker`, the most review-heavy part of capture, for a case that needs a stall and a press inside the same few seconds.
  - Intended future outcome: no audio is dropped at a Pause or Finish that lands inside a stall.
  - Relevant files / subsystems: `desktop/src/scribe_desktop/audio_capture.py` (`CaptureWorker.pause`, `.stop`, `_on_block`).
  - Dependencies / prerequisites: this plan's `state=backlog_dropped` line (D4).
  - Recommended next action: plan it when the trigger fires.
  - Risk if deferred: correctness: up to the buffer's length of audio before the press is dropped without a flag (D3's named residue); before 0.4.3 the same stall ended the recording.
  - Revisit by: the first `capture_stream state=backlog_dropped` line in an installed log
  - [2026-11-27, the security review's SEC-003 and SEC-004] Widened to Resume: a stall straddling Resume can put up to about 2.5 s of sound captured while paused into the recording, unlogged; the practitioner accepted it by name ("Accept, name it (Recommended)"), and the same fix (dropping audio by the time it was captured) covers both directions. The `state=backlog_dropped` line's two limits (it misses a stop just after a stall, and it appears after a device loss) are stated in the threat model; widening the line's rule would be a new dated D4 sentence, not built.
- **Find and remove the stall's cause** (the practitioner's "Defer (Recommended)", 2026-11-26).
  - Why deferred: nothing has measured how long real stalls are; the new lines supply that first.
  - Intended future outcome: ordinary recordings run with callback gaps near 100 ms.
  - Relevant files / subsystems: the live worker's decode threads (`transcription.py` `WhisperSpeechProvider`, no `cpu_threads` set), the bundled OpenMP runtime's spin time, Python's garbage collector, thread priority.
  - Dependencies / prerequisites: installed 0.4.3 and some weeks of `state=closed` lines.
  - Recommended next action: read the lines at Task P.4; plan from the numbers.
  - Risk if deferred: ux-degradation: the buffer covers a stall, it does not remove it.
  - Revisit by: a `state=closed` gap above half of `INPUT_LATENCY_SECONDS` (and under 30 s), or another overflow whose `duration_ms` is above 300
- **An overflow with normal callback gaps** (the practitioner's "Defer (Recommended)", 2026-11-26).
  - Why deferred: it would mean the driver or Windows reported the break; no evidence of one exists.
  - Intended future outcome: a fix chosen on that evidence (driver, sound interface).
  - Relevant files / subsystems: `audio_capture.py`; Windows sound settings.
  - Dependencies / prerequisites: one such logged overflow.
  - Recommended next action: none until the trigger.
  - Risk if deferred: ux-degradation: such a break still ends the recording with a clear message.
  - Revisit by: a `capture_failure … detail_code=status_input_overflow` line whose `duration_ms` is 300 or less
- **Clinic 2's computer** (the practitioner's "Defer (Recommended)", 2026-11-26).
  - Why deferred: that install waits on its Cliniko key, and a clinic-only computer has no Python to run the script.
  - Intended future outcome: its first recording's opened line reads `detail_code=mme`, the requested buffer and no `state=default_latency`.
  - Relevant files / subsystems: the installed log there.
  - Dependencies / prerequisites: clinic 2's install (`plan-installation.md` retained item).
  - Recommended next action: add the check to clinic 2's P.1.
  - Risk if deferred: minor: the constant was chosen on this computer's microphone.
  - Revisit by: clinic 2's install
- **A different microphone or sound interface on this computer** (a headset, a new default).
  - Why deferred: nothing changes today.
  - Intended future outcome: the script re-run on the new device before it is used for clinical recordings.
  - Relevant files / subsystems: `scripts/measure-capture-stall.py`.
  - Dependencies / prerequisites: none.
  - Recommended next action: run the script with `--device`.
  - Risk if deferred: minor: an unmeasured device may honour the buffer differently; the opened line shows the request and any fallback.
  - Revisit by: a new input device on this computer

### Excluded — Revisit Only If Needed
- **A larger block size, a blocking read in a thread, a different host API, exclusive mode, `sys.setswitchinterval`, tolerating or repairing an overflow.**
  - Why excluded: each changes more behaviour than one stream argument, or does not help (a blocking reader still needs the interpreter lock; the switch interval does nothing for a held lock), or breaks the never-silent-gap rule.
  - When to revisit: only with the "normal gaps" deferred item.
  - Relevant files / subsystems: `audio_capture.py`.
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- **Enrolment and the Microphone tab's level monitor keep today's small buffer** (the practitioner's "Accept (Recommended)", 2026-11-26).
  - Why accepted for now: an overflow there fails safe and visibly: the meter stops with a message until Refresh or a new choice of microphone, and the guided enrolment ends with nothing saved (corrected 2026-11-27 from the security review's SEC-005); the always-open monitor would otherwise hold about 2.5 s of room audio in memory instead of 0.2 s.
  - Risk if assumption becomes false: an enrolment part fails more often than is tolerable.
  - Trigger for revisit: an enrolment part fails with "microphone failed".
  - Recommended next action: give the enrolment stream the buffer (a second backend instance in `MainWindow`).
- **The stream is on MME and PortAudio's MME code behaves as its source reads** (buffer count = ceil(latency ÷ 0.1 s) + 1, one callback per 100 ms, an overflow flag only when every buffer is full).
  - Why accepted for now: read from PortAudio's `master`; the bundled library calls itself "V19.7.0-devel, revision unknown". Phase 0 measures it before anything is built.
  - Risk if assumption becomes false: Phase 0's premise or rule fails and Task 0.3 is a decision gate; nothing is built on the assumption.
  - Trigger for revisit: Task 0.2's table.
  - Recommended next action: none before Task 0.2.
  - Revalidated 2026-11-26 (Task 0.2's block): the device is on MME, the callback keeps its 100 ms cadence at every buffer, and each buffer covered the stalls its count predicts (2.0 flagged a 2.0 s stall in 10 of 10 trials, 2.5 in none). The measurement confirms the behaviour on this computer; the library's source was still not read.
- **2.0 s is a sufficient stall to survive.**
  - Why accepted for now: a judgement. It is ten times today's tolerance (about 0.2 s) and far under the 25 s queue bound and the 10 s control timeout; the log gives no stall length.
  - Risk if assumption becomes false: a longer stall still ends a recording, with its length now logged.
  - Trigger for revisit: an overflow whose `duration_ms` exceeds the buffer.
  - Recommended next action: a new dated decision with the measurement repeated (D1).

### Key Design Decisions
- See `Design Decisions` (D1–D9). The practitioner's decisions of 2026-11-26: "0.4.3 first (Recommended)", "Install when ready (Recommended)", "Yes, amend C13 (Recommended)", "One session, /execute (Recommended)" (D6); "Include in plan (Recommended)" (D8); the four deferrals and the acceptance above; "Neither (Recommended)" for the two exploration notes in the plans folder; "Nothing, lock it (Recommended)".
  - Why: each is recorded where it applies.
  - Alternatives rejected: on the decisions.
  - Still applies to follow-up work: Yes

## Key Findings

### Files / Symbols Involved
- `desktop/src/scribe_desktop/audio_capture.py`
  - `SoundDeviceBackend.list_input_devices` (169–184): every host API's input entries, no filter.
  - `SoundDeviceBackend.open_stream` (186–238): `sd.RawInputStream(samplerate=16000, blocksize=1600, device, channels=1, dtype="int16", callback, finished_callback)`, no `latency=`. The callback (196–209) delivers the block, then reports a truthy status as `CaptureOverflowError(detail_code=status_detail_code(status))`. `finished` (211–220) reports `DeviceLostError` unless `handle.stopped_by_us`. If the constructor succeeds and `start()` raises, the stream is not closed (an existing gap).
  - `_SoundDeviceStream.stop` (156–163): `abort()` then `close()`.
  - `AudioCaptureError` (67–73), `CAPTURE_DETAIL_CODES` (54–64), `CaptureWorker` (334–550): `_on_block` drops blocks once paused, failed or stopped (410–411); `_on_error` ignores a flag once failed or stopped (421–422) but not while paused.
- `desktop/src/scribe_desktop/session.py`: `CaptureWorker(self._backend, …)` at 980; `_on_capture_failure` (2381–2412) logs `capture_failure` with `session_id`, `session_state`, `error_code`, `detail_code`.
- `desktop/src/scribe_desktop/app.py`: ONE `SoundDeviceBackend()` (786) goes to the controller (794) and to `MainWindow` (838), which feeds the level monitor (`ui/main_window.py:573`) and enrolment (`:650`). `logger` is in scope there.
- `desktop/src/scribe_desktop/ui/microphone.py`: the idle level monitor is open whenever the app is not recording or enrolling (timer from construction, 176–179); the level bar polls every 100 ms; the combo labels entries by name only (214–216). `ui/practitioner.py:868` lists devices the same way.
- `desktop/src/scribe_desktop/logging_setup.py`: `ALLOWED_KEYS` (44–66) has `duration_ms`, `count`, `device_id`, `state`, `detail_code`, `session_id`; `log_event` (563–573) sorts keys and takes `str | int | float`. No tripwire signature is a substring of the new lines.
- `desktop/src/scribe_desktop/exclusions.py`: `check_tool_wer` (595) and `tool_wer_refusal_line` (627), the crash-report refusal `speaker_eval.py:1461–1464` uses. `replay_kept.py:183–204` shows how a tool takes the app's single-instance exclusion.
- Tests: `desktop/tests/test_audio_capture.py::TestSoundDeviceBackendCallback` (314–430, the fake `sounddevice` module); `test_live_session.py:930–957` pins the `capture_failure` line; four `main()` tests replace the backend with `"SoundDeviceBackend": lambda: object()` (`test_audit.py:1706` and `:1927`, `test_exclusions.py:1343`, `test_hands_free.py:697`). Scripts are loaded in tests by `importlib.util.spec_from_file_location` (`test_measure_suggestions.py:52–60`).

### Codebase Integration Notes
- **The trigger (2026-11, installed 0.4.2, content-free log lines only).** One `capture_failure detail_code=status_input_overflow error_code=CaptureOverflowError` line, the first since 0.1.1. It came well into a recording, with the app long open (corrected 2026-11-27 from the security review's SEC-007: the earlier wording named the recording's elapsed time and its place in the day, against C2). It was not at Start (so not the start-up import stall that `ml_warmup.py` fixed) and not on a 15-minute sweep tick. `failed` followed 0.78 s later, inside the live worker's 1 s in-lock stop, so the live worker was probably mid-window: weak evidence, not a diagnosis. The day and times stay off the repository (`plan-clinic-smoke.md` D12).
- **Nothing in the app's own code explains a stall of hundreds of milliseconds mid-recording.** The live worker builds its models once at Start; its per-window work does not grow with the recording; the live view appends; every timer is small; there is no `gc.` or `sys.setswitchinterval` use. The candidates are outside the project's code (the "stall's cause" deferred item).
- **The worktree.** This plan is built on the branch `claude/dreamy-brahmagupta-2ebc65` in `C:\Recording clinic software\.claude\worktrees\plan-run3-leftovers-8f7c7f`, which has no `.venv` and no `extension\node_modules`. The main venv's editable install points at the MAIN checkout's `desktop\src`, so every QA run sets `PYTHONPATH` to this worktree's `desktop\src` and runs the main venv's tools from the worktree's `desktop\`; a run without it silently tests `main` (the UI refresh's R8).
- **Other work in flight.** The backup run (`loop/past-sessions-backup-20261126-063148-9edc`, its own worktree, version files already 0.5.0) edits `app.py` (hunks clear of line 786) and `desktop/tests/test_audit.py` (the two stand-ins are at 1711 and 1932 there). It will meet this plan at its merge of `main`: those two files, the five version files, `CHANGELOG.md`, `AGENTS.md`, `docs/release/pilot-builds.md`, the security documents. The stronger-voice run is in Task P.4 and commits to `main`.
- **Line endings.** `AGENTS.md`, `CHANGELOG.md`, `docs/security/threat-model.md` and `docs/security/data-flow-map.md` are CRLF in the working tree; check `git ls-files --eol` for every document edited.
- **Critique gate (2026-11-26, three read-only lenses).** Coverage: issues found and folded in (the gap window, the consultation's day kept out, the four test stand-ins, the monitor's log noise, the findings-register row, the stall-at-press residue). Practicality: issues found and folded in (the read-back latency is constant on MME, the 2.0 s candidate sits on its own threshold, `stop()` does not drain, non-MME entries raise no flag, the worktree workflow). Simplicity: the core kept; the diagnostics narrowed to recordings, the stall helper's unit test replaced by a self-check, no rollback section, a shorter mock.

### External / API Findings
From PortAudio `master` (`src/hostapi/wmme/pa_win_wmme.c`, `pa_win_ds.c`, `pa_win_wasapi.c`, `pa_win_wdmks.c`) and `sounddevice` 0.5.5 as installed; read 2026-11-26, to be confirmed by Phase 0.
- The bundled library has MME, DirectSound, WASAPI and WDM-KS; the default is MME. A 16 kHz shared-mode WASAPI open without auto-convert is refused unless the device's mix format is 16 kHz.
- MME input: host buffer = the 1600-frame block; count = ceil(latency ÷ 0.1 s) + 1, minimum 2, no cap; one callback per buffer whatever the count. `sounddevice` passes the device's "high" default, 0.18 s on MME, so 3 buffers and about 0.2 s of tolerance today. An overflow is flagged only when every buffer is full, and the flag is handed to the callback AFTER the one that ran late.
- `stream.latency` on MME (and DirectSound) is the minimum buffering, 0.1 s, whatever was asked: it cannot show the buffer.
- `Pa_StopStream` on an input-only MME stream does not deliver the backlog; `Pa_AbortStream` discards it. Steady-state tail loss at a stop is 0 to 100 ms whatever the count.
- DirectSound and WASAPI never raise an input-overflow flag: a stall there would lose audio silently. WDM-KS does raise it, but takes the latency as its packet size (bursts).
- `ctypes.PyDLL` calls keep the interpreter lock; cffi callbacks take it; every `Pa_OpenStream` or `Pa_StartStream` failure is `sd.PortAudioError`.

## Planned Workflow Summary

### Flow 1 — Measure, then choose
The practitioner runs the script from a normal terminal with both builds closed, outside clinic hours. It opens the microphone the way the app does, keeps no audio, and prints a paste block of numbers. The rule frozen in D5 picks the buffer, or stops the plan at a decision gate.

### Flow 2 — A recording on 0.4.3
Start opens the recording's stream with the buffer and logs one opened line. A callback that runs late no longer drops frames until the buffer is full. Finish logs the longest gap seen. If frames are still dropped, the recording fails exactly as today and its failure line carries the largest recent gap.

### Flow 3 — Release
Build, smoke from the worktree, documents and version, hardening, then on the practitioner's word: `main` moved, pushed, built of record, verified, installed during the ten with shadow mode on.

## Design Decisions
- **D1 — One constant, recordings only.** `audio_capture.INPUT_LATENCY_SECONDS` is passed as `latency=` when the device's host API is MME. `SoundDeviceBackend` takes `input_latency: float | None` (default the constant); the level monitor's and enrolment's instance is built with `None` and opens exactly as today. Block size, rate, format, the 25 s queue and every failure path are unchanged. After Task 0.3 the value changes only by a new dated decision with Phase 0 repeated.
  Alternatives considered: the buffer for every stream (more room audio held at idle; rejected by the practitioner's acceptance above); a per-machine setting (nothing needs one yet).
- **D2 — Never worse than today.** If the open with the explicit latency raises `sd.PortAudioError`, from the constructor or from `start()`, the failed attempt is marked stopped by us and closed (errors ignored), then ONE open with the default follows. Each attempt has its own handle, so a failed attempt's `finished` callback never reports device loss. `state=default_latency` is logged only when the second open succeeds; a second refusal is today's `DeviceLostError(open_failed)`.
  Alternatives considered: no fallback (a refused buffer would then refuse every Start on that device, after the previous session is already retired).
- **D3 — The never-silent-loss rule, and its one new residue.** A truthy callback status still delivers its block and then fails the recording with the same message and log word; those tests are not edited. New residue, named in the threat model: audio still waiting behind a stalled callback when Pause or Finish is pressed is dropped without a flag, up to the stall's length and at most the buffer (before, that stall ended the recording); likewise audio captured during a pause can arrive after Resume. A close inside a stall is logged (D4). The full fix is deferred.
- **D4 — The log-line contract (numbers and fixed words only; logged for the recording's backend only, never from the callback).**
  - `capture_stream detail_code=<host> device_id=<n> duration_ms=<requested latency, ms> state=opened` — the explicit buffer was requested and the open succeeded.
  - `capture_stream detail_code=<host> device_id=<n> state=default_latency` — opened with the default: the host is not MME, or D2's retry succeeded.
  - `capture_stream count=<blocks> device_id=<n> duration_ms=<longest gap, ms> state=closed` — once per stream, in a `finally` after `abort()` and `close()`.
  - `capture_stream device_id=<n> duration_ms=<age of the last callback, ms> state=backlog_dropped` — before the closed line, only when at least one callback arrived and the last one is more than 250 ms old at the stop.
  - `capture_failure …` gains `duration_ms=<largest of the last three callback gaps, ms>` when the error carries one (`AudioCaptureError(gap_ms=…)`); every other failure's line is byte-identical to today's.
  - `<host>` is one of `mme`, `directsound`, `wasapi`, `wdmks`, `other`, mapped from `sd.query_hostapis(sd.query_devices(id)["hostapi"])["name"]`; anything unresolved is `other` (and opens with the default).
  - Reading rules: a large gap means the callback ran late (the interpreter lock, or Windows not scheduling the thread; a timestamp cannot separate them); a gap of 30 s or more most likely means the computer was asleep or locked, which the log cannot show, so it is read beside Windows' own power and lock events before a cause is named (corrected 2026-11-27, codex round 8's PR-LOW-001); an opened line with no closed line is a process exit.
  - The gaps come from an injected monotonic clock (`SoundDeviceBackend(clock=…)`), stamped at callback entry; statistics are per stream.
  - Each figure, exactly (added 2026-11-26 with peer round 3's class sweep): a *gap* is the time between two consecutive callback entries of one stream. `gap_ms` on a failure is the largest of the three most recent gaps at the moment the status is seen, the flagged callback's own gap included; with fewer than three gaps, the largest of those; with none (a flag on the first callback) the error carries no gap and the line no `duration_ms`. On the closed line `count` is the number of callbacks that stream received and `duration_ms` the largest gap of its life, 0 with fewer than two callbacks. The *age of the last callback* is the clock read at the top of `_SoundDeviceStream.stop()`, before `abort()`, minus the last callback's entry stamp; the backlog line is logged when that age is strictly more than 250 ms. On the opened line `duration_ms` is the explicit latency actually passed to that successful stream, the instance's `input_latency`, as `round(input_latency × 1000)` (the constant only by default; corrected 2026-11-26 from peer round 4, PR-LOW-002). Every logged time is `round(seconds × 1000)` as an int.
  Alternatives considered: logging from `SessionController` (four stop sites in the custody-critical file); logging every stream (the monitor's lines would carry sleeps and idle hours); the "granted" latency (constant on MME).
- **D5 — The measurement rule, frozen 2026-11-26 before any run.** The scoring stall is `time.sleep(S)` inside the callback (exact, repeatable). Candidates: 1.0, 2.0, 2.5, 3.0 s.
  - Premise: on the default row a 0.3 s stall raises a flag in at least 4 of 5 trials.
  - Choose the smallest candidate that meets all of:
    - (a) it opens, and in 10 of 10 trials a 2.0 s stall gives no flag and no lost block (the sampling protocol's `residual` below half a block);
    - (b) over 20 s the callback gap's median is 100 ms ± 20 ms, its 99th percentile at most 250 ms, with no flag;
    - (c) tail at `abort()` over 20 trials: the candidate's median minus the default's is at most 50 ms, and the candidate's maximum is at most 200 ms. Per trial, `tail_ms = (t_abort_call − t_first_callback) × 1000 + 100 − 100 × (blocks delivered before the abort call)`, each run 5 s plus a random 0 to 100 ms;
    - (d) `abort()` + `close()`: the candidate's median is at most the default's plus 250 ms;
    - (e) open to first block: the candidate's median is at most the default's plus 250 ms.
  - The sampling protocol (frozen with the rule; added 2026-11-26 from peer round 2, PR-MED-001, before any run). Every time is `time.perf_counter()` taken at callback entry unless stated.
    - **Every trial is its own open and its own stream**, closed by `abort()` then `close()`.
    - **A stall trial** (the premise and (a)): let ten callbacks arrive; in the eleventh, after its block is counted, sleep S inside the callback; observe for 1.0 s after that callback returns (the backlog drains in that time); then `abort()`. *Flag*: a truthy status on any callback from the eleventh to the trial's end. *Lost blocks* (rewritten 2026-11-26 from peer round 4, PR-MED-001: a figure taken between two single callback entries is fooled by one late callback). A callback can only run late, never early, so the audio clock is anchored on the earliest phase seen at each end. With `e_i` the entry time of the trial's i-th callback (i counts delivered blocks from 1): `T0 = min over i = 1…10 of (e_i − i × 0.1 s)`; the *tail set* is every callback whose entry falls in the last 0.5 s before `t_abort_call`; `residual = min over the tail set of ((e_j − T0) ÷ 0.1 s − j)`, in blocks, unrounded. A trial passes (a) with no flag and a `residual` strictly less than 0.5; a `residual` of 0.5 or more fails, so a tie at exactly half a block fails (amended 2026-11-26 from peer round 5, PR-LOW-001: the earlier `round` sent a residual of exactly 0.5 to 0). The row's printed *lost blocks* figure is `max(0, floor(residual + 0.5))`, for display only; the verdict reads the residual. A trial with fewer than three callbacks in its tail set is invalid and fails. Validity, stated: the verdict is right when at least one of the first ten callbacks and at least one of the tail callbacks each entered strictly less than 50 ms after its block's completion; on MME the flag remains the detector and this figure is the second check.
    - **The cadence run** (b): one open per row, 20 s from the first callback; the gaps are between consecutive callback entries.
    - **A tail trial** (c): as (c) states; `abort()` is called 5 s plus a uniform random 0 to 100 ms after the first callback's entry, `t_abort_call` is taken immediately before it, and "blocks delivered before the abort call" are the callbacks whose entry time is earlier than `t_abort_call`. In (b), "100 ms ± 20 ms" means from 80 to 120 ms inclusive; every "at most" is inclusive. The same 20 opens of a row supply (d), the time from just before `abort()` to the return of `close()`, and (e), the time from just before the stream's constructor to the first callback's entry.
    - **The statistics** (added 2026-11-26 from peer round 3, PR-MED-001). A median is `statistics.median` (the mean of the two middle values for an even count). The 99th percentile is the nearest-rank one, the sorted value at rank `ceil(0.99 × n)`, as `guard_eval._percentile` computes it (`desktop/src/scribe_desktop/guard_eval.py:684–689`). A maximum is the largest value. Every comparison in (a)–(e) is made on unrounded values; the paste block rounds to whole ms for display only.
    - **A candidate that will not open** fails (a); its other bars are not evaluated and its row prints `refused`. A figure that is missing for any other reason fails its bar. The rule function never raises on a table: every input has an answer.
    - `--product` mode uses the same protocol through `SoundDeviceBackend.open_stream`: the stall sleeps inside `on_block`, and a flag is an `on_error` call.
  - Prediction, written before the run: the default trips at 0.3 s; 1.0 fails (a); 2.0 sits on its own threshold; **2.5 is chosen**.
  - If the device's host API is not MME, the premise is not met, or no candidate passes: stop. Task 0.3 becomes a decision for the practitioner with the table (a smaller target stall, a larger candidate, or no change). The rule is never adjusted after a run.
  Alternatives considered: a `PyDLL` lock-hold as the scoring stall (0 to 100 ms of phase noise; kept as one confirmation row).
- **D6 — Release route (the practitioner, 2026-11-26).** 0.4.3 ahead of 0.5.0; built in one session with `/execute`, no loop; installed when ready, during the ten Task 9.1 consultations, which then span 0.4.2 and 0.4.3. This amends the backup plan's C13 for 0.4.3 only: 0.4.3 adds no config file (the before and after fingerprints are untouched) and changes no note-generation logic; it changes only which audio a recording captures (a callback stall that ended a recording no longer does, and the named residues at Pause, Resume and Finish), so a different transcript can give a different note (corrected 2026-11-27 from codex round 8's PR-MED-001: the earlier wording said it "cannot change a note's content"); C13 still holds for 0.5.0. 0.4.1 stays reserved for the UI refresh's Phase 6.
- **D7 — The script is a tracked developer tool.** `scripts/measure-capture-stall.py`, because D1 requires the measurement repeated for any later change (the guard constants' precedent). It keeps no audio, pastes no device name, and follows the developer tools' two refusals (crash reports excluded for `python.exe`; the app's single-instance exclusion held for the run).
- **D8 — The Microphone list shows MME entries only (the practitioner's "Include in plan (Recommended)", 2026-11-26).** `SoundDeviceBackend.list_input_devices` keeps only entries whose host API is named "MME" when at least one input entry is on MME; otherwise the list is unfiltered (a non-Windows developer host, a test fake without host information). Device ids are PortAudio's own and do not change. Each microphone then appears once, and every listed entry reports dropped frames.
  Alternatives considered: leaving DirectSound and WASAPI entries listed (a stall there loses audio with no flag).
- **D9 — Proportionate ceremony.** No "Rolling back below 0.4.3" section: nothing at rest changes shape, so one sentence in the build's row. The findings-register row, the threat-model and data-flow corrections and the cross-family peer pass are kept (`docs/lessons.md`: never skip the peer pass on documents).

## Schema / Data Changes
None. No record, file, setting or protocol message changes shape. The installed log gains the `capture_stream` event and, on a capture failure, a `duration_ms` field.

## Config / Environment / Deployment Impact
- No new dependency, setting, model or environment variable. The model pack is unchanged.
- Release: the five version files (six values), `CHANGELOG.md`, a build of record from `main`, the attestation and hash checks, an install over 0.4.2 after the day's last Complete or Discard, the extension reloaded and Chrome restarted.
- Rolling back to 0.4.2 needs only that every recording is finished or discarded first, then the extension reloaded and Chrome restarted.
- Release risk: the 0.5.0 branch must merge `main` afterwards (the files named in Codebase Integration Notes).

## Critical Constraints
- **C1 — Nothing heavy while the practitioner is consulting.** The suite, a measurement, a mock recording and a codex pass each start on the practitioner's word.
- **C2 — Nothing per consultation in a tracked file** (`plan-clinic-smoke.md` D12; the repository is public). The trigger is recorded by month and relative facts. Phase P records totals by month: the largest gap, the overflow count, the fallback count; never a count of recordings per week.
- **C3 — The agent never opens the microphone and never reads, plays or describes a recording.** The script and every smoke are the practitioner's, from a normal terminal; nothing checked from an agent shell counts (`docs/lessons.md`). The agent may read the two builds' content-free logs.
- **C4 — The script keeps no audio.** A block's length is counted and the block dropped; it writes no file of its own (holding the app's single-instance lock opens, and creates when absent, the app's empty `app.lock`); the paste block holds numbers, a device id, a host word, two library version strings and whether the imported code is this checkout's, never a device name or a folder path (a name can carry a person's name). Amended 2026-11-27 from the security review's SEC-001 and the script review's F7.
- **C5 — Commit, push, moving `main`, the `Release` run and the install each wait for the practitioner's word.** Shadow mode stays on.
- **C6 — The backup run's worktree and branch are not touched.** What it must know goes through the shared notes folder to its composer.
- **C7 — The capture failure paths are not edited** beyond D2 and the optional `gap_ms`: `CaptureWorker`, `MockCaptureBackend`, `enrolment.py`, `ui/microphone.py` and `logging_setup.py` take no edit. The only edits to existing tests are the four stand-ins in Task 1.4.
- **C8 — Every QA run uses this worktree's source** (`PYTHONPATH`, Codebase Integration Notes). `main` is fast-forwarded only after the smoke passes; if `main` has moved, merge `main` into the branch, re-run the suite, then fast-forward.

## Validation / Verification
- Desktop, from the worktree's `desktop\` with `PYTHONPATH` set: `ruff check .`, `mypy`, `pytest`. Baseline: 11176 passed / 9 skipped at 0.4.2 (recorded on the stronger-voice plan, not re-run here); expected after the build: that plus the new tests, the count recorded at Task 1.5.
- Extension, in the main checkout after the fast-forward: `npm run qa` and `npm run build -- --mode dev`.
- Read-only baselines taken 2026-11-26 at `685743a`:
  - `grep -rn "latency=" desktop/src` → 0 lines (after Task 1.1: at least 1);
  - `grep -rn "WASAPI" docs AGENTS.md desktop/src` → 3 lines (`data-flow-map.md:175`, `audio_capture.py:4` and `:167`; after Phase 3 each is reworded to the measured host API);
  - `grep -rn "capture_failure" desktop/tests` → 6 lines;
  - `grep -c "def test_" desktop/tests/test_audio_capture.py` → 31.
- Phase 0's paste block and Task 0.3's choice; Phase 2's figures; Phase P's installed log lines.
- D3's unedited tests still show an injected overflow ending a recording as `failed` with its audio kept.

## Deferred / Out of Scope
See `Planning Extraction Summary` (five deferred items, one exclusion, three accepted assumptions). No change to live transcription, thread counts, garbage collection, the warm-up, the queue or the chunk store.

## Current State / Handoff Note
- Last completed step: the local commit of the 0.4.3 work on this branch (2026-11-28, on the practitioner's "Yes, commit it"; not pushed, `main` not moved). Before it: the full suite after Round 8 (11343 passed / 9 skipped), H4 (2026-11-27: codex rounds 8 and 9, every finding fixed), the full suite after Round 7 (11334 passed / 9 skipped), H1–H3 (Round 7), Tasks 3.1 and 3.2, Task 2.1 ("pass, all good", longest gap 189 ms), Task 1.5, Tasks 1.1 to 1.4, Task 0.3 ("Yes, 2.5 s"), Tasks 0.2 and 0.1, planning and "Approve plan" (2026-11-26).
- Current in-progress step: None
- Immediate next action: Phase P on the practitioner's word at each step (C5, C8): P.1's docstring path, fast-forwarding `main`, `npm run qa` and the dev build there, the push, the `Release` run and the install with shadow mode on.
- Open blockers / open questions: each Phase P step waits for the practitioner's word; whether the 69 s mock is accepted or a longer one is wanted (asked 2026-11-27). Working pattern: parallel subagents only until the practitioner's usage reset; after it, back to one session working in sequence (their words in Round 7).
- Last plan sync: 2026-11-28

## Review History
- 2026-11-26 round 1: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=n/a; action=round 2 with a fresh peer (a plan review never converges on its first round)
- 2026-11-26 round 2: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=measurement-rule completeness; action=amendment applied (D5's sampling protocol), round 3 with a fresh peer
- 2026-11-26 round 3: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=measurement-rule completeness; action=amendment applied (D5's statistics), round 4 with a fresh peer
- 2026-11-26 round 4: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=measurement-rule completeness; action=amendments applied (the lost-block figure; the opened line's latency), round 5 with a fresh peer (the cap)
- 2026-11-26 round 5: 0 CRIT / 0 HIGH / 0 MED / 1 LOW; skew=measurement-rule boundary; action=amendment applied (the half-block tie); cap reached, not converged: a sixth round only on the practitioner's word
- 2026-11-26 round 6: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none (cap raised by one on the practitioner's "One more round"); the plan peer-review pass has converged

## Review Findings Log

### Round 1 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed
Source: codex gpt-6-astra high — Codex plan peer-review
Materiality: 0 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (the peer ran in a read-only sandbox; plan hash unchanged across the run, `8f207b8f…5cab`); the text below is the peer's, verbatim.

No findings

Spot-checked cites and results:

- `.cursor/plans/plan-capture-overflow.md:109` against `desktop/src/scribe_desktop/audio_capture.py:169`, `:186`, `:408`, `:431`, `:449`, `:532`: enumeration, callback ordering, pause gating, stop and failure teardown match the plan’s premises.
- Plan `:149`, `:249` against `desktop/src/scribe_desktop/app.py:786`, `:794`, `:838`; `ui/main_window.py:573`, `:650`; and `session.py:980`: the two-backend split preserves recording ownership. Monitoring and enrolment use the UI instance.
- Plan `:151`, `:252` against `audio_capture.py:211`, `:222` and installed `sounddevice.py:914`, `:1119`, `:1146`, `:1160`: retry isolation, cleanup and success-only fallback logging are feasible requirements. Constructor and start refusals are covered by the planned tests.
- Plan `:154` against `desktop/src/scribe_desktop/logging_setup.py:44`, `:73`, `:563` and `session.py:2381`: proposed fields are allowed; fixed event/value words do not match the tripwire signatures. Existing failures without a gap can retain their exact rendering.
- Plan `:158`, `:162` against `audio_capture.py:408`, `:431`, `:440`: callbacks continue while paused, so an ordinary pause does not itself age the callback timestamp. The deferred Pause/Resume backlog residue is explicitly acknowledged at plan `:153`.
- Plan `:164`, `:234`: the requested rows cover the premise and bars (a)–(e); the tail formula accounts for the first 100 ms block. No verified contradiction in the selection rule survived review.
- Plan `:231`, `:239`, `:262`: baseline measurement can precede the new constant; product mode explicitly refuses its absence, and Phase 2 selects the worktree source through `PYTHONPATH`.
- Plan `:176`, `:232` against `desktop/src/scribe_desktop/exclusions.py:595`, `:627` and `replay_kept.py:191`: the refusal and single-instance APIs support the proposed script.
- Plan `:177` against `audio_capture.py:169`, `ui/microphone.py:207`, `ui/practitioner.py:864` and `practitioner_profile.py:203`: filtering preserves PortAudio IDs; no persisted selected-device ID or wrong-device remapping was found.
- Plan `:257` against `desktop/tests/test_audit.py:1706`, `:1927`, `test_exclusions.py:1343`, `test_hands_free.py:697`: the four constructor stand-ins are correctly identified. `test_install_layout.py:907` derives the expected version dynamically; the existing sounddevice fakes and conftest sentinels do not prevent the planned tests.
- Plan `:269` against `docs/security/data-flow-map.md:175`, `:746`, `:1276`; `docs/security/threat-model.md:1777`, `:4083`; and `docs/security/retention-schedule.md:42`: the relevant capture and developer-tool documentation has task ownership. The task count is 20.

PortAudio host-specific claims at plan `:129`–`:135` were not independently source-verified: those sources were unavailable. Memory of PortAudio behavior supplied no sufficiently certain contradiction to report; the installed sounddevice wrapper alone cannot establish those host internals.

Static review only: no files changed, tests executed, applications launched or audio accessed.

Materiality: 0 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-1 RESULT: 0

### Round 2 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed
Source: Codex (codex gpt-6-astra high) plan peer-review
Materiality: 1 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (read-only sandbox; plan hash unchanged across the run, `dbd325d1…b399`). A first attempt at this round was inconclusive and appended nothing: the planning session's brief had told the peer to stop at the `## Review Findings Log` heading, above the task list, and the peer said so; the brief was corrected and a fresh peer re-ran the round. The finding below is the peer's, verbatim; its walk-throughs W1–W7 (no further finding) are in the run log.

**PR-MED-001 — Freeze the sampling protocol that determines the buffer value**
- **Materiality:** build-affecting (verified by the planning session: D5 and Task 0.1 defined the bars but not a trial)
- **Evidence:** `.cursor/plans/plan-capture-overflow.md:167` requires no frame shortfall beyond one block, but D5 (`:164–173`) and Task 0.1 (`:263`) do not define the stall trial’s boundaries, the callback at which the stall occurs, the expected-frame calculation, or the post-stall observation period. D5(e) (`:171`) also leaves unspecified which opens supply its median.
- **Why it matters:** Two reasonable implementations can select different candidates. Counting immediately after the sleeping callback returns can classify queued, recoverable audio as missing; counting after the backlog drains can pass the same stream. The real backend delivers individual blocks (`desktop/src/scribe_desktop/audio_capture.py:196–209`), with 1,600 frames per 100 ms (`:39–45`), and abort discards pending buffers (installed `sounddevice.py:1146–1168`). Therefore the observation boundary changes the measurement, rather than merely its presentation. Using different trial populations for the startup median can likewise change D5(e).
- **Proposed amendment:** Before Task 0.2, freeze the stall injection point, trial boundaries, expected-versus-delivered frame equation and post-stall observation period, and identify the exact opens supplying D5(e)’s median.
- **Verification:** Rechecked D5 and the complete task list; neither supplies those definitions.
- **/fix decision:** Applied 2026-11-26 by the planning session (Claude Code). D5 gained "The sampling protocol": one open per trial; the stall in the eleventh callback with a 1.0 s observation after it returns; the shortfall equation from the first and last callback entry times; the cadence run; the 20 tail-trial opens supplying (c), (d) and (e); a candidate that will not open fails (a) and a missing figure fails its bar; `--product` uses the same protocol. Task 0.1 now points at it and adds no rule of its own. Landed and re-read; siblings checked (Task 0.1's row list, Task 0.2, Task 2.1, Validation): none contradicts it.

Materiality: 1 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-2 RESULT: 1

### Round 3 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed
Source: Codex gpt-6-astra high plan peer-review
Materiality: 1 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (read-only sandbox; plan hash unchanged across the run, `784e2f18…1da6`). The finding is the peer's, verbatim; its walk-throughs (no further finding) are in the run log. The peer also noted, without a finding, that the shortfall equation can read one block low when the first callback is late, and that under the MME assumption a real overflow also raises the flag, which fails (a) by itself.

**PR-MED-001 — D5 leaves the percentile calculation unfrozen**
- **Materiality:** build-affecting (verified by the planning session: no estimator was named; `guard_eval.py:684–689` is nearest-rank as cited)
- **Evidence:** `.cursor/plans/plan-capture-overflow.md:168` requires the callback-gap 99th percentile to be at most 250 ms; `:175` defines sampling, while `:289` prohibits adding measurement rules. None specifies the percentile estimator.
- **Why it matters:** A 20-second sample can contain 200 gaps: 197 at 97.2 ms, followed by 240, 300 and 310 ms, totalling 19,998.4 ms. Its median passes. Nearest-rank gives p99 = **240 ms**, and inclusive interpolation gives **240.6 ms**, both passing; exclusive interpolation gives **299.4 ms**, failing. Identical callbacks can therefore select different buffer constants.
- **Code check:** `desktop/src/scribe_desktop/guard_eval.py:684–689` already implements nearest-rank, providing a suitable precedent, but D5 does not adopt it.
- **Proposed amendment:** Explicitly freeze nearest-rank percentile calculation, following `guard_eval.py:684–689`, and add the borderline sample above to Task 0.1’s hardware-free verification.
- **/fix decision:** Applied 2026-11-26 by the planning session (Claude Code). D5's sampling protocol gained "The statistics": the median (`statistics.median`), the nearest-rank 99th percentile, the maximum, comparisons on unrounded values with rounding for display only. Task 0.1's tests gained the borderline sample. Landed and re-read. The class swept by the planning session in the same pass: the shortfall equation now uses `round` (the peer's own note; a floor flips on jitter) with its one-block resolution named; the tail trial's abort time, the block count before the abort and the inclusive bounds are defined; D4 gained "Each figure, exactly" (the gap, `gap_ms`, `count`, the closed line's `duration_ms`, the age of the last callback, the rounding).

Materiality: 1 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-3 RESULT: 1

### Round 4 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 2 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (read-only sandbox; plan hash unchanged across the run, `c3480cf0…6b6a`). The two findings are the peer's, verbatim; its walk-throughs (no further finding) are in the run log.

**PR-MED-001 — Callback-entry timing can conceal the two-block loss D5 promises to detect**

- Materiality: build-affecting (verified by the planning session: the counterexample's arithmetic holds against the round-3 text)
- Evidence: `.cursor/plans/plan-capture-overflow.md:175` measures shortfall between the first and last callback **entries** and claims to catch unflagged losses of two blocks or more. `desktop/src/scribe_desktop/audio_capture.py:196` receives callback timing information but currently discards it; installed `C:\Recording clinic software\.venv\Lib\site-packages\sounddevice.py:1759` explicitly distinguishes capture time from callback invocation time.
- Counterexample: forty blocks would normally arrive from 0.1 through 4.0 seconds. Delay the first callback until 0.3 seconds, retaining its audio and delivering the initial backlog before callback eleven. Subsequently lose exactly two blocks without a flag during the scoring stall, leaving 38 delivered blocks and the last callback at 4.0 seconds. D5 calculates 37 elapsed block intervals, plus one, minus 38: **zero shortfall**, so bar (a) passes. Rounding does not repair the initial 200 ms offset. Bar (e) uses separate opens (`plan:177`) and cannot reject this trial.
- Proposed amendment: Replace the unconditional two-block guarantee with a loss measurement that accounts for endpoint scheduling delay, freeze its validity conditions, and add this delayed-first-callback counterexample to Task 0.1’s rule tests.
- /fix decision: Applied 2026-11-26 by the planning session (Claude Code). The stall trial's figure is now *lost blocks*, anchored on the earliest phase of the first ten callbacks and of the tail set (the last 0.5 s), with a three-callback validity floor and its validity condition stated; bar (a) reads "no lost block"; Task 0.1's row list and tests follow (the counterexample reads 2). On the counterexample: `T0` = 0, the tail's minimum is 40 − 38, `lost` = 2. Landed and re-read; siblings swept (bar (a), Task 0.1's rows and tests; the round-2 and round-3 blocks quote the older wording as history).

**PR-LOW-002 — The opened-line formula contradicts the requested-latency contract**

- Materiality: build-affecting (verified: D4's line said "requested latency" while "Each figure, exactly" named the constant)
- Evidence: `.cursor/plans/plan-capture-overflow.md:155` requires the requested latency, but the new formula at `:163` explicitly uses `INPUT_LATENCY_SECONDS`; `:149` and Task 1.1 at `:324` permit an `input_latency` override. The actual stream argument belongs at `desktop/src/scribe_desktop/audio_capture.py:223`.
- With a 2.5-second constant and a backend configured to request 1.0 second with logging enabled, these instructions require different output: 2500 versus 1000 milliseconds. Ordinary application wiring uses the default, but the stated constructor contract supports both arguments together.
- Proposed amendment: Define opened-line `duration_ms` as the rounded explicit latency actually passed to that successful stream attempt, and assert it using an override different from the constant.
- /fix decision: Applied 2026-11-26 by the planning session (Claude Code). "Each figure, exactly" now names the instance's `input_latency`; `test_an_mme_recording_stream_requests_the_buffer` also runs with an override different from the constant. Landed and re-read.

Materiality: 2 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-4 RESULT: 2

### Round 5 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed (the pass's cap; the fix below has not been read by a fresh peer)
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 1 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (read-only sandbox; plan hash unchanged across the run, `e805fad6…f9a4`). The finding is the peer's, verbatim; its six worked streams and seven walk-throughs (no further finding) are in the run log.

**PR-LOW-001 — The inclusive 50 ms validity boundary can hide one lost block**

- Materiality: build-affecting (verified by the planning session: with every one of the first ten callbacks exactly 50 ms late and one block lost, the residual is 0.5 and Python's `round` gives 0)
- Evidence: `.cursor/plans/plan-capture-overflow.md:175`, `:178`, `:340`; `desktop/src/scribe_desktop/audio_capture.py:39–45` establishes the 100 ms block.
- If all first ten callbacks arrive exactly 50 ms late, `T0` is 0.05 s later than the physical block clock. After exactly one unflagged lost block, on-time tail callbacks give a minimum residual of `(100 − 50) / 100 = 0.5`. Python’s `round(0.5)` is 0, so the trial passes. Both endpoints satisfy the stated “within 50 ms” condition. Conversely, a healthy stream with an on-time baseline and tail callbacks exactly 50 ms late produces the same residual; changing the rounding direction alone cannot distinguish them.
- Proposed amendment: Make the validity bound strictly less than 50 ms, define half-block ties as indeterminate trials that fail qualification, and add both boundary cases to Task 0.1’s tests.
- /fix decision: Applied 2026-11-26 by the planning session (Claude Code). The verdict now reads the unrounded `residual`: a trial passes with no flag and a residual strictly below 0.5, so a half-block tie fails; the printed lost-block figure is display only; the validity bound is strictly less than 50 ms at both ends; Task 0.1's tests gain both ties and the same two cases at 49 ms. Checked by hand: with a true loss of L blocks, baseline lateness b and tail lateness t, the residual is L + (t − b) ÷ 100 ms; under b, t < 50 ms a healthy trial gives less than 0.5 (passes) and one lost block more than 0.5 (fails). Landed and re-read; siblings swept (bar (a), Task 0.1's tests; "The statistics" already says every comparison is on unrounded values).

Materiality: 1 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-5 RESULT: 1

### Round 6 - 2026-11-26 - capture-overflow plan, independent cross-family codex plan peer-review
- Round status: Closed
Source: Codex (gpt-6-astra high) plan peer-review
Materiality: 0 build-affecting / 0 record-only / 0 invalid

Recorded by the planning session from the peer's own output (read-only sandbox; plan hash unchanged across the run, `76391f2a…d574`). The cap was raised by one round on the practitioner's word ("One more round", 2026-11-26).

No findings. The peer worked round 5's fix by hand (the residual is L + (t − b) ÷ 100 ms; inside the validity condition a healthy trial lies strictly between −0.5 and 0.5 and passes, and any loss of one block or more lies above 0.5 and fails; both half-block ties fail; the displayed figure is 0 exactly when the residual is below 0.5, so it cannot contradict the verdict, and no sentence makes the rule read the display figure), found no sibling sentence still stating the older contract, and repeated the seven walk-throughs with no defect. It names what it could not check: PortAudio's host-specific internals were not re-read from source (no network), so the plan's Phase 0 measurement remains their confirmation.

The plan peer-review pass has converged: a round after the first with no new build-affecting finding.

Materiality: 0 build-affecting / 0 record-only / 0 invalid
PEER-ROUND-6 RESULT: 0


### Round 7 - 2026-11-27 - Step H1–H3 as four parallel read-only review agents (code, the script, simplification, security)
Run on the practitioner's word of 2026-11-27 ("can you spawn more agents so its finished quicker, i have a lot of usage left for tomorrow. Make sure it goes back to normal after the usage reset"): four same-family subagents, read-only, each with its own lens, over the uncommitted Phase 1 code, the script and the Phase 3 documents. No CRIT or HIGH. Every finding was re-read against the code by this session before its disposition. The practitioner's four dispositions (2026-11-27), each the recommended option: "Apply all (Recommended)" (the code and script fixes), "Add all (Recommended)" (the tests), "Fix all (Recommended)" (the documents), "Accept, name it (Recommended)" (the Resume residue).
- **Code review** (MED 1, LOW 8): the app's wiring of the two backends was pinned by nothing (MED; new `desktop/tests/test_app_capture_wiring.py`); the closed line's life-long longest gap, `count=1 duration_ms=0`, the age read before `abort()`, the rounding, the retry's errors-ignored close, one open on the no-buffer instance and on a non-MME device, and an MME output beside non-MME inputs were unpinned (new tests); two races in `_SoundDeviceStream.stop()` (two closed lines when the worker's failure and Finish both stop the stream; a stamp between two reads overstating the age) fixed by a per-handle lock and reading the clock first; `gap_ms` accepted only as a non-negative int; the backlog line's reach (finding 9) documented, not widened.
- **Script review** (MED 3, LOW 6): the choice's "meets all of", the protocol as executed and the two verdict lines were weakly pinned (37 new tests, 73 → 110); a refused product row was invisible (now `refused` in the stall table); an exception in the last row discarded the table, and the self-check's heartbeat could outlive a raising hold (fixed); a flaky 0.2 s hold (now 1.0 s; a Windows-only positive case added); `--list` unsafe when redirected (fixed); "writes no file" (worded: the app's empty `app.lock`); the docstring's run command names this worktree (changed at P.1's merge).
- **Simplification** (5 items): the tuple copy in `recent_gap_ms`, the stale closed-line docstring and the script's two aliases removed; `Recorder.frames` (custody wording) and the docstring path left (the second at P.1); the two host queries skipped for the level meter's instance, which now opens exactly as before.
- **Security review** (LOW 7): the paste block's module path could carry an account name (now `this checkout` / `another checkout`; C4 amended); an error or Ctrl+C printed a traceback (now the type's name only, exit 2, the lock released; [2026-11-27, codex rounds 8–9] this covers an error DURING the measurement: Ctrl+C prints `interrupted`, and an error in the imports or the start-up checks before it is an ordinary Python error); the backlog line's two limits and the Resume direction of D3's residue named in the threat model and flow 6 (the Resume one accepted by name); the meter and enrolment sentence corrected (they stop with a message; an enrolment ends with nothing saved); the lesson's over-claim corrected (only MME was measured); the trigger line's elapsed time and its place in the day removed from this plan before any commit (C2).
- Two forced deviations by the script's delegate, accepted: two assertions of the (untracked, this plan's own) script test file that pinned the old path were updated, and the checkout test uses `os.path` because the file's custody guard refuses `pathlib`.
- Verified by the delegates with the worktree's source: `test_audio_capture.py` and `test_app_capture_wiring.py` 79 passed; the filtered capture tests 87 passed; `test_measure_capture_stall.py` 110 passed (three runs); `ruff check .` clean in `desktop/`; mypy no issues in 72 source files (the script on its own, no issues). The full suite is owed, on the practitioner's word (C1).


### Round 8 - 2026-11-27 - Codex peer-review (Step H4, two parallel read-only slices: A code at xhigh, B documents at high)
Source: Codex peer-review (gpt-6-astra, read-only; started on the practitioner's "Yes, start it", 2026-11-27). Both slices left the working tree unchanged (diff hash equal before and after). Every scope file and document has its evidence line. No CRIT or HIGH. Every finding was re-read against the code by this session and verified; all were Fix-now and applied (the code fixes by a delegate, re-checked here).
- **A-PR-MED-001** `scripts/measure-capture-stall.py` `run_cadence`: a cadence whose callbacks stopped early (no flag) was scored on its healthy prefix, so bar (b) could pass without D5's full 20 s. Fixed: when the last callback inside the window is more than `CADENCE_P99_NS` before its end, the flag count is None (bar (b) fails, the table shows `-`); no D5 threshold changed. Three new tests (early stop, a full window, the exact bound).
- **A-PR-LOW-001** an interruption during start-up or an abort that raises skipped the close. Fixed in the script's `raw_opener` (close on any non-PortAudio exception and re-raise, no retry; `stop()` closes in a `finally`) and in the product (`SoundDeviceBackend._open` discards the handle on any exception, one clause; `_SoundDeviceStream.stop()` closes in a `finally`, then logs the closed line once). The D2 retry still catches PortAudioError only. Four new tests.
- **B-PR-MED-001** D6 and the dated line on `plan-phase3a-note-pipeline.md` said 0.4.3 "cannot change a note's content". Corrected: it changes no note-generation logic and adds no config file, but it changes which audio a recording captures, so a different transcript can give a different note. The practitioner's decisions are unchanged; the two shared notes for the other runs carry the same correction.
- **B-PR-LOW-001** "30 s or more is a sleep or lock, not a stall" (threat model, D4's reading rules): now "most likely asleep or locked, which the log cannot show", read beside Windows' power and lock events before a cause is named.
- **B-PR-LOW-002** AGENTS.md step 17's "writes no file": now names the empty `app.lock`.
- **B-PR-LOW-003** Task 0.1's identity line named the module path: now the checkout word; the two recorded paste blocks' path lines replaced by a dated "[path removed …]" annotation.
- **B-PR-LOW-004** "an error or Ctrl+C prints only its type's name" (scripts/README.md, data-flow map, threat model): narrowed to an error during the measurement; Ctrl+C prints `interrupted`; an error in the imports or start-up checks is an ordinary Python error.
- **B-PR-LOW-005** F-175's "a recording that loses microphone audio stops" overstated the control (the Pause and Finish residue loses audio unflagged): now "a recording with dropped microphone frames stops with a message".
- Verified: `test_audio_capture.py`, `test_app_capture_wiring.py`, `test_measure_capture_stall.py`, `test_live_session.py` 238 passed; after merging the product's two identical except clauses, the first two 82 passed; `test_pilot_docs.py` 13 passed; `ruff check .` clean in `desktop/`, mypy no issues in 72 source files. The script's E501 at its docstring line 16 predates this work and goes with P.1's path change.

### Round 9 - 2026-11-27 - Codex peer-review (Step H4 confirmation, high)
Source: Codex peer-review (gpt-6-astra, read-only; working tree unchanged). All eight round-8 fixes confirmed, with file:line evidence; no code regression. One new LOW: two summary lines of this plan still carried the corrected claims (H1's "writes nothing"; Round 7's error-output sentence). Fixed with dated corrections. The pass closes here (docs-only-low-close: the round's only finding was verified LOW wording in a document, applied).

## Tasks

### Phase 0 — Measure on this computer
- [x] 🟩 **0.1 The script and its tests.** `scripts/measure-capture-stall.py`, `desktop/tests/test_measure_capture_stall.py`, an entry in `scripts/README.md`.
  - As built (2026-11-26, `/execute` in the planning session on Fable; not committed): ruff clean on the script (default rules, as the plan's command, and the desktop rule set apart from the docstring's one long command line) and on `desktop/`; `test_measure_capture_stall.py` 73 passed, three runs in a row, with `PYTHONPATH` on this worktree's `desktop\src` (C8). No microphone was opened: the runs use a fake `sounddevice` whose thread calls the callback with empty blocks. Notes, none of them a rule change:
    - Times are `time.perf_counter_ns()` at callback entry, the same clock as D5's `perf_counter` read as whole nanoseconds, so the half-block tie is exact (`2 × residual < block`); with float seconds a tie would turn on rounding noise.
    - `--list` opens no stream, so it takes neither refusal; every other mode takes both before `sounddevice` is imported.
    - A device that is not on MME is named in the paste block (`not scored`) and no trial is run on it; the block then ends `premise: not met`, `chosen: none`.
    - `--product` measures two rows, `SoundDeviceBackend(input_latency=None)` and `SoundDeviceBackend()`, stall and stop trials only, and ends `product: pass | fail` (bars (a), (c), (d) and (e) on the product row).
    - The paste block also shows each candidate's five bars, so a decision gate at Task 0.3 can see which bar failed.
    - Beside the tests the task names: the frozen schedule pinned (candidates, stall counts, every duration), each bar's inclusive bound, the percentile equal to `guard_eval._percentile`, two end-to-end runs on the fake stream (raw and `--product`), and a text guard that the script opens no file and imports no audio or logging module.
    - The peer-loop observation, recorded: `grep -c $'\r'` reads 0 for a CRLF file in this shell, so the endings checks of the planning rounds proved nothing; `file <path>` is the check (the plan file is LF; `scripts/README.md` stays CRLF after its edit).
  - Modes: `--list` (id, host word, name; on screen only); the default measurement on the default input or `--device <id>`; `--product` (the same stall and tail rows through `SoundDeviceBackend.open_stream`, sleeping inside `on_block`; it refuses when the imported `audio_capture` has no `INPUT_LATENCY_SECONDS`).
  - Before any stream: the crash-report refusal (`exclusions.check_tool_wer`, exit 2), the single-instance exclusion (refuse if an app is open), `sounddevice` imported inside `main()`.
  - Identity lines: `sounddevice` and PortAudio versions, which checkout's `audio_capture` was imported (`this checkout` or `another checkout`, no path; amended 2026-11-27 from the security review's SEC-001), the device id and host word. A non-MME device is listed but not scored.
  - Every trial, count and time follows D5's sampling protocol exactly; the script adds no measurement rule of its own.
  - Rows for the default and each D5 candidate: the read-back latency (information only); the 20 s cadence figures; stall trials (0.3 s ×5, 1.0 s ×5, 2.0 s ×10, 3.0 s ×5) with the flag count, the lost-block figure and which callback after the stall carried the flag; the tail and stop figures of D5 (c)–(e); one row for a stop that lands inside a 1.0 s stall (the backlog dropped, D3's residue, information only); one `PyDLL` lock-hold row on the default (0.5 s, expects a flag; skipped when `sys._is_gil_enabled()` is False), preceded by a self-check that the hold really stops a second thread's heartbeat.
  - Output: a Markdown paste block per C4, ending with `premise: met | not met` and `chosen: <value> | none`, computed by one pure function.
  - Tests (hardware-free, the script loaded by importlib): the rule function on tables that pick 2.5, pick nothing, fail the premise and meet a non-MME device; the percentile on the borderline sample of 200 gaps (197 at 97.2 ms, then 240, 300 and 310 ms): nearest-rank gives 240 ms and bar (b) passes; the lost-block figure on four entry-time lists: a healthy trial with jitter (0), a first callback 200 ms late with two blocks then lost (2: peer round 4's counterexample), one block lost (1), a tail set of two callbacks (invalid, fails), and peer round 5's two half-block ties, each of which fails (first ten callbacks all exactly 50 ms late with one block lost and an on-time tail: residual 0.5; a healthy trial whose tail callbacks are all exactly 50 ms late: residual 0.5), beside the same two at 49 ms, which give the right verdicts (fail with one lost, pass when healthy); the paste block holds no device name; both refusals. The script is linted explicitly (`ruff check scripts/measure-capture-stall.py`).
  - Done when: ruff clean, its tests pass, and the docstring gives the exact command with real paths.
- [x] 🟩 **0.2 The practitioner's run.**   [operator]
  - From a normal PowerShell, outside clinic hours, both builds closed, about 20 minutes: `& 'C:\Recording clinic software\.venv\Scripts\python.exe' 'C:\Recording clinic software\.claude\worktrees\plan-run3-leftovers-8f7c7f\scripts\measure-capture-stall.py'` (first with `--list` if the Microphone tab's choice is not the default).
  - Done when: the paste block is in this plan under this task, and the versions printed match the build lock (`sounddevice` 0.5.5).
  - As run (2026-11-26, the practitioner, a normal PowerShell, the default input; a first attempt was refused because an app was still open, as designed). The block as pasted, its heading line shown in bold:

    **Capture-stall measurement (`scripts/measure-capture-stall.py`)**

    - sounddevice 0.5.5; PortAudio V19.7.0-devel, revision unknown
    - audio_capture: [path removed 2026-11-27 (codex round 8's PR-LOW-003); the run printed the imported module's folder path, which today's script no longer prints; it was the main checkout's]
    - device id 1; host mme; mode raw
    - default input latency, low / high, ms: 90 / 180

    | row | read-back ms | gaps | gap median ms | gap p99 ms | gap max ms | flags |
    |---|---|---|---|---|---|---|
    | default | 100 | 200 | 100 | 100 | 101 | 0 |
    | 1 s | 100 | 199 | 100 | 101 | 101 | 0 |
    | 2 s | 100 | 200 | 100 | 101 | 101 | 0 |
    | 2.5 s | 100 | 199 | 100 | 101 | 101 | 0 |
    | 3 s | 100 | 200 | 100 | 101 | 101 | 0 |

    | row | stall s | trials | flagged | passed | invalid | lost blocks (max) | flag on callback (0 = the stalled one) |
    |---|---|---|---|---|---|---|---|
    | default | 0.3 | 5 | 5 | 0 | 0 | 3 | 1 |
    | default | 1 | 5 | 5 | 0 | 0 | 10 | 1 |
    | default | 2 | 10 | 10 | 0 | 0 | 20 | 1 |
    | default | 3 | 5 | 5 | 0 | 0 | 30 | 1 |
    | 1 s | 0.3 | 5 | 0 | 5 | 0 | 0 | - |
    | 1 s | 1 | 5 | 5 | 0 | 0 | 10 | 1 |
    | 1 s | 2 | 10 | 10 | 0 | 0 | 20 | 1 |
    | 1 s | 3 | 5 | 5 | 0 | 0 | 30 | 1 |
    | 2 s | 0.3 | 5 | 0 | 5 | 0 | 0 | - |
    | 2 s | 1 | 5 | 0 | 5 | 0 | 0 | - |
    | 2 s | 2 | 10 | 10 | 0 | 0 | 20 | 1 |
    | 2 s | 3 | 5 | 5 | 0 | 0 | 30 | 1 |
    | 2.5 s | 0.3 | 5 | 0 | 5 | 0 | 0 | - |
    | 2.5 s | 1 | 5 | 0 | 5 | 0 | 0 | - |
    | 2.5 s | 2 | 10 | 0 | 10 | 0 | 0 | - |
    | 2.5 s | 3 | 5 | 5 | 0 | 0 | 30 | 1 |
    | 3 s | 0.3 | 5 | 0 | 5 | 0 | 0 | - |
    | 3 s | 1 | 5 | 0 | 5 | 0 | 0 | - |
    | 3 s | 2 | 10 | 0 | 10 | 0 | 0 | - |
    | 3 s | 3 | 5 | 4 | 1 | 0 | 30 | 1 |

    | row | stops | tail median ms | tail max ms | stop median ms | first block median ms | stop inside a stall: stop ms / undelivered ms / callbacks after |
    |---|---|---|---|---|---|---|
    | default | 20 | 44 | 86 | 72 | 326 | 549 / 500 / 0 |
    | 1 s | 20 | 40 | 90 | 71 | 391 | 542 / 500 / 0 |
    | 2 s | 20 | 59 | 100 | 72 | 396 | 545 / 500 / 0 |
    | 2.5 s | 20 | 48 | 91 | 83 | 357 | 562 / 501 / 0 |
    | 3 s | 20 | 47 | 96 | 81 | 337 | 561 / 501 / 0 |

    | candidate | (a) | (b) | (c) | (d) | (e) |
    |---|---|---|---|---|---|
    | 1 s | fail | pass | pass | pass | pass |
    | 2 s | fail | pass | pass | pass | pass |
    | 2.5 s | pass | pass | pass | pass | pass |
    | 3 s | pass | pass | pass | pass | pass |

    - interpreter-lock row (default buffer): 0.5 s hold: flag yes (expected yes)

    premise: met
    chosen: 2.5

  - Read against D5 (2026-11-26; the rule is unchanged and nothing was re-run). `sounddevice` is 0.5.5, the build lock's version; the device is on MME. The premise is met (5 of 5). 1.0 and 2.0 fail (a): the 2.0 s stall was flagged in 10 of 10 trials on each. 2.5 is the smallest candidate that meets every bar: (a) 10 of 10 with no flag and no lost block; (b) median 100 ms, 99th percentile 101 ms, no flag; (c) 48 − 44 = 4 ms against at most 50, maximum 91 ms against at most 200; (d) 83 ms against at most 72 + 250; (e) 357 ms against at most 326 + 250. D5's prediction held in every part.
  - Observations, information only (no rule reads them):
    - The read-back latency is 100 ms on every row, as expected on MME: it says nothing about the buffer, and the stall rows are the evidence.
    - On every flagged row the largest lost-block figure is the stall's whole length (3, 10, 20 and 30 blocks), also where the buffer nearly covered the stall (the 1 s buffer under a 1 s stall: 10). An overflow is therefore never a small gap, which is what D3 already assumes.
    - On every flagged row the flag came on the callback after the stalled one.
    - The 3 s buffer took one 3 s stall in five without a flag: a buffer's limit sits near its own length.
    - A stop that lands inside a 1.0 s stall takes about 0.55 s and leaves about 0.5 s undelivered, with no callback after it (D3's residue, as described).
    - The lock-hold row raised a flag on the default buffer, as expected.
    - The imported `audio_capture` was the main checkout's (the venv's own install). The raw mode reads only its three stream constants, the same in both checkouts; Task 2.1's `--product` run must name this worktree's source (C8).
- [x] 🟩 **0.3 The buffer's value.**   [decision]
  - Options: the value D5's rule chooses / a decision gate if the rule stops (a smaller target stall, a larger candidate, no change).
  - Decide after: Task 0.2's paste block.
  - Blocks: Phase 1.
  - Chosen: 2.5 s, the value D5's rule chooses (2026-11-26); rationale: the practitioner's "Yes, 2.5 s" on Task 0.2's block, where 2.5 is the smallest candidate that meets all five bars. `audio_capture.INPUT_LATENCY_SECONDS = 2.5`; by D1 it changes only by a new dated decision with Phase 0 repeated.

### Phase 1 — Build
- [x] 🟩 **1.1 The recording stream's buffer and its lines.** `audio_capture.py` `SoundDeviceBackend` (`__init__(logger=None, input_latency=INPUT_LATENCY_SECONDS, clock=time.monotonic)`, `open_stream`, `_SoundDeviceStream.stop`), `AudioCaptureError` (optional `gap_ms`), the module and class docstrings (the host API as measured). Contract: D1, D2, D4. With no logger nothing is logged; with a fake `sounddevice` that has no host queries the host is `other` and the open is today's.
- [x] 🟩 **1.2 The MME-only list.** `SoundDeviceBackend.list_input_devices` per D8. `ui/microphone.py` and `ui/practitioner.py` take no edit.
- [x] 🟩 **1.3 Wiring.** `app.py`: the controller's backend is `SoundDeviceBackend(logger=logger)`; `MainWindow`'s is a second `SoundDeviceBackend(input_latency=None)`. `session.py` `_on_capture_failure`: add `duration_ms` when the error carries `gap_ms`.
- [x] 🟩 **1.4 Tests.** In `test_audio_capture.py` (the fake `sounddevice` gains `query_devices`, `query_hostapis` and a refusable stream in NEW tests only):
  - `test_an_mme_recording_stream_requests_the_buffer` (also with an `input_latency` different from the constant: the stream argument and the opened line's `duration_ms` both follow the instance's value), `test_a_non_mme_stream_opens_with_the_default`, `test_an_instance_built_without_a_buffer_opens_as_today`;
  - `test_a_refused_buffer_retries_once_with_the_default` (constructor refusal and `start()` refusal; the first attempt closed; no device-lost from its `finished`), `test_a_second_refusal_is_open_failed`, `test_the_fallback_line_is_logged_only_when_the_retry_opens`;
  - `test_the_flagged_callback_carries_the_largest_recent_gap` (normal, long gap with a clean status, short gap with the flag: the long gap is carried; and the order where the long gap is on the flagged callback), `test_a_first_callback_has_no_gap`;
  - `test_the_stream_lines_hold_numbers_and_fixed_words_only` (opened, default, closed, backlog-dropped; a status object's text never appears; the lines pass `log_event`), `test_a_close_inside_a_stall_logs_the_backlog_line`, `test_no_logger_logs_nothing`;
  - `test_the_list_keeps_mme_entries_only`, `test_the_list_is_unfiltered_without_an_mme_entry`.
  - In `test_live_session.py`: `capture_failure` carries `duration_ms` only for an error with a gap; the existing parametrised line test passes unedited.
  - The four stand-ins become `lambda **kwargs: object()` (`test_audit.py` ×2, `test_exclusions.py`, `test_hands_free.py`): the only edits to existing tests.
  - As built, Tasks 1.1 to 1.4 (2026-11-26, `/execute`, not committed):
    - `INPUT_LATENCY_SECONDS = 2.5` (Task 0.3). Each open attempt has its own handle, created before its stream; `finished` reports device loss only once the constructor has returned and the stream was not stopped by us, which is today's condition unchanged. A refused attempt is discarded (marked stopped, closed with errors ignored) and logs nothing.
    - The gaps are stamped for both backend instances; only the one with a logger writes a line. `audio_capture` now imports `log_event`.
    - The module and class docstrings name MME as measured. The word WASAPI stays once in the module, in the host-name map (D4's `wasapi` word), so the Validation baseline's grep keeps one line there after Phase 3.
    - `app.py`: `backend = SoundDeviceBackend(logger=logger)` for the controller, `ui_backend = SoundDeviceBackend(input_latency=None)` for `MainWindow`.
    - Tests beside the named ones: the decided value pinned at 2.5; a device whose host cannot be resolved opens as today; the other capture errors carry no gap; a stop at exactly 250 ms logs no backlog line; a stream with no callback closes with zeros and one closed line after two stops; a stop that raises still logs the closed line; the list is unfiltered when the host query fails. In `test_live_session.py`: `test_a_capture_failure_carries_the_gap_only_when_the_error_has_one`.
    - Verified with `PYTHONPATH` on this worktree's source (C8): `ruff check .` clean in `desktop/`; `test_audio_capture.py` 64 passed (51 test functions, 31 before); `test_measure_capture_stall.py` 73 passed; `test_live_session.py -k capture_failure` 7 passed (the existing parametrised line test unedited); the four `main()` tests with the changed stand-ins 4 passed. mypy and the full suite are Task 1.5's, not run.
- [x] 🟩 **1.5 The suite, on the practitioner's word (C1, C8).** ruff, mypy, pytest from the worktree. Done when: clean, the new count recorded here.
  - As run (2026-11-26, on the practitioner's "Run it now"; the worktree's `desktop\` with `PYTHONPATH` on its source, the tree at `685743a` plus this plan's uncommitted changes): `ruff check .` clean; `mypy` no issues in 72 source files; `pytest` 11282 passed, 9 skipped (11 min 19 s). The baseline at this commit is 11177 passed, 9 skipped (the stronger-voice plan's count at `24415e4`; the Validation section's 11176 is one commit older), and this plan adds 105: 73 for the script, 30 in `test_audio_capture.py`, 2 in `test_live_session.py`.

### Phase 2 — Smoke on the developer build
- [x] 🟩 **2.1 The practitioner's smoke from the worktree.**   [operator]
  - `--product` run of the script with `$env:PYTHONPATH = 'C:\Recording clinic software\.claude\worktrees\plan-run3-leftovers-8f7c7f\desktop\src'` set first: the 2.0 s stall rows pass through the product's own open.
  - The developer build launched from the same PowerShell (`& 'C:\Recording clinic software\.venv\Scripts\python.exe' -m scribe_desktop.app`, installed app closed): the Microphone list shows each microphone once; one mock recording of 3 to 5 minutes with live transcription, one Pause and Resume, a known last word said and Finish pressed at once; the word is in the transcript; Recovery and the level meter behave as before.
  - The developer log shows `state=opened` with `detail_code=mme` and the requested buffer, `state=closed` with a count and the longest gap, and no `state=default_latency`.
  - Done when: pass or fail in the practitioner's words, and the longest gap (a number) are recorded here.
  - The `--product` run (the practitioner, 2026-11-27, a normal terminal, both builds closed, `PYTHONPATH` on this worktree's source). Their paste block, unedited:

    ### Capture-stall measurement (`scripts/measure-capture-stall.py`)

    - sounddevice 0.5.5; PortAudio V19.7.0-devel, revision unknown
    - audio_capture: [path removed 2026-11-27 (codex round 8's PR-LOW-003); the run printed the imported module's folder path, which today's script no longer prints; it was this worktree's]
    - device id 1; host mme; mode product
    - default input latency, low / high, ms: 90 / 180

    | row | stall s | trials | flagged | passed | invalid | lost blocks (max) | flag on callback (0 = the stalled one) |
    |---|---|---|---|---|---|---|---|
    | product default | 0.3 | 5 | 5 | 0 | 0 | 3 | 1 |
    | product default | 1 | 5 | 5 | 0 | 0 | 10 | 1 |
    | product default | 2 | 10 | 10 | 0 | 0 | 20 | 1 |
    | product default | 3 | 5 | 5 | 0 | 0 | 30 | 1 |
    | product 2.5 s | 0.3 | 5 | 0 | 5 | 0 | 0 | - |
    | product 2.5 s | 1 | 5 | 0 | 5 | 0 | 0 | - |
    | product 2.5 s | 2 | 10 | 0 | 10 | 0 | 0 | - |
    | product 2.5 s | 3 | 5 | 5 | 0 | 0 | 30 | 1 |

    | row | stops | tail median ms | tail max ms | stop median ms | first block median ms | stop inside a stall: stop ms / undelivered ms / callbacks after |
    |---|---|---|---|---|---|---|
    | product default | 20 | 54 | 92 | 72 | 376 | 556 / 501 / 0 |
    | product 2.5 s | 20 | 71 | 94 | 81 | 346 | 548 / 501 / 0 |

    | candidate | (a) | (c) | (d) | (e) |
    |---|---|---|---|---|
    | product 2.5 s | pass | pass | pass | pass |

    product: pass

  - Read against D5 (2026-11-27; nothing re-run). The imported `audio_capture` is this worktree's (C8), so the rows went through the product's own `SoundDeviceBackend.open_stream`. With the default buffer every stall is flagged, the 0.3 s one included (the premise again, through the product's open). With 2.5 s: (a) the 2.0 s stall 10 of 10 with no flag and no lost block, and the 0.3 s and 1.0 s stalls likewise; (c) 71 − 54 = 17 ms against at most 50, maximum 94 ms against at most 200; (d) 81 ms against at most 72 + 250; (e) 346 ms against at most 376 + 250. The 3.0 s stall, longer than the buffer, is flagged 5 of 5: an overflow beyond the buffer still fails the recording (D3).
  - The mock recording on the developer build (the practitioner, 2026-11-27, launched from the same PowerShell): "pass, all good" (their words).
  - The developer log for it, read by the agent (numbers and fixed words only): `capture_stream detail_code=mme device_id=1 duration_ms=2500 state=opened`; one Pause and one Resume on the same stream; `capture_stream count=687 device_id=1 duration_ms=189 state=closed`; no `state=default_latency`, no `state=backlog_dropped`, no `capture_failure`. **The longest gap is 189 ms** over 687 blocks (the normal gap is 100 ms).
  - As run: the recording was about 69 s (687 blocks), not the 3 to 5 minutes this task asked for, so the longest gap is read over about a minute of live transcription. The buffer itself was proven by the `--product` run above; a longer figure comes from clinic use (Tasks P.3 and P.4). Put to the practitioner as a question (accept, or one longer mock).

### Phase 3 — Version 0.4.3 and documents
- [x] 🟩 **3.1 Version.** `desktop/pyproject.toml`, `desktop/src/scribe_desktop/__init__.py`, `extension/package.json`, `extension/package-lock.json` (two values; not the `@humanwhocodes/retry` line), `extension/src/manifest.ts`; the `CHANGELOG.md` entry under `[Unreleased]` in the 0.4.2 entry's form. Verification: `pytest -k version`.
- [x] 🟩 **3.2 Documents** (each claim checked against the code; CRLF kept):
  - `docs/security/threat-model.md`: the capture paragraphs beside "THE WARM-UP" (the buffer for recordings only; the MME-only list and why; the fallback; each line of D4 and what its `duration_ms` means; D3's residue; the script among the crash-report tools, now three).
  - `docs/security/data-flow-map.md`: flow 6's host API as measured; the `capture_failure` sentence; the script as a paragraph under flow 6 (no new flow number: the backup branch takes flow 30); the tools enumeration.
  - `docs/security/retention-schedule.md`: the in-memory plaintext row (a recording's device buffers hold up to the constant).
  - The "two tools" comments in `exclusions.py` and `scripts/register-native-host.py` (comments only).
  - `docs/design-system.md`: the Microphone list, if it describes the entries.
  - `docs/pilot/findings-register.md`: one row with the next unused id (month only, clinic 1, stage `shadow`, encounter `—`, controlled by 0.4.3; `test_pilot_docs.py` pins the vocabulary).
  - `docs/lessons.md`: a docstring's hardware claim is measured before it is trusted; `stream.latency` does not show an MME buffer.
  - `AGENTS.md`: Current Status, Local Run Steps step 17 (the script), the installed-version lines, the live-transcription pointer, the retained-items sentence.
  - Dated lines: `plan-installation.md` (the retained follow-up resolved by this plan, the trigger by month) and `plan-phase3a-note-pipeline.md` (the ten span 0.4.2 and 0.4.3, in the practitioner's words, D6).
  - The shared notes folder: a note for the stronger-voice composer (its Task P.4 line) and the backup run's composer (C13's amendment; `app.py` and `test_audit.py`).
  - As built, Tasks 3.1 and 3.2 (2026-11-27, not committed; every file's CRLF ending kept, checked with `file`):
    - 3.1: the six values read 0.4.3 (the lock file's two `scribe-extension` entries only); `pytest -k version` 179 passed. The `npm run build -- --mode dev` and `npm run qa` belong to P.1 in the main checkout. The CHANGELOG entry sits first under `[Unreleased]` / Added.
    - 3.2: the threat model's "THE RECORDING BUFFER" block after surface 11's residue, and the "third tool" sentence beside the WER exclusions; flow 6's host and buffer, two paragraphs at flow 6's end (the buffer, the measurement tool), the `capture_failure` sentence and the tools enumeration in the data-flow map; one sentence in the retention schedule's in-memory plaintext row; the comments in `exclusions.py` (two) and `scripts/register-native-host.py` ("those tools"); F-175 in the findings register (`test_pilot_docs.py` 13 passed); a `docs/lessons.md` section; AGENTS.md's Current Status paragraph, Local Run Steps step 17, the installation line's retained-item words and a microphone-stream pointer appended to the live-transcription pointer; the dated lines on `plan-installation.md` and `plan-phase3a-note-pipeline.md`; the note `capture-overflow-for-other-runs.md` in the shared notes folder. `docs/design-system.md` describes no Microphone list entries, so it is unchanged. `ruff check .` clean in `desktop/` (the script's import-order note on `register-native-host.py` predates this change, unchanged at HEAD).

### Step H — Hardening
- [x] 🟩 **H1** `/review-loop` to convergence, with two named lenses: every new log line is numbers and fixed words only; the script writes no file of its own (holding the app's lock opens the app's empty `app.lock`; corrected 2026-11-27, codex round 9's PR-LOW-001) and pastes no name.
- [x] 🟩 **H2** `/simplify` — log findings; trivial → `/fix`.
- [x] 🟩 **H3** `/security-review`, scoped to D4's lines, the script and D8.
  - As run, H1–H3 (2026-11-27): four parallel read-only review agents on the practitioner's word, in place of the `/review-loop`, `/simplify` and `/security-review` commands; findings and dispositions in the Review Findings Log, Round 7. The full suite after their fixes, on the practitioner's "Yes, run it now" (2026-11-27), from the worktree's source: `ruff check .` clean, mypy no issues in 72 source files, 11334 passed / 9 skipped (11282 + 52 new).
- [x] 🟩 **H4** One cross-family codex pass over code and documents (one evidence line per document required), with a confirmation round after any fix.
  - As run (2026-11-27): Round 8, two parallel slices (code at xhigh, documents at high), 2 + 6 findings, all verified and fixed; Round 9's confirmation, all eight confirmed and one LOW wording fix applied; closed docs-only-low. The full suite after Round 8's code fixes, on the practitioner's "Yes, run it now" (2026-11-28), from the worktree's source: `ruff check .` clean, mypy no issues in 72 source files, 11343 passed / 9 skipped (11334 + 9 new).

### Phase P — Release and observe
- [ ] 🟥 **P.1 `main`, push, build of record.**   [operator]
  - On the practitioner's word: the script's docstring run command changed from this worktree's path to the main checkout's (Round 7); `main` fast-forwarded per C8; `npm run qa` and the dev extension build in the main checkout; push; the `Release` run; `gh attestation verify` (exit code) and the hashes; the row in `docs/release/pilot-builds.md` with D9's one rollback sentence; `AGENTS.md` and `CHANGELOG.md` updated in the same commit.
- [ ] 🟥 **P.2 Install.**   [operator]
  - The practitioner re-verifies from a normal terminal, installs over 0.4.2 after the day's last Complete or Discard with shadow mode on, reloads the extension and restarts Chrome. The dated line on `plan-phase3a-note-pipeline.md` is on `main` first.
- [ ] 🟥 **P.3 The first recording's lines.** The installed log shows `capture_stream … state=opened` with `detail_code=mme` and the chosen buffer in ms, a `state=closed` line, and no `state=default_latency`. Recorded here as numbers, by month.
- [ ] 🟥 **P.4 After about four weeks of clinic use.** From the installed log, by month: the largest `state=closed` gap under 30 s, and the counts of overflows, `state=default_latency` and `state=backlog_dropped` lines. Each deferred item's trigger is read against them.
- [ ] 🟥 **P.5 Close.** The findings-register row's resolved month, the lifecycle state, `/document`.

## Retained Follow-Up Items
N/A until the plan completes.

### Deferred — Actionable Later
- N/A

### Excluded — Revisit Only If Needed
- N/A

### Accepted Assumptions — Revalidate Later
- N/A

## Follow-Up Continuation Notes
N/A until the plan completes.

---
*Plan saved to: .cursor/plans/plan-capture-overflow.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
