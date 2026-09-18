# Feature Implementation Plan
**Feature:** note-learning-and-styles
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: `.cursor/plans/plan-practitioner-profile.md` (this plan consumes its cue file, learned-phrase mechanism, consent versioning and Practitioner tab; its Excluded item "training or fine-tuning any model" binds this plan)
- Follow-up plans: None (PLAN.md Phases 4 and 5 — Cliniko API + embedded controls — are separate phases, not children of this plan)

## Goal
Make the scribe feel like less work than typing: transcribe WHILE the consultation is recorded so the note is ready when Stop is pressed; let the practitioner type their own shorthand over a note line (say "we'll put a crack into the neck" → the Treatment line becomes "HVLA Cx") and learn that as a rule from the edit, so the same utterance next time proposes the shorthand and, after three unchanged confirmations, lands pre-filled; offer four writing styles (Verbatim, Clean clinical, Own voice, Narrative — the Heidi-like prose) with the prose styles produced by a LOCAL language model that may only rephrase already-confirmed content and is checked afterwards; let the practitioner seed all of this by uploading one to five of their own past notes at first run or any time from settings, learned from and then deleted on their say-so; and replace the per-line click for the practitioner's own rules with visible marking plus Save as the single act of ratification.

## Planning Extraction Summary

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.1; executed in architect mode (Fable architect, `claude-opus-5` via the profile-level `loop-delegate` definition, as in practitioner-profile stages 3–6); tier-gap dosing applied (design decisions, edge-case inventory, data contracts, acceptance criteria and the caller manifest locked; no microcopy dictionary or permission matrix — single-user app). Tasks marked `[executor: premium-only]` are the custody, threading and checker work the architect keeps rather than delegates.

### Agreed Scope (Build Now)
- Live transcription during recording (Phase 1): a `LiveTranscriber` worker fed PLAINTEXT PCM by a tee installed before encryption, runs the existing stage functions one ~30 s window at a time (open segments force-closed at 30 s), keeps segments + per-segment embeddings in memory, never touches `SessionCrypto` or the store, never writes a file. Finish seals capture as today; the tail is drained on the processing thread, the shared `assemble_transcript` helper runs the speaker pass over the kept embeddings and `write_transcript` writes `transcript.enc` once. Discard stops the worker, drops its buffers and clears the live view. Any worker failure, queue overflow or fall-behind degrades to today's batch path with a named reason.
- Typed edits (Phase 2): the Note tab gains an Edit control on a note line or proposal that replaces its text with practitioner-typed wording — a `clinician` provenance assertion carrying the clinician's decision. This is the surface shorthand learning hangs off (the tab has no text editing today — code-verified).
- Expansion learning (Phase 2): on Save, a typed edit whose source utterance is the practitioner's own is recorded as a learned autofill rule (trigger → wording) appended to the practitioner's `autofill_rules.json` with a metadata sidecar, review-later on the Practitioner tab with one-click delete. Triggers pass THE refusal filter; typed wording passes the narrower `refuse_typed_wording` (numbers, dates, medications; practitioner decision 2026-09-18). After `LEARNED_RULE_AUTO_CONFIRM_AFTER = 3` unchanged confirmations the rule's lines arrive pre-filled; a Remove of a pre-filled line demotes the rule back to proposing (count reset), never deletes it.
- Save-as-ratification (Phase 2; practitioner decision 2026-09-18): lines from the practitioner's own `autofill_rules.json` / `prefill_templates.json` entries and from auto-confirmed learned rules enter the note with `ConfirmationDecision.decided_by = "config"` (config digest, confirmation count), rendered with a distinct "pre-filled" mark, removable, and ratified by Save whose label reads "Save — confirms the N pre-filled lines shown". Model-derived proposals keep per-line confirm. Interim review stays in the desktop Note tab until PLAN.md Phase 4 places the draft in Cliniko.
- Writing styles (Phases 3–4): a persisted `note_style` — `verbatim` (today's rendering), `clean` (terse one-line-per-assertion rendering, no substitution, no model), `own_voice` (local model conditioned on the style profile), `narrative` (local model, fuller standard clinical prose — the Heidi-like option). Default after this plan: `clean`. Prose styles run in the Note tab after finalisation, rephrase ONLY confirmed assertion text, pass the new fidelity gate (Check 5) and are ratified by Save; a failing section keeps `clean` with a review warning; one rendering path serves display, persistence and Copy.
- Sample-note learning (Phase 3): optional at first run (banner line, never blocking, no voice profile required — consent recorded in the style store) and always available on the Practitioner tab: 1–5 past notes per run (recommended 3–5), plain text, pasted text or `.docx`, read into memory only. Derived and saved to a DPAPI-wrapped `style_profile.json` under its own key: section order/heading map, shorthand from a shipped controlled vocabulary (unrecognised tokens tick-to-keep), style measures, and up to 30 exemplar sentences that pass the refusal filter UNCHANGED (practitioner decision 2026-09-18: refuse, never scrub), each shown for review with per-item remove before and after save; a key-first "Delete learned style" action. Deleting the originals is a separate explicit confirmation naming the paths, unticked by default.
- Local language model (Phase 4): the runtime chosen by Task 4.0's preflight (`llama-cpp-python` prebuilt CPU wheel or `onnxruntime-genai`), installed only as a pinned hashed wheel under `[ml]`; ONE ~4B instruct model at 4-bit (practitioner decision 2026-09-18: pin the 4B now) pinned in `scripts/setup-models.py` by SHA-256 with size and free-space checks; the no-sockets integration test is the offline control for this runtime.
- Consent v3 (Phase 0): covers typed-edit learning, sample-note learning and Save-as-ratification; v2 kept as history; re-consent on the tab.
- Note schema v2 (Phase 0): `note.enc` gains the new fields with defaults so v1 notes remain readable.
- Security docs, design system, retention schedule and threat model extended for every new surface (Phases 0 and H).

### Deferred — Actionable Later
- PLAN.md Phase 4 (Cliniko API draft creation) and Phase 5 (embedded Start/status controls, patient-change pause)
  - Why deferred: practitioner-confirmed 2026-09-18 — separate PLAN.md phases; this plan removes the desktop-side friction so that when Phase 4 lands, Cliniko becomes the single review step with no further pipeline change.
  - Intended future outcome: press Start beside the Cliniko note, Finish, open the draft once.
  - Relevant files / subsystems: `extension/src/*` (scaffold only), `native_host.py`, `protocol/fixtures/`.
  - Dependencies / prerequisites: this plan's Phase 2 (`decided_by = "config"` lines) so the draft carries pre-filled content.
  - Recommended next action: plan Phase 4 after this plan's Phase 2 closes.
  - Risk if deferred: ux-degradation: review happens in the desktop app until then.
  - Revisit by: this plan's Phase 2 close
- The Phase 3B validation set and completion gate (no unsupported clinical assertion over the set)
  - Why deferred: needs the shared recording set (practitioner-profile Task 6.1), practitioner-owned.
  - Intended future outcome: the prose styles measured over the set; the Task 9.1 gate re-run with `clean` as the default style.
  - Relevant files / subsystems: `docs/testing/shipping-gate.md`, `speaker_eval.py` pattern.
  - Dependencies / prerequisites: Task 6.1 recordings.
  - Recommended next action: extend the gate rubric with a style column when the set exists (Task H5 adds the column now, empty).
  - Risk if deferred: correctness: prose styles ship behind the same disabled copy flag until measured.
  - Revisit by: Task 6.1 recordings exist
- `gpt-oss-20b` as the prose model
  - Why deferred: practitioner decision 2026-09-18 — the prose job is rephrasing short confirmed lines, which a 4B model handles; the 12 GB file and a GPU wheel are not justified before quality is measured.
  - Intended future outcome: revisit only if the 4B's Check 5 pass rate over the ten fixture notes (Task 4.3's acceptance) is below 9/10 after prompt tuning.
  - Relevant files / subsystems: `language_model.py`, `scripts/setup-models.py`.
  - Dependencies / prerequisites: Task 4.3's fixture pass rate recorded.
  - Recommended next action: none unless the trigger fires.
  - Risk if deferred: ux-degradation: prose quality bounded by the 4B model.
  - Revisit by: Task 4.3 fixture pass rate < 9/10
- CUDA (GPU) build of `llama-cpp-python`
  - Why deferred: practitioner decision 2026-09-18 (Deferral gate) — the CUDA wheel comes from a second download source outside the one sanctioned network step; CPU inference of a 4B model is acceptable for a few seconds per section.
  - Intended future outcome: a pinned, hash-verified GPU wheel documented as a second sanctioned fetch, if CPU time proves too slow.
  - Relevant files / subsystems: `desktop/pyproject.toml`, `docs/security/data-flow-map.md` non-flows.
  - Dependencies / prerequisites: Task 4.3's measured CPU seconds-per-section on the practitioner's machine.
  - Recommended next action: none unless the trigger fires.
  - Risk if deferred: ux-degradation: prose rendering takes seconds, not sub-second.
  - Revisit by: CPU prose time per note > 20 s on the practitioner's machine
- Estimated speaker count (D-S1) — unchanged from the parent plan; the live path keeps the parent's labelling rule.

### Excluded — Revisit Only If Needed
- Training or fine-tuning any model on notes, transcripts or phrases
  - Why excluded: practitioner decision 2026-09-05 (parent plan). Sample-note learning is EXTRACTION into config; style conditioning is prompt-time only.
  - When to revisit: never for clinical data.
  - Relevant files / subsystems: `sample_notes.py` (new), the Phase 4 provider.
- Learning from patient or other-speaker lines; negative learning from removals — unchanged parent exclusions; a Remove of a pre-filled line demotes a learned rule to proposing but never deletes it.
- Any cloud or network path — unchanged; the model download stays inside `scripts/setup-models.py`.
- Scrubbing (editing) sentences to keep them as exemplars
  - Why excluded: practitioner decision 2026-09-18 — a control that edits instead of refusing breaks the fail-closed rule (`docs/lessons.md`); exemplars are kept only when they pass unchanged.
  - When to revisit: never.
- Reading `.pdf` sample notes
  - Why excluded: needs an OCR/pdf dependency for little gain; the practitioner can paste text.
  - When to revisit: if practitioners in a commercial deployment hold notes only as PDF.
- Learning trigger → wording from a typed line with NO matching practitioner utterance
  - Why excluded: no trigger exists to learn; the line is still added, just not learned.
  - When to revisit: never — definitional.
- Shorthand substitution at render time (the first draft's `clean` renderer)
  - Why excluded: it would change confirmed text AFTER the check and the digest; shorthand reaches a note only through a learned or authored rule the practitioner confirmed.
  - When to revisit: never.

### Accepted Assumptions — Revalidate Later
- One practitioner per Windows login (parent plan assumption). Trigger: commercialisation.
- Whisper `small` transcribes a ~30 s window in well under 30 s on the practitioner's machine (Phase 2 benchmark figures), so the live worker keeps up.
  - Why accepted: not a decision — the worker's fall-behind cut-off (D2) makes the failure mode a named degradation, not a correctness issue.
  - Risk if false: live mode switches itself off and Finish uses the batch path with the reason line; verified by Task 1.6's benchmark line.
- The 4B instruct model produces per-section prose that passes Check 5 in at least 9 of 10 fixture notes after prompt tuning.
  - Risk if false: the `gpt-oss-20b` deferral trigger fires.
- Exemplars that pass the refusal filter unchanged carry no patient identifier.
  - Why accepted: the filter refuses name-shaped, numeric, date and medication tokens; the practitioner reviews each exemplar; one-click delete.
  - Risk if false: a patient detail persists in `style_profile.json` (DPAPI-wrapped under its own key) — bounded by review and delete. Trigger: H3 security review.

### Key Design Decisions
See `## Design Decisions` D1–D12 (state-once). The ones that constrain everything else: the live worker sees plaintext PCM before encryption and never holds session crypto (D1); the model only ever sees confirmed assertion text, never the transcript (D6); no new provenance for config-decided lines — the decision carries `decided_by` (D4); sample notes are never copied and deletion of the originals is an explicit confirmation (D9).

## Key Findings

### Files / Symbols Involved (code-verified 2026-09-18 at `main` `b3a65a2`; line numbers from the hardening pass)
- `desktop/src/scribe_desktop/transcription.py` — `transcribe_session` (1099): `segment_session_audio` over the whole store → `pack_transcription_windows` (516) → `WhisperSpeechProvider.transcribe_segment` (998) per window; per-segment spectral embeddings and enrolment cosines are computed INSIDE the same window loop from the window PCM (1212–1235) → `assign_words_to_segments` (553) → `mark_words` (428) → `label_speakers` (726) / `attribute_speakers` (841) → `write_transcript` (1040). `TranscriptDocument.created_at` is `datetime.now(UTC)` (1251) — no byte-for-byte equality between runs is possible. `recover_session_transcription` (1293) is the crash-recovery path and stays as is.
- `desktop/src/scribe_desktop/audio_capture.py` — `CaptureWorker` (292) takes ONE `sink` callable at construction (313) invoked on the single writer thread; an exception in the sink goes `_fail()` → `_on_capture_failure` → session FAILED (476–484). The live tee must therefore swallow and report its own errors, never raise into the sink. `stop(flush=True)` (405) delivers the final partial chunk.
- `desktop/src/scribe_desktop/session.py` — `SessionState` (72); `SessionController.start` (364; builds the worker with the `append_chunk` sink at ~400–407 and retires a previous live session at 378–387), `pause` (421; joins the capture barrier outside the lock), `resume` (439), `finish` (448–470; `worker.stop(flush=True)` outside the lock, THEN `store.finish()`), `transcribe` (488; the `transcribing` flag at 533, the `_custody_reservations` refusal at 513–518 — the flag is single-run-per-session and `discard()` RAISES when it is set at 688–694, so the live worker must NOT reuse it), `complete` (575), `discard` (668). Controls are promised safe from any thread. Controller construction takes typed factories (`ui/main_window.py:84`, `ui/session_screen.py:39`).
- Callers to update when signatures move: `ui/session_screen.py:151` (`start`), `:217` (`transcribe(wrapped)`); `speaker_eval.py:1078–1082` and `tests/test_integration_no_sockets.py:482` call `transcribe_session` directly (unchanged by this plan — D1 keeps the batch signature).
- `desktop/src/scribe_desktop/session_store.py` — `iter_chunks` (420), `append_chunk` (378), `finish` (391); `write_note` (817) refuses non-transcript assertions lacking digest/config evidence — a consumer of the decision model (Task 0.2).
- `desktop/src/scribe_desktop/note.py` — `NoteModelProvider` (707), `ExtractiveNoteProvider` (1154), `MockNoteModelProvider` (1353, test-only); `NoteSpan.provenance` is `Literal["transcript","autofill","prefill"]` with `_check_provenance` (332–348); `NoteAssertion._check_confirmation` (~395–405) requires `proposal_id`, `shown_text_digest`, `config_digest` for non-transcript provenance; `compose_draft` (~1815) and `finalise_note` (1976–1979) refuse any base assertion that is not transcript-provenance; `GeneratedNote.schema_version` 1 (514, 620), models are `extra="forbid"`. Provenance is also branched on in `note_check.py` 436, 1078, 1101, 1364, 1415 and `ui/models.py` 408 (`PROVENANCE_LABELS`), 942; `ui/note.py` 569, 747.
- `desktop/src/scribe_desktop/note_config.py` — `AutofillRule` (561), `AutofillRulesFile` (789; duplicate triggers already refused by validation), `load_note_config` (945, whole-file, all-or-nothing), `refuse_learning_candidate` (1100; takes original-case TRANSCRIPT source words with `first_in_segment`/`following`; refuses capitalised alphabetic tokens as names — so it refuses "HVLA Cx"; opener exemptions are defined for segment position 0 only, 1119–1131), `append_user_cues` (1328; checks `known` before writing, 1357–1373 — the pre-write duplicate check learned rules must mirror), `LEARNED_SIDECAR_FILENAME` (1012), `load_learned_phrases` (1390), `delete_user_cue` (1427), `default_config_root` (893), filenames 168–170.
- `desktop/src/scribe_desktop/note_fill.py` — the one-authored-entry → one-proposal emitters (the only shipping `NoteProposal(...)` construction sites).
- `desktop/src/scribe_desktop/note_check.py` — Check 1 `reconstruction_warnings` (37–51, 422–451) rebuilds a transcript assertion byte-for-byte from `(segment, first_word, last_word)`; it CANNOT validate a rephrase, hence Check 5 (D6).
- `desktop/src/scribe_desktop/ui/note.py` — `add_line` (614), `remove_line` (658), `move_line` (673), `undo_line` (714) — whole-utterance only; `confirm_proposal` (506), decline, retract; `save` (1068: the ONLY place a learned phrase is written); `_copy_ready()`. NO text editing exists.
- `desktop/src/scribe_desktop/ui/models.py` — `CONSENT_TEXT_V2` / `CONSENT_TEXT_VERSION`, `consent_is_current` (1287), `learning_status` (1050), `build_note_generator` (1075), `build_transcriber` (1417; constructs `WhisperSpeechProvider`/`SileroVad` INSIDE the worker call, 1434–1437, so the GUI thread never blocks on model load), `build_recovery_runner` (1453), `attribution_readiness` (1349), `COPY_TO_CLINIKO_ENABLED`.
- `desktop/src/scribe_desktop/ui/practitioner.py` — `on_confirm_consent` (582), `refresh_learned_phrases` (774), `delete_learned_phrase` (817), first-run banner; `ui/main_window.py` tabs (156–162), D10 first-run selection (170–173).
- `desktop/src/scribe_desktop/practitioner_profile.py` — ONE `key.dpapi` + `voice.enc` per `profile\` root; `save_profile` (275–290) reuses the existing key; `unwrap_key_from_file` verifies the description. The style profile therefore needs its OWN root and key (D9), never a second artefact under `profile\`.
- `desktop/src/scribe_desktop/benchmark.py` — `assert_offline_env` (43–98) asserts the Hugging Face / onnxruntime kill-switch variables; `llama-cpp-python` reads none of them — the honest offline control for it is the local path + pin + the no-sockets test (D8). `default_models_root` (101–105) is the MSIX-virtualisation-sensitive cache.
- `desktop/pyproject.toml` — `[ml]` = `faster-whisper>=1.2`, `onnxruntime>=1.28`; mypy `ignore_missing_imports` override list at 80–103 (needs `llama_cpp` and `docx`); ruff banned-api list 65–72.
- `scripts/setup-models.py` — the pins + verify logic and the `.candidate`-promotion pattern (parent Task 0.6) to reuse for a large file.
- Docs to extend: `docs/security/threat-model.md` (Phase 3A section 173–407 — boundary 2 at 200–206 states the per-assertion-confirmation control this plan replaces; practitioner-profile section 408–671), `docs/security/data-flow-map.md` (flows 12–13; explicit non-flows 274+ incl. "clinical artefacts exist on disk only under per-session keys" at 275–279, which the style profile amends), `docs/security/retention-schedule.md` (in-memory row; the models-cache size row), `docs/design-system.md` (clinical-content rules 131–162), `docs/testing/shipping-gate.md`.

### Codebase Integration Notes
- Live transcription reuses every stage of `transcribe_session` as functions; the worker is a driver over plaintext PCM, not a second pipeline and not a store reader. The recovery runner and the batch signature stay exactly as they are.
- `SessionController.transcribe` needs NO signature change: `build_transcriber` closes over the sealed worker, drains its tail and runs the document assembly + `write_transcript` inside the same `transcriber(directory, crypto)` callable on the processing `TaskThread` (the round-32/42 reservation reasoning in `transcribe()` stays literally untouched).
- `label_speakers` (`transcription.py:726`) takes raw PCM and is documented as PAIRED with the inline per-window path in `transcribe_session` (`:740`); the batch tail at `:1238–1250` decides from `np`, `saw_empty_segment`, `len(embeddings)`, `has_text`, `similarities` and `attributing`. The live path cannot call `label_speakers` (D1 drops PCM) — Task 1.0 extracts that tail into a shared `assemble_transcript(...)` helper used by both drivers (codex PR-MED-005), the public batch signature unchanged.
- Learning-on-Save is the single write point for learned cues; learned rules use the same moment, the same `known` pre-write duplicate check and the same user-file + metadata-sidecar shape.
- Config loading is whole-file with loud failure; a learned rule is validated as an `AutofillRule` BEFORE the write so a bad write cannot brick loading.
- `ui.models` is the composition layer: every new factory (live transcriber, typed-wording filter, style renderer, prose provider, sample-note learner) is built there so the screens stay ML-free and testable with mocks.
- Shared helpers across phases: `refuse_typed_wording` (Phase 2 typed wording ONLY — sample-derived shorthand uses the controlled vocabulary and exemplars the full refusal filter, D10), the learned-entry metadata sidecar model (cues today, rules in Phase 2), `model_file_report_lines` for the language model, the DPAPI-wrapped-store pattern (voice today, style profile in Phase 0).
- Gotchas (`docs/lessons.md`): model downloads must be run by the practitioner from a normal terminal (MSIX-virtualised agent shells); the app must never be launched from an ephemeral terminal; heredocs over ~1 KB fail in the Bash tool; verify=composer on this host; a control must fail toward safety (refuse, never edit-and-keep).

### External / API Findings
- Prose runtime installation: see D8 and Task 4.0 — `llama-cpp-python`'s PyPI default BUILDS from source and its prebuilt CPU wheels live on a separate index; `onnxruntime-genai` ships PyPI wheels; Python 3.14 availability of either is unverified until the practitioner's preflight. Neither has stubs (mypy override) nor a `local_files_only` switch; both load a local path only.
- Candidate 4B model: an instruct GGUF at Q4_K_M ≈ 2.5 GB (exact repository, file and SHA-256 recorded by Task 4.1 when pinned; Qwen3-4B-Instruct is the first candidate to try).
- `python-docx` has no stubs: mypy override needed; it joins BASE `dependencies` (the installer ships it), not `[ml]`.

## Planned Workflow Summary

### Flow 1 — A consultation with live transcription
- Start → the capture sink encrypts chunks to the store as today AND hands the same PCM to the live worker's queue. Each ~30 s of VAD-segmented audio is transcribed and embedded in memory and its segments posted to the Transcript screen (display-only, header "Live — updates while recording"). Pause stops feeding; Resume continues. Finish → capture flushes and the store is sealed (fast, on the GUI thread as today); the processing thread then drains the worker's tail, assembles the document with the speaker pass over the kept embeddings and writes it once; generation starts. If the worker died or fell behind, Finish runs the batch path with the status line "live transcription stopped; transcribing after the recording instead". Discard → the worker is stopped and its buffers dropped before the key is destroyed; the live view is cleared.

### Flow 2 — Learning shorthand from a typed edit
- The transcript holds the practitioner's line "ok we'll put a crack into the neck now"; the extractive draft routes it to Treatment. The practitioner presses Edit on that line, types "HVLA Cx", and saves. Save records `trigger="crack into the neck"` → `["HVLA Cx"]`, section `treatment`, appended to their `autofill_rules.json` with metadata in the sidecar (the trigger passed the refusal filter; the wording passed `refuse_typed_wording`). Next consultation the utterance yields a proposal "HVLA Cx" marked learned; after three unchanged confirmations it lands pre-filled, marked, and Save ratifies it.

### Flow 3 — Choosing a style
- Practitioner tab → Writing style: Verbatim / Clean clinical / Own voice / Narrative. Clean needs no model. Own voice and Narrative are greyed with a reason line when the language model is absent, and Own voice also when the style profile is empty.

### Flow 4 — Seeding from past notes
- First run shows a second banner line: "Optional: teach the scribe your note style from 1–5 past notes." The tab's "Learn from my notes" group accepts up to five files or pasted text, shows what will be kept (headings map, shorthand list, the exemplar sentences that passed unchanged) for review with per-item remove, saves on confirm, then asks separately whether to delete the listed original files.

## Design Decisions
- D1 — The live worker is fed plaintext PCM by a tee wrapped around the capture sink BEFORE encryption; it never holds `SessionCrypto`, never reads the store, never writes a file; it keeps per-window segments and per-segment embeddings (and enrolment cosines when a profile is applied) in memory and drops PCM per window. Finish assembles and writes once through the batch stage functions. Why: no custody entanglement, the idempotence and crash-recovery contracts untouched, the batch path stays the fallback. Rejected: a worker reading the encrypted store (custody under Discard); writing partial transcripts (breaks atomic replace and the footer contract).
- D2 — Lifecycle: the worker has its OWN handle on the live session (`_LiveSession.live_transcriber`), never the `transcribing` flag. `discard()` in RECORDING/PAUSED stops-and-joins it (bounded timeout) inside the first locked section before the key-first deletion and tells the Transcript screen to clear. `finish()` stays synchronous and cheap: it seals capture exactly as today (`worker.stop(flush=True)`, then `store.finish()`), marks the worker "sealed" (no more feeding) and leaves it attached to the live session; the TAIL DRAIN (the last open segment and any queued windows) happens on the existing processing `TaskThread` inside the transcriber callable (Task 1.3), never on the GUI thread (codex PR-MED-003: `ui/session_screen.py:175` calls `controller.finish()` directly in the GUI slot). From PROCESSING on, the worker is owned by that callable and the existing `transcribing` guard covers Discard as today; an exception in the drain marks live mode failed (batch fallback), never the session. `pause()`/`resume()` gate feeding. Cleanup is by ATTACHED-WORKER OWNERSHIP, not by state (codex PR-MED-014): whichever path leaves a worker attached — `_fail_locked` (a footer-write failure at `session.py:480–482` enters FAILED with no capture-failure callback), `_on_capture_failure`, retire-on-`start()`, and `discard()` in ANY state where the transcriber callable has not yet claimed the worker (RECORDING, PAUSED, FAILED, and the PROCESSING interval before `transcribing` is set at `:534`) — stops it, joins it and confirms its buffers are cleared BEFORE `discard_session` destroys the key; a join timeout is a reported failure, never counted as cleared; late live-view updates after a stop are dropped. The tee never raises into the sink: any error flips the worker to failed and is reported through the status line. Bounds (codex PR-MED-004): an open VAD segment is force-closed at `LIVE_MAX_SEGMENT_SECONDS = 30` at the lowest-probability frame of its last 5 s (the two halves are separate segments; `pack_transcription_windows` then never sees an oversized live segment); queued plaintext PCM is capped at three windows INCLUDING the model-load period — exceeding it, or more than two transcribed windows behind, stops the worker itself (failed, "live transcription could not keep up"). Why: the single-run-per-session `transcribing` guard (`session.py:513–535, 688–694`) would refuse Discard for the whole consultation if reused during RECORDING. Rejected: reusing the flag during recording; draining the tail inside `finish()`.
- D3 — The Whisper provider and VAD for the live worker are constructed on the worker's own thread at Start; a load failure flips live mode to failed with the reason line and the consultation continues; at Finish the worker's provider is released before the batch fallback constructs its own, so two models are never resident. Why: `build_transcriber` deliberately loads inside the worker call to keep the GUI thread free.
- D4 — No new provenance literal. `ConfirmationDecision` gains `decided_by: Literal["clinician","config"]` (default `clinician` so v1 notes read), `config_digest` for `config`, optional `confirmation_count`. Config-decided lines keep `autofill`/`prefill` provenance and the existing `proposal_id`/`shown_text_digest`/`config_digest` evidence, minted at the emitter. A typed edit is a new provenance `clinician` (typed text, `decided_by="clinician"`, the replaced assertion's id recorded as `replaces`). Why: a fourth literal for config lines would force every provenance branch (`note.py` 332–348, ~395, ~1815, 1976–1979; `note_check.py` ×5; `session_store.py:817`; `ui/models.py`, `ui/note.py`) to learn a value that changes nothing about the text's origin; `clinician` is genuinely new (text typed, not quoted) and the branches must learn it once. Rejected: auto-clicking confirm in the UI (evidence would lie about who confirmed); `authored_rule`.
- D5 — Save-as-ratification (practitioner decision 2026-09-18): pre-filled lines carry a distinct mark and the Save button reads "Save — confirms the N pre-filled lines shown"; the threat model's boundary-2 control moves from per-assertion click to visible marking plus one Save per note, and Save stays refused while any MODEL-derived proposal is pending. Check 4's `clinician_asserted` review warning (`note_check.py:1325–1330`, today emitted for EVERY non-transcript assertion and gating Save at `ui/note.py:1074`) is NOT emitted for `decided_by="config"` assertions — Save is their acknowledgement; every other review warning keeps its gate (codex PR-MED-010). Auto-confirm after `LEARNED_RULE_AUTO_CONFIRM_AFTER = 3` unchanged confirmations; "unchanged" after auto-confirm means the pre-filled line was present and unedited at Save; a Remove of a pre-filled line resets the rule to proposing with count 0; an Edit of a learned rule's line REPLACES that rule's wording in place (same `rule_id`, same trigger, count 0, `auto_confirmed = False`, the previous wording kept in the sidecar's history) — exactly one active expansion per normalised trigger, which is what the loader enforces at `note_config.py:852–856` (codex PR-MED-007). Rejected: time-based thresholds; a cap on pre-filled lines (the practitioner authored every one); learning a corrected wording as a second rule under the same trigger.
- D6 — Prose provider input is ONLY confirmed assertion texts grouped by section plus the style profile (own_voice) or a fixed narrative instruction; never the transcript, never proposals. Output is parsed per section and passed through NEW Check 5 (fidelity, codex PR-HIGH-001 — token containment alone certifies nothing): (a) every input assertion's content tokens (normalised) appear in that section's prose; (b) the prose adds NO content token absent from the inputs other than tokens on a shipped connective allow-list (`config_defaults/prose_connectives.json`: articles, prepositions, conjunctions, auxiliaries, pronouns, "reports/notes/advised"-class verbs) — so "neck pain with paralysis" fails on `paralysis`; (c) no negation or polarity token (`no`, `not`, `never`, `denies`, `without`, `nil`, `n't`) may be added or removed relative to the inputs — so "no neck pain" fails; (d) no number, date, medication or laterality token may be added, removed or changed. A section that fails keeps the `clean` rendering with a `style_fallback` review warning. Check 5 is a GATE, not a certificate: prose that passes is still shown to the practitioner and ratified by the same Save that ratifies pre-filled lines (D5) — Save is unavailable while prose is being rendered and only a displayed rendering can be saved (D7) — and the `clean` rendering of the same assertions is stored beside it as the evidential base. Why: Check 1 rebuilds byte-for-byte from coordinates and cannot validate a rephrase; unrestricted rephrasing cannot be mechanically certified, so the practitioner's reading is the control and Check 5 bounds what reaches their eyes. Rejected: generating the whole note from the transcript (the original 3B shape); containment-only checking.
- D7 — Styles are a rendering stage AFTER finalisation in the Note tab (codex PR-MED-002: `build_note_generator` returns an unchecked draft, `ui/models.py:1109`; `finalise_note` runs at `ui/note.py:1013`, and display and Copy both use `format_note_body`, `ui/note.py:1014, 1129`). `verbatim` and `clean` are deterministic (`clean` = one terse line per assertion, no substitution); the prose styles run on a `TaskThread` after each finalisation, bound to the finalised note's digest, invalidated by any subsequent edit, and wrap `clean` as their fallback. ONE rendering path: `format_note_body(note)` reads `GeneratedNote.style_renderings` (per-section prose + input digest + Check 5 verdict) and falls back to `clean` per section, for display, `note.enc` persistence/reload and Copy alike — a stale rendering (digest mismatch) is never shown. Setting stored in `practitioner_settings.json`, default `clean`.
- D8 — Language-model offline contract: the runtime is installed ONLY as a prebuilt CPU wheel pinned by version AND sha256 (`pip --require-hashes` from a documented wheel source; a source build is refused — codex PR-MED-006: the PyPI default of `llama-cpp-python` BUILDS from source and its prebuilt CPU wheels live on a separate index; Python 3.14 wheel availability is unverified); the runtime itself is chosen by Task 4.0's preflight `[decision]` between `llama-cpp-python` (prebuilt CPU wheel) and `onnxruntime-genai` (PyPI wheel, sits on the already-shipped onnxruntime, ONNX model export instead of GGUF); the wheel fetch is recorded in `data-flow-map.md` as the second sanctioned fetch beside `setup-models.py`. The model file is pinned by SHA-256 in `setup-models.py` with a size and free-space precondition and `.candidate` resume; loaded from the local path only; `assert_offline_env` still runs (it is the app-wide invariant) but the ENFORCING control for this runtime is the no-sockets integration test extended to a prose generation. Why: neither runtime reads a kill-switch variable; claiming parity with the Whisper contract would be the `docs/lessons.md` structure-does-not-enforce failure.
- D9 — Sample notes are read into memory from the chosen files and never copied; the learning output is `style_profile.json` DPAPI-wrapped under its OWN root `style\` with its own `key.dpapi` and a distinct verified description (voice and style keys cannot open each other's store, nor can a session key); deleting the originals is a separate explicit confirmation naming the paths, default unticked. The style store carries its OWN `ConsentRecord` (version + timestamp + `learning_opt_in`), written at sample Save from the tab's consent box, so sample learning at first run needs no voice profile (codex PR-MED-008: today consent persists only inside `voice.enc`, `ui/practitioner.py:588–590`, and `learning_status` refuses without a profile, `ui/models.py:1058`); `consent_is_current` accepts either store's record, and a stale record on either side re-asks on the tab. The style store has its own visible "Delete learned style" action (key-first, independent of the voice profile, which `delete_profile` at `ui/practitioner.py:762` does not touch — codex PR-MED-009) and a post-save "Learned style" list with per-exemplar delete. Rejected: a second artefact under `profile\` (would overwrite or share the voice key); auto-delete; requiring enrolment before sample learning.
- D10 — Exemplars: max 30; a sentence is kept only if it passes THE refusal filter UNCHANGED (no name-shaped, numeric, date or medication token) — refused sentences are dropped, never edited; each kept exemplar is shown and individually removable before save and after (D9). Sample-derived SHORTHAND is auto-extracted from patient notes, so it does NOT get the typed-wording filter (codex PR-MED-012): a token is admitted only if it is in the shipped controlled vocabulary `config_defaults/clinical_abbreviations.json` (the common physio/osteo/chiro abbreviations — HVLA, Cx, Tx, Lx, ROM, NAD, Rx, Hx …); an unrecognised all-caps or abbreviation-shaped token is listed separately as "unrecognised — tick to keep" (default unticked) and only a ticked one is saved. The retention schedule and non-flow list gain a row stating that exemplars are practitioner-reviewed sentences from the practitioner's own past notes under the style key, deleted with that store.
- D11 — `refuse_typed_wording(text)` is a second, narrower filter for PRACTITIONER-TYPED text ONLY: refuses numbers, dates and medication tokens (sharing the token classifiers with `refuse_learning_candidate`), no name heuristic (practitioner decision 2026-09-18). Triggers are still derived from transcript words through `refuse_learning_candidate` with `first_in_segment`/`following` supplied for the utterance position, trigger ≤ 6 content tokens. Why: the transcript filter refuses "HVLA Cx" as a name; typed wording is the practitioner's own, shown on screen and named at Save.
- D12 — Consent v3 is REWRITTEN by data class, not appended (codex PR-MED-011: v2 promises "refuses phrases containing names, numbers, dates or medication names" and "Nothing else about any patient is stored beyond their session", `ui/models.py:1262–1264`, both of which this plan changes): the voice fingerprint; learned phrases and learned rules (transcript-derived triggers refused for names/numbers/dates/medications; typed wording refused for numbers/dates/medications only — the practitioner is responsible for names in their own typed shorthand); the learned style (what is derived from uploaded notes, that exemplar sentences are kept only when they pass the filter unchanged and are shown for review, stored encrypted, deletable); Save ratifying pre-filled lines. `CONSENT_TEXT_V2` is frozen as a literal historical text with its own literal "Version consent-v2." (today it interpolates the mutable `CONSENT_TEXT_VERSION`, `ui/models.py:1267`). The complete v3 text is pinned verbatim in a test beside its version.

## Schema / Data Changes
- `autofill_rules.json` (practitioner's user file): learned rules appended as ordinary `AutofillRule`s with `rule_id = "learned-<ulid>"`; a corrected wording replaces the rule's `expansion` in place (D5). `autofill_rules.learned.json` metadata sidecar (never read by the loader): `{schema_version: 1, entries: {rule_id: {learned_at, trigger_source: "typed_edit", confirmations: int, auto_confirmed: bool, history: [{replaced_at, previous_expansion}]}}}`.
- `style_profile.json` (DPAPI-wrapped under `style\` with its own `key.dpapi`): `{schema_version: 1, learned_at, consent: ConsentRecord, section_order: [section_key], heading_labels: {section_key: str}, shorthand: [str], measures: {mean_sentence_words, abbreviation_ratio, person, tense}, exemplars: [{section_key, text}], source_count: int}`. `ConsentRecord` is the existing voice-profile consent model reused (version, timestamp, `learning_opt_in`).
- `config_defaults/clinical_abbreviations.json` (shipped controlled vocabulary, D10) and `config_defaults/prose_connectives.json` (Check 5's allow-list, D6); both loaded with the same completeness guard as `section_cues.json`.
- `practitioner_settings.json`: `{schema_version: 1, note_style: "verbatim|clean|own_voice|narrative"}`.
- `note.enc` schema v2: `ConfirmationDecision.decided_by` (default `clinician`), `config_digest`, `confirmation_count`; provenance literal `clinician` with `typed_text` and `replaces`; `GeneratedNote.style` (default `verbatim`) and `style_renderings: {section_key: {prose, input_digest, verdict}}` (D7); readers accept v1 and v2.
- `TranscriptDocument`: unchanged.
- Consent: `CONSENT_TEXT_V3`, `CONSENT_TEXT_VERSION = "consent-v3"`.

## Config / Environment / Deployment Impact
- New runtime dependencies: `python-docx` (base, added in Phase 3 Task 3.3); the prose runtime chosen by Task 4.0 (`llama-cpp-python` prebuilt CPU wheel from its documented wheel index, or `onnxruntime-genai` from PyPI), installed ONLY as a pinned wheel with `--require-hashes` — never a source build (D8) — under `[ml]`; both libraries added to the mypy `ignore_missing_imports` override. The wheel fetch becomes the second sanctioned network step, documented beside `setup-models.py` in `data-flow-map.md` and `AGENTS.md` Local Run Steps.
- Python 3.14 compatibility of the chosen runtime is UNVERIFIED — Task 4.0's preflight on the practitioner's machine decides; if neither runtime ships a 3.14 CPU wheel the fallback recorded there is a 3.12 venv for the app (CI already runs 3.12).
- New pinned model entry in `scripts/setup-models.py` (~2.5 GB; practitioner-run from a normal terminal; free-space precondition; `.candidate` resume). The parent plan's installer decision covers this file. The retention schedule's models-cache size row is updated.
- The shipping-gate run config is unchanged; the gate runs under `clean` (Task H5 addendum).
- No env vars. Release risk: the default style flips to `clean` for the existing user; `verbatim` remains selectable.

## Critical Constraints
- C1 — No cloud, no network, no training (parent plan). Every model load is local-path + SHA-256 pin; the no-sockets test covers every ML runtime.
- C2 — The transcript remains raw evidence and display-only; the live view is the same widget under the same `NoTextInteraction` rule and is cleared on Discard.
- C3 — Nothing enters a saved note without a recorded decision: model-derived content keeps per-line confirm; config-decided lines carry `decided_by="config"` with digest evidence and are ratified by Save (D5); typed lines carry the clinician's decision. Copy stays behind `COPY_TO_CLINIKO_ENABLED`.
- C4 — The prose model never sees transcript text (D6); its output never bypasses Check 5, is never shown, persisted or copied from a stale rendering (D7), and is ratified by Save like every other non-transcript line.
- C5 — Three admission paths, one class of control: `refuse_learning_candidate` for transcript- or note-derived sentences (cue phrases, rule triggers, exemplars); `refuse_typed_wording` for practitioner-typed text (rule wording); the controlled vocabulary plus explicit tick-to-keep for auto-extracted shorthand (D10). All refuse; none edits.
- C6 — A learned or extracted artefact is written only on an explicit Save/Confirm and validated before the write; sample files are never copied; their deletion is a separate explicit confirmation (D9).
- C7 — Key custody: the live worker never holds session crypto (D1); no path destroys a session key while any worker holds that session's crypto; Discard drops the worker's plaintext buffers before the key is destroyed (D2).
- C8 — Every fallback names its reason on screen: live worker failed / could not keep up / model failed to load; language model absent; style profile empty; Check 5 failed.
- C9 — Nothing logs clinical text: live segments, typed wording, exemplars and prose never reach a log line.

## Validation / Verification
- Baseline (executed 2026-09-18 on `b3a65a2`): `desktop/` `ruff check .` clean, `mypy` clean over 34 files, `pytest` 2023 passed in 123 s; extension 36. Every phase closes at ruff clean, mypy clean, pytest green with the new tests added.
- Phase 0: a v1 `note.enc` fixture reads under v2; a `config` decision without a digest is unrepresentable; voice, style and session keys cannot open each other's store; a v2 consent record reads but is not current.
- Phase 1: `assemble_transcript` parity test — the batch path before and after extraction yields the same document for the windowed-batching fixtures, and live vs batch agree for empty/one-segment input, no profile, enrolled matches and textless clusters; VAD determinism pin (same frames → same segments) and the live document passes every invariant `read_transcript` enforces; forced segment close at 30 s of sustained speech (a 90 s continuous-speech fixture yields ≥ 3 segments and live updates); queued-PCM cap during a blocked model load → failed → batch; Discard during RECORDING stops and joins the worker, its buffers are gone and the view is cleared BEFORE `key.dpapi` is deleted (thread test); a tee exception never reaches `_fail()`; fall-behind → failed → batch fallback with the reason line; Finish stays under 100 ms with a blocked tail (GUI responsiveness) and the last flushed chunk is in the live tail drained on the TaskThread; `test_integration_no_sockets.py` extended to the live path.
- Phase 2: the Edit control produces a `clinician` assertion and every provenance branch handles it (a parametrised test over the branch list in Key Findings); `refuse_typed_wording` class test (accepts "HVLA Cx", refuses "paracetamol 500 mg", "3/4/26"); learned rule validated as `AutofillRule` and duplicate-checked BEFORE the write; a corrected wording replaces in place and reloads as one active rule per trigger (correction, reload, undo/cancel, write-failure cases); written only on Save (Cancel/Discard/Delete write nothing); auto-confirm at exactly three, Remove demotes; no `clinician_asserted` warning for `decided_by="config"` lines and an end-to-end case where a note holding only pre-filled lines is ratified by the counted Save while an unrelated review warning still gates; Save is refused with a pending model proposal.
- Phase 3: learner never writes to or copies from the source directory; an exemplar with any refused token is dropped unchanged; an unrecognised abbreviation is saved only when ticked; sample Save with NO voice profile records consent in the style store and `consent_is_current` reads it; "Delete learned style" is key-first and works without a voice profile; the delete-originals step touches only the listed paths and only after confirmation; style setting round-trips; first-run banner appears once; the 5 s microphone poll never decrypts the style store.
- Phase 4: the runtime installs only from the pinned hashed wheel (an install/import/smoke gate refuses a source build); pinned model loads from the local path only; Check 5 class test — missing fact, added content token ("with paralysis"), added negation ("no neck pain"), removed negation, added number/medication/laterality each FAIL; a faithful rephrase passes; failure falls back to `clean` for that section with the warning; a stale rendering (digest mismatch after an edit) is never displayed, persisted or copied; Save is disabled during a blocked render and a render that completes cannot persist unseen wording (blocked-render/Save test); display, reload and Copy produce identical text; the prompt builder is pinned never to accept `TranscriptDocument` and an instruction-shaped assertion is rendered, not obeyed; no-sockets test covers a prose generation; fixture pass rate recorded (acceptance ≥ 9/10).
- Manual (practitioner): live transcript filling during a real recording; Flow 2 end to end across three consultations; a sample-note learning run on real past notes with the review step; each style rendered for one real session; CPU seconds per prose section recorded (feeds the CUDA deferral trigger).

## Deferred / Out of Scope
- See Planning Extraction Summary (state-once): PLAN.md Phases 4–5, the validation-set gate, `gpt-oss-20b`, the CUDA wheel, D-S1; scrubbing, PDF input, no-utterance learning and render-time substitution excluded.

## Current State / Handoff Note
- Last completed step: cross-family codex `gpt-6-astra` plan peer-review CONVERGED — round 1 (2026-09-18: 13 findings, all applied) and round 2 (2026-09-19, confirmation: 11 of 13 confirmed, the 2 stale siblings closed by PR-LOW-017/018; 5 new — 2 MED, 3 LOW — all verified and applied: worker cleanup by attached-worker ownership in D2/Task 1.2, Save disabled during an in-flight rendering in D6/D7/Task 4.4, `python-docx` moved to Task 3.3, two record-only sibling fixes). Logs: `.cursor/loops/note-learning-plan-peer-r{1,2}.log` (the first round-2 attempt on 2026-09-18 died on the codex usage window after reading only the plan and was re-run unchanged after the reset). Previous: `/review-plan` hardening (2026-09-18).
- Current in-progress step: None
- Immediate next action: commit the plan file, then `/execute-loop` in architect mode from Phase 0 (the wizard reproduces the practitioner-profile Loop config: executor claude-p `claude-fable-5-1`, delegate `claude-opus-5` via `loop-delegate`, peer codex `gpt-6-astra` high, architect=on, cadence=every-phase)
- Open blockers / open questions: Task 4.0 `[decision]` (runtime + Python 3.14 wheel availability) is decided by the practitioner-run preflight (Task P.0) before Phase 4 builds
- Last plan sync: 2026-09-19

## Review History
- 2026-09-18 round 1: 0 CRIT / 1 HIGH / 11 MED / 1 LOW; skew=plan-peer-review (codex `gpt-6-astra` high, cross-family); action=all 13 verified and applied as plan amendments by the owning session
- 2026-09-19 round 2: 0 CRIT / 0 HIGH / 2 MED / 3 LOW (3 build-affecting, 2 record-only); skew=plan-peer-review (codex `gpt-6-astra` high, cross-family, confirmation); 11 of 13 round-1 amendments confirmed, the 2 stale siblings closed by PR-LOW-017/018; action=all 5 applied; plan ready for `/execute-loop`

## Review Findings Log

### Round 1 - 2026-09-18 - note-learning-and-styles plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed (13 applied as plan amendments by the owning session, 2026-09-18)
- Source: Codex plan peer-review
- Materiality: 13 build-affecting / 0 record-only / 0 invalid (owning session verified: 13 build-affecting / 0 record-only / 0 invalid)
- Plan reviewed at: `b3a65a2` — target plan is untracked; tracked code is unchanged.
- Files read: `.agents/skills/peer-review/SKILL.md`; full `.cursor/plans/plan-note-learning-and-styles.md`; `AGENTS.md`; `PLAN.md`; `docs/lessons.md`; parent plan’s exclusions; all requested symbols in `session.py`, `audio_capture.py`, `transcription.py`, `session_store.py`, `note.py`, `note_fill.py`, `note_check.py`, `note_config.py`, `ui/note.py`, `ui/models.py`, `ui/practitioner.py`, `practitioner_profile.py`, and `benchmark.py`; `desktop/pyproject.toml`; `scripts/setup-models.py`; requested sections of the threat model, data-flow map, retention schedule and design system. Additional reads: `speech.py`, `ui/session_screen.py`, `ui/main_window.py`, and socket-integration test safeguards. Official llama-cpp-python installation documentation checked.
- Finding verification: 20 candidates / 7 dropped / 1 downgraded
- Review method: Static, read-only review. No files or directories created or changed; no tests run.

#### Findings

##### Missing verification / rollback / migration

**PR-HIGH-001 — Check 5 admits unsupported clinical assertions and polarity changes**

- Plan section: D6; Tasks 4.2–4.3; Phase 4 verification.
- Materiality: build-affecting
- Why it matters: Input `neck pain` and output `neck pain with paralysis` satisfy the specified token-containment and number/date/medication checks. Output `no neck pain` also retains every input token while reversing meaning. These additions occur after the existing checks. A passing verdict would therefore give unsupported model text a route into the saved clinical note.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:162`: “every input assertion's content tokens (normalised) appear in that section's prose, and the prose contains no number, date or medication token absent from the inputs”.
- Evidence: `desktop/src/scribe_desktop/note_check.py:78`: “An assertion that does not parse to structure is NOT contradiction-checked;”; `:79`: “it is carried by clinician confirmation alone”. The plan places the new rendering stage after that check.
- Suggested change: Define an enforceable contract for new claims, polarity and relationships, and add adversarial cases for each. Token coverage must not certify semantic fidelity. Where unrestricted rephrasing cannot be mechanically verified, require ratification of the exact generated prose before persistence, with the clean rendering as the safe fallback.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: Check 5 redefined as a fidelity GATE (D6 rules a-d: no added content token outside a shipped connective allow-list, no added/removed negation, no changed number/date/medication/laterality) with the prose still ratified by Save and the clean rendering stored as evidential base; Task 4.2 renamed `fidelity_warnings` with the adversarial cases. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-MED-002 — The proposed style stage targets a factory that neither checks nor writes the final note**

- Plan section: D7; note schema v2; Task 4.4.
- Materiality: build-affecting
- Why it matters: `build_note_generator` returns an unchecked draft before proposal decisions and review edits. Finalisation happens later in the Note tab. The proposed schema also stores style and verdicts without defining where checked prose is retained. Implementing the named task alone cannot ensure that the displayed, saved and copied wording agrees.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:255`: “`ui/models.py` `build_note_generator` composes the style stage after check and before write; `GeneratedNote.style` / `style_checks` written”.
- Evidence: `desktop/src/scribe_desktop/ui/models.py:1109`: `return NoteGenerationResult(draft=draft, config=config, document=document)`. Actual finalisation is `desktop/src/scribe_desktop/ui/note.py:1013`: `self._note = finalise_note(self._working, self._build_resolutions(), document, config)`. Display at `:1014` uses `models.format_note_body(self._note)`; Copy at `:1129` uses `models.format_note_body(note)`.
- Suggested change: Specify a post-finalisation asynchronous style stage, its checked output payload and input binding, invalidation after edits, and one rendering path for display, persistence/reload and Copy. Verify that stale style results cannot replace a newer review and that saved wording equals reviewed wording.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D7 + Task 4.4 moved the style stage to the Note tab after `finalise_note` on a TaskThread, bound to the finalised digest, invalidated on edit; `format_note_body` is the one rendering path; `style_renderings` stored with input digest + verdict. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-003 — Finish would synchronously wait for inference on the GUI thread**

- Plan section: D2–D3; Tasks 1.1–1.2.
- Materiality: build-affecting
- Why it matters: Finish currently runs directly in the GUI slot. Adding tail inference and backlog draining inside `controller.finish()` blocks the GUI before its background task and progress state start. Constructing the live model on another thread does not prevent a synchronous join from freezing the interface.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:158`: “`finish()` calls `live_transcriber.finish()` strictly AFTER `worker.stop(flush=True)` returns and before `store.finish()`”.
- Evidence: `desktop/src/scribe_desktop/ui/session_screen.py:175`: `session = self._controller.finish()`. Only subsequently does `:188` call `self._begin_transcription()`, which creates `task = TaskThread(job, self)` at `:222`.
- Suggested change: Explicitly plan the asynchronous Finish/drain handoff and busy/progress controls. Preserve existing custody boundaries, for example by sealing capture before draining the live tail in the processing worker. Add a blocked-tail test proving GUI responsiveness and correct control gating.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D2 + Tasks 1.1-1.3: `finish()` only seals capture and marks the worker sealed; the tail drain runs inside the transcriber callable on the processing TaskThread; Finish-under-100-ms test added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-004 — The existing VAD and packer do not bound continuous live speech**

- Plan section: D1–D2; Task 1.1; Phase 1 verification.
- Materiality: build-affecting
- Why it matters: Continuous speech does not produce a completed VAD segment until silence or input exhaustion. The packer explicitly permits oversized segments. A live driver reusing these semantics can retain an arbitrarily long open segment and show no updates while its completed-window queue remains below the cutoff.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:230`: “VAD per frame with carried state, windows via `pack_transcription_windows`”. At `:158`: “Fall-behind cut-off: more than two windows queued → the worker stops itself”.
- Evidence: `desktop/src/scribe_desktop/speech.py:290`: `if silence_run >= min_silence_frames:` closes speech; `:295`: `if in_speech:` handles the input-ending remainder. `desktop/src/scribe_desktop/transcription.py:528`: “lands in exactly one window; a single segment longer than the budget”; `:529`: “becomes its own (oversized) window — the provider seeks through it”.
- Suggested change: Define a maximum open-segment and queued-PCM bound, including during model loading. Specify bounded splitting with word/overlap ownership, or visible degradation to batch before that bound is exceeded. Verify sustained speech exceeding 90 seconds and a blocked model load.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D2 + Task 1.1: forced segment close at 30 s (lowest-probability frame of the last 5 s), queued-PCM cap of three windows including model load, fall-behind cut-off; sustained-speech and blocked-load tests added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-005 — The named speaker helper cannot consume the proposed LiveResult**

- Plan section: Codebase Integration Notes; Task 1.3.
- Materiality: build-affecting
- Why it matters: `label_speakers` takes raw PCM and recomputes embeddings. D1 deliberately discards that PCM. The batch pipeline instead contains an inline embedding-based finalisation policy, including empty-segment handling and enrolled-cluster selection. Merely validating the resulting transcript structure does not establish attribution parity.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:232`: “the returned callable runs only the speaker pass (`label_speakers` / `attribute_speakers` over the kept embeddings) + `write_transcript`”.
- Evidence: `desktop/src/scribe_desktop/transcription.py:726`: `def label_speakers(`; `:727`: `segment_pcms: list[bytes],`. Its own documentation at `:740` says “to bound plaintext, so it cannot call this whole-list wrapper — both”. The actual batch branch at `:1242` is `if np is None or saw_empty_segment or len(embeddings) < 2:`.
- Suggested change: Task a shared final-speaker/document assembly helper consuming embeddings, similarities, text flags and empty-segment state. Use it from live and batch drivers while preserving the public batch signature. Verify parity for empty/one-segment input, no profile, enrolled matches and textless clusters.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: New Task 1.0 extracts the batch tail (`transcription.py:1238-1250`) into `assemble_transcript`, used by both drivers; parity test over the degenerate cases added; Integration Note corrected. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-006 — The CPU-wheel installation premise needs correction and a compatibility gate**

- Plan section: External / API Findings; D8; Task 4.1.
- Materiality: build-affecting
- Why it matters: A bare PyPI version pin does not establish the required Windows CPU-wheel installation. The documented default installation builds native code; prebuilt CPU wheels use a separate index. Python 3.14 compatibility remains unverified. This can block installation or silently introduce a compiler-based build outside the intended deployment contract.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:138`: “`llama-cpp-python` CPU wheels install from PyPI; a version pin (`==`) goes in `[ml]`.”
- Evidence: `desktop/pyproject.toml:9`: `# Plan targets 3.12+; dev machine runs 3.14 (recorded in plan Key Findings)`. The official installation instructions state “This will also build `llama.cpp` from source” and direct CPU-wheel installation to a separate wheel index. [Official package documentation](https://pypi.org/project/llama-cpp-python/)
- Suggested change: Preserve CPU-only deployment, but pin an actual compatible Windows wheel, its source and digest, and define an installation/import/smoke gate that refuses source-build fallback. Reconcile the sanctioned dependency-fetch documentation before Phase 4 depends on this runtime.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D8 rewritten: prebuilt CPU wheel pinned by version + sha256 with `--require-hashes`, source build refused by an install/import/smoke gate; new Task 4.0 `[decision]` (llama-cpp-python prebuilt wheel vs onnxruntime-genai) decided by a practitioner-run preflight incl. Python 3.14 availability (3.12 venv fallback recorded); wheel fetch documented as the second sanctioned fetch. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-007 — Editing learned wording conflicts with duplicate-trigger rejection**

- Plan section: D5; Task 2.2; learned-rule schema.
- Materiality: build-affecting
- Why it matters: Correcting a pre-filled rule normally retains its trigger. D5 requires a new rule while retaining and resetting the old one. The planned duplicate check will reject that new rule; bypassing the check produces config the existing loader rejects. The correction workflow therefore needs an explicit version/supersession contract.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:161`: “an Edit of it learns the new wording as a NEW rule and resets the old.” Task 2.2 at `:239` requires a “`known`-style duplicate check against the practitioner's rules BEFORE the write”.
- Evidence: `desktop/src/scribe_desktop/note_config.py:852`: `earlier = triggers.get(trigger_tokens)`; `:855`: `f"rules {earlier} and {rule.rule_id} share the same "`; `:856`: `f"normalised trigger phrase"`. Existing append semantics at `:1367`–`:1369` skip a known phrase as `"duplicate"`.
- Suggested change: Define rule versioning/supersession so correction creates the required new learning record while exactly one expansion remains active per normalized trigger. Retain the old record and reset its status without leaving competing active rules. Verify correction, reload, undo/cancel and write-failure behavior.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D5 + Task 2.2: a corrected wording replaces the rule's expansion IN PLACE (same rule_id, count reset, history in the sidecar) — one active rule per trigger; `replace_learned_rule_wording` added; correction/reload/undo/write-failure cases in Validation. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Coverage

**PR-MED-008 — First-run sample learning has no usable consent-record path**

- Plan section: Agreed Scope; Task 0.1; Task 3.4; style-profile schema.
- Materiality: build-affecting
- Why it matters: Sample learning is offered before voice enrolment, but existing consent persistence requires a readable voice profile. Keeping that path unchanged leaves either an undocumented enrolment prerequisite or a sample-profile Save without the promised versioned consent. The proposed style schema contains no consent record.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:32`: “optional at first run (banner line, never blocking)”. Task 0.1 at `:223`: “the tab's re-consent path unchanged”.
- Evidence: `desktop/src/scribe_desktop/ui/practitioner.py:588`: `profile = self._profile`; `:589`: `if self.is_busy or profile is None or not self.consent_checkbox.isChecked():`; `:590`: `return`. `desktop/src/scribe_desktop/ui/models.py:1058`–`:1059` similarly disables existing learning when the voice profile is absent.
- Suggested change: Define where sample-learning consent is recorded and checked independently of voice enrolment, or explicitly specify the prerequisite and first-run behavior. Cover absent, stale and deleted voice profiles, and recheck consent at sample Save.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D9 + Tasks 0.1/0.3/3.4: the style store carries its own `ConsentRecord` written at sample Save from the tab's consent box; `consent_is_current` reads either store; sample learning needs no voice profile. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-009 — Retained style data has no tasked deletion path**

- Plan section: Accepted Assumptions; D9–D10; Tasks 0.3 and 3.4.
- Materiality: build-affecting
- Why it matters: The plan relies on review and deletion to bound retained patient-derived exemplars, but tasks only specify removal before initial Save and deletion of source files. The existing Delete action deletes the voice store, not the newly separate style key and payload.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:166`: “exemplars are practitioner-reviewed sentences from the practitioner's own past notes under the style key, deleted with the profile.” At `:102`: “bounded by review and delete”.
- Evidence: `desktop/src/scribe_desktop/ui/practitioner.py:762`: `delete_profile(root=self._profile_root)`. `desktop/src/scribe_desktop/practitioner_profile.py:241`: `return base, base / KEY_FILENAME, base / PROFILE_BLOB_FILENAME`; `:84`: `PROFILE_BLOB_FILENAME: Final = "voice.enc"`.
- Suggested change: Add a visible retained-style deletion action, key-first destruction, failure/retry handling and in-memory invalidation. Specify post-save exemplar removal and the relationship between voice and style deletion. Verify deletion remains available without a usable voice profile.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D9 + new Task 3.6: 'Learned style' group with per-exemplar delete and a key-first 'Delete learned style' action (`delete_style_profile`, independent of the voice profile); Validation case added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-010 — Existing clinician-asserted warnings prevent Save from being the single ratification action**

- Plan section: D5; Tasks 0.2 and 2.4.
- Materiality: build-affecting
- Why it matters: Every autofill/prefill assertion currently produces an unsuppressible `clinician_asserted` review warning. Save refuses all unacknowledged review warnings. Adding config decisions, marks and a counted Save label therefore still requires a separate acknowledgement even when the only review issue is the practitioner’s own pre-filled wording.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:161`: “the threat model's boundary-2 control moves from per-assertion click to visible marking plus one Save per note”.
- Evidence: `desktop/src/scribe_desktop/note_check.py:1325`: `if assertion.provenance == "transcript":`; all other assertions reach `:1329`: `note_warning_code="clinician_asserted",` and `:1330`: `severity="review",`. `desktop/src/scribe_desktop/ui/note.py:1074`: `if state.blocking_errors or state.unacknowledged_reviews:`.
- Suggested change: Explicitly define how Save ratifies the config-decided warning class without a preceding acknowledgement. Preserve unrelated review-warning gates. Add an end-to-end case where a note containing only eligible pre-filled lines can be ratified with the counted Save action.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D5 + Task 2.4: no `clinician_asserted` warning for `decided_by="config"` assertions (Save is their acknowledgement); other review warnings keep their gate; end-to-end pre-filled-only case added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Unstated assumptions

**PR-MED-011 — Consent v3 cannot retain v2’s promises unchanged**

- Plan section: D12; Task 0.1.
- Materiality: build-affecting
- Why it matters: V2 promises name refusal and no other patient information retained beyond the session. Typed wording now deliberately omits the name heuristic, and sample-derived sentences persist under a practitioner key. Appending three sentences leaves contradictory consent claims. V2’s historical version label also currently interpolates the mutable current-version constant.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:223`: “`CONSENT_TEXT_V3` (v2 + the three D12 sentences), flip `CONSENT_TEXT_VERSION`, keep v2 as history”.
- Evidence: `desktop/src/scribe_desktop/ui/models.py:1262`: `"patient, so it refuses phrases containing names, numbers, dates or medication names, "`; `:1264`: `"Nothing else about any patient is stored beyond their session, and nothing leaves "`; `:1267`: `f"Version {CONSENT_TEXT_VERSION}."`.
- Suggested change: Rewrite superseded v3 promises by data class, explicitly describing the narrower typed-wording filter and retained sample derivatives. Preserve v2 as a literal historical text with its original version label. Pin the complete new consent text in verification.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D12 + Task 0.1: consent v3 rewritten by data class (voice, learned phrases/rules with the two filters stated honestly, learned style, Save ratification); v2 frozen with a literal version label; full v3 text pinned in a test. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-012 — Sample-derived shorthand bypasses the sample name-refusal control**

- Plan section: D10–D11; Task 3.3.
- Materiality: build-affecting
- Why it matters: The narrower filter was justified for wording deliberately typed by the practitioner. Task 3.3 also applies it to automatically extracted tokens from patient notes. An uppercase surname or initials rejected from an exemplar can therefore survive as “shorthand.” Dictionary exclusion does not establish that a token is clinical vocabulary.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:247`: “shorthand (all-caps or abbreviation-shaped tokens that pass `refuse_typed_wording` and are not dictionary words)”. D11 at `:167` defines the narrower filter for “PRACTITIONER-TYPED text”.
- Evidence: `desktop/src/scribe_desktop/note_config.py:1108`: “words in original case and original order — checked before any”; `:1109`: “normalisation, so a capitalised name is still capitalised here;”. The enforcing name branch at `:1135` is `if is_name_like_token(raw, first_in_segment=at_real_start):`, followed by `return "name"`.
- Suggested change: Give automatically extracted shorthand a source-appropriate admission rule, such as a controlled clinical-abbreviation vocabulary with explicit handling of unknown tokens. Audit all retained sample-derived free-text fields. Preserve both fixed decisions: the narrow filter for genuinely typed wording and unchanged refusal for exemplars.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: D10 + Tasks 0.3/3.3/3.4: sample-derived shorthand admitted only from the shipped `clinical_abbreviations.json` vocabulary; unrecognised tokens listed tick-to-keep (default unticked); the typed-wording filter stays typed-only. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Simpler / safer alternatives

**PR-LOW-013 — Style-profile reporting is assigned to the periodic file-stat path**

- Plan section: Task 3.5; composition-layer integration.
- Materiality: build-affecting
- Why it matters: Learned date and exemplar counts live inside the encrypted style payload. Adding them directly to `model_file_report_lines` invites repeated profile decryption on the five-second microphone poll, recreating the recently removed polling behavior. The existing separate voice-profile reporting path already supplies the simpler pattern.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:249`: “`model_file_report_lines` gains the style-profile line (learned date, source count, exemplar count).”
- Evidence: `desktop/src/scribe_desktop/ui/models.py:1122`: “model — so the screen may recompute them on its 5 s poll (round 51”; `:1123`: “MED-001: the poll must never read the profile; that line is”; `:1124`: “``voice_profile_report_line``'s, taken separately).”
- Suggested change: Use a separate cached style-profile report refreshed on relevant profile events. Keep periodic file reporting stat-only and verify that steady timer ticks do not decrypt the style payload.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-18
- /fix decision: Applied
- /fix notes: Task 3.5: a separate cached `style_profile_report_line` refreshed on learn/delete events; `model_file_report_lines` stays stat-only; poll-never-decrypts test added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-18
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

PEER-PLAN-ROUND-1 RESULT: 13 findings (CRIT 0 / HIGH 1 / MED 11 / LOW 1; build-affecting 13 / record-only 0 / invalid 0).


### Round 2 - 2026-09-19 - note-learning-and-styles plan, post-round-1-amendment independent cross-family codex plan peer-review (round 2, confirmation)

- Round status: Closed (5 applied as plan amendments by the owning session, 2026-09-19; the two NOT CONFIRMED round-1 items, PR-MED-006 and PR-MED-012, are completed by PR-LOW-017 and PR-LOW-018)
- Source: Codex plan peer-review
- Materiality: 3 build-affecting / 2 record-only / 0 invalid (owning session verified: 3 build-affecting / 2 record-only / 0 invalid)
- Plan reviewed at: `b3a65a2` — target plan is untracked; tracked code is unchanged.
- Files read: Full `.cursor/plans/plan-note-learning-and-styles.md`; `.agents/skills/peer-review/SKILL.md`; `docs/lessons.md`; parent plan’s exclusions; requested symbols and surrounding code in `desktop/src/scribe_desktop/session.py`, `ui/session_screen.py`, `transcription.py`, `speech.py`, `note_check.py`, `note_config.py`, `ui/note.py`, `ui/models.py`, `ui/practitioner.py`, `practitioner_profile.py`; full `desktop/pyproject.toml`. Project context supplied through `AGENTS.md`.
- Finding verification: 8 candidates / 3 dropped / 0 downgraded
- Dropped candidates: general semantic-certification objection already addressed by D6; presumed impossibility of hashed runtime installation already addressed by preflight; unrestricted heading retention insufficiently established against canonical heading matching.
- Review method: Static, read-only review across all five lenses. No files or directories created or changed; no tests run.

#### Round-1 amendment confirmations

- **PR-HIGH-001 — CONFIRMED:** D6, Task 4.2 and Phase 4 validation now bound additions, omissions and polarity changes, explicitly state “Check 5 is a GATE, not a certificate” (`.cursor/plans/plan-note-learning-and-styles.md:163`), retain clean evidence and require Save ratification. This respects `desktop/src/scribe_desktop/note_check.py:78`: “An assertion that does not parse to structure is NOT contradiction-checked;”. The asynchronous ratification timing issue is separately reported below.
- **PR-MED-002 — CONFIRMED:** D7, schema v2 and Task 4.4 place rendering after finalisation, bind results to the input digest and unify display/persistence/Copy. Actual factory output remains `return NoteGenerationResult(draft=draft, config=config, document=document)` (`desktop/src/scribe_desktop/ui/models.py:1109`); finalisation and display are at `desktop/src/scribe_desktop/ui/note.py:1013–1014`, with Copy using `clipboard.setText(models.format_note_body(note))` at `:1129`.
- **PR-MED-003 — CONFIRMED:** Flow 1, D2 and Tasks 1.1–1.3 move tail draining to the processing worker; Task 1.2 explicitly says “no drain here — D2” (`.cursor/plans/plan-note-learning-and-styles.md:442`). This addresses the direct GUI call `session = self._controller.finish()` (`desktop/src/scribe_desktop/ui/session_screen.py:175`) preceding `task = TaskThread(job, self)` at `:222`.
- **PR-MED-004 — CONFIRMED:** D2, Task 1.1 and Phase 1 validation specify forced segment closure, bounded queued PCM during model loading and sustained-speech tests. These address `if silence_run >= min_silence_frames:` (`desktop/src/scribe_desktop/speech.py:290`) and the packer’s “becomes its own (oversized) window” policy (`desktop/src/scribe_desktop/transcription.py:529`).
- **PR-MED-005 — CONFIRMED:** Integration Notes, Task 1.0 and Task 1.3 require shared `assemble_transcript` extraction and parity checks. This matches the raw-PCM parameter `segment_pcms: list[bytes],` (`desktop/src/scribe_desktop/transcription.py:727`) and the actual batch-tail condition `if np is None or saw_empty_segment or len(embeddings) < 2:` at `:1242`.
- **PR-MED-006 — NOT CONFIRMED:** D8, deployment impact and Tasks 4.0–4.1 contain the corrected wheel-source, hashing and compatibility gates, but External / API Findings still asserts the superseded PyPI/version-only premise at `.cursor/plans/plan-note-learning-and-styles.md:139`. The remaining inconsistency is record-only; see PR-LOW-017.
- **PR-MED-007 — CONFIRMED:** D5, the sidecar schema, Task 2.2 and validation specify in-place correction, retained history and one active rule per trigger. This respects `earlier = triggers.get(trigger_tokens)` (`desktop/src/scribe_desktop/note_config.py:852`) and duplicate rejection at `:853–856`.
- **PR-MED-008 — CONFIRMED:** D9, the style schema, Tasks 0.1/0.3/3.4 and validation provide a style-store consent record without requiring voice enrolment. This addresses the existing guard `if self.is_busy or profile is None or not self.consent_checkbox.isChecked():` (`desktop/src/scribe_desktop/ui/practitioner.py:589`) and `if profile is None:` (`desktop/src/scribe_desktop/ui/models.py:1058`).
- **PR-MED-009 — CONFIRMED:** D9 and Tasks 0.3/3.6 provide independent key-first style deletion, retained-item deletion, memory invalidation and failure reporting. The existing action calls only `delete_profile(root=self._profile_root)` (`desktop/src/scribe_desktop/ui/practitioner.py:762`); existing key reuse is explicit at `desktop/src/scribe_desktop/practitioner_profile.py:279`.
- **PR-MED-010 — CONFIRMED:** D5, Task 2.4 and Phase 2 validation explicitly exempt config-decided assertions from `clinician_asserted` while preserving other warning gates. This addresses `note_warning_code="clinician_asserted",` (`desktop/src/scribe_desktop/note_check.py:1329`) and `if state.blocking_errors or state.unacknowledged_reviews:` (`desktop/src/scribe_desktop/ui/note.py:1074`).
- **PR-MED-011 — CONFIRMED:** D12 and Task 0.1 rewrite consent by data class, freeze historical v2 and pin v3 verbatim. This addresses the existing promise `"Nothing else about any patient is stored beyond their session, and nothing leaves "` (`desktop/src/scribe_desktop/ui/models.py:1264`) and mutable historical label `f"Version {CONSENT_TEXT_VERSION}."` at `:1267`.
- **PR-MED-012 — NOT CONFIRMED:** D10–D11 and Tasks 3.3–3.4 correctly distinguish vocabulary-based sample shorthand from typed wording, but Integration Notes still assign `refuse_typed_wording` to “Phase 3 shorthand/exemplar pre-check” (`.cursor/plans/plan-note-learning-and-styles.md:135`). The remaining inconsistency is record-only; see PR-LOW-018.
- **PR-LOW-013 — CONFIRMED:** Task 3.5 requires a separate cached report refreshed on learn/delete events; Phase 3 validation prohibits timer-driven style decryption. This follows `desktop/src/scribe_desktop/ui/models.py:1123`: “MED-001: the poll must never read the profile; that line is”.

#### New findings

##### Missing verification / rollback / migration

**PR-MED-014 — Live-worker cleanup omits admitted non-recording exits**

- Plan section: D2; Task 1.2; C7; Phase 1 validation.
- Materiality: build-affecting
- Why it matters: The explicit stop/join coverage is limited to RECORDING/PAUSED. A footer-write failure instead enters FAILED directly, without `_on_capture_failure`; the UI then permits discard without ever starting the processing callable. The planned worker can therefore retain plaintext after key deletion. There is also a PROCESSING handoff interval before `transcribing` becomes true. The live worker holds no crypto, so this finding concerns retained plaintext and incomplete shutdown, not destruction of a key used by that worker.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:442`: “`discard` stops-and-joins inside the first locked section before key deletion (RECORDING/PAUSED) and relies on the existing `transcribing` guard from PROCESSING on”.
- Evidence: `desktop/src/scribe_desktop/session.py:480–482`:
  ```python
              except StoreWriteError:
                  self._fail_locked(live)
                  return live.session
  ```
  `desktop/src/scribe_desktop/session.py:1046`: `self._transition_locked(live, SessionState.FAILED)`. The flag defaults to `transcribing: bool = False` at `:258` and becomes true only at `:534`. Discard checks `if live.transcribing:` at `:690`, then reaches `discard_session(live.directory, live.crypto)  # key-first, destroys crypto` at `:730`. `desktop/src/scribe_desktop/ui/session_screen.py:180` checks `if session.state != SessionState.PROCESSING:` and returns at `:187`.
- Suggested change: Define cleanup by attached-worker ownership, covering FAILED and unclaimed PROCESSING workers as well as RECORDING/PAUSED. Preserve the existing reservation logic and require confirmed shutdown/buffer clearance before deletion; a shutdown timeout must not count as completion. Add footer-failure→Discard and Finish-before-transcriber-entry tests, including suppression of late live-view updates. This need not reopen arbitrary-thread custody hardening.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-19
- /fix decision: Applied
- /fix notes: D2 + Task 1.2: cleanup is by attached-worker ownership — `_fail_locked`, `_on_capture_failure`, retire-on-start and `discard()` in any state where the transcriber callable has not claimed the worker (RECORDING/PAUSED/FAILED/pre-claim PROCESSING) stop, join and confirm buffers cleared before `discard_session`; a join timeout is a reported failure; late live-view updates dropped; footer-failure→Discard and Finish-before-claim→Discard tests added. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-MED-015 — Waiting Save can commit prose produced after the ratifying click**

- Plan section: D6–D7; Task 4.4; Phase 4 validation.
- Materiality: build-affecting
- Why it matters: The permitted wait-and-continue interpretation lets Save commit newly generated prose that was unavailable when the practitioner clicked. Digest freshness establishes which assertions were rendered, not that the practitioner reviewed the resulting wording. This leaves the human control introduced by PR-HIGH-001 incomplete.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:471`: “Save waits for or cancels an in-flight rendering”.
- Evidence: `.cursor/plans/plan-note-learning-and-styles.md:163`: “prose that passes is still shown to the practitioner and ratified by the same Save that ratifies pre-filled lines”. Current Save snapshots `note = self._note` (`desktop/src/scribe_desktop/ui/note.py:1069`) and persists that snapshot through `on_save(note)` at `:1081`; it has no asynchronous review-after-completion contract.
- Suggested change: Disable/refuse Save while rendering, or cancel rendering and save only the already-displayed clean version. Newly completed prose must be displayed before a fresh Save click can ratify it. Add a blocked-render/Save test proving that completion cannot automatically persist unseen wording. Preserve the single-Save policy.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-19
- /fix decision: Applied
- /fix notes: D6/D7 + Task 4.4 + Validation: Save is DISABLED while a rendering is in flight and re-enabled only after the completed prose is displayed; a blocked-render/Save test proves completion cannot persist unseen wording. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Practicality / feasibility / sequencing

**PR-LOW-016 — Phase 3 needs a dependency assigned to Phase 4**

- Plan section: Tasks 3.3 and 4.1; phase-close validation.
- Materiality: build-affecting
- Why it matters: Phase 3 must deliver DOCX ingestion and pass its checks before Phase 4’s separately gated runtime work. The only dependency-installation task currently arrives afterward.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:458`: “`.docx` via `python-docx`”; Task 4.1 at `:468`: “`python-docx` in base deps, mypy overrides”.
- Evidence: The complete existing base dependency list, `desktop/pyproject.toml:11–20`, is:
  ```toml
  dependencies = [
      "PySide6>=6.8",
      "pydantic>=2.7",
      "cryptography>=43",
      "keyring>=25",
      "psutil>=6",
      # Phase 2: DPAPI key custody (win32crypt.CryptProtectData) — user-approved
      # dependency in the hardened Phase 2 plan.
      'pywin32>=306; sys_platform == "win32"',
  ]
  ```
  `.cursor/plans/plan-note-learning-and-styles.md:199`: “Every phase closes at ruff clean, mypy clean, pytest green with the new tests added.”
- Suggested change: Move the `python-docx` dependency and necessary typing configuration into Task 3.3 or an earlier foundational task. Leave prose-runtime installation in Phase 4.
- Materiality (owning session): build-affecting (peer: build-affecting) — verified against the cited code 2026-09-19
- /fix decision: Applied
- /fix notes: Task 3.3 now adds `python-docx` to base dependencies with its mypy override (removed from Task 4.1); Deployment Impact names the phase. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

##### Unstated assumptions

**PR-LOW-017 — External findings retain the superseded runtime-installation premise**

- Plan section: External / API Findings; PR-MED-006 amendment record.
- Materiality: record-only
- Why it matters: The concrete tasks already prescribe the corrected installation contract, but the supporting findings still assert its predecessor. This prevents full sibling-consistency confirmation without changing the required build.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:139`: “`llama-cpp-python` CPU wheels install from PyPI; a version pin (`==`) goes in `[ml]`.”
- Evidence: Amended D8 at `.cursor/plans/plan-note-learning-and-styles.md:165`: “the runtime is installed ONLY as a prebuilt CPU wheel pinned by version AND sha256”; the same line states “its prebuilt CPU wheels live on a separate index; Python 3.14 wheel availability is unverified”.
- Suggested change: Replace the stale external finding with a pointer to D8 and Task 4.0’s source/hash/compatibility preflight. Preserve the historical quotation inside Round 1.
- Materiality (owning session): record-only (peer: record-only) — verified against the cited code 2026-09-19
- /fix decision: Applied
- /fix notes: External / API Findings replaced with a pointer to D8 and Task 4.0 (source-build default, separate wheel index, unverified 3.14 availability, both runtimes). Edit landed and sibling sections reconciled.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

**PR-LOW-018 — Integration notes retain the superseded sample-filter assignment**

- Plan section: Codebase Integration Notes; C5; PR-MED-012 amendment record.
- Materiality: record-only
- Why it matters: D10–D11 and the implementation tasks already specify the corrected admission paths. The integration summary still assigns the typed-only helper to sample derivatives, leaving contradictory guidance.
- Current plan text: `.cursor/plans/plan-note-learning-and-styles.md:135`: “`refuse_typed_wording` (Phase 2 wording, Phase 3 shorthand/exemplar pre-check)”.
- Evidence: D10 at `.cursor/plans/plan-note-learning-and-styles.md:167`: “Sample-derived SHORTHAND is auto-extracted from patient notes, so it does NOT get the typed-wording filter”. D11 at `:168` specifies “PRACTITIONER-TYPED text ONLY”. Existing name refusal is `if is_name_like_token(raw, first_in_segment=at_real_start):` followed by `return "name"` (`desktop/src/scribe_desktop/note_config.py:1135–1136`).
- Suggested change: Reconcile the integration summary and clarify C5’s shorthand terminology: transcript triggers/exemplars use the full refusal filter; practitioner-typed wording uses the narrower filter; extracted shorthand uses the controlled vocabulary and explicit unknown-token retention. Preserve Round 1’s historical quotations.
- Materiality (owning session): record-only (peer: record-only) — verified against the cited code 2026-09-19
- /fix decision: Applied
- /fix notes: Codebase Integration Notes and C5 rewritten: three admission paths — full refusal filter for transcript/note-derived sentences, typed-wording filter for typed rule wording only, controlled vocabulary + tick-to-keep for extracted shorthand. Edit landed and sibling sections reconciled.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (owning planning session, Fable 5.1)

PEER-PLAN-ROUND-2 RESULT: 5 new findings (CRIT 0 / HIGH 0 / MED 2 / LOW 3; build-affecting 3 / record-only 2 / invalid 0); round-1 confirmations 11 of 13.

## Tasks

### Phase 0 — Contracts, consent and schema (foundational; own review boundary)
- [ ] 🟥 Task 0.1: Consent v3 — `ui/models.py`: `CONSENT_TEXT_V3` rewritten by data class per D12; `CONSENT_TEXT_V2` frozen with a literal "Version consent-v2."; flip `CONSENT_TEXT_VERSION`; `consent_is_current` accepts a record from the voice store OR the style store (D9). Done when a v2 record reads but is not current, the tab asks again, and the full v3 text is pinned verbatim in a test. Verification: consent tests extended.
- [ ] 🟥 Task 0.2: Note model v2 — `note.py`: `ConfirmationDecision.decided_by` / `config_digest` / `confirmation_count` per D4; provenance literal `clinician` (`typed_text`, `replaces`); `GeneratedNote.schema_version = 2` with v1 readable; `style` and `style_renderings` fields with defaults (D7). Update every provenance branch listed in Key Findings (`note.py` 332–348, ~395, ~1815, 1976–1979; `note_check.py` 436, 1078, 1101, 1364, 1415; `session_store.py:817`; `ui/models.py` 408, 942; `ui/note.py` 569, 747) so `clinician` is handled explicitly and `decided_by="config"` lines pass `finalise_note`. Done when the parametrised branch test and the v1-fixture read pass.   [executor: premium-only]
- [ ] 🟥 Task 0.3: Settings and style-profile stores — `note_config.py`: `PractitionerSettings` (`note_style`, default `clean`) + `PRACTITIONER_SETTINGS_FILENAME`; `StyleProfile` model per Schema / Data Changes including its `ConsentRecord`; `practitioner_profile.py`: a `style\` root with its own `key.dpapi` and verified description, `save_style_profile` / `load_style_profile` / `delete_style_profile` (key-first, independent of `delete_profile`) (D9). Also the two shipped vocabularies `config_defaults/clinical_abbreviations.json` and `config_defaults/prose_connectives.json` with the `section_cues.json` completeness guard. Done when round-trip works and the three-key isolation test passes.
- [ ] 🟥 Task 0.4: Filters — `note_config.py`: `refuse_typed_wording(text) -> RefusalClass | None` sharing the number/date/medication classifiers with `refuse_learning_candidate` (D11); `LEARNED_RULE_AUTO_CONFIRM_AFTER = 3`. Done when the class test in Validation passes.
- [ ] 🟥 Task 0.5: Security-doc stubs — add the new surfaces (live worker, typed edits, learned rules, Save-as-ratification, style profile + exemplars, sample-note ingest, language model + Check 5) with C1–C9 to `docs/security/threat-model.md` (amending boundary 2 at 200–206 per D5), flows 14–16 and the amended non-flow at 275–279 in `data-flow-map.md`, rows in `retention-schedule.md` (in-memory live buffers; exemplars; models cache size). Finalised at Phase H.

### Phase 1 — Live transcription
- [ ] 🟥 Task 1.0: `transcription.py` `assemble_transcript(header, segments, marked_segments, embeddings, similarities, saw_empty_segment, attributing, np, ...) -> TranscriptDocument` — the batch tail at `:1238–1250` extracted verbatim into a shared helper; `transcribe_session` calls it; its public signature and the windowed-batching tests unchanged. Done when the parity test in Validation passes. (codex PR-MED-005)   [executor: premium-only]
- [ ] 🟥 Task 1.1: `transcription.py` `LiveTranscriber` — a queue-fed worker thread: `feed(pcm_chunk)`, `pause()`/`resume()`, `seal()` (no more input), `drain() -> LiveResult` (tail + all segments, marked words, embeddings, cosines, `saw_empty_segment`), `stop()` (abandon, drop buffers), `failed_reason`; VAD per frame with carried state and the 30 s forced close (D2), windows via `pack_transcription_windows`, provider + VAD constructed on the worker thread (D3), the queued-PCM cap and fall-behind cut-off (D2), PCM dropped per window; never touches crypto or files (D1). Verification: VAD determinism pin, sustained-speech, blocked-load and fall-behind tests.   [executor: premium-only]
- [ ] 🟥 Task 1.2: `session.py` — `_LiveSession.live_transcriber`; `start` wraps the `append_chunk` sink with a non-raising tee feeding the worker (factory injected at controller construction, `ui/main_window.py:84`; None keeps today's behaviour); `pause`/`resume` gate feeding; `finish` seals capture exactly as today then calls `live_transcriber.seal()` and leaves the worker on the live session (no drain here — D2); `discard` stops-and-joins any still-attached (unclaimed) worker inside the first locked section before key deletion — RECORDING, PAUSED, FAILED and pre-claim PROCESSING alike — and relies on the existing `transcribing` guard once the callable has claimed it; `_fail_locked`, `_on_capture_failure` and retire-on-`start` stop it (D2 ownership rule). Verification: the Discard thread test, footer-failure→Discard, Finish-before-transcriber-entry→Discard, late-update suppression, and the Finish-under-100-ms test.   [executor: premium-only]
- [ ] 🟥 Task 1.3: `ui/models.py` `build_transcriber` — when a sealed worker is attached, the returned callable (running on the processing `TaskThread`, `ui/session_screen.py:222`) drains it, calls `assemble_transcript` over the `LiveResult`, then `write_transcript`; on a drain failure or `failed_reason` it releases the worker's provider and runs today's batch closure. Status lines for the three C8 live reasons. `SessionController.transcribe`'s signature is untouched.
- [ ] 🟥 Task 1.4: `ui/transcript.py` — live segments appended as posted (queued signal), header "Live — updates while recording", same `NoTextInteraction`; cleared on Discard; replaced wholesale by the final document at QUEUED. C2.
- [ ] 🟥 Task 1.5: Recovery and no-sockets — a crash mid-recording with a live worker recovers through the unchanged batch path; `test_integration_no_sockets.py` covers the live path.
- [ ] 🟥 Task 1.6: Benchmark line — `benchmark.py` panel: "live window latency" (window seconds ÷ transcribe seconds), verifying the accepted assumption on the practitioner's machine.

### Phase 2 — Typed edits, expansion learning and Save-as-ratification
- [ ] 🟥 Task 2.1: Edit control — `ui/note.py`: an Edit action on a note line or proposal opens an inline single-line editor; commit produces a `clinician` assertion replacing the line (`replaces` recorded), rendered with its own provenance label; undo restores. Follows `add_line`/`move_line`'s resolution bookkeeping. `docs/design-system.md` edit cue added. Done when the branch test from Task 0.2 covers a typed line end to end through `finalise_note` and `write_note`.
- [ ] 🟥 Task 2.2: Learned-rule writer — `note_config.py`: `append_learned_rules(pairs, *, config_root, learned_at)` mirroring `append_user_cues` (validate each as `AutofillRule`, `known`-style duplicate check against the practitioner's rules BEFORE the write, whole-file replacement of `autofill_rules.json`, metadata sidecar `autofill_rules.learned.json`), `replace_learned_rule_wording(rule_id, wording)` (in-place expansion replacement, count reset, history entry — D5), `load_learned_rules`, `delete_learned_rule`, `record_rule_outcome(rule_id, outcome)` (confirmed / removed → count and `auto_confirmed` per D5). Done when a bad candidate can never reach disk, exactly one active rule per trigger survives a correction, and loading never breaks.
- [ ] 🟥 Task 2.3: Candidate detection on Save — `ui/note.py` `save`: for each `clinician` assertion whose replaced line's source segment passes `spoken_by_confirmed_clinician`, derive the trigger (≤ 6 content tokens of the utterance through `refuse_learning_candidate` with position context) and the wording (typed text through `refuse_typed_wording`); queue; write via `append_learned_rules` only on Save; the Save notice names each rule learned; Cancel/Discard/Delete extend the Phase 5.6 unlearned-queue notice. C5, C6.
- [ ] 🟥 Task 2.4: Pre-fill and ratification — `note_fill.py`: emit `decided_by="config"` assertions (digest, count) for practitioner-authored entries and auto-confirmed learned rules, proposals otherwise; `note_check.py:1325–1330`: no `clinician_asserted` warning for `decided_by="config"` assertions (every other warning unchanged); `ui/note.py`: the pre-filled mark, Remove (→ `record_rule_outcome(removed)`), Edit of a learned line (→ `replace_learned_rule_wording`), the Save label "Save — confirms the N pre-filled lines shown", Save refused with a pending model proposal or any other unacknowledged review warning; unchanged pre-filled lines at Save → `confirmed`. See D5; C3. Verification: the end-to-end pre-filled-only note case.
- [ ] 🟥 Task 2.5: Practitioner tab — "Learned shorthand" group: recent and all learned rules (trigger → wording, section, count, pre-filled flag) with one-click delete, mirroring `refresh_learned_phrases`; `learning_status` extended.

### Phase 3 — Style setting and sample-note learning
- [ ] 🟥 Task 3.1: Style setting UI — `ui/practitioner.py` "Writing style" radio group bound to `PractitionerSettings`; prose options disabled with a reason line when unavailable (C8). Design-system cue added.
- [ ] 🟥 Task 3.2: Renderers — `note.py` `render_note(note, style)`: `verbatim` = today's rendering; `clean` = one terse line per assertion in section order, no substitution (D7). Default `clean`. Done when both renderers are pinned against a fixture note.
- [ ] 🟥 Task 3.3: `sample_notes.py` — `python-docx` added to BASE `dependencies` in `desktop/pyproject.toml` with its mypy override here (codex PR-LOW-016: Phase 3 must close green before Phase 4); `read_sample_note(path | text)` (`.txt`, pasted text, `.docx` via `python-docx`), `learn_style_profile(notes) -> StyleProfileDraft`: section order via heading match against the 17 canonical labels, `heading_labels`, shorthand split into `recognised` (in `clinical_abbreviations.json`) and `unrecognised` (all-caps or abbreviation-shaped, not in the vocabulary — saved only when ticked, D10), measures, exemplars kept only when `refuse_learning_candidate` passes them unchanged, ≤ 30. Reads only; never writes near the source. See D9, D10.
- [ ] 🟥 Task 3.4: Learning UI — Practitioner tab "Learn from my notes": the consent box must be ticked (writes the style store's `ConsentRecord` at Save, no voice profile required — D9); pick up to five files or paste text (cap and minimum enforced); a review screen listing the headings map, recognised shorthand, unrecognised tokens with tick-to-keep (default unticked) and exemplars with per-item remove; Save writes `style_profile.json`; a subsequent dialog lists the paths with "Delete these files now" unticked; first-run banner line. See D9.
- [ ] 🟥 Task 3.5: Status — a separate `style_profile_report_line` (learned date, source count, exemplar count) cached on the Practitioner tab and refreshed on learn/delete events only; `model_file_report_lines` stays stat-only (round-51 MED-001 rule, `ui/models.py:1122–1124`). Verification: the poll-never-decrypts test. (codex PR-LOW-013)
- [ ] 🟥 Task 3.6: Learned-style management — Practitioner tab "Learned style" group: the saved exemplars and shorthand listed with per-item delete (rewrites the store), and a "Delete learned style" action (key-first via `delete_style_profile`, confirmation dialog, works with no voice profile, in-memory copies invalidated, failure message on `StoreWriteError`). See D9. (codex PR-MED-009)

### Phase 4 — Local language model and the prose styles
- [ ] 🟥 Task 4.0: Choose the prose runtime            [decision]
  - Options: `llama-cpp-python` (prebuilt CPU wheel from its documented wheel index, GGUF model) / `onnxruntime-genai` (PyPI wheel on the already-shipped onnxruntime, ONNX model export)
  - Decide after: a practitioner-run preflight from a normal terminal on this machine: install the candidate as a pinned hashed wheel into a throwaway venv on Python 3.14 (then 3.12 if 3.14 has no wheel), import, run a ten-token smoke generation; record wheel URL, version, sha256, Python version and seconds. If neither has a 3.14 wheel, the recorded fallback is a 3.12 venv for the app. See D8. (codex PR-MED-006)
  - Blocks: Tasks 4.1, 4.3, P.1
- [ ] 🟥 Task 4.1: Runtime and pin — the chosen runtime pinned by version + sha256 under `[ml]` with the wheel source documented (`AGENTS.md` Local Run Steps, `data-flow-map.md` second sanctioned fetch), its mypy override; an install/import/smoke gate test that refuses a source build; `language_model.py`: `LocalLanguageModel` (local path, SHA-256 against a single-sourced pin, a smoke generation at construction, `assert_offline_env` invariant), `MockLanguageModel`; `scripts/setup-models.py` entry for the 4B model with size + free-space precondition and `.candidate` resume; retention-schedule cache row. See D8; C1.
- [ ] 🟥 Task 4.2: Check 5 — `note_check.py` `fidelity_warnings(section_inputs, section_prose)` per D6 rules (a)–(d) (missing content token; added content token outside `prose_connectives.json`; added or removed negation/polarity token; added, removed or changed number / date / medication / laterality token → `style_fallback`), sharing the token classifiers. Done when the adversarial class test passes ("with paralysis", "no neck pain", removed negation, laterality flip each fail; a faithful rephrase passes). (codex PR-HIGH-001)   [executor: premium-only]
- [ ] 🟥 Task 4.3: `ProseStyleProvider` — input: confirmed assertion texts by section + `StyleProfile` (own_voice) or the fixed narrative instruction (narrative); prompt builder typed to refuse `TranscriptDocument`; output parsed per section; Check 5 per section; failure keeps `clean` for that section with the warning; ten fixture notes with the pass rate recorded on this task (acceptance ≥ 9/10) and CPU seconds per section recorded. See D6; C4.   [executor: premium-only]
- [ ] 🟥 Task 4.4: Note-tab wiring — `ui/note.py`: after each `finalise_note` (`:1013`) a `TaskThread` runs the style stage for the current `note_style`, bound to the finalised note's digest; the result lands in `GeneratedNote.style_renderings` only if the digest still matches (any edit invalidates); `format_note_body` (`ui/models.py`) is the ONE rendering path for display, `note.enc` persistence/reload and Copy (`ui/note.py:1014, 1129`); Save is DISABLED while a rendering is in flight and re-enabled only after the completed prose has been displayed — a Save never persists wording the practitioner has not seen (codex PR-MED-015: Save snapshots `self._note` at `ui/note.py:1069`); the no-sockets test covers a prose generation. See D7. (codex PR-MED-002)   [executor: premium-only]

### Phase H — Hardening stage
- [ ] 🟥 H1: `/review-loop` over Phases 0–4 as one surface
- [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
- [ ] 🟥 H3: `/security-review` — finalise the Task 0.5 stubs; same routing
- [ ] 🟥 H4: cross-family codex `/peer-review` re-check to convergence
- [ ] 🟥 H5: `docs/testing/shipping-gate.md` addendum: the gate runs under `clean`; an empty style column added for the recording set

### Phase P — Practitioner-owned
- [ ] 🟥 Task P.0: The Task 4.0 runtime preflight from a normal terminal (before Phase 4 starts).
- [ ] 🟥 Task P.1: Run `scripts\setup-models.py --only <4B entry>` from a normal terminal (before Phase 4's smoke).
- [ ] 🟥 Task P.2: Live smoke of Flow 1 on a real recording; Flow 2 across three consultations; one sample-note learning run; each style once; record CPU seconds per prose section.

## Retained Follow-Up Items
(not applicable until completion)

## Follow-Up Continuation Notes
(not applicable until completion)

---
*Plan saved to: .cursor/plans/plan-note-learning-and-styles.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
