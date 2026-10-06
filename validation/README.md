# Validation set inputs (pilot plan Phase 2)

- `scripts/` — 40 invented synthetic encounter scripts (`<id>.json`). `scripts\build-validation-set.py` speaks them into a set folder; keep that folder outside this repository.
- `config/` — the note config the scripts are written against: the shipped defaults plus three autofill rules that `syn-07`, `syn-08` and `syn-09` trigger on purpose. Pass it as `--config validation\config`.
- `rules/` — pass-rule files. `option-a-proposed.json` is decision 3.5's option (a); the ratified rule v1 is recorded in `docs/testing/validation-harness.md`.

Invented content only: never a real patient, consultation or recording. How to run and what the numbers mean: `docs/testing/validation-harness.md`.
