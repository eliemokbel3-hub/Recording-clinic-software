// Cliniko workflow safeguards plan Task 6.0: the `dom` test project runs
// under jsdom, and the `chrome.*` fake behaves as the page script and the
// side panel will use it there.
import { afterEach, expect, test } from "vitest";

import { EXTENSION_ID, installChromeFake, removeChromeFake } from "./chrome-fake";

afterEach(() => {
  removeChromeFake();
});

test("the dom project has a document", () => {
  const div = document.createElement("div");
  div.textContent = "<b>text</b>";
  document.body.append(div);
  expect(div.innerHTML).toBe("&lt;b&gt;text&lt;/b&gt;");
  expect(div.querySelector("b")).toBeNull();
});

test("a panel port reaches the worker's onConnect with the panel's sender, and messages cross both ways", async () => {
  const fake = installChromeFake();
  const workerSeen: unknown[] = [];
  fake.runtime.onConnect.addListener((port) => {
    expect(port.sender).toEqual({ id: EXTENSION_ID, url: fake.runtime.getURL("src/panel.html") });
    port.onMessage.addListener((m) => workerSeen.push(m));
    port.postMessage({ kind: "view" });
  });
  const panelSeen: unknown[] = [];
  const panel = chrome.runtime.connect({ name: "scribe-panel" });
  panel.onMessage.addListener((m: unknown) => panelSeen.push(m));
  panel.postMessage({ kind: "command" });
  expect(workerSeen).toEqual([]); // asynchronous, as in Chrome
  await Promise.resolve();
  expect(workerSeen).toEqual([{ kind: "command" }]);
  // Posted inside onConnect, before the panel listened: still delivered.
  expect(panelSeen).toEqual([{ kind: "view" }]);
  fake.runtime.id = undefined;
  expect(() => chrome.runtime.sendMessage({ kind: "hello" })).toThrow("Extension context invalidated.");
});
