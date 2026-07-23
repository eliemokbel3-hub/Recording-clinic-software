"""Generate (once) the extension identity keypair and derive the stable ID.

Plan Step 3. The manifest `key` field is the base64 DER SubjectPublicKeyInfo
of an RSA public key; Chrome derives the extension ID from SHA-256 of that
DER (first 16 bytes, each nibble mapped to a-p). Pinning `key` keeps the
unpacked extension's ID stable across machines so the native-messaging host
manifest's `allowed_origins` never drifts.

- `extension/key.pem` (private key) is GITIGNORED and never committed; it is
  only needed to regenerate the same public key. The `key` value grants ID
  *stability*, not secrecy.
- Re-running with an existing key.pem is idempotent: it re-derives and
  re-prints the same values.

Usage (from the repo root):
    .venv/Scripts/python.exe scripts/generate-extension-key.py
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

REPO = Path(__file__).resolve().parents[1]
KEY_PEM = REPO / "extension" / "key.pem"


def load_or_create_private_key() -> rsa.RSAPrivateKey:
    if KEY_PEM.exists():
        key = serialization.load_pem_private_key(KEY_PEM.read_bytes(), password=None)
        assert isinstance(key, rsa.RSAPrivateKey)
        return key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    KEY_PEM.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return key


def main() -> int:
    created = not KEY_PEM.exists()
    key = load_or_create_private_key()
    spki_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    manifest_key = base64.b64encode(spki_der).decode("ascii")
    digest = hashlib.sha256(spki_der).digest()
    extension_id = "".join(chr(ord("a") + (b >> 4)) + chr(ord("a") + (b & 0xF)) for b in digest[:16])

    print(f"key.pem: {'created' if created else 'already existed (reused)'} at {KEY_PEM}")
    print(f"manifest key: {manifest_key}")
    print(f"extension id: {extension_id}")
    print(f"allowed_origins entry: chrome-extension://{extension_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
