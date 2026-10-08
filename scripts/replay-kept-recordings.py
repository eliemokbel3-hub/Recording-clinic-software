"""Kept-recordings replay launcher (development-recordings plan Task 4.1a).

Thin by design: ``ruff`` and ``mypy`` run inside ``desktop/``, so all logic
lives in ``scribe_desktop.replay_kept`` and this file only dispatches.

Run it YOURSELF from a normal terminal on the developer build (never an agent
shell - those cannot see the user's model folder or unwrap this Windows
user's keys, docs/lessons.md), with Clinic Scribe closed (either build) and
the models downloaded by ``scripts/setup-models.py``, naming the
Past-sessions folder explicitly. In Command Prompt:

    .venv\\Scripts\\python.exe scripts\\replay-kept-recordings.py "%LOCALAPPDATA%\\ClinikoScribe\\past_sessions"
    .venv\\Scripts\\python.exe scripts\\replay-kept-recordings.py "%LOCALAPPDATA%\\ClinikoScribe-dev\\past_sessions" --only <session id>
    .venv\\Scripts\\python.exe scripts\\replay-kept-recordings.py <folder> --enrolment me.wav

In PowerShell write ``"$env:LOCALAPPDATA\\ClinikoScribe\\past_sessions"``
instead (``%LOCALAPPDATA%`` is not expanded there, and the tool would refuse
the literal text as not a folder).

It reads the folder and writes nothing there; it holds the app's
single-instance lock for its run, so neither build can start meanwhile. The
output holds session ids, numbers, model names and the folder given - no
transcript, note or name text; the numbers are DRIFT against what the app
kept, never accuracy. See ``docs/testing/kept-recordings.md``.
"""

from __future__ import annotations

import sys

from scribe_desktop.replay_kept import main

if __name__ == "__main__":
    sys.exit(main())
