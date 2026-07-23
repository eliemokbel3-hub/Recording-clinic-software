import { defineManifest } from "@crxjs/vite-plugin";

// Critical Constraints (plan): host permissions limited to Cliniko + nativeMessaging;
// no <all_urls>, no content scripts in Phase 1.
// "key" pins the extension ID to mbmhglgadhdohpgbmpbjnaifjagfdfid on every machine
// (see extension/KEY.md); regenerate only via scripts/generate-extension-key.py.
export default defineManifest({
  manifest_version: 3,
  key: "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0xCeYi0oFYOLACueOgrOF0wVBJuDYCGUlDIhp0y5kthyNhSk5LHDrYfzQAGbC068E2sI2OyfTDv7S227MMZ7CAHnnRsqYaR2oQ/RnVK7FyEwK+cPEpoqsDwMVYHlCGvwllhdRjvyB6I5RGUAtrp8+XE4+k7iA58khq3JcE5V2BRxewMWOhFFivn0fbkO/g5toT2dcsbQbNQ+eBIvaBlXLlNp3Q0NJ607QI2GIrgW/cp3ci9lUBKM8KaFcXOwh2IgIVEieQnQ2Y2XqCfUyd3U2wJ22OTc2dEGM3WfK0jTz8Ac/NqIQzlvxj1AnHmsdZZvgwMM76lzuSrJC2zMpJTTiwIDAQAB",
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
