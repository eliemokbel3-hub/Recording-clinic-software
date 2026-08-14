# Design system — desktop app

The desktop companion's UI conventions, as built in Phase 2. Each cue points at the
code that owns it; the code wins on any disagreement. Chrome-side UI (Phase 5) should
follow the same interaction posture even though the toolkit differs.

Suggested sections as this grows: surfaces & layout · dialogs · menus · forms & inputs ·
view patterns · tokens · microcopy.

## Surfaces & layout
- One window, tabbed: Microphone / Session / Recovery / Transcript / **Note** / Status —
  `desktop/src/scribe_desktop/ui/main_window.py`. No secondary windows; no new UI
  framework (PySide6 only, extending the Phase-1 status panel rather than replacing it).
- The **Note review tab** shows the generated note and the full uncertainty-marked
  transcript SIDE BY SIDE through the whole review, until copy or Complete —
  `ui/note.py`. This is presentational coverage of anything cue routing dropped: the
  clinician can always see a low-confidence phrase the note omitted, which no automated
  check reaches.
- GUI-free view logic lives in `ui/models.py` (state→controls maps, list rendering,
  transcript rendering, readiness reports). Widgets stay thin so the logic is testable
  offscreen — every screen has offscreen tests, no real audio or ML in CI.
- Long work never blocks the UI thread: `ui/tasks.py` `TaskThread` with indeterminate
  progress (transcription, benchmark runs).

## Interaction posture
- **State drives enablement.** Controls are enabled/disabled from the session state
  machine, not from ad-hoc flags — `ui/models.py` state→controls map, applied in
  `ui/session_screen.py`. A control that would be invalid in the current state is
  disabled, not merely error-handling a bad click.
- **Refuse destructive actions during live work, with a reason.** Closing the window is
  refused while recording (`ui/main_window.py` `closeEvent`); the benchmark is refused
  while a session is active (`ui/microphone.py`). The failure being prevented is lost
  consultation audio, so refusal beats a confirmation dialog.
- **Never auto-resume recording.** Recovery offers resume-processing or discard only —
  `ui/recovery.py`. Restarting a microphone without the clinician's say-so is out of
  bounds.
- **Say what to do, not just what failed.** A dead input stream surfaces the actual
  remedy ("check Windows Settings > Privacy & security > Microphone"), and a silent-but-
  open stream surfaces a distinct "No signal" hint — `ui/microphone.py`. Latch such
  messages; do not hammer a retry loop.
- **Self-refreshing status.** Readiness panels poll rather than rendering once at
  construction (model report every 5 s, level meter at 100 ms, failure watcher at 500 ms).
  A panel that reports state must not be able to show a stale truth indefinitely — this
  cost a live debugging session when it did.
- **Confirmation shows exactly what will be inserted.** Each note proposal renders the
  exact insertable text, one bullet per assertion (never assembled prose), and the digest
  of what will be written is read from the RENDERED widget's text — never copied from the
  proposal — so a rendering bug is refusable at write time rather than silently saved
  (`ui/note.py`; the `_rendered_excerpt` / `shown_text_digest` path).
- **Group and summarise warnings; keep blocking distinct from advisory.** Review warnings
  are grouped by code and summarised, and blocking errors are presented distinctly from
  review warnings with each blocking state naming the action it blocks and how to clear it
  — warning fatigue is a real failure mode (`ui/models.py` `summarise_warnings` /
  `WARNING_COPY` / `complete_block_reason`).
- **Guard live custody with a controller lease, not a button flag.** A destructive or
  view-swapping action during a live generation/review is refused through the controller-
  owned `GenerationLease` (`session.py`), which spans the whole compose→review→write — a
  button-enabled flag cannot prevent a worker/GUI interleaving. Always offer a
  non-destructive escape (Cancel review and regenerate — keeps the queued transcript and
  key) alongside any destructive one (Delete note and complete without one).

## Clinical-content rules (non-negotiable)
- Transcript text is display-only (`NoTextInteraction`) and cleared on close —
  `ui/transcript.py`. It is never logged, never written outside the encrypted store.
- The generated NOTE is the copyable surface — but ONLY after the Task-9.1 shipping gate
  passes AND the note is fully ratified (no pending proposal, no blocking error, saved,
  no unacknowledged review warning). Until both hold, the note panel is `NoTextInteraction`
  and Copy is disabled; the guard lives in one predicate applied to both the button and
  the text-selection flags and re-checked at click time — `ui/note.py` `_copy_ready()`
  (`COPY_TO_CLINIKO_ENABLED` in `ui/models.py` is the 9.1 flag). The transcript panel is
  never copyable. Never widen copy to only-the-flag; disabling the button alone is
  insufficient because selectable text keeps native copy shortcuts.
- Provenance is visibly distinguished in the note — transcript-derived vs
  clinician-authored vs autofill/prefill — so the clinician can see the source of every
  line at a glance (`ui/note.py` / `ui/models.py` rendering).
- Uncertainty is visible, not hidden: low-confidence words, numbers, and names render as
  `[word?]` — `ui/models.py`. The clinician must be able to see what the model was unsure
  about at a glance.
- Speaker labels render per segment alongside timestamps. Today two speakers only; see
  the retained follow-up in `AGENTS.md`.

## Microcopy
- Plain clinical English, no jargon, no exclamation marks. Name the artefact the user
  cares about ("recording did not finish cleanly; the tail may be missing") rather than
  the internal cause (a missing store footer).
- Destructive actions are named for what they do — Complete and Discard, not OK/Cancel.
