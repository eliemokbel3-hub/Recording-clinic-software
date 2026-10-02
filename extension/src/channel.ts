// Installation plan Task 1.3 (D2, D3): the build channel. A `--mode dev`
// build is the developer's own copy — its own key (so its own extension id),
// " (dev)" on its name, the dev native host name and its own output folder —
// loaded only in a separate Chrome profile. Every other build is the release
// build, whose values never change (C2): the default `npm run build` (Vite's
// "production" mode) and `--mode release` both produce it. Any other mode is
// refused, so a mistyped mode never builds a third identity.
//
// The private keys are gitignored (extension/key.pem, extension/key-dev.pem);
// only the public keys live here. Regenerate either only via
// scripts/generate-extension-key.py (see extension/KEY.md).

export type BuildChannel = "release" | "dev";

export interface ChannelIdentity {
  /** The manifest `key`: base64 DER SubjectPublicKeyInfo of the public key. */
  readonly key: string;
  /** The extension id Chrome derives from `key` (pinned by manifest.test.ts). */
  readonly extensionId: string;
  /** Appended to the manifest's name and the toolbar title. */
  readonly nameSuffix: string;
  /** The native host the extension connects to (`protocol.ts` HOST_NAME). */
  readonly hostName: string;
  /** Vite's build output folder, relative to extension/. */
  readonly outDir: string;
}

export const CHANNELS: Readonly<Record<BuildChannel, ChannelIdentity>> = {
  release: {
    key: "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0xCeYi0oFYOLACueOgrOF0wVBJuDYCGUlDIhp0y5kthyNhSk5LHDrYfzQAGbC068E2sI2OyfTDv7S227MMZ7CAHnnRsqYaR2oQ/RnVK7FyEwK+cPEpoqsDwMVYHlCGvwllhdRjvyB6I5RGUAtrp8+XE4+k7iA58khq3JcE5V2BRxewMWOhFFivn0fbkO/g5toT2dcsbQbNQ+eBIvaBlXLlNp3Q0NJ607QI2GIrgW/cp3ci9lUBKM8KaFcXOwh2IgIVEieQnQ2Y2XqCfUyd3U2wJ22OTc2dEGM3WfK0jTz8Ac/NqIQzlvxj1AnHmsdZZvgwMM76lzuSrJC2zMpJTTiwIDAQAB",
    extensionId: "mbmhglgadhdohpgbmpbjnaifjagfdfid",
    nameSuffix: "",
    hostName: "com.scribe.cliniko_host",
    outDir: "dist",
  },
  dev: {
    key: "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnzZ/TUKmMLhVvmc7MHION9vRLvuQpiODkUm/r6k6L7UR6A0VMeCyey5uexiTd5PXF0cUu3nAS8i49hayTItOnslwDuWP4BZthjkacygof1pZYd+oJQ/2RWnDqCNbBJVak0YDbI9ovka1BTi90TfJzbMuFY66EoLpaaSPIN23nQFdZle6rGCBt/Rq5CkNcTLfqzF5DDdMFsf6C2k2gcUSaPa6vnu6w0XvzppFr1yPQriNLFiqDjhet/tbLwjO8o1kXWR19e5KAs3/DK4+9poVu+W3qwOJWioXA2ajEfG5sUMWKl706tgnYatwXiGdtWDd62d9pFchhH7OOLe85FexaQIDAQAB",
    extensionId: "pecfiifdlmdbkifmjkbkeiaflpenfejd",
    nameSuffix: " (dev)",
    hostName: "com.scribe.cliniko_host_dev",
    outDir: "dist-dev",
  },
};

/** Vite's `mode` → the channel; refuses anything but dev, release and the default. */
export function channelForMode(mode: string): BuildChannel {
  if (mode === "dev") return "dev";
  if (mode === "release" || mode === "production") return "release";
  throw new Error(`unknown build mode "${mode}": use --mode dev or --mode release`);
}

/** The compile-time constants `vite.config.ts` and `vitest.config.ts` inject. */
export function buildDefines(channel: BuildChannel): Record<string, string> {
  return { __SCRIBE_HOST_NAME__: JSON.stringify(CHANNELS[channel].hostName) };
}
