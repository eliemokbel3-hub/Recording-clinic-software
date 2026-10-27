"""Validation-run7 plan D1 (Tasks 1.1-1.3): the JOINED-RUN fixture matrix
and THE 0.3.4 oracle.

The matrix is a set of small invented transcripts in which the recogniser
"split" one line into pieces — joined (a same-speaker piece ending in a
comma), broken by every named residue (a bare cut, a full stop, a speaker
change, a textless segment, a partly or wholly quoted piece, the
next-patient cut), with a ``high_risk_omission`` piece, a suspect piece, the
patient's split and no confirmed clinician. Each case carries, as plain
data written from D1's words, the ``clinician_line_omitted`` anchors per
joined run (0.3.5), the anchors 0.3.4's per-segment code drew, the
``[flagged]`` lines and the boundary. ``SplitCase.note`` builds the note with
the REAL checker's Check 4 and Check 6 warnings, as ``check_note`` emits them.

The ORACLE is 0.3.4's per-segment ``clinician_line_omissions``, kept here
verbatim (``clinician_line_anchors_v034``) with the chooser and the harness
credit 0.3.4 built on it (``flagged_v034``, ``credited_v034``). ONE oracle,
read by the chooser's both-rules C4 pin (Task 1.2) and by the harness's
re-derivation pin (Task 1.3): the product never imports it.

``every_small_tail`` (review round 14) widens those pins from the matrix's
cells to every three-piece tail over a closed set of piece kinds.

No clinical content: invented sentences only.
"""

from __future__ import annotations

import functools
import itertools
from datetime import UTC, datetime
from typing import Final, NamedTuple

from scribe_desktop.note import (
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteSpan,
    NoteWarning,
    SourceCoords,
    content_tokens,
    covered_words,
    reconstruct_span_text,
    spoken_by_confirmed_clinician,
    transcript_digest,
)
from scribe_desktop.note_check import (
    clinician_line_omissions,
    next_patient_warnings,
    omission_warnings,
)
from scribe_desktop.note_config import NoteConfig, next_patient_boundary
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import (
    SPEAKER_1,
    SPEAKER_2,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
)
from scribe_desktop.ui.models import next_patient_segment

SESSION_ID: Final = "c" * 32
NOW: Final = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)
CONFIG: Final = NoteConfig()
CLINICIAN: Final = SPEAKER_2
PATIENT: Final = SPEAKER_1

Span = tuple[int, int, int]


def split_document(
    *turns: tuple[str, str], suspect: tuple[int, ...] = ()
) -> TranscriptDocument:
    """``turns`` are ``(text, speaker)``, one segment each; every word of a
    ``suspect`` segment is marked suspect (the guard marks a whole segment).
    ``""`` is a textless segment."""
    segments = []
    for index, (text, speaker) in enumerate(turns):
        words = tuple(
            TranscriptWord(
                word_text=token,
                start_seconds=position * 0.3,
                end_seconds=position * 0.3 + 0.25,
                probability=0.9,
                uncertain=False,
                suspect=index in suspect,
            )
            for position, token in enumerate(text.split())
        )
        segments.append(
            TranscriptSegment(
                start_seconds=float(index * 10),
                end_seconds=float(index * 10 + 5),
                speaker=speaker,
                transcript_words=words,
            )
        )
    return TranscriptDocument(
        session_id=SESSION_ID,
        created_at=NOW,
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=tuple(segments),
    )


def quoted_note(
    document: TranscriptDocument,
    spans: tuple[Span, ...],
    *,
    clinician: str | None = CLINICIAN,
    warnings: tuple[NoteWarning, ...] = (),
) -> GeneratedNote:
    """A note quoting ``spans`` (``(segment, first, last)``), one transcript
    line each, carrying ``warnings`` as given."""
    assertions = []
    for number, (segment, first, last) in enumerate(spans):
        source = document.transcript_segments[segment]
        assertions.append(
            NoteAssertion(
                assertion_id=f"t{number:04d}",
                section_key="presenting_complaint",
                speaker=source.speaker,
                note_span=NoteSpan(
                    span_text=reconstruct_span_text(source.transcript_words[first : last + 1]),
                    provenance="transcript",
                    source_coords=SourceCoords(segment, first, last),
                ),
            )
        )
    return GeneratedNote(
        session_id=SESSION_ID,
        created_at=NOW,
        template_profile_id="clinic-a",
        provider_name="extractive-v1",
        clinician_speaker=clinician,
        transcript_digest=transcript_digest(document),
        config_digest=CONFIG.config_digest(),
        note_sections=(
            (
                GeneratedSection(
                    section_key="presenting_complaint", note_assertions=tuple(assertions)
                ),
            )
            if assertions
            else ()
        ),
        note_warnings=warnings,
    )


def checked_note(
    document: TranscriptDocument,
    spans: tuple[Span, ...] = (),
    *,
    clinician: str | None = CLINICIAN,
) -> GeneratedNote:
    """``quoted_note`` carrying the REAL checker's Check 4 (both codes) and
    Check 6 warnings, in ``check_note``'s order."""
    bare = quoted_note(document, spans, clinician=clinician)
    warnings = (
        *omission_warnings(bare, document),
        *clinician_line_omissions(bare, document, CONFIG),
        *next_patient_warnings(document, CONFIG),
    )
    return quoted_note(document, spans, clinician=clinician, warnings=warnings)


class SplitCase(NamedTuple):
    """One matrix cell. ``lines`` / ``lines_v034``: the
    ``clinician_line_omitted`` anchors under 0.3.5's per-run code and under
    0.3.4's per-segment oracle; ``flagged``: the ``[flagged]`` lines under
    0.3.5 (``ui.models.flagged_segments``); ``boundary``: the cut."""

    name: str
    turns: tuple[tuple[str, str], ...]
    lines: tuple[int, ...]
    lines_v034: tuple[int, ...]
    flagged: frozenset[int]
    quoted: tuple[Span, ...] = ()
    clinician: str | None = CLINICIAN
    suspect: tuple[int, ...] = ()
    boundary: int | None = None

    def document(self) -> TranscriptDocument:
        return split_document(*self.turns, suspect=self.suspect)

    def note(self) -> GeneratedNote:
        return checked_note(self.document(), self.quoted, clinician=self.clinician)


# The clinician's uncued advice line, split three ways. Lower case throughout
# the clinician's pieces: a capitalised word would be name-like (Check 4's
# first code), and none of them holds a side, number, dose, negation,
# medication, hedge, closing or greeting.
_A, _B, _C = "please keep walking", "every single morning", "and rest after"
# Lines 0-1 of the boundary cells: clinical content before the closing (D2's
# head-case guard), both quoted, so neither draws Check 4.
_KNEE = ("My left knee is sore.", PATIENT)
_EXAM = ("On examination the knee is tender to touch.", CLINICIAN)
_QUOTE_HEAD: Final[tuple[Span, ...]] = ((0, 0, 4), (1, 0, 7))

SPLIT_CASES: Final[tuple[SplitCase, ...]] = (
    SplitCase(
        "comma-split",
        (
            ("My knee is sore.", PATIENT),
            (f"{_A},", CLINICIAN),
            (f"{_B},", CLINICIAN),
            (f"{_C}.", CLINICIAN),
            ("Okay.", PATIENT),
        ),
        lines=(1,),
        lines_v034=(1, 2, 3),
        flagged=frozenset({1, 2, 3}),
    ),
    SplitCase(
        "bare-cut",
        ((_A, CLINICIAN), (f"{_B}.", CLINICIAN)),
        lines=(0, 1),
        lines_v034=(0, 1),
        flagged=frozenset({0, 1}),
    ),
    SplitCase(
        "full-stop",
        ((f"{_A}.", CLINICIAN), (f"{_B}.", CLINICIAN)),
        lines=(0, 1),
        lines_v034=(0, 1),
        flagged=frozenset({0, 1}),
    ),
    SplitCase(
        "speaker-change",
        ((f"{_A},", CLINICIAN), (f"{_B},", PATIENT), (f"{_C}.", CLINICIAN)),
        lines=(0, 2),
        lines_v034=(0, 2),
        flagged=frozenset({0, 2}),
    ),
    SplitCase(
        "textless-between",
        ((f"{_A},", CLINICIAN), ("", CLINICIAN), (f"{_B}.", CLINICIAN)),
        lines=(0, 2),
        lines_v034=(0, 2),
        flagged=frozenset({0, 2}),
    ),
    SplitCase(
        "partly-quoted-piece",
        ((f"{_A},", CLINICIAN), (f"{_B}.", CLINICIAN)),
        lines=(1,),
        lines_v034=(1,),
        flagged=frozenset({1}),
        quoted=((0, 0, 1),),
    ),
    SplitCase(
        "quoted-first-piece",
        ((f"{_A},", CLINICIAN), (f"{_B},", CLINICIAN), (f"{_C}.", CLINICIAN)),
        lines=(1,),
        lines_v034=(1, 2),
        flagged=frozenset({1, 2}),
        quoted=((0, 0, 2),),
    ),
    SplitCase(
        # The 65 pieces of run 6's heldout-3 load "beside a high_risk_omission
        # piece": no second code for the run (one remedy, add the line), and
        # the first code's anchor marks every piece.
        "high-risk-piece",
        ((f"{_A},", CLINICIAN), ("2 times every morning,", CLINICIAN), (f"{_C}.", CLINICIAN)),
        lines=(),
        lines_v034=(0, 2),
        flagged=frozenset({0, 1, 2}),
    ),
    SplitCase(
        # The run's content is on its second piece; the anchor is the run's
        # first piece, every word of it suspect.
        "suspect-first-piece",
        ((f"{_A},", CLINICIAN), (f"{_B}.", CLINICIAN)),
        lines=(0,),
        lines_v034=(1,),
        flagged=frozenset({0, 1}),
        suspect=(0,),
    ),
    SplitCase(
        "patient-split",
        ((f"{_A},", PATIENT), (f"{_B}.", PATIENT)),
        lines=(),
        lines_v034=(),
        flagged=frozenset(),
    ),
    SplitCase(
        "no-confirmed-clinician",
        ((f"{_A},", CLINICIAN), (f"{_B},", CLINICIAN), (f"{_C}.", CLINICIAN)),
        lines=(),
        lines_v034=(),
        flagged=frozenset(),
        clinician=None,
    ),
    SplitCase(
        # The closing (3) joins the advice piece before it; the greeting (4)
        # is the cut, so the run 2-3 is truncated there, never dropped, and
        # the clinician's greeting piece past it draws nothing new. The
        # patient's "right" past the cut keeps its own mark.
        "boundary-truncates",
        (
            _KNEE,
            _EXAM,
            (f"{_A},", CLINICIAN),
            ("okay, see you next week,", CLINICIAN),
            ("hello, come on in,", CLINICIAN),
            ("My right shoulder hurts.", PATIENT),
        ),
        lines=(2,),
        lines_v034=(2, 3),
        flagged=frozenset({2, 3, 5}),
        quoted=_QUOTE_HEAD,
        boundary=4,
    ),
    SplitCase(
        # Peer round 1 PR-MED-001: the clinician's wholly uncovered
        # high_risk_omission anchors AT (3) and PAST (4) the cut keep their
        # own marks, and the run past the cut is never expanded.
        "tail-anchors",
        (
            _KNEE,
            _EXAM,
            ("okay, see you next week.", CLINICIAN),
            ("hello, come in, take 2 tablets,", CLINICIAN),
            ("and walk on the left side.", CLINICIAN),
        ),
        lines=(2,),
        lines_v034=(2,),
        flagged=frozenset({2, 3, 4}),
        quoted=_QUOTE_HEAD,
        boundary=3,
    ),
)


# ---------------------------------------------------------------------------
# THE 0.3.4 oracle (validation-run6 plan D1 and D13, as 0.3.4 shipped them).
# ---------------------------------------------------------------------------


def clinician_line_anchors_v034(
    note: GeneratedNote, document: TranscriptDocument, config: NoteConfig = CONFIG
) -> tuple[int, ...]:
    """0.3.4's ``clinician_line_omissions``, per SEGMENT, verbatim but for
    returning the anchors: every segment before the boundary that the
    confirmed clinician spoke, that no word of is covered, that holds a
    non-suspect content token and that draws no ``high_risk_omission``."""
    if note.clinician_speaker is None:
        return ()
    covered = covered_words(note, document)
    already = {
        coords.segment_index
        for warning in omission_warnings(note, document)
        if (coords := warning.source_coords) is not None
    }
    segments = document.transcript_segments
    boundary = next_patient_boundary(document, config)
    end = len(segments) if boundary is None else boundary
    anchors: list[int] = []
    for segment_index, segment in enumerate(segments[:end]):
        words = segment.transcript_words
        if (
            not spoken_by_confirmed_clinician(segment.speaker, note.clinician_speaker)
            or segment_index in already
            or any((segment_index, word_index) in covered for word_index in range(len(words)))
            or not any(content_tokens(word.word_text) for word in words if not word.suspect)
        ):
            continue
        anchors.append(segment_index)
    return tuple(anchors)


def _high_risk_anchors(note: GeneratedNote) -> frozenset[int]:
    return frozenset(
        coords.segment_index
        for warning in note.note_warnings
        if warning.note_warning_code == "high_risk_omission"
        and (coords := warning.source_coords) is not None
    )


def flagged_v034(
    note: GeneratedNote, document: TranscriptDocument, config: NoteConfig = CONFIG
) -> frozenset[int]:
    """0.3.4's ``[flagged]`` lines: every omission anchor — the note's
    ``high_risk_omission`` anchors and 0.3.4's per-segment
    ``clinician_line_omitted`` anchors."""
    return _high_risk_anchors(note) | frozenset(
        clinician_line_anchors_v034(note, document, config)
    )


def credited_v034(
    note: GeneratedNote, document: TranscriptDocument, config: NoteConfig = CONFIG
) -> frozenset[int]:
    """0.3.4's flagged-line credit (validation-run6 plan D13): the
    ``flagged_v034`` anchors before Check 6's boundary that the confirmed
    clinician spoke and the note leaves wholly uncovered. An anchor outside
    the transcript (a negative one included — Python would index from the
    end) is never credited (review round 15 PR-LOW-001)."""
    segments = document.transcript_segments
    covered = covered_words(note, document)
    cut = next_patient_segment(note.note_warnings)
    return frozenset(
        index
        for index in flagged_v034(note, document, config)
        if 0 <= index < len(segments)
        and (cut is None or index < cut)
        and spoken_by_confirmed_clinician(segments[index].speaker, note.clinician_speaker)
        and not any(
            (index, word) in covered for word in range(len(segments[index].transcript_words))
        )
    )


# ---------------------------------------------------------------------------
# Every small tail (review round 14 LOW-001): the matrix's claims — C4, the
# 0.3.4 oracle equal to the harness's re-derivation, and the credit chain —
# rest on a construction argument, so they are pinned over EVERY three-piece
# tail after the quoted head, over a closed set of piece kinds that holds each
# join condition and each named residue, not only over the matrix's cells.
# ---------------------------------------------------------------------------

# kind: (text, speaker, treatment) — "suspect" marks the piece's every word,
# "quoted" quotes the whole piece, "partly" its first word.
_PIECES: Final[dict[str, tuple[str, str, str]]] = {
    "comma": ("keep walking,", CLINICIAN, ""),
    "stop": ("keep walking.", CLINICIAN, ""),
    "suspect": ("every morning,", CLINICIAN, "suspect"),
    "quoted": ("every morning,", CLINICIAN, "quoted"),
    "partly": ("every morning,", CLINICIAN, "partly"),
    "number": ("take 2 daily,", CLINICIAN, ""),
    "textless": ("", CLINICIAN, ""),
    "filler": ("um,", CLINICIAN, ""),
    "patient": ("rest after,", PATIENT, ""),
    "patient-number": ("take 2 daily,", PATIENT, ""),
    "closing": ("okay, see you next week,", CLINICIAN, ""),
    "greeting": ("hello, come on in,", CLINICIAN, ""),
}


@functools.cache
def every_small_tail() -> tuple[tuple[str, TranscriptDocument, GeneratedNote], ...]:
    """``(name, document, note)`` for each of the 12 ** 3 tails of three
    pieces after ``_KNEE`` and ``_EXAM`` (quoted, so they draw nothing and
    give a closing-then-greeting tail the earlier content D2's boundary
    needs), the note made by the real checker (``checked_note``). Built once
    per test session."""
    tails = []
    for kinds in itertools.product(_PIECES, repeat=3):
        turns = [_KNEE, _EXAM]
        quoted = list(_QUOTE_HEAD)
        suspect = []
        for index, kind in enumerate(kinds, start=len(turns)):
            text, speaker, treatment = _PIECES[kind]
            turns.append((text, speaker))
            if treatment == "suspect":
                suspect.append(index)
            elif treatment == "quoted":
                quoted.append((index, 0, len(text.split()) - 1))
            elif treatment == "partly":
                quoted.append((index, 0, 0))
        document = split_document(*turns, suspect=tuple(suspect))
        tails.append(("/".join(kinds), document, checked_note(document, tuple(quoted))))
    return tuple(tails)
