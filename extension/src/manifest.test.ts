// Cliniko workflow safeguards plan Task 6.1: the manifest pin. The extension
// asks for exactly these permissions, reaches only Cliniko hosts, never holds
// `tabs` or <all_urls>, and keeps the pinned key (so the native host's
// `allowed_origins` still names it).
import { createHash } from "node:crypto";

import { describe, expect, test } from "vitest";

import manifestExport from "./manifest";
import { CLINIKO_MATCH, PANEL_PATH } from "./manifest-paths";

interface Manifest {
  key: string;
  permissions: string[];
  host_permissions: string[];
  optional_permissions?: string[];
  optional_host_permissions?: string[];
  side_panel: { default_path: string };
  content_scripts: { matches: string[]; js: string[]; all_frames?: boolean }[];
  web_accessible_resources?: unknown;
  externally_connectable?: unknown;
}

const manifest = manifestExport as unknown as Manifest;

/** Chrome's extension id: the first 16 bytes of SHA-256(public key DER), a-p encoded. */
function extensionId(keyBase64: string): string {
  const digest = createHash("sha256").update(Buffer.from(keyBase64, "base64")).digest("hex");
  return [...digest.slice(0, 32)].map((c) => String.fromCharCode(97 + parseInt(c, 16))).join("");
}

describe("manifest pin", () => {
  test("permissions are exactly the four the plan names", () => {
    expect([...manifest.permissions].sort()).toEqual(["alarms", "nativeMessaging", "scripting", "sidePanel"]);
    expect(manifest.permissions).not.toContain("tabs");
    expect(manifest.optional_permissions).toBeUndefined();
    expect(manifest.optional_host_permissions).toBeUndefined();
  });

  // Literal patterns, not the shared constant, so a widened CLINIKO_MATCH
  // fails here (round 37 PR-LOW-202).
  test("hosts are Cliniko's only", () => {
    expect(CLINIKO_MATCH).toBe("https://*.cliniko.com/*");
    expect(manifest.host_permissions).toEqual(["https://*.cliniko.com/*"]);
    const text = JSON.stringify(manifest);
    expect(text).not.toContain("<all_urls>");
    expect(text).not.toContain("http://");
    expect(manifest.externally_connectable).toBeUndefined();
  });

  test("the page script runs on Cliniko hosts only, top frame only", () => {
    expect(manifest.content_scripts).toHaveLength(1);
    for (const script of manifest.content_scripts) {
      expect(script.matches).toEqual(["https://*.cliniko.com/*"]);
      expect(script.js).toEqual(["src/page.ts"]);
      expect(script.all_frames).toBe(false);
    }
  });

  test("the side panel is the extension's own page", () => {
    expect(manifest.side_panel.default_path).toBe(PANEL_PATH);
  });

  test("the pinned key still yields the registered extension id", () => {
    expect(extensionId(manifest.key)).toBe("mbmhglgadhdohpgbmpbjnaifjagfdfid");
  });
});
