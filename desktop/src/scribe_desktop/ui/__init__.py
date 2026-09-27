"""Phase-2 desktop UI (plan Step 10).

Extends the Phase-1 status window into a small multi-screen app:
microphone (device pick + level + benchmark/model report panel), session
controls, recovery list (Flow 3), and the transcript-inspection view
(Complete/Discard). GUI-free view logic lives in ``ui.models`` so it is
unit-testable without Qt; the screens are thin wiring over it.

Critical Constraints honoured here: no network code (no QtNetwork; the app's
one network-capable module is ``scribe_desktop.cliniko_client``, and no UI
module imports it — ``ui/bridge.py``, ``ui/main_window.py`` and
``ui/clinics.py`` reach Cliniko only through ``encounter`` and ``clinics``),
no clinical text in logs, and transcript content is
DISPLAYED only — never written anywhere except the encrypted store.
"""
