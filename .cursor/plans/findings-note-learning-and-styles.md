# Review findings — note learning and styles

Companion to `plan-note-learning-and-styles.md`. It holds the FULL review round blocks that the plan carries only as digests.

**Lifecycle:** this file and its companion plan are ONE unit — move, archive or delete them together. A round present here must have its digest (or, mid-recovery, its full copy) in the plan; a round digest in the plan must have its full block here.

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

### Round 3 - 2026-09-19 - Phase 0 (Tasks 0.1–0.5) as one surface, in-session `/review-loop` round 1 of 3

- Round status: Closed (3 applied by the same seat, 2026-09-19)
- Source: Claude Code (Fable 5.1 architect, `/execute-loop` run stage-0 leg a4, headless)
- Primary review baseline: the working tree against `886b466` (the commit predating the plan's first `/execute` checkpoint; nothing of Phase 0 is committed). Changed files (all read in full from disk, not from diff fragments): `desktop/src/scribe_desktop/{logging_setup,note,note_check,note_config,practitioner_profile,session_store}.py`, `desktop/src/scribe_desktop/ui/{models,note,practitioner}.py`, `desktop/src/scribe_desktop/config_defaults/{clinical_abbreviations,prose_connectives}.json`, `desktop/tests/{test_note_pipeline,test_ui_models,test_ui_screens}.py`, NEW `desktop/tests/{test_note_schema_v2,test_style_profile,test_typed_wording,test_vocabularies_and_settings}.py`, `docs/security/{threat-model,data-flow-map,retention-schedule}.md`. No generated artefacts skipped.
- Lenses: custody (three-key isolation, key-first deletion, description binding, the AAD, key destroyed on every exit of `_seal` / `_open`); the provenance branches (every `provenance ==/!=/in` site in `src` enumerated — 18 sites — and each classified as quoted-vs-authored (correct for `clinician`), proposal-only, or the D4 admission set; every `proposal_id` consumer in `ui/note.py` and `note_check.py` confirmed proposal-scoped, so a `clinician` line's `proposal_id = None` reaches no `str`-assuming site); the fail-closed vocabulary guard (`_parse_shipped_vocabulary` refuses non-object, missing key, empty list, non-string, blank, multi-word, control character, duplicate, and — for the connectives — mixed case; `_load_shipped_vocabulary` wraps read/decode failures; both constants derive at import so an emptied package cannot import as "admit nothing"); the D12 consent text (every promise re-read against a control: the fingerprint, phrase learning and the transcript-side filter are built; the typed-shorthand, learned-rule and learned-style promises bind Phase 2/3 controls and are vacuously true today — nothing of those kinds exists to be undeletable — by the plan's own sequencing of consent v3 into Phase 0); the doc stubs (every present-tense sentence in the three docs re-read against a built symbol; every unbuilt control marked "planned; enforced from Phase N").
- Looks good: `_seal` keeps the round-14 custody ordering for both stores (fresh key written FIRST on first save; a present-but-dead key blob permits a fresh key; an uninspectable key refuses the save before any write; a live-but-unwrappable key refuses typed with nothing replaced; the in-memory key destroyed in `finally`); `_open` destroys the key in `finally` and reports `key` / `blob` / `authentication` structurally; `_malformed` is raised `from None` with locations only; the AAD is the second wall (the voice AAD under the style key fails authentication — pinned); `delete_style_profile` and `delete_profile` unlink their own root only (pinned side by side). Schema v2: a `config` decision without its digest is unrepresentable; a typed line's decision must name the line itself and be `clinician`-decided; the provider boundary is the ingestion check, and `finalise_note` re-establishes both the admission set and the typed-line decision; a v1 label cannot carry v2 content. The consent text v3 withdraws exactly the two v2 sentences the plan named and adds no promise a built or planned control does not back.
- Finding verification: 5 candidates; 2 dropped (pydantic private-method handling — the suite's green run over `_carries_v2_content` is the evidence it works; `learning_status` reading only the voice store — that is Phase 3's D9 wiring, planned, and the doc says so); 0 downgraded
- Executor judgment: LOW-002 (a default parameter no caller uses). Structural quality: LOW-003 (two near-duplicate path helpers whose tuples were discarded at every call site). Post-fix regressions: none — no `/fix` has run on this work before this round (regression baseline = the working tree; the only prior rounds are plan peer-reviews). Missed-issue pass: re-read `practitioner_profile.py` 284–552 (custody, high-risk), `note.py` 336–735 and 1938–2215 (the type model and the pipeline boundaries), `note_config.py` 993–1243 and 1415–1450, `ui/models.py` 400–630 and 1236–1340, `session_store.py` 807–840, `note_check.py` 430–445 / 1076–1110 / 1325–1350 / 1370–1440, and the three docs' diff hunks; result: LOW-001.

#### Findings

- **[LOW]** LOW-001: `desktop/src/scribe_desktop/ui/models.py:604` — the `clinician_asserted` warning copy named only "(autofill or prefill)" while, since schema v2, a typed `clinician` line draws the same review (`note_check.provenance_warnings` emits it for every authored line) — a provenance branch still worded as a two-way split — Triage: Fix-now (fix-on-fast); Decision: Applied. /fix notes: title now "A clinician-authored line was added (autofill, prefill or typed)" with a comment naming D4; the copy test (`test_ui_screens.py::TestNoteViewModels::test_every_registered_warning_code_has_copy`) pins structure, not wording, so no test changed; ruff + mypy clean. /fix date: 2026-09-19. /fix applied by: Claude Code.
- **[LOW]** LOW-002: `desktop/src/scribe_desktop/practitioner_profile.py:330` — `_key_present(key_path, store=_VOICE_STORE)` carried a default no caller used (both callers pass the store), a leftover of the refactor that reads as if the voice store were privileged — Triage: Fix-now (fix-on-fast); Decision: Applied. /fix notes: the default removed; the one caller (`_seal`) already passes `store`; ruff + mypy clean. /fix date: 2026-09-19. /fix applied by: Claude Code.
- **[LOW]** LOW-003: `desktop/src/scribe_desktop/practitioner_profile.py:320–327` (and the eight wrappers at 462–550) — `_paths` / `_style_paths` returned `(base, key_path, blob_path)` tuples whose key and blob members were discarded at every call site after the `_SealedStore` refactor (`base, _key_path, _blob_path = …`), two near-duplicate helpers encoding the store's default root outside the store record — Triage: Fix-now (fix-on-fast, single file, no behaviour change); Decision: Applied. /fix notes: `_SealedStore` gains `default_root: Callable[[], Path]` (`default_profile_root` / `default_style_root`), one `_base(store, root)` replaces both helpers, and the eight wrappers call it; the public signatures and every message are unchanged; `Callable` imported from `collections.abc`; ruff + mypy clean. /fix date: 2026-09-19. /fix applied by: Claude Code.

Fix-delta self-check: PASS — re-read the 3 applied hunks across 2 files (`practitioner_profile.py` 284–330 + 456–552; `ui/models.py` 600–608): every wrapper resolves its root through `_base`, no exit path changed, the copy change is wording only.

REVIEW-ROUND-3 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 3), all applied in-round; suite owed to the composer (two source files changed).

### Round 4 - 2026-09-19 - Phase 0 as one surface, in-session `/review-loop` round 2 of 3 (post-fix confirmation)

- Round status: Closed (0 findings; converged)
- Source: Claude Code (Fable 5.1 architect, `/execute-loop` run stage-0 leg a4, headless)
- Primary review baseline: unchanged from round 3 (the working tree against `886b466`; the same changed-files list, every file re-read in full). Regression baseline: the pre-`/fix` state of round 3 — the three applied hunks in `practitioner_profile.py` (the `_SealedStore.default_root` field + `_base`, 286–326; the eight wrappers, 456–542; `_key_present`'s signature, 329) and `ui/models.py` (the `clinician_asserted` copy, 600–608).
- Post-fix regression check: `_SealedStore` is constructed by keyword at both sites, so the inserted field changes no positional order; every public wrapper resolves its directory through `_base(store, root)` and keeps its signature, its default root (`default_profile_root` / `default_style_root` — pinned by `test_style_profile.py::test_the_style_root_is_a_sibling_of_the_profile_root`) and every error message; `_key_present`'s one caller passes `store`; the test suite's monkeypatch seams (`pp.wrap_key_to_file`, `pp.unwrap_key_from_file`, `pp.atomic_write_bytes`, `Path.stat` / `unlink` / `read_bytes`) are untouched; the copy change is wording only and `test_every_registered_warning_code_has_copy` pins structure. The threat-model's surface 15 names `_SealedStore`, `_seal`, `_open`, `_unlink_store` — all still present under those names. Round classification: 0 🆕 / 0 ⚡ / 0 🔁.
- Finding verification: 0 candidates. Executor judgment: none. Structural quality: none. Missed-issue pass: re-read `practitioner_profile.py` 284–552 and `ui/models.py` 596–610 with fresh eyes, plus the round-3 finding sites; result: none.
- Convergence: no CRIT/HIGH/MED in either round and round 4 is empty — the loop stops here (2 rounds of the 3-round cap). Cross-family peer pass: the composer-seat codex `gpt-6-astra` pass follows `phase-complete` per the run contract (this round's findings are trivial, so the `/review` skill's own non-trivial trigger does not fire; the loop's every-phase peer cadence does).

REVIEW-ROUND-4 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0); converged.

### Round 5 - 2026-09-19 - Phase 0 (Tasks 0.1–0.5) as one surface, independent cross-family codex peer review (code round 1, pass stage-0.p1)

- Round status: Closed (PR-MED-016 applied in leg a6 and confirmed closed as a class by round 6)
- Source: Codex peer-review
- Baseline: Uncommitted Phase 0 working tree against `886b46635547a4149993ab0fa64b1e775ce38683`; unchanged across the interrupted review.
- Files reviewed: `desktop/src/scribe_desktop/{logging_setup,note,note_check,note_config,practitioner_profile,session_store}.py`; `desktop/src/scribe_desktop/ui/{models,note,practitioner}.py`; both new `config_defaults/{clinical_abbreviations,prose_connectives}.json` files; `desktop/tests/{test_note_pipeline,test_ui_models,test_ui_screens,test_note_schema_v2,test_style_profile,test_typed_wording,test_vocabularies_and_settings}.py`; `docs/security/{threat-model,data-flow-map,retention-schedule}.md`. Context: project instructions, lessons, product plan, specified implementation-plan contracts and rounds 3–4; relevant baseline models, custody implementation and local Pydantic documentation.
- Validation basis: Static inspection only; no tests, application execution or filesystem writes. Composer-reported ruff, mypy and 2152 passing tests were treated as supplied evidence, not independently rerun.
  - Custody: distinct descriptions and AAD at `practitioner_profile.py:105` and `:111`; description verification at `session_store.py:589`; shared sealing preserves key reuse, first-write ordering and unconditional in-memory key destruction (`practitioner_profile.py:347`). Decryption retains AAD verification and cleanup (`:386`). Both deletion wrappers use their own store/root and the shared key-first deletion loop (`:440`, `:500`, `:538`). No custody-ordering regression found against the baseline.
  - Provenance/decision branch inventory: `note.py:373,413,460,469,482,505,684,685,2010,2121,2197,2204,2205`; `note_check.py:438,1082,1107,1331,1345,1374,1429`; `session_store.py:818`; `ui/models.py:503,505,949`; `ui/note.py:571,751`, plus the provenance-label mapping at `ui/models.py:409`. The remaining transcript/non-transcript splits correctly distinguish quoted evidence from authored text. Proposal-ID consumers remain proposal-scoped or autofill-gated (`note_check.py:1345`); no string-assuming consumer was found reachable with a typed assertion’s `proposal_id=None`.
  - Evidence enforcement: config-digest mismatch is rejected by `NoteAssertion` (`note.py:505`) when finalisation constructs the assertion (`:2241`). Typed base lines require a clinician decision (`:2204`). `write_note` first performs full serialized revalidation (`session_store.py:746,811`), covering missing/invalid decisions and v2 content under a v1 label, then verifies text/config relations (`:821`). The v1 fixture at `test_note_schema_v2.py:640` matches the baseline’s serialized field shape, including explicit null evidence and the three-field confirmation; it is not merely a new-model dump with defaults removed.
  - Vocabularies/filter/consent: no prohibited clinical or polarity additions identified in the connective list, or medication names/patient identifiers in the abbreviation list. The import guard rejects empty, missing and malformed entries; `_one_word` delegates blank rejection to `_no_control_chars` (`note_config.py:225,1072,1206`). Both refusal paths call the same date, number and medication classifiers; the typed filter names its narrower scope and residue. Consent v3 is pinned by literal equality, and later-feature promises are bound to the plan’s Phase 2–3 sequencing.
- Finding verification: 3 candidates / 2 dropped / 0 downgraded. Dropped: purported empty-string vocabulary bypass, already rejected by `_no_control_chars`; consent-record/version documentation currency concerns, excluded from findings under the supplied scope.

#### Confirmed / disputed (rounds 3–4)

- LOW-001 — Confirmed applied: `desktop/src/scribe_desktop/ui/models.py:605` now names “autofill, prefill or typed”, matching the authored-line warning at `note_check.py:1331`.
- LOW-002 — Confirmed applied: `_key_present` requires an explicit store (`desktop/src/scribe_desktop/practitioner_profile.py:329`), supplied by its caller at `:364`.
- LOW-003 — Confirmed applied: `_SealedStore.default_root` and `_base` centralize root selection (`desktop/src/scribe_desktop/practitioner_profile.py:295,324`); all voice/style wrappers use that route. No downstream regression identified.

#### PR-MED-016 — Malformed style-profile errors can expose input through validation locations

- **[MED]** `desktop/src/scribe_desktop/practitioner_profile.py:423` — raw validation locations are not necessarily content-free.
- Triage: Fix-now.
- Fix route: premium-only.
- Why it matters: The new style loader promises structural errors without clinical input. Dictionary keys and unexpected field names are input too; copying them into the replacement exception defeats that boundary even with `hide_input_in_errors=True` and `raise … from None`. No current production logging path for this error was identified, so this is MED rather than an asserted active logging leak.
- Current behaviour: `_malformed` joins every component of `error["loc"]` verbatim and inserts the result into `ProfileUnusableError` (`practitioner_profile.py:422–428`). `StyleProfile.heading_labels` validates mapping keys against `NoteSectionKey` (`note_config.py:1132`). An authenticated malformed payload with `heading_labels={"Zebra-secret patient": "Assessment"}` therefore produces a location containing that input key; `load_style_profile` carries it into its supposedly structural exception (`practitioner_profile.py:529`). Unexpected JSON field names create the same class of exposure. Hiding `input_value` does not sanitize locations.
- Desired behaviour: Loader errors must contain only fixed structural identifiers and counts. Drop raw locations, or render them through a schema-aware allow-list that replaces dynamic mapping keys and unknown field names with fixed placeholders.
- Pattern to follow: Preserve the terse, content-independent boundary used by `_canonical_note` (`session_store.py:759–771`) and retain suppressed validation-error chaining.
- Pattern siblings: A source search for location joins, `error["loc"]`, and input-hiding configuration found one location-rendering implementation: `_malformed`. Both callers need the class fix: `load_profile` at `practitioner_profile.py:482` and `load_style_profile` at `:529`. Raw style validation-error rendering also deserves coverage because the existing assertion at `test_style_profile.py:203` checks only invalid values, not dynamic keys. The loader regression at `test_style_profile.py:420` has the same coverage gap.
- Invariant: Malformed encrypted-store content must not appear in the public error message or its rendered traceback, including content occurring in keys rather than values.
- Verification: Re-read the mapping schema, shared formatter and both callers. Local Pydantic documentation distinguishes hidden input values/types from retained error locations; its extra-field example also retains the supplied field name. Existing tests cover `"Zebra\tsecret"` as an exemplar value, leaving key-based exposure untested. Add cases for an invalid heading key and unexpected field names, asserting absence from the loader’s message and formatted traceback. No tests were run during this review.
- Regression risk: Low for custody and successful reads; the change concerns failure diagnostics. Preserve `reason="malformed"`, store attribution and exception-chain suppression. Update tests that expect specific locations if diagnostics become count-only.
- /fix decision: Applied
- /fix notes: `desktop/src/scribe_desktop/practitioner_profile.py` — `_malformed(store, model, exc)` (464) now takes the model class and renders every `error["loc"]` through `_render_location` (454): an integer index, pydantic's `[key]` marker or a name in `_declared_field_names(model)` (437 — the model's declared fields plus those of every nested `BaseModel` its annotations reach, walked with `typing.get_args` through `tuple`/`Mapping`/`Annotated`/unions by `_nested_models`, 423) renders as itself, anything else as the fixed `_LOCATION_PLACEHOLDER = "<field>"` (419); both callers pass their model (`load_profile` 537, `load_style_profile` 584); `reason="malformed"`, the store label and `from None` unchanged; the docstring rewritten to claim exactly this (a location is not input-free; values hidden by `hide_input_in_errors`, keys and unknown names by the allow-list). Invariant honoured: a mapping key and an unknown field name never reach the message or the formatted traceback for either store. Verification: `tests/test_style_profile.py` — NEW `TestMalformedLocationRendering` (DPAPI-free: the declared-name set reaches nested models; a mapping key, an unknown field and a tab-bearing exemplar VALUE all render as the placeholder while `exemplars.0.exemplar_text` still names the site; the voice model renders the same way) and the parametrised loader test `test_a_malformed_blob_renders_no_key_or_unknown_field_name` (mapping key → `heading_labels.<field>.[key]`, unknown top-level field → `<field>`, unknown nested consent field → `consent.<field>`; the secret absent from `str(exc)`, the formatted traceback and the chain — a VOCABULARY bound, qualified at round 6 PR-LOW-019: a key spelled like a declared field name renders as that name); `tests/test_practitioner_profile.py` — the parametrised `test_a_malformed_blob_renders_no_unknown_field_name` (top-level and nested-consent unknown fields through the voice loader). The two existing hidden-input pins (203, 420 in `test_style_profile.py`; the voice `{}` case) keep passing by construction (`embedding`, `exemplars` are declared names). Sibling sites: none — `_malformed` is the one location renderer. ruff clean; mypy clean (34 files); pytest owed to the composer.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (Fable 5.1 architect, leg a6)

#### LEG 1 verified tuples
- PR-MED-016: `materiality=behavioral severity=low surface=production rec=Fix-now` — decision: Fix-now — applied 2026-09-19T11:56+10:00 (leg a6; see `/fix notes` above) — VERIFIED (leg a5, 2026-09-19): `_malformed` (`practitioner_profile.py:416–431`) joins every `error["loc"]` component verbatim, and on pydantic 2.13.4 (`.venv/Lib/site-packages/pydantic/version.py:11`) a location is NOT input: `hide_input_in_errors` hides only `input_value` / `input_type` (`pydantic/config.py:756–797`), an `extra="forbid"` refusal carries the unknown field NAME as its loc (`config.py:99–105`, the documented `y` example), and a `Mapping` field's key is a loc component (a `NoteSectionKey` key refusal on `StyleProfile.heading_labels`, `note_config.py:1132`, renders `heading_labels.<key>.[key]`). Both callers reach it (`load_profile` :482, `load_style_profile` :529); the existing hidden-input pins (`test_style_profile.py` 203, 420) exercise a VALUE, never a key or an unknown field, so the class is untested. DOWNGRADED MED → LOW with evidence: (1) the blob is GCM-authenticated under a DPAPI-wrapped key, and the app writes only `profile.to_bytes()` of a validated model (`_seal`, :347–383), so a non-canonical key or unknown field reaches `_malformed` only from a same-user hand-crafted blob — outside boundary 2's defended set — or a cross-version schema drift, whose leaked component is a field NAME, not patient text; (2) no production path renders or logs the detail: `ui/models.py` `learning_status` (:1068–1069) and `attribution_readiness` (:1414–1419) consume `exc.reason` only and format fixed hints, the Practitioner tab reads those hints and the readiness `reason` (`ui/practitioner.py:472`), and `src` has no `logger.exception` / `logger.error` site (the only `getLogger` is `logging_setup.py:327`), so the text lives only in the unhandled-exception path no consumer takes today. Fix-now stands because `_malformed`'s docstring ("names the reason, the error count and the field locations, never a value", :418–422) is a control claim that outruns the structure (lessons.md class) and the round-14 PR-HIGH-003 boundary was "no store content in a rendered error"; the fix is local — render each loc through the model's declared field names (allow-list, integers kept) and replace a dynamic mapping key or unknown field with a fixed placeholder — plus two key-based tests (an invalid `heading_labels` key, an unexpected top-level field) asserting absence from the message and the formatted traceback for both stores. `Regression risk` as the peer states: `reason="malformed"`, the store label and `from None` preserved; no test pins an exact location string.
- Cap verdict: accept — production-behavioral — one bounded finding on the failure-diagnostics path of an authenticated store, no reachable consumer of the text, a local fix; a residue of this class at cap 5 accept-closes on the tail signature.

Fix-delta self-check: PASS — re-read the 4 applied hunks in `practitioner_profile.py` (417–476, 537, 584 and the import) and the three test hunks: both loaders pass their model, the placeholder replaces only non-declared string components, the `<root>` case and every existing message are unchanged, no exit path other than the malformed branch's message text changed.

PEER-ROUND-5 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0).

### Round 6 - 2026-09-19 - Phase 0 (Tasks 0.1–0.5), independent cross-family codex peer review (confirmation round, pass stage-0.p1)

- Round status: Closed (Converged: PR-MED-016 closed as a class (round 6), PR-LOW-019 applied (leg a8); pass stage-0.p1 accept-closed by the composer on the tail signature)
- Source: Codex peer-review
- Baseline: Uncommitted Phase 0 against `886b46635547a4149993ab0fa64b1e775ce38683`; HEAD verified unchanged.
- Files reviewed: Full diff of `desktop/src/scribe_desktop/practitioner_profile.py`; specified regions of `desktop/tests/test_style_profile.py` and `desktop/tests/test_practitioner_profile.py`; reachable model definitions in `note_config.py` and `note.py`; relevant consumers in `ui/models.py`; implementation-plan Round 5, including LEG 1 and `/fix notes`; local Pydantic definitions/documentation and relevant project context.
- Validation basis: Static reading only. No files written, application execution, tests or network calls. Composer-reported clean ruff, strict mypy and 2160 passing tests were supplied evidence, not independently rerun.
  - **Renderer:** Every string outside the recursively collected declared names and `[key]` becomes `<field>`; integers pass and empty locations become `<root>` (`desktop/src/scribe_desktop/practitioner_profile.py:437`, `:454`). `_nested_models` reaches `ConsentRecord`, `StyleMeasures` and tuple-contained `StyleExemplar`; the voice model reaches `ConsentRecord` (`practitioner_profile.py:423`; `note_config.py:1130`, `:1134`, `:1135`; `practitioner_profile.py:203`). Neither current model graph contains discriminated unions or ordinary union fields. Literal keys and nested extra-field errors cannot introduce strings outside the allowed vocabulary. Input strings coinciding with that vocabulary can pass; the documentation consequence is recorded below.
  - **Callers and chaining:** Both callers supply the correct model and retain `from None` (`desktop/src/scribe_desktop/practitioner_profile.py:537`, `:584`). `reason="malformed"` and store attribution remain intact (`:480`). Successful reads and custody operations are unaffected by the formatter change.
  - **Regression tests:** The five new loader cases would reject the pre-fix raw-location rendering through their secret-absence assertions in both messages and formatted tracebacks (`desktop/tests/test_style_profile.py:535`; `desktop/tests/test_practitioner_profile.py:559`, with traceback helper at `:204`). The renderer pins cover nested fields and integer positions (`test_style_profile.py:243`, `:250`, `:263`). Expected-location assertions are additional checks: a location-shape change can cause a failure, but cannot conceal a secrecy regression because the absence assertions remain independent.
  - **Bounded sweep:** Current status has 17 modified tracked files and six untracked files. Against Round 5’s file list (`.cursor/plans/plan-note-learning-and-styles.md:606`), the additions are the plan record and the explicitly requested voice-loader test file; that file’s diff contains only the new import and two parametrized cases. No unexplained file-scope expansion found. A historical file list alone cannot establish byte-for-byte equality of the other files.
- Finding verification: 1 candidates / 0 dropped / 0 downgraded

#### Confirmed / disputed (round 5)

- **PR-MED-016 — Confirmed closed as a class for arbitrary input-string disclosure:** the shared renderer confines both loaders’ location strings to the specified schema vocabulary, marker and placeholders, with chaining suppressed (`desktop/src/scribe_desktop/practitioner_profile.py:454`, `:479`, `:537`, `:584`). One LOW documentation overclaim remains below; no behavioral secrecy regression identified.

#### PR-LOW-019 — “Never a key” overstates the vocabulary-based guarantee

- **[LOW]** `desktop/src/scribe_desktop/practitioner_profile.py:477` — the renderer restricts string vocabulary but does not distinguish a field name from an input key with the same spelling.
- Triage: Fix-now.
- Fix route: fix-on-fast.
- Why it matters: The requested control documentation should describe exactly what is enforced. This is a documentation correction, not an arbitrary-content leak.
- Current behaviour: `_render_location` accepts `part in declared` regardless of its position (`practitioner_profile.py:457`). For example, a malformed style mapping containing `heading_labels={"source_count": "C/O"}` has an invalid Literal key, but `source_count` is also a declared field (`note_config.py:1132`, `:1136`), so its location renders as `heading_labels.source_count.[key]`. Likewise, an extra `model_id` inside voice consent can render verbatim because the outer voice model declares that name (`practitioner_profile.py:196`, `:203`). Both outputs stay within the intended fixed vocabulary, but contradict the absolute phrase “never a key.”
- Desired behaviour: Describe the enforced guarantee as “no string outside the declared-field vocabulary, fixed marker and placeholders”; explicitly allow input keys whose spelling coincides with that vocabulary. No runtime change is necessary.
- Pattern to follow: The precise vocabulary description immediately preceding the overclaim at `practitioner_profile.py:475`.
- Pattern siblings: Related wording appears at `desktop/tests/test_style_profile.py:522` (“never the key”) and `desktop/tests/test_practitioner_profile.py:547` (“never the name”); qualify these as referring to the non-declared sentinel names exercised by those tests. Searches across `desktop/src` and `desktop/tests` for these phrases and mapping/unknown-field variants found no other unconditional equivalent claim.
- Invariant: Documentation must distinguish restricted output vocabulary from positional identification and removal of every input-derived key.
- Verification: Re-read the global name collection, membership condition, mapping schema and nested consent schema. The counterexamples follow directly from those definitions and the installed Pydantic location contract; no execution performed.
- Regression risk: None from the proposed wording-only correction; retain the renderer and existing assertions.
- Scope-expansion disposition: None; bounded to the fix’s explanatory text.
- /fix decision: Applied
- /fix notes: wording only, no runtime or assertion change — `desktop/src/scribe_desktop/practitioner_profile.py` `_malformed` docstring (the closing sentence at 477 replaced: the guarantee is stated as "no string outside the declared-field vocabulary, the marker and the placeholder ever reaches the message — never a value, and never free text from a key or an unknown field name", with the position-blind membership named explicitly: an input key or unknown field spelled like a declared name renders AS that name, a token from the schema's public vocabulary); the two test-docstring siblings qualified the same way (`tests/test_style_profile.py` the loader case's docstring — the sentinels are non-declared names; `tests/test_practitioner_profile.py` the voice loader case's docstring); the plan's round-5 `/fix notes` clause qualified in passing ("a VOCABULARY bound … a key spelled like a declared field name renders as that name"). Sibling sites: the three the peer named — the leg-a7 sweep over `desktop/src`, `desktop/tests` and `docs/` found no other. Verification: ruff clean; mypy clean (34 files); the secrecy assertions are untouched and the pytest run is the composer's.
- /fix date: 2026-09-19
- /fix applied by: Claude Code (Fable 5.1 architect, leg a8)

#### LEG 1 verified tuples
- PR-LOW-019: `materiality=docs-only severity=low surface=docs rec=Fix-now` — decision: Fix-now — applied 2026-09-19T12:06+10:00 (leg a8; see `/fix notes` above) — VERIFIED (leg a7, 2026-09-19): the counterexample is real on the current renderer — `_render_location` (`practitioner_profile.py:454–461`) admits `part in declared` at ANY position (:457), and `_declared_field_names` (:437–451) is one flat set over the model graph, so a `heading_labels` key spelled `source_count` (a declared `StyleProfile` field, `note_config.py:1136`) renders `heading_labels.source_count.[key]`, and an extra consent field spelled `model_id` (declared on the outer voice model, :196) renders `consent.model_id` — both drawn from the FIXED vocabulary, so the disclosure is bounded to "this input equals one of the schema's public field names" and no free text can pass; the docstring's closing "never a key" (:477) therefore overstates what the structure enforces (the lessons.md claim-outruns-structure class, wording only). Sibling sweep confirmed exhaustive: `desktop/src` + `desktop/tests` grep for "never a key" / "never the key" / "never the name" / "never a value" and the mapping / unknown-field variants finds exactly the three sites the peer names (`practitioner_profile.py:477`, `test_style_profile.py:522`, `test_practitioner_profile.py:547`); `docs/` carries no such claim; the plan's own round-5 `/fix notes` (this file, the "carry the placeholder, never the key" clause) repeats it as record text — the fix leg may qualify it in passing. Fix is wording only: state the guarantee as "no string outside the declared-field vocabulary, the `[key]` marker and the placeholder; an input key that coincides with a declared name renders as that name" at the three sites; no runtime or assertion change (the secrecy assertions use non-declared sentinels).
- Cap verdict: accept — docs-only — round 2 of cap 5 has converged (the MED closed as a class; the one remaining item is a wording correction with no behavioural or assertion change); a round-7 confirmation is NOT warranted after a wording-only fix — the composer may accept-close the pass on the tail signature once the fix leg lands and the composer suite is green.

PEER-ROUND-6 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1).

### Round 7 - 2026-09-19 - Phase 1 (Tasks 1.0–1.6, live transcription) as one surface, in-session `/review-loop` round 1 of 3
- Round status: Closed (4 applied by the same seat, 2026-09-19)
- Source: Claude Code (Fable 5.1 architect, `/execute-loop` run stage-1 leg b4, headless)
- Scope: `git diff -- desktop/ docs/` at the green 2344 tree (13 changed files) plus `tests/test_live_session.py` and `tests/test_live_transcription.py`; lenses in order: custody (the attached-worker ownership enumeration), threading, parity, C8/C9, the design-system cue and doc claims.
- Custody enumeration (every consumer of an attached worker, re-verified after the fix): `start` (attaches; the failure path stops it), `_fail_locked` ← `_on_capture_failure` / `finish` footer failure / `transcribe` failure, `_retire_locked` ← `start` on a non-active session, `discard` in RECORDING / PAUSED / FAILED / pre-claim PROCESSING / QUEUED (unlocked window, under the reservation, before `discard_session`), `claim_live_transcriber` (PROCESSING + `transcribing` → the callable owns it; `discard` is refused by the flag and `_fail_locked` cannot reach it — the capture worker is already stopped), and — the gap found — `complete` / `complete_without_note` / `complete_deleting_saved_note`. The key is never destroyed while the callable owns the worker: `complete*` require QUEUED, reached only after the callable returned and `_live_transcript`'s `finally` stopped the worker.
- MED-001 — `desktop/src/scribe_desktop/session.py:705, 740, 767` (custody, surface=production, non-production-impacting: no dependency / env / migration) — A transcriber callable that never claims the worker (not the shipped `build_transcriber`, which claims inside the run) leaves it attached at QUEUED holding its undrained result (plaintext words + embeddings); all three Complete paths then destroyed the key with that plaintext still resident until garbage collection — the class the D2 ownership rule closes for Discard was open for Complete. Evidence: `_LiveSession.live_transcriber` untouched by `complete_session`; `test_complete_stops_an_unclaimed_worker_before_the_key_is_deleted` (new, ×3) reproduced `buffers_cleared is False` at the moment of `complete_session` before the fix. Fix: `self._stop_live_locked(live)` before `complete_session` in all three (a no-op when the shipped callable claimed it; the short in-lock bound suffices because a sealed worker's thread has exited). Triage: Fix-now. /fix decision: Applied. /fix notes: one helper call per path + the parametrised test (observes `complete_session` through the `session_mod` seam). /fix date: 2026-09-19. /fix applied by: architect (same seat).
- LOW-002 — `session.py:476` — `start()`'s failure path (the device fails to open AFTER the live worker started) stopped the worker with the 10 s default bound UNDER the controller lock; the worker holds no audio at that point (no tee exists yet). Fix: `stop(timeout=_LIVE_STOP_LOCKED_TIMEOUT_S)` + `test_a_start_failure_stops_a_loading_worker_with_the_short_bound` (a blocked model load, `start(99)` returns within the short bound, the worker clears itself). Triage: Fix-now; Decision: Applied.
- LOW-003 — `ui/main_window.py:215` (delegate-built 1.4) — `begin_live_view` ran inside the worker factory, i.e. inside `start()` before the device was opened, so a failed Start left the live header up with no session. Fix: `SessionScreen.session_started` (emitted after a successful `start`, synchronously inside `on_start` — it always precedes the delivery of the worker's first queued post) → `transcript_screen.begin_live_view`; the factory only builds; `test_start_emits_session_started_only_on_success` + the MainWindow test adjusted (building opens nothing; the signal does). Triage: Fix-now; Decision: Applied.
- LOW-004 — `benchmark.py:221` (delegate-built 1.6; the delegate flagged it) — `threshold_report` raised `ValueError` for a result with `rtf == 0` where it used to print a row. Fix: the live line reads "live window latency not measurable (RTF 0)" for that model and the panel renders on; `test_report_names_an_unmeasurable_zero_rtf_instead_of_failing`. Triage: Fix-now; Decision: Applied (supersedes the "ACCEPTED" note on the Task 1.6 line — no Accept disposition was taken).
- Lens verdicts with no finding: THREADING — `feed` is a byte-accounted `queue.put` (never blocks the capture writer; the cap fails the worker), `seal` is one sentinel under `_state_lock`, the drain joins on the `TaskThread`, `_post` and `stop` share the post lock so no update is delivered after `stop()` was CALLED (timeout or not), the two stop bounds are as documented, and `_fail_locked`'s in-lock stop cannot overlap Discard's unlocked stop because Discard joins the capture worker first (its failure callback cannot fire afterwards). PARITY — `assemble_transcript` differs from the pre-extraction tail only by `len(marked_segments)` (equal by construction) and `list(embeddings)`; the recorded-call parity and live-vs-batch fixtures pin it; the D2 AS-BUILT addendum's claims (cut at the padded bound, the held-segment rule, the true retention bound) match the code. C8/C9 — the three fallback lines + the assembled line reach the Session screen through the queued signal; `transcription.py` logs nothing; the only new log line (`live_transcriber_stop_timeout`) carries `session_id` + `session_state` (whitelisted); any repr of a `LiveResult` / live `TranscriptSegment` carries `transcript_words=` / `word_text=`, already tripwire signatures. DESIGN SYSTEM — the live-view bullet claims exactly what the widget does (header, append-only, no speaker, same `NoTextInteraction`, cleared on Discard, replaced at QUEUED). Observation (no finding): a new Start now clears the previous transcript view via `begin_live_view` → `_clear` — previously the retired session's document stayed visible with dead callbacks; the new behaviour is the honest one.

### Round 8 - 2026-09-19 - Phase 1 as one surface, in-session `/review-loop` round 2 of 3 (post-fix confirmation)
- Round status: Closed (0 findings; converged)
- Source: Claude Code (Fable 5.1 architect, `/execute-loop` run stage-1 leg b4, headless)
- Post-fix regression check over the four round-7 hunks: (MED-001) `_stop_live_locked` runs under the lock the three Complete paths already hold, before `complete_session`; with the shipped callable the handle is already `None` (claimed) so the paths are byte-for-byte today's; a timeout keeps the worker attached and logs, and the Complete still proceeds (the worker holds no crypto — C7) — consistent with Discard. (LOW-002) the short bound at Start touches only the failure path. (LOW-003) `session_started` is emitted only after `controller.start` returned; the MainWindow connection precedes the D10 first-run selection; the queued `live_window` delivery cannot precede the synchronous `begin_live_view`. (LOW-004) the guard is the only change to the report; every pinned line is unchanged. Round classification: round-7 findings all 🆕 and all closed; no fix-induced finding; converged.

### Round 9 - 2026-09-19 - Phase 1 (Tasks 1.0–1.6, live transcription) as one surface, independent cross-family codex peer review (code round 1, pass stage-1.p1)

- Round status: Closed (PR-MED-017/018 and PR-LOW-020/021 applied in legs b6–b7 and confirmed closed as a class by rounds 10–11)
- Source: Codex peer-review
- Baseline: `0f3af9b` (`HEAD`); uncommitted Phase 1 changes.
- Files reviewed: All 12 changed files under `desktop/` and `docs/`: `transcription.py`, `session.py`, `benchmark.py`, `ui/main_window.py`, `ui/models.py`, `ui/session_screen.py`, `ui/transcript.py`, `test_benchmark.py`, `test_integration_no_sockets.py`, `test_ui_models.py`, `test_ui_screens.py`, and `docs/design-system.md`; both new test files read in full: `test_live_session.py`, `test_live_transcription.py`. Supporting reads covered capture barriers, logging, security documentation, and the specified plan contracts and rounds 7–8.
- Validation basis: Static code and baseline comparison only. No files written and no tests executed. Composer-reported green checks were treated as supplied evidence, not independently reproduced.
- Finding verification: 7 candidates / 3 dropped / 0 downgraded. Dropped concerns: claim/Discard handover race, overlapping live/batch model residency on the shipped drain path, and a non-material release-lag test assertion issue.

#### Confirmed / disputed (rounds 7–8)

- **MED-001 — Partly confirmed:** All three Complete paths now stop an attached worker before calling `complete_session` (`desktop/src/scribe_desktop/session.py:711`, `:747`, `:775`). This fixes the exited-worker case, but the helper’s timeout does not prevent deletion; the claim of complete custody closure is disputed below.
- **LOW-002 — Confirmed:** Start-failure cleanup uses the short bound at `desktop/src/scribe_desktop/session.py:479`; the device-open failure precedes capture-thread startup (`desktop/src/scribe_desktop/audio_capture.py:358`).
- **LOW-003 — Confirmed:** `session_started` follows successful `controller.start()` (`desktop/src/scribe_desktop/ui/session_screen.py:178`), and the worker factory only constructs the worker (`desktop/src/scribe_desktop/ui/main_window.py:221`).
- **LOW-004 — Confirmed:** The zero-RTF guard emits the unmeasurable line and continues rendering (`desktop/src/scribe_desktop/benchmark.py:221`).

#### Custody, threading and parity verification

- **Start failure:** Stops the live worker before `discard_session` (`session.py:479`, `:482`). A blocked model load can remain alive, but this path has not fed consultation PCM and the live worker has no session crypto.
- **Capture/footer/transcription failure:** `_fail_locked` closes the store, requests worker shutdown and retains custody (`session.py:1176`). An uncleared worker remains attached.
- **Discard:** Joins capture first, then requests live-worker shutdown under the custody reservation (`session.py:838`). Successful shutdown clears buffers before deletion; timeout proceeds to deletion, as PR-MED-017 details.
- **Complete variants:** All three invoke `_stop_live_locked`, but all proceed after an unsuccessful stop (`session.py:711`, `:747`, `:775`).
- **Retirement:** Stops capture and requests live shutdown, then unconditionally drops the live handle and destroys the in-memory crypto (`session.py:1225`). The on-disk key remains, but an uncleared worker can become untracked.
- **Claimed worker:** `transcribe()` installs `transcribing` under the same lock that checks reservations (`session.py:627`, `:642`); `claim_live_transcriber()` detaches only inside that run (`:578`); Discard refuses while it runs (`:804`). The shipped callable’s `drain()` joins before returning, and its `finally` stops the worker before batch construction (`transcription.py:1971`; `ui/models.py:1590`). No claim/Discard crypto race found.
- **Recovered custody:** `complete_recovered`, `discard_recovered`, and `destroy_recovered_crypto` remain the existing recovered-session operations (`session.py:1046`, `:1055`, `:1063`); shipped recovery-list protection excludes the controller-owned session.
- **Threading:** Pause gates live feeding after the capture barrier; Resume opens that gate before capture resumes (`session.py:499`, `:518`). Store exceptions still propagate through the tee; live-feed exceptions become worker failures (`:142`). The shipped live callback emits a Qt signal rather than touching widgets. No new controller-lock dependency exists in the live worker’s shutdown path.
- **Parity/C8/C9:** The extracted batch tail preserves behavior, with collection normalization and explicit metadata arguments; recovery is unchanged. Segment release and packing match batch outside the documented forced close. All three live failure kinds have screen status lines. New production logging carries only session ID/state; transcript-word representations retain existing tripwire signatures. The outstanding bounds and validation gaps follow.

#### PR-MED-017 — [MED] `desktop/src/scribe_desktop/session.py:848` — An unsuccessful live-worker stop still permits custody deletion

- Triage: Fix-now.
- Fix route: premium-only.
- Why it matters: Discard can report success while its worker still holds consultation PCM and transcription products. This violates C7’s explicit requirement that those buffers be dropped before key destruction.
- Current behaviour: `stop()` correctly returns `False` while its thread remains alive (`transcription.py:1997`). Discard records that result, then unconditionally calls `discard_session` and drops the controller handle (`session.py:851`, `:865`, `:869`). The three Complete paths similarly ignore the helper’s unsuccessful shutdown. The existing timeout test explicitly expects deletion while the worker is still running (`test_live_session.py:373`–`:376`).
- Desired behaviour: An uncleared worker must prevent successful destructive completion. Retain a tracked, protected session and expose a recoverable stopping/failure state until shutdown is confirmed; allow retry without pretending recording continues.
- Pattern to follow: `CaptureWorker.stop()` refuses to return successfully while its thread remains alive (`audio_capture.py:425`–`:427`).
- Pattern siblings: The custody/stop search found `complete()` (`session.py:711`), `complete_without_note()` (`:747`), `complete_deleting_saved_note()` (`:775`), and retirement’s unconditional detachment (`:1232`–`:1237`). Start failure is distinct because consultation PCM has not been fed. The claimed shipped path joins in `drain()` before cleanup.
- Invariant: C7 requires Discard’s plaintext buffers to be gone before key destruction. D2’s AS-BUILT “the key still goes” exception conflicts with that constraint and with `session.py:815`; it does not establish the stronger guarantee requested here.
- Verification: Reading the blocked-provider test supplies a concrete admitted timeout case. Add event-gated checks that every destructive path preserves custody and worker ownership on timeout, then succeeds after release. No test executed during this review.
- Regression risk: Merely raising after capture stops could leave a session falsely presented as recording. Preserve appropriate state, sweep protection, leases and retry behavior. Severity is MED because the live worker holds no session crypto and no external disclosure was established.
- /fix decision: Applied
- /fix notes: Fail closed on every custody-destroying consumer of the stop helpers (`session.py`): `_stop_live_locked` now RETURNS the cleared verdict (True = nothing uncleared attached) and `_refuse_uncleared_live` raises the one `SessionActivityError` ("has not stopped yet; the session is kept - try again"); `discard()` refuses BEFORE `discard_session` — under the second lock, after `_record_live_stop_locked` logged and kept the worker attached, a session in RECORDING / PAUSED / pre-claim PROCESSING is routed to FAILED (its capture worker is already stopped and its store closed; key + chunks kept; Discard legal again) while QUEUED / FAILED stay as they are, `live.worker = None`, and the `finally` releases the reservation; the three Complete paths refuse and stay QUEUED (the held lease kept by `complete_without_note`'s existing contract); `_retire_locked` stops the live worker FIRST and refuses the retirement (handle + in-memory crypto kept, no new worker built) — the ONE caller allowed to ignore the verdict is `_fail_locked`, which destroys nothing; the `start()` failure path still stops with the short bound and proceeds because no tee ever fed that worker (no plaintext exists). Tests (`tests/test_live_session.py`): `test_a_stop_timeout_refuses_discard_keeps_the_key_then_succeeds` (×3: recording / paused / processing — refusal, FAILED, key present, timeout logged, reservation released, then the retry succeeds after the worker clears), `test_a_stop_timeout_refuses_complete_and_keeps_the_session_queued` (all three Complete paths refuse, the lease is kept, then Complete succeeds), `test_retire_on_start_refuses_while_a_timed_out_failure_left_a_worker_uncleared` (Start refused, no new worker, then succeeds). D2 AS-BUILT (3) rewritten to the enforced rule. Residue (UI copy, not custody): after a refused Discard the Session screen's 500 ms state watcher reports the FAILED transition with the generic "Recording failed (device lost or disk full)" line over the refusal message — the state and the remedy (Discard again) are right, the sentence is imprecise; a one-line UI follow-up for the confirmation round to weigh.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b6, same seat as LEG 1)

#### PR-MED-018 — [MED] `desktop/src/scribe_desktop/transcription.py:2083` — Continuous queue draining can bypass the plaintext backlog bound

- Triage: Fix-now.
- Fix route: premium-only.
- Why it matters: A slow VAD/contended machine can retain growing consultation PCM without triggering the promised windows-behind fallback.
- Current behaviour: `_drain_queue()` runs until `queue.Empty`, before `_process_ready()` checks the backlog (`:2021`–`:2023`). Each consumed chunk is removed from queue-byte accounting before `_ingest()` appends it to `_pcm` (`:2076`–`:2080`, `:2111`). The earliest ready window pins the retention floor (`:1703`, `:2138`). If arrivals keep the queue nonempty at roughly the ingestion rate, queue occupancy stays small while ready windows and retained PCM grow; the backlog check is never reached. A subsequent seal disables that check (`:2098`).
- Desired behaviour: Enforce the backlog/retained-PCM limit during ingestion, independently of whether the producer queue becomes empty. Bound each drain pass or otherwise guarantee timely processing/failure.
- Pattern to follow: The existing feed-time queue cap fails the worker when its limit is crossed (`:1923`–`:1934`); apply an equally enforceable bound to audio already transferred into worker-owned retention.
- Pattern siblings: Both `_drain_queue()` callers—`_run()` at `:2021` and `_process_ready()` at `:2106`—share this issue. `_handle` accounting, `_ingest`, and `_trim` form the retained-buffer side of the same path.
- Invariant: D2’s fall-behind cutoff and bounded plaintext retention must hold during continuous capture, including an ingestion bottleneck.
- Verification: The producer/consumer schedule follows directly from the loop and accounting order. The existing PCM-retention test explicitly avoids backlog and waits for previous posts (`test_live_transcription.py:858`, `:879`). Add a deterministic VAD/producer handshake that keeps queue occupancy low while crossing the permitted ready-window backlog.
- Regression risk: Preserve batch-equivalent window packing, cheap sealing, and the specified sealed-tail behavior. Avoid introducing blocking into the capture tee.
- /fix decision: Applied
- /fix notes: `transcription.py` `_ingest` evaluates the same windows-behind rule after every ingested chunk (the windows waiting behind the next one to run: `len(ready) - 1 > max_windows_behind` → `fell_behind`), so a drain pass that never empties the queue fails at the bound instead of ingesting the whole queue into the retention buffer; the pop-time check in `_process_ready` stays (equivalent at that point); the tee and `seal` are untouched (non-blocking, one sentinel); `_ingest` never runs after seal, so the sealed tail is still drained in full. Test: `tests/test_live_transcription.py::test_the_backlog_bound_fires_during_ingestion_not_only_at_a_window_pop` — twelve one-window utterances (72 s, under the 90 s queue cap) queued behind a blocked model load; on release the worker fails `fell_behind` having ingested fewer than half the bytes (≥ the 3 utterances the bound needs) and never calling the provider — before the fix the whole queue was ingested first.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b6)

#### PR-LOW-020 — [LOW] `.cursor/plans/plan-note-learning-and-styles.md:159` — The sealed-tail “≤ 5 windows” claim is not enforced

- Triage: Fix-now.
- Fix route: fix-on-fast.
- Why it matters: The plan states a quantitative resource bound that the implementation does not provide, independently of PR-MED-018.
- Current behaviour: The queue cap measures 90 seconds of PCM (`transcription.py:1405`–`:1409`), not three actual packed windows. Gaps split windows (`:1677`), and sealed processing bypasses the windows-behind check (`:2098`). For example, behind one blocked provider call, ten repetitions of one second of speech plus five seconds of silence fit within the queue cap; sealing before release allows substantially more than five windows to drain.
- Desired behaviour: State the actual enforced byte/duration bound and distinguish it from a variable packed-window count. Recalculate that bound after PR-MED-018.
- Pattern to follow: `transcription.py:1401` correctly describes the queue limit as windows’ **worth of audio**.
- Pattern siblings: The specified plan/code search found the numeric “≤ 5 windows” claim in D2’s AS-BUILT addendum. The inaccurate bound should also be corrected wherever reused in implementation verification; historical review records should remain historical.
- Invariant: A documented hard resource bound must follow from an enforcing structure.
- Verification: The short-utterance/gap fixture already used at `test_live_transcription.py:699` demonstrates why audio duration and packed-window count differ. The counterexample requires no queue starvation.
- Regression risk: Do not discard an otherwise legitimate sealed tail merely to preserve the inaccurate prose.
- /fix decision: Applied
- /fix notes: D2 AS-BUILT (plan `:159`) restated: the sealed tail is bounded in AUDIO — the queue cap's 90 s of PCM (three windows' WORTH) plus the ready backlog the cut-off admits — and the window COUNT depends on the gap structure (short utterances 5 s apart make many small windows); the "≤ 5 windows" figure is gone; the same sentence records that the backlog rule now also runs per ingested chunk (PR-MED-018). No code change; the sealed tail is still drained in full.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b6)

#### PR-LOW-021 — [LOW] `desktop/tests/test_integration_no_sockets.py:716` — Live socket polling starts after the only inference window finishes

- Triage: Fix-now.
- Fix route: fix-on-fast.
- Why it matters: The new test does not establish its claimed observation of live inference or tail draining, despite passing.
- Current behaviour: The child feeds one initial tone and then silence forever (`:642`). It prints `LIVE-POSTED` only after that window posts (`:651`–`:654`), and the parent waits for this marker before beginning socket polling (`:716`–`:719`). The post follows provider transcription and embedding (`transcription.py:2165`–`:2201`). The drain is sampled only after `TRANSCRIBED` (`test_integration_no_sockets.py:728`–`:730`).
- Desired behaviour: Make the polling interval demonstrably overlap a live provider call and the processing drain, using bounded entry/release gates or continuous polling with explicit overlap evidence.
- Pattern to follow: The existing batch integration leg waits for `MID-TRANSCRIBE`, polls while the child is gated, then sends `GO` (`test_integration_no_sockets.py:547`–`:551`).
- Pattern siblings: The same test’s drain observation has the same gap. Its docstring (`:697`–`:699`) and “poll spans … first window” comment (`:713`–`:715`) overstate the current coverage.
- Invariant: A phase-specific no-sockets observation must overlap the phase it claims to verify.
- Verification: Child input generation, marker ordering and parent polling order establish the gap statically. The existing real-model tests remain useful evidence, but do not repair this live-orchestration timing assertion.
- Regression risk: Use bounded gates and guaranteed child cleanup; do not replace the gap with sleep-based timing assumptions.
- /fix decision: Applied
- /fix notes: `tests/test_integration_no_sockets.py` `_LIVE_CAPTURE_CHILD`: a `GatedLiveProvider` blocks INSIDE the live worker's provider call on the batch leg's pattern — the first call (the window transcribed during capture) prints `MID-LIVE-TRANSCRIBE` and waits for `GO`, the second (the tail window drained after Finish) prints `MID-LIVE-DRAIN` and waits for `GO2`; both reads happen on the worker thread while the main thread is not reading stdin (FINISH only after LIVE-POSTED, CONTINUE only after the drain returned). After the first window posts the feeder switches to a continuous tone so an utterance is still OPEN at Finish and the drain has a tail window. The parent polls ten times while the child is provably inside live inference (the store must grow across the polls), sends GO, awaits LIVE-POSTED, sends FINISH, awaits MID-LIVE-DRAIN, polls ten times inside the drain, sends GO2, then the existing TRANSCRIBED / CONTINUE / COMPLETED-OK sequence; the child asserts exactly two provider calls and two segments (one live, one drained). Docstring and comments corrected to the coverage the gates enforce. FOLLOW-UP (leg b7, 2026-09-19): the composer's suite failed this leg deterministically (`gated.calls == 1`, no `MID-LIVE-DRAIN`) — a feed-timing gap in the CHILD, not an implementation gap: `LIVE-POSTED` was printed the instant the feeder switched to the second tone, the parent's `FINISH` arrived within milliseconds, so the "open" utterance held only a few 50 ms blocks — under the segmenter's 0.25 s minimum speech length — and `LiveSegmenter.finish()` correctly DROPPED it at the seal (the same short-span filter the batch path applies; D2's tail drain did run, it just had no window to transcribe). Traced: `seal()` → `_finalise_segments` → `finish()` closes the open span → `_close` filters `end − start < min_speech` → no segment → no window → no second call. Fixed in the child: the feeder counts its second-utterance blocks and the main thread announces `LIVE-POSTED` only once 20 blocks (a full second of tone, four times the minimum) have been fed — so the seal's close always yields a segment, a tail window and the gated second call, whatever the parent's round-trip timing; the feeder keeps the tone continuous until `stop`, so the span stays OPEN (a following silence would close it into a live window instead) and the 30 s forced cut is ~12 s of wall-clock stall away. Deterministic on this host by construction, not by timing.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b6)

#### LEG 1 verified tuples
- PR-MED-017: `materiality=behavioral severity=med surface=production rec=Fix-now` — CONFIRMED as a real path: `LiveTranscriber.stop()` returns `False` when `thread.join(timeout)` leaves the thread alive (`transcription.py:1993–1997`); `discard()` stores that verdict (`session.py:848`), `_record_live_stop_locked` only logs and keeps the worker attached (`:1198–1214`), and `discard_session` then runs unconditionally (`:865`) — so on a join timeout the key IS destroyed while the worker thread may still hold `_pcm` / `_marked` / `_embeddings` in memory until its blocked provider call returns and `_exit_cleanup` clears them; the three Complete paths (`:711`, `:747`, `:775`) and retirement (`:1225–1237`, drops the handle unconditionally) share the shape, and the D2 AS-BUILT text (3) documents the exception rather than the constraint. Said plainly: yes, that path lets the key go while plaintext MAY still be held — but only in process memory (the worker holds no session crypto, writes no file, and self-clears when its call returns; the hazard is bounded in-memory residue after a cryptographic deletion of the ON-DISK audio, with no persisted artefact and no disclosure path), which is why it verifies at MED, not HIGH. C7's literal second clause is nonetheless violated, so Fix-now: fail CLOSED on an uncleared stop — Discard raises `SessionActivityError` BEFORE `discard_session` (the reservation's `finally` releases; the capture worker is already stopped, so the session is routed to FAILED first from RECORDING / PAUSED / pre-claim PROCESSING — key + chunks intact, `Discard` legal again, the stopped worker retried idempotently on the next click as `CaptureWorker.stop` already is), the Complete paths raise and keep QUEUED (their existing failure contract), and `start()` refuses to retire a session whose worker is uncleared instead of dropping the handle; the timeout test inverts to refusal-then-success after the gate opens; D2 AS-BUILT (3) rewritten to the enforced rule.
- PR-MED-018: `materiality=behavioral severity=low surface=production rec=Fix-now` — CONFIRMED mechanism, downgraded on reachability: `_drain_queue` loops until `queue.Empty` (`transcription.py:2083–2090`) and the windows-behind check lives only in `_process_ready` (`:2098`), so a producer that keeps the queue non-empty at the ingestion rate never reaches the check while ready windows pin the retention floor (`:1703`, `:2138`) and `_pcm` grows; queue-byte accounting is decremented at dequeue (`:2076–2077`) before `_ingest` appends (`:2111`), so the feed-time cap does not cover it. The regime needs ingestion SLOWER than real-time capture — silero costs ~1 ms per 32 ms frame (~30× headroom; the measured pipeline RTF ≈ 0.5 is dominated by Whisper), so it takes a ≥30× VAD stall — hence LOW; the fix is mechanical (evaluate the backlog after each ingested chunk inside the drain loop, or bound a drain pass), keeping the tee non-blocking and the seal cheap.
- PR-LOW-020: `materiality=docs-only severity=low surface=docs rec=Fix-now` — CONFIRMED: `LIVE_QUEUE_CAP_BYTES` is 3 × 30 s of PCM (`transcription.py:1405–1409`), a duration not a packed-window count; with 1 s utterances 5 s apart (`:1677` splits on the gap) 90 s of queued audio is 15 windows, plus the ready backlog, and the sealed tail bypasses the count (`:2098`) — the D2 AS-BUILT "≤ 5 windows" (plan `:159`) is not what the structure enforces; restate as "the queue cap's 90 s of audio plus the ready backlog; the window count depends on the gap structure".
- PR-LOW-021: `materiality=behavioral severity=low surface=test-harness rec=Fix-now` — CONFIRMED: the child feeds one 0.6 s tone then silence forever (`test_integration_no_sockets.py:642`), prints `LIVE-POSTED` only after the window's provider + embedding call completed (`:651–654`, post at `transcription.py:2201`), and the parent starts polling only after that marker (`:716–719`) — the ten polls observe silent capture, not inference; the drain is sampled after `TRANSCRIBED` (`:728–730`). Fix like the batch leg: gate the child's provider (`MID-LIVE-TRANSCRIBE` printed inside the call during capture, parent polls, then `GO`) and gate the drain the same way; correct the docstring and comment.
- Cap verdict: accept — production-behavioral — one verified custody path (PR-MED-017) plus three mechanical items; the fix leg is followed by a confirmation round (round 2 of cap 5) because a custody change earns a re-read (Phase 6 lesson), well inside the cap (round 1 of cap 5).
- LEG 2 decisions: PR-MED-017 `Fix-now — applied 2026-09-19 14:04 (leg b6)`; PR-MED-018 `Fix-now — applied 2026-09-19 14:04 (leg b6)`; PR-LOW-020 `Fix-now — applied 2026-09-19 14:04 (leg b6)`; PR-LOW-021 `Fix-now — applied 2026-09-19 14:04 (leg b6)`.

PEER-ROUND-9 RESULT: 4 findings (CRIT 0 / HIGH 0 / MED 2 / LOW 2).

### Round 10 - 2026-09-19 - Phase 1 (Tasks 1.0–1.6), independent cross-family codex peer review (confirmation round, pass stage-1.p1)

- Round status: Closed (PR-LOW-022 and PR-LOW-023 applied in leg b9 and confirmed closed as a class by round 11)
- Source: Codex peer-review
- Baseline: `main` / `HEAD` at `0f3af9b987691504b74cf3e090dd895c76f91234`; uncommitted Phase 1 working tree.
- Files reviewed: Full scoped diffs for `desktop/src/scribe_desktop/session.py`, `desktop/src/scribe_desktop/transcription.py`, and `desktop/tests/test_integration_no_sockets.py`; changed test regions in `desktop/tests/test_live_session.py` and `desktop/tests/test_live_transcription.py`; supporting custody, capture-stop, UI-status, claimed-worker cleanup, and marker-reader code. Plan review limited to Round 9 and D2 AS-BUILT.
- Validation basis: Static reading only; no files written, tests executed, or network requests made. Composer-reported ruff, strict mypy, and pytest success accepted as supplied evidence. Diff statistics show 13 tracked changed files, plus the two untracked live-test files, consistent with the declared Phase 1 surface; statistics alone cannot establish hunk-level identity with round 9.
- Finding verification: 5 candidates / 3 dropped / 1 downgraded. Dropped: the recorded UI-message overwrite, unbounded growth from an oversized chunk or blocked provider alone, and loss of an early tail marker. The remaining silence-retention issue is LOW given the ingestion-starvation regime required.

#### Confirmed / disputed (round 9)

- **PR-MED-017 — Confirmed closed as a class.** Every `_stop_live_locked` caller is accounted for: `complete` (`desktop/src/scribe_desktop/session.py:713`), `complete_without_note` (`:750`), `complete_deleting_saved_note` (`:779`), `_fail_locked` (`:1205`), and `_retire_locked` (`:1265`). All destructive callers refuse on `False`; `_fail_locked` only closes the store and transitions to FAILED, retaining key and handle. Discard checks its direct stop verdict before deletion (`:855`, `:870`, `:884`), closes the store and marks stopped capture FAILED, and releases its reservation in `finally` (`:892`). Capture shutdown has already stopped the stream and joined its writer (`desktop/src/scribe_desktop/audio_capture.py:416`). Complete-without-note retains its lease on refusal (`session.py:750`, `:756`); retirement refuses before destroying in-memory crypto or dropping the session (`:1265`, `:1273`). Successful clearing alone detaches the attached worker (`:1228`). The other detachment is an ownership transfer inside the guarded transcription run (`:585`); the shipped owner joins in `drain()` and stops in `finally` (`desktop/src/scribe_desktop/transcription.py:1971`; `desktop/src/scribe_desktop/ui/models.py:1590`). Start-failure cleanup precedes any tee-fed consultation PCM (`session.py:479`), and recovered-session operations remain separate from controller-owned sessions, which stay sweep/recovery-protected (`:1044`). Retry is idempotent: `stop()` joins again, then clears and inspects buffers (`transcription.py:1990`); worker exit also clears stopped products (`:2240`). The shipped worker callback introduces no controller-lock dependency. Refusal and retry assertions are substantive at `desktop/tests/test_live_session.py:384`, `:426`, and `:502` and would fail on the pre-fix behavior.
- **PR-MED-018 — Partly confirmed; class closure disputed.** The per-chunk check closes accumulation of *additional ready windows* during uninterrupted queue draining (`desktop/src/scribe_desktop/transcription.py:2124`). A single incoming chunk is bounded by feed admission (`:1923`), and a blocked provider cannot concurrently grow `_pcm`; further arrivals remain queue-capped. However, one ready window can still pin arbitrarily much subsequent silence without increasing the ready-window count; see PR-LOW-022. The check also changes sealed-tail behavior; see PR-LOW-023. The new test is non-vacuous: its `_audio_bytes` assertion would fail when the entire queued fixture was ingested before the old pop-time check (`desktop/tests/test_live_transcription.py:748`), but it covers repeated utterances rather than long gaps.
- **PR-LOW-020 — Confirmed closed as the requested documentation correction.** D2 AS-BUILT now distinguishes 90 seconds of queued PCM from a variable packed-window count (`.cursor/plans/plan-note-learning-and-styles.md:159`). The removed five-window claim is no longer asserted there. The remaining retention enforcement problem is identified separately in PR-LOW-022.
- **PR-LOW-021 — Confirmed closed as a class.** Provider-entry gates cover both calls (`desktop/tests/test_integration_no_sockets.py:638`, `:642`); the parent polls before sending `GO` and `GO2` (`:767`, `:786`). Twenty second-utterance blocks precede `LIVE-POSTED`, providing a substantial open tail before Finish (`:698`). The normal sequence separates stdin readers: first provider gate → live post → main-thread FINISH → tail provider gate → completed drain → main-thread CONTINUE. Exactly two provider calls and two segments are required (`:726`). An early `MID-LIVE-DRAIN` relative to `TRANSCRIBING` is retained by the marker reader (`:290`), not discarded. Missing markers time out and kill/reap the child (`:314`), with final cleanup at `:800`; a blocked child cannot silently pass or hang the suite indefinitely. The pre-fix child would fail the new marker requirements.
- **Recorded UI-copy residue — Disputed; no finding.** `on_discard()` displays the refusal and synchronously calls `refresh()` (`desktop/src/scribe_desktop/ui/session_screen.py:217`). `refresh()` records FAILED in `_last_state` (`:144`), so the next timer tick returns without replacing the message (`:128`). The described overwrite does not occur on the shipped synchronous Discard path.

#### PR-LOW-022 — [LOW] `desktop/src/scribe_desktop/transcription.py:2124` — A ready window still pins unbounded PCM across subsequent silence

- Triage: Fix-now.
- Fix route: premium-only.
- Why it matters: The remaining ingestion-starvation case defeats the intended plaintext-retention bound despite the new per-chunk window-count check.
- Current behaviour: Once one utterance becomes a ready window, keep supplying VAD-negative chunks so `_drain_queue()` never observes an empty queue (`:2083`). Queue-byte accounting is reduced before ingestion (`:2076`), so occupancy can remain below its cap. Silence produces no additional ready windows; `behind` remains zero (`:2124`). `_trim()` nevertheless retains every byte from the first ready window onward (`:2148`), and processing that window is deferred until queue draining finishes. Retained PCM can therefore grow with the recording duration.
- Desired behaviour: Bound retained PCM independently of the number of subsequent speech windows, or guarantee that ready windows are processed during a bounded ingestion pass.
- Pattern to follow: The feed-time byte cap (`:1923`) enforces a measurable resource limit; worker-owned retention needs an equivalent enforceable limit or bounded scheduling.
- Pattern siblings: Searches for `_drain_queue`, `_ingest`, `_pcm`, and `retention_floor_seconds` identify both drain callers (`:2021`, `:2106`), the single ingestion path (`:2080`), and the retention-floor calculation (`:2148`). Both callers share this residual case.
- Invariant: A continuously nonempty producer queue must not allow consultation-length plaintext accumulation behind a bounded number of ready windows.
- Verification: Add a deterministic producer/VAD handshake that maintains small queue occupancy after one ready utterance while feeding prolonged silence. Assert bounded retained bytes or timely window processing. The existing new fixture generates additional windows (`desktop/tests/test_live_transcription.py:736`); the existing retention test deliberately waits for each previous post (`:918`), so neither covers this schedule. Static counterexample only; no test run.
- Regression risk: Preserve window packing, non-blocking feeding, cheap sealing, and legitimate sealed-tail draining. Severity is LOW because the schedule requires sustained ingestion contention; this is the remaining subclass of PR-MED-018, not a newly established disclosure path.
- Scope-expansion disposition: Within Task 1.1’s existing bounded-retention contract.
- /fix decision: Applied
- /fix notes: `transcription.py` `_drain_queue` now returns as soon as a window is ready (checked at the top of every iteration, so on entry too), handing it to `_process_ready` BEFORE more chunks are ingested; `_process_ready` already re-drains after every window, so the loop alternates ingest-until-ready / transcribe. The retained plaintext is therefore at most the window in progress plus the open span plus one chunk whatever the producer's pace — the peer's schedule (one ready utterance, then prolonged silence keeping the queue non-empty) processes the window before the silence is ingested and the floor moves on. THE FOUR REGIMES after both fixes: (1) real-time feed, provider keeping up — each window is transcribed as it becomes ready; retained ≤ one window + open span + one chunk; nothing fails. (2) Blocked or slow provider with a bounded queue — nothing is ingested during the call, audio accumulates in the QUEUE, bounded by `LIVE_QUEUE_CAP_BYTES` (90 s) at feed time; `feed` fails the worker `fell_behind` on the chunk that crosses the cap (fails closed at the producer, the tee never blocks); with the drain yielding at every ready window the pop-time / ingest-time windows-behind rule can no longer accumulate in normal operation and survives as a DEFENSIVE bound that fires only when one ingested chunk closes more than three windows (pinned by a 30 s five-utterance single chunk). (3) The starvation regime (ingestion slower than the producer) — the drain yields at the first ready window, so a ready window is never deferred behind later chunks; retained ≤ one window + open span + one chunk; the queue absorbs the excess up to the cap, then fails closed as in (2). (4) A sealed backlog — see PR-LOW-023: drains in full, bounded in audio by the queue cap at seal time. Tests (`tests/test_live_transcription.py`): the round-9 backlog test is REWRITTEN as `test_a_queued_backlog_is_processed_window_by_window_with_bounded_retention` (twelve queued utterances behind a blocked load: all twelve transcribed, retained peak ≤ one utterance + one chunk + the pad), NEW `test_a_ready_window_followed_by_long_silence_does_not_pin_the_buffer` (the peer's schedule: one window then 60 s of silence, peak ≤ 6 s of audio, never the recording), the old `test_falling_more_than_two_windows_behind_stops_the_worker` (which pinned the now-unreachable pile-up) is REWRITTEN as `test_a_provider_slower_than_the_feed_trips_the_queue_cap` (blocked provider, three windows' worth plus one chunk queued → `fell_behind` at feed time, one provider call) plus NEW `test_a_single_chunk_closing_many_windows_trips_the_defensive_backlog_bound`; the pacing test, the 90 s fixture and the cheap-seal test are unchanged. D2 AS-BUILT rewritten to the enforced schedule and bounds.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b9, same seat as LEG 1)

#### PR-LOW-023 — [LOW] `desktop/src/scribe_desktop/transcription.py:2125` — The ingestion check rejects a legitimate already-sealed backlog

- Triage: Fix-now.
- Fix route: premium-only.
- Why it matters: The fix can discard successful live work and force full batch retranscription after Finish, contrary to the retained sealed-tail contract.
- Current behaviour: `seal()` sets `_sealed` and appends a sentinel after queued PCM (`:1954`). Those queued chunks still pass through `_ingest()` before `_seal_seen` becomes true (`:2071`, `:2080`). The new count check is unconditional (`:2125`). For example, block the first provider call, queue five more one-second utterances separated by five-second gaps—well below the 90-second queue cap—call `seal()`, then release the provider. Ingestion fails on the fourth ready queued window before reaching the seal sentinel. Previously, draining reached that sentinel before the pop-time check, whose sealed exemption allowed the tail to complete (`:2098`).
- Desired behaviour: Preserve full draining of an admitted, finite sealed tail while retaining effective bounds during ongoing capture.
- Pattern to follow: D2 AS-BUILT explicitly exempts the sealed tail from the window-count cutoff (`.cursor/plans/plan-note-learning-and-styles.md:159`); coordinate producer-side sealing and consumer-side admission checks accordingly.
- Pattern siblings: The relevant sites are producer-side `seal()` (`:1954`), `_handle()`’s sentinel recognition (`:2071`), `_ingest()`’s unconditional cutoff (`:2125`), and `_process_ready()`’s existing sealed exemption (`:2098`). Searches for `_sealed`, `_seal_seen`, and `max_windows_behind` found no other backlog-check implementation.
- Invariant: Finish closes admission; an otherwise healthy, bounded queued tail must not become a fall-behind failure solely while being drained.
- Verification: Extend the blocked-provider fixture at `desktop/tests/test_live_transcription.py:693` with a separate case that seals before releasing the provider and expects all six windows to drain. The current cheap-seal test has only two windows (`:837`), below the rejection threshold. The proposed case distinguishes pre-fix success from current fallback by static control-flow tracing; no test run.
- Regression risk: Simply removing the ingestion check would reopen PR-MED-018. Resolve sealing semantics together with the independent retention bound, keeping `feed()` and `seal()` cheap.
- Scope-expansion disposition: Within the existing Task 1.1 lifecycle and sealed-tail contract.
- /fix decision: Applied
- /fix notes: Both cut-offs (`_ingest`'s and `_process_ready`'s) now read `self._sealed` — the seal as REQUESTED, set under `_state_lock` before the sentinel is enqueued — instead of `_seal_seen`: once Finish sealed, every chunk still queued is a finite tail already bounded by the queue cap at seal time and drains in full; `feed()` and `seal()` are untouched (non-blocking put, one sentinel). Test: NEW `test_a_sealed_backlog_drains_in_full_instead_of_falling_behind` — the peer's fixture (first provider call blocked, five more one-second utterances five seconds apart queued, `seal()`, release): no failure, six windows transcribed, six provider calls. Regime (4) in the PR-LOW-022 notes: a sealed backlog retains at most one window + open span + one chunk while draining and ends with the whole tail transcribed.
- /fix date: 2026-09-19
- /fix applied by: architect (leg b9)

#### LEG 1 verified tuples
- PR-LOW-022: `materiality=behavioral severity=low surface=production rec=Fix-now` — CONFIRMED mechanism: `_drain_queue` (`transcription.py:2083–2090`) runs to `queue.Empty` before `_process_ready` (`:2092`) is reached, so a ready window R sits unprocessed while later chunks are ingested; VAD-negative chunks add no ready window, `behind` stays 0 at `:2124`, and `_trim` (`:2148–2157`) keeps every byte from R's start (`_LiveWindows.retention_floor_seconds` = `ready[0][0].start`) — retained PCM grows with the silence. Reachability is the same starvation regime as PR-MED-018's downgrade: the producer must keep the queue non-empty at the ingestion rate, i.e. ingestion slower than real-time capture (~1 ms silero per 32 ms frame ≈ 30× headroom), and queue-byte accounting drops at dequeue (`:2076`) so the 90 s feed cap never trips — hence LOW. The clean closure is scheduling, not another counter: bound a drain pass so a ready window is processed promptly (e.g. `_drain_queue` returns as soon as a ready window exists, letting `_process_ready` run before more chunks are ingested; the queue is re-drained after every window at `:2106`), which also makes the retained buffer at most one window plus the open span plus one chunk in that regime.
- PR-LOW-023: `materiality=regression severity=low surface=production rec=Fix-now` — CONFIRMED, traced end to end: `seal()` sets `_sealed` under `_state_lock` (`:1960`) then puts `_LiveSeal` at the TAIL of the queue (`:1961`), behind every chunk queued while the provider was blocked; the worker's `_drain_queue` dequeues those chunks first, each through `_ingest` (`:2080`) whose cutoff at `:2124–2129` reads only `len(ready)` — `_seal_seen` is still False (`:2072`) — so with five one-window utterances queued (30 s, under the 90 s cap) the FOURTH ready window fails `fell_behind` before the sentinel is reached; before the round-9 fix the sentinel was consumed inside the same drain and the only cutoff (`_process_ready`, `:2098`) was sealed-exempt, so the tail drained in full. A behavioural regression of the D2 sealed-tail contract introduced by the PR-MED-018 fix; LOW because the failure degrades to the batch closure with its C8 line (the transcript is still correct and complete, the live work is discarded and Finish costs a full re-transcription). Fix: the ingestion cutoff must honour the seal as REQUESTED, not as seen — `self._sealed` is set before the sentinel is enqueued, so once it is True every remaining queued chunk belongs to a finite tail already bounded by the queue cap at seal time; guard `:2125` (and, for consistency, `:2098`) with `not self._sealed`; the peer's proposed six-window sealed fixture pins it.
- Cap verdict: accept — production-behavioral — two LOWs, both mechanical and inside Task 1.1's retention/tail contract; a round-11 confirmation IS warranted after the fix leg (round 3 of cap 5) because the change re-schedules the drain/ingest loop, which is the plaintext-bound surface C7 names, and the round-10 lesson stands: a bound moved by a fix earns a fresh cross-family read (round 2 of cap 5).
- LEG 2 decisions: PR-LOW-022 `Fix-now — applied 2026-09-19 16:58 (leg b9)`; PR-LOW-023 `Fix-now — applied 2026-09-19 16:58 (leg b9)`.

PEER-ROUND-10 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 2).

### Round 11 - 2026-09-19 - Phase 1 (Tasks 1.0–1.6), independent cross-family codex peer review (second confirmation round, pass stage-1.p1)

- Round status: Closed — No new findings — converged
- Source: Codex peer-review
- Baseline: `main` / `HEAD` at `0f3af9b987691504b74cf3e090dd895c76f91234`; uncommitted Phase 1 working tree.
- Files reviewed: Full `desktop/src/scribe_desktop/transcription.py` diff; the five specified tests and supporting fixtures in `desktop/tests/test_live_transcription.py`; supporting Finish/capture-stop ordering in `desktop/src/scribe_desktop/session.py` and `desktop/src/scribe_desktop/audio_capture.py`. Plan assessment restricted to Round 10 and D2 AS-BUILT.
- Validation basis: Static reading and control-flow tracing only; no writes, tests, or network requests. Composer-reported clean ruff, strict mypy over 34 source files, and green pytest accepted as supplied evidence. `git diff --stat` shows 13 tracked changed files, 2,375 insertions and 69 deletions; status additionally shows the two untracked live-test files. This matches the recorded Phase 1 file surface; statistics alone cannot prove hunk-level identity with round 10.
- Finding verification: 3 candidates / 3 dropped / 0 downgraded. Dropped after tracing: loss of the newly opened span’s retention floor, a seal/cutoff ordering regression on the shipped path, and queue starvation caused by yielding between windows.

#### Confirmed / disputed (round 10)

- **PR-LOW-022 — Confirmed closed as a class.** `_drain_queue` checks readiness before every dequeue (`desktop/src/scribe_desktop/transcription.py:2092`); `_process_ready` transcribes, trims, and re-drains after each window (`:2117`). A ready window therefore cannot pin later chunks indefinitely. PR-MED-018’s accumulation class stays closed: multiple ready windows can arise within one admitted chunk, but the ingestion cutoff remains (`:2140`), and no further chunk is ingested while ready work remains.
- **PR-LOW-023 — Confirmed closed as a class.** Both cutoffs use requested sealing (`desktop/src/scribe_desktop/transcription.py:2111`, `:2141`), published before the sentinel (`:1960`). The shipped Finish path joins capture before sealing (`desktop/src/scribe_desktop/session.py:539`, `:565`; `desktop/src/scribe_desktop/audio_capture.py:425`), so the exemption drains an admitted, finite tail.
- **Recorded CONSEQUENCE — Confirmed.** With normal one-second capture chunks, ready windows are processed before another chunk is admitted to worker retention. A slow provider leaves arrivals in the byte-capped queue; `feed` records `FELL_BEHIND` before enqueueing the over-cap chunk (`desktop/src/scribe_desktop/transcription.py:1923`). The window-count checks remain defensive protection against multiple windows closed within one oversized chunk, as recorded in D2 AS-BUILT (`.cursor/plans/plan-note-learning-and-styles.md:159`).

**C7 retention in the four regimes**

The stated retention bound describes the worker’s retained audio span; the separately capped queue and bounded processing copies also hold plaintext.

| Regime | Retention and enforcing control |
|---|---|
| Real-time feed, provider keeping up | The worker retains the current window, unresolved span, and at most one newly ingested chunk. Ready work is processed before another dequeue (`transcription.py:2092`, `:2117`). |
| Blocked provider, bounded queue | Ingestion stops during the provider call. Worker retention stays fixed; incoming PCM occupies the separately capped queue. The first over-cap feed fails closed (`transcription.py:1925`, `:1931`). |
| Starvation schedule | Once a window becomes ready, draining yields before consuming later silence. After transcription, trimming releases its old floor; subsequent silence cannot preserve that window’s PCM (`transcription.py:2092`, `:2118`, `:2164`). Excess arrivals remain queue-capped. |
| Sealed backlog | The same alternating schedule bounds worker retention while the finite admitted queue drains. Sealing exempts the window-count checks, not the feed-time admission cap (`transcription.py:1915`, `:2111`, `:2141`). |

A chunk that closes a window and opens another span does not lose the latter’s audio: the segmenter retains its padded or hard start (`desktop/src/scribe_desktop/transcription.py:1523`), the packer retains its earliest ready/open window (`:1702`), and `_trim` takes the minimum (`:2164`). Processing the old window releases only audio preceding the remaining floor.

Queue occupancy **can** stay below the byte cap while an oversized chunk creates several ready windows inside `_ingest`; this is precisely the defensive case. The chunk itself passed byte admission, the per-chunk cutoff catches excessive unsealed readiness, and yielding prevents accumulation across further chunks (`desktop/src/scribe_desktop/transcription.py:2123`, `:2140`).

**Sealing order and liveness**

`_sealed` changes only from false to true (`desktop/src/scribe_desktop/transcription.py:1830`, `:1960`). Observing true before consuming the sentinel is intentional and cannot exempt a run that was never sealed. A cutoff that reads false immediately before a concurrent seal may still commit an already-qualified unsealed failure; sealing does not undo an earlier failure decision. Normal capture chunks cannot create that defensive overflow, and the shipped capture join prevents feed/sentinel overlap. No legitimate already-sealed tail rejection was found.

Yielding introduces no wait between windows: processing immediately re-drains the queue (`desktop/src/scribe_desktop/transcription.py:2119`). A keeping-up worker therefore continues consuming arrivals; sustained excess processing time remains the intended fall-behind condition. `feed` and `seal` retain their short accounting/state sections and unbounded-queue puts, with no provider wait or join (`:1910`, `:1954`).

**Five-test verification**

- `test_a_queued_backlog_is_processed_window_by_window_with_bounded_retention` requires twelve results/posts and bounded measured retention (`desktop/tests/test_live_transcription.py:787`). The pre-fix drain fails during backlog ingestion.
- `test_a_ready_window_followed_by_long_silence_does_not_pin_the_buffer` requires one result and a retention peak of at most six seconds (`desktop/tests/test_live_transcription.py:819`). The pre-fix drain retains the minute-long silence behind the ready window and violates the assertions.
- `test_a_sealed_backlog_drains_in_full_instead_of_falling_behind` seals before releasing the blocked provider, then requires six calls and six segments (`desktop/tests/test_live_transcription.py:839`). The complete pre-fix implementation fails its ingestion cutoff.
- `test_a_provider_slower_than_the_feed_trips_the_queue_cap` inspects failure **before releasing the provider**, then requires a failing drain, exactly one provider call, and cleared buffers (`desktop/tests/test_live_transcription.py:713`). This substantively proves producer-side failure.
- `test_a_single_chunk_closing_many_windows_trips_the_defensive_backlog_bound` requires failure before any provider call, then a failing drain and cleared buffers (`desktop/tests/test_live_transcription.py:741`).

The last two are preservation tests and also pass the round-10 implementation; they do not claim newly introduced behavior. None is vacuous. The six-window test distinguishes the complete pre-fix implementation, though yielding alone also makes that fixture pass; the requested-seal guards were independently verified by reading.

PEER-ROUND-11 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).
