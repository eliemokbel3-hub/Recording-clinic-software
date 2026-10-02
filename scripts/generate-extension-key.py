"""Generate (once) the extension identity keypair and derive the stable ID.

Plan Step 3. The manifest `key` field is the base64 DER SubjectPublicKeyInfo
of an RSA public key; Chrome derives the extension ID from SHA-256 of that
DER (first 16 bytes, each nibble mapped to a-p). Pinning `key` keeps the
unpacked extension's ID stable across machines so the native-messaging host
manifest's `allowed_origins` never drifts.

- `extension/key.pem` (private key) is GITIGNORED and never committed; it is
  only needed to regenerate the same public key. The `key` value grants ID
  *stability*, not secrecy.
- Re-running with an existing key file is idempotent: it re-derives and
  re-prints the same values.
- `--out` names another key file (installation plan Task 1.3: the dev
  channel's `extension/key-dev.pem`, also gitignored). A relative path is
  taken from the repo root. The default is unchanged: `extension/key.pem`.
  Any other file is refused before anything is read or written (round 27).

Usage (from the repo root):
    .venv/Scripts/python.exe scripts/generate-extension-key.py
    .venv/Scripts/python.exe scripts/generate-extension-key.py --out extension/key-dev.pem
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

REPO = Path(__file__).resolve().parents[1]
KEY_PEM = REPO / "extension" / "key.pem"
# Round 27 PR-LOW-024: the private key is written unencrypted, so `--out` may
# name only the two key files `.gitignore` excludes — never a repository file
# a commit would pick up.
ALLOWED_KEY_FILES = (KEY_PEM, REPO / "extension" / "key-dev.pem")


def resolve_out(out: Path) -> Path | None:
    """The key file ``--out`` names (a relative path is from the repo root),
    or ``None`` when it is not one of ``ALLOWED_KEY_FILES``."""
    key_pem = (out if out.is_absolute() else REPO / out).resolve()
    allowed = {path.resolve() for path in ALLOWED_KEY_FILES}
    return key_pem if key_pem in allowed else None


def load_or_create_private_key(key_pem: Path) -> rsa.RSAPrivateKey:
    if key_pem.exists():
        key = serialization.load_pem_private_key(key_pem.read_bytes(), password=None)
        assert isinstance(key, rsa.RSAPrivateKey)
        return key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--out",
        type=Path,
        default=KEY_PEM,
        help=(
            "the private key file: extension/key.pem (default) or extension/key-dev.pem; "
            "a relative path is from the repo root"
        ),
    )
    args = parser.parse_args(argv)
    key_pem = resolve_out(args.out)
    if key_pem is None:
        parser.error("--out must be extension/key.pem or extension/key-dev.pem (both gitignored)")

    created = not key_pem.exists()
    key = load_or_create_private_key(key_pem)
    spki_der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    manifest_key = base64.b64encode(spki_der).decode("ascii")
    digest = hashlib.sha256(spki_der).digest()
    extension_id = "".join(chr(ord("a") + (b >> 4)) + chr(ord("a") + (b & 0xF)) for b in digest[:16])

    print(f"{key_pem.name}: {'created' if created else 'already existed (reused)'} at {key_pem}")
    print(f"manifest key: {manifest_key}")
    print(f"extension id: {extension_id}")
    print(f"allowed_origins entry: chrome-extension://{extension_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
