// The service worker's logic (Cliniko workflow safeguards plan Task 6.2),
// kept free of `chrome` so it is testable: `background.ts` wires Chrome's
// events to these methods and gives it a `HubApi` over the real APIs.
//
// What the hub does, and what it never does:
// - It relays: Chrome's tab events become `context` reports (through
//   `ContextReporter`, the one producer), the app's `state` becomes each
//   Cliniko tab's slice and the side panel's view, and a click becomes a
//   `command`. The app decides every outcome (Constraint 3); a refused
//   command comes back in `state.last_refusal`.
// - SENDERS (D2). A command is accepted only from the side panel — this
//   extension's own panel page, not a tab — or from the page script in the
//   top frame of a tab whose URL is on an allow-listed host; the page script
//   may send only the block's three actions. Everything is rebuilt from
//   named fields, and `ConnectionManager.send` refuses an envelope the
//   extension's own protocol mirror does not accept.
// - NAMES. A patient's name is held only in the latest `state` in memory and
//   passed to the panel and to its own clinic's tabs; nothing here writes
//   `chrome.storage` or logs a payload.
// - "Resume previous" goes to the recording's note: a tracked tab already
//   showing it is brought forward; otherwise the tab the click came from (or
//   the focused one) is sent to the URL built from the allow-list and the
//   live session's ids — never from a URL anyone supplied.
// - After an install or update it re-injects the page script into open
//   Cliniko tabs (D13), and the panel says "Restoring the safeguards on this
//   tab…" for such a tab until its page script says hello.

import type { ConnectionState } from "./connection";
import type { PageSlice, TabSnapshot } from "./context";
import { ContextReporter, clinikoHost, noteKey, noteUrl, sliceFor } from "./context";
import type { CommandAction, CommandPayload, ContextPayload, StatePayload } from "./protocol";
import { COMMAND_ACTIONS, HOST_PATTERN, ID_PATTERN, LIMITS, SESSION_REF_PATTERN } from "./protocol";

export const PANEL_PORT = "scribe-panel";

// --- messages between the worker, the page script and the panel ---------------

export type ToPage = { kind: "slice"; slice: PageSlice };

export type FromPage =
  | { kind: "hello"; href: string }
  | { kind: "href"; href: string }
  | { kind: "block"; action: "finish" | "resume_previous" | "discard"; session_ref: string; state_rev: number; confirmed?: true };

export type FocusKind = "none" | "not_cliniko" | "clinic_not_set_up" | "cliniko";

export interface PanelView {
  connection: ConnectionState;
  /** The app's latest snapshot on the current connection; null while down. */
  state: StatePayload | null;
  /** The focused tab: its kind, whether its page script is being restored, and its id when on Cliniko. */
  focus: { kind: FocusKind; restoring: boolean; tab_id?: number };
}

export type ToPanel = { kind: "view"; view: PanelView };

export interface PanelCommand {
  kind: "command";
  action: CommandAction;
  state_rev: number;
  session_ref?: string;
  confirmed?: true;
  consent?: true;
  target?: { tab_id: number; clinic_host: string; patient_id: string; note_id: string };
}

export interface SenderLike {
  id?: string | undefined;
  url?: string | undefined;
  frameId?: number | undefined;
  tab?: { id?: number | undefined; url?: string | undefined; windowId?: number | undefined } | undefined;
}

export interface PanelPortLike {
  name: string;
  sender?: SenderLike | undefined;
  postMessage(message: ToPanel): void;
  disconnect(): void;
  onMessage: { addListener(cb: (message: unknown) => void): void };
  onDisconnect: { addListener(cb: () => void): void };
}

export interface HubApi {
  extensionId: string;
  panelUrl: string;
  pageScriptFiles(): string[];
  queryTabs(): Promise<TabSnapshot[]>;
  getTab(tabId: number): Promise<TabSnapshot | null>;
  lastFocusedWindow(): Promise<number | null>;
  sendToTab(tabId: number, message: ToPage): void;
  navigateTab(tabId: number, url: string): void;
  activateTab(tabId: number, windowId: number): void;
  openTab(url: string): void;
  injectPageScript(tabId: number, files: string[]): Promise<boolean>;
}

/** The link to the native host (`ConnectionManager`). */
export interface LinkLike {
  readonly state: ConnectionState;
  readonly appState: StatePayload | null;
  readonly wasLive: boolean;
  send(type: "context", payload: ContextPayload): boolean;
  send(type: "command", payload: CommandPayload): boolean;
}

const BLOCK_ACTIONS: ReadonlySet<string> = new Set(["finish", "resume_previous", "discard"]);
const MAX_HREF_CHARS = 2048;
const RESYNC_ATTEMPTS = 3;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStateRev(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= LIMITS.max_state_rev;
}

function isSessionRef(value: unknown): value is string {
  return typeof value === "string" && SESSION_REF_PATTERN.test(value);
}

function stripQuery(url: string): string {
  return url.split(/[?#]/)[0] ?? "";
}

export class Hub {
  readonly reporter: ContextReporter;
  private link: LinkLike | null = null;
  private readonly panels = new Set<PanelPortLike>();
  private readonly sentSlices = new Map<number, string>();
  private readonly restoring = new Set<number>();
  private allowList: readonly string[] = [];
  private lastRev: number | null = null;
  private needSync = true;
  private syncing = false;
  // Round 37 PR-MED-200: Chrome answers a lookup (`queryTabs`, `getTab`) with
  // the state when it was asked, so an answer can land after a newer event.
  // Every tab or window event bumps `events`; `touched` and `activated` hold
  // the count at a tab's last event and at a window's last activation. An
  // answer is applied only when nothing newer concerns it: a newer event
  // carried the truth itself or started its own, fresher lookup.
  private events = 0;
  private readonly touched = new Map<number, number>();
  private readonly activated = new Map<number, number>();

  constructor(private readonly api: HubApi) {
    this.reporter = new ContextReporter((payload) => this.link?.send("context", payload) ?? false);
  }

  attach(link: LinkLike): void {
    this.link = link;
  }

  // --- the link ------------------------------------------------------------------

  /** A new host (so a new pipe client): the app knows no tab yet. */
  handshake(): void {
    this.needSync = true;
    this.lastRev = null;
    this.reporter.deactivate();
  }

  connectionChanged(): void {
    if (this.link?.state !== "connected") {
      this.needSync = true;
      this.lastRev = null;
      this.reporter.deactivate();
    }
    this.render();
  }

  stateArrived(state: StatePayload): void {
    if (!state.app_running) {
      // Nothing is reported to an absent app; its return is a new client.
      this.needSync = true;
      this.lastRev = null;
      this.allowList = [];
      this.reporter.deactivate();
      this.render();
      return;
    }
    // A snapshot whose rev went back is a restarted app: re-report.
    if (this.lastRev !== null && state.state_rev < this.lastRev) this.needSync = true;
    this.lastRev = state.state_rev;
    this.allowList = [...state.allow_list];
    if (this.needSync) {
      this.needSync = false;
      void this.resync();
    } else if (!this.syncing) {
      this.reporter.setAllowList(state.allow_list); // a resync in flight reads the latest itself
    }
    this.render();
  }

  private async resync(): Promise<void> {
    if (this.syncing) {
      this.needSync = true;
      return;
    }
    this.syncing = true;
    let done = false;
    try {
      for (let attempt = 0; attempt < RESYNC_ATTEMPTS && !done; attempt += 1) {
        const start = this.events;
        const [tabs, focused] = await Promise.all([this.api.queryTabs(), this.api.lastFocusedWindow()]);
        const state = this.link?.appState;
        if (this.link?.state !== "connected" || !state?.app_running) {
          this.needSync = true;
          return;
        }
        if (this.events !== start) continue; // a tab moved while Chrome answered: ask again
        this.reporter.resync(tabs, focused, state.allow_list);
        this.sentSlices.clear();
        done = true;
      }
      // Still moving: stay inert (nothing reported); the next event or snapshot asks again.
      if (!done) this.needSync = true;
    } catch {
      this.needSync = true;
    } finally {
      this.syncing = false;
    }
    this.render();
  }

  /** Count a tab or window event (see `events`); a resync still owed runs now. */
  private bump(tabId?: number, activeIn?: number): void {
    this.events += 1;
    if (tabId !== undefined) this.touched.set(tabId, this.events);
    if (activeIn !== undefined) this.activated.set(activeIn, this.events);
    if (this.needSync && !this.syncing && this.link?.state === "connected" && this.link.appState?.app_running === true) {
      this.needSync = false;
      void this.resync();
    }
  }

  /** Fetch a tab Chrome told us about and apply it unless a newer event overtook the answer. */
  private lookUp(tabId: number, adjust: (tab: TabSnapshot) => TabSnapshot = (tab) => tab): void {
    const start = this.events;
    void this.api.getTab(tabId).then((found) => {
      if (found === null) return;
      const tab = adjust(found);
      if ((this.touched.get(tabId) ?? 0) > start) return;
      if (tab.active && (this.activated.get(tab.windowId) ?? 0) > start) return;
      this.apply(tab);
    });
  }

  private apply(tab: TabSnapshot): void {
    this.reporter.tabUpdated(tab);
    this.render();
  }

  // --- Chrome's tab events --------------------------------------------------------

  tabUpdated(tab: TabSnapshot): void {
    this.bump(tab.id, tab.active ? tab.windowId : undefined);
    this.apply(tab);
  }

  tabActivated(tabId: number, windowId: number): void {
    this.bump(tabId, windowId);
    if (this.reporter.tabActivated(tabId, windowId)) {
      this.render();
      return;
    }
    this.lookUp(tabId, (tab) => ({ ...tab, active: true, windowId }));
  }

  tabRemoved(tabId: number): void {
    this.bump(tabId);
    this.reporter.tabRemoved(tabId);
    this.sentSlices.delete(tabId);
    this.restoring.delete(tabId);
    this.render();
  }

  tabReplaced(addedTabId: number, removedTabId: number): void {
    this.tabRemoved(removedTabId);
    this.bump(addedTabId);
    this.lookUp(addedTabId);
  }

  windowFocused(windowId: number, none: number): void {
    if (windowId === none) return;
    this.bump();
    this.reporter.windowFocused(windowId);
    this.render();
  }

  // --- install / update: re-inject the page script (D13) --------------------------

  async installed(reason: string): Promise<void> {
    if (reason !== "install" && reason !== "update") return;
    const files = this.api.pageScriptFiles();
    if (files.length === 0) return;
    let tabs: TabSnapshot[];
    try {
      tabs = await this.api.queryTabs();
    } catch {
      return;
    }
    for (const tab of tabs) {
      if (clinikoHost(tab.url) === null) continue;
      this.restoring.add(tab.id);
      this.sentSlices.delete(tab.id);
      void this.api.injectPageScript(tab.id, files).then((ok) => {
        if (!ok) this.restoring.delete(tab.id);
        this.render();
      });
    }
    this.render();
  }

  // --- the page script --------------------------------------------------------------

  /** A message from a page script. Returns nothing; replies go by `sendToTab`. */
  pageMessage(message: unknown, sender: SenderLike): void {
    const tabId = sender.tab?.id;
    const senderUrl = sender.tab?.url;
    if (sender.id !== this.api.extensionId || tabId === undefined || sender.frameId !== 0) return;
    const host = clinikoHost(senderUrl);
    if (host === null || senderUrl === undefined || !isObject(message)) return;
    const kind = message["kind"];
    if (kind === "hello" || kind === "href") {
      const href = message["href"];
      let url = senderUrl;
      if (typeof href === "string" && href.length <= MAX_HREF_CHARS && clinikoHost(href) === host) url = href;
      if (kind === "hello") {
        this.restoring.delete(tabId);
        this.sentSlices.delete(tabId); // a fresh page script gets its slice even if unchanged
      }
      this.bump(tabId);
      const known = this.reporter.snapshot(tabId);
      if (known !== null) {
        this.apply({ ...known, url });
      } else {
        this.lookUp(tabId); // Chrome's own answer is newer than the page's message (round 37 PR-MED-200)
      }
      return;
    }
    if (kind === "block") this.blockCommand(message, tabId, host);
  }

  private blockCommand(message: Record<string, unknown>, tabId: number, host: string): void {
    const state = this.link?.appState;
    const action = message["action"];
    const ref = message["session_ref"];
    const rev = message["state_rev"];
    if (!state?.app_running || !state.allow_list.includes(host)) return;
    if (typeof action !== "string" || !BLOCK_ACTIONS.has(action) || !isSessionRef(ref) || !isStateRev(rev)) return;
    const command: CommandPayload = { action: action as CommandAction, state_rev: rev, session_ref: ref };
    if (action === "discard") {
      if (message["confirmed"] !== true) return; // the second click is required
      command.confirmed = true;
    }
    this.sendCommand(command, tabId);
  }

  // --- the side panel ----------------------------------------------------------------

  panelConnected(port: PanelPortLike): void {
    const sender = port.sender;
    if (
      port.name !== PANEL_PORT ||
      sender?.id !== this.api.extensionId ||
      sender.tab !== undefined ||
      sender.url === undefined ||
      stripQuery(sender.url) !== this.api.panelUrl
    ) {
      port.disconnect();
      return;
    }
    this.panels.add(port);
    port.onDisconnect.addListener(() => this.panels.delete(port));
    port.onMessage.addListener((message) => this.panelMessage(message));
    port.postMessage({ kind: "view", view: this.panelView() });
  }

  private panelMessage(message: unknown): void {
    if (!isObject(message) || message["kind"] !== "command") return;
    const action = message["action"];
    const rev = message["state_rev"];
    if (typeof action !== "string" || !(COMMAND_ACTIONS as readonly string[]).includes(action) || !isStateRev(rev)) {
      return;
    }
    const command: CommandPayload = { action: action as CommandAction, state_rev: rev };
    const ref = message["session_ref"];
    if (ref !== undefined) {
      if (!isSessionRef(ref)) return;
      command.session_ref = ref;
    }
    if (action === "discard") {
      if (message["confirmed"] !== true) return;
      command.confirmed = true;
    }
    if (action === "start") {
      const target = message["target"];
      if (message["consent"] !== true || !isObject(target)) return; // the tick is required
      const tabId = target["tab_id"];
      const clinicHost = target["clinic_host"];
      const patientId = target["patient_id"];
      const noteId = target["note_id"];
      if (
        typeof tabId !== "number" ||
        !Number.isInteger(tabId) ||
        typeof clinicHost !== "string" ||
        !HOST_PATTERN.test(clinicHost) ||
        typeof patientId !== "string" ||
        !ID_PATTERN.test(patientId) ||
        typeof noteId !== "string" ||
        !ID_PATTERN.test(noteId)
      ) {
        return;
      }
      command.consent = { confirmed: true, text_version: "recording-consent-v1" };
      command.target = { tab_id: tabId, clinic_host: clinicHost, patient_id: patientId, note_id: noteId };
    }
    this.sendCommand(command, null);
  }

  private sendCommand(command: CommandPayload, fromTab: number | null): void {
    const link = this.link;
    if (link === null) return;
    const sent = link.send("command", command);
    if (sent && command.action === "resume_previous") this.goToRecordingNote(command.session_ref, fromTab);
  }

  /** "Resume previous": bring the recording's note forward (see the module docstring). */
  private goToRecordingNote(sessionRef: string | undefined, fromTab: number | null): void {
    const state = this.link?.appState;
    const live = state?.live;
    if (!state || !live || live.session_ref !== sessionRef || !live.linked) return;
    const { clinic_host: host, patient_id: patientId, note_id: noteId } = live;
    const url = noteUrl(host, patientId, noteId, state.allow_list);
    if (url === null || host === undefined || patientId === undefined || noteId === undefined) return;
    const key = noteKey({ page: "note", host, patient_id: patientId, note_id: noteId });
    const showing = key === null ? [] : this.reporter.tabsShowing(key);
    const focused = this.reporter.focusedTab();
    if (focused !== null && showing.includes(focused)) return; // already on screen
    const existing = showing[0];
    if (existing !== undefined) {
      const snapshot = this.reporter.snapshot(existing);
      if (snapshot !== null) this.api.activateTab(existing, snapshot.windowId);
      return;
    }
    // Only a tab already on an allow-listed Cliniko page is navigated; any
    // other tab is left alone and the note opens in a new one (round 36 LOW-030).
    const target = fromTab ?? focused;
    if (target !== null && this.reporter.view(target).page !== "not_cliniko") {
      this.api.navigateTab(target, url);
      return;
    }
    this.api.openTab(url);
  }

  // --- rendering -----------------------------------------------------------------

  panelView(): PanelView {
    const link = this.link;
    const state = link?.state === "connected" ? link.appState : null;
    return { connection: link?.state ?? "disconnected", state, focus: this.focusInfo() };
  }

  private focusInfo(): PanelView["focus"] {
    const tabId = this.reporter.focusedTab();
    if (tabId === null) return { kind: "none", restoring: false };
    const host = clinikoHost(this.reporter.url(tabId));
    const restoring = this.restoring.has(tabId);
    if (host === null) return { kind: "not_cliniko", restoring: false };
    if (!this.allowList.includes(host)) return { kind: "clinic_not_set_up", restoring, tab_id: tabId };
    return { kind: "cliniko", restoring, tab_id: tabId };
  }

  /** Push the panel's view, and each Cliniko tab's slice when it changed. */
  render(): void {
    const view = this.panelView();
    for (const port of this.panels) {
      try {
        port.postMessage({ kind: "view", view });
      } catch {
        this.panels.delete(port);
      }
    }
    const link = this.link;
    const state = link?.state === "connected" ? link.appState : null;
    const wasLive = link?.wasLive ?? false;
    for (const tabId of this.reporter.clinikoTabs()) {
      const host = clinikoHost(this.reporter.url(tabId));
      const slice = sliceFor(state, tabId, host, this.allowList, wasLive);
      const text = JSON.stringify(slice);
      if (this.sentSlices.get(tabId) === text) continue;
      this.sentSlices.set(tabId, text);
      this.api.sendToTab(tabId, { kind: "slice", slice });
    }
  }
}
