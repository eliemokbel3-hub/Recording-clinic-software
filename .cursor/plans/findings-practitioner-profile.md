# Review findings — practitioner profile

Companion to `plan-practitioner-profile.md`. It holds the FULL review round blocks that the plan carries only as digests.

**Lifecycle:** this file and its companion plan are ONE unit — move, archive or delete them together. A round present here must have its digest (or, mid-recovery, its full copy) in the plan; a round digest in the plan must have its full block here.

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

### Round 3 - 2026-09-05 - practitioner-profile plan, post-round-2-amendment independent cross-family codex plan peer-review (round 3, confirmation)

- Round status: Closed (1 of 1 Applied 2026-09-05, record-only) — PASS CONVERGED at this round
- Source: Codex plan peer-review
- Materiality: 0 build-affecting / 1 record-only / 0 invalid
- Plan reviewed at: 8819173
- Files read:
  - `.agents/skills/peer-review/SKILL.md`; `.cursor/plans/plan-practitioner-profile.md` in full.
  - Requested symbols and surrounding code in `desktop/src/scribe_desktop/note.py`, `transcription.py`, `session.py`, `ui/microphone.py`, `ui/models.py`, and `scripts/setup-models.py`.
  - Privacy contract in `desktop/src/scribe_desktop/note_config.py`; requested sections of `docs/testing/shipping-gate.md`; `docs/lessons.md`.
  - Pointer-only matches for Task 2.3, D-S1, 9.1 and 9.2 in `.cursor/plans/plan-phase3a-note-pipeline.md`.
- Finding verification: 3 candidates / 2 dropped / 0 downgraded
- Verification method: Static review only. No tests run; no files or directories written. Working tree remained clean. Dropped candidates concerned acknowledgement invalidation and the R3 proposal population, both already explicitly handled.

#### Round-2 change confirmations

- **PR-MED-016 — CONFIRMED.** D9, Critical Constraints and Task 5.2 consistently require original-case checks before normalisation (`.cursor/plans/plan-practitioner-profile.md:240`, `:273`, `:958`). Task 5.2 states “the displayed candidate keeps original case”. This addresses `desktop/src/scribe_desktop/note.py:222`, `return _STRIP_PUNCT_RE.sub("", token).lower()`, preceding the uppercase-dependent check at `desktop/src/scribe_desktop/transcription.py:326`. D9 also specifies `first_in_segment` from source-word position.
- **PR-MED-017 — NOT CONFIRMED in full; build sequencing is corrected.** Task 0.6 now verifies promotion through script output and assigns the later app check to Phase 3 (`.cursor/plans/plan-practitioner-profile.md:923`), consistent with `scripts/setup-models.py:111`, `tmp.replace(target)`. Task 3.2 correctly names the Microphone screen. However, Flow 3 still names the Status panel (`plan:220`), contradicting that amendment and `desktop/src/scribe_desktop/ui/microphone.py:271–272`. The remaining defect is record-only; see PR-LOW-019.
- **PR-LOW-018 — CONFIRMED.** Agreed Scope now points to Task 5.5’s precise population and exclusions (`.cursor/plans/plan-practitioner-profile.md:31`). The assumption at `:110` says “Phase 6 MEASURES auto-confirm and can trigger a reassessment”, consistent with unconditional activation in Task 2.3 (`:938`) and reassessment in Task 6.2 (`:971`).
- **PR-HIGH-001 — CONFIRMED.** The original-case refusal completes the mechanical repair; Task 5.2 requires “This phrase contains no patient information” (`.cursor/plans/plan-practitioner-profile.md:958`). Consent discloses plaintext retention and practitioner judgement (`:260`), while Task 5.4 names the semantic limit (`:960`). This matches `desktop/src/scribe_desktop/note_config.py:17`, `"NOT patient data" is a POLICY, not an enforced property.`
- **PR-MED-004 — CONFIRMED.** D15 explicitly covers reverse admission, monitor handoff and polling suppression, ownership through the result handler, release on every path, and both start-order tests (`.cursor/plans/plan-practitioner-profile.md:245`). Flow 1 now says “Recording is allowed before and after enrolment (D10), never during it (D15)” (`:214`). This addresses the state-agnostic generation precedent (`desktop/src/scribe_desktop/session.py:746`), `ACTIVE_STATES` (`:88–89`), monitor reopening (`ui/microphone.py:199`) and separate benchmark worker (`:291–295`).
- **PR-MED-005 — CONFIRMED.** D16 and Tasks 1.1, 2.1 and 3.1 consistently select availability, construction and UI behaviour through the chosen embedder (`.cursor/plans/plan-practitioner-profile.md:246`, `:930`, `:936`, `:943`). Task 1.1 explicitly specifies “spectral: always”. The spectral implementation exists at `desktop/src/scribe_desktop/transcription.py:579–585`; both production factories are covered (`ui/models.py:828`, `:856`).
- **PR-MED-015 — CONFIRMED.** Task 5.5 explicitly includes “transcript assertions + confirmed proposals”, effective-removal counting, move/undo exclusions and manual-addition treatment (`.cursor/plans/plan-practitioner-profile.md:961`); Agreed Scope now delegates to that contract (`:31`). This matches `desktop/src/scribe_desktop/note.py:1939`, `sections = _merge_confirmed(draft.note_sections, confirmed)`, and the post-proposal scoring point at `docs/testing/shipping-gate.md:44`.

#### New findings

##### Practicality / feasibility / sequencing

###### PR-LOW-019 — Flow 3 still names the wrong model-report surface

- Plan section: Planned Workflow Summary, Flow 3; Task 3.2.
- Materiality: record-only
- Why it matters: The implementation and verification tasks now identify the correct surface, but the workflow summary directs readers elsewhere. Correcting that summary changes neither the build nor its verification.
- Current plan text: `.cursor/plans/plan-practitioner-profile.md:220`:
  > The Status panel's model report says the speaker model is absent (or the profile needs re-enrolment) so the degradation is visible, never silent.
- Evidence: Task 3.2, `.cursor/plans/plan-practitioner-profile.md:944`:
  > shown by the microphone screen's `refresh_model_status` label

  `desktop/src/scribe_desktop/ui/models.py:791`:
  > Model-readiness lines for the microphone screen's report panel.

  `desktop/src/scribe_desktop/ui/microphone.py:271–272`:
  ```python
  def refresh_model_status(self) -> None:
      self.model_status_label.setText("\n".join(models.model_report_lines()))
  ```
- Suggested change: Replace “The Status panel's model report” in Flow 3 with “The Microphone screen's model report”. Preserve Tasks 0.6 and 3.2’s amended sequencing and surface.
- /fix decision: Applied
- /fix notes: Verified record-only (composer): Flow 3 still said "Status panel" while Tasks 0.6/3.2 name the Microphone screen's `refresh_model_status` label (`ui/microphone.py:271-272`, `ui/models.py:791`). Amended: Flow 3 now names the Microphone screen's model report. This completes PR-MED-017.
- /fix date: 2026-09-05
- /fix applied by: Claude Code (`claude-fable-5-1`, owning planning session)

PEER-PLAN-ROUND-3 RESULT: 1 new findings (CRIT 0 / HIGH 0 / MED 0 / LOW 1; build-affecting 0 / record-only 1 / invalid 0); round-2 confirmations 6 of 7.
- Composer note (2026-09-05, transcription): block transcribed verbatim from `.cursor/loops/practitioner-profile-plan-peer-r3-findings.md` (codex session `01a073fb-0aed-71a0-acb2-e80a5205aa2b`, `gpt-6-astra` at HIGH effort, 23:50-23:54 UTC, read-only, exit 0, 87k tokens; the first round-3 attempt at 12:27 UTC died on the usage window after two commands and emitted nothing). PASS CONVERGED: zero NEW build-affecting findings this round; 6 of 7 round-2 changes confirmed and the seventh completed by PR-LOW-019.

### Round 4 - 2026-09-06 - practitioner-profile Phase 0 (Tasks 0.1 + 0.3), in-session `/review-loop` round 1 of cap 3
- Round status: Closed (4 of 4 Applied 2026-09-06 by Claude Code, one at a time, each verified by re-read; the two code fixes await the composer's suite re-run before round 5)
- Fix-delta self-check: PASS — re-read 4 applied hunks across 3 files (`setup-models.py` skip line, the smoke's `render_matrix` width, the Task 0.4 recipe, the Task 1.1 sub-bullet); no neighbouring exit path touched, no drive-by, the pinned strings ("[skip]", the digest, 6-character test names) unchanged.
- Source: Claude Code
- Primary review baseline: the working tree against `main` `ea5775e` (the first code round of this work; the plan's `Last plan sync` predates every change). Changed files, all read in full, nothing skipped: `scripts/setup-models.py`, `scripts/speaker-embedding-smoke.py` (new), `scripts/README.md`, `desktop/tests/test_setup_scripts.py` (new), `.cursor/plans/plan-phase3a-note-pipeline.md`, `.cursor/plans/plan-practitioner-profile.md`. Suites at review time: composer-run GREEN (ruff, mypy 30 files, pytest 1408).
- Looks good: the offline assertion precedes the `onnxruntime` import and is pinned with the import made un-importable; candidate mode never writes `<name>.onnx`; the pinned path is silero's shape (verify, atomic write, mismatch exits with both digests); the default `setup-models.py` run is unchanged while unpinned and says so; the front-end matches WeSpeaker's Kaldi recipe step for step (DC removal → 0.97 pre-emphasis → window → 512-point power spectrum without Nyquist → 80 Kaldi-mel triangles 20 Hz–Nyquist → float32-eps log floor → CMN) with the tone-peak and geometry pins; no transcript, PCM or audio content is printed anywhere; no new dependency, env var or persisted artefact.
- Finding verification: 6 candidates; 2 dropped (the `urlopen` redirect-downgrade residue — the https check covers the initial URL only — is silero's pre-existing pattern, closed by the digest once pinned and by the reported digest in candidate mode; `scripts/README.md` never listing `setup-models.py` is a pre-existing omission outside Task 0.3); 0 downgraded. *[Corrected 2026-09-06 by peer round 6 PR-HIGH-002: the first dismissal was WRONG for candidate mode — a digest of unpinned bytes identifies what arrived, it does not authenticate the origin, so the reported digest does not close the downgrade; fixed in round 6 (https enforced on every redirect hop). The silero half of the reasoning stands: its pre-existing pin makes the transport immaterial.]*
- Executor judgment: LOW-004 only (the smoke duplicates the load contract and front-end Task 1.1 will own — routed as a plan note, not a code change now). Structural quality: none. Post-fix regression check: round 1 — no prior fixes; regression baseline = the working tree; none.
- Missed-issue pass: re-read all six changed files with fresh eyes (the two scripts and the test module line by line; the README entry; both plans' edited regions); result: LOW-003.
- `ROLE: round` line: NOT written to `.cursor/loops/` (executor write scope — the only loop-log write is the `VERIFY_OK` emit); the composer's log owns it.
- **[LOW]** LOW-001: `scripts/setup-models.py` `fetch_speaker_embedding`, candidate branch — the "[skip] speaker-embedding candidate already downloaded" line names no way to fetch a DIFFERENT candidate (D-P1's second option, the ECAPA export): the practitioner must delete the `.candidate` file by hand and nothing says so. Desired: the skip line states the remedy. Verification: re-read; `test_existing_candidate_is_reported_without_network` still pins "[skip]" + the digest. — Triage: Fix-now; Decision: Applied (2026-09-06, Claude Code — the skip line now says "to fetch a DIFFERENT candidate, delete this .candidate file and re-run with its --candidate-url"; siblings: none)
- **[LOW]** LOW-002: `scripts/speaker-embedding-smoke.py` `render_matrix` — the column width is the longest file name, so a name shorter than the 5-character "1.000" cell misaligns the matrix the practitioner pastes onto Task 0.4. Desired: a floor of 6 on the width. Verification: re-read; `test_render_matrix_is_numbers_and_names_only` unchanged (6-character names). — Triage: Fix-now; Decision: Applied (2026-09-06, Claude Code — `width = max([len(name) for name in names] + [6])`; siblings: none)
- **[LOW]** LOW-003 (missed-issue pass): this plan, Task 0.4 "How to run it" sub-bullet — the Audacity recipe paraphrases `speaker_eval.WAV_FORMAT_HELP` with different menu wording ("Tracks → Mix → Stereo to Mono", "Export → WAV signed 16-bit PCM" vs the canonical "Tracks > Mix > Mix Stereo Down to Mono", "Export Audio > WAV 16-bit PCM"); two recipes for one format drift, and the reader's refusal message quotes the canonical one. Desired: quote the canonical string. — Triage: Fix-now; Decision: Applied (2026-09-06, Claude Code — the Task 0.4 sub-bullet now carries the `WAV_FORMAT_HELP` recipe verbatim and says the reader quotes it on refusal; siblings: `scripts/README.md`'s smoke entry states the format only, no recipe — nothing to change)
- **[LOW]** LOW-004 (scope expansion, LOW): `scripts/speaker-embedding-smoke.py` `fbank` / `load_session` / `SpeakerModelError` are a private copy of what Task 1.1 defines canonically in `speaker_embedding.py`; left as two copies, the D-P1 evidence and the shipped front-end can drift. Scope-expansion disposition: Include in plan — headless AUTO-DISPOSABLE (LOW, do-the-work, not production-impacting): a sub-bullet on Task 1.1 (not a new task — it refines 1.1's own single-front-end goal): the smoke imports the module's front-end and embedder, its private copies are retired, and the Task 0.3 front-end tests move to the module's suite. Production-impact: no. — Triage: Fix-now (plan note); Decision: Applied (2026-09-06, Claude Code — the "One front-end, one load contract" sub-bullet added under Task 1.1; no code touched; siblings: none)

### Round 5 - 2026-09-06 - practitioner-profile Phase 0 (Tasks 0.1 + 0.3), in-session `/review-loop` round 2 of cap 3 (confirmation)
- Round status: Closed (0 findings) — LOOP CONVERGED at this round
- Source: Claude Code
- Primary review baseline: unchanged from round 4 — the working tree against `main` `ea5775e`; the same six changed files (`git status` identical), every one re-read in full from disk (the whole `setup-models.py` diff, the smoke, the test module, the README entry, both plans' edited regions). Suites after the round-4 fixes: composer-run GREEN (ruff clean, mypy 30 files, pytest 1408 passed, 60.8 s).
- Post-fix regression check (regression baseline = the pre-`/fix` working tree of round 4): four hunks — the candidate-mode skip line (message only; `test_existing_candidate_is_reported_without_network` still pins "[skip]" + the digest and passed), the `render_matrix` width floor (no signature change; the 6-character test names produce the same output; passed), the Task 0.4 recipe and the Task 1.1 sub-bullet (plan prose). No signature, return value or data shape changed; no caller affected; no fix changed behaviour beyond what its finding described. Result: none.
- Correctness / security / executor-judgment / structural passes: nothing new — the candidate mode still never writes `<name>.onnx`; the pinned mode's `replace` overwrites a mismatched promoted file only after the candidate's digest matches; a `.part` left by an interrupted write is overwritten by the next run; the offline assertion still precedes the `onnxruntime` import; output stays names and numbers.
- Round classification: no findings to classify (0 🆕 / 0 ⚡ / 0 🔁). Finding verification: 0 candidates. Missed-issue pass: re-read the four round-4 hunks in context plus the full `setup-models.py` diff and the smoke's rendering / `main` tail; result: none.
- Convergence: round 5 found no CRIT, HIGH, MED or LOW; per `/review-loop`'s termination check the loop is CONVERGED at round 2 of cap 3 (rounds 4 → 5: 4 LOW → 0). The cross-family codex peer pass is owed at the COMPOSER seat (`gpt-6-astra`, per `Loop config:`), not chained from here.
- `ROLE: round` line: NOT written to `.cursor/loops/` (executor write scope); the composer's log owns it.

### Round 6 - 2026-09-06 - practitioner-profile Phase 0 (Tasks 0.1 + 0.3), independent cross-family codex peer review (first cross-family code round)

- Round status: Closed (4 of 4 Applied 2026-09-06 by the executor's `/fix` leg after the composer routed all four to fixing under `gates=fix-biased`; the composer's suite re-run and the codex confirmation round 7 are pending — the round re-opens only if the peer refutes a fix)
- Fix-delta self-check: PASS — re-read the 4 applied deltas across 3 files (`setup-models.py`: the handler class + the opener swap + the docstring rule; `speaker-embedding-smoke.py`: `_utterance_vector` / `embed` / `cosine_matrix` / `main`, the load boundary, the two docstring passages; the plan's D12 and Task 0.4; the test module's fixture, fake session and 19 new items). Nothing outside the four findings touched; the offline-before-import ordering, the candidate-never-promoted rule and the pinned-mode paths are unchanged; the 40 pre-existing test items keep their expectations (the fake opener replaces the fake `urlopen` one-for-one; the default fake output stays `(1, 4)`). Composer suites after the leg: mypy clean, pytest 1427 passed, ruff ONE E501 (a `_fake_build_opener` call line lengthened by the rename, `test_setup_scripts.py:301`) — wrapped 2026-09-06 15:13, no other line over 100 (grep-verified); ruff re-run pending.
- Source: Codex peer-review
- Baseline: `main` / HEAD `ea5775e`; the pinned working-tree diff plus the two new untracked files. Confirmed Claude-family executor/reviewer → GPT-family independent peer.
- Files reviewed: `scripts/setup-models.py` and `scripts/speaker-embedding-smoke.py` in full; `desktop/tests/test_setup_scripts.py` in full; `scripts/README.md`; both plans’ scoped changes and the requested practitioner-profile sections. Supporting reads: `speech.py`’s `SileroVad`, `benchmark.py`’s offline helpers, `speaker_eval.py`’s WAV reader, security documentation, relevant lessons, and Python 3.14’s redirect implementation.
- Validation basis: Static review only; composer-verified ruff, mypy and 1408 passing tests accepted. No tests, model downloads, file writes or directory creation performed. The front-end’s configured operations match the [upstream WeSpeaker inference recipe](https://raw.githubusercontent.com/wenet-e2e/wespeaker/master/wespeaker/bin/infer_onnx.py) and [Kaldi-compatible implementation](https://docs.pytorch.org/audio/2.6.0/_modules/torchaudio/compliance/kaldi.html) on inspection; numerical parity was not executed.
- Finding verification: 7 candidates / 3 dropped / 1 downgraded. Dropped: an incorrect default Kaldi recipe allegation; `.part` residue as an unverified-promotion route (residue is not consumed and the next write replaces it); the PowerShell placeholder-path allegation (substituting the printed concrete path works). Downgraded: the front-end detection guarantee from MED to LOW because no implemented arithmetic defect was established.

#### Confirmed / disputed (rounds 4–5)

- **LOW-001 confirmed resolved:** `scripts/setup-models.py:270` now explains deleting the existing candidate before selecting another; fetch semantics remain unchanged.
- **LOW-002 confirmed resolved:** `scripts/speaker-embedding-smoke.py:245` floors column width at six, covering signed three-decimal cells.
- **LOW-003 confirmed resolved:** Task 0.4 at `.cursor/plans/plan-practitioner-profile.md:416` now uses the menu wording in `speaker_eval.py:138`.
- **LOW-004 confirmed addressed by the planned consolidation:** `.cursor/plans/plan-practitioner-profile.md:426` explicitly retires the private implementation when Task 1.1 lands.
- **Round 4’s redirect dismissal disputed:** a digest calculated from an unpinned download identifies the received bytes; it does not authenticate their origin. This differs materially from Silero’s already-pinned download.
- **Round 5’s regression assessment confirmed:** no downstream regression found in the four applied fixes. Its clean independent-review conclusion is superseded by the findings below.

#### PR-HIGH-002 — Candidate downloads can silently lose HTTPS protection before their trust pin is established

- **Severity:** HIGH
- **Location:** `scripts/setup-models.py:185`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** Candidate mode establishes the digest that Task 0.5 will trust. A transport downgrade can substitute those initial bytes before their digest is reported, and the substituted digest can subsequently be pinned and promoted. This does not bypass an independently trusted existing pin; it compromises how this workflow establishes that pin.
- **Current behaviour:** Lines 186–190 check only the supplied URL: `if not url.startswith("https://")`, followed by `with urllib.request.urlopen(url) as resp:` and `data: bytes = resp.read()`. Python’s default redirect handler allows HTTP redirect destinations. An initially HTTPS download that redirects to HTTP therefore reaches an unauthenticated transport; a sufficiently large replacement body passes the size floor and receives a normal candidate digest. [CPython redirect implementation](https://raw.githubusercontent.com/python/cpython/3.14/Lib/urllib/request.py)
- **Desired behaviour:** Enforce HTTPS on every redirect before following it. Reject a downgrade without fetching its body or writing a candidate. Checking only the final response URL is insufficient for an intermediate downgrade followed by another redirect.
- **Pattern to follow:** Preserve the existing download → validate → write sequence, adding a redirect policy at the transport boundary. Keep ordinary HTTPS redirects supported.
- **Pattern siblings:** The same helper serves candidate and pinned speaker downloads (`scripts/setup-models.py:256`, `:283`). Silero uses default `urlopen` at `:133`, but its pre-existing trusted digest at `:136` prevents the candidate-mode trust-bootstrap failure. Search covered `https`, `urlopen`, and download call sites in both scripts and their tests.
- **Invariant:** Bytes used to establish the initial model pin must arrive through authenticated HTTPS for the entire request chain.
- **Verification:** Static path traced through download, candidate reporting and later promotion. `desktop/tests/test_setup_scripts.py:238` covers an initially HTTP URL only; the fake response bypasses redirect handling. Add transport-policy tests using stubs: HTTPS redirects accepted, downgrade refused before the downgraded request, and no candidate written.
- **Regression risk:** Overly restrictive handling could reject legitimate HTTPS hosting/CDN redirects. Preserve those and keep all tests network-free.
- **/fix decision:** Applied
- **/fix notes:** `scripts/setup-models.py` — `_HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler)` overrides `redirect_request` (which receives the ABSOLUTE target after `http_error_302` joins a relative `Location`) and raises `SystemExit` naming the non-https target BEFORE the hop is fetched; `_download_speaker_embedding` builds its opener with `build_opener(_HttpsOnlyRedirectHandler)` (which swaps out the default handler) and opens through it; the supplied-URL https check stays; silero's `urlopen` untouched; module docstring states the every-hop rule. Verified by reading (the suites are the composer's): the invariant "bytes used to establish the pin arrive over https for the whole chain" holds because every hop passes through `redirect_request`. Tests (`desktop/tests/test_setup_scripts.py`, `TestSpeakerEmbeddingRedirectPolicy`, 6 tests, socket-free): the stdlib DEFAULT handler driven through its own `http_error_302` with a fake parent opener DOES open an `http://` target (the premise proven, not assumed — the stdlib source was permission-refused to this seat); the project handler refuses the same hop with no request made; https→https and a relative `Location` still open; a chain is refused at its first non-https hop with only the https hop opened; the helper installs exactly `_HttpsOnlyRedirectHandler`; a refused download writes no candidate. The autouse network guard now also refuses `build_opener`; the fake opener records the handler classes. Sibling sites: the pinned path shares the helper (covered by construction); silero (`:133`) deliberately unchanged per the finding. No dependency added.
- **/fix date:** 2026-09-06
- **/fix applied by:** Claude Code

#### PR-MED-018 — Arbitrary model outputs are flattened into purported speaker embeddings

- **Severity:** MED
- **Location:** `scripts/speaker-embedding-smoke.py:228`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** The smoke is the evidence used to choose a candidate and threshold. A framewise or multi-vector output can be presented as a valid utterance embedding instead of being refused as an incompatible export.
- **Current behaviour:** Lines 228–229 use `output = session.run(None, {spec.name: feed})[0]` and `vector = np.asarray(output, dtype=np.float32).reshape(-1)`. Output metadata is printed at lines 197–198 but never validated. A finite, nonzero output shaped `(1, frames, dimension)` becomes one long “embedding”; equal-length recordings can produce a normal-looking cosine matrix. Different lengths fail later in `np.stack`, after per-file success output.
- **Desired behaviour:** Validate that the selected output represents exactly one utterance vector. Accept explicitly supported vector layouts, remove only their permitted singleton batch axis, and reject framewise/multiple-vector outputs with `SpeakerModelError`. Establish an unambiguous output-selection rule and consistent embedding dimension.
- **Pattern to follow:** Mirror the explicit input-rank/feature checks at `scripts/speaker-embedding-smoke.py:209` and `SileroVad`’s signature/probe validation at `desktop/src/scribe_desktop/speech.py:202`.
- **Pattern siblings:** `cosine_matrix` also flattens at `scripts/speaker-embedding-smoke.py:240`; it should consume validated vectors rather than provide another shape-coercion escape. Search covered output access, `reshape(-1)`, normalization and matrix construction.
- **Invariant:** Each matrix row represents one fixed-dimensional utterance embedding, not a flattened collection of frames or embeddings.
- **Verification:** Static trace establishes acceptance of any finite nonzero first output after flattening. `_FakeSession` always returns `(1, 4)` (`desktop/tests/test_setup_scripts.py:513`), so existing model-contract tests never exercise incompatible output layouts. Add fake-session cases for accepted layouts, framewise output, multiple vectors and inconsistent dimensions.
- **Regression risk:** Do not hard-code 256 dimensions: D-P1 also permits other candidates. Validate the layout and consistency while retaining legitimate candidate dimensions.
- **/fix decision:** Applied
- **/fix notes:** `scripts/speaker-embedding-smoke.py` — new `_utterance_vector(output, name)`: accepts `(dim,)` or `(1, dim)` (strips only the singleton batch axis), refuses any other rank / batch and `dim < 2` with `SpeakerModelError` naming the output and its shape; `embed` takes the FIRST output (rule stated in its docstring: a multi-output export must list the utterance embedding first) through it, no `reshape(-1)` anywhere; `cosine_matrix` consumes validated 1-D vectors only and refuses mixed dimensions or non-1-D input with `SpeakerModelError`; `main` wraps the matrix call into a `SystemExit`; no dimension hard-coded. Verified by reading against the invariant "each matrix row is one fixed-dimensional utterance embedding". Tests: `_FakeSession(output_shape=...)` (default `(1, 4)`; tiles its 4-vector into any layout); accepted `(4,)`, `(1, 4)`, `(1, 256)`, `(7,)` → unit-norm `(dim,)`; refused `(1, 3, 4)` framewise, `(2, 4)` multi-vector, `(1, 1, 4)`, `(1,)`, `(1, 1)`; `cosine_matrix` mixed dims and 2-D refused; `main` on a framewise fake exits naming "framewise or multi-vector" before any matrix line. Siblings: `cosine_matrix` (`:240`) swept as the finding named.
- **/fix date:** 2026-09-06
- **/fix applied by:** Claude Code

#### PR-LOW-020 — Dependency and session-setup failures escape the promised typed load boundary

- **Severity:** LOW
- **Location:** `scripts/speaker-embedding-smoke.py:179`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** A missing/broken ONNX Runtime installation produces an uncaught traceback instead of the documented `SpeakerModelError` and the CLI’s normal failure message. This matters on the practitioner’s first actual model load, which the fake-session tests bypass.
- **Current behaviour:** `import onnxruntime` at line 179, `options = onnxruntime.SessionOptions()` at line 181, and telemetry setup at line 184 precede the `try:` at line 185. Only `InferenceSession` construction is wrapped. The docstring nevertheless promises “every failure a `SpeakerModelError`” at line 170.
- **Desired behaviour:** Translate dependency import and session-setup failures into an actionable `SpeakerModelError`, while retaining the deliberate offline assertion before import and the pre-import path checks.
- **Pattern to follow:** Extend the existing constructor exception translation and the `main` handler at lines 275–278 to cover the stated model-load boundary.
- **Pattern siblings:** The stronger claim appears at `scripts/speaker-embedding-smoke.py:21`, `:170`, `scripts/README.md:18`, and `.cursor/plans/plan-practitioner-profile.md:414`. `SileroVad` also imports outside its constructor catch, so copying its arrangement does not establish the smoke’s broader promise. Search covered `SpeakerModelError`, `SessionOptions`, and typed-load wording.
- **Verification:** With a present local model and ONNX Runtime unavailable or failing to import its DLL, the failure occurs before line 185. Existing import-blocking tests use missing/UNC paths and exit before reaching this boundary. Add a present-file import-failure case and a stubbed session-options failure case.
- **Regression risk:** Preserve `OfflineEnvError` as the explicit precondition failure; do not accidentally move import ahead of the offline/path checks.
- **/fix decision:** Applied
- **/fix notes:** `scripts/speaker-embedding-smoke.py` `load_session` — `assert_offline_env`, the UNC check and `is_file` stay BEFORE the import exactly as before; the import is now inside its own `try` (any exception → `SpeakerModelError` "onnxruntime is not importable (...); it is part of the desktop [ml] extra: <pip command>"), and session options, the telemetry opt-out and session construction share one typed boundary whose message names the failing step; the load-contract docstring and the module docstring item 1 now state exactly this (`OfflineEnvError` named as the one precondition failure outside the boundary); `scripts/README.md:18` "load failures typed" and this plan's Task 0.3 record are true as written. Verified by reading. Tests: a PRESENT file with `sys.modules["onnxruntime"] = None` → `SpeakerModelError` matching "not importable … [ml]"; a `SimpleNamespace` stub whose `SessionOptions` raises → `SpeakerModelError` "(session options)" carrying the cause; the pre-existing missing/UNC-before-import test unchanged and still ordered correctly. Siblings: `SileroVad` (`speech.py:184`) deliberately NOT changed — it never made the broader promise and is outside Task 0.3.
- **/fix date:** 2026-09-06
- **/fix applied by:** Claude Code

#### PR-LOW-021 — The smoke overstates its ability to detect a wrong front-end

- **Severity:** LOW
- **Location:** `scripts/speaker-embedding-smoke.py:28`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** A useful same-versus-other cosine gap does not establish preprocessing compatibility. Presenting it as that proof can cause the practitioner to overlook a model-card mismatch when recording D-P1 evidence.
- **Current behaviour:** Lines 28–30 state: “A wrong front-end shows up here as near-random similarities”. The structural checks only reject certain input shapes; other preprocessing differences still produce valid features and embeddings. In particular, away from the log floor, uniform amplitude scaling adds a constant to log energies that per-utterance CMN removes (`scripts/speaker-embedding-smoke.py:155`–`:160`), illustrating why a preprocessing difference need not produce random similarities.
- **Desired behaviour:** Describe the cosine smoke as a separation/sanity check that may expose incompatibility, not a guarantee of detecting it. State that the selected export’s preprocessing recipe must be checked independently and recorded alongside the smoke result.
- **Pattern to follow:** D12’s existing “verified against the model card” requirement and the Critical Constraint at `.cursor/plans/plan-practitioner-profile.md:275` that claims match enforcing structure.
- **Pattern siblings:** The same unconditional claim appears in D12 at `.cursor/plans/plan-practitioner-profile.md:247`. Task 0.4 at `:416` should point to checking the complete preprocessing recipe, beyond its current explicit bin-count check. Search covered `near.random` and `wrong front.end`; historical review prose should remain historical.
- **Verification:** Static review found no implemented fbank arithmetic defect. Existing tests establish shape, determinism, CMN and filter geometry, not universal detection of an incompatible front-end. Re-read the revised wording and ensure it distinguishes model-card compatibility from observed separation.
- **Regression risk:** Documentation-only clarification; preserve the practitioner-owned D-P1 decision and current numerical implementation.
- **/fix decision:** Applied
- **/fix notes:** Three rewordings, no numerical change: the smoke's module docstring (the "near-random similarities" sentence removed; a new "What the matrix does and does not prove" paragraph — a separation / sanity check that can expose but not prove; the CMN-cancels-scale example; bin count the one outright refusal; check the export's preprocessing recipe against the model card independently and record it on Task 0.4 beside the matrix); D12 in this plan (same claim replaced with the same wording, tagged round 6 PR-LOW-021); the Task 0.4 sub-bullet (the practitioner also pastes the model card's window, frame geometry, bin count, sample scale and mean-normalisation beside the matrix; a different window or scale is a D-P1 fact). Historical round prose (rounds 4–5, the peer's round-6 text) untouched. Verified by re-reading all three.
- **/fix date:** 2026-09-06
- **/fix applied by:** Claude Code

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-06)
- PR-HIGH-002: materiality=behavioral; verified severity=med; peer severity=high (preserved); evidence: `scripts/setup-models.py:186-190` checks `url.startswith("https://")` on the SUPPLIED URL only, then calls `urllib.request.urlopen(url)` with the default opener, whose `HTTPRedirectHandler.http_error_302` refuses only schemes outside `http`/`https`/`ftp` (CPython's "For security reasons we don't allow redirection to anything other than http, https or ftp" — the stdlib file `C:\Python314\Lib\urllib\request.py` was permission-refused to this seat, so the behaviour rests on the peer's cited 3.14 source plus this executor's knowledge of it and MUST be proven by the fix leg's stubbed-opener test); an https→http hop is therefore followed and the received bytes are what `_report_candidate` digests, so round 4's "closed by the reported digest in candidate mode" was WRONG on the bootstrap point — a digest identifies the bytes received, it does not authenticate their origin; the peer is right and the finding is CONFIRMED. Downgrade HIGH → MED, evidence: exploitation needs BOTH an on-path attacker on the practitioner's network AND a redirect to plain http issued by the authenticated origin the practitioner named (or by an already-plain hop) — the realistic candidate hosts (Hugging Face `resolve` → CDN, GitHub releases) redirect https→https; the artefact is an ONNX graph, not code, loaded only under the asserted-offline runtime (a tampered model degrades or biases speaker attribution — a clinical-quality harm the practitioner reviews at signing — it cannot exfiltrate); and the pinned path (Task 0.5 onward) stays bytes-exact. The INVARIANT the peer states is nonetheless the project's own ("the one network flow is pinned https", `data-flow-map.md` flow 9; Critical Constraint "the model is fetched only by `scripts/setup-models.py`"), and the fix is a custom `HTTPRedirectHandler` that refuses a non-https `Location` BEFORE the hop is fetched, installed through `build_opener` for this helper only — no new dependency, no behaviour change for silero; scope: yes (the transport policy of the helper Task 0.3 added — `_download_speaker_embedding` serves both the candidate and the pinned path, `:256`/`:283`); production-impacting: no; recommendation: Fix-now — a few lines at the transport boundary plus three network-free tests (an https→https redirect accepted, an https→http redirect refused before the downgraded request with no candidate written, a multi-hop chain refused at the first non-https hop); the round-4 dismissal is corrected in this block, not silently.
- PR-MED-018: materiality=behavioral; verified severity=med; peer severity=med (preserved); evidence: `scripts/speaker-embedding-smoke.py:228-229` takes output `[0]` and `reshape(-1)`s ANY finite non-zero array — a framewise `(1, frames, dim)` output becomes one long vector, files of equal length then yield a plausible cosine matrix (the D-P1 evidence), files of unequal length crash inside `np.stack` at `:240` AFTER each file's "-> embedding dim N" success line; the input side already validates rank and feature dim (`:216-224`) while the output side validates nothing, and `_FakeSession.run` (`desktop/tests/test_setup_scripts.py:503-513`) always returns `(1, 4)`, so no test exercises an incompatible layout — CONFIRMED as described, no downgrade (the smoke's whole purpose is trustworthy evidence for a `[decision]`); scope: yes (the smoke's own output contract, Task 0.3); production-impacting: no; recommendation: Fix-now — accept exactly `(dim,)` or `(1, dim)` (strip the singleton batch axis only), refuse rank ≥ 3, a batch ≠ 1 and `dim < 2` with `SpeakerModelError`, select the FIRST output by an explicit rule stated in the docstring, make `cosine_matrix` consume validated 1-D vectors (no `reshape(-1)`) and refuse mixed dimensions, never hard-code 256; fake-session tests for `(dim,)`, `(1, dim)`, `(1, frames, dim)` refused, `(2, dim)` refused, mixed dims refused.
- PR-LOW-020: materiality=behavioral (plus the docs overclaim); verified severity=low; peer severity=low (preserved); evidence: `scripts/speaker-embedding-smoke.py:179` `import onnxruntime`, `:181` `SessionOptions()`, `:184` `disable_telemetry_events()` all sit BEFORE the `try:` at `:185`, so a missing or DLL-broken onnxruntime raises a raw `ImportError`/`AttributeError` traceback instead of the `SpeakerModelError` the docstring promises at `:170` ("every failure a `SpeakerModelError`") and `:21`, `scripts/README.md:18` ("load failures typed") and this plan's Task 0.3 record ("`SpeakerModelError` on every load failure"); `SileroVad` (`speech.py:184-201`) has the same import-outside-try arrangement but never promised more than a typed `InferenceSession` failure — the smoke's docstring did; CONFIRMED at LOW (the practitioner still sees a traceback naming onnxruntime; no wrong result, no silent path); scope: yes; production-impacting: no; recommendation: Fix-now — wrap the import, `SessionOptions`, telemetry call and session construction in ONE typed boundary (`except Exception` → `SpeakerModelError` naming the step and the `[ml]` extra remedy), keeping `assert_offline_env` and the UNC/is_file checks BEFORE the import exactly as now (the import-blocking test must still pass); add a present-file test with `sys.modules["onnxruntime"] = None` expecting `SpeakerModelError` and a stubbed module whose `SessionOptions` raises; make the three docstring/README/plan claims true by the fix rather than weakening them.
- PR-LOW-021: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: `scripts/speaker-embedding-smoke.py:28-30` "A wrong front-end shows up here as near-random similarities" and D12 (`plan-practitioner-profile.md:247`) "a wrong front-end fails the D-P1 smoke visibly (near-random similarities)" are unconditional; the peer's counter-example holds — a uniform amplitude-scale mismatch adds a constant to every log-mel value away from the eps floor and per-utterance CMN (`:159-160`) removes it exactly, so that class of front-end difference leaves the cosine matrix untouched; likewise a Povey-vs-Hamming or 25-vs-32 ms mismatch degrades rather than randomises; the smoke's structural check catches only a wrong feature COUNT (`:220`); the Task 0.4 sub-bullet asks the practitioner about the bin count only; CONFIRMED docs-only at LOW; scope: yes (the smoke's docstring, D12's wording, the Task 0.4 instruction — record-level); production-impacting: no; recommendation: Fix-now — reword all three to "a separation / sanity check that can expose an incompatible export but does not prove preprocessing compatibility; the export's preprocessing recipe (window, frame geometry, bin count, scale, CMN) is checked against the model card independently and recorded on Task 0.4 beside the matrix", keeping the historical round prose untouched.

PEER-ROUND-6 RESULT: 4 findings (CRIT 0 / HIGH 1 / MED 1 / LOW 2).

### Round 7 - 2026-09-06 - practitioner-profile Phase 0 (Tasks 0.1 + 0.3), independent cross-family codex peer review (confirmation round after round 6)

- Round status: Closed — No new findings — converged
- Source: Codex peer-review
- Baseline: `main` / HEAD `ea5775e38b3dc8bff66ad41bfcad9c559b21f221`; scoped working-tree changes and the two new untracked files. Claude-family fix executor → independent GPT-family confirmation peer.
- Files reviewed: `scripts/setup-models.py`, `scripts/speaker-embedding-smoke.py` and `desktop/tests/test_setup_scripts.py` in full; `scripts/README.md`; both plans’ scoped changes; practitioner-profile round 6 including all fix notes and LEG 1 tuples, D11/D12, Tasks 0.3–0.6/D-P1 and Task 1.1’s consolidation instruction. Supporting reads: `speech.py`’s `SileroVad`, `benchmark.py`’s offline helpers, `speaker_eval.py`’s WAV reader and conversion recipe, relevant security documentation and lessons, and local CPython 3.14’s `urllib/request.py`.
- Validation basis: Static review only. Accepted composer verification: ruff clean, mypy clean over 30 files, pytest 1427 passed, including 59 setup-script tests. No tests, downloads, file writes or directory creation performed.
- Finding verification: 3 candidates / 3 dropped / 0 downgraded. Dropped: redirect-family bypass, because all five status handlers share the checked stdlib path; `.part` residue as an unverified-promotion route, because residue is never consumed and promotion follows digest verification; non-finite inputs reaching the matrix through the CLI, because its vectors come exclusively from the validating `embed` path.

#### Confirmed / disputed (round 6 fixes)

- **PR-HIGH-002 — confirmed complete:** `scripts/setup-models.py:203` rejects destinations failing `startswith("https://")` before delegating; `:218` installs `build_opener(_HttpsOnlyRedirectHandler)`. Local `C:/Python314/Lib/urllib/request.py:692` resolves relative destinations, `:697` calls `self.redirect_request(...)` before `:718` opens the next request, and `:720` aliases 301/303/307/308 to that same implementation. Both speaker download paths use the helper (`scripts/setup-models.py:286`, `:313`); Silero’s `urlopen` remains unchanged at `:137`. Tests call the real stdlib `http_error_302` at `desktop/tests/test_setup_scripts.py:335`, establishing default downgrade behavior, refusal and ordinary/relative HTTPS acceptance. The chain test at `:369` simulates successive hops; recursive enforcement is additionally established by the inspected stdlib call path.
- **PR-MED-018 — confirmed complete:** `scripts/speaker-embedding-smoke.py:235` strips only a singleton batch axis; `:237` refuses remaining non-vector ranks and `:243` refuses dimensions below two. The first-output rule is explicit at `:252` and implemented by `session.run(...)[0]` at `:281`. The finite, nonzero norm check remains at `:284`; `cosine_matrix` rejects mixed dimensions and non-1-D arrays at `:297`. No production dimension is hard-coded. Accepted layouts and alternative dimensions are covered at `desktop/tests/test_setup_scripts.py:704`; incompatible layouts and mixed dimensions at `:714` and `:732`.
- **PR-LOW-020 — confirmed complete:** `scripts/speaker-embedding-smoke.py:185` retains offline assertion, UNC rejection and file checks before import. Both exception-translation blocks (`:193`, `:201`) provide continuous typed coverage from import through session construction, with step-specific messages. The import-blocking test remains meaningful: its expected `"setup-models"` and `"UNC"` messages at `desktop/tests/test_setup_scripts.py:655` and `:657` cannot be satisfied by the new import-error message. Present-file import failure and session-options failure are covered at `:660` and `:672`.
- **PR-LOW-021 — confirmed complete:** `scripts/speaker-embedding-smoke.py:40` states “It does NOT prove the front-end matches the model card”; `.cursor/plans/plan-practitioner-profile.md:247` makes the same distinction. Task 0.4 at `:518` explicitly requests window, frame geometry, bin count, sample scale and mean-normalisation evidence alongside the signature and matrix.

The broader pass found no additional actionable defect. Candidate reuse visibly instructs deletion before changing candidates (`scripts/setup-models.py:300`); fresh downloads pass the size floor before writing, and pinned candidate/download paths verify before replacement (`:270`, `:288`). The WAV reader checks format and complete frame counts (`desktop/src/scribe_desktop/speaker_eval.py:266`, `:278`), and the front-end consumes bounded PCM16 samples. The round-4 correction at `.cursor/plans/plan-practitioner-profile.md:500` correctly distinguishes a reported digest from authenticated origin. Task 0.4’s PowerShell commands are usable after substituting the requested URL and printed concrete candidate path; Task 1.1 at `:528` explicitly retires the smoke’s private implementation.

PEER-ROUND-7 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 8 - 2026-09-15 - practitioner-profile Phase 0 Task 0.5 (the model pin), in-session `/review-loop` round 1 of cap 3
- Round status: Closed (5 of 5 Applied 2026-09-15 by Claude Code, one at a time, each verified by re-read; the two code-file fixes await the composer's suite re-run before round 9)
- Fix-delta self-check: PASS — re-read 5 applied hunks across 5 files (the constants comment and the derived size string in `setup-models.py`; the removed fixture parameter in the test module; the flow-8 sentence in `data-flow-map.md`; the smoke entry in `scripts/README.md`); no behaviour changed, no neighbouring exit path touched, the shipped-pin tests' expectations hold (`str(size) in EXPECTED_SIZE` is true of the derived string).
- Source: Claude Code
- Primary review baseline: the working tree against `main` `281ae64` (round 1 for Task 0.5; the plan's previous sync predates every change). Changed files, all read in full, nothing skipped: `scripts/setup-models.py`, `desktop/tests/test_setup_scripts.py`, `AGENTS.md` (step 3), `docs/security/data-flow-map.md` (flows 8–9), this plan. Suites at review time: composer-run GREEN (ruff, mypy 30 files, pytest 1431).
- Looks good: the pin constants match the Task 0.4 record byte for byte (URL, 26530309, the 64-hex digest); the pinned path was already built and tested at Task 0.3 and is now exercised against the SHIPPED values with nothing monkeypatched (the pin test refuses a wrong digest naming both digests and leaves the candidate; the CLI refuses `--candidate-url`; a wrong-bytes download writes nothing and asked for exactly the shipped URL); the module docstring states the pinned behaviour first and candidate mode as the generic empty-pin route; the `--candidate-url` usage line is gone; AGENTS.md step 3 and flow 9 say what the code does; every test stays network-free.
- Finding verification: 6 candidates; 1 dropped (an "unused" `SPEAKER_EMBEDDING_SIZE_BYTES` — it is the recorded registry fact the task asked for and the shipped-pin test reads it; only its duplication with the human string is a defect, LOW-001); 0 downgraded.
- Executor judgment: LOW-001, LOW-002 (a claim in a code comment the repo never verified). Structural quality: none. Post-fix regression check: round 1 — no prior fixes on this task; regression baseline = the working tree; none.
- Missed-issue pass: re-read the five changed files plus `scripts/README.md` (a doc that describes the same entry and was NOT in the diff); result: LOW-004, LOW-005.
- `ROLE: round` line: NOT written to `.cursor/loops/` (executor write scope).
- **[LOW]** LOW-001: `scripts/setup-models.py` constants — `SPEAKER_EMBEDDING_SIZE_BYTES` and `SPEAKER_EMBEDDING_EXPECTED_SIZE` both spell the number 26530309; a future re-pin can change one and not the other. Desired: the string derives from the int. — Triage: Fix-now; Decision: Applied (the string is now an f-string over the int; the "25.3 MiB" label and date stay literal; `test_constants_are_a_real_pin` still holds)
- **[LOW]** LOW-002: `scripts/setup-models.py` constants comment — "MIT-licensed" restated the plan's External / API Finding, which the plan itself marks "not verified online during planning"; the practitioner's model-card read at Task 0.4 recorded the front-end and architecture, not the licence. A code comment must not assert what nothing in the repo verified. Desired: drop the claim from the comment (the plan keeps it with its caveat). — Triage: Fix-now; Decision: Applied (comment now reads "80-bin Kaldi fbank in, 256-dim embedding out"; licence verification stays a commercialisation-time fact outside this plan)
- **[LOW]** LOW-003: `desktop/tests/test_setup_scripts.py` `test_candidate_url_is_refused_through_the_cli` requested the `capsys` fixture and never read it. — Triage: Fix-now; Decision: Applied (parameter removed; siblings: none — every other `capsys` in the module is read)
- **[LOW]** LOW-004 (missed-issue pass): `docs/security/data-flow-map.md` flow 8 said "until its promotion … the same bytes sit beside it as `.onnx.candidate`", implying both files coexist; before Task 0.6 only the `.candidate` exists and promotion is one rename. — Triage: Fix-now; Decision: Applied (reworded: "until that plan's Task 0.6 promotes it, the file exists only as `.onnx.candidate` — promotion is one rename")
- **[LOW]** LOW-005 (missed-issue pass): `scripts/README.md` smoke entry still said `setup-models.py --only speaker-embedding` "leaves [the candidate] in candidate mode" — false since the pin: that command now verifies and promotes. — Triage: Fix-now; Decision: Applied (the entry now says the explicit path reads the promoted `.onnx` or a `.candidate` left by an UNPINNED fetch, and that the entry is pinned since Task 0.5)

### Round 9 - 2026-09-15 - practitioner-profile Phase 0 Task 0.5 (the model pin), in-session `/review-loop` round 2 of cap 3 (confirmation)
- Round status: Closed (1 of 1 Applied 2026-09-15 by Claude Code, doc-only) — LOOP CONVERGED at this round
- Fix-delta self-check: PASS — re-read the one applied hunk (the flow-8 paragraph re-wrapped; words unchanged).
- Source: Claude Code
- Primary review baseline: unchanged from round 8 — the working tree against `main` `281ae64`; the same six changed files (`git status` identical: `scripts/setup-models.py`, `scripts/README.md`, `desktop/tests/test_setup_scripts.py`, `AGENTS.md`, `docs/security/data-flow-map.md`, this plan), every one re-read in full from disk. Suites after the round-8 fixes: composer-run GREEN (ruff clean, mypy 30 files, pytest 1431 passed).
- Post-fix regression check (regression baseline = the pre-`/fix` working tree of round 8): five hunks — the derived size string (an f-string over the int; `test_constants_are_a_real_pin` passed), the constants comment (words only), the removed `capsys` parameter (the test passed), the flow-8 sentence and the README entry (prose). No signature, return value or data shape changed; no caller affected. Result: none.
- Correctness / security / executor-judgment / structural passes: nothing new — the pin constants still match the Task 0.4 record; the pinned path, the redirect policy and the candidate machinery are untouched since round 7; the docs say what the code does.
- Round classification: 1 🆕 / 0 ⚡ / 0 🔁. Finding verification: 1 candidate; 0 dropped; 0 downgraded. Missed-issue pass: re-read all six changed files with fresh eyes; result: LOW-001.
- Convergence: no CRIT, HIGH or MED; the single 🆕 LOW is applied; per `/review-loop`'s termination check the loop is CONVERGED at round 2 of cap 3 (rounds 8 → 9: 5 LOW → 1 LOW doc-only → applied). The cross-family codex peer pass over the Task 0.5 diff is owed at the COMPOSER seat.
- `ROLE: round` line: NOT written to `.cursor/loops/` (executor write scope).
- **[LOW]** LOW-001: `docs/security/data-flow-map.md` flow 8 — the round-8 rewording left the hard-wrapped paragraph ragged ("… no / clinical content. Written / ONLY by flow 9 …"); rendered output is unaffected, the source is untidy where every neighbouring paragraph is evenly wrapped. — Triage: Fix-now; Decision: Applied (paragraph re-wrapped, no words changed; doc-only, no suite needed)

### Round 10 - 2026-09-15 - practitioner-profile Phase 0 Task 0.5 (pin the model), independent cross-family codex peer review

- Round status: Closed (3 of 3 Applied 2026-09-15 by the executor's `/fix` leg after the composer routed all three to fixing under `gates=fix-biased`; the composer's suite re-run and the codex confirmation round 11 are pending — the round re-opens only if the peer refutes a fix)
- Fix-delta self-check: PASS — re-read the 4 applied hunks across 4 files (flow 9 in `data-flow-map.md`; the `setup-models.py` module docstring; the smoke's module docstring and missing-file remedy; Task 0.6 in this plan). Words only; no control flow, signature or CLI contract touched; the "scripts/setup-models.py" substring the two tests match is preserved.
- Source: Codex peer-review
- Baseline: Working tree against `main` at HEAD `281ae64`; Task 0.5 uncommitted. Independent GPT-family review following Claude-family rounds 8–9.
- Files reviewed: `scripts/setup-models.py` in full; changed regions of `scripts/README.md`, `desktop/tests/test_setup_scripts.py`, `AGENTS.md`, and `docs/security/data-flow-map.md`; the specified Task 0.4 report, Task 0.5 record, Task 0.6, D-P1, and rounds 8–9 in `.cursor/plans/plan-practitioner-profile.md`. Supporting read: `scripts/speaker-embedding-smoke.py`, including its explicit-path consumer and user instructions.
- Validation basis: Read-only inspection and diff review. Accepted composer verification: ruff clean, mypy clean over 30 source files, pytest 1431 passed, including 63 setup-script tests. No tests, downloads, application execution, or file writes performed.
- Finding verification: 5 candidates / 2 dropped / 0 downgraded. Dropped: requiring duplicate literal URL/digest assertions where the requested shipped-pin refusal test already exists; treating flow 8’s recorded pre-promotion state as an assertion about every future installation.

#### Confirmed / disputed (rounds 8–9)

- Round 8 LOW-001 — Confirmed applied: `scripts/setup-models.py:94` now derives the size text with `f"{SPEAKER_EMBEDDING_SIZE_BYTES} bytes …"`.
- Round 8 LOW-002 — Confirmed applied: `scripts/setup-models.py:79` describes “80-bin Kaldi fbank in” without the unverified licence claim.
- Round 8 LOW-003 — Confirmed applied: `desktop/tests/test_setup_scripts.py:264` declares the CLI refusal test without `capsys`; its refusal and filesystem assertions remain.
- Round 8 LOW-004 — Confirmed for the recorded Task 0.4 state: `docs/security/data-flow-map.md:108` says “the file exists only as `.onnx.candidate`”; `scripts/setup-models.py:285` performs `candidate.replace(target)`.
- Round 8 LOW-005 — Confirmed applied in the README: `scripts/README.md:20` says “the entry is pinned since Task 0.5”. A downstream sibling remains in the smoke script; see PR-REG-001.
- Round 9 LOW-001 — Confirmed applied: the flow-8 paragraph at `docs/security/data-flow-map.md:107` is rewrapped as recorded; no runtime behaviour changed.
- Rounds 8–9’s broader conclusion that the documentation fully matches enforcement is disputed in the limited respects below. Their recorded suite results are accepted.

#### Pin, paths, and tests verified

- Ordinal string comparisons against `.cursor/plans/plan-practitioner-profile.md:455` confirm the URL, size `26530309`, and SHA-256 `7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068` match exactly (`scripts/setup-models.py:88`, `:92`, `:96`).
- The nonempty pin selects pinned mode. Candidate mismatch raises with both digests before `candidate.replace(target)`; fresh-download mismatch raises before `_write_atomically(target, data)` (`scripts/setup-models.py:264`, `:277`, `:295`). No unchecked setup write or promotion path was found.
- The pinned download calls `_download_speaker_embedding`, which installs `_HttpsOnlyRedirectHandler`; pinning has not bypassed the speaker model’s redirect checks (`scripts/setup-models.py:227`, `:295`).
- A standard run includes the speaker model through `if speaker_embedding_pinned(): fetch_speaker_embedding(root)` (`scripts/setup-models.py:369`). This intentionally adds the 25.3 MiB model to setup, promoting the existing candidate where present.
- The shipped-pin tests leave the pin constants unchanged and check wrong-digest refusal, both reported digests, candidate preservation, CLI override refusal, and no write after a wrong download (`desktop/tests/test_setup_scripts.py:235`). The default-run test also uses the shipped pin (`:188`). Candidate-mode assertions were retained; the existing empty-pin fixtures remain (`:292`). Network refusal guards and fake openers remain (`:71`, `:80`).

#### PR-LOW-022 — HTTPS redirect documentation exceeds the installed guard’s scope

- **Severity:** LOW
- **Location:** `docs/security/data-flow-map.md:125`
- **Triage:** Fix-now
- **Fix route:** fix-on-fast
- **Why it matters:** The security map attributes the speaker-specific transport guarantee to all setup downloads.
- **Current behaviour:** Flow 9 says, “Every download, and every redirect hop of it, must be https: a redirect to http is refused before it is fetched.” `scripts/setup-models.py:30` similarly says, “Every download here must be https and so must EVERY redirect hop”. However, silero uses `urllib.request.urlopen(SILERO_VAD_URL)` at `scripts/setup-models.py:146`. The custom handler’s own documentation explicitly says “Installed for the speaker-embedding helper only; silero’s already-pinned fetch is untouched” (`:206`).
- **Desired behaviour:** Scope both statements explicitly to speaker-embedding downloads, in candidate and pinned modes. Preserve the separate digest-verification claims.
- **Pattern to follow:** The accurate scope statement at `scripts/setup-models.py:206`.
- **Pattern siblings:** `scripts/setup-models.py:30`. Searches for `Every download`, HTTPS wording, and every-hop/redirect claims across the scoped script and documentation found these two overbroad current statements.
- **Invariant:** Documented transport guarantees must match the downloader that enforces them.
- **Verification:** Static repro: if the silero endpoint supplies a downgrade redirect, its ordinary urllib path does not install the speaker guard. The existing socket-free test at `desktop/tests/test_setup_scripts.py:400` documents the default handler’s downgrade-following behaviour. No payload or network request was run.
- **Regression risk:** Minimal for a prose-only scope correction; extending the guard to other downloaders would be a separate behavioural change.
- **/fix decision:** Applied
- **/fix notes:** `docs/security/data-flow-map.md` flow 9 — the sentence now reads "The speaker-embedding download — candidate and pinned alike — must be https on every redirect hop … (the guard is installed for that helper only; silero-vad and the whisper snapshots rely on their pre-existing pins, not on a redirect guard)"; `scripts/setup-models.py` module docstring — the same scoping, naming silero's default opener and its SHA-256 pin and whisper's commit SHAs. The digest claims are untouched. Verified by re-reading both and by grep: no "Every download" claim remains anywhere in the scoped files. Siblings: both sites the finding named; none else found. No code changed.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### PR-REG-001 — Smoke guidance still promises a candidate file after pinned setup

- **Severity:** LOW
- **Location:** `scripts/speaker-embedding-smoke.py:190`
- **Triage:** Fix-now
- **Fix route:** fix-on-fast
- **Why it matters:** After Task 0.6 removes the candidate by promotion, the smoke’s instructions and missing-file remedy direct the practitioner back to a filename setup no longer produces.
- **Current behaviour:** The missing-model error says, “`--only speaker-embedding (the candidate lands as <name>.onnx.candidate)`” (`scripts/speaker-embedding-smoke.py:191`). Its module instructions likewise say setup “has left the candidate file in the cache” (`:7`) and show a `.onnx.candidate` model argument (`:11`).
- **Desired behaviour:** Explain that the shipped pinned entry produces `<name>.onnx`, and use that path in the current example and remedy. Retain explicit support for an unpromoted candidate when evaluating an unpinned model.
- **Pattern to follow:** The corrected distinction in `scripts/README.md:18`.
- **Pattern siblings:** `scripts/speaker-embedding-smoke.py:7` and `:11`. Searching its setup references and candidate/promotion wording found these instruction sites plus the missing-file message; the dual-path CLI help at `:323` remains accurate.
- **Invariant:** A recovery instruction must identify the artifact its recommended setup operation actually produces.
- **Verification:** Static repro: Task 0.6 executes `candidate.replace(target)` (`scripts/setup-models.py:285`); using the smoke’s candidate-path example then fails `model_path.is_file()` (`scripts/speaker-embedding-smoke.py:188`). Repeating pinned setup skips the verified target (`scripts/setup-models.py:270`) and does not recreate the candidate.
- **Regression risk:** Low; update prose and the error message while preserving explicit-path loading and candidate compatibility.
- **/fix decision:** Applied
- **/fix notes:** `scripts/speaker-embedding-smoke.py` — module docstring: the shipped entry is pinned, `setup-models.py --only speaker-embedding` leaves the verified, promoted model, and the example now passes `…\speaker-embedding\wespeaker-voxceleb-resnet34-LM.onnx`; the explicit `--model` path is explained as the way an UNPINNED candidate's `.onnx.candidate` is read (Task 0.4 ran that way); the missing-file remedy now says "the pinned entry is written or promoted as <name>.onnx; an unpinned candidate fetch leaves <name>.onnx.candidate" and still contains "scripts/setup-models.py", the substring the two existing tests match. No control flow, signature or CLI option changed (the `--model` help already named both paths). Verified by re-reading; the composer's suites confirm the two message-matching tests. Siblings: `:7` and `:11` (the finding's) and `:190-191`, all covered.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### PR-LOW-023 — Task 0.6’s command is not runnable verbatim from project-root PowerShell

- **Severity:** LOW
- **Location:** `.cursor/plans/plan-practitioner-profile.md:466`
- **Triage:** Fix-now
- **Fix route:** fix-on-fast
- **Why it matters:** The next practitioner-owned task requires translating shorthand into a working command.
- **Current behaviour:** Task 0.6 instructs the practitioner to “re-run `setup-models.py --only speaker-embedding`”. The file resides under `scripts/`; that bare command neither selects the project’s virtual-environment interpreter nor supplies the script path.
- **Desired behaviour:** State “from the project folder in a normal PowerShell” and give `.venv\Scripts\python.exe scripts\setup-models.py --only speaker-embedding`.
- **Pattern to follow:** The interpreter-qualified setup invocation in `AGENTS.md:34`.
- **Pattern siblings:** None within Task 0.6’s instruction. Filename shorthand in descriptive inventories is not treated as a runnable command.
- **Verification:** Read-only file discovery locates `scripts\setup-models.py`; the script’s usage at `scripts/setup-models.py:35` supplies the interpreter and relative path. The promotion branch prints the requested target filename and verified digest (`:286`).
- **Regression risk:** None to runtime behaviour; instruction-only correction.
- **/fix decision:** Applied
- **/fix notes:** Task 0.6 now reads "from the project folder in a normal PowerShell run `.venv\Scripts\python.exe scripts\setup-models.py --only speaker-embedding`" and names the promoted file `wespeaker-voxceleb-resnet34-LM.onnx`; the rest of the task text (what to confirm, the Task 3.2 note, Blocks) is unchanged. Verified by re-reading. Siblings: none (the Current State bullet already carried the full command).
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-15)
- PR-LOW-022: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: `docs/security/data-flow-map.md:125-127` says "Every download, and every redirect hop of it, must be https" and `scripts/setup-models.py:30` "Every download here must be https and so must EVERY redirect hop", while silero fetches through the default opener at `scripts/setup-models.py:146` (`urllib.request.urlopen(SILERO_VAD_URL)`) and only `_download_speaker_embedding` builds its opener with `_HttpsOnlyRedirectHandler` (`:227`), whose own docstring says "Installed for the speaker-embedding helper only" — both prose claims are broader than the enforcing code; CONFIRMED docs-only at LOW (silero's digest pin makes its transport immaterial, so no security gap — an overclaim, the project's recurring class); scope: yes (the flow-9 sentence is Task 0.5's own edit; the docstring sentence is the same claim from Task 0.3, a pattern sibling); production-impacting: no; recommendation: Fix-now — scope both sentences to the speaker-embedding downloads (candidate and pinned) and keep the separate digest claims; no code change.
- PR-REG-001: materiality=docs-only (a message string and docstring text; no control-flow change); verified severity=low; peer severity=low (preserved); evidence: `scripts/speaker-embedding-smoke.py:7-8` ("has left the candidate file in the cache"), `:11` (the `.onnx.candidate` example path) and the missing-file remedy at `:190-191` ("the candidate lands as <name>.onnx.candidate") all describe the unpinned route; under the shipped pin `setup-models.py --only speaker-embedding` promotes by `candidate.replace(target)` (`scripts/setup-models.py:285`) and a re-run skips the verified `<name>.onnx` (`:270`), so after Task 0.6 the example path fails `is_file()` (`:188`) and the remedy names a file setup no longer produces; the `--model` help at `:323` already states both paths; CONFIRMED at LOW; the fix is wording plus the promoted path as the primary example, with the candidate path kept as the explicit second case (an unpinned candidate — D-P1's second option — must still be readable; `_utterance_vector`, `load_session` and the CLI contract are untouched; the two tests matching "setup-models" in the remedy keep that substring); scope: yes (the smoke is Task 0.3's file, but the claim is made stale by Task 0.5's pin — the same sibling class the round-8 README fix closed); production-impacting: no; recommendation: Fix-now — docstring lines 3-15 and the remedy at `:189-192`; a code file changes, so the composer re-runs the suites after the fix leg.
- PR-LOW-023: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: Task 0.6 at `.cursor/plans/plan-practitioner-profile.md:543` says "re-run `setup-models.py --only speaker-embedding`" with no interpreter or `scripts\` path, whereas `AGENTS.md` step 3 and this plan's own Task 0.4 sub-bullet spell `.venv\Scripts\python.exe scripts\setup-models.py …`; the practitioner-facing instruction for the next practitioner-owned task is not runnable as written (the Current State bullet already carries the full command, but the task is what the practitioner reads); CONFIRMED docs-only at LOW; scope: yes (the instruction for the task Task 0.5 unlocks; the round-8 class); production-impacting: no; recommendation: Fix-now — write the verbatim PowerShell command on Task 0.6 ("from the project folder in a normal PowerShell"), keeping the rest of the task text.

PEER-ROUND-10 RESULT: 3 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 3).

### Round 11 - 2026-09-15 - practitioner-profile Phase 0 Task 0.5 (pin the model), independent cross-family codex peer review (confirmation round after round 10)

- Round status: Closed — No new findings — converged
- Source: Codex peer-review
- Baseline: Working tree against `main` at HEAD `281ae64`; Task 0.5 uncommitted. Independent GPT-family confirmation following the Claude-family executor’s round-10 fixes.
- Files reviewed: `scripts/setup-models.py` and `scripts/speaker-embedding-smoke.py` in full; `scripts/README.md`; scoped changes and relevant assertions in `desktop/tests/test_setup_scripts.py`; `AGENTS.md` step 3; `docs/security/data-flow-map.md` flows 8–9; `.cursor/plans/plan-practitioner-profile.md` round 10 in full, including LEG 1 verified tuples and all `/fix` fields, plus Phase 0 tasks, Task 0.4’s pin record, Task 0.5, Task 0.6 and D-P1.
- Validation basis: Read-only source inspection, diff review, pattern searches and ordinal comparisons of recorded pin values. Accepted composer verification: ruff clean; mypy clean over 30 source files; pytest 1431 passed, zero network. No tests, downloads, application execution or file writes performed.
- Finding verification: 0 candidates / 0 dropped / 0 downgraded

#### Confirmed / disputed (round 10 fixes)

- **PR-LOW-022 — Fix confirmed complete.** `docs/security/data-flow-map.md:126` now says “speaker-embedding download — candidate and pinned alike”; `scripts/setup-models.py:33` says “That guard is installed for the speaker-embedding helper only”. This matches the custom opener at `scripts/setup-models.py:230`. Silero’s default opener at `scripts/setup-models.py:149` remains separate from its digest check at `scripts/setup-models.py:152`; flow 8’s pre-promotion record remains accurate for the recorded state.
- **PR-REG-001 — Fix confirmed complete.** `scripts/speaker-embedding-smoke.py:12` uses `wespeaker-voxceleb-resnet34-LM.onnx`; `scripts/speaker-embedding-smoke.py:15` explicitly retains the unpinned candidate case. The remedy at `scripts/speaker-embedding-smoke.py:194` says “the pinned entry is written or promoted as” `<name>.onnx`. The diff changes wording only: `model_path.is_file()` at `scripts/speaker-embedding-smoke.py:191`, explicit-path loading and CLI behaviour remain unchanged. Both assertions matching `"setup-models"` remain satisfied by the message (`desktop/tests/test_setup_scripts.py:718`, `desktop/tests/test_setup_scripts.py:894`).
- **PR-LOW-023 — Fix confirmed complete.** `.cursor/plans/plan-practitioner-profile.md:558` now specifies “from the project folder in a normal PowerShell” and supplies `.venv\Scripts\python.exe scripts\setup-models.py --only speaker-embedding`. The interpreter and script paths make this runnable verbatim under the project’s documented prerequisites.

#### Pin and independent scope verification

- Ordinal comparisons against Task 0.4’s record at `.cursor/plans/plan-practitioner-profile.md:547` confirm all three values match exactly:
  - URL (`scripts/setup-models.py:91`): `https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/main/voxceleb_resnet34_LM.onnx`
  - Size (`scripts/setup-models.py:95`): `26530309`
  - SHA-256 (`scripts/setup-models.py:99`): `7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068`
- Candidate promotion remains after digest verification (`scripts/setup-models.py:282`, `scripts/setup-models.py:288`); fresh-download installation remains after digest verification (`scripts/setup-models.py:300`, `scripts/setup-models.py:305`). No unverified installation route was found.
- Searches across the scoped prose found no remaining overbroad redirect guarantee or current claim that pinned setup produces an unpromoted candidate. Historical task records and explicitly conditional empty-pin guidance remain appropriately distinguished. No further actionable practitioner-command defect or message-assertion regression was found.

PEER-ROUND-11 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 12 - 2026-09-15 - practitioner-profile Phase 1 (Tasks 1.1–1.4: embedder, profile custody, enrolment, D15), in-session `/review-loop` round 1 of cap 3
- Round status: Closed (4 of 4 Applied 2026-09-15 by Claude Code, one at a time, each verified by re-read; the three code-file fixes — `speaker_embedding.py`, `practitioner_profile.py` and their tests — await the composer's suite re-run before round 13)
- Source: Claude Code
- Primary review baseline: commit `f1471f1` (the commit predating this phase's first `/execute` checkpoint). Changed files (all read in full): `desktop/src/scribe_desktop/speaker_embedding.py`, `practitioner_profile.py`, `enrolment.py` (new); `session.py`, `session_store.py`, `logging_setup.py`, `ui/microphone.py`, `ui/models.py`; `scripts/setup-models.py`, `scripts/speaker-embedding-smoke.py`, `scripts/README.md`; `desktop/tests/test_speaker_embedding.py`, `test_practitioner_profile.py`, `test_enrolment.py` (new), `test_setup_scripts.py`, `test_ui_screens.py`; `docs/security/threat-model.md`, `retention-schedule.md`, `data-flow-map.md`; `CHANGELOG.md`. No generated or binary artefacts. Reviewed with the Critical Constraints in hand: no audio persisted (pinned by the temp-`LOCALAPPDATA` tests), the profile encrypted at rest under a DPAPI-wrapped key, nothing about the vector or consent in any log/status/exception (the tripwire markers; every typed error carries structure only), offline asserted before the onnxruntime import (`load_onnx_session` asserts at entry, imports after the path and digest checks), docstrings claiming only what the structure enforces (the two LOW claim-outruns found below).
- Post-Fix Regression Check: regression baseline = the b2 fix leg (the `_Flip` fixture in `test_enrolment.py`); test-only, no signature or shape changed, no caller affected — none.
- Executor Judgment: none beyond the findings (the `_numpy()` helper is repeated in three modules by the transcription module's established pattern; the test-local PCM helpers are deliberately per-file).
- Structural Quality: none.
- Missed-issue pass: re-read `speaker_embedding.py` (the load path and the mock), `practitioner_profile.py` (custody ordering, `_key_present`), `enrolment.py` (both exits of the capture loop), the `session.py` D15 hunks and `session_store.py`'s unwrap; result: MED-001, LOW-002.
- Finding verification: 6 candidates; 2 dropped (the `_l2_normalised` "model returned" wording for the file-less embedders — cosmetic, no behaviour; `profile_present` reading a permission error as "no profile" — a first-run hint by design, the save path refuses typed once LOW-002 lands); 0 downgraded.
- Round classification: round-1 review of this work (the Phase 0 rounds reviewed other code) — skipped.
- Fix-delta self-check: PASS — re-read 7 applied hunks across 5 files (the tone smoke input and its `__init__` call, the two mock/module docstrings, `_key_present` and the `save_profile` docstring, the two custody-ordering docstrings, the two new/tightened tests).

- **[MED]** MED-001: `desktop/src/scribe_desktop/speaker_embedding.py:96` — the load-time smoke inference feeds one second of digital silence
  - Triage: Fix-now
  - Fix route: fix-on-fast
  - Why it matters: silence is DEGENERATE through the front-end — every frame's fbank is the constant log(eps), which per-utterance mean subtraction turns into an all-zero feature matrix. A model's response to an all-zero input is exactly the edge case that could come back as a zero or non-finite vector; `_l2_normalised` would then raise and EVERY `OnnxSpeakerEmbedder` construction would fail on the real model, taking enrolment and attribution down to the D2 fallback for no fault in the model file. The fake-session tests could not see this (the fake returns a constant fourth component), and the real-model test only runs where the cache is visible.
  - Current behaviour: `_SMOKE_PCM = b"\0" * 32000` fed to `fbank` at construction.
  - Desired behaviour: a deterministic, ordinary, non-degenerate one-second input (a 440 Hz tone at moderate int16 amplitude) generated in numpy at construction; the same frame count so the probe exercises the same axes.
  - Pattern to follow: `SileroVad`'s load-time smoke inference (PR-MED-015) — the point is to fail at load on an INCOMPATIBLE export, not to feed a pathological input.
  - Pattern siblings: none found (searched `_SMOKE_PCM`, `b"\0" *`, `smoke inference` across `desktop/src`; the VAD's silent frame is legitimate for a probability model that must accept silence).
  - Verification: `test_construction_probes_shape_and_smoke_infers_once` still pins one feed of shape `(1, 98, 80)`; the skip-if-absent `TestRealModel` exercises the real path where the cache is visible; suite re-run by the composer.
  - Regression risk: `OnnxSpeakerEmbedder.__init__` only.
  - /fix decision: Applied
  - /fix notes: `_SMOKE_PCM` replaced by `_smoke_pcm()` (440 Hz, amplitude 8000, one second, numpy under the offline assert) with the reason recorded beside it; the constructor calls it; no other site. Verified by re-read: the feed shape is unchanged (16000 samples → 98 frames), the fake-session tests' arithmetic is unaffected.
  - /fix date: 2026-09-15
  - /fix applied by: Claude Code
- **[LOW]** LOW-001: `desktop/src/scribe_desktop/speaker_embedding.py:41` and `:503` — the module docstring ("no function keeps a reference to the PCM it was given") and the mock's docstring ("never the bytes") outrun the structure: the caller-supplied lookup map's KEYS are PCM the double holds, and `test_records_lengths_never_bytes` passed trivially (it inspected top-level values, and the map is a dict) — Triage: Fix-now; Decision: Applied (both docstrings now say exactly what is held — the caller's map and the embedded lengths — and that embedding never adds bytes; the test is `test_holds_only_the_callers_map_and_the_lengths_it_embedded`: after embedding a mapped and an unmapped PCM the map still holds only the caller's key; siblings: none — the module's other claims were checked line by line)
- **[LOW]** LOW-002: `desktop/src/scribe_desktop/practitioner_profile.py:203` — `_key_present` lets a non-`FileNotFoundError` stat failure (a locked or permission-denied `key.dpapi`) escape `save_profile` as a raw `OSError`, against the module's typed-error posture; the direction was already safe (nothing written) but untyped — Triage: Fix-now; Decision: Applied (any other `OSError` is now `StoreWriteError("profile key custody blob is not readable")`, raised before anything is written; the docstrings of `_key_present` and `save_profile` say so; new test `test_uninspectable_key_refuses_the_save_before_any_write` pins that the on-disk bytes are unchanged; siblings: `profile_present` deliberately reads any stat failure as "not present" — a first-run hint, not custody — and `load_profile`'s reads are already typed)
- **[LOW]** LOW-003: `desktop/src/scribe_desktop/practitioner_profile.py:25` and `docs/security/threat-model.md` Practitioner-profile §1 — the custody-ordering claim "no partial state (a new key beside an old blob, or the reverse) can exist" is wrong in both directions: an old key beside a NEW blob is the normal re-enrolment result, and a key with no blob IS a partial state the ordering allows (it reads as absent) — Triage: Fix-now; Decision: Applied (both texts now state exactly what the structure enforces — the key is never regenerated while a key blob exists, so a new key beside an old blob cannot arise, and the one partial state allowed is key-without-blob, read as absent; sibling searched: the retention-schedule row says only "re-enrolment replaces ONLY `voice.enc` under the existing key", which is accurate and untouched)

### Round 13 - 2026-09-15 - practitioner-profile Phase 1 (Tasks 1.1–1.4), in-session `/review-loop` round 2 of cap 3 (confirmation)
- Round status: Closed (2 of 2 Applied 2026-09-15 by Claude Code, doc-only — no suite owed) — LOOP CONVERGED at this round
- Source: Claude Code
- Primary review baseline: commit `f1471f1`, the same full changed-files set as round 12 (every file re-read in this session; `speaker_embedding.py` and `practitioner_profile.py` re-read from disk again after the round-12 fixes).
- Post-Fix Regression Check: regression baseline = the round-12 fix leg (four hunks: the tone smoke input and its constructor call; the mock/module PCM-retention docstrings and the tightened test; the typed `_key_present` and its new test; the custody-ordering docstring and threat-model text). `_key_present` now raises `StoreWriteError` on a non-`FileNotFoundError` stat failure — its only caller is `save_profile`, whose docstring records it; `_smoke_pcm()` feeds the same 16000-sample length, so the fake-session probe assertion `(1, 98, 80)` and `embedding_dim` are unchanged; no signature, return type or data shape changed; the composer's re-run (1514 passed) covers every changed exit path. Result: none.
- Executor Judgment: none. Structural Quality: none.
- Missed-issue pass: re-read `speaker_embedding.py` (the embedders, the smoke input), `practitioner_profile.py` (the custody docstrings, `_key_present`, `save_profile`), and every security-doc claim that names a Phase 1 mechanism against the code; result: LOW-001, LOW-002.
- Finding verification: 3 candidates; 1 dropped (`_smoke_pcm`'s redundant `bytes(...)` wrapper around `tobytes()` — cosmetic, no behaviour); 0 downgraded.
- Round classification: 2 🆕 / 0 ⚡ / 0 🔁 — converging (only pre-existing doc-precision LOWs).
- Fix-delta self-check: PASS — re-read 3 applied hunks across 3 doc files.

- **[LOW]** LOW-001: `docs/security/threat-model.md` Practitioner-profile §5 and `CHANGELOG.md` (the Phase 1 entry) — both say `begin_enrolment` refuses "while a registered activity (the benchmark worker) runs", but Phase 1 ships only the hook (`set_enrolment_blocker`); nothing registers the benchmark until Task 3.1/3.2 wires `MainWindow`, so that refusal is not yet live — a claim ahead of the structure — Triage: Fix-now; Decision: Applied (both now say the hook exists and the app registers the benchmark worker at Phase 3, and the threat model marks which direction of the exclusion IS live — the benchmark refusing while enrolling; siblings searched: `session.py`'s `begin_enrolment` docstring says "the registered blocker" without naming the benchmark and is accurate; the plan's Task 3.1 already carries the wiring note)
- **[LOW]** LOW-002: `docs/security/retention-schedule.md` (the profile row) — "no repr, dump or JSON of it can reach a log" over-claims: the tripwire drops renderings that carry a registered marker; a field-restricted dump with none of the marker fields would pass (and would carry nothing sensitive), and the threat model already states that limit — Triage: Fix-now; Decision: Applied (the row now says a repr, full dump or JSON carries a marker and is dropped, restates the documented limit, and names the primary control — nothing in the profile path logs; sibling: `practitioner_profile.py`'s module docstring says "a stray repr, model_dump or JSON ... is dropped", accurate as a description of the markers, untouched)

### Round 14 - 2026-09-15 - practitioner-profile Phase 1 (Tasks 1.1–1.4), independent cross-family codex peer review (first cross-family code round)

- Round status: Closed (3 of 3 Applied 2026-09-15 by the executor's `/fix` leg after the composer routed all three to fixing under `gates=fix-biased` — PR-HIGH-003 at its executor-verified MED; the composer's suite re-run and the codex confirmation round 15 are pending — the round re-opens only if the peer refutes a fix)
- Fix-delta self-check: PASS — re-read 9 applied hunks across 5 files (the shared model config and both `model_config` lines, the `from None` loader branch, the capture-failure slot and its two checks, the three custody docstrings/threat-model paragraph, the two test additions)
- Source: Codex peer-review
- Baseline: `main` at HEAD `f1471f1`; the uncommitted Phase 1 working tree supplied for this review.
- Files reviewed: The pinned 21-file surface: `desktop/src/scribe_desktop/{speaker_embedding,practitioner_profile,enrolment,session,session_store,logging_setup}.py`; `desktop/src/scribe_desktop/ui/{microphone,models}.py`; `desktop/tests/{test_speaker_embedding,test_practitioner_profile,test_enrolment,test_setup_scripts,test_ui_screens}.py`; `scripts/{setup-models,speaker-embedding-smoke}.py`; `scripts/README.md`; `docs/security/{threat-model,data-flow-map,retention-schedule}.md`; `CHANGELOG.md`; and the specified sections of `.cursor/plans/plan-practitioner-profile.md`. The six new files and both custody/controller files were read in full. Supporting review covered the permitted VAD, offline helpers, capture backend, spectral embedding, logging-tripwire tests and dependencies.
- Validation basis: Static review; composer-verified state accepted: ruff clean, strict mypy clean over 33 source files, pytest 1514 passed. No tests, payloads or application code executed; no files written.
- Finding verification: 7 candidates / 4 dropped / 0 downgraded. Dropped: same-user model-file substitution already covered by the accepted boundary; missing-`LOCALAPPDATA` prerequisite edge; redundant formatter-field test expansion where the generic scan already applies; traceback-local memory retention beyond the documented scrubbing guarantee.

#### Confirmed / disputed (rounds 12–13)

- **Round 12 MED-001 — confirmed fixed:** `speaker_embedding.py:107–111` generates the deterministic tone, and construction uses it at `:439`; the unchanged inference geometry remains tested.
- **Round 12 LOW-001 — confirmed fixed:** `speaker_embedding.py:38–43` and `:514–522` accurately describe the mock’s retained caller-supplied map; `test_speaker_embedding.py:511–522` checks that embedding adds lengths without adding PCM keys.
- **Round 12 LOW-002 — confirmed fixed:** `practitioner_profile.py:214–215` translates other key-stat failures to `StoreWriteError` before key generation or replacement.
- **Round 12 LOW-003 — partly confirmed:** the normal existing-key/new-blob state and first-save key-only state are now described correctly. The replacement wording introduces an unsupported universal claim about existing key blobs; the distinct regression is recorded below as PR-REG-002.
- **Round 13 LOW-001 — confirmed fixed:** the threat-model draft and CHANGELOG distinguish the blocker hook from its future registration. `session.py:815–821` provides the hook; `ui/microphone.py:298–306` implements the opposite exclusion. Benchmark registration and close refusal belong to the forthcoming Practitioner-tab integration; the recorded flow-8 correction is already assigned to Phase 3 documentation and is not re-logged.
- **Round 13 LOW-002 — confirmed fixed:** the retention row now limits the tripwire claim to marker-bearing representations. `logging_setup.py:266–287` scans the formatter’s fields and exception/stack channels; bare values remain an explicitly documented limitation.

#### PR-HIGH-003 — Profile validation errors expose sensitive input values

- **Severity:** HIGH
- **Location:** `desktop/src/scribe_desktop/practitioner_profile.py:292`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** The Critical Constraint explicitly excludes voice-vector and consent contents from exception messages. The public parsing path raises input-bearing Pydantic errors, and the custody loader preserves those errors as an explicitly rendered cause. A structural outer message does not remove the sensitive exception underneath it.
- **Current behaviour:** Both models use `model_config = ConfigDict(frozen=True, extra="forbid")` (`:114`, `:134`), without hiding input values in validation-error rendering. `from_bytes` directly returns `cls.model_validate_json(blob)` (`:189`). The loader acknowledges that “a pydantic error’s rendered detail carries input values (the vector)” (`:290–291`), but then raises `ProfileUnusableError("malformed", "voice.enc is not a valid profile") from exc` (`:292`). A profile whose embedding fails field validation can therefore expose its input vector through the direct `ValidationError` or the loader’s chained traceback.
- **Desired behaviour:** Make profile and consent validation-error renderings omit sensitive inputs, and prevent the loader from exposing an input-bearing validation cause. Preserve the structural `malformed` reason.
- **Pattern to follow:** The loader’s existing structural-error convention at `:293–300`; apply that convention to the complete rendered exception chain as well as the outer message.
- **Pattern siblings:** Within the profile module: `ConsentRecord` configuration (`:114`), `PractitionerProfile` configuration (`:134`), direct `from_bytes` validation (`:188–189`), and the loader wrapper (`:289–292`). The pre-existing Pydantic wrappers in `session_store.py:645` and `:771` use a related chaining pattern; they are not additional Phase 1 findings or permission to broaden this fix.
- **Invariant:** Neither the vector nor consent contents appear in an exception message, status, report or log.
- **Verification:** Static reproduction path: parse a profile with otherwise meaningful embedding components and a component rejected by the finite-value validator at `:153–157`; inspect the direct validation error and the complete chained loader exception. The existing malformed-content test at `test_practitioner_profile.py:394–401` checks an empty object and only the wrapper’s string. Add checks for sensitive input-bearing failures and complete exception rendering. The tripwire is insufficient as the sole remedy: an unquoted Pydantic field location does not necessarily contain the quoted or assignment-form signatures at `logging_setup.py:148–156`. No payload was authored or executed during review.
- **Regression risk:** Detailed validation diagnostics become intentionally less revealing. Keep error types/reasons and existing custody failure handling stable.
- **/fix decision:** Applied
- **/fix notes:** `practitioner_profile.py` — one shared `_NO_INPUT_IN_ERRORS = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)` is now the `model_config` of BOTH `ConsentRecord` and `PractitionerProfile` (no new dependency: pydantic's own switch), and the loader's `malformed` branch raises `ProfileUnusableError` `from None` with a structural message naming the error count and the field locations (`exc.errors()` `loc` joined; never a value) — the `malformed` reason, the `key`/`authentication`/`model` branches and the custody ordering are unchanged. Tests (`test_practitioner_profile.py`): new platform-neutral `TestValidationErrorsCarryNoInput` — a non-finite component (field validator), a dimension mismatch (model validator, whose input is the WHOLE record) and a consent-record error, each asserting the complete `traceback.format_exception` rendering keeps the structural reason and carries none of the sentinel markers (a distinctive vector component `0.31337`, `consent-v7`, a 2031 timestamp); `test_authentic_but_invalid_content_is_malformed` now pins `__cause__ is None` and `__suppress_context__`; new Windows `test_malformed_blob_renders_no_vector_or_consent_anywhere` drives the loader over an authenticated blob whose `embedding_dim` mismatches and asserts the full rendering has no `ValidationError` and no marker. Siblings: the peer's `session_store.py:645`/`:771` chaining sites were explicitly excluded by the finding and are untouched. Verified by re-read of every hunk; the composer runs the suites.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### PR-MED-019 — A queued capture failure can be bypassed by target completion

- **Severity:** MED
- **Location:** `desktop/src/scribe_desktop/enrolment.py:193`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** Capture can report success after the backend has detected dropped audio or queue overflow. That contradicts the typed capture-failure contract and lets the upcoming enrolment flow accept audio whose integrity the backend has already rejected.
- **Current behaviour:** `on_error` appends `blocks.queue.append(_Failed(exc))` behind pending audio (`:148–153`). The consumer detects a failure only when that item is dequeued (`:174–180`). An earlier audio block can instead satisfy `if speech_seconds >= target_speech_seconds: return bytes(buffer)` (`:193–194`). The `finally` stops the stream but never checks pending failures (`:201–210`). The real backend’s block-then-error callback ordering at `audio_capture.py:170–173` makes a flagged final block a concrete trigger.
- **Desired behaviour:** A detected capture failure must take precedence over successful completion. Retain failure state independently of queued PCM and check it through stream shutdown before returning successful audio.
- **Pattern to follow:** The existing fail-closed `EnrolmentCaptureError` branch at `:179–180`; ensure its meaning applies independently of queue position.
- **Pattern siblings:** Both producers converge on this queue: backend errors through `on_error` (`:148–153`) and queue overflow through `on_block` (`:155–159`). Both successful-target and duration-cap decisions at `:193–200` occur before a later failure item is consumed.
- **Invariant:** Known device failure or dropped capture data must not become a successful enrolment result.
- **Verification:** Use a deterministic backend sequence that delivers a target-reaching block and reports its capture error before stream shutdown completes; require `EnrolmentCaptureError`. Cover queued overflow as well. The existing overflow test at `test_enrolment.py:214–231` uses a target beyond its delivered audio, so it reaches the failure item without exercising this early-success branch. Static review only.
- **Regression risk:** Shutdown/callback ordering needs care: avoid deadlocking the callback thread, preserve cancellation handling, and retain stream/buffer/VAD cleanup on every result.

- **/fix decision:** Applied
- **/fix notes:** `enrolment.py` `record_enrolment` — a `failure` slot (the FIRST capture failure) written by `on_error` under `blocks.mutex` BEFORE the wake-up `_Failed` item is enqueued (both producers, the backend's `on_error` and the overflow path, go through it); `raise_if_failed()` reads the slot under the same mutex and is called (a) in the loop after each block, before BOTH decision exits (target reached, cap hit), and (b) in the `finally` after `stream.stop()` on the SUCCESS path only (`succeeded` flag) — no callback can fire once the stream is stopped, so that is the last possible failure, and it wins over the successful return; a failing exit keeps its original error; cancellation, the 10 s idle timeout and the buffer/VAD cleanup are unchanged; the callback thread only ever takes the queue mutex briefly (no wait), so no deadlock. Tests (`test_enrolment.py`): `test_failure_reported_behind_the_target_block_still_fails` (a target-reaching block, then `backend.fail()` while the consumer is gated — deterministic via the existing gated-VAD pattern → `EnrolmentCaptureError`, stream released, nothing under a temp `LOCALAPPDATA`), `test_overflow_reported_behind_the_target_block_still_fails` (queue bound 1, overflow behind the target block), `test_failure_reported_during_shutdown_still_fails` (a stream whose `stop()` reports dropped frames → the post-shutdown check raises, the inner stream still released). Invariant honoured by reading: "known device failure or dropped capture data must not become a successful enrolment result" — every `return` is preceded by a slot check and followed by the post-stop check. Verified by re-read; the composer runs the suites.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### PR-REG-002 — Revised custody wording overstates key continuity

- **Severity:** LOW
- **Location:** `desktop/src/scribe_desktop/practitioner_profile.py:25`
- **Triage:** Fix-now
- **Fix route:** fix-on-fast
- **Why it matters:** The round-12 documentation fix now promises a stronger invariant than the implementation enforces. Foundation documentation must distinguish reusable custody from a merely present, cryptographically dead key file. This is a documentation defect; the identified path does not destroy an otherwise readable profile or revive an old generation.
- **Current behaviour:** The revised text says, “The key is never regenerated while a key blob exists,” and that a new key beside an old blob “cannot arise” (`:25–29`). However, `_key_present` returns `not key_blob_is_dead(key_path.stat().st_size)` (`:211`). A present zero-length/truncated key therefore selects fresh-key generation at `:245`, followed by key writing at `:248` before blob replacement at `:250`. If that replacement fails, the new key remains beside the old, already unusable blob. Separately, key-first deletion at `:320–324` can leave an old blob without its key when blob unlink fails.
- **Desired behaviour:** Scope key-continuity and failed-re-enrolment guarantees to an existing reusable key. Name missing/dead custody and interrupted deletion as additional possible states, without claiming loss of a readable profile.
- **Pattern to follow:** `session_store.py:115–120` explicitly treats zero-length/truncated blobs as cryptographically dead; documentation should use that same distinction.
- **Pattern siblings:** The matching key-continuity and “only partial state” assertions in `docs/security/threat-model.md`, Practitioner-profile surface 1. The profile module’s `_key_present` docstring at `:205–209` also says only confirmed absence returns false, despite its dead-key branch. The retention row’s ordinary existing-key re-enrolment description does not require the same universal claim.
- **Invariant:** Security documentation states only what the enforcing structure guarantees and names permitted failure residue.
- **Verification:** Static branch trace: present truncated key → `_key_present` false → new key written → blob replacement fails. Also trace successful key unlink followed by failed blob unlink. Reconcile the affected prose against both paths; no security payload or fault injection was run.
- **Regression risk:** Documentation-only correction. Do not change dead-key recovery or custody ordering merely to make the prose true.
- **/fix decision:** Applied
- **/fix notes:** Docs only, no custody code changed. `practitioner_profile.py` module docstring: the re-enrolment guarantee is scoped to an EXISTING, REUSABLE key (present, not dead, unwrappable) and a new "Permitted states" bullet names the three residues — key-without-blob (absent), a dead key blob (a fresh key is written; a failed blob write then leaves the new key beside the old, already-unreadable blob), and an interrupted deletion (keyless blob, typed and named) — each with the `reason` the loader reports; `_key_present` docstring now says `False` for a confirmed absence AND a dead blob, naming why; `docs/security/threat-model.md` surface 1 carries the same scoped claim and the same three permitted states. Siblings: the retention row's "re-enrolment replaces ONLY `voice.enc` under the existing key" needs no universal claim and is untouched. Verified by re-read against `_key_present`, `save_profile` and `delete_profile`.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-15)
- PR-HIGH-003: materiality=behavioral; verified severity=med; peer severity=high (preserved); evidence: `practitioner_profile.py:189` returns `model_validate_json` raw and `:292` raises `from exc`, so `traceback.format_exception` renders the pydantic cause with its `input_value=` for the failing component (and, for the model-level `_dim_matches` validator at `:174-181`, the whole input including the vector and the consent record) — and the tripwire signatures at `logging_setup.py:148-156` do NOT match pydantic's unquoted location line (`embedding.0`), so a `logger.exception` around the loader would persist vector components: a genuine breach of the Critical Constraint that nothing about the vector or consent appears in any exception rendering. Downgrade evidence: no shipped caller renders the chain today — nothing in the profile path logs, and the Phase 3 `TaskThread.failed` route emits `type: str(exc)` (the terse outer message) only — so the exposure needs a future traceback logger or an interactive debugger inside boundary 2; the fix is a config flag pydantic already provides (`hide_input_in_errors=True` on both models' `model_config`, no new dependency) plus `from None` at `:292` and a test that renders the full chain of the loader's error AND the direct `from_bytes` error and asserts no vector component or consent value appears; scope: inside Phase 1's declared task list: yes (Task 1.2); production-impacting: no; recommendation: Fix-now — a structural constraint with a one-flag structural fix.
- PR-MED-019: materiality=behavioral; verified severity=med; peer severity=med (preserved); evidence: `enrolment.py:148-153` appends `_Failed` to the SAME FIFO deque behind any queued audio, `:193-194` returns success on the block that reaches the target without draining the queue, and the `finally` at `:201-210` stops the stream and clears the buffers but consults no failure state — with the real backend firing `on_block` then `on_error` for a status-flagged block (`audio_capture.py:170-173`), a final block that both completes the target and reports dropped frames returns success over audio the backend has rejected; the overflow producer (`:155-159`) converges on the same queue. Yes, the fix needs a failure flag checked through shutdown: `on_error` records the exception in a slot written under `blocks.mutex` BEFORE it enqueues the wake-up item; both decision exits (`:193` success, `:195` cap) check the slot first and raise `EnrolmentCaptureError` when set; the check before `return` is sufficient "through shutdown" because `stream.stop()` runs after it and no callback can fire once the stream is stopped, so no new state can arrive between the check and the return; cleanup in the `finally` is unchanged. Test shape: the existing `_SlowVad` gate pattern (`test_enrolment.py:214-231`) — deliver a target-reaching block, call `backend.fail()` while the consumer is gated, release, require `EnrolmentCaptureError`; a sibling for the overflow producer; scope: inside Phase 1's declared task list: yes (Task 1.3); production-impacting: no; recommendation: Fix-now — a fail-closed capture contract that currently fails open on one ordering.
- PR-REG-002: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: `practitioner_profile.py:211` returns `not key_blob_is_dead(...)`, so a present zero-length/truncated `key.dpapi` selects first-enrolment at `:245-250` and a fresh key is written beside the old blob — that blob is already cryptographically dead under the shared deadness rule (`session_store.py:115-120`), so no readable profile is lost and no generation is revived, but the round-12 wording "never regenerated while a key blob exists" (`:25-29`), the `_key_present` docstring's "only a CONFIRMED absence is False" (`:206-209`) and threat-model surface 1's "cannot arise" overstate it; `delete_profile:320-324` can leave the blob without its key when the blob unlink fails (typed, and the error names the file); scope: inside Phase 1's declared task list: yes (Tasks 1.2/1.4 docs); production-impacting: no; recommendation: Fix-now — scope the claim to a LIVE (non-dead) key blob and name dead-key regeneration and an interrupted deletion as the permitted residue, in all three sites; no custody code change.

PEER-ROUND-14 RESULT: 3 findings (CRIT 0 / HIGH 1 / MED 1 / LOW 1).

### Round 15 - 2026-09-15 - practitioner-profile Phase 1 (Tasks 1.1–1.4), independent cross-family codex peer review (confirmation round after round 14)

- Round status: Closed (2 of 2 Applied 2026-09-15 by the executor's `/fix` leg after the composer routed both to fixing under `gates=fix-biased`; the composer's suite re-run and the codex confirmation round 16 are pending — the round re-opens only if the peer refutes a fix)
- Fix-delta self-check: PASS — re-read 6 applied hunks across 3 files (the `raise_if_cancelled` helper and its three call sites, the two cancellation tests, the sentinel constant and the four tightened/added validation-rendering tests)
- Source: Codex peer-review
- Baseline: `main` at HEAD `f1471f194daf5555369c538179acf0cda6d1938a`; the supplied uncommitted Phase 1 working tree.
- Files reviewed: The pinned 21-file surface: `desktop/src/scribe_desktop/{speaker_embedding,practitioner_profile,enrolment,session,session_store,logging_setup}.py`; `desktop/src/scribe_desktop/ui/{microphone,models}.py`; `desktop/tests/{test_speaker_embedding,test_practitioner_profile,test_enrolment,test_setup_scripts,test_ui_screens}.py`; `scripts/{setup-models,speaker-embedding-smoke}.py`; `scripts/README.md`; `docs/security/{threat-model,data-flow-map,retention-schedule}.md`; `CHANGELOG.md`; and the specified plan sections, including the complete Round 14 block and its fix records. All six new files were read in full. Supporting review covered `audio_capture.py` callback ordering and the logging tripwire.
- Validation basis: Static review only. Composer-verified results accepted: ruff clean, strict mypy clean over 33 source files, pytest 1521 passed. No tests, application code or payloads executed; no files or directories written. Pin constants remain single-sourced at `desktop/src/scribe_desktop/speaker_embedding.py:58`, imported and aliased by `scripts/setup-models.py:96`; offline assertion at `speaker_embedding.py:285` still precedes path/digest checks and the ONNX import at `:308`.
- Finding verification: 4 candidates / 2 dropped / 0 downgraded. Dropped: sensitive extra-field locations without an established producer; value-bearing numpy conversion errors requiring nonnumeric fake output outside the pinned model’s contract.

#### Confirmed / disputed (round 14 fixes)

- **PR-HIGH-003 — fix confirmed partial: production correction complete; consent regression verification incomplete.** Both models use input-hiding configuration (`desktop/src/scribe_desktop/practitioner_profile.py:124`, `:130`, `:152`); direct `from_bytes` uses that configuration (`:207`), and the loader raises structural `malformed` diagnostics `from None` (`:319`). The model-level loader test excludes the complete rendered validation cause (`desktop/tests/test_practitioner_profile.py:490`). The standalone-consent test gap is PR-LOW-024 below.
- **PR-MED-019 — fix confirmed complete for recorded capture failures.** The first failure is stored under the queue mutex before notification (`desktop/src/scribe_desktop/enrolment.py:157`); overflow uses the same producer (`:167`); failure checks precede both decisions (`:210`) and follow shutdown on success (`:235`). Shutdown holds no queue mutex, and buffer/VAD cleanup remains in the nested `finally` (`:220`). The three new tests exercise target-reaching failure, overflow and shutdown failure (`desktop/tests/test_enrolment.py:233`, `:260`, `:285`) and would reject the pre-fix success behavior. Cancellation is a separate missed sibling below.
- **PR-REG-002 — fix confirmed complete.** Reusable-key continuity and dead-key/interrupted-deletion residue are accurately distinguished in `desktop/src/scribe_desktop/practitioner_profile.py:23`, `:30`, `:223` and `docs/security/threat-model.md:340`. Save and deletion ordering remain unchanged (`practitioner_profile.py:255`, `:351`).

#### PR-MED-020 — Cancellation during the final block can return successful PCM

- **Severity:** MED
- **Location:** `desktop/src/scribe_desktop/enrolment.py:210`
- **Triage:** Fix-now
- **Fix route:** premium-only
- **Why it matters:** A cancellation request can be ignored permanently when the current block completes enrolment. The caller receives successful PCM and can continue into embedding/save despite the pending cancellation.
- **Current behaviour:** The only cancellation check is `if should_stop is not None and should_stop():` at `:186`, before the queue wait and block processing. After `on_progress(...)` at `:205`, execution performs `raise_if_failed()` at `:210`, then `succeeded = True` and `return bytes(buffer)` at `:212–213`. The post-shutdown success check at `:235` also checks only capture failure. A progress callback can synchronously set the cancellation event on the target-reaching update; no thread race is needed.
- **Desired behaviour:** Recheck cancellation before accepting the final block and before releasing a successful result after shutdown. Preserve capture-failure precedence, existing failing exits, and cleanup.
- **Pattern to follow:** The new failure checks before completion and after shutdown (`:210`, `:230–235`), combined with the existing typed cancellation branch (`:186–187`).
- **Pattern siblings:** Searches for `should_stop`, `Cancelled`, `succeeded`, `return bytes`, `raise_if_failed` and `on_progress` found one cancellation poll (`:186`) and one successful return (`:213`), plus its post-shutdown completion path (`:230–235`). Timeout (`:190–193`) and duration-cap (`:214–219`) exits also follow the initial poll but already reject PCM. The existing cancellation test (`desktop/tests/test_enrolment.py:188`) supplies sub-target audio and reaches another iteration.
- **Invariant:** A pending cancellation observed before successful completion must not produce an enrolment result.
- **Verification:** Add deterministic coverage where the target-reaching progress callback requests cancellation, and where cancellation arrives during shutdown. Require `EnrolmentCancelledError`, no returned PCM, released stream and reset VAD. Static inspection confirms the current code returns successfully in both cases when no capture failure exists.
- **Regression risk:** Keep cancellation callbacks outside queue locks and retain unconditional cleanup. This is MED control-flow behavior: capture integrity is intact, and Practitioner-tab persistence wiring remains future work.
- **/fix decision:** Applied
- **/fix notes:** `enrolment.py` — a `raise_if_cancelled()` helper (the caller's predicate evaluated OUTSIDE any queue lock) now runs at the loop top (replacing the inline poll), again after `raise_if_failed()` before BOTH decision exits (so a Cancel set synchronously by the target-reaching `on_progress` is honoured, capture failure keeping precedence), and again after stream shutdown on the success path, after the post-shutdown failure check; failing exits keep their original error; cleanup unchanged. Tests (`test_enrolment.py`): `test_cancellation_requested_by_the_target_reaching_progress_callback` (`on_progress` sets the stop event at the target → `EnrolmentCancelledError`, no PCM, stream released, VAD reset twice) and `test_cancellation_arriving_during_shutdown_still_cancels` (a stream whose `stop()` sets the event → the post-shutdown poll raises). Invariant honoured by reading: every `return` is now preceded by a cancel poll and followed by the post-stop poll. Verified by re-read; the composer runs the suites.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### PR-LOW-024 — Consent error regression does not check the rejected input

- **Severity:** LOW
- **Location:** `desktop/tests/test_practitioner_profile.py:224`
- **Triage:** Fix-now
- **Fix route:** fix-on-fast
- **Why it matters:** The production consent model hides inputs correctly, but its new regression test passes without that protection. One explicitly required half of PR-HIGH-003 is therefore unprotected against recurrence.
- **Current behaviour:** The invalid field is `"learning_opt_in": "not-a-bool"` at `:230`. The assertion is `assert not any(marker in rendered for marker in _SECRET_MARKERS), rendered` at `:235`. That marker set (`:183`) contains vector digits and values from the valid consent-version/timestamp fields. Pre-fix field-error rendering exposes the rejected boolean input, not those valid siblings, so the assertion still passes.
- **Desired behaviour:** Assert that Pydantic’s input-value metadata is absent, or check the actual rejected value using a sentinel placed outside traceback-rendered call lines. The test must fail when the consent model loses `hide_input_in_errors`.
- **Pattern to follow:** The vector-field test places its sentinel in the rejected field (`:208–215`); the loader test additionally checks that the unwanted validation cause itself is absent (`:490`).
- **Pattern siblings:** Searches for `hide_input`, `_SECRET_MARKERS`, `_rendered`, `format_exception`, `__cause__` and `__suppress_context__` covered the vector-field test (`:208`), direct model-validator test (`:217`), consent test (`:224`), loader cause pin (`:457`) and loader model-validator test (`:467`). Apply a representation-independent input-metadata assertion to the direct model-validator check too, so coverage does not depend on whole-record representation truncation.
- **Invariant:** Regression coverage for both model configurations must reject the corresponding pre-fix input-bearing rendering.
- **Verification:** Static comparison of the sole rejected consent field with every asserted marker establishes the gap. After tightening, verify that removing input hiding from `ConsentRecord` alone makes its test fail; retain full traceback rendering and the structural-field assertion.
- **Regression risk:** Test-only change; production code already satisfies this requirement.
- **/fix decision:** Applied
- **/fix notes:** Test-only (`test_practitioner_profile.py`). (1) New `test_both_models_hide_their_input_structurally` asserts `model_config["hide_input_in_errors"] is True` on BOTH models — a dropped flag fails here whatever pydantic renders. (2) The consent test is now `test_consent_record_error_hides_the_rejected_value`: the REJECTED field carries the sentinel — `consent_text_version=_SECRET_REJECTED_CONSENT_VERSION` (`"consent-v7x"`, a module constant so no traceback-rendered call line carries it; it fails the version pattern) with a valid `learning_opt_in` — and the test asserts the location survives, `"input_value" not in rendered`, and no marker (`"consent-v7"` matches the rejected value as a substring). Pre-fix reasoning: without the flag pydantic renders `[type=string_pattern_mismatch, input_value='consent-v7x', input_type=str]`, so BOTH the metadata assertion and the marker assertion fail — the test now proves the consent half of PR-HIGH-003. (3) The representation-independent `"input_value" not in rendered` assertion is added to the direct model-validator test (so coverage no longer depends on where pydantic truncates the whole-record repr) and to the vector-field test. Full traceback rendering and the structural-field assertions are retained. Verified by re-read; the composer runs the suites.
- **/fix date:** 2026-09-15
- **/fix applied by:** Claude Code

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-15)
- PR-MED-020: materiality=behavioral; verified severity=med; peer severity=med (preserved); evidence: `enrolment.py:186` is the ONLY `should_stop` poll and it runs before the queue wait, `:210-213` then checks the failure slot and returns success without re-polling, and the post-shutdown check at `:230-235` consults only the failure slot — so a cancellation requested synchronously from the target-reaching `on_progress` (`:204-207`) or during shutdown is ignored and PCM is returned, against the docstring's contract at `:134-135` ("`EnrolmentCancelledError` when `should_stop` returns True"); kept at MED rather than downgraded because the practitioner's Cancel on a biometric capture must be honoured by the structure, not by the caller re-checking (the Phase 3 tab would otherwise embed and save a profile the practitioner aborted; the window is one block's processing, but the peer's synchronous-callback case needs no race at all). Fix shape: fold the cancel poll into the same two places as the failure check — before both decision exits (after `raise_if_failed()`, failure precedence kept) and after shutdown on the success path — plus two deterministic tests (`should_stop` set from inside the target-reaching `on_progress`; set by a stream whose `stop()` flips it) requiring `EnrolmentCancelledError`, no PCM, stream released, VAD reset; scope: inside Phase 1's declared task list: yes (Task 1.3); production-impacting: no; recommendation: Fix-now — same class as PR-MED-019 (a decision exit ignoring a signal), same fix locus.
- PR-LOW-024: materiality=behavioral (test-only: the pin does not prove the property it names); verified severity=low; peer severity=low (preserved); evidence: `test_practitioner_profile.py:224-235` rejects `"learning_opt_in": "not-a-bool"` (`:230`) while `_SECRET_MARKERS` (`:183`) holds only the vector digits and the VALID consent version/timestamp — a pydantic field error renders `input_value=` for the rejected field alone, so without `hide_input_in_errors` on `ConsentRecord` the rendering would carry `'not-a-bool'`, which no marker matches, and the test would still pass; the direct model-validator test (`:217-222`) depends on the whole-record repr reaching the `embedding` entry before pydantic's input truncation, so it too can pass without the flag. Fix shape (test-only): assert the configuration structurally (`ConsentRecord.model_config["hide_input_in_errors"] is True`, likewise for `PractitionerProfile`), make the REJECTED value the sentinel (a consent version that fails the pattern, e.g. `consent-v7x`, held in a module constant so no traceback-rendered call line carries it), and assert `input_value` is absent from every rendering (the representation-independent check the peer names) in the consent, model-validator and vector-field tests; scope: inside Phase 1's declared task list: yes (Task 1.4 tests); production-impacting: no; recommendation: Fix-now — restores the regression protection PR-HIGH-003's second half was meant to have.

PEER-ROUND-15 RESULT: 2 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 1).

### Round 16 - 2026-09-15 - practitioner-profile Phase 1 (Tasks 1.1–1.4), independent cross-family codex peer review (confirmation round after round 15)

- Round status: Closed
- Source: Codex peer-review
- Baseline: `main` at HEAD `f1471f194daf5555369c538179acf0cda6d1938a`; working tree against HEAD, including the six new files.
- Files reviewed: The pinned 21-file surface: `desktop/src/scribe_desktop/{speaker_embedding,practitioner_profile,enrolment,session,session_store,logging_setup}.py`; `desktop/src/scribe_desktop/ui/{microphone,models}.py`; `desktop/tests/{test_speaker_embedding,test_practitioner_profile,test_enrolment,test_setup_scripts,test_ui_screens}.py`; `scripts/{setup-models,speaker-embedding-smoke}.py`; `scripts/README.md`; `docs/security/{threat-model,data-flow-map,retention-schedule}.md`; `CHANGELOG.md`; and `.cursor/plans/plan-practitioner-profile.md`, including Critical Constraints and the complete Round 15 block, verified tuples and `/fix` fields. Enrolment source/tests and profile error-rendering tests read in full. Supporting reads covered capture callbacks, VAD reset and task-error delivery.
- Validation basis: Static review only. Composer-verified results accepted: ruff clean; strict mypy clean over 33 source files; pytest 1524 passed, zero network, writes confined to `tmp_path`. No tests, application code or payloads executed; no files or directories created or edited. Final Git inspection confirms exactly the pinned 15 modified tracked files plus six new files, with no changes outside that surface.
- Finding verification: 2 candidates / 2 dropped / 0 downgraded. Dropped: an apparent missing UI lease-release path is explicitly assigned to Phase 3 (`.cursor/plans/plan-practitioner-profile.md:697`); generic exception forwarding has no demonstrated PCM/vector-bearing producer in the inspected production paths.

No new findings — converged.

#### Confirmed / disputed (round 15 fixes)

- **PR-MED-020 — fix confirmed complete.** After the progress callback, `raise_if_failed()` then `raise_if_cancelled()` precede `succeeded = True` and the sole PCM return (`desktop/src/scribe_desktop/enrolment.py:220`). Both checks run again after shutdown and cleanup (`:247`). Capture failure retains precedence at both completion checks; cancellation predicates execute outside queue locks (`:175`). The nested `finally` retains buffer clearing and VAD reset even when shutdown raises (`:231`). The new tests request cancellation from the target-reaching progress callback (`desktop/tests/test_enrolment.py:205`) and during stream shutdown (`:232`); both require no result, `EnrolmentCancelledError`, released stream and two VAD resets. Both reject the pre-fix behavior.
- **PR-LOW-024 — fix confirmed complete.** Both models’ input-hiding configuration is pinned directly (`desktop/tests/test_practitioner_profile.py:213`). The consent test places the sentinel in the rejected field and asserts `"input_value" not in rendered`, alongside the field location and sentinel exclusions (`:239`); removing `ConsentRecord` input hiding would fail these checks. The direct model-validator test also excludes input metadata independently of representation truncation (`:229`). `_rendered` still uses `"".join(traceback.format_exception(exc))` (`:194`), preserving full traceback coverage.

#### Independent confirmation

- Successful capture remains reachable; timeout and insufficient speech at the duration cap still reject PCM (`desktop/src/scribe_desktop/enrolment.py:198`, `:222`, `:225`). No additional completion bypass was found.
- D15 acquisition installs the lease after all refusals; identity-checked release clears it, while Start/Resume remain guarded (`desktop/src/scribe_desktop/session.py:823`, `:854`, `:376`, `:441`).
- Model pins remain single-sourced in `desktop/src/scribe_desktop/speaker_embedding.py:58`, imported by `scripts/setup-models.py:96`. Runtime digest verification still precedes the ONNX import (`speaker_embedding.py:294`, `:308`).

PEER-ROUND-16 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

### Round 17 - 2026-09-16 - practitioner-profile Phase 2 (Tasks 2.1–2.5: attribution, document fields, auto-confirm, harness, docs), in-session `/review-loop` round 1 of cap 3
- Round status: Closed (4 of 4 Applied 2026-09-16 by Claude Code, one per file, each verified by re-read; the three code-file fixes — `transcription.py`, `ui/transcript.py`, `speaker_eval.py` — and their test pins await the composer's suite re-run before round 18)
- Source: Claude Code
- Primary review baseline: HEAD `58e7bad` (the Phase 1 commit, the commit predating this phase's first `/execute` checkpoint). Changed files (all read in full — the source/doc diffs against HEAD, the new test module and the edited test regions): `desktop/src/scribe_desktop/transcription.py`, `speaker_embedding.py`, `ui/models.py`, `ui/transcript.py`, `speaker_eval.py`, `scripts/measure-speakers.py`, `docs/security/threat-model.md`, `docs/security/data-flow-map.md`, `docs/testing/speaker-measurement.md`, `CHANGELOG.md`, `desktop/tests/test_attribution.py` (new), `test_speaker_eval.py`, `test_ui_models.py`, `test_ui_screens.py`, this plan. No generated artefacts skipped. Reviewed with the Critical Constraints in hand: the windowed plaintext bound (the model embedding is computed on the same slice inside the same window and reduced to one float before the loop advances — held; the batching tests unchanged and green), D1 (the confirmed role stays the checked radio `generate()` reads; `enrolled_speaker` reaches `compose_draft` nowhere — grep), D4 (the line is always shown when attributed and `change` is one click, enabled with the other controls), the text-free rule (every new exception, status line and report cell carries labels, numbers, reason words, paths or fixed copy — no vector, PCM or transcript text; the readiness line renders only the structural reason word), and the harness writing no profile (pinned by the namespace test).
- Looks good: D3's both-entry-points rule is one seam (`attribution_inputs`) pinned on both factories; the readiness probe loads no model on the GUI thread and the "did not run" line covers the residue it cannot see; the lying-field defence is at construction; the D13 zero-match choice and the enrolled cluster are scoped to textual clusters (PR-MED-008) by one predicate; the enrolled condition scores all-`speaker_1` (PR-MED-014) and the replay provider keeps the second pass Whisper-free; the docs claim only what the structure enforces and name the residues (the pin-vs-bytes probe gap, the D4 boundary). Two deliberate non-findings: `model_report_lines` was NOT extended (D2 names it, but Task 0.6 assigned the in-app model-presence line to Task 3.2 — recorded on Task 2.3); the harness tests use a zero-crossing double (`_FrequencyEmbedder`) rather than `MockSpeakerEmbedder` (the plan's verification wording) — deterministic and ML-free, which is the intent, and it lets the pipeline's own slices be embedded without precomputing them. The D13 remainder-split consequence is already Task 2.6, not re-raised here.
- Executor judgment: LOW-002 (a duplicated predicate that contradicted a "one definition" docstring). Structural quality: none worth a maintainer's attention (`speaker_eval.main` grew by three sequential enrolment blocks; still one linear flow with the decisions commented — not flagged).
- Post-Fix Regression Check (regression baseline: the c1/c2 build state, before the c3/c4 fix legs): the c3/c4 fixes changed test fixtures/expectations, one docstring and one local rename (`auto` → `auto_counts` in `render_report`, no signature or shape change) — no caller affected; none.
- Missed-issue pass: re-read `transcription.py` (`transcribe_session`'s loop and tail, `attribute_speakers`, `enrolled_cluster`, the document validators), `ui/transcript.py` (`_populate_generation_controls`, `change_role`, `_reset_generation_state`, `_update_controls`), `speaker_eval.py` (`main`'s enrolment blocks, `_transcribe_in_temporary_store`, `EnrolmentInputs`), `ui/models.py` (`attribution_readiness` / `attribution_inputs`) with fresh eyes; result: LOW-001, LOW-004 (the other two came from the main passes). Checked and cleared: the pipeline keeps one similarity per segment even for an empty slice (None) so the degenerate branch's `enrolled_cluster` call stays index-aligned; the zero-match tie falls to the first-appearing label so no swap; `change_role_button.click()` is inert only while generation controls are disabled, which is also when a change would be meaningless; the "did not run" line's one unreachable-in-practice alternative cause (a profile enrolled between the worker finishing and the view showing) is blocked by D15's refusal while processing.
- Finding verification: 5 candidates; 1 dropped (an apparent GUI-thread cost in `attribution_readiness` — a DPAPI unwrap and one AES decrypt, milliseconds, same as every session-key unwrap the app already does on that thread); 0 downgraded.
- Findings (all LOW, all in scope, none production-impacting; no MED/HIGH/CRIT; no Defer/Accept — the Deferral Confirmation Gate did not fire):
  - **[LOW]** LOW-001: `desktop/src/scribe_desktop/transcription.py:1135` — the pipeline's profile/embedder identity guard checked `model_id` and `embedding_dim` but not `model_sha256`, while its docstring and D3 speak of the embedder's VERIFIED digest; the composition layer checks all three, the pipeline should not be looser than its own claim — Triage: Fix-now; Decision: Applied. `/fix notes`: the guard now compares `model_sha256` too; `test_attribution.py::test_a_profile_from_a_different_embedder_is_refused` gains the `model_sha256` case. Siblings: `ui/models.attribution_inputs` already compares all three (consistent). Verified by re-read; suite owed.
  - **[LOW]** LOW-002: `desktop/src/scribe_desktop/transcription.py:1246` — `has_text` was computed inline (`any(word.word_text.strip() ...)`) while `segment_has_text` claimed to be "the ONE definition" — a duplicated predicate the docstring said did not exist — Triage: Fix-now; Decision: Applied. `/fix notes`: new `words_have_text(words)` is the single definition (exported); `segment_has_text` delegates; the pipeline calls it; the "agrees with the radios' source" test also pins the delegation. Siblings: `ui.models.speaker_quotations` keeps its own join-and-strip (unchanged by the plan's instruction; the test pins the two agree). Verified by re-read; suite owed.
  - **[LOW]** LOW-003: `desktop/src/scribe_desktop/ui/transcript.py:303` — the auto-confirm reset (the flag plus two `hide()` calls) was copy-pasted at three sites (`_populate_generation_controls`, `change_role`, `_reset_generation_state`) — Triage: Fix-now; Decision: Applied. `/fix notes`: one `_clear_auto_confirm()` helper used at all three sites; behaviour identical (the offscreen tests cover all three paths). Siblings: none found (grep `attribution_label.hide`). Verified by re-read; suite owed.
  - **[LOW]** LOW-004: `desktop/src/scribe_desktop/speaker_eval.py:1013` — `EnrolmentInputs`' default dataclass `repr` rendered the profile, whose rendering carries the enrolment vector, in a module whose contract is that every result type renders text-free — nothing prints it today, but the module's posture is structural, not by-convention — Triage: Fix-now; Decision: Applied. `/fix notes`: both fields are `field(repr=False)`; the `TestEnrolmentInputs` test asserts the rendering carries neither `embedding` nor a vector value. Siblings: `ConditionResult` / `RecordingResult` hold only numbers and labels (none). Verified by re-read; suite owed.
- Recommended fix order (applied): LOW-002 → LOW-001 (same file, the predicate first so the guard hunk sits above unchanged code), LOW-003, LOW-004 — independent otherwise.
- Fix-delta self-check: PASS — re-read 4 applied hunks across 3 source files and their 3 test pins; no neighbouring exit path touched, no drive-by edit.
- Summary: files reviewed 15; critical 0; warnings 0 (0 HIGH / 0 MED); executor judgment items 1; structural quality items 0; round 17 (round 1 of this work's `/review-loop`, cap 3 — Round Classification not applicable); finding verification 5 candidates / 1 dropped / 0 downgraded; missed-issue pass as above. Cross-tool peer recommendation: not triggered by the trivial-findings rule (0 CRIT, 0 HIGH); the composer-seat codex pass follows at convergence regardless (the loop's standing cadence).

### Round 18 - 2026-09-16 - practitioner-profile Phase 2 (Tasks 2.1–2.5), in-session `/review-loop` round 2 of cap 3 (confirmation)
- Round status: Closed (no findings) — LOOP CONVERGED at this round
- Source: Claude Code
- Primary review baseline: HEAD `58e7bad`, the same changed-files list as round 17 (15 files); full re-review — the four round-17 fix regions re-read fresh from disk in their surrounding context, every other file unchanged since round 17's full read and re-scanned for the classes round 17 flagged (duplicated predicates, guards looser than their docstrings, copy-pasted state resets, result types that could render the vector). Composer suites after the round-17 fixes: ruff clean, mypy clean over 33 files, pytest 1625 passed.
- Post-Fix Regression Check (regression baseline: the pre-round-17 working tree, i.e. the state the composer verified at 02:17): LOW-001 — the guard's new `model_sha256` comparison; every caller passes a profile whose digest is the embedder's (`ui/models.attribution_inputs` re-checks all three before calling, `speaker_eval.enrolment_inputs` copies the embedder's identity into the synthetic profile, every test profile pairs `""` with a file-less double) — no caller affected. LOW-002 — `words_have_text` / `segment_has_text` delegation: the validator, the pipeline and the test pin all route through the one predicate; `Iterable` was already imported — no signature or shape changed. LOW-003 — `_clear_auto_confirm()`: the three sites (`_populate_generation_controls` before the attributed branch, `change_role` after the un-check, `_reset_generation_state`) reset exactly the flag and the two widgets they reset before; the constructor's own initial `_auto_confirmed = False` stands — no behaviour change (all eleven offscreen auto-confirm tests exercise the three paths). LOW-004 — `field(repr=False)` on a frozen dataclass: keyword construction, equality and hashing unchanged — no caller affected. Result: none.
- Round Classification: no findings to classify.
- Missed-issue pass: re-read `transcription.py:300-380` (the predicate pair and the document validators), `:1136-1156` (the identity guard), `:1244-1282` (the tail: `has_text`, the degenerate branch, the document fields), `ui/transcript.py:296-400` (`_populate_generation_controls`, the two helpers, `change_role`, `_reset_generation_state`), `speaker_eval.py:798-842` (`EnrolmentInputs`, `enrolment_inputs`); result: none. One plan-hygiene note, not a finding: Task 2.2's dated build record names `segment_has_text` as "the ONE definition" — round 17's LOW-002 moved that role to `words_have_text` (recorded in that finding's `/fix notes`); a pointer is added to the task record so the plan does not read as contradicting the code.
- Finding verification: 0 candidates.
- Fix-delta self-check: SKIP — no delta applied this round.
- Summary: files reviewed 15; critical 0; warnings 0 (0 HIGH / 0 MED / 0 LOW); executor judgment items 0; structural quality items 0; round 18 (round 2 of cap 3 — converged: no CRIT/HIGH/MED in either round, round 17's four LOWs applied and confirmed regression-free); no code changed this round, so no suite is owed. Next per the loop's convergence actions: the composer-seat cross-family codex peer pass over the Phase 2 diff (NOT chained by the executor), with Task 2.6's remainder-split question put to the peer explicitly.

### Round 19 - 2026-09-16 - practitioner-profile Phase 2 (Tasks 2.1–2.5), independent cross-family codex peer review (first cross-family code round)

- Round status: Closed (5 of 5 Applied 2026-09-16 by the executor's `/fix` leg after the composer routed all five to fixing under `gates=fix-biased` — PR-HIGH-004 and PR-HIGH-005 at their executor-verified MED; the composer's suite re-run and the codex confirmation round 20 are pending — the round re-opens only if the peer refutes a fix)
- Source: Codex peer-review
- Baseline: `main` / HEAD `58e7bad`; uncommitted Phase 2 working-tree changes.
- Files reviewed: All 15 pinned files: `desktop/src/scribe_desktop/transcription.py`, `speaker_embedding.py`, `speaker_eval.py`, `ui/models.py`, `ui/transcript.py`; `desktop/tests/test_attribution.py` (read in full), `test_speaker_eval.py`, `test_ui_models.py`, `test_ui_screens.py`; `docs/security/data-flow-map.md`, `docs/security/threat-model.md`, `docs/testing/speaker-measurement.md`; `scripts/measure-speakers.py`; `CHANGELOG.md`; the specified sections of `.cursor/plans/plan-practitioner-profile.md`. Supporting reads covered profile loading, `speaker_role`, generation/recovery callers and unchanged batching tests.
- Validation basis: Static inspection only; no files written and no tests or application code executed. Accepted composer verification: ruff clean, mypy strict clean over 33 source files, pytest 1625 passed, zero network. Confirmed Claude executor → GPT/Codex peer family diversity.
- Finding verification: 7 candidates / 2 dropped / 0 downgraded. Dropped: treating the planned additive nullable fields as an old-artifact compatibility failure; treating a readiness object's repr as a demonstrated output leak without an output caller.

#### Confirmed / disputed (rounds 17–18)

- **LOW-001 — confirmed fixed:** The pipeline checks `model_id`, `model_sha256` and `embedding_dim` together at `desktop/src/scribe_desktop/transcription.py:1146`; the parametrized refusal test covers all three.
- **LOW-002 — confirmed fixed:** `words_have_text` owns the predicate at `desktop/src/scribe_desktop/transcription.py:307`; `segment_has_text` delegates and the pipeline uses it at `:1253`.
- **LOW-003 — confirmed fixed:** `_clear_auto_confirm` at `desktop/src/scribe_desktop/ui/transcript.py:360` resets the flag and both widgets; population, manual change and generation-state reset all call it.
- **LOW-004 — confirmed fixed:** Both `EnrolmentInputs` fields use `field(repr=False)` at `desktop/src/scribe_desktop/speaker_eval.py:813`.
- **Round 18 — prior fixes remain intact:** No regression found in those four fixes. The fresh Phase 2 pass found the separate issues below.

#### Task 2.6 assessment

I recommend **option (a)**: when segments match the profile, temporarily label the entire remainder `speaker_2`, understood as the “other” group, until D-S1 has the shared recording evidence. Preserve the specified zero-match fallback. Forced two-means does not establish that a third person exists, so its split adds misleading labels in ordinary two-person consultations; option (c) introduces speaker-count estimation before its deferred measurement. With practitioner attribution correct, this is primarily a **labelling-quality issue**: it fragments the remaining voice and changes the manual heuristic's evidence, but does not itself move those utterances into clinician-owned sections. D4's accepted misattribution risk remains separate. The executor was right to implement D13 as written and record the decision instead of changing the design silently. Amend D13 and its expectations through the scoped plan review before building option (a); the current remainder implementation is not logged as a code finding.

#### PR-HIGH-004 — [HIGH] `desktop/src/scribe_desktop/ui/transcript.py:320` — Generation availability hides the D2 fallback notice

- Triage: Fix-now
- Fix route: premium-only
- Why it matters: Recovery transcription can fall back without telling the clinician that voice attribution was unavailable. A live note-config failure also hides that information. This meets the specified HIGH weighting for silent D2 fallback.
- Current behaviour: The only fallback renderer is inside `_populate_generation_controls`:
  > `readiness = self._attribution_readiness_provider()`  
  > `if readiness.profile_present:`

  But `show_document` at `:274` gates that entire function and its parent:
  > `if self._can_generate:`  
  > `    self._populate_generation_controls(document)`  
  > `self.generate_box.setVisible(self._can_generate)`

  The production recovery caller at `desktop/src/scribe_desktop/ui/main_window.py:245` leaves `can_generate=False`. On the live path, a config error sets `self._can_generate = False` at `ui/transcript.py:345`, hiding an already-populated notice.
- Desired behaviour: Show the degradation status for displayed text-bearing, unattributed transcripts with a present/unusable profile, independently of note-generation availability.
- Pattern to follow: The screen's transcript warnings render outside the generation group. Keep recovery's existing lack of generation controls.
- Pattern siblings: Recovered views (`show_document`, `:274`) and live config-loader failures (`:345`). Searches for all four attribution-reason constants, `attribution_readiness`, and attribution-label visibility found no alternative shipped renderer; `ui/models.py:831` currently reports Whisper/VAD only.
- Invariant: D2 fallback is visible on both transcription entry points; status visibility must not enable Generate or clinician-selection controls.
- Verification: Traced both factories to the production recovery caller and screen. Existing fallback tests exercise `can_generate=True`; the recovered test at `desktop/tests/test_ui_screens.py:2672` uses an attributed document and does not cover degradation. Add offscreen visibility checks for recovered fallback and live config failure, with Generate still unavailable.
- Regression risk: Showing the entire generation group would widen recovery behavior. Separate the status presentation and preserve all generation gates.
- /fix decision: Applied
- /fix notes: `ui/transcript.py` — a new plain-text `attribution_status_label` sits in the MAIN layout between the legend and the generation group; `show_document` calls `_show_attribution_status(document)` before the generation gate: hidden for an attributed document (the group's confirmation line is that case's status) or a transcript with no speech, otherwise the readiness probe's reason or `ATTRIBUTION_DID_NOT_RUN_REASON` when a profile is present — on BOTH entry points, whether or not generation controls exist; the old `elif quotes:` renderer inside `_populate_generation_controls` is removed; `_clear` hides the new label. No Generate gate touched (`_update_controls` unchanged; the recovered view still has no radios and a disabled Generate; a config failure still hides the group and disables Generate). Siblings: the recovered caller (`main_window.py:245`) and the live config-failure path (`transcript.py:345`) — both now covered. Verified by re-read; pinned in `test_ui_screens.py::TestTranscriptAutoConfirm`: the three fallback tests moved to the status label (the confirmation line stays hidden), plus `test_the_recovered_view_still_names_the_fallback` (no group, no radios, Generate disabled, status shown), `test_a_failed_note_config_keeps_the_fallback_visible` (group hidden, Generate disabled, status shown), `test_no_status_on_the_recovered_view_without_a_profile`, `test_no_status_for_a_transcript_without_speech` (probe not consulted), and the reset test asserts the status clears on discard. Suite owed (composer).
- /fix date: 2026-09-16
- /fix applied by: Claude Code

#### PR-HIGH-005 — [HIGH] `desktop/src/scribe_desktop/ui/models.py:897` — Unusable profile blobs can be classified as never enrolled

- Triage: Fix-now
- Fix route: premium-only
- Why it matters: A saved profile truncated to zero bytes silently disables attribution even in the normal live view. The clinician receives neither the unusable-profile explanation nor its remedy.
- Current behaviour:
  > `if not profile_present(root=profile_root):`  
  > `    return AttributionReadiness(profile_present=False, profile=None, reason=None)`

  The first-run helper at `desktop/src/scribe_desktop/practitioner_profile.py:340` implements:
  > `return blob_path.stat().st_size > 0`  
  > `except OSError:`  
  > `    return False`

  Thus zero-length blobs and stat failures bypass `load_profile`. The worker returns `(None, None)` at `ui/models.py:937`, and the screen suppresses the notice because `profile_present` is false.
- Desired behaviour: Distinguish confirmed absence from an existing malformed or unreadable profile. Continue transcription through the fallback while reporting the latter with a structural D2 reason.
- Pattern to follow: `load_profile` at `practitioner_profile.py:292` distinguishes `FileNotFoundError` → `None` from other read failures → `ProfileUnusableError`.
- Pattern siblings: Both pipeline factories and the Transcript-screen probe share this readiness function. Searching `profile_present(` under `desktop/src` found this new readiness consumer and the helper definition only. The helper's D10 first-run semantics need not be changed.
- Invariant: An unusable stored profile must not become an indistinguishable “never enrolled” state.
- Verification: Static trace of an existing zero-byte `voice.enc` through the presence check, worker fallback and UI suppression. Add coverage for zero-byte and unreadable blobs, retaining the quiet manual path for genuinely missing blobs.
- Regression risk: Broadly changing the first-run helper could alter future onboarding behavior. Correct the attribution-readiness classification locally and keep model loading off the GUI thread.
- /fix decision: Applied
- /fix notes: `ui/models.py::attribution_readiness` no longer consults `profile_present` (the import is dropped): presence is `load_profile`'s own verdict — `None` = confirmed absent (no `voice.enc`), `ProfileUnusableError` = present-but-unusable with its structural reason word (`model` → re-enrol line, else the unusable line) — and the model-file stat is checked only for a usable profile; the D10 helper itself is untouched; no model is loaded on the GUI thread. Both factories share the function, so the worker's `(None, None)` fallback now comes with the screen's reason line for these states. Verified by re-read; pinned in `test_ui_models.py::TestAttributionReadiness`: a structural pin that `profile_present` is absent from the module namespace, a zero-byte `voice.enc` with the loader reporting `blob` / `authentication` → present + reason (the model stat never consulted), the real-loader Windows case (an empty blob with no key → `key`), the model-missing line now requires a usable profile, and the loader's `None` is the only confirmed absence. Suite owed (composer). Lint residue (leg c9): the first suite run after this fix found six ruff errors in `test_ui_models.py` only — the new `windows_only` marker had been placed above the module's imports (E402 ×5) and one monkeypatch line ran to 103 characters (E501); the marker now follows the imports as in the file's original layout and the line is wrapped; pytest and mypy were already green (1635 passed).
- /fix date: 2026-09-16
- /fix applied by: Claude Code

#### PR-REG-003 — [MED] `desktop/src/scribe_desktop/speaker_eval.py:1319` — Leave-one-out preparation bypasses per-recording error isolation

- Triage: Fix-now
- Fix route: fix-on-fast
- Why it matters: One invalidly encoded label file can abort the entire measurement run before valid recordings are scored or the report is produced.
- Current behaviour: Pool preparation reads:
  > `track = parse_audacity_labels(labels_path.read_text(encoding="utf-8-sig"))`

  Its handler at `:1321` catches only:
  > `except (RecordingRefusedError, OSError):`

  `main` calls `pool = _leave_one_out_pool(pairs)` at `:1405`, outside the per-recording exception boundary. A `UnicodeDecodeError` therefore escapes when two or more pairs trigger leave-one-out preparation.
- Desired behaviour: Exclude unreadable inputs from the enrolment pool and preserve the existing per-recording reporting path: report the failure once, continue valid recordings, print their report and return nonzero for errors.
- Pattern to follow: The broad handler at `:1438` reports unexpected exceptions by type only and preserves completed results.
- Pattern siblings: `clinician_pcm` at `:1323` also runs outside the pool's handler; per-recording `enrolment_inputs` at `:1419` precedes the broad handler and catches only `EnrolmentError`. These new preparation boundaries need the same error-isolation policy. The dedicated enrolment-WAV branch at `:1395` has separate explicit handling.
- Invariant: A failing recording must not discard other results; unaudited exception messages must not enter output.
- Verification: Re-read the new preparation and existing `evaluate_recording` read at `:1115`. Previously that read occurred under the per-recording guard. Add a regression case with one undecodable label track and one valid pair, asserting continuation, type-only reporting and nonzero exit.
- Regression risk: Catching failures without preserving their eventual error accounting could produce a misleading successful exit. Do not broaden handlers to print arbitrary exception messages.
- /fix decision: Applied
- /fix notes: `speaker_eval.py` — `_leave_one_out_pool` skips a pair on ANY `Exception` (the per-recording evaluation reports that pair once, type-only, through its existing broad handler); the per-recording `enrolment_inputs` step gains an `except Exception` branch that counts an error, prints `[error] <name>: enrolled condition failed - <Type>` (type only — the message is unaudited for content) and measures the recording on the legacy conditions; `clinician_pcm` is pure slicing over already-read inputs and cannot raise for them. Exit status stays truthful (non-zero). Siblings swept: the pool read (`:1319`), the per-recording enrolment (`:1419`); the dedicated `--enrolment` branch keeps its explicit handling. Verified by re-read; pinned in `test_speaker_eval.py::TestMainEnrolled`: `test_an_undecodable_label_track_does_not_abort_the_leave_one_out_run` (a non-UTF-8 track: the run continues, `[error] b.wav: UnicodeDecodeError` type-only, the valid recording scored, exit 1) and `test_an_unexpected_enrolment_failure_is_reported_by_type_and_the_run_continues` (an exploding embedder: both recordings still measured, the sentinel text absent, exit 1). Suite owed (composer).
- /fix date: 2026-09-16
- /fix applied by: Claude Code

#### PR-LOW-025 — [LOW] `desktop/src/scribe_desktop/speaker_eval.py:668` — One-cluster output does not prove every segment matched

- Triage: Fix-now
- Fix route: fix-on-fast
- Why it matters: The documentation and generated report misdescribe what the measurement establishes, potentially confusing threshold failures with degenerate clustering.
- Current behaviour:
  > `all ``speaker_1`` there means every`  
  > `segment matched the profile`

  The report at `:1170` similarly calls it an “all-matched output”. However, zero matches still reach `_cluster_embeddings` at `transcription.py:886`; degenerate features return all `speaker_1` at `:713`. The preserved pipeline degenerate branch at `:1254` also produces one cluster without establishing matches.
- Desired behaviour: Describe enrolled one-cluster outputs as scorable regardless of whether they came from all matches or degenerate fallback. Preserve the current metrics.
- Pattern to follow: `_score_condition` at `speaker_eval.py:741` correctly scores enrolled outputs without asserting why they contain one cluster.
- Pattern siblings: `speaker_eval.py:74`, `:668`, `:1169`; `docs/testing/speaker-measurement.md:26`; `CHANGELOG.md:8`; Task 2.4's explanatory shorthand at `.cursor/plans/plan-practitioner-profile.md:580`. Searches covered “all-matched”, “every segment matched” and related spellings. The explicitly all-matched fixture at `desktop/tests/test_speaker_eval.py:1673` can retain its fixture-specific description.
- Invariant: Report prose must not infer threshold crossings from cluster labels alone.
- Verification: Read the zero-match and degenerate branches and the unconditional enrolled scoring predicate. This is a wording correction; the false-positive case is already measured.
- Regression risk: None if confined to prose. Do not restore the legacy merged exclusion for enrolled outputs.
- /fix decision: Applied
- /fix notes: prose only, metrics untouched — the five sibling sites now say a one-cluster enrolled output is scored whatever produced it (every segment matched, or a degenerate clustering after none did; the labels alone do not say which, the `Auto-confirm` verdict and `Similarity` do): `speaker_eval.py` module docstring (`:74`), `ConditionResult` docstring (`:668`), the report header (`:1169`); `docs/testing/speaker-measurement.md` (the enrolled-condition section); `CHANGELOG.md` (the Phase 2 entry); and the Task 2.4 build record in this plan. The all-matched fixture test keeps its fixture-specific description. Verified by re-read (grep for "all-matched" / "every segment matched" over the repo: only the fixture test and the plan's original D-text remain, as the peer allowed). Suite owed (composer) for the two report-header pins.
- /fix date: 2026-09-16
- /fix applied by: Claude Code

#### PR-LOW-026 — [LOW] `docs/security/threat-model.md:404` — Attribution documentation states an unconditional 30-second window cap

- Triage: Fix-now
- Fix route: fix-on-fast
- Why it matters: The new security prose claims a tighter plaintext bound than the preserved implementation provides.
- Current behaviour:
  > `slice with the speaker model INSIDE the same ≤30 s window its spectral`

  But `pack_transcription_windows` at `desktop/src/scribe_desktop/transcription.py:525` explicitly retains an oversized lone segment:
  > `a single segment longer than the budget`  
  > `becomes its own (oversized) window`

  Attribution embeds that same segment slice.
- Desired behaviour: State the unchanged bound accurately: packed windows target at most 30 seconds; a lone longer VAD segment occupies its own oversized window. Attribution adds no whole-session accumulation.
- Pattern to follow: The qualified pipeline explanation at `transcription.py:1171` and provider-call comment at `:1020`.
- Pattern siblings: New claims at `docs/security/data-flow-map.md:95` and `CHANGELOG.md:8`; existing equivalent shorthand at `data-flow-map.md:86` and `transcription.py:961`. Searches covered `≤30`, `≤ 30`, `<=30` and `<= 30`. The configured budget at `transcription.py:189` and explicitly qualified passages at `:1020`/`:1172` are not defects.
- Invariant: Security documentation describes the enforced bound, including its existing oversized-segment exception.
- Verification: Read window packing and the unchanged tests at `desktop/tests/test_transcription.py:320` and `:888`, which explicitly cover oversized windows. No new plaintext accumulation was found.
- Regression risk: None for documentation corrections. Do not change segmentation or buffering to satisfy the inaccurate wording.
- /fix decision: Applied
- /fix notes: docs only — `docs/security/threat-model.md` surface 6 now states the enforced bound with its exception (windows packed to at most 30 s; a lone VAD segment longer than the budget is its own oversized window, exactly as before attribution; the bound the batching AND oversized-window tests pin); `docs/security/data-flow-map.md` flow 7's new sentence carries the same qualification and the pre-existing "packed ≤30 s windows" shorthand at `:86` is qualified in the same pass; `CHANGELOG.md`'s Phase 2 entry likewise. No segmentation or buffering changed. Verified by re-read against `pack_transcription_windows` (`transcription.py:525-526`) and the pipeline comment (`:1171-1173`). No suite owed for this finding.
- /fix date: 2026-09-16
- /fix applied by: Claude Code

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-16)
- PR-HIGH-004: materiality=behavioral; verified severity=med; peer severity=high (preserved); evidence: `ui/transcript.py:274-277` gates `_populate_generation_controls` (the ONLY renderer of the D2 line, `:320-325`) on `can_generate`, and `:345` sets `_can_generate = False` on a config error so `generate_box.setVisible(False)` at `:277` hides an already-populated line — the recovered caller (`ui/main_window.py:245`) never passes `can_generate`, so a fallback on the recovery path (which DOES apply the profile, `ui/models.py:1009`) shows nothing; scope: yes (Task 2.3 "status line for the fallback cases (D2)"); production-impacting: no; recommendation: Fix-now — render the status line outside the generation group, driven by the document plus the readiness probe, on both entry points, with every Generate gate untouched. Downgrade evidence (HIGH → MED): in BOTH hidden cases no note can be produced from that view (the recovered view has no generation controls by the plan's design, and a config failure disables Generate), so the practitioner cannot "record without knowing attribution is off"; on the one path that produces a note — a live session with a loadable config — the line IS shown (pinned by three offscreen tests); the consequence is a delayed notice (the next live consultation shows it), not a silent degradation of a clinical record. A real D2 visibility gap on two paths, not a Critical-Constraint breach.
- PR-HIGH-005: materiality=behavioral; verified severity=med; peer severity=high (preserved); evidence: `ui/models.py:897` short-circuits on `profile_present` (`practitioner_profile.py:340` — `st_size > 0`, any `OSError` → False), so a zero-length `voice.enc` or a blob whose stat is refused reads as "never enrolled" (`profile_present=False`, no reason) although `load_profile` (`:290-295`) would classify both as unusable (`authentication` / `blob`); the worker then returns `(None, None)` and the Transcript screen shows the manual radios with NO line; scope: yes (Task 2.3's D2 status line; Task 2.1's factory fallback); production-impacting: no; recommendation: Fix-now — decide presence from `load_profile`'s own distinction (`None` = confirmed absent, `ProfileUnusableError` = present-but-unusable), not from the D10 first-run stat, keeping `profile_present` itself unchanged. Downgrade evidence (HIGH → MED): the state needs an external fault the profile's own custody never produces (`save_profile` writes through temp+fsync+replace, so a zero-byte blob or a stat refusal comes from truncation or a permission/lock change outside the app); the fallback lands on the pre-enrolment manual path (the same radios and explicit confirmation the app shipped with — no clinical content is attributed wrongly); and the practitioner sees the absence of the confirmation line on the very next live transcript and, from Phase 3, a Practitioner tab that reports the profile state. The peer's invariant holds and the fix is small and structural, but the consequence is a missing explanation, not a wrong note: a lesser defect against D2's "never silent", not a Critical-Constraint breach.
- PR-REG-003: materiality=behavioral; verified severity=med; peer severity=med (preserved); evidence: `speaker_eval.py:1319-1321` catches `(RecordingRefusedError, OSError)` around `read_text(encoding="utf-8-sig")`, but an invalidly encoded label file raises `UnicodeDecodeError` (a `ValueError`, not an `OSError`), and `main` calls the pool builder at `:1405` OUTSIDE the per-recording `try` whose broad handler (`:1438`) reports by type only — so with two or more pairs one bad label file aborts the run before any recording is scored; the same read inside `evaluate_recording` (`:1115`) sits under that guard; likewise the per-recording `enrolment_inputs` call (`:1419`) catches only `EnrolmentError`, so an unexpected exception there (an embedder failure on the pool) escapes the same way; scope: yes (Task 2.4's leave-one-out fallback); production-impacting: no; recommendation: Fix-now — the pool builder skips any `Exception` (the per-recording path reports that pair once, type-only), and the per-recording enrolment step gains the same type-only isolation with error accounting so the exit status stays non-zero; add the undecodable-track regression case the peer names.
- PR-LOW-025: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: `speaker_eval.py:668` ("all `speaker_1` there means every segment matched") and the report header (`:1170`) overstate — zero matches with degenerate features (`_cluster_embeddings`, `transcription.py:713`) and the pipeline's degenerate branch (`:1254`) also yield one `speaker_1` cluster without any match; scope: yes; production-impacting: no; recommendation: Fix-now — reword to "one-cluster enrolled outputs are scored whatever produced them (all matched, or a degenerate clustering)" at the five sibling sites the peer enumerated (`speaker_eval.py:74`, `:668`, `:1169`; `docs/testing/speaker-measurement.md:26`; `CHANGELOG.md:8`; the Task 2.4 wording in this plan), metrics unchanged.
- PR-LOW-026: materiality=docs-only; verified severity=low; peer severity=low (preserved); evidence: `docs/security/threat-model.md:404` claims "INSIDE the same ≤30 s window", but `pack_transcription_windows` (`transcription.py:525-526`) keeps a lone VAD segment longer than the budget as its own oversized window and attribution embeds that slice; the pipeline's own comment (`:1171-1173`) states the bound with that exception; scope: yes (Task 2.5); production-impacting: no; recommendation: Fix-now — state the enforced bound with its oversized-lone-segment exception at the new claims (`threat-model.md:404`, `data-flow-map.md:95`, `CHANGELOG.md:8`) and qualify the pre-existing shorthand at `data-flow-map.md:86` in the same pass since it is the same sentence class; no code change.

Fix-delta self-check: PASS — re-read 9 applied hunks across 3 source files (`ui/models.py`, `ui/transcript.py`, `speaker_eval.py`) and the 4 doc/changelog sites, plus their 9 test pins; no neighbouring exit path touched (the config-failure early return and the `_clear` path re-traced with the new status label), no drive-by edit; one over-long print line wrapped in the same hunk.

PEER-ROUND-19 RESULT: 5 findings (CRIT 0 / HIGH 2 / MED 1 / LOW 2).

### Round 20 - 2026-09-16 - practitioner-profile Phase 2 (Tasks 2.1–2.5), independent cross-family codex peer review (confirmation round after round 19)

- Round status: Closed (1 of 1 Applied 2026-09-16 by the executor's /fix leg after the composer routed it to fixing under gates=fix-biased; the composer's suite re-run and the codex confirmation round 21 are pending — the round re-opens only if the peer refutes the fix)
- Source: Codex peer-review
- Baseline: `main` / HEAD `58e7bada7b3b48bd729238773541a9f4bb4f11ef`; uncommitted Phase 2 working-tree changes.
- Files reviewed: The 15 pinned files: `desktop/src/scribe_desktop/{transcription,speaker_embedding,speaker_eval}.py`, `desktop/src/scribe_desktop/ui/{models,transcript}.py`, `desktop/tests/{test_attribution,test_speaker_eval,test_ui_models,test_ui_screens}.py`, `docs/security/{data-flow-map,threat-model}.md`, `docs/testing/speaker-measurement.md`, `scripts/measure-speakers.py`, `CHANGELOG.md`, and the specified sections of `.cursor/plans/plan-practitioner-profile.md`, including the full Round 19 block and its verification and `/fix` fields. Supporting inspection covered profile loading and generation/recovery callers. Git status and the HEAD diff listed no changes outside the pinned surface.
- Validation basis: Static inspection only; no files written, tests run, application code executed, or payloads authored. Accepted composer verification: ruff clean; mypy strict clean over 33 source files; pytest 1635 passed, zero network. Claude executor → GPT/Codex independent confirmation. No new whole-session PCM accumulation, direct document-field route into `compose_draft`, or content-bearing output was identified. Generate retains its existing gates.
- Finding verification: 1 candidate / 0 dropped / 0 downgraded. The remaining failure is a concrete unguarded preparation path, recorded below as the outstanding part of PR-REG-003 rather than counted twice.

#### Confirmed / disputed (round 19 fixes)

- **PR-HIGH-004 — fix confirmed complete:** `desktop/src/scribe_desktop/ui/transcript.py:248` places the status label outside the generation group; `:287` renders it before the generation gate; `:294` handles text-bearing unattributed documents using readiness. Recovery and config-failure paths preserve visibility without enabling generation. Offscreen coverage at `desktop/tests/test_ui_screens.py:2640` onward covers the fallback reasons, recovery, config failure, quiet absent-profile/no-speech cases and reset.
- **PR-HIGH-005 — fix confirmed complete:** `desktop/src/scribe_desktop/ui/models.py:903` reads the profile directly; `:906` classifies `ProfileUnusableError` as present with a structural remedy, and only the loader’s `None` produces confirmed absence at `:913`. Both factories use the same resolver at `:982` and `:1013`; no first-run stat decides attribution presence.
- **PR-REG-003 — fix partial:** `desktop/src/scribe_desktop/speaker_eval.py:1325` now guards pool reads/parsing with `Exception`, and unexpected per-recording enrolment failures receive type-only reporting and error accounting. However, `clinician_pcm` remains outside that guard at `:1330`; accepted finite timestamps can make its sample-index conversion overflow at `:859`, aborting pool preparation before the batch guard. See PR-REG-004.
- **PR-LOW-025 — fix confirmed complete:** The enrolled-condition descriptions at `desktop/src/scribe_desktop/speaker_eval.py:74`, `:668`, and the report header explain that a one-cluster output remains scorable without proving every segment matched. The sibling wording in `docs/testing/speaker-measurement.md:26`, `CHANGELOG.md:8`, and the plan’s Task 2.4 record agrees; scoring semantics remain unchanged.
- **PR-LOW-026 — fix confirmed complete:** `docs/security/threat-model.md:404`, `docs/security/data-flow-map.md:86` and `:95`, and `CHANGELOG.md:8` qualify the packing budget with the oversized lone-VAD-segment exception. Attribution continues to operate inside the existing window loop at `desktop/src/scribe_desktop/transcription.py:1172`; buffering and segmentation were not changed to satisfy the prose.

#### PR-REG-004 — [MED] `desktop/src/scribe_desktop/speaker_eval.py:1330` — Clinician-span extraction still escapes leave-one-out isolation

- Severity: MED
- Triage: Fix-now
- Fix route: fix-on-fast
- Why it matters: One malformed label track can still abort the entire leave-one-out run before valid recordings are evaluated or their report is printed. This is the remaining preparation boundary from PR-REG-003.
- Current behaviour: The broadened pool handler at `:1328` catches:
  > `except Exception:`

  But the subsequent `clinician_pcm` call at `:1330` remains outside that handler. Pool construction is itself outside the per-recording guard at `:1412`:
  > `pool = _leave_one_out_pool(pairs)`

  The label parser’s timestamp checks at `:254` and `:260` permit finite, nonnegative values without a recording-duration upper bound. `clinician_pcm` converts the product of an end timestamp and `SAMPLE_RATE` to an integer before clipping it at `:859`. A sufficiently large finite timestamp makes that product infinite, so conversion raises `OverflowError`. The Round 19 `/fix notes` claim that this extraction cannot raise for already-read inputs is therefore incorrect.
- Desired behaviour: Keep every input-dependent step of preparing one pool entry inside the per-pair exception boundary, including clinician-span extraction. Preserve the normal per-recording path that reports the offending recording once, prints only the exception type for unexpected failures, continues other recordings, and returns nonzero.
- Pattern to follow: The existing broad per-recording evaluation handler and the newly isolated `enrolment_inputs` step: failures affect the relevant recording/condition while completed results remain reportable.
- Pattern siblings: Timestamp-to-sample conversions within `clinician_pcm` at `:858`–`:859`; its unguarded pool use at `:1330`; the pool-builder invocation before the batch guard at `:1412`. The read/parse boundary at `:1325` and per-recording enrolment boundary are the already-corrected siblings.
- Invariant: A failing recording must not discard other results; unexpected exception messages must not enter output.
- Verification: Static trace from accepted finite label timestamps through multiplication, integer conversion and the uncovered call boundary. No payload was authored or executed. The new undecodable-track test exercises the guarded read, while the unexpected-enrolment test exercises the later guard; neither covers extraction failing between those boundaries.
- Regression risk: Merely suppressing extraction failures could conceal a failed condition or produce a successful exit. Preserve error accounting and single reporting through the per-recording path. Add a focused extraction-failure regression check when the executor applies the fix.
- /fix decision: Applied — the extraction now runs inside the per-pair boundary and an extraction-only failure is reported once, by type, with error accounting.
- /fix notes: `speaker_eval.py::_leave_one_out_pool` now returns `(pool, failures)`: the read/parse `try` is unchanged (a pair that fails there is skipped silently because the per-recording evaluation re-reads the same inputs and reports it by type — the round-19 test pins that), and `clinician_pcm` runs in its own `try` whose failure is recorded as WAV name → exception type name; `main` prints each such entry once as `[error] <wav>: enrolled pool preparation failed - <Type>` and increments `errors` (after `errors = 0`, before the loop), so the exit stays non-zero and no message text reaches stdout. The parser's contract is untouched (spans are data, no duration bound). Siblings: `:858`/`:859` are the same conversion and sit inside the same new boundary; the read/parse boundary and the per-recording enrolment boundary were already isolated in round 19. Verified by re-read; pinned by `test_speaker_eval.py::TestMainEnrolled::test_an_oversized_label_timestamp_does_not_abort_the_leave_one_out_run` (a track with `end = 1e305`: exit 1, the type-only error line, "infinity" absent, both recordings still measured, the offending recording enrolled from the other's spans while the other gets no pool). Suite owed (composer).
- /fix date: 2026-09-16
- /fix applied by: Claude Code

PEER-ROUND-20 RESULT: 1 findings (CRIT 0 / HIGH 0 / MED 1 / LOW 0)

#### LEG 1 verified tuples (executor `claude-fable-5-1`, 2026-09-16)
- PR-REG-004: materiality=behavioral; verified severity=med; peer severity=med (preserved); evidence: confirmed end to end — `parse_audacity_labels` admits any finite non-negative pair (`speaker_eval.py:254`, `:260`: `float("1e305")` is finite, ≥ 0 and ≥ start), `clinician_pcm` then computes `int(span.end_seconds * SAMPLE_RATE)` at `:859` BEFORE the `min(..., len(pcm))` clip — `1e305 * 16000` overflows to `inf` (Python float multiplication raises nothing) and `int(inf)` raises `OverflowError` ("cannot convert float infinity to integer"; `:858` has the same conversion for `start`) — and that call sits at `:1330`, outside the pool builder's own `try` (`:1325-1329`) and outside `main`'s per-recording handler (the pool is built at `:1412`, the guarded loop starts at `:1421`), so the exception propagates out of `main` as a traceback before any recording is scored or the report printed; the per-recording path itself would NOT trip on such a track (`align_segments` compares floats only), so the label file is harmless everywhere except this new preparation step — the round-19 `/fix notes` claim that extraction "cannot raise for already-read inputs" was wrong; scope: yes (Task 2.4's leave-one-out fallback, the surface PR-REG-003 already covered); production-impacting: no; recommendation: Fix-now — move the extraction inside the per-pair boundary, and because an extraction-only failure is NOT re-hit by the evaluation (unlike a read/parse failure, which the evaluation reports once already), the pool builder must itself report that pair once, type-only, and count it towards the non-zero exit — return the failures to `main` rather than swallow them, so "reported once" holds for both failure classes; add the oversized-timestamp regression case the peer names (a label track with `end = 1e305`: run continues, `[error] <name>: … OverflowError` type-only, the other recording scored, exit 1). No change to the parser's contract (spans are data, no duration bound) is needed for this. Final disposition (leg 2): Applied.

Fix-delta self-check: PASS — re-read the 3 applied hunks in `speaker_eval.py` (the pool builder's two boundaries and its new return, `main`'s tuple unpack and the failure report placed after `errors = 0`) and the 1 test pin; the read/parse skip path and the per-recording enrolment path re-traced unchanged; no drive-by edit.

### Round 21 - 2026-09-16 - practitioner-profile Phase 2 (Tasks 2.1–2.5), independent cross-family codex peer review (confirmation round after round 20)

- Round status: Closed
- No new findings — converged
- Source: Codex peer-review
- Baseline: `main` / HEAD `58e7bada7b3b48bd729238773541a9f4bb4f11ef`; uncommitted Phase 2 working-tree changes.
- Files reviewed: The 15 pinned files: `desktop/src/scribe_desktop/{transcription,speaker_embedding,speaker_eval}.py`, `desktop/src/scribe_desktop/ui/{models,transcript}.py`, `desktop/tests/{test_attribution,test_speaker_eval,test_ui_models,test_ui_screens}.py`, `docs/security/{data-flow-map,threat-model}.md`, `docs/testing/speaker-measurement.md`, `scripts/measure-speakers.py`, `CHANGELOG.md`, and the specified context in `.cursor/plans/plan-practitioner-profile.md`, including Round 20 in full, its verified tuples and `/fix` fields. Read `test_attribution.py` in full. Supporting inspection covered enrolment and generation callers. Git status and the HEAD diff showed no changes outside the pinned surface.
- Validation basis: Static inspection only; no files written, tests run, application code executed, or payloads authored. Accepted composer verification: ruff clean; mypy strict clean over 33 source files; pytest 1636 passed, zero network. Independent GPT/Codex confirmation of the Claude-family fix.
- Finding verification: 0 candidates / 0 dropped / 0 downgraded.

#### Confirmed / disputed (round 20 fix)

- **PR-REG-004 — fix confirmed complete:** `desktop/src/scribe_desktop/speaker_eval.py:1336` guards reading/parsing, and `:1341` separately guards extraction, including both sample-index conversions at `:858` and `:859`. The extraction handler records only `"failures[wav_path.name] = type(exc).__name__"` at `:1344`. The sole caller unpacks both results at `:1427`; `main` reports each extraction failure once and increments `errors` at `:1440`, while continuing the recording loop. The final `"return 0 if results and not errors else 1"` at `:1489` preserves the nonzero exit. Read/parse failures remain deferred to per-recording evaluation, avoiding duplicate pool reporting. `desktop/tests/test_speaker_eval.py:1976` exercises the real parser and extraction with an oversized finite timestamp; its evaluation stub does not manufacture the extraction error. Assertions at `:1991`–`:1998` cover nonzero exit, type-only reporting, both report rows and the remaining usable pool.

#### Scope and invariant checks

- **Batch isolation:** Traced preparation, enrolment, evaluation, teardown and report aggregation. No additional concrete input-dependent batch-abort or error-accounting defect was identified. Successful pool entries retain their existing extraction semantics.
- **Conversion siblings:** The label-controlled conversions are both inside the corrected boundary. Other timestamp-to-sample conversions in `transcription.py` consume pipeline-generated segment/window times, rather than Audacity timestamps; harness evaluation remains guarded.
- **Plaintext bound:** Attribution remains inside the existing window loop at `desktop/src/scribe_desktop/transcription.py:1239`, retaining a similarity scalar per segment. No new whole-session PCM accumulation was introduced into the production pipeline.
- **D1 and Generate:** `desktop/src/scribe_desktop/ui/transcript.py:538` reads the checked radio; the generator passes that selection to `compose_draft` at `desktop/src/scribe_desktop/ui/models.py:796`. Template, config, recovery and lease gates remain intact.
- **Text-free output:** The fix retains exception type names only. No new path emitting vectors, PCM or transcript text into logs, status, exceptions or reports was identified.

PEER-ROUND-21 RESULT: 0 findings (CRIT 0 / HIGH 0 / MED 0 / LOW 0).

