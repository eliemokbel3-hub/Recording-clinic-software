"""Step 9: secure-storage tests — tamper detection and post-destruction failure."""

import pytest
from cryptography.exceptions import InvalidTag

from scribe_desktop.secure_storage import SecureStorageProvider, SessionCrypto

# --- durable store (real Windows Credential Manager, test data only) -----

CLINIC = "test-clinic"
NAME = "phase1-probe"


@pytest.fixture()
def store() -> SecureStorageProvider:
    provider = SecureStorageProvider()
    yield provider
    provider.delete(CLINIC, NAME)  # never leave test credentials behind


def test_store_retrieve_delete_round_trip(store: SecureStorageProvider) -> None:
    store.store(CLINIC, NAME, "not-a-real-key")
    assert store.retrieve(CLINIC, NAME) == "not-a-real-key"
    store.delete(CLINIC, NAME)
    assert store.retrieve(CLINIC, NAME) is None


def test_delete_is_idempotent(store: SecureStorageProvider) -> None:
    store.delete(CLINIC, NAME)
    store.delete(CLINIC, NAME)


def test_clinics_are_namespaced(store: SecureStorageProvider) -> None:
    other = "test-clinic-2"
    try:
        store.store(CLINIC, NAME, "value-a")
        store.store(other, NAME, "value-b")
        assert store.retrieve(CLINIC, NAME) == "value-a"
        assert store.retrieve(other, NAME) == "value-b"
    finally:
        store.delete(other, NAME)


def test_invalid_clinic_id_rejected(store: SecureStorageProvider) -> None:
    with pytest.raises(ValueError):
        store.store("", NAME, "x")
    with pytest.raises(ValueError):
        store.store("a/b", NAME, "x")


# --- session crypto -------------------------------------------------------


def test_encrypt_decrypt_round_trip() -> None:
    crypto = SessionCrypto()
    blob = crypto.encrypt(b"phase-1 test payload")
    assert crypto.decrypt(blob) == b"phase-1 test payload"
    assert blob != b"phase-1 test payload"


def test_tamper_detection() -> None:
    crypto = SessionCrypto()
    blob = bytearray(crypto.encrypt(b"payload"))
    blob[-1] ^= 0xFF  # flip a tag bit
    with pytest.raises(InvalidTag):
        crypto.decrypt(bytes(blob))


def test_truncated_blob_rejected() -> None:
    crypto = SessionCrypto()
    with pytest.raises(InvalidTag):
        crypto.decrypt(b"short")


def test_post_destruction_decryption_impossible() -> None:
    crypto = SessionCrypto()
    blob = crypto.encrypt(b"to be destroyed")
    crypto.destroy()
    assert crypto.destroyed
    with pytest.raises(RuntimeError, match="destroyed"):
        crypto.decrypt(blob)
    with pytest.raises(RuntimeError, match="destroyed"):
        crypto.encrypt(b"new data")


def test_destroy_is_idempotent() -> None:
    crypto = SessionCrypto()
    crypto.destroy()
    crypto.destroy()
    assert crypto.destroyed


def test_sessions_have_distinct_keys() -> None:
    a, b = SessionCrypto(), SessionCrypto()
    blob = a.encrypt(b"cross-session")
    with pytest.raises(InvalidTag):
        b.decrypt(blob)
