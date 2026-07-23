// Message protocol — hand-mirrored from the canonical fixtures.
//
// The canonical contract lives in protocol/fixtures/ (plan Key Design
// Decision: fixtures-canonical protocol). This module and the pydantic
// mirror (desktop/src/scribe_desktop/protocol.py) are both validated
// against the same fixture files; drift is a test failure.

export const PROTOCOL_VERSION = 1;
export const MIN_SUPPORTED_VERSION = 1;
export const HOST_NAME = "com.scribe.cliniko_host";
// Project policy bound, both directions (platform allows more Chrome->host).
export const MAX_FRAME_BYTES = 1_048_576;

export const MESSAGE_TYPES = ["hello", "hello_ack", "ping", "pong", "error"] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export const ERROR_CODES = [
  "version_below_floor",
  "bad_nonce",
  "malformed",
  "oversized",
  "internal",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

const NONCE_FORBIDDEN: ReadonlySet<MessageType> = new Set(["hello"]);
const NONCE_REQUIRED: ReadonlySet<MessageType> = new Set(["hello_ack", "ping", "pong"]);

export interface Envelope {
  protocol_version: number;
  type: MessageType;
  request_id?: string;
  session_nonce?: string;
  payload: Record<string, unknown>;
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
    if (typeof request_id !== "string" || request_id.length < 1 || request_id.length > 128) {
      throw new ProtocolError("malformed", "request_id must be a 1-128 character string");
    }
  }
  if (session_nonce !== undefined) {
    if (typeof session_nonce !== "string" || session_nonce.length < 16 || session_nonce.length > 128) {
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
  if (messageType === "error") {
    const code = payload["code"];
    const message = payload["message"];
    if (typeof code !== "string" || !(ERROR_CODES as readonly string[]).includes(code)) {
      throw new ProtocolError("malformed", "error payload requires a known code");
    }
    if (typeof message !== "string" || message.length === 0) {
      throw new ProtocolError("malformed", "error payload requires a message");
    }
  }

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
