# Protocol fixtures — canonical contract

These JSON fixture files are the **canonical protocol contract** between the
Chrome extension and the desktop native host (plan Key Design Decision:
fixtures-canonical protocol). The TypeScript types (`extension/src/protocol.ts`)
and pydantic models (`desktop/src/scribe_desktop/protocol.py`) are hand-mirrored,
and each side's tests validate against these same files — fixture drift is a
test failure.

Populated in plan Step 2. Valid and invalid cases both live here.
