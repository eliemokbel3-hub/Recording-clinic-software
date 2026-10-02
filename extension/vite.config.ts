import { crx } from "@crxjs/vite-plugin";
import { defineConfig } from "vite";

import { CHANNELS, buildDefines, channelForMode } from "./src/channel";
import { manifestFor } from "./src/manifest";

// Installation plan Task 1.3: `npm run build` (and `-- --mode release`) builds
// the release extension into dist/, unchanged; `npm run build -- --mode dev`
// builds the dev extension into dist-dev/, so a dev build never replaces the
// unpacked release build Chrome has loaded. An unknown mode stops the build.
export default defineConfig(({ mode }) => {
  const channel = channelForMode(mode);
  return {
    plugins: [crx({ manifest: manifestFor(channel) })],
    define: buildDefines(channel),
    build: { outDir: CHANNELS[channel].outDir },
  };
});
