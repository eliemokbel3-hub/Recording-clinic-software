"""Task 2.3 speaker-measurement harness launcher (Phase 3A Task 2.3a).

Thin by design: ``ruff`` and ``mypy`` run inside ``desktop/``, so all logic
lives in ``scribe_desktop.speaker_eval`` and this file only dispatches.

Run it YOURSELF from a normal terminal (never an agent shell - those cannot
see the user's model cache, docs/lessons.md), with the models already
downloaded by ``scripts/setup-models.py``:

    .venv\\Scripts\\python.exe scripts\\measure-speakers.py <recordings-dir>

``<recordings-dir>`` holds ``<name>.wav`` (16 kHz mono 16-bit PCM) beside
``<name>.txt`` (an Audacity exported label track whose labels are ROLE
names, one of them ``clinician``). The Markdown table on stdout is ready to
paste into the plan's Task 2.3. Nothing from the recordings is logged or
printed. The temporary encrypted store is torn down key-first, and every
teardown failure the OS reports - and any residue - is surfaced by path (a
leftover the OS refuses to delete is named for by-hand removal, never
hidden).
"""

from __future__ import annotations

import sys

from scribe_desktop.speaker_eval import main

if __name__ == "__main__":
    sys.exit(main())
