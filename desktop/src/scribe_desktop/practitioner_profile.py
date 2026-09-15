"""The practitioner's voice profile: model, custody, deletion (plan Task 1.2).

What is stored (plan Design Decision D5), under
``%LOCALAPPDATA%\\ClinikoScribe\\profile\\``:

- ``key.dpapi`` — an AES-256-GCM key, DPAPI-wrapped (current-user scope)
  with the description ``"ClinikoScribe practitioner profile key"``, generated
  ONCE at first enrolment and living until Delete. ``session_store``'s
  wrap/unwrap helpers do the work; the description is verified on unwrap, so
  a session key blob can never be read as the profile key or vice versa.
- ``voice.enc`` — ``PractitionerProfile`` as canonical JSON, AES-GCM under
  that key with the AAD ``b"clinikoscribe-practitioner-profile-v1"`` (a blob
  of another version or purpose fails authentication). It holds a NUMERIC
  voice vector only — never audio — plus the identity of the embedder that
  produced it (``model_id`` + ``model_sha256``), when and from how much speech
  it was made, the device name, and the consent record.

Custody ordering (D5, round 1 PR-MED-012):

- First enrolment: fresh key -> ``key.dpapi`` written atomically FIRST ->
  ``voice.enc`` written atomically. A failure between the two leaves a key
  with no blob, which ``load_profile`` reports as ABSENT (``None``).
- Re-enrolment: an EXISTING, REUSABLE key — a ``key.dpapi`` that is not
  dead (zero-length/truncated, the session store's deadness rule) and that
  unwraps — is kept, and ONLY ``voice.enc`` is replaced, by one
  ``os.replace``. Under a reusable key a failure at any step leaves the
  previous profile readable, and a fresh key is never written beside a blob
  that reusable key could still open. A live key that cannot be unwrapped
  REFUSES the save (typed): the practitioner deletes the profile first.
- Permitted states the ordering allows (peer round 14 PR-REG-002), none of
  which loses a readable profile or revives an old one: a key with no blob
  (a first enrolment that failed after the key write) reads as ABSENT; a
  present but DEAD key blob is already the cryptographic death of the old
  ``voice.enc``, so a save writes a fresh key and then the blob — and if that
  blob write fails, the new key sits beside the old, already-unreadable blob
  (``authentication``); an interrupted deletion (key unlinked, blob unlink
  failed) leaves a keyless blob (``key``) and the typed error names the
  file that remains.
- Deletion: the key is unlinked FIRST (cryptographic deletion), then the
  blob; idempotent. Plain NTFS unlink — the same forensic residual the
  session store accepts at the same-user boundary (threat model).

``load_profile`` returns ``None`` for an absent profile and raises
``ProfileUnusableError`` — with a structural ``reason`` — when a blob exists
but cannot be used: the key is missing/dead/undecryptable, the blob is
unreadable, fails authentication (tamper, truncation, wrong AAD), is
malformed, or records a model other than the one the caller asks for. The
plan's attribution path (D3) treats an unusable profile as ABSENT for
attribution while the reason stays visible for the status line (D2) — the
loader names which, the consumer decides.

Nothing in this module logs. Error messages carry structure only — a reason
word, a path — never a field of the profile. The profile's field names are
registered with the log tripwire so a stray repr, ``model_dump`` or JSON of
a ``PractitionerProfile`` or ``ConsentRecord`` is dropped by the last-line
filter (``logging_setup._PAYLOAD_SIGNATURES``).
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from pathlib import Path
from typing import Final, Literal

from cryptography.exceptions import InvalidTag
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    KEY_FILENAME,
    KeyCustodyError,
    StoreWriteError,
    atomic_write_bytes,
    key_blob_is_dead,
    unwrap_key_from_file,
    wrap_key_to_file,
)

PROFILE_BLOB_FILENAME: Final = "voice.enc"
PROFILE_KEY_DESCRIPTION: Final = "ClinikoScribe practitioner profile key"
PROFILE_AAD: Final = b"clinikoscribe-practitioner-profile-v1"
PROFILE_SCHEMA_VERSION: Final = 1
# Bounded so a tampered-but-authenticated blob (impossible under GCM) or a
# far-future schema cannot make the parser allocate without limit.
_MAX_EMBEDDING_DIM: Final = 4096
_MAX_DEVICE_NAME_CHARS: Final = 200
_MODEL_ID_PATTERN: Final = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
_SHA256_OR_EMPTY_PATTERN: Final = r"^([0-9a-f]{64})?$"
_CONSENT_VERSION_PATTERN: Final = r"^consent-v[0-9]{1,4}$"

UnusableReason = Literal["key", "blob", "authentication", "malformed", "model"]


class ProfileError(Exception):
    """Base class for practitioner-profile failures."""


class ProfileUnusableError(ProfileError):
    """A profile blob exists but cannot be used. ``reason`` is structural:
    ``key`` (missing, dead or undecryptable ``key.dpapi``), ``blob``
    (unreadable), ``authentication`` (tamper / truncation / wrong AAD),
    ``malformed`` (parsed but invalid), ``model`` (made by a different
    embedder than the caller's — re-enrol)."""

    def __init__(self, reason: UnusableReason, detail: str) -> None:
        super().__init__(f"practitioner profile unusable ({reason}): {detail}")
        self.reason: UnusableReason = reason


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value


# Validation errors must never render the INPUT (peer round 14 PR-HIGH-003):
# a pydantic error's default rendering carries ``input_value=`` — for a field
# validator the offending field, for a model validator the whole input — which
# for these models is the vector and the consent record. ``hide_input_in_errors``
# is pydantic's own switch for exactly this; both models set it, and the
# loader never chains a validation error as a cause.
_NO_INPUT_IN_ERRORS = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)


class ConsentRecord(BaseModel):
    """What the practitioner agreed to, and when (consent text v1, Task 0.2)."""

    model_config = _NO_INPUT_IN_ERRORS

    accepted_at: datetime
    consent_text_version: str = Field(pattern=_CONSENT_VERSION_PATTERN)
    learning_opt_in: bool

    @field_validator("accepted_at")
    @classmethod
    def _accepted_at_aware(cls, value: datetime) -> datetime:
        return _aware(value)


class PractitionerProfile(BaseModel):
    """The encrypted profile's content (D5). ``embedding`` is the enrolled
    voice vector as produced by the embedder named by ``model_id`` /
    ``model_sha256``: finite, non-zero, exactly ``embedding_dim`` long. The
    embedder L2-normalises what it returns; the model does not re-normalise
    and does not require unit norm (a synthetic test profile may carry any
    finite non-zero vector). Validation errors render WITHOUT their input
    (``hide_input_in_errors``): a ``ValidationError`` from ``from_bytes`` or
    ``model_validate`` names types and locations only."""

    model_config = _NO_INPUT_IN_ERRORS

    schema_version: Literal[1] = PROFILE_SCHEMA_VERSION
    model_id: str = Field(pattern=_MODEL_ID_PATTERN)
    model_sha256: str = Field(pattern=_SHA256_OR_EMPTY_PATTERN)
    embedding: tuple[float, ...] = Field(min_length=2, max_length=_MAX_EMBEDDING_DIM)
    embedding_dim: int = Field(ge=2, le=_MAX_EMBEDDING_DIM)
    created_at: datetime
    enrolment_speech_seconds: float = Field(gt=0.0)
    device_name: str = Field(max_length=_MAX_DEVICE_NAME_CHARS)
    consent: ConsentRecord

    @field_validator("created_at")
    @classmethod
    def _created_at_aware(cls, value: datetime) -> datetime:
        return _aware(value)

    @field_validator("embedding")
    @classmethod
    def _embedding_finite_and_non_zero(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not all(math.isfinite(v) for v in value):
            raise ValueError("embedding must be finite")
        if all(v == 0.0 for v in value):
            raise ValueError("embedding must not be the zero vector")
        return value

    @field_validator("enrolment_speech_seconds")
    @classmethod
    def _speech_seconds_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("enrolment_speech_seconds must be finite")
        return value

    @field_validator("device_name")
    @classmethod
    def _device_name_printable(cls, value: str) -> str:
        if any(ch.isspace() and ch != " " for ch in value) or not value.isprintable():
            raise ValueError("device_name must be printable, single-line text")
        return value

    @model_validator(mode="after")
    def _dim_matches(self) -> PractitionerProfile:
        if len(self.embedding) != self.embedding_dim:
            raise ValueError(
                f"embedding has {len(self.embedding)} elements; embedding_dim is "
                f"{self.embedding_dim}"
            )
        return self

    def to_bytes(self) -> bytes:
        """Canonical JSON bytes — the plaintext ``voice.enc`` encrypts."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, blob: bytes) -> PractitionerProfile:
        return cls.model_validate_json(blob)


def default_profile_root() -> Path:
    # Deliberately NO UNC refusal, exactly like default_sessions_root: a
    # folder-redirected LOCALAPPDATA is an accepted same-user deployment
    # residual for the custody stores (data-flow map, flow 6).
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / "profile"


def _paths(root: Path | None) -> tuple[Path, Path, Path]:
    base = root if root is not None else default_profile_root()
    return base, base / KEY_FILENAME, base / PROFILE_BLOB_FILENAME


def _key_present(key_path: Path) -> bool:
    """True for a key blob that COULD be a DPAPI blob (the shared deadness
    rule). ``False`` for a CONFIRMED absence and for a present but DEAD
    (zero-length/truncated) blob — the old profile under a dead key is
    already unreadable, so a save may write a fresh key (peer round 14
    PR-REG-002). Any other stat failure is typed (``StoreWriteError``) so a
    save never proceeds — and never writes a new key over one it merely could
    not inspect (round 12 LOW-002)."""
    try:
        return not key_blob_is_dead(key_path.stat().st_size)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise StoreWriteError(f"profile key custody blob is not readable: {exc}") from exc


def save_profile(profile: PractitionerProfile, *, root: Path | None = None) -> Path:
    """Write the profile under the custody ordering in the module docstring;
    returns the blob path. First enrolment generates the key and writes it
    first; re-enrolment reuses the existing key and replaces only
    ``voice.enc``. ``StoreWriteError`` on any failed write (nothing partial is
    left at either path — ``atomic_write_bytes``) and when the existing key
    blob cannot be inspected (refused before anything is written);
    ``ProfileUnusableError`` (``key``) when an existing key cannot be
    unwrapped, with nothing replaced. The in-memory key is destroyed before
    returning either way — the wrapped blob on disk is the only copy."""
    base, key_path, blob_path = _paths(root)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StoreWriteError(f"failed creating profile directory: {exc}") from exc
    crypto: SessionCrypto
    re_enrolment = _key_present(key_path)
    if re_enrolment:
        try:
            crypto = unwrap_key_from_file(base, description=PROFILE_KEY_DESCRIPTION)
        except KeyCustodyError as exc:
            raise ProfileUnusableError(
                "key",
                "the existing profile key cannot be unwrapped; delete the profile "
                "before enrolling again",
            ) from exc
    else:
        crypto = SessionCrypto()
    try:
        if not re_enrolment:
            wrap_key_to_file(crypto, base, description=PROFILE_KEY_DESCRIPTION)
        sealed = crypto.encrypt(profile.to_bytes(), PROFILE_AAD)
        atomic_write_bytes(blob_path, sealed, error_label="practitioner profile")
    finally:
        crypto.destroy()
    return blob_path


def load_profile(
    *,
    root: Path | None = None,
    model_id: str | None = None,
    model_sha256: str | None = None,
) -> PractitionerProfile | None:
    """The stored profile, ``None`` when no ``voice.enc`` exists (a key with
    no blob is absent too), else ``ProfileUnusableError`` naming why it
    cannot be used. When ``model_id`` / ``model_sha256`` are given, a profile
    recording a different embedder identity is unusable (``model``) — D3:
    re-enrol; the caller treats it as absent for attribution. The in-memory
    key is destroyed before returning."""
    base, key_path, blob_path = _paths(root)
    try:
        sealed = blob_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ProfileUnusableError("blob", f"voice.enc unreadable: {exc}") from exc
    try:
        crypto = unwrap_key_from_file(base, description=PROFILE_KEY_DESCRIPTION)
    except KeyCustodyError as exc:
        raise ProfileUnusableError("key", str(exc)) from exc
    try:
        plain = crypto.decrypt(sealed, PROFILE_AAD)
    except InvalidTag as exc:
        raise ProfileUnusableError(
            "authentication", "voice.enc failed authentication under the profile key"
        ) from exc
    finally:
        crypto.destroy()
    try:
        profile = PractitionerProfile.from_bytes(plain)
    except ValidationError as exc:
        # Structural ON PURPOSE, and NOT chained (round 14 PR-HIGH-003): the
        # models already hide their input in the rendered error, and ``from
        # None`` keeps the validation error out of this exception's rendered
        # chain altogether — a traceback of the loader's error names the
        # reason, the error count and the field locations, never a value.
        locations = sorted(
            {".".join(str(part) for part in error["loc"]) or "<root>" for error in exc.errors()}
        )
        raise ProfileUnusableError(
            "malformed",
            f"voice.enc is not a valid profile ({exc.error_count()} validation error(s) at "
            f"{', '.join(locations)})",
        ) from None
    if model_id is not None and profile.model_id != model_id:
        raise ProfileUnusableError(
            "model", "the profile was made by a different speaker model; re-enrol"
        )
    if model_sha256 is not None and profile.model_sha256 != model_sha256:
        raise ProfileUnusableError(
            "model", "the profile was made with a different model file; re-enrol"
        )
    return profile


def profile_present(*, root: Path | None = None) -> bool:
    """Whether a ``voice.enc`` exists (a STAT, no decryption) — the first-run
    check (D10). Says nothing about usability; ``load_profile`` decides that."""
    _base, _key_path, blob_path = _paths(root)
    try:
        return blob_path.stat().st_size > 0
    except OSError:
        return False


def delete_profile(*, root: Path | None = None) -> None:
    """Key FIRST (cryptographic deletion), then the blob. Idempotent: absent
    files are fine. Any other unlink failure raises ``StoreWriteError`` —
    after the key unlink succeeded the blob is already unreadable, and the
    error says which file remains."""
    _base, key_path, blob_path = _paths(root)
    for label, path in (("profile key", key_path), ("profile blob", blob_path)):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise StoreWriteError(f"failed deleting the {label}: {exc}") from exc


__all__ = [
    "PROFILE_AAD",
    "PROFILE_BLOB_FILENAME",
    "PROFILE_KEY_DESCRIPTION",
    "PROFILE_SCHEMA_VERSION",
    "ConsentRecord",
    "PractitionerProfile",
    "ProfileError",
    "ProfileUnusableError",
    "UnusableReason",
    "default_profile_root",
    "delete_profile",
    "load_profile",
    "profile_present",
    "save_profile",
]
