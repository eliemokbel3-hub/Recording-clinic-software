// Step 1 smoke test. (background.ts itself executes chrome.* at SW top level
// by design — plan executor facts — so it is exercised in Chrome at the
// Step 12 gate, not imported under node.)
import { expect, test } from "vitest";

import { HOST_NAME } from "./protocol";

test("scaffold exposes the locked host name", () => {
  expect(HOST_NAME).toBe("com.scribe.cliniko_host");
});
