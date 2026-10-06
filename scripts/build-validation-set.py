"""Synthetic validation-set builder launcher (pilot plan Phase 2, Tasks 2.5 / 2.7).

Thin by design: ``ruff`` and ``mypy`` run inside ``desktop/``, so all logic
lives in ``scribe_desktop.validation_set`` and this file only dispatches
(pinned by ``desktop/tests/test_validation_set.py``).

Run it YOURSELF from a normal terminal on the developer build, with at least
two Windows voices installed (Settings, Time & language, Speech):

    .venv\\Scripts\\python.exe scripts\\build-validation-set.py validation\\scripts <set-folder>

Each synthetic script becomes ``<id>.wav`` (16 kHz mono), ``<id>.txt`` (its
label track) and a copy of ``<id>.json`` in ``<set-folder>``; role-play
scripts are skipped. ``--only <id> ...`` builds a subset. Keep the set folder
outside the repository. See ``docs/testing/validation-harness.md``.
"""

from __future__ import annotations

import sys

from scribe_desktop.validation_set import main

if __name__ == "__main__":
    sys.exit(main())
