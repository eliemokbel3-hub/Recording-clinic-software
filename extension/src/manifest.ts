import { defineManifest } from "@crxjs/vite-plugin";

// Critical Constraints (plan): host permissions limited to Cliniko + nativeMessaging;
// no <all_urls>, no content scripts in Phase 1. The stable-ID "key" is added in
// plan Step 3 (extension identity).
export default defineManifest({
  manifest_version: 3,
  name: "Cliniko Scribe Companion",
  version: "0.1.0",
  description: "Privacy-first clinical scribe companion for Cliniko (Phase 1: security foundation)",
  permissions: ["nativeMessaging"],
  host_permissions: ["https://*.cliniko.com/*"],
  background: {
    service_worker: "src/background.ts",
    type: "module",
  },
});
