"""Secure storage foundation (plan Step 9).

Two distinct mechanisms (plan Key Design Decision):
- DURABLE secrets (later: the two clinics' Cliniko API keys) go to Windows
  Credential Manager via `keyring`, keyed `(clinic_id, secret_name)` from the
  start so Phase 4 needs no interface churn. Phase 1 stores TEST data only.
- EPHEMERAL session data uses AES-256-GCM with a key from `os.urandom(32)`
  held only in memory; `destroy()` overwrites and drops the key, after which
  decryption is impossible (cryptographic deletion, per PLAN.md).

No custom cryptography — `cryptography` library primitives only
(Critical Constraint).
"""

from __future__ import annotations

import os

import keyring
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SERVICE_PREFIX = "ClinikoScribe"
_NONCE_BYTES = 12  # AES-GCM standard nonce size
_KEY_BYTES = 32  # AES-256


class SecureStorageProvider:
    """Minimal durable-secret store over Windows Credential Manager.

    Interface is deliberately small (store/retrieve/delete) — queueing and
    migration hooks belong to Phase 4 (plan: keep the interface minimal).
    """

    @staticmethod
    def _service(clinic_id: str) -> str:
        if not clinic_id or "/" in clinic_id:
            raise ValueError("clinic_id must be a non-empty identifier without '/'")
        return f"{_SERVICE_PREFIX}/{clinic_id}"

    def store(self, clinic_id: str, secret_name: str, value: str) -> None:
        keyring.set_password(self._service(clinic_id), secret_name, value)

    def retrieve(self, clinic_id: str, secret_name: str) -> str | None:
        return keyring.get_password(self._service(clinic_id), secret_name)

    def delete(self, clinic_id: str, secret_name: str) -> None:
        try:
            keyring.delete_password(self._service(clinic_id), secret_name)
        except keyring.errors.PasswordDeleteError:
            pass  # already absent — deletion is idempotent


class SessionCrypto:
    """Per-session AES-256-GCM encryption with explicit key destruction."""

    def __init__(self) -> None:
        self._key: bytearray | None = bytearray(os.urandom(_KEY_BYTES))

    @property
    def destroyed(self) -> bool:
        return self._key is None

    def _cipher(self) -> AESGCM:
        if self._key is None:
            raise RuntimeError("session key has been destroyed")
        return AESGCM(bytes(self._key))

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(_NONCE_BYTES)
        return nonce + self._cipher().encrypt(nonce, plaintext, None)

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) <= _NONCE_BYTES:
            raise InvalidTag()
        nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        return self._cipher().decrypt(nonce, ciphertext, None)

    def destroy(self) -> None:
        """Overwrite and drop the key: cryptographic deletion of everything
        encrypted under it. Idempotent."""
        if self._key is not None:
            for i in range(len(self._key)):
                self._key[i] = 0
            self._key = None
