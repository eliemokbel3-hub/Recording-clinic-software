"""Transcription-guard measurement launcher (invented-text-guard plan Task 1.5).

Thin by design: ``ruff`` and ``mypy`` run inside ``desktop/``, so all logic
lives in ``scribe_desktop.guard_eval`` and this file only dispatches (pinned
by ``desktop/tests/test_guard_eval.py``).

Use it YOURSELF from a normal terminal on the developer build (never an agent
shell - those cannot see the user's model folder, docs/lessons.md), with the
installed app closed, the models downloaded by ``scripts/setup-models.py``
and a synthetic set built by ``scripts/build-validation-set.py`` into an
empty folder outside the repository:

    .venv\\Scripts\\python.exe scripts\\measure-transcription-guard.py --set <set-folder>

``--candidates`` takes one or more constant sets to sweep
(``min_words,max_seconds,words_per_second,mean_probability,no_speech``);
``--primer 0.3.1`` decodes with 0.3.1's primer for comparison only. The
Markdown tables on stdout hold numbers, yes/no, closed words and case ids
only - paste them onto the plan's Task 3.1.
"""

from __future__ import annotations

import sys

from scribe_desktop.guard_eval import main

if __name__ == "__main__":
    sys.exit(main())
