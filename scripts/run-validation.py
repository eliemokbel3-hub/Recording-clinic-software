"""Validation harness launcher (pilot plan Phase 2, Task 2.7).

Thin by design: ``ruff`` and ``mypy`` run inside ``desktop/``, so all logic
lives in ``scribe_desktop.validation`` and this file only dispatches
(pinned by ``desktop/tests/test_validation_harness.py``).

Run it YOURSELF from a normal terminal on the developer build (never an agent
shell - those cannot see the user's model folder, docs/lessons.md), with the
installed app closed and the models downloaded by ``scripts/setup-models.py``:

    .venv\\Scripts\\python.exe scripts\\run-validation.py <set-folder> --config <folder> --rule validation\\rules\\option-a-proposed.json

``<set-folder>`` holds ``<id>.json`` + ``<id>.wav`` + ``<id>.txt`` per
encounter (``scripts\\build-validation-set.py`` makes the synthetic ones).
``--config`` is an explicit note-config folder, never the app's own;
``validation\\config`` is the one the synthetic scripts are written against.
The text-free report on stdout is pass or fail against the rule. See
``docs/testing/validation-harness.md``.
"""

from __future__ import annotations

import sys

from scribe_desktop.validation import main

if __name__ == "__main__":
    sys.exit(main())
