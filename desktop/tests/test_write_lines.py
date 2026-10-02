"""Cliniko draft-write plan Task 5.1: the write's microcopy dictionary.

What is pinned here:
- ``WRITE_LINES`` is EXACTLY the plan's keys and wording (plus D5/D9's
  ``write_pending``, the Task 2.1 additions and Task 7.3's D15 changes:
  ``note_unreadable`` in, ``note_has_text`` and the three own-defaults lines
  out; ``written_auto`` went with seen-mode completion), every line plain
  text: no exclamation mark, no newline, every placeholder one of
  ``{reason}`` / ``{seconds}`` / ``{cause}``.
- Every refusal name the write can meet resolves to a line: every
  ``encounter.WritebackRefusal`` through ``writeback_refusal_line`` and every
  ``encounter.NoteRefusal`` through ``note_refusal_line``, each inside
  ``check_failed``; every ``not_taken`` cause kind through
  ``not_taken_cause``; each ``NoteRefusal`` in exactly one of
  ``check_refused`` / ``check_failed``; every ``draft_write.WriteRefusalName``
  through ``write_refusal_line``. (The ``WriteRefusalName`` and
  ``WriteOutcome`` enumerations are in ``test_draft_write.py``.)
- ``write_line`` is the formatting boundary: a reason or cause from anywhere
  but the tables is refused (Constraint 9), a detail the line has no
  placeholder for is refused, seconds are whole and rounded up.
- The ``write_uncertain`` prefix (PR-MED-017): with ``uncertain`` every
  refusal line is preceded by it; the progress, success and in-flight lines,
  and the lines that already say the outcome is open, are not;
  ``write_prefixed`` puts the same prefix on a line from outside the
  dictionary (the session lock's).
- ``custody_refusal_text`` names a write in flight, and any
  ``WriteLineRefusal`` (``WritePendingError``), by its line, leaves every
  other ``SessionControllerError`` and every ``AudioCaptureError`` as the
  screens always showed them, and
  shows any other error as ``CUSTODY_UNEXPECTED_REASON`` alone (round 49
  PR-LOW-044: never its message or type).
- ``write_control`` (Task 5.2, the Note tab's ``_write_ready``) takes its
  standing reasons in order — not saved, unlinked, mock, then the record,
  then (dev channel only, ``test_dev_write_guard.py``) the dev write guard —
  and ``write_record_block`` is the one record-status mapping the button and
  the main window's slot share.
"""

from __future__ import annotations

import re
import string
from typing import get_args

import pytest

from scribe_desktop.audio_capture import AudioCaptureError, CaptureOverflowError, DeviceLostError
from scribe_desktop.draft_write import WriteRefusal, WriteRefusalName
from scribe_desktop.encounter import NoteRefusal, WritebackRefusal, WritebackRefused
from scribe_desktop.session import SessionActivityError, WriteInFlightError
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.ui import models

# The plan's Task 5.1 wording, verbatim ("N s" is ``{seconds} s``, "<reason>"
# ``{reason}``, "<cause>" ``{cause}``), plus ``write_pending``.
_EXPECTED = {
    "ready": "Write draft to Cliniko",
    "checking": "Checking the note with Cliniko …",
    "writing": "Writing the draft to Cliniko …",
    "written_seen": (
        "Draft written to Cliniko. Reload the note page in Chrome; press Complete once you "
        "can see it there. If Cliniko says the note was updated elsewhere, choose Discard "
        "my changes."
    ),
    "written_done": (
        "Draft written to Cliniko and this recording is complete. Past sessions shows what "
        "was kept. Review and finalise the note in Cliniko."
    ),
    "not_saved": "Save the note first.",
    "unlinked": "This recording is not linked to a Cliniko note. Copy the note instead.",
    "mock_note": "This note came from the test provider and cannot be written to a chart.",
    # Installation plan Task 1.6 (D4).
    "dev_build_writes_off": (
        "Writing to Cliniko is off in this developer build. To allow it, tick \"Allow "
        "Cliniko writes from this developer build\" on the Status tab, or copy the note "
        "instead."
    ),
    "check_failed": (
        "The note could not be checked with Cliniko just now ({reason}). Copy the note, or "
        "try again."
    ),
    "rate_limited": "Cliniko is rate-limiting this clinic. Try again in {seconds} s.",
    "note_unreadable": (
        "A question in the Cliniko note holds something the app cannot read, so nothing "
        "was written. Copy the note instead."
    ),
    "write_uncertain": (
        "An earlier write may have reached Cliniko. Check the note there before copying "
        "anything."
    ),
    "nothing_to_write": (
        "This note has no content that maps to the Cliniko template, so there is nothing "
        "to write. Copy the note instead."
    ),
    "not_taken": "Cliniko did not take the draft ({cause}). Copy the note instead.",
    "record_unreadable": (
        "The record of this recording's earlier write cannot be read, so its outcome "
        "cannot be checked. Look at the note in Cliniko before copying anything."
    ),
    "unknown": (
        "The write did not confirm. Nothing is lost - press Write again to check the note "
        "before anything is sent."
    ),
    "write_in_flight": "A draft is being written to Cliniko. Wait for it to finish.",
    "recovery_busy": (
        "A recovered recording is still being processed. Wait for it to finish, then write."
    ),
    # Task 5.2's two (round 14 LOW-011; R22-07's nothing-sent case).
    "clinic_busy": (
        "A key check for this clinic is running on the Clinics tab. Wait for it to finish, "
        "then write."
    ),
    "not_sent": (
        "The write stopped on this computer before anything was sent to Cliniko. Copy the "
        "note, or try again."
    ),
    "write_pending": (
        "A write to Cliniko was attempted for this note, so it can no longer be changed "
        "or regenerated here. Copy it, complete the recording or discard it."
    ),
    # Task 5.1's Task 2.1 additions (R22-22, R22-20). " - " for the plan's
    # dash, as ``unknown`` already writes it.
    "check_refused": (
        "Cliniko shows that this note cannot take the draft ({reason}). Copy the note instead."
    ),
    "finalised_before_write": (
        "The note was finalised in Cliniko before the write reached it, so the draft was "
        "not written. Copy the note instead."
    ),
    "write_forbidden": (
        "Cliniko refused the write although the note is still a draft - this clinic's key "
        "may not be allowed to edit notes. Copy the note instead."
    ),
}

_DETAIL: dict[str, dict[str, object]] = {
    "check_failed": {"reason": models.writeback_refusal_line(WritebackRefusal.NOT_VERIFIED)},
    "check_refused": {"reason": models.note_refusal_line(NoteRefusal.NOTE_FINAL)},
    "rate_limited": {"seconds": 42},
    "not_taken": {"cause": models.not_taken_cause("note_not_found")},
}


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


class TestDictionary:
    def test_the_dictionary_is_exactly_the_plans_wording(self) -> None:
        assert dict(models.WRITE_LINES) == _EXPECTED

    def test_every_line_is_plain_text_with_only_the_named_placeholders(self) -> None:
        for key, template in models.WRITE_LINES.items():
            assert "!" not in template and "\n" not in template, key
            assert _fields(template) == set(_DETAIL.get(key, {})), key
            line = models.write_line(key, **_DETAIL.get(key, {}))
            assert "{" not in line and "}" not in line, key

    def test_a_missing_placeholder_is_never_shown_half_formatted(self) -> None:
        for key in _DETAIL:
            with pytest.raises(KeyError):
                models.write_line(key)


class TestTheFormattingBoundary:
    def test_a_reason_from_outside_the_refusal_tables_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            models.write_line("check_failed", reason="ConnectionError: api.au1.cliniko.com")

    def test_a_cause_from_outside_not_taken_cause_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cause"):
            models.write_line("not_taken", cause="the note says the patient is cured")

    def test_seconds_are_whole_and_rounded_up(self) -> None:
        assert models.write_line("rate_limited", seconds=59.2).endswith("Try again in 60 s.")
        assert models.write_line("rate_limited", seconds=0.01).endswith("Try again in 1 s.")
        assert models.write_line("rate_limited", seconds=0).endswith("Try again in 1 s.")
        for bad in ("soon", True, float("nan"), float("inf"), None):
            with pytest.raises(ValueError, match="seconds"):
                models.write_line("rate_limited", seconds=bad)

    def test_a_detail_the_line_has_no_placeholder_for_is_refused(self) -> None:
        """Round 16: never silently dropped — a caller expecting its detail
        in the line learns at once that it is not there."""
        cause = models.not_taken_cause("template_mismatch")
        with pytest.raises(ValueError, match="placeholder"):
            models.write_line("not_taken", cause=cause, question="Diagnosis")
        with pytest.raises(ValueError, match="placeholder"):
            models.write_line("ready", seconds=5)

    def test_only_the_causes_prefix_is_checked(self) -> None:
        """Residue, named (round 15): ``_is_write_cause`` checks the prefix;
        the suffix — a template question's label, the field categories — is
        trusted to ``not_taken_cause``'s callers. This pins the limit so a
        change to it is deliberate."""
        mismatch = models.NOT_TAKEN_CAUSES["template_mismatch"]
        line = models.write_line("not_taken", cause=f"{mismatch}: any trailing text")
        assert "any trailing text" in line
        with pytest.raises(ValueError, match="cause"):
            models.write_line("not_taken", cause=f"{mismatch} any trailing text")


class TestEveryRefusalResolves:
    def test_every_writeback_refusal_has_its_own_reason(self) -> None:
        assert set(models.WRITEBACK_REFUSAL_REASONS) == set(WritebackRefusal)
        assert len(set(models.WRITEBACK_REFUSAL_REASONS.values())) == len(WritebackRefusal)
        for reason in WritebackRefusal:
            text = models.writeback_refusal_line(reason)
            assert text and not text.endswith("."), reason
            assert f"({text})" in models.write_line("check_failed", reason=text)

    def test_every_note_refusal_resolves_inside_check_failed(self) -> None:
        for reason in NoteRefusal:
            text = models.note_refusal_line(reason)
            assert f"({text})" in models.write_line("check_failed", reason=text)

    def test_every_not_taken_cause_kind_resolves(self) -> None:
        assert set(models.NOT_TAKEN_CAUSES) == {
            "template_mismatch",
            "rejected",
            "key_rejected",
            "key_unavailable",
            "note_not_found",
        }
        causes = [models.not_taken_cause(kind) for kind in models.NOT_TAKEN_CAUSES]
        causes.append(models.not_taken_cause("template_mismatch", question="Diagnosis"))
        causes.append(models.not_taken_cause("rejected", categories=("content", "other")))
        for cause in causes:
            line = models.write_line("not_taken", cause=cause)
            assert f"({cause})" in line and "{" not in line, cause
        with pytest.raises(KeyError):
            models.not_taken_cause("no-such-cause")

    def test_the_cause_names_a_question_or_categories_only_when_given(self) -> None:
        mismatch = models.NOT_TAKEN_CAUSES["template_mismatch"]
        assert models.not_taken_cause("template_mismatch") == mismatch
        assert models.not_taken_cause("template_mismatch", question="Diagnosis") == (
            f"{mismatch}: Diagnosis"
        )
        assert models.not_taken_cause("rejected") == "Cliniko refused the content"
        assert models.not_taken_cause("rejected", categories=("content", "other")) == (
            "Cliniko refused these fields: content, other"
        )

    def test_a_rejected_key_is_sent_to_replace_key_like_the_note_check(self) -> None:
        """Validate would add the clinic again (a duplicate is refused); the
        Note check's own line for the same key already says Replace key."""
        assert "replace it on the Clinics tab" in models.not_taken_cause("key_rejected")
        assert models.not_taken_cause("key_rejected") == models.note_refusal_line(
            NoteRefusal.KEY_REJECTED
        )
        assert models.not_taken_cause("note_not_found") == models.note_refusal_line(
            NoteRefusal.NOTE_NOT_FOUND
        )


class TestUncertainPrefix:
    def test_every_refusal_line_is_prefixed_while_an_earlier_attempt_is_open(self) -> None:
        warning = models.WRITE_LINES["write_uncertain"]
        for key in models.WRITE_UNCERTAIN_PREFIXED:
            line = models.write_line(key, uncertain=True, **_DETAIL.get(key, {}))
            assert line.startswith(f"{warning} "), key
            assert line.endswith(models.write_line(key, **_DETAIL.get(key, {}))), key

    def test_the_progress_success_in_flight_and_open_outcome_lines_are_never_prefixed(
        self,
    ) -> None:
        unprefixed = set(models.WRITE_LINES) - models.WRITE_UNCERTAIN_PREFIXED
        assert unprefixed == {
            "ready",
            "checking",
            "writing",
            "written_seen",
            "written_done",
            "write_uncertain",
            "record_unreadable",
            "unknown",
            "write_in_flight",
        }
        for key in unprefixed:
            assert models.write_line(key, uncertain=True) == models.write_line(key)

    def test_the_prefixed_set_is_a_subset_of_the_dictionary(self) -> None:
        assert models.WRITE_UNCERTAIN_PREFIXED <= set(models.WRITE_LINES)

    def test_every_copy_inviting_line_is_prefixed(self) -> None:
        """PR-MED-017's point: a line that suggests Copy must never stand
        alone after an attempt whose outcome is open. Any case: the dev
        guard's line says "copy the note" mid-sentence (installation plan
        Task 1.6)."""
        for key, template in models.WRITE_LINES.items():
            if re.search(r"\bcopy\b", template, re.IGNORECASE):
                assert key in models.WRITE_UNCERTAIN_PREFIXED, key


class TestCustodyRefusalText:
    def test_a_write_in_flight_reads_as_its_line(self) -> None:
        assert models.custody_refusal_text(WriteInFlightError("complete")) == (
            models.write_line("write_in_flight")
        )

    def test_any_other_refusal_reads_as_before(self) -> None:
        exc = SessionActivityError("a discard is completing; the session cannot be completed")
        assert models.custody_refusal_text(exc) == (
            "SessionActivityError: a discard is completing; the session cannot be completed"
        )

    @pytest.mark.parametrize(
        "exc",
        [
            PermissionError(13, "Access is denied", r"C:\sessions\feedc0defeedc0de\key.dpapi"),
            StoreWriteError("transcript not durably readable: 'C:\\sessions\\feedc0defeedc0de'"),
            RuntimeError("feedc0defeedc0de"),
        ],
        ids=["os", "store", "runtime"],
    )
    def test_an_unexpected_error_reads_as_the_fixed_reason_only(
        self, exc: Exception
    ) -> None:
        """Round 49 PR-LOW-044 (Constraint 9): an error nobody authored may
        carry a session directory — its text and type never reach the line."""
        assert models.custody_refusal_text(exc) == models.CUSTODY_UNEXPECTED_REASON
        assert not models.CUSTODY_UNEXPECTED_REASON.endswith(".")  # callers add their own
        assert "!" not in models.CUSTODY_UNEXPECTED_REASON

    @pytest.mark.parametrize(
        "exc",
        [
            DeviceLostError("failed opening input device 3: Device unavailable"),
            CaptureOverflowError("capture queue overflowed"),
            AudioCaptureError("cannot resume a failed capture worker"),
        ],
        ids=["device-lost", "overflow", "capture"],
    )
    def test_a_capture_error_keeps_its_authored_text(self, exc: Exception) -> None:
        """Round 49 k5 watch-point: a capture error is authored (a device
        index and PortAudio's text, never a path) and is the microphone
        diagnostic at Start, so it reads as before."""
        assert models.custody_refusal_text(exc) == f"{type(exc).__name__}: {exc}"

    def test_a_failed_read_is_record_unreadable_and_a_foreign_line_takes_the_prefix(
        self,
    ) -> None:
        """Round 34 LOW-006: ``write_record_block(None)`` fails closed, and
        ``write_prefixed`` is ``write_line``'s own prefix."""
        assert models.write_record_block(None) == models.write_line("record_unreadable")
        locked = models.chrome_refusal_message("locked")
        assert models.write_prefixed(locked, uncertain=False) == locked
        assert models.write_prefixed(locked, uncertain=True) == (
            f"{models.WRITE_LINES['write_uncertain']} {locked}"
        )
        assert models.write_line("unlinked", uncertain=True) == models.write_prefixed(
            models.write_line("unlinked"), uncertain=True
        )

    def test_a_write_line_refusal_reads_as_its_line(self) -> None:
        """Task 5.2: ``WritePendingError`` (a ``WriteLineRefusal``) shows its
        line — never "WritePendingError: …"."""
        from scribe_desktop.ui.transcript import WritePendingError

        line = models.write_line("write_pending", uncertain=True)
        assert models.custody_refusal_text(WritePendingError(line)) == line
        assert models.custody_refusal_text(models.WriteLineRefusal(line)) == line


class TestWriteControl:
    """Task 5.2 (D2's ``_write_ready`` less in-flight / rendering): the
    order of the standing reasons and what each record status allows."""

    _BINDING = models.WriteBinding("s", True)

    def _control(self, **overrides: object) -> models.WriteControl:
        from scribe_desktop.draft_write import WriteRecordStatus

        fields: dict[str, object] = {
            "saved": True,
            "binding": self._BINDING,
            "mock": False,
            "status": WriteRecordStatus("none"),
            "channel": "production",
            "allow_dev_writes": False,
        }
        fields.update(overrides)
        return models.write_control(**fields)  # type: ignore[arg-type]

    def test_a_saved_linked_real_note_with_no_record_is_ready(self) -> None:
        assert self._control() == models.WriteControl(True)

    def test_the_reasons_come_in_order(self) -> None:
        unlinked = models.WriteBinding("s", False)
        assert self._control(saved=False, binding=unlinked, mock=True, status=None) == (
            models.WriteControl(False, models.write_line("not_saved"))
        )
        assert self._control(binding=unlinked, mock=True, status=None) == (
            models.WriteControl(False, models.write_line("unlinked"))
        )
        assert self._control(mock=True, status=None) == (
            models.WriteControl(False, models.write_line("mock_note"))
        )
        assert self._control(status=None) == (
            models.WriteControl(False, models.write_line("record_unreadable"))
        )

    @pytest.mark.parametrize(
        ("outcome", "matches", "expected"),
        [
            ("unreadable", False, (False, "record_unreadable")),
            ("written", True, (False, "written_seen")),
            ("written", False, (False, "write_uncertain")),
            ("attempting", True, (True, "unknown")),
            ("unknown", False, (True, "unknown")),
            ("refused", True, (True, None)),
        ],
    )
    def test_each_record_status(
        self, outcome: str, matches: bool, expected: tuple[bool, str | None]
    ) -> None:
        from scribe_desktop.draft_write import WriteRecordStatus

        ready, key = expected
        status = WriteRecordStatus(outcome, note_matches=matches)  # type: ignore[arg-type]
        control = self._control(status=status)
        # The shared mapping: it closes exactly the statuses the button does.
        assert models.write_record_block(status) == (
            None if ready else models.write_line(key)  # type: ignore[arg-type]
        )
        assert control == models.WriteControl(
            ready, models.write_line(key) if key is not None else None
        )


class TestTheTaskTwoOneAdditions:
    def test_every_write_refusal_name_resolves_to_a_line(self) -> None:
        """Task 7.3: every ``WriteRefusalName`` — ``note_unreadable`` among
        them — reads as a dictionary line, prefixed while an earlier attempt
        is open."""
        writeback = WritebackRefused(WritebackRefusal.NOT_VERIFIED)
        for name in get_args(WriteRefusalName):
            refusal = WriteRefusal(
                name,
                writeback=writeback if name == "writeback_refused" else None,
                question="Diagnosis" if name == "template_mismatch" else None,
                section="Examination" if name == "template_mismatch" else None,
            )
            line = models.write_refusal_line(refusal)
            assert line and "{" not in line and "!" not in line, name
        assert models.write_refusal_line(WriteRefusal("note_unreadable")) == (
            models.WRITE_LINES["note_unreadable"]
        )
        open_line = models.write_refusal_line(
            WriteRefusal("note_unreadable", earlier_attempt_open=True)
        )
        assert open_line == (
            f"{models.WRITE_LINES['write_uncertain']} {models.WRITE_LINES['note_unreadable']}"
        )

    def test_the_written_line_names_clinikos_discard_my_changes(self) -> None:
        """Task 7.3 (the P.2 smoke, step 3): an editor already open keeps the
        pre-write copy; its "updated elsewhere" dialog's Discard my changes
        keeps the written draft."""
        assert models.write_line("written_seen").endswith(
            "If Cliniko says the note was updated elsewhere, choose Discard my changes."
        )

    def test_the_retired_lines_are_gone(self) -> None:
        for key in (
            "note_has_text",
            "defaults_unreadable",
            "defaults_no_template",
            "defaults_unmatched",
        ):
            assert key not in models.WRITE_LINES, key
        assert "no_baseline" not in models.NOT_TAKEN_CAUSES
        assert not hasattr(models, "OWN_DEFAULTS_PROBLEMS")

    def test_write_label_cleans_and_clips_a_cliniko_label(self) -> None:
        """R22-07: the caller cleans first, so ``write_line`` never refuses
        a label Cliniko sent — a 300-character label and one holding line
        breaks both format."""
        separated = models.write_label("a b")
        assert separated == "a b"
        long = models.write_label("L" * 300)
        assert len(long) == models.WRITE_LABEL_CHARS and long.endswith("…")
        broken = models.write_label("Standard\nConsult ation‮")
        assert "\n" not in broken and " " not in broken and "‮" not in broken
        for label in (long, broken):
            cause = models.not_taken_cause("template_mismatch", question=label)
            assert label in models.write_line("not_taken", cause=cause)

    def test_a_note_refusal_is_either_permanent_or_worth_trying_again(self) -> None:
        """Task 5.1(e): each ``NoteRefusal`` reads as exactly one of
        ``check_refused`` (trying again cannot change it) and
        ``check_failed``."""
        assert models.PERMANENT_NOTE_REFUSALS == {
            NoteRefusal.NOTE_FINAL,
            NoteRefusal.NOTE_ARCHIVED,
            NoteRefusal.PATIENT_MISMATCH,
            NoteRefusal.WRONG_PRACTITIONER,
        }
        refused_head = models.WRITE_LINES["check_refused"].split("(")[0]
        failed_head = models.WRITE_LINES["check_failed"].split("(")[0]
        for reason in NoteRefusal:
            line = models.note_check_line(reason)
            permanent = reason in models.PERMANENT_NOTE_REFUSALS
            assert line.startswith(refused_head) is permanent, reason
            assert line.startswith(failed_head) is not permanent, reason
            assert "try again" not in line if permanent else "try again" in line
            assert models.note_check_line(reason, uncertain=True).startswith(
                models.WRITE_LINES["write_uncertain"]
            )

    def test_a_rejected_key_and_a_finalised_note_read_as_their_own_lines(self) -> None:
        final = models.note_check_line(NoteRefusal.NOTE_FINAL)
        assert final == models.write_line(
            "check_refused", reason=models.note_refusal_line(NoteRefusal.NOTE_FINAL)
        )
        assert models.write_line("finalised_before_write") != final
