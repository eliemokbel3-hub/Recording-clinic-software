# Extension identity (plan Step 3)

- **Extension ID (stable, pinned):** `mbmhglgadhdohpgbmpbjnaifjagfdfid`
- **allowed_origins entry:** `chrome-extension://mbmhglgadhdohpgbmpbjnaifjagfdfid/`
- **Pinned via:** the `key` field in `src/manifest.ts` (base64 DER SubjectPublicKeyInfo)
- **Private key:** `extension/key.pem` — gitignored, NEVER commit. It only provides
  ID *stability* (regenerating the same public key), not secrecy: with an unpacked
  dev extension the `key` value is public by design.
- **Regenerate/re-derive:** `.venv/Scripts/python.exe scripts/generate-extension-key.py`
  (idempotent while `key.pem` exists; a lost `key.pem` means a NEW ID, which requires
  re-running host registration so `allowed_origins` matches).
- **Phase 7 note:** the Chrome Web Store assigns its own ID at publication — the host
  manifest's `allowed_origins` must be updated then (recorded in the plan).
