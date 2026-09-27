// Cliniko workflow safeguards plan Tasks 6.0 / 6.2: the service worker booted
// against the `chrome.*` fake — its listeners, the side-panel behaviour, the
// restarted worker getting the app's state back by reconnecting, re-injection
// on an update, and nothing written to `chrome.storage`.
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { PROTOCOL_VERSION } from "./protocol";
import type { FakeChrome, FakeRuntimePort } from "./test/chrome-fake";
import { EXTENSION_ID, installChromeFake, removeChromeFake } from "./test/chrome-fake";

const HOST = "example-clinic.au1.cliniko.com";
const NOTE = `https://${HOST}/patients/1001/treatment_notes/2002/edit`;
const NONCE = "n".repeat(32);

let fake: FakeChrome;

beforeEach(() => {
  vi.resetModules();
  fake = installChromeFake();
});

afterEach(() => {
  removeChromeFake();
});

async function flush(): Promise<void> {
  for (let i = 0; i < 20; i += 1) await Promise.resolve();
}

async function boot(): Promise<FakeRuntimePort> {
  await import("./background");
  const port = fake.nativePorts[0];
  if (!port) throw new Error("the worker did not connect");
  return port;
}

function handshake(port: FakeRuntimePort): void {
  const hello = port.sent[0] as { request_id: string };
  port.onMessage.emit({
    protocol_version: PROTOCOL_VERSION,
    type: "hello_ack",
    request_id: hello.request_id,
    session_nonce: NONCE,
    payload: {},
  });
}

function sendState(port: FakeRuntimePort, payload: Record<string, unknown>): void {
  port.onMessage.emit({ protocol_version: PROTOCOL_VERSION, type: "state", session_nonce: NONCE, payload });
}

const RUNNING = {
  state_rev: 1,
  app_running: true,
  allow_list: [HOST],
  hotkey: { available: false },
  spoken_pause: false,
  warnings: [],
};

test("the worker connects, opens the panel from the icon and listens to tabs", async () => {
  const port = await boot();
  expect(port.sent[0]).toMatchObject({ type: "hello" });
  expect(fake.called("sidePanel.setPanelBehavior")).toEqual([[{ openPanelOnActionClick: true }]]);
  for (const event of [
    fake.tabs.onUpdated,
    fake.tabs.onActivated,
    fake.tabs.onRemoved,
    fake.tabs.onReplaced,
    fake.windows.onFocusChanged,
    fake.runtime.onMessage,
    fake.runtime.onConnect,
    fake.runtime.onInstalled,
  ]) {
    expect(event.hasListeners()).toBe(true);
  }
});

test("a restarted worker gets the app's state by reconnecting, reports the open note and badges OK", async () => {
  fake.tabs_ = [{ id: 5, windowId: 1, active: true, url: NOTE }];
  const port = await boot();
  handshake(port);
  expect(fake.badge.text).toBe("…");
  sendState(port, {
    ...RUNNING,
    banner: { session_ref: "AbCdEfGhIjKlMnOpQrStUv_-", clinic_host: HOST, note_id: "2002", count: 1 },
  });
  await flush();
  expect(fake.badge.text).toBe("OK");
  expect(port.sent).toContainEqual({
    protocol_version: PROTOCOL_VERSION,
    type: "context",
    session_nonce: NONCE,
    payload: { seq: 1, tab_id: 5, window_id: 1, focused: true, page: "note", host: HOST, patient_id: "1001", note_id: "2002" },
  });
  expect(fake.tabMessages).toContainEqual({ tabId: 5, message: { kind: "slice", slice: { active: true, frame: null } } });
});

test("an update re-injects the page script into Cliniko tabs from the built manifest", async () => {
  fake.tabs_ = [
    { id: 5, windowId: 1, active: true, url: NOTE },
    { id: 8, windowId: 1, active: false },
  ];
  await boot();
  fake.runtime.onInstalled.emit({ reason: "update" });
  await flush();
  expect(fake.called("scripting.executeScript")).toEqual([[{ target: { tabId: 5 }, files: ["assets/page.js"] }]]);
});

test("names travel only in memory: nothing is written to chrome.storage", async () => {
  fake.tabs_ = [{ id: 5, windowId: 1, active: true, url: NOTE }];
  const port = await boot();
  handshake(port);
  sendState(port, {
    ...RUNNING,
    live: {
      session_ref: "AbCdEfGhIjKlMnOpQrStUv_-",
      phase: "paused",
      linked: true,
      recorded_seconds: 5,
      consent_confirmed_at: "2026-09-27T01:31:02Z",
      clinic_host: HOST,
      patient_id: "1001",
      note_id: "2002",
      verification: "verified",
      patient_name: "Alex Example",
    },
    block: {
      reason: "note_changed",
      session_ref: "AbCdEfGhIjKlMnOpQrStUv_-",
      clinic_host: HOST,
      clinic_label: "Example Clinic",
      patient_name: "Alex Example",
    },
  });
  await flush();
  fake.runtime.onMessage.emit(
    { kind: "block", action: "finish", session_ref: "AbCdEfGhIjKlMnOpQrStUv_-", state_rev: 1 },
    { id: EXTENSION_ID, frameId: 0, tab: { id: 5, windowId: 1, active: true, url: NOTE } },
    () => undefined,
  );
  expect(port.sent.at(-1)).toMatchObject({ type: "command", payload: { action: "finish" } });
  expect(fake.storedText()).toBe("[[],[]]");
  expect(fake.badge.text).toBe("PAUSED");
});

test("no key rides along: every message to the host is a valid envelope with nothing beyond the mirror's fields", async () => {
  fake.tabs_ = [{ id: 5, windowId: 1, active: true, url: NOTE }];
  const port = await boot();
  handshake(port);
  sendState(port, {
    ...RUNNING,
    block: { reason: "note_changed", session_ref: "AbCdEfGhIjKlMnOpQrStUv_-", clinic_host: HOST, clinic_label: "Example Clinic" },
  });
  await flush();
  // A page (or anything posing as one) adds fields; none may reach the host.
  fake.runtime.onMessage.emit(
    {
      kind: "block",
      action: "finish",
      session_ref: "AbCdEfGhIjKlMnOpQrStUv_-",
      state_rev: 1,
      api_key: "FAKEKEY0000000000000000000000000000-au1",
      target: { tab_id: 5 },
    },
    { id: EXTENSION_ID, frameId: 0, tab: { id: 5, windowId: 1, active: true, url: NOTE } },
    () => undefined,
  );
  const { parseEnvelope } = await import("./protocol");
  expect(port.sent.length).toBeGreaterThan(2);
  for (const message of port.sent) {
    expect(() => parseEnvelope(message)).not.toThrow(); // unknown keys are refused by the mirror
    expect(["hello", "ping", "context", "command"]).toContain((message as { type: string }).type);
  }
  expect(JSON.stringify(port.sent)).not.toContain("FAKEKEY");
  expect(JSON.stringify(fake.tabMessages)).not.toContain("FAKEKEY");
});
