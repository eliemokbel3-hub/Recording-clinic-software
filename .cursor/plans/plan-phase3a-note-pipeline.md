# Feature Implementation Plan
**Feature:** phase3a-note-pipeline
**Overall Progress:** `0%`

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
Turn a finished `TranscriptDocument` into a reviewable clinical note, without a language model. The app fills a canonical 16-section internal schema, maps it onto whatever Cliniko template a given practitioner uses, applies clinician-authored autofill macros and body-region prefills, and runs a mechanical checking stage that flags anything the transcript does not support. Phase 3B adds `gpt-oss-20b` behind the provider seam this phase defines.

## Planning Extraction Summary
Populate this during plan creation or plan hardening.

**Workflow Schema:** v22

**Executor tier:** entirely premium

### Agreed Scope (Build Now)
- Canonical 16-section note schema with stable keys, plus a per-practitioner template mapping layer (canonical → target field; many-to-one and omission both legal).
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
  - Recommended next action: open with D-N1 (runtime, quantisation, acceptability bar) — candidates llama-cpp-python (GGUF) and onnxruntime-genai; Ollama/llama-server rejected up front (a localhost HTTP server collides with the ruff bans on `socket`/`http`/`urllib.request` and the no-sockets test). Evidence order: wheel gate on py3.14 + py3.12 → measured peak RSS vs total RAM (~12-13 GiB weights; a 16 GB machine is probably not viable) → wall-clock for a 16-section note → quality on this phase's matrix → chat-template and `parse_special` control → SHA-pinned acquisition. Model-boundary injection defences (harmony role separation, per-call nonce delimiter, `parse_special=False`, no tool capability) land there too, plus `note_model_ready()` kept **separate** from `models_ready()`.
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
  - Why: section routing is fundamentally a who-said-it problem, and no clinician/patient distinction exists in the codebase — `speaker_1`/`speaker_2` are cluster indices whose only guarantee is that the first segment is `speaker_1` (`transcription.py:586`). Without roles, a patient's "I think it's a slipped disc" routes into section 8, *Diagnosis* — precisely what `PLAN.md:14` forbids, emitted by a provider otherwise described as grounded by construction. Grounded is not the same as correctly attributed.
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
- **Clinician-owned sections (7, 8, 11, 12) populate only after per-session role confirmation.** Unresolved role ⇒ those sections stay blank.
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
- Last completed step: Planning complete — hardened via `/review-plan` (three parallel critique lenses), then re-hardened after a cross-family `/peer-review`
- Current in-progress step: None
- Immediate next action: Start Task 1.0 (capture both clinics' template section lists) via `/execute` or `/execute-loop`
- Open blockers / open questions: **Task 1.0 needs the practitioner's real Cliniko template section lists for both clinics** — it now gates the canonical schema constant, not just the mapping
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

- (no reviews yet)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
Each /review invocation appends a detailed findings block here, with
/fix updating per-finding Decision and Notes as it processes each one.

- (no findings yet)

## Tasks

### Phase 1 — Foundations, types, providers, custody
- [ ] 🟥 1.0: Capture both clinics' real Cliniko treatment-note template section lists from the practitioner, and confirm whether they are identical. **Precedes the schema constant** — the canonical set is only defensible as a superset once both real templates have been seen.
  - Done when: both lists are recorded in this plan, and each canonical key is annotated with its meaning, its clinician/patient ownership, and its mapping rule per clinic.
- [ ] 🟥 1.1: Note types in `note.py` — `NoteAssertion`, `NoteSpan`, `NoteProposal`, `ConfirmationDecision`, `GeneratedSection`, `NoteWarning`, `GeneratedNote`, `NoteRequest`, `NoteModelProvider` Protocol, and the canonical 16-section constant reconciled against Task 1.0. Frozen pydantic, `extra="forbid"`, mirroring `TranscriptDocument` (`transcription.py:252-292`). Reuse `SESSION_ID_PATTERN`.
  - **`NoteAssertion` is the unit `GeneratedSection` holds** — not `NoteSpan`. A `transcript` assertion holds exactly one span with one contiguous `source_coords = (segment_index, first_word_index, last_word_index)`; the type makes multi-interval assembly unrepresentable rather than merely checked.
  - A non-`transcript` assertion carries `proposal_id`, `shown_text_digest`, `config_digest`, and a `ConfirmationDecision(decision, timestamp)`. `NoteProposal` is structurally distinct from `NoteAssertion`, so an unconfirmed proposal cannot be written by construction.
  - `GeneratedNote` additionally carries `session_id` (bound, `SESSION_ID_PATTERN`), `template_profile_id`, the confirmed cluster→role assignment, `transcript_digest`, and `config_digest`. **Define `transcript_digest` precisely**: algorithm, version tag, and exact byte domain — the decrypted canonical `TranscriptDocument.to_bytes()` output, not ciphertext — computed in one place and verified identically by `read_note` and `complete_session`.
  - Done when: types import cleanly, mypy strict passes, a round-trip test passes, and tests assert that a `NoteProposal` cannot be placed in a `GeneratedSection`, that a `transcript` assertion spanning two intervals is unrepresentable, and that a non-`transcript` assertion without a `ConfirmationDecision` is rejected at construction.
- [ ] 🟥 1.2: `normalise_token()` / `content_tokens()` in `note.py` — the single normalisation source (see the shared-helpers inventory). Build on `_STRIP_PUNCT_RE` (`transcription.py:203`).
  - Done when: a test pins that autofill matching and checker tokenisation call the same function.
- [ ] 🟥 1.3: Both providers in `note.py` — `ExtractiveNoteProvider` (verbatim transcript spans, cue-matched to sections, role-aware once 2.2 lands) and `MockNoteModelProvider(behaviour=...)` with the Axis B behaviours. Ship in `src/`, following `MockSpeechProvider` (`speech.py:115`).
  - Done when: both satisfy the Protocol and `MockNoteModelProvider` produces each Axis B behaviour deterministically.
- [ ] 🟥 1.4: Tripwire signatures in `logging_setup.py:57-87` — `note_sections`, `note_spans`, `note_warnings`, `span_text`, `note_excerpt`, `transcript_utterances`, quoted and unquoted. Test over `repr` and `model_dump_json` of every note model **including `NoteRequest`**.
  - Done when: each model's lone repr is dropped by the filter.
- [ ] 🟥 1.5: `NOTE_FILENAME` and the `complete_session` custody fix in `session_store.py`. If `note.enc` exists: fsync + verify-decrypt + parse + session-binding + `transcript_digest` match, all before `delete_session_key`. **Fails closed, symmetric with the transcript** — any failure retains the key and Complete does not proceed. Retaining custody is precisely what keeps regeneration possible; deleting the note and completing would delete the key too, making the transcript unreadable and regeneration impossible.
  - The clinician's exits are **Regenerate note** or an explicit, confirmed choice to delete the note and complete without one — never a silent deletion.
  - Done when: the 56-function custody suite passes unchanged, plus tests for note-absent, note-valid, note-corrupt-ciphertext, note-authenticated-but-malformed, note-wrong-session, note-digest-mismatch, and unlink-failure — each asserting the key is retained.

### Phase 2 — Speaker roles and diarization measurement
- [ ] 🟥 2.1: Per-segment cepstral mean normalisation in `_segment_embedding` (`transcription.py:507-543`), to remove the gain nuisance that makes one loud and one quiet speaker separable as two clusters.
  - Done when: existing diarization tests pass and a new test shows a gain-shifted copy of a segment clusters with its original.
- [ ] 🟥 2.2: `speaker_role()` — **preselect** which cluster is the clinician from talk-time share, question-asking rate, and first-speaker order. The result is a default for the mandatory confirmation in Task 7.5, never an authority. Sections 7, 8, 11, 12 (assessment, diagnosis, advice, management plan) populate only from confirmed-clinician utterances; unresolved or merged clustering leaves them blank with candidate quotations surfaced instead.
  - A clinician's *question* is not a diagnosis: cue matching into clinician-owned sections must exclude interrogative forms.
  - Done when: role preselection is a pure function with fixture tests; a test asserts clinician-owned sections stay empty when the role is unconfirmed; and a test asserts an interrogative clinician utterance does not populate section 8.
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
  - Done when: Generate is unreachable without both confirmations; the saved artifact records which cluster was confirmed as clinician; and a test pins that sections 7, 8, 11 and 12 stay empty when a note is somehow composed without a confirmed role.
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
