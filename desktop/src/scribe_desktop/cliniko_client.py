"""Read-only Cliniko API client: the app's ONE network surface (plan D9).

Cliniko workflow safeguards plan, Task 1.1. Everything the desktop app sends
over a network goes through this module, and it can send only a ``GET`` to
``api.<shard>.cliniko.com`` over HTTPS. The confinement is structural:

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
- ``HTTPSTransport.request`` refuses every method but ``GET`` before a
  connection exists, and the client only ever passes ``GET``; there is no
  write method (Critical Constraint 1).
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
- A response body is read ONLY for a 200 (every other status is classified
  from the status line and headers alone, so a refusal whose body stalls
  keeps its own name). It is read with ``read1`` — at most one socket receive
  per call — in pieces that together never ask for more than
  ``MAX_BODY_BYTES + 1`` bytes, with the request deadline checked before each
  piece; a body longer than ``MAX_BODY_BYTES`` (1 MiB) is refused as
  ``Malformed`` and never parsed.

Failures become NAMED errors (``ClinikoError`` subclasses) whose text is a
fixed sentence per class: what an exception raised here RENDERS — its
message, repr or formatted traceback — carries no key, request path, id or
response byte, and each is raised OUTSIDE the ``except`` block that
classified the library's exception, so it has no ``__context__`` to render
either. The exception OBJECT is not so clean: its ``__traceback__`` keeps
the frames it unwound through, locals included (``call``'s ``api_key``
before its ``del``, ``_get``'s ``headers`` with the Basic token, the path,
ids and ``RawResponse``), so while a caller holds the exception those values
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


class InvalidContactEmail(ValueError):
    def __init__(self) -> None:
        super().__init__("the contact email is not a plain email address")


class InvalidId(ValueError):
    def __init__(self) -> None:
        super().__init__("a Cliniko id must be 1-19 digits with no leading zero")


# --- the transport seam -----------------------------------------------------


@dataclass(frozen=True)
class RawResponse:
    """What a transport hands back: the status, the rate-limit reset header
    and, for a 200 only, at most ``max_body + 1`` body bytes (the extra byte
    proves "over"); any other status carries ``b""`` — its body is never
    read. The body is patient data, so it is kept out of the repr."""

    status: int
    rate_limit_reset: str | None
    body: bytes = field(repr=False)


class Transport(Protocol):
    """Injected in tests; ``HTTPSTransport`` in the app."""

    def request(
        self, method: str, host: str, path: str, headers: Mapping[str, str], max_body: int
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

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None: ...

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
    named error raised with no chained context. Only a 200's body is read:
    every other status is final from its status line and headers (codex
    round 8 PR-MED-012 — a 401/403/429 whose body stalled used to become
    ``Unreachable``), and the unread body goes with the closed connection.
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
        self, method: str, host: str, path: str, headers: Mapping[str, str], max_body: int
    ) -> RawResponse:
        if method != "GET":
            raise ValueError("the Cliniko transport sends GET only")
        if max_body < 0:
            raise ValueError("max_body must be non-negative")
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
        try:
            _guarded(lambda: conn.set_debuglevel(0))
            _guarded(lambda: conn.request("GET", path, headers=headers))
            in_time()
            response = _guarded(conn.getresponse)
            status = _guarded(lambda: int(response.status))
            reset = _guarded(lambda: response.getheader("X-RateLimit-Reset"))
            body = _read_bounded(response, max_body, in_time) if status == 200 else b""
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001 - a close failure changes no outcome
                pass
        return RawResponse(status=status, rate_limit_reset=reset, body=body)


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
    """The GET methods of one logical call. Every method returns the answer's
    JSON object (a ``dict``) or raises a named error."""

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

    def _get(self, resource: str) -> dict[str, Any]:
        if self._authorization is None:
            raise RuntimeError("this Cliniko call has ended; open a new one")
        headers = {
            "Authorization": self._authorization,
            "Accept": "application/json",
            "User-Agent": self._agent,
        }
        raw = self._transport.request(
            "GET", self._host, API_VERSION_PREFIX + resource, headers, MAX_BODY_BYTES
        )
        return _interpret(raw)


def _interpret(raw: RawResponse) -> dict[str, Any]:
    status = raw.status
    if status == 200:
        return _parse_object(raw.body)
    if status in (401, 403):
        raise CredentialsRejected(status)
    if status == 404:
        raise NotFound()
    if status == 429:
        reset = raw.rate_limit_reset
        raise RateLimited(reset if reset and _RESET_RE.fullmatch(reset) else None)
    if 300 <= status < 400:
        raise RedirectRefused(status)
    if 500 <= status < 600:
        raise Unreachable(status)
    raise UnexpectedStatus(status)


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
