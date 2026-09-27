// Cliniko workflow safeguards plan Tasks 6.3 / 6.5: the page script under
// jsdom — inert until allow-listed, the frame and the block in a closed
// shadow root, text only, trusted clicks only, Discard's second click, the
// href heartbeat, teardown when the host leaves the allow-list, and the
// takeover after an extension update.
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type { PageSlice } from "./context";
import type { PageScript } from "./page";
import { DISARM_MS, MARKER } from "./page";
import type { FakeChrome } from "./test/chrome-fake";
import { EXTENSION_ID, installChromeFake, removeChromeFake } from "./test/chrome-fake";

const REF = "AbCdEfGhIjKlMnOpQrStUv_-";
const MARKUP = '<img src=x onerror="alert(1)"><b>Alex</b> Example';
const WORKER = { id: EXTENSION_ID };

let fake: FakeChrome;
const scripts: PageScript[] = [];

beforeEach(() => {
  vi.resetModules();
  for (const el of document.querySelectorAll(`[${MARKER}]`)) el.remove();
  history.replaceState({}, "", "/patients/1001/treatment_notes/2002/edit");
  fake = installChromeFake();
});

afterEach(() => {
  for (const script of scripts.splice(0)) script.stop(); // no heartbeat outlives its test
  vi.useRealTimers();
  removeChromeFake();
});

async function booted(): Promise<PageScript> {
  const mod = await import("./page");
  if (mod.pageScript === null) throw new Error("the page script did not boot");
  scripts.push(mod.pageScript);
  return mod.pageScript;
}

async function trustedScript(): Promise<PageScript> {
  const mod = await import("./page");
  mod.pageScript?.stop();
  const script = new mod.PageScript(document, chrome.runtime, { isTrusted: () => true });
  script.start();
  scripts.push(script);
  return script;
}

function deliver(slice: PageSlice, sender: { id?: string; tab?: { id: number; windowId: number; active: boolean } } = WORKER): void {
  fake.runtime.onMessage.emit({ kind: "slice", slice }, sender, () => undefined);
}

const BLOCK: PageSlice = {
  active: true,
  frame: "paused",
  block: {
    session_ref: REF,
    state_rev: 12,
    reason: "note_changed",
    same_clinic: true,
    recording_clinic: "Example Clinic",
    previous_patient: MARKUP,
    this_patient: "Sam Example",
  },
};

function part(script: PageScript, name: string): Element | null {
  return script.shadowForTests?.querySelector(`[data-part="${name}"]`) ?? null;
}

function button(script: PageScript, action: string): HTMLButtonElement {
  const found = script.shadowForTests?.querySelector<HTMLButtonElement>(`button[data-action="${action}"]`);
  if (!found) throw new Error(`no ${action} button`);
  return found;
}

function blockMessages(): unknown[] {
  return fake.runtimeMessages.filter((m) => (m as { kind?: string }).kind === "block");
}

test("it says hello once and draws nothing until its host is allow-listed", async () => {
  const script = await booted();
  expect(fake.runtimeMessages).toEqual([{ kind: "hello", href: location.href }]);
  deliver({ active: false, frame: null });
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();
  history.pushState({}, "", "/appointments");
  script.tick();
  expect(fake.runtimeMessages).toHaveLength(1); // inert: no href report
});

test("the frame is drawn red while recording and amber while paused, in a closed shadow root", async () => {
  const script = await booted();
  deliver({ active: true, frame: "recording" });
  const host = document.querySelector(`[${MARKER}]`);
  expect(host).not.toBeNull();
  expect(host?.shadowRoot).toBeNull(); // closed: the page cannot reach in
  expect(script.shadowForTests?.querySelector("[data-frame]")?.getAttribute("data-frame")).toBe("recording");
  deliver({ active: true, frame: "paused" });
  expect(script.shadowForTests?.querySelector("[data-frame]")?.getAttribute("data-frame")).toBe("paused");
  deliver({ active: true, frame: null });
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();
});

test("a markup-bearing patient name is rendered as text, never parsed", async () => {
  const script = await booted();
  deliver(BLOCK);
  expect(part(script, "previous")?.textContent).toBe(MARKUP);
  expect(part(script, "current")?.textContent).toBe("Sam Example");
  expect(script.shadowForTests?.querySelector("img")).toBeNull();
  expect(script.shadowForTests?.querySelector("b")).toBeNull();
  expect(part(script, "reason")?.textContent).toBe("This tab opened a different treatment note.");
});

test("an inherited name as the reason code shows the generic line (round 38 PR-LOW-211)", async () => {
  const script = await booted();
  const block = BLOCK.block;
  if (!block) throw new Error("BLOCK has a block");
  for (const reason of ["constructor", "toString"]) {
    deliver({ ...BLOCK, block: { ...block, reason } });
    expect(part(script, "reason")?.textContent).toBe("The recording was paused.");
  }
});

test("the machine's own pause reasons have their text (D5 as amended 2026-09-28)", async () => {
  const script = await booted();
  const block = BLOCK.block;
  if (!block) throw new Error("BLOCK has a block");
  deliver({ ...BLOCK, block: { ...block, reason: "suspend" } });
  expect(part(script, "reason")?.textContent).toBe("The computer went to sleep.");
  deliver({ ...BLOCK, block: { ...block, reason: "locked" } });
  expect(part(script, "reason")?.textContent).toBe("The computer was locked.");
});

test("a block for another clinic's recording names that clinic by label only", async () => {
  const script = await booted();
  deliver({
    active: true,
    frame: "paused",
    block: { session_ref: REF, state_rev: 12, reason: "other_note", same_clinic: false, recording_clinic: "Example Clinic" },
  });
  expect(part(script, "previous")?.textContent).toBe("Recording belongs to a patient in Example Clinic");
  expect(part(script, "current")?.textContent).toBe("The patient on this tab");
});

test("a slice from a tab or another extension is ignored", async () => {
  await booted();
  deliver(BLOCK, { id: EXTENSION_ID, tab: { id: 5, windowId: 1, active: true } });
  deliver(BLOCK, { id: "abcdefghijklmnopabcdefghijklmnop" });
  fake.runtime.onMessage.emit({ kind: "slice", slice: { active: true, frame: "red" } }, WORKER, () => undefined);
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();
});

test("a click the user did not make does nothing", async () => {
  const script = await booted();
  deliver(BLOCK);
  button(script, "finish").click(); // jsdom's click() is not trusted
  button(script, "discard").click();
  expect(blockMessages()).toEqual([]);
  expect(button(script, "discard").textContent).toBe("Discard previous");
});

test("trusted clicks carry the rendered session_ref and state_rev", async () => {
  const script = await trustedScript();
  deliver(BLOCK);
  button(script, "finish").click();
  button(script, "resume_previous").click();
  expect(blockMessages()).toEqual([
    { kind: "block", action: "finish", session_ref: REF, state_rev: 12 },
    { kind: "block", action: "resume_previous", session_ref: REF, state_rev: 12 },
  ]);
});

test("Discard needs a second click, and disarms after 15 seconds", async () => {
  vi.useFakeTimers();
  const script = await trustedScript();
  deliver(BLOCK);
  button(script, "discard").click();
  expect(blockMessages()).toEqual([]);
  expect(button(script, "discard").textContent).toBe("Confirm discard");
  expect(part(script, "confirm")?.textContent).toContain("cannot be undone");
  vi.advanceTimersByTime(DISARM_MS);
  expect(button(script, "discard").textContent).toBe("Discard previous");
  button(script, "discard").click();
  button(script, "discard").click();
  expect(blockMessages()).toEqual([{ kind: "block", action: "discard", session_ref: REF, state_rev: 12, confirmed: true }]);
});

test("an armed Discard does not carry over to another session's block", async () => {
  const script = await trustedScript();
  deliver(BLOCK);
  button(script, "discard").click();
  const other = "ZyXwVuTsRqPoNmLkJiHgFe01";
  deliver({ ...BLOCK, block: { ...(BLOCK.block as NonNullable<PageSlice["block"]>), session_ref: other } });
  expect(button(script, "discard").textContent).toBe("Discard previous");
  button(script, "discard").click();
  expect(blockMessages()).toEqual([]);
});

test("while active, an href change is reported; leaving the allow-list tears everything down", async () => {
  const script = await booted();
  deliver(BLOCK);
  history.pushState({}, "", "/patients/1003/treatment_notes/2004/edit");
  script.tick();
  expect(fake.runtimeMessages.at(-1)).toEqual({ kind: "href", href: location.href });
  deliver({ active: false, frame: null });
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();
  expect(script.shadowForTests).toBeNull();
  const count = fake.runtimeMessages.length;
  history.pushState({}, "", "/appointments");
  script.tick();
  expect(fake.runtimeMessages).toHaveLength(count);
});

test("an element the page removes is put back on the next heartbeat", async () => {
  const script = await booted();
  deliver({ active: true, frame: "recording" });
  document.querySelector(`[${MARKER}]`)?.remove();
  script.tick();
  expect(document.querySelector(`[${MARKER}]`)).not.toBeNull();
});

test("an orphaned copy tears itself down; a re-injected copy takes over", async () => {
  const script = await booted();
  deliver({ active: true, frame: "recording" });
  fake.runtime.id = undefined; // the extension was updated under this copy
  script.tick();
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();
  deliver({ active: true, frame: "recording" }, { id: EXTENSION_ID });
  expect(document.querySelector(`[${MARKER}]`)).toBeNull();

  const stale = document.createElement("div");
  stale.setAttribute(MARKER, "");
  document.documentElement.append(stale);
  fake.runtime.id = EXTENSION_ID;
  const mod = await import("./page");
  const fresh = new mod.PageScript(document, chrome.runtime);
  fresh.start();
  scripts.push(fresh);
  expect(document.querySelectorAll(`[${MARKER}]`)).toHaveLength(0);
});
