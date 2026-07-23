# Scripts

- `register-native-host.py` (plan Step 6) — generates the Chrome native-messaging
  host manifest and `dev-host-launcher.bat` from the current interpreter path,
  writes and verifies the HKCU registry entry; `--unregister` reverses it.
- `generate-extension-key.py` or documented openssl commands (plan Step 3) —
  extension identity keypair; `key.pem` is gitignored and never committed.
