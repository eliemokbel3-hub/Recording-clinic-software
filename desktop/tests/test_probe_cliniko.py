"""Cliniko workflow safeguards plan, Task 1.3: the read-only feasibility probe.

``scripts/probe-cliniko.py`` is loaded through ``importlib`` (hyphenated,
outside any package) and driven end to end through its ``main`` with injected
prompts and a fake transport answering fixture responses that carry names,
ids, answer text, a phone number, a date of birth, the subdomain, the email and
the key. The pin: the printed output carries NONE of them — only statuses,
field names, value kinds and yes/no facts — and the key is read once, through
the secret prompt only. No socket is opened; Cliniko is never contacted.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

from scribe_desktop import cliniko_client as cc

REPO = Path(__file__).resolve().parents[2]
KEY = "MS0xMjM0NTY3ODkwLXByb2JlLWtleQ-au2"
EMAIL = "probe.owner@example-clinic.com.au"
NOTE_ID = "918273645"
PATIENT_ID = "564738291"
USER_ID = "4455667788"
PRACTITIONER_ID = "1122334455"
BOOKING_ID = "99887766"
TEMPLATE_ID = "55443322"
URL = (
    f"https://sunnyclinic.au2.cliniko.com/patients/{PATIENT_ID}"
    f"/treatment_notes/{NOTE_ID}/edit?page=1"
)
API = "https://api.au2.cliniko.com/v1"

FIXTURES: dict[str, object] = {
    "/v1/user": {
        "id": USER_ID,
        "first_name": "Zanzibar",
        "last_name": "Quixotic",
        "email": "zanzibar.q@sunnyclinic.example",
        "role": "practitioner",
        "active": True,
        "links": {"self": f"{API}/users/{USER_ID}"},
    },
    f"/v1/practitioners?q%5B%5D=user_id%3A%3D{USER_ID}": {
        "practitioners": [
            {
                "id": PRACTITIONER_ID,
                "first_name": "Zanzibar",
                "user": {"links": {"self": f"{API}/users/{USER_ID}"}},
            }
        ],
        "total_entries": 1,
    },
    "/v1/settings/public": {"account": {"subdomain": "sunnyclinic", "name": "Sunny Physio"}},
    "/v1/settings": {"account": {"country": "Australia", "time_zone": "Australia/Sydney"}},
    f"/v1/treatment_notes/{NOTE_ID}": {
        "id": NOTE_ID,
        "draft": True,
        "finalized_at": None,
        "title": "Initial consult",
        "Weird Key 1": "oddvalue9",
        "content": {
            "sections": [
                {
                    "name": "Subjective",
                    "questions": [
                        {
                            "name": "Presenting complaint",
                            "type": "text",
                            "answer": "Left knee pain since Tuesday after netball",
                        },
                        {"name": "Pain scale", "type": "text", "answer": ""},
                        {
                            "name": "Side",
                            "type": "radiobuttons",
                            "answers": [
                                {"value": "Left", "selected": True},
                                {"value": "Right"},
                            ],
                        },
                    ],
                }
            ]
        },
        "patient": {"links": {"self": f"{API}/patients/{PATIENT_ID}"}},
        "practitioner": {"links": {"self": f"{API}/practitioners/{PRACTITIONER_ID}"}},
        "booking": {"links": {"self": f"{API}/bookings/{BOOKING_ID}"}},
        "treatment_note_template": {
            "links": {"self": f"{API}/treatment_note_templates/{TEMPLATE_ID}"}
        },
    },
    f"/v1/patients/{PATIENT_ID}": {
        "id": PATIENT_ID,
        "first_name": "Wilhelmina",
        "last_name": "Fotheringay",
        "date_of_birth": "1981-02-03",
        "patient_phone_numbers": [{"number": "0412345678", "phone_type": "Mobile"}],
    },
    f"/v1/bookings/{BOOKING_ID}": {
        "id": BOOKING_ID,
        "starts_at": "2026-09-27T01:30:00Z",
        "patient_name": "Wilhelmina Fotheringay",
    },
}

SECRETS = (
    KEY,
    KEY.split("-")[0],
    base64.b64encode(f"{KEY}:".encode()).decode(),
    EMAIL,
    URL,
    "sunnyclinic",
    "Sunny Physio",
    "Zanzibar",
    "Quixotic",
    "Wilhelmina",
    "Fotheringay",
    "Left knee",
    "netball",
    "0412345678",
    "1981-02-03",
    "2026-09-27T01:30",
    "Australia/Sydney",
    "Initial consult",
    "Presenting complaint",
    "Subjective",
    "Weird Key",
    "oddvalue9",
    NOTE_ID,
    PATIENT_ID,
    USER_ID,
    PRACTITIONER_ID,
    BOOKING_ID,
    TEMPLATE_ID,
)


class RouteTransport:
    """Answers each path from ``routes`` (a status override per path)."""

    def __init__(
        self, fixtures: Mapping[str, object], statuses: Mapping[str, int] | None = None
    ) -> None:
        self._fixtures = fixtures
        self._statuses = dict(statuses or {})
        self.calls: list[tuple[str, str, str]] = []

    def request(
        self, method: str, host: str, path: str, headers: Mapping[str, str], max_body: int
    ) -> cc.RawResponse:
        self.calls.append((method, host, path))
        status = self._statuses.get(path, 200 if path in self._fixtures else 404)
        body = json.dumps(self._fixtures.get(path, {})).encode()
        return cc.RawResponse(status, None, body)


@pytest.fixture(scope="module")
def probe() -> ModuleType:
    path = REPO / "scripts" / "probe-cliniko.py"
    spec = importlib.util.spec_from_file_location("probe_cliniko", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(
    probe: ModuleType,
    transport: RouteTransport,
    *,
    email: str = EMAIL,
    url: str = URL,
    key: str = KEY,
) -> tuple[int, list[str], list[str]]:
    lines: list[str] = []
    answers = [email, url]
    secret_prompts: list[str] = []

    def read_secret(prompt: str) -> str:
        secret_prompts.append(prompt)
        return key

    code = probe.main(
        [],
        read_line=lambda prompt: answers.pop(0),
        read_secret=read_secret,
        out=lines.append,
        transport=transport,
    )
    return code, lines, secret_prompts


def _assert_no_secret(lines: list[str]) -> None:
    printed = "\n".join(lines)
    for secret in SECRETS:
        assert secret not in printed, secret


class TestRedaction:
    def test_the_output_is_structure_only(self, probe: ModuleType) -> None:
        transport = RouteTransport(FIXTURES)
        code, lines, prompts = _run(probe, transport)
        assert code == 0
        _assert_no_secret(lines)
        assert len(prompts) == 1  # the key is read once, through the secret prompt
        for expected in (
            "Key shard equals the note URL's shard: yes",
            "GET /user: 200",
            "  role: practitioner",
            "  active: yes",
            "GET /practitioners?q[]=user_id:=<id>: 200",
            "  practitioner records for this user: 1",
            "GET /settings/public: 200",
            "  /settings/public answered: yes",
            "  account.subdomain present: yes",
            "  subdomain matches the note URL's: yes",
            "GET /settings: 200",
            "GET /treatment_notes/<id>: 200",
            "  draft: true",
            "  finalized_at: null",
            "  patient link present: yes",
            "  practitioner link present: yes",
            "  booking link present: yes",
            "  treatment_note_template link present: yes",
            "  patient link equals the URL's patient: yes",
            "  note practitioner is the key user's practitioner: yes",
            "GET /patients/<id>: 200",
            "GET /bookings/<id>: 200",
            "  starts_at present: yes",
        ):
            assert expected in lines, expected
        printed = "\n".join(lines)
        assert '"answer": "<text>"' in printed  # the answer reduced to non-empty
        assert '"answer": "<empty>"' in printed
        assert '"<key>": "<text>"' in printed  # a data-shaped key is not printed
        assert {c[0] for c in transport.calls} == {"GET"}
        assert {c[1] for c in transport.calls} == {"api.au2.cliniko.com"}

    def test_a_refused_call_prints_its_class_and_status_only(self, probe: ModuleType) -> None:
        transport = RouteTransport(FIXTURES, statuses={"/v1/settings/public": 403})
        code, lines, _prompts = _run(probe, transport)
        assert code == 0
        assert "GET /settings/public: CredentialsRejected (HTTP 403)" in lines
        assert "  /settings/public answered: no" in lines
        _assert_no_secret(lines)

    def test_a_note_without_a_booking_skips_it(self, probe: ModuleType) -> None:
        fixtures = dict(FIXTURES)
        note = dict(fixtures[f"/v1/treatment_notes/{NOTE_ID}"])
        note["booking"] = None
        note["practitioner"] = {"links": {"self": f"{API}/practitioners/777"}}
        note["draft"] = False
        note["finalized_at"] = "2026-09-27T02:00:00Z"
        fixtures[f"/v1/treatment_notes/{NOTE_ID}"] = note
        code, lines, _prompts = _run(probe, RouteTransport(fixtures))
        assert code == 0
        assert "GET /bookings/<id>: skipped (the note links no booking)" in lines
        assert "  booking link present: no" in lines
        assert "  draft: false" in lines
        assert "  finalized_at: set" in lines
        assert "  note practitioner is the key user's practitioner: no" in lines
        _assert_no_secret(lines)

    def test_a_role_that_is_not_a_plain_word_prints_as_its_kind(
        self, probe: ModuleType
    ) -> None:
        fixtures = dict(FIXTURES)
        fixtures["/v1/user"] = {**FIXTURES["/v1/user"], "role": "Dr Zanzibar"}
        code, lines, _prompts = _run(probe, RouteTransport(fixtures))
        assert code == 0
        assert "  role: <text>" in lines
        _assert_no_secret(lines)


class TestNothingSent:
    def test_a_bad_url_sends_nothing_and_is_not_echoed(self, probe: ModuleType) -> None:
        transport = RouteTransport(FIXTURES)
        bad = f"https://sunnyclinic.au2.cliniko.com/patients/{PATIENT_ID}/appointments"
        code, lines, prompts = _run(probe, transport, url=bad)
        assert code == 2
        assert transport.calls == [] and prompts == []  # asked for no key either
        assert bad not in "\n".join(lines)

    @pytest.mark.parametrize("key", ["MS0xMjM0NTY3ODkw-zz9", "no-suffix-key", ""])
    def test_an_unusable_key_sends_nothing(self, probe: ModuleType, key: str) -> None:
        transport = RouteTransport(FIXTURES)
        code, lines, _prompts = _run(probe, transport, key=key)
        assert code == 2
        assert transport.calls == []
        if key:
            assert key not in "\n".join(lines)

    def test_a_bad_email_sends_nothing(self, probe: ModuleType) -> None:
        transport = RouteTransport(FIXTURES)
        code, lines, prompts = _run(probe, transport, email="a@b.co\r\nX: 1")
        assert code == 2
        assert transport.calls == [] and prompts == []

    @pytest.mark.parametrize(
        "argv",
        [[KEY], [f"--key={KEY}"], ["-k", KEY], ["--help", KEY], [EMAIL, URL]],
        ids=["positional", "option-equals", "option-pair", "help-plus-key", "email-and-url"],
    )
    def test_an_argument_is_refused_without_echoing_it(
        self, probe: ModuleType, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Codex round 8 PR-MED-011: argparse's default rejection printed an
        unknown argument verbatim to stderr, so a key passed as an argument
        was echoed. The refusal is a fixed sentence, before argparse."""
        transport = RouteTransport(FIXTURES)
        asked: list[str] = []

        def ask(prompt: str) -> str:
            asked.append(prompt)
            return ""

        code = probe.main(
            argv, read_line=ask, read_secret=ask, out=print, transport=transport
        )
        assert code == 2
        assert asked == [] and transport.calls == []
        captured = capsys.readouterr()
        for text in (captured.out, captured.err):
            for secret in (KEY, KEY.split("-")[0], EMAIL, URL):
                assert secret not in text
        assert "takes no arguments" in captured.out

    def test_help_alone_still_prints_the_help(
        self, probe: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as info:
            probe.main(["--help"], read_line=lambda p: "", read_secret=lambda p: "", out=print)
        assert info.value.code == 0
        assert "getpass" in capsys.readouterr().out


class TestShape:
    def test_leaves_reduce_to_their_kind(self, probe: ModuleType) -> None:
        assert probe.shape(
            {"a": "x", "b": "", "c": 3, "d": 1.5, "e": True, "f": None, "G h": "y"}
        ) == {
            "a": "<text>",
            "b": "<empty>",
            "c": "<number>",
            "d": "<number>",
            "e": "<bool>",
            "f": None,
            "<key>": "<text>",
        }

    def test_lists_show_length_and_distinct_shapes(self, probe: ModuleType) -> None:
        assert probe.shape(["a", "b", "", 1]) == {
            "<items>": 4,
            "<shapes>": ["<text>", "<empty>", "<number>"],
        }

    def test_depth_is_capped(self, probe: ModuleType) -> None:
        deep: object = "leaf"
        for _ in range(40):
            deep = {"k": deep}
        rendered = json.dumps(probe.shape(deep))
        assert "<deep>" in rendered and "leaf" not in rendered

    def test_the_url_parser_takes_only_a_note_page(self, probe: ModuleType) -> None:
        target = probe.parse_note_url(URL)
        assert (target.subdomain, target.shard, target.patient_id, target.note_id) == (
            "sunnyclinic",
            "au2",
            PATIENT_ID,
            NOTE_ID,
        )
        for bad in (
            "http://sunnyclinic.au2.cliniko.com/patients/1/treatment_notes/2",
            "https://evil.example.com/patients/1/treatment_notes/2",
            "https://sunnyclinic.au2.cliniko.com.evil.example/patients/1/treatment_notes/2",
            "https://sunnyclinic.au2.cliniko.com/patients/01/treatment_notes/2",
            "https://sunnyclinic.au2.cliniko.com/appointments?calendar_start_date=2026-09-27",
        ):
            assert probe.parse_note_url(bad) is None, bad
