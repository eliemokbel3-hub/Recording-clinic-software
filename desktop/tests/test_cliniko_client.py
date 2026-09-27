"""Cliniko workflow safeguards plan, Task 1.1: the read-only Cliniko client.

No test here opens a socket or contacts Cliniko. The client is driven through
an injected ``Transport`` fake, and ``HTTPSTransport`` through an injected
connection factory whose fake connection records every call; the only real
stdlib object built is the TLS context (``build_tls_context``), which reads
the Windows certificate store and touches no network.

Covered (plan Validation, "Client"):
- the host pin: every documented shard maps to ``api.<shard>.cliniko.com``; an
  unknown or missing suffix, or a header-breaking key, is ``InvalidKey`` with
  no request made;
- GET only: every method sends ``GET``; the real transport refuses any other
  method before a connection exists; the module source names no other method;
- redirects refused, the size cap (read bounded at the call, over-cap refused),
  and every named error, per status and per library failure stage, including
  ``CertificateRejected``;
- no key, request path, id or contact email in any exception's text, repr or
  rendered traceback, in any log record, or on stdout/stderr;
- the contact email: CR/LF and other shapes refused;
- the key read ONCE per call and refused after the call ends;
- ``SSLKEYLOGFILE`` removed by ``apply_offline_env`` and refused by
  ``assert_offline_env``, and never opened by the client's TLS context;
- confinement: exactly one ``noqa: TID251`` in ``desktop/src`` (on this
  module's ``http.client`` import), and no other module imports ``http``,
  ``ssl``, ``socket``, ``urllib.request`` or ``PySide6.QtNetwork``.
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import ssl
import sys
import time
import traceback
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from scribe_desktop import cliniko_client as cc
from scribe_desktop.benchmark import (
    FORBIDDEN_TLS_OVERRIDES,
    OfflineEnvError,
    apply_offline_env,
    assert_offline_env,
)

_hc = cc.http.client  # the stdlib module, reached without a banned import here

SRC = Path(cc.__file__).resolve().parent
KEY = "MS0xMjM0NTY3ODkwLWZha2Uta2V5LWZvci10ZXN0cw-au2"
TOKEN = base64.b64encode(f"{KEY}:".encode()).decode()
EMAIL = "practitioner@example-clinic.com.au"
NOTE_ID = "918273645"
PATIENT_ID = "564738291"
SECRETS = (KEY, TOKEN, KEY.split("-")[0], EMAIL, NOTE_ID, PATIENT_ID, "treatment_notes/9")


class FakeTransport:
    """Records every request; answers from a queue (default: an empty object)."""

    def __init__(self, *responses: cc.RawResponse) -> None:
        self.calls: list[tuple[str, str, str, dict[str, str], int]] = []
        self._responses = list(responses)

    def request(
        self, method: str, host: str, path: str, headers: Mapping[str, str], max_body: int
    ) -> cc.RawResponse:
        self.calls.append((method, host, path, dict(headers), max_body))
        if self._responses:
            return self._responses.pop(0)
        return cc.RawResponse(200, None, b"{}")


def _ok(obj: object) -> cc.RawResponse:
    return cc.RawResponse(200, None, json.dumps(obj).encode())


def _client(transport: FakeTransport) -> cc.ClinikoClient:
    return cc.ClinikoClient(contact_email=EMAIL, transport=transport)


def _every_method(call: cc.ClinikoCall) -> None:
    call.get_user()
    call.get_practitioners_for_user("12345")
    call.get_public_settings()
    call.get_settings()
    call.get_treatment_note(NOTE_ID)
    call.get_patient(PATIENT_ID)
    call.get_booking("777")


def _assert_carries_nothing(error: BaseException) -> None:
    rendered = "".join(traceback.format_exception(error))
    for text in (str(error), repr(error), rendered):
        for secret in SECRETS:
            assert secret not in text, (type(error).__name__, secret)
    assert error.__cause__ is None
    assert error.__context__ is None


# --- the host pin -----------------------------------------------------------


class TestHostPin:
    @pytest.mark.parametrize("shard", sorted(cc.SHARDS))
    def test_every_documented_shard_maps_to_its_api_host(self, shard: str) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: f"abcdEFGH1234+/=-{shard}") as call:
            call.get_user()
        assert transport.calls[0][1] == f"api.{shard}.cliniko.com"
        assert transport.calls[0][2] == "/v1/user"

    def test_the_documented_shard_set_is_pinned(self) -> None:
        assert cc.SHARDS == {
            "au1", "au2", "au3", "au4", "au5", "ca1", "uk1", "uk2", "uk3", "us1", "eu1"
        }

    @pytest.mark.parametrize(
        "key",
        [
            "MS0xMjM0NTY3ODkwLWZha2U",  # no suffix: REFUSED, never defaulted to au1
            "MS0xMjM0NTY3ODkwLWZha2U-au9",  # unknown shard
            "MS0xMjM0NTY3ODkwLWZha2U-zz1",
            "MS0xMjM0NTY3ODkwLWZha2U-AU2",
            "MS0xMjM0NTY3ODkwLWZha2U-au2\r\nX-Evil: 1",
            "MS0xMjM0NTY3ODkwLWZha2U-au2\n",
            "MS0xMjM0 NTY3ODkw-au2",
            "short-au2",
            "",
        ],
    )
    def test_an_unusable_key_is_refused_before_any_request(self, key: str) -> None:
        transport = FakeTransport()
        with pytest.raises((cc.InvalidKey, cc.CredentialsRejected)) as info:
            with _client(transport).call(lambda: key):
                pytest.fail("the call must not open")
        assert transport.calls == []
        _assert_carries_nothing(info.value)

    def test_api_host_refuses_an_unknown_shard(self) -> None:
        assert cc.api_host("au2") == "api.au2.cliniko.com"
        with pytest.raises(cc.InvalidKey):
            cc.api_host("evil.example.com/au2")


# --- GET only ---------------------------------------------------------------


class TestGetOnly:
    def test_every_method_sends_get_with_the_pinned_headers(self) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            _every_method(call)
        assert {c[0] for c in transport.calls} == {"GET"}
        assert [c[2] for c in transport.calls] == [
            "/v1/user",
            "/v1/practitioners?q%5B%5D=user_id%3A%3D12345",
            "/v1/settings/public",
            "/v1/settings",
            f"/v1/treatment_notes/{NOTE_ID}",
            f"/v1/patients/{PATIENT_ID}",
            "/v1/bookings/777",
        ]
        for _method, host, _path, headers, max_body in transport.calls:
            assert host == "api.au2.cliniko.com"
            assert headers == {
                "Authorization": f"Basic {TOKEN}",
                "Accept": "application/json",
                "User-Agent": f"Clinic Scribe ({EMAIL})",
            }
            assert max_body == cc.MAX_BODY_BYTES

    def test_the_call_exposes_only_get_methods(self) -> None:
        public = {n for n in vars(cc.ClinikoCall) if not n.startswith("_")}
        assert public == {
            "host",
            "close",
            "get_user",
            "get_practitioners_for_user",
            "get_public_settings",
            "get_settings",
            "get_treatment_note",
            "get_patient",
            "get_booking",
        }

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "get", "HEAD"])
    def test_the_real_transport_refuses_every_other_method_before_connecting(
        self, method: str
    ) -> None:
        built: list[str] = []
        transport = cc.HTTPSTransport(
            connection_factory=lambda *a, **k: built.append("conn"),
            tls_context=lambda: built.append("tls"),
        )
        with pytest.raises(ValueError, match="GET only"):
            transport.request(method, "api.au2.cliniko.com", "/v1/user", {}, 10)
        assert built == []

    def test_the_module_source_names_no_other_http_method(self) -> None:
        source = (SRC / "cliniko_client.py").read_text(encoding="utf-8")
        for verb in ("POST", "PUT", "PATCH", "DELETE"):
            assert f'"{verb}"' not in source and f"'{verb}'" not in source


# --- status mapping and the body cap ----------------------------------------


class TestStatusMapping:
    def test_200_returns_the_json_object(self) -> None:
        transport = FakeTransport(_ok({"id": "1", "role": "practitioner"}))
        with _client(transport).call(lambda: KEY) as call:
            assert call.get_user() == {"id": "1", "role": "practitioner"}

    @pytest.mark.parametrize(
        ("status", "error"),
        [
            (401, cc.CredentialsRejected),
            (403, cc.CredentialsRejected),
            (404, cc.NotFound),
            (429, cc.RateLimited),
            (301, cc.RedirectRefused),
            (302, cc.RedirectRefused),
            (307, cc.RedirectRefused),
            (308, cc.RedirectRefused),
            (500, cc.Unreachable),
            (502, cc.Unreachable),
            (503, cc.Unreachable),
            (400, cc.UnexpectedStatus),
            (422, cc.UnexpectedStatus),
            (201, cc.UnexpectedStatus),
            (204, cc.UnexpectedStatus),
            (100, cc.UnexpectedStatus),
        ],
    )
    def test_each_status_is_a_named_error(self, status: int, error: type[Exception]) -> None:
        body = json.dumps({"message": f"patient {PATIENT_ID}", "note": NOTE_ID}).encode()
        transport = FakeTransport(cc.RawResponse(status, None, body))
        with pytest.raises(error) as info:
            with _client(transport).call(lambda: KEY) as call:
                call.get_treatment_note(NOTE_ID)
        _assert_carries_nothing(info.value)
        assert getattr(info.value, "status", status) == status

    def test_rate_limit_keeps_a_plain_reset_and_drops_anything_else(self) -> None:
        transport = FakeTransport(
            cc.RawResponse(429, "1790000000", b""),
            cc.RawResponse(429, "x" * 41, b""),
            cc.RawResponse(429, "12\r\nSet-Cookie: a", b""),
            cc.RawResponse(429, None, b""),
        )
        resets = []
        with _client(transport).call(lambda: KEY) as call:
            for _ in range(4):
                with pytest.raises(cc.RateLimited) as info:
                    call.get_user()
                resets.append(info.value.reset)
        assert resets == ["1790000000", None, None, None]

    # Explicit ids: a generated id is the whole body, and pytest puts the id in
    # the PYTEST_CURRENT_TEST environment variable, which Windows caps at
    # 32 767 characters (the deep array's id failed setup and teardown).
    @pytest.mark.parametrize(
        "body",
        [
            pytest.param(b"", id="empty"),
            pytest.param(b"[]", id="array"),
            pytest.param(b"null", id="null"),
            pytest.param(b'"text"', id="string"),
            pytest.param(b"{not json", id="not-json"),
            pytest.param(b"\xff\xfe{}", id="not-utf8"),
            pytest.param(b"[" * 100_000 + b"]" * 100_000, id="nested-past-recursion-limit"),
            pytest.param(b'{"n": ' + b"9" * 5000 + b"}", id="int-over-digit-limit"),
        ],
    )
    def test_a_body_that_is_not_a_json_object_is_malformed(self, body: bytes) -> None:
        # Codex round 8 PR-LOW-013: the digit-limit case is Malformed only
        # while the int-string limit is below 5000 digits, and the host can
        # move it (PYTHONINTMAXSTRDIGITS, -X int_max_str_digits) — so the test
        # pins the interpreter default and restores the host's value.
        previous = sys.get_int_max_str_digits()
        sys.set_int_max_str_digits(4300)
        try:
            assert sys.get_int_max_str_digits() == 4300
            transport = FakeTransport(cc.RawResponse(200, None, body))
            with pytest.raises(cc.Malformed) as info:
                with _client(transport).call(lambda: KEY) as call:
                    call.get_user()
        finally:
            sys.set_int_max_str_digits(previous)
        _assert_carries_nothing(info.value)

    def test_a_body_at_the_cap_parses_and_one_byte_over_is_refused(self) -> None:
        at_cap = b'{"a": 1}' + b" " * (cc.MAX_BODY_BYTES - 8)
        assert len(at_cap) == cc.MAX_BODY_BYTES
        over = at_cap + b" "
        transport = FakeTransport(
            cc.RawResponse(200, None, at_cap), cc.RawResponse(200, None, over)
        )
        with _client(transport).call(lambda: KEY) as call:
            assert call.get_user() == {"a": 1}
            with pytest.raises(cc.Malformed):
                call.get_user()


# --- the real transport over a fake connection -------------------------------


class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"{}",
        headers: Mapping[str, str] | None = None,
        chunk: int | None = None,
        read_error: BaseException | None = None,
    ) -> None:
        self._status = status
        self._body = body
        self._headers = dict(headers or {})
        self._chunk = chunk
        self._read_error = read_error
        self.read_sizes: list[int] = []

    @property
    def status(self) -> int:
        return self._status

    def getheader(self, name: str) -> str | None:
        return self._headers.get(name)

    def read1(self, amt: int) -> bytes:
        """One socket receive: up to ``amt`` bytes, at most ``chunk``."""
        self.read_sizes.append(amt)
        if self._read_error is not None:
            raise self._read_error
        take = amt if self._chunk is None else min(amt, self._chunk)
        out, self._body = self._body[:take], self._body[take:]
        return out

    def read(self, amt: int) -> bytes:
        # Codex round 8 PR-MED-010: `HTTPResponse.read(n)` loops receives
        # until it has n bytes, so a drip inside ONE call outran the deadline.
        # The transport must read with `read1` only; `pytest.fail` raises a
        # BaseException, which `_guarded` does not catch.
        pytest.fail("the transport called read(); it must use read1()")


class FakeConnection:
    def __init__(self, response: FakeResponse, fail: dict[str, BaseException]) -> None:
        self.response = response
        self.fail = fail
        self.log: list[tuple[Any, ...]] = []

    def set_debuglevel(self, level: int) -> None:
        self.log.append(("set_debuglevel", level))
        if "set_debuglevel" in self.fail:
            raise self.fail["set_debuglevel"]

    def set_tunnel(self, *args: Any, **kwargs: Any) -> None:  # must never be called
        self.log.append(("set_tunnel",))

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        self.log.append(("request", method, url, dict(headers)))
        if "request" in self.fail:
            raise self.fail["request"]

    def getresponse(self) -> FakeResponse:
        self.log.append(("getresponse",))
        if "getresponse" in self.fail:
            raise self.fail["getresponse"]
        return self.response

    def close(self) -> None:
        self.log.append(("close",))
        if "close" in self.fail:
            raise self.fail["close"]


def _transport(
    response: FakeResponse | None = None,
    clock: Callable[[], float] = time.monotonic,
    **fail: BaseException,
) -> tuple[cc.HTTPSTransport, FakeConnection, list[tuple[Any, ...]]]:
    conn = FakeConnection(response or FakeResponse(), fail)
    built: list[tuple[Any, ...]] = []
    context = object()

    def factory(host: str, **kwargs: Any) -> FakeConnection:
        built.append((host, kwargs))
        if "factory" in fail:
            raise fail["factory"]
        return conn

    transport = cc.HTTPSTransport(
        connection_factory=factory,
        tls_context=lambda: context,
        timeout=7.5,
        clock=clock,
    )
    built.append(("context", context))
    return transport, conn, built


class TestHTTPSTransport:
    def test_one_pinned_connection_per_request_debug_zero_no_tunnel(self) -> None:
        response = FakeResponse(body=b'{"ok": true}', headers={"X-RateLimit-Reset": "60"})
        transport, conn, built = _transport(response)
        raw = transport.request("GET", "api.au2.cliniko.com", "/v1/user", {"A": "b"}, 100)
        context = built[0][1]
        assert built[1] == (
            "api.au2.cliniko.com",
            {"port": 443, "timeout": 7.5, "context": context},
        )
        assert conn.log == [
            ("set_debuglevel", 0),
            ("request", "GET", "/v1/user", {"A": "b"}),
            ("getresponse",),
            ("close",),
        ]
        assert raw == cc.RawResponse(200, "60", b'{"ok": true}')

    def test_the_default_factory_is_https_connection(self) -> None:
        transport = cc.HTTPSTransport()
        assert transport._factory is _hc.HTTPSConnection

    def test_the_read_is_bounded_at_the_call_that_allocates(self) -> None:
        response = FakeResponse(body=b"x" * 50, chunk=3)
        transport, _conn, _built = _transport(response)
        raw = transport.request("GET", "h", "/p", {}, 10)
        assert raw.body == b"x" * 11  # max_body + 1: enough to prove "over"
        assert response.read_sizes == [11, 8, 5, 2]  # never more than is left
        assert sum(min(n, 3) for n in response.read_sizes) == 11

    def test_an_unbounded_body_is_refused_by_the_client(self) -> None:
        response = FakeResponse(body=b"{" + b" " * (cc.MAX_BODY_BYTES + 5000) + b"}")
        transport, _conn, _built = _transport(response)
        client = cc.ClinikoClient(contact_email=EMAIL, transport=transport)
        with pytest.raises(cc.Malformed):
            with client.call(lambda: KEY) as call:
                call.get_user()
        assert response.read_sizes == [cc.MAX_BODY_BYTES + 1]

    @pytest.mark.parametrize(
        ("stage", "exc", "expected"),
        [
            ("factory", OSError("api.au2.cliniko.com"), cc.Unreachable),
            ("set_debuglevel", ValueError("x"), cc.Malformed),
            (
                "request",
                ssl.SSLCertVerificationError(1, f"certificate verify failed {NOTE_ID}"),
                cc.CertificateRejected,
            ),
            ("request", ssl.SSLError(1, "wrong version number"), cc.Unreachable),
            ("request", ssl.SSLEOFError(8, "EOF"), cc.Unreachable),
            ("request", TimeoutError("timed out"), cc.Unreachable),
            ("request", ConnectionRefusedError(10061, "refused"), cc.Unreachable),
            ("request", OSError(11001, "getaddrinfo failed"), cc.Unreachable),
            ("request", ValueError(f"Invalid header value {KEY}"), cc.Malformed),
            ("request", UnicodeEncodeError("latin-1", KEY, 0, 1, "x"), cc.Malformed),
            ("request", _hc.CannotSendRequest(), cc.Malformed),
            ("getresponse", _hc.RemoteDisconnected("closed"), cc.Unreachable),
            ("getresponse", _hc.BadStatusLine(f"HTTP/1.1 {PATIENT_ID}"), cc.Malformed),
            ("getresponse", _hc.LineTooLong("header line"), cc.Malformed),
            ("getresponse", _hc.HTTPException("too many headers"), cc.Malformed),
            ("getresponse", TimeoutError(), cc.Unreachable),
            ("read", _hc.IncompleteRead(f"patient {PATIENT_ID}".encode()), cc.Unreachable),
            ("read", ssl.SSLZeroReturnError(6, "closed"), cc.Unreachable),
            ("read", ConnectionResetError(), cc.Unreachable),
            ("read", ValueError("I/O operation on closed file"), cc.Malformed),
            ("read", RuntimeError(f"unexpected {NOTE_ID}"), cc.Malformed),
        ],
    )
    def test_each_library_failure_stage_is_a_named_error(
        self, stage: str, exc: BaseException, expected: type[cc.ClinikoError]
    ) -> None:
        if stage == "read":
            transport, conn, _built = _transport(FakeResponse(read_error=exc))
        else:
            transport, conn, _built = _transport(**{stage: exc})
        client = cc.ClinikoClient(contact_email=EMAIL, transport=transport)
        with pytest.raises(cc.ClinikoError) as info:
            with client.call(lambda: KEY) as call:
                call.get_treatment_note(NOTE_ID)
        assert type(info.value) is expected
        _assert_carries_nothing(info.value)
        if stage != "factory":
            assert conn.log[-1] == ("close",)  # closed on every failure after construction
        assert ("set_tunnel",) not in conn.log

    def test_a_slow_drip_body_is_abandoned_at_the_deadline(self) -> None:
        """Round 7 LOW-001, made real by codex round 8 PR-MED-010: each body
        read is ONE receive (``read1``; ``FakeResponse.read`` fails the test),
        so a body dripping one byte per receive meets the deadline check
        between receives instead of hiding inside one multi-receive call."""
        now = [0.0]
        response = FakeResponse(body=b"x" * 100, chunk=1)
        receive = response.read1

        def slow_receive(amt: int) -> bytes:
            now[0] += 4.0
            return receive(amt)

        response.read1 = slow_receive  # type: ignore[method-assign]
        transport, conn, _built = _transport(response, clock=lambda: now[0])
        assert cc.DEADLINE_SECONDS == 30.0
        with pytest.raises(cc.Unreachable) as info:
            transport.request("GET", "h", "/p", {}, 1000)
        assert len(response.read_sizes) == 8  # receives start at t=0..28; t=32 is past 30
        assert conn.log[-1] == ("close",)
        _assert_carries_nothing(info.value)

    def test_a_slow_request_is_abandoned_before_the_answer_is_read(self) -> None:
        now = [0.0]
        transport, conn, _built = _transport(clock=lambda: now[0])
        send = conn.request

        def slow_request(method: str, url: str, *, headers: Mapping[str, str]) -> None:
            now[0] += 31.0
            send(method, url, headers=headers)

        conn.request = slow_request  # type: ignore[method-assign]
        with pytest.raises(cc.Unreachable):
            transport.request("GET", "h", "/p", {}, 10)
        assert ("getresponse",) not in conn.log
        assert conn.log[-1] == ("close",)

    @pytest.mark.parametrize(
        ("status", "error"),
        [
            (401, cc.CredentialsRejected),
            (403, cc.CredentialsRejected),
            (404, cc.NotFound),
            (429, cc.RateLimited),
            (302, cc.RedirectRefused),
            (422, cc.UnexpectedStatus),
            (503, cc.Unreachable),
        ],
    )
    def test_a_refusal_whose_body_stalls_keeps_its_own_name(
        self, status: int, error: type[cc.ClinikoError]
    ) -> None:
        """Codex round 8 PR-MED-012: the body used to be read for every
        status, so a 401/403 (or a 429) whose body stalled or was cut became
        ``Unreachable`` — under D4 a named refusal turned into "offline".
        Only a 200's body is read now; the reader here would fail if touched."""
        response = FakeResponse(
            status=status,
            headers={"X-RateLimit-Reset": "60"},
            read_error=_hc.IncompleteRead(b"partial"),
        )
        transport, conn, _built = _transport(response)
        client = cc.ClinikoClient(contact_email=EMAIL, transport=transport)
        with pytest.raises(cc.ClinikoError) as info:
            with client.call(lambda: KEY) as call:
                call.get_treatment_note(NOTE_ID)
        assert type(info.value) is error
        assert getattr(info.value, "status", status) in (status, None)
        if status == 429:
            assert isinstance(info.value, cc.RateLimited) and info.value.reset == "60"
        assert response.read_sizes == []  # the body was never read
        assert conn.log[-1] == ("close",)

    def test_a_non_200_answer_carries_no_body(self) -> None:
        transport, _conn, _built = _transport(FakeResponse(status=404, body=b"{}"))
        raw = transport.request("GET", "h", "/p", {}, 10)
        assert raw.status == 404 and raw.body == b""

    def test_the_raw_response_repr_carries_no_body(self) -> None:
        """Round 7 LOW-002: the body is patient data; a stray repr of a
        ``RawResponse`` (a log line, a traceback's locals) must not carry it."""
        raw = cc.RawResponse(200, None, f'{{"first_name": "{PATIENT_ID}"}}'.encode())
        assert PATIENT_ID not in repr(raw) and "first_name" not in repr(raw)
        assert raw == cc.RawResponse(200, None, raw.body)  # still compared

    def test_a_close_failure_changes_no_outcome(self) -> None:
        transport, _conn, _built = _transport(close=OSError("reset"))
        raw = transport.request("GET", "h", "/p", {}, 10)
        assert raw.status == 200

    def test_a_tls_context_failure_is_named(self) -> None:
        def broken() -> ssl.SSLContext:
            raise ssl.SSLError(1, "no certificate store")

        transport = cc.HTTPSTransport(connection_factory=lambda *a, **k: None, tls_context=broken)
        with pytest.raises(cc.Unreachable) as info:
            transport.request("GET", "h", "/p", {}, 10)
        _assert_carries_nothing(info.value)


# --- TLS ---------------------------------------------------------------------


class TestTlsContext:
    def test_tls_12_minimum_verified_and_no_key_log(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        keylog = tmp_path / "keys.log"
        monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
        context = cc.build_tls_context()
        assert context.minimum_version == ssl.TLSVersion.TLSv1_2
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        assert context.keylog_filename is None
        assert not keylog.exists()  # the variable is never read by this context

    def test_the_module_never_uses_create_default_context(self) -> None:
        source = (SRC / "cliniko_client.py").read_text(encoding="utf-8")
        code = source.split('"""', 2)[2]  # past the module docstring, which names it
        assert "create_default_context(" not in code
        assert "set_tunnel(" not in code
        assert "set_debuglevel(0)" in code


class TestSslKeyLogFile:
    def test_it_is_refused_by_name_and_removed_at_startup(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        assert "SSLKEYLOGFILE" in FORBIDDEN_TLS_OVERRIDES
        target = tmp_path / "never-touched.log"
        apply_offline_env()
        monkeypatch.setenv("SSLKEYLOGFILE", str(target))
        with pytest.raises(OfflineEnvError, match="SSLKEYLOGFILE") as info:
            assert_offline_env()
        assert str(target) not in str(info.value)
        apply_offline_env()
        assert "SSLKEYLOGFILE" not in os.environ
        assert_offline_env()
        assert not target.exists()


# --- nothing leaks ------------------------------------------------------------


class TestNothingLeaks:
    def test_no_log_record_or_output_carries_a_secret(
        self, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        caplog.set_level(logging.DEBUG)
        scenarios: list[Callable[[], cc.HTTPSTransport]] = [
            lambda: _transport(request=ssl.SSLCertVerificationError(1, KEY))[0],
            lambda: _transport(getresponse=_hc.BadStatusLine(PATIENT_ID))[0],
            lambda: _transport(FakeResponse(read_error=_hc.IncompleteRead(b"x")))[0],
            lambda: _transport(FakeResponse(status=404))[0],
            lambda: _transport(FakeResponse(status=302))[0],
            lambda: _transport(FakeResponse(status=200, body=b"[" + KEY.encode()))[0],
        ]
        for build in scenarios:
            client = cc.ClinikoClient(contact_email=EMAIL, transport=build())
            with pytest.raises(cc.ClinikoError):
                with client.call(lambda: KEY) as call:
                    call.get_treatment_note(NOTE_ID)
        logged = caplog.text + "".join(str(r.__dict__) for r in caplog.records)
        out = capsys.readouterr()
        for secret in SECRETS:
            assert secret not in logged
            assert secret not in out.out and secret not in out.err

    def test_value_errors_carry_nothing(self) -> None:
        for error in (cc.InvalidContactEmail(), cc.InvalidId(), cc.InvalidKey()):
            _assert_carries_nothing(error)


# --- the contact email ----------------------------------------------------------


class TestContactEmail:
    @pytest.mark.parametrize(
        "email",
        [
            "a@b.co",
            "first.last+scribe@clinic.example.com.au",
            "x_y%z@sub-domain.example.org",
        ],
    )
    def test_plain_addresses_are_accepted(self, email: str) -> None:
        assert cc.validate_contact_email(email) == email
        transport = FakeTransport()
        with cc.ClinikoClient(contact_email=email, transport=transport).call(lambda: KEY) as c:
            c.get_user()
        assert transport.calls[0][3]["User-Agent"] == f"Clinic Scribe ({email})"

    @pytest.mark.parametrize(
        "email",
        [
            "a@b.co\r\nX-Injected: 1",
            "a@b.co\n",
            "a@b.co\r",
            "a b@c.co",
            "a@b.co) (evil",
            "no-at-sign.example.com",
            "a@nodot",
            "@b.co",
            "a@b.co;c@d.co",
            "a" * 65 + "@b.co",
            "a@" + "b" * 250 + ".co",
            "",
        ],
    )
    def test_injection_and_bad_shapes_are_refused(self, email: str) -> None:
        with pytest.raises(cc.InvalidContactEmail) as info:
            cc.ClinikoClient(contact_email=email, transport=FakeTransport())
        if email:
            assert email not in str(info.value)


# --- the key read once ----------------------------------------------------------


class TestKeyReadOnce:
    def test_one_read_serves_every_request_in_the_call(self) -> None:
        reads: list[int] = []

        def read_key() -> str:
            reads.append(1)
            return KEY

        transport = FakeTransport()
        with _client(transport).call(read_key) as call:
            _every_method(call)
        assert reads == [1]
        assert len(transport.calls) == 7

    def test_a_call_refuses_use_after_it_ends(self) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            call.get_user()
        with pytest.raises(RuntimeError, match="ended"):
            call.get_user()
        assert len(transport.calls) == 1

    def test_the_call_ends_even_when_its_body_raises(self) -> None:
        transport = FakeTransport(cc.RawResponse(404, None, b""))
        with pytest.raises(cc.NotFound):
            with _client(transport).call(lambda: KEY) as call:
                call.get_patient(PATIENT_ID)
        with pytest.raises(RuntimeError):
            call.get_user()

    @pytest.mark.parametrize("missing", [None, ""])
    def test_a_missing_key_is_rejected_without_a_request(self, missing: str | None) -> None:
        transport = FakeTransport()
        with pytest.raises(cc.CredentialsRejected):
            with _client(transport).call(lambda: missing):
                pytest.fail("the call must not open")
        assert transport.calls == []

    def test_the_client_holds_no_key(self) -> None:
        transport = FakeTransport()
        client = _client(transport)
        with client.call(lambda: KEY) as call:
            call.get_user()
        state = repr(vars(client)) + repr(vars(call))
        assert KEY not in state and TOKEN not in state


# --- ids --------------------------------------------------------------------------


class TestIds:
    @pytest.mark.parametrize(
        "bad", ["0", "0123", "12a", "", "1" * 20, "1\n", "-1", "1/../user", " 1", "１２"]
    )
    def test_a_bad_id_is_refused_before_any_request(self, bad: str) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            for method in (
                call.get_treatment_note,
                call.get_patient,
                call.get_booking,
                call.get_practitioners_for_user,
            ):
                with pytest.raises(cc.InvalidId):
                    method(bad)
        assert transport.calls == []

    def test_the_largest_id_is_accepted(self) -> None:
        assert cc.check_id("9" * 19) == "9" * 19


# --- confinement --------------------------------------------------------------------


_NETWORK_MODULES = ("http", "ssl", "socket", "urllib.request", "PySide6.QtNetwork")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # A relative import keeps its leading dots, so the closure test
            # can refuse one instead of silently not following it.
            base = "." * node.level + (node.module or "")
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)
    return names


def _is_network(name: str) -> bool:
    return any(name == m or name.startswith(m + ".") for m in _NETWORK_MODULES)


class TestConfinement:
    def test_exactly_one_tid251_noqa_on_the_http_client_import(self) -> None:
        hits = [
            (path.name, line.strip())
            for path in sorted(SRC.rglob("*.py"))
            for line in path.read_text(encoding="utf-8").splitlines()
            if "noqa: TID251" in line
        ]
        assert len(hits) == 1, hits
        name, line = hits[0]
        assert name == "cliniko_client.py"
        assert line.startswith("import http.client  # noqa: TID251")

    def test_only_the_client_imports_a_network_module(self) -> None:
        offenders = {
            path.relative_to(SRC).as_posix(): sorted(n for n in _imports(path) if _is_network(n))
            for path in sorted(SRC.rglob("*.py"))
        }
        offenders = {k: v for k, v in offenders.items() if v}
        assert offenders == {"cliniko_client.py": ["http.client", "ssl"]}

    def test_the_native_host_never_reaches_the_client(self) -> None:
        """The host's import closure over ``scribe_desktop`` (every import,
        function-level ones included) never includes the client."""
        seen: set[str] = set()
        pending = ["native_host"]
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            path = SRC.joinpath(*name.split(".")).with_suffix(".py")
            if not path.exists():
                path = SRC.joinpath(*name.split("."), "__init__.py")
            for imported in _imports(path):
                assert not imported.startswith("."), (name, imported)  # not followed: refuse
                if imported.startswith("scribe_desktop."):
                    local = imported.removeprefix("scribe_desktop.")
                    if (SRC / f"{local.replace('.', '/')}.py").exists() or (
                        SRC / local.replace(".", "/") / "__init__.py"
                    ).exists():
                        pending.append(local)
        assert "native_host" in seen and "protocol" in seen
        assert "cliniko_client" not in seen

    def test_only_the_clinic_registry_and_note_verification_import_the_client(
        self,
    ) -> None:
        """Task 1.1 built the client with no caller; Task 2.1b's clinic
        registry is the first, for the Clinics tab's Validate / Replace key,
        and Task 3.2's note verification (``encounter.verify_note_context``)
        the second (the data-flow map's flow 18 and the threat model's
        "Cliniko API client" say so). A new caller must update this pin
        together with those docs."""
        importers = sorted(
            path.relative_to(SRC).as_posix()
            for path in SRC.rglob("*.py")
            if path.name != "cliniko_client.py"
            and any("cliniko_client" in name for name in _imports(path))
        )
        assert importers == ["clinics.py", "encounter.py"]
