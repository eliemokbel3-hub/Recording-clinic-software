// Message protocol — hand-mirrored from the canonical fixtures.
//
// The canonical contract lives in protocol/fixtures/ (plan Key Design
// Decision: fixtures-canonical protocol). This module and the pydantic
// mirror (desktop/src/scribe_desktop/protocol.py) are both validated
// against the same fixture files; drift is a test failure.
//
// Protocol v2 (Cliniko workflow safeguards plan D2, Task 4.1): three new
// types — `context` and `command` (extension -> app) and `state` (app ->
// extension) — each with a payload whose every string and array is bounded
// (LIMITS, pinned in meta.json) and whose unknown keys are refused. A refused
// command arrives as `state.last_refusal`; `error` stays fatal-only.
// Lengths count code points, as Python's len() does.

export const PROTOCOL_VERSION = 2;
export const MIN_SUPPORTED_VERSION = 2;
export const HOST_NAME = "com.scribe.cliniko_host";
// Project policy bound, both directions (platform allows more Chrome->host).
export const MAX_FRAME_BYTES = 1_048_576;

export const MESSAGE_TYPES = [
  "hello",
  "hello_ack",
  "ping",
  "pong",
  "error",
  "context",
  "command",
  "state",
] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export const ERROR_CODES = [
  "version_below_floor",
  "bad_nonce",
  "malformed",
  "oversized",
  "internal",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

// Every bound both mirrors enforce, pinned in protocol/fixtures/meta.json.
export const LIMITS = {
  max_seq: 9_007_199_254_740_991,
  max_state_rev: 9_007_199_254_740_991,
  max_tab_id: 2_147_483_647,
  max_recorded_seconds: 1_000_000,
  max_banner_count: 99,
  max_request_id_chars: 128,
  max_display_chars: 120,
  max_label_chars: 80,
  max_message_chars: 300,
  max_reason_chars: 48,
  max_timestamp_chars: 40,
  max_chord_chars: 40,
  max_allow_list: 16,
  max_warnings: 8,
  session_ref_chars: 24,
} as const;

// Shapes shared with the pydantic mirror (character for character).
export const ID_PATTERN = /^[1-9][0-9]{0,18}$/;
export const HOST_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2}[0-9]\.cliniko\.com$/;
export const SESSION_REF_PATTERN = /^[A-Za-z0-9_-]{24}$/;
export const REASON_PATTERN = /^[a-z][a-z0-9_]{0,47}$/;
export const TIMESTAMP_PATTERN =
  /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$/;
// Display text is one line: no C0 or C1 control character, no DEL.
const TEXT_PATTERN = /^[^\u0000-\u001f\u007f-\u009f]+$/u;

const NONCE_FORBIDDEN: ReadonlySet<MessageType> = new Set(["hello"]);
const NONCE_REQUIRED: ReadonlySet<MessageType> = new Set([
  "hello_ack",
  "ping",
  "pong",
  "context",
  "command",
  "state",
]);

export const COMMAND_ACTIONS = [
  "start",
  "pause",
  "resume",
  "finish",
  "discard",
  "resume_previous",
  "open_review",
] as const;
export type CommandAction = (typeof COMMAND_ACTIONS)[number];
// The actions that act on ONE session and must name it (D2).
export const SESSION_BOUND_ACTIONS: ReadonlySet<CommandAction> = new Set([
  "resume",
  "finish",
  "discard",
  "resume_previous",
  "open_review",
]);
export const PAGE_KINDS = ["note", "login", "other_cliniko", "not_cliniko", "closed"] as const;
export type PageKind = (typeof PAGE_KINDS)[number];
const HOSTED_PAGES: ReadonlySet<PageKind> = new Set(["note", "login", "other_cliniko"]);
const VERIFICATION_VIEWS = ["checking", "verified", "unverified_offline", "refused"] as const;
const LIVE_PHASES = ["recording", "paused", "finishing", "queued"] as const;
const LIVE_VERIFICATIONS = ["verified", "unverified_offline"] as const;

export interface Envelope {
  protocol_version: number;
  type: MessageType;
  request_id?: string;
  session_nonce?: string;
  payload: Record<string, unknown>;
}

export interface ContextPayload {
  seq: number;
  tab_id: number;
  window_id: number;
  focused: boolean;
  page: PageKind;
  host?: string;
  patient_id?: string;
  note_id?: string;
}

export interface CommandTarget {
  tab_id: number;
  clinic_host: string;
  patient_id: string;
  note_id: string;
}

export interface CommandPayload {
  action: CommandAction;
  state_rev: number;
  session_ref?: string;
  consent?: { confirmed: true; text_version: "recording-consent-v1" };
  target?: CommandTarget;
  confirmed?: true;
}

export interface ReportState {
  tab_id: number;
  clinic_host: string;
  patient_id: string;
  note_id: string;
  verification: (typeof VERIFICATION_VIEWS)[number];
  refusal?: string;
  clinic_label?: string;
  patient_name?: string;
  appointment_starts_at?: string;
}

export interface LiveState {
  session_ref: string;
  phase: (typeof LIVE_PHASES)[number];
  linked: boolean;
  recorded_seconds: number;
  consent_confirmed_at: string;
  clinic_host?: string;
  patient_id?: string;
  note_id?: string;
  verification?: (typeof LIVE_VERIFICATIONS)[number];
  clinic_label?: string;
  patient_name?: string;
}

export interface StatePayload {
  state_rev: number;
  app_running: boolean;
  allow_list: string[];
  hotkey: { available: boolean; chord?: string };
  spoken_pause: boolean;
  warnings: string[];
  report?: ReportState;
  live?: LiveState;
  block?: {
    reason: string;
    session_ref: string;
    clinic_host: string;
    clinic_label: string;
    patient_name?: string;
  };
  banner?: {
    session_ref: string;
    clinic_host: string;
    note_id: string;
    count: number;
    patient_name?: string;
  };
  notice?: string;
  last_refusal?: { action: CommandAction; reason: string; message: string };
}

export class ProtocolError extends Error {
  constructor(
    readonly code: ErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "ProtocolError";
  }
}

const ENVELOPE_KEYS = new Set(["protocol_version", "type", "request_id", "session_nonce", "payload"]);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// --- payload field checks (every failure is "malformed") ---------------------

function malformed(message: string): never {
  throw new ProtocolError("malformed", message);
}

function codePoints(value: string): number {
  return [...value].length;
}

/** The object at `where`, with only the named keys (the rest refused). */
function objectWith(value: unknown, where: string, allowed: readonly string[]): Record<string, unknown> {
  if (!isPlainObject(value)) malformed(`${where} must be a JSON object`);
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) malformed(`unknown field in ${where}: ${key}`);
  }
  return value;
}

function present(obj: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function integer(obj: Record<string, unknown>, key: string, low: number, high: number): number {
  const value = obj[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value < low || value > high) {
    malformed(`${key} must be an integer in [${String(low)}, ${String(high)}]`);
  }
  return value;
}

function boolean(obj: Record<string, unknown>, key: string): boolean {
  const value = obj[key];
  if (typeof value !== "boolean") malformed(`${key} must be a boolean`);
  return value;
}

function literalTrue(obj: Record<string, unknown>, key: string): true {
  if (obj[key] !== true) malformed(`${key} must be true`);
  return true;
}

function matching(obj: Record<string, unknown>, key: string, pattern: RegExp, maxChars?: number): string {
  const value = obj[key];
  if (typeof value !== "string" || !pattern.test(value)) malformed(`${key} has the wrong shape`);
  if (maxChars !== undefined && codePoints(value) > maxChars) malformed(`${key} is too long`);
  return value;
}

function text(obj: Record<string, unknown>, key: string, maxChars: number): string {
  const value = obj[key];
  if (typeof value !== "string" || !TEXT_PATTERN.test(value) || codePoints(value) > maxChars) {
    malformed(`${key} must be one line of at most ${String(maxChars)} characters`);
  }
  return value;
}

function oneOf<T extends string>(obj: Record<string, unknown>, key: string, options: readonly T[]): T {
  const value = obj[key];
  if (typeof value !== "string" || !(options as readonly string[]).includes(value)) {
    malformed(`${key} is not one of the allowed values`);
  }
  return value as T;
}

function optional<T>(obj: Record<string, unknown>, key: string, check: () => T): T | undefined {
  return present(obj, key) ? check() : undefined;
}

function list(obj: Record<string, unknown>, key: string, maxItems: number, item: RegExp): string[] {
  const value = obj[key];
  if (!Array.isArray(value) || value.length > maxItems) {
    malformed(`${key} must be an array of at most ${String(maxItems)} items`);
  }
  for (const entry of value) {
    if (typeof entry !== "string" || !item.test(entry)) malformed(`${key} has an item of the wrong shape`);
  }
  return value as string[];
}

function checkEmpty(payload: Record<string, unknown>, type: MessageType): void {
  if (Object.keys(payload).length !== 0) malformed(`${type} carries an empty payload`);
}

function checkError(payload: Record<string, unknown>): void {
  objectWith(payload, "error payload", ["code", "message"]);
  const code = payload["code"];
  const message = payload["message"];
  if (typeof code !== "string" || !(ERROR_CODES as readonly string[]).includes(code)) {
    malformed("error payload requires a known code");
  }
  if (typeof message !== "string" || message.length === 0 || codePoints(message) > LIMITS.max_message_chars) {
    malformed("error payload requires a message of at most 300 characters");
  }
}

function checkContext(payload: Record<string, unknown>): void {
  const p = objectWith(payload, "context", [
    "seq",
    "tab_id",
    "window_id",
    "focused",
    "page",
    "host",
    "patient_id",
    "note_id",
  ]);
  integer(p, "seq", 1, LIMITS.max_seq);
  integer(p, "tab_id", 0, LIMITS.max_tab_id);
  integer(p, "window_id", 0, LIMITS.max_tab_id);
  boolean(p, "focused");
  const page = oneOf(p, "page", PAGE_KINDS);
  const host = optional(p, "host", () => matching(p, "host", HOST_PATTERN));
  const patientId = optional(p, "patient_id", () => matching(p, "patient_id", ID_PATTERN));
  const noteId = optional(p, "note_id", () => matching(p, "note_id", ID_PATTERN));
  if (HOSTED_PAGES.has(page) !== (host !== undefined)) {
    malformed("a host is carried exactly by a page on a Cliniko host");
  }
  const note = page === "note";
  if ((patientId !== undefined) !== note || (noteId !== undefined) !== note) {
    malformed("patient and note ids are carried exactly by a note page");
  }
}

function checkCommand(payload: Record<string, unknown>): void {
  const p = objectWith(payload, "command", ["action", "state_rev", "session_ref", "consent", "target", "confirmed"]);
  const action = oneOf(p, "action", COMMAND_ACTIONS);
  integer(p, "state_rev", 0, LIMITS.max_state_rev);
  const sessionRef = optional(p, "session_ref", () => matching(p, "session_ref", SESSION_REF_PATTERN));
  const consent = optional(p, "consent", () => {
    const c = objectWith(p["consent"], "consent", ["confirmed", "text_version"]);
    literalTrue(c, "confirmed");
    if (c["text_version"] !== "recording-consent-v1") malformed("unknown consent text version");
    return c;
  });
  const target = optional(p, "target", () => {
    const t = objectWith(p["target"], "target", ["tab_id", "clinic_host", "patient_id", "note_id"]);
    for (const key of ["tab_id", "clinic_host", "patient_id", "note_id"]) {
      if (!present(t, key)) malformed(`target requires ${key}`);
    }
    integer(t, "tab_id", 0, LIMITS.max_tab_id);
    matching(t, "clinic_host", HOST_PATTERN);
    matching(t, "patient_id", ID_PATTERN);
    matching(t, "note_id", ID_PATTERN);
    return t;
  });
  const confirmed = optional(p, "confirmed", () => literalTrue(p, "confirmed"));
  const start = action === "start";
  if ((target !== undefined) !== start || (consent !== undefined) !== start) {
    malformed("start carries exactly a target and a consent");
  }
  if (start && sessionRef !== undefined) malformed("start acts on no session");
  if (SESSION_BOUND_ACTIONS.has(action) && sessionRef === undefined) {
    malformed(`${action} must name the session it acts on`);
  }
  if ((confirmed !== undefined) !== (action === "discard")) {
    malformed("discard, and only discard, carries the confirming second click");
  }
}

function checkReport(value: unknown): void {
  const r = objectWith(value, "report", [
    "tab_id",
    "clinic_host",
    "patient_id",
    "note_id",
    "verification",
    "refusal",
    "clinic_label",
    "patient_name",
    "appointment_starts_at",
  ]);
  integer(r, "tab_id", 0, LIMITS.max_tab_id);
  matching(r, "clinic_host", HOST_PATTERN);
  matching(r, "patient_id", ID_PATTERN);
  matching(r, "note_id", ID_PATTERN);
  const verification = oneOf(r, "verification", VERIFICATION_VIEWS);
  const refusal = optional(r, "refusal", () => matching(r, "refusal", REASON_PATTERN));
  optional(r, "clinic_label", () => text(r, "clinic_label", LIMITS.max_label_chars));
  const name = optional(r, "patient_name", () => text(r, "patient_name", LIMITS.max_display_chars));
  const startsAt = optional(r, "appointment_starts_at", () =>
    matching(r, "appointment_starts_at", TIMESTAMP_PATTERN, LIMITS.max_timestamp_chars),
  );
  if ((refusal !== undefined) !== (verification === "refused")) {
    malformed("a refusal is carried exactly by a refused verification");
  }
  if (verification !== "verified" && (name !== undefined || startsAt !== undefined)) {
    malformed("display strings come only from a verified note");
  }
}

function checkLive(value: unknown): void {
  const l = objectWith(value, "live", [
    "session_ref",
    "phase",
    "linked",
    "recorded_seconds",
    "consent_confirmed_at",
    "clinic_host",
    "patient_id",
    "note_id",
    "verification",
    "clinic_label",
    "patient_name",
  ]);
  matching(l, "session_ref", SESSION_REF_PATTERN);
  oneOf(l, "phase", LIVE_PHASES);
  const linked = boolean(l, "linked");
  integer(l, "recorded_seconds", 0, LIMITS.max_recorded_seconds);
  matching(l, "consent_confirmed_at", TIMESTAMP_PATTERN, LIMITS.max_timestamp_chars);
  const ids = [
    optional(l, "clinic_host", () => matching(l, "clinic_host", HOST_PATTERN)),
    optional(l, "patient_id", () => matching(l, "patient_id", ID_PATTERN)),
    optional(l, "note_id", () => matching(l, "note_id", ID_PATTERN)),
    optional(l, "verification", () => oneOf(l, "verification", LIVE_VERIFICATIONS)),
  ];
  const display = [
    optional(l, "clinic_label", () => text(l, "clinic_label", LIMITS.max_label_chars)),
    optional(l, "patient_name", () => text(l, "patient_name", LIMITS.max_display_chars)),
  ];
  if (linked && ids.some((v) => v === undefined)) {
    malformed("a linked session names its clinic, patient, note and verification");
  }
  if (!linked && [...ids, ...display].some((v) => v !== undefined)) {
    malformed("an unlinked session names no clinic or patient");
  }
}

function checkState(payload: Record<string, unknown>): void {
  const p = objectWith(payload, "state", [
    "state_rev",
    "app_running",
    "allow_list",
    "hotkey",
    "spoken_pause",
    "warnings",
    "report",
    "live",
    "block",
    "banner",
    "notice",
    "last_refusal",
  ]);
  integer(p, "state_rev", 0, LIMITS.max_state_rev);
  const running = boolean(p, "app_running");
  const allowList = list(p, "allow_list", LIMITS.max_allow_list, HOST_PATTERN);
  const hotkey = objectWith(p["hotkey"], "hotkey", ["available", "chord"]);
  const available = boolean(hotkey, "available");
  const chord = optional(hotkey, "chord", () => text(hotkey, "chord", LIMITS.max_chord_chars));
  if ((chord !== undefined) !== available) malformed("an available hotkey names its chord");
  boolean(p, "spoken_pause");
  list(p, "warnings", LIMITS.max_warnings, REASON_PATTERN);
  optional(p, "report", () => checkReport(p["report"]));
  optional(p, "live", () => checkLive(p["live"]));
  optional(p, "block", () => {
    const b = objectWith(p["block"], "block", ["reason", "session_ref", "clinic_host", "clinic_label", "patient_name"]);
    matching(b, "reason", REASON_PATTERN);
    matching(b, "session_ref", SESSION_REF_PATTERN);
    matching(b, "clinic_host", HOST_PATTERN);
    text(b, "clinic_label", LIMITS.max_label_chars);
    optional(b, "patient_name", () => text(b, "patient_name", LIMITS.max_display_chars));
  });
  optional(p, "banner", () => {
    const b = objectWith(p["banner"], "banner", ["session_ref", "clinic_host", "note_id", "count", "patient_name"]);
    matching(b, "session_ref", SESSION_REF_PATTERN);
    matching(b, "clinic_host", HOST_PATTERN);
    matching(b, "note_id", ID_PATTERN);
    integer(b, "count", 1, LIMITS.max_banner_count);
    optional(b, "patient_name", () => text(b, "patient_name", LIMITS.max_display_chars));
  });
  optional(p, "notice", () => matching(p, "notice", REASON_PATTERN));
  optional(p, "last_refusal", () => {
    const r = objectWith(p["last_refusal"], "last_refusal", ["action", "reason", "message"]);
    oneOf(r, "action", COMMAND_ACTIONS);
    matching(r, "reason", REASON_PATTERN);
    text(r, "message", LIMITS.max_message_chars);
  });
  const anyPresent = ["report", "live", "block", "banner", "notice", "last_refusal"].some((key) => present(p, key));
  if (!running && (allowList.length > 0 || anyPresent)) {
    malformed("an app that is not running reports nothing else");
  }
}

function checkPayload(type: MessageType, payload: Record<string, unknown>): void {
  switch (type) {
    case "hello":
    case "hello_ack":
    case "ping":
    case "pong":
      checkEmpty(payload, type);
      return;
    case "error":
      checkError(payload);
      return;
    case "context":
      checkContext(payload);
      return;
    case "command":
      checkCommand(payload);
      return;
    case "state":
      checkState(payload);
      return;
  }
}

/** Validate an already-decoded JSON value into an Envelope. Throws ProtocolError. */
export function parseEnvelope(value: unknown): Envelope {
  if (!isPlainObject(value)) {
    throw new ProtocolError("malformed", "envelope must be a JSON object");
  }
  for (const key of Object.keys(value)) {
    if (!ENVELOPE_KEYS.has(key)) {
      throw new ProtocolError("malformed", `unknown envelope field: ${key}`);
    }
  }
  const { protocol_version, type, request_id, session_nonce, payload } = value;

  if (!Number.isInteger(protocol_version)) {
    throw new ProtocolError("malformed", "protocol_version must be an integer");
  }
  // Floor check BEFORE the positivity check (MED-001): any integer below the
  // floor — including 0 — classifies as version_below_floor on both mirrors.
  if ((protocol_version as number) < MIN_SUPPORTED_VERSION) {
    throw new ProtocolError(
      "version_below_floor",
      `protocol_version ${String(protocol_version)} is below the supported floor ${String(MIN_SUPPORTED_VERSION)}`,
    );
  }
  if (typeof type !== "string" || !(MESSAGE_TYPES as readonly string[]).includes(type)) {
    throw new ProtocolError("malformed", "unknown message type");
  }
  const messageType = type as MessageType;

  if (request_id !== undefined) {
    // Code points, as for every payload string (round 25 LOW-021).
    if (
      typeof request_id !== "string" ||
      request_id.length < 1 ||
      codePoints(request_id) > LIMITS.max_request_id_chars
    ) {
      throw new ProtocolError("malformed", "request_id must be a 1-128 character string");
    }
  }
  if (session_nonce !== undefined) {
    if (typeof session_nonce !== "string" || codePoints(session_nonce) < 16 || codePoints(session_nonce) > 128) {
      throw new ProtocolError("malformed", "session_nonce must be a 16-128 character string");
    }
  }
  if (NONCE_FORBIDDEN.has(messageType) && session_nonce !== undefined) {
    throw new ProtocolError("malformed", `${messageType} must not carry a session_nonce`);
  }
  if (NONCE_REQUIRED.has(messageType) && session_nonce === undefined) {
    throw new ProtocolError("bad_nonce", `${messageType} requires a session_nonce`);
  }
  if (!isPlainObject(payload)) {
    throw new ProtocolError("malformed", "payload must be a JSON object");
  }
  checkPayload(messageType, payload);

  const envelope: Envelope = {
    protocol_version: protocol_version as number,
    type: messageType,
    payload,
  };
  if (request_id !== undefined) envelope.request_id = request_id;
  if (session_nonce !== undefined) envelope.session_nonce = session_nonce;
  return envelope;
}

export function makeHello(requestId: string): Envelope {
  return {
    protocol_version: PROTOCOL_VERSION,
    type: "hello",
    request_id: requestId,
    payload: {},
  };
}

export function makePing(requestId: string, sessionNonce: string): Envelope {
  return {
    protocol_version: PROTOCOL_VERSION,
    type: "ping",
    request_id: requestId,
    session_nonce: sessionNonce,
    payload: {},
  };
}
