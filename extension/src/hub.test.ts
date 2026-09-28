// Cliniko workflow safeguards plan Tasks 6.2 / 6.5: the service worker's hub —
// sender checks, the commands it builds, "Resume previous" navigation,
// re-injection after an update, and the state a restarted worker gets back.
import { describe, expect, test } from "vitest";

import type { ConnectionState } from "./connection";
import type { TabSnapshot } from "./context";
import type { HubApi, PanelPortLike, PanelView, SenderLike, ToPage, ToPanel } from "./hub";
import { Hub, PANEL_PORT } from "./hub";
import type { CommandPayload, ContextPayload, StatePayload } from "./protocol";

const EXT = "mbmhglgadhdohpgbmpbjnaifjagfdfid";
const PANEL_URL = `chrome-extension://${EXT}/src/panel.html`;
const HOST = "example-clinic.au1.cliniko.com";
const OTHER = "other-clinic.au2.cliniko.com";
const NOTE_A = `https://${HOST}/patients/1001/treatment_notes/2002/edit`;
const NOTE_B = `https://${HOST}/patients/1003/treatment_notes/2004/edit`;
const REF = "AbCdEfGhIjKlMnOpQrStUv_-";
const OLD_REF = "ZyXwVuTsRqPoNmLkJiHgFe01";

class FakeLink {
  state: ConnectionState = "connected";
  appState: StatePayload | null = null;
  wasLive = false;
  readonly contexts: ContextPayload[] = [];
  readonly commands: CommandPayload[] = [];
  send(type: "context" | "command", payload: ContextPayload | CommandPayload): boolean {
    if (this.state !== "connected") return false;
    if (type === "context") this.contexts.push(payload as ContextPayload);
    else this.commands.push(payload as CommandPayload);
    return true;
  }
}

class FakeApi implements HubApi {
  extensionId = EXT;
  panelUrl = PANEL_URL;
  tabs: TabSnapshot[] = [];
  focused = 1;
  files = ["assets/page.js"];
  readonly toTabs: { tabId: number; message: ToPage }[] = [];
  readonly navigated: [number, string][] = [];
  readonly activated: [number, number][] = [];
  readonly opened: string[] = [];
  readonly injected: number[] = [];
  /** While set, lookups are answered later, with the state they were asked in (as Chrome does). */
  private held: (() => void)[] | null = null;
  /** Runs inside every `queryTabs` call: an event landing while Chrome answers. */
  duringQuery: (() => void) | null = null;
  hold(): void {
    this.held = [];
  }
  release(): void {
    const answers = this.held ?? [];
    this.held = null;
    for (const answer of answers) answer();
  }
  private answer<T>(value: T): Promise<T> {
    const held = this.held;
    if (held === null) return Promise.resolve(value);
    return new Promise((resolve) => held.push(() => resolve(value)));
  }
  pageScriptFiles(): string[] {
    return this.files;
  }
  queryTabs(): Promise<TabSnapshot[]> {
    const answer = this.answer(this.tabs.map((t) => ({ ...t })));
    this.duringQuery?.();
    return answer;
  }
  getTab(tabId: number): Promise<TabSnapshot | null> {
    const tab = this.tabs.find((t) => t.id === tabId);
    return this.answer(tab ? { ...tab } : null);
  }
  lastFocusedWindow(): Promise<number | null> {
    return this.answer(this.focused);
  }
  sendToTab(tabId: number, message: ToPage): void {
    this.toTabs.push({ tabId, message: structuredClone(message) });
  }
  navigateTab(tabId: number, url: string): void {
    this.navigated.push([tabId, url]);
  }
  activateTab(tabId: number, windowId: number): void {
    this.activated.push([tabId, windowId]);
  }
  openTab(url: string): void {
    this.opened.push(url);
  }
  injectPageScript(tabId: number): Promise<boolean> {
    this.injected.push(tabId);
    return Promise.resolve(true);
  }
  lastSlice(tabId: number): ToPage["slice"] | undefined {
    return this.toTabs.filter((m) => m.tabId === tabId).at(-1)?.message.slice;
  }
}

class FakePanelPort implements PanelPortLike {
  name = PANEL_PORT;
  readonly received: ToPanel[] = [];
  disconnected = false;
  private messageCb: ((m: unknown) => void) | null = null;
  constructor(readonly sender: SenderLike) {}
  postMessage(message: ToPanel): void {
    this.received.push(structuredClone(message));
  }
  disconnect(): void {
    this.disconnected = true;
  }
  onMessage = { addListener: (cb: (m: unknown) => void) => (this.messageCb = cb) };
  onDisconnect = { addListener: () => undefined };
  send(message: unknown): void {
    this.messageCb?.(message);
  }
  get view(): PanelView | undefined {
    return this.received.at(-1)?.view;
  }
}

function state(extra: Partial<StatePayload> = {}): StatePayload {
  return {
    state_rev: 10,
    app_running: true,
    allow_list: [HOST, OTHER],
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
    ...extra,
  };
}

const LIVE_A = {
  session_ref: REF,
  phase: "paused" as const,
  linked: true,
  recorded_seconds: 61,
  consent_confirmed_at: "2026-09-27T01:31:02Z",
  clinic_host: HOST,
  patient_id: "1001",
  note_id: "2002",
  verification: "verified" as const,
  clinic_label: "Example Clinic",
  patient_name: "Alex Example",
};

const BLOCK_A = {
  reason: "note_changed",
  session_ref: REF,
  clinic_host: HOST,
  clinic_label: "Example Clinic",
  patient_name: "Alex Example",
};

async function flush(): Promise<void> {
  for (let i = 0; i < 20; i += 1) await Promise.resolve();
}

async function started(tabs: TabSnapshot[], first: StatePayload = state()): Promise<{ api: FakeApi; link: FakeLink; hub: Hub }> {
  const api = new FakeApi();
  api.tabs = tabs;
  const link = new FakeLink();
  const hub = new Hub(api);
  hub.attach(link);
  hub.handshake();
  link.appState = first;
  hub.stateArrived(first);
  await flush();
  return { api, link, hub };
}

function panel(hub: Hub, sender: SenderLike = { id: EXT, url: PANEL_URL }): FakePanelPort {
  const port = new FakePanelPort(sender);
  hub.panelConnected(port);
  return port;
}

const TAB_A: TabSnapshot = { id: 5, windowId: 1, active: true, url: NOTE_A };
const TAB_MAIL: TabSnapshot = { id: 8, windowId: 1, active: false, url: undefined };

describe("reports after a handshake", () => {
  test("a worker restart re-reports every allow-listed tab and hands the panel the app's full state", async () => {
    const banner = { session_ref: OLD_REF, clinic_host: HOST, note_id: "2002", count: 1 };
    const { link, hub } = await started([TAB_A, TAB_MAIL], state({ banner }));
    expect(link.contexts.map((c) => [c.tab_id, c.page, c.focused])).toEqual([[5, "note", true]]);
    const port = panel(hub);
    expect(port.view?.state?.banner).toEqual(banner);
    expect(port.view?.state?.allow_list).toEqual([HOST, OTHER]);
    expect(port.view?.focus).toEqual({ kind: "cliniko", restoring: false, tab_id: 5 });
  });

  test("nothing is reported while the app is not running", async () => {
    const off: StatePayload = { ...state(), app_running: false, allow_list: [] };
    const { link, hub } = await started([TAB_A], off);
    hub.tabUpdated({ ...TAB_A, url: NOTE_B });
    expect(link.contexts).toEqual([]);
  });

  test("a snapshot whose rev went back (a restarted app) re-reports the tabs", async () => {
    const { link, hub } = await started([TAB_A]);
    const again = state({ state_rev: 1 });
    link.appState = again;
    hub.stateArrived(again);
    await flush();
    expect(link.contexts.filter((c) => c.tab_id === 5)).toHaveLength(2);
  });

  test("an app that stops and comes back is re-reported to", async () => {
    const { link, hub } = await started([TAB_A]);
    const off: StatePayload = { ...state(), app_running: false, allow_list: [] };
    link.appState = off;
    hub.stateArrived(off);
    const back = state({ state_rev: 12 });
    link.appState = back;
    hub.stateArrived(back);
    await flush();
    expect(link.contexts.filter((c) => c.page === "note")).toHaveLength(2);
  });
});

// Round 37 PR-MED-200: an answer from Chrome that a newer tab event overtook
// is never applied — the app must not get a stale report under a fresh seq.
describe("lookups overtaken by a newer event", () => {
  const TAB_B: TabSnapshot = { id: 6, windowId: 1, active: false, url: NOTE_B };
  const fromTab5: SenderLike = { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_A, windowId: 1 } };

  function linked(tabs: TabSnapshot[]): { api: FakeApi; link: FakeLink; hub: Hub } {
    const api = new FakeApi();
    api.tabs = tabs;
    const link = new FakeLink();
    const hub = new Hub(api);
    hub.attach(link);
    hub.handshake();
    return { api, link, hub };
  }

  function arrive(link: FakeLink, hub: Hub, snapshot: StatePayload = state()): void {
    link.appState = snapshot;
    hub.stateArrived(snapshot);
  }

  test("a tab closed while the resync query is answered is never reported", async () => {
    const { api, link, hub } = linked([TAB_A]);
    api.hold();
    arrive(link, hub);
    api.tabs = [];
    hub.tabRemoved(5);
    api.release();
    await flush();
    expect(link.contexts).toEqual([]);
  });

  test("a tab that navigates while the resync query is answered is reported with its new note only", async () => {
    const { api, link, hub } = linked([TAB_A]);
    api.hold();
    arrive(link, hub);
    const moved = { ...TAB_A, url: NOTE_B };
    api.tabs = [moved];
    hub.tabUpdated(moved);
    api.release();
    await flush();
    expect(link.contexts.map((c) => [c.tab_id, c.note_id])).toEqual([[5, "2004"]]);
  });

  test("a tab activated while the resync query is answered is the only one ever reported focused", async () => {
    const { api, link, hub } = linked([TAB_A, TAB_B]);
    api.hold();
    arrive(link, hub);
    api.tabs = [{ ...TAB_A, active: false }, { ...TAB_B, active: true }];
    hub.tabActivated(6, 1);
    api.release();
    await flush();
    expect(link.contexts.filter((c) => c.focused).map((c) => c.tab_id)).toEqual([6]);
    expect(hub.reporter.focusedTab()).toBe(6);
  });

  test("a resync overtaken on every try reports nothing, and the next event asks again", async () => {
    const { api, link, hub } = linked([TAB_A]);
    let asked = 0;
    api.duringQuery = () => {
      asked += 1;
      hub.tabUpdated(TAB_MAIL);
    };
    arrive(link, hub);
    await flush();
    expect(asked).toBe(3);
    expect(link.contexts).toEqual([]);
    api.duringQuery = null;
    hub.tabUpdated(TAB_MAIL);
    await flush();
    expect(link.contexts.map((c) => [c.tab_id, c.page])).toEqual([[5, "note"]]);
  });

  test("an older activation answered after a newer one never takes the focus", async () => {
    const { api, link, hub } = await started([TAB_A]);
    const tab7: TabSnapshot = { id: 7, windowId: 1, active: true, url: NOTE_B };
    api.tabs = [{ ...TAB_A, active: false }, tab7];
    api.hold();
    hub.tabActivated(7, 1);
    api.tabs = [TAB_A, { ...tab7, active: false }];
    hub.tabActivated(5, 1);
    api.release();
    await flush();
    expect(hub.reporter.focusedTab()).toBe(5);
    expect(link.contexts.some((c) => c.tab_id === 7 && c.focused)).toBe(false);
  });

  test("a replacing tab that navigates during its lookup keeps its new note", async () => {
    const { api, link, hub } = await started([TAB_A]);
    const swapped: TabSnapshot = { id: 9, windowId: 1, active: true, url: NOTE_A };
    api.tabs = [swapped];
    api.hold();
    hub.tabReplaced(9, 5);
    const moved = { ...swapped, url: NOTE_B };
    api.tabs = [moved];
    hub.tabUpdated(moved);
    api.release();
    await flush();
    expect(link.contexts.filter((c) => c.tab_id === 9).map((c) => c.note_id)).toEqual(["2004"]);
  });

  test("an unknown tab's hello is applied with Chrome's own URL, not the message's", async () => {
    const { api, link, hub } = await started([]);
    api.tabs = [{ id: 5, windowId: 1, active: true, url: NOTE_B }];
    hub.pageMessage({ kind: "hello", href: NOTE_A }, fromTab5);
    await flush();
    expect(link.contexts.map((c) => [c.tab_id, c.note_id])).toEqual([[5, "2004"]]);
  });

  test("an unknown tab closed during its hello's lookup is never reported", async () => {
    const { api, link, hub } = await started([]);
    api.tabs = [{ id: 5, windowId: 1, active: true, url: NOTE_A }];
    api.hold();
    hub.pageMessage({ kind: "hello", href: NOTE_A }, fromTab5);
    api.tabs = [];
    hub.tabRemoved(5);
    api.release();
    await flush();
    expect(link.contexts).toEqual([]);
  });
});

describe("page script senders", () => {
  const block ={ kind: "block", action: "finish", session_ref: REF, state_rev: 10 };
  const good: SenderLike = { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_A, windowId: 1 } };

  test("a block click from an allow-listed tab's top frame becomes a command", async () => {
    const { link, hub } = await started([TAB_A], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage(block, good);
    expect(link.commands).toEqual([{ action: "finish", state_rev: 10, session_ref: REF }]);
  });

  test.each([
    ["another extension", { ...good, id: "abcdefghijklmnopabcdefghijklmnop" }],
    ["a subframe", { ...good, frameId: 3 }],
    ["no tab", { id: EXT, frameId: 0 }],
    ["a host off the allow-list", { ...good, tab: { id: 5, url: "https://unlisted-clinic.au3.cliniko.com/x", windowId: 1 } }],
    ["a page that is not Cliniko", { ...good, tab: { id: 5, url: "https://mail.example.com/", windowId: 1 } }],
  ])("%s is refused", async (_name, sender) => {
    const { link, hub } = await started([TAB_A], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage(block, sender);
    expect(link.commands).toEqual([]);
  });

  test("a page may send only Resume previous and Finish previous — never a discard (SEC-003)", async () => {
    const { link, hub } = await started([TAB_A], state({ block: BLOCK_A, live: LIVE_A }));
    for (const action of ["start", "pause", "resume", "open_review"]) hub.pageMessage({ ...block, action }, good);
    hub.pageMessage({ ...block, action: "discard" }, good);
    hub.pageMessage({ ...block, action: "discard", confirmed: "yes" }, good);
    hub.pageMessage({ ...block, action: "discard", confirmed: true }, good);
    // Nor as a panel-shaped command sent from a page (round 63 LOW).
    hub.pageMessage({ kind: "command", action: "discard", confirmed: true, state_rev: 10, session_ref: REF }, good);
    expect(link.commands).toEqual([]);
    // The side panel's two-click Discard is unchanged.
    panel(hub).send({ kind: "command", action: "discard", confirmed: true, state_rev: 10, session_ref: REF });
    expect(link.commands).toEqual([{ action: "discard", state_rev: 10, session_ref: REF, confirmed: true }]);
  });

  test("extra fields from a page never reach the command", async () => {
    const { link, hub } = await started([TAB_A], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage({ ...block, target: { tab_id: 5 }, consent: true, url: NOTE_B }, good);
    expect(link.commands).toEqual([{ action: "finish", state_rev: 10, session_ref: REF }]);
  });

  test("a hello refreshes the tab from its own location and gets its slice again", async () => {
    const { api, link, hub } = await started([TAB_A]);
    const before = api.toTabs.length;
    hub.pageMessage({ kind: "hello", href: NOTE_B }, good);
    expect(link.contexts.at(-1)).toMatchObject({ tab_id: 5, page: "note", patient_id: "1003", note_id: "2004" });
    expect(api.toTabs.length).toBe(before + 1);
    // An href on another host is ignored; the tab's own URL stands.
    hub.pageMessage({ kind: "href", href: `https://${OTHER}/patients/9/treatment_notes/9/edit` }, good);
    expect(link.contexts.at(-1)).toMatchObject({ tab_id: 5, note_id: "2002" });
  });
});

describe("the side panel", () => {
  test.each([
    ["a tab", { id: EXT, url: PANEL_URL, tab: { id: 5, url: NOTE_A } }],
    ["another extension", { id: "abcdefghijklmnopabcdefghijklmnop", url: PANEL_URL }],
    ["another extension page", { id: EXT, url: `chrome-extension://${EXT}/src/other.html` }],
  ])("a port from %s is disconnected", async (_name, sender) => {
    const { hub } = await started([TAB_A]);
    const port = panel(hub, sender);
    expect(port.disconnected).toBe(true);
    expect(port.received).toEqual([]);
  });

  test("Start carries the consent, the target and the rendered rev", async () => {
    const { link, hub } = await started([TAB_A]);
    const port = panel(hub);
    const target = { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002" };
    port.send({ kind: "command", action: "start", state_rev: 10, target });
    expect(link.commands).toEqual([]); // no tick, no Start
    port.send({ kind: "command", action: "start", state_rev: 10, target, consent: true });
    expect(link.commands).toEqual([
      { action: "start", state_rev: 10, consent: { confirmed: true, text_version: "recording-consent-v1" }, target },
    ]);
  });

  test("a malformed panel command is dropped", async () => {
    const { link, hub } = await started([TAB_A]);
    const port = panel(hub);
    port.send({ kind: "command", action: "explode", state_rev: 10 });
    port.send({ kind: "command", action: "finish", state_rev: 10, session_ref: "short" });
    port.send({ kind: "command", action: "finish", state_rev: -1, session_ref: REF });
    port.send({ kind: "command", action: "start", state_rev: 10, consent: true, target: { tab_id: 5, clinic_host: "evil.example", patient_id: "1", note_id: "2" } });
    expect(link.commands).toEqual([]);
  });
});

describe("Resume previous", () => {
  const resume = { kind: "block", action: "resume_previous", session_ref: REF, state_rev: 10 };

  test("the clicked tab is sent to the note built from the allow-list and the live ids", async () => {
    const tabB = { ...TAB_A, url: NOTE_B };
    const { api, link, hub } = await started([tabB], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage(resume, { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_B, windowId: 1 } });
    expect(link.commands).toEqual([{ action: "resume_previous", state_rev: 10, session_ref: REF }]);
    expect(api.navigated).toEqual([[5, NOTE_A]]);
  });

  test("a tab already showing the note is brought forward instead", async () => {
    const tabB = { ...TAB_A, url: NOTE_B };
    const other = { id: 6, windowId: 2, active: true, url: NOTE_A };
    const { api, hub } = await started([tabB, other], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage(resume, { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_B, windowId: 1 } });
    expect(api.activated).toEqual([[6, 2]]);
    expect(api.navigated).toEqual([]);
  });

  test("from the panel with no Cliniko tab focused, the note opens in a new tab", async () => {
    const { api, hub } = await started([TAB_MAIL], state({ block: BLOCK_A, live: LIVE_A }));
    panel(hub).send({ kind: "command", action: "resume_previous", state_rev: 10, session_ref: REF });
    expect(api.opened).toEqual([NOTE_A]);
  });

  test("from the panel, a focused Cliniko tab of a clinic that is not set up is left alone (round 36 LOW-030)", async () => {
    const unlisted = { id: 7, windowId: 1, active: true, url: "https://unlisted-clinic.au3.cliniko.com/appointments" };
    const { api, hub } = await started([unlisted], state({ block: BLOCK_A, live: LIVE_A }));
    panel(hub).send({ kind: "command", action: "resume_previous", state_rev: 10, session_ref: REF });
    expect(api.navigated).toEqual([]);
    expect(api.opened).toEqual([NOTE_A]);
  });

  test("a host no longer on the allow-list is never navigated to", async () => {
    const tabB = { ...TAB_A, url: NOTE_B };
    const { api, hub } = await started([tabB], state({ allow_list: [HOST], block: BLOCK_A, live: { ...LIVE_A, clinic_host: OTHER } }));
    hub.pageMessage(resume, { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_B, windowId: 1 } });
    expect(api.navigated).toEqual([]);
    expect(api.opened).toEqual([]);
  });

  test("a stale ref still goes to the app (which refuses it) but moves no tab", async () => {
    const tabB = { ...TAB_A, url: NOTE_B };
    const { api, link, hub } = await started([tabB], state({ block: BLOCK_A, live: LIVE_A }));
    hub.pageMessage({ ...resume, session_ref: OLD_REF }, { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_B, windowId: 1 } });
    expect(link.commands).toHaveLength(1);
    expect(api.navigated).toEqual([]);
  });
});

describe("re-injection after an update (D13)", () => {
  test("install and update re-inject into open Cliniko tabs only, and the panel says restoring", async () => {
    const unlisted = { id: 7, windowId: 1, active: false, url: "https://unlisted-clinic.au3.cliniko.com/" };
    const { api, hub } = await started([TAB_A, TAB_MAIL, unlisted]);
    await hub.installed("update");
    expect(api.injected.sort()).toEqual([5, 7]);
    const port = panel(hub);
    expect(port.view?.focus).toEqual({ kind: "cliniko", restoring: true, tab_id: 5 });
    hub.pageMessage({ kind: "hello", href: NOTE_A }, { id: EXT, frameId: 0, tab: { id: 5, url: NOTE_A, windowId: 1 } });
    expect(port.view?.focus).toEqual({ kind: "cliniko", restoring: false, tab_id: 5 });
  });

  test("a browser update does not re-inject", async () => {
    const { api, hub } = await started([TAB_A]);
    await hub.installed("chrome_update");
    expect(api.injected).toEqual([]);
  });
});

describe("slices and names", () => {
  test("each Cliniko tab gets its slice; a non-Cliniko tab gets nothing", async () => {
    const other = { id: 9, windowId: 1, active: false, url: `https://${OTHER}/appointments` };
    const { api } = await started([TAB_A, TAB_MAIL, other], state({ block: BLOCK_A, live: LIVE_A }));
    expect(api.lastSlice(5)?.block?.previous_patient).toBe("Alex Example");
    expect(api.lastSlice(9)?.block?.same_clinic).toBe(false);
    expect(JSON.stringify(api.lastSlice(9))).not.toContain("Alex");
    expect(api.toTabs.some((m) => m.tabId === 8)).toBe(false);
  });

  test("a host that leaves the allow-list is sent the inert slice", async () => {
    const other = { id: 9, windowId: 1, active: false, url: `https://${OTHER}/appointments` };
    const { api, link, hub } = await started([TAB_A, other], state({ live: { ...LIVE_A, phase: "recording" } }));
    expect(api.lastSlice(9)).toEqual({ active: true, frame: "recording" });
    const narrowed = state({ allow_list: [HOST], state_rev: 11 });
    link.appState = narrowed;
    hub.stateArrived(narrowed);
    expect(api.lastSlice(9)).toEqual({ active: false, frame: null });
  });

  test("a dropped link leaves a live session's tabs amber, not red", async () => {
    const { api, link, hub } = await started([TAB_A], state({ live: { ...LIVE_A, phase: "recording" } }));
    link.state = "disconnected";
    link.appState = null;
    link.wasLive = true;
    hub.connectionChanged();
    expect(api.lastSlice(5)).toEqual({ active: true, frame: "paused" });
  });
});
