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
//
// Protocol v2 (Cliniko workflow safeguards plan D2, Task 4.1): a `state`
// carrying this session's nonce is handed to the state listener and the
// connection STAYS up — a refused command arrives as `state.last_refusal`,
// never as `error` (which stays fatal and disconnects).
//
// Task 6.2: `send` carries a `context` or `command` out under this session's
// nonce, and only after the extension's own mirror has accepted the whole
// envelope (a malformed message is dropped here, never sent). The badge
// (D1, replacing the Phase 1 connection badges) reflects the APP, not only
// the host: REC / PAUSED for a live session, "!" when the link is down while
// a session was live, OK while the app runs idle, OFF when it does not.

import type { ContextPayload, CommandPayload, Envelope, StatePayload } from "./protocol";
import { HOST_NAME, PROTOCOL_VERSION, makeHello, makePing, parseEnvelope } from "./protocol";

export const RECONNECT_ALARM = "scribe-reconnect";
export const PING_ALARM = "scribe-ping";
// HIGH-002: watchdog for a host that opens the port but never answers hello.
export const WATCHDOG_ALARM = "scribe-handshake-watchdog";
// chrome.alarms minimum is 30s; cap backoff at 5 minutes.
const BACKOFF_MINUTES = [0.5, 1, 2, 5] as const;
const WATCHDOG_MINUTES = 0.5;

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
  setBadge(text: string, color: string, title?: string): void;
  newRequestId(): string;
}

export interface ConnectionHooks {
  /** A fresh handshake completed (a new host, so a new pipe client). */
  onHandshake?: () => void;
  /** The connection state or the badge changed. */
  onChange?: (state: ConnectionState) => void;
}

export interface Badge {
  text: string;
  color: string;
  title: string;
}

const RED = "#c62828";
const AMBER = "#b26a00";
const GREEN = "#2e7d32";
const GREY = "#757575";

/**
 * D1's badge. `state` is the app's latest snapshot on the current
 * connection (null before the first one); `wasLive` says the last running
 * snapshot had a recording or paused session, so a link that goes down
 * under it shows "!" rather than a quiet OFF.
 */
export function badgeFor(connection: ConnectionState, state: StatePayload | null, wasLive: boolean): Badge {
  const down = connection !== "connected" || (state !== null && !state.app_running);
  // A live session's warning outranks ERR: a failed link under a recording
  // is first of all a paused recording (round 36 LOW-028). A new link with
  // no snapshot yet has not shown the app back either (round 37 PR-LOW-201).
  if ((down || state === null) && wasLive) {
    return {
      text: "!",
      color: RED,
      title: "Clinic Scribe: lost the link to the app while a recording was live - it is paused",
    };
  }
  if (connection === "error") {
    return { text: "ERR", color: RED, title: "Clinic Scribe: the link to the app failed - retrying" };
  }
  if (connection === "connecting" || (connection === "connected" && state === null)) {
    return { text: "…", color: AMBER, title: "Clinic Scribe: connecting to the app" };
  }
  if (down) return { text: "OFF", color: GREY, title: "Clinic Scribe is not running" };
  const phase = state?.live?.phase;
  if (phase === "recording") return { text: "REC", color: RED, title: "Clinic Scribe: recording" };
  if (phase === "paused" || state?.block !== undefined) {
    return { text: "PAUSED", color: AMBER, title: "Clinic Scribe: recording paused" };
  }
  return { text: "OK", color: GREEN, title: "Clinic Scribe is running" };
}

export class ConnectionManager {
  state: ConnectionState = "disconnected";
  /** The app's latest `state` on the CURRENT connection (null until one arrives). */
  appState: StatePayload | null = null;
  /** The last running snapshot had a recording or paused session (the "!" badge). */
  wasLive = false;
  private port: PortLike | null = null;
  private sessionNonce: string | null = null;
  private helloRequestId: string | null = null;
  private pingRequestId: string | null = null;
  private pingOutstanding = false; // MED-005: silence between alarms = dead host
  private backoffIndex = 0;
  private reconnectScheduled = false; // LOW-007: fail()+onDisconnect must not double-step backoff

  constructor(
    private readonly api: ChromeLike,
    // The app's latest `state` snapshot, handed to the hub (`hub.ts`).
    private readonly onState: (state: StatePayload) => void = () => undefined,
    private readonly hooks: ConnectionHooks = {},
  ) {}

  /**
   * Send a `context` or `command` under this session's nonce. The whole
   * envelope must pass the extension's own mirror first; a malformed one is
   * dropped. False when not connected or refused.
   */
  send(type: "context", payload: ContextPayload): boolean;
  send(type: "command", payload: CommandPayload): boolean;
  send(type: "context" | "command", payload: ContextPayload | CommandPayload): boolean {
    if (this.state !== "connected" || !this.port || !this.sessionNonce) return false;
    const envelope = {
      protocol_version: PROTOCOL_VERSION,
      type,
      session_nonce: this.sessionNonce,
      payload: { ...payload },
    };
    try {
      parseEnvelope(envelope);
    } catch {
      return false;
    }
    try {
      this.port.postMessage(envelope);
    } catch {
      return false;
    }
    return true;
  }

  /** Full fresh handshake. Safe to call repeatedly (idempotent while connecting/connected). */
  connect(): void {
    if (this.state === "connecting" || this.state === "connected") return;
    this.reconnectScheduled = false;
    this.sessionNonce = null; // discard any stale nonce (plan acceptance criterion)
    this.appState = null;
    this.pingOutstanding = false;
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
    // HIGH-002: a host that never answers hello must not wedge us in
    // "connecting" — the watchdog fires unless hello_ack clears it.
    this.api.createAlarm(WATCHDOG_ALARM, WATCHDOG_MINUTES);
  }

  /** Periodic liveness probe (PING_ALARM); no-op unless connected. */
  ping(): void {
    if (this.state !== "connected" || !this.port || !this.sessionNonce) return;
    if (this.pingOutstanding) {
      // MED-005: previous ping never answered — the host is dead or hung.
      this.fail();
      return;
    }
    this.pingOutstanding = true;
    this.pingRequestId = this.api.newRequestId();
    this.port.postMessage(makePing(this.pingRequestId, this.sessionNonce));
  }

  /** Route an alarm firing to the matching behaviour. */
  onAlarm(name: string): void {
    if (name === RECONNECT_ALARM) this.connect();
    if (name === PING_ALARM) this.ping();
    if (name === WATCHDOG_ALARM && this.state === "connecting") this.fail();
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
      this.api.clearAlarm(WATCHDOG_ALARM);
      this.setState("connected");
      this.hooks.onHandshake?.();
      return;
    }
    if (envelope.type === "pong") {
      if (
        this.state !== "connected" ||
        envelope.session_nonce !== this.sessionNonce ||
        envelope.request_id !== this.pingRequestId
      ) {
        this.fail();
        return;
      }
      this.pingOutstanding = false;
      return;
    }
    if (envelope.type === "state") {
      if (this.state !== "connected" || envelope.session_nonce !== this.sessionNonce) {
        this.fail();
        return;
      }
      // parseEnvelope validated the payload against the v2 state shape.
      const state = envelope.payload as unknown as StatePayload;
      this.appState = state;
      if (state.app_running) {
        const phase = state.live?.phase;
        this.wasLive = phase === "recording" || phase === "paused" || state.block !== undefined;
      }
      this.refreshBadge();
      this.onState(state);
      return;
    }
    if (envelope.type === "error") {
      this.fail();
      return;
    }
    // hello/ping/context/command are host-bound; receiving one here is a broken peer.
    this.fail();
  }

  private fail(): void {
    const port = this.port;
    this.port = null;
    this.sessionNonce = null;
    this.appState = null;
    this.setState("error");
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
    this.appState = null;
    if (this.state !== "error") this.setState("disconnected");
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectScheduled) return; // LOW-007: one backoff step per failure
    this.reconnectScheduled = true;
    this.api.clearAlarm(WATCHDOG_ALARM);
    const minutes = BACKOFF_MINUTES[Math.min(this.backoffIndex, BACKOFF_MINUTES.length - 1)];
    this.backoffIndex += 1;
    this.api.createAlarm(RECONNECT_ALARM, minutes ?? 5);
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    this.refreshBadge();
    this.hooks.onChange?.(state);
  }

  private refreshBadge(): void {
    const badge = badgeFor(this.state, this.appState, this.wasLive);
    this.api.setBadge(badge.text, badge.color, badge.title);
  }
}
