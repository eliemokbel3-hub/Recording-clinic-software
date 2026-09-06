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
