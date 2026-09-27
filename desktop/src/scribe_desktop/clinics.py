"""Clinic registry: each clinic's Cliniko identity and API key (plan D10).

Cliniko workflow safeguards plan, Tasks 2.1a (the record type and the
loader, no network) and 2.1b (key validation and storage).

WHAT IS KEPT WHERE. ``clinics.json`` (default
``%LOCALAPPDATA%\\ClinikoScribe\\clinics.json``) holds NON-SECRET records —
clinic id, display name, subdomain, shard, the key user's user and
practitioner ids, the validation time and whether the subdomain is confirmed
— plus the practitioner's contact email (the client's ``User-Agent``). The
API key lives ONLY in Windows Credential Manager through the injected key
store (``SecureStorageProvider`` in the app), under
``(clinic_id, KEY_SECRET_NAME)``. This module writes the key nowhere else,
never logs, and no refusal it returns carries the key: a ``Refused`` holds a
reason code and a clinic id only.

THE LOADER is fail-closed. A missing file is an empty registry. A file that
is present but unreadable, larger than ``MAX_FILE_BYTES``, not the schema
(every field is validated), or inconsistent (a repeated clinic id or
subdomain) leaves the registry EMPTY with ``load_problem`` set, and every
mutation is then refused (``REGISTRY_UNREADABLE``), so a damaged file is
never silently overwritten; the practitioner fixes or deletes it.

VALIDATION (D10) is split by thread so the network never runs on the GUI
thread and the registry is only ever mutated there:

- ``begin_validation`` (GUI thread): the local checks (email shape, key
  format and shard, the typed web address, the name), then for a new clinic
  a fresh clinic id, for a Replace key the ``clinic_rev`` bump (D9). It
  captures the clinic's rev in the returned ``ValidationRequest``.
- ``run_validation`` (worker thread): ONE Cliniko client call (the key is
  read once, from the request), touching no registry state: ``GET /user``
  (an active login, whatever its role) → ``GET /practitioners`` for that
  user (exactly one record, and it active) → ``GET /settings/public`` for
  the subdomain. When that last
  request is refused, the practitioner's TYPED web address is used instead
  and recorded unconfirmed: ``confirm_subdomain_from_note`` confirms it when
  the first note verifies with that key on that host (Phase 3 calls it).
- ``commit_validation`` (GUI thread): refused unless, for a Replace, the
  clinic still exists and, for either, the clinic's rev is still the
  captured one — checked BEFORE the worker's own refusal is passed on, so a
  stale refusal is named stale — then the duplicate-subdomain check against
  the CURRENT registry, then the key store and the file write.

CLINIC_REV (D9). Each clinic has an in-memory counter, never persisted. It
is bumped when a Replace key is dispatched and again when it commits, by
every successful commit, and by Remove (before anything else). A result
committed on the GUI thread checks it: a Validate or Replace whose rev moved
is dropped whole (``SUPERSEDED``), and a delayed result for a removed clinic
is ``CLINIC_GONE`` and can never restore the entry. A result is compared
against the rev it captured at dispatch, so a key replaced between the
requests of one call (which read its key once, at the start) cannot commit.
Confirming the subdomain does NOT bump the rev: it only marks a recorded
address as confirmed and changes no identity a pending result depends on.

ORDER OF WRITES, so a failure never leaves a key at rest that the registry
does not list: a NEW clinic writes the file first and then stores the key
(a failed key store first deletes whatever the store may have written, then
rewrites the file without the record; if either step fails the record stays
listed, and Remove clears it). A
REPLACE stores the new key and then writes the record; if the write fails,
Credential Manager holds the new key under the old record, and the rev is
bumped so nothing pending commits — a later verification checks the
record's practitioner id against what the new key's note says (Phase 3), so
the mismatch fails closed. REMOVE deletes the key first and then rewrites
the file; a failed rewrite leaves the record listed with no key, and Remove
can be pressed again (the key delete is idempotent).

Residue (named, not closed): the typed key is a Python ``str`` — it lives
in the ``ValidationRequest`` until the caller drops it, and it cannot be
zeroed (threat model, Cliniko API client residue (2)).
"""

from __future__ import annotations

import json
import os
import re
import secrets
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Final, Literal, NamedTuple, Protocol

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    ValidationError,
    field_validator,
)

from scribe_desktop.cliniko_client import (
    SHARDS,
    CertificateRejected,
    ClinikoClient,
    ClinikoError,
    CredentialsRejected,
    InvalidContactEmail,
    InvalidKey,
    NotFound,
    RateLimited,
    Transport,
    Unreachable,
    check_id,
    shard_of_key,
    validate_contact_email,
)
from scribe_desktop.note_config import _no_control_chars
from scribe_desktop.session_store import StoreWriteError, atomic_write_bytes

REGISTRY_FILENAME: Final = "clinics.json"
KEY_SECRET_NAME: Final = "cliniko_api_key"
SCHEMA_VERSION: Final = 1
# The plan's Agreed Scope is TWO clinics; the bound also caps the allow-list
# the app will send to Chrome (protocol v2 bounds every array, D2).
MAX_CLINICS: Final = 2
MAX_DISPLAY_NAME_CHARS: Final = 60
MAX_FILE_BYTES: Final = 64 * 1024
_MAX_ADDRESS_INPUT_CHARS: Final = 2048
_CLINIC_ID_PATTERN: Final = r"^[0-9a-f]{16}$"
_ID_PATTERN: Final = r"^[1-9][0-9]{0,18}$"
_SUBDOMAIN_RE: Final = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_HOST_RE: Final = re.compile(
    r"(?P<subdomain>[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.(?P<shard>[a-z]{2}[0-9])\.cliniko\.com"
)
# Never a clinic's web address: ``api`` is the API host itself.
_RESERVED_SUBDOMAINS: Final = frozenset({"api", "www"})


# --- Cliniko's answers, as Task P.1 found them ----------------------------------
# EVERY assumption this registry makes about Cliniko's answers lives in this
# block; nothing else in the module reads a Cliniko field name. The
# practitioner's feasibility run (``scripts/probe-cliniko.py``, Task P.1) ran
# on clinic 1 on 2026-09-27; clinic 2 is still owed. Each item says which.
#
# (a) ``GET /user`` carries ``id`` and ``active`` — CONFIRMED (clinic 1). The
#     id is read as digits (a string or a number); ``active`` must be a JSON
#     boolean, anything else is refused as unreadable. The user's ``role`` is
#     NOT read: it is no gate (D10 as amended 2026-09-27 — P.1 found the
#     practitioner's own login is an ``administrator``; the practitioner
#     decided that the practitioner record decides, whatever the role).
# (b) ``GET /practitioners?q[]=user_id:=<id>`` answers a ``practitioners``
#     list whose entries carry ``id`` and ``active`` — CONFIRMED (clinic 1,
#     one record). Validation needs EXACTLY ONE record and it must be active;
#     ``active`` is read as a JSON boolean (anything else is unreadable). A
#     receptionist's or bookkeeper's login has no practitioner record, so it
#     is still refused.
# (c) ``GET /settings/public`` answers ``account.subdomain`` — CONFIRMED
#     (clinic 1: answered 200, the subdomain matching the note URL's, so D10's
#     primary route applies there). UNCONFIRMED: which statuses mean "this key
#     may not read it" (the typed-address route); 401/403/404 are assumed, as
#     no probe has been refused there — clinic 2 may show it.
# (d) The clinic's WEB host shard equals its API key's shard — CONFIRMED
#     (clinic 1); the Cliniko route builds the host from the key's shard, and
#     a typed address must carry the same shard. Clinic 2 is unconfirmed.

_SETTINGS_REFUSED: Final = (CredentialsRejected, NotFound)  # (c)


class _Shape(Exception):
    """An answer did not have the shape the P.1 block expects."""


def _answer_id(value: object) -> str:
    if isinstance(value, bool):
        raise _Shape()
    text = str(value) if isinstance(value, int) else value
    if not isinstance(text, str) or re.fullmatch(_ID_PATTERN, text) is None:
        raise _Shape()
    return check_id(text)


def _user_identity(body: Mapping[str, Any]) -> tuple[str, bool]:  # (a)
    active = body.get("active")
    if not isinstance(active, bool):
        raise _Shape()
    return _answer_id(body.get("id")), active


def _practitioner_records(body: Mapping[str, Any]) -> list[tuple[str, bool]]:  # (b)
    """Each practitioner record as ``(id, active)``."""
    entries = body.get("practitioners")
    if not isinstance(entries, list):
        raise _Shape()
    records: list[tuple[str, bool]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise _Shape()
        active = entry.get("active")
        if not isinstance(active, bool):
            raise _Shape()
        records.append((_answer_id(entry.get("id")), active))
    return records


def _public_subdomain(body: Mapping[str, Any]) -> str:  # (c)
    account = body.get("account")
    subdomain = account.get("subdomain") if isinstance(account, dict) else None
    if not isinstance(subdomain, str):
        raise _Shape()
    subdomain = subdomain.strip().lower()
    if _SUBDOMAIN_RE.fullmatch(subdomain) is None or subdomain in _RESERVED_SUBDOMAINS:
        raise _Shape()
    return subdomain


# --- records ------------------------------------------------------------------


def _subdomain(value: str) -> str:
    if _SUBDOMAIN_RE.fullmatch(value) is None or value in _RESERVED_SUBDOMAINS:
        raise ValueError("not a Cliniko subdomain")
    return value


def _shard(value: str) -> str:
    if value not in SHARDS:
        raise ValueError("not a documented Cliniko shard")
    return value


_DisplayName = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_DISPLAY_NAME_CHARS),
    AfterValidator(_no_control_chars),
]
_ClinikoId = Annotated[str, StringConstraints(pattern=_ID_PATTERN)]


class ClinicHost(NamedTuple):
    """A clinic's web address, ``<subdomain>.<shard>.cliniko.com``."""

    subdomain: str
    shard: str

    @property
    def host(self) -> str:
        return f"{self.subdomain}.{self.shard}.cliniko.com"


class ClinicRecord(BaseModel):
    """One clinic, non-secret (D10). The key is never a field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    clinic_id: Annotated[str, StringConstraints(pattern=_CLINIC_ID_PATTERN)]
    display_name: _DisplayName
    subdomain: Annotated[str, AfterValidator(_subdomain)]
    shard: Annotated[str, AfterValidator(_shard)]
    user_id: _ClinikoId
    practitioner_id: _ClinikoId
    validated_at: AwareDatetime
    # False when the subdomain was TYPED (Cliniko did not share it with this
    # key); a note verified with this key on this host confirms it.
    subdomain_confirmed: StrictBool

    @property
    def host(self) -> str:
        return ClinicHost(self.subdomain, self.shard).host


class _RegistryFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    contact_email: str | None
    clinics: tuple[ClinicRecord, ...] = Field(max_length=MAX_CLINICS)

    @field_validator("contact_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return None if value is None else validate_contact_email(value)


def parse_clinic_address(text: str) -> ClinicHost:
    """A typed web address — ``<subdomain>.<shard>.cliniko.com`` or an
    ``https://`` URL on it, as copied from the address bar. Only the host is
    kept (a pasted note URL's path and ids are dropped here). ``ValueError``
    for anything else, including ``http://`` and a port."""
    raw = text.strip().lower()
    if not raw or len(raw) > _MAX_ADDRESS_INPUT_CHARS:
        raise ValueError("not a Cliniko web address")
    if raw.startswith("https://"):
        raw = raw.removeprefix("https://")
    elif "://" in raw:
        raise ValueError("not a Cliniko web address")
    host = re.split(r"[/?#]", raw, maxsplit=1)[0]
    match = _HOST_RE.fullmatch(host)
    if (
        match is None
        or match.group("shard") not in SHARDS
        or match.group("subdomain") in _RESERVED_SUBDOMAINS
    ):
        raise ValueError("not a Cliniko web address")
    return ClinicHost(match.group("subdomain"), match.group("shard"))


def default_registry_path() -> Path:
    # The same root idiom (and no-UNC-refusal posture) as the other stores.
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / REGISTRY_FILENAME


# --- outcomes -----------------------------------------------------------------


class ClinicRefusal(StrEnum):
    """Why a registry operation did nothing (or, where its copy says so,
    only part of it). The UI's wording for each is in ``ui/models.py``."""

    NAME_INVALID = "name_invalid"
    EMAIL_INVALID = "email_invalid"
    KEY_FORMAT = "key_format"
    ADDRESS_INVALID = "address_invalid"
    TOO_MANY_CLINICS = "too_many_clinics"
    KEY_REJECTED = "key_rejected"
    USER_INACTIVE = "user_inactive"
    NO_PRACTITIONER_RECORD = "no_practitioner_record"
    SEVERAL_PRACTITIONER_RECORDS = "several_practitioner_records"
    PRACTITIONER_INACTIVE = "practitioner_inactive"
    ADDRESS_NEEDED = "address_needed"
    SHARD_MISMATCH = "shard_mismatch"
    ADDRESS_MISMATCH = "address_mismatch"
    DIFFERENT_ACCOUNT = "different_account"
    DUPLICATE_SUBDOMAIN = "duplicate_subdomain"
    UNREACHABLE = "unreachable"
    RATE_LIMITED = "rate_limited"
    CERTIFICATE_REJECTED = "certificate_rejected"
    ANSWER_UNREADABLE = "answer_unreadable"
    SUPERSEDED = "superseded"
    CLINIC_GONE = "clinic_gone"
    KEY_STORE_FAILED = "key_store_failed"
    REGISTRY_WRITE_FAILED = "registry_write_failed"
    REGISTRY_UNREADABLE = "registry_unreadable"
    LINKED_TO_LIVE_SESSION = "linked_to_live_session"
    KEY_DELETE_FAILED = "key_delete_failed"


class LoadProblem(StrEnum):
    UNREADABLE = "unreadable"
    TOO_LARGE = "too_large"
    NOT_VALID = "not_valid"


@dataclass(frozen=True)
class Refused:
    reason: ClinicRefusal
    clinic_id: str | None = None


@dataclass(frozen=True)
class ValidationRequest:
    """A dispatched Validate or Replace key. It carries the typed key to the
    worker and back to the commit; the key is kept out of the repr."""

    clinic_id: str
    display_name: str
    contact_email: str
    api_key: str = field(repr=False)
    typed_host: ClinicHost | None
    # A Replace key: the record as it stood at dispatch. None: a new clinic.
    expected: ClinicRecord | None
    rev: int


@dataclass(frozen=True)
class ValidatedAccount:
    """What Cliniko confirmed for the key (the worker's success result)."""

    user_id: str
    practitioner_id: str
    host: ClinicHost
    subdomain_confirmed: bool


@dataclass(frozen=True)
class Committed:
    record: ClinicRecord
    replaced: bool


@dataclass(frozen=True)
class Removed:
    record: ClinicRecord


class KeyStore(Protocol):
    """``SecureStorageProvider``'s shape (Credential Manager in the app)."""

    def store(self, clinic_id: str, secret_name: str, value: str) -> None: ...

    def retrieve(self, clinic_id: str, secret_name: str) -> str | None: ...

    def delete(self, clinic_id: str, secret_name: str) -> None: ...


def _refusal_for(error: ClinikoError) -> ClinicRefusal:
    if isinstance(error, InvalidKey):
        return ClinicRefusal.KEY_FORMAT
    if isinstance(error, CredentialsRejected):
        return ClinicRefusal.KEY_REJECTED
    if isinstance(error, RateLimited):
        return ClinicRefusal.RATE_LIMITED
    if isinstance(error, Unreachable):
        return ClinicRefusal.UNREACHABLE
    if isinstance(error, CertificateRejected):
        return ClinicRefusal.CERTIFICATE_REJECTED
    # NotFound, Malformed, RedirectRefused, UnexpectedStatus.
    return ClinicRefusal.ANSWER_UNREADABLE


def _new_clinic_id() -> str:
    return secrets.token_hex(8)


def _utc_now() -> datetime:
    return datetime.now(UTC)


# --- the registry -------------------------------------------------------------


class ClinicRegistry:
    """The clinic registry. Every method but ``run_validation`` runs on the
    GUI thread; ``run_validation`` reads only its request and the injected
    transport. Construction reads ``clinics.json`` and nothing else — no key,
    no network."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        storage: KeyStore | None = None,
        transport: Transport | None = None,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = _new_clinic_id,
    ) -> None:
        self._path = path if path is not None else default_registry_path()
        if storage is None:
            from scribe_desktop.secure_storage import SecureStorageProvider

            storage = SecureStorageProvider()
        self._storage: KeyStore = storage
        self._transport = transport
        self._clock = clock
        self._id_factory = id_factory
        self._revs: dict[str, int] = {}
        self._records: tuple[ClinicRecord, ...] = ()
        self._contact_email: str | None = None
        self._load_problem: LoadProblem | None = None
        self._load()

    # --- reading ----------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def records(self) -> tuple[ClinicRecord, ...]:
        return self._records

    @property
    def contact_email(self) -> str | None:
        return self._contact_email

    @property
    def load_problem(self) -> LoadProblem | None:
        return self._load_problem

    @property
    def key_store(self) -> KeyStore:
        """Where the keys live — note verification (``encounter``) reads a
        clinic's key through it, once per verification, on its worker."""
        return self._storage

    @property
    def transport(self) -> Transport | None:
        """The injected transport (None: the real HTTPS transport)."""
        return self._transport

    def record(self, clinic_id: str) -> ClinicRecord | None:
        return next((r for r in self._records if r.clinic_id == clinic_id), None)

    def allow_list(self) -> tuple[str, ...]:
        """Exactly the registry's hosts (D10), sorted — what Chrome is sent."""
        return tuple(sorted(r.host for r in self._records))

    def rev(self, clinic_id: str) -> int:
        return self._revs.get(clinic_id, 0)

    def _bump(self, clinic_id: str) -> None:
        self._revs[clinic_id] = self.rev(clinic_id) + 1

    def _load(self) -> None:
        try:
            with self._path.open("rb") as stream:
                blob = stream.read(MAX_FILE_BYTES + 1)
        except FileNotFoundError:
            return
        except OSError:
            self._load_problem = LoadProblem.UNREADABLE
            return
        if len(blob) > MAX_FILE_BYTES:
            self._load_problem = LoadProblem.TOO_LARGE
            return
        try:
            parsed = _RegistryFile.model_validate_json(blob)
        except (ValidationError, ValueError):
            self._load_problem = LoadProblem.NOT_VALID
            return
        ids = [r.clinic_id for r in parsed.clinics]
        subdomains = [r.subdomain for r in parsed.clinics]
        if len(set(ids)) != len(ids) or len(set(subdomains)) != len(subdomains):
            self._load_problem = LoadProblem.NOT_VALID
            return
        self._records = parsed.clinics
        self._contact_email = parsed.contact_email

    def _write(self, records: Sequence[ClinicRecord], contact_email: str | None) -> None:
        """Atomic replace of ``clinics.json``; ``OSError``/``StoreWriteError``
        on failure, with the previous file intact."""
        payload = {
            "schema_version": SCHEMA_VERSION,
            "contact_email": contact_email,
            "clinics": [r.model_dump(mode="json") for r in records],
        }
        blob = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(self._path, blob, error_label=REGISTRY_FILENAME)

    # --- validation (D10) ---------------------------------------------------

    def begin_validation(
        self,
        *,
        api_key: str,
        contact_email: str,
        display_name: str | None = None,
        clinic_id: str | None = None,
        typed_address: str | None = None,
    ) -> ValidationRequest | Refused:
        """GUI thread. ``clinic_id`` None adds a clinic (``display_name``
        required); otherwise it is a Replace key for that clinic, which bumps
        its rev before capturing it (D9)."""
        if self._load_problem is not None:
            return Refused(ClinicRefusal.REGISTRY_UNREADABLE)
        try:
            email = validate_contact_email(contact_email.strip())
        except InvalidContactEmail:
            return Refused(ClinicRefusal.EMAIL_INVALID)
        try:
            key_shard = shard_of_key(api_key)
        except InvalidKey:
            return Refused(ClinicRefusal.KEY_FORMAT)
        typed: ClinicHost | None = None
        if typed_address is not None and typed_address.strip():
            try:
                typed = parse_clinic_address(typed_address)
            except ValueError:
                return Refused(ClinicRefusal.ADDRESS_INVALID)
            if typed.shard != key_shard:
                return Refused(ClinicRefusal.SHARD_MISMATCH)
        if clinic_id is None:
            name = (display_name or "").strip()
            try:
                _no_control_chars(name)  # blank, or a control character
            except ValueError:
                return Refused(ClinicRefusal.NAME_INVALID)
            if len(name) > MAX_DISPLAY_NAME_CHARS:
                return Refused(ClinicRefusal.NAME_INVALID)
            if len(self._records) >= MAX_CLINICS:
                return Refused(ClinicRefusal.TOO_MANY_CLINICS)
            if typed is not None and any(r.subdomain == typed.subdomain for r in self._records):
                return Refused(ClinicRefusal.DUPLICATE_SUBDOMAIN)
            new_id = self._id_factory()
            while self.record(new_id) is not None or new_id in self._revs:
                new_id = self._id_factory()
            return ValidationRequest(
                clinic_id=new_id,
                display_name=name,
                contact_email=email,
                api_key=api_key,
                typed_host=typed,
                expected=None,
                rev=self.rev(new_id),
            )
        current = self.record(clinic_id)
        if current is None:
            return Refused(ClinicRefusal.CLINIC_GONE, clinic_id)
        if key_shard != current.shard:
            return Refused(ClinicRefusal.DIFFERENT_ACCOUNT, clinic_id)
        if typed is not None and typed != ClinicHost(current.subdomain, current.shard):
            # The typed address, not the key, is the mismatch (round 15 LOW-007).
            return Refused(ClinicRefusal.ADDRESS_MISMATCH, clinic_id)
        self._bump(clinic_id)
        return ValidationRequest(
            clinic_id=clinic_id,
            display_name=current.display_name,
            contact_email=email,
            api_key=api_key,
            typed_host=typed,
            expected=current,
            rev=self.rev(clinic_id),
        )

    def run_validation(self, request: ValidationRequest) -> ValidatedAccount | Refused:
        """Worker thread: D10's three reads as ONE client call. Never raises;
        every failure is a ``Refused`` naming its class, carrying no key,
        path, id or answer byte."""
        try:
            return self._validate(request)
        except ClinikoError as error:
            reason = _refusal_for(error)
        except Exception:  # noqa: BLE001 - _Shape, InvalidId, the unforeseen: never raise
            reason = ClinicRefusal.ANSWER_UNREADABLE
        # The refusal keeps only the reason: the exception, whose frames hold
        # the key (threat-model Cliniko residue (6)), goes with its block.
        return Refused(reason, request.clinic_id)

    def _validate(self, request: ValidationRequest) -> ValidatedAccount | Refused:
        clinic_id = request.clinic_id
        key_shard = shard_of_key(request.api_key)
        client = ClinikoClient(contact_email=request.contact_email, transport=self._transport)
        api_key = request.api_key
        with client.call(lambda: api_key) as call:
            # D10 as amended 2026-09-27: the role is no gate; the ONE active
            # practitioner record decides.
            user_id, active = _user_identity(call.get_user())
            if not active:
                return Refused(ClinicRefusal.USER_INACTIVE, clinic_id)
            records = _practitioner_records(call.get_practitioners_for_user(user_id))
            if not records:
                return Refused(ClinicRefusal.NO_PRACTITIONER_RECORD, clinic_id)
            if len(records) > 1:
                return Refused(ClinicRefusal.SEVERAL_PRACTITIONER_RECORDS, clinic_id)
            practitioner_id, practitioner_active = records[0]
            if not practitioner_active:
                return Refused(ClinicRefusal.PRACTITIONER_INACTIVE, clinic_id)
            subdomain: str | None
            try:
                subdomain = _public_subdomain(call.get_public_settings())
            except _SETTINGS_REFUSED:
                subdomain = None
        typed = request.typed_host
        expected = request.expected
        if subdomain is not None:
            if typed is not None and typed.subdomain != subdomain:
                return Refused(ClinicRefusal.ADDRESS_MISMATCH, clinic_id)
            host = ClinicHost(subdomain, key_shard)  # P.1 (d)
            confirmed = True
        else:
            if typed is None and expected is not None:
                typed = ClinicHost(expected.subdomain, expected.shard)
            if typed is None:
                return Refused(ClinicRefusal.ADDRESS_NEEDED, clinic_id)
            if typed.shard != key_shard:  # P.1 (d)
                return Refused(ClinicRefusal.SHARD_MISMATCH, clinic_id)
            host = typed
            confirmed = False
        if expected is not None and host != ClinicHost(expected.subdomain, expected.shard):
            return Refused(ClinicRefusal.DIFFERENT_ACCOUNT, clinic_id)
        return ValidatedAccount(
            user_id=user_id,
            practitioner_id=practitioner_id,
            host=host,
            subdomain_confirmed=confirmed,
        )

    def commit_validation(
        self, request: ValidationRequest, result: ValidatedAccount | Refused
    ) -> Committed | Refused:
        """GUI thread: apply a finished validation, or refuse it whole. A
        stale result — its clinic removed, or its rev moved — is named as
        such whatever the worker found, so a delayed refusal is never shown
        as current (codex round 17 PR-LOW-070); a current refusal is
        returned unchanged."""
        clinic_id = request.clinic_id
        if self._load_problem is not None:
            return Refused(ClinicRefusal.REGISTRY_UNREADABLE, clinic_id)
        current = self.record(clinic_id)
        # A Replace for a removed clinic is named as such before the rev check
        # (which Remove's bump would also fail) — round 16 LOW-011.
        if request.expected is not None and current is None:
            return Refused(ClinicRefusal.CLINIC_GONE, clinic_id)
        if self.rev(clinic_id) != request.rev:
            return Refused(ClinicRefusal.SUPERSEDED, clinic_id)
        if request.expected is None and current is not None:
            return Refused(ClinicRefusal.SUPERSEDED, clinic_id)
        if isinstance(result, Refused):
            return result
        if request.expected is None and len(self._records) >= MAX_CLINICS:
            return Refused(ClinicRefusal.TOO_MANY_CLINICS, clinic_id)
        if any(
            r.subdomain == result.host.subdomain and r.clinic_id != clinic_id
            for r in self._records
        ):
            return Refused(ClinicRefusal.DUPLICATE_SUBDOMAIN, clinic_id)
        record = ClinicRecord(
            clinic_id=clinic_id,
            display_name=request.display_name,
            subdomain=result.host.subdomain,
            shard=result.host.shard,
            user_id=result.user_id,
            practitioner_id=result.practitioner_id,
            validated_at=self._clock(),
            subdomain_confirmed=result.subdomain_confirmed,
        )
        if current is None:
            return self._commit_new(record, request)
        return self._commit_replace(record, request)

    def _commit_new(self, record: ClinicRecord, request: ValidationRequest) -> Committed | Refused:
        clinic_id = record.clinic_id
        before = self._records
        after = (*before, record)
        try:
            self._write(after, request.contact_email)
        except (OSError, StoreWriteError):
            return Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, clinic_id)
        self._records, self._contact_email = after, request.contact_email
        self._bump(clinic_id)
        try:
            self._storage.store(clinic_id, KEY_SECRET_NAME, request.api_key)
        except Exception:  # noqa: BLE001 - keyring backends raise their own types
            # A store that raised may still have written (round 15 LOW-010):
            # delete it before un-listing the clinic. If the delete fails, the
            # clinic STAYS listed, so Remove can clear whatever is there.
            try:
                self._storage.delete(clinic_id, KEY_SECRET_NAME)
                self._write(before, request.contact_email)
            except Exception:  # noqa: BLE001 - either failure keeps it listed
                pass  # the record stays listed; Remove clears it
            else:
                self._records = before
            return Refused(ClinicRefusal.KEY_STORE_FAILED, clinic_id)
        return Committed(record, replaced=False)

    def _commit_replace(
        self, record: ClinicRecord, request: ValidationRequest
    ) -> Committed | Refused:
        clinic_id = record.clinic_id
        # Whatever happens next, the stored key may have changed: nothing
        # dispatched under the previous rev may commit.
        self._bump(clinic_id)
        try:
            self._storage.store(clinic_id, KEY_SECRET_NAME, request.api_key)
        except Exception:  # noqa: BLE001 - keyring backends raise their own types
            return Refused(ClinicRefusal.KEY_STORE_FAILED, clinic_id)
        after = tuple(record if r.clinic_id == clinic_id else r for r in self._records)
        try:
            self._write(after, request.contact_email)
        except (OSError, StoreWriteError):
            return Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, clinic_id)
        self._records, self._contact_email = after, request.contact_email
        return Committed(record, replaced=True)

    # --- remove and confirm -------------------------------------------------

    def remove(self, clinic_id: str, *, live_session_clinic: str | None) -> Removed | Refused:
        """GUI thread. Refused while the live session (recording, paused,
        processing or queued) is linked to this clinic (D10) — the caller
        passes that clinic id, or None when no live session is linked."""
        if self._load_problem is not None:
            return Refused(ClinicRefusal.REGISTRY_UNREADABLE, clinic_id)
        current = self.record(clinic_id)
        if current is None:
            return Refused(ClinicRefusal.CLINIC_GONE, clinic_id)
        if live_session_clinic == clinic_id:
            return Refused(ClinicRefusal.LINKED_TO_LIVE_SESSION, clinic_id)
        self._bump(clinic_id)
        try:
            self._storage.delete(clinic_id, KEY_SECRET_NAME)
        except Exception:  # noqa: BLE001 - keyring backends raise their own types
            return Refused(ClinicRefusal.KEY_DELETE_FAILED, clinic_id)
        after = tuple(r for r in self._records if r.clinic_id != clinic_id)
        try:
            self._write(after, self._contact_email)
        except (OSError, StoreWriteError):
            return Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, clinic_id)
        self._records = after
        return Removed(current)

    def confirm_subdomain_from_note(self, clinic_id: str, host: str, expected_rev: int) -> bool:
        """GUI thread; called when a note VERIFIED with this clinic's key on
        ``host`` (Phase 3). Marks a typed subdomain confirmed. False — and
        nothing changes — when the clinic is gone, its rev moved since the
        verification was dispatched, the host is not the clinic's, or the
        write fails (the next verified note retries). True when confirmed,
        now or before."""
        if self._load_problem is not None:
            return False
        current = self.record(clinic_id)
        if current is None or self.rev(clinic_id) != expected_rev or current.host != host:
            return False
        if current.subdomain_confirmed:
            return True
        confirmed = current.model_copy(update={"subdomain_confirmed": True})
        after = tuple(confirmed if r.clinic_id == clinic_id else r for r in self._records)
        try:
            self._write(after, self._contact_email)
        except (OSError, StoreWriteError):
            return False
        self._records = after
        return True
