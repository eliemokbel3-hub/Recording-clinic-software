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

The learned STYLE store (note-learning-and-styles plan, Phase 0 Task 0.3,
D9) is a SECOND store of the same shape under its OWN root
``%LOCALAPPDATA%\\ClinikoScribe\\style\\``: its own ``key.dpapi`` wrapped with
a DISTINCT verified description (``"ClinikoScribe practitioner style key"``)
and ``style.enc`` — a ``StyleProfile`` under that key with its own AAD. The
three custody stores — session, voice, style — therefore cannot open each
other's blobs: the description check refuses the key before any decryption,
and the AAD refuses the blob even under the right key. One implementation
(``_SealedStore`` and the ``_seal`` / ``_open`` / ``_unlink_store`` helpers)
serves both practitioner stores, so the custody ordering above is the style
store's too, and ``delete_style_profile`` is key-first and independent of
``delete_profile``. The ``StyleProfile`` MODEL lives in ``note_config``
(beside the other clinician-config shapes; it names canonical section keys,
and ``note`` cannot be imported here — ``transcription`` imports this
module) and carries its OWN ``ConsentRecord`` (D9: sample learning at first
run needs no voice profile); ``load_style_profile`` imports it at call time,
the deferred-import convention ``session_store`` uses.

Nothing in this module logs. Error messages carry structure only — a reason
word, a path — never a field of the profile. The profile's field names are
registered with the log tripwire so a stray repr, ``model_dump`` or JSON of
a ``PractitionerProfile`` or ``ConsentRecord`` is dropped by the last-line
filter (``logging_setup._PAYLOAD_SIGNATURES``).
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, get_args

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

if TYPE_CHECKING:
    from scribe_desktop.note_config import StyleProfile
    from scribe_desktop.speaker_embedding import SpeakerEmbedder

PROFILE_BLOB_FILENAME: Final = "voice.enc"
PROFILE_KEY_DESCRIPTION: Final = "ClinikoScribe practitioner profile key"
PROFILE_AAD: Final = b"clinikoscribe-practitioner-profile-v1"
PROFILE_SCHEMA_VERSION: Final = 1
# The learned-style store (D9): its own root, key description and AAD.
STYLE_DIRNAME: Final = "style"
STYLE_BLOB_FILENAME: Final = "style.enc"
STYLE_KEY_DESCRIPTION: Final = "ClinikoScribe practitioner style key"
STYLE_AAD: Final = b"clinikoscribe-practitioner-style-v1"
STYLE_SCHEMA_VERSION: Final = 1
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
    embedder than the caller's — re-enrol). ``store`` names which store
    (the voice profile by default; the learned style raises with its own
    label) — the message is otherwise identical in shape."""

    def __init__(
        self, reason: UnusableReason, detail: str, *, store: str = "practitioner profile"
    ) -> None:
        super().__init__(f"{store} unusable ({reason}): {detail}")
        self.reason: UnusableReason = reason
        self.store: str = store


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
    """What the practitioner agreed to, and when: the ratified consent text's
    version string (``consent-v1`` from Task 0.2; ``consent-v2`` from Task
    5.0; ``consent-v3`` from the note-learning-and-styles plan's Phase 0 —
    the CURRENT version is ``ui.models.CONSENT_TEXT_VERSION``, and a record
    carrying an older one is readable but not current), the time, and the
    learning opt-in as ticked when the record was saved. Carried by the voice
    profile AND, since that plan's D9, by the style profile — one model, two
    stores, so ``ui.models.consent_is_current`` reads either."""

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

    def made_by(self, embedder: SpeakerEmbedder) -> bool:
        """True when this profile records exactly the identity ``embedder``
        reports — ``model_id``, ``model_sha256`` AND ``embedding_dim`` (D16:
        a profile is usable only with the embedder that produced it). THE one
        definition of that agreement: the pipeline refuses a profile that is
        not ``made_by`` the embedder it is given, and the composition layer
        applies no profile that is not ``made_by`` the embedder it built
        (round 53 SIMP-001 — one invariant, one site)."""
        return (
            self.model_id == embedder.model_id
            and self.model_sha256 == embedder.model_sha256
            and self.embedding_dim == embedder.embedding_dim
        )

    def to_bytes(self) -> bytes:
        """Canonical JSON bytes — the plaintext ``voice.enc`` encrypts."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, blob: bytes) -> PractitionerProfile:
        return cls.model_validate_json(blob)


# ---------------------------------------------------------------------------
# Custody — ONE implementation for the two practitioner stores (the voice
# profile; the learned style of the note-learning-and-styles plan, D9).
# ---------------------------------------------------------------------------


def default_profile_root() -> Path:
    # Deliberately NO UNC refusal, exactly like default_sessions_root: a
    # folder-redirected LOCALAPPDATA is an accepted same-user deployment
    # residual for the custody stores (data-flow map, flow 6).
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / "profile"


def default_style_root() -> Path:
    """The learned-style store's root (D9): a SIBLING of the profile root,
    never a second artefact under it — the voice key must not open it."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / STYLE_DIRNAME


class _SealedStore(NamedTuple):
    """What distinguishes the two DPAPI-custodied stores: the words their
    errors use, the default root, the blob's name, the key blob's verified
    description and the blob's AAD. Everything else — the custody ordering,
    key reuse, key-first deletion — is shared code below."""

    label: str  # "practitioner profile" / "learned style" — the store, in errors
    dir_label: str  # "profile" / "style" — the directory and the blob, in errors
    key_label: str  # "profile key" / "style key"
    default_root: Callable[[], Path]
    blob_filename: str
    key_description: str
    aad: bytes
    retry_hint: str  # what to do when the existing key cannot be unwrapped


_VOICE_STORE: Final = _SealedStore(
    label="practitioner profile",
    dir_label="profile",
    key_label="profile key",
    default_root=default_profile_root,
    blob_filename=PROFILE_BLOB_FILENAME,
    key_description=PROFILE_KEY_DESCRIPTION,
    aad=PROFILE_AAD,
    retry_hint="delete the profile before enrolling again",
)
_STYLE_STORE: Final = _SealedStore(
    label="learned style",
    dir_label="style",
    key_label="style key",
    default_root=default_style_root,
    blob_filename=STYLE_BLOB_FILENAME,
    key_description=STYLE_KEY_DESCRIPTION,
    aad=STYLE_AAD,
    retry_hint="delete the learned style before learning again",
)


def _base(store: _SealedStore, root: Path | None) -> Path:
    """The store's directory: the caller's ``root`` or the store's default."""
    return root if root is not None else store.default_root()


def _key_present(key_path: Path, store: _SealedStore) -> bool:
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
        raise StoreWriteError(
            f"{store.key_label} custody blob is not readable: {exc}"
        ) from exc


def _seal(store: _SealedStore, base: Path, plaintext: bytes) -> Path:
    """The custody ordering in the module docstring, for either store: first
    save generates the key and writes it FIRST; a later save reuses the
    existing key and replaces only the blob. ``StoreWriteError`` on any failed
    write (nothing partial is left at either path — ``atomic_write_bytes``)
    and when the existing key blob cannot be inspected (refused before
    anything is written); ``ProfileUnusableError`` (``key``) when an existing
    key cannot be unwrapped, with nothing replaced. The in-memory key is
    destroyed before returning either way — the wrapped blob on disk is the
    only copy."""
    key_path = base / KEY_FILENAME
    blob_path = base / store.blob_filename
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StoreWriteError(f"failed creating {store.dir_label} directory: {exc}") from exc
    crypto: SessionCrypto
    reuse_key = _key_present(key_path, store)
    if reuse_key:
        try:
            crypto = unwrap_key_from_file(base, description=store.key_description)
        except KeyCustodyError as exc:
            raise ProfileUnusableError(
                "key",
                f"the existing {store.key_label} cannot be unwrapped; {store.retry_hint}",
                store=store.label,
            ) from exc
    else:
        crypto = SessionCrypto()
    try:
        if not reuse_key:
            wrap_key_to_file(crypto, base, description=store.key_description)
        sealed = crypto.encrypt(plaintext, store.aad)
        atomic_write_bytes(blob_path, sealed, error_label=store.label)
    finally:
        crypto.destroy()
    return blob_path


def _open(store: _SealedStore, base: Path) -> bytes | None:
    """The stored blob's PLAINTEXT, ``None`` when no blob exists (a key with
    no blob is absent too), else ``ProfileUnusableError`` — ``blob``,
    ``key`` or ``authentication``. The in-memory key is destroyed before
    returning."""
    blob_path = base / store.blob_filename
    try:
        sealed = blob_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ProfileUnusableError(
            "blob", f"{store.blob_filename} unreadable: {exc}", store=store.label
        ) from exc
    try:
        crypto = unwrap_key_from_file(base, description=store.key_description)
    except KeyCustodyError as exc:
        raise ProfileUnusableError("key", str(exc), store=store.label) from exc
    try:
        return crypto.decrypt(sealed, store.aad)
    except InvalidTag as exc:
        raise ProfileUnusableError(
            "authentication",
            f"{store.blob_filename} failed authentication under the {store.key_label}",
            store=store.label,
        ) from exc
    finally:
        crypto.destroy()


# A validation location component that is not a declared field name, an
# integer index or pydantic's own ``[key]`` marker is INPUT (a mapping key, an
# unknown field name — codex PR-MED-016) and renders as this placeholder.
_LOCATION_PLACEHOLDER: Final = "<field>"
_KEY_MARKER: Final = "[key]"


def _nested_models(annotation: object) -> list[type[BaseModel]]:
    """Every ``BaseModel`` subclass reachable from a field annotation —
    through ``tuple[...]``, ``Mapping[...]``, ``Annotated[...]`` and unions."""
    found: list[type[BaseModel]] = []
    stack: list[object] = [annotation]
    while stack:
        item = stack.pop()
        if isinstance(item, type) and issubclass(item, BaseModel):
            found.append(item)
        else:
            stack.extend(get_args(item))
    return found


def _declared_field_names(model: type[BaseModel]) -> frozenset[str]:
    """The field names ``model`` declares, plus those of every nested model
    its annotations reach — the allow-list a rendered location may name."""
    names: set[str] = set()
    pending: list[type[BaseModel]] = [model]
    seen: set[type[BaseModel]] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for name, info in current.model_fields.items():
            names.add(name)
            pending.extend(_nested_models(info.annotation))
    return frozenset(names)


def _render_location(loc: tuple[int | str, ...], declared: frozenset[str]) -> str:
    parts: list[str] = []
    for part in loc:
        if isinstance(part, int) or part == _KEY_MARKER or part in declared:
            parts.append(str(part))
        else:
            parts.append(_LOCATION_PLACEHOLDER)
    return ".".join(parts) or "<root>"


def _malformed(
    store: _SealedStore, model: type[BaseModel], exc: ValidationError
) -> ProfileUnusableError:
    """Structural ON PURPOSE, and raised by the caller ``from None`` (round 14
    PR-HIGH-003): the models hide their input VALUES in the rendered error
    (``hide_input_in_errors``), ``from None`` keeps the validation error out
    of the exception's rendered chain altogether, and every location is
    rendered through ``model``'s DECLARED field names (codex PR-MED-016: a
    location is not input-free — an ``extra="forbid"`` refusal carries the
    unknown field name and a mapping refusal carries the key, neither of
    which ``hide_input_in_errors`` hides). A traceback of the loader's error
    therefore names the reason, the error count and locations made only of
    declared field names, integer indices and pydantic's ``[key]`` marker —
    any other component is ``<field>``. What that bounds, exactly (codex
    PR-LOW-019): no string outside the declared-field vocabulary, the marker
    and the placeholder ever reaches the message — never a value, and never
    free text from a key or an unknown field name. The membership test is
    position-blind, so an input key or unknown field whose spelling
    coincides with a declared name renders AS that name (a token from the
    schema's public vocabulary, not the input's identity)."""
    declared = _declared_field_names(model)
    locations = sorted({_render_location(error["loc"], declared) for error in exc.errors()})
    return ProfileUnusableError(
        "malformed",
        f"{store.blob_filename} is not a valid {store.dir_label} ({exc.error_count()} "
        f"validation error(s) at {', '.join(locations)})",
        store=store.label,
    )


def _blob_present(base: Path, store: _SealedStore) -> bool:
    try:
        return (base / store.blob_filename).stat().st_size > 0
    except OSError:
        return False


def _unlink_store(store: _SealedStore, base: Path) -> None:
    """Key FIRST (cryptographic deletion), then the blob. Idempotent: absent
    files are fine. Any other unlink failure raises ``StoreWriteError`` —
    after the key unlink succeeded the blob is already unreadable, and the
    error says which file remains."""
    targets = (
        (store.key_label, base / KEY_FILENAME),
        (f"{store.dir_label} blob", base / store.blob_filename),
    )
    for label, path in targets:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise StoreWriteError(f"failed deleting the {label}: {exc}") from exc


def save_profile(profile: PractitionerProfile, *, root: Path | None = None) -> Path:
    """Write the profile under the custody ordering in the module docstring
    (``_seal``); returns the blob path. First enrolment generates the key
    and writes it first; re-enrolment reuses the existing key and replaces
    only ``voice.enc``."""
    return _seal(_VOICE_STORE, _base(_VOICE_STORE, root), profile.to_bytes())


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
    plain = _open(_VOICE_STORE, _base(_VOICE_STORE, root))
    if plain is None:
        return None
    try:
        profile = PractitionerProfile.from_bytes(plain)
    except ValidationError as exc:
        raise _malformed(_VOICE_STORE, PractitionerProfile, exc) from None
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
    return _blob_present(_base(_VOICE_STORE, root), _VOICE_STORE)


def delete_profile(*, root: Path | None = None) -> None:
    """Key FIRST (cryptographic deletion), then the blob (``_unlink_store``).
    Touches the VOICE store only — the learned style has its own root, key
    and ``delete_style_profile`` (D9)."""
    _unlink_store(_VOICE_STORE, _base(_VOICE_STORE, root))


def save_style_profile(profile: StyleProfile, *, root: Path | None = None) -> Path:
    """Write the learned style under the SAME custody ordering as the voice
    profile, in its OWN root under its OWN key (D9); returns the blob path.
    A later save reuses the existing style key and replaces only
    ``style.enc``. Errors as ``save_profile``'s, with ``learned style`` /
    ``style key`` in their text."""
    return _seal(_STYLE_STORE, _base(_STYLE_STORE, root), profile.to_bytes())


def load_style_profile(*, root: Path | None = None) -> StyleProfile | None:
    """The stored learned style, ``None`` when no ``style.enc`` exists, else
    ``ProfileUnusableError`` (``key`` / ``blob`` / ``authentication`` /
    ``malformed``; never ``model`` — the style store records no embedder).
    The in-memory key is destroyed before returning."""
    from scribe_desktop.note_config import StyleProfile

    plain = _open(_STYLE_STORE, _base(_STYLE_STORE, root))
    if plain is None:
        return None
    try:
        return StyleProfile.from_bytes(plain)
    except ValidationError as exc:
        raise _malformed(_STYLE_STORE, StyleProfile, exc) from None


def style_profile_present(*, root: Path | None = None) -> bool:
    """Whether a ``style.enc`` exists (a STAT, no decryption) — the first-run
    banner's second line (Task 3.4). Usability is ``load_style_profile``'s."""
    return _blob_present(_base(_STYLE_STORE, root), _STYLE_STORE)


def delete_style_profile(*, root: Path | None = None) -> None:
    """Key FIRST, then ``style.enc``; idempotent; INDEPENDENT of
    ``delete_profile`` — deleting the learned style leaves the voice profile
    exactly as it was, and vice versa (D9, codex PR-MED-009)."""
    _unlink_store(_STYLE_STORE, _base(_STYLE_STORE, root))


__all__ = [
    "PROFILE_AAD",
    "PROFILE_BLOB_FILENAME",
    "PROFILE_KEY_DESCRIPTION",
    "PROFILE_SCHEMA_VERSION",
    "STYLE_AAD",
    "STYLE_BLOB_FILENAME",
    "STYLE_DIRNAME",
    "STYLE_KEY_DESCRIPTION",
    "STYLE_SCHEMA_VERSION",
    "ConsentRecord",
    "PractitionerProfile",
    "ProfileError",
    "ProfileUnusableError",
    "UnusableReason",
    "default_profile_root",
    "default_style_root",
    "delete_profile",
    "delete_style_profile",
    "load_profile",
    "load_style_profile",
    "profile_present",
    "save_profile",
    "save_style_profile",
    "style_profile_present",
]
