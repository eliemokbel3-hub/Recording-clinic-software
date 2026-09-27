"""Read-only Cliniko feasibility probe (Cliniko workflow safeguards plan, Task 1.3).

The practitioner runs this ONCE per clinic (Task P.1) from a normal terminal
at the repository root, with a patient's treatment note open in Cliniko:

    .venv\\Scripts\\python.exe scripts\\probe-cliniko.py

It asks for the contact email (the User-Agent Cliniko requires), the open
note's URL, and the clinic's API key — the key through ``getpass`` only (not
echoed, never an argument, never an environment variable) — and then makes
READ-ONLY calls through the app's own client (``scribe_desktop.cliniko_client``:
GET only, the host pinned from the key's shard, TLS 1.2+, no redirects):
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
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import sys
from collections.abc import Callable
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
    # echoed. Anything but -h/--help is refused here, before argparse, with a
    # fixed sentence that never interpolates what was passed.
    if any(arg not in ("-h", "--help") for arg in args):
        out(
            "This script takes no arguments - the key is asked for, never passed. "
            "Nothing was sent; if you typed the key on the command line, clear it "
            "from your terminal history."
        )
        return 2
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
    held = [read_secret("Cliniko API key (not shown): ").strip()]

    try:
        with client.call(held.pop) as call:
            Probe(call, out).run(target)
    except cc.InvalidKey:
        out("The key is not in Cliniko's format or names an unknown shard; nothing was sent.")
        return 2
    except cc.CredentialsRejected:
        out("No key was entered; nothing was sent.")
        return 2
    out("Done. Paste everything above into Task P.1's Done note - it holds no patient data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
