# Shipping-gate run config (rubric v1, 2026-09-05)

The clinician config used for the Task 9.1 shipping-gate run: three prefill
templates (knee, shoulder, lower back — one seed sentence each, per the
ratified composition) and one autofill rule (trigger phrase "ice pack").
Boilerplate only — no patient data. The seed and expansion sentences are
offered as PROPOSALS the clinician confirms or declines; nothing here enters a
note on its own.

## Install (practitioner, from Explorer or a normal terminal — never an agent shell)

1. Create the folder `%LOCALAPPDATA%\ClinikoScribe\config` if it does not exist
   (paste `%LOCALAPPDATA%\ClinikoScribe` into the Explorer address bar, then
   New folder → `config`).
2. Copy `autofill_rules.json` and `prefill_templates.json` from this folder
   into it. `template_profiles.json` is NOT copied — the shipped default
   (Template A, both clinics) is used when the file is absent.
3. Launch the app (Explorer double-click on `.venv\Scripts\scribe-app.exe`, or a
   persistent terminal), finish a session, and check the Transcript screen's
   "Prefill region" list offers Knee, Shoulder and Lower back. A malformed file
   fails closed: Generate is unavailable and the status line names the file.

## Editing

One clinical claim per sentence. Commas, brackets, slashes and percent signs
are fine; a colon or semicolon may only end a sentence (the loader's
single-claim shape check refuses it mid-sentence). To keep a deliberately
longer sentence as one claim, write the entry as
`{"assertion_text": "...", "single_claim": true}` instead of a bare string.
Validate a change without launching the app:

```bash
.venv\Scripts\python.exe -c "from pathlib import Path; from scribe_desktop.note_config import load_note_config; c = load_note_config(Path(r'docs/testing/shipping-gate-config')); print(len(c.autofill_rules), 'rules,', len(c.prefill_templates), 'prefills')"
```
