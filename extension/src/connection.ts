// Native-messaging connection manager (plan Step 7).
//
// MV3 lifecycle rules (plan executor facts): an open native port extends the
// service worker's lifetime, but the SW still dies on browser restart/update/
// crash, and setTimeout does not survive suspension. Therefore:
// - connect() runs at SW top level (fires on every wake) and on onStartup/
//   onInstalled
// - backoff between reconnect attempts uses chrome.alarms
// - EVERY reconnect is a full fresh handshake; the stale nonce is discarded.
//
// The session nonce is a session identifier, not authentication (plan Key
// Design Decision) — a mismatch means a broken/mixed session, so disconnect.

import type { Envelope } from "./protocol";
import { HOST_NAME, makeHello, makePing, parseEnvelope } from "./protocol";

export const RECONNECT_ALARM = "scribe-reconnect";
export const PING_ALARM = "scribe-ping";
// chrome.alarms minimum is 30s; cap backoff at 5 minutes.
const BACKOFF_MINUTES = [0.5, 1, 2, 5] as const;

export type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

export interface PortLike {
  postMessage(message: unknown): void;
  disconnect(): void;
  onMessage: { addListener(cb: (message: unknown) => void): void };
  onDisconnect: { addListener(cb: () => void): void };
}

// The minimal chrome surface the manager needs — injectable for tests.
export interface ChromeLike {
  connectNative(hostName: string): PortLike;
  createAlarm(name: string, delayInMinutes: number): void;
  clearAlarm(name: string): void;
  setBadge(text: string, color: string): void;
  newRequestId(): string;
}

const BADGES: Record<ConnectionState, [string, string]> = {
  connecting: ["…", "#f0ad4e"],
  connected: ["OK", "#2e7d32"],
  disconnected: ["OFF", "#9e9e9e"],
  error: ["ERR", "#c62828"],
};

export class ConnectionManager {
  state: ConnectionState = "disconnected";
  private port: PortLike | null = null;
  private sessionNonce: string | null = null;
  private helloRequestId: string | null = null;
  private pingRequestId: string | null = null;
  private backoffIndex = 0;

  constructor(private readonly api: ChromeLike) {}

  /** Full fresh handshake. Safe to call repeatedly (idempotent while connecting/connected). */
  connect(): void {
    if (this.state === "connecting" || this.state === "connected") return;
    this.sessionNonce = null; // discard any stale nonce (plan acceptance criterion)
    this.setState("connecting");
    try {
      this.port = this.api.connectNative(HOST_NAME);
    } catch {
      this.onDisconnected();
      return;
    }
    this.port.onMessage.addListener((message) => this.onMessage(message));
    this.port.onDisconnect.addListener(() => this.onDisconnected());
    this.helloRequestId = this.api.newRequestId();
    this.port.postMessage(makeHello(this.helloRequestId));
  }

  /** Periodic liveness probe (PING_ALARM); no-op unless connected. */
  ping(): void {
    if (this.state !== "connected" || !this.port || !this.sessionNonce) return;
    this.pingRequestId = this.api.newRequestId();
    this.port.postMessage(makePing(this.pingRequestId, this.sessionNonce));
  }

  /** Route an alarm firing to the matching behaviour. */
  onAlarm(name: string): void {
    if (name === RECONNECT_ALARM) this.connect();
    if (name === PING_ALARM) this.ping();
  }

  private onMessage(raw: unknown): void {
    let envelope: Envelope;
    try {
      envelope = parseEnvelope(raw);
    } catch {
      this.fail();
      return;
    }
    if (envelope.type === "hello_ack") {
      if (this.state !== "connecting" || envelope.request_id !== this.helloRequestId) {
        this.fail();
        return;
      }
      this.sessionNonce = envelope.session_nonce ?? null;
      this.backoffIndex = 0;
      this.api.clearAlarm(RECONNECT_ALARM);
      this.setState("connected");
      return;
    }
    if (envelope.type === "pong") {
      if (
        this.state !== "connected" ||
        envelope.session_nonce !== this.sessionNonce ||
        envelope.request_id !== this.pingRequestId
      ) {
        this.fail();
      }
      return;
    }
    if (envelope.type === "error") {
      this.fail();
      return;
    }
    // hello/ping are host-bound; receiving one here is a broken peer.
    this.fail();
  }

  private fail(): void {
    this.setState("error");
    const port = this.port;
    this.port = null;
    this.sessionNonce = null;
    try {
      port?.disconnect();
    } catch {
      // already gone
    }
    this.scheduleReconnect();
  }

  private onDisconnected(): void {
    this.port = null;
    this.sessionNonce = null;
    if (this.state !== "error") this.setState("disconnected");
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    const minutes = BACKOFF_MINUTES[Math.min(this.backoffIndex, BACKOFF_MINUTES.length - 1)];
    this.backoffIndex += 1;
    this.api.createAlarm(RECONNECT_ALARM, minutes ?? 5);
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    const [text, color] = BADGES[state];
    this.api.setBadge(text, color);
  }
}
