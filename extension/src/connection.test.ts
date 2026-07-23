// Step 7: connection-manager tests with a mocked chrome surface.
import { describe, expect, test } from "vitest";

import type { ChromeLike, PortLike } from "./connection";
import { ConnectionManager, PING_ALARM, RECONNECT_ALARM } from "./connection";
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
    expect(api.badges.at(-1)).toEqual(["OK", "#2e7d32"]);
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
    api.lastPort.receive({ protocol_version: 1, type: "hello_ack", request_id: "req-1", payload: {} });
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
      protocol_version: 1,
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
      protocol_version: 1,
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

  test("every reconnect is a fresh handshake with a new request_id", () => {
    const { api, manager } = handshake();
    api.lastPort.drop();
    manager.onAlarm(RECONNECT_ALARM);
    expect(api.ports.length).toBe(2);
    expect(api.lastPort.sent[0]).toMatchObject({ type: "hello", request_id: "req-2" });
    // stale nonce discarded: a pong with the OLD nonce during connecting is a failure
    api.lastPort.receive(ack("req-2", "m".repeat(32)));
    expect(manager.state).toBe("connected");
    manager.onAlarm(PING_ALARM);
    expect(api.lastPort.sent[1]).toMatchObject({ session_nonce: "m".repeat(32) });
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

  test("typed error envelope from host disconnects and schedules reconnect", () => {
    const { api, manager } = handshake();
    api.lastPort.receive({
      protocol_version: 1,
      type: "error",
      payload: { code: "internal", message: "boom" },
    });
    expect(manager.state).toBe("error");
    expect(api.alarms.some((a) => a.name === RECONNECT_ALARM)).toBe(true);
  });
});
