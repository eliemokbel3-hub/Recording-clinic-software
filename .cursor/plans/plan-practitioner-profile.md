# Feature Implementation Plan
**Feature:** practitioner-profile
**Overall Progress:** `0%`

## Lifecycle State
- Active

## Completion Status
- Completion timestamp:
- Main implementation complete: No
- Ready for archive: No

## Plan Lineage
- Parent plan: None (sibling of `plan-phase3a-note-pipeline.md`, which keeps the practitioner-owned gates 2.3 / D-S1 / 9.1 / 9.2; this plan records the Task 9.1 run PAUSE there by pointer — Task 0.1 — and never duplicates those tasks)
- Follow-up plans: None yet (Phase 3B — the local `gpt-oss-20b` note model — is scoped in the Phase 3A plan's `Deferred — Actionable Later` and will consume this plan's cue file and learned phrasing; see `Deferred — Actionable Later` below)

## Goal
Make the app adapt to the one practitioner who uses it, without ever keeping anything about a patient. Three pieces, built in this order: (1) **voice enrolment** — a one-time read-aloud at first run produces an encrypted, locally stored voice fingerprint, so every stretch of speech in a consultation is classified "the practitioner" or "someone else" instead of guessed from a two-way clustering plus wording hints, and the clinician role on the Transcript screen is confirmed automatically from it (practitioner-decided 2026-09-05: unconditionally whenever a profile exists, with a visible one-click change); (2) a **per-practitioner cue file** — the phrases that route a spoken sentence into a note section become a fourth clinician config file, bound into the note's config digest, so each practitioner's phrasing works on their own install; (3) **consented phrase learning** — during review the practitioner can add one of their own transcript lines to a section and, on explicit approval, save the phrasing to their cue file. All local, all encrypted or clinician-authored, all deletable. The Task 9.1 shipping-gate RUN is paused (its rubric v1 stays ratified and frozen) until enrolment ships, so ONE set of mock recordings serves the gate, Task 2.3 and the enrolment measurement.

## Planning Extraction Summary
Populated 2026-09-05 from the confirmed `/explore` scratch `.cursor/plans/explore-practitioner-profile.md` (practitioner profile, 2026-09-05) plus the three practitioner answers and the two follow-up decisions recorded in that session.

**Workflow Schema:** v22

**Executor tier:** entirely premium — planned on Fable 5.1; executor Fable/Opus-class via `/execute-loop`; tier-gap dosing applied (design decisions locked, edge-case inventory, contracts, per-task acceptance criteria, executor-facts block); every task is premium-only in substance (DPAPI custody, a biometric artefact, the windowed plaintext bound in `transcribe_session`, the confirm-first guards, the security docs)

### Agreed Scope (Build Now)
- **Sequencing (practitioner-decided 2026-09-05): enrolment FIRST, then the cue file, then learning.** The Task 9.1 shipping-gate RUN is PAUSED — rubric v1 stays ratified and frozen, nothing is re-ratified — until enrolment ships, so that ONE set of mock recordings serves three purposes: the gate's scoring, Task 2.3's before/after speaker measurement, and the enrolment measurement. Recording protocol for that set (Task 6.1): each mock consultation is recorded through the app (the gate's instrument) AND in parallel by an external recorder to a 16 kHz mono 16-bit WAV with an Audacity role-label track (the harness's input contract), with a second real voice speaking the patient part (round 1 PR-MED-013), plus one separate enrolment WAV of the practitioner reading aloud; the WAVs fall under the Task 2.3 retention decision.
- **Piece 1 — voice enrolment** (Phases 0–3): (a) a local ONNX speaker-embedding model added to `scripts/setup-models.py` (SHA-256-pinned, offline-asserted, `SileroVad`-style load contract, UNC refusal), fetched by the practitioner from a normal terminal, with the existing spectral 2-means path as the VISIBLE fallback when the model or profile is absent; (b) a **Practitioner** tab plus a first-run prompt carrying the consent/disclosure text and checkbox, a ~60 s read-aloud captured through `CaptureBackend` directly into memory (never through `SessionController`; PCM embedded, then dropped — no audio written anywhere), re-enrol and delete; (c) a profile store `%LOCALAPPDATA%\ClinikoScribe\profile\` holding `key.dpapi` (DPAPI-wrapped, the session-key primitives) and `voice.enc` (AES-GCM: the embedding, model id + SHA, created_at, the consent record) — deletion is key deletion; (d) in `transcribe_session`, per-segment model embeddings computed inside the existing windowed loop; with a profile present each segment is scored against the enrolled vector, the practitioner-matched segments get one label and the remaining segments are 2-means-clustered among themselves (labels: `speaker_1` is the practitioner whenever a profile is applied, the others `speaker_2` / `speaker_3` by first appearance — D13); when NO segment clears the threshold the ordinary 2-means over all segments runs and the cluster with the higher mean similarity is the practitioner (D4 is unconditional); both transcription entry points — live Finish (`build_transcriber`) AND crash recovery (`build_recovery_runner` → `recover_session_transcription`) — apply the profile; without a profile the current path runs unchanged; (e) the Transcript screen confirms the clinician role AUTOMATICALLY from the profile — the best-matching cluster, unconditionally whenever a profile exists (practitioner-ratified 2026-09-05; Design Decision D4) — showing "Clinician: confirmed from your voice profile" with a one-click change back to the manual radios; the manual radios remain the path when no profile exists; (f) `speaker_eval.py` gains an "enrolled" condition and an auto-confirm outcome, documented in `docs/testing/speaker-measurement.md`; (g) threat model (a new surface: the practitioner's own biometric at rest; the auto-confirm relaxation as a practitioner-ratified responsibility boundary), retention row, data-flow-map flow, design-system convention for the first-run surface, `AGENTS.md` Local Run Steps.
- **Piece 2 — the per-practitioner cue file** (Phase 4): a fourth clinician config file `section_cues.json` (`schema_version: 1`, `{section_key: [phrase, ...]}`) shipped as `config_defaults/section_cues.json` carrying today's 98 phrases across the 17 canonical keys; loaded by `load_note_config` with the SAME per-file whole-file replacement (practitioner-confirmed 2026-09-05), first-run default, loud failure and `_TriggerText` validation; a new `NoteConfig.section_cues` field so `config_digest` binds every note to the cue set that routed it; duplicate normalised phrases (within or across sections) refused at validation; `build_note_generator` constructs the provider FROM the config; `DEFAULT_SECTION_CUES` derived from the shipped file (one source); the gate-run cue file `docs/testing/shipping-gate-config/section_cues.json` authored from the practitioner's phrases.
- **Piece 3 — consented phrase learning, with review edits** (Phase 5): an explicit "Edit the note" control group on the Note tab (the transcript panel itself stays a non-interactive text box): (i) **Add a transcript line** — a chooser listing the eligible utterances, a section chooser limited to what that utterance may enter under the existing ownership rules (a clinician-owned section accepts only the confirmed clinician's non-question utterances), and Add, which inserts the whole utterance as a `transcript`-provenance assertion (contiguous coords, its own assertion-id scheme, refused when the utterance is already anywhere in the note); (ii) **Remove line** and **Move line to section…** for any `transcript`-provenance assertion the router produced (practitioner-decided 2026-09-05, Fix now at the hardening gate) — removal only ever subtracts, is reversible until Save, and any resulting omission warning is acknowledgeable, never blocking (D14); a move is remove + add under the same ownership rules; (iii) after an add or a move of one of the practitioner's OWN utterances, when learning opt-in is on, "Learn this phrasing?" shows the exact phrase (the utterance's leading content tokens, editable) and the exact line that would be appended to the practitioner's `section_cues.json` — saved only on explicit approval; a removal teaches nothing. The Practitioner tab lists and deletes learned phrases. Automatic pattern mining is out. The gate doc's R3 wording is clarified for a run in which removal exists — the precise population and exclusions are Task 5.5's (round 2 PR-LOW-018) — a clarification of rubric v1, not a threshold change.
- **Cross-cutting**: the consent text (drafted in `Config / Environment / Deployment Impact`, ratified by the practitioner in Task 0.2), the Phase 3A plan + `AGENTS.md` pause pointer (Task 0.1), CHANGELOG, and the measurement run once the recording set exists (Phase 6).

### Deferred — Actionable Later
- Estimated speaker count among the NON-practitioner voices (D-S1's estimated-k)
  - Why deferred: enrolment removes the worst failure (the practitioner merged with someone else); patient-vs-bystander separation stays 2-means until the recording set shows whether more is needed. Already deferred in the Phase 2 and 3A plans; this plan changes the problem, not the deferral.
  - Intended future outcome: k estimated (silhouette or agglomerative threshold) over the non-practitioner segments only.
  - Relevant files / subsystems: `transcription.py` `_cluster_embeddings`, `speaker_eval.py`, the Phase 3A plan's D-S1 task.
  - Dependencies / prerequisites: the Task 6.1 recording set measured under the enrolled condition.
  - Recommended next action: decide D-S1 in the Phase 3A plan with this plan's harness numbers.
  - Risk if deferred: ux-degradation: two non-practitioner voices share one label and the clinician corrects attribution on review.
  - Revisit by: the Phase 6 measurement run
- Phase 3B model-side personalisation (showing the local note model the practitioner's confirmed phrasing at generation time)
  - Why deferred: no model yet; belongs to the Phase 3B plan, which consumes this plan's cue file and learned phrases as its per-practitioner input.
  - Intended future outcome: per-practitioner drafts in the practitioner's own phrasing without training any model.
  - Relevant files / subsystems: the Phase 3B provider behind `NoteModelProvider`; `note_config.py` cue and phrase data.
  - Dependencies / prerequisites: Phase 3B planned; this plan's Phases 4–5 shipped.
  - Recommended next action: name it in the Phase 3B plan's scope when that plan is created.
  - Risk if deferred: minor: extractive routing stays the only personalisation until 3B.
  - Revisit by: Phase 3B planning
- Multi-practitioner profiles on one Windows login
  - Why deferred: the app is single-practitioner per Windows user account today (per-user named mutex, per-user config and sessions roots); a second practitioner on the same login would be classified "someone else", which is visible at the auto-confirm line and correctable with one click.
  - Intended future outcome: a profile chooser at start of session, if commercialisation puts two practitioners on one login.
  - Relevant files / subsystems: `practitioner_profile.py` (new), `ui/practitioner.py` (new).
  - Dependencies / prerequisites: a commercial deployment model.
  - Recommended next action: none until commercialisation.
  - Risk if deferred: minor: not a supported deployment today.
  - Revisit by: commercialisation

### Excluded — Revisit Only If Needed
- Any cloud or network path for learning, embeddings or telemetry
  - Why excluded: PLAN.md — no cloud processing of audio or transcripts; the ONE sanctioned network step stays `scripts/setup-models.py`, run by the practitioner.
  - When to revisit: never for clinical data; a hosted commercial variant would be its own plan.
  - Relevant files / subsystems: `benchmark.assert_offline_env`, `speech.py`, the new `speaker_embedding.py`.
  - Recommended next action (if any): none.
- Training or fine-tuning any model on consultations or on the practitioner's phrases
  - Why excluded (practitioner-confirmed 2026-09-05 after discussion): the training data would be consultations (patients' words) kept and replayed, which the app's retention promise forbids; the local 20B model needs GPU-class hardware and a torch stack the project avoids; a few hundred practitioner sentences barely move such a model while showing them at write time works immediately; and a model trained to sound like the practitioner learns to GUESS like them — the opposite of the ratified "never add what was not said" rule. Learning here is a stored phrase list and one voice vector, both approved by the practitioner.
  - When to revisit: only if Phase 3B's evidence shows generation-time conditioning on approved phrasing is insufficient — then as its own project with its own privacy design.
  - Relevant files / subsystems: Phase 3B provider.
  - Recommended next action (if any): none.
- Retaining enrolment audio or any patient audio/text for learning; enrolling anyone but the practitioner
  - Why excluded: the profile holds a numeric fingerprint, never a recording; patients are never profiled. Structural in Tasks 1.3 and 5.1.
  - When to revisit: never.
  - Relevant files / subsystems: `enrolment.py` (new), `practitioner_profile.py` (new).
  - Recommended next action (if any): none.
- Automatic, unapproved learning ("the app noticed and saved it" without a click)
  - Why excluded: the practitioner's rule — nothing is written that the practitioner did not say or approve; every learned phrase is shown exactly as it will be saved and saved only on approval.
  - When to revisit: never as silent behaviour; a "suggestions queue" the practitioner reviews later would be a UX refinement of the same rule.
  - Relevant files / subsystems: `ui/note.py`, `ui/practitioner.py`.
  - Recommended next action (if any): none.
- Inferring cue DELETIONS from removals ("negative learning")
  - Why excluded: a removed line says the router was wrong once, not that the phrase never belongs there; silent narrowing of the practitioner's own cue file is the unapproved-learning class in another coat. The practitioner deletes phrases explicitly on the Practitioner tab.
  - When to revisit: if Phase 6's R3 numbers show one cue misrouting repeatedly — then as a proposed deletion with approval, never inferred.
  - Relevant files / subsystems: `ui/note.py`, `ui/practitioner.py`.
  - Recommended next action (if any): none.
- Writing "practitioner" into `TranscriptSegment.speaker`
  - Why excluded: three pinned guards and the note checker assume opaque cluster labels plus a SEPARATE confirmed role; the enrolment result travels as a separate document field (Schema / Data Changes) that the UI turns into the confirmed role.
  - When to revisit: never.
  - Relevant files / subsystems: `transcription.py`, `note.py` `speaker_role`, `note_check.py`.
  - Recommended next action (if any): none.

### Accepted Assumptions — Revalidate Later
- An ungated, redistributable ONNX speaker-embedding model of WeSpeaker / ECAPA class runs on onnxruntime CPU under Python 3.12–3.14 with acceptable per-segment latency, and its input front-end (Kaldi-style 80-bin log-mel fbank, 25 ms / 10 ms, per-utterance mean normalisation) can be reproduced in numpy to the accuracy the model needs.
  - Why accepted for now: the Phase 2 plan already names this model class as the in-family upgrade; onnxruntime is already a dependency; the front-end is a bounded numeric recipe. Resolved early by Tasks 0.3–0.5 (practitioner fetch + smoke + decision D-P1).
  - Risk if assumption becomes false: enrolment falls back to the CMN'd spectral embedding, which is loudness-invariant but not microphone/room-invariant; the harness shows it; the plan carries the fallback as a measured, VISIBLE degradation (Design Decision D2), never a silent one.
  - Trigger for revisit: D-P1's smoke shows same-speaker cosine similarity not clearly separated from different-speaker similarity on the practitioner's own recordings.
  - Recommended next action: try the second candidate; if both fail, ship enrolment on spectral features and re-open the model choice as a follow-up.
- The practitioner's voice is stable enough across days, rooms and microphones for cosine matching plus re-enrolment.
  - Why accepted for now: speaker-embedding models are trained for exactly this invariance; re-enrolment is one minute.
  - Risk if assumption becomes false: misattribution reappears; with unconditional auto-confirm (D4) a patient's sentence can be attributed to the practitioner until the practitioner clicks "change" — mitigated by the visible similarity value, the checker, review at signing, and re-enrolment.
  - Trigger for revisit: the Phase 6 measurement shows auto-confirm correctness below the Phase 3A harness's current role accuracy, or the practitioner reports wrong-side attribution in use.
  - Recommended next action: re-enrol on the current microphone; if still wrong, revisit D4's unconditional trigger (a margin-based fallback is drafted in D4's rejected alternatives).
- One practitioner per Windows user account.
  - Why accepted for now: the app is single-instance per user, config and sessions are per user; both clinics are one practitioner.
  - Risk if assumption becomes false: a second practitioner is "someone else" — visible, correctable, deferred above.
  - Trigger for revisit: commercialisation.
  - Recommended next action: none.
- Task 2.3's labelled recordings (still owed) double as the enrolment measurement set and the gate's consultations (Task 6.1's single recording protocol).
  - Why accepted for now: practitioner-decided 2026-09-05 — one recording set, everything built from it.
  - Risk if assumption becomes false: enrolment ships measured only on synthetic tests until the set exists; Phase 6 MEASURES auto-confirm and can trigger a reassessment of D4 (Task 6.2); D4 itself is on whenever a profile exists (round 2 PR-LOW-018).
  - Trigger for revisit: the recording set is not produced before Phase 6.
  - Recommended next action: none — the practitioner owns Task 6.1.
- Practitioner-decided 2026-09-05: storing the practitioner's own voice embedding (encrypted) and approved phrases (plain-text config) locally, with disclosure and consent at first run, is acceptable.
  - Why accepted for now: the practitioner asked for it, with disclosure from start-up.
  - Risk if assumption becomes false: none for patients (nothing of theirs is stored); the practitioner deletes both from the Practitioner tab at any time.
  - Trigger for revisit: the consent text ratification (Task 0.2) changes the terms.
  - Recommended next action: none.

### Key Design Decisions
- Enrolment is evidence that the UI turns into the confirmed role; the transcript keeps opaque cluster labels (D1).
  - Why: three pinned guards and the checker assume labels are opaque and the role is separate; the enrolment result travels as its own document field.
  - Alternatives rejected: a `practitioner` label written by the pipeline.
  - Still applies to follow-up work: Yes
- Practitioner-vs-other first, then cluster the rest; no profile → today's path unchanged (D2/D3).
  - Why: no behaviour change until the practitioner enrols; the fallback is the shipped pipeline, visibly reported.
  - Alternatives rejected: estimated-k as the first step (D-S1 stays deferred).
  - Still applies to follow-up work: Yes
- Auto-confirm the clinician role UNCONDITIONALLY whenever a profile exists, best-matching cluster wins, one-click change visible (D4 — practitioner-ratified 2026-09-05 after the guarded alternative was offered and declined).
  - Why: the practitioner's product decision; the manual step's protection is replaced by the visible confirmation line, the similarity value, the checker and review at signing.
  - Alternatives rejected: margin-gated auto-confirm with manual fallback (offered; declined); auto-confirm removed entirely (the practitioner's original ask).
  - Still applies to follow-up work: Yes — recorded in the threat model as a responsibility boundary.
- The profile store mirrors session custody, not config (D5).
  - Why: the embedding is biometric; DPAPI-wrapped key + AES-GCM blob; deletion is key deletion; the consent record lives inside the blob.
  - Alternatives rejected: plaintext JSON beside the config files.
  - Still applies to follow-up work: Yes
- Cue file semantics = whole-file replacement, like the other three config files (D6 — practitioner-confirmed 2026-09-05).
  - Why: one precedence rule; the loader's rationale ("merge semantics are where never-partially-applies goes to die") is kept; the shipped defaults become a real file the practitioner or Phase 5 edits.
  - Alternatives rejected: an additive user file merged over defaults.
  - Still applies to follow-up work: Yes
- Cues enter the config digest (D7).
  - Why: every note is bound to the cue set that routed it, exactly as for autofill rules.
  - Alternatives rejected: cues as a constructor argument outside the digest.
  - Still applies to follow-up work: Yes
- Enrolment capture bypasses the session store by construction (D8).
  - Why: a short capture through `CaptureBackend` into memory, embedded, then released; nothing on disk but the encrypted vector.
  - Alternatives rejected: reusing `SessionController.start` (creates a recoverable audio artefact).
  - Still applies to follow-up work: Yes
- Learning is propose-then-approve, practitioner utterances only, after an add OR a move (D9).
  - Why: the eligibility check is structural (utterance attributed to the confirmed clinician), the stored artefact is a phrase in the practitioner's own cue file, and the UI shows exactly what will be saved.
  - Alternatives rejected: mining declined/removed lines silently; a context menu on the transcript panel (the panel is a non-interactive text box — an explicit chooser control is used instead).
  - Still applies to follow-up work: Yes
- Label scheme with a profile applied: `speaker_1` = the practitioner, `speaker_2` / `speaker_3` = the others by first appearance; zero matches → ordinary 2-means, highest mean similarity wins (D13).
  - Why: D4 is unconditional, so `enrolled_speaker` must always be set when a profile is applied; a fixed practitioner label keeps the document self-describing; the UI renders any label string (verified).
  - Alternatives rejected: leaving `enrolled_speaker` unset on zero matches (contradicts D4); keeping "first segment is speaker_1" on the profile path (meaningless once labels carry a role).
  - Still applies to follow-up work: Yes
- Review edits — remove and move a routed line — subtract only, reversible until Save, warnings acknowledgeable (D14; practitioner-decided 2026-09-05, Fix now).
  - Why: a wrongly routed line no longer has to wait for Cliniko; removal cannot introduce content, so the confirm-first guarantees are untouched; a move is remove + add under the ownership rules.
  - Alternatives rejected: editing in Cliniko only (the original exclusion); free-text editing of assertions (would break byte-identical reconstruction, Check 1).
  - Still applies to follow-up work: Yes
- Recording before enrolment stays allowed; the first-run surface asks, never blocks (D10).
  - Why: with no profile the pipeline is today's; blocking would stop a practitioner with an incomplete model setup for no safety gain.
  - Alternatives rejected: mandatory enrolment before any recording.
  - Still applies to follow-up work: Yes — the practitioner may harden it later.
- Model candidate verification is a practitioner-run step, then a `[decision]` (D11 — practitioner-confirmed 2026-09-05).
  - Why: agent shells never fetch models (MSIX-virtualised LOCALAPPDATA; the one network step is user-run).
  - Alternatives rejected: the executor fetching from a probe.
  - Still applies to follow-up work: Yes

## Key Findings

### Files / Symbols Involved
Verified 2026-09-05 at `main` `8527ce9` (re-probed at plan-write time; all present and tracked).

**Speaker labelling — what enrolment replaces the guess in**
- `desktop/src/scribe_desktop/transcription.py`: `_segment_embedding(pcm, np, *, sample_rate=16000, cepstral_mean_normalisation=True)` (24 mel-band log powers + low-band centroid over 25 ms Hann windows, CMN per segment); `_kmeans_two`; `_cluster_embeddings(embeddings, np) -> list[str]` (z-score, 2-means, first segment ALWAYS `SPEAKER_1`, degenerate → all `SPEAKER_1`); `label_speakers(...)` whole-list wrapper (tests + harness). `transcribe_session` (`:886`) embeds each VAD segment INLINE per ~30 s window (`:960-990`) to bound plaintext and clusters once at the end; the degenerate policy is duplicated at both sites with a "change together" comment (round 42 LOW-011). `SPEAKER_1/2` constants; `TranscriptSegment.speaker: str`; `TranscriptDocument(schema_version=1, session_id, created_at, model_name, sample_rate, transcript_segments)`.
- Pinned behaviours (`tests/test_transcription.py:455-511, 700, 865`): single/identical → one speaker; two voices alternate; first segment is speaker one; empty PCM degrades; gain shift leaves the embedding unchanged; labels survive batching.
- `desktop/src/scribe_desktop/note.py`: `speaker_role(document) -> SpeakerRolePreselection(preselected_clinician_speaker, margin, speaker_evidence)` (`:976`; question rate 0.60 / first speaker 0.25 / talk share 0.15; `None` for <2 clusters or a tie); the confirmed-role guard on `compose_draft` (`:1783-1795`); `CLINICIAN_OWNED_SECTIONS` (`:152`). Tests in `tests/test_note.py` pin the question-asker preselection, first-speaker tie-break, merged-cluster → none, "the result is not itself a speaker label"; `tests/test_note_check.py` pins "a lying speaker field cannot defeat the role check".
- `desktop/src/scribe_desktop/ui/transcript.py`: `_populate_generation_controls` (`:235`) calls `speaker_role(document)`, one `QRadioButton` per speaker from `models.speaker_quotations(document)` with " (suggested)", none pre-checked; `set_role`, `_selected_role`, `generate()` (`:394`) → `controller.begin_generation()` → `_note_generator_factory(clinician_speaker=role, template_profile_id, prefill_id)` on a `TaskThread`; `_config_loader` seam.
- `desktop/src/scribe_desktop/speaker_eval.py`: `evaluate_recording`, `_transcribe_in_temporary_store`, `cluster_metrics`, `role_outcome` (scores `speaker_role`'s preselection against Audacity role labels), `_score_condition` (two conditions: shipped and CMN-off), `render_report`; text-free results; fail-closed teardown. Input contract in `docs/testing/speaker-measurement.md`.

**Note routing — what the cue file parameterises**
- `note.py` `_RAW_SECTION_CUES` (`:729-841`; 17 keys, 98 phrases), `DEFAULT_SECTION_CUES` (normalised at import via `content_tokens`), `ExtractiveNoteProvider(cues=DEFAULT_SECTION_CUES)` (`:1067`), `_route` (first section in `request.section_keys` order whose cue is a contiguous token run — `_contains_phrase` `:871`), `provider_name = "extractive-v1"`; `note_check.py:140-146` records the lexicons as a FIRST CUT.
- `ui/models.py` `build_note_generator(..., config_root=None, provider_factory=ExtractiveNoteProvider)` (`:751-786`) — the ONLY production construction site: `load_note_config(config_root)` then `compose_draft(document, config, provider_factory(), ...)`; the provider is built WITHOUT the config today.
- `note_config.py`: per-file whole-file replacement, absent → shipped default via `importlib.resources` (`config_defaults/`), existing-but-unreadable/malformed → typed error (`_read_config_blob` `:771`); `NoteConfig(template_profiles, autofill_rules, prefill_templates)` frozen `extra="forbid"`; `to_bytes()` = `model_dump_json()`; `config_digest()` = `sha256-v1` over it; `*File` models with `schema_version: Literal[1]`; `_TriggerText` (≤200 chars, no control/format chars); duplicate-trigger detection under `content_tokens`; `default_config_root()` under LOCALAPPDATA with no UNC refusal (documented decision). `note_fill.py` `_first_phrase_match` shares the matching primitive.

**Custody, models, capture, app shell — what enrolment reuses**
- `session_store.py` `wrap_key_to_file` / `unwrap_key_from_file` (`:542-577`: `win32crypt.CryptProtectData(key, "ClinikoScribe session key", ...)`, `atomic_write_bytes`, `KeyCustodyError`, `key_blob_is_dead`), `delete_session_key`, `default_sessions_root()`; `secure_storage.SessionCrypto` (AES-256-GCM; `export_key`/`from_key`/`encrypt`/`decrypt(aad)`/`destroy`).
- `speech.py` `SileroVad` (`:161-225`): `assert_offline_env` BEFORE `import onnxruntime`; `SessionOptions`; `disable_telemetry_events()`; UNC refused; load failures → `VadModelError` at construction; `default_vad_model_path()`; `segment_probabilities` (VAD); `iter_frames`.
- `scripts/setup-models.py`: `fetch_silero_vad` (URL + `SILERO_VAD_SHA256` pin, `.part` temp, size check), `fetch_whisper` (HF snapshot, pinned revision, `allow_patterns`), `--only` validated against `{"silero-vad", *WHISPER_CANDIDATES}` (`:150`). User-run only.
- `audio_capture.py`: `CaptureBackend` (`list_input_devices`, `open_stream`), `SoundDeviceBackend`, `MockCaptureBackend`, `pcm16_rms_level`; `ui/microphone.py` opens its own monitor stream outside a session (device combo, level meter). `session.py` `SessionController.start(device_id)` always creates a session store — never the enrolment path.
- `ui/models.py` `build_transcriber(model_name)` (`:828`) and `build_recovery_runner(model_name)` (`:855`): BOTH construct `SileroVad()` + `WhisperSpeechProvider` inside the worker call and run `transcribe_session` / `recover_session_transcription` — the two entry points the profile must reach; `format_transcript_text(document)` (`:266`) renders the Note tab's transcript panel as plain text (no per-line widgets; the panel is `NoTextInteraction`); no UI code hard-codes `speaker_1`/`speaker_2`, so any label string renders. `ui/note.py` `_refinalise` (`:408`) rebuilds the note as `finalise_note(draft, self._build_resolutions(), document, config)` — review edits therefore operate on the draft the screen holds (a copy with assertions added or filtered), never on the finalised note. No test pins a literal `config_digest`; fourteen equality pins compare digests between objects (`test_note_config.py` 10, `test_note_fill.py` 2, `test_note_pipeline.py` 2) and keep passing when the domain grows.
- `ui/main_window.py`: tabs Microphone / Session / Recovery / Transcript / Note / Status; `_on_live_transcript`, `_on_draft_ready`, `closeEvent`; `note_screen.clear()` at four sites. `app.py`: mutex → sweep → `MainWindow`; no first-run hook; no `QSettings`. `ui/models.py` `model_report_lines()` (model-readiness lines for the Microphone screen's report panel — the visible-fallback surface).
- `ui/tasks.py` `TaskThread(fn)` — the off-GUI-thread worker pattern; `tests/test_ui_screens.py` `_process_until`, `FakeController`, `FakeBackend`, `_note_document`/`_note_result` fixtures — the offscreen test pattern.

**Docs that change**
- `docs/security/threat-model.md` (trust boundaries `:15-60`; Phase 3A surfaces 1–4 `:173-316`; review triggers `:328`), `docs/security/retention-schedule.md` (table `:12-28`; config row `:27`; pre-committed rules `:81`), `docs/security/data-flow-map.md` (components `:18`; flows 1–11 `:27-165`; explicit non-flows `:165`), `docs/design-system.md`, `docs/testing/speaker-measurement.md`, `AGENTS.md` (Local Run Steps step 3, Subsystem Documentation), `CHANGELOG.md`.

### Codebase Integration Notes
- **Where the model embedding is computed:** inside `transcribe_session`'s windowed loop, at the same point the spectral embedding is computed (`:960-990`), so the one-window plaintext bound is unchanged; the embedder is passed in like the provider (a `SpeakerEmbedder` protocol with a mock for tests), never imported at module import time (lazy ML imports, the `speech.py` convention).
- **Attribution output:** a new optional `TranscriptDocument` field set (Schema / Data Changes) — `enrolled_speaker: str | None`, `enrolment_similarity: float | None`, `speaker_model_id: str | None` — written by the pipeline when a profile was applied; consumed by `ui/transcript.py` to auto-confirm (D4) and by `speaker_eval.py` to score. `speaker_role()` stays pure and unchanged for the no-profile path; with the field set the UI does not call it for the selection (it may still show its evidence).
- **The role guard stays satisfied structurally:** `compose_draft(clinician_speaker=...)` receives the radio group's selection exactly as today; auto-confirm PRE-CHECKS the enrolled speaker's radio and renders the confirmation line — the selection is still a UI state the practitioner can change, and no code path passes `.preselected_clinician_speaker` or `.enrolled_speaker` straight into `compose_draft`.
- **Profile custody reuse:** generalise the two DPAPI helpers with a `description` parameter (or add `profile`-named siblings) rather than duplicating the win32crypt calls; `atomic_write_bytes` and `key_blob_is_dead` are reused as-is; a profile whose `model_sha256` differs from the installed model is treated as ABSENT with a visible "re-enrol" message (Design Decision D3 residue).
- **Cue injection is one site:** `build_note_generator`'s `provider_factory` becomes `Callable[[NoteConfig], NoteModelProvider]`; tests that construct `ExtractiveNoteProvider()` bare keep the shipped defaults (derived from the same file), so the fixture matrix keeps passing.
- **`speaker_eval.py` third condition:** the enrolment vector comes from a separate enrolment WAV (`--enrolment <wav>`, the practitioner's read-aloud) so the measured condition is exactly what the app does; leave-one-out from labelled clinician spans is a documented fallback for a set without an enrolment WAV. The harness contract (text-free results, temporary store, fail-closed teardown) is unchanged; the new condition adds a `RoleOutcome` for the auto-confirmed label.
- **Repo gotchas that bind here** (`docs/lessons.md`): agent shells are MSIX-virtualised — the model download and any `%LOCALAPPDATA%` write for the practitioner's own use are USER-run; never launch the GUI from an ephemeral terminal; codex peers get a basetemp outside the repo and do not run the suite; a claim in a docstring or security doc must state only what the structure enforces (this plan's custody and consent claims especially); a concurrency/custody "class-closed" claim needs an exhaustive consumer enumeration; the `/execute-loop` spawn notes (POSIX paths, benign EXIT:4, bare npm shim, verify=composer).
- **Shared helpers inventory (for the loop's later phases):** `speaker_embedding.SpeakerEmbedder` + `MockSpeakerEmbedder` (Phases 1, 2, 6); `practitioner_profile` load/save/delete + `ProfileAbsent`/`ProfileUnusable` (Phases 1, 2, 3, 5); the DPAPI helper with a description parameter (Phase 1); `note_config.SectionCuesFile` + `NoteConfig.section_cues` (Phases 4, 5); the Practitioner tab (Phases 3, 5).

### External / API Findings
- Not verified online during planning (agent shells never fetch models). Candidate ungated ONNX speaker-embedding models for Task 0.3, in order: (1) WeSpeaker VoxCeleb ResNet34-LM ONNX export (the `wespeaker-voxceleb-resnet34-LM` weights, MIT-licensed, ~26 MB; input Kaldi-style 80-bin fbank, output 256-dim); (2) an ECAPA-TDNN ONNX export (192-dim). The practitioner's fetch (Task 0.4) establishes the exact URL, size and SHA-256; the executor pins them (Task 0.5). Output vectors are compared by cosine similarity after L2 normalisation.

## Planned Workflow Summary

### Flow 1 — First run and enrolment
- The app starts with no profile: the Practitioner tab is selected and a banner explains what will be stored and why. The practitioner reads the consent text, ticks the box (and optionally the learning opt-in), picks the microphone, and records ~60 s of read-aloud; the capture goes straight into memory, VAD keeps the speech, the embedder averages one vector, the vector plus the consent record is encrypted under a fresh DPAPI-wrapped profile key, and the PCM is dropped. Re-enrol replaces the vector; Delete removes the key (cryptographic deletion). Recording is allowed before and after enrolment (D10), never during it (D15).

### Flow 2 — A consultation with a profile present
- Finish → `transcribe_session` embeds each VAD segment with the speaker model inside the windowed loop, scores each against the enrolled vector, labels the matched segments as one cluster and 2-means the rest, and writes `enrolled_speaker` + `enrolment_similarity` into the transcript. The Transcript screen shows "Clinician: confirmed from your voice profile (similarity 0.xx) — change", pre-checks that speaker, and Generate becomes available once the template profile is chosen, as today; "change" reverts to the manual radios. The note pipeline is unchanged from there.

### Flow 3 — A consultation without a profile, or with the model missing
- Today's path, unchanged: spectral 2-means, `speaker_role` suggestion, manual confirmation. The Status panel's model report says the speaker model is absent (or the profile needs re-enrolment) so the degradation is visible, never silent.

### Flow 4 — Cue routing with the practitioner's file
- `load_note_config` reads `section_cues.json` (user file, else shipped default); `build_note_generator` constructs `ExtractiveNoteProvider` with the config's cues; every note's `config_digest` covers them.

### Flow 5 — Learning a phrase during review
- On the Note tab, in the "Edit the note" controls beside the transcript panel, the practitioner picks one of their own transcript lines from the chooser and a section allowed for it → Add puts the line into the working draft as a transcript assertion (re-finalised, checked as usual) — or, for a line the router placed wrongly, Remove line / Move line to section… (subtract only; Undo until Save) → after an add or a move of the practitioner's own line, "Learn this phrasing?" shows the phrase and the exact line to be written → Approve appends it to the user `section_cues.json` (created from the shipped default if absent) → the Practitioner tab lists it, with Delete.

### Flow 6 — Measurement
- The practitioner records the single set (Task 6.1); `scripts/measure-speakers.py --enrolment <wav> <dir>` reports the three conditions (before 2.1, shipped, enrolled) and the auto-confirm correctness; the plan records the numbers; D-S1 and the gate resume.

## Design Decisions
- **D1 — Enrolment feeds the confirmed role through a separate transcript field; cluster labels stay opaque** because the pinned guards (`the result is not itself a speaker label`, the lying-speaker-field check, the confirmed-role guard on `compose_draft`) assume exactly that separation. Alternatives considered: a `practitioner` label written into `TranscriptSegment.speaker` (rejected — breaks three guards and couples the pipeline to a UI decision).
- **D2 — Model absent or unusable → the shipped spectral path, reported visibly** in `model_report_lines()` and the Transcript screen's status line ("speaker model not installed — run setup-models" / "profile needs re-enrolment"), the same shape as the whisper `medium` → `small` fallback. Alternatives considered: refusing to transcribe without the model (rejected — blocks the clinic for a non-clinical feature); silent fallback (rejected — the project's standing rule against silent degradation).
- **D3 — Attribution = practitioner-vs-other by cosine similarity against the enrolled vector, then 2-means over the "other" segments.** Segment scoring uses a fixed threshold constant set by D-P1 from the practitioner's own smoke and re-checked in Phase 6; when NO segment clears it, the ordinary 2-means over all segments runs and the cluster with the higher mean similarity is taken as the practitioner (D4 is unconditional, so `enrolled_speaker` is ALWAYS set when a profile is applied and the document has any transcribed speech); similarities are RAW cosines in [-1, 1] (finite; a zero-norm vector scores -1) and the threshold is compared on that scale — never a 0–1 clamp (round 1 PR-MED-007); the candidate clusters for `enrolled_speaker` are those holding at least one segment with transcribed text (a textless cluster has no radio and cannot be confirmed), and a document with no segments at all carries no attribution fields and leaves generation unavailable exactly as today (PR-MED-008); a profile whose `model_sha256` does not match the installed model's VERIFIED digest is ABSENT (re-enrol). Both transcription entry points apply the profile (`build_transcriber` and `build_recovery_runner`). Alternatives considered: estimated-k first (deferred, D-S1); a threshold learned per session (rejected — unmeasurable without labels).
- **D4 — Auto-confirm the clinician role UNCONDITIONALLY when a profile exists (practitioner-ratified 2026-09-05).** The cluster with the highest mean similarity to the enrolled vector is pre-checked as the clinician; the line "Clinician: confirmed from your voice profile (similarity 0.xx) — change" is always shown; "change" reverts to the manual radios with " (suggested)" from `speaker_role`; auto-confirm satisfies the ROLE predicate only — the template-profile choice, a valid config, no recovery in flight and the generation lease gate Generate exactly as today (round 1 PR-MED-009). Residual risk, stated for the threat model: with a weak best match (the practitioner absent, a very different microphone, a profile from another person on the same login) a patient's utterances can populate clinician-owned sections until the practitioner clicks "change" — the compensating controls are the visible similarity value, the Phase 5 checker (which still blocks unresolved errors), per-assertion review, the practitioner's review at signing, and re-enrolment. Alternatives considered: margin-gated auto-confirm with manual fallback when the best match is weak or two clusters both match (offered 2026-09-05; declined — kept here as the documented hardening if Phase 6 measures a problem); no auto-confirm (the original design; superseded by the practitioner's decision).
- **D5 — Profile custody mirrors session custody**: `%LOCALAPPDATA%\ClinikoScribe\profile\key.dpapi` (DPAPI, description "ClinikoScribe practitioner profile key") + `voice.enc` (AES-256-GCM under that key, AAD `b"clinikoscribe-practitioner-profile-v1"`); deletion = key deletion then blob unlink; re-enrolment replaces ONLY `voice.enc` (one `os.replace`) under the EXISTING key — the key is generated once at first enrolment and lives until Delete — so a failure between steps leaves the previous profile usable and no older generation can be revived (round 1 PR-MED-012); the blob holds the vector, `model_id`, `model_sha256`, `embedding_dim`, `created_at`, `enrolment_speech_seconds`, `device_name`, and the consent record (`accepted_at`, `consent_text_version`, `learning_opt_in`); nothing about it is ever logged (the log tripwire's field scan covers any new record fields by construction). Alternatives considered: plaintext JSON in `config\` (rejected — biometric); Credential Manager (rejected — a vector is not a secret string and the store is size-limited).
- **D6 — `section_cues.json` is a whole-file replacement config file** (practitioner-confirmed): the shipped default carries all 98 phrases; a user file replaces it entirely; a section key missing from a user file means NO cues for that section (stated in the file header comment and the loader docstring); validation refuses unknown keys, blank/control-character phrases, and duplicate normalised phrases within or across sections (routing order would otherwise decide silently). Alternatives considered: additive merge (rejected — a second precedence rule).
- **D7 — Cues are part of `NoteConfig` and therefore of `config_digest`**; `ExtractiveNoteProvider` is constructed from the config at the one production site. Alternatives considered: provider-level constant (rejected — a note would not record which cues routed it).
- **D8 — Enrolment capture is a dedicated in-memory path** (`enrolment.py`) over `CaptureBackend.open_stream` on a `TaskThread`, VAD-gated to require at least 30 s of speech within a 60–90 s window, returning PCM bytes that are embedded and then dropped; no session, no store, no file. Alternatives considered: `SessionController.start` (rejected — recoverable audio artefact); saving the enrolment WAV (rejected — no audio retained).
- **D9 — Learning is propose-then-approve and structurally practitioner-only**: the "Learn this phrasing?" prompt follows only an add or a move of an utterance whose speaker equals the confirmed clinician (the add/move controls themselves are D14); the learned phrase is the utterance's leading 2–4 content tokens (editable before approval); a candidate is REFUSED while any of its SOURCE tokens — the original-case transcript words, checked BEFORE `content_tokens` lowercases them, with `first_in_segment` taken from the word's position — is name-like (`transcription.is_name_like_token`) or numeric, the stored phrase being the normalised form (round 2 PR-MED-016), the prompt requires the practitioner to tick "This phrase contains no patient information" before Save, and the consent text says that judgement is theirs — the app validates shape only (round 1 PR-HIGH-001); the prompt dry-runs the proposed cue set on the source utterance and, when an earlier section's cue still wins first-match routing, says so and offers an edit — never a silent cue deletion (PR-MED-011); the write is an atomic replace of the user `section_cues.json` (created from the shipped default if absent, preserving D6); learning requires `learning_opt_in` in the profile's consent record. Alternatives considered: silent mining (excluded); learning from patient lines (excluded).
- **D10 — First run asks, never blocks**; the Practitioner tab is selected at startup when no profile exists and a banner explains; every other screen works as today.
- **D11 — The model candidate is fetched by the practitioner and then chosen by a `[decision]` task (D-P1)** after a smoke that reports same-speaker vs different-speaker cosine similarity on the practitioner's own short recordings; the executor pins URL, size and SHA-256 from the practitioner's report, exactly as silero is pinned.
- **D13 — Label scheme with a profile applied:** `speaker_1` is the practitioner (the matched cluster, or the highest-similarity cluster on zero matches — in both cases among clusters holding at least one segment with transcribed text, PR-MED-008), `speaker_2` and `speaker_3` the remainder by first appearance (2-means over the non-practitioner segments; a degenerate remainder yields only `speaker_2`). The no-profile path keeps "first segment is `speaker_1`". Consumers already tolerate N labels: `speaker_role` scores any number of clusters, the radios are one per label, `format_transcript_text` prints the label, the harness's `cluster_metrics` is label-name independent.
- **D14 — Review edits (remove / move a routed line) subtract only.** `NoteScreen` keeps a set of removed assertion ids and a list of manual additions; `_refinalise` builds the working draft as a copy of the generated draft with removed assertions filtered out and additions appended to their sections, then calls `finalise_note` as today, so every check (reconstruction, contradiction, provenance, omission) runs on the edited note; every edit — add, remove, move, undo — goes through the existing content-change helper (`_after_resolution_change`: acknowledgements cleared, note un-saved, re-finalised), so a stale acknowledgement can never survive a changed note (round 1 PR-MED-010); an omission warning raised by a removal is acknowledgeable (review severity), never a block; removals and additions are reversible until Save ("Undo"); after Save they are fixed like proposal decisions. Manual additions use an assertion-id scheme distinct from the provider's (`m<segment>` vs `x<segment>`) and refuse an utterance already present in the note. Alternatives considered: extending `finalise_note`'s signature with removal ids (rejected — the screen-held draft is the one input the pipeline already takes); free-text editing (rejected — Check 1).
- **D15 — Enrolment is a controller-owned activity.** `SessionController.begin_enrolment()` / `end_enrolment()` (the generation-lease SHAPE, but NOT state-agnostic): `begin_enrolment` REFUSES while a session is in an active state (recording / paused / transcribing) or a benchmark worker runs — `SessionActivityError` — and `start`/`resume` refuse while enrolling; `begin_enrolment` stops the microphone screen's monitor stream and the monitor poll (`_ensure_monitor`) is suppressed while the activity is held, resuming on release; the benchmark refuses while enrolling; `closeEvent` refuses while the activity is held; Re-record/Delete are disabled meanwhile; the Practitioner tab holds the activity from capture start through embedding, `save_profile` and its own result handler (success or failure) and releases it there on every path; tests cover BOTH start orders (enrolment then Start; Start then enrolment) and a monitor poll tick during enrolment (round 1 PR-MED-004, completed at round 2). Alternatives considered: a one-time monitor stop (rejected — the poll restarts the stream).
- **D16 — Two embedders behind one protocol.** `OnnxSpeakerEmbedder` (the model) and `SpectralSpeakerEmbedder` (the existing CMN'd mel embedding wrapped; `model_id = "spectral-cmn-v1"`, no file, always available) both satisfy `SpeakerEmbedder`; the profile records which produced it and is usable only with the same `model_id`; D-P1 picks which one SHIPS for enrolment and the other stays for tests and the harness; with the ONNX embedder chosen and its model absent at runtime, D2's visible fallback (no attribution) applies — spectral is never substituted silently (round 1 PR-MED-005). Availability and the factories key on the SELECTED embedder: `SHIPPED_SPEAKER_EMBEDDER` (D-P1's recorded choice, a constant in `speaker_embedding.py`) decides which class `build_transcriber`, `build_recovery_runner` and the Practitioner tab construct; `speaker_embedder_available()` is always true for spectral and true for onnx iff the pinned file is present; the enrolment UI's disabled state applies only when the SELECTED embedder is unavailable (completed at round 2).
- **D12 — Front-end in numpy, model-specific, verified against the model card** (Kaldi-style 80-bin log-mel fbank, 25 ms / 10 ms, Hamming/Povey window, per-utterance mean subtraction, 16 kHz); a wrong front-end fails the D-P1 smoke visibly (near-random similarities), which is why the smoke precedes the build.

## Schema / Data Changes
- `TranscriptDocument` (`transcription.py`): three new OPTIONAL fields with `None` defaults — `enrolled_speaker: str | None` (must equal one of the segments' labels when set; validator), `enrolment_similarity: float | None` (raw cosine in [-1, 1], finite — the mean over the matched cluster; PR-MED-007), `speaker_model_id: str | None`. `schema_version` stays `1` (additive, defaulted; old `transcript.enc` artefacts read unchanged; an artefact written with the fields is read by this version only — the recovery path never runs an older build against a newer store on this single-user machine).
- `NoteConfig` (`note_config.py`): new field `section_cues: tuple[SectionCues, ...]` (or a mapping model) — frozen, part of `to_bytes()`; `config_digest` changes for every config the moment the field exists (expected; the digest identifies content). No persisted artefact embeds a `NoteConfig`; `GeneratedNote.config_digest` values in existing tests that pin a literal digest are updated (Task 4.4 inventory).
- New config file `section_cues.json` (`schema_version: 1`, `section_cues: {<canonical key>: [phrase, ...]}`) shipped as `config_defaults/section_cues.json`.
- New profile store `%LOCALAPPDATA%\ClinikoScribe\profile\` (`key.dpapi`, `voice.enc`) — Design Decision D5.
- New model cache entry `%LOCALAPPDATA%\ClinikoScribe\models\speaker-embedding\<model>.onnx`.

## Config / Environment / Deployment Impact
- No environment variables. No CI changes beyond the model being absent on CI (tests skip-if-absent, the whisper pattern).
- `scripts/setup-models.py` gains `speaker-embedding` in the `--only` set (URL + SHA-256 + size pin), ~26 MB; `AGENTS.md` Local Run Steps step 3 gains the size and the note that enrolment needs it. User-run only.
- **Consent text v1 — DRAFT for practitioner ratification (Task 0.2); shown on the Practitioner tab and at first run; the version string is stored in the profile's consent record:**
  > "This app can learn your voice and your phrasing to improve your notes. If you agree, it stores on this computer: a numeric fingerprint of your voice (never a recording), encrypted; and, if you also turn on phrase learning, the short phrases you approve during review, kept as plain text in your own config file until you delete them. The app cannot tell whether a phrase names a patient — only you can — so it shows you every phrase before saving it, refuses names and numbers, and asks you to confirm it contains no patient information; keep phrases general. Nothing else about any patient is stored beyond their session, and nothing leaves this computer. You can re-record your voice, delete it, or delete any learned phrase at any time from this tab. Version consent-v1."
  (Round 1 PR-MED-002 / PR-HIGH-001: the voice profile is encrypted; approved phrases are PLAIN TEXT in `section_cues.json` with the other clinician config, retained until deleted; the no-patient-information judgement is the practitioner's — the loader validates shape only, `note_config.py:17-21`.)
  A second checkbox, off by default: "Also learn my phrasing from lines I add during review (asks each time)". Ratified text replaces the draft verbatim in `ui/models.py` `CONSENT_TEXT_V1`; changing the text later means a new version and re-consent at next start.
- Release risk: a practitioner who never enrols sees no change; a practitioner who enrols on one microphone and records on another may see wrong auto-confirms until re-enrolment (D4 residual, visible).

## Critical Constraints
- **No cloud, no network at runtime** (PLAN.md): the offline kill-switches are asserted BEFORE `onnxruntime` is imported in the new embedder; the model is fetched only by `scripts/setup-models.py`, run by the practitioner.
- **No audio is ever persisted for enrolment**; the profile holds a numeric vector only; PCM buffers are dropped when embedding completes (pinned by test with a mock backend).
- **The profile is encrypted at rest under a DPAPI-wrapped key; deletion is key deletion**; no log record, status line, exception message or report ever carries the vector or the consent record's contents (the log tripwire scans every formatter field by construction; add the profile fields to its adversarial fixtures).
- **The windowed plaintext bound in `transcribe_session` is unchanged**: the speaker embedding is computed per segment inside the same window the spectral one is; no whole-session PCM is held.
- **Cluster labels stay opaque and the confirmed role stays a UI selection** (D1); no code path passes a pipeline field straight into `compose_draft`'s `clinician_speaker`.
- **Auto-confirm as ratified (D4)**: always shown, always changeable with one click, never hidden behind a setting the practitioner did not choose.
- **Cue file: whole-file replacement, fail-closed loader, digest-bound** (D6, D7).
- **Learning: approval-only, practitioner utterances only, opt-in-gated** (D9); the exact text to be written is shown before it is written; a candidate phrase with a name-like or numeric SOURCE token (checked in original case, before normalisation) is refused, the practitioner confirms it holds no patient information, and the consent text says that judgement is theirs (round 1 PR-HIGH-001).
- **Review edits subtract or re-route the practitioner's own transcript lines only** (D14): no free-text editing, no new content, ownership rules enforced on every add or move, reversible until Save.
- **Docstrings and security docs claim only what the structure enforces**, naming residues (the project's recurring review class).
- **Compatibility**: old `transcript.enc` artefacts read unchanged; a config directory without `section_cues.json` loads the shipped default; a machine without the speaker model behaves exactly as today.

## Validation / Verification
Baselines pinned at planning (read-only dry-run, 2026-09-05, `main` `8527ce9`):
- Desktop suite: `pytest --collect-only -q` → **1368 collected**; full run 1368 passed (76 s on this host); `ruff check .` clean; `mypy` clean over **30** source files.
- `note.py` `_RAW_SECTION_CUES`: **17** sections, **98** phrases (the shipped `section_cues.json` must carry exactly these until the practitioner edits a copy).
- `config_defaults/`: 3 files → 4 after Phase 4.
- `scripts/setup-models.py --only` valid set: `{"silero-vad", *WHISPER_CANDIDATES}` → plus `speaker-embedding` after Task 0.3.
- `note_screen.clear()` call sites in `main_window.py`: 4; `speaker_role(` call sites outside its definition: 3 (`speaker_eval.py`, `ui/transcript.py`, `note.py` guard text); `provider_factory` mentions in `ui/models.py`: 2.
- CI: three jobs green on `main` (last run 33934875082-series; extension on Node 24).

Per-phase checks:
- **Phase 0**: the Phase 3A plan and `AGENTS.md` carry the pause pointer; the consent text is ratified (practitioner); `setup-models.py --only speaker-embedding` fetches the candidate for the practitioner and prints size + SHA-256; the smoke script prints same-speaker vs different-speaker cosine on two short practitioner recordings and one other voice; D-P1 recorded.
- **Phase 1**: unit tests — embedder load contract (absent → `SpeakerModelError`, UNC refused, offline asserted before import), front-end shape (80 × frames) and determinism, profile round-trip, key-first deletion, unreadable/truncated blob → typed error, model-SHA mismatch → absent, no PCM persisted (mock backend; the enrolment function returns and the only artefacts on disk are `key.dpapi` + `voice.enc`), log-tripwire fixtures extended.
- **Phase 2**: attribution unit tests with synthetic vectors (matched cluster + 2-means remainder; all-matched; NONE-matched → ordinary 2-means with the higher-similarity cluster as `speaker_1`; single segment; three labels rendered); BOTH entry points (`build_transcriber` and `build_recovery_runner`) pass the embedder + profile (pinned with fakes); pipeline tests with `MockSpeakerEmbedder` injected (document fields set; the plaintext bound test still passes; degenerate policy unchanged); transcript round-trip with the new fields; the `enrolled_speaker` validator refuses a label absent from the segments; offscreen UI tests — auto-confirm pre-check + confirmation line, "change" reverts, Generate still gated on the template profile (enrolment alone leaves it disabled — PR-MED-009), manual path when the field is `None`, the lying-field defence; harness tests for the third condition.
- **Phase 3**: offscreen UI tests for the Practitioner tab (consent gate, enrol with a mock backend, status, re-enrol, delete), first-run tab selection; docs re-read against the code (the round-40/41 class).
- **Phase 4**: loader properties for the fourth file (absent → default; malformed → loud; unknown key, blank, duplicate refused; digest changes with the file and with a one-phrase edit); provider routes by config cues (a user file that removes an advice cue stops that routing); `DEFAULT_SECTION_CUES` equals the shipped file; the gate-run cue file loads.
- **Phase 5**: the utterance chooser lists only eligible utterances and the section chooser only allowed sections (clinician-owned → the confirmed clinician's non-questions); the added assertion reconstructs byte-identically (Check 1) and carries the manual id scheme; an utterance already in the note is refused; Remove filters the assertion out of the working draft and any omission warning is acknowledgeable, never blocking; Undo restores; Move = remove + add under the ownership rules; edits are frozen after Save; the learn prompt fires after an add or a move of a practitioner utterance only and shows the exact line; approve writes atomically and the loader reads it back; decline writes nothing; opt-in off → no prompt; Practitioner tab lists and deletes.
- **Phase 6 (practitioner)**: the recording set; `measure-speakers.py --enrolment` numbers recorded in this plan and the Phase 3A plan (Task 2.3); the gate run resumes per rubric v1 with the R3 clarification of Task 5.5 (removed lines count in the numerator).
- **Gates**: `ruff check . && mypy && pytest` in `desktop/` green at every phase boundary; CI three jobs green; `/review-loop` + cross-family codex `/peer-loop` at each phase boundary (the loop's standing cadence); the Hardening stage before Phase 6.

## Deferred / Out of Scope
See `Planning Extraction Summary` → `Deferred — Actionable Later`, `Excluded — Revisit Only If Needed`, and `Accepted Assumptions — Revalidate Later` (state-once; nothing is restated here). The Task 9.1 shipping-gate RUN, Task 2.3 and D-S1 remain in `plan-phase3a-note-pipeline.md`; this plan only pauses the run (Task 0.1) and feeds it the single recording set (Task 6.1).

## Current State / Handoff Note
- Last completed step: plan peer-review round 2 (codex `gpt-6-astra` at high, 11 of 15 round-1 amendments confirmed, the other four completed, 3 new findings applied 2026-09-05 — see `Review History`); before that round 1 (15 findings, all applied); before that `/review-plan` hardening pass 1 (2026-09-05, Claude Code `claude-fable-5-1`): recovery-path attribution added (`build_recovery_runner`), the zero-match rule under D4 fixed (D13), the label scheme fixed (D13), Phase 5 re-shaped to an explicit chooser control plus remove/move (D14, practitioner Fix-now at the gate), the R3 clarification task 5.5 added, the digest-pin fact recorded. Planning complete before that (same day; exploration scratch `explore-practitioner-profile.md` consumed).
- Current in-progress step: None.
- Immediate next action: plan peer-review ROUND 3 (confirmation of round 2's amendments; a fresh codex session, `gpt-6-astra` at high — round 2 cost 131k tokens); the pass converges on zero NEW build-affecting findings. Then `/execute-loop` from Task 0.1. Tasks 0.2 and 0.4 need the PRACTITIONER before Phase 1 can start.
- Open blockers / open questions: the speaker-embedding model candidate (Tasks 0.3–0.5, D-P1) — practitioner-run fetch.
- Phase 0 interleaving (for an `/execute-loop` run): agent tasks 0.1 and 0.3 first → PAUSE for the practitioner's 0.2 (consent ratification) and 0.4 (fetch + smoke, normal terminal) → agent task 0.5 → PAUSE for the practitioner's 0.6 (promote the pinned model) → D-P1 (`[decision]`, a planned hard-stop) → Phase 1. Run Phase 0 as one-phase-and-stop; Phases 1–3 may run back-to-back; Phase 6 is practitioner-only.
- Last plan sync: 2026-09-05 (created).
- Plan peer-review round 1 (codex `gpt-6-astra` xhigh): ATTEMPTED 2026-09-05 11:40-11:46 UTC and INCONCLUSIVE - the run died on the ChatGPT account's usage limit after reading the code ("You've hit your usage limit ... try again at Sep 6th, 2026 2:41 AM"), no findings emitted, nothing logged; the peer had finished READING every named source (25 commands, 135k tokens) and was cut off before writing; after the reset (or on purchased credits) RESUME that session rather than re-reading: `codex exec resume 01a0715e-f6ba-7bf0-9fa5-e6c6d823b30a -s read-only -m gpt-6-astra -c model_reasoning_effort=xhigh "Your reading is complete. Now output the full Round 1 block exactly as the OUTPUT section of the original prompt specifies, ending with the PEER-PLAN-ROUND-1 RESULT line." </dev/null` (fallback: re-run the unchanged prompt `.cursor/loops/practitioner-profile-plan-peer-r1-prompt.txt` as round 1). The plan is NOT cross-family reviewed until that round lands.
- Loop config: none yet (first run). Cross-family peer for this plan's reviews and its loop run (practitioner-decided 2026-09-05): codex `gpt-6-astra`, reasoning effort xhigh, read-only sandbox (`codex exec -s read-only -m gpt-6-astra -c model_reasoning_effort=xhigh`), replacing `gpt-5.6-sol` used through round 72.

## Review History
Each /review invocation appends a one-line entry here. Round NUMBERS
are never allocated by counting this section's entries — allocation
follows /review's **Detect review round** rule (the canonical
definition: the `Review Findings Log`'s round headers, with a legacy
highest-History-round fallback when the Log has no headers; every
findings writer follows it). Ignore the placeholder line when reading
this section.

- 2026-09-05 round 1: 0 CRIT / 1 HIGH / 14 MED / 0 LOW; skew=cross-family; action=amended-in-place (plan peer-review — independent cross-family Codex plan peer-review on `gpt-6-astra` xhigh, read-only sandbox, run as a resumed session after the first attempt died on the account's usage limit; block transcribed verbatim by the owning planning session (Claude Code `claude-fable-5-1`). Materiality verified: 15 build-affecting / 0 record-only / 0 invalid — every peer label upheld. All 15 applied as `/review-plan`-style amendments the same day (consent text, D3/D4/D5/D9/D13/D14, new D15/D16, Tasks 0.3/0.5/0.6/1.1/1.2/1.3/2.1–2.4/3.1/3.2/5.1/5.1b/5.2/5.4/5.5/6.1, Flow 2, Critical Constraints), siblings swept. NOT converged: a plan peer-loop never converges on round 1; round 2 is owed. Line owned by the seat that finishes the round.)
- 2026-09-05 round 2: 0 CRIT / 0 HIGH / 2 MED / 1 LOW; skew=cross-family; action=amended-in-place (plan peer-review — post-round-1-amendment independent cross-family Codex plan peer-review on `gpt-6-astra` at HIGH effort, read-only sandbox, fresh session; block transcribed verbatim by the owning planning session (Claude Code `claude-fable-5-1`). Round-1 confirmations 11 of 15: PR-HIGH-001, PR-MED-004, PR-MED-005, PR-MED-015 NOT CONFIRMED as amended and completed this round. New: PR-MED-016 (the name refusal ran after lowercasing — moved before normalisation), PR-MED-017 (Task 0.6 depended on a Phase 3 report line — re-anchored), PR-LOW-018 (stale summaries — reconciled); materiality verified 2 build-affecting / 1 record-only / 0 invalid, all applied the same day. NOT converged: two NEW build-affecting findings this round; round 3 (confirmation) owed. Line owned by the seat that finishes the round.)

Format /review will append:
- YYYY-MM-DD round N: X CRIT / X HIGH / X MED / X LOW; skew=<class>; action=<rec>

## Review Findings Log
Each /review invocation appends a detailed findings block here, with
/fix updating per-finding Decision and Notes as it processes each one.
Findings carry stable IDs within a round (CRIT-001, HIGH-001,
MED-001, LOW-001, etc.) so they can be referenced across sessions
and tools without copy-paste. Plan peer-review rounds carry the
mode-distinct `Source: <Tool> plan peer-review` and a `Materiality:`
summary (canonical definitions in `/peer-review`; `/fix` never ingests
them). Closed-round compaction follows `/document` Step 6.7 (the
sidecar would be `findings-practitioner-profile.md`).

### Round 1 - 2026-09-05 - practitioner-profile plan, independent cross-family codex plan peer-review (round 1)

- Round status: Closed (15 of 15 Applied 2026-09-05 as plan amendments by the owning planning session; NOT converged — round 2 owed)
- Source: Codex plan peer-review
- Materiality: 15 build-affecting / 0 record-only / 0 invalid
- Plan reviewed at: b64bddb
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-practitioner-profile.md`; `AGENTS.md`; `docs/lessons.md`; `docs/design-system.md`.
  - Requested symbols in `desktop/src/scribe_desktop/transcription.py`, `note.py`, `note_config.py`, `note_check.py`, `session_store.py`, `secure_storage.py`, `speech.py`, `audio_capture.py`, `session.py`, `speaker_eval.py`.
  - Requested UI paths in `desktop/src/scribe_desktop/ui/models.py`, `transcript.py`, `note.py`, `main_window.py`; related lifecycle code in `microphone.py`, `session_screen.py`, `tasks.py`.
  - `desktop/src/scribe_desktop/logging_setup.py`; `desktop/src/scribe_desktop/config_defaults/*.json`; relevant cases in `desktop/tests/test_transcription.py`; `scripts/setup-models.py`.
  - Requested sections of `docs/security/threat-model.md`, `docs/security/retention-schedule.md`, `docs/security/data-flow-map.md`; `docs/testing/speaker-measurement.md`; `docs/testing/shipping-gate.md`.
  - Context-only references in `PLAN.md` and `.cursor/plans/plan-phase3a-note-pipeline.md`, including Task 2.3, D-S1, 9.1 and 9.2.
- Finding verification: 25 candidates / 10 dropped / 0 downgraded
- Verification method: Static review only; no tests run and no files or directories written.

#### Unstated assumptions

##### PR-HIGH-001 — Clinician attribution does not exclude patient information from persistent learning

- Plan section: Goal; Design Decision D9; Task 5.2; consent draft.
- Materiality: build-affecting
- Why it matters: A correctly identified clinician can say “John Smith has diabetes.” Saving that utterance’s leading tokens retains patient information outside session custody. D4 additionally permits incorrectly attributed patient speech to reach this path. Its documented clinical-attribution residual does not disclose this new persistent-retention consequence.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:240`:
  > the learned phrase is the utterance's leading 2–4 content tokens (editable before approval)

  `.cursor/plans/plan-practitioner-profile.md:258`:
  > Nothing about any patient is stored beyond their session
- Evidence: `desktop/src/scribe_desktop/note_config.py:17–21`:
  > - "NOT patient data" is a POLICY, not an enforced property. Every validator  
  >   below constrains SHAPE and character content — length, control characters,  
  >   the single-claim form, duplicate detection — and none of them classifies  
  >   meaning. A clinician override can put patient data in any accepted string,  
  >   so nothing here may be treated as non-clinical BECAUSE it validated.
- Suggested change: Before learning ships, require the practitioner to generalise the candidate and explicitly confirm it contains no patient-specific information. Disclose its actual retention and the semantic-validation limit, including D4’s additional learning consequence, during consent ratification. If absolute exclusion remains a requirement, constrain persistent phrases to a closed non-patient vocabulary. Add clinician-spoken identifier/history and incorrect-role verification cases. Preserve D4 itself.
- /fix decision: Applied
- /fix notes: Verified build-affecting (composer). Amended: D9 (name-like/numeric tokens refused via `is_name_like_token`; mandatory no-patient-information checkbox), Task 5.2, the consent text (plain-text phrases, the judgement is the practitioner's), Critical Constraints, Task 5.4 (threat-model residue), the consent assumption wording.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-002 — Consent promises encryption for phrases stored as plaintext JSON

- Plan section: Config / Environment / Deployment Impact; Tasks 0.2 and 5.2.
- Materiality: build-affecting
- Why it matters: The proposed consent describes a different storage protection from the implementation being authorised. Atomic replacement supplies durability, not encryption.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:258`:
  > it stores on this computer, encrypted: a numeric fingerprint of your voice (never a recording), and the phrases you approve for routing your sentences into note sections.
- Evidence: `desktop/src/scribe_desktop/note_config.py:8–12`:
  > Config files are INTENDED to be clinician-authored boilerplate rather than  
  > patient data (plan Schema / Data Changes): they live in plaintext under  
  > ``%LOCALAPPDATA%\\ClinikoScribe\\config\\``, deliberately outside the  
  > encrypted session store and the 24 h rule, so they survive session  
  > destruction.

  `desktop/src/scribe_desktop/note_config.py:782`:
  ```python
  return user_path.read_bytes(), "user"
  ```
- Suggested change: Correct the consent before Task 0.2 ratification to distinguish the encrypted voice profile from plaintext approved cues, their indefinite retention and ordinary file deletion. If encrypted phrases are required, add the corresponding encryption, loading and deletion contracts explicitly while preserving whole-file replacement semantics.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: the consent text now distinguishes the encrypted voice profile from plain-text approved phrases retained until deleted; the accepted-assumption wording matches.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-003 — The profile/model identity check is not bound to loaded model bytes

- Plan section: Design Decision D3; Task 1.1; Codebase Integration Notes.
- Materiality: build-affecting
- Why it matters: A different, shape-compatible ONNX file at the installed path can pass the planned load smoke while the embedder reports the registry’s SHA. The profile then appears compatible with a different embedding space, producing incorrect similarities and unconditional role confirmation.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:348`:
  > `model_id` + `model_sha256` properties (read from the pinned registry constant, not recomputed per call).

  `.cursor/plans/plan-practitioner-profile.md:234`:
  > a profile whose `model_sha256` does not match the installed model is ABSENT (re-enrol)
- Evidence: The referenced Silero construction loads the supplied path, without authenticating its digest, at `desktop/src/scribe_desktop/speech.py:197–199`:
  ```python
  self._session = onnxruntime.InferenceSession(
      str(path), sess_options=options, providers=["CPUExecutionProvider"]
  )
  ```

  Actual-byte hashing exists in the setup path, `scripts/setup-models.py:95`:
  ```python
  digest = hashlib.sha256(target.read_bytes()).hexdigest()
  ```
- Suggested change: Require actual model bytes to match the pin once at embedder construction, before inference, and expose only that verified identity. Per-embedding hashing remains unnecessary. Add a valid-shape/wrong-digest case and verify visible fallback through both production factories.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: Task 1.1 — the model file's bytes are hashed once at construction and checked against the pin; mismatch raises `SpeakerModelError`; D3 says the profile is matched against the VERIFIED digest.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

#### Coverage

##### PR-MED-004 — Enrolment bypasses the existing capture and worker lifecycle guards

- Plan section: Tasks 1.3, 3.1 and 3.2; Planned Workflow Summary, Flow 1.
- Materiality: build-affecting
- Why it matters: Enrolment is invisible to the controller’s active-session state. Session capture, monitor polling and benchmark work can therefore overlap it. A one-time monitor stop is insufficient because polling restarts it. Capture-only busy handling also leaves embedding/save and queued success handling outside the close/delete guards.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:361`:
  > running `record_enrolment` on a `TaskThread` (GUI thread never blocks; the microphone screen's monitor stream is paused during capture)

  Task 3.2:
  > `closeEvent` refuses close while an enrolment capture runs
- Evidence: `desktop/src/scribe_desktop/session.py:355–360`:
  ```python
  self._refuse_while_generating("start")
  live = self._live
  if live is not None and live.session.state in ACTIVE_STATES:
      raise SessionActivityError(
          "another session is active (single-active-session invariant)"
      )
  ```

  `desktop/src/scribe_desktop/ui/microphone.py:199`:
  ```python
  self._ensure_monitor()
  ```

  Its benchmark guard at `:277` is:
  ```python
  if self._controller.state in ACTIVE_STATES:
  ```
- Suggested change: Add coordinated enrolment activity ownership, honoured by session Start/Resume, monitor polling, benchmark, Re-record/Delete and window close. Hold it through capture, embedding, save and result handling; release it on every failure path. Test both capture-start orders and a monitor timer tick during enrolment. Recording before enrolment remains allowed under D10.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: new D15 (controller-owned enrolment activity honoured by start/resume, the monitor poll, the benchmark, close, Re-record/Delete); Tasks 1.3, 3.1, 3.2.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-005 — The spectral-only decision outcome has no executable implementation branch

- Plan section: D-P1; Tasks 1.1, 2.1 and 3.1.
- Materiality: build-affecting
- Why it matters: D-P1 offers enrolment without an ONNX model, but the implementation tasks provide only ONNX/mock embedders and disable enrolment or omit attribution when the model is absent. A listed decision outcome cannot deliver the feature.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:343`:
  > spectral features only (enrolment on the CMN'd embedding, no model)

  `.cursor/plans/plan-practitioner-profile.md:354`:
  > pass the embedder + profile when `speaker_model_available()` and a profile loads (else report the fallback, D2)

  `.cursor/plans/plan-practitioner-profile.md:361`:
  > disabled states when the speaker model is absent (message names `setup-models.py`)
- Evidence: A reusable spectral implementation exists at `desktop/src/scribe_desktop/transcription.py:579–580`:
  ```python
  if cepstral_mean_normalisation:
      log_mel = log_mel - log_mel.mean()
  ```

  Its return at `:585` is:
  ```python
  return np.concatenate([log_mel, [centroid / _EMBED_LOW_BAND_HZ]]).astype(np.float32)
  ```
- Suggested change: Define a `SpectralSpeakerEmbedder`, versioned algorithm identity, profile compatibility rules and model-free availability/UI behavior, with tests. Alternatively, make selection of this D-P1 option explicitly require amendment of the downstream tasks before Phase 1 proceeds.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: new D16 (`SpectralSpeakerEmbedder` behind the same protocol, profile bound to `model_id`); Task 1.1; D-P1's option text.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

#### Practicality / feasibility / sequencing

##### PR-MED-006 — Phase 0 never installs the verified candidate at the runtime filename

- Plan section: Tasks 0.3–0.5; Current State / Handoff Note.
- Materiality: build-affecting
- Why it matters: Task 0.4 leaves a `.part` file. Task 0.5 changes repository pins but cannot promote the practitioner’s cache file from an agent shell. The next phases expect a final `.onnx` file, so following the sequence leaves enrolment unavailable.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:339`:
  > the script downloads to `models/speaker-embedding/<name>.onnx.part`, prints size and SHA-256, and refuses to finalise until a pin exists

  `.cursor/plans/plan-practitioner-profile.md:341`:
  > **Pin the model** — SHA-256, size and URL into `setup-models.py` (candidate mode removed for this entry)
- Evidence: The existing setup completes installation with an explicit promotion, `scripts/setup-models.py:110–111`:
  ```python
  tmp.write_bytes(data)
  tmp.replace(target)
  ```
- Suggested change: Add a practitioner-run step after pinning to rerun setup, verify the candidate against the selected pin, promote it to the runtime filename and confirm availability. Specify how the earlier smoke receives the `.part` candidate path before promotion. Include this step in the Phase 0 pause/resume sequence.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: Task 0.3 (candidate file + explicit smoke path), new practitioner Task 0.6 (re-run setup-models to verify and promote), the handoff's Phase 0 pause sequence.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-007 — The similarity range rejects valid unconditional-fallback results

- Plan section: Schema / Data Changes; Design Decision D3; Tasks 1.1 and 2.1.
- Materiality: build-affecting
- Why it matters: L2 normalisation does not make cosine similarity nonnegative. If every segment has a negative similarity, D4 still selects the best cluster, whose mean can remain negative. The proposed document validator then prevents transcription from completing.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:248`:
  > `enrolment_similarity: float | None` (0–1, the mean cosine of the matched cluster)

  `.cursor/plans/plan-practitioner-profile.md:234`:
  > when NO segment clears it, the ordinary 2-means over all segments runs and the cluster with the higher mean similarity is taken as the practitioner
- Evidence: The pipeline constructs the validated document before persistence, `desktop/src/scribe_desktop/transcription.py:989`:
  ```python
  document = TranscriptDocument(
  ```

  Persistence occurs afterward at `:1004`:
  ```python
  write_transcript(session_dir, crypto, document)
  ```

  Under Task 1.1’s L2-normalised-vector contract, `(1, 0)` and `(-1, 0)` are valid unit vectors with cosine `-1`.
- Suggested change: Store finite raw cosine in `[-1, 1]`, with defined handling of numerical overshoot, zero vectors and nonfinite values. Alternatively, specify one consistent transformation into `[0, 1]` for thresholding, storage, UI and reports. Test an all-negative zero-match case without changing D4.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D3 and Tasks 2.1/2.2 — raw cosine in [-1, 1], finite, zero-norm scores -1; the threshold on that scale.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-008 — Segment-label membership does not guarantee a radio exists to auto-confirm

- Plan section: D13; Tasks 2.1–2.3; Schema / Data Changes.
- Materiality: build-affecting
- Why it matters: A best-matching acoustic cluster can contain only segments for which Whisper produced no text. It passes the planned membership validator but has no corresponding radio. An entirely silent recording has no cluster at all, making the always-set requirement impossible.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:354`:
  > set `enrolled_speaker` (always, when a profile is applied)

  `.cursor/plans/plan-practitioner-profile.md:355`:
  > `enrolled_speaker ∈ segment labels` validator; `read_transcript` round-trip; `models.speaker_quotations` unchanged.
- Evidence: `desktop/src/scribe_desktop/ui/models.py:298–300` excludes textless clusters:
  ```python
  text = " ".join(word.word_text for word in segment.transcript_words).strip()
  if not text:
      continue
  ```

  `desktop/src/scribe_desktop/ui/transcript.py:243–244` builds radios only from those quotations:
  ```python
  quotes = models.speaker_quotations(document)
  for speaker, quote in quotes.items():
  ```

  The existing silence case at `desktop/tests/test_transcription.py:697–698` asserts:
  ```python
  assert document.transcript_segments == ()
  assert read_transcript(session_dir, crypto) == document
  ```
- Suggested change: Define zero detected segments explicitly: preserve the empty document, invent no speaker and keep generation unavailable. For a nonempty acoustic cluster without recognised text, provide a selectable radio with a nonclinical placeholder or another explicit compatible policy. Test both cases through the relevant pipeline/UI paths. This resolves an impossible selection without introducing confidence gating.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D3, D13, Tasks 2.1/2.2 — candidate clusters must hold a segment with text; no segments → no attribution fields, generation unavailable as today.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-009 — “Enable Generate immediately” conflicts with template confirmation

- Plan section: Design Decision D4; Task 2.3; Phase 2 verification.
- Materiality: build-affecting
- Why it matters: Voice enrolment confirms the clinician role, but the template remains unselected. Following the task literally either enables a button whose handler does nothing or bypasses the separate template-confirmation control.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:235`:
  > Generate is enabled immediately.
- Evidence: `desktop/src/scribe_desktop/ui/transcript.py:273`:
  ```python
  self.profile_combo.addItem("- choose template profile -", None)
  ```

  At `:296`:
  ```python
  both_confirmed = self._role_confirmed() and self._profile_confirmed()
  ```

  At `:303`:
  ```python
  self.generate_button.setEnabled(can_generate_now and both_confirmed)
  ```

  The handler independently refuses a missing template at `:400–401`:
  ```python
  if role is None or profile_id is None:
      return  # Generate is disabled until both are confirmed; defensive.
  ```
- Suggested change: Specify that auto-confirm satisfies only the clinician-role predicate. Preserve template selection, valid config, recovery and generation-lease gates. Replace the unconditional enablement test with one proving enrolment alone leaves Generate disabled, then template selection enables it when all other conditions hold.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D4, Flow 2, Task 2.3 — auto-confirm satisfies the role predicate only; Generate stays gated on the template profile, config, recovery and lease.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-010 — Review edits leave previous warning acknowledgements valid

- Plan section: D14; Tasks 5.1 and 5.1b; Phase 5 verification.
- Materiality: build-affecting
- Why it matters: Acknowledgements are stored by warning code. After acknowledging one omission, removing another clinician dose line can introduce a new `high_risk_omission` under the already-acknowledged code. Calling `_refinalise` alone allows the edited note to retain that stale acknowledgement.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:374`:
  > Add appends a `transcript`-provenance `NoteAssertion` (contiguous coords for the whole utterance, id `m<segment>`) to the screen's working draft and `_refinalise`s
- Evidence: The existing content-change path explicitly invalidates acknowledgements, `desktop/src/scribe_desktop/ui/note.py:367–372`:
  ```python
  def _after_resolution_change(self) -> None:
      # A content change invalidates prior acknowledgements and un-saves the
      # note: the clinician acknowledges a STABLE note, then saves.
      self._acknowledged.clear()
      self._note_saved = False
      self._refinalise()
  ```

  Warning state is code-based at `:454`:
  ```python
  acked = group.code in self._acknowledged
  ```

  Removed high-risk coordinates produce this code at `desktop/src/scribe_desktop/note_check.py:1432–1434`:
  ```python
  note_warning_code="high_risk_omission",
  severity="review",
  source_coords=SourceCoords(segment_index, min(uncovered), max(uncovered)),
  ```
- Suggested change: Route add/remove/move/undo through one content-change helper that invalidates acknowledgements before refinalising. Test an acknowledged omission followed by removal of another dose line: Save and Copy must remain unavailable until fresh acknowledgement.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D14, Tasks 5.1/5.1b — every edit goes through `_after_resolution_change` (acknowledgements cleared, un-saved, re-finalised).
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

#### Simpler / safer alternatives

##### PR-MED-011 — Appending a learned cue can leave the demonstrated misrouting unchanged

- Plan section: Goal; D9; Task 5.2.
- Materiality: build-affecting
- Why it matters: Routing selects the first matching canonical section. Moving a line to a later section and appending a cue there does not override an existing earlier-section match. The app can approve and save “learning” that cannot reproduce the correction it just observed.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:376`:
  > After an add or a move of one of the practitioner's own utterances

  The same task specifies:
  > Approve → `note_config.append_user_cue(section_key, phrase)`
- Evidence: `desktop/src/scribe_desktop/note.py:1084–1088`:
  ```python
  for key in request.section_keys:
      if key in CLINICIAN_OWNED_SECTIONS and (not is_clinician or question):
          continue
      if any(_contains_phrase(tokens, phrase) for phrase in self._cues.get(key, ())):
          return key
  ```

  The earlier presenting-complaint section includes this cue at `:738`:
  ```python
  "pain in",
  ```
- Suggested change: Before offering a cue as a successful learned correction, dry-run the proposed cue set against the source utterance. If the selected section still loses, explain the conflict and offer an explicit cue edit; never delete cues silently. Pin a move to advice for an utterance that also matches an earlier presenting-complaint cue. This preserves the existing routing contract without introducing a new precedence system.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D9 and Task 5.2 — the learn prompt dry-runs the proposed cue set on the source utterance and warns when an earlier section's cue still wins; never a silent deletion.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

#### Missing verification / rollback / migration

##### PR-MED-012 — Per-file atomic writes do not make re-enrolment a safe profile replacement

- Plan section: Design Decision D5; Task 1.2; Phase 1 verification.
- Materiality: build-affecting
- Why it matters: Re-enrolment writes a fresh key over the existing key before replacing `voice.enc`. A crash or blob-write failure between those commits leaves the old profile encrypted under a lost key, destroying the previously usable profile and consent record.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:349`:
  > `save_profile(profile)` (fresh `SessionCrypto`, DPAPI-wrap with the profile description, AES-GCM with the v1 AAD, atomic writes, key first)
- Evidence: `desktop/src/scribe_desktop/session_store.py:551–552` replaces the fixed key file:
  ```python
  key_path = session_dir / KEY_FILENAME
  atomic_write_bytes(key_path, blob, error_label="key custody blob")
  ```

  The atomicity boundary is one path, at `:525`:
  ```python
  os.replace(tmp_path, path)
  ```

  The session precedent creates a new directory, `desktop/src/scribe_desktop/session.py:367–371`:
  ```python
  session = RecordingSession(key_reference="key.dpapi")  # state defaults to idle
  directory = self._root / session.session_id
  crypto = SessionCrypto()
  try:
      directory.mkdir(parents=True, exist_ok=True)
  ```
- Suggested change: Specify replacement failure semantics separately from first enrolment. A simpler option is to retain the existing profile key during re-enrolment and atomically replace only the authenticated blob; another is a staged key/blob generation with one commit point. Add fault-injection checks around every replacement step, ensuring failed re-enrolment preserves the prior usable profile and Delete cannot revive an older generation.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: D5 and Task 1.2 — the profile key is generated once and re-enrolment replaces only `voice.enc` atomically; fault-injection tests.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-013 — The shared recording protocol does not resolve role-play versus acoustic identity

- Plan section: Agreed Scope; Task 6.1; Phase 6 verification.
- Materiality: build-affecting
- Why it matters: The frozen gate procedure defaults to the practitioner acting both roles. Voice enrolment recognises a person, not an acted role: correctly matching both parts to the practitioner would be scored against conflicting `clinician`/`patient` ground truth. This cannot establish speaker separation or auto-confirm accuracy.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:389`:
  > ~10 mock consultations recorded through the app AND in parallel to labelled 16 kHz WAVs (Audacity role-label tracks; one three-speaker consultation), plus one enrolment WAV
- Evidence: `docs/testing/shipping-gate.md:17`:
  > Each consultation is MOCK (the practitioner acting both roles, as at the Phase 2 completion gate) — the ratified default — unless the practitioner expressly substitutes a consented recording for a given consultation.

  The harness treats role labels as speaker truth, `desktop/src/scribe_desktop/speaker_eval.py:583–584`:
  ```python
  majority_true = majority(chosen)
  verdict: RoleVerdict = "CORRECT" if majority_true == CLINICIAN_LABEL else "WRONG"
  ```
- Suggested change: Resolve the performer protocol before Task 6.1: use distinct actual voices for the practitioner and other roles, including three actual voices in the D-S1 consultation, while keeping consultation content mock and thresholds frozen. Record this explicitly in the shared-set instructions so the practitioner does not discover after recording that one-person role-play cannot serve all three measurements.
- /fix decision: Applied
- /fix notes: Verified build-affecting — and a practitioner-facing change to the recording protocol: a second real voice speaks the patient part (mock content), a third for the three-speaker consultation. Amended: Task 6.1 and the Agreed Scope protocol; the gate doc's mock definition is clarified at Task 5.5 with thresholds untouched. Surfaced to the practitioner in session and ACCEPTED 2026-09-05 ("protocol ok").
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-014 — The inherited scorer suppresses metrics for all-matched enrolled speech

- Plan section: Task 2.4; Phase 2 harness verification.
- Materiality: build-affecting
- Why it matters: Under D13, all `speaker_1` can mean either correctly matched practitioner-only speech or every patient segment incorrectly matching the practitioner. The existing scorer classifies both as merged and omits cluster metrics, hiding a significant enrolled-condition failure from the measurement intended to assess it.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:357`:
  > a third `ConditionResult` "enrolled" over the shipped pipeline with the embedder + a synthetic in-memory profile
- Evidence: `desktop/src/scribe_desktop/speaker_eval.py:660–667`:
  ```python
  merged = len(labels) >= 2 and set(labels) == {SPEAKER_1}
  scorable = not merged and any(truth.true_label is not None for truth in truths)
  return ConditionResult(
      condition=name,
      predicted_labels=tuple(labels),
      merged=merged,
      metrics=cluster_metrics(labels, truths) if scorable else None,
      role=role_outcome(speaker_role(document), labels, truths),
  )
  ```
- Suggested change: Define an enrolled-condition policy that computes accuracy, confusion and purity even with one predicted cluster. Preserve legacy before/after semantics where required. Add harness cases for all-matched output over both clinician-only and clinician/patient label tracks; verify that the latter retains its measurable false-positive evidence.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: Task 2.4 — the enrolled condition computes cluster metrics even for an all-`speaker_1` output; the legacy conditions keep their merged semantics.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### PR-MED-015 — R3’s replacement denominator and removal counting are ambiguous

- Plan section: Task 5.5; Phase 6 gate verification.
- Materiality: build-affecting
- Why it matters: “Assertions the generator produced” can mean transcript-only draft assertions, excluding later-confirmed autofill/prefill assertions that the frozen rubric counts. A note with only confirmed proposals can consequently acquire a zero denominator. Counting removal actions also includes undone removals or a move’s removal leg unless explicitly excluded.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:379`:
  > R3's numerator = lines removed during review + lines still needing deletion at signing; denominator = assertions the generator produced (the count before any removal); thresholds untouched
- Evidence: Confirmed proposals are added during finalisation, `desktop/src/scribe_desktop/note.py:1939`:
  ```python
  sections = _merge_confirmed(draft.note_sections, confirmed)
  ```

  The existing rubric’s scoring population is stated at `docs/testing/shipping-gate.md:44`:
  > after every proposal is decided and every warning acknowledged, before Save — so R1–R5 count the same note for every scorer.

  Its R3 definition at `:48` is:
  > **R3 noise** = assertions that must be deleted / assertions in the note.
- Suggested change: Define the pre-removal denominator explicitly, including how finally confirmed proposal assertions are counted. Define distinct effective deletions, excluding restored removals, moves and undone manual additions, and specify treatment of any retained manual additions. Add text-free worked examples covering proposal-only notes, remove→undo and move. Verify that the agreed clarification preserves the intended rubric-v1 population before recording begins.
- /fix decision: Applied
- /fix notes: Verified build-affecting. Amended: Task 5.5 — the denominator is the post-decision, pre-removal note (transcript assertions + confirmed proposals), the numerator counts effective removals only, manual additions count in neither, three worked examples.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

PEER-PLAN-ROUND-1 RESULT: 15 findings (CRIT 0 / HIGH 1 / MED 14 / LOW 0; build-affecting 15 / record-only 0 / invalid 0).
- Composer note (2026-09-05, transcription): block transcribed verbatim from `.cursor/loops/practitioner-profile-plan-peer-r1-findings.md` (codex session `01a0715e-f6ba-7bf0-9fa5-e6c6d823b30a`, read 11:40-11:46 UTC then cut off by the usage limit, resumed 11:57-12:06 UTC with a write-the-round prompt, exit 0). Per-finding dispositions below are the owning planning session's; the peer's materiality labels are preserved beside them.

### Round 2 - 2026-09-05 - practitioner-profile plan, post-round-1-amendment independent cross-family codex plan peer-review (round 2)

- Round status: Closed (3 of 3 Applied 2026-09-05 as plan amendments; the four unconfirmed round-1 amendments completed; NOT converged — round 3 owed)
- Source: Codex plan peer-review
- Materiality: 2 build-affecting / 1 record-only / 0 invalid
- Plan reviewed at: f010d7d
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-practitioner-profile.md` in full; `AGENTS.md`; `docs/lessons.md`; `PLAN.md`.
  - Requested code in `desktop/src/scribe_desktop/note_config.py`, `speech.py`, `session.py`, `transcription.py`, `note.py`, `note_check.py`, `session_store.py`, `speaker_eval.py`, and `scripts/setup-models.py`.
  - Requested UI paths in `desktop/src/scribe_desktop/ui/microphone.py`, `models.py`, `transcript.py`, and `note.py`.
  - `docs/testing/shipping-gate.md`; `docs/testing/speaker-measurement.md`; `docs/design-system.md`; `docs/security/data-flow-map.md`; `docs/security/retention-schedule.md`; Phase 3A surfaces 1–4 and checker limits in `docs/security/threat-model.md`.
  - Pointer-only references for Task 2.3, D-S1, 9.1 and 9.2 in `.cursor/plans/plan-phase3a-note-pipeline.md`.
- Finding verification: 10 candidates / 7 dropped / 0 downgraded
- Verification method: Static review only. No tests run; no files or directories written. HEAD and working-tree status remained unchanged. Continuing PR-MED-004/005 defects are reported below, not counted again as NEW findings. Other dropped candidates concerned inherited custody residuals, already-addressed measurement behavior, unsupported validation concerns, and migration paths handled by recovery re-transcription.

#### Round-1 amendment confirmations

- **PR-HIGH-001 — NOT CONFIRMED.** D9, consent and Task 5.2 now require explicit no-patient-information confirmation and disclose plaintext retention, matching `note_config.py:8` and `:17`. However, the added name refusal conflicts with the prescribed content-token extraction: `note.py:222` lowercases tokens, while `transcription.py:326` requires uppercase for name detection. See new PR-MED-016.
- **PR-MED-002 — CONFIRMED.** Config / Environment / Deployment Impact, `.cursor/plans/plan-practitioner-profile.md:260`, now distinguishes the encrypted voice fingerprint from phrases “kept as plain text in your own config file until you delete them,” consistent with `desktop/src/scribe_desktop/note_config.py:8` and `_read_config_blob` at `:782`.
- **PR-MED-003 — CONFIRMED.** D3 (`plan:234`) requires the verified model digest; Task 1.1 (`plan:796`) hashes actual file bytes once at construction and refuses mismatch. This supplies the authentication absent from the cited `speech.py:197` path-loading precedent and follows actual-byte hashing at `scripts/setup-models.py:95`.
- **PR-MED-004 — NOT CONFIRMED.** D15 and Tasks 1.3/3.1/3.2 coordinate consumers while enrolment is held, but do not specify refusal when recording or a benchmark starts first, nor ownership through queued result handling. The referenced generation lease is explicitly “State-agnostic on purpose” (`desktop/src/scribe_desktop/session.py:746`); the benchmark owns a separate widget worker (`ui/microphone.py:291`). Flow 1 (`plan:214`) still says “Recording sessions is allowed throughout (D10).” Specify reverse admission, monitor handoff and result-handler release, with both start-order tests requested in round 1.
- **PR-MED-005 — NOT CONFIRMED.** D16 (`plan:246`) adds a model-free spectral embedder, but Task 1.1 (`plan:796`) still defines `speaker_model_available()` as a “STAT-only probe”; Task 2.1 (`plan:802`) conditions attribution on that probe; Task 3.1 (`plan:809`) still disables enrolment when the speaker model is absent. Explicitly branch availability, factories and UI on the selected embedder. `_segment_embedding` remains reusable (`desktop/src/scribe_desktop/transcription.py:579` and `:585`).
- **PR-MED-006 — CONFIRMED.** Tasks 0.3/0.6 and the handoff sequence (`plan:786`, `:789`, `:305`) now provide an explicit candidate path and practitioner-run verified promotion, matching `scripts/setup-models.py:110`–`:111`. The newly added app-status acceptance check introduces a separate sequencing defect, PR-MED-017.
- **PR-MED-007 — CONFIRMED.** D3, Schema / Data Changes and Tasks 2.1/2.2 (`plan:234`, `:250`, `:802`, `:803`) consistently use finite raw cosine in `[-1, 1]`, with zero-norm scoring defined as `-1`. Negative unconditional-fallback results therefore fit the document contract before persistence (`desktop/src/scribe_desktop/transcription.py:989`, `:1004`).
- **PR-MED-008 — CONFIRMED.** D3/D13 and Tasks 2.1/2.2 restrict the selected label to clusters with transcribed text and omit attribution when none is selectable (`plan:234`, `:243`, `:802`, `:803`). This matches the quotations filter at `desktop/src/scribe_desktop/ui/models.py:298` and radio creation at `ui/transcript.py:243`.
- **PR-MED-009 — CONFIRMED.** D4, Flow 2 and Task 2.3 (`plan:235`, `:217`, `:804`) satisfy only the role predicate and preserve template/config/recovery/lease gates. Phase 2 verification explicitly keeps Generate disabled until template selection, matching `desktop/src/scribe_desktop/ui/transcript.py:296`, `:303`, and `:400`.
- **PR-MED-010 — CONFIRMED.** D14 and Tasks 5.1/5.1b (`plan:244`, `:822`, `:823`) route every edit through acknowledgement invalidation before refinalisation. This matches `_after_resolution_change` at `desktop/src/scribe_desktop/ui/note.py:367`, necessary because acknowledgements are code-based (`:454`) and further removals can raise another `high_risk_omission` (`note_check.py:1432`).
- **PR-MED-011 — CONFIRMED.** D9 and Task 5.2 (`plan:240`, `:824`) require a dry-run verdict and an explicit warning/edit offer when an earlier cue wins. This fits the first-match loop at `desktop/src/scribe_desktop/note.py:1084`; no implicit precedence change or silent deletion is introduced.
- **PR-MED-012 — CONFIRMED.** D5 and Task 1.2 (`plan:236`, `:797`) retain the existing key for re-enrolment and atomically replace only `voice.enc`, with replacement fault-injection checks. This correctly respects the single-path commit boundary at `desktop/src/scribe_desktop/session_store.py:525`; the first-enrolment key-first path remains separate.
- **PR-MED-013 — CONFIRMED.** Agreed Scope and Task 6.1 (`plan:28`, `:836`) explicitly require distinct actual voices, including a third voice for the three-speaker consultation, with mock content and practitioner acceptance recorded. The gate-document clarification is scheduled before recording. This resolves the acoustic-identity conflict with `docs/testing/shipping-gate.md:17` and the clinician-majority scorer at `desktop/src/scribe_desktop/speaker_eval.py:583`.
- **PR-MED-014 — CONFIRMED.** Task 2.4 (`plan:805`) explicitly computes enrolled-condition cluster metrics for all-`speaker_1` output while retaining legacy semantics. This addresses the existing suppression at `desktop/src/scribe_desktop/speaker_eval.py:660`–`:666`.
- **PR-MED-015 — NOT CONFIRMED.** Task 5.5 (`plan:827`) correctly defines the post-proposal/pre-removal denominator, effective removals, move/undo exclusions and manual-addition treatment, consistent with `_merge_confirmed` at `desktop/src/scribe_desktop/note.py:1939`. Agreed Scope (`plan:31`) still repeats the ambiguous “assertions the generator produced” denominator and unqualified removal count. The remaining repair is record-only; see PR-LOW-018.

#### New findings

##### Unstated assumptions

###### PR-MED-016 — Content-token normalisation defeats the newly mandated name refusal

- Plan section: D9; Task 5.2; Critical Constraints.
- Materiality: build-affecting
- Why it matters: The canonical content-token function lowercases the candidate before the planned name heuristic examines it. A clinician-spoken “John Smith has diabetes” becomes “john smith has diabetes”; neither name can trigger this check. The explicit practitioner checkbox remains a control, so severity is MED. This is a mechanical interaction introduced by the amendment, not a request to overturn the accepted semantic-validation limit.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:824`:
  > leading 2–4 content tokens, editable, `_TriggerText`-validated live, REFUSED while any token is name-like per `is_name_like_token` or numeric
- Evidence: `desktop/src/scribe_desktop/note.py:225`–`:232`:
  ```python
  def content_tokens(text: str) -> tuple[str, ...]:
      """Normalised content tokens of ``text``: punctuation-only tokens and
      pure disfluencies dropped, everything else preserved in order."""
      tokens: list[str] = []
      for raw in text.split():
          token = normalise_token(raw)
          if token and token not in _FILLER_TOKENS:
              tokens.append(token)
  ```
  `desktop/src/scribe_desktop/note.py:222`:
  ```python
  return _STRIP_PUNCT_RE.sub("", token).lower()
  ```
  `desktop/src/scribe_desktop/transcription.py:325`–`:327`:
  ```python
  stripped = _STRIP_PUNCT_RE.sub("", text)
  if not stripped or not stripped[0].isalpha() or not stripped[0].isupper():
      return False
  ```
- Suggested change: Preserve original case in the displayed/editable candidate and run name/number checks before routing normalisation. Define the `first_in_segment` argument using the source-token position. Use canonical normalisation for matching and duplicate detection. Add a capitalised clinician-spoken identifier case proving the proposed candidate cannot silently lose the new guard.
- /fix decision: Applied
- /fix notes: Verified build-affecting (composer): `note.py:222` lowercases every token and `transcription.py:326` requires an initial capital, so the round-1 refusal could never fire. Amended: D9, Task 5.2 and Critical Constraints — the name/number check runs on the original-case SOURCE tokens before normalisation with `first_in_segment` from the word's position; the stored phrase is the normalised form; a capitalised clinician-spoken name is a pinned refusal case. This completes PR-HIGH-001.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### Practicality / feasibility / sequencing

###### PR-MED-017 — Task 0.6 requires an app status feature that is built only in Phase 3

- Plan section: Task 0.6; Task 3.2; Phase 0 handoff sequence.
- Materiality: build-affecting
- Why it matters: The new promotion step blocks Phase 1 on an app report that does not yet exist. Following the acceptance criterion literally prevents reaching the task that implements it.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:789`:
  > then launch the app and confirm the Status panel reports the speaker model present. Blocks: D-P1's Phase 1 start.

  `.cursor/plans/plan-practitioner-profile.md:810`:
  > `models.model_report_lines()` gains the speaker model + profile state (D2 visibility)
- Evidence: The current report ends with only Whisper and VAD, `desktop/src/scribe_desktop/ui/models.py:810`–`:814`:
  ```python
  vad_ready = vad_model_available()
  return [
      whisper_line,
      "VAD model (silero): " + ("ready" if vad_ready else missing),
  ]
  ```
  Its actual display owner is the microphone screen, `desktop/src/scribe_desktop/ui/microphone.py:271`–`:272`:
  ```python
  def refresh_model_status(self) -> None:
      self.model_status_label.setText("\n".join(models.model_report_lines()))
  ```
- Suggested change: Finish Task 0.6 with practitioner-context verification of the promoted filename and pinned digest, optionally using the existing Phase 0 smoke. Defer the app-report acceptance check to Task 3.2/3.4 and name its actual UI surface. Alternatively, explicitly move the minimal report implementation into Phase 0.
- /fix decision: Applied
- /fix notes: Verified build-affecting: `model_report_lines()` (`ui/models.py:810-814`) lists only whisper and VAD today and its display owner is the microphone screen's `refresh_model_status`. Amended: Task 0.6 verifies the promotion from the script's output (and the Phase 0 smoke), the in-app report check moves to Task 3.4 and Task 3.2 names its real surface. This completes PR-MED-006's sequencing.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

##### Missing verification / rollback / migration

###### PR-LOW-018 — Summary wording retains superseded scoring and activation claims

- Plan section: Agreed Scope, Piece 3; Accepted Assumptions; Task 5.5.
- Materiality: record-only
- Why it matters: The detailed contracts already establish the intended behavior, but their summaries still describe different scoring or an additional activation gate. Reconcile the summaries without changing Task 5.5’s rules or the practitioner’s fixed D4 decision.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:31`:
  > numerator = lines removed during review + lines still needing deletion at signing, denominator = assertions the generator produced

  `.cursor/plans/plan-practitioner-profile.md:110`:
  > the plan gates "auto-confirm on by default" on the Phase 6 run (Task 6.2), not on shipping the code.
- Evidence: The amended authoritative scoring task, `.cursor/plans/plan-practitioner-profile.md:827`, says:
  > numerator = EFFECTIVE removals (still in force at the scoring point — an undone removal and a move's removal leg do not count)

  The activation task, `.cursor/plans/plan-practitioner-profile.md:804`, says:
  > when `document.enrolled_speaker` is set, pre-check that radio

  Task 6.2, `.cursor/plans/plan-practitioner-profile.md:837`, specifies reassessment:
  > if auto-confirm correctness is below the shipped role accuracy, re-open D4's margin-gated alternative as a scoped `/review-plan`.
- Suggested change: Replace the abbreviated R3 formula with a pointer to Task 5.5, or reproduce its precise population and exclusions. Describe Phase 6 as measurement and a trigger for reassessment, removing the unsupported activation-gate claim. Preserve the frozen thresholds and unconditional D4 behavior.
- /fix decision: Applied
- /fix notes: Verified record-only: the Agreed Scope summary still carried the pre-amendment R3 formula and the accepted assumption still spoke of gating auto-confirm on Phase 6. Amended: the summary now points at Task 5.5's population and exclusions; the assumption says Phase 6 measures and can trigger a reassessment while D4 stays on. This completes PR-MED-015.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session, `/review-plan`-style amendments)

PEER-PLAN-ROUND-2 RESULT: 3 new findings (CRIT 0 / HIGH 0 / MED 2 / LOW 1; build-affecting 2 / record-only 1 / invalid 0); round-1 confirmations 11 of 15.
- Composer completions of the four round-1 amendments the peer did NOT confirm (2026-09-05): PR-HIGH-001 → completed by PR-MED-016; PR-MED-004 → D15 now specifies reverse admission (`begin_enrolment` refuses while a session is active or a benchmark runs), the monitor hand-off and suppression, release in the result handler, and both start-order tests plus a poll-tick test; Flow 1's "allowed throughout" corrected; PR-MED-005 → D16 and Tasks 1.1/2.1/3.1 key availability, the factories and the enrolment UI on `SHIPPED_SPEAKER_EMBEDDER`; PR-MED-015 → completed by PR-LOW-018.
- Composer note (2026-09-05, transcription): block transcribed verbatim from `.cursor/loops/practitioner-profile-plan-peer-r2-findings.md` (codex session `01a0717f-c16a-79b3-97cd-0a888fc5e01d`, `gpt-6-astra` at HIGH effort, 12:16-12:24 UTC, read-only, exit 0, 131k tokens). Dispositions are the owning planning session's; the peer's materiality labels are preserved.

## Tasks
Phases are grouped for `/execute-loop` (a `/review-loop` + cross-family peer pass at each boundary). No phase heading carries `[gates: high-auto-ok]`: this plan touches key custody, a biometric artefact, clinical-record content and a ratified safety relaxation, so HIGH findings pause for the practitioner by design. Every task is `[executor: premium-only]` in substance (Executor tier line); the label is omitted per task because the whole plan is premium.

### Phase 0 — Bookkeeping, consent, model candidate
- [ ] 🟥 0.1: **Record the gate pause by pointer.** `plan-phase3a-note-pipeline.md`: a dated bullet at the top of `Current State / Handoff Note` and one sub-bullet under Task 9.1 ("RUN PAUSED 2026-09-05 until `plan-practitioner-profile.md` Phase 3 ships; rubric v1 unchanged; the single recording set is that plan's Task 6.1"), the START HERE step 4 line annotated; `AGENTS.md` Next priority → this plan; CHANGELOG untouched (no code). Verification: the two files read back; the Phase 3A history checker still passes.
- [ ] 🟥 0.2: **Ratify the consent text** (PRACTITIONER). Read the draft in `Config / Environment / Deployment Impact`; approve or edit; record "ratified <date>, version consent-v1" on this task. Blocks: 3.1.
- [ ] 🟥 0.3: **Add the speaker-embedding candidate to `scripts/setup-models.py`.** Registry entry `speaker-embedding` (candidate name, URL, expected size; SHA-256 pin initially EMPTY = "candidate mode": the script downloads to `models/speaker-embedding/<name>.onnx.candidate`, prints size and SHA-256, and does not promote it until a pin exists; the smoke takes an explicit model path so it can read the candidate file); `--only speaker-embedding` accepted; `scripts/README.md` line. Plus `scripts/speaker-embedding-smoke.py`: loads the ONNX (the `SileroVad` contract), embeds each WAV given on the command line with the numpy front-end (D12), prints the cosine matrix and dims — text-free. Verification: `--help` and the `--only` validation tested without network; the smoke's front-end unit-tested on synthetic PCM (shape, determinism).
- [ ] 🟥 0.4: **Fetch the candidate and run the smoke** (PRACTITIONER, normal terminal): `setup-models.py --only speaker-embedding`; report the printed size + SHA-256; record two ~20 s recordings of yourself (different days or rooms if possible) and one other person as 16 kHz mono WAVs; run the smoke; paste the cosine matrix onto this task. Blocks: 0.5, D-P1.
- [ ] 🟥 0.5: **Pin the model** — SHA-256, size and URL into `setup-models.py` (candidate mode removed for this entry); `AGENTS.md` step 3 size note; `docs/security/data-flow-map.md` flow 9 (the one network flow) gains the model. Verification: the pin test (a wrong digest refuses, like silero).
- [ ] 🟥 0.6: **Promote the pinned model** (PRACTITIONER, normal terminal): re-run `setup-models.py --only speaker-embedding` — it verifies the candidate file against the pin and promotes it to `<name>.onnx` (PR-MED-006) — then confirm from the script's own output the promoted filename and the verified digest (optionally re-run the Task 0.3 smoke against the promoted path). The in-app report of the model's presence is Task 3.2's (the microphone screen's model status label, `refresh_model_status`) and is checked at the Task 3.4 smoke, not here (round 2 PR-MED-017). Blocks: D-P1's Phase 1 start.
- [ ] 🟥 D-P1: **Choose the model and the attribution threshold.**  `[decision]`
  - Options: candidate 1 (WeSpeaker ResNet34-LM) / candidate 2 (ECAPA-TDNN export) / spectral features only (`SpectralSpeakerEmbedder`, D16 — no model)
  - Decide after: Task 0.4's cosine matrix shows same-speaker similarity clearly above different-speaker (a gap of at least 0.2 is the expected shape); the threshold constant is set at the midpoint and re-checked in Phase 6
  - Blocks: 1.1, 2.1

### Phase 1 — Embedder and profile custody (foundation)
- [ ] 🟥 1.1: **`speaker_embedding.py` (new).** `SpeakerEmbedder` (protocol) + `OnnxSpeakerEmbedder(model_path)`: `assert_offline_env` before `import onnxruntime`; `SessionOptions`, telemetry off, UNC refused, `SpeakerModelError` at load (missing/corrupt/wrong I/O shape, probed at construction — the `VadModelError` contract); `embed(pcm16: bytes) -> np.ndarray` L2-normalised; the numpy fbank front-end (D12) as `_fbank(pcm)`; `default_speaker_model_path()`, `SHIPPED_SPEAKER_EMBEDDER` (D-P1's choice), `speaker_embedder_available()` (spectral: always; onnx: a STAT-only, UNC-safe probe of the pinned file), `build_speaker_embedder()` returning the selected class (D16), `MockSpeakerEmbedder` (deterministic vectors keyed by a caller-supplied map) for tests. `model_id` + `model_sha256` properties — the digest computed from the model FILE'S BYTES once at construction and checked against the pinned value, a mismatch raising `SpeakerModelError` so a shape-compatible substitute cannot pass as the pinned model (round 1 PR-MED-003); `SpectralSpeakerEmbedder` alongside (D16). Verification: Phase 1 tests; mypy override for onnxruntime already exists.
- [ ] 🟥 1.2: **`practitioner_profile.py` (new).** `PractitionerProfile` (frozen pydantic: `schema_version=1`, `model_id`, `model_sha256`, `embedding: tuple[float, ...]`, `embedding_dim`, `created_at`, `enrolment_speech_seconds`, `device_name`, `consent: ConsentRecord(accepted_at, consent_text_version, learning_opt_in)`); `default_profile_root()`; `save_profile(profile)` (first enrolment: fresh `SessionCrypto`, DPAPI-wrap with the profile description, key written first; re-enrolment: the EXISTING key reused and only `voice.enc` replaced atomically — D5, PR-MED-012; AES-GCM with the v1 AAD; fault-injection tests around each step prove a failed re-enrolment leaves the prior profile usable); `load_profile() -> PractitionerProfile | None` (absent → None; unreadable/undecryptable/wrong AAD/wrong model → `ProfileUnusableError` naming which); `delete_profile()` (key unlink first, then blob, idempotent); the DPAPI helpers in `session_store.py` gain a `description` parameter (session callers unchanged). No logging anywhere in the module. Verification: Phase 1 tests incl. the log-tripwire fixture extension.
- [ ] 🟥 1.3: **`enrolment.py` (new).** `record_enrolment(backend, device_id, *, target_speech_seconds=30.0, max_seconds=90.0, on_progress) -> bytes` — opens `CaptureBackend.open_stream` into an in-memory buffer (the microphone screen's monitor-stream shape), VAD-gates with `SileroVad` to count speech seconds, stops at the target or the cap, returns PCM (raises `EnrolmentTooShortError` under the target); `enrol(pcm, embedder) -> tuple[np.ndarray, float]` (mean of per-VAD-segment embeddings, L2-normalised, speech seconds); the caller drops the PCM. Never creates a session or touches any store; it runs INSIDE `SessionController.begin_enrolment()` (D15) so Start/Resume, the monitor poll and the benchmark refuse meanwhile. Verification: mock-backend tests; "no file written anywhere" pinned with a temp `LOCALAPPDATA`.
- [ ] 🟥 1.4: **Phase 1 tests + docs stubs.** `tests/test_speaker_embedding.py`, `tests/test_practitioner_profile.py`, `tests/test_enrolment.py`; the retention-schedule row and the threat-model surface drafted (finalised in 3.3). Verification: the Phase 1 list in `Validation / Verification`; suite green.

### Phase 2 — Attribution in the pipeline, auto-confirm, harness
- [ ] 🟥 2.1: **`transcription.py` attribution.** `transcribe_session(..., speaker_embedder: SpeakerEmbedder | None = None, enrolled_profile: PractitionerProfile | None = None)`: inside the windowed loop compute the model embedding per segment when both are supplied (the spectral embedding still computed for the remainder clustering); at the end `attribute_speakers(similarities, spectral_embeddings, threshold)` → labels per D13 (matched → `speaker_1`; the rest → `_cluster_embeddings` among themselves as `speaker_2`/`speaker_3`; zero matches → ordinary 2-means over all segments with the higher-similarity cluster as `speaker_1`; degenerate policy unchanged and still mirrored with `label_speakers`); set `enrolled_speaker` (always when a profile is applied and at least one cluster holds a segment with text — D3/D13; a document with no segments carries no attribution fields), `enrolment_similarity` (raw cosine in [-1, 1]), `speaker_model_id` on the document; without both inputs the current path runs byte-for-byte. `ui/models.py` `build_transcriber` AND `build_recovery_runner` pass `build_speaker_embedder()` + the profile when `speaker_embedder_available()` and a profile loads whose `model_id` matches the selected embedder (else report the fallback, D2); `recover_session_transcription` gains the same two parameters. Verification: Phase 2 tests; the existing batching/plaintext-bound tests unchanged.
- [ ] 🟥 2.2: **`TranscriptDocument` fields** (Schema / Data Changes) with the validators `enrolled_speaker ∈ {labels of segments that have transcribed text}` and `enrolment_similarity` finite in [-1, 1]; `read_transcript` round-trip; `models.speaker_quotations` unchanged. Verification: round-trip + validator tests.
- [ ] 🟥 2.3: **Auto-confirm on the Transcript screen (D4).** `_populate_generation_controls`: when `document.enrolled_speaker` is set, pre-check that radio, render the line "Clinician: confirmed from your voice profile (similarity 0.xx) — change" (a link-styled button); Generate stays gated on the template profile, config, recovery and lease exactly as today (PR-MED-009); "change" un-checks and shows the manual radios with `speaker_role`'s " (suggested)"; when `None`, today's behaviour. `set_role` / `_selected_role` unchanged (the selection stays the UI state `generate()` reads). Status line for the fallback cases (D2). Verification: offscreen tests listed for Phase 2; the lying-field defence (a document whose `enrolled_speaker` names no segment is refused at construction, so the UI never sees it).
- [ ] 🟥 2.4: **`speaker_eval.py` enrolled condition.** `--enrolment <wav>` (16 kHz mono; refused otherwise) → the enrolment vector via `enrol()`; a third `ConditionResult` "enrolled" over the shipped pipeline with the embedder + a synthetic in-memory profile; the enrolled condition computes `cluster_metrics` even when every predicted label is `speaker_1` (an all-matched output is a measurable false-positive case, not a merged one — PR-MED-014; the legacy two conditions keep their merged semantics); a `RoleOutcome` for the auto-confirmed label (correct when the matched cluster is mostly the `clinician` label); leave-one-out from labelled clinician spans as the documented fallback when no enrolment WAV is given; report columns; `scripts/measure-speakers.py` flag; `docs/testing/speaker-measurement.md`. Teardown contract untouched (the profile is in memory only — never written by the harness). Verification: harness tests with `MockSpeakerEmbedder`.
- [ ] 🟥 2.5: **Threat-model + data-flow entries for attribution and D4** (drafted; finalised in 3.3). Verification: docs re-read against the code.

### Phase 3 — Practitioner surface and documentation
- [ ] 🟥 3.1: **`ui/practitioner.py` — the Practitioner tab.** Consent text (`CONSENT_TEXT_V1` + version constant in `ui/models.py`, ratified in 0.2) with the consent checkbox and the learning opt-in checkbox; device pick (the microphone screen's device list); "Record my voice (about a minute)" with a live level and a speech-seconds counter, running `record_enrolment` on a `TaskThread` (GUI thread never blocks; the whole capture → embed → save sequence runs under `begin_enrolment()` — D15 — so the monitor poll, Start/Resume and the benchmark refuse meanwhile and Re-record/Delete are disabled); on success `enrol` + `save_profile`, PCM dropped, status "Voice profile saved <date> (model <id>)"; "Re-record" and "Delete voice profile" (confirm dialog); a "Learned phrases" list placeholder (Phase 5); disabled states only when the SELECTED embedder is unavailable (the onnx file absent — the message names `setup-models.py`; spectral is always available, D16). Verification: Phase 3 offscreen tests.
- [ ] 🟥 3.2: **First-run behaviour + report lines.** `MainWindow`: at startup with no profile, select the Practitioner tab and show a banner ("Set up your voice profile so the app always knows which words are yours — you can still record without it"); `models.model_report_lines()` gains the speaker model + profile state (D2 visibility; shown by the microphone screen's `refresh_model_status` label — the surface Task 0.6 defers to, PR-MED-017); `closeEvent` refuses close while the enrolment activity is held (D15). Verification: offscreen tests.
- [ ] 🟥 3.3: **Docs.** `threat-model.md`: surface 5 — the practitioner's own biometric at rest (same-user residual; DPAPI; deletion) and the D4 auto-confirm relaxation as a practitioner-ratified responsibility boundary with its named residual; `retention-schedule.md`: profile row (indefinite until deleted; deletion = key deletion; never swept) and the consent record; `data-flow-map.md`: flow 12 (microphone → in-memory PCM → embedding → profile store), the model-cache entry, the explicit non-flows (no enrolment audio on disk); `design-system.md`: the first-run surface convention and the confirmation-line pattern; `AGENTS.md` Subsystem Documentation pointer; CHANGELOG. Verification: every claim traced to a call site (the docs review class).
- [ ] 🟥 3.4: **Phase 3 smoke by the PRACTITIONER**: fresh start → banner → consent → enrol → a mock consultation → auto-confirmed role shown → Generate. Record PASS/FAIL here.

### Phase 4 — Per-practitioner cue file
- [ ] 🟥 4.1: **Ship the defaults file.** `config_defaults/section_cues.json` generated from `_RAW_SECTION_CUES` (17 keys, 98 phrases, canonical key order); `note.py` derives `_RAW_SECTION_CUES` / `DEFAULT_SECTION_CUES` FROM the packaged file at import (one source; a test pins equality with the 17/98 counts). Verification: counts test.
- [ ] 🟥 4.2: **Loader + model.** `note_config.py`: `SectionCuesFile(schema_version: Literal[1], section_cues: Mapping[NoteSectionKey, tuple[_TriggerText, ...]])` with the D6 validations; `NoteConfig.section_cues`; a `normalised_cues()` accessor returning the `DEFAULT_SECTION_CUES` shape; `load_note_config` reads the fourth filename with the same precedence; module docstring updated (a missing key = no cues for that section). Verification: Phase 4 loader tests; digest-pin inventory updated.
- [ ] 🟥 4.3: **Provider from config.** `ui/models.py` `build_note_generator(provider_factory: Callable[[NoteConfig], NoteModelProvider] = lambda cfg: ExtractiveNoteProvider(cues=cfg.normalised_cues()))`; tests that pass a factory updated. Verification: a user file that removes/adds a cue changes routing through the window path (offscreen test).
- [ ] 🟥 4.4: **Phase 4 tests + docs.** Loader properties (absent/malformed/unknown key/blank/duplicate/digest), `note_check.py:140-146` honesty note updated to name the file, `data-flow-map.md` flow 11 + `retention-schedule.md` config row name the fourth file, `docs/testing/shipping-gate.md` "Preparing" names it. No literal digest pin exists (Key Findings), so the fourteen equality pins need no edit. Verification: suite green.
- [ ] 🟥 4.5: **The gate-run cue file** (PRACTITIONER supplies phrases; executor authors): `docs/testing/shipping-gate-config/section_cues.json` = the shipped defaults plus the practitioner's own phrases for advice, treatment, plan and follow-up; README updated; validated through the loader. Verification: the loader smoke in the README.

### Phase 5 — Consented phrase learning
- [ ] 🟥 5.1: **"Add a transcript line" on the Note tab (D14).** An explicit control group beside the transcript panel (the panel stays a non-interactive text box): an utterance chooser listing the utterances not already in the note, labelled by segment index + speaker + the first words; a section chooser limited to the sections that utterance may enter (clinician-owned → the confirmed clinician's non-questions only; the `_route` ownership rule reused, not re-implemented); Add appends a `transcript`-provenance `NoteAssertion` (contiguous coords for the whole utterance, id `m<segment>`) to the screen's working draft through the content-change helper (acknowledgements cleared, note un-saved, re-finalised — D14, PR-MED-010); Undo removes it again the same way; edits disabled after Save. Verification: Phase 5 tests incl. Check 1 reconstruction and the duplicate refusal.
- [ ] 🟥 5.1b: **Remove / Move a routed line (D14).** Per rendered `transcript`-provenance assertion: "Remove line" adds its id to the screen's removed set; "Move to section…" = remove + add through the 5.1 path under the same ownership rules; the content-change helper filters removed ids out of the working draft before `finalise_note` (acknowledgements cleared — PR-MED-010); an omission warning the checker raises for a removed line is acknowledgeable (review severity) and named in the warning copy; Undo restores; frozen after Save. Verification: Phase 5 tests (remove → warning acknowledgeable, never blocking; undo; move; frozen after Save).
- [ ] 🟥 5.2: **"Learn this phrasing?" prompt.** After an add or a move of one of the practitioner's own utterances, when `learning_opt_in` is on: a dialog showing the section, the candidate phrase (leading 2–4 content tokens, editable, `_TriggerText`-validated live, REFUSED while any SOURCE token, in original case and before normalisation, is name-like per `is_name_like_token(word, first_in_segment=...)` or numeric — PR-HIGH-001 / PR-MED-016; the displayed candidate keeps original case, the stored phrase is `content_tokens`' normalised form; a capitalised clinician-spoken name is a pinned refusal case), a dry-run verdict ("with this phrase the line routes to <section>", or a warning that an earlier section's cue still wins first-match routing plus an offer to edit — never a silent cue deletion, PR-MED-011), the exact JSON line to be appended, and a mandatory "This phrase contains no patient information" checkbox; Approve → `note_config.append_user_cue(section_key, phrase)` (creates the user file from the shipped default if absent; atomic replace; refuses duplicates with the same message the loader would give); Decline → nothing written; opt-in off → a one-line hint pointing at the Practitioner tab. Verification: Phase 5 tests.
- [ ] 🟥 5.3: **Practitioner tab: learned phrases.** List = phrases in the user `section_cues.json` not present in the shipped default, grouped by section; Delete removes one (atomic replace); the loader is the only reader. Verification: offscreen tests.
- [ ] 🟥 5.4: **Docs + tests.** Threat-model surface 1 (config as note-content input) extended to the learned-phrase path, naming the semantic limit (the app cannot classify meaning; the name/number refusal plus the practitioner's confirmation are the controls — PR-HIGH-001); surface 2 (clinician-asserted content) extended to review edits (subtract-only, D14); data-flow-map flow 13 (review → approved phrase → cue file); `design-system.md` (the edit controls); CHANGELOG. Verification: suite green.
- [ ] 🟥 5.5: **Gate-doc R3 clarification** (`docs/testing/shipping-gate.md` "What is measured" + the R3 line in the plan's Task 9.1 table header, both plans): with Remove available: denominator = the assertions in the note at the scoring point BEFORE any removal but AFTER every proposal decision (transcript assertions + confirmed proposals — the population rubric v1 already scores); numerator = EFFECTIVE removals (still in force at the scoring point — an undone removal and a move's removal leg do not count) + lines still needing deletion at signing; manual additions count in neither; thresholds untouched; three text-free worked examples in the doc (a proposal-only note, remove → undo, a move) — PR-MED-015; the practitioner initials the clarification on this task. Verification: re-read; no number changed.

### Phase H — Hardening stage
- [ ] 🟥 H1: `/review-loop` (or `/review` → `/fix`) to convergence over Phases 1–5 as one surface
- [ ] 🟥 H2: `/simplify` — log findings; trivial → `/fix`, substantial → scoped `/review-plan`
- [ ] 🟥 H3: `/security-review` — log findings; same impact-tiered routing (custody, consent, the D4 residual, the cue-file input surface)
- [ ] 🟥 H4: final cross-family `/peer-review` (codex) re-check to confirm convergence

### Phase 6 — Measurement and gate resumption (PRACTITIONER-owned)
- [ ] 🟥 6.1: **The single recording set.** Per the protocol in `Agreed Scope`: ~10 mock consultations recorded through the app AND in parallel to labelled 16 kHz WAVs (Audacity role-label tracks; one three-speaker consultation), plus one enrolment WAV; **voices (PR-MED-013):** the practitioner speaks ONLY the clinician part and a second real person (a colleague or family member; mock content, no real patient) speaks the patient part, with a third real voice for the three-speaker consultation — one person acting both parts cannot be scored for speaker separation or auto-confirm, because enrolment recognises a person, not a part; the gate doc's mock definition is clarified accordingly at Task 5.5 (thresholds untouched); practitioner-accepted 2026-09-05; the retention decision for the WAVs settled and recorded in the Phase 3A plan's Task 2.3.
- [ ] 🟥 6.2: **Run the harness** (`scripts/measure-speakers.py --enrolment <wav> <dir>` from a normal terminal); record the three conditions' numbers and the auto-confirm correctness here AND in the Phase 3A plan's Task 2.3; decide D-S1 there; if auto-confirm correctness is below the shipped role accuracy, re-open D4's margin-gated alternative as a scoped `/review-plan`.
- [ ] 🟥 6.3: **Resume the Task 9.1 gate run** in the Phase 3A plan against rubric v1 with the same consultations (the gate scoring happened at recording time in 6.1 — the sheet under Task 9.1 is filled from it); the pause pointer from 0.1 closed.

## Retained Follow-Up Items
(Not applicable while plan is Active.)

## Follow-Up Continuation Notes
(Not applicable while plan is Active — populated at completion.)

---
*Plan saved to: .cursor/plans/plan-practitioner-profile.md*
*To resume in a new session: open a fresh Agent (Ctrl+I), run /start-session, then run /load-plan*
