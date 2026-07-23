// Step 1 trivial smoke test: the scaffold's module graph loads under vitest.
import { expect, test } from "vitest";

import { HOST_NAME } from "./background";

test("scaffold exposes the locked host name", () => {
  expect(HOST_NAME).toBe("com.scribe.cliniko_host");
});
