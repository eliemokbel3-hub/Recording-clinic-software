// Cliniko workflow safeguards plan Tasks 6.4 / 6.5: the side panel under
// jsdom, talking to a fake worker over the `chrome.*` fake's port — the
// layouts drawn as text, the consent tick rules, the commands each button
// sends, Discard's second click, the banner, the refusal line, reconnecting
// after a worker restart, and nothing written to storage.
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type { PanelView } from "./hub";
import { DISARM_MS, RECONNECT_MS } from "./panel";
import { CONNECTING, CONSENT_TEXT } from "./panel-view";
import type { StatePayload } from "./protocol";
import type { FakeChrome, FakeRuntimePort } from "./test/chrome-fake";
import { installChromeFake, removeChromeFake } from "./test/chrome-fake";

const HOST = "example-clinic.au1.cliniko.com";
const REF = "AbCdEfGhIjKlMnOpQrStUv_-";
const OLD_REF = "ZyXwVuTsRqPoNmLkJiHgFe01";
const MARKUP = '<img src=x onerror="alert(1)"><b>Alex</b> Example';

let fake: FakeChrome;
let workers: FakeRuntimePort[];
let commands: unknown[];

beforeEach(() => {
  vi.resetModules();
  const mount = document.createElement("main");
  mount.id = "panel";
  document.body.replaceChildren(mount);
  fake = installChromeFake();
  workers = [];
  commands = [];
  fake.runtime.onConnect.addListener((port) => {
    workers.push(port);
    port.onMessage.addListener((m) => commands.push(m));
  });
});

afterEach(() => {
  vi.useRealTimers();
  removeChromeFake();
});

async function flush(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

function state(extra: Partial<StatePayload> = {}): StatePayload {
  return {
    state_rev: 21,
    app_running: true,
    allow_list: [HOST],
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
    ...extra,
  };
}

const REPORT = {
  tab_id: 5,
  clinic_host: HOST,
  patient_id: "1001",
  note_id: "2002",
  verification: "verified" as const,
  clinic_label: "Example Clinic",
  patient_name: MARKUP,
};

const LIVE = {
  session_ref: REF,
  phase: "recording" as const,
  linked: true,
  recorded_seconds: 95,
  consent_confirmed_at: "2026-09-27T01:31:02Z",
  clinic_host: HOST,
  patient_id: "1001",
  note_id: "2002",
  verification: "verified" as const,
  clinic_label: "Example Clinic",
  patient_name: MARKUP,
};

async function show(s: StatePayload | null, focus: PanelView["focus"] = { kind: "cliniko", restoring: false, tab_id: 5 }): Promise<void> {
  const worker = workers.at(-1);
  if (!worker) throw new Error("the panel did not connect");
  const view: PanelView = { connection: "connected", state: s, focus };
  worker.postMessage({ kind: "view", view });
  await flush();
}

async function open(): Promise<void> {
  await import("./panel");
}

function q(selector: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(selector);
}

function part(name: string): string | null | undefined {
  return q(`[data-part="${name}"]`)?.textContent;
}

function layout(): string | null | undefined {
  return q("[data-layout]")?.getAttribute("data-layout");
}

function click(action: string): void {
  const button = q(`button[data-action="${action}"]`);
  if (!button) throw new Error(`no ${action} button`);
  button.click();
}

function consentBox(): HTMLInputElement {
  const box = document.querySelector<HTMLInputElement>('[data-part="consent"] input[type="checkbox"]');
  if (!box) throw new Error("no consent box");
  return box;
}

function tick(): void {
  const box = consentBox();
  box.checked = true;
  box.dispatchEvent(new Event("change"));
}

function startButton(): HTMLButtonElement {
  const button = document.querySelector<HTMLButtonElement>('button[data-action="start"]');
  if (!button) throw new Error("no Start");
  return button;
}

test("it connects to the worker and shows Connecting until the first view", async () => {
  await open();
  expect(workers).toHaveLength(1);
  expect(workers[0]?.name).toBe("scribe-panel");
  expect(part("message")).toBe(CONNECTING);
});

test("each layout is drawn; a markup-bearing name stays text", async () => {
  await open();
  await show(state({ report: REPORT }));
  expect(layout()).toBe("ready");
  expect(part("patient")).toBe(MARKUP);
  expect(q("img")).toBeNull();
  expect(q("b")).toBeNull();

  await show(state({ report: { ...REPORT, verification: "checking", patient_name: undefined } as unknown as typeof REPORT }));
  expect(layout()).toBe("checking");

  await show(state({ live: LIVE }));
  expect(layout()).toBe("live");
  expect(part("timer")).toBe("1:35");
  expect(part("patient")).toBe(MARKUP);

  await show(
    state({
      live: { ...LIVE, phase: "paused" },
      block: { reason: "other_note", session_ref: REF, clinic_host: HOST, clinic_label: "Example Clinic", patient_name: MARKUP },
      report: { ...REPORT, patient_id: "1003", note_id: "2004", patient_name: "<i>Sam</i>" },
    }),
  );
  expect(layout()).toBe("blocked");
  expect(part("previous")).toBe(MARKUP);
  expect(part("current")).toBe("<i>Sam</i>");
  expect(q("img")).toBeNull();
  expect(q("i")).toBeNull();

  await show({ ...state(), app_running: false, allow_list: [] });
  expect(layout()).toBe("message");
});

test("Start is disabled until the consent box is ticked, and every Start clears it", async () => {
  await open();
  await show(state({ report: REPORT }));
  expect(consentBox().checked).toBe(false); // never pre-ticked
  expect(q('[data-part="consent"]')?.textContent?.trim()).toBe(CONSENT_TEXT);
  expect(startButton().disabled).toBe(true);
  tick();
  expect(startButton().disabled).toBe(false);
  click("start");
  await flush();
  expect(commands).toEqual([
    {
      kind: "command",
      action: "start",
      state_rev: 21,
      consent: true,
      target: { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002" },
    },
  ]);
  expect(consentBox().checked).toBe(false);
  expect(startButton().disabled).toBe(true);
});

test("the tick survives a repeated view but not a different note", async () => {
  await open();
  await show(state({ report: REPORT }));
  tick();
  await show(state({ report: REPORT, state_rev: 22 })); // same note, newer rev
  expect(consentBox().checked).toBe(true);
  await show(state({ report: { ...REPORT, patient_id: "1003", note_id: "2004" }, state_rev: 23 }));
  expect(consentBox().checked).toBe(false);
  expect(startButton().disabled).toBe(true);
});

test("Live buttons carry the live session's ref", async () => {
  await open();
  await show(state({ live: LIVE }));
  click("pause");
  click("finish");
  await show(state({ live: { ...LIVE, phase: "paused" }, state_rev: 22 }));
  click("resume");
  await flush();
  expect(commands).toEqual([
    { kind: "command", action: "pause", state_rev: 21, session_ref: REF },
    { kind: "command", action: "finish", state_rev: 21, session_ref: REF },
    { kind: "command", action: "resume", state_rev: 22, session_ref: REF },
  ]);
});

test("a queued session shows no timer and no Live buttons", async () => {
  await open();
  await show(state({ live: { ...LIVE, phase: "queued", recorded_seconds: 0 } }));
  expect(layout()).toBe("message");
  expect(q('[data-part="timer"]')).toBeNull();
  expect(q('button[data-action="pause"]')).toBeNull();
  expect(part("queued")).toBe("The last recording is waiting for review in Clinic Scribe.");
});

test("Blocked: Resume previous and Finish previous send the block's ref; Discard takes a second click", async () => {
  vi.useFakeTimers();
  await open();
  await show(
    state({
      live: { ...LIVE, phase: "paused" },
      block: { reason: "note_changed", session_ref: REF, clinic_host: HOST, clinic_label: "Example Clinic" },
    }),
  );
  click("resume_previous");
  click("finish");
  click("discard");
  await flush();
  expect(q('button[data-action="discard"]')?.textContent).toBe("Confirm discard");
  expect(part("confirm")).toContain("cannot be undone");
  vi.advanceTimersByTime(DISARM_MS);
  expect(q('button[data-action="discard"]')?.textContent).toBe("Discard previous");
  click("discard");
  click("discard");
  await flush();
  expect(commands).toEqual([
    { kind: "command", action: "resume_previous", state_rev: 21, session_ref: REF },
    { kind: "command", action: "finish", state_rev: 21, session_ref: REF },
    { kind: "command", action: "discard", confirmed: true, state_rev: 21, session_ref: REF },
  ]);
});

test("the banner's Open for review sends the banner's ref; the refusal line is an alert", async () => {
  await open();
  await show(
    state({
      banner: { session_ref: OLD_REF, clinic_host: HOST, note_id: "2002", count: 2 },
      last_refusal: { action: "open_review", reason: "review_in_progress", message: "Save or cancel the note review first." },
    }),
  );
  expect(part("banner-text")).toBe("2 unreviewed recordings for this note — Open for review");
  expect(q('[data-part="refusal"]')?.getAttribute("role")).toBe("alert");
  expect(part("refusal")).toBe("Save or cancel the note review first.");
  click("open_review");
  await flush();
  expect(commands).toEqual([{ kind: "command", action: "open_review", state_rev: 21, session_ref: OLD_REF }]);
});

test("a worker restart drops the port; the panel shows Connecting and reconnects", async () => {
  vi.useFakeTimers();
  await open();
  await show(state({ report: REPORT }));
  workers[0]?.disconnect();
  expect(part("message")).toBe(CONNECTING);
  vi.advanceTimersByTime(RECONNECT_MS);
  expect(workers).toHaveLength(2);
  await show(state({ report: REPORT }));
  expect(layout()).toBe("ready");
});

test("names never reach chrome.storage", async () => {
  await open();
  await show(state({ report: REPORT, live: { ...LIVE, phase: "queued" } }));
  tick();
  click("start");
  await flush();
  expect(fake.storedText()).toBe("[[],[]]");
});
