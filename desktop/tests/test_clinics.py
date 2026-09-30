"""Clinic registry (Cliniko workflow safeguards plan Tasks 2.1a / 2.1b, D9/D10).

Every Cliniko answer comes from an injected transport and every key goes to
an in-memory key store: no network, no Credential Manager, no host file.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import scribe_desktop.clinics as clinics_module
from scribe_desktop import cliniko_client as cc
from scribe_desktop.clinics import (
    KEY_SECRET_NAME,
    MAX_CLINICS,
    ClinicHost,
    ClinicRecord,
    ClinicRefusal,
    ClinicRegistry,
    Committed,
    LoadProblem,
    Refused,
    Removed,
    ValidatedAccount,
    ValidationRequest,
    parse_clinic_address,
)
from scribe_desktop.session_store import StoreWriteError

KEY ="MS0xMjM0NTY3ODkwLWZha2Uta2V5LWZvci10ZXN0cw-au2"
KEY_2 = "U2Vjb25kLWZha2Uta2V5LWZvci10aGUtc2FtZS1jbGluaWM-au2"
KEY_3 = "VGhpcmQtZmFrZS1rZXktZm9yLXRoZS1zYW1lLWNsaW5pYw-au2"
KEY_AU3 = "RmFrZS1rZXktb24tYW5vdGhlci1zaGFyZA-au3"
EMAIL = "practitioner@example-clinic.com.au"
NOW = datetime(2026, 9, 27, 7, 0, tzinfo=UTC)
# Task P.1 (clinic 1): the practitioner's own login is an administrator with
# one active practitioner record — D10 as amended accepts it.
USER = {"id": "1234567", "role": "administrator", "active": True}
PRACTITIONERS = {"practitioners": [{"id": "7654321", "active": True}], "total_entries": 1}
PUBLIC = {"account": {"subdomain": "northside"}}
IDS = ["0123456789abcdef", "fedcba9876543210", "00112233445566ff", "ffeeddccbbaa9988"]


def _token(key: str) -> str:
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def ok(body: object) -> cc.RawResponse:
    return cc.RawResponse(status=200, rate_limit_reset=None, body=json.dumps(body).encode())


def status(code: int) -> cc.RawResponse:
    return cc.RawResponse(status=code, rate_limit_reset=None, body=b"")


# A RawResponse, an exception to raise, or a zero-argument callable answering.
Answer = Any


class ScriptedTransport:
    """Answers the three validation reads by path; records every request."""

    def __init__(
        self,
        user: Answer | None = None,
        practitioners: Answer | None = None,
        public: Answer | None = None,
    ) -> None:
        self.routes: dict[str, Answer] = {
            "/v1/user": user if user is not None else ok(USER),
            "/v1/practitioners": (
                practitioners if practitioners is not None else ok(PRACTITIONERS)
            ),
            "/v1/settings/public": public if public is not None else ok(PUBLIC),
        }
        self.calls: list[tuple[str, str, str, dict[str, str]]] = []

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
        assert body is None, "the clinic registry only reads"
        self.calls.append((method, host, path, dict(headers)))
        route = next(r for r in self.routes if path == r or path.startswith(r + "?"))
        answer = self.routes[route]
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer()
        return answer


class MemoryKeyStore:
    def __init__(self) -> None:
        self.keys: dict[tuple[str, str], str] = {}
        self.reads = 0
        self.fail_store = False
        self.fail_after_store = False  # writes, THEN raises (round 15 LOW-010)
        self.fail_delete = False

    def store(self, clinic_id: str, secret_name: str, value: str) -> None:
        if self.fail_store:
            raise RuntimeError("backend unavailable")
        self.keys[(clinic_id, secret_name)] = value
        if self.fail_after_store:
            raise RuntimeError("backend failed after writing")

    def retrieve(self, clinic_id: str, secret_name: str) -> str | None:
        self.reads += 1
        return self.keys.get((clinic_id, secret_name))

    def delete(self, clinic_id: str, secret_name: str) -> None:
        if self.fail_delete:
            raise RuntimeError("backend unavailable")
        self.keys.pop((clinic_id, secret_name), None)


def make_registry(
    tmp_path: Path,
    transport: Any = None,
    storage: MemoryKeyStore | None = None,
) -> ClinicRegistry:
    ids: Iterator[str] = iter(IDS)
    return ClinicRegistry(
        tmp_path / "clinics.json",
        storage=storage if storage is not None else MemoryKeyStore(),
        transport=transport if transport is not None else ScriptedTransport(),
        clock=lambda: NOW,
        id_factory=lambda: next(ids),
    )


def begin(registry: ClinicRegistry, **overrides: Any) -> ValidationRequest | Refused:
    kwargs: dict[str, Any] = {
        "api_key": KEY,
        "contact_email": EMAIL,
        "display_name": "Northside",
        "typed_address": None,
    }
    kwargs.update(overrides)
    return registry.begin_validation(**kwargs)


def validate(registry: ClinicRegistry, **overrides: Any) -> Committed | Refused:
    request = begin(registry, **overrides)
    if isinstance(request, Refused):
        return request
    return registry.commit_validation(request, registry.run_validation(request))


def added(registry: ClinicRegistry, **overrides: Any) -> ClinicRecord:
    outcome = validate(registry, **overrides)
    assert isinstance(outcome, Committed), outcome
    return outcome.record


def write_file(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def record_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "clinic_id": IDS[0],
        "display_name": "Northside",
        "subdomain": "northside",
        "shard": "au2",
        "user_id": "1234567",
        "practitioner_id": "7654321",
        "validated_at": "2026-09-27T07:00:00+00:00",
        "subdomain_confirmed": True,
    }
    base.update(overrides)
    return base


def file_dict(*records: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": 1,
        "contact_email": EMAIL,
        "clinics": list(records),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Task 2.1a: the record type and the fail-closed loader (no network).
# ---------------------------------------------------------------------------


class TestLoader:
    def test_a_missing_file_is_an_empty_registry(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        assert registry.records == ()
        assert registry.load_problem is None
        assert registry.allow_list() == ()
        assert registry.contact_email is None

    def test_a_valid_file_loads_every_field(self, tmp_path: Path) -> None:
        write_file(
            tmp_path / "clinics.json",
            file_dict(
                record_dict(),
                record_dict(
                    clinic_id=IDS[1],
                    display_name="Southside",
                    subdomain="southside",
                    shard="au3",
                    subdomain_confirmed=False,
                ),
            ),
        )
        registry = make_registry(tmp_path)
        assert registry.load_problem is None
        assert registry.contact_email == EMAIL
        first, second = registry.records
        assert first.host == "northside.au2.cliniko.com"
        assert first.validated_at == NOW
        assert second.subdomain_confirmed is False
        assert registry.allow_list() == (
            "northside.au2.cliniko.com",
            "southside.au3.cliniko.com",
        )
        assert registry.record(IDS[1]) == second
        assert registry.record("ffffffffffffffff") is None

    def test_what_is_saved_loads_back_and_never_holds_the_key(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        record = added(registry)
        blob = (tmp_path / "clinics.json").read_bytes()
        assert KEY.encode() not in blob
        assert KEY.split("-")[0].encode() not in blob
        reloaded = make_registry(tmp_path)
        assert reloaded.records == (record,)
        assert reloaded.contact_email == EMAIL

    @pytest.mark.parametrize(
        ("name", "payload"),
        [
            ("not json", b"{not json"),
            ("a list", b"[]"),
            ("schema version 2", file_dict(schema_version=2)),
            ("an unknown top-level field", file_dict(extra=True)),
            ("an unknown record field", file_dict(record_dict(api_key="x"))),
            ("a bad clinic id", file_dict(record_dict(clinic_id="../etc"))),
            ("a blank name", file_dict(record_dict(display_name="  "))),
            ("a newline in the name", file_dict(record_dict(display_name="a\nb"))),
            ("a long name", file_dict(record_dict(display_name="x" * 61))),
            ("an unknown shard", file_dict(record_dict(shard="zz9"))),
            ("the API host as a subdomain", file_dict(record_dict(subdomain="api"))),
            ("a dotted subdomain", file_dict(record_dict(subdomain="a.b"))),
            ("an upper-case subdomain", file_dict(record_dict(subdomain="North"))),
            ("a numeric user id", file_dict(record_dict(user_id=1234567))),
            ("a leading-zero id", file_dict(record_dict(practitioner_id="0765"))),
            ("a naive time", file_dict(record_dict(validated_at="2026-09-27T07:00:00"))),
            ("a string flag", file_dict(record_dict(subdomain_confirmed="yes"))),
            ("a bad contact email", file_dict(contact_email="a@b\r\nX: y")),
            (
                "a repeated clinic id",
                file_dict(record_dict(), record_dict(subdomain="southside")),
            ),
            (
                "a repeated subdomain",
                file_dict(record_dict(), record_dict(clinic_id=IDS[1])),
            ),
            (
                "more clinics than the cap",
                file_dict(
                    *(
                        record_dict(clinic_id=IDS[i], subdomain=f"clinic{i}")
                        for i in range(MAX_CLINICS + 1)
                    )
                ),
            ),
        ],
    )
    def test_a_bad_file_fails_closed(
        self, tmp_path: Path, name: str, payload: bytes | dict[str, Any]
    ) -> None:
        path = tmp_path / "clinics.json"
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            write_file(path, payload)
        registry = make_registry(tmp_path)
        assert registry.load_problem is LoadProblem.NOT_VALID, name
        assert registry.records == ()
        assert registry.allow_list() == ()

    def test_an_oversized_file_fails_closed(self, tmp_path: Path) -> None:
        (tmp_path / "clinics.json").write_bytes(b" " * (clinics_module.MAX_FILE_BYTES + 1))
        registry = make_registry(tmp_path)
        assert registry.load_problem is LoadProblem.TOO_LARGE
        assert registry.records == ()

    def test_an_unopenable_file_fails_closed(self, tmp_path: Path) -> None:
        (tmp_path / "clinics.json").mkdir()
        registry = make_registry(tmp_path)
        assert registry.load_problem is LoadProblem.UNREADABLE
        assert registry.records == ()

    def test_a_damaged_file_is_never_overwritten(self, tmp_path: Path) -> None:
        path = tmp_path / "clinics.json"
        path.write_bytes(b"{damaged")
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport, store)
        request = begin(registry)
        assert request == Refused(ClinicRefusal.REGISTRY_UNREADABLE)
        assert registry.remove(IDS[0], live_session_clinic=None) == Refused(
            ClinicRefusal.REGISTRY_UNREADABLE, IDS[0]
        )
        assert registry.confirm_subdomain_from_note(IDS[0], "x.au2.cliniko.com", 0) is False
        assert path.read_bytes() == b"{damaged"
        assert transport.calls == [] and store.keys == {}

    def test_a_commit_is_refused_when_the_file_was_found_damaged(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        request = begin(registry)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        registry._load_problem = LoadProblem.NOT_VALID  # as if loaded damaged
        outcome = registry.commit_validation(request, result)
        assert outcome == Refused(ClinicRefusal.REGISTRY_UNREADABLE, request.clinic_id)


class TestClinicAddress:
    @pytest.mark.parametrize(
        "text",
        [
            "northside.au2.cliniko.com",
            "  Northside.AU2.Cliniko.com ",
            "https://northside.au2.cliniko.com",
            "https://northside.au2.cliniko.com/patients/123/treatment_notes/456/edit?page=1",
            "northside.au2.cliniko.com/appointments#today",
        ],
    )
    def test_accepted_forms_keep_only_the_host(self, text: str) -> None:
        assert parse_clinic_address(text) == ClinicHost("northside", "au2")

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "northside",
            "http://northside.au2.cliniko.com",
            "ftp://northside.au2.cliniko.com",
            "northside.au2.cliniko.com:443",
            "user@northside.au2.cliniko.com",
            "api.au2.cliniko.com",
            "www.au2.cliniko.com",
            "northside.zz9.cliniko.com",
            "northside.cliniko.com",
            "a.b.au2.cliniko.com",
            "northside.au2.cliniko.com.example.com",
            "-northside.au2.cliniko.com",
            "north side.au2.cliniko.com",
            "x" * 2049,
        ],
    )
    def test_anything_else_is_refused(self, text: str) -> None:
        with pytest.raises(ValueError):
            parse_clinic_address(text)


# ---------------------------------------------------------------------------
# Task 2.1b: validation (D10) and storage.
# ---------------------------------------------------------------------------


class TestValidation:
    def test_the_cliniko_route_stores_the_key_and_the_record(self, tmp_path: Path) -> None:
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport, store)
        record = added(registry)
        assert record == ClinicRecord(
            clinic_id=IDS[0],
            display_name="Northside",
            subdomain="northside",
            shard="au2",
            user_id="1234567",
            practitioner_id="7654321",
            validated_at=NOW,
            subdomain_confirmed=True,
        )
        assert store.keys == {(IDS[0], KEY_SECRET_NAME): KEY}
        assert registry.records == (record,)
        assert registry.contact_email == EMAIL
        assert registry.allow_list() == ("northside.au2.cliniko.com",)
        assert [(m, h, p.split("?")[0]) for m, h, p, _ in transport.calls] == [
            ("GET", "api.au2.cliniko.com", "/v1/user"),
            ("GET", "api.au2.cliniko.com", "/v1/practitioners"),
            ("GET", "api.au2.cliniko.com", "/v1/settings/public"),
        ]
        assert transport.calls[1][2] == "/v1/practitioners?q%5B%5D=user_id%3A%3D1234567"

    def test_one_validate_is_one_call_under_one_key(self, tmp_path: Path) -> None:
        transport = ScriptedTransport()
        added(make_registry(tmp_path, transport))
        tokens = {headers["Authorization"] for *_, headers in transport.calls}
        assert tokens == {_token(KEY)}

    @pytest.mark.parametrize(
        "user",
        [
            {**USER, "role": "administrator"},
            {**USER, "role": "practitioner"},
            {**USER, "role": "receptionist"},
            {"id": "1234567", "active": True},
            {**USER, "role": 3},
        ],
        ids=["administrator", "practitioner", "receptionist", "no-role", "odd-role"],
    )
    def test_the_role_is_no_gate_one_active_record_decides(
        self, tmp_path: Path, user: dict[str, Any]
    ) -> None:
        """D10 as amended 2026-09-27 (practitioner decision after P.1): any
        active login with exactly one active practitioner record is accepted,
        whatever its role — the role field is never read."""
        record = added(make_registry(tmp_path, ScriptedTransport(user=ok(user))))
        assert record.practitioner_id == "7654321"

    def test_a_numeric_id_in_an_answer_is_accepted(self, tmp_path: Path) -> None:
        transport = ScriptedTransport(
            user=ok({**USER, "id": 1234567}),
            practitioners=ok({"practitioners": [{"id": 7654321, "active": True}]}),
        )
        record = added(make_registry(tmp_path, transport))
        assert (record.user_id, record.practitioner_id) == ("1234567", "7654321")

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"contact_email": "not an email"}, ClinicRefusal.EMAIL_INVALID),
            ({"contact_email": "a@b.com\r\nX-Evil: 1"}, ClinicRefusal.EMAIL_INVALID),
            ({"api_key": "no-shard-suffix"}, ClinicRefusal.KEY_FORMAT),
            ({"api_key": KEY[:-3] + "zz9"}, ClinicRefusal.KEY_FORMAT),
            ({"api_key": KEY + "\r\n"}, ClinicRefusal.KEY_FORMAT),
            # Draft-write Task 5.4 (R22-11): no key at all is its own refusal.
            ({"api_key": ""}, ClinicRefusal.KEY_MISSING),
            ({"api_key": "  \t\r\n"}, ClinicRefusal.KEY_MISSING),
            ({"api_key": " x "}, ClinicRefusal.KEY_FORMAT),
            ({"display_name": ""}, ClinicRefusal.NAME_INVALID),
            ({"display_name": None}, ClinicRefusal.NAME_INVALID),
            ({"display_name": "North\nside"}, ClinicRefusal.NAME_INVALID),
            ({"display_name": "x" * 61}, ClinicRefusal.NAME_INVALID),
            ({"typed_address": "http://northside.au2.cliniko.com"}, ClinicRefusal.ADDRESS_INVALID),
            ({"typed_address": "northside.au3.cliniko.com"}, ClinicRefusal.SHARD_MISMATCH),
        ],
    )
    def test_a_local_refusal_sends_nothing_and_stores_nothing(
        self, tmp_path: Path, overrides: dict[str, Any], reason: ClinicRefusal
    ) -> None:
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport, store)
        outcome = validate(registry, **overrides)
        assert outcome == Refused(reason)
        assert transport.calls == []
        assert store.keys == {}
        assert not (tmp_path / "clinics.json").exists()

    @pytest.mark.parametrize(
        ("transport", "reason"),
        [
            (ScriptedTransport(user=status(401)), ClinicRefusal.KEY_REJECTED),
            (ScriptedTransport(user=status(403)), ClinicRefusal.KEY_REJECTED),
            (ScriptedTransport(user=ok({**USER, "active": False})), ClinicRefusal.USER_INACTIVE),
            (
                ScriptedTransport(practitioners=ok({"practitioners": []})),
                ClinicRefusal.NO_PRACTITIONER_RECORD,
            ),
            (
                ScriptedTransport(
                    practitioners=ok(
                        {
                            "practitioners": [
                                {"id": "1", "active": True},
                                {"id": "2", "active": True},
                            ]
                        }
                    )
                ),
                ClinicRefusal.SEVERAL_PRACTITIONER_RECORDS,
            ),
            (
                ScriptedTransport(
                    practitioners=ok(
                        {
                            "practitioners": [
                                {"id": "1", "active": True},
                                {"id": "2", "active": False},
                            ]
                        }
                    )
                ),
                ClinicRefusal.SEVERAL_PRACTITIONER_RECORDS,
            ),
            (
                ScriptedTransport(
                    practitioners=ok({"practitioners": [{"id": "7654321", "active": False}]})
                ),
                ClinicRefusal.PRACTITIONER_INACTIVE,
            ),
            (
                ScriptedTransport(practitioners=ok({"practitioners": [{"id": "7654321"}]})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (
                ScriptedTransport(
                    practitioners=ok({"practitioners": [{"id": "7654321", "active": "yes"}]})
                ),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (ScriptedTransport(user=status(503)), ClinicRefusal.UNREACHABLE),
            (ScriptedTransport(public=status(500)), ClinicRefusal.UNREACHABLE),
            (ScriptedTransport(user=status(429)), ClinicRefusal.RATE_LIMITED),
            (ScriptedTransport(user=cc.Unreachable()), ClinicRefusal.UNREACHABLE),
            (ScriptedTransport(user=cc.CertificateRejected()), ClinicRefusal.CERTIFICATE_REJECTED),
            (ScriptedTransport(user=status(302)), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=status(418)), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=status(404)), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=cc.Malformed()), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=ok({"role": "practitioner"})), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=ok({**USER, "id": "0123"})), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=ok({**USER, "id": True})), ClinicRefusal.ANSWER_UNREADABLE),
            (
                ScriptedTransport(user=ok({**USER, "active": "yes"})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (
                ScriptedTransport(practitioners=ok({"practitioners": {"id": "1"}})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (
                ScriptedTransport(practitioners=ok({"practitioners": ["7654321"]})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (
                ScriptedTransport(public=ok({"account": {"subdomain": "api"}})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (
                ScriptedTransport(public=ok({"account": {"subdomain": "a.b"}})),
                ClinicRefusal.ANSWER_UNREADABLE,
            ),
            (ScriptedTransport(public=ok({"account": None})), ClinicRefusal.ANSWER_UNREADABLE),
            (ScriptedTransport(user=RuntimeError(KEY)), ClinicRefusal.ANSWER_UNREADABLE),
        ],
    )
    def test_each_answer_refusal_stores_nothing_and_carries_no_key(
        self, tmp_path: Path, transport: ScriptedTransport, reason: ClinicRefusal
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, transport, store)
        request = begin(registry)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        assert result == Refused(reason, request.clinic_id)
        assert registry.commit_validation(request, result) == result
        assert store.keys == {} and registry.records == ()
        assert not (tmp_path / "clinics.json").exists()
        for text in (repr(result), str(result), repr(request)):
            assert KEY not in text and KEY.split("-")[0] not in text

    @pytest.mark.parametrize("refused", [status(401), status(403), status(404)])
    def test_settings_refused_needs_a_typed_address(
        self, tmp_path: Path, refused: cc.RawResponse
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(public=refused), store)
        outcome = validate(registry)
        assert isinstance(outcome, Refused)
        assert outcome.reason is ClinicRefusal.ADDRESS_NEEDED
        assert store.keys == {} and registry.records == ()

    def test_the_typed_address_route_records_an_unconfirmed_subdomain(
        self, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(public=status(403)), store)
        record = added(registry, typed_address="https://northside.au2.cliniko.com/patients/1")
        assert record.host == "northside.au2.cliniko.com"
        assert record.subdomain_confirmed is False
        assert store.keys == {(IDS[0], KEY_SECRET_NAME): KEY}

    def test_a_typed_address_agreeing_with_cliniko_is_confirmed(self, tmp_path: Path) -> None:
        record = added(make_registry(tmp_path), typed_address="northside.au2.cliniko.com")
        assert record.subdomain_confirmed is True

    def test_a_typed_address_contradicting_cliniko_is_refused(self, tmp_path: Path) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        outcome = validate(registry, typed_address="southside.au2.cliniko.com")
        assert isinstance(outcome, Refused)
        assert outcome.reason is ClinicRefusal.ADDRESS_MISMATCH
        assert store.keys == {}

    def test_a_duplicate_subdomain_is_refused_at_commit(self, tmp_path: Path) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        first = added(registry)
        outcome = validate(registry, api_key=KEY_2, display_name="Again")
        assert outcome == Refused(ClinicRefusal.DUPLICATE_SUBDOMAIN, IDS[1])
        assert store.keys == {(first.clinic_id, KEY_SECRET_NAME): KEY}
        assert registry.records == (first,)

    def test_a_duplicate_typed_subdomain_is_refused_before_any_request(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport)
        added(registry)
        transport.calls.clear()
        outcome = validate(registry, api_key=KEY_2, typed_address="northside.au2.cliniko.com")
        assert outcome == Refused(ClinicRefusal.DUPLICATE_SUBDOMAIN)
        assert transport.calls == []

    def test_more_than_two_clinics_is_refused(self, tmp_path: Path) -> None:
        subdomains = iter(["northside", "southside", "eastside"])
        transport = ScriptedTransport(
            public=lambda: ok({"account": {"subdomain": next(subdomains)}})
        )
        registry = make_registry(tmp_path, transport)
        added(registry)
        added(registry, api_key=KEY_2, display_name="Southside")
        transport.calls.clear()
        assert validate(registry, api_key=KEY_3) == Refused(ClinicRefusal.TOO_MANY_CLINICS)
        assert transport.calls == []

    def test_the_request_repr_carries_no_key(self, tmp_path: Path) -> None:
        request = begin(make_registry(tmp_path))
        assert isinstance(request, ValidationRequest)
        assert KEY not in repr(request)
        assert request.api_key == KEY

    def test_a_worker_result_carries_no_key(self, tmp_path: Path) -> None:
        registry = make_registry(tmp_path)
        request = begin(registry)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        assert isinstance(result, ValidatedAccount)
        assert KEY not in repr(result) and KEY.split("-")[0] not in repr(result)


class TestNothingAtStartupOrIdle:
    def test_loading_and_reading_make_no_call_and_read_no_key(self, tmp_path: Path) -> None:
        write_file(tmp_path / "clinics.json", file_dict(record_dict()))
        store = MemoryKeyStore()
        transport = ScriptedTransport()
        registry = make_registry(tmp_path, transport, store)
        registry.allow_list()
        registry.records  # noqa: B018 - reading is the point
        registry.record(IDS[0])
        registry.rev(IDS[0])
        assert transport.calls == []
        assert store.reads == 0

    def test_the_module_never_logs(self) -> None:
        source = Path(clinics_module.__file__).read_text(encoding="utf-8")
        assert "import logging" not in source and "log_event" not in source


# ---------------------------------------------------------------------------
# Replace key, Remove, and clinic_rev (D9) — the mutation verification.
# ---------------------------------------------------------------------------


def _setup_one(
    tmp_path: Path, transport: Any = None
) -> tuple[ClinicRegistry, MemoryKeyStore, ClinicRecord]:
    store = MemoryKeyStore()
    registry = make_registry(tmp_path, transport or ScriptedTransport(), store)
    return registry, store, added(registry)


def _replace(registry: ClinicRegistry, clinic_id: str, key: str, **kw: Any) -> Any:
    return registry.begin_validation(
        api_key=key, contact_email=EMAIL, clinic_id=clinic_id, **kw
    )


class TestReplaceKey:
    def test_replace_stores_the_new_key_and_updates_the_record(self, tmp_path: Path) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.routes["/v1/practitioners"] = ok(
            {"practitioners": [{"id": "999", "active": True}]}
        )
        rev_before = registry.rev(record.clinic_id)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        assert registry.rev(record.clinic_id) == rev_before + 1  # bumped at dispatch
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert isinstance(outcome, Committed) and outcome.replaced
        assert outcome.record.practitioner_id == "999"
        assert outcome.record.display_name == "Northside"
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY_2}
        assert registry.rev(record.clinic_id) == rev_before + 2  # and at commit
        assert make_registry(tmp_path).records == (outcome.record,)

    def test_a_key_for_another_shard_is_refused_before_any_request(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.calls.clear()
        rev = registry.rev(record.clinic_id)
        outcome = _replace(registry, record.clinic_id, KEY_AU3)
        assert outcome == Refused(ClinicRefusal.DIFFERENT_ACCOUNT, record.clinic_id)
        assert transport.calls == [] and registry.rev(record.clinic_id) == rev
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}

    @pytest.mark.parametrize("key", ["", "   ", "\t\r\n"])
    def test_no_key_is_key_missing_before_any_request(self, tmp_path: Path, key: str) -> None:
        """Draft-write Task 5.4 (R22-11): Replace key names a missing key
        as Validate does — nothing sent, the rev and the stored key kept."""
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.calls.clear()
        rev = registry.rev(record.clinic_id)
        assert _replace(registry, record.clinic_id, key) == Refused(ClinicRefusal.KEY_MISSING)
        assert transport.calls == [] and registry.rev(record.clinic_id) == rev
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}

    def test_a_key_for_another_account_is_refused_and_the_old_key_kept(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.routes["/v1/settings/public"] = ok({"account": {"subdomain": "elsewhere"}})
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert outcome == Refused(ClinicRefusal.DIFFERENT_ACCOUNT, record.clinic_id)
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}
        assert registry.records == (record,)

    def test_a_typed_address_for_another_clinic_is_refused(self, tmp_path: Path) -> None:
        """Round 15 LOW-007: the typed ADDRESS is the mismatch, not the key."""
        registry, _, record = _setup_one(tmp_path)
        rev = registry.rev(record.clinic_id)
        outcome = _replace(
            registry, record.clinic_id, KEY_2, typed_address="southside.au2.cliniko.com"
        )
        assert outcome == Refused(ClinicRefusal.ADDRESS_MISMATCH, record.clinic_id)
        assert registry.rev(record.clinic_id) == rev

    def test_replace_on_the_typed_route_keeps_the_address_unconfirmed(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry, _, record = _setup_one(tmp_path, transport)
        assert record.subdomain_confirmed
        transport.routes["/v1/settings/public"] = status(403)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert isinstance(outcome, Committed)
        assert outcome.record.host == record.host
        assert outcome.record.subdomain_confirmed is False

    def test_replace_of_an_unknown_clinic_is_refused(self, tmp_path: Path) -> None:
        registry, _, _ = _setup_one(tmp_path)
        assert _replace(registry, "ffffffffffffffff", KEY_2) == Refused(
            ClinicRefusal.CLINIC_GONE, "ffffffffffffffff"
        )


class TestClinicRev:
    """D9 / Task 2.2's clinic-mutation verification: no delayed result
    restores verified eligibility, display data or a removed entry."""

    def test_a_delayed_replace_result_after_a_later_replace_is_dropped(
        self, tmp_path: Path
    ) -> None:
        registry, store, record = _setup_one(tmp_path)
        first = _replace(registry, record.clinic_id, KEY_2)
        second = _replace(registry, record.clinic_id, KEY_3)
        assert isinstance(first, ValidationRequest) and isinstance(second, ValidationRequest)
        first_result = registry.run_validation(first)
        second_result = registry.run_validation(second)
        assert isinstance(registry.commit_validation(second, second_result), Committed)
        assert registry.commit_validation(first, first_result) == Refused(
            ClinicRefusal.SUPERSEDED, record.clinic_id
        )
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY_3}

    def test_a_delayed_replace_result_after_remove_never_restores_the_clinic(
        self, tmp_path: Path
    ) -> None:
        registry, store, record = _setup_one(tmp_path)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        assert isinstance(registry.remove(record.clinic_id, live_session_clinic=None), Removed)
        # Named as gone, not merely superseded (round 16 LOW-011).
        outcome = registry.commit_validation(request, result)
        assert outcome == Refused(ClinicRefusal.CLINIC_GONE, record.clinic_id)
        assert registry.records == () and store.keys == {}
        assert make_registry(tmp_path).records == ()

    def test_a_delayed_refusal_after_remove_is_named_gone(self, tmp_path: Path) -> None:
        """Codex round 17 PR-LOW-070: a stale REFUSAL is named stale too,
        never shown as the current outcome."""
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.routes["/v1/user"] = status(401)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        assert result == Refused(ClinicRefusal.KEY_REJECTED, record.clinic_id)
        assert isinstance(registry.remove(record.clinic_id, live_session_clinic=None), Removed)
        assert registry.commit_validation(request, result) == Refused(
            ClinicRefusal.CLINIC_GONE, record.clinic_id
        )
        assert registry.records == () and store.keys == {}

    def test_a_delayed_refusal_after_a_later_replace_is_superseded(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.routes["/v1/user"] = status(401)
        first = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(first, ValidationRequest)
        result = registry.run_validation(first)
        assert result == Refused(ClinicRefusal.KEY_REJECTED, record.clinic_id)
        assert isinstance(_replace(registry, record.clinic_id, KEY_3), ValidationRequest)
        assert registry.commit_validation(first, result) == Refused(
            ClinicRefusal.SUPERSEDED, record.clinic_id
        )
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}

    def test_a_current_refusal_is_returned_unchanged(self, tmp_path: Path) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.routes["/v1/user"] = status(401)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        assert registry.commit_validation(request, result) == Refused(
            ClinicRefusal.KEY_REJECTED, record.clinic_id
        )
        assert registry.records == (record,)
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}

    def test_a_replace_landing_between_the_requests_of_a_call_drops_it(
        self, tmp_path: Path
    ) -> None:
        transport = ScriptedTransport()
        registry, store, record = _setup_one(tmp_path, transport)
        transport.calls.clear()
        in_flight = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(in_flight, ValidationRequest)
        landed: list[Any] = []

        def practitioners_then_replace() -> cc.RawResponse:
            landed.append(_replace(registry, record.clinic_id, KEY_3))
            return ok(PRACTITIONERS)

        transport.routes["/v1/practitioners"] = practitioners_then_replace
        result = registry.run_validation(in_flight)
        assert isinstance(result, ValidatedAccount)
        # The call read its key once: every request carried KEY_2, none KEY_3.
        assert {h["Authorization"] for *_, h in transport.calls} == {_token(KEY_2)}
        assert registry.commit_validation(in_flight, result) == Refused(
            ClinicRefusal.SUPERSEDED, record.clinic_id
        )
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}
        assert isinstance(landed[0], ValidationRequest)

    def test_a_delayed_new_clinic_result_is_refused_once_its_rev_moved(
        self, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        request = begin(registry)
        assert isinstance(request, ValidationRequest)
        result = registry.run_validation(request)
        registry._bump(request.clinic_id)  # any rev change since dispatch
        assert registry.commit_validation(request, result) == Refused(
            ClinicRefusal.SUPERSEDED, request.clinic_id
        )
        assert store.keys == {} and registry.records == ()

    def test_a_removed_clinic_id_is_never_minted_again(self, tmp_path: Path) -> None:
        store = MemoryKeyStore()
        ids = iter([IDS[0], IDS[0], IDS[1]])
        registry = ClinicRegistry(
            tmp_path / "clinics.json",
            storage=store,
            transport=ScriptedTransport(),
            clock=lambda: NOW,
            id_factory=lambda: next(ids),
        )
        record = added(registry)
        registry.remove(record.clinic_id, live_session_clinic=None)
        again = begin(registry)
        assert isinstance(again, ValidationRequest)
        assert again.clinic_id == IDS[1]


class TestRemove:
    def test_remove_deletes_the_key_and_the_record(self, tmp_path: Path) -> None:
        registry, store, record = _setup_one(tmp_path)
        rev = registry.rev(record.clinic_id)
        outcome = registry.remove(record.clinic_id, live_session_clinic=None)
        assert outcome == Removed(record)
        assert store.keys == {} and registry.records == () and registry.allow_list() == ()
        assert registry.rev(record.clinic_id) == rev + 1
        assert make_registry(tmp_path).records == ()

    def test_remove_is_refused_while_the_live_session_is_linked(self, tmp_path: Path) -> None:
        registry, store, record = _setup_one(tmp_path)
        rev = registry.rev(record.clinic_id)
        outcome = registry.remove(record.clinic_id, live_session_clinic=record.clinic_id)
        assert outcome == Refused(ClinicRefusal.LINKED_TO_LIVE_SESSION, record.clinic_id)
        assert registry.records == (record,) and registry.rev(record.clinic_id) == rev
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY}

    def test_removing_the_other_clinic_leaves_the_linked_one_alone(
        self, tmp_path: Path
    ) -> None:
        subdomains = iter(["northside", "southside"])
        transport = ScriptedTransport(
            public=lambda: ok({"account": {"subdomain": next(subdomains)}})
        )
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, transport, store)
        linked = added(registry)
        other = added(registry, api_key=KEY_2, display_name="Southside")
        rev = registry.rev(linked.clinic_id)
        assert registry.remove(other.clinic_id, live_session_clinic=linked.clinic_id) == Removed(
            other
        )
        assert registry.records == (linked,) and registry.rev(linked.clinic_id) == rev
        assert store.keys == {(linked.clinic_id, KEY_SECRET_NAME): KEY}

    def test_a_failed_key_delete_keeps_the_clinic(self, tmp_path: Path) -> None:
        registry, store, record = _setup_one(tmp_path)
        store.fail_delete = True
        outcome = registry.remove(record.clinic_id, live_session_clinic=None)
        assert outcome == Refused(ClinicRefusal.KEY_DELETE_FAILED, record.clinic_id)
        assert registry.records == (record,)

    def test_a_failed_rewrite_keeps_the_record_and_a_retry_finishes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, store, record = _setup_one(tmp_path)
        real_write = registry._write

        def failing(*_: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(registry, "_write", failing)
        outcome = registry.remove(record.clinic_id, live_session_clinic=None)
        assert outcome == Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, record.clinic_id)
        assert store.keys == {} and registry.records == (record,)
        monkeypatch.setattr(registry, "_write", real_write)
        assert registry.remove(record.clinic_id, live_session_clinic=None) == Removed(record)

    def test_removing_an_unknown_clinic_is_refused(self, tmp_path: Path) -> None:
        registry, _, _ = _setup_one(tmp_path)
        assert registry.remove("ffffffffffffffff", live_session_clinic=None) == Refused(
            ClinicRefusal.CLINIC_GONE, "ffffffffffffffff"
        )


class TestWriteOrder:
    def test_a_new_clinic_whose_file_write_fails_stores_no_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = MemoryKeyStore()
        registry = make_registry(tmp_path, ScriptedTransport(), store)

        def failing(*_: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(registry, "_write", failing)
        assert validate(registry) == Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, IDS[0])
        assert store.keys == {} and registry.records == ()

    def test_a_new_clinic_whose_key_store_fails_is_taken_off_the_list(
        self, tmp_path: Path
    ) -> None:
        store = MemoryKeyStore()
        store.fail_store = True
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        assert validate(registry) == Refused(ClinicRefusal.KEY_STORE_FAILED, IDS[0])
        assert registry.records == ()
        assert make_registry(tmp_path).records == ()

    def test_a_store_that_wrote_before_failing_leaves_no_unlisted_key(
        self, tmp_path: Path
    ) -> None:
        """Round 15 LOW-010: whatever a failed store wrote is deleted before
        the clinic is taken off the list."""
        store = MemoryKeyStore()
        store.fail_after_store = True
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        assert validate(registry) == Refused(ClinicRefusal.KEY_STORE_FAILED, IDS[0])
        assert store.keys == {} and registry.records == ()
        assert make_registry(tmp_path).records == ()

    def test_a_failed_cleanup_keeps_the_clinic_listed_for_remove(self, tmp_path: Path) -> None:
        store = MemoryKeyStore()
        store.fail_after_store = True
        store.fail_delete = True
        registry = make_registry(tmp_path, ScriptedTransport(), store)
        assert validate(registry) == Refused(ClinicRefusal.KEY_STORE_FAILED, IDS[0])
        # The key the store wrote is still at rest, so the clinic stays
        # listed (in memory and on disk) — Remove is the way to clear it.
        assert store.keys == {(IDS[0], KEY_SECRET_NAME): KEY}
        assert [r.clinic_id for r in registry.records] == [IDS[0]]
        assert [r.clinic_id for r in make_registry(tmp_path).records] == [IDS[0]]
        store.fail_delete = False
        assert isinstance(registry.remove(IDS[0], live_session_clinic=None), Removed)
        assert store.keys == {}

    def test_a_replace_whose_key_store_fails_keeps_the_record_and_moves_the_rev(
        self, tmp_path: Path
    ) -> None:
        registry, store, record = _setup_one(tmp_path)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        store.fail_store = True
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert outcome == Refused(ClinicRefusal.KEY_STORE_FAILED, record.clinic_id)
        assert registry.records == (record,)
        assert registry.rev(record.clinic_id) == request.rev + 1

    def test_a_replace_whose_file_write_fails_moves_the_rev(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, store, record = _setup_one(tmp_path)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)

        def failing(*_: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(registry, "_write", failing)
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert outcome == Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, record.clinic_id)
        assert store.keys == {(record.clinic_id, KEY_SECRET_NAME): KEY_2}
        assert registry.records == (record,)
        assert registry.rev(record.clinic_id) == request.rev + 1


class TestConfirmSubdomainFromNote:
    def _typed(self, tmp_path: Path) -> tuple[ClinicRegistry, ClinicRecord]:
        registry = make_registry(tmp_path, ScriptedTransport(public=status(403)))
        return registry, added(registry, typed_address="northside.au2.cliniko.com")

    def test_a_verified_note_confirms_a_typed_subdomain(self, tmp_path: Path) -> None:
        registry, record = self._typed(tmp_path)
        rev = registry.rev(record.clinic_id)
        assert registry.confirm_subdomain_from_note(record.clinic_id, record.host, rev)
        assert registry.records[0].subdomain_confirmed is True
        assert registry.rev(record.clinic_id) == rev  # confirming changes no identity
        assert make_registry(tmp_path).records[0].subdomain_confirmed is True

    def test_already_confirmed_is_true_and_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, _, record = _setup_one(tmp_path)
        monkeypatch.setattr(registry, "_write", lambda *_: pytest.fail("rewrote"))
        assert registry.confirm_subdomain_from_note(
            record.clinic_id, record.host, registry.rev(record.clinic_id)
        )

    def test_another_host_confirms_nothing(self, tmp_path: Path) -> None:
        registry, record = self._typed(tmp_path)
        rev = registry.rev(record.clinic_id)
        assert not registry.confirm_subdomain_from_note(
            record.clinic_id, "southside.au2.cliniko.com", rev
        )
        assert registry.records[0].subdomain_confirmed is False

    def test_a_verification_from_before_a_replace_confirms_nothing(
        self, tmp_path: Path
    ) -> None:
        registry, record = self._typed(tmp_path)
        rev = registry.rev(record.clinic_id)
        _replace(registry, record.clinic_id, KEY_2)
        assert not registry.confirm_subdomain_from_note(record.clinic_id, record.host, rev)
        assert registry.records[0].subdomain_confirmed is False

    def test_a_verification_after_remove_never_restores_the_clinic(
        self, tmp_path: Path
    ) -> None:
        registry, record = self._typed(tmp_path)
        rev = registry.rev(record.clinic_id)
        registry.remove(record.clinic_id, live_session_clinic=None)
        assert not registry.confirm_subdomain_from_note(record.clinic_id, record.host, rev)
        assert registry.records == ()
        assert make_registry(tmp_path).records == ()

    def test_a_failed_write_leaves_it_unconfirmed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, record = self._typed(tmp_path)

        def failing(*_: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(registry, "_write", failing)
        assert not registry.confirm_subdomain_from_note(
            record.clinic_id, record.host, registry.rev(record.clinic_id)
        )
        assert registry.records[0].subdomain_confirmed is False


# ---------------------------------------------------------------------------
# Cliniko draft-write plan Task 3.1a (D14): the per-clinic default source.
# ---------------------------------------------------------------------------


class TestDefaultSource:
    def test_a_file_written_before_the_setting_loads_as_cliniko_template(
        self, tmp_path: Path
    ) -> None:
        write_file(tmp_path / "clinics.json", file_dict(record_dict()))
        registry = make_registry(tmp_path)
        assert registry.load_problem is None
        assert registry.records[0].default_source == "cliniko_template"

    def test_an_unknown_value_fails_closed(self, tmp_path: Path) -> None:
        write_file(tmp_path / "clinics.json", file_dict(record_dict(default_source="elsewhere")))
        registry = make_registry(tmp_path)
        assert registry.load_problem is LoadProblem.NOT_VALID
        assert registry.records == ()

    def test_a_new_clinic_starts_at_cliniko_template_and_the_default_is_not_written(
        self, tmp_path: Path
    ) -> None:
        registry, _, record = _setup_one(tmp_path)
        assert record.default_source == "cliniko_template"
        saved = json.loads((tmp_path / "clinics.json").read_text(encoding="utf-8"))
        assert "default_source" not in saved["clinics"][0]

    def test_the_setting_round_trips_through_the_file(self, tmp_path: Path) -> None:
        registry, _, record = _setup_one(tmp_path)
        rev = registry.rev(record.clinic_id)
        changed = registry.set_default_source(record.clinic_id, "own_file", writing_clinic=None)
        assert isinstance(changed, ClinicRecord)
        assert changed.default_source == "own_file"
        assert changed.model_copy(update={"default_source": "cliniko_template"}) == record
        assert registry.records == (changed,)
        saved = json.loads((tmp_path / "clinics.json").read_text(encoding="utf-8"))
        assert saved["clinics"][0]["default_source"] == "own_file"
        assert make_registry(tmp_path).records == (changed,)
        # Back to the default: the field leaves the file again (R22-24).
        back = registry.set_default_source(
            record.clinic_id, "cliniko_template", writing_clinic=None
        )
        assert back == record
        saved = json.loads((tmp_path / "clinics.json").read_text(encoding="utf-8"))
        assert "default_source" not in saved["clinics"][0]
        assert make_registry(tmp_path).records == (record,)
        # It changes no identity a pending result depends on.
        assert registry.rev(record.clinic_id) == rev

    def test_the_same_value_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, _, record = _setup_one(tmp_path)
        monkeypatch.setattr(registry, "_write", lambda *_: pytest.fail("rewrote"))
        assert (
            registry.set_default_source(
                record.clinic_id, "cliniko_template", writing_clinic=record.clinic_id
            )
            == record
        )

    def test_an_invalid_source_raises_before_anything_is_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        registry, _, record = _setup_one(tmp_path)
        monkeypatch.setattr(registry, "_write", lambda *_: pytest.fail("rewrote"))
        with pytest.raises(ValueError, match="default source"):
            registry.set_default_source(
                record.clinic_id,
                "elsewhere",  # type: ignore[arg-type]
                writing_clinic=None,
            )
        assert registry.records == (record,)

    def test_refused_while_a_write_is_in_flight_for_that_clinic(self, tmp_path: Path) -> None:
        registry, _, record = _setup_one(tmp_path)
        before = (tmp_path / "clinics.json").read_bytes()
        outcome = registry.set_default_source(
            record.clinic_id, "own_file", writing_clinic=record.clinic_id
        )
        assert outcome == Refused(ClinicRefusal.WRITE_IN_FLIGHT, record.clinic_id)
        assert registry.records == (record,)
        assert (tmp_path / "clinics.json").read_bytes() == before
        # A write for ANOTHER clinic does not refuse it.
        assert isinstance(
            registry.set_default_source(
                record.clinic_id, "own_file", writing_clinic="fedcba9876543210"
            ),
            ClinicRecord,
        )

    def test_refused_for_a_gone_clinic(self, tmp_path: Path) -> None:
        registry, _, _ = _setup_one(tmp_path)
        assert registry.set_default_source(
            "ffffffffffffffff", "own_file", writing_clinic=None
        ) == Refused(ClinicRefusal.CLINIC_GONE, "ffffffffffffffff")

    def test_refused_when_the_file_was_found_damaged(self, tmp_path: Path) -> None:
        path = tmp_path / "clinics.json"
        path.write_bytes(b"{damaged")
        registry = make_registry(tmp_path)
        assert registry.set_default_source(IDS[0], "own_file", writing_clinic=None) == Refused(
            ClinicRefusal.REGISTRY_UNREADABLE, IDS[0]
        )
        assert path.read_bytes() == b"{damaged"

    @pytest.mark.parametrize(
        "failure",
        # Round 26 LOW-010: the atomic writer's own failure is not an OSError.
        [OSError("disk full"), StoreWriteError("clinics file write failed")],
    )
    def test_a_failed_write_leaves_the_setting_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
    ) -> None:
        registry, _, record = _setup_one(tmp_path)
        before = (tmp_path / "clinics.json").read_bytes()

        def failing(*_: Any) -> None:
            raise failure

        monkeypatch.setattr(registry, "_write", failing)
        outcome = registry.set_default_source(record.clinic_id, "own_file", writing_clinic=None)
        assert outcome == Refused(ClinicRefusal.REGISTRY_WRITE_FAILED, record.clinic_id)
        assert registry.records == (record,)
        assert (tmp_path / "clinics.json").read_bytes() == before

    def test_a_pending_verification_still_matches_after_a_change(self, tmp_path: Path) -> None:
        """No rev bump: a verification dispatched before the change still
        confirms the subdomain after it."""
        registry = make_registry(tmp_path, ScriptedTransport(public=status(403)))
        record = added(registry, typed_address="northside.au2.cliniko.com")
        rev = registry.rev(record.clinic_id)
        registry.set_default_source(record.clinic_id, "own_file", writing_clinic=None)
        assert registry.confirm_subdomain_from_note(record.clinic_id, record.host, rev)
        (confirmed,) = registry.records
        assert confirmed.subdomain_confirmed and confirmed.default_source == "own_file"

    def test_replace_key_keeps_own_file(self, tmp_path: Path) -> None:
        registry, _, record = _setup_one(tmp_path)
        registry.set_default_source(record.clinic_id, "own_file", writing_clinic=None)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        outcome = registry.commit_validation(request, registry.run_validation(request))
        assert isinstance(outcome, Committed)
        assert outcome.record.default_source == "own_file"
        assert make_registry(tmp_path).records[0].default_source == "own_file"

    @pytest.mark.parametrize(
        ("before", "during"), [("cliniko_template", "own_file"), ("own_file", "cliniko_template")]
    )
    def test_a_change_made_while_a_replace_is_in_flight_is_kept(
        self, tmp_path: Path, before: Any, during: Any
    ) -> None:
        """D14: the Replace carries the record AS IT IS AT COMMIT, not the one
        it captured at dispatch."""
        registry, _, record = _setup_one(tmp_path)
        registry.set_default_source(record.clinic_id, before, writing_clinic=None)
        request = _replace(registry, record.clinic_id, KEY_2)
        assert isinstance(request, ValidationRequest)
        assert request.expected is not None and request.expected.default_source == before
        result = registry.run_validation(request)
        registry.set_default_source(record.clinic_id, during, writing_clinic=None)
        outcome = registry.commit_validation(request, result)
        assert isinstance(outcome, Committed)
        assert outcome.record.default_source == during
        assert make_registry(tmp_path).records[0].default_source == during
