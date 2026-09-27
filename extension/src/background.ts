// MV3 service worker — wires ConnectionManager and the Hub to the real
// chrome APIs. Top-level connect() fires on every SW wake (plan executor
// facts); a restarted worker gets the app's full `state` back by
// reconnecting, because the app sends a full snapshot on every new pipe
// connection (Cliniko workflow safeguards plan D2, Task 6.2).

import type { ChromeLike, PortLike } from "./connection";
import { ConnectionManager, PING_ALARM } from "./connection";
import type { TabSnapshot } from "./context";
import type { HubApi } from "./hub";
import { Hub } from "./hub";
import { PANEL_PATH } from "./manifest-paths";

const api: ChromeLike = {
  connectNative: (hostName: string): PortLike => {
    const port = chrome.runtime.connectNative(hostName);
    return {
      postMessage: (message: unknown) => port.postMessage(message),
      disconnect: () => port.disconnect(),
      onMessage: {
        addListener: (cb: (message: unknown) => void) =>
          port.onMessage.addListener((message: unknown) => cb(message)),
      },
      onDisconnect: {
        addListener: (cb: () => void) =>
          port.onDisconnect.addListener(() => {
            // LOW-006: surface the disconnect diagnostic (e.g. "Specified
            // native messaging host not found") instead of discarding it.
            const err = chrome.runtime.lastError;
            if (err?.message) console.warn("native host disconnect:", err.message);
            cb();
          }),
      },
    };
  },
  createAlarm: (name: string, delayInMinutes: number) => {
    void chrome.alarms.create(name, { delayInMinutes });
  },
  clearAlarm: (name: string) => {
    void chrome.alarms.clear(name);
  },
  setBadge: (text: string, color: string, title?: string) => {
    void chrome.action.setBadgeText({ text });
    void chrome.action.setBadgeBackgroundColor({ color });
    if (title !== undefined) void chrome.action.setTitle({ title });
  },
  newRequestId: () => crypto.randomUUID(),
};

function snapshot(tab: chrome.tabs.Tab): TabSnapshot | null {
  if (tab.id === undefined || tab.id < 0) return null;
  return { id: tab.id, windowId: tab.windowId, active: tab.active, url: tab.url };
}

const hubApi: HubApi = {
  extensionId: chrome.runtime.id,
  panelUrl: chrome.runtime.getURL(PANEL_PATH),
  pageScriptFiles: () => chrome.runtime.getManifest().content_scripts?.[0]?.js ?? [],
  queryTabs: async () => (await chrome.tabs.query({})).flatMap((tab) => snapshot(tab) ?? []),
  getTab: async (tabId: number) => {
    try {
      return snapshot(await chrome.tabs.get(tabId));
    } catch {
      return null;
    }
  },
  lastFocusedWindow: async () => {
    try {
      return (await chrome.windows.getLastFocused()).id ?? null;
    } catch {
      return null;
    }
  },
  sendToTab: (tabId, message) => {
    // A tab without a live page script (not loaded yet, or orphaned by an
    // update before re-injection) has no receiver; its hello asks again.
    chrome.tabs.sendMessage(tabId, message).catch(() => undefined);
  },
  navigateTab: (tabId, url) => {
    chrome.tabs.update(tabId, { url }).catch(() => undefined);
  },
  activateTab: (tabId, windowId) => {
    chrome.tabs.update(tabId, { active: true }).catch(() => undefined);
    chrome.windows.update(windowId, { focused: true }).catch(() => undefined);
  },
  openTab: (url) => {
    chrome.tabs.create({ url }).catch(() => undefined);
  },
  injectPageScript: async (tabId, files) => {
    try {
      await chrome.scripting.executeScript({ target: { tabId }, files });
      return true;
    } catch {
      return false;
    }
  },
};

const hub = new Hub(hubApi);
const manager = new ConnectionManager(api, (state) => hub.stateArrived(state), {
  onHandshake: () => hub.handshake(),
  onChange: () => hub.connectionChanged(),
});
hub.attach(manager);

chrome.runtime.onStartup.addListener(() => manager.connect());
chrome.runtime.onInstalled.addListener((details) => {
  manager.connect();
  void hub.installed(details.reason);
});
chrome.alarms.onAlarm.addListener((alarm) => manager.onAlarm(alarm.name));

chrome.tabs.onUpdated.addListener((_tabId, _change, tab) => {
  const snap = snapshot(tab);
  if (snap !== null) hub.tabUpdated(snap);
});
chrome.tabs.onActivated.addListener((info) => hub.tabActivated(info.tabId, info.windowId));
chrome.tabs.onRemoved.addListener((tabId) => hub.tabRemoved(tabId));
chrome.tabs.onReplaced.addListener((added, removed) => hub.tabReplaced(added, removed));
chrome.windows.onFocusChanged.addListener((windowId) => hub.windowFocused(windowId, chrome.windows.WINDOW_ID_NONE));

// Page scripts: hello / href / the block's buttons. Nothing is answered inline.
chrome.runtime.onMessage.addListener((message: unknown, sender: chrome.runtime.MessageSender) => {
  hub.pageMessage(message, sender);
  return false;
});
// The side panel's port.
chrome.runtime.onConnect.addListener((port) => hub.panelConnected(port));

// The toolbar icon opens the global side panel (D1).
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => undefined);

// Periodic liveness ping (also keeps the port measurably healthy).
void chrome.alarms.create(PING_ALARM, { periodInMinutes: 1 });

// Top level: runs on every service-worker start/wake.
manager.connect();
