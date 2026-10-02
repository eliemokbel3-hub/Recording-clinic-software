import { defineConfig } from "vitest/config";

import { buildDefines } from "./src/channel";

// Cliniko workflow safeguards plan Task 6.0: two test projects. Every
// `*.test.ts` runs under node as before; a `*.dom.test.ts` (the page script
// and the side panel) runs under jsdom, the one pinned DOM devDependency the
// practitioner authorised (2026-09-27). Kept apart from vite.config.ts so the
// crx build plugin never loads under test.
//
// Installation plan Task 1.3 (D2): the tests run against the release
// channel's compile-time constants, so the pins test what ships; the dev
// values are tested through `channel.ts` directly. Every project gets BOTH
// the static `define` and the setup file that binds the same values on
// `globalThis` — a jsdom project does not apply `define` (see the setup
// file), and a new project must list both.
const define = buildDefines("release");
const setupFiles = ["src/test/build-defines.ts"];

export default defineConfig({
  test: {
    projects: [
      {
        define,
        test: {
          name: "node",
          environment: "node",
          include: ["src/**/*.test.ts"],
          exclude: ["src/**/*.dom.test.ts"],
          setupFiles,
        },
      },
      {
        define,
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.dom.test.ts"],
          setupFiles,
        },
      },
    ],
  },
});
