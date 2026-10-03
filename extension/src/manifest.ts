import { defineManifest } from "@crxjs/vite-plugin";

import { CHANNELS, type BuildChannel } from "./channel";
import { CLINIKO_MATCH, PANEL_PATH } from "./manifest-paths";

// Critical Constraints (plan): host permissions limited to Cliniko + nativeMessaging;
// no <all_urls>, no `tabs` permission.
// "key" pins the extension ID on every machine — the release build to
// mbmhglgadhdohpgbmpbjnaifjagfdfid (see extension/KEY.md), a `--mode dev` build
// to its own id (installation plan Task 1.3, `channel.ts`); regenerate only via
// scripts/generate-extension-key.py. Both channels ask for the same permissions.
//
// Cliniko workflow safeguards plan Task 6.1 (D1, D13): the global side panel,
// and the page script on Cliniko hosts only. `scripting` re-injects that page
// script into open Cliniko tabs after an update or reload; it reaches only the
// hosts in `host_permissions`. Without `tabs`, a tab's URL is readable only
// while it is on a Cliniko host. Every change here needs `npm run build`, a
// reload in chrome://extensions and a full Chrome restart (AGENTS.md step 7).

const NAME = "Clinic Scribe Companion";

/** The manifest for one build channel; only the key and the name differ. */
export function manifestFor(channel: BuildChannel) {
  const identity = CHANNELS[channel];
  return defineManifest({
    manifest_version: 3,
    key: identity.key,
    name: NAME + identity.nameSuffix,
    version: "0.1.2",
    description: "Privacy-first clinical scribe companion for Cliniko: consent, controls and recording safeguards",
    permissions: ["nativeMessaging", "alarms", "sidePanel", "scripting"],
    host_permissions: [CLINIKO_MATCH],
    action: {
      default_title: NAME + identity.nameSuffix,
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
}

export default manifestFor("release");
