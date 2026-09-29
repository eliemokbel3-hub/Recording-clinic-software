"""Cliniko workflow safeguards plan, Task 1.3: the read-only feasibility probe;
cliniko-draft-write plan, Task 1.2: its ``--test-write`` and
``--test-write-final`` modes.

``scripts/probe-cliniko.py`` is loaded through ``importlib`` (hyphenated,
outside any package) and driven end to end through its ``main`` with injected
prompts and a fake transport answering fixture responses that carry names,
ids, answer text, a phone number, a date of birth, the subdomain, the email and
the key. The pin: the printed output carries NONE of them — only statuses,
field names, value kinds and yes/no facts — and the key is read once, through
the secret prompt only. No socket is opened; Cliniko is never contacted.

The test-write legs run against ``NoteServer``, a fake that keeps ONE note
and applies each PATCH to it (replacing ``content`` whole, or merging a
partial one by section and question name); the practitioner's editor actions
at each pause are callables in the prompt queue that change that note.
"""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

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
        self,
        method: str,
        host: str,
        path: str,
        headers: Mapping[str, str],
        max_body: int,
        *,
        body: bytes | None = None,
    ) -> cc.RawResponse:
        assert body is None, "the read-only probe sends no body"
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


# --- the test write (draft-write plan, Task 1.2) ---------------------------------

NOTE_PATH = f"/v1/treatment_notes/{NOTE_ID}"
TEMPLATE_PATH = f"/v1/treatment_note_templates/{TEMPLATE_ID}"
SURNAME = "Fotheringay"
DIGITS = NOTE_ID[-4:]
SCAFFOLD = "Site - Chron - Sensory -"
SENTINEL = "Wilhelmina sentinel phrase"
WRITE_SECRETS = (*SECRETS, DIGITS, SCAFFOLD, SENTINEL, "sentinel", "edited by hand")
RICH = (0, 0)  # section 1, question 1: the first paragraph question
PLAIN = (0, 1)  # section 1, question 2: the first text question
OTHER = (1, 0)  # section 2, question 1: an untargeted paragraph question
TEMPLATE: dict[str, Any] = {
    "id": TEMPLATE_ID,
    "name": "Initial consult",
    "content": {
        "sections": [
            {
                "name": "Subjective",
                "questions": [
                    {"name": "Presenting complaint", "type": "paragraph", "answer": SCAFFOLD},
                    {"name": "Pain scale", "type": "text"},
                ],
            }
        ]
    },
}


def _write_note(**changes: Any) -> dict[str, Any]:
    note = copy.deepcopy(FIXTURES[NOTE_PATH])
    assert isinstance(note, dict)
    note["content"] = {
        "sections": [
            {
                "name": "Subjective",
                "questions": [
                    {
                        "name": "Presenting complaint",
                        "type": "paragraph",
                        "answer": "<p>Left knee pain since Tuesday after netball</p>",
                    },
                    {"name": "Pain scale", "type": "text", "answer": ""},
                    {
                        "name": "Side",
                        "type": "radiobuttons",
                        "answers": [{"value": "Left", "selected": True}, {"value": "Right"}],
                    },
                ],
            },
            {
                "name": "Objective",
                "questions": [
                    {
                        "name": "Findings",
                        "type": "paragraph",
                        "answer": "<p>Wilhelmina swelling</p>",
                    }
                ],
            },
        ]
    }
    note.update(changes)
    return note


class NoteServer:
    """One Cliniko note that each PATCH changes: ``content`` replaced whole,
    or (``merge=True``) each sent question replaced by section and question
    name. ``patch_answers`` overrides PATCH answers in order (``None`` =
    apply normally); ``fail_reads_after`` answers every note GET with a 503
    once that many PATCHes were sent; every other path answers from
    ``FIXTURES``."""

    def __init__(
        self,
        note: dict[str, Any],
        *,
        merge: bool = False,
        patch_answers: tuple[cc.RawResponse | None, ...] = (),
        fail_reads_after: int | None = None,
    ) -> None:
        self.note = note
        self.merge = merge
        self._patch_answers = list(patch_answers)
        self._fail_reads_after = fail_reads_after
        self.calls: list[tuple[str, str, str]] = []
        self.patches: list[dict[str, Any]] = []

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
        self.calls.append((method, host, path))
        if method == "PATCH":
            assert path == NOTE_PATH and body is not None
            assert headers["Content-Type"] == "application/json"
            sent = json.loads(body.decode("utf-8"))
            assert list(sent) == ["content"]
            self.patches.append(sent["content"])
            if self._patch_answers:
                answer = self._patch_answers.pop(0)
                if answer is not None:
                    return answer
            self._apply(sent["content"])
            return cc.RawResponse(200, None, json.dumps(self.note).encode())
        assert method == "GET" and body is None
        if path == NOTE_PATH:
            if self._fail_reads_after is not None and self.patch_count >= self._fail_reads_after:
                return cc.RawResponse(503, None, b"")
            return cc.RawResponse(200, None, json.dumps(self.note).encode())
        if path == TEMPLATE_PATH:
            return cc.RawResponse(200, None, json.dumps(TEMPLATE).encode())
        status = 200 if path in FIXTURES else 404
        return cc.RawResponse(status, None, json.dumps(FIXTURES.get(path, {})).encode())

    def _apply(self, content: dict[str, Any]) -> None:
        if not self.merge:
            self.note["content"] = copy.deepcopy(content)
            return
        for sent_section in content["sections"]:
            section = next(
                s for s in self.note["content"]["sections"] if s["name"] == sent_section["name"]
            )
            for sent_question in sent_section["questions"]:
                index = next(
                    i
                    for i, q in enumerate(section["questions"])
                    if q["name"] == sent_question["name"]
                )
                section["questions"][index] = copy.deepcopy(sent_question)

    def answer(self, position: tuple[int, int]) -> Any:
        section, question = position
        return self.note["content"]["sections"][section]["questions"][question].get("answer")

    def edit(self, *changes: tuple[tuple[int, int], str]) -> Callable[[str], str]:
        """An editor action at a pause: set these answers, then press Enter."""

        def act(prompt: str) -> str:
            for (section, question), text in changes:
                self.note["content"]["sections"][section]["questions"][question]["answer"] = text
            return ""

        return act

    @property
    def patch_count(self) -> int:
        return sum(1 for c in self.calls if c[0] == "PATCH")


Step = str | Callable[[str], str]


def _run_write(
    probe: ModuleType,
    server: NoteServer,
    steps: list[Step],
    *,
    mode: str = "--test-write",
    surname: str = SURNAME,
    digits: str = DIGITS,
) -> tuple[int, list[str]]:
    lines: list[str] = []
    answers: list[Step] = [EMAIL, URL, surname, digits, *steps]

    def read_line(prompt: str) -> str:
        item = answers.pop(0)
        return item(prompt) if callable(item) else item

    code = probe.main(
        [mode], read_line=read_line, read_secret=lambda prompt: KEY, out=lines.append,
        transport=server,
    )
    printed = "\n".join(lines)
    for secret in WRITE_SECRETS:
        assert secret not in printed, secret
    return code, lines


def _original() -> dict[str, Any]:
    return copy.deepcopy(_write_note()["content"])


LOCKED_LINE = (
    "The note is finalised or archived: if Cliniko will not let you delete the "
    "marker, archive the note."
)


class TestTestWrite:
    def test_the_marker_body_is_escaped_rich_text_and_joined_plain_text(
        self, probe: ModuleType
    ) -> None:
        assert probe.MARKER_TEXT == (
            "Clinic Scribe test write - delete this text: a < b & \"c\" 'd' é"
        )
        assert probe.rich_answer(probe.MARKER_LINES) == (
            "<p>Clinic Scribe test write - delete this text: a &lt; b &amp; &quot;c&quot; "
            "&#x27;d&#x27; é</p><p>Clinic Scribe test write - second line</p><p></p>"
        )
        assert probe.plain_answer(probe.MARKER_LINES) == (
            f"{probe.MARKER_TEXT}\nClinic Scribe test write - second line\n"
        )

    def test_a_full_run_on_a_merging_server_restores_the_note(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note(), merge=True)
        original = _original()
        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                "",  # question 5: the editor saved nothing new
                server.edit((OTHER, "<p>edited by hand 1</p>"), (RICH, "<p>edited by hand 2</p>")),
                server.edit((OTHER, "<p>edited by hand 3</p>")),
                server.edit((OTHER, original["sections"][1]["questions"][0]["answer"])),
            ],
        )
        assert code == 0
        assert probe.MARKER_LEFT not in lines
        assert server.note["content"] == original
        assert server.patch_count == 4  # marker, full pass, partial pass, restore
        first = server.patches[0]
        assert first["sections"][0]["questions"][0]["answer"] == probe.rich_answer(
            probe.MARKER_LINES
        )
        assert first["sections"][0]["questions"][1]["answer"] == probe.plain_answer(
            probe.MARKER_LINES
        )
        assert first["sections"][0]["questions"][2] == original["sections"][0]["questions"][2]
        assert first["sections"][1] == original["sections"][1]
        assert server.patches[2] == {
            "sections": [
                {
                    "name": "Subjective",
                    "questions": [
                        {**original["sections"][0]["questions"][0],
                         "answer": probe.rich_answer(probe.PARTIAL_MARKER_LINES)}
                    ],
                }
            ]
        }
        assert server.patches[3] == original
        for expected in (
            "  note section 1, question 1: paragraph, answer <text>",
            "  note section 1, question 2: text, answer <empty>",
            "  note section 1, question 3: radiobuttons, answer choices",
            "GET /treatment_note_templates/<id>: 200",
            "  template section 1, question 1: paragraph, default answer <text>",
            "  template section 1, question 2: text, default answer absent",
            "PATCH /treatment_notes/<id> (test marker): 200",
            "  rich-text question (section 1, question 1): equal",
            "  plain-text question (section 1, question 2): equal",
            "  every other question byte-identical: yes",
            "  every other question visibly identical: yes",
            "  marker still present in the rich-text question after the editor save: yes",
            "  edits seen before the write: another question yes; "
            "the rich-text test question yes",
            "  the other question's edit survived the write: no",
            "  the rich-text test question's edit survived the write: no (expected: no)",
            "  the other question's edit survived the write: yes",
            "  Cliniko kept every other question as it was: yes",
            "  the partial write's own marker read back at the test question: yes",
            "  the test question's section holds other questions: yes",
            # The only shared-section paragraph here is the note's first
            # question, where the partial body puts it anyway on BOTH array
            # levels (round 11 MED-001, codex round 12 PR-MED-028).
            "  partial content (question 2): MERGED (not ruled out: sections matched by "
            "position; questions matched by position)",
            "  every other question reads as at the start: yes",
            "  the rich-text test question held only a marker or its original answer: yes",
            "  the plain-text test question held only a marker or its original answer: yes",
            "Restored the original content.",
        ):
            assert expected in lines, expected

    def test_a_replacing_server_leaves_the_marker_and_says_so(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note())
        original = _original()
        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                # Question 5: the open editor saved its stale copy over the marker.
                server.edit((RICH, original["sections"][0]["questions"][0]["answer"])),
                server.edit((OTHER, "<p>edited by hand 1</p>")),
                server.edit((OTHER, "<p>edited by hand 3</p>")),
                "",
            ],
        )
        assert code == 2
        assert lines[-1] == probe.MARKER_LEFT  # the warning is the last line
        assert server.patch_count == 3  # no restore was sent
        for expected in (
            "  marker still present in the rich-text question after the editor save: no",
            "  marker still present in the plain-text question after the editor save: yes",
            "  (no edit to the rich-text test question was seen before the write)",
            "  partial content (question 2): REPLACED",
            "  structure unchanged since the start: no",
            "Not restored: something besides the two test questions differs from the start.",
            "The note's questions no longer match the start - the partial write may "
            "have removed some. Re-enter anything missing by hand in Cliniko.",
        ):
            assert expected in lines, expected

    def test_restore_waits_for_every_other_question_to_match_the_start(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(_write_note(), merge=True)
        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                "",
                server.edit((OTHER, "<p>edited by hand 1</p>")),
                server.edit((OTHER, "<p>edited by hand 3</p>")),
                "",  # the other question's edit is NOT put back
            ],
        )
        assert code == 2
        assert server.patch_count == 3
        assert "  every other question reads as at the start: no" in lines
        assert lines[-1] == probe.MARKER_LEFT
        assert LOCKED_LINE not in lines
        assert server.answer(RICH) == probe.rich_answer(probe.PARTIAL_MARKER_LINES)

    def test_a_failure_after_the_first_write_leaves_the_marker(self, probe: ModuleType) -> None:
        server = NoteServer(
            _write_note(), merge=True, patch_answers=(None, cc.RawResponse(503, None, b""))
        )
        code, lines = _run_write(probe, server, ["yes", "", server.edit()])
        assert code == 2
        assert "PATCH /treatment_notes/<id> (full body): Unreachable (HTTP 503)" in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_rejected_later_write_still_leaves_the_marker(self, probe: ModuleType) -> None:
        # A not-applied refusal un-sets only what ITS write set: the first
        # write already placed the marker.
        server = NoteServer(
            _write_note(), merge=True, patch_answers=(None, cc.RawResponse(422, None, b"{}"))
        )
        code, lines = _run_write(probe, server, ["yes", "", server.edit()])
        assert code == 2
        assert "PATCH /treatment_notes/<id> (full body): ClinikoRejected (HTTP 422)" in lines
        assert "Nothing was written." not in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_failed_read_after_the_write_leaves_the_marker(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note(), merge=True, fail_reads_after=1)
        code, lines = _run_write(probe, server, ["yes"])
        assert code == 2 and server.patch_count == 1
        assert "GET /treatment_notes/<id>: Unreachable (HTTP 503)" in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_an_unexpected_error_is_reported_by_class_and_leaves_the_marker(
        self, probe: ModuleType
    ) -> None:
        def interrupt(prompt: str) -> str:
            raise KeyboardInterrupt(SENTINEL)

        server = NoteServer(_write_note(), merge=True)
        code, lines = _run_write(probe, server, ["yes", interrupt])
        assert code == 2 and server.patch_count == 1
        assert "Stopped: KeyboardInterrupt" in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_finalising_the_note_mid_run_stops_the_writes(self, probe: ModuleType) -> None:
        # Round 9 MED-003: Finalise is one click in the editor the
        # practitioner is using; no later PATCH may go to a finalised note.
        server = NoteServer(_write_note(), merge=True)

        def finalise(prompt: str) -> str:
            server.note.update(draft=False, finalized_at="2026-09-29T02:00:00Z")
            return ""

        code, lines = _run_write(probe, server, ["yes", finalise])
        assert code == 2 and server.patch_count == 1
        assert (
            "Refused: the note is no longer an open draft (finalised or archived in Cliniko)."
        ) in lines
        assert LOCKED_LINE in lines  # round 10 LOW-008
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_changed_question_list_stops_before_the_window_pass(
        self, probe: ModuleType
    ) -> None:
        # Round 9 LOW-006: the positions were taken at the start.
        server = NoteServer(_write_note(), merge=True)

        def add_question(prompt: str) -> str:
            server.note["content"]["sections"][0]["questions"].insert(
                0, {"name": "New", "type": "paragraph", "answer": "<p>x</p>"}
            )
            return ""

        code, lines = _run_write(probe, server, ["yes", add_question])
        assert code == 2 and server.patch_count == 1
        assert "Refused: the note's questions changed since the start." in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_formatting_only_difference_elsewhere_still_restores(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(_write_note(), merge=True)
        original = _original()
        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                "",
                server.edit((OTHER, "<p>edited by hand 1</p>")),
                server.edit((OTHER, "<p>edited by hand 3</p>")),
                # Put back as the editor might: same visible text, other markup.
                server.edit((OTHER, "<div>Wilhelmina   swelling</div>")),
            ],
        )
        assert code == 0 and probe.MARKER_LEFT not in lines
        assert "  every other question reads as at the start: yes" in lines
        assert server.patches[-1] == original

    # --- round 10 --------------------------------------------------------------

    def test_an_edit_at_the_yes_prompt_stops_before_the_first_write(
        self, probe: ModuleType
    ) -> None:
        # LOW-005: the pause at the prompt is time in the editor too.
        server = NoteServer(_write_note(), merge=True)

        def edit_then_yes(prompt: str) -> str:
            server.edit((OTHER, "<p>edited by hand</p>"))(prompt)
            return "yes"

        code, lines = _run_write(probe, server, [edit_then_yes])
        assert code == 2 and server.patch_count == 0
        assert "Refused: the note changed since it was checked - run the probe again." in lines
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines

    def test_a_changed_question_list_during_a_window_pause_stops(
        self, probe: ModuleType
    ) -> None:
        # LOW-009: the window pass's body was built before the pause.
        server = NoteServer(_write_note(), merge=True)

        def add_question(prompt: str) -> str:
            server.note["content"]["sections"][1]["questions"].append(
                {"name": "New", "type": "paragraph", "answer": "<p>x</p>"}
            )
            return ""

        code, lines = _run_write(probe, server, ["yes", "", add_question])
        assert code == 2 and server.patch_count == 1
        assert "Refused: the note's questions changed during the pause." in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_lone_test_question_qualifies_the_merged_verdict(self, probe: ModuleType) -> None:
        # MED-002: with nothing else in its section, a replace of the named
        # section looks like a merge.
        note = _write_note()
        note["content"] = {
            "sections": [
                {"name": "Subjective", "questions": [
                    {"name": "Presenting complaint", "type": "paragraph", "answer": "<p>a</p>"}
                ]},
                {"name": "Plan", "questions": [
                    {"name": "Pain scale", "type": "text", "answer": ""},
                    {"name": "Findings", "type": "text", "answer": "b"},
                ]},
            ]
        }
        server = NoteServer(note, merge=True)
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 0
        assert "  the test question's section holds other questions: no" in lines
        assert (
            "  partial content (question 2): MERGED (not ruled out: a replace of the named "
            "section; sections matched by position; questions matched by position)"
        ) in lines

    def test_the_rich_target_prefers_a_section_with_other_questions(
        self, probe: ModuleType
    ) -> None:
        content = {
            "sections": [
                {"name": "A", "questions": [{"name": "Q", "type": "paragraph"}]},
                {"name": "B", "questions": [
                    {"name": "Q", "type": "text"}, {"name": "R", "type": "paragraph"}
                ]},
            ]
        }
        assert probe.rich_target(content) == probe.Position(1, 1)
        content["sections"][1]["questions"].pop()
        assert probe.rich_target(content) == probe.Position(0, 0)
        # Round 11 MED-001: away from the note's first question when it can be.
        content["sections"][0]["questions"].append({"name": "T", "type": "text"})
        assert probe.rich_target(content) == probe.Position(0, 0)  # the only shared one
        content["sections"][1]["questions"].append({"name": "R", "type": "paragraph"})
        assert probe.rich_target(content) == probe.Position(1, 1)
        # Codex round 12 PR-MED-028: displaced on BOTH levels first; among
        # the one-level ones, the first.
        one_level = {
            "sections": [
                {"name": "A", "questions": [
                    {"name": "Q", "type": "paragraph"}, {"name": "S", "type": "paragraph"}
                ]},
                {"name": "B", "questions": [
                    {"name": "R", "type": "paragraph"}, {"name": "T", "type": "text"}
                ]},
            ]
        }
        assert probe.rich_target(one_level) == probe.Position(0, 1)

    @staticmethod
    def _second_note() -> dict[str, Any]:
        """A note whose shared-section paragraph is its section's SECOND
        question, in the FIRST section: (0, 1)."""
        note = _write_note()
        subjective = note["content"]["sections"][0]["questions"]
        subjective[0], subjective[1] = subjective[1], subjective[0]  # text first
        return note

    @staticmethod
    def _displaced_note() -> dict[str, Any]:
        """A note whose shared-section paragraph is displaced on both array
        levels: (1, 1)."""
        note = _write_note()
        note["content"]["sections"][1]["questions"].insert(
            0, {"name": "Observations", "type": "text", "answer": "obs"}
        )
        return note

    @staticmethod
    def _second_section_note() -> dict[str, Any]:
        """A note whose only shared-section paragraph is its section's FIRST
        question, in the SECOND section: (1, 0)."""
        note = _write_note()
        note["content"]["sections"][0]["questions"].pop(0)  # Subjective: text, choices
        note["content"]["sections"][1]["questions"].append(
            {"name": "Observations", "type": "text", "answer": "obs"}
        )
        return note

    def test_a_target_in_the_first_section_qualifies_sections_by_position(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(self._second_note(), merge=True)
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 0
        assert "  rich-text question (section 1, question 2): equal" in lines
        assert (
            "  partial content (question 2): MERGED (not ruled out: sections matched by position)"
        ) in lines

    def test_a_target_first_in_its_section_qualifies_questions_by_position(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(self._second_section_note(), merge=True)
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 0
        assert "  rich-text question (section 2, question 1): equal" in lines
        assert (
            "  partial content (question 2): MERGED (not ruled out: questions matched by "
            "position)"
        ) in lines

    def test_a_fully_displaced_target_merged_by_name_is_plain_merged(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(self._displaced_note(), merge=True)
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 0
        assert "  rich-text question (section 2, question 2): equal" in lines
        assert "  partial content (question 2): MERGED" in lines

    @pytest.mark.parametrize("axis", ["sections", "questions"])
    def test_one_level_matched_by_position_is_reported_replaced(
        self, probe: ModuleType, axis: str
    ) -> None:
        """Codex round 12 PR-MED-028: with the target displaced on both
        levels, a server matching EITHER level by position changes the
        question list, whichever level it is."""

        class Mixed(NoteServer):
            def _apply(self, content: dict[str, Any]) -> None:
                sections = self.note["content"]["sections"]
                for i, sent_section in enumerate(content["sections"]):
                    if axis == "sections":
                        section = sections[i]
                    else:
                        section = next(s for s in sections if s["name"] == sent_section["name"])
                    held = section["questions"]
                    for j, sent in enumerate(sent_section["questions"]):
                        if axis == "questions":
                            held[j] = copy.deepcopy(sent)
                            continue
                        index = next(
                            (k for k, q in enumerate(held) if q["name"] == sent["name"]), None
                        )
                        if index is None:
                            held.append(copy.deepcopy(sent))
                        else:
                            held[index] = copy.deepcopy(sent)

        server = Mixed(self._displaced_note())
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert "  partial content (question 2): REPLACED" in lines
        assert code == 2 and lines[-1] == probe.MARKER_LEFT

    def test_a_partial_write_the_server_ignores_is_reported_ignored(
        self, probe: ModuleType
    ) -> None:
        # Codex round 12 PR-MED-027: a 200 that drops the partial body.
        server = NoteServer(
            _write_note(),
            merge=True,
            patch_answers=(None, None, cc.RawResponse(200, None, b"{}")),
        )
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert "  Cliniko kept every other question as it was: yes" in lines
        assert "  the partial write's own marker read back at the test question: no" in lines
        assert "  partial content (question 2): IGNORED" in lines
        assert code == 0  # the restore still runs: only the test questions differ

    def test_a_test_question_edited_before_the_restore_is_restored_and_reported(
        self, probe: ModuleType
    ) -> None:
        # Codex round 12 PR-MED-026 (narrowed): the test questions are the
        # probe's own and are restored; the report says one held other text.
        server = NoteServer(_write_note(), merge=True)
        original = _original()
        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                "",
                server.edit((OTHER, "<p>edited by hand 1</p>")),
                server.edit((OTHER, "<p>edited by hand 3</p>")),
                server.edit(
                    (OTHER, original["sections"][1]["questions"][0]["answer"]),
                    (RICH, "<p>edited by hand 4</p>"),
                ),
            ],
        )
        assert code == 0 and server.note["content"] == original
        assert (
            "  the rich-text test question held only a marker or its original answer: no"
        ) in lines
        assert (
            "  the plain-text test question held only a marker or its original answer: yes"
        ) in lines
        assert "Restored the original content." in lines

    def test_a_merge_by_position_is_reported_replaced(self, probe: ModuleType) -> None:
        # Round 11 MED-001: a server that merges arrays by index puts the
        # partial body's one question over the note's FIRST question.
        class ByIndex(NoteServer):
            def _apply(self, content: dict[str, Any]) -> None:
                for i, section in enumerate(content["sections"]):
                    for j, question in enumerate(section["questions"]):
                        target = self.note["content"]["sections"][i]["questions"]
                        target[j] = copy.deepcopy(question)

        server = ByIndex(self._second_note())
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert "  partial content (question 2): REPLACED" in lines
        assert code == 2 and lines[-1] == probe.MARKER_LEFT

    @pytest.mark.parametrize(
        ("got", "rich", "expected"),
        [
            ("same", False, "equal"),
            ("Clinic Scribe test write - delete this text: a < b & \"c\" 'd' é", False,
             "sanitised"),
            ("Clinic Scribe test write - delete this text: a &lt; b &amp; &quot;c&quot; "
             "&#x27;d&#x27; é", False, "html-escaped"),
            ("<p>Clinic Scribe test write - delete this text: a &lt; b &amp; &quot;c&quot; "
             "&#x27;d&#x27; é</p>", True, "sanitised"),
            # Round 11 LOW-004: escaped twice.
            ("<p>Clinic Scribe test write - delete this text: a &amp;lt; b &amp;amp; "
             "&amp;quot;c&amp;quot; &amp;#x27;d&amp;#x27; é</p>", True, "double-escaped"),
            ("Clinic Scribe test write - delete this text: a &amp;lt; b &amp;amp; "
             "&amp;quot;c&amp;quot; &amp;#x27;d&amp;#x27; é", False, "rejected"),
            ("", False, "rejected"),
        ],
    )
    def test_the_echo_classes(
        self, probe: ModuleType, got: str, rich: bool, expected: str
    ) -> None:
        # LOW-007: a plain-text echo found only after HTML-decoding is named.
        assert probe.echo_class("same", got, rich=rich) == expected

    def test_a_body_that_cannot_be_encoded_writes_nothing(self, probe: ModuleType) -> None:
        # Round 9 LOW-009: the body is built and encoded before the flag.
        note = _write_note()
        note["content"]["sections"][1]["questions"][0]["answer"] = "<p>\ud800</p>"
        server = NoteServer(note, merge=True)
        code, lines = _run_write(probe, server, ["yes"])
        assert code == 2 and server.patch_count == 0
        assert "Stopped: DraftUnencodable" in lines
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines

    def test_a_restore_that_does_not_read_back_leaves_the_marker(
        self, probe: ModuleType
    ) -> None:
        # The restore's 200 is not trusted: the note is read back.
        server = NoteServer(
            _write_note(),
            merge=True,
            patch_answers=(None, None, None, cc.RawResponse(200, None, b"{}")),
        )
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 2 and server.patch_count == 4
        assert "  the note reads as at the start: no" in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_partial_write_that_changes_another_question_is_unclear(
        self, probe: ModuleType
    ) -> None:
        class Blanking(NoteServer):
            """Keeps the structure but clears the section's other answers."""

            def _apply(self, content: dict[str, Any]) -> None:
                super()._apply(content)
                if len(content["sections"][0]["questions"]) == 1:
                    self.note["content"]["sections"][0]["questions"][1]["answer"] = ""

        server = Blanking(_write_note(), merge=True)
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert "  Cliniko kept every other question as it was: no" in lines
        assert "  partial content (question 2): unclear" in lines
        # Only the plain-text TEST question was cleared, so the restore runs.
        assert code == 0 and server.note["content"] == _original()

    # --- smoke 2026-09-29: a template with no plain-text question ------------

    @staticmethod
    def _rich_only_note() -> dict[str, Any]:
        """Shaped like clinic 1's real template (P.1 smoke output): three
        sections of 1 / 3 / 3 questions, paragraphs and one checkboxes
        question, NO ``text`` question; most answers absent."""
        note = _write_note()
        note["content"] = {
            "sections": [
                {"name": "History", "questions": [
                    {"name": "Presenting complaint", "type": "paragraph",
                     "answer": "<p>Site - Chron - Sensory -</p>"},
                ]},
                {"name": "Assessment", "questions": [
                    {"name": "Observations", "type": "paragraph"},
                    {"name": "Areas", "type": "checkboxes", "answers": [
                        {"value": "Neck", "selected": True}, {"value": "Back"},
                    ]},
                    {"name": "Findings", "type": "paragraph"},
                ]},
                {"name": "Plan", "questions": [
                    {"name": "Treatment", "type": "paragraph"},
                    {"name": "Advice", "type": "paragraph"},
                    {"name": "Review", "type": "paragraph"},
                ]},
            ]
        }
        return note

    def test_a_note_with_no_plain_text_question_is_tested_on_its_rich_text_one(
        self, probe: ModuleType
    ) -> None:
        """Practitioner decision 2026-09-29: the probe tests the rich-text
        question alone, says so, and keeps every safety property — the typed
        yes, the refusals, structure-only output, restore-or-MARKER-LEFT —
        and the checkboxes answer rides through every write untouched."""
        note = self._rich_only_note()
        original = copy.deepcopy(note["content"])
        server = NoteServer(note, merge=True)
        other = (0, 0)
        target = (1, 2)  # displaced on both levels, in a shared section
        prompts: list[str] = []

        def recorded(action: Callable[[str], str]) -> Callable[[str], str]:
            def step(prompt: str) -> str:
                prompts.append(prompt)
                return action(prompt)

            return step

        code, lines = _run_write(
            probe,
            server,
            [
                "yes",
                recorded(server.edit()),  # question 5
                recorded(server.edit((other, "<p>edited by hand 1</p>"),
                                     (target, "<p>edited by hand 2</p>"))),
                recorded(server.edit((other, "<p>edited by hand 3</p>"))),
                recorded(server.edit((other, original["sections"][0]["questions"][0]["answer"]))),
            ],
        )
        assert code == 0 and probe.MARKER_LEFT not in lines
        assert server.note["content"] == original  # the checkboxes answer included
        assert server.patch_count == 4  # marker, full pass, partial pass, restore
        # The first write changes the one test question and nothing else.
        expected = copy.deepcopy(original)
        expected["sections"][1]["questions"][2]["answer"] = probe.rich_answer(
            probe.MARKER_LINES
        )
        assert server.patches[0] == expected
        for expected in (
            "  the note has no plain-text (text) question: only the rich-text question is "
            "tested, so this run gives no plain-text results",
            "  rich-text question (section 2, question 3): equal",
            "  every other question byte-identical: yes",
            "  marker still present in the rich-text question after the editor save: yes",
            "  the rich-text test question's edit survived the write: no (expected: no)",
            "  partial content (question 2): MERGED",
            "  the rich-text test question held only a marker or its original answer: yes",
            "Restored the original content.",
        ):
            assert expected in lines, expected
        assert not any("plain-text question (" in line for line in lines)
        assert not any("plain-text test question" in line for line in lines)
        assert "the test question" in prompts[2] and "two test questions" not in prompts[2]
        assert "the test question" in prompts[3] and "two test questions" not in prompts[3]

    def test_a_rich_only_run_still_leaves_the_marker_when_it_cannot_restore(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(self._rich_only_note())  # replaces content whole
        code, lines = _run_write(probe, server, ["yes", "", "", "", ""])
        assert code == 2
        assert "  partial content (question 2): REPLACED" in lines
        assert (
            "Not restored: something besides the test question differs from the start."
        ) in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_a_rich_only_run_still_needs_the_typed_yes(self, probe: ModuleType) -> None:
        server = NoteServer(self._rich_only_note())
        code, lines = _run_write(probe, server, ["no"])
        assert code == 2 and server.patch_count == 0
        assert "Refused: no yes was typed." in lines
        assert "Nothing was written." in lines

    def test_a_rejected_first_write_wrote_nothing(self, probe: ModuleType) -> None:
        body = json.dumps(
            {"message": SENTINEL, "errors": {"content": [SENTINEL], "wilhelmina_x": [SENTINEL]}}
        ).encode()
        server = NoteServer(_write_note(), patch_answers=(cc.RawResponse(422, None, body),))
        code, lines = _run_write(probe, server, ["yes"])
        assert code == 2
        assert (
            "PATCH /treatment_notes/<id> (test marker): ClinikoRejected (HTTP 422) "
            "categories: content, other"
        ) in lines
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines

    @pytest.mark.parametrize(
        ("note", "surname", "digits", "steps"),
        [
            pytest.param(
                _write_note(draft=False, finalized_at="2026-09-27T02:00:00Z"),
                SURNAME, DIGITS, [], id="finalised",
            ),
            pytest.param(
                _write_note(finalized_at="2026-09-27T02:00:00Z"), SURNAME, DIGITS, [],
                id="finalized-at-set",
            ),
            pytest.param(
                _write_note(archived_at="2026-09-27T02:00:00Z"), SURNAME, DIGITS, [],
                id="archived",
            ),
            pytest.param(
                _write_note(deleted_at="2026-09-27T02:00:00Z"), SURNAME, DIGITS, [],
                id="deleted",
            ),
            pytest.param(_write_note(id=777), SURNAME, DIGITS, [], id="another-note-id"),
            pytest.param(
                _write_note(patient={"links": {"self": f"{API}/patients/777"}}),
                SURNAME, DIGITS, [], id="wrong-patient",
            ),
            pytest.param(
                _write_note(practitioner={"links": {"self": f"{API}/practitioners/777"}}),
                SURNAME, DIGITS, [], id="wrong-practitioner",
            ),
            pytest.param(_write_note(), "Smith", DIGITS, [], id="wrong-surname"),
            pytest.param(_write_note(), SURNAME, "0000", [], id="wrong-digits"),
            pytest.param(_write_note(), SURNAME, "", [], id="no-digits"),
            pytest.param(_write_note(), SURNAME, DIGITS, ["no"], id="no-yes"),
            pytest.param(_write_note(), SURNAME, DIGITS, ["YES please"], id="not-exactly-yes"),
            pytest.param(
                {**_write_note(), "content": {"sections": [{"name": "S", "questions": [
                    {"name": "Q", "type": "text", "answer": ""}]}]}},
                SURNAME, DIGITS, [], id="no-rich-text-question",
            ),
            pytest.param(
                {**_write_note(), "content": {"sections": "x"}}, SURNAME, DIGITS, [],
                id="no-sections",
            ),
        ],
    )
    def test_every_refusal_writes_nothing(
        self,
        probe: ModuleType,
        note: dict[str, Any],
        surname: str,
        digits: str,
        steps: list[Step],
    ) -> None:
        server = NoteServer(copy.deepcopy(note))
        code, lines = _run_write(probe, server, steps, surname=surname, digits=digits)
        assert code == 2
        assert server.patch_count == 0
        assert any(line.startswith("Refused: ") for line in lines)
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines

    def test_the_surname_is_compared_case_and_space_insensitively(
        self, probe: ModuleType
    ) -> None:
        server = NoteServer(_write_note())
        code, lines = _run_write(probe, server, ["no"], surname="  fotheringay ")
        assert code == 2 and "Refused: no yes was typed." in lines


class TestTestWriteFinal:
    FINAL = {"draft": False, "finalized_at": "2026-09-27T02:00:00Z"}

    def test_a_refused_write_is_reported_by_class_and_category(self, probe: ModuleType) -> None:
        body = json.dumps(
            {"message": SENTINEL, "errors": {"draft": [SENTINEL], SENTINEL: [SENTINEL]}}
        ).encode()
        server = NoteServer(
            _write_note(**self.FINAL), patch_answers=(cc.RawResponse(422, None, body),)
        )
        code, lines = _run_write(probe, server, ["yes"], mode="--test-write-final")
        assert code == 0
        assert server.patch_count == 1
        assert (
            "PATCH /treatment_notes/<id> (finalised note): ClinikoRejected (HTTP 422) "
            "categories: draft, other"
        ) in lines
        assert "Cliniko refused the write to the finalised note, as expected." in lines
        assert probe.MARKER_LEFT not in lines

    def test_a_200_is_an_alarm(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note(**self.FINAL))
        code, lines = _run_write(probe, server, ["yes"], mode="--test-write-final")
        assert code == 2
        assert "ALARM: Cliniko accepted a write into a FINALISED note." in lines
        assert LOCKED_LINE in lines
        assert lines[-1] == probe.MARKER_LEFT

    def test_an_unknown_outcome_leaves_the_marker(self, probe: ModuleType) -> None:
        server = NoteServer(
            _write_note(**self.FINAL), patch_answers=(cc.RawResponse(503, None, b""),)
        )
        code, lines = _run_write(probe, server, ["yes"], mode="--test-write-final")
        assert code == 2
        assert lines[-1] == probe.MARKER_LEFT

    @pytest.mark.parametrize(
        ("status", "described"),
        [
            (401, "CredentialsRejected (HTTP 401)"),
            (403, "CredentialsRejected (HTTP 403)"),
            (404, "NotFound"),
        ],
    )
    def test_a_permission_or_not_found_refusal_is_inconclusive(
        self, probe: ModuleType, status: int, described: str
    ) -> None:
        # Round 9 MED-004: a key without write permission is refused the
        # same way on ANY note — that is not Cliniko refusing a final note.
        server = NoteServer(
            _write_note(**self.FINAL), patch_answers=(cc.RawResponse(status, None, b""),)
        )
        code, lines = _run_write(probe, server, ["yes"], mode="--test-write-final")
        assert code == 2 and server.patch_count == 1
        assert f"PATCH /treatment_notes/<id> (finalised note): {described}" in lines
        assert "Cliniko refused the write to the finalised note, as expected." not in lines
        assert (
            "Cliniko refused the write, but not as a validation error. If --test-write "
            "wrote to a draft with this same key, this is Cliniko refusing the finalised "
            "note; if not, check the key's permissions."
        ) in lines
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines

    def test_an_open_draft_is_refused(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note())
        code, lines = _run_write(probe, server, ["yes"], mode="--test-write-final")
        assert code == 2 and server.patch_count == 0
        assert "Nothing was written." in lines

    def test_no_yes_writes_nothing(self, probe: ModuleType) -> None:
        server = NoteServer(_write_note(**self.FINAL))
        code, lines = _run_write(probe, server, [""], mode="--test-write-final")
        assert code == 2 and server.patch_count == 0
        assert "Refused: no yes was typed." in lines
        assert "Nothing was written." in lines
        assert probe.MARKER_LEFT not in lines


class TestTestWriteArguments:
    @pytest.mark.parametrize(
        "argv",
        [
            ["--test-write", KEY],
            ["--test-write", "--test-write-final"],
            ["--test-write=1"],
            ["--partial"],
        ],
        ids=["mode-plus-key", "two-modes", "mode-with-value", "unknown-flag"],
    )
    def test_anything_but_one_mode_is_refused_without_echo(
        self, probe: ModuleType, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        server = NoteServer(_write_note())
        asked: list[str] = []

        def ask(prompt: str) -> str:
            asked.append(prompt)
            return ""

        code = probe.main(argv, read_line=ask, read_secret=ask, out=print, transport=server)
        assert code == 2 and asked == [] and server.calls == []
        out = capsys.readouterr().out
        assert KEY not in out and "takes no arguments" in out
