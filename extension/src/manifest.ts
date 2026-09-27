import { defineManifest } from "@crxjs/vite-plugin";

import { CLINIKO_MATCH, PANEL_PATH } from "./manifest-paths";

// Critical Constraints (plan): host permissions limited to Cliniko + nativeMessaging;
// no <all_urls>, no `tabs` permission.
// "key" pins the extension ID to mbmhglgadhdohpgbmpbjnaifjagfdfid on every machine
// (see extension/KEY.md); regenerate only via scripts/generate-extension-key.py.
//
// Cliniko workflow safeguards plan Task 6.1 (D1, D13): the global side panel,
// and the page script on Cliniko hosts only. `scripting` re-injects that page
// script into open Cliniko tabs after an update or reload; it reaches only the
// hosts in `host_permissions`. Without `tabs`, a tab's URL is readable only
// while it is on a Cliniko host. Every change here needs `npm run build`, a
// reload in chrome://extensions and a full Chrome restart (AGENTS.md step 8).

export default defineManifest({
  manifest_version: 3,
  key: "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0xCeYi0oFYOLACueOgrOF0wVBJuDYCGUlDIhp0y5kthyNhSk5LHDrYfzQAGbC068E2sI2OyfTDv7S227MMZ7CAHnnRsqYaR2oQ/RnVK7FyEwK+cPEpoqsDwMVYHlCGvwllhdRjvyB6I5RGUAtrp8+XE4+k7iA58khq3JcE5V2BRxewMWOhFFivn0fbkO/g5toT2dcsbQbNQ+eBIvaBlXLlNp3Q0NJ607QI2GIrgW/cp3ci9lUBKM8KaFcXOwh2IgIVEieQnQ2Y2XqCfUyd3U2wJ22OTc2dEGM3WfK0jTz8Ac/NqIQzlvxj1AnHmsdZZvgwMM76lzuSrJC2zMpJTTiwIDAQAB",
  name: "Cliniko Scribe Companion",
  version: "0.1.0",
  description: "Privacy-first clinical scribe companion for Cliniko: consent, controls and recording safeguards",
  permissions: ["nativeMessaging", "alarms", "sidePanel", "scripting"],
  host_permissions: [CLINIKO_MATCH],
  action: {
    default_title: "Cliniko Scribe Companion",
  },
  side_panel: {
    default_path: PANEL_PATH,
  },
  background: {
    service_worker: "src/background.ts",
    type: "module",
  },
  content_scripts: [
    {
      matches: [CLINIKO_MATCH],
      js: ["src/page.ts"],
      run_at: "document_idle",
      all_frames: false,
    },
  ],
});
