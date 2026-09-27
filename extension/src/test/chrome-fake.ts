// A recording fake of the `chrome.*` surface the extension uses (Cliniko
// workflow safeguards plan Task 6.0). Tests install it as the global `chrome`
// before importing a module that touches `chrome` at load time (the page
// script, the side panel, the service worker), then drive its events and read
// back what was called. No network, no real browser: every call is recorded,
// and `storage` records writes so a test can prove no patient name is stored.

export class FakeEvent<A extends unknown[]> {
  readonly listeners: ((...args: A) => unknown)[] = [];

  addListener(cb: (...args: A) => unknown): void {
    this.listeners.push(cb);
  }
  removeListener(cb: (...args: A) => unknown): void {
    const at = this.listeners.indexOf(cb);
    if (at >= 0) this.listeners.splice(at, 1);
  }
  hasListeners(): boolean {
    return this.listeners.length > 0;
  }
  /** Fire the event; returns each listener's return value. */
  emit(...args: A): unknown[] {
    return [...this.listeners].map((cb) => cb(...args));
  }
}

export interface FakeTab {
  id: number;
  windowId: number;
  active: boolean;
  url?: string;
}

export interface FakeSender {
  id?: string;
  url?: string;
  tab?: FakeTab;
  frameId?: number;
}

export class FakeRuntimePort {
  readonly sent: unknown[] = [];
  readonly onMessage = new FakeEvent<[unknown]>();
  readonly onDisconnect = new FakeEvent<[]>();
  disconnected = false;
  /** The other end (set by `FakeChrome.connectPanel`). */
  peer: FakeRuntimePort | null = null;

  constructor(
    readonly name: string,
    readonly sender?: FakeSender,
  ) {}

  postMessage(message: unknown): void {
    if (this.disconnected) throw new Error("Attempting to use a disconnected port object");
    this.sent.push(message);
    // Delivered asynchronously, as Chrome does: a message posted inside
    // onConnect still reaches a listener the other side adds right after.
    const peer = this.peer;
    if (peer) {
      const copy = structuredClone(message);
      queueMicrotask(() => {
        if (!peer.disconnected) peer.onMessage.emit(copy);
      });
    }
  }
  disconnect(): void {
    if (this.disconnected) return;
    this.disconnected = true;
    const peer = this.peer;
    if (peer && !peer.disconnected) {
      peer.disconnected = true;
      peer.onDisconnect.emit();
    }
  }
}

export class FakeStorageArea {
  readonly writes: Record<string, unknown>[] = [];
  private data: Record<string, unknown> = {};

  set(items: Record<string, unknown>): Promise<void> {
    this.writes.push(structuredClone(items));
    Object.assign(this.data, items);
    return Promise.resolve();
  }
  get(): Promise<Record<string, unknown>> {
    return Promise.resolve(structuredClone(this.data));
  }
  remove(key: string): Promise<void> {
    delete this.data[key];
    return Promise.resolve();
  }
}

export const EXTENSION_ID = "mbmhglgadhdohpgbmpbjnaifjagfdfid";

/** The fake. `tabs` is the browser's tab table; tests edit it directly. */
export class FakeChrome {
  tabs_: FakeTab[] = [];
  focusedWindow = 1;
  readonly calls: { api: string; args: unknown[] }[] = [];
  readonly nativePorts: FakeRuntimePort[] = [];
  readonly tabMessages: { tabId: number; message: unknown }[] = [];
  readonly runtimeMessages: unknown[] = [];
  readonly badge = { text: "", color: "", title: "" };
  manifest: Record<string, unknown> = {
    content_scripts: [{ matches: ["https://*.cliniko.com/*"], js: ["assets/page.js"] }],
  };

  private record(api: string, ...args: unknown[]): void {
    this.calls.push({ api, args });
  }

  called(api: string): unknown[][] {
    return this.calls.filter((c) => c.api === api).map((c) => c.args);
  }

  readonly runtime = {
    id: EXTENSION_ID as string | undefined,
    lastError: undefined as { message?: string } | undefined,
    onStartup: new FakeEvent<[]>(),
    onInstalled: new FakeEvent<[{ reason: string }]>(),
    onMessage: new FakeEvent<[unknown, FakeSender, (response?: unknown) => void]>(),
    onConnect: new FakeEvent<[FakeRuntimePort]>(),
    getURL: (path: string) => `chrome-extension://${EXTENSION_ID}/${path.replace(/^\//, "")}`,
    getManifest: () => this.manifest,
    connectNative: (host: string) => {
      this.record("runtime.connectNative", host);
      const port = new FakeRuntimePort(host);
      this.nativePorts.push(port);
      return port;
    },
    sendMessage: (message: unknown) => {
      if (this.runtime.id === undefined) throw new Error("Extension context invalidated.");
      this.runtimeMessages.push(structuredClone(message));
      return Promise.resolve(undefined);
    },
    connect: (info: { name: string }) => {
      if (this.runtime.id === undefined) throw new Error("Extension context invalidated.");
      const panelSide = new FakeRuntimePort(info.name);
      const workerSide = new FakeRuntimePort(info.name, {
        id: EXTENSION_ID,
        url: this.runtime.getURL("src/panel.html"),
      });
      panelSide.peer = workerSide;
      workerSide.peer = panelSide;
      this.runtime.onConnect.emit(workerSide);
      return panelSide;
    },
  };

  readonly alarms = {
    onAlarm: new FakeEvent<[{ name: string }]>(),
    create: (name: string, info: unknown) => {
      this.record("alarms.create", name, info);
      return Promise.resolve();
    },
    clear: (name: string) => {
      this.record("alarms.clear", name);
      return Promise.resolve(true);
    },
  };

  readonly action = {
    setBadgeText: (details: { text: string }) => {
      this.badge.text = details.text;
      return Promise.resolve();
    },
    setBadgeBackgroundColor: (details: { color: string }) => {
      this.badge.color = details.color;
      return Promise.resolve();
    },
    setTitle: (details: { title: string }) => {
      this.badge.title = details.title;
      return Promise.resolve();
    },
  };

  readonly tabs = {
    onUpdated: new FakeEvent<[number, { url?: string; status?: string }, FakeTab]>(),
    onActivated: new FakeEvent<[{ tabId: number; windowId: number }]>(),
    onRemoved: new FakeEvent<[number, { windowId: number; isWindowClosing: boolean }]>(),
    onReplaced: new FakeEvent<[number, number]>(),
    query: () => Promise.resolve(this.tabs_.map((t) => ({ ...t }))),
    get: (tabId: number) => {
      const tab = this.tabs_.find((t) => t.id === tabId);
      return tab ? Promise.resolve({ ...tab }) : Promise.reject(new Error(`No tab with id: ${String(tabId)}.`));
    },
    update: (tabId: number, props: { url?: string; active?: boolean }) => {
      this.record("tabs.update", tabId, props);
      return Promise.resolve(undefined);
    },
    create: (props: { url?: string }) => {
      this.record("tabs.create", props);
      return Promise.resolve(undefined);
    },
    sendMessage: (tabId: number, message: unknown) => {
      this.tabMessages.push({ tabId, message: structuredClone(message) });
      return Promise.resolve(undefined);
    },
  };

  readonly windows = {
    WINDOW_ID_NONE: -1,
    onFocusChanged: new FakeEvent<[number]>(),
    getLastFocused: () => Promise.resolve({ id: this.focusedWindow }),
    update: (windowId: number, props: { focused?: boolean }) => {
      this.record("windows.update", windowId, props);
      return Promise.resolve(undefined);
    },
  };

  readonly scripting = {
    executeScript: (injection: unknown) => {
      this.record("scripting.executeScript", injection);
      return Promise.resolve([]);
    },
  };

  readonly sidePanel = {
    setPanelBehavior: (behavior: unknown) => {
      this.record("sidePanel.setPanelBehavior", behavior);
      return Promise.resolve();
    },
    open: (options: unknown) => {
      this.record("sidePanel.open", options);
      return Promise.resolve();
    },
  };

  readonly storage = {
    local: new FakeStorageArea(),
    session: new FakeStorageArea(),
  };

  /** Everything written to any storage area, as one JSON string. */
  storedText(): string {
    return JSON.stringify([this.storage.local.writes, this.storage.session.writes]);
  }

  /** Every message the fake carried to a tab, the runtime or a port, as one JSON string. */
  carriedText(ports: FakeRuntimePort[] = []): string {
    return JSON.stringify([
      this.tabMessages,
      this.runtimeMessages,
      this.nativePorts.map((p) => p.sent),
      ports.map((p) => p.sent),
    ]);
  }
}

/** Install a fresh fake as the global `chrome`; returns it. */
export function installChromeFake(): FakeChrome {
  const fake = new FakeChrome();
  (globalThis as unknown as { chrome: unknown }).chrome = fake;
  return fake;
}

/** Remove the global `chrome` again. */
export function removeChromeFake(): void {
  delete (globalThis as unknown as { chrome?: unknown }).chrome;
}
