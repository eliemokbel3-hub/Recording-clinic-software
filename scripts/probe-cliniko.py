"""Cliniko feasibility probe (Cliniko workflow safeguards plan, Task 1.3) and
the practitioner's test write (cliniko-draft-write plan, Task 1.2).

The practitioner runs this from a normal terminal at the repository root,
never an agent shell. With no argument it is READ-ONLY (safeguards Task P.1,
once per clinic, with a patient's treatment note open in Cliniko):

    .venv\\Scripts\\python.exe scripts\\probe-cliniko.py

``--test-write`` and ``--test-write-final`` WRITE to Cliniko; they are the
draft-write plan's Task P.1 and are described at the end of this docstring.
Everything below up to there is the read-only mode.

It asks for the contact email (the User-Agent Cliniko requires), the open
note's URL, and the clinic's API key — the key through ``getpass`` only (not
echoed, never an argument, never an environment variable) — and then makes
READ-ONLY calls through the app's own client (``scribe_desktop.cliniko_client``;
this read-only mode makes GET calls only, the host pinned from the key's
shard, TLS 1.2+, no redirects):
``/user``, ``/practitioners?q[]=user_id:=<id>``, ``/settings/public``,
``/settings``, ``/treatment_notes/<id>``, ``/patients/<id>`` and, when the note
links one, ``/bookings/<id>``.

It prints ONLY structure: the status of each call, each answer's field names
with every value reduced to its kind (``<text>`` / ``<empty>`` / ``<number>`` /
``<bool>`` / ``null``; the note's ``content`` is therefore its section and
question shape with answers reduced to empty or non-empty), the key user's
account role when it is a plain word (such as ``practitioner``), and yes/no
facts — whether the note is a draft and unfinalised, which links it carries,
whether its patient is the URL's and its practitioner the key user's, whether
``/settings/public`` answered and its subdomain matches the URL's. It never
prints a name, an id value, an answer's text, the URL, the subdomain, the
email or the key. Nothing is written. Named residue: a JSON KEY is printed
when it has the shape of a field name (lower-case identifier); Cliniko's
documented API keys objects by fixed field names, so a data-bearing key
would need Cliniko to key an object by patient data, which its schema does
not do — any other key prints as ``<key>``.
Paste the output into Task P.1's Done note.

THE TEST WRITE (draft-write plan, Flow 4). Run it ONLY on a note of a DUMMY
patient you created in your own clinic, with that note open in Cliniko's
editor:

    .venv\\Scripts\\python.exe scripts\\probe-cliniko.py --test-write

It asks for the same three inputs plus the dummy patient's surname and the
last four digits of the note's id (both compared with what Cliniko returns,
never printed), then re-reads the note and REFUSES — writing nothing — unless
the note is an open draft (``draft`` true, ``finalized_at`` null, not
archived), its patient is the URL's and its practitioner is the key user's,
and the surname and digits match. It prints the note's questions by position
(type and empty/non-empty only) and the template's question structure with
whether each question carries a default answer (question 3), picks a
rich-text (``paragraph``) question — of those in a section that holds other
questions, the first NOT in the first section and NOT its section's first
question, else the first displaced on one of those, else the first; with no
such section, the first ``paragraph`` — and the FIRST plain-text
(``text``) question, says what it will do and waits for a typed ``yes``; it
then re-reads the note and refuses unless nothing changed while it waited.
A note with no ``paragraph`` question is refused. A note with no ``text``
question is tested on its rich-text question ALONE: the run says so, gives
no plain-text results, and every step below applies to that one question
(the other questions, a checkboxes question included, are checked as
"every other question" throughout).
Every write goes through the app's own ``ClinikoCall.write_draft_note`` (the
``PATCH`` of the note's ``content`` only). Then:

1. writes the test marker (``MARKER_LINES``: an adversarial line, a second
   line, an empty line) into the test question(s), re-reads, and reports per
   question ``equal`` / ``sanitised`` / ``html-escaped`` (a plain-text answer
   that came back HTML-escaped) / ``double-escaped`` (a rich-text answer
   escaped twice) / ``rejected``, and whether every other question came back
   unchanged (questions 1 and 4);
2. pauses — save or edit the note in the open editor — re-reads and reports
   whether the marker survived the editor's save (question 5);
3. the full-body window pass: reads the note, pauses while you edit a
   DIFFERENT question AND the rich-text test question in the editor, reads
   again to see your edits, PATCHes the body built from the FIRST read, and
   reports which edit survived (question 6 — the test question's edit is
   expected to be lost);
4. the partial-body window pass: the same, but you edit only a different
   question and the PATCH carries only the rich-text test question, with a
   marker of its own (``PARTIAL_MARKER_LINES``: the same first line, a
   different second line); it reports whether Cliniko kept the other
   questions and your edit, whether that partial marker read back at the
   test question, whether the test question's section holds other
   questions, and a verdict for question 2: ``MERGED``, ``REPLACED``,
   ``IGNORED`` (a 200 that did not apply the partial body), ``unclear`` (the
   question list kept its shape but another answer changed), or
   ``MERGED (not ruled out: …)`` naming what this note could not test — a
   replace of the named section (nothing else in it), sections matched by
   position (the test question is in the first section) or questions
   matched by position (it is its section's first question): the partial
   body always carries it as the first question of the first section. A
   pause in which the note's questions change stops the run by name;
5. restores: pauses while you put back any text you changed in the OTHER
   questions and close the editor, re-reads, and PATCHes the original
   content back ONLY if the note's structure is unchanged and every
   question but the test question(s) reads as it did at the start (compared
   as visible text); the test question(s) are restored whatever they hold,
   and for each it reports whether it held only a marker or its original
   answer. Otherwise — and on ANY failure after the first write
   was sent — it prints ``MARKER LEFT - delete it by hand in Cliniko`` as
   its LAST line and exits 2 (preceded by a line saying to archive the note
   if it was found finalised or archived and the marker cannot be deleted).
   Any read that finds the note no longer an open draft stops the run.

``--test-write-final`` is the separate finalised leg: run it on a SECOND note
of the same dummy patient that you have FINALISED by hand. It refuses unless
the note re-reads as final (and the same patient, practitioner, surname and
digit checks pass), waits for ``yes``, PATCHes the marker into its first
rich-text (else plain-text) question and prints the answer's class, status
and — for a 422 — the fixed error categories (never their text). Only a
validation refusal (``ClinikoRejected``) is "as expected" (exit 0); a
401/403/404 is Cliniko refusing the finalised note only if ``--test-write``
wrote with the same key (exit 2). A 200 is an ALARM: Cliniko wrote into a
finalised note; it prints ``MARKER LEFT`` and exits 2, as it does when the
outcome is unknown.

Both modes print structure only: statuses, error classes, fixed categories,
positions, question types and yes/no facts — never a name, an id value, an
answer's text, the URL, the surname, the digits, the email or the key. The
marker itself is this script's own constant.
"""

from __future__ import annotations

import argparse
import copy
import getpass
import html
import json
import re
import sys
import unicodedata
from collections.abc import Callable, Collection, Iterator
from pathlib import Path
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "desktop" / "src"))

from scribe_desktop import cliniko_client as cc  # noqa: E402
from scribe_desktop.benchmark import apply_offline_env, assert_offline_env  # noqa: E402

NOTE_URL_RE = re.compile(
    r"https://(?P<subdomain>[a-z0-9][a-z0-9-]{0,62})\.(?P<shard>[a-z]{2}[0-9])\.cliniko\.com"
    r"/patients/(?P<patient_id>[1-9][0-9]{0,18})"
    r"/treatment_notes/(?P<note_id>[1-9][0-9]{0,18})(?:/edit)?(?:\?[^\s#]*)?(?:#\S*)?"
)
_SAFE_KEY = re.compile(r"[a-z_][a-z0-9_]{0,63}")
_LINK_ID = re.compile(r"/([1-9][0-9]{0,18})$")
_ROLE = re.compile(r"[a-z_]{1,32}")
_MAX_DEPTH = 12


class NoteTarget(NamedTuple):
    subdomain: str
    shard: str
    patient_id: str
    note_id: str


def parse_note_url(url: str) -> NoteTarget | None:
    match = NOTE_URL_RE.fullmatch(url)
    if match is None:
        return None
    return NoteTarget(
        match.group("subdomain"),
        match.group("shard"),
        match.group("patient_id"),
        match.group("note_id"),
    )


def shape(value: object, depth: int = 0) -> object:
    """The structure of a JSON value with every leaf reduced to its kind.

    Keys are kept only when they look like schema field names (lower-case
    identifiers); any other key is shown as ``<key>``. A data-bearing key
    that happens to be a lower-case identifier WOULD print — the residue the
    module docstring names. Lists show their length and the distinct shapes
    of their items, in first-seen order.
    """
    if depth > _MAX_DEPTH:
        return "<deep>"
    if value is None:
        return None
    if isinstance(value, bool):
        return "<bool>"
    if isinstance(value, (int, float)):
        return "<number>"
    if isinstance(value, str):
        return "<empty>" if value == "" else "<text>"
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            name = key if isinstance(key, str) and _SAFE_KEY.fullmatch(key) else "<key>"
            if name in out:
                name = f"{name}#{len(out)}"
            out[name] = shape(item, depth + 1)
        return out
    if isinstance(value, list):
        distinct: list[object] = []
        for item in value:
            item_shape = shape(item, depth + 1)
            if item_shape not in distinct:
                distinct.append(item_shape)
        return {"<items>": len(value), "<shapes>": distinct}
    return "<other>"


def _valid_id(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    try:
        return cc.check_id(str(value))
    except cc.InvalidId:
        return None


def _yes(flag: bool | None) -> str:
    return "unknown" if flag is None else ("yes" if flag else "no")


def _link_id(record: dict[str, Any], field: str) -> str | None:
    link = record.get(field)
    if not isinstance(link, dict):
        return None
    links = link.get("links")
    url = links.get("self") if isinstance(links, dict) else None
    if not isinstance(url, str):
        return None
    match = _LINK_ID.search(url)
    return match.group(1) if match else None


class Probe:
    """Runs the calls and prints only structure through ``out``."""

    def __init__(self, call: cc.ClinikoCall, out: Callable[[str], None]) -> None:
        self._call = call
        self._out = out

    def fetch(self, label: str, get: Callable[[], dict[str, Any]]) -> dict[str, Any] | None:
        try:
            answer = get()
        except cc.ClinikoError as error:
            status = getattr(error, "status", None)
            suffix = f" (HTTP {status})" if isinstance(status, int) else ""
            self._out(f"GET {label}: {type(error).__name__}{suffix}")
            return None
        self._out(f"GET {label}: 200")
        self._out(json.dumps(shape(answer), indent=2, sort_keys=True))
        return answer

    def run(self, target: NoteTarget) -> None:
        out = self._out
        call = self._call
        key_shard = call.host.split(".")[1]
        out(f"Key shard equals the note URL's shard: {_yes(key_shard == target.shard)}")

        user = self.fetch("/user", call.get_user)
        user_id = _valid_id(user.get("id")) if user else None
        if user is not None:
            role = user.get("role")
            # An account role is a word like "practitioner", never patient
            # data; anything else prints as its kind only.
            shown = role if isinstance(role, str) and _ROLE.fullmatch(role) else shape(role)
            out(f"  role: {shown}")
            active = user.get("active")
            out(f"  active: {_yes(active) if isinstance(active, bool) else 'absent'}")

        practitioner_ids: list[str] = []
        if user_id is not None:
            found = self.fetch(
                "/practitioners?q[]=user_id:=<id>",
                lambda: call.get_practitioners_for_user(user_id),
            )
            records = found.get("practitioners") if found else None
            if isinstance(records, list):
                practitioner_ids = [
                    str(r["id"]) for r in records if isinstance(r, dict) and "id" in r
                ]
                out(f"  practitioner records for this user: {len(records)}")
        else:
            out("GET /practitioners?q[]=user_id:=<id>: skipped (no usable user id)")

        public = self.fetch("/settings/public", call.get_public_settings)
        out(f"  /settings/public answered: {_yes(public is not None)}")
        if public is not None:
            account = public.get("account")
            subdomain = account.get("subdomain") if isinstance(account, dict) else None
            out(f"  account.subdomain present: {_yes(isinstance(subdomain, str))}")
            if isinstance(subdomain, str):
                out(f"  subdomain matches the note URL's: {_yes(subdomain == target.subdomain)}")

        self.fetch("/settings", call.get_settings)

        note = self.fetch(
            "/treatment_notes/<id>", lambda: call.get_treatment_note(target.note_id)
        )
        if note is not None:
            draft = note.get("draft")
            out(f"  draft: {str(draft).lower() if isinstance(draft, bool) else 'absent'}")
            if "finalized_at" in note:
                out(f"  finalized_at: {'null' if note['finalized_at'] is None else 'set'}")
            else:
                out("  finalized_at: absent")
            for field in ("patient", "practitioner", "booking", "treatment_note_template"):
                out(f"  {field} link present: {_yes(_link_id(note, field) is not None)}")
            patient_link = _link_id(note, "patient")
            out(
                "  patient link equals the URL's patient: "
                + _yes(None if patient_link is None else patient_link == target.patient_id)
            )
            practitioner_link = _link_id(note, "practitioner")
            same = (
                None
                if practitioner_link is None or not practitioner_ids
                else practitioner_link in practitioner_ids
            )
            out(f"  note practitioner is the key user's practitioner: {_yes(same)}")

        self.fetch("/patients/<id>", lambda: call.get_patient(target.patient_id))

        booking_id = _link_id(note, "booking") if note is not None else None
        if booking_id is not None:
            booking = self.fetch("/bookings/<id>", lambda: call.get_booking(booking_id))
            if booking is not None:
                out(f"  starts_at present: {_yes(isinstance(booking.get('starts_at'), str))}")
        else:
            out("GET /bookings/<id>: skipped (the note links no booking)")


# --- the test write (draft-write plan, Task 1.2) -------------------------------

MARKER_TEXT = "Clinic Scribe test write - delete this text: a < b & \"c\" 'd' é"
MARKER_LINES = (MARKER_TEXT, "Clinic Scribe test write - second line", "")
# The partial pass writes a marker the full pass did not, so a 200 that
# ignored the partial body cannot read back as a merge (codex round 12
# PR-MED-027). Same first line: ``marker_present`` still finds it.
PARTIAL_LINE = "Clinic Scribe test write - partial pass"
PARTIAL_MARKER_LINES = (MARKER_TEXT, PARTIAL_LINE, "")
MARKER_LEFT = "MARKER LEFT - delete it by hand in Cliniko"
RICH = "paragraph"
PLAIN = "text"
# A write refused with one of these was not applied; any other failure of a
# PATCH (a timeout, a 5xx, a 429, an unreadable status line) may have been.
_NOT_APPLIED = (cc.ClinikoRejected, cc.CredentialsRejected, cc.NotFound)
_TYPE_WORD = re.compile(r"[a-z_]{1,32}")
_BLOCK_TAG = re.compile(
    r"<\s*/?\s*(?:p|div|li|ul|ol|blockquote|h1|h2)\b[^>]*>|<\s*br\s*/?\s*>", re.IGNORECASE
)
_ANY_TAG = re.compile(r"<[^>]*>")
_ABSENT = "\x00absent"


def rich_answer(lines: tuple[str, ...]) -> str:
    """Rich text shaped as the app sends it: one ``<p>`` per line, escaped.
    One difference: an empty line stays ``<p></p>`` here, where the app's
    ``draft_write.to_cliniko_answer`` sends ``<p><br></p>``."""
    return "".join(f"<p>{html.escape(line, quote=True)}</p>" for line in lines)


def plain_answer(lines: tuple[str, ...]) -> str:
    return "\n".join(lines)


def _collapse(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _html_text(text: str) -> str:
    return html.unescape(_ANY_TAG.sub("", _BLOCK_TAG.sub("\n", text)))


def _fold(text: str) -> str:
    return _collapse(text).casefold()


def visible(question: object) -> str:
    """A question's answer as comparable visible text: a rich-text answer's
    tags dropped (block tags as line breaks) and entities decoded, any text
    whitespace-collapsed and NFC; a choice list or other value as sorted
    JSON. Used only to COMPARE — never printed."""
    if not isinstance(question, dict):
        return _ABSENT
    if "answer" not in question:
        return json.dumps(question.get("answers"), sort_keys=True)
    value = question["answer"]
    if not isinstance(value, str):
        return json.dumps(value, sort_keys=True)
    return _collapse(_html_text(value) if question.get("type") == RICH else value)


def marker_present(value: object) -> bool:
    if not isinstance(value, str):
        return False
    wanted = _collapse(MARKER_TEXT)
    return wanted in _collapse(value) or wanted in _collapse(_html_text(value))


def echo_class(sent: str, got: object, *, rich: bool) -> str:
    """Question 4: ``equal`` (byte-equal), ``sanitised`` (changed, marker
    text still there), ``double-escaped`` (a rich-text answer whose marker
    appears only after a second decode) or ``rejected`` (the marker did not
    come back). A
    plain-text answer whose marker is found only after HTML-decoding is
    ``html-escaped`` (round 10 LOW-007: D4 reads a ``text`` answer as
    already visible, never decoded)."""
    if got == sent:
        return "equal"
    if not marker_present(got):
        # Round 11 LOW-004: a rich-text answer escaped twice decodes once
        # to ``&lt;``; D4 decodes once, so name it rather than "rejected".
        if (
            rich
            and isinstance(got, str)
            and _collapse(MARKER_TEXT) in _collapse(html.unescape(_html_text(got)))
        ):
            return "double-escaped"
        return "rejected"
    if not rich and isinstance(got, str) and _collapse(MARKER_TEXT) not in _collapse(got):
        return "html-escaped"
    return "sanitised"


class Position(NamedTuple):
    section: int
    question: int

    def label(self) -> str:
        return f"section {self.section + 1}, question {self.question + 1}"


def sections_of(content: object) -> list[dict[str, Any]] | None:
    """The ``sections`` list when every section is an object with a
    ``questions`` list of objects; else None."""
    if not isinstance(content, dict):
        return None
    sections = content.get("sections")
    if not isinstance(sections, list):
        return None
    for section in sections:
        if not isinstance(section, dict):
            return None
        found = section.get("questions")
        if not isinstance(found, list) or not all(isinstance(q, dict) for q in found):
            return None
    return sections


def questions(content: dict[str, Any]) -> Iterator[tuple[Position, dict[str, Any]]]:
    for i, section in enumerate(sections_of(content) or []):
        for j, question in enumerate(section["questions"]):
            yield Position(i, j), question


def question_at(content: dict[str, Any], position: Position) -> dict[str, Any] | None:
    sections = sections_of(content) or []
    if position.section >= len(sections):
        return None
    found = sections[position.section]["questions"]
    return found[position.question] if position.question < len(found) else None


def structure(content: dict[str, Any]) -> object:
    """Section and question names and types, for comparison only."""
    return [
        (section.get("name"), [(q.get("name"), q.get("type")) for q in section["questions"]])
        for section in sections_of(content) or []
    ]


def with_answers(content: dict[str, Any], answers: dict[Position, str]) -> dict[str, Any]:
    """A deep copy of ``content`` with the given answers replaced."""
    out = copy.deepcopy(content)
    for position, value in answers.items():
        out["sections"][position.section]["questions"][position.question]["answer"] = value
    return out


def partial_content(content: dict[str, Any], position: Position, value: str) -> dict[str, Any]:
    """Only the one question (with ``value``) inside its section."""
    section = content["sections"][position.section]
    question = {**copy.deepcopy(section["questions"][position.question]), "answer": value}
    kept = {k: copy.deepcopy(v) for k, v in section.items() if k != "questions"}
    return {"sections": [{**kept, "questions": [question]}]}


def _open_draft(note: dict[str, Any]) -> bool:
    return (
        note.get("draft") is True
        and "finalized_at" in note
        and note["finalized_at"] is None
        and note.get("archived_at") is None
        and note.get("deleted_at") is None
    )


def _first(content: dict[str, Any], kind: str) -> Position | None:
    return next((p for p, q in questions(content) if q.get("type") == kind), None)


def _blind_axes(position: Position) -> int:
    """How many array levels the partial body cannot test at ``position``: it
    always carries the test question as question 0 of section 0."""
    return (position.section == 0) + (position.question == 0)


def rich_target(content: dict[str, Any]) -> Position | None:
    """The rich-text test question: of the ``paragraph`` questions in a
    section that holds other questions too, the first one displaced on both
    array levels (section index and question index both ≥ 1), else on one,
    else the first; with no such section, the first ``paragraph``. Only a
    section with other questions can show whether a partial body replaces
    the section it names (round 10 MED-002), and only a displaced index can
    show whether that level is matched by position — the partial body
    always carries the question as question 0 of section 0 (round 11
    MED-001, codex round 12 PR-MED-028)."""
    sections = sections_of(content) or []
    shared = [
        p
        for p, q in questions(content)
        if q.get("type") == RICH and len(sections[p.section]["questions"]) > 1
    ]
    if not shared:
        return _first(content, RICH)
    return min(shared, key=_blind_axes)  # the first of the least blind


def _tests_phrase(targets: Collection[Position]) -> str:
    """How the prompts name the test questions: two, or the rich-text one
    alone when the note has no plain-text question."""
    return "the two test questions" if len(targets) > 1 else "the test question"


def _marker_or_original(now: object, original: object) -> bool:
    """A test question reads (as visible text) as its original answer or as
    exactly one of the markers the probe writes — nothing else."""
    if not isinstance(now, dict) or not isinstance(original, dict):
        return False
    render = rich_answer if original.get("type") == RICH else plain_answer
    allowed = {visible(original)} | {
        visible({**original, "answer": render(lines)})
        for lines in (MARKER_LINES, PARTIAL_MARKER_LINES)
    }
    return visible(now) in allowed


def _section_shared(content: dict[str, Any], position: Position) -> bool:
    sections = sections_of(content) or []
    return len(sections[position.section]["questions"]) > 1


def _type_word(question: dict[str, Any]) -> str:
    value = question.get("type")
    return value if isinstance(value, str) and _TYPE_WORD.fullmatch(value) else "<other>"


def _answer_kind(question: dict[str, Any]) -> str:
    if "answer" in question:
        value = question["answer"]
        if value is None:
            return "null"
        if isinstance(value, str):
            return "<empty>" if value == "" else "<text>"
        return "<other>"
    return "choices" if "answers" in question else "absent"


def describe(error: cc.ClinikoError) -> str:
    """Class, status and — for a 422 — the fixed categories; nothing else."""
    status = getattr(error, "status", None)
    text = type(error).__name__ + (f" (HTTP {status})" if isinstance(status, int) else "")
    categories = getattr(error, "categories", ())
    if categories:
        text += " categories: " + ", ".join(categories)
    return text


class _Stop(Exception):
    """A refusal or failure whose line is already printed."""


class TestWrite:
    """Task P.1's test write over one ``ClinikoCall`` (Flow 4)."""

    def __init__(
        self,
        call: cc.ClinikoCall,
        target: NoteTarget,
        *,
        surname: str,
        digits: str,
        out: Callable[[str], None],
        read_line: Callable[[str], str],
    ) -> None:
        self._call = call
        self._target = target
        self._surname = surname
        self._digits = digits
        self._out = out
        self._read_line = read_line
        self.maybe_written = False
        self.restored = False
        # The class of the last PATCH refusal that was NOT applied, or None.
        self.last_refusal: type[cc.ClinikoError] | None = None
        # The note was seen finalised or archived after the start: a marker
        # left in it may not be deletable by hand (round 10 LOW-008).
        self.note_locked = False

    # --- reads and the one write ---------------------------------------------

    def _fetch(self, label: str, get: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            answer = get()
        except cc.ClinikoError as error:
            self._out(f"GET {label}: {describe(error)}")
            raise _Stop() from None
        self._out(f"GET {label}: 200")
        return answer

    def _note(self, why: str = "") -> dict[str, Any]:
        """EVERY note read — the first and each one after a write — stops by
        name unless the answer carries the URL's note id (codex round 48
        PR-LOW-043, the app's SEC-002 check): a later body is what the next
        PATCH is built from, so another note's content never reaches one."""
        label = "/treatment_notes/<id>" + (f" ({why})" if why else "")
        note = self._fetch(label, lambda: self._call.get_treatment_note(self._target.note_id))
        if _valid_id(note.get("id")) != self._target.note_id:
            raise self._refuse("the note Cliniko returned is not the URL's note")
        return note

    def _content(self, why: str = "") -> dict[str, Any]:
        """The draft leg's every note read after the start: it stops by name
        unless the note is STILL an open draft (round 9 MED-003 — Finalise is
        one click in the editor the practitioner is using between reads)."""
        note = self._note(why)
        if not _open_draft(note):
            self.note_locked = True
            raise self._refuse(
                "the note is no longer an open draft (finalised or archived in Cliniko)"
            )
        content = note.get("content")
        if sections_of(content) is None:
            self._out("  the note's content has no sections/questions list")
            raise _Stop()
        assert isinstance(content, dict)
        return content

    def _patch(self, content: dict[str, Any], label: str) -> None:
        # The body is built and encoded BEFORE the flag: a failure here sent
        # nothing (round 9 LOW-009).
        draft = cc.DraftContent.model_validate({"content": content})
        draft.to_body()
        before = self.maybe_written
        self.maybe_written = True  # from here the marker may be in the note
        self.last_refusal = None
        try:
            self._call.write_draft_note(self._target.note_id, draft)
        except cc.ClinikoError as error:
            self._out(f"PATCH /treatment_notes/<id> ({label}): {describe(error)}")
            if isinstance(error, _NOT_APPLIED):
                self.maybe_written = before
                self.last_refusal = type(error)
            raise _Stop() from None
        self._out(f"PATCH /treatment_notes/<id> ({label}): 200")

    # --- the checks both legs share ----------------------------------------------

    def _refuse(self, reason: str) -> _Stop:
        self._out(f"Refused: {reason}.")
        return _Stop()

    def verify(self, *, want_final: bool) -> dict[str, Any]:
        call, target = self._call, self._target
        user = self._fetch("/user", call.get_user)
        user_id = _valid_id(user.get("id"))
        if user_id is None:
            raise self._refuse("the key user has no usable id")
        found = self._fetch(
            "/practitioners?q[]=user_id:=<id>",
            lambda: call.get_practitioners_for_user(user_id),
        )
        records = found.get("practitioners")
        practitioner_ids = {
            str(r["id"])
            for r in (records if isinstance(records, list) else [])
            if isinstance(r, dict) and "id" in r
        }
        note = self._note()
        draft = note.get("draft")
        if not isinstance(draft, bool) or "finalized_at" not in note:
            raise self._refuse("the note carries no draft / finalized_at fields")
        is_final = not draft or note["finalized_at"] is not None
        if note.get("archived_at") is not None or note.get("deleted_at") is not None:
            raise self._refuse("the note is archived")
        if want_final and not is_final:
            raise self._refuse(
                "the note is not finalised - this leg needs a note you finalised by hand"
            )
        if not want_final and is_final:
            raise self._refuse("the note is finalised - the test write needs an open draft")
        # The note's own id was checked by ``_note`` (every read).
        if _link_id(note, "patient") != target.patient_id:
            raise self._refuse("the note's patient is not the URL's patient")
        if _link_id(note, "practitioner") not in practitioner_ids:
            raise self._refuse("the note's practitioner is not the key user's practitioner")
        if target.note_id[-4:] != self._digits:
            raise self._refuse("the last four digits do not match the note's id")
        patient = self._fetch("/patients/<id>", lambda: call.get_patient(target.patient_id))
        surname = patient.get("last_name")
        if not isinstance(surname, str) or not surname or _fold(surname) != _fold(self._surname):
            raise self._refuse("the surname does not match the note's patient")
        return note

    def _print_questions(self, content: dict[str, Any], label: str) -> None:
        for position, question in questions(content):
            self._out(
                f"  {label} {position.label()}: {_type_word(question)}, "
                f"answer {_answer_kind(question)}"
            )

    def _print_template(self, note: dict[str, Any]) -> None:
        """Question 3: the template's question structure and whether each
        question carries a default answer."""
        template_id = _link_id(note, "treatment_note_template")
        label = "GET /treatment_note_templates/<id>"
        if template_id is None:
            self._out(f"{label}: skipped (the note links no template)")
            return
        try:
            template = self._call.get_treatment_note_template(template_id)
        except cc.ClinikoError as error:
            self._out(f"{label}: {describe(error)}")
            return
        self._out(f"{label}: 200")
        self._out(json.dumps(shape(template), indent=2, sort_keys=True))
        inner = template.get("content")
        content = inner if sections_of(inner) is not None else template
        if sections_of(content) is None:
            self._out("  the template carries no sections/questions list")
            return
        assert isinstance(content, dict)
        for position, question in questions(content):
            self._out(
                f"  template {position.label()}: {_type_word(question)}, "
                f"default answer {_answer_kind(question)}"
            )

    # --- the draft leg ---------------------------------------------------------------

    def run_write(self) -> int:
        out = self._out
        note = self.verify(want_final=False)
        original = note.get("content")
        if sections_of(original) is None:
            raise self._refuse("the note's content has no sections/questions list")
        assert isinstance(original, dict)
        rich, plain = rich_target(original), _first(original, PLAIN)
        self._print_questions(original, "note")
        self._print_template(note)
        if rich is None:
            raise self._refuse("the note needs a rich-text (paragraph) question")
        targets = {rich: rich_answer(MARKER_LINES)}
        if plain is None:
            # Smoke 2026-09-29 (practitioner decision): a template with no
            # plain-text question is tested on its rich-text question alone.
            out(
                "  the note has no plain-text (text) question: only the rich-text question "
                "is tested, so this run gives no plain-text results"
            )
            where = f"the rich-text question ({rich.label()})"
        else:
            targets[plain] = plain_answer(MARKER_LINES)
            where = (
                f"the rich-text question ({rich.label()}) and the plain-text question "
                f"({plain.label()})"
            )
        out(f"Test marker: {MARKER_LINES!r}")
        out(
            f"Will write it into {where}, re-read the note, pause four times for you to use "
            "the Cliniko editor, and put the original content back only if nothing else "
            "has changed."
        )
        if self._read_line("Type yes to write the test marker: ").strip() != "yes":
            raise self._refuse("no yes was typed")
        # Round 10 LOW-005: the pause at the prompt is time in the editor too.
        if self._content("before the first write") != original:
            raise self._refuse("the note changed since it was checked - run the probe again")

        # Questions 1 and 4: the write, the echo, the untargeted questions.
        self._patch(with_answers(original, targets), "test marker")
        after = self._content()
        for position, sent in targets.items():
            kind = "rich-text" if position == rich else "plain-text"
            got = (question_at(after, position) or {}).get("answer")
            echo = echo_class(sent, got, rich=position == rich)
            out(f"  {kind} question ({position.label()}): {echo}")
        others = [p for p, _q in questions(original) if p not in targets]
        same_shape = structure(after) == structure(original)
        byte_same = same_shape and all(
            question_at(after, p) == question_at(original, p) for p in others
        )
        seen_same = same_shape and all(
            visible(question_at(after, p)) == visible(question_at(original, p)) for p in others
        )
        out(f"  every other question byte-identical: {_yes(byte_same)}")
        out(f"  every other question visibly identical: {_yes(seen_same)}")

        # Question 5: the open editor.
        self._read_line(
            "Now save or edit the note in the open Cliniko editor, then press Enter: "
        )
        saved = self._content("after the editor save")
        for position in targets:
            kind = "rich-text" if position == rich else "plain-text"
            present = marker_present((question_at(saved, position) or {}).get("answer"))
            out(f"  marker still present in the {kind} question after the editor save: "
                f"{_yes(present)}")

        # Question 6, then question 2.
        self._window_pass(original, targets, rich, partial=False)
        self._window_pass(original, targets, rich, partial=True)
        return self._restore(original, set(targets), rich)

    def _window_pass(
        self,
        original: dict[str, Any],
        targets: dict[Position, str],
        rich: Position,
        *,
        partial: bool,
    ) -> None:
        out = self._out
        name = "partial body" if partial else "full body"
        out(f"Window pass ({name}):")
        first = self._content(f"{name}, before the pause")
        if structure(first) != structure(original):
            # Round 9 LOW-006: the positions were taken at the start; on a
            # changed note they could name another question's real answer.
            raise self._refuse("the note's questions changed since the start")
        if partial:
            body = partial_content(first, rich, rich_answer(PARTIAL_MARKER_LINES))
            prompt = (
                "Now, in the open Cliniko editor, change the text of a question OTHER than "
                f"{_tests_phrase(targets)}, save, then press Enter: "
            )
        else:
            body = with_answers(first, targets)
            prompt = (
                "Now, in the open Cliniko editor, change the text of a question OTHER than "
                f"{_tests_phrase(targets)} AND of the rich-text test question "
                f"({rich.label()}), save, then press Enter: "
            )
        self._read_line(prompt)
        seen = self._content(f"{name}, to see your edits")
        if structure(seen) != structure(first):
            # Round 10 LOW-009: the body was built from ``first``.
            raise self._refuse("the note's questions changed during the pause")
        edited = [
            p
            for p, q in questions(seen)
            if p not in targets and visible(q) != visible(question_at(first, p))
        ]
        target_edited = visible(question_at(seen, rich)) != visible(question_at(first, rich))
        out(f"  edits seen before the write: another question {_yes(bool(edited))}; "
            f"the rich-text test question {_yes(target_edited)}")
        self._patch(body, name)
        after = self._content(f"{name}, after the write")
        kept_shape = structure(after) == structure(seen)
        if edited:
            survived = kept_shape and all(
                visible(question_at(after, p)) == visible(question_at(seen, p)) for p in edited
            )
            out(f"  the other question's edit survived the write: {_yes(survived)}")
        else:
            out("  (no edit to another question was seen before the write)")
        if not partial and target_edited:
            kept = kept_shape and visible(question_at(after, rich)) == visible(
                question_at(seen, rich)
            )
            out(f"  the rich-text test question's edit survived the write: {_yes(kept)} "
                "(expected: no)")
        elif not partial:
            out("  (no edit to the rich-text test question was seen before the write)")
        if partial:
            untouched = kept_shape and all(
                visible(q) == visible(question_at(seen, p))
                for p, q in questions(after)
                if p != rich
            )
            out(f"  Cliniko kept every other question as it was: {_yes(untouched)}")
            landed = kept_shape and _collapse(PARTIAL_LINE) in visible(question_at(after, rich))
            out(f"  the partial write's own marker read back at the test question: "
                f"{_yes(landed)}")
            shared = _section_shared(first, rich)
            out(f"  the test question's section holds other questions: {_yes(shared)}")
            if not kept_shape:
                verdict = "REPLACED"
            elif untouched and not landed:
                # Codex round 12 PR-MED-027: a 200 that dropped the body.
                verdict = "IGNORED"
            else:
                verdict = "MERGED" if untouched else "unclear"
            # What this note could not tell apart from a merge: a replace of
            # the named section when it holds nothing else (round 10
            # MED-002); a level matched by position where the test question
            # sits at the index the partial body puts it anyway (round 11
            # MED-001, codex round 12 PR-MED-028).
            untested = [
                what
                for what, blind in (
                    ("a replace of the named section", not shared),
                    ("sections matched by position", rich.section == 0),
                    ("questions matched by position", rich.question == 0),
                )
                if blind
            ]
            if verdict == "MERGED" and untested:
                verdict = f"MERGED (not ruled out: {'; '.join(untested)})"
            out(f"  partial content (question 2): {verdict}")

    def _restore(
        self, original: dict[str, Any], targets: set[Position], rich: Position
    ) -> int:
        """The restore condition is: the structure unchanged and every
        UNTARGETED question as at the start. The test questions (two, or the
        rich-text one alone) are the probe's own and are restored whatever
        they hold — the full pass has
        the practitioner edit the rich-text one, and saving the open editor
        at this pause can write that edit back — so for each it only REPORTS
        whether it held anything but a marker or its original answer (codex
        round 12 PR-MED-026, narrowed)."""
        out = self._out
        self._read_line(
            "Before the restore: in the Cliniko editor, put back any text you changed in "
            f"questions OTHER than {_tests_phrase(targets)}, save, CLOSE the editor tab, "
            "then press Enter: "
        )
        now = self._content("before the restore")
        same_shape = structure(now) == structure(original)
        others_same = same_shape and all(
            visible(q) == visible(question_at(original, p))
            for p, q in questions(now)
            if p not in targets
        )
        out(f"  structure unchanged since the start: {_yes(same_shape)}")
        out(f"  every other question reads as at the start: {_yes(others_same)}")
        if same_shape:
            for position in sorted(targets):
                kind = "rich-text" if position == rich else "plain-text"
                clean = _marker_or_original(
                    question_at(now, position), question_at(original, position)
                )
                out(
                    f"  the {kind} test question held only a marker or its original "
                    f"answer: {_yes(clean)}"
                )
        if not others_same:
            out(
                f"Not restored: something besides {_tests_phrase(targets)} differs from the "
                "start."
            )
            if not same_shape:
                out(
                    "The note's questions no longer match the start - the partial write may "
                    "have removed some. Re-enter anything missing by hand in Cliniko."
                )
            return 2
        self._patch(original, "restore")
        back = self._content("after the restore")
        restored = structure(back) == structure(original) and all(
            visible(q) == visible(question_at(original, p)) for p, q in questions(back)
        )
        out(f"  the note reads as at the start: {_yes(restored)}")
        if not restored:
            return 2
        self.restored = True
        out("Restored the original content.")
        return 0

    # --- the finalised leg --------------------------------------------------------------

    def run_final(self) -> int:
        out = self._out
        note = self.verify(want_final=True)
        content = note.get("content")
        if sections_of(content) is None:
            raise self._refuse("the note's content has no sections/questions list")
        assert isinstance(content, dict)
        position = _first(content, RICH) or _first(content, PLAIN)
        self._print_questions(content, "note")
        if position is None:
            raise self._refuse("the note has no rich-text or plain-text question")
        question = question_at(content, position) or {}
        value = (
            rich_answer(MARKER_LINES) if question.get("type") == RICH
            else plain_answer(MARKER_LINES)
        )
        out(f"Test marker: {MARKER_LINES!r}")
        out(
            f"Will try to write it into the FINALISED note's {position.label()} "
            f"({_type_word(question)}); Cliniko is expected to refuse."
        )
        if self._read_line("Type yes to attempt the write: ").strip() != "yes":
            raise self._refuse("no yes was typed")
        try:
            self._patch(with_answers(content, {position: value}), "finalised note")
        except _Stop:
            if self.maybe_written:
                out("The outcome is unknown: the marker may be in the finalised note.")
                return 2
            if self.last_refusal is cc.ClinikoRejected:
                out("Cliniko refused the write to the finalised note, as expected.")
                return 0
            # Round 9 MED-004: a 401/403/404 is not by itself Cliniko refusing
            # a finalised note — a key without write permission looks the same
            # (round 10 LOW-006: the draft leg with this key decides which).
            out(
                "Cliniko refused the write, but not as a validation error. If --test-write "
                "wrote to a draft with this same key, this is Cliniko refusing the finalised "
                "note; if not, check the key's permissions."
            )
            return 2
        out("ALARM: Cliniko accepted a write into a FINALISED note.")
        return 2


def run_test_write(
    call: cc.ClinikoCall,
    target: NoteTarget,
    *,
    final: bool,
    surname: str,
    digits: str,
    out: Callable[[str], None],
    read_line: Callable[[str], str],
) -> tuple[int, bool]:
    """One leg; never raises. Returns the exit code and whether the marker
    may be left. ``MARKER LEFT`` is printed whenever a PATCH may have
    reached the note and the original content was not restored (``main``
    repeats it as the last line)."""
    session = TestWrite(
        call, target, surname=surname, digits=digits, out=out, read_line=read_line
    )
    try:
        code = session.run_final() if final else session.run_write()
    except _Stop:
        code = 2
    except (Exception, KeyboardInterrupt) as error:  # noqa: BLE001 - reported by class only
        out(f"Stopped: {type(error).__name__}")
        code = 2
    marker_left = session.maybe_written and not session.restored
    if marker_left:
        if final or session.note_locked:
            out(
                "The note is finalised or archived: if Cliniko will not let you delete the "
                "marker, archive the note."
            )
        out(MARKER_LEFT)
        code = code or 2
    elif code != 0:
        out("Nothing was written.")
    return code, marker_left


_MODES = {"--test-write": False, "--test-write-final": True}


def main(
    argv: list[str] | None = None,
    *,
    read_line: Callable[[str], str] = input,
    read_secret: Callable[[str], str] = getpass.getpass,
    out: Callable[[str], None] = print,
    transport: cc.Transport | None = None,
) -> int:
    args = sys.argv[1:] if argv is None else argv
    # Codex round 8 PR-MED-011: argparse's own rejection prints an unknown
    # argument VERBATIM to stderr, so a key typed as an argument would be
    # echoed. Anything but ONE of -h/--help or the two test-write modes is
    # refused here, before argparse, with a fixed sentence that never
    # interpolates what was passed.
    if len(args) > 1 or any(arg not in ("-h", "--help", *_MODES) for arg in args):
        out(
            "This script takes no arguments other than --test-write or --test-write-final "
            "- the key is asked for, never passed. Nothing was sent; if you typed the key "
            "on the command line, clear it from your terminal history."
        )
        return 2
    mode = args[0] if args and args[0] in _MODES else None
    if mode is None:
        argparse.ArgumentParser(
            description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
        ).parse_args(args)
    apply_offline_env()
    assert_offline_env()

    email = read_line("Contact email for Cliniko's User-Agent: ").strip()
    try:
        client = cc.ClinikoClient(contact_email=email, transport=transport)
    except cc.InvalidContactEmail:
        out("That is not a plain email address; nothing was sent.")
        return 2
    target = parse_note_url(read_line("Paste the open treatment note's URL: ").strip())
    if target is None:
        out("That is not a Cliniko treatment-note URL "
            "(https://<clinic>.<shard>.cliniko.com/patients/<id>/treatment_notes/<id>...); "
            "nothing was sent.")
        return 2
    surname = digits = ""
    if mode is not None:
        surname = read_line("The dummy patient's surname (compared, never printed): ").strip()
        digits = read_line(
            "The last four digits of the note's id (compared, never printed): "
        ).strip()
    held = [read_secret("Cliniko API key (not shown): ").strip()]

    code = 0
    marker_left = False
    try:
        with client.call(held.pop) as call:
            if mode is None:
                Probe(call, out).run(target)
            else:
                code, marker_left = run_test_write(
                    call,
                    target,
                    final=_MODES[mode],
                    surname=surname,
                    digits=digits,
                    out=out,
                    read_line=read_line,
                )
    except cc.InvalidKey:
        out("The key is not in Cliniko's format or names an unknown shard; nothing was sent.")
        return 2
    except cc.CredentialsRejected:
        out("No key was entered; nothing was sent.")
        return 2
    out("Done. Paste everything above into Task P.1's Done note - it holds no patient data.")
    if marker_left:
        out(MARKER_LEFT)  # round 9 LOW-010: the warning is the last line
    return code


if __name__ == "__main__":
    sys.exit(main())
