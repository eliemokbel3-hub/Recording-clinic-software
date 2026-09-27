# Protocol fixtures — canonical contract

These JSON fixture files are the **canonical protocol contract** between the
Chrome extension and the desktop native host — and, through the host's relay
over the named pipe, `scribe-app` (plan Key Design Decision:
fixtures-canonical protocol). The TypeScript types (`extension/src/protocol.ts`)
and pydantic models (`desktop/src/scribe_desktop/protocol.py`) are hand-mirrored,
and each side's tests validate against these same files — fixture drift is a
test failure.

## Layout

- `meta.json` — the protocol version (2), the supported floor (2), the host
  name, the frame bound, and `limits`: every numeric range and every string
  and array length both mirrors enforce. Each mirror's test pins its own
  constants to these values.
- `valid/` — messages both mirrors must accept. The file name is the message
  type, optionally followed by `__<variant>` (`context__note.json`).
- `invalid/` — `{"reason": ..., "message": ...}` cases both mirrors must
  refuse. `reason` says why; the prefix before `__` names the type under test.

## Protocol v2 (Cliniko workflow safeguards plan D2)

v2 adds three types; hello / hello_ack / ping / pong now carry an EMPTY
payload, and every payload refuses unknown keys.

- **`context`** (extension → app): `{seq, tab_id, window_id, focused, page,
  host?, patient_id?, note_id?}`. `page` is `note | login | other_cliniko |
  not_cliniko | closed`. A host is carried exactly by `note`, `login` and
  `other_cliniko`; patient and note ids exactly by `note`. A tab that left the
  allow-list reports `not_cliniko` with no host; a removed tab `closed`. No
  URL is ever carried.
- **`command`** (extension → app): `{action, state_rev, session_ref?,
  consent?, target?, confirmed?}`. `start` carries exactly `target` and
  `consent: {confirmed: true, text_version: "recording-consent-v1"}` and no
  `session_ref`; `resume`, `finish`, `discard`, `resume_previous` and
  `open_review` carry the `session_ref` they act on; `discard` alone carries
  `confirmed: true` (the second click); `pause` may omit the ref.
- **`state`** (app → extension): the app's full snapshot — `state_rev`,
  `app_running`, `allow_list`, `hotkey`, `spoken_pause`, `warnings`, and the
  optional `report`, `live`, `block`, `banner`, `notice` and `last_refusal`.
  A refused command is named in `last_refusal`; `error` stays fatal-only (the
  extension disconnects on it). An app that is not running reports nothing
  but the empty shape.

Shapes: a Cliniko id is a string `^[1-9][0-9]{0,18}$` (never a JSON number);
a host is `<subdomain>.<shard>.cliniko.com`; a `session_ref` is exactly 24
url-safe characters; a reason code is `^[a-z][a-z0-9_]{0,47}$`; display text
is one line (no control character); a timestamp is ISO 8601 with a zone;
booleans are JSON booleans and integers JSON integers — the envelope's
`protocol_version` too (a numeric string or a boolean is `malformed`). Lengths
count characters (code points) on both sides, the envelope's `request_id` and
`session_nonce` included (`ping__astral_request_id.json`).

Display text and privacy (Cliniko workflow safeguards plan D2, Constraint 8;
see the data-flow map, flows 19–20). A patient's name can appear only in
`state` — `report.patient_name` (with `appointment_starts_at`, refused unless
the report is `verified`), `live.patient_name` (refused on an unlinked
session) and `block.patient_name`; `banner.patient_name` is allowed by the
shape but the app never sends it (a retired session keeps no display
string). `context` and `command` carry ids and codes only, never a name or a
URL, and no message carries a Cliniko API key. What each Chrome tab is then
told is the extension's per-tab slice, not a protocol message
(`extension/src/context.ts` `sliceFor`).

`context`, `command` and `state` require the session nonce on the Chrome
wire. On the host ↔ app pipe the host strips it from `context` and `command`
and stamps it on `state`, so pipe messages carry NONE — that leg is checked
by the Python mirror only (`parse_pipe_envelope`; the extension never sees
the pipe).

Named residue: JavaScript cannot tell `1.0` from `1` after `JSON.parse`, so
the TypeScript mirror accepts a fraction-free float where the Python mirror
refuses it. No fixture relies on either reading.
