"""Cliniko draft-write plan Task 5.1: the write's microcopy dictionary.

What is pinned here:
- ``WRITE_LINES`` is EXACTLY the plan's keys and wording (plus D5/D9's
  ``write_pending``), every line plain text: no exclamation mark, no newline,
  every placeholder one of ``{reason}`` / ``{seconds}`` / ``{cause}``.
- Every refusal name the write can meet resolves to a line: every
  ``encounter.WritebackRefusal`` through ``writeback_refusal_line`` and every
  ``encounter.NoteRefusal`` through ``note_refusal_line``, each inside
  ``check_failed``; every ``not_taken`` cause kind through
  ``not_taken_cause``. (The ``WriteOutcome`` names arrive with Task 3.4,
  whose test extends this enumeration.)
- ``write_line`` is the formatting boundary: a reason or cause from anywhere
  but the tables is refused (Constraint 9), a detail the line has no
  placeholder for is refused, seconds are whole and rounded up.
- The ``write_uncertain`` prefix (PR-MED-017): with ``uncertain`` every
  refusal line is preceded by it; the progress, success and in-flight lines,
  and the lines that already say the outcome is open, are not.
- ``custody_refusal_text`` names a write in flight by its line and leaves
  every other custody refusal as the screens always showed it.
"""

from __future__ import annotations

import re
import string

import pytest

from scribe_desktop.encounter import NoteRefusal, WritebackRefusal
from scribe_desktop.session import SessionActivityError, WriteInFlightError
from scribe_desktop.ui import models

# The plan's Task 5.1 wording, verbatim ("N s" is ``{seconds} s``, "<reason>"
# ``{reason}``, "<cause>" ``{cause}``), plus ``write_pending``.
_EXPECTED = {
    "ready": "Write draft to Cliniko",
    "checking": "Checking the note with Cliniko …",
    "writing": "Writing the draft to Cliniko …",
    "written_auto": (
        "Draft written to Cliniko. Reload the note page in Chrome to see it, then review "
        "and finalise it there."
    ),
    "written_seen": (
        "Draft written to Cliniko. Reload the note page in Chrome; press Complete once you "
        "can see it there."
    ),
    "written_done": (
        "Draft written to Cliniko and this recording is complete. Review and finalise the "
        "note in Cliniko."
    ),
    "not_saved": "Save the note first.",
    "unlinked": "This recording is not linked to a Cliniko note. Copy the note instead.",
    "mock_note": "This note came from the test provider and cannot be written to a chart.",
    "check_failed": (
        "The note could not be checked with Cliniko just now ({reason}). Copy the note, or "
        "try again."
    ),
    "rate_limited": "Cliniko is rate-limiting this clinic. Try again in {seconds} s.",
    "note_has_text": (
        "The Cliniko note already holds text. Copy the note and paste it in yourself."
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
    "write_pending": (
        "A write to Cliniko was attempted for this note, so it can no longer be changed "
        "or regenerated here. Copy it, complete the recording or discard it."
    ),
}

_DETAIL: dict[str, dict[str, object]] = {
    "check_failed": {"reason": models.writeback_refusal_line(WritebackRefusal.NOT_VERIFIED)},
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
            "note_not_found",
            "no_baseline",
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
            "written_auto",
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
        alone after an attempt whose outcome is open."""
        for key, template in models.WRITE_LINES.items():
            if re.search(r"\bCopy\b", template):
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
