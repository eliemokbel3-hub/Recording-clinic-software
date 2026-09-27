// Paths the manifest and the runtime share. Kept apart from manifest.ts so the
// service worker never bundles the crx build plugin.
export const CLINIKO_MATCH = "https://*.cliniko.com/*";
export const PANEL_PATH = "src/panel.html";
