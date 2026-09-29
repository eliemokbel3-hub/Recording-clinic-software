"""Cliniko workflow safeguards plan, Task 1.1: the Cliniko client; the one
draft write added by the cliniko-draft-write plan, Task 1.1 (D1, D5, D11).

No test here opens a socket or contacts Cliniko. The client is driven through
an injected ``Transport`` fake, and ``HTTPSTransport`` through an injected
connection factory whose fake connection records every call; the only real
stdlib object built is the TLS context (``build_tls_context``), which reads
the Windows certificate store and touches no network.

Covered (safeguards plan Validation, "Client", and draft-write Validation,
"Client"):
- the host pin: every documented shard maps to ``api.<shard>.cliniko.com``; an
  unknown or missing suffix, or a header-breaking key, is ``InvalidKey`` with
  no request made;
- two request shapes: every read sends ``GET`` with no body; the one write
  sends ``PATCH`` with a ``DraftContent`` body to ``/v1/treatment_notes/<id>``;
  the real transport refuses every other shape (another method, a lower-case
  spelling, a GET with a body, a PATCH without one or to another path) before
  a connection exists; the module's string constants name ``PATCH`` once and
  no other write method; ``DraftContent`` has one field and its body one key;
- the write's classes decided on the status line (a 200 is written whatever
  its body does), and a 422 reduced to fixed categories with no chained
  context and no trace of its keys or values anywhere;
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
  ``ssl``, ``socket``, ``urllib.request`` or ``PySide6.QtNetwork``;
- the client's surface confined (draft-write Task 5.3): outside it, a module
  reaches only the client names and ``ClinikoCall`` capabilities pinned for
  it, never a client class's private member (``TestWriteCallSites``).
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import ssl
import symtable
import sys
import textwrap
import time
import traceback
from collections.abc import Callable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

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
        self.bodies: list[bytes | None] = []
        self._responses = list(responses)

    def request(
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> cc.RawResponse:
        self.calls.append((method, host, path, dict(headers), max_body))
        self.bodies.append(body)
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
    call.get_treatment_note_template("4321")


# A Cliniko ``content`` object: one rich-text question, one checkbox question
# whose ``answers`` array must round-trip, a question type this module does
# not know, and an unknown key of the object itself.
CONTENT: dict[str, Any] = {
    "sections": [
        {
            "name": "Subjective",
            "questions": [
                {"name": "Presenting complaint", "type": "paragraph", "answer": "<p>a &lt; b</p>"},
                {
                    "name": "Consent",
                    "type": "checkboxes",
                    "answers": [{"value": "Informed consent given", "selected": True}],
                },
                {"name": "Chart", "type": "bodycharts", "future_field": [1, 2]},
            ],
        }
    ],
    "future_key": {"kept": True},
}


def _one_answer(answer: str) -> dict[str, Any]:
    question = {"name": "Q", "type": "text", "answer": answer}
    return {"sections": [{"name": "S", "questions": [question]}]}


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


# --- the two request shapes ----------------------------------------------------

WRITE_PATH = f"/v1/treatment_notes/{NOTE_ID}"
VALID_BODY = b'{"content": {"sections": []}}'
API_HOST = "api.au2.cliniko.com"
WRITE_HEADERS = {"Content-Type": "application/json"}
_HTTP_WORDS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
)


def _string_constants(source: str) -> list[str]:
    """Every string constant in the module (docstrings included), as the
    parser sees it — whatever quote style or concatenation spelled it."""
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


class TestMethods:
    def test_every_read_sends_get_with_no_body_and_the_pinned_headers(self) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            _every_method(call)
        assert {c[0] for c in transport.calls} == {"GET"}
        assert transport.bodies == [None] * len(transport.calls)
        assert [c[2] for c in transport.calls] == [
            "/v1/user",
            "/v1/practitioners?q%5B%5D=user_id%3A%3D12345",
            "/v1/settings/public",
            "/v1/settings",
            f"/v1/treatment_notes/{NOTE_ID}",
            f"/v1/patients/{PATIENT_ID}",
            "/v1/bookings/777",
            "/v1/treatment_note_templates/4321",
        ]
        for _method, host, _path, headers, max_body in transport.calls:
            assert host == "api.au2.cliniko.com"
            assert headers == {
                "Authorization": f"Basic {TOKEN}",
                "Accept": "application/json",
                "User-Agent": f"Clinic Scribe ({EMAIL})",
            }
            assert max_body == cc.MAX_BODY_BYTES

    def test_the_write_sends_one_patch_with_the_content_body(self) -> None:
        transport = FakeTransport(_ok({"id": NOTE_ID}))
        with _client(transport).call(lambda: KEY) as call:
            answer = call.write_draft_note(NOTE_ID, cc.DraftContent(content=CONTENT))
        assert answer == cc.WriteAnswer(written=True, note={"id": NOTE_ID})
        assert len(transport.calls) == 1
        method, host, path, headers, max_body = transport.calls[0]
        assert (method, host, path, max_body) == (
            "PATCH",
            "api.au2.cliniko.com",
            WRITE_PATH,
            cc.MAX_BODY_BYTES,
        )
        assert headers == {
            "Authorization": f"Basic {TOKEN}",
            "Accept": "application/json",
            "User-Agent": f"Clinic Scribe ({EMAIL})",
            "Content-Type": "application/json",
        }
        body = transport.bodies[0]
        assert body is not None
        assert json.loads(body.decode("utf-8")) == {"content": CONTENT}

    def test_the_call_exposes_the_reads_and_the_one_write(self) -> None:
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
            "get_treatment_note_template",
            "write_draft_note",
        }

    @pytest.mark.parametrize(
        ("method", "path", "body"),
        [
            pytest.param("POST", WRITE_PATH, VALID_BODY, id="post"),
            pytest.param("PUT", WRITE_PATH, VALID_BODY, id="put"),
            pytest.param("DELETE", WRITE_PATH, None, id="delete"),
            pytest.param("HEAD", "/v1/user", None, id="head"),
            pytest.param("get", "/v1/user", None, id="lower-case-get"),
            pytest.param("patch", WRITE_PATH, VALID_BODY, id="lower-case-patch"),
            pytest.param("GET", "/v1/user", VALID_BODY, id="get-with-body"),
            pytest.param("GET", "/v1/user", b"", id="get-with-empty-body"),
            pytest.param("PATCH", WRITE_PATH, None, id="patch-without-body"),
            pytest.param("PATCH", WRITE_PATH, b"", id="patch-with-empty-body"),
            pytest.param("PATCH", "/v1/patients/1", VALID_BODY, id="patch-patient"),
            pytest.param("PATCH", "/v1/treatment_notes", VALID_BODY, id="patch-collection"),
            pytest.param("PATCH", "/v1/treatment_notes/0", VALID_BODY, id="patch-zero-id"),
            pytest.param("PATCH", "/v1/treatment_notes/1/x", VALID_BODY, id="patch-sub-path"),
            pytest.param("PATCH", f"{WRITE_PATH}?draft=false", VALID_BODY, id="patch-query"),
            pytest.param("PATCH", f"{WRITE_PATH}\n", VALID_BODY, id="patch-trailing-newline"),
            pytest.param(
                "PATCH", "/v1/treatment_notes/1" + "0" * 19, VALID_BODY, id="patch-long"
            ),
            pytest.param("PATCH", "/treatment_notes/1", VALID_BODY, id="patch-no-version"),
            pytest.param(
                "PATCH", "/v1/treatment_notes/１２", VALID_BODY, id="patch-non-ascii-digits"
            ),
            pytest.param("PATCH", WRITE_PATH, bytearray(VALID_BODY), id="patch-bytearray"),
            # MED-001 (round 9): the body's SHAPE, as Cliniko will parse it.
            pytest.param("PATCH", WRITE_PATH, b'{"draft": false}', id="body-draft-only"),
            pytest.param(
                "PATCH", WRITE_PATH, b'{"content": {}, "draft": false}', id="body-plus-draft"
            ),
            pytest.param(
                "PATCH", WRITE_PATH, b'{"content": {}, "title": "x"}', id="body-plus-title"
            ),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                b'{"content": {}, "\\u0064raft": false}',
                id="body-escaped-draft-key",
            ),
            pytest.param("PATCH", WRITE_PATH, b'{"content": []}', id="body-content-list"),
            pytest.param("PATCH", WRITE_PATH, b'{"content": null}', id="body-content-null"),
            pytest.param("PATCH", WRITE_PATH, b"[]", id="body-array"),
            pytest.param("PATCH", WRITE_PATH, b"{}", id="body-empty-object"),
            pytest.param("PATCH", WRITE_PATH, b"not json", id="body-not-json"),
            pytest.param("PATCH", WRITE_PATH, b"\xff\xfe{}", id="body-not-utf8"),
        ],
    )
    def test_the_real_transport_refuses_every_other_shape_before_connecting(
        self, method: str, path: str, body: Any
    ) -> None:
        built: list[str] = []
        transport = cc.HTTPSTransport(
            connection_factory=lambda *a, **k: built.append("conn"),
            tls_context=lambda: built.append("tls"),
        )
        # Each shape carries the headers its method WOULD be admitted with,
        # so only the shape itself is refused.
        headers = WRITE_HEADERS if method.upper() != "GET" else {}
        with pytest.raises(ValueError, match="draft PATCH to one treatment note"):
            transport.request(method, API_HOST, path, headers, 10, body=body)
        assert built == []

    @pytest.mark.parametrize(
        "host", ["h", "evil.example.com", "api.au9.cliniko.com", "northside.au2.cliniko.com"]
    )
    @pytest.mark.parametrize(
        ("method", "path", "body", "headers"),
        [("PATCH", WRITE_PATH, VALID_BODY, WRITE_HEADERS), ("GET", "/v1/user", None, {})],
        ids=["write", "read"],
    )
    def test_every_request_is_admitted_only_to_a_documented_api_host(
        self, host: str, method: str, path: str, body: bytes | None, headers: dict[str, str]
    ) -> None:
        """LOW-004 (round 9) and round 10 LOW-001: the transport pins the
        host itself, for the read as well as the write."""
        built: list[str] = []
        transport = cc.HTTPSTransport(
            connection_factory=lambda *a, **k: built.append("conn"),
            tls_context=lambda: built.append("tls"),
        )
        with pytest.raises(ValueError, match="draft PATCH to one treatment note"):
            transport.request(method, host, path, headers, 10, body=body)
        assert built == []

    @pytest.mark.parametrize(
        ("method", "path", "body", "headers"),
        [
            pytest.param("GET", "/user", None, {}, id="get-outside-v1"),
            pytest.param("GET", "/v1/user", None, {"X-Other": "1"}, id="get-extra-header"),
            pytest.param("GET", "/v1/user", None, WRITE_HEADERS, id="get-content-type"),
            pytest.param("PATCH", WRITE_PATH, VALID_BODY, {}, id="patch-no-content-type"),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                VALID_BODY,
                {"Content-Type": "application/x-www-form-urlencoded"},
                id="patch-form-content-type",
            ),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                VALID_BODY,
                {"Content-Type": "application/json; charset=x"},
                id="patch-content-type-with-parameter",
            ),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                VALID_BODY,
                {**WRITE_HEADERS, "Content-Length": "2"},
                id="patch-content-length",
            ),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                VALID_BODY,
                {**WRITE_HEADERS, "Transfer-Encoding": "chunked"},
                id="patch-transfer-encoding",
            ),
            pytest.param(
                "PATCH",
                WRITE_PATH,
                VALID_BODY,
                {**WRITE_HEADERS, "content-type": "text/plain"},
                id="patch-content-type-twice",
            ),
        ],
    )
    def test_only_the_clients_own_headers_are_admitted(
        self, method: str, path: str, body: bytes | None, headers: dict[str, str]
    ) -> None:
        """Round 10 MED-001: the SAME body bytes can parse as something else
        under a caller-chosen Content-Type or framing header, so the
        transport admits only ``_send``'s header names."""
        built: list[str] = []
        transport = cc.HTTPSTransport(
            connection_factory=lambda *a, **k: built.append("conn"),
            tls_context=lambda: built.append("tls"),
        )
        with pytest.raises(ValueError, match="draft PATCH to one treatment note"):
            transport.request(method, API_HOST, path, headers, 10, body=body)
        assert built == []

    def test_only_plain_objects_are_admitted_and_only_the_snapshot_is_sent(self) -> None:
        """Round 11 LOW-002: what ``_admit`` checks is what is sent — a
        ``Mapping`` that answers differently on a second pass, a ``bytes``
        subclass ``http.client`` would stream as a file, and ``str``
        subclasses are refused before connecting."""

        class Shifting(Mapping[str, str]):
            """Shows the admitted header for one ``items()`` pass (one
            iteration, one lookup), a form Content-Type on every pass after."""

            def __init__(self) -> None:
                self.passes = 0

            def _current(self) -> dict[str, str]:
                self.passes += 1
                if self.passes <= 2:
                    return dict(WRITE_HEADERS)
                return {"Content-Type": "application/x-www-form-urlencoded"}

            def __getitem__(self, key: str) -> str:
                return self._current()[key]

            def __iter__(self) -> Any:
                return iter(self._current())

            def __len__(self) -> int:
                return 1

        class Streamed(bytes):
            def read(self, amt: int = -1) -> bytes:
                return b'{"draft": false}'

        class Method(str):
            pass

        built: list[str] = []
        transport = cc.HTTPSTransport(
            connection_factory=lambda *a, **k: built.append("conn"),
            tls_context=lambda: built.append("tls"),
        )
        for method, headers, body in (
            ("PATCH", WRITE_HEADERS, Streamed(VALID_BODY)),
            (Method("PATCH"), WRITE_HEADERS, VALID_BODY),
            ("PATCH", {Method("Content-Type"): "application/json"}, VALID_BODY),
        ):
            with pytest.raises(ValueError, match="draft PATCH to one treatment note"):
                transport.request(method, API_HOST, WRITE_PATH, headers, 10, body=body)
        assert built == []
        # A shifting mapping is read ONCE: the admitted snapshot is sent
        # (the fake connection's own ``dict(headers)`` would read the form
        # Content-Type from the mapping itself).
        shifting = Shifting()
        ok_transport, conn, _built = _transport()
        ok_transport.request("PATCH", API_HOST, WRITE_PATH, shifting, 10, body=VALID_BODY)
        assert shifting.passes == 2
        assert conn.log[1] == ("request", "PATCH", WRITE_PATH, WRITE_HEADERS)

    def test_the_clients_own_headers_are_admitted_in_any_case(self) -> None:
        transport, conn, _built = _transport()
        headers = {
            "authorization": "Basic x",
            "ACCEPT": "application/json",
            "User-Agent": "u",
            "content-TYPE": "application/json",
        }
        transport.request("PATCH", API_HOST, WRITE_PATH, headers, 10, body=VALID_BODY)
        assert conn.log[1] == ("request", "PATCH", WRITE_PATH, headers)

    def test_a_body_with_an_extra_field_is_refused_whoever_built_it(self) -> None:
        """MED-001 (round 9): a ``DraftContent`` subclass that adds ``draft``
        passes ``write_draft_note``'s type, and the transport still refuses
        its body before a connection exists."""

        class Sneaky(cc.DraftContent):
            draft: bool = False

        transport, conn, _built = _transport()
        client = cc.ClinikoClient(contact_email=EMAIL, transport=transport)
        with client.call(lambda: KEY) as call:
            with pytest.raises(ValueError, match="draft PATCH to one treatment note"):
                call.write_draft_note(NOTE_ID, Sneaky(content=CONTENT))
        assert conn.log == []

    @pytest.mark.parametrize(
        ("method", "path", "body", "headers"),
        [("GET", "/v1/user", None, {}), ("PATCH", WRITE_PATH, VALID_BODY, WRITE_HEADERS)],
    )
    def test_the_two_admitted_shapes_connect(
        self, method: str, path: str, body: bytes | None, headers: dict[str, str]
    ) -> None:
        transport, conn, _built = _transport()
        transport.request(method, API_HOST, path, headers, 10, body=body)
        assert conn.log[1] == ("request", method, path, headers)
        assert conn.bodies == [body]

    def test_the_module_names_patch_once_and_no_other_write_method(self) -> None:
        """The source-count pin (D1): of every string constant the parser
        sees in the module, whatever its case, quoting or concatenation,
        exactly one IS an HTTP method other than GET, and it is ``PATCH``,
        bound to ``_WRITE_METHOD`` — the one name the allow-list and
        ``write_draft_note`` share. (Prose that mentions a method is a longer
        constant and is not counted.) Residue: a method string assembled at
        run time is outside what a source check can see; the transport's
        allow-list still admits only the two shapes whatever a caller built."""
        source = (SRC / "cliniko_client.py").read_text(encoding="utf-8")
        methods = [
            value
            for value in _string_constants(source)
            if value.strip().upper() in _HTTP_WORDS - {"GET"}
        ]
        assert methods == ["PATCH"]
        binders = [
            node.target.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.value, ast.Constant)
            and node.value.value == "PATCH"
            and isinstance(node.target, ast.Name)
        ]
        assert binders == ["_WRITE_METHOD"]


class TestDraftContent:
    def test_the_model_has_exactly_one_field(self) -> None:
        assert set(cc.DraftContent.model_fields) == {"content"}

    def test_the_serialised_body_has_exactly_one_top_level_key(self) -> None:
        body = json.loads(cc.DraftContent(content=CONTENT).to_body())
        assert list(body) == ["content"]
        assert body["content"] == CONTENT  # unknown types and answers arrays round-trip

    @pytest.mark.parametrize(
        "extra",
        [
            {"draft": False},
            {"title": "x"},
            {"patient_id": PATIENT_ID},
            {"treatment_note_template_id": "1"},
            {"booking_id": "1"},
        ],
    )
    def test_any_other_field_is_refused(self, extra: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            cc.DraftContent(content=CONTENT, **extra)

    def test_the_model_is_frozen(self) -> None:
        draft = cc.DraftContent(content=CONTENT)
        with pytest.raises(ValidationError):
            draft.content = []  # type: ignore[misc]

    def test_the_content_object_needs_its_sections_list(self) -> None:
        for bad in ({}, {"sections": {}}, {"sections": "x"}, [], "x"):
            with pytest.raises(ValidationError):
                cc.DraftContent(content=bad)

    def test_non_ascii_is_kept_as_utf8(self) -> None:
        assert "é".encode() in cc.DraftContent(content=_one_answer("é")).to_body()

    @pytest.mark.parametrize(
        "answer",
        [pytest.param("\ud800", id="lone-surrogate"), pytest.param(float("nan"), id="nan")],
    )
    def test_an_unencodable_body_is_a_named_error_before_any_request(
        self, answer: Any
    ) -> None:
        """MED-002 (round 9): the codec's own error carries the whole note in
        its ``object`` (and so its repr); what leaves is a fixed sentence."""
        content = _one_answer("x")
        content["sections"][0]["questions"][0]["answer"] = answer
        content["sections"][0]["questions"].append(
            {"name": "Q2", "type": "text", "answer": f"note text {PATIENT_ID}"}
        )
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            with pytest.raises(cc.DraftUnencodable) as info:
                call.write_draft_note(NOTE_ID, cc.DraftContent(content=content))
        assert transport.calls == []
        _assert_carries_nothing(info.value)
        assert "note text" not in repr(info.value)

    def test_a_write_after_the_call_ended_sends_nothing(self) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            pass
        with pytest.raises(RuntimeError, match="ended"):
            call.write_draft_note(NOTE_ID, cc.DraftContent(content=CONTENT))
        assert transport.calls == []

    @pytest.mark.parametrize("bad", ["0", "01", "1/../../patients/1", "", "1\n"])
    def test_a_bad_note_id_sends_nothing(self, bad: str) -> None:
        transport = FakeTransport()
        with _client(transport).call(lambda: KEY) as call:
            with pytest.raises(cc.InvalidId):
                call.write_draft_note(bad, cc.DraftContent(content=CONTENT))
            with pytest.raises(cc.InvalidId):
                call.get_treatment_note_template(bad)
        assert transport.calls == []


# --- the write's answer classes (D5) and the 422 path (D11) ---------------------

SENTINEL = "Wilhelmina sentinel phrase"
SENTINEL_KEY = "wilhelmina_sentinel_phrase"  # identifier-shaped: still data


def _write(transport: Any) -> cc.WriteAnswer:
    client = cc.ClinikoClient(contact_email=EMAIL, transport=transport)
    with client.call(lambda: KEY) as call:
        return call.write_draft_note(NOTE_ID, cc.DraftContent(content=CONTENT))


class TestWriteAnswer:
    @pytest.mark.parametrize(
        ("status", "error"),
        [
            (401, cc.CredentialsRejected),
            (403, cc.CredentialsRejected),
            (404, cc.NotFound),
            (429, cc.RateLimited),
            (400, cc.ClinikoRejected),
            (409, cc.ClinikoRejected),
            (418, cc.ClinikoRejected),
            (422, cc.ClinikoRejected),
            (301, cc.RedirectRefused),
            (307, cc.RedirectRefused),
            (500, cc.Unreachable),
            (503, cc.Unreachable),
            (201, cc.UnexpectedStatus),
            (204, cc.UnexpectedStatus),
            (100, cc.UnexpectedStatus),
            (600, cc.UnexpectedStatus),
        ],
    )
    def test_each_status_is_its_named_class(
        self, status: int, error: type[cc.ClinikoError]
    ) -> None:
        with pytest.raises(error) as info:
            _write(FakeTransport(cc.RawResponse(status, None, b"")))
        # Round 10 LOW-004: every status-bearing class keeps the status.
        assert getattr(info.value, "status", status) == status
        _assert_carries_nothing(info.value)

    def test_another_4xx_carries_no_categories(self) -> None:
        body = json.dumps({"errors": {"content": ["x"]}}).encode()
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(FakeTransport(cc.RawResponse(400, None, body)))
        assert info.value.categories == ()

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param(cc.RawResponse(200, None, b"{not json"), id="malformed"),
            pytest.param(cc.RawResponse(200, None, b"[]"), id="not-an-object"),
            pytest.param(
                cc.RawResponse(200, None, b"{}" + b" " * cc.MAX_BODY_BYTES), id="oversize"
            ),
            pytest.param(cc.RawResponse(200, None, b"", body_unreadable=True), id="stalled"),
        ],
    )
    def test_a_200_is_written_whatever_its_body_does(self, raw: cc.RawResponse) -> None:
        """PR-MED-005: the status line decides; a body that fails to read or
        parse leaves the write ``written`` with no echo."""
        assert _write(FakeTransport(raw)) == cc.WriteAnswer(written=True, note=None)

    def test_the_answer_repr_carries_no_note_text(self) -> None:
        answer = cc.WriteAnswer(written=True, note={"answer": SENTINEL})
        assert SENTINEL not in repr(answer)

    @pytest.mark.parametrize(
        ("errors", "expected"),
        [
            ({"content": ["is invalid"]}, ("content",)),
            ({"draft": ["x"], "title": ["y"]}, ("draft", "title")),
            (
                {
                    "patient_id": [1],
                    "booking_id": [1],
                    "attendee_id": [1],
                    "treatment_note_template_id": [1],
                },
                ("attendee_id", "booking_id", "patient_id", "treatment_note_template_id"),
            ),
            ({SENTINEL_KEY: [SENTINEL], SENTINEL: SENTINEL}, ("other",)),
            ({"content": [SENTINEL], SENTINEL_KEY: {"nested": SENTINEL}}, ("content", "other")),
            ({}, ()),
        ],
    )
    def test_a_422_is_reduced_to_fixed_categories(
        self, errors: dict[str, Any], expected: tuple[str, ...]
    ) -> None:
        body = json.dumps({"message": "Validation Failed", "errors": errors}).encode()
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(FakeTransport(cc.RawResponse(422, None, body)))
        assert info.value.status == 422
        assert info.value.categories == expected
        assert set(info.value.categories) <= cc.REJECTION_CATEGORIES | {cc.REJECTION_OTHER}

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param(b"{not json " + SENTINEL.encode(), id="not-json"),
            pytest.param(b"\xff\xfe" + SENTINEL.encode(), id="not-utf8"),
            pytest.param(json.dumps([SENTINEL]).encode(), id="array"),
            pytest.param(json.dumps({"errors": [SENTINEL]}).encode(), id="errors-array"),
            pytest.param(json.dumps({"errors": SENTINEL}).encode(), id="errors-text"),
            pytest.param(b"[" * 100_000 + b"]" * 100_000, id="nested-past-recursion-limit"),
            pytest.param(
                json.dumps({"errors": {"content": ["x"]}}).encode()
                + b" " * cc.MAX_BODY_BYTES,
                id="oversize",
            ),
        ],
    )
    def test_a_malformed_422_has_no_categories_and_no_chained_context(
        self, body: bytes
    ) -> None:
        """PR-MED-007: the parser's exception never becomes ``__cause__`` or
        ``__context__`` of the named error."""
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(FakeTransport(cc.RawResponse(422, None, body)))
        assert info.value.categories == ()
        assert info.value.__cause__ is None and info.value.__context__ is None
        assert SENTINEL not in "".join(traceback.format_exception(info.value))

    def test_a_stalled_422_has_no_categories(self) -> None:
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(FakeTransport(cc.RawResponse(422, None, b"", body_unreadable=True)))
        assert info.value.categories == ()

    def test_a_422_leaves_no_trace_of_its_keys_or_values(
        self, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The tripwire (D11): a 422 whose keys — an identifier-shaped one
        included — and values carry a sentinel phrase leaves it in no log
        record, no exception text and nothing printed."""
        caplog.set_level(logging.DEBUG)
        body = json.dumps(
            {
                "message": f"Validation Failed {SENTINEL}",
                "errors": {
                    SENTINEL_KEY: [SENTINEL],
                    SENTINEL: [SENTINEL_KEY],
                    "content": [f"{SENTINEL} is invalid"],
                },
            }
        ).encode()
        # Over the real transport, so the body is actually read off the wire.
        response = FakeResponse(status=422, body=body)
        transport, _conn, _built = _transport(response)
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(transport)
        error = info.value
        assert error.categories == ("content", "other")
        rendered = "".join(traceback.format_exception(error))
        logged = caplog.text + "".join(str(r.__dict__) for r in caplog.records)
        out = capsys.readouterr()
        for text in (str(error), repr(error), rendered, logged, out.out, out.err):
            for secret in (SENTINEL, SENTINEL_KEY, "sentinel", *SECRETS):
                assert secret not in text
        assert error.__cause__ is None and error.__context__ is None
        assert str(error) == cc.ClinikoRejected.MESSAGE
        # LOW-001 (round 9): the 422 body is dropped before the raise, so no
        # frame of the client that the error's traceback keeps holds it.
        tb = error.__traceback__
        client_frames = 0
        while tb is not None:
            frame = tb.tb_frame
            if frame.f_code.co_filename == cc.__file__:
                client_frames += 1
                for value in frame.f_locals.values():
                    held = value.body if isinstance(value, cc.RawResponse) else value
                    assert SENTINEL not in repr(held), frame.f_code.co_name
            tb = tb.tb_next
        assert client_frames >= 1

    def test_a_get_422_is_still_unexpected_and_unread(self) -> None:
        response = FakeResponse(status=422, read_error=_hc.IncompleteRead(b"x"))
        transport, _conn, _built = _transport(response)
        with pytest.raises(cc.UnexpectedStatus):
            with cc.ClinikoClient(contact_email=EMAIL, transport=transport).call(
                lambda: KEY
            ) as call:
                call.get_treatment_note(NOTE_ID)
        assert response.read_sizes == []


class TestWriteOverTheTransport:
    """The write's body handling in ``HTTPSTransport`` itself (D5)."""

    def test_a_200_whose_body_stalls_is_still_written(self) -> None:
        now = [0.0]
        response = FakeResponse(status=200, body=b"x" * 100, chunk=1)
        receive = response.read1

        def slow_receive(amt: int) -> bytes:
            now[0] += 4.0
            return receive(amt)

        response.read1 = slow_receive  # type: ignore[method-assign]
        transport, conn, _built = _transport(response, clock=lambda: now[0])
        raw = transport.request(
            "PATCH", API_HOST, WRITE_PATH, WRITE_HEADERS, 1000, body=VALID_BODY
        )
        assert raw.status == 200 and raw.body_unreadable and raw.body == b""
        assert conn.log[-1] == ("close",)
        assert cc._write_outcome(raw) == cc.WriteAnswer(written=True, note=None)

    @pytest.mark.parametrize(
        "error",
        [
            _hc.IncompleteRead(b"partial"),
            ConnectionResetError(),
            TimeoutError(),
            ssl.SSLZeroReturnError(6, "closed"),
            ValueError("I/O operation on closed file"),
        ],
    )
    def test_a_200_whose_body_read_fails_is_still_written(self, error: BaseException) -> None:
        response = FakeResponse(status=200, read_error=error)
        assert _write(_transport(response)[0]) == cc.WriteAnswer(written=True, note=None)

    def test_an_oversize_200_is_written_without_an_echo(self) -> None:
        response = FakeResponse(status=200, body=b"{" + b" " * (cc.MAX_BODY_BYTES + 10) + b"}")
        assert _write(_transport(response)[0]) == cc.WriteAnswer(written=True, note=None)
        assert response.read_sizes == [cc.MAX_BODY_BYTES + 1]

    def test_a_200_echo_is_parsed(self) -> None:
        response = FakeResponse(status=200, body=b'{"draft": true}')
        assert _write(_transport(response)[0]) == cc.WriteAnswer(
            written=True, note={"draft": True}
        )

    def test_a_422_body_is_read_bounded(self) -> None:
        body = json.dumps({"errors": {"content": ["x"]}}).encode()
        response = FakeResponse(status=422, body=body + b" " * (cc.MAX_BODY_BYTES + 10))
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(_transport(response)[0])
        assert info.value.categories == ()  # over the cap: never parsed
        assert response.read_sizes == [cc.MAX_BODY_BYTES + 1]

    def test_a_stalled_422_keeps_its_name(self) -> None:
        response = FakeResponse(status=422, read_error=_hc.IncompleteRead(b"x"))
        with pytest.raises(cc.ClinikoRejected) as info:
            _write(_transport(response)[0])
        assert info.value.categories == ()

    @pytest.mark.parametrize("status", [401, 403, 404, 429, 409, 503, 302])
    def test_other_write_answers_are_never_read(self, status: int) -> None:
        response = FakeResponse(status=status, read_error=_hc.IncompleteRead(b"x"))
        with pytest.raises(cc.ClinikoError):
            _write(_transport(response)[0])
        assert response.read_sizes == []

    @pytest.mark.parametrize(
        ("stage", "exc", "expected"),
        [
            ("request", TimeoutError("timed out"), cc.Unreachable),
            ("request", ConnectionResetError(), cc.Unreachable),
            ("getresponse", _hc.RemoteDisconnected("closed"), cc.Unreachable),
            ("getresponse", _hc.BadStatusLine("x"), cc.Malformed),
            ("request", ssl.SSLCertVerificationError(1, "x"), cc.CertificateRejected),
        ],
    )
    def test_a_failure_before_the_status_line_is_named(
        self, stage: str, exc: BaseException, expected: type[cc.ClinikoError]
    ) -> None:
        transport, _conn, _built = _transport(**{stage: exc})
        with pytest.raises(cc.ClinikoError) as info:
            _write(transport)
        assert type(info.value) is expected
        _assert_carries_nothing(info.value)


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
        self.bodies: list[bytes | None] = []

    def set_debuglevel(self, level: int) -> None:
        self.log.append(("set_debuglevel", level))
        if "set_debuglevel" in self.fail:
            raise self.fail["set_debuglevel"]

    def set_tunnel(self, *args: Any, **kwargs: Any) -> None:  # must never be called
        self.log.append(("set_tunnel",))

    def request(
        self, method: str, url: str, body: bytes | None = None, *, headers: Mapping[str, str]
    ) -> None:
        self.log.append(("request", method, url, dict(headers)))
        self.bodies.append(body)
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
        raw = transport.request("GET", API_HOST, "/v1/user", {"Accept": "b"}, 100)
        context = built[0][1]
        assert built[1] == (
            "api.au2.cliniko.com",
            {"port": 443, "timeout": 7.5, "context": context},
        )
        assert conn.log == [
            ("set_debuglevel", 0),
            ("request", "GET", "/v1/user", {"Accept": "b"}),
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
        raw = transport.request("GET", API_HOST, "/v1/p", {}, 10)
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
            transport.request("GET", API_HOST, "/v1/p", {}, 1000)
        assert len(response.read_sizes) == 8  # receives start at t=0..28; t=32 is past 30
        assert conn.log[-1] == ("close",)
        _assert_carries_nothing(info.value)

    def test_a_slow_request_is_abandoned_before_the_answer_is_read(self) -> None:
        now = [0.0]
        transport, conn, _built = _transport(clock=lambda: now[0])
        send = conn.request

        def slow_request(
            method: str, url: str, body: bytes | None = None, *, headers: Mapping[str, str]
        ) -> None:
            now[0] += 31.0
            send(method, url, body, headers=headers)

        conn.request = slow_request  # type: ignore[method-assign]
        with pytest.raises(cc.Unreachable):
            transport.request("GET", API_HOST, "/v1/p", {}, 10)
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
        assert getattr(info.value, "status", status) == status  # round 11 LOW-001
        if status == 429:
            assert isinstance(info.value, cc.RateLimited) and info.value.reset == "60"
        assert response.read_sizes == []  # the body was never read
        assert conn.log[-1] == ("close",)

    def test_a_non_200_answer_carries_no_body(self) -> None:
        transport, _conn, _built = _transport(FakeResponse(status=404, body=b"{}"))
        raw = transport.request("GET", API_HOST, "/v1/p", {}, 10)
        assert raw.status == 404 and raw.body == b""

    def test_the_raw_response_repr_carries_no_body(self) -> None:
        """Round 7 LOW-002: the body is patient data; a stray repr of a
        ``RawResponse`` (a log line, a traceback's locals) must not carry it."""
        raw = cc.RawResponse(200, None, f'{{"first_name": "{PATIENT_ID}"}}'.encode())
        assert PATIENT_ID not in repr(raw) and "first_name" not in repr(raw)
        assert raw == cc.RawResponse(200, None, raw.body)  # still compared

    def test_a_close_failure_changes_no_outcome(self) -> None:
        transport, _conn, _built = _transport(close=OSError("reset"))
        raw = transport.request("GET", API_HOST, "/v1/p", {}, 10)
        assert raw.status == 200

    def test_a_tls_context_failure_is_named(self) -> None:
        def broken() -> ssl.SSLContext:
            raise ssl.SSLError(1, "no certificate store")

        transport = cc.HTTPSTransport(connection_factory=lambda *a, **k: None, tls_context=broken)
        with pytest.raises(cc.Unreachable) as info:
            transport.request("GET", API_HOST, "/v1/p", {}, 10)
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
        assert len(transport.calls) == 8

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


# Cliniko draft-write plan Task 5.3 (Critical Constraint 2): the write and its
# reconcile start only from the Note tab's button slot. The chain is
# ``ClinikoCall.write_draft_note`` -> ``draft_write`` (its ONE caller module)
# -> ``MainWindow._on_write_requested`` (the ONE slot, connected only to the
# Note tab's ``write_requested``). ``TestWriteCallSites`` holds the FIRST
# link: what a module outside the client may reach of it at all. The slot's
# own AST pin arrives with the slot (Task 5.2). Outside the package, and so
# outside these pins by design: ``scripts/probe-cliniko.py``'s
# practitioner-run ``--test-write`` modes (Flow 4), which the app never
# imports.
_CLIENT = "cliniko_client.py"
# Everything each importer may bind from the client, by name — the whole
# client namespace a module outside it can hold, so ``http``, ``ssl``,
# ``HTTPSTransport``, ``_WRITE_METHOD``, ``_admit`` and the module object
# itself are refused by default. Pinned EXACTLY (no slack). A new caller
# updates it together with the threat model's "Cliniko API client" section
# and flow 18.
_ALLOWED_IMPORTS: Mapping[str, frozenset[str]] = {
    "clinics.py": frozenset(
        {
            "SHARDS",
            "CertificateRejected",
            "ClinikoClient",
            "ClinikoError",
            "CredentialsRejected",
            "InvalidContactEmail",
            "InvalidKey",
            "NotFound",
            "RateLimited",
            "Transport",
            "Unreachable",
            "check_id",
            "shard_of_key",
            "validate_contact_email",
        }
    ),
    "encounter.py": frozenset(
        {
            "CertificateRejected",
            "ClinikoCall",
            "ClinikoClient",
            "ClinikoError",
            "CredentialsRejected",
            "InvalidKey",
            "NotFound",
            "RateLimited",
            "Transport",
            "Unreachable",
            "check_id",
        }
    ),
}
# The ``ClinikoCall`` capabilities each module may name, pinned exactly;
# every other module may name none. ``draft_write.py`` gains
# ``write_draft_note`` with Task 3.2.
_ALLOWED_CAPABILITIES: Mapping[str, frozenset[str]] = {
    "clinics.py": frozenset({"get_user", "get_practitioners_for_user", "get_public_settings"}),
    "encounter.py": frozenset({"get_treatment_note", "get_patient", "get_booking"}),
}
# ``ClinikoCall``'s public members that reach nothing: ``close`` drops the
# key (``host``, a property, is left out by the derivation).
_INERT_CALL_MEMBERS = frozenset({"close"})
# Attribute routes into a function's module globals or an object's members
# that step around every name the pins derive.
_REFLECTION = frozenset({"__globals__", "__dict__"})


@cache
def _client_classes() -> dict[str, ast.ClassDef]:
    tree = ast.parse((SRC / _CLIENT).read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _is_private(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__")


def _private_members() -> frozenset[str]:
    """Every private member a client class defines, DERIVED from the client's
    source — method names, ``self._x`` targets and class-body annotations —
    so a new private sender or attribute is covered with no pin change."""
    names: set[str] = set()
    for cls in _client_classes().values():
        for node in ast.walk(cls):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.ctx, ast.Store)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                names.add(node.attr)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return frozenset(name for name in names if _is_private(name))


def _public_methods(*class_names: str) -> frozenset[str]:
    classes = _client_classes()
    return frozenset(
        node.name
        for class_name in class_names
        for node in classes[class_name].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
        and not any(
            isinstance(decorator, ast.Name) and decorator.id == "property"
            for decorator in node.decorator_list
        )
    )


def _call_capabilities() -> frozenset[str]:
    """``ClinikoCall``'s public methods less the inert ones — each reaches
    Cliniko. Derived, so a new read or write is covered with no pin change."""
    return _public_methods("ClinikoCall") - _INERT_CALL_MEMBERS


def _transport_sends() -> frozenset[str]:
    """The transport types' public methods — each sends a request."""
    return _public_methods("Transport", "HTTPSTransport")


_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda


def _parameters(fn: _FunctionNode) -> list[ast.arg]:
    args = fn.args
    extra = [arg for arg in (args.vararg, args.kwarg) if arg is not None]
    return [*args.posonlyargs, *args.args, *args.kwonlyargs, *extra]


def _binds_again(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """Whether ``fn`` binds its parameter ``name`` again in its OWN scope —
    asked of the compiler's symbol table (``symtable``), never of a list of
    binding node types, so every binding form the language has counts: an
    assignment, ``del``, a loop / ``with`` / walrus target, ``except … as``,
    ``import … as``, a nested ``def`` / ``class`` of that name, and a
    ``match`` capture (``case name``, ``[*name]``, ``{**name}``) — the forms
    the AST records as plain strings included. A nested scope's own LOCAL
    binding lives in its own child table and is not ``fn``'s; but a nested
    function, lambda, comprehension or class body that declares the name
    ``nonlocal`` and binds it there (codex round 19 PR-LOW-033) rebinds
    ``fn``'s parameter, so every descendant table is asked too — a
    ``nonlocal`` that only READS it does not count. Source the compiler
    refuses on its own (e.g. a ``nonlocal`` that needs the enclosing
    function) counts as bound: fail closed."""
    try:
        module = symtable.symtable(ast.unparse(fn), "<method>", "exec")
    except SyntaxError:
        return True
    tables = list(module.get_children())
    while tables:
        table = tables.pop(0)
        if isinstance(table, symtable.Function) and table.get_name() == fn.name:
            symbol = table.lookup(name)
            if symbol.is_assigned() or symbol.is_imported():
                return True
            nested = list(table.get_children())
            while nested:
                child = nested.pop()
                if name in child.get_identifiers():
                    inner = child.lookup(name)
                    if inner.is_nonlocal() and (inner.is_assigned() or inner.is_imported()):
                        return True
                nested.extend(child.get_children())
            return False
        tables.extend(table.get_children())
    return True


def _where_parameter_holds(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> list[ast.AST]:
    """Every node of ``fn``'s body in which ``name`` is still ``fn``'s own
    parameter — skipping a nested function or lambda that shadows it and a
    nested class — or ``[]`` when ``fn`` binds it again anywhere in its own
    scope (``_binds_again``, the compiler's answer) or in a comprehension
    (whose target shadows it there): then no use of it counts as the
    class's own."""
    if _binds_again(fn, name):
        return []
    held: list[ast.AST] = []
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, _FunctionNode) and any(p.arg == name for p in _parameters(node)):
            continue
        if isinstance(node, ast.ClassDef):
            continue
        if isinstance(node, ast.Name) and node.id == name and not isinstance(node.ctx, ast.Load):
            return []
        held.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return held


def _own_member_uses(tree: ast.AST, private: frozenset[str]) -> set[int]:
    """The ``id`` of every ``<receiver>.<private>`` node that is a class's use
    of ITS OWN member — the structural exemption, never a spelling: the
    receiver is the enclosing method's FIRST parameter (a ``staticmethod``
    has none), still that parameter where it is used (``_where_parameter_
    holds``), and the enclosing class ITSELF defines the member — a method
    of that name, a class-body binding, or a store on the first parameter in
    one of its methods. A subclass of a client class inherits ``_send`` but
    never defines it, so its ``self._send`` is not exempt."""
    exempt: set[int] = set()
    for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        receivers: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = [
            (fn, _parameters(fn)[0].arg)
            for fn in cls.body
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            and fn.args.posonlyargs + fn.args.args
            and not any(
                isinstance(decorator, ast.Name) and decorator.id == "staticmethod"
                for decorator in fn.decorator_list
            )
        ]
        defined: set[str] = set()
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
            elif isinstance(node, ast.Assign):
                defined.update(t.id for t in node.targets if isinstance(t, ast.Name))
        for fn, first in receivers:
            defined.update(
                node.attr
                for node in ast.walk(fn)
                if isinstance(node, ast.Attribute)
                and isinstance(node.ctx, ast.Store)
                and isinstance(node.value, ast.Name)
                and node.value.id == first
            )
        for fn, first in receivers:
            if not any(
                isinstance(node, ast.Attribute)
                and node.attr in private
                and isinstance(node.value, ast.Name)
                and node.value.id == first
                for node in ast.walk(fn)
            ):
                continue  # nothing to exempt: skip the symbol-table pass
            exempt.update(
                id(node)
                for node in _where_parameter_holds(fn, first)
                if isinstance(node, ast.Attribute)
                and node.attr in private
                and node.attr in defined
                and isinstance(node.value, ast.Name)
                and node.value.id == first
            )
    return exempt


def _client_class_aliases(tree: ast.AST, client_classes: frozenset[str]) -> frozenset[str]:
    """``client_classes`` plus every name ``tree`` binds to one of them, by a
    plain or annotated assignment, through any chain of such aliases."""
    names = set(client_classes)
    bindings: list[tuple[list[ast.expr], ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            bindings.append((node.targets, node.value))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            bindings.append(([node.target], node.value))
    grew = True
    while grew:
        grew = False
        for targets, value in bindings:
            if not (
                (isinstance(value, ast.Name) and value.id in names)
                or (isinstance(value, ast.Attribute) and value.attr in client_classes)
            ):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.add(target.id)
                    grew = True
    return frozenset(names)


def _client_reach(tree: ast.AST, module: str) -> list[str]:
    """Every reach into the client in ``tree`` (the source of ``module``)
    that the pins do not admit — the rules ``TestWriteCallSites`` states."""
    private = _private_members()
    capabilities = _call_capabilities() - _ALLOWED_CAPABILITIES.get(module, frozenset())
    sends = _transport_sends()
    imports = _ALLOWED_IMPORTS.get(module, frozenset())
    client_classes = frozenset(_client_classes())
    class_names = _client_class_aliases(tree, client_classes)
    own_uses = _own_member_uses(tree, private)
    forbidden_strings = private | capabilities | sends | _REFLECTION
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if "cliniko_client" in a.name]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").endswith("cliniko_client"):
                found += [f"client import {a.name}" for a in node.names if a.name not in imports]
            else:
                found += [f"import {a.name}" for a in node.names if a.name == "cliniko_client"]
        elif isinstance(node, ast.ClassDef):
            found += [
                f"subclass of {ast.unparse(base)}"
                for base in node.bases
                if any(
                    (isinstance(part, ast.Name) and part.id in class_names)
                    or (isinstance(part, ast.Attribute) and part.attr in client_classes)
                    for part in ast.walk(base)
                )
            ]
        elif isinstance(node, ast.Attribute):
            if (
                node.attr == "cliniko_client"
                or node.attr in _REFLECTION
                or node.attr in capabilities
                or (node.attr in private and id(node) not in own_uses)
            ):
                found.append(f".{node.attr}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in sends:
                found.append(f".{node.func.attr}(...)")
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and node.value in forbidden_strings:
                found.append(repr(node.value))
    return found


class TestWriteCallSites:
    """What a module outside the client may reach of it — the SEMANTIC
    surface is "anything that can put a request on the network", and the
    client is the only module that can (``TestConfinement``). So the pins
    CONFINE the client's surface instead of listing forbidden spellings
    (``docs/lessons.md`` 2026-08-10): the private members and capabilities
    are DERIVED from the client's own source, and a module outside it may
    reach only a pinned allow-list; anything new fails by default.

    Outside ``cliniko_client.py``, in every module:
    - imports: a module may import from the client only the names
      ``_ALLOWED_IMPORTS`` pins for it (none, for all but ``clinics.py`` and
      ``encounter.py``) — never the module object, so ``http`` / ``ssl``,
      ``HTTPSTransport``, ``_WRITE_METHOD``, ``_admit`` are out of reach;
    - no class has a base naming a client class — by name, as an attribute
      (``encounter.ClinikoCall``), or through a name the module binds to one
      (``B = ClinikoCall``);
    - a client class's private member (``_send``, ``_transport``,
      ``_factory``, ``_authorization`` …, derived) appears only as a
      class's use of ITS OWN member (``_own_member_uses``): on the enclosing
      method's first parameter, never bound again in that method (the
      compiler's symbol table decides — ``_binds_again``), where the
      class itself defines the member — never on another receiver (a
      module-level ``self = call`` included) and never as a string
      (``getattr``, ``vars(x)[…]``);
    - a ``ClinikoCall`` capability (its public methods but ``close``,
      derived — every read and ``write_draft_note``) is named only by the
      modules ``_ALLOWED_CAPABILITIES`` pins for it, as attribute or string;
    - a transport send (``request``) is never CALLED as ``x.request(…)`` and
      never named as a string;
    - ``__globals__`` / ``__dict__`` are never reached.

    Residue, named: (1) the transport's ``request`` is checked in call
    position only — the name collides with the app's own ``result.request``
    / ``checkout.request`` data fields, so a bound-then-called
    ``f = t.request`` is unseen; (2) names built at run time (joined
    strings, ``getattr`` over a computed name), ``vars(obj)`` without a
    subscript string, ``sys.modules``, ``importlib`` / ``__import__`` — no
    source pin sees them; review does. Holding a client object is allowed
    anywhere (``ClinikoClient`` and ``ClinikoCall`` are importable, and
    ``encounter`` / ``clinics`` re-export what they import); what it can DO
    outside the pinned modules is what the rules above confine."""

    def test_no_module_reaches_the_client_beyond_its_pins(self) -> None:
        offenders: dict[str, list[str]] = {}
        for path in sorted(SRC.rglob("*.py")):
            module = path.relative_to(SRC).as_posix()
            if module == _CLIENT:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            found = _client_reach(tree, module)
            if found:
                offenders[module] = found
        assert offenders == {}

    def test_the_allow_lists_are_exactly_what_each_module_uses(self) -> None:
        """No slack: an entry a module no longer uses is a widening nobody
        reviewed, so each pin equals the module's actual use."""
        capabilities = _call_capabilities()
        for module, allowed in _ALLOWED_IMPORTS.items():
            tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
            imported = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                and (node.module or "").endswith("cliniko_client")
                for alias in node.names
            }
            named = {
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute) and node.attr in capabilities
            }
            assert imported == allowed, module
            assert named == _ALLOWED_CAPABILITIES[module], module
        assert set(_ALLOWED_CAPABILITIES) <= set(_ALLOWED_IMPORTS)

    def test_the_derived_surface_is_the_clients_own(self) -> None:
        """Guards the derivation: a refactor cannot quietly empty the sets."""
        assert {
            "_send",
            "_get",
            "_transport",
            "_factory",
            "_tls_context",
            "_authorization",
            "_host",
        } <= _private_members()
        assert {"write_draft_note", "get_user", "get_treatment_note"} <= _call_capabilities()
        assert not {"close", "host"} & _call_capabilities()
        assert "request" in _transport_sends()
        for allowed in (*_ALLOWED_IMPORTS.values(), *_ALLOWED_CAPABILITIES.values()):
            assert allowed <= set(vars(cc)) | _call_capabilities()

    def test_the_write_method_is_sent_once_from_write_draft_note(self) -> None:
        """Inside the client: ``ClinikoCall._send`` is called twice — the
        write method from ``write_draft_note`` and ``GET`` from ``_get`` — and
        ``_WRITE_METHOD`` is passed as an argument nowhere else."""
        call_class = _client_classes()["ClinikoCall"]
        sends = [
            (method.name, ast.unparse(node.args[0]))
            for method in call_class.body
            if isinstance(method, ast.FunctionDef)
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_send"
        ]
        assert sends == [("write_draft_note", "_WRITE_METHOD"), ("_get", "'GET'")]
        client = ast.parse((SRC / _CLIENT).read_text(encoding="utf-8"))
        passed = [
            node
            for node in ast.walk(client)
            if isinstance(node, ast.Call)
            and any(
                isinstance(arg, ast.Name) and arg.id == "_WRITE_METHOD"
                for arg in (*node.args, *(keyword.value for keyword in node.keywords))
            )
        ]
        assert len(passed) == 1

    def test_the_pin_sees_every_form_it_claims(self) -> None:
        """Guards the rules themselves: each is recognised in a module with
        no allowance, and in an importer beyond its pin; near-misses pass."""
        reaches = (
            "import scribe_desktop.cliniko_client",
            "import scribe_desktop.cliniko_client as cc",
            "from scribe_desktop import cliniko_client",
            "from . import cliniko_client",
            "from scribe_desktop.cliniko_client import ssl",
            "from scribe_desktop.cliniko_client import http as h",
            "from scribe_desktop.cliniko_client import HTTPSTransport",
            "from .cliniko_client import _WRITE_METHOD",
            "x = scribe_desktop.cliniko_client",
            "class Mine(ClinikoCall): pass",
            "call._send('PUT', '/treatment_notes/1', body)",
            "call._transport._factory(host)",
            "self._transport._tls_context()",
            "ClinikoCall._send(call, 'PATCH', path, body)",
            "getattr(call, '_send')",
            "vars(call)['_authorization']",
            "call.write_draft_note('1', content)",
            "send = call.write_draft_note",
            "getattr(call, 'write_draft_note')",
            "call.get_settings()",
            "self._transport.request('DELETE', host, path, headers, 1)",
            "getattr(transport, 'request')",
            "call.get_user.__globals__['http']",
            "type(call).__dict__",
            # Round 17 PR-MED-030: the exemption is structural, not the name.
            "self = call\nself._send('PATCH', '/treatment_notes/1', body)",
            "def f(call):\n    self = call\n    return self._authorization",
            "class Mine:\n    def f(self):\n        return self._send('PUT', '/x', b'')",
            "class Mine:\n"
            "    def _send(self):\n        pass\n"
            "    def f(self, call):\n        self = call\n        self._send('PUT', '/x', b'')",
            "class Mine:\n"
            "    _send = None\n"
            "    @staticmethod\n    def f(self):\n        self._send('PUT', '/x', b'')",
            "class Mine:\n"
            "    def __init__(self):\n        self._clock = 1\n"
            "    def f(self, xs):\n"
            "        for self in xs:\n            pass\n"
            "        return self._clock",
            "class Mine(encounter.ClinikoCall): pass",
            "B = ClinikoCall\nclass Mine(B): pass",
            "B = encounter.ClinikoCall\nC = B\nclass Mine(C): pass",
            "class Mine(Generic[ClinikoCall]): pass",
        )
        for sample in reaches:
            assert _client_reach(ast.parse(sample), "ui/bridge.py"), sample
        # Round 18 PR-LOW-032: every way to bind the receiver again — the
        # forms the AST keeps as plain strings included — voids the
        # exemption, in a class that DOES define ``_send``; the same class
        # with no rebinding stays exempt (the control).
        rebindings = (
            "match call:\n    case self:\n        pass",
            "match call:\n    case [*self]:\n        pass",
            "match call:\n    case {**self}:\n        pass",
            "match call:\n    case {'k': self}:\n        pass",
            "try:\n    pass\nexcept Exception as self:\n    pass",
            "import os as self",
            "from os import path as self",
            "def self():\n    pass",
            "class self:\n    pass",
            "with open(call) as self:\n    pass",
            "del self",
            "self: object = call",
            "self += 1",
            # Round 19 PR-LOW-033: a NESTED scope declaring it ``nonlocal``
            # and binding it — through the forms the AST keeps as strings.
            "def replace():\n"
            "    nonlocal self\n"
            "    match call:\n        case self:\n            pass\n"
            "replace()",
            "def replace():\n"
            "    nonlocal self\n"
            "    try:\n        pass\n    except Exception as self:\n        pass",
            "def swap():\n    nonlocal self\n    import os as self",
            "class Inner:\n    nonlocal self\n    from os import path as self",
            "def outer():\n"
            "    def inner():\n        nonlocal self\n        def self():\n            pass",
        )
        # The controls: no rebinding at all, and a nested ``nonlocal`` that
        # only READS the receiver — both keep the class's own-member exemption.
        controls = ("pass", "def peek():\n    nonlocal self\n    return self")
        for rebinding in (*rebindings, *controls):
            body = textwrap.indent(f"{rebinding}\nself._send('PUT', '/x', b'')", " " * 8)
            sample = f"class Mine:\n    _send = None\n    def f(self, call):\n{body}"
            reached = _client_reach(ast.parse(sample), "ui/bridge.py")
            assert reached if rebinding not in controls else not reached, sample
        # An importer beyond its own pins.
        for sample in (
            "from scribe_desktop.cliniko_client import ClinikoCall",
            "call.get_patient('1')",
            "call.write_draft_note('1', content)",
        ):
            assert _client_reach(ast.parse(sample), "clinics.py"), sample
        near_misses = (
            # A class's use of its OWN member on the method's first parameter.
            "class Registry:\n"
            "    def __init__(self, transport, clock):\n"
            "        self._transport = transport\n"
            "        self._clock = clock\n"
            "    @property\n    def transport(self):\n        return self._transport\n"
            "    def now(self):\n        return (lambda: self._clock())()\n"
            "    def inner(self):\n"
            "        def shadowed(self):\n            return self\n"
            "        return self._clock()",
            "class Latch:\n"
            "    _clock = None\n"
            "    def at(me):\n        return me._clock()",
            "self._send_event.set()",
            "result.request.clinic",
            "checkout.request = None",
            "from scribe_desktop.cliniko_client import ClinikoClient, check_id",
            "call.close()",
            "call.host",
            "client.call(read_key)",
            '"""Send a PATCH to one note."""',
        )
        for near_miss in near_misses:
            assert not _client_reach(ast.parse(near_miss), "clinics.py"), near_miss
