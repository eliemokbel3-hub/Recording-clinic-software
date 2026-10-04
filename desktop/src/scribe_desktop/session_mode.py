"""A recording's mode (pilot plan Task 1.2; D1, D3).

``SessionMode`` is the ONE type the shadow boundary reads: the session
(``session.RecordingSession``) and its encounter record
(``encounter.EncounterRecord`` v2) carry it, the draft write refuses a
shadow session (``draft_write.refuse_before_read``), the Note tab refuses
Copy for one, the audit row records it and the Past-sessions label marks
it. It is fixed at Start from the pilot setting (``note_config.
shadow_mode_on``) and never changes for that recording.

This module imports nothing of the app, so every store can depend on it."""

from __future__ import annotations

from enum import StrEnum


class SessionMode(StrEnum):
    """``normal``: everyday use. ``shadow``: the pilot's comparison run —
    the note is drafted as usual but cannot be written to Cliniko or
    copied, and a Save of it teaches the app nothing (D13)."""

    NORMAL = "normal"
    SHADOW = "shadow"
