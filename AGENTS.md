# Project: Privacy-First Cliniko Clinical Scribe

## What This App Does
A single-practitioner clinical scribe for two Cliniko clinics: a thin Chrome extension embedded in the Cliniko workflow plus a secure Windows desktop companion that records consultations, runs local Whisper transcription and local `gpt-oss-20b` note generation, and creates draft treatment notes through Cliniko's official API. No cloud processing of audio or transcripts; the clinician reviews and finalises every note in Cliniko. See `PLAN.md` for the full product plan.

## Tech Stack
| Layer | Technology | Notes |
|---|---|---|
| Frontend | Chrome extension (Manifest V3) | Runs only on authorised Cliniko domains; UI embedded in the treatment-note workflow |
| Backend | Windows desktop companion | Talks to Chrome via authenticated Native Messaging; local Whisper transcription + local `gpt-oss-20b` note generation |
| Database | Local encrypted session storage | Per-session encryption keys; Cliniko is the permanent system of record — no clinical data synced between machines |
| Hosting | None (local-only) | Chrome extension + local Windows desktop app; may move to a hosting platform later when commercialising; source=user-confirmed:2026-07-23 |
| DNS | | Only if used |

## Links
- GitHub: https://github.com/eliemokbel3-hub/Recording-clinic-software
- Production:
- Dev database:
- Live URL:

## Environment Variables
| Variable | Purpose | Local | Production |
|---|---|---|---|
| _None yet_ | Cliniko API keys are stored in Windows Credential Manager, not env vars; add rows here if env vars are introduced | — | — |

## Database Notes
[List the main tables, key entities, or schema notes here.]

## Local Run Steps
**Prerequisites:** Python 3.12+ (dev machine runs 3.14), Node 24 LTS (a 22.13+ release of the Node 22 line is also accepted by every extension tool; Node 23 is not), Google Chrome.

1. Clone the repo
2. `python -m venv .venv` then `.venv\Scripts\python.exe -m pip install -e ".\desktop[dev,ml]"` and `.venv\Scripts\python.exe -m pip install sounddevice` (the `[ml]` extra = faster-whisper/onnxruntime/huggingface_hub; `sounddevice` is deliberately not in pyproject — the test suite is absent-safe without it, but recording needs it)
3. Download the local ML models (one-time, the ONLY sanctioned network step): `.venv\Scripts\python.exe scripts\setup-models.py` — **run this YOURSELF from a normal terminal (PowerShell/cmd), never from an agent shell**: agent shells on this machine are MSIX-virtualized and their `%LOCALAPPDATA%` writes land in a package-private location invisible to user-launched apps (`docs/lessons.md`). ~3.0 GiB with all four benchmark candidates; silero + whisper `small` alone ≈ 470 MiB; the `speaker-embedding` entry (practitioner-profile plan) is in CANDIDATE mode until Task 0.5 pins it — `--only speaker-embedding --candidate-url <https URL>` downloads `<name>.onnx.candidate` and prints size + SHA-256 without promoting; a run without `--only` skips it visibly
4. `cd extension && npm install && npm run build` (bundle lands in `extension/dist`)
5. Register the native host: `.venv\Scripts\python.exe scripts\register-native-host.py` (per Windows user; rerun after any venv move or reinstall — installs to `%LOCALAPPDATA%\ClinikoScribe`, which must stay space-free and `.exe`-based or Chrome silently reports "host not found")
6. Load `extension/dist` as an unpacked extension in `chrome://extensions` (Developer mode), pin its icon
7. **Fully restart Chrome** — window-close is not a restart when background mode is on; verify no `chrome.exe` remains before relaunching
8. Verify: pinned icon shows a green **OK** badge; `.venv\Scripts\scribe-app.exe` self-test passes 2/2
9. QA suites: `desktop:` `ruff check . && mypy && pytest` (in `desktop/`); `extension:` `npm run qa`
10. Speaker measurement (Task 2.3, practitioner-run from a normal terminal once labelled recordings exist): `.venv\Scripts\python.exe scripts\measure-speakers.py <recordings-dir>` — see `docs/testing/speaker-measurement.md`

**Cloud (web) sessions are DISABLED for this project — practitioner decision 2026-09-05.** All work runs on the Windows host: do not start `/execute-loop`, a build, or a review from a Claude Code web session, and do not create cloud environments for this repo. The notes that follow are retained for the record only, from the one cloud run (2026-09-04): `python3.12 -m venv .venv && .venv/bin/pip install -e "./desktop[dev]"`, then `apt-get install -y libegl1 libgl1 libopengl0 libxkbcommon0 libfontconfig1 libdbus-1-3 libglib2.0-0` (PySide6 needs the EGL runtime before `QtWidgets` imports), and run the suite from `desktop/` as `QT_QPA_PLATFORM=offscreen SCRIBE_SKIP_INTEGRATION=1 ../.venv/bin/python -m pytest -q`. Expected host-only results, held as SETS rather than driven to zero: 8 items in `test_secure_storage.py` (no keyring backend), 3 in `test_status_and_app.py` (DPAPI), the 6 `TestWindowedPipeline` cases in `test_transcription.py` (numpy absent without `[ml]`), and 5 mypy errors (numpy stubs, Windows-only ctypes attributes). The `claude` binary there authenticates by environment token, so `/execute-loop` runs with the subagent executor and no cross-family peer (see `docs/lessons.md`). If a new session offers a cloud environment, decline it and choose your own computer.

**Launching the desktop app:** double-click `.venv\Scripts\scribe-app.exe` in Explorer, or run it from a PERSISTENT terminal (`.venv\Scripts\python.exe -m scribe_desktop.app` keeps console output). NEVER launch it from an ephemeral terminal (e.g. a chat Run button) — the closing terminal kills the GUI child (`docs/lessons.md`). Only one instance runs per user: a second launch shows "already running" and exits (named-mutex guard).

No `.env` needed — the project has no environment variables (secrets live in Windows Credential Manager; the offline ML kill-switches are set by the app itself).

Machine-specific run notes (local absolute paths, personal DB endpoints, machine-local ports) belong in a gitignored `AGENTS.local.md`, not here — and never put secrets in it.

## Current Status
**Phase 1 (security foundation) COMPLETE (gate passed 2026-07-26) and Phase 2 (local recording + transcription) COMPLETE (gate passed 2026-08-02; hardening closed at 0 CRIT/HIGH across 46 review rounds).** The what-works summary — encrypted per-chunk recording, DPAPI custody with the 24 h recovery window, fully-local silero + faster-whisper transcription with uncertainty marks and 2-speaker labels, the benchmark panel and the single-instance guard — is recorded verbatim in `docs/architecture/phase-history.md`.

**Phase 3A (note pipeline) IN PROGRESS — its internal Phases 1–8 and the hardening stage (H1–H4) are CLOSED (2026-08-04 → 2026-09-03), Phase 9's gates remain practitioner-owned.** Landed: the canonical 17-section note schema and assertion model (`note.py`), the config engine and use-time profile binding (`note_config.py`), autofill + prefill (`note_fill.py`), the four-check note checker with its dose/laterality severity contract (`note_check.py`), the compose→confirm→check→write pipeline and controller custody coordinator, the Note tab review UI, and the security docs extended to 3A. Suites 1368 desktop + 36 extension. The phase-by-phase record (decisions, review-round counts, what each internal phase closed) is verbatim in `docs/architecture/phase-history.md`.
**Internal 3A Phase 2 Task 2.3a (the Task 2.3 measurement harness) CLOSED 2026-09-04** — `speaker_eval.py` + `scripts/measure-speakers.py`, peer-converged (rounds 62–67); Task 2.3 itself waits on the shared recording set (`plan-practitioner-profile.md` Task 6.1).
**Internal 3A Phase 9 prep (Tasks 9.0 + 9.1a) CLOSED 2026-09-04, peer-converged 2026-09-05** (rounds 68–72, 0 CRIT/HIGH; the cloud-built diff's owed cross-family pass ran on the Windows host). Landed: CI actions on Node 24 (proven green, zero annotations), `docs/testing/shipping-gate.md` (ratified unchanged as rubric v1 on 2026-09-05) and three both-outcome copy-wiring tests (`COPY_TO_CLINIKO_ENABLED` stays `False`). Phase 9's gates — 9.1 (shipping) and 9.2 (completion) — remain practitioner-owned. Full record: `docs/architecture/phase-history.md`.
**Practitioner profile IN PROGRESS — Phase 0 agent tasks CLOSED 2026-09-06 (`.cursor/plans/plan-practitioner-profile.md`, 8%)**: Tasks 0.1 (the Task 9.1 pause pointer in the Phase 3A plan) and 0.3 (`setup-models.py` speaker-embedding candidate mode with https-only redirects, `scripts/speaker-embedding-smoke.py`, 59 tests) built by the first `/execute-loop` run on this plan (run stage-0), in-session review converged (rounds 4–5) and cross-family codex `gpt-6-astra` peer pass converged (rounds 6–7: 1 HIGH verified MED, 1 MED, 2 LOW, all fixed). Suite 1427. The run is PAUSED for the practitioner's Task 0.4 (fetch + smoke, normal terminal), then 0.5 (agent), 0.6 (practitioner), D-P1 `[decision]`. The plan itself: voice enrolment (an encrypted, DPAPI-custodied voice fingerprint; practitioner-vs-other attribution inside `transcribe_session`; the clinician role auto-confirmed UNCONDITIONALLY from it by practitioner decision, with a visible one-click change), a per-practitioner cue file (`section_cues.json`, whole-file replacement, inside the note's `config_digest`), and consented phrase learning (propose-then-approve, practitioner utterances only, names and numbers refused, plain-text config disclosed in consent-v1 — ratified); planned, hardened and peer-converged 2026-09-05 (codex rounds 1–3). Consequence: the Task 9.1 shipping-gate RUN stays PAUSED (rubric v1 frozen) until enrolment ships, so ONE recording set serves the gate, Task 2.3 and the enrolment measurement.

## Last Session
- Date: 2026-09-06 (Windows host; `/execute-loop` run stage-0 on the practitioner-profile plan — Phase 0 agent tasks)
- Worked on: the wizard (preset claude -p + codex peer, architect OFF; executor `claude-fable-5-1`/high default account, peer `gpt-6-astra`/high; isolation=none by practitioner choice — the venv's editable install points at the base checkout, so a worktree would test the wrong tree) → preflight (harness probe: grants work, the compound gate command is denied inside the executor → verify=composer; config-snapshot high-auto=on attested) → Tasks 0.1 + 0.3 built by one executor session over six wrapper legs (build, review r4, review r5, peer-r6 verify, peer-r6 fix, lint) → composer-run suites at each handoff → codex peer rounds 6–7 (4 → 0) → `/document` (this block; rounds 4–7 compacted into the findings sidecar) → the phase commit `1e7528b` → `/push` (2026-09-09; CI run 34287270126 green on all three jobs, 0 annotations).
- Pattern worth knowing: (1) The wizard's probe script reports codex ABSENT from a Git Bash shell — `shutil.which` misses the `codex.cmd` shim — while `codex` runs fine from both shells; probe the catalog by hand (`codex debug models`) and carry on. (2) The loop's Windows desktop notifications are delivered through the BurntToast PowerShell module (`New-BurntToastNotification`); without it every `NOTIFY:` record is `failed` and a phase cannot flush before its commit. Installed CurrentUser on 2026-09-06 (a non-interactive shell needs the NuGet provider first: `Install-PackageProvider NuGet -Force -Scope CurrentUser`, then `Install-Module BurntToast -Scope CurrentUser -Force`). (3) The helper computes a NOTIFY record's mode from `class=` + `severity=` and keys a finding-route record by `--round/--id`; a hand-supplied `mode=` or `key=` is refused. (4) A cross-family peer round at `gpt-6-astra` HIGH over a ~940-line diff ran ~5 min and stayed inside the 5-hour window (two rounds plus the previous day's plan rounds).
- Next priority: the PRACTITIONER's Task 0.4 (normal PowerShell — `.venv\Scripts\python.exe scripts\setup-models.py --only speaker-embedding --candidate-url <https URL of the WeSpeaker ResNet34-LM ONNX>`, then `scripts\speaker-embedding-smoke.py --model <the .candidate path> me-1.wav me-2.wav other.wav`; paste the URL/size/SHA-256, the I/O signature, the cosine matrix and the model card's preprocessing recipe onto Task 0.4). Then resume `/execute-loop` (same as last run) for Task 0.5, pause for 0.6, then D-P1. `/retro` over `.cursor/loops/stage-0-*` is recommended when the phase run ends.
- Still needs the PRACTITIONER: Tasks 0.4 and 0.6 (above); the shared recording set (Task 6.1: ~10 mock consultations through the app AND to labelled 16 kHz WAVs, a second real voice for the patient part, one enrolment WAV) plus the Task 2.3 retention decision — hard-return-by before Phase 9's completion gate.

## Known Issues / Next Tasks
- [x] **Cross-family peer pass over the stage-9 diff DONE 2026-09-05** (Tasks 9.0 + 9.1a): codex `gpt-5.6-sol` xhigh rounds 70–72 on the Windows host, driven from an interactive `/peer-review` session, 8 → 3 → 0 findings — one HIGH verified MED (the copy action and its payload were unpinned; two clipboard pins added, suite 1366 → 1368), three MED and seven LOW doc / plan / test-docstring corrections — every fix confirmed by the next round; `.github/workflows/ci.yml`, `docs/testing/shipping-gate.md`, the `test_ui_screens.py` additions and `AGENTS.md` are peer-converged. (Was: `Risk if deferred: correctness` · `Revisit by: before Task 9.1 ratification`.)
- [ ] **Flaky real-ML integration leg, once** — `tests/test_integration_no_sockets.py::test_recorder_no_sockets_during_real_whisper_transcription` failed on 2026-08-18 in a full run that took 8m50s (normal 43–115 s, real-ML legs included) and passed in isolation and on every full rerun since; the change under test was runtime-inert. Best explanation is cold model loading plus I/O contention tripping a timing-sensitive leg. NOT confirmed either way: the traceback was lost to a truncated pipe. If it recurs, capture full output before anything else. `Risk if deferred: minor` · `Revisit by: next recurrence`
- [ ] **Three-or-more-speaker labelling** — the speaker step assumes exactly two voices (2-means over VAD-segment embeddings), so a third person in the room (parent, carer, interpreter, student) is silently merged into another speaker's label and the clinician must fix attribution when reviewing. Approach recorded in the Phase 2 plan: estimate the speaker count instead of assuming it, with ungated ONNX speaker embeddings as the fallback if spectral features prove too weak. `Risk if deferred: ux-degradation` · `Revisit by: Phase 3 validation set construction` `[2026-09-05 reconciliation] Needs re-evaluation — plan-practitioner-profile.md's voice enrolment classifies practitioner-vs-other BEFORE clustering (the merged-practitioner failure goes away); estimated k for the remaining voices stays deferred there (D-S1) pending the shared recording set.`
- [ ] **Diarization quality tuning** beyond the chosen approach — same trigger, do it together with the item above. `Risk if deferred: ux-degradation` · `Revisit by: Phase 3 validation set construction`
- [x] **CI action runtimes moved to Node 24** (Task 9.0, 2026-09-04): `actions/checkout@v5`, `actions/setup-python@v6`, `actions/setup-node@v5` and the extension job's `node-version: 24` (practitioner-decided; Node 20 EOL 2026-04-30). Each target major's `action.yml` declares `runs.using: node24` (verified 2026-09-04). PROVEN 2026-09-05: CI run 33934875082 on `main` (`e7f4072`) green on all three jobs (desktop 3.12, desktop 3.14, extension on Node 24.20.0) with zero annotations; the only deprecation text is two Node module warnings (DEP0040 `punycode`, DEP0169 `url.parse`) from `setup-node@v5`'s own code, not runtime-version notices. Dev machines: install Node 24 LTS once (`node --version`).

## Subsystem Documentation
Add concise "if working on X, read Y" pointers here for any subsystem that has focused documentation.
These pointers are treated as required reading by the agent before planning or modifying work in that area.

- Before planning or building any feature, read `PLAN.md` (product spec: architecture, phased roadmap, safety and test requirements, commercial path).
- If touching security, crypto, logging, the native-messaging channel, or data handling, read `docs/security/threat-model.md` and `docs/security/data-flow-map.md` first (trust boundaries, accepted residual risks, enforced constraints).
- If changing what data is kept or for how long, read `docs/security/retention-schedule.md`.
- If working on the message protocol, the canonical contract is `protocol/fixtures/` (both mirrors are tested against it — see `protocol/fixtures/README.md`).
- Before any task, skim `docs/lessons.md` — short, run-evidenced gotchas about this machine and this workflow that will otherwise cost hours.
- If working on the speaker-measurement harness (Task 2.3 / 2.3a, `speaker_eval.py`) or preparing labelled recordings, read `docs/testing/speaker-measurement.md` (input contract, what is measured, the teardown custody contract).
- If preparing, ratifying or running the Task 9.1 shipping gate (copy-to-Cliniko enablement), read `docs/testing/shipping-gate.md` — rubric v1, ratified 2026-09-05: the transcript set, the text-free rubric and pass rule, the in-app procedure, custody, and the grep-derived flip checklist.
- If authoring or installing the shipping-gate run config (prefill seeds, autofill triggers, later `section_cues.json`), read `docs/testing/shipping-gate-config/README.md` — install steps, the one-claim-per-sentence rule, the loader smoke.
- If you need the phase-by-phase history (what closed when, review-round counts, suites at each close), read `docs/architecture/phase-history.md`; `AGENTS.md`'s Current Status keeps only what is current.
- If doing UI work (desktop screens now, Chrome-side UI in Phase 5), read `docs/design-system.md` for the app's interaction conventions.
- If changing `note_check.py`'s Check 2 or its severity contract, read the "checker's honest limit" block in `docs/security/threat-model.md` first: laterality differences are REVIEW-graded by practitioner decision (2026-09-03) after the parser's bilateral/correlative limits proved not locally closable; negated-symptom and exclusive-dose differences still block. Do not re-open laterality parser patching without re-reading rounds 48–59 in the plan.

<!-- Example entries:
-->

## Documentation Status
- Structure version: v23
- Last reviewed: 2026-09-09
