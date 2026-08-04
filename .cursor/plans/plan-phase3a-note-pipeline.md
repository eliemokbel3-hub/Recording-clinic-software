# Feature Implementation Plan
**Feature:** phase3a-note-pipeline
**Overall Progress:** `16%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None
- Follow-up plans: Phase 3B — local `gpt-oss-20b` note model (not yet created; scoped in `Deferred — Actionable Later`)

## Goal
Turn a finished `TranscriptDocument` into a reviewable clinical note, without a language model. The app fills a canonical 17-section internal schema, maps it onto whatever Cliniko template a given practitioner uses, applies clinician-authored autofill macros and body-region prefills, and runs a mechanical checking stage that flags anything the transcript does not support. Phase 3B adds `gpt-oss-20b` behind the provider seam this phase defines.

## Planning Extraction Summary
Populate this during plan creation or plan hardening.

**Workflow Schema:** v22

**Executor tier:** entirely premium

### Agreed Scope (Build Now)
- Canonical 17-section note schema with stable keys, plus a per-practitioner template mapping layer (canonical → target field; many-to-one and omission both legal).
- `NoteModelProvider` Protocol plus the assertion-centric type model: `NoteAssertion` (the unit a section holds), `NoteSpan`, `NoteProposal`, `ConfirmationDecision`, `NoteRequest`, `GeneratedSection`, `NoteWarning`, `GeneratedNote`.
- `ExtractiveNoteProvider` (the phase's shipping default; no LLM) and `MockNoteModelProvider` (deterministic adversarial instrument).
- Speaker **role identification** — which cluster is the clinician — with a UI override. Clinician-owned sections accept clinician utterances only.
- Autofill engine: spoken-keyword triggers matched **against the transcript**, emitting **proposals** — never auto-inserted.
- Prefill engine: body-region templates, emitting proposals.
- One confirmation path for both accelerators: propose → show exact text → **per-assertion** confirm or decline → confirmed text becomes an assertion carrying its confirmation evidence.
- Per-session clinician-role confirmation, with a real UI control; clinician-owned sections stay blank until it is resolved.
- Error-severity warnings that block `write_note`, copy, and Complete — each with a tasked exit (acknowledge, retract-and-refinalise, regenerate, or delete-note-and-complete).
- A `template_profile_id` selector so a session is bound to the right clinic's mapping.
- Provenance-aware checking stage (`note_check.py`): grounding, high-risk classes, provenance integrity, scoped omission.
- Config engine: validating loader for mapping / autofill / prefill, shipped defaults plus user overrides, read-only viewer.
- `note.enc` artifact under the session key, and the `complete_session` custody-verification fix.
- Note review UI tab with provenance rendering, per-assertion confirmation, role control, and blocking-error presentation.
- Per-segment cepstral mean normalisation on speaker embeddings, plus a measured 2-way accuracy baseline on a real multi-speaker recording.
- Docs: partial threat-model re-review, data-flow map, retention schedule, design-system amendment, `PLAN.md` reconciliation.

### Deferred — Actionable Later
- **`runtime.py` extraction** — moving the offline-env and model-cache helpers out of `benchmark.py` into a shared module with re-exports.
  - Why deferred: Phase 3A adds no ML dependency, so the extracted helpers have **zero consumers** this phase. As originally planned it front-loaded the riskiest refactor in the phase (16+ import sites) purely to serve a Phase 3B consumer, in the same stage as the custody-critical `complete_session` change.
  - Intended future outcome: `runtime.py` holding `OFFLINE_ENV`, `OfflineEnvError`, `apply_offline_env`, `assert_offline_env`, `default_models_root`, `whisper_snapshot_missing/complete`, `list_whisper_candidates`, `WHISPER_REQUIRED_FILES`, `WHISPER_TOKENIZER_FILES`, `_present`; `benchmark.py` re-exports.
  - Relevant files / subsystems: `benchmark.py:43-142`; consumers `app.py:22`, `speech.py:38`, `transcription.py:58-63`, `ui/microphone.py:22-27`, `scripts/setup-models.py:63-67`; five embedded child-process source strings in `tests/test_integration_no_sockets.py` (literal starts **202, 391, 558, 731, 832** — AST-verified; the module's only real import is line 58).
  - Dependencies / prerequisites: none. `benchmark.py` imports nothing from `scribe_desktop` (stdlib only, ML lazy inside functions), so the extraction is a clean leaf with no circularity.
  - Recommended next action: do it as Phase 3B's opening step. **`benchmark.py` must gain an `__all__` first** — mypy `strict = true` implies `no_implicit_reexport`, which rejects re-export of imported names and would break four `src/` consumers plus ruff `F401`. Note the embedded child strings are *not* the hazard: they import at runtime, where `__all__` is unenforced. Carry `test_benchmark.py:47`'s lazy-import tripwire (`"faster_whisper" not in benchmark.__dict__`) to the new module.
  - Risk if deferred: minor: the extraction is bookkeeping until a second ML consumer exists.
  - Revisit by: Phase 3B opening step
  - Note: this deliberately deviates from the `AGENTS.md` "Phase-3-opening structural moves" carry-in, which recorded it as a Phase-3 opener. The deviation is recorded, not silent.

- **Ungated ONNX speaker-embedding upgrade** (ECAPA/WeSpeaker class, SHA-pinned like silero).
  - Why deferred: practitioner decision — measure the existing representation first. The upgrade is the fix if cepstral mean normalisation proves insufficient.
  - Intended future outcome: embeddings that separate real human speakers reliably enough to support estimated-k.
  - Relevant files / subsystems: `transcription.py:507-543` (`_segment_embedding`), `scripts/setup-models.py`.
  - Dependencies / prerequisites: the Phase 1 measurement result (Task 2.3).
  - Recommended next action: resolve as part of decision task D-S1; if 2-way accuracy on real speech is poor after CMN, this is the remedy.
  - Risk if deferred: ux-degradation: a third voice merges into another speaker's label and the clinician corrects attribution on review.
  - Revisit by: D-S1 resolution

- **Config editor UI** — screens for editing keywords, expansions, prefills, and template mappings.
  - Why deferred: practitioner decision — the config shape should settle against real use before a UI is built on it. Phase 3A ships a validating loader plus a read-only viewer.
  - Intended future outcome: in-app editing of all three config classes, multi-practitioner.
  - Relevant files / subsystems: `note_config.py`, `ui/`.
  - Dependencies / prerequisites: config schema stable after real use.
  - Recommended next action: its own phase after Phase 3B.
  - Risk if deferred: minor: editing is file-based in the interim.

- **Phase 3B — local `gpt-oss-20b` note model.**
  - Why deferred: the phase split decided this session. Everything in 3A is model-independent; 3B is a runtime decision plus one provider implementation.
  - Intended future outcome: `GptOssNoteProvider` behind the Protocol this phase defines, meeting `PLAN.md:175`.
  - Relevant files / subsystems: `note.py`, `scripts/setup-models.py`, `benchmark.py`, `ui/models.py`.
  - Dependencies / prerequisites: 3A gate passed.
  - Recommended next action: open with D-N1 (runtime, quantisation, acceptability bar) — candidates llama-cpp-python (GGUF) and onnxruntime-genai; Ollama/llama-server rejected up front (a localhost HTTP server collides with the ruff bans on `socket`/`http`/`urllib.request` and the no-sockets test). Evidence order: wheel gate on py3.14 + py3.12 → measured peak RSS vs total RAM (~12-13 GiB weights; a 16 GB machine is probably not viable) → wall-clock for a 17-section note → quality on this phase's matrix → chat-template and `parse_special` control → SHA-pinned acquisition. Model-boundary injection defences (harmony role separation, per-call nonce delimiter, `parse_special=False`, no tool capability) land there too, plus `note_model_ready()` kept **separate** from `models_ready()`.
  - Risk if deferred: blocked-work: note quality stays extractive until it lands.
  - Revisit by: Phase 3A completion gate

### Excluded — Revisit Only If Needed
- Semantic entailment checking via a second model as judge.
  - Why excluded: the clinician is the judge (`PLAN.md:14`); a judge model doubles the local compute budget and adds a second unverifiable component.
  - When to revisit: only if the lexical checker proves inadequate after real use.
  - Relevant files / subsystems: `note_check.py`.
  - Recommended next action (if any): none.

- Model-provided citations / self-reported grounding.
  - Why excluded: unreliable from a 20B and it adds injection surface. Grounding is derived mechanically, independent of provider cooperation — which is the point of it being a distinct stage per `PLAN.md:44-48`.
  - When to revisit: if 3B's model proves reliable at structured attribution.
  - Relevant files / subsystems: `note.py`, `note_check.py`.
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- The practitioner's two clinics can share one canonical schema, differing only in the mapping layer.
  - Why accepted for now: mapping is a projection; a superset canonical schema maps down to either template.
  - Risk if assumption becomes false: a clinic needs a section the canonical 16 lacks, forcing a schema addition after fixtures assert against its keys.
  - Trigger for revisit: the practitioner supplies both real template section lists (Task 1.0).
  - Recommended next action: confirm both lists before freezing the mapping fixtures.

- Cue matching plus speaker roles can populate the canonical sections usefully enough to be worth shipping.
  - Why accepted for now: it is the phase's fallback and its calibration instrument regardless. Usefulness is no longer left implicit, though — it now has its own **shipping gate** (see `Validation / Verification`), decided by the practitioner over a defined real-transcript set, separate from the completion gate.
  - Risk if assumption becomes false: copy-to-Cliniko is withheld and 3A is classified honestly as internal infrastructure until 3B lands. The phase still completes; only the "shippable without an LLM" claim retires.
  - Trigger for revisit: Task 6.4's first real-transcript run, then the shipping gate.
  - Recommended next action: record the outcome honestly rather than overselling it; the completion gate does not depend on it, and the shipping gate is allowed to fail without failing the phase.

- The same-user attacker stays outside the defended boundary; config files and in-memory note plaintext inherit that posture.
  - Why accepted for now: carried from the Phase 1 threat model, boundary 2.
  - Risk if assumption becomes false: config becomes an injection vector into clinical records.
  - Trigger for revisit: Phase 7 packaging.
  - Recommended next action: the loader fails closed on malformed config; recorded in the threat-model re-review.

### Key Design Decisions
- **Provenance is a first-class field on every note span** (`transcript` | `autofill` | `prefill`) — and it proves **attribution, not truth**.
  - Why: autofill and prefill insert text that is not in the transcript — exactly what the checker exists to catch. Treating them as generated content blocks every macro; ignoring them makes the checker meaningless. Provenance lets each class be generated, rendered, and checked differently.
  - **Scope limit, stated once and binding everywhere:** knowing *where a span came from* says nothing about whether its clinical claim is *true of this encounter*. Cross-family peer review (2026-08-04) broke the original design on exactly this point: a patient saying "I didn't follow the exercise programme" satisfies a trigger on "exercise programme", so a macro asserting "Home exercise programme reviewed and progressed" would have entered a signed note with no error warning — the trigger was present, grounding skipped autofill spans, and `clinician_asserted` is review-severity. Truth is supplied **only** by explicit clinician confirmation of the exact inserted text (below), never by provenance, trigger presence, or role attribution.
  - Alternatives rejected: blending all content and loosening the checker (destroys the safety property); refusing macros entirely (rejects a standard, legitimate clinical workflow); treating trigger presence as evidence of truth (the broken original design).
  - Still applies to follow-up work: Yes

- **Note generation runs post-QUEUED, from the transcript screen** — not inside the transcriber callable, not as a new session state.
  - Why: `session.py:421-431` routes any exception from the transcriber to `_fail_locked` and re-raises, so a generation failure would mark FAILED a session whose `transcript.enc` is already durable, and recovery re-runs Whisper from audio (minutes) to recover from a note failure. Post-QUEUED gives structural failure isolation, free retry without re-transcribing, and the recovered path for free.
  - Alternatives rejected: a new state between PROCESSING and QUEUED — costs `LEGAL_TRANSITIONS`, `_CONTROLS` (a bare lookup at `ui/models.py:117`, so a missed entry is a KeyError), `ACTIVE_STATES`, `RECOVERABLE_STATES`, and the 9×9 exhaustive matrix at `test_session_machine.py:85-86`, to buy nothing — the note is consumed by Phase 4 write-back, so it must exist before WRITTEN, not before QUEUED.
  - Still applies to follow-up work: Yes — 3B slots in as a provider swap with no pipeline change.

- **Autofill is a PROPOSAL, not an auto-insertion. Nothing clinician-authored enters a note without explicit per-assertion confirmation.**
  - Why: this reverses the original "split" posture (autofill auto-inserts, prefill confirmed), which the peer review broke — see the provenance scope limit above. Trigger matching still runs against the transcript and never against the note, but a matched trigger now makes a rule a *candidate*, not an insertion. Both accelerators converge on one path: propose → show the exact text → clinician confirms or declines → confirmed text becomes a span. Confirmation is **per assertion**, not per section: a prefill seed containing three independent clinical claims is three confirmations, because confirming a block is not evidence about each claim inside it.
  - Alternatives rejected: auto-insert with attribution (the original design — permits a false assertion into a signed note with zero errors); auto-insert restricted to clinician-spoken triggers (role identification is a heuristic, so it cannot carry a truth guarantee); per-section confirmation for prefill (hides independent claims behind one click).
  - Cost accepted: more clicks per note. That is the price of the safety property, and it is the practitioner's own recorded preference over the alternative.
  - Still applies to follow-up work: Yes — binds 3B unchanged.

- **Confirmation is EVIDENCE carried by the artifact, not a caller convention.**
  - Why: an earlier draft had `finalise_note()` take a caller-supplied "confirmed proposal set" while the saved span recorded nothing about the confirmation. Any caller could construct a clinician-authored span directly, and the artifact could not prove a human ever saw the text. A safety property that only holds if callers behave is not a safety property.
  - Rule: every non-`transcript` assertion carries `proposal_id`, the exact-text digest of what was shown, the config digest it came from, and a `ConfirmationDecision` (decision + timestamp). `write_note` **verifies** every non-transcript assertion against those records and refuses the write if any is unbacked. Confirmation is reconstructible from `note.enc` alone.
  - Config expansions are authored as **explicit lists of atomic assertions** — never prose that gets NLP-split at runtime, which would make the decomposition itself an unverified inference.
  - Alternatives rejected: caller-supplied confirmed sets (unprovable); a confirmation flag without exact-text binding (cannot detect text changing between display and write).
  - Still applies to follow-up work: Yes

- **An `error`-severity warning blocks action; it is not advisory — and every blocking state has a tasked exit.**
  - Why: the original plan defined the error/review taxonomy and gated the *fixture matrix* on it, but nothing in the running app acted on an error — a note carrying a fabricated diagnosis, a laterality flip, or a dose error could be written, copied into Cliniko, and completed. A warning with no consequence is documentation, not a control.
  - Rule: any unresolved `error` blocks `write_note` (enforced **inside** `write_note`, not only by the UI), blocks copy, and blocks Complete. `review`-severity warnings do not block but must be acknowledged before Complete.
  - **No blocking state may be unresolvable.** Round 2 found this created a deadlock: every clinician-authored assertion raises an unsuppressible `clinician_asserted` review warning requiring acknowledgement, yet nothing supplied an acknowledgement action; errors were said to clear "by removing a span or regenerating", yet no retraction control existed; and `mapping_drop` was an error that regeneration recreates, since the mapping UI is read-only. A blocked Complete with no exit means the 24 h sweep destroys the session. So: acknowledgement state and control, per-assertion retraction with refinalisation, and the explicit delete-note-and-complete path are all **tasked**, and `mapping_drop` is downgraded — content a legal mapping would drop renders into a mandatory "Unmapped content" target instead of raising an unclearable error.
  - Alternatives rejected: advisory-only errors (the original design); blocking on `review` too (unusable given expected review volume); keeping `mapping_drop` an error (unresolvable by construction).
  - Still applies to follow-up work: Yes

- **`NoteAssertion` is the unit of the note, not `NoteSpan`. A transcript-derived assertion carries exactly ONE contiguous source interval.**
  - Why: coordinate reconstruction is **span-local**, and span-local exactness does not compose. A section holding two individually-valid spans — "the cervical spine" from one range, "is tender" from another — reconstructs both exactly while asserting something the transcript never said. Round 2 of the cross-family peer review broke the round-1 fix on exactly this: the earlier claim that "cross-source recombination is rejected structurally" was true within a span and false across spans.
  - Rule: a `transcript` assertion contains one span with one contiguous `(segment_index, first_word_index, last_word_index)` interval. Grammatical concatenation of independently grounded spans into one assertion is prohibited by the type, not by a check. Assertions render with a hard visual boundary — a separate bullet — so the clinician reads discrete quoted claims, never assembled prose.
  - Cost accepted: notes read as a list of quoted claims rather than flowing prose. For an extractive provider that is honest output; 3B's model provenance may relax it under its own contract.
  - Alternatives rejected: a checker pass detecting recombination (undecidable lexically — the recombined text is grounded token-for-token); trusting span-local reconstruction (the broken round-1 design).
  - Still applies to follow-up work: Yes

- **Grounding for `transcript` spans is by exact transcript coordinates, not lexical containment.**
  - Why: lexical containment permits false recombination — from "the cervical spine is normal; the lumbar spine is tender", a provider can assemble "the cervical spine is tender" using only grounded tokens. With an extractive provider every span *is* a literal transcript slice, so the span can carry typed `(segment_index, first_word_index, last_word_index)` coordinates and be verified by reconstructing it from the immutable transcript and comparing. That is exact, not heuristic.
  - The original design used lexical containment in 3A to accommodate a paraphrasing model in 3B — weakening the phase that can be exact to suit a phase that does not exist yet. 3B adds a distinct `model` provenance with its own containment-based contract when it arrives.
  - Alternatives rejected: lexical containment in 3A (the original design); deferring all grounding to 3B (leaves 3A unverified).
  - Still applies to follow-up work: Yes — 3B extends, never replaces, this.

- **Uncertainty severity grades on `probability < UNCERTAINTY_THRESHOLD`, never on `TranscriptWord.uncertain`.**
  - Why: `mark_words` (`transcription.py:342-346`) sets `uncertain` as a **union** — `probability < threshold OR is_number_token OR is_name_like_token`. Every number and every name-like token is therefore `uncertain=True` unconditionally. Grading "error, or review if source uncertain" on that flag makes the review branch fire 100% of the time for exactly those two classes, rendering their error branch unreachable and silently degrading the two highest-value checks to review-only.
  - Alternatives rejected: reusing the `uncertain` flag (the original design; caught at hardening).
  - Still applies to follow-up work: Yes — binds 3B unchanged.

- **The note view is copyable; the transcript view stays display-only.**
  - Why: Phase 4 owns Cliniko write-back, so until it lands copy/paste is the only route from a generated note into Cliniko. A display-only note makes this phase unusable in practice.
  - Alternatives rejected: display-only (blocks all use before Phase 4); copy-after-Complete (Complete deletes the key, so the note becomes unreadable — would require reworking custody ordering).
  - Still applies to follow-up work: Yes — practitioner-ratified amendment to a documented non-negotiable; recorded in the threat model and design system, not applied silently.

- **Speaker role identification lands in this phase.**
  - Why: section routing is fundamentally a who-said-it problem, and no clinician/patient distinction exists in the codebase — `speaker_1`/`speaker_2` are cluster indices whose only guarantee is that the first segment is `speaker_1` (`transcription.py:586`). Without roles, a patient's "I think it's a slipped disc" routes into `diagnosis` — precisely what `PLAN.md:14` forbids, emitted by a provider otherwise described as grounded by construction. Grounded is not the same as correctly attributed.
  - **The heuristic is PRESELECTION ONLY.** Talk-time share, question-asking rate and first-speaker order are not stable role identifiers, and even a correct role does not make a clinician's *question* ("Could this be a disc problem?") a diagnosis. So: per-session clinician-role confirmation is **mandatory** before any clinician-owned section populates; the heuristic supplies the default selection and nothing more. If clustering is merged or the role is unresolved, clinician-owned sections stay **blank** and the UI surfaces candidate quotations for the clinician to place.
  - Alternatives rejected: restricting the extractive provider to speaker-neutral sections (ships a much thinner note); routing regardless and flagging (leans on warnings for a structural problem, worsening the false-positive load that is already the phase's top risk); trusting the heuristic unconfirmed (a wrong assignment restores the exact patient-speculation-to-Diagnosis failure this decision exists to prevent).
  - Still applies to follow-up work: Yes

- **Estimated-k diarization is a decision task, not a commitment.**
  - Why: the 25-dim representation (`_segment_embedding`, `transcription.py:507-543`) has no per-segment gain normalisation, its whitening is estimated from ~n points in 25 dims, and every existing diarization test uses sine tones at 220 Hz vs 2600 Hz — nothing demonstrates it separates real human speakers even at k=2. Adding a more sensitive decision (how many clusters) on top of an unvalidated representation is backwards.
  - Alternatives rejected: implementing estimated-k directly (the pre-hardening plan); dropping speaker work entirely (leaves a third voice silently merged).
  - Still applies to follow-up work: Yes

## Key Findings

### Files / Symbols Involved
- **New:** `note.py` (types, Protocol, both providers, `compose_draft`/`finalise_note`, `write_note`/`read_note`, canonical section constant), `note_config.py`, `note_fill.py` (autofill + prefill), `note_check.py`, `ui/note.py`.
- **Modified:** `session_store.py` (`NOTE_FILENAME`, `complete_session`), `session.py` (note-artifact accessor), `transcription.py` (cepstral mean normalisation; speaker roles), `logging_setup.py` (tripwire signatures), `ui/models.py` (factories, rendering, `SessionControllerLike`), `ui/transcript.py` (Generate, `is_busy`), `ui/main_window.py` (tab, signals, `closeEvent`, `_destroy_recovered_crypto` guard), `desktop/pyproject.toml` (`package-data` for shipped config defaults).
- **Read-only anchors:** `read_transcript:788`, `atomic_write_bytes:488`, `is_number_token:300`, `is_name_like_token:312`, `format_timestamp` (`ui/models.py:212`), `SESSION_ID_PATTERN`, `_STRIP_PUNCT_RE:203`, `_COMMON_SEGMENT_STARTERS:210`.

**Shared-helpers inventory** (used by more than one phase — build once, reuse):
- `normalise_token()` / `content_tokens()` — **one** implementation in `note.py`, consumed by autofill trigger matching, the structured contradiction checks, and Check 4 omission. NOT by Check 1, which is exact coordinate reconstruction and needs no tokenisation. Divergent normalisers would make Check 3 raise `autofill_trigger_absent` **errors** on rules that legitimately fired.
- `speaker_role(segment)` — clinician/patient resolution, consumed by the extractive provider, Check 4's scoping, and the UI.
- The canonical section key set — consumed by `note_config` validation, both providers, the checker, and the mapping layer.

### Codebase Integration Notes
Repo-specific gotchas verified during hardening — do not rediscover these:

- **`TranscriptWord.uncertain` is not an acoustic confidence signal.** See the Key Design Decision above. Use `probability`.
- **Four all-`speaker_1` guard sites**, not two: `_cluster_embeddings:579-580` (zero variance) and `:583-584` (all labels equal), plus `label_speakers:606-607` and `transcribe_session:909-910`. The docstring at `:596-602` says to change them together. `:585-586`'s binary `SPEAKER_1 if label == first else SPEAKER_2` hardcodes two speakers and needs first-appearance canonical ordering for k>2.
- **`_kmeans_two:553` does `rng.choice(count, size=2, replace=False)`** — generalising to `size=k` raises `ValueError` when k > n. Silhouette is undefined at k=1, and duplicate points produce NaN, which `np.argmax` selects as the maximum. `test_transcription.py:414-419` already feeds exact duplicates, so a naive implementation fails on an existing fixture.
- **The live path has no note plumbing.** `_LiveSession` (`session.py:207-220`) keeps `directory`/`crypto` private and `SessionControllerLike` (`ui/models.py:54-83`) exposes neither. The recovered path works only because `main_window.py:189-212` happens to hold `outcome.crypto`. A controller accessor plus a `FakeController` (`tests/test_ui_screens.py:103`) update is required.
- **`_destroy_recovered_crypto` (`main_window.py:214-220`)** is invoked at `:185` when a live transcript overwrites the view, and can zeroize a key under a running generation thread.
- **`complete_session` verifies only `transcript.enc`** (`session_store.py:563-581`) before `delete_session_key`.
- **`ui/transcript.py` has no `is_busy`**; `main_window.py:154-158` checks exactly `session_screen`, `recovery_screen`, `microphone_screen`.
- **`tests/test_ui_screens.py:773-774` asserts `tabs.count() == 5`** plus the tab-title list — a Note tab breaks both.
- **`TaskThread.failed` (`ui/tasks.py:38`) emits `f"{type(exc).__name__}: {exc}"` to the UI** and its docstring claims these carry structural text only. A pydantic `ValidationError` over note models embeds the offending values — i.e. note text.
- **`models_ready()` (`ui/models.py:269`) is reused verbatim as the CI gate `requires_ml_models`** (`test_integration_no_sockets.py:95`). Do not fold a note model into it (binds 3B).
- **`desktop/pyproject.toml` has no `package-data`** — non-`.py` shipped config defaults would be invisible to a non-editable install.
- **Diarization tests are `pytest.importorskip("numpy")`-gated** (`test_transcription.py:410, 415, 422, 577`), so speaker work is behind the best-effort ML install even though the note layer is not.
- **`CLINICAL_INITIAL_PROMPT` names exactly two drugs and is token-budget-capped** (`transcription.py:107-158`) — correctly rejected as a medication lexicon source.
- **`sweep_protected_ids` (`app.py:105-124`) already protects any non-terminal controller session**, so a QUEUED session under note review is safe from the 24 h sweep with no change.
- **`_CONTROLS[QUEUED]` already disables everything** — post-QUEUED placement needs no `_CONTROLS` entry.

### External / API Findings
N/A — this phase makes no network calls and integrates no external API. Cliniko integration is Phase 4.

## Planned Workflow Summary

### Flow 1 — Generate a note from a finished transcript
Ordering is load-bearing: **every span is composed before any check runs, and nothing is written until the checks pass.** The original ordering checked first and confirmed afterwards, so confirmed clinician-authored spans reached `note.enc` having never passed the provenance-integrity check.

**On the Transcript screen, before any generation** — this placement is load-bearing: both inputs are consumed by `compose_draft()`, so a control living on the Note tab would depend on output it must precede (round 2's circular-sequencing finding):
- Session reaches QUEUED after transcription.
- The clinician confirms the session's `template_profile_id` and the clinician-role assignment (the heuristic preselects; confirmation is mandatory). Both are persisted onto `NoteRequest` and `GeneratedNote`, so the saved artifact records which cluster was confirmed as the clinician.
- **Generate** becomes available only once both are confirmed.

**Generation (`compose_draft()`, no checks):**
- The provider fills each canonical section from role-attributed utterances, producing `transcript` **assertions** — one contiguous source interval each, never assembled across intervals.
- Autofill triggers are matched against the transcript and prefill seeds selected by body region — both emitting **proposals** at atomic-assertion granularity, neither entering the note.

**Review and confirmation (Note tab):**
- The tab renders the base note plus every proposal as its **exact proposed text**, each assertion on its own hard boundary, provenance visible.
- The clinician confirms or declines **per assertion**. Each confirmation records `proposal_id`, the exact-text digest of what was displayed, and a `ConfirmationDecision`.

**Finalisation (`finalise_note()`):**
- All checks run over the composed note — coordinate reconstruction, structured contradiction checks, provenance integrity, omission, uncertainty.
- Zero unresolved `error` and zero unacknowledged `review` warnings are preconditions. Exits from a blocked state: retract the offending assertion and refinalise, regenerate, or take the explicit delete-note-and-complete path.
- `write_note` independently verifies every non-transcript assertion against its confirmation record and refuses an unbacked one, then writes `note.enc`. The note displays mapped onto the practitioner's template; copy is enabled only if the shipping gate passed.

### Flow 2 — Complete or discard with a note present
- Complete is refused while generation is running, while any proposal is unconfirmed, while an `error` is unresolved, or while a `review` warning is unacknowledged.
- On Complete: `transcript.enc` is fsynced and verify-decrypted, then `note.enc` if present, then the key is deleted.
- **A `note.enc` that fails any check FAILS CLOSED — the key is retained and Complete does not proceed.** Verification covers fsync, authentication, parse, session binding, and `transcript_digest` match; an authenticated-but-malformed or stale note fails too. The clinician is offered **Regenerate note**, or an explicit choice to delete the note and complete without one.
  - This reverses the original asymmetric policy, whose rationale ("the note is regenerable") was self-defeating: Complete deletes the session key, so once it proceeds the transcript is unreadable and the note can never be regenerated. Retaining custody is what keeps regeneration possible.
- On Discard: the key is deleted first, then the whole session directory, covering `note.enc` with no change.

## Design Decisions
Recorded once in `Planning Extraction Summary → Key Design Decisions`; not restated here per the State-once convention.

Two additional structural decisions:
- **The high-risk classes are re-aimed at clinician-authored spans.** With coordinate grounding, a `transcript` span either reconstructs exactly or is an error — there is no ungrounded-token residue in 3A for the classifier table to run over. The classes still matter, but at a different target: a **confirmed `autofill`/`prefill` span asserting something the transcript CONTRADICTS**. A prefill seed saying "left shoulder" in an encounter where the transcript says right is a laterality error; a macro asserting a dose the transcript contradicts is a dose error. So the classes run as *contradiction* checks against the transcript over clinician-authored spans, not as *containment* checks over provider output.
  **Scope honestly: confirmation is the ONLY control on the CRIT's example.** An earlier draft of this plan claimed the negation check also caught the patient-said-"I didn't follow the exercise programme" case. That was wrong and is retracted: "I didn't follow the exercise programme" does not contradict "Home exercise programme reviewed and progressed" — a clinician can review something the patient was not doing. Both can be true. No mechanical check catches it; per-assertion clinician confirmation does, and nothing else does.
  **Decidability bound.** Closed vocabularies plus bounded windows do not establish that two mentions concern the *same fact* — "right hip, left shoulder" defeats naive laterality comparison, and unrelated numbers or medications produce false contradictions the same way. So contradiction checks run ONLY over structured assertions carrying an explicit claim type, an entity/anatomical anchor, and a value, comparing only matched entities. An assertion without that structure is not contradiction-checked; it is carried by confirmation alone, and the plan says so rather than implying coverage it does not have.
  Alternatives considered: six independent containment checks (the pre-hardening design — six interacting FP rates, aimed at a span class that no longer produces ungrounded tokens); free-text contradiction detection (not decidable with closed vocabularies); dropping the classes in 3A (leaves structured clinician-authored contradictions undetected).
  `is_name_like_token`'s `first_in_segment` heuristic is calibrated for Whisper-capitalised VAD segment openers — a concept absent from note prose — so it is applied only to clinician-authored assertions, never to reconstructed transcript assertions.
- **`NoteSpan` carries typed source coordinates, not an encoded string.** `source_ref: str | None` (rule id or template id — `provenance` disambiguates), `trigger_start_seconds: float | None`, and for `transcript` provenance a typed `source_coords: (segment_index, first_word_index, last_word_index)`. A single encoded string doing three jobs would be parsed back by the UI, by the trigger verification, and by the confirmation resolution, and would make the "resolvable source" global property untestable without a parser.
  Coordinates also carry the **uncertainty** obligation: from `(segment, first, last)` the checker can reach every source `TranscriptWord` and its `probability`, so a low-confidence ordinary clinical word copied verbatim — which trips none of the high-risk classes — still raises a `review` warning. Without coordinates that requirement (`PLAN.md:175`'s "all uncertainty surfaced") is unverifiable, and repeated identical words with different probabilities are ambiguous.
  Alternatives considered: one encoded union string (rejected); span text plus a lexical back-search (ambiguous on repeated words); no coordinates (leaves grounding heuristic and uncertainty unprovable).

## Schema / Data Changes
- **Canonical section set (17, stable keys).** The plan previously referred to "the canonical 16-section constant" without listing it; reconciled against the captured template and recorded here as the single source. **Reference sections by KEY, never by ordinal** — the list has already grown once, and ordinal references are how off-by-one errors get baked into fixtures.

  | # | Key | Meaning | Owner | Template A target |
  |---|---|---|---|---|
  | 1 | `presenting_complaint` | Why the patient came today | patient | Presenting complaint/patient progress |
  | 2 | `history_presenting_complaint` | How the current problem developed | patient | Presenting complaint/patient progress |
  | 3 | `progress_since_last_visit` | **NEW** — change since the last appointment | patient | Presenting complaint/patient progress |
  | 4 | `past_medical_history` | Relevant prior history | patient | Presenting complaint/patient progress |
  | 5 | `red_flags_screening` | Screening questions and answers | either | Assessment |
  | 6 | `objective_examination` | Observed findings, tests performed | clinician | Assessment |
  | 7 | `outcome_measures` | Pain scores, ROM, functional scales | either | Assessment |
  | 8 | `assessment` | Clinical reasoning | **clinician** | Assessment |
  | 9 | `diagnosis` | Working diagnosis / impression | **clinician** | Diagnosis |
  | 10 | `treatment_performed` | What was done this session | clinician | Treatment |
  | 11 | `response_to_treatment` | In-session response | either | Response to treatment |
  | 12 | `advice_home_exercise` | Advice given, home programme | **clinician** | Management/Advice |
  | 13 | `management_plan` | Ongoing plan | **clinician** | Management/Advice |
  | 14 | `consent` | Consent discussion, as narrative | clinician | **intentionally unmapped** — Template A's only consent target is an attestation checkbox |
  | 15 | `referrals_investigations` | Referrals made, imaging requested | clinician | Management/Advice |
  | 16 | `precautions_contraindications` | Cautions affecting treatment | clinician | Assessment |
  | 17 | `follow_up_review` | Next appointment, review timing | clinician | Management/Advice |

  Clinician-owned (populate only after role confirmation): `assessment`, `diagnosis`, `advice_home_exercise`, `management_plan`.

  **Mapping is a PROPOSAL pending practitioner confirmation** at Task 3.1 — where content belongs is a clinical judgment, not an engineering one. The non-obvious calls to confirm: `outcome_measures` → Assessment (vs Response to treatment), and `referrals_investigations` / `follow_up_review` → Management/Advice.

  **The mapping config distinguishes UNMAPPED from INTENTIONALLY UNMAPPED.** A canonical section with no target because the mapping author overlooked it raises the `mapping_drop` review warning; one marked intentionally-unmapped is silent. Without the distinction, `consent` would warn on every note where consent is discussed — which is most of them — and warning fatigue is this phase's top risk. Practitioner decision 2026-08-04: fold `past_medical_history` into Presenting complaint/patient progress and `red_flags_screening` + `precautions_contraindications` into Assessment, so nothing safety-critical is dropped; mark `consent` intentionally unmapped, since the checkbox is ticked manually. **Assessment therefore carries screening and precaution content it would not have carried if written by hand** — a deliberate trade recorded here so it is not mistaken for a routing bug.

  **Never map a canonical section to an attestation-typed target.** The rule keys on TARGET TYPE, not on the section: `consent` is legitimately mappable to a free-text consent field in some other practitioner's template, and is unmapped here only because Template A's target is a checkbox (see Critical Constraints).

- **New encrypted artifact `note.enc`** in `sessions\<id>\`, under the same session key as audio and transcript, written via `atomic_write_bytes` with **no AAD** (matching `write_transcript`, whose docstring records why: `complete_session` verifies with a plain decrypt and the two must stay in agreement). `NOTE_FILENAME` joins the `Final` constants at `session_store.py:66-68`.
- **New plaintext config files** under `%LOCALAPPDATA%\ClinikoScribe\config\` plus shipped in-repo defaults — clinician-authored boilerplate, not patient data, and deliberately outside the session store and the 24 h rule so they survive session destruction.
- `GeneratedNote` carries `transcript_digest` and `config_digest` for staleness detection and attribution.

## Config / Environment / Deployment Impact
- No new environment variables, no migrations, no deploy-side config — the app is local-only (`AGENTS.md` Hosting: `None (local-only)`).
- **Config resolution must be specified before `config_digest` has meaning** (Task 3.2): precedence between shipped defaults and user overrides, merge-vs-replace granularity, first-run behaviour with no user config, and behaviour when shipped defaults change under an existing override. Follow the existing root-resolution idiom — `os.environ.get("LOCALAPPDATA") or str(Path.home())` (`session_store.py:164-171`, `benchmark.py:102-105`, `logging_setup.py:115-116`) — and resolve the UNC question one way or the other, as `session_store.py:165-169` did deliberately for session roots.
- `desktop/pyproject.toml` needs `package-data` if shipped defaults are non-`.py` files.
- No new runtime dependency. This phase adds nothing to the `[ml]` extra, so the note layer runs on every CI leg rather than behind a best-effort install — **except** the speaker work, which is numpy-gated.

## Critical Constraints
- **Documentation-only** (`PLAN.md:14`): never invent diagnoses, examination findings, treatment, advice, referrals, investigations or plans. Unsupported sections stay blank.
- **Runtime performs zero network I/O.** This phase adds no network surface; the ruff bans on `socket`, `http`, `urllib.request`, `PySide6.QtNetwork` stand.
- **No plaintext clinical content at rest outside the encrypted session store, and none in logs.** New tripwire signatures must cover `note_sections`, `note_spans`, `note_warnings`, `span_text`, `note_excerpt`, **and `transcript_utterances`** — the last carries raw transcript across the provider boundary 16× per note and is matched by none of the others (`PayloadTripwireFilter` does plain substring matching, `logging_setup.py:108`).
- **Cryptographic deletion by key custody**: every new clinical artifact lives under the session key inside `sessions\<id>\`.
- **Complete ordering is binding**: fsync → verify decrypt → delete key. The note joins this ordering and **fails closed exactly like the transcript** — any failure retains the key.
- **No clinician-authored text enters a note without explicit per-assertion confirmation of the exact inserted wording.** Binds autofill and prefill identically. A matched trigger makes a rule a candidate; it never inserts.
- **Trigger matching runs against the transcript, never against the note.** Necessary but not sufficient — presence gates candidacy, not truth.
- **An unresolved `error` warning blocks `write_note`, blocks copy, and blocks Complete.** `review` warnings do not block but must be acknowledged before Complete.
- **`transcript`-provenance spans are verified by exact-coordinate reconstruction** against the immutable transcript; any mismatch is an error. Cross-source recombination is rejected structurally, not detected lexically.
- **Every non-transcript span is attributed on the face of the note** and carries a `clinician_asserted` review warning that cannot be suppressed.
- **The clinician-owned sections — `assessment`, `diagnosis`, `advice_home_exercise`, `management_plan` — populate only after per-session role confirmation.** Unresolved role ⇒ those sections stay blank.
- **The app NEVER writes, ticks, or proposes a consent attestation.** The practitioner's real template carries Informed Consent as a checkbox asserting that working diagnosis, benefits and risks were explained and consent was gained. That is a claim about a conversation having happened, not a description of findings — and unlike a wrong sentence in a note, a wrongly-ticked consent box is a false legal claim indistinguishable from a true one. No canonical section maps to it, no proposal path reaches it, and the note view renders it as a manual reminder only. Practitioner-ratified 2026-08-04.
- **`mypy strict` and `ruff` must stay clean**; no new mypy override is required by this phase.

## Validation / Verification
- Per phase: `cd desktop && ruff check . && mypy && pytest` (556 collected today).
- **Adversarial fixture matrix**, ~60-80 curated cells, as `(fixture_id, transcript, provider_behaviour, config, expected_warning_codes)` over authored `TranscriptDocument` fixtures:
  - **Axis A — transcript content**, from `PLAN.md:164-173`: negation and changing symptoms; left/right and anatomical region; numbers, dates, medications, dosages, measurements; small talk; overlapping speakers and accents; uncertainty and contradiction; spoken prompt injection; apparent end-of-consultation and new-patient greetings. Acoustic rows simulate the transcript's observable consequences (low `probability` words, mis-segmented speakers, merged turns), not audio.
  - **Axis B — provider behaviour** via `MockNoteModelProvider`: faithful; fabricated fact; laterality flip; dose change; negation flip; name substitution; invented diagnosis/plan/referral/investigation; over-omission; obeys an injected instruction; malformed output.
  - **Axis C — config behaviour**: trigger present / absent / spoken by the patient; overlapping triggers; prefill confirmed / declined / partially confirmed; a mapping collapsing several canonical sections into one target; a mapping dropping a populated section.
- **Fixtures carry an expected-output oracle, not only expected warning codes.** Each cell declares its expected canonical section contents, the exact `source_coords` of every `transcript` span, span ordering, and the mapped per-clinic output. Asserting warning codes alone lets a cue matcher that produces badly organised notes pass every test — the phase would go green while its shipping provider is unusable.
- **Eight global properties over the matrix:**
  1. No false negatives on error classes — every fabrication/flip cell produces its code.
  2. No false positives — every faithful cell, and every cell driven by `ExtractiveNoteProvider`, produces zero error warnings. Includes the multi-body-region, multi-medication and multi-measurement cells that would defeat naive contradiction windows.
  3. No unattributed content — every `autofill`/`prefill` assertion carries `clinician_asserted` and a resolvable source.
  4. **No unconfirmed content reaches a note** — `finalise_note()` refuses any composed note containing a proposal, and `write_note` refuses on an unresolved `error`. Asserted as *action states*, not warning codes.
  5. **Exact reconstruction** — every `transcript` assertion rebuilds byte-identically from its single contiguous interval against the fixture transcript.
  6. **No cross-span assembly** — an adversarial fixture reproducing the recombination case ("the cervical spine is normal; the lumbar spine is tender" → an attempted "the cervical spine is tender" assembled from two individually valid intervals) must be **unrepresentable at construction**, not merely flagged. This is the round-2 CRIT, pinned.
  7. **Confirmation is provable from the artifact** — every non-`transcript` assertion in every saved fixture note carries a `ConfirmationDecision` whose `shown_text_digest` matches its text. A note constructed with a clinician-authored assertion lacking one is refused by `write_note`.
  8. **Uncertainty is surfaced** — every low-`probability` *included* source word draws a review warning; every fixture's `clinically_material_span_ids` are either preserved or draw an omission warning. Fixture-only oracle, honestly scoped: omitted low-confidence content is covered presentationally by Task 7.6, not by a check.
- **Targeted regression tests:** the two diarization degenerate-case guards agree on identical input; an injected payload reaches no instruction position in any assembled `NoteRequest`; `requires_ml_models` gating is unaffected by note work; `tabs.count()` and tab-title assertions updated.
- **Speaker measurement:** role and 2-way cluster accuracy across several labelled human recordings including a three-speaker one, before and after cepstral mean normalisation — the evidence that resolves D-S1.
- **Completion gate:** CI green on py3.12 and py3.14; the eight global properties hold; and recorded synthetic consultations run end to end with autofill and prefill exercised and the note mapped onto the real Cliniko template — judged on: every span attributed, no unconfirmed proposal in a saved note, no unresolved error at Complete, no material clinician-spoken content silently dropped, no clinician-owned section populated from patient speech or from an unconfirmed role, and every low-confidence source word surfaced.
- **Shipping gate (separate from the completion gate):** copy-to-Cliniko is exposed only if the practitioner judges the extractive output acceptable over a defined real-transcript set. If it is not, 3A is classified honestly as internal infrastructure and the copy affordance is withheld until 3B. This is the answer to "the phase can go green while its provider is unusable" — usefulness gets its own explicit gate rather than riding on the test suite.
- This gate deliberately excludes `PLAN.md:175`'s "no unsupported clinical assertion" as a *product* claim — with an extractive provider, `transcript` spans are exact by reconstruction. Its "all uncertainty surfaced" clause is **not** excluded: global property 8 carries it, because that clause is separable and verifiable in 3A. The full `PLAN.md:175` gate is 3B's, against a model that can violate the first clause.

## Deferred / Out of Scope
Recorded in `Planning Extraction Summary` above — `runtime.py` extraction (→ 3B), the ONNX speaker-embedding upgrade (→ D-S1 outcome), the config editor UI (→ post-3B), and Phase 3B itself. Excluded outright: semantic entailment via a judge model, and model-provided citations.

Everything Cliniko-facing stays Phase 4: template fetch, draft creation, the write ledger, dedupe, and the offline queue. This phase maps canonical sections onto a practitioner template for **display only**.

## Current State / Handoff Note
- Loop config: executor=claude-p model="opus" effort=xhigh profile=default; peer=codex model="gpt-5.6-sol" effort=xhigh; architect=off; cadence=every-phase; caps=review:3,peer:4; gates=fix-biased; cap-raise=auto-plus-one; scope=all; autocommit=on; isolation=none; merge=off; perms=scoped; liveness=10
- **START HERE — FINAL Phase 1 handoff (executor `stage-1`, 2026-08-04, after peer rounds 3–6 and their fix legs).** Phase 1 (Tasks 1.0–1.5) is COMPLETE and green, with ONE item deliberately carried forward (Phase 5 Task 5.0 — read it before writing Axis-B behaviours). Phase 2 (Tasks 2.1–2.3 + `[decision]` D-S1) is next; D-S1 is a MUST-PAUSE decision task for the practitioner.
  - **What exists now:** `desktop/src/scribe_desktop/note.py` (~840 lines) — the canonical 17-section constant, the assertion-centric type model, digests, the single tokenisation source, the provider Protocol, `ExtractiveNoteProvider` and `MockNoteModelProvider`. Plus 10 new tripwire signature families in `logging_setup.py` and the note leg of the Complete ordering in `session_store.py`.
  - **Suites:** `ruff` clean; `mypy` strict clean on **24** source files (23 before); `pytest` **775 passed** (556 before). `ruff` also prints two `Access is denied (os error 5)` warnings before passing — see the residue note below; they are not a failure.
  - **`/review-loop`: converged in 2 rounds** (cap 3). Round 1: 0 CRIT / 0 HIGH / 2 MED / 3 LOW, all five applied and verified one at a time. Round 2: zero findings, two candidates dropped on verification. No gate fired — every finding was `Fix-now`, none was scope expansion, so the Deferral Confirmation Gate stayed silent (correctly, on an empty batch).
  - **Round 3 — cross-family peer (codex `gpt-5.6-sol`) — 1 finding, PR-HIGH-001, now FIXED and closed.** The tripwire filter scanned `record.getMessage()` only, while handler filters run BEFORE the formatter appends the traceback — so a caught note-validation error could persist clinical text into the log with the drop counter untouched. `PayloadTripwireFilter` now scans message + `exc_info` + `stack_info`, side-effect-free. My leg-1 verification confirmed the mechanism but could not reproduce it (script execution was not granted then); the fix leg DID reproduce it — the two new channel tests were run against the pre-fix scan surface and both failed, showing the would-be-written traceback carrying `input_value={'span_text': 'SECRETMARK...`. That two-leg record (verify → operator disposes → fix) is in Round 3's `/fix notes`.
  - **This closes the gap between what the logging docstring claimed and what the code did.** The docstring now states precisely what the tripwire guarantees: it catches content arriving with a REGISTERED SIGNATURE in message, traceback, or stack — and it CANNOT detect bare clinical text with no signature, which is why `log_event`'s whitelist is the primary control and the tripwire is the backstop. Do not re-inflate that claim.
  - Two things a later phase should know: the fix is a small **operator-approved scope expansion** (the filter body at `logging_setup.py:138-152` sits outside Task 1.4's declared `:57-87`), and a two-handler logger now renders a bad record's traceback twice — accepted, documented in `_scan_text`, and irrelevant at this app's log volume.
  - **Round 4 — a SECOND cross-family peer round on the post-fix tree — 2 findings, both FIXED and closed.** PR-MED-001 was against my own Round 3 fix: `_scan_text` reached `exc_text` through an `elif` (so a populated cache was skipped whenever `exc_info` was present) and rendered `exc_info[1]`'s own `__traceback__` rather than the exact tuple the formatter prints. Both are corrected and both pre-fix states were reproduced by test before fixing. PR-MED-002 was the adversarial instrument again: `dose_change` on `0`/`0.5`, `name_substitution` on a patient already named Wilson, and `fabricated_fact` on a transcript equal to `_FABRICATED_TEXT` all returned faithful output without raising. Fixed at the `_mutate` choke point AND in the mutators — a probe established that the choke-point guard carries the safety invariant for any future mutator while the mutator changes recover genuine mutability (`0.5` → `0.10`), so neither is redundant.
  - **Round 5 — a THIRD cross-family peer round — 2 findings, both verified then fixed. Read this one, because it is the interesting one.** Both findings were the third instance of a class already fixed twice: `_scan_text` selecting less than the formatter renders (rounds 3, 4, 5) and a mock behaviour serializing differently without producing its failure class (rounds 1, 4, 5). Every earlier fix closed the named instance and left the class open, which is why the next peer found the next instance. **Round 5 fixed the classes:**
    - `logging_setup._scan_text` now COPIES `logging.Formatter.format`'s three predicates rather than re-deriving them (`if record.exc_info:` / `if record.exc_text:` / `if record.stack_info:`). The completeness claim and, more importantly, its two preconditions are in the docstring: both handlers share ONE stock formatter, and the format string interpolates only `asctime`/`levelname`/`name`/`message`. **If a later phase adds a custom formatter, a second formatter, or a `LogRecord` factory, that claim lapses and `_scan_text` must be revisited.**
    - `note.py` gained ONE semantic predicate, `_same_statement` (built on the shared `content_tokens`), used at `_fabricate`, `_substitute_name` and the `_mutate` choke point — plus a structural fingerprint backstop at the single exit of `generate_sections` that refuses any non-`faithful` result indistinguishable from `faithful`. **A behaviour Phase 5 adds inherits that guarantee automatically**; it no longer has to know this history. A probe confirmed the backstop alone catches the whole class, with the per-site predicates supplying the precise diagnosis and letting the scan continue to a valid target.
  - **Round 6 tested those two claims and falsified one — read this before trusting any completeness claim in this file.** The logging claim enumerated the interpolated format fields correctly and then drew a false conclusion from them: it asserted a superset while scanning only `message`, so a record NAMED `span_text='left knee'` passed the filter while the formatter emitted the signature. That was the FOURTH instance of one class (rounds 3, 4, 5, 6: the filter scanning less than the formatter emits), and each earlier fix had hand-extended the scan by one case. **The round-6 fix removes the hand-written list entirely:** `LOG_FORMAT` is one constant that both builds the handlers' single formatter and derives `_SCANNED_FIELDS`, so a field added to the format is scanned without anyone remembering. Its regression asserts, for EVERY derived field, that the signature is visible in the real formatter's output and dropped by the filter — so a future format change extends the test automatically. The two exclusions are `message` (covered by `getMessage()`) and `asctime` (regenerated from the clock — now asserted, not assumed). Remaining preconditions, pinned by test rather than prose: one stock shared `logging.Formatter` built from `LOG_FORMAT`. A custom formatter, a second format string, a `LogRecord` factory, or a propagating parent breaks the claim.
  - **The peer also corrected my reasoning about the mock's `invented_*` behaviours, and the correction matters more than the finding.** I argued the class survives because the duplicate text lands in a clinician-owned section. It does not: what preserves it is COORDINATE MISMATCH — a fixed multiword assertion cites only the first transcript word, so exact reconstruction fails. A hand-authored one-word `TranscriptWord` holding the whole phrase would defeat my version. Recorded on Task 5.0, because it dictates the shape of every Axis-B postcondition.
  - **OPEN BY DECISION, NOT OVERSIGHT: `MockNoteModelProvider` still proves difference, not class.** Round 6's PR-MED-001 is real and was **deferred to Phase 5 Task 5.0 by operator decision** — it is test-only, and its correct specification depends on the Axis-B behaviour set Phase 5 defines (the peer's own point that the fingerprint omits `speaker` is a requirement that cannot exist until those behaviours do). Three attempts across rounds 1, 4 and 5 each landed narrower than the class. **Task 5.0 carries the full provenance — both peer probe results, the `speaker` gap, the coordinate-mismatch correction, and the four-round history. Read it before writing Axis-B behaviours, not after.**
  - **`MockNoteModelProvider` had failed the same way three times before this.** The invariant is pinned by a matrix that is now 12 behaviours × 8 fixtures, with a statement-level oracle written independently in the test file so a bug in the provider's own comparator cannot hide itself.
  - **Repo residue, a USER action item — not fixable from any agent shell here:** the codex peer left `desktop/.pytest-tmp-peer-round4/` and `desktop/tmpjsi6ocul/` in the tree. No agent shell on this host can read or delete them (`takeown` and `icacls` both denied), git cannot open them so they never appear in `git status`'s untracked list, and they are why `ruff check .` warns twice before passing. **Delete them from a normal terminal before any blanket `git add`.**
  - One deliberate omission to note rather than hide: `/review-loop` asks for a per-round `ROLE: round` line in the run's loop log, but `scripts/loop-journal.py` has no `ROLE:round` emit token (only `ROLE:start` / `ROLE:end`), and hand-writing into the composer-owned probe log is exactly what that helper exists to prevent. The round data is in `Review History` above instead.
  - **Read the per-task "Done" blocks under Tasks 1.1–1.5 before touching this code** — they record the decisions taken against real code (why the digest match is `write_note`'s job and not the type's, why `role_unconfirmed` is deliberately left reachable, why four extra tripwire signatures were needed, why the `session_store`→`note` import is call-time).
  - **Carried into later tasks, do not lose:**
    - Tasks 4.1 / 5.2 must upgrade `test_normalisation_has_exactly_one_implementation` from a source scan to a real call-site pin.
    - Tasks 5.1 / 5.2 / 5.4 extend `NOTE_WARNING_SEVERITY` with their own codes; they never re-grade a registered one.
    - Task 5.1 must rebuild spans with `note.reconstruct_span_text()` — the same function both providers use — or "exact reconstruction" fails on whitespace alone.
    - Task 6.2's `write_note` still owes: refuse on unresolved `error`, and verify `shown_text_digest` against the assertion's text (construction checks presence, not the match, on purpose).
    - The `ExtractiveNoteProvider` cue lists are a first cut authored against fixture transcripts, NOT clinical evidence. Task 6.4 judges them on a real transcript; Task 9.1's shipping gate binds that judgment to copy enablement.
- Last completed step: Phase 1 — Foundations, types, providers, custody (Tasks 1.1–1.5): built in one `/execute` run, hardened by `/review-loop` (2 rounds), then FOUR cross-family peer rounds — 3, 4, 5 and 6 — each verified by this seat before any fix. All six rounds are Closed with Review History lines carrying verified severities. Seven findings applied; ONE (round 6 PR-MED-001, the mock provider's class-vs-difference gap) deferred to Phase 5 Task 5.0 by operator decision.
- Retained follow-up carried out of Phase 1: **Phase 5 Task 5.0** — the only open item from six review rounds, and it is open by decision rather than oversight.
- Current in-progress step: None
- Immediate next action: Task 2.1 (per-segment cepstral mean normalisation in `_segment_embedding`, `transcription.py:507-543`). Note that Task 2.3 needs **several labelled human recordings including a three-speaker one**, which only the practitioner can supply — check that before starting 2.3, and D-S1 cannot be decided without 2.3's numbers.
- Open blockers / open questions: None from Phase 1. Task 1.0 closed 2026-08-04 — both clinics share one template, the canonical set is reconciled to 17 sections, and the consent checkbox is recorded as never-written
- Peer review: cross-family plan peer review by codex `gpt-5.6-sol`, 2026-08-04 — 10 findings (1 CRIT / 7 HIGH / 2 MED), all build-affecting, all accepted and folded in. Deliberately NOT logged to the `Review Findings Log`: plan critique must never reach `/fix`. Summary of what changed:
  - **CRIT** — provenance proves attribution, not truth. Autofill reversed from auto-insert to proposal; per-assertion confirmation now binds both accelerators.
  - Error warnings gained teeth (block write / copy / Complete).
  - Pipeline reordered: compose all spans → confirm → check → write. Previously confirmed spans were written having never been checked.
  - Grounding for `transcript` spans moved from lexical containment to exact coordinate reconstruction; the high-risk classes re-aimed at clinician-authored spans as *contradiction* checks.
  - `complete_session` note policy reversed from asymmetric-delete to fail-closed — the original rationale was self-defeating.
  - Role heuristic demoted to preselection with mandatory confirmation and a real UI control (Task 7.5).
  - Controller-owned `generating` lease replaces UI-only guards (`start()` retires a queued session).
  - Added `template_profile_id`, an expected-output fixture oracle, an uncertainty global property, and a shipping gate separate from the completion gate.
- Peer review round 2: cross-family, codex `gpt-5.6-sol`, 2026-08-04 — verified the round-1 fixes (4 closed / 6 partially closed / 0 not closed) and returned 10 new findings (1 CRIT / 7 HIGH / 2 MED), all build-affecting, all accepted and folded in. Its diagnosis of the six partials is worth keeping: *the plan stated the desired invariant but omitted the state, artifact fields, transition, or canonical enforcement point needed to make it mechanically testable.* What changed:
  - **CRIT** — coordinate reconstruction is span-LOCAL and does not compose. Two individually valid spans concatenate into an unsupported assertion. `NoteAssertion` is now the unit a section holds, carrying exactly one contiguous interval, making multi-interval assembly unrepresentable rather than checked.
  - **Retracted an over-claim**: an earlier draft said the negation check *also* caught the round-1 exercise-programme case. It does not — "I didn't follow the exercise programme" and "reviewed and progressed" are not contradictory. Confirmation is the only control there, and the plan now says so.
  - Confirmation became artifact evidence (`proposal_id`, `shown_text_digest`, `ConfirmationDecision`) verified inside `write_note`, not a caller convention.
  - Every blocking state gained a tasked exit (acknowledge / retract-and-refinalise / delete-note-and-complete); `mapping_drop` downgraded to review with an "Unmapped content" target, since as an error it was unclearable.
  - Role and template-profile controls moved to the Transcript screen — on the Note tab they depended on the output they must precede.
  - Contradiction checks restricted to structured assertions with a matched entity anchor; unstructured assertions are explicitly carried by confirmation alone.
  - The generation lease became a token spanning the GUI handoff, covering recovered sessions that bypass `SessionController`.
  - Added Tasks 4.0 (atomic-assertion authoring), 7.6 (transcript visible through review), 9.1 (shipping gate binding copy enablement); reconciled three stale references.
- Hardening stopped here by decision, not by convergence: round 2's findings were mostly under-specification rather than wrong design, and the remaining detail is better resolved against real code than in another planning round.
- Last plan sync: 2026-08-04

## Review History
Each /review invocation appends a one-line entry here. Round NUMBERS
are never allocated by counting this section's entries — allocation
follows /review's **Detect review round** rule (the canonical
definition: the `Review Findings Log`'s round headers, with a legacy
highest-History-round fallback when the Log has no headers; every
findings writer follows it). Ignore the placeholder line when reading
this section.

- 2026-08-04 round 1: 0 CRIT / 0 HIGH / 2 MED / 3 LOW; skew=none; action=none
- 2026-08-04 round 2: 0 CRIT / 0 HIGH / 0 MED / 0 LOW; skew=none; action=none
- 2026-08-04 round 3: 0 CRIT / 0 HIGH / 1 MED / 0 LOW; skew=pre-existing; action=none (cross-family peer, codex `gpt-5.6-sol`. SEVERITY DRIFT, recorded not smoothed: the peer filed PR-HIGH-001 as **HIGH**/Fix-now; leg-1 executor verification confirmed the mechanism but set verified severity **med**, on the evidence that no exception-logging call site exists in shipping code. Counts above are the VERIFIED severities — Round 3's own `Findings:` line carries the peer's original HIGH, and the two are meant to differ. `skew=pre-existing` is the origin class and is not a comment on that drift: the defective scan surface is unchanged Step-4 code that Phase 3A never touched — Task 1.4 only appended signature strings. Operator disposed Fix now; applied and closed in the fix leg.)
- 2026-08-04 round 4: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=mixed; action=none (cross-family peer, codex. UPDATED IN PLACE by the seat closing the round — the peer wrote this line while the round was still Open, carrying its own counts; a second line would have been the contradictory-duplicate the checker exists to catch. Counts are now the VERIFIED severities: PR-MED-002 confirmed **med**, PR-MED-001 verified **low** against the peer's MED, on reachability — it additionally needs a divergent `exc_text` or hand-built tuple on top of an exception-logging call site, of which shipping code still has none. Both were disposed **Fix now** regardless of severity and both are Applied; the round's own `Findings:` line keeps the peer's original labels. `skew=mixed` is retained and correct: PR-MED-001 is ⚡ fix-induced against Round 3's new code — an INCOMPLETE fix, not a regression, since nothing was scanned beyond the message before it — while PR-MED-002 is 🔁 same-family with Round 1's MED-002, a no-op-mutation pattern sibling my Round 1 sweep missed.)
- 2026-08-04 round 5: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=same-family; action=strengthen-siblings (cross-family peer, codex. Both findings VERIFIED against the code before any fix, per this leg's verify-then-fix gate; neither was invalid, so both were fixed. No severity drift — I agree with the peer's MED and LOW. `skew=same-family` and `action=strengthen-siblings` are the honest classification of the round's real lesson: these are the THIRD instance each of two classes already fixed twice — `_scan_text` selection narrower than the formatter's (rounds 3, 4, 5) and a mock behaviour that serializes differently without producing its failure class (rounds 1, 4, 5). Each earlier fix closed the named instance and left the class open. This leg fixed the class in both: predicate PARITY copied from `logging.Formatter.format` with its two preconditions written down, and one semantic `_same_statement` predicate plus a structural fingerprint backstop at the single exit of `generate_sections`. A probe showed the backstop alone already catches the whole mock class, including for behaviours not yet written.)
- 2026-08-04 round 6: 0 CRIT / 0 HIGH / 1 MED / 1 LOW; skew=same-family; action=strengthen-siblings (cross-family peer, codex. It tested round 5's two completeness claims and falsified one: the logging claim enumerated the interpolated format fields correctly but scanned only `message`, so a record NAMED `span_text='left knee'` passed the filter while the formatter emitted it — the FOURTH instance of "the filter scans less than the formatter emits". Fixed as a class this time: the scanned-field list is DERIVED from `LOG_FORMAT` rather than hand-written, so it cannot drift again. **SPLIT DISPOSITION by the operator:** PR-LOW-001 Applied; PR-MED-001 **Deferred to Phase 5** as Task 5.0 with full provenance — it is test-only and its correct specification depends on the Axis-B behaviour set Phase 5 defines, and three attempts had each landed narrower than the class. No severity drift: I agree with the peer's MED and LOW. The mock class is therefore OPEN by decision, not by oversight, and its history — rounds 1, 4, 5, 6 — is recorded on Task 5.0.)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
Each /review invocation appends a detailed findings block here, with
/fix updating per-finding Decision and Notes as it processes each one.

### Round 1 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5)
- Source: Claude Code
- Round status: Closed
- Compacted 5 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)
  - MED-001: `note.py` `is_interrogative()` — an auxiliary-verb opener makes every imperative a "question", so real clinician advice is silently dropped — decision: Applied
  - MED-002: `note.py` `MockNoteModelProvider._flip_laterality` — the laterality mutation silently no-ops on a capitalised token — decision: Applied
  - LOW-001: `note.py` `MockNoteModelProvider` — `over_omission` on a single-utterance fixture silently equals `faithful` — decision: Applied
  - LOW-002: `note.py` `MockNoteModelProvider._mutate` — only the FIRST assertion is inspected, while the error says "in the transcript" — decision: Applied
  - LOW-003: `note.py` `MAX_ASSERTION_CHARS = 4000` — an unusually long single VAD segment makes the shipping provider raise a raw pydantic `ValidationError` in... — decision: Applied

### Round 2 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5), post-fix
- Source: Claude Code
- Round status: Closed
- Compacted 0 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)

### Round 3 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5), independent cross-family peer review
- Source: Codex peer-review
- Round status: Closed
- Compacted 1 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)
  - PR-HIGH-001: `desktop/src/scribe_desktop/logging_setup.py:145` — tripwire ignores exception and stack rendering, so a note-validation traceback can persist clin... — decision: Applied

### Round 4 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5), post-round-3-fix independent cross-family peer review
- Source: Codex peer-review
- Round status: Closed
- Compacted 2 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)
  - PR-MED-001: `desktop/src/scribe_desktop/logging_setup.py:190` — `_scan_text` can miss the exception text the production formatter actually emits — decision: Applied
  - PR-MED-002: `desktop/src/scribe_desktop/note.py:982` — non-faithful mock behaviours can silently collapse to `faithful` — decision: Applied

### Round 5 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5), post-round-4-fix independent cross-family peer review
- Source: Codex peer-review
- Round status: Closed
- Compacted 2 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)
  - PR-MED-001: `desktop/src/scribe_desktop/note.py:1030` — byte-different mock output can still fail to produce its named adversarial behaviour — decision: Applied
  - PR-LOW-001: `desktop/src/scribe_desktop/logging_setup.py:197` — `_scan_text` still selects fewer `exc_info` states than the production formatter — decision: Applied

### Round 6 — 2026-08-04 — Phase 1 (Tasks 1.1–1.5), post-round-5-fix independent cross-family peer review
- Source: Codex peer-review
- Round status: Closed
- Compacted 2 finding(s) → `findings-phase3a-note-pipeline.md` (full round block moved verbatim; this plan and that file are ONE lifecycle unit — move, archive or delete them together)
  - PR-MED-001: `desktop/src/scribe_desktop/note.py:1016` — the structural fingerprint proves difference, not the requested adversarial failure class — decision: Deferred (operator, to Phase 5)
  - PR-LOW-001: `desktop/src/scribe_desktop/logging_setup.py:211` — `_scan_text` still omits fields emitted by the configured formatter — decision: Applied

## Tasks

### Phase 1 — Foundations, types, providers, custody
- [x] 🟩 1.0: Capture both clinics' real Cliniko treatment-note template section lists, and confirm whether they are identical. **Precedes the schema constant** — the canonical set is only defensible as a superset once both real templates have been seen.

  **Template A — captured 2026-08-04** (three groups, six text fields, one checkbox):

  | Group | Field | Type |
  |---|---|---|
  | History | Presenting complaint/patient progress | rich text (HTML) |
  | Examination | Assessment | plain text |
  | Examination | Informed Consent | **checkbox — never written by this app** (see Critical Constraints) |
  | Examination | Diagnosis | plain text |
  | Treatment/Management | Treatment | plain text |
  | Treatment/Management | Response to treatment | plain text |
  | Treatment/Management | Management/Advice | plain text |

  Three findings this capture forces, all to be resolved when the second template arrives:
  - **The canonical schema is missing interval history.** "Presenting complaint/**patient progress**" carries progress-since-last-appointment, which is distinct from presenting complaint (canonical 1) and from response to treatment (canonical 10 — within-session). On a return-visit-heavy caseload this is the highest-volume field in the template, and nothing currently maps to it. Add a canonical section.
  - **The mapping model must express more than `{canonical_key: target_field}`.** Targets carry a group, a content type (HTML vs plain — never emit formatting into a plain field), and in one case a non-text type that is explicitly unmappable.
  - **Six-into-seventeen is heavily many-to-one.** Four canonical sections had no natural target; resolved 2026-08-04 by folding three into existing fields and marking `consent` intentionally unmapped (see `Schema / Data Changes`). The round-2 "Unmapped content" target therefore has no consumer under Template A — keep it, since a future practitioner's mapping will leave genuine gaps, but it is not exercised by this template.

  - **Confirmed 2026-08-04: both clinics use this same template, and Management/Advice is the last field.** So there is exactly ONE mapping profile today. The per-practitioner mapping layer stays — it is the commercial requirement, for future practitioners with different templates — but `template_profile_id` resolves to the sole profile automatically. Do NOT make the clinician choose a profile from a list of one; surface a chooser only when more than one exists.
  - **Done 2026-08-04.** The template is recorded, the canonical set is reconciled (17 sections with stable keys, `progress_since_last_visit` added, listed in `Schema / Data Changes`), every key carries its meaning, ownership and target, and the unmapped-content question is resolved. Carried to Task 3.1: practitioner confirmation of the two non-obvious mapping calls (`outcome_measures` → Assessment; `referrals_investigations` / `follow_up_review` → Management/Advice).
- [x] 🟩 1.1: Note types in `note.py` — `NoteAssertion`, `NoteSpan`, `NoteProposal`, `ConfirmationDecision`, `GeneratedSection`, `NoteWarning`, `GeneratedNote`, `NoteRequest`, `NoteModelProvider` Protocol, and the canonical 17-section constant (listed in `Schema / Data Changes`). Frozen pydantic, `extra="forbid"`, mirroring `TranscriptDocument` (`transcription.py:252-292`). Reuse `SESSION_ID_PATTERN`.
  - **`NoteAssertion` is the unit `GeneratedSection` holds** — not `NoteSpan`. A `transcript` assertion holds exactly one span with one contiguous `source_coords = (segment_index, first_word_index, last_word_index)`; the type makes multi-interval assembly unrepresentable rather than merely checked.
  - A non-`transcript` assertion carries `proposal_id`, `shown_text_digest`, `config_digest`, and a `ConfirmationDecision(decision, timestamp)`. `NoteProposal` is structurally distinct from `NoteAssertion`, so an unconfirmed proposal cannot be written by construction.
  - `GeneratedNote` additionally carries `session_id` (bound, `SESSION_ID_PATTERN`), `template_profile_id`, the confirmed cluster→role assignment, `transcript_digest`, and `config_digest`. **Define `transcript_digest` precisely**: algorithm, version tag, and exact byte domain — the decrypted canonical `TranscriptDocument.to_bytes()` output, not ciphertext — computed in one place and verified identically by `read_note` and `complete_session`.
  - Done when: types import cleanly, mypy strict passes, a round-trip test passes, and tests assert that a `NoteProposal` cannot be placed in a `GeneratedSection`, that a `transcript` assertion spanning two intervals is unrepresentable, and that a non-`transcript` assertion without a `ConfirmationDecision` is rejected at construction.
  - **Done 2026-08-04.** `desktop/src/scribe_desktop/note.py`. All three structural rejections are pinned in `tests/test_note.py`. Decisions taken against the code, recorded so later phases inherit them rather than re-litigate:
    - `NoteAssertion.note_span` is ONE `NoteSpan`, and `SourceCoords` is a 3-field `NamedTuple` (not a model), so two intervals fail validation at construction — no list of spans, no list of coordinate triples.
    - Construction requires the confirmation record's PRESENCE, its `confirmed` value, and a matching `proposal_id`, but deliberately does NOT recompute `shown_text_digest` against the text: that verification is `write_note`'s (Task 6.2), and making it unrepresentable here would leave 6.2's defence-in-depth check untestable.
    - `role_unconfirmed` is likewise left to Check 3, not enforced by the type: a clinician-owned section populated with no confirmed role must stay REACHABLE so 5.3 can fire on it.
    - `transcript_digest` = `sha256-v1:<hex>` over the decrypted canonical `TranscriptDocument.to_bytes()`. `digest_bytes()` is the single primitive; `complete_session` digests the transcript plaintext it already holds, so nothing re-serialises.
    - `NoteWarning` carries `note_warning_code` + `severity` validated against `NOTE_WARNING_SEVERITY`, so a check cannot re-grade `mapping_drop` to error later. Codes registered now are Check 3's five; Tasks 5.1/5.2/5.4 EXTEND the registry.
    - `reconstruct_span_text()` is the canonical word-range→text rule (strip each word, join with single spaces) — Whisper's leading spaces would otherwise make "exact reconstruction" fail on whitespace alone in Task 5.1.
- [x] 🟩 1.2: `normalise_token()` / `content_tokens()` in `note.py` — the single normalisation source (see the shared-helpers inventory). Build on `_STRIP_PUNCT_RE` (`transcription.py:203`).
  - Done when: a test pins that autofill matching and checker tokenisation call the same function.
  - **Done 2026-08-04.** `note.py` imports `transcription._STRIP_PUNCT_RE` rather than restating the rule. `content_tokens` drops punctuation-only tokens and pure disfluencies but KEEPS negation and hedging — dropping "not"/"never" would make a negated claim and its opposite tokenise identically, defeating Check 2 before it is written.
  - The Done-when is pinned as far as today's code allows: 4.1 and 5.2 do not exist yet, so `test_normalisation_has_exactly_one_implementation` asserts by source scan that `def normalise_token` occurs exactly once in `src/` and `_STRIP_PUNCT_RE` has exactly one owner plus one consumer. **Tasks 4.1 and 5.2 must upgrade this to a call-site pin** once there are call sites.
- [x] 🟩 1.3: Both providers in `note.py` — `ExtractiveNoteProvider` (verbatim transcript spans, cue-matched to sections, role-aware once 2.2 lands) and `MockNoteModelProvider(behaviour=...)` with the Axis B behaviours. Ship in `src/`, following `MockSpeechProvider` (`speech.py:115`).
  - Done when: both satisfy the Protocol and `MockNoteModelProvider` produces each Axis B behaviour deterministically.
  - **Done 2026-08-04.** 13 Axis B behaviours (`MOCK_BEHAVIOURS`), each a pure function of the request. A behaviour whose failure class the fixture cannot express (no laterality / number / negation / name token) raises `NoteProviderError` instead of silently degrading into a different, quietly-passing class — that would let a Phase 5 cell go green on the wrong evidence.
  - `ExtractiveNoteProvider` routes whole utterances by cue into the first matching canonical section, so every assertion is one contiguous interval that reconstructs exactly. The Critical-Constraint role gate is enforced NOW (clinician-owned sections take only confirmed-clinician, non-interrogative utterances); 2.2 supplies the preselection heuristic behind `clinician_speaker`, not the gate.
  - Protocol conformance is proved statically inside `note.py` under `if TYPE_CHECKING`, because mypy is configured over `src` only — a test-side annotation would prove nothing.
  - Cue lists are a first cut authored against the fixture transcripts, not clinical evidence. Task 6.4's real-transcript run is what decides whether they are usable, and Task 9.1's shipping gate is what binds that judgment to copy enablement.
- [x] 🟩 1.4: Tripwire signatures in `logging_setup.py:57-87` — `note_sections`, `note_spans`, `note_warnings`, `span_text`, `note_excerpt`, `transcript_utterances`, quoted and unquoted. Test over `repr` and `model_dump_json` of every note model **including `NoteRequest`**.
  - Done when: each model's lone repr is dropped by the filter.
  - **Done 2026-08-04.** All six mandated names registered in quoted and unquoted form, plus four more the audit forced: `note_assertions`, `note_span` (singular — the actual `NoteAssertion` field; `note_spans=` would not match it), `note_warning_code`, and `note_confirmation`. Without those, a lone `GeneratedSection`, `NoteAssertion`, `NoteWarning` or `ConfirmationDecision` repr — and their JSON, which no class-name signature could catch — passed the filter. `NoteUtterance` needs nothing new: it holds `TranscriptWord`s under the already-registered `transcript_words`.
  - Coverage keys on FIELD NAMES, so an empty `GeneratedSection` is dropped too; the test asserts exactly `2 x len(models)` drops over repr and JSON of all nine note models.
  - **Amended 2026-08-04 (peer round 3, PR-HIGH-001, operator-approved scope expansion beyond this task's declared `:57-87`):** registering signatures is only half a tripwire — the filter has to SEE the text. `PayloadTripwireFilter` scanned `record.getMessage()` alone, and handler filters run before the formatter appends `exc_info`/`stack_info`, so a traceback could carry these very signatures past it. The scan surface now covers message + exception + stack. See Round 3's `/fix notes`.
- [x] 🟩 1.5: `NOTE_FILENAME` and the `complete_session` custody fix in `session_store.py`. If `note.enc` exists: fsync + verify-decrypt + parse + session-binding + `transcript_digest` match, all before `delete_session_key`. **Fails closed, symmetric with the transcript** — any failure retains the key and Complete does not proceed. Retaining custody is precisely what keeps regeneration possible; deleting the note and completing would delete the key too, making the transcript unreadable and regeneration impossible.
  - The clinician's exits are **Regenerate note** or an explicit, confirmed choice to delete the note and complete without one — never a silent deletion.
  - Done when: the 56-function custody suite passes unchanged, plus tests for note-absent, note-valid, note-corrupt-ciphertext, note-authenticated-but-malformed, note-wrong-session, note-digest-mismatch, and unlink-failure — each asserting the key is retained.
  - **Done 2026-08-04.** All seven cases plus two the case list did not name: audio-header-vs-directory binding precedence, and unresolvable session identity. Existing custody tests pass unchanged.
    - Two helpers landed beside it: `_resolve_session_identity()` (audio header authoritative, directory name as fallback, **fail closed** when neither yields a well-formed id) and `_verify_note_for_completion()`.
    - `complete_session` gained `delete_note: bool = False` — the clinician's explicit "complete without a note" exit. It unlinks FIRST and a failed unlink aborts with the key retained, so Complete can never proceed over a note still on disk. Default False, so every existing caller is unchanged.
    - `session_store` now imports `note` at CALL time inside `_verify_note_for_completion`. Not a cycle: `note.py` imports `session_store` at module load for `SESSION_ID_PATTERN`/`atomic_write_bytes`, so the dependency is one-way at import time by construction.

### Phase 2 — Speaker roles and diarization measurement
- [ ] 🟥 2.1: Per-segment cepstral mean normalisation in `_segment_embedding` (`transcription.py:507-543`), to remove the gain nuisance that makes one loud and one quiet speaker separable as two clusters.
  - Done when: existing diarization tests pass and a new test shows a gain-shifted copy of a segment clusters with its original.
- [ ] 🟥 2.2: `speaker_role()` — **preselect** which cluster is the clinician from talk-time share, question-asking rate, and first-speaker order. The result is a default for the mandatory confirmation in Task 7.5, never an authority. The clinician-owned sections (`assessment`, `diagnosis`, `advice_home_exercise`, `management_plan`) populate only from confirmed-clinician utterances; unresolved or merged clustering leaves them blank with candidate quotations surfaced instead.
  - A clinician's *question* is not a diagnosis: cue matching into clinician-owned sections must exclude interrogative forms.
  - Done when: role preselection is a pure function with fixture tests; a test asserts clinician-owned sections stay empty when the role is unconfirmed; and a test asserts an interrogative clinician utterance does not populate `diagnosis`.
- [ ] 🟥 2.3: Measure role and 2-way cluster accuracy on **several labelled human recordings** (not one), before and after 2.1, including at least one three-speaker recording. Record the numbers in this plan.
  - Done when: the measurements are recorded and D-S1 can be decided on evidence rather than a single sample.
- [ ] 🟥 D-S1: Estimated-k speaker counting — adopt or defer.  `[decision]`
  - Options: (a) implement k-selection over k ∈ {1..4}; (b) keep k=2 and defer estimated-k to the ONNX embedding upgrade
  - Decide after: Task 2.3's measured 2-way accuracy
  - Blocks: nothing in this plan — the extractive provider and the checker work under either outcome
  - If (a): cap k at n−1 (`_kmeans_two:553` raises `ValueError` otherwise), handle silhouette being undefined at k=1 with an explicit threshold rule, guard NaN from duplicate points (`argmax` selects NaN as maximum; `test_transcription.py:414-419` already feeds duplicates), update **all four** guard sites, and replace `:585-586`'s binary labelling with first-appearance ordering.

### Phase 3 — Config engine
- [ ] 🟥 3.1: Build the per-clinic mapping fixtures from the template lists captured in Task 1.0, plus the `template_profile_id` selector: a session is bound to exactly one profile, chosen manually (real encounter context does not arrive until Phase 5 — `session.py:124`), persisted on `GeneratedNote`, and visible in the UI.
  - Done when: each clinic's canonical→target mapping is expressed and tested, a session cannot generate a note without a bound profile, and a mapping that would drop a populated canonical section warns rather than silently discarding.
- [ ] 🟥 3.2: `note_config.py` — frozen models plus a validating loader for template mapping, autofill rules, and prefill templates. Specify and implement resolution precedence, first-run, and upgrade behaviour (see `Config / Environment / Deployment Impact`). Validation is declarative where possible: `ConfigDict(extra="forbid", frozen=True)`, `Field(max_length=...)`, one validator for control characters, one for duplicate triggers. Mirror `read_transcript`'s error shape (`transcription.py:788-802`).
  - Done when: malformed config fails loudly with a typed error and never partially applies; `config_digest` is well-defined.
- [ ] 🟥 3.3: Shipped default config plus `package-data` in `desktop/pyproject.toml`.
  - Done when: defaults load in a non-editable install.

### Phase 4 — Autofill and prefill
- [ ] 🟥 4.0: **Atomic-assertion authoring in the config schema.** Autofill expansions and prefill seeds are authored as explicit LISTS of atomic assertions in the config file — never as prose that gets split at runtime. Runtime decomposition of clinical prose would itself be an unverified inference, and it is the one place where "per assertion" could silently become "per blob". `note_config.py`'s validator rejects a non-list expansion.
  - Done when: a config declaring a multi-claim expansion as a single string fails validation with a message naming the fix.
- [ ] 🟥 4.1: `note_fill.py` autofill — match trigger phrases against `TranscriptWord` sequences via `normalise_token`, emitting one **`NoteProposal` per atomic assertion** in the matched rule's expansion list, each carrying the rule id, the trigger's start time, and its exact text. Never an assertion, never one proposal for a multi-claim expansion.
  - Done when: a rule whose trigger is absent cannot fire; a three-assertion expansion yields three proposals; and a test asserts that a trigger spoken by the **patient** still only produces proposals, never an insertion — the round-1 CRIT's failure case, pinned.
- [ ] 🟥 4.2: `note_fill.py` prefill — body-region detection from transcript keywords, clinician-overridable, emitting one `NoteProposal` per atomic assertion in the selected seed.
  - Done when: proposals are structurally distinct from assertions and cannot reach `note.enc` unconfirmed; and a multi-assertion seed yields one proposal per claim, pinned by test.

### Phase 5 — Checking stage and the adversarial matrix
- [ ] 🟥 5.0: **Make every `MockNoteModelProvider` behaviour prove it produced its NAMED Axis-B class.** Carried from Phase 1 peer round 6 (PR-MED-001), deferred here by operator decision 2026-08-04 — the fix is test-only and its correct specification depends on the Axis-B behaviour set THIS phase defines, so writing it in Phase 1 would have been a fourth guess. **Do this while defining the Axis B behaviours, not after.** Everything needed is recorded here; do not re-derive it.
  - **The invariant wanted:** every non-`faithful` behaviour either produces its SPECIFICALLY NAMED failure class, or raises `NoteProviderError` because the fixture cannot express that class. Output that merely differs from `faithful` is necessary but NOT sufficient. Results must also be structurally valid (re-validate through fresh pydantic construction) unless the requested class is `malformed_output`.
  - **Why the existing single-exit fingerprint is insufficient:** `MockNoteModelProvider._fingerprint` compares (section_key, content tokens, source_coords) against the faithful result and raises when they match. That proves DIFFERENCE, not CLASS — a cell can return a different result for the wrong reason, exercise the wrong checker or none, and still look like valid evidence that the named class was generated.
  - **Two concrete peer probes, reproduced against the current code — use them as the first two regressions:**
    - `obeys_injection` returned a management-plan assertion for an ordinary clinician examination containing NO injected instruction. Different from faithful, wrong class.
    - `negation_flip` returned `span_text=''`, which fails fresh `NoteSpan` validation. Different from faithful, structurally invalid.
  - **The fingerprint omits `speaker`.** A future speaker-attribution behaviour (misattributing an utterance to the wrong cluster — a real Axis-B class for this phase) would be wrongly REJECTED as indistinguishable from faithful. Either project `speaker` into the generic fingerprint or register such behaviours with their own oracle.
  - **A correction to the Phase-1 executor's reasoning that matters for how postconditions are written.** Phase 1 argued that an `invented_*` behaviour whose fixed text duplicates transcript content still produces its class "because it lands in a clinician-owned section". The peer showed that is not what preserves the class: what actually does is COORDINATE MISMATCH — the fixed multiword assertion cites only the first transcript word, so exact reconstruction fails. A hand-authored one-word `TranscriptWord` holding the whole phrase would defeat that reasoning entirely. **Do not rely on section ownership as the proof; write a behaviour-specific postcondition asserting the class directly.** That is the sound form for all of them.
  - **This class has now recurred in rounds 1, 4, 5 and 6** (laterality case-sensitivity → zero-doses and `Wilson` → punctuation/case cosmetics → wrong-class/invalid output). Every previous fix closed the named instances and left the class open. A per-behaviour postcondition asserted by an independent oracle is the shape that ends it; a generic difference check is the shape that has not.
  - Done when: each behaviour has a named postcondition asserted by an oracle written independently of the provider's own comparator; a deliberately-added speaker-only test behaviour is handled correctly; every non-`malformed_output` result round-trips through fresh pydantic validation; and the two probes above are regressions.
- [ ] 🟥 5.1: `note_check.py` Check 1 — **coordinate reconstruction** over `transcript` assertions: rebuild each from its single contiguous `source_coords` against the immutable transcript and compare exactly. Any mismatch is an error; multi-interval assembly is unrepresentable by Task 1.1's types, so it needs no check. No lexical allowlist in 3A; the containment variant is 3B's, added alongside `model` provenance.
  - Emit a `review` warning for every *included* source word whose `probability < UNCERTAINTY_THRESHOLD`, reached through the coordinates.
  - **Scope honestly:** this reaches only words the note included. A low-confidence clinically material phrase that cue routing OMITTED is reached by neither this check nor Check 4. The 3A answer is presentational, not algorithmic — Task 7.6 keeps the full uncertainty-marked transcript visible beside the note through review — and the plan claims no automated detection it does not have.
- [ ] 🟥 5.2: Check 2 — the high-risk classes as **contradiction** checks over confirmed clinician-authored assertions, and ONLY over assertions carrying explicit structure: a claim type, an entity/anatomical anchor, and a value. Compare only MATCHED entities — an unmatched pair is not a contradiction. "Right hip, left shoulder" must not fire; nor must unrelated numbers or medications co-occurring in one window.
  - Vocabulary: numbers via `is_number_token:300`, names via `is_name_like_token:312`, medications via a closed lexicon, laterality and negation via anchored comparison. Severity grades on `probability < UNCERTAINTY_THRESHOLD`, never on `uncertain`.
  - An unstructured assertion is NOT contradiction-checked; it is carried by clinician confirmation alone, and the plan says so rather than implying coverage.
  - Done when: false-positive fixtures containing multiple body regions, multiple medications, and multiple measurements in one section all produce zero contradiction errors.
- [ ] 🟥 5.3: Check 3 — provenance integrity: `unconfirmed_proposal` (error — covers autofill and prefill identically), `autofill_trigger_absent` (error), `clinician_asserted` (review, unsuppressible), `mapping_drop` (**review**, not error — content a legal mapping would discard renders into a mandatory "Unmapped content" target instead; an error here would be unclearable, since the mapping UI is read-only and regeneration recreates it), and `role_unconfirmed` (error if a clinician-owned section is populated without a confirmed role).
- [ ] 🟥 5.4: Check 4 — omission, **scoped to clinician-attributed transcript spans carrying high-risk tokens**, not every capitalised or numeric token. Unscoped it is a false-positive generator whose rate rises the better the note excludes small talk, which `PLAN.md:104` requires.
  - **Stated limit:** this is a high-risk-token heuristic, not a materiality classifier. `clinically_material_span_ids` exists in fixtures as a test oracle and has no runtime producer — so the automated claim is "high-risk clinician-spoken content is either carried or flagged", never the broader "no clinically material omission". Task 7.6 carries the rest presentationally.
  - Done when: a small-talk-heavy fixture produces no omission warnings for patient-side chat.
- [ ] 🟥 5.5: The adversarial matrix, its expected-output oracle, and the eight global properties (see `Validation / Verification`).
  - Done when: all eight properties hold and the matrix runs in CI with no ML dependency.

### Phase 6 — Pipeline and controller plumbing
- [ ] 🟥 6.1: The two-stage pipeline in `note.py`, matching Flow 1's ordering exactly. `compose_draft()` takes a resolved provider plus the config-resolved rules and returns the base note **plus proposals**, running no checks. `finalise_note()` takes the confirmed proposals **with their `ConfirmationDecision` records**, composes assertions, then runs **every** check and assembles `GeneratedNote`. Checks never run before confirmation, and confirmation evidence rides the artifact rather than the call.
  - Done when: `finalise_note()` refuses a note containing an unconfirmed proposal; refuses a non-`transcript` assertion whose `shown_text_digest` does not match the text actually confirmed; and confirmed clinician-authored assertions pass through Checks 2 and 3.
- [ ] 🟥 6.2: `write_note`/`read_note` mirroring `write_transcript`/`read_transcript`, over `atomic_write_bytes`, no AAD. Unlink a stale `note.enc` before `write_transcript` writes, so re-transcription cannot leave a note describing a superseded transcript.
  - **`write_note` enforces the invariants itself**, as defense in depth rather than trusting the UI: it refuses on any unresolved `error`, and it verifies every non-`transcript` assertion against its `ConfirmationDecision` and `shown_text_digest`, refusing an unbacked one.
  - `read_note` verifies `session_id` binding and `transcript_digest` using the single definition from Task 1.1 — the same code path `complete_session` uses.
- [ ] 🟥 6.3: **A controller-owned `generating` lease**, not UI guards alone. Prefer a controller operation that performs scoped artifact access over exposing raw directory/crypto accessors. While the lease is held, block `start()`, `complete()`, `discard()`, session retirement, and recovered-key destruction. Add the lease to `SessionControllerLike` and `FakeController`.
  - The UI-guard-only design was insufficient: `start()` (`session.py:285-290`) calls `_retire_locked` (`:554`) on a **queued** session, dropping the in-memory handle a generation worker depends on — and `SessionController` documents any-thread safety, so a UI button state cannot be the guard.
  - **The lease is a TOKEN spanning the whole operation, not the worker.** Acquire before the `TaskThread` starts; release only after the GUI-thread `write_note` succeeds or failure cleanup completes. A worker-scoped lease released on callable return leaves the custody-critical gap exactly where `write_note` runs.
  - **Recovered sessions bypass `SessionController` entirely** — `main_window.py:194-220` calls store primitives directly — so controller guards alone cannot protect them. Route live AND recovered Complete / Discard / key-destruction through one lease-aware custody coordinator.
  - Done when: tests cover `start()`-, Complete-, Discard-, and `_destroy_recovered_crypto`-during-generation on both live and recovered paths, plus a barrier test firing exactly after worker return and before `write_note`.
- [ ] 🟥 6.4: First real-transcript run through `ExtractiveNoteProvider`; record honestly how usable the output is (see the matching Accepted Assumption).

### Phase 7 — Note review UI
- [ ] 🟥 7.1: `ui/note.py` — the Note tab: sections in canonical order, provenance visibly distinguished, warnings grouped and summarised rather than listed flat (warning fatigue is the phase's top risk), and **per-assertion confirm/decline showing the exact text that will be inserted**. Blocking errors are presented distinctly from review warnings, each naming the action it blocks and the way to clear it. Assertions render on hard boundaries (one bullet each), never as assembled prose.
  - Controls this task owns: **acknowledge** a review warning, **retract** a confirmed assertion and refinalise, and the explicit **delete note and complete without one** path. Every blocking state reachable in the UI has a visible exit here.
  - Text is selectable and **copy is enabled only when the Task 9.1 shipping gate has passed** — the copy affordance is bound to that decision, not unconditional. Cleared on close.
- [ ] 🟥 7.2: `ui/transcript.py` — Generate action on a `TaskThread`, an `is_busy` property, and Complete refused while generating, while any proposal is unconfirmed, while an `error` is unresolved, or while a `review` warning is unacknowledged. **`write_note` must run in the `succeeded` handler on the GUI thread, not inside the `TaskThread` callable** — a worker-thread write can interleave with a GUI-thread Complete, which a button guard cannot prevent.
- [ ] 🟥 7.5: The **clinician-role and template-profile controls — on the TRANSCRIPT screen, not the Note tab.** Both are consumed by `compose_draft()`, so a control on the Note tab would depend on the output it must precede. Role is preselected by Task 2.2's heuristic, overridable, and shows candidate quotations from each cluster so the choice is informed. **Generate** is disabled until both are confirmed; both are persisted onto `NoteRequest` and `GeneratedNote`.
  - Done when: Generate is unreachable without both confirmations; the saved artifact records which cluster was confirmed as clinician; and a test pins that the clinician-owned sections stay empty when a note is somehow composed without a confirmed role.
- [ ] 🟥 7.6: **Keep the full uncertainty-marked transcript visible beside the note** through the whole review, until copy or Complete. This is 3A's honest answer to "all uncertainty surfaced": the checker reaches only words the note *included*, so a low-confidence clinically material phrase that cue routing omitted is invisible to every automated check. Presentational coverage is real coverage for a clinician reviewing before signing — algorithmic coverage would need a materiality classifier this phase does not have.
  - Done when: every low-`probability` transcript word is reachable in the UI at review time, pinned by an offscreen test, and the threat-model text (Task 8.1) states this is presentational rather than detected.
- [ ] 🟥 7.3: `ui/main_window.py` — register the tab, wire signals, add the note screen to the `closeEvent` busy check (`:154-158`), and clear note plaintext when a different transcript loads over a stale note. Update `tests/test_ui_screens.py:773-774`.
- [ ] 🟥 7.4: `ui/models.py` — `build_note_generator`, note and warning rendering (reuse `format_timestamp:212` for autofill attribution), and the read-only config viewer's report lines, with tests.

### Phase 8 — Documentation
- [ ] 🟥 8.1: Threat-model re-review covering this phase's surfaces — config as a note-content input, clinician-asserted content in a clinical record, the extended in-memory transcript lifetime across the review window, and the **ratified copyable-note change**. Record the checker's honest limit: in 3A, `transcript` spans are exact by coordinate reconstruction — recombination is rejected structurally, not detected — but clinician-authored spans are verified only against transcript *contradiction*, so a confirmed assertion the transcript is merely silent about is not detectable by any check. That residual is carried by per-assertion clinician confirmation and by the clinician's own review at signing (`PLAN.md:14`), and must be stated rather than implied. The `threat-model.md:161-166` note-model trigger stays deferred to 3B.
- [ ] 🟥 8.2: `data-flow-map.md` new flows and component rows; `retention-schedule.md` note-artifact and config rows.
- [ ] 🟥 8.3: `docs/design-system.md` — amend the clinical-content non-negotiable to distinguish transcript (display-only) from note (copyable), with the rationale; update the "Today two speakers only" line per D-S1's outcome.
- [ ] 🟥 8.4: `PLAN.md` reconciliation — record the 3A/3B split, the canonical schema, the mapping layer, autofill and prefill. `AGENTS.md` and `CHANGELOG.md` updates.

### Hardening stage (standard for multi-phase plans)
- [ ] 🟥 Step H: Hardening pass
  - [ ] 🟥 H1: `/review-loop` (or `/review` → `/fix`) to convergence
  - [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
  - [ ] 🟥 H3: `/security-review` — log findings; same impact-tiered routing
  - [ ] 🟥 H4: final `/review` (or cross-family `/peer-review`) re-check to confirm convergence

### Phase 9 — Gates
- [ ] 🟥 9.1: **Shipping gate.** Define the representative real-transcript set (composition and size, not "a transcript"), define the acceptability rubric, run `ExtractiveNoteProvider` across it, and record the practitioner's pass/fail decision in this plan. **Bind copy enablement in `ui/note.py` to that recorded decision** — on a fail, copy stays disabled and 3A is classified honestly as internal infrastructure until 3B lands.
  - Done when: the set and rubric are written down, the decision is recorded, and offscreen tests cover BOTH outcomes — copy enabled after a pass, copy disabled after a fail.
- [ ] 🟥 9.2: Run the completion gate in `Validation / Verification` and record the outcome here.

*No phase heading carries `[gates: high-auto-ok]`. This phase touches key custody, clinical-record content, and crypto lifecycle; HIGH findings pause for the practitioner by design.*

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
(Not applicable while plan is Active — populated at completion.)

---
*Plan saved to: .cursor/plans/plan-phase3a-note-pipeline.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
