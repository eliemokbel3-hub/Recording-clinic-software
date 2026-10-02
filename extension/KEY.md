# Extension identity (plan Step 3; two channels since installation plan Task 1.3)

- **Extension ID (stable, pinned):** `mbmhglgadhdohpgbmpbjnaifjagfdfid` — the release
  build (`npm run build` → `dist/`), unchanged since Step 3.
- **allowed_origins entry:** `chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`
- **Dev-channel ID:** `pecfiifdlmdbkifmjkbkeiaflpenfejd` — the dev build
  (`npm run build -- --mode dev` → `dist-dev/`), linked to the dev host
  `com.scribe.cliniko_host_dev` only (`chrome-extension://pecfiifdlmdbkifmjkbkeiaflpenfejd/`).
- **Pinned via:** each channel's `key` field in `src/channel.ts` (`CHANNELS`; base64 DER
  SubjectPublicKeyInfo), which `manifestFor` in `src/manifest.ts` uses for the channel
  `vite.config.ts` builds.
- **Private keys:** `extension/key.pem` (release) and `extension/key-dev.pem` (dev) —
  both gitignored, NEVER commit. They only provide ID *stability* (regenerating the same
  public key), not secrecy: with an unpacked extension the `key` value is public by design.
- **Regenerate/re-derive:** `.venv/Scripts/python.exe scripts/generate-extension-key.py`
  for the release key, or with `--out extension/key-dev.pem` for the dev key
  (idempotent while the key file exists; a lost key means a NEW ID, which requires
  updating BOTH `src/channel.ts` and the desktop's `desktop/src/scribe_desktop/identity.py`
  (`EXTENSION_ID` / `DEV_EXTENSION_ID`, which the host registration writes into
  `allowed_origins`), then re-running that channel's host registration).
- **Phase 7 note:** the Chrome Web Store assigns its own ID at publication — the host
  manifest's `allowed_origins` must be updated then (recorded in the plan).
