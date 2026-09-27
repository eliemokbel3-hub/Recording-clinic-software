import { defineConfig } from "vitest/config";

// Cliniko workflow safeguards plan Task 6.0: two test projects. Every
// `*.test.ts` runs under node as before; a `*.dom.test.ts` (the page script
// and the side panel) runs under jsdom, the one pinned DOM devDependency the
// practitioner authorised (2026-09-27). Kept apart from vite.config.ts so the
// crx build plugin never loads under test.
export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: "node",
          environment: "node",
          include: ["src/**/*.test.ts"],
          exclude: ["src/**/*.dom.test.ts"],
        },
      },
      {
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.dom.test.ts"],
        },
      },
    ],
  },
});
