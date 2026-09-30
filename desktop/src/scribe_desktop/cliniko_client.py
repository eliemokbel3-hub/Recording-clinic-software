"""The Cliniko API client: the app's ONE network surface (plan D9).

Cliniko workflow safeguards plan, Task 1.1; the one draft write added by the
cliniko-draft-write plan, Task 1.1 (D1). Everything the desktop app sends over
a network goes through this module, and it can send only two request shapes
to ``api.<shard>.cliniko.com`` over HTTPS: a ``GET`` with no body, or a
``PATCH`` with a body to exactly ``/v1/treatment_notes/<id>``. The
confinement is structural:

- ``http.client`` is imported HERE and nowhere else in ``desktop/src``. Ruff's
  TID251 bans ``http``, ``socket``, ``urllib.request`` and
  ``PySide6.QtNetwork`` everywhere; the single TID251 exemption is on this
  module's import, and a test pins both the count (exactly one) and that no
  other module imports ``http``/``ssl``/``socket``/``urllib.request``. A
  DYNAMIC import (``importlib.import_module("http.client")``) is outside what
  either check sees — the residue of a source-level ban.
- The host is built only from a documented shard (``SHARDS``) taken from the
  API key's ``-<shard>`` suffix. A key with no suffix or an unknown one is
  REFUSED (``InvalidKey``), never defaulted to ``au1``.
- ``HTTPSTransport.request`` admits exactly those two shapes and raises
  ``ValueError`` for anything else — another method, a lower-case spelling, a
  ``GET`` with a body, a ``PATCH`` without one, to any other host, outside
  ``/v1/``, a ``PATCH`` to any other path, a header name ``_send`` does not
  set (or one set twice in two cases), a ``PATCH`` whose ``Content-Type`` is
  not exactly ``application/json``, or whose body is not a JSON object with
  exactly ONE key, ``content``, holding an object — before a connection
  exists. That body-and-header check is the choke
  point: whoever builds the request (a ``DraftContent`` subclass with an
  extra field, a future method, another module calling the transport), a
  top-level ``draft``, ``title`` or id cannot leave, so a note can only be
  filled, never finalised, created or moved (draft-write Critical
  Constraint 1). The method string ``"PATCH"`` is written once in this
  module (``_WRITE_METHOD``; a source test pins the count), and the only
  caller that sends it is ``ClinikoCall.write_draft_note``, whose body is
  serialised from ``DraftContent`` (one field, ``content``). Residue: what
  Cliniko does with a key INSIDE ``content`` is Cliniko's, and so is its
  handling of a PATCH to a note that is already final — the write path
  re-reads the note first (draft-write D3), and Cliniko documents a final
  note as immutable.
- No redirects: ``http.client`` never follows one, and a 3xx answer is
  ``RedirectRefused``. No proxy: ``HTTPSConnection`` reads no proxy
  environment variable and ``set_tunnel`` is never called. The debug level is
  pinned to 0, so ``http.client`` never prints a request line or header.
- TLS: ``build_tls_context`` is a ``PROTOCOL_TLS_CLIENT`` context (hostname
  check on, certificate required) with ``minimum_version = TLSv1_2`` and the
  Windows certificate store (``load_default_certs``). It is deliberately NOT
  ``ssl.create_default_context``, which opens the file named by
  ``SSLKEYLOGFILE``; this context never reads that variable and pins
  ``keylog_filename = None``. ``benchmark.apply_offline_env`` also deletes the
  variable at startup and ``assert_offline_env`` refuses it. Residue: the
  trust decision is the Windows store's, so a root installed there (a TLS
  inspection proxy's) is trusted like any other.
- A response body is read ONLY for a 200, and for a ``PATCH`` also for a 422
  (every other status is classified from the status line and headers alone,
  so a refusal whose body stalls keeps its own name). It is read with
  ``read1`` — at most one socket receive per call — in pieces that together
  never ask for more than ``MAX_BODY_BYTES + 1`` bytes, with the request
  deadline checked before each piece; a body longer than ``MAX_BODY_BYTES``
  (1 MiB) is refused as ``Malformed`` and never parsed. For a ``PATCH`` the
  status line decides (draft-write D5): a body that then fails to read is
  reported as unreadable, never as a failure of the request, so a 200 whose
  body stalls is still a write Cliniko accepted.
- A 422 answer to the write is reduced to FIXED categories before any
  exception exists: each top-level ``errors`` key becomes one of
  ``REJECTION_CATEGORIES`` (Cliniko's documented treatment-note field names)
  or ``"other"``; no key text, value or other body byte survives in the
  error, and the body is dropped before the error is raised, so no frame of
  the call holds it either (draft-write D11). An identifier-shaped key can
  itself carry data, so the categories are a fixed set, not a shape filter.

Failures become NAMED errors (``ClinikoError`` subclasses) whose text is a
fixed sentence per class: what an exception raised here RENDERS — its
message, repr or formatted traceback — carries no key, request path, id or
response byte, and each is raised OUTSIDE the ``except`` block that
classified the library's exception, so it has no ``__context__`` to render
either. The exception OBJECT is not so clean: its ``__traceback__`` keeps
the frames it unwound through, locals included (``call``'s ``api_key``
before its ``del``, ``_send``'s ``headers`` with the Basic token, the path,
ids, ``RawResponse`` and, for the write, the serialised body, which is note
text), so while a caller holds the exception those values
stay referenced (codex round 9 PR-MED-030; the threat model's Cliniko
residue (6)). The transport wraps each library call
separately (construction, request, getresponse, every read) because a
library can fail on first use rather than at construction (lessons
2026-09-24). This module never logs.

The key: ``ClinikoClient.call(read_key)`` calls ``read_key`` ONCE per logical
call (a Clinics-tab Validate or Replace key reads the key just typed; note
verification will read Credential Manager) and every
request inside that ``with`` block shares it; on exit the call drops its
reference to the Authorization header and refuses further use. A Python
``str`` cannot be zeroed, so "dropped" means this module's own references
go (a live exception from the call aside, above); the bytes live until the
interpreter reuses the memory.
"""

from __future__ import annotations

import base64
import http.client  # noqa: TID251 - the ONE sanctioned network import (plan D9, Task 1.1)
import json
import re
import ssl
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Final, Protocol

from pydantic import BaseModel, ConfigDict

# The documented Cliniko shards (docs.api.cliniko.com, 2026-09-27). A key's
# ``-<shard>`` suffix selects ``api.<shard>.cliniko.com``.
SHARDS: Final[frozenset[str]] = frozenset(
    {"au1", "au2", "au3", "au4", "au5", "ca1", "uk1", "uk2", "uk3", "us1", "eu1"}
)
API_VERSION_PREFIX: Final = "/v1"
HTTPS_PORT: Final = 443
# Each socket operation (connect, every TLS/send/receive step) times out at
# TIMEOUT_SECONDS. DEADLINE_SECONDS bounds the request as a whole where it can
# stretch without end — the body: it is checked after the request is sent and
# before every body read, and each body read is ``read1`` (at most one socket
# receive), so a slow-drip body is abandoned (``Unreachable``) at most one
# receive timeout after the deadline (codex round 8 PR-MED-010: a plain
# ``read(n)`` loops receives until it has ``n`` bytes). Bounded ONLY per step,
# the named residue: a single library call that is not a body read — the
# connect + TLS handshake + send, reading the status line and headers, and a
# chunked body's framing (the chunk-size line, its CRLF, the trailer).

TIMEOUT_SECONDS: Final = 15.0
DEADLINE_SECONDS: Final = 30.0
MAX_BODY_BYTES: Final = 1 * 1024 * 1024
APP_NAME: Final = "Clinic Scribe"

# A Cliniko key is base64 text plus ``-<shard>``. The charset refuses CR/LF and
# every other header-breaking character before the key reaches a header.
_KEY_RE: Final = re.compile(r"(?P<body>[A-Za-z0-9+/=_\-]{8,500})-(?P<shard>[a-z]{2}[0-9])")
# The protocol's id shape (plan D2): digits, no leading zero, at most 19.
_ID_RE: Final = re.compile(r"[1-9][0-9]{0,18}")
# A deliberately simple shape check; its job is refusing header injection
# (CR/LF, parentheses, spaces) in the User-Agent, not RFC 5322 validation.
_EMAIL_RE: Final = re.compile(
    r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]{1,63}(\.[A-Za-z0-9\-]{1,63})+"
)
_EMAIL_MAX: Final = 254
# ``X-RateLimit-Reset`` is kept only when it is short, plain text.
_RESET_RE: Final = re.compile(r"[0-9A-Za-z:.+\- ]{1,40}")
# The ONE write (draft-write D1): this method string appears nowhere else in
# the module, and the transport admits it only with a body, only to a path of
# this shape.
_WRITE_METHOD: Final = "PATCH"
_WRITE_PATH_RE: Final = re.compile(API_VERSION_PREFIX + r"/treatment_notes/[1-9][0-9]{0,18}")
# Every request is admitted only to a documented API host (the transport's
# own pin; ``ClinikoClient`` builds the host from the key's shard as well).
_API_HOSTS: Final[frozenset[str]] = frozenset(f"api.{shard}.cliniko.com" for shard in SHARDS)
# The header names ``_send`` sets (casefolded); the write adds Content-Type.
_JSON: Final = "application/json"
_READ_HEADERS: Final[frozenset[str]] = frozenset({"authorization", "accept", "user-agent"})
# D11: a 422's ``errors`` keys are reduced to these (Cliniko's documented
# treatment-note fields) or to ``REJECTION_OTHER``; nothing else survives.
REJECTION_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "content",
        "title",
        "patient_id",
        "booking_id",
        "attendee_id",
        "treatment_note_template_id",
        "draft",
    }
)
REJECTION_OTHER: Final = "other"


# --- named errors -----------------------------------------------------------


class ClinikoError(Exception):
    """Base of every failure this module raises. The text is the class's
    fixed ``MESSAGE`` — never a key, path, id or response byte."""

    MESSAGE: str = "the Cliniko request failed"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class InvalidKey(ClinikoError):
    MESSAGE = "the API key is not in Cliniko's format or names an unknown shard"


class CredentialsRejected(ClinikoError):
    """HTTP 401 or 403: the key was refused or lacks permission."""

    MESSAGE = "Cliniko rejected the API key"

    def __init__(self, status: int) -> None:
        super().__init__()
        self.status = status


class NotFound(ClinikoError):
    MESSAGE = "Cliniko has no such record"


class RateLimited(ClinikoError):
    """HTTP 429. ``reset`` is the ``X-RateLimit-Reset`` header when it is
    short plain text, else None; it is an attribute, never in the text."""

    MESSAGE = "Cliniko's rate limit was reached"

    def __init__(self, reset: str | None) -> None:
        super().__init__()
        self.reset = reset


class Unreachable(ClinikoError):
    """No usable answer: a connection or DNS failure, a timeout, a dropped
    connection, a TLS failure other than certificate verification, or a 5xx
    (``status`` set only for the 5xx case)."""

    MESSAGE = "Cliniko could not be reached"

    def __init__(self, status: int | None = None) -> None:
        super().__init__()
        self.status = status


class CertificateRejected(ClinikoError):
    MESSAGE = "Cliniko's TLS certificate was not trusted"


class Malformed(ClinikoError):
    """The answer could not be used: an unparseable status line or headers,
    a body over ``MAX_BODY_BYTES``, a body that is not a JSON object, or an
    unclassified library failure."""

    MESSAGE = "Cliniko's answer could not be read"


class RedirectRefused(ClinikoError):
    MESSAGE = "Cliniko answered with a redirect, which is refused"

    def __init__(self, status: int) -> None:
        super().__init__()
        self.status = status


class UnexpectedStatus(ClinikoError):
    MESSAGE = "Cliniko answered with an unexpected status"

    def __init__(self, status: int) -> None:
        super().__init__()
        self.status = status


class ClinikoRejected(ClinikoError):
    """The draft write was refused with a 4xx other than 401, 403, 404 and
    429 (draft-write D5). ``categories`` is sorted, drawn only from
    ``REJECTION_CATEGORIES`` and ``REJECTION_OTHER``, and set only for a 422
    whose body could be read and parsed; it is an attribute, never in the
    text."""

    MESSAGE = "Cliniko did not accept the draft"

    def __init__(self, status: int, categories: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.status = status
        self.categories = categories


class InvalidContactEmail(ValueError):
    def __init__(self) -> None:
        super().__init__("the contact email is not a plain email address")


class InvalidId(ValueError):
    def __init__(self) -> None:
        super().__init__("a Cliniko id must be 1-19 digits with no leading zero")


class DraftUnencodable(ValueError):
    """The draft body could not be serialised as strict UTF-8 JSON (a lone
    surrogate, a NaN, a value JSON has no form for). Fixed text: the codec's
    own error carries the whole note in its ``object``, so it never leaves
    this module."""

    def __init__(self) -> None:
        super().__init__("the draft could not be encoded as UTF-8 JSON")


# --- the transport seam -----------------------------------------------------


@dataclass(frozen=True)
class RawResponse:
    """What a transport hands back: the status, the rate-limit reset header
    and, for a 200 (and a ``PATCH``'s 422) only, at most ``max_body + 1``
    body bytes (the extra byte proves "over"); any other status carries
    ``b""`` — its body is never read. ``body_unreadable`` is set only for a
    ``PATCH`` whose read body failed (the status line had already decided,
    draft-write D5); its ``body`` is then ``b""``. The body is patient data,
    so it is kept out of the repr."""

    status: int
    rate_limit_reset: str | None
    body: bytes = field(repr=False)
    body_unreadable: bool = False


class Transport(Protocol):
    """Injected in tests; ``HTTPSTransport`` in the app. ``body`` is the
    request body: ``None`` for a ``GET``, the serialised draft for the
    ``PATCH``."""

    def request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> RawResponse: ...


class _Response(Protocol):
    @property
    def status(self) -> int: ...

    def getheader(self, name: str, /) -> str | None: ...

    # ``read1`` only — never ``read``: ``HTTPResponse.read(n)`` loops socket
    # receives until it has ``n`` bytes, so the deadline could not bound it.
    def read1(self, amt: int, /) -> bytes: ...


class _Connection(Protocol):
    def set_debuglevel(self, level: int, /) -> None: ...

    def request(
        self, method: str, url: str, body: bytes | None = None, *, headers: Mapping[str, str]
    ) -> None: ...

    def getresponse(self) -> _Response: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[..., _Connection]


def build_tls_context() -> ssl.SSLContext:
    """TLS 1.2+, certificate and hostname verified against the Windows store,
    no key log. See the module docstring for why this is not
    ``ssl.create_default_context``."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    context.keylog_filename = None  # type: ignore[assignment]
    return context


def _classify(exc: BaseException) -> type[ClinikoError]:
    """Map the stdlib raise set of ``http.client`` + ``ssl`` to a named error.

    Order matters: ``SSLCertVerificationError`` is also a ``ValueError`` and
    an ``OSError``; ``RemoteDisconnected`` is both a ``ConnectionResetError``
    and a ``BadStatusLine``; ``IncompleteRead`` is an ``HTTPException``.
    """
    if isinstance(exc, ssl.SSLCertVerificationError):
        return CertificateRejected
    if isinstance(exc, (http.client.RemoteDisconnected, http.client.IncompleteRead)):
        return Unreachable
    if isinstance(exc, OSError):  # ssl.SSLError, TimeoutError, DNS, refused, reset
        return Unreachable
    return Malformed  # HTTPException (bad status line, header limits), ValueError, other


class HTTPSTransport:
    """The real transport: one ``HTTPSConnection`` per request, closed after.

    Each library call is wrapped on its own (``_guarded``) so a failure at
    any of them — construction, request (connect + TLS handshake + send),
    ``getresponse``, the status/header read, every body read — becomes a
    named error raised with no chained context. Only a 200's body is read,
    and for the ``PATCH`` also a 422's (the module docstring): every other
    status is final from its status line and headers (codex round 8
    PR-MED-012 — a 401/403/429 whose body stalled used to become
    ``Unreachable``), and the unread body goes with the closed connection.
    A ``PATCH`` body that fails to read after its status is reported
    (``RawResponse.body_unreadable``), never raised (draft-write D5).
    """

    def __init__(
        self,
        *,
        connection_factory: ConnectionFactory | None = None,
        tls_context: Callable[[], ssl.SSLContext] = build_tls_context,
        timeout: float = TIMEOUT_SECONDS,
        deadline: float = DEADLINE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._factory: ConnectionFactory = (
            connection_factory if connection_factory is not None else http.client.HTTPSConnection
        )
        self._tls_context = tls_context
        self._timeout = timeout
        self._deadline = deadline
        self._clock = clock

    def request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> RawResponse:
        headers = _admit(method, host, path, headers, body)
        if max_body < 0:
            raise ValueError("max_body must be non-negative")
        writing = method == _WRITE_METHOD
        expires = self._clock() + self._deadline

        def in_time() -> None:
            if self._clock() > expires:
                raise Unreachable()

        context = _guarded(self._tls_context)
        conn = _guarded(
            lambda: self._factory(
                host, port=HTTPS_PORT, timeout=self._timeout, context=context
            )
        )
        unreadable = False
        try:
            _guarded(lambda: conn.set_debuglevel(0))
            _guarded(lambda: conn.request(method, path, body, headers=headers))
            in_time()
            response = _guarded(conn.getresponse)
            status = _guarded(lambda: int(response.status))
            reset = _guarded(lambda: response.getheader("X-RateLimit-Reset"))
            answer = b""
            if writing and status in (200, 422):
                # The status line has decided (draft-write D5): a body that
                # fails to read is reported, never raised.
                read = _read_after_status(response, max_body, in_time)
                unreadable = read is None
                answer = read or b""
            elif status == 200:
                answer = _read_bounded(response, max_body, in_time)
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001 - a close failure changes no outcome
                pass
        return RawResponse(
            status=status, rate_limit_reset=reset, body=answer, body_unreadable=unreadable
        )


def _admit(
    method: str, host: str, path: str, headers: Mapping[str, str], body: bytes | None
) -> dict[str, str]:
    """The transport's allow-list (draft-write D1): to a documented API host
    and under ``/v1/``, a ``GET`` with no body, or the ``PATCH`` to one
    treatment note's path with a ``{"content": {...}}`` JSON body and nothing
    else — each with only ``_send``'s own header names (round 10 MED-001: a
    caller-chosen ``Content-Type``, ``Content-Length`` or
    ``Transfer-Encoding`` could make the same bytes parse as something else).
    Anything else raises before a connection exists.

    Returns the headers as a plain ``dict`` snapshot, and ``request`` sends
    ONLY that snapshot: the method, host, path and every header name and
    value must be exactly ``str`` and the body exactly ``bytes``, so what is
    checked is what is sent (round 11 LOW-002 — a caller-built ``Mapping``
    that answers differently on a second pass, a ``bytes`` subclass that
    ``http.client`` would stream as a file, or a ``str`` subclass with its
    own ``__eq__`` is refused)."""
    pairs = list(headers.items())
    exact = (
        type(method) is str
        and type(host) is str
        and type(path) is str
        and (body is None or type(body) is bytes)
        and all(type(name) is str and type(value) is str for name, value in pairs)
    )
    snapshot = dict(pairs)
    if exact and host in _API_HOSTS and path.startswith(API_VERSION_PREFIX + "/"):
        if method == "GET" and body is None and _headers_admitted(snapshot, writing=False):
            return snapshot
        if (
            method == _WRITE_METHOD
            and _WRITE_PATH_RE.fullmatch(path) is not None
            and body is not None
            and _is_draft_body(body)
            and _headers_admitted(snapshot, writing=True)
        ):
            return snapshot
    raise ValueError(
        "the Cliniko transport sends a GET, or a draft PATCH to one treatment note, only"
    )


def _headers_admitted(headers: dict[str, str], *, writing: bool) -> bool:
    """Header names (ASCII, case-insensitive, each once) from ``_send``'s
    set; the write also carries exactly ``Content-Type: application/json``.
    ASCII first: Unicode case-folding maps some other letters onto ASCII
    ones (U+017F, the long s, folds to ``"s"``), so ``lower()`` on an ASCII
    name is the comparison (H1 round 45 LOW-004)."""
    if not all(name.isascii() for name in headers):
        return False
    names = [name.lower() for name in headers]
    if len(set(names)) != len(names) or not set(names) <= _READ_HEADERS | {"content-type"}:
        return False
    content_type = next(
        (value for name, value in headers.items() if name.lower() == "content-type"),
        None,
    )
    return content_type == _JSON if writing else content_type is None


def _is_draft_body(body: bytes) -> bool:
    """The body as Cliniko will read it — parsed, so an escaped key
    (``"\\u0064raft"``) counts as the key it spells — is a JSON object whose
    ONLY key is ``content`` and whose ``content`` is an object."""
    parsed: object
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (ValueError, RecursionError):
        return False
    return (
        isinstance(parsed, dict)
        and list(parsed) == ["content"]
        and isinstance(parsed["content"], dict)
    )


def _read_after_status(
    response: _Response, max_body: int, in_time: Callable[[], None]
) -> bytes | None:
    """A write answer's body, or None when it could not be read (a stall
    past the deadline, a dropped connection); the named error stays here."""
    try:
        return _read_bounded(response, max_body, in_time)
    except ClinikoError:
        return None


def _guarded[T](fn: Callable[[], T]) -> T:
    """Run one library call; on failure raise its named error with NO
    ``__context__`` (raised after the ``except`` block has finished)."""
    error: type[ClinikoError]
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - every failure is classified
        error = _classify(exc)
    raise error()


def _read_bounded(
    response: _Response, max_body: int, in_time: Callable[[], None]
) -> bytes:
    """At most ``max_body + 1`` bytes: each ``read1`` (one socket receive)
    asks only for what is left of that allowance, and ``in_time`` runs before
    every one; an empty piece is the end of the body."""
    allowance = max_body + 1
    chunks: list[bytes] = []
    total = 0
    while total < allowance:
        in_time()
        chunk = _guarded(partial(response.read1, allowance - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)[:allowance]


# --- the write's body and answer ----------------------------------------------


class NoteContent(BaseModel):
    """A treatment note's ``content`` object as Cliniko shapes it:
    ``{"sections": [{name, description?, questions: [...]}, ...]}``
    (``content.sections[].questions[]``, confirmed by the safeguards plan's
    P.1). Loosely typed so unknown question types, checkbox ``answers``
    arrays and any other key of the object round-trip unchanged."""

    model_config = ConfigDict(extra="allow", frozen=True)

    sections: list[dict[str, Any]]


class DraftContent(BaseModel):
    """The draft write's request body (draft-write D1): ``content`` and
    nothing else. There is no ``draft``, ``title``, patient, booking,
    attendee or template field, and any other key is refused at construction
    (``extra="forbid"``), so the serialised body has exactly one top-level
    key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: NoteContent

    def to_body(self) -> bytes:
        """The UTF-8 JSON body ``{"content": {"sections": [...]}}``. Strict:
        a lone surrogate, a NaN or a value JSON cannot hold raises
        ``DraftUnencodable`` — with no chained context — before any request
        exists (the write module checks earlier still)."""
        try:
            return json.dumps(self.model_dump(), ensure_ascii=False, allow_nan=False).encode(
                "utf-8"
            )
        except (ValueError, TypeError, RecursionError):  # UnicodeEncodeError is a ValueError
            pass
        raise DraftUnencodable()  # outside the handler: no __context__


@dataclass(frozen=True)
class WriteAnswer:
    """A 200 to the draft write. ``written`` is True by construction: every
    other answer raises. ``note`` is the parsed echo when the body could be
    read and parsed, else None — the write happened either way
    (draft-write D5). Kept out of the repr: it is note text."""

    written: bool
    note: dict[str, Any] | None = field(repr=False)


# --- the client -------------------------------------------------------------


def validate_contact_email(email: str) -> str:
    """The User-Agent's contact email, refused on CR/LF or a failed shape
    check (``InvalidContactEmail`` carries no part of it)."""
    if len(email) > _EMAIL_MAX or _EMAIL_RE.fullmatch(email) is None:
        raise InvalidContactEmail()
    return email


def shard_of_key(api_key: str) -> str:
    """The key's documented shard; ``InvalidKey`` for a missing or unknown
    suffix or any character outside the key alphabet."""
    match = _KEY_RE.fullmatch(api_key)
    if match is None or match.group("shard") not in SHARDS:
        raise InvalidKey()
    return match.group("shard")


def api_host(shard: str) -> str:
    if shard not in SHARDS:
        raise InvalidKey()
    return f"api.{shard}.cliniko.com"


def check_id(value: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise InvalidId()
    return value


class ClinikoClient:
    """Builds one ``ClinikoCall`` per logical call. Holds no key."""

    def __init__(self, *, contact_email: str, transport: Transport | None = None) -> None:
        self._user_agent = f"{APP_NAME} ({validate_contact_email(contact_email)})"
        self._transport: Transport = transport if transport is not None else HTTPSTransport()

    @contextmanager
    def call(self, read_key: Callable[[], str | None]) -> Iterator[ClinikoCall]:
        """Read the key ONCE, yield a call bound to it, drop it on exit.

        ``read_key`` is invoked exactly once, before anything else; a missing
        key is ``CredentialsRejected(401)`` without a request, and a key in
        the wrong shape is ``InvalidKey`` without a request.
        """
        api_key = read_key()
        if not api_key:
            raise CredentialsRejected(401)
        host = api_host(shard_of_key(api_key))
        token = base64.b64encode(f"{api_key}:".encode("ascii")).decode("ascii")
        del api_key
        call = ClinikoCall(self._transport, host, f"Basic {token}", self._user_agent)
        del token
        try:
            yield call
        finally:
            call.close()


class ClinikoCall:
    """The methods of one logical call: the GETs, each returning the answer's
    JSON object (a ``dict``) or raising a named error, and the one draft
    write, ``write_draft_note``."""

    def __init__(self, transport: Transport, host: str, authorization: str, agent: str) -> None:
        self._transport = transport
        self._host = host
        self._authorization: str | None = authorization
        self._agent = agent

    @property
    def host(self) -> str:
        return self._host

    def close(self) -> None:
        self._authorization = None

    def get_user(self) -> dict[str, Any]:
        return self._get("/user")

    def get_practitioners_for_user(self, user_id: str) -> dict[str, Any]:
        # ``q[]=user_id:=<id>`` percent-encoded; the id is digits only.
        return self._get(f"/practitioners?q%5B%5D=user_id%3A%3D{check_id(user_id)}")

    def get_public_settings(self) -> dict[str, Any]:
        return self._get("/settings/public")

    def get_settings(self) -> dict[str, Any]:
        return self._get("/settings")

    def get_treatment_note(self, note_id: str) -> dict[str, Any]:
        return self._get(f"/treatment_notes/{check_id(note_id)}")

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        return self._get(f"/patients/{check_id(patient_id)}")

    def get_booking(self, booking_id: str) -> dict[str, Any]:
        return self._get(f"/bookings/{check_id(booking_id)}")

    def get_treatment_note_template(self, template_id: str) -> dict[str, Any]:
        return self._get(f"/treatment_note_templates/{check_id(template_id)}")

    def write_draft_note(self, note_id: str, content: DraftContent) -> WriteAnswer:
        """Fill the draft ``note_id`` with ``content`` — the ONE write
        (draft-write D1). Classified on the status line before any body is
        used (D5): a 200 is a ``WriteAnswer`` whatever its body does; 401/403
        ``CredentialsRejected``; 404 ``NotFound``; 422 ``ClinikoRejected``
        with D11's fixed categories; any other 4xx but 429
        ``ClinikoRejected`` with none; 429 ``RateLimited``; 3xx
        ``RedirectRefused``; 5xx ``Unreachable``; anything else
        ``UnexpectedStatus``. The transport's own failures are named too:
        ``Unreachable`` (a timeout, a lost connection, a TLS failure),
        ``CertificateRejected``, ``Malformed`` (no readable status line, or a
        failure before anything was sent). For D5 the request WAS NOT
        APPLIED only on ``CredentialsRejected``, ``NotFound`` and
        ``ClinikoRejected``; every other failure is ``unknown``. No request
        is made for a bad id (``InvalidId``), an unencodable body
        (``DraftUnencodable``) or an ended call (``RuntimeError``).

        The 422 body is dropped before the error is raised, so no frame of
        this call holds Cliniko's echo; ``content`` (what was sent) stays in
        this frame's locals while a caller holds the error (the module
        docstring's traceback residue)."""
        path = f"/treatment_notes/{check_id(note_id)}"
        body = content.to_body()
        raw = self._send(_WRITE_METHOD, path, body)
        del body
        outcome = _write_outcome(raw)
        del raw
        if isinstance(outcome, ClinikoError):
            raise outcome
        return outcome

    def _get(self, resource: str) -> dict[str, Any]:
        return _interpret(self._send("GET", resource, None))

    def _send(self, method: str, resource: str, body: bytes | None) -> RawResponse:
        if self._authorization is None:
            raise RuntimeError("this Cliniko call has ended; open a new one")
        headers = {
            "Authorization": self._authorization,
            "Accept": _JSON,
            "User-Agent": self._agent,
        }
        if body is not None:
            headers["Content-Type"] = _JSON
        return self._transport.request(
            method, self._host, API_VERSION_PREFIX + resource, headers, MAX_BODY_BYTES, body=body
        )


def _interpret(raw: RawResponse) -> dict[str, Any]:
    if raw.status == 200:
        return _parse_object(raw.body)
    raise _status_error(raw.status, raw.rate_limit_reset)


def _status_error(status: int, reset: str | None) -> ClinikoError:
    """The named error for every answer but a 200, for a GET; for the
    write, every class ``_write_outcome`` has not already decided."""
    if status in (401, 403):
        return CredentialsRejected(status)
    if status == 404:
        return NotFound()
    if status == 429:
        return RateLimited(reset if reset and _RESET_RE.fullmatch(reset) else None)
    if 300 <= status < 400:
        return RedirectRefused(status)
    if 500 <= status < 600:
        return Unreachable(status)
    return UnexpectedStatus(status)


def _write_outcome(raw: RawResponse) -> WriteAnswer | ClinikoError:
    """``write_draft_note``'s classes (draft-write D5), decided on the
    status alone; the body is consulted only after the class is fixed. An
    error is RETURNED, not raised, so the caller can drop ``raw`` first; it
    is built outside any handler, so it has neither ``__cause__`` nor
    ``__context__``."""
    status = raw.status
    if status == 200:
        note: dict[str, Any] | None
        try:
            note = None if raw.body_unreadable else _parse_object(raw.body)
        except Malformed:
            note = None
        return WriteAnswer(written=True, note=note)
    if status == 422:
        # Reduced to fixed categories here (D11).
        categories = () if raw.body_unreadable else _rejection_categories(raw.body)
        return ClinikoRejected(status, categories)
    if 400 <= status < 500 and status not in (401, 403, 404, 429):
        return ClinikoRejected(status)
    return _status_error(status, raw.rate_limit_reset)


def _rejection_categories(body: bytes) -> tuple[str, ...]:
    """D11: the 422 body's top-level ``errors`` keys as fixed categories —
    each a ``REJECTION_CATEGORIES`` member or ``REJECTION_OTHER``. An
    oversize, unparseable or differently shaped body gives none. No key text
    or value leaves this function."""
    if len(body) > MAX_BODY_BYTES:
        return ()
    parsed: object
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (ValueError, RecursionError):
        parsed = None
    if not isinstance(parsed, dict):
        return ()
    errors = parsed.get("errors")
    if not isinstance(errors, dict):
        return ()
    return tuple(
        sorted({key if key in REJECTION_CATEGORIES else REJECTION_OTHER for key in errors})
    )


def _parse_object(body: bytes) -> dict[str, Any]:
    if len(body) > MAX_BODY_BYTES:
        raise Malformed()
    parsed: object
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (ValueError, RecursionError):  # JSONDecodeError, UnicodeDecodeError, int digits
        parsed = None
    if not isinstance(parsed, dict):
        raise Malformed()  # raised outside the except block: no chained context
    return parsed
