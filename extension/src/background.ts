// MV3 service worker — wires ConnectionManager to the real chrome APIs.
// Top-level connect() fires on every SW wake (plan executor facts).

import type { ChromeLike, PortLike } from "./connection";
import { ConnectionManager, PING_ALARM } from "./connection";

export { HOST_NAME } from "./protocol";

const api: ChromeLike = {
  connectNative: (hostName: string): PortLike => chrome.runtime.connectNative(hostName),
  createAlarm: (name: string, delayInMinutes: number) => {
    void chrome.alarms.create(name, { delayInMinutes });
  },
  clearAlarm: (name: string) => {
    void chrome.alarms.clear(name);
  },
  setBadge: (text: string, color: string) => {
    void chrome.action.setBadgeText({ text });
    void chrome.action.setBadgeBackgroundColor({ color });
  },
  newRequestId: () => crypto.randomUUID(),
};

const manager = new ConnectionManager(api);

chrome.runtime.onStartup.addListener(() => manager.connect());
chrome.runtime.onInstalled.addListener(() => manager.connect());
chrome.alarms.onAlarm.addListener((alarm) => manager.onAlarm(alarm.name));

// Periodic liveness ping (also keeps the port measurably healthy).
void chrome.alarms.create(PING_ALARM, { periodInMinutes: 1 });

// Top level: runs on every service-worker start/wake.
manager.connect();
