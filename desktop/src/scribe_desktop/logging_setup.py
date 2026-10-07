"""Structured, clinical-data-free logging (plan Step 4).

Enforcement is STRUCTURAL (plan Key Design Decision):
1. Code logs ONLY through :func:`log_event`, which accepts a whitelisted
   metadata schema — message type, protocol version, byte sizes, timings,
   state names, error codes, filesystem paths. It never accepts a message
   object or free-form interpolated content.
2. A last-line tripwire filter (:class:`PayloadTripwireFilter`) scans what a
   record would actually put on disk — its message, its exception rendering,
   and its stack rendering — and DROPS the record when a registered
   signature appears, counting the violation.
3. Ruff G004 bans f-strings in logging calls; TID251 bans network imports
   everywhere but the Cliniko client's one exempted import.

What (2) does and does NOT guarantee — stated precisely, because an
over-claim here invites the misuse it appears to cover:
- It catches payload/clinical content that arrives with one of its
  registered SIGNATURES attached — a model repr, dict, or JSON rendering,
  in the message or inside a traceback (`_PAYLOAD_SIGNATURES` lists both
  quoted and unquoted forms of every content-bearing field name).
- It does NOT and cannot detect bare clinical text with no signature —
  ``logger.info("%s", span.span_text)`` logs a sentence the filter has no
  way to recognise. Signature matching is a tripwire, not a classifier.
  (1) is therefore the PRIMARY control and this is the backstop, not the
  other way round.

Critical Constraint: the native host's stdout carries only framed protocol
bytes — logging goes to a rotating file and stderr, NEVER stdout.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
import traceback
from pathlib import Path
from typing import Final, TextIO

from scribe_desktop import install_layout

# Whitelisted metadata keys accepted by log_event (plan: whitelisted schema).
ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "message_type",
        "protocol_version",
        "byte_size",
        "duration_ms",
        "state",
        "error_code",
        "path",
        "detail_code",
        "count",
        "pid",
        # Phase 2 session event keys — extended DELIBERATELY (plan Step 1);
        # each is non-clinical metadata: random session id, audio-format
        # numbers, chunk ordinal, hardware device ordinal. NEVER add keys
        # that could carry audio, transcript text, or patient data.
        "session_id",
        "session_state",
        "chunk_index",
        "sample_rate",
        "device_id",
    }
)

# Signatures that indicate a protocol envelope/payload leaked into a log line.
# Both quoted (JSON/dict repr) and unquoted (pydantic model repr, e.g.
# "session_nonce='...' payload={}") forms are covered (HIGH-003). These
# strings MUST stay disjoint from log_event's ALLOWED_KEYS renderings —
# payload/session_nonce/request_id are deliberately not whitelisted keys.
_PAYLOAD_SIGNATURES: Final[tuple[str, ...]] = (
    '"payload"',
    "'payload'",
    "payload=",
    '"session_nonce"',
    "'session_nonce'",
    "session_nonce=",
    "request_id=",
    '"protocol_version":',
    "'protocol_version':",
    # Phase 2 (PR-MED-001): a RecordingSession repr/dict/JSON carries
    # encounter_context (patient/booking identifiers per PLAN.md) — drop it
    # in quoted and unquoted forms, like payload/session_nonce above.
    '"encounter_context"',
    "'encounter_context'",
    "encounter_context=",
    # Phase 2 Step 9: transcript artifact markers. The transcript model's
    # field names are DELIBERATELY distinctive (transcript_segments /
    # transcript_words / word_text) so any repr, model_dump, or JSON of a
    # TranscriptDocument/Segment/Word — clinical content — is dropped by
    # this last-line filter in quoted and unquoted forms alike.
    '"transcript_segments"',
    "'transcript_segments'",
    "transcript_segments=",
    '"transcript_words"',
    "'transcript_words'",
    "transcript_words=",
    '"word_text"',
    "'word_text'",
    "word_text=",
    # Phase 3A Task 1.4: note artifact markers. Every note model in
    # ``note.py`` carries at least one of these field names, so a repr,
    # model_dump or JSON of ANY of them — GeneratedNote, GeneratedSection,
    # NoteAssertion, NoteSpan, NoteProposal, NoteWarning,
    # ConfirmationDecision, NoteRequest, NoteUtterance — is dropped here,
    # empty or populated. ``transcript_utterances`` earns its own entry
    # because NoteRequest carries the raw transcript across the provider
    # boundary once per note and is matched by none of the others (the
    # filter does plain substring matching). ``note_spans`` (plural) has no
    # field today: it is registered ahead of 3B's model-provenance shape so
    # a future multi-span container cannot ship unguarded.
    '"note_sections"',
    "'note_sections'",
    "note_sections=",
    '"note_assertions"',
    "'note_assertions'",
    "note_assertions=",
    '"note_span"',
    "'note_span'",
    "note_span=",
    '"note_spans"',
    "'note_spans'",
    "note_spans=",
    '"span_text"',
    "'span_text'",
    "span_text=",
    '"note_excerpt"',
    "'note_excerpt'",
    "note_excerpt=",
    '"note_warnings"',
    "'note_warnings'",
    "note_warnings=",
    '"note_warning_code"',
    "'note_warning_code'",
    "note_warning_code=",
    '"note_confirmation"',
    "'note_confirmation'",
    "note_confirmation=",
    '"transcript_utterances"',
    "'transcript_utterances'",
    "transcript_utterances=",
    # Note-learning-and-styles plan Phase 0 (schema v2, D7): a section's
    # prose rendering is clinical text. ``StyleRendering`` carries
    # ``prose_text`` (its only content field) and the note carries them
    # under ``style_renderings``; both are registered so a bare rendering's
    # repr is dropped like every other note model's.
    '"style_renderings"',
    "'style_renderings'",
    "style_renderings=",
    '"prose_text"',
    "'prose_text'",
    "prose_text=",
    # Practitioner-profile plan Phase 1 (D5): the voice-profile markers. A
    # repr, model_dump or JSON of a ``PractitionerProfile`` carries
    # ``embedding`` (the biometric vector) and ``enrolment_speech_seconds``;
    # one of a ``ConsentRecord`` carries ``consent_text_version`` — so every
    # rendering of either model is dropped, empty or populated. No
    # ``log_event`` key renders as any of these (pinned by test).
    '"embedding"',
    "'embedding'",
    "embedding=",
    '"enrolment_speech_seconds"',
    "'enrolment_speech_seconds'",
    "enrolment_speech_seconds=",
    '"consent_text_version"',
    "'consent_text_version'",
    "consent_text_version=",
    # Note-learning-and-styles plan Phase 0 (D9/D10): a ``StyleExemplar`` is
    # a sentence from the practitioner's own past notes; its one content
    # field is ``exemplar_text`` so a bare exemplar's rendering is dropped
    # (a whole ``StyleProfile`` already carries ``consent_text_version``).
    '"exemplar_text"',
    "'exemplar_text'",
    "exemplar_text=",
    # Note-learning-and-styles plan Phase 2 (D5, D11; C9): wording the
    # practitioner TYPED over a note line travels outside the note models as
    # a learned-rule candidate / listing (``typed_wording``) and, once a rule's
    # wording is corrected, in the sidecar's history (``previous_expansion``).
    # Both names are distinctive so a rendering of either is dropped.
    '"typed_wording"',
    "'typed_wording'",
    "typed_wording=",
    '"previous_expansion"',
    "'previous_expansion'",
    "previous_expansion=",
    # Note-learning-and-styles plan Phase 3 (D9; C9): a sample note read
    # into memory travels as ``sample_notes.SampleNote.sample_text`` (a
    # pasted note or a file's text), and the review-screen carrier lists
    # the learner's shorthand under ``recognised_shorthand`` /
    # ``unrecognised_shorthand``; all three names are distinctive so a
    # rendering of the sample or the draft is dropped (an exemplar is
    # already caught by ``exemplar_text``).
    '"sample_text"',
    "'sample_text'",
    "sample_text=",
    '"recognised_shorthand"',
    "'recognised_shorthand'",
    "recognised_shorthand=",
    '"unrecognised_shorthand"',
    "'unrecognised_shorthand'",
    "unrecognised_shorthand=",
    # Note-learning-and-styles plan Phase 4 (D6; C9): the prose stage's
    # input carries a finalised note's confirmed texts by section as
    # ``prose_style.ProseInput.section_texts``; the name is distinctive so a
    # rendering of the input is dropped (a rendering's own text is already
    # caught by ``prose_text``, a note's by ``note_sections``).
    '"section_texts"',
    "'section_texts'",
    "section_texts=",
    # Cliniko workflow safeguards plan Task 3.1 (D3): an ``EncounterContext``
    # carries ``patient_id`` and ``treatment_note_id``, a
    # ``ConsentAttestation`` always renders ``treatment_note_id`` (None when
    # unlinked), and ``NoteTarget`` / ``EncounterRecord`` / a
    # ``RecordingSession`` carry one of them; ``NoteDisplay`` carries the
    # patient's name as ``patient_display_name``. Every rendering of any of
    # them is dropped, empty or populated (pinned by test as a class).
    '"patient_id"',
    "'patient_id'",
    "patient_id=",
    '"treatment_note_id"',
    "'treatment_note_id'",
    "treatment_note_id=",
    '"patient_display_name"',
    "'patient_display_name'",
    "patient_display_name=",
    # Task 4.1 (protocol v2, D2): the ``state`` payload's display strings
    # travel as ``patient_name`` (report, live, block, banner) and a
    # ``context`` / ``command`` names ``note_id``. A payload or model of any
    # of them is dropped, quoted or unquoted.
    '"patient_name"',
    "'patient_name'",
    "patient_name=",
    '"note_id"',
    "'note_id'",
    "note_id=",
    # Round 57 SEC-010 (backstop only — no production log call carries
    # these): the Cliniko credential and the clinic registry. The request
    # headers carry the Basic-encoded key under ``Authorization``; a
    # ``ValidationRequest`` holds ``api_key`` (kept out of its repr, but a
    # dict or JSON rendering would show it); ``ClinicRecord`` / ``clinics.json``
    # carry the practitioner's ``contact_email``.
    '"Authorization"',
    "'Authorization'",
    "Authorization:",
    '"api_key"',
    "'api_key'",
    "api_key=",
    '"contact_email"',
    "'contact_email'",
    "contact_email=",
    # Privacy-professional-controls plan Task 1.2 (C3): an ``audit.AuditRow``
    # holds ids only, but a rendering of one ties a session to a patient's
    # Cliniko note and the practitioner — so every rendering is dropped, like
    # the encounter types'. These three names are the row's own (a row also
    # renders ``treatment_note_id`` and ``consent_text_version``, already
    # registered); no ``log_event`` key renders as any of them (pinned by
    # test).
    '"past_session"',
    "'past_session'",
    "past_session=",
    '"note_provenance"',
    "'note_provenance'",
    "note_provenance=",
    '"consent_confirmed_at"',
    "'consent_confirmed_at'",
    "consent_confirmed_at=",
    # Privacy-professional-controls plan Task 2.1 (D2): ``generated.enc``'s
    # document carries the first note body the review showed as
    # ``generated_text`` — clinical text, dropped in every rendering. A Past-
    # sessions label names the patient as ``patient_name`` (registered above,
    # Task 4.1), so a rendering of a label is dropped too.
    '"generated_text"',
    "'generated_text'",
    "generated_text=",
    # Development-recordings plan Task 1.4 (D15; C6): the audit row's nested
    # ``RecordingRecord`` can be rendered on its own, and none of the row's
    # other names would then appear — so its distinctive field ``kept_at`` is
    # registered (a whole row is already dropped by the names above). No
    # ``log_event`` key renders as it (pinned by test).
    '"kept_at"',
    "'kept_at'",
    "kept_at=",
)

# THE production log format — one string, used to build every handler's
# formatter AND to derive what the tripwire scans, so the two cannot drift.
LOG_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"

_FORMAT_FIELD_RE: Final = re.compile(r"%\((\w+)\)")
# Handled outside the generic sweep: ``message`` is scanned via getMessage()
# (which applies args), and ``asctime`` is REGENERATED by the formatter from
# the clock, so a value placed there by a caller never reaches the output.
_SELF_HANDLED_FIELDS: Final[frozenset[str]] = frozenset({"asctime", "message"})


def _interpolated_fields(fmt: str) -> tuple[str, ...]:
    """Record attributes ``fmt`` interpolates, minus the self-handled ones.

    DERIVED, never hand-listed. Rounds 3, 4, 5 and 6 were all one class —
    the filter scanning less than the formatter emits — and each round's fix
    hand-extended the scan by one more case. Deriving from the format string
    itself is what closes that class: a field added to ``LOG_FORMAT`` is
    scanned without anyone remembering to add it here.
    """
    return tuple(sorted(set(_FORMAT_FIELD_RE.findall(fmt)) - _SELF_HANDLED_FIELDS))


_SCANNED_FIELDS: Final[tuple[str, ...]] = _interpolated_fields(LOG_FORMAT)

_dropped_records = 0
_handler_errors = 0


def dropped_record_count() -> int:
    """Number of log records dropped by the tripwire (exposed for tests/audit)."""
    return _dropped_records


def handler_error_count() -> int:
    """Number of records a handler failed to write (exposed for tests)."""
    return _handler_errors


# An exception type's name is shown only when it is a plain identifier.
_TYPE_NAME: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")


def exception_type_name(exc_type: object) -> str:
    """``exc_type.__name__`` when it is a plain identifier, else ``unknown``."""
    name = getattr(exc_type, "__name__", None)
    if isinstance(name, str) and _TYPE_NAME.fullmatch(name):
        return name
    return "unknown"


class QuietHandlerErrors(logging.Handler):
    """Privacy-professional-controls round 23 PR-MED-020 (C3): a handler that
    fails to write a record (a full disk, a failed rollover, a broken stream,
    a bad format) reports it as ONE fixed stderr line naming the error's
    TYPE, and nothing else.

    The stock ``Handler.handleError`` prints ``sys.exception()`` with its
    whole ``__context__`` chain, the call stack and the record's message and
    arguments. Whenever the failing call runs while an exception is being
    handled — every exception hook (the thread hook runs inside ``except:``),
    and any ``log_event`` inside an ``except`` block — that chain is the
    handled exception's message and traceback, which may carry clinical text.
    This override never prints a traceback, a chain, a stack, a message or an
    argument, never writes stdout, keeps no reference to the exception, and
    never raises. Every handler ``setup_logging`` builds carries it (pinned by
    test); ``logging_setup`` is the only module that installs a handler.
    Residue: a third-party logger with no handler of its own falls to Python's
    ``logging.lastResort`` (WARNING and above), which is not one of these."""

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802 - stdlib name
        global _handler_errors
        _handler_errors += 1
        try:
            stream = sys.stderr
            if logging.raiseExceptions and stream:
                name = exception_type_name(type(sys.exception()))
                stream.write(f"--- Logging error ({name}) ---\n")
        except Exception:  # noqa: BLE001 - reporting a failure must never raise
            pass


class _QuietRotatingFileHandler(QuietHandlerErrors, logging.handlers.RotatingFileHandler):
    """The rotating log file, with the quiet failure report."""


class _QuietStreamHandler(QuietHandlerErrors, logging.StreamHandler[TextIO]):
    """The stderr handler, with the quiet failure report."""


class PayloadTripwireFilter(logging.Filter):
    """Last-line defence: drop any record whose formatted output would carry a
    registered signature, and count the violation.

    The scan covers EVERY channel a handler can write — the message, the
    exception rendering, and the stack rendering — not just the message.
    Handler filters run BEFORE the formatter appends ``exc_info`` /
    ``stack_info``, so a message-only scan let a caught note-validation error
    persist clinical text into the log while the drop counter stayed at zero
    (peer round 3, PR-HIGH-001).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        global _dropped_records
        try:
            text = self._scan_text(record)
        except Exception:  # noqa: BLE001 - malformed record: drop it
            _dropped_records += 1
            return False
        if any(sig in text for sig in _PAYLOAD_SIGNATURES):
            _dropped_records += 1
            return False
        return True

    @staticmethod
    def _scan_text(record: logging.LogRecord) -> str:
        """Everything this record could put on disk, rendered SIDE-EFFECT-FREE.

        Mirrors the standard formatter's exception INPUTS, conservatively:
        ``logging.Formatter.format`` appends ``record.exc_text`` when that
        cache is set and otherwise renders the complete ``record.exc_info``
        TUPLE, so both are scanned and neither is trusted to stand for the
        other. Scanning both is a deliberate superset — the two can diverge
        (round 4 PR-MED-001): an ``elif`` skipped a populated cache whenever
        ``exc_info`` was present, and rendering only ``exc_info[1]`` walks
        that exception's own ``__traceback__`` rather than the tuple's
        ``exc_info[2]``, which is what the formatter actually prints.

        ``record.exc_text`` is deliberately never WRITTEN: the formatter owns
        that cache, and a filter that populated it would change what a second
        handler formats. The cost is that a two-handler logger renders the
        traceback twice per bad record — accepted, because this process logs
        only operational events and correctness here outranks the work.

        COMPLETENESS, restated after round 6 falsified the previous version.
        ``Formatter.format`` emits the interpolated BASE FIELDS, then
        ``exc_text``, then the rendered ``exc_info``, then ``stack_info``.
        All four channels are scanned, each on the formatter's own predicate.

        The round-5 docstring named the interpolated fields correctly and
        then drew a false conclusion from them: it claimed a superset while
        scanning only ``message``, silently treating ``name`` and
        ``levelname`` as non-content. A record named
        ``span_text='left knee'`` passed the filter and was emitted. That is
        the fourth instance of one class — the filter scanning less than the
        formatter emits — so the base-field list is no longer WRITTEN DOWN
        HERE at all: ``_SCANNED_FIELDS`` is DERIVED from ``LOG_FORMAT`` (the
        single string both this scan and the handlers' formatter are built
        from), so adding a field to the format automatically adds it to the
        scan. A hand-maintained list is precisely how this recurred.

        Preconditions, narrower and checkable, all pinned by tests: both
        handlers are built by ``setup_logging`` from ``LOG_FORMAT`` and share
        one stock ``logging.Formatter``; ``asctime`` is excluded because the
        formatter REGENERATES it from the clock, so a caller cannot smuggle
        content through it; ``message`` is covered by ``getMessage()``. A
        custom formatter, a second format string, a ``LogRecord`` factory, or
        a propagating parent handler would each break the claim and require
        revisiting this method.

        Rendering the record through a real formatter instead of mirroring it
        stays rejected: ``formatException`` writes ``record.exc_text``, so it
        would need a record copy — trading a tested mirror for a subtler one.
        """
        parts = [record.getMessage()]
        for field in _SCANNED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                parts.append(str(value))
        # PREDICATE PARITY with logging.Formatter.format, line for line:
        #   if record.exc_info:  -> render the tuple into exc_text
        #   if record.exc_text:  -> append it
        #   if record.stack_info -> append the stack
        # The predicates are copied, not re-derived. Three rounds of findings
        # (3, 4, 5) were all the same class — a scan condition NARROWER than
        # the formatter's — so the rule here is parity, never a new
        # special case: `exc_info` is tested for TRUTHINESS exactly as the
        # formatter tests it, because a truthy tuple whose value slot is None
        # (`(RuntimeError, None, tb)`, reachable via an explicit `exc_info=`
        # argument) still gets rendered and persisted by the formatter.
        if record.exc_info:
            parts.append("".join(traceback.format_exception(*record.exc_info)))
        if record.exc_text:
            parts.append(record.exc_text)
        if record.stack_info:
            parts.append(record.stack_info)
        return "\n".join(parts)


def default_log_dir() -> Path:
    return install_layout.data_root() / "logs"


def setup_logging(
    name: str,
    *,
    log_dir: Path | None = None,
    stderr: bool = True,
    file: bool = True,
    max_bytes: int = 1_000_000,
) -> logging.Logger:
    """Configure the process logger: rotating file + optional stderr, tripwired.

    NEVER attaches a stdout handler (Critical Constraint: stdout purity).
    Replaced handlers are CLOSED, not just detached (MED-002: an orphaned
    open handle on the log file breaks rotation renames on Windows).
    ``file=False`` (installation plan Task 2.7: a packaged build refusing to
    run outside its install folder) builds no file handler and creates no
    log folder — stderr only, when there is one.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    tripwire = PayloadTripwireFilter()
    # ONE formatter object, built from the same LOG_FORMAT the tripwire derives
    # its scanned fields from, shared by every handler (pinned by test).
    formatter = logging.Formatter(LOG_FORMAT)

    if file:
        directory = log_dir if log_dir is not None else default_log_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # Round 23 PR-MED-020: both handlers report a write failure as one
            # fixed line (``QuietHandlerErrors``), never the handled exception.
            file_handler = _QuietRotatingFileHandler(
                directory / f"{name}.log", maxBytes=max_bytes, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(tripwire)
            logger.addHandler(file_handler)
        except OSError:
            # LOW-012: an unwritable log dir must not kill the process before
            # the origin check — fall back to stderr-only logging.
            pass

    # sys.stderr is None under a pythonw-backed launcher with no redirection.
    if stderr and sys.stderr is not None:
        stderr_handler = _QuietStreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.addFilter(tripwire)
        logger.addHandler(stderr_handler)

    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: str | int | float) -> None:
    """The ONLY sanctioned logging call sites use: event name + whitelisted fields.

    Raises ValueError on a non-whitelisted key so misuse fails tests, not
    silently leaks. Values are scalars only — never message objects.
    """
    bad = set(fields) - ALLOWED_KEYS
    if bad:
        raise ValueError(f"log_event fields not in whitelist: {sorted(bad)}")
    parts = [event] + [f"{key}={fields[key]}" for key in sorted(fields)]
    logger.info("%s", " ".join(parts))
