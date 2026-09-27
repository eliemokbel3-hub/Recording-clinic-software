// Step 7: connection-manager tests with a mocked chrome surface.
import { describe, expect, test } from "vitest";

import type { ChromeLike, PortLike } from "./connection";
import { ConnectionManager, PING_ALARM, RECONNECT_ALARM, WATCHDOG_ALARM, badgeFor } from "./connection";
import type { StatePayload } from "./protocol";
import { PROTOCOL_VERSION } from "./protocol";

const NONCE = "n".repeat(32);

class FakePort implements PortLike {
  sent: unknown[] = [];
  private messageListeners: ((m: unknown) => void)[] = [];
  private disconnectListeners: (() => void)[] = [];
  disconnected = false;

  postMessage(message: unknown): void {
    this.sent.push(message);
  }
  disconnect(): void {
    this.disconnected = true;
  }
  onMessage = {
    addListener: (cb: (m: unknown) => void) => this.messageListeners.push(cb),
  };
  onDisconnect = {
    addListener: (cb: () => void) => this.disconnectListeners.push(cb),
  };
  receive(message: unknown): void {
    for (const cb of this.messageListeners) cb(message);
  }
  drop(): void {
    for (const cb of this.disconnectListeners) cb();
  }
}

class FakeChrome implements ChromeLike {
  ports: FakePort[] = [];
  alarms: { name: string; delay: number }[] = [];
  cleared: string[] = [];
  badges: [string, string][] = [];
  private counter = 0;

  connectNative(): FakePort {
    const port = new FakePort();
    this.ports.push(port);
    return port;
  }
  createAlarm(name: string, delayInMinutes: number): void {
    this.alarms.push({ name, delay: delayInMinutes });
  }
  clearAlarm(name: string): void {
    this.cleared.push(name);
  }
  setBadge(text: string, color: string): void {
    this.badges.push([text, color]);
  }
  newRequestId(): string {
    return `req-${++this.counter}`;
  }
  get lastPort(): FakePort {
    const port = this.ports[this.ports.length - 1];
    if (!port) throw new Error("no port");
    return port;
  }
}

function ack(requestId: string, nonce: string = NONCE) {
  return {
    protocol_version: PROTOCOL_VERSION,
    type: "hello_ack",
    request_id: requestId,
    session_nonce: nonce,
    payload: {},
  };
}

function state(nonce: string, refused: boolean) {
  const payload: Record<string, unknown> = {
    state_rev: 3,
    app_running: true,
    allow_list: ["example-clinic.au1.cliniko.com"],
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
  };
  if (refused) {
    payload["last_refusal"] = {
      action: "start",
      reason: "not_verified",
      message: "Recording was not started: Cliniko did not verify the note.",
    };
  }
  return { protocol_version: PROTOCOL_VERSION, type: "state", session_nonce: nonce, payload };
}

function handshake(): { api: FakeChrome; manager: ConnectionManager } {
  const api = new FakeChrome();
  const manager = new ConnectionManager(api);
  manager.connect();
  api.lastPort.receive(ack("req-1"));
  return { api, manager };
}

describe("handshake", () => {
  test("hello then valid ack connects and clears the reconnect alarm", () => {
    const { api, manager } = handshake();
    expect(manager.state).toBe("connected");
    expect(api.lastPort.sent[0]).toMatchObject({ type: "hello", request_id: "req-1" });
    expect(api.cleared).toContain(RECONNECT_ALARM);
    // Connected to the host, but the app has not answered yet (Task 6.2).
    expect(api.badges.at(-1)?.[0]).toBe("…");
    api.lastPort.receive(state(NONCE, false));
    expect(api.badges.at(-1)).toEqual(["OK", "#2e7d32"]);
  });

  test("the handshake hook fires once per fresh handshake", () => {
    const api = new FakeChrome();
    let handshakes = 0;
    const manager = new ConnectionManager(api, undefined, { onHandshake: () => (handshakes += 1) });
    manager.connect();
    api.lastPort.receive(ack("req-1"));
    expect(handshakes).toBe(1);
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.receive(ack("req-2"));
    expect(handshakes).toBe(2);
  });

  test("ack with mismatched request_id fails and schedules reconnect", () => {
    const api = new FakeChrome();
    const manager = new ConnectionManager(api);
    manager.connect();
    api.lastPort.receive(ack("req-999"));
    expect(manager.state).toBe("error");
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(true);
  });

  test("malformed ack (missing nonce) fails", () => {
    const api = new FakeChrome();
    const manager = new ConnectionManager(api);
    manager.connect();
    api.lastPort.receive({ protocol_version: PROTOCOL_VERSION, type: "hello_ack", request_id: "req-1", payload: {} });
    expect(manager.state).toBe("error");
  });

  test("connect is idempotent while connecting/connected", () => {
    const { api, manager } = handshake();
    manager.connect();
    expect(api.ports.length).toBe(1);
  });
});

describe("ping/pong", () => {
  test("pong echoing nonce and request_id keeps the session", () => {
    const { api, manager } = handshake();
    manager.onAlarm(PING_ALARM);
    expect(api.lastPort.sent[1]).toMatchObject({ type: "ping", session_nonce: NONCE });
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "pong",
      request_id: "req-2",
      session_nonce: NONCE,
      payload: {},
    });
    expect(manager.state).toBe("connected");
  });

  test("pong with foreign nonce disconnects", () => {
    const { api, manager } = handshake();
    manager.onAlarm(PING_ALARM);
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "pong",
      request_id: "req-2",
      session_nonce: "x".repeat(32),
      payload: {},
    });
    expect(manager.state).toBe("error");
    expect(api.lastPort.disconnected).toBe(true);
  });

  test("ping is a no-op when not connected", () => {
    const api = new FakeChrome();
    const manager = new ConnectionManager(api);
    manager.ping();
    expect(api.ports.length).toBe(0);
  });
});

describe("disconnect and reconnect", () => {
  test("host drop schedules backoff reconnect with growing delays", () => {
    const { api, manager } = handshake();
    api.lastPort.drop();
    expect(manager.state).toBe("disconnected");
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.drop();
    const delays = api.alarms.filter((a) => a.name === RECONNECT_ALARM).map((a) => a.delay);
    expect(delays).toEqual([0.5, 1, 2]);
  });

  test("every reconnect is a fresh handshake with a new request_id and nonce", () => {
    const { api, manager } = handshake();
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    expect(api.ports.length).toBe(2);
    expect(api.lastPort.sent[0]).toMatchObject({ type: "hello", request_id: "req-2" });
    api.lastPort.receive(ack("req-2", "m".repeat(32)));
    expect(manager.state).toBe("connected");
    manager.onAlarm(PING_ALARM);
    expect(api.lastPort.sent[1]).toMatchObject({ session_nonce: "m".repeat(32) });
  });

  test("a pong carrying the STALE pre-reconnect nonce is rejected (LOW-017)", () => {
    const { api, manager } = handshake(); // session nonce = NONCE
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.receive(ack("req-2", "m".repeat(32))); // fresh nonce
    manager.onAlarm(PING_ALARM);
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "pong",
      request_id: "req-3",
      session_nonce: NONCE, // stale nonce from the previous session
      payload: {},
    });
    expect(manager.state).toBe("error");
  });

  test("watchdog fires while connecting -> error + reconnect scheduled (HIGH-002)", () => {
    const api = new FakeChrome();
    const manager = new ConnectionManager(api);
    manager.connect(); // host never answers hello
    expect(api.alarms.some((a) => a.name === WATCHDOG_ALARM)).toBe(true);
    manager.onAlarm(WATCHDOG_ALARM);
    expect(manager.state).toBe("error");
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(true);
  });

  test("watchdog is cleared by a successful handshake", () => {
    const { api, manager } = handshake();
    expect(api.cleared).toContain(WATCHDOG_ALARM);
    manager.onAlarm(WATCHDOG_ALARM); // late fire must be a no-op when connected
    expect(manager.state).toBe("connected");
  });

  test("silent host: second ping alarm without a pong fails the session (MED-005)", () => {
    const { api, manager } = handshake();
    manager.onAlarm(PING_ALARM); // ping sent, never answered
    expect(manager.state).toBe("connected");
    manager.onAlarm(PING_ALARM); // outstanding ping detected
    expect(manager.state).toBe("error");
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(true);
  });

  test("answered pings keep the session healthy across alarms", () => {
    const { api, manager } = handshake();
    for (const requestId of ["req-2", "req-3"]) {
      manager.onAlarm(PING_ALARM);
      api.lastPort.receive({
        protocol_version: PROTOCOL_VERSION,
        type: "pong",
        request_id: requestId,
        session_nonce: NONCE,
        payload: {},
      });
    }
    expect(manager.state).toBe("connected");
  });

  test("backoff resets after a successful handshake", () => {
    const { api, manager } = handshake();
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.receive(ack("req-2"));
    expect(manager.state).toBe("connected");
    api.lastPort.drop();
    const delays = api.alarms.filter((a) => a.name === RECONNECT_ALARM).map((a) => a.delay);
    expect(delays.at(-1)).toBe(0.5);
  });

  test("a state carrying a refusal is delivered and keeps the connection (Constraint 9)", () => {
    const api = new FakeChrome();
    const states: StatePayload[] = [];
    const manager = new ConnectionManager(api, (state) => states.push(state));
    manager.connect();
    api.lastPort.receive(ack("req-1"));
    api.lastPort.receive(state(NONCE, true));
    expect(manager.state).toBe("connected");
    expect(api.lastPort.disconnected).toBe(false);
    expect(states).toHaveLength(1);
    expect(states[0]?.last_refusal).toMatchObject({ action: "start", reason: "not_verified" });
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(false);
  });

  test("a state with a foreign nonce disconnects and is not delivered", () => {
    const api = new FakeChrome();
    const states: StatePayload[] = [];
    const manager = new ConnectionManager(api, (s) => states.push(s));
    manager.connect();
    api.lastPort.receive(ack("req-1"));
    api.lastPort.receive(state("x".repeat(32), false));
    expect(manager.state).toBe("error");
    expect(states).toHaveLength(0);
  });

  test("a state before the handshake completes is a broken peer", () => {
    const api = new FakeChrome();
    const states: StatePayload[] = [];
    const manager = new ConnectionManager(api, (s) => states.push(s));
    manager.connect();
    api.lastPort.receive(state(NONCE, false));
    expect(manager.state).toBe("error");
    expect(states).toHaveLength(0);
  });

  test("a state keeps the latest snapshot on the manager and a disconnect clears it", () => {
    const { api, manager } = handshake();
    api.lastPort.receive(state(NONCE, false));
    expect(manager.appState?.state_rev).toBe(3);
    api.lastPort.drop();
    expect(manager.appState).toBeNull();
  });

  test("typed error envelope from host disconnects and schedules reconnect", () => {
    const { api, manager } = handshake();
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "error",
      payload: { code: "internal", message: "boom" },
    });
    expect(manager.state).toBe("error");
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(true);
  });
});

const LIVE = {
  session_ref: "AbCdEfGhIjKlMnOpQrStUv_-",
  linked: false,
  recorded_seconds: 12,
  consent_confirmed_at: "2026-09-27T01:31:02Z",
};

function snapshot(extra: Partial<StatePayload> = {}): StatePayload {
  return {
    state_rev: 4,
    app_running: true,
    allow_list: [],
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
    ...extra,
  };
}

describe("the badge reflects the app (D1, Task 6.2)", () => {
  test.each([
    ["error", null, false, "ERR"],
    ["connecting", null, false, "…"],
    ["connected", null, false, "…"],
    ["disconnected", null, false, "OFF"],
    ["connected", { ...snapshot(), app_running: false }, false, "OFF"],
    ["connected", snapshot(), false, "OK"],
    ["connected", snapshot({ live: { ...LIVE, phase: "recording" } }), true, "REC"],
    ["connected", snapshot({ live: { ...LIVE, phase: "paused" } }), true, "PAUSED"],
    ["connected", snapshot({ live: { ...LIVE, phase: "queued" } }), false, "OK"],
    ["disconnected", null, true, "!"],
    ["error", null, true, "!"],
    ["connecting", null, true, "!"],
    ["connected", null, true, "!"], // round 37 PR-LOW-201: a new link has not shown the app back yet
    ["connected", { ...snapshot(), app_running: false }, true, "!"],
  ] as const)("%s / %j / wasLive=%s -> %s", (connection, appState, wasLive, text) => {
    expect(badgeFor(connection, appState, wasLive).text).toBe(text);
  });

  test("a session live when the link drops leaves '!' until the app says otherwise", () => {
    const { api, manager } = handshake();
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "state",
      session_nonce: NONCE,
      payload: snapshot({ live: { ...LIVE, phase: "recording" } }),
    });
    expect(api.badges.at(-1)?.[0]).toBe("REC");
    api.lastPort.drop();
    expect(api.badges.at(-1)?.[0]).toBe("!");
    manager.onAlarm(RECONNECT_ALARM);
    api.lastPort.receive(ack("req-2"));
    expect(api.badges.at(-1)?.[0]).toBe("!"); // no snapshot yet on the new link
    api.lastPort.receive({
      protocol_version: PROTOCOL_VERSION,
      type: "state",
      session_nonce: NONCE,
      payload: snapshot(),
    });
    expect(api.badges.at(-1)?.[0]).toBe("OK");
  });
});

describe("send (Task 6.2)", () => {
  const context = { seq: 1, tab_id: 5, window_id: 1, focused: true, page: "login" as const, host: "a.au1.cliniko.com" };

  test("a valid context goes out under the session nonce", () => {
    const { api, manager } = handshake();
    expect(manager.send("context", context)).toBe(true);
    expect(api.lastPort.sent.at(-1)).toEqual({
      protocol_version: PROTOCOL_VERSION,
      type: "context",
      session_nonce: NONCE,
      payload: context,
    });
  });

  test("nothing is sent before the handshake", () => {
    const api = new FakeChrome();
    const manager = new ConnectionManager(api);
    manager.connect();
    expect(manager.send("context", context)).toBe(false);
    expect(api.lastPort.sent).toHaveLength(1); // the hello only
  });

  test("a payload the mirror refuses is dropped, never sent", () => {
    const { api, manager } = handshake();
    const before = api.lastPort.sent.length;
    // A start without its consent, and a context carrying a URL.
    expect(
      manager.send("command", {
        action: "start",
        state_rev: 1,
        target: { tab_id: 5, clinic_host: "a.au1.cliniko.com", patient_id: "1", note_id: "2" },
      }),
    ).toBe(false);
    expect(manager.send("context", { ...context, url: "https://a.au1.cliniko.com/" } as typeof context)).toBe(false);
    expect(api.lastPort.sent).toHaveLength(before);
    expect(manager.state).toBe("connected");
  });
});
