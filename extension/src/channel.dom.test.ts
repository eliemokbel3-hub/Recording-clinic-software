// Installation plan Task 1.3: the jsdom project binds the build-time host
// name too (src/test/build-defines.ts), to the release value — the node
// project's twin is in manifest.test.ts.
import { expect, test } from "vitest";

import { CHANNELS } from "./channel";
import { HOST_NAME } from "./protocol";

test("the jsdom project sees the release host name", () => {
  expect(HOST_NAME).toBe(CHANNELS.release.hostName);
  expect(HOST_NAME).toBe("com.scribe.cliniko_host");
});
