"""Note checking stage (Phase 3A, Tasks 5.1-5.4).

This module owns the four content checks that run over a composed
``GeneratedNote`` AFTER confirmation and BEFORE ``write_note`` (the plan's
pipeline order: compose -> confirm -> CHECK -> write). Every check is a pure
function from (note, transcript, config) to ``NoteWarning`` tuples — no
state, no I/O, and NO LOGGING anywhere in this module: the returned warnings
carry codes, ids and coordinates only, never clinical text, so the module's
PUBLIC surface adds nothing content-bearing. Named residue rather than an
absolute: the internal ``_StructuredClaim`` tuples do hold anchor/value
tokens (medication names, dose numbers) in memory while Check 2 compares —
they never cross the API and this module opens no logging channel, but
their field values carry NO registered tripwire signature, so if a later
phase ever logs one the tripwire will not catch it. Do not log them.
Round 45 LOW-005 adds the SIBLINGS this residue note omitted, so the class
is named rather than one instance: ``ui.models.RenderedAssertion.text`` and
``ui.models.RenderedProposal.excerpt`` carry clinical text under field names
(``text=``, ``excerpt=``) that are likewise absent from
``logging_setup._PAYLOAD_SIGNATURES`` — a repr of either would pass the
filter. Neither module opens a logging channel today. The rule for all of
them is the same: these are view/compare structures, not note models; do
not log them, and register a signature first if that ever changes.

What each check claims — and, recorded with equal care, what it does NOT:

- **Check 1, ``reconstruction_warnings``** — every ``transcript`` assertion
  is rebuilt from its single contiguous ``source_coords`` against the
  immutable transcript with ``note.reconstruct_span_text`` (the SAME
  function both providers use, so the comparison is exact, not
  whitespace-lucky) and compared byte-for-byte. Unresolvable coordinates are
  ``source_coords_invalid``; a resolvable interval whose text differs is
  ``reconstruction_mismatch``; both are errors. For every span that
  reconstructs exactly, every INCLUDED source word whose raw
  ``probability`` sits below ``UNCERTAINTY_THRESHOLD`` draws a
  ``low_confidence_source`` review warning, reached through the
  coordinates (a failed span draws its error instead — the cited words
  are not the note's content).
  HONEST SCOPE (Task 5.1): this reaches only words the note included. A
  low-confidence clinically material phrase that routing OMITTED is reached
  by neither this check nor Check 4 — the 3A answer is presentational
  (Task 7.6 keeps the fully uncertainty-marked transcript visible beside
  the note through review), and this module claims no automated detection
  it does not have. Multi-interval assembly needs no check here: Task 1.1's
  types make it unrepresentable.
- **Check 2, ``contradiction_warnings``** — the high-risk classes as
  CONTRADICTION checks over confirmed clinician-authored (``autofill`` /
  ``prefill``) assertions, and ONLY over assertions that parse to explicit
  structure: a claim type, an entity/anatomical anchor, and a value
  (``_StructuredClaim``). Anchors come from closed lexicons; values are
  laterality tokens, negation status, or numbers (a dose compares only
  when an explicit STRENGTH atom — attached or separated — binds
  UNAMBIGUOUSLY to its medication through one of three closed grammatical
  relations over closed connectors, exact grammar outranking positional
  and ambiguity binding nothing, with the unit part of the anchor and
  every relation token graded for confidence; and a differing dose
  HARD-BLOCKS only on mechanically-established EXCLUSIVE-state identity —
  token-identical statements drawn wholly from the closed
  exclusive-administration grammar — while every other matched-anchor
  difference grades ``dose_mismatch`` review, because dose changes,
  titrations and inventory strengths (two tablet strengths can be held at
  once) are ordinary documentation; the ``_DOSE_WINDOW`` comment records
  the rounds-19-24 lessons and the complete bounded residue, every named
  form pinned by test).
  Only MATCHED anchors are ever compared — an unmatched pair is not a
  contradiction, so "right hip, left shoulder" cannot fire and unrelated
  numbers or medications co-occurring in one window compare with nothing.
  An assertion that does not parse to structure is NOT contradiction-checked;
  it is carried by clinician confirmation alone, and this docstring says so
  rather than implying coverage. Severity grades on the transcript-side
  evidence's raw ``probability < UNCERTAINTY_THRESHOLD`` — NEVER on the
  ``uncertain`` flag, which also marks every number and name regardless of
  confidence and would demote exactly the contradictions that matter most.
  The checking stage does NOT semantically decompose entries: a compound
  that legitimately passed Phase 4's atomic-shape authoring residue (claims
  joined only by clinically-required punctuation — ``mmol/L``, slash and
  plus joins) is checked AS ONE assertion, each of its anchored claims
  individually; nothing here splits it, and Phase 7's exact-wording
  confirmation remains the control for the join itself.
- **Check 3, ``provenance_warnings``** — provenance integrity, with codes
  exactly as the plan enumerates: ``unconfirmed_proposal`` (error — one per
  still-pending proposal, autofill and prefill identically),
  ``autofill_trigger_absent`` (error — every autofill assertion's rule is
  re-resolved through its content-derived proposal id and its trigger
  re-verified against the transcript with ``note_fill``'s OWN matcher, the
  single matching source, so a legitimately-fired rule can never be flagged
  absent by a divergent re-implementation), ``clinician_asserted`` (review,
  unsuppressible — every non-``transcript`` assertion draws it,
  acknowledgement being the exit), ``mapping_drop`` (review, NOT error —
  emitted by ``note_config.mapping_drop_warnings``, the single source; an
  error grade would be unclearable and deadlock Complete), and
  ``role_unconfirmed`` (error — a clinician-owned section populated without
  a confirmed role). ``role_unconfirmed`` also fires per-assertion when a
  clinician-owned section holds a transcript assertion whose SOURCE SEGMENT
  — derived from the coordinates, never from the assertion's own
  ``speaker`` field, which is provider-supplied display attribution — was
  spoken by a cluster other than the confirmed clinician: content a
  non-clinician spoke is content populated without the backing of a
  confirmed role, which is the spoken-injection defence the plan assigns to
  role ownership. NOT checked, recorded rather than implied: prefill
  assertions have no trigger claim to re-verify (selection is an explicit
  clinician choice or a detection the clinician overrides); a wrong
  ``speaker`` label on an assertion OUTSIDE the clinician-owned sections is
  display attribution reviewed via Task 7.6, not a check; and the
  ``shown_text_digest``-vs-text match is ``write_note``'s verification
  (Task 6.2), deliberately not duplicated here.
- **Check 4, ``omission_warnings``** — omission, SCOPED to
  clinician-attributed transcript segments carrying high-risk tokens
  (numbers via ``is_number_token``, names via ``is_name_like_token``,
  medications via the closed lexicon) that no note assertion's coordinates
  carry. One ``high_risk_omission`` review warning per affected segment,
  its coordinates spanning the uncovered high-risk words. STATED LIMIT
  (Task 5.4): this is a high-risk-token heuristic, not a materiality
  classifier — the automated claim is "high-risk clinician-spoken content
  is either carried or flagged", never the broader "no clinically material
  omission" (fixtures' ``clinically_material_span_ids`` is a TEST oracle
  with no runtime producer). Unscoped, this check is a false-positive
  generator whose rate rises the better the note excludes small talk, which
  ``PLAN.md`` requires the note to do — so patient-side speech never draws
  an omission warning, and with no confirmed role the scoping predicate
  does not exist and the check honestly emits nothing.

``check_note`` is the stage entry point. It REFUSES (typed
``CheckTargetMismatchError``) to check a note against a transcript or
config whose digests do not match the note's own — a check run against the
wrong artifacts would manufacture false confidence either way — and the
config is canonicalised first (``note_config._canonical_config``, the
round-12 boundary lesson), so a validator-skipping or subclassed config
cannot smuggle a lying digest past the gate.

The three lexicons here are a FIRST CUT authored against the fixture matrix
and ordinary physiotherapy vocabulary, NOT clinical evidence — the same
honesty note the ``ExtractiveNoteProvider`` cue lists carry. They are
closed sets by design: a token outside them yields no structure and
therefore no contradiction, which fails toward silence, never toward a
false accusation.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from itertools import combinations
from typing import Final, Literal, NamedTuple

from scribe_desktop.note import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the mock's negation vocabulary IS the checker's negation vocabulary —
    # two sets would let the instrument express a class the checker cannot
    # see, exactly the drift Task 1.2 pinned tokenisation against.
    _NEGATIONS,
    CLINICIAN_OWNED_SECTIONS,
    GeneratedNote,
    NoteAssertion,
    NoteProposal,
    NoteWarning,
    SourceCoords,
    content_tokens,
    is_interrogative,
    normalise_token,
    reconstruct_span_text,
    transcript_digest,
)
from scribe_desktop.note_config import (
    # Package-private by name, shared deliberately (the note.py convention):
    # ONE definition of what ends a clause. The config authoring guard and
    # this parser must agree, or "one claim" would mean two different things
    # on the two sides of the same pipeline.
    _TERMINAL_PUNCT,
    AutofillRule,
    NoteConfig,
    _canonical_config,
    bind_template_profile,
    mapping_drop_warnings,
)
from scribe_desktop.note_fill import _first_phrase_match, _proposal_id
from scribe_desktop.transcription import (
    UNCERTAINTY_THRESHOLD,
    TranscriptDocument,
    TranscriptWord,
    is_name_like_token,
    is_number_token,
)


class NoteCheckError(Exception):
    """Base class for checking-stage failures (mirrors ``NoteConfigError``)."""


class CheckTargetMismatchError(NoteCheckError):
    """The note's recorded digests do not match the transcript or config it
    was presented for checking against — the run would be meaningless."""


# ---------------------------------------------------------------------------
# Shared vocabulary (Tasks 5.2 / 5.4). Closed sets; module docstring records
# their first-cut, non-evidence status and the fail-toward-silence direction.
# ---------------------------------------------------------------------------

_LATERALITY_TOKENS: Final[frozenset[str]] = frozenset({"left", "right"})

_ANATOMY_LEXICON: Final[frozenset[str]] = frozenset(
    {
        "knee", "knees", "shoulder", "shoulders", "hip", "hips", "elbow",
        "elbows", "wrist", "wrists", "ankle", "ankles", "foot", "feet",
        "hand", "hands", "arm", "arms", "leg", "legs", "thigh", "thighs",
        "calf", "calves", "heel", "heels", "toe", "toes", "finger",
        "fingers", "thumb", "thumbs", "neck", "back", "spine", "glute",
        "glutes", "hamstring", "hamstrings", "quadriceps", "groin",
        "achilles", "patella", "meniscus",
    }
)

_SYMPTOM_LEXICON: Final[frozenset[str]] = frozenset(
    {
        "pain", "ache", "aches", "aching", "numbness", "tingling",
        "swelling", "weakness", "stiffness", "dizziness", "headache",
        "headaches", "nausea", "fever", "bruising", "locking", "clicking",
        "instability", "spasm", "spasms", "cramp", "cramps", "soreness",
        "tenderness",
    }
)

_MEDICATION_LEXICON: Final[frozenset[str]] = frozenset(
    {
        "paracetamol", "panadol", "ibuprofen", "nurofen", "aspirin",
        "naproxen", "diclofenac", "voltaren", "codeine", "tramadol",
        "meloxicam", "celecoxib", "amitriptyline", "gabapentin",
        "pregabalin", "prednisone", "prednisolone",
    }
)

# The bounded gap inside a dose-binding relation. Small on purpose: a wide
# positional search is where "unrelated numbers co-occurring" turns into
# false dose claims. Rounds 19-24 arrived at a rule that is STRUCTURAL end
# to end — see `_strength_atoms` / `_dose_binding` / `_same_state`:
#
# - A dose claim is built ONLY from an explicit STRENGTH ATOM — number+unit
#   attached ("500mg") or separated ("500 mg") — bound to a medication
#   through one of THREE closed grammatical relations whose connectors are
#   themselves a closed set (`_DOSE_CONNECTORS`): exact-inverse "<atom> of
#   <medication>", the literal dose-phrase "<medication> [connectors] dose
#   of <atom>", and medication-first "<medication> [connectors] <atom>".
#   Exact local grammar outranks positional binding, two relations naming
#   different medications are AMBIGUOUS and bind nothing (round 24
#   PR-MED-001), and every relation token joins the claim's confidence and
#   coordinates (rounds 23-24). The canonical unit joins the ANCHOR, so a
#   mg claim and a g claim are an UNMATCHED pair (no unit conversion is
#   claimed).
# - Severity is an EXCLUSIVE-STATE question (rounds 23-24 PR-MED-002/003):
#   differing values hard-block (`contradiction`) only when the two
#   statements are token-identical once each dose atom is collapsed AND
#   that wording lies wholly inside the closed exclusive-administration
#   grammar (`_EXCLUSIVE_DOSE_CONTEXT`) — a current regimen fact with one
#   strength slot. Everything else with a matched anchor — dose change,
#   titration, inventory or product strength (two tablet strengths can be
#   held at once), differing or novel wording — grades `dose_mismatch`
#   review: surfaced and acknowledgeable, never a block on legitimate
#   documentation.
#
# The residue is COMPLETE-BY-CONSTRUCTION in both directions. SILENT forms
# are exactly the quantities that never become a bound atom: unit-less
# strengths ("paracetamol 500"), count/dose-form quantities ("2 tablets",
# prescribed or stock — mechanically inseparable), temporal/measurement
# quantities ("2 days ago", "20 minutes"), cross-unit restatements,
# spelled quantities, unrecognised suffixes ("20min"), non-connector gaps
# ("mixed with 5 ml water"), and ambiguous multi-medication bindings.
# REVIEW-not-error forms are exactly the matched-anchor differences whose
# shared wording is not provably one exclusive regimen fact — including
# genuinely-current paraphrases outside the closed grammar, accepted as
# the conservative boundary. Each named form is pinned by a test; unlisted
# context wording demotes to review and unlisted gap wording breaks the
# binding — both allow-list directions, so novel forms fail toward
# review/silence, never toward blocking or a guessed dose. Deny-list
# repairs (temporal/status word lists) were considered and rejected in
# rounds 21-24: unlisted wording would fail toward FIRING, the unsafe
# direction.
_DOSE_WINDOW: Final = 3
_NEGATION_WINDOW: Final = 2

# Canonical strength units. Long and short forms map to one canonical unit
# so "500 mg", "500mg" and "500 milligrams" all anchor as (medication, mg).
_STRENGTH_UNITS: Final[dict[str, str]] = {
    "mg": "mg", "milligram": "mg", "milligrams": "mg",
    "mcg": "mcg", "microgram": "mcg", "micrograms": "mcg",
    "g": "g", "gram": "g", "grams": "g",
    "ml": "ml", "millilitre": "ml", "millilitres": "ml",
    "milliliter": "ml", "milliliters": "ml",
}

_NUMBER_WITH_SUFFIX_RE: Final = re.compile(r"^(\d+(?:\.\d+)?)([a-z]+)?$")

# Round 24 PR-MED-001: the ONLY words that may sit between a medication and
# its strength atom (relation R1) or between a medication and the literal
# ``dose`` (relation R3). A closed set, not "any non-digit gap" — that gap
# is how `paracetamol mixed with 5 ml water` became a paracetamol dose. A
# word outside this set breaks the relation and the atom stays unbound
# (silence, the safe direction).
_DOSE_CONNECTORS: Final[frozenset[str]] = frozenset({"at", "to", "a", "the"})

# Round 24 PR-MED-003: the closed POSITIVE grammar of the error-grade
# population. `contradiction` may hard-block two differing dose values only
# when their collapsed contexts are identical AND drawn wholly from this
# exclusive-administration vocabulary (medication names, administration
# verbs, frequency/timing words, the dose-relation words) — the wording of
# an explicitly current regimen fact with ONE strength slot. This is an
# ALLOW-list on purpose: any word outside it (inventory's "have"/"tablets"/
# "remaining", stock, product, novel status wording) makes the context
# non-exclusive and demotes the pair to `dose_mismatch` review — unlisted
# wording fails toward review, never toward blocking. Two tablet strengths
# can be held at once; only one regimen fact of identical wording can be
# true at once.
_EXCLUSIVE_DOSE_CONTEXT: Final[frozenset[str]] = frozenset(
    {
        "i", "take", "takes", "taking", "on",
        "advised", "prescribed", "recommended", "continue", "continues",
        "daily", "nightly", "once", "twice",
        "each", "every", "morning", "evening", "night", "afternoon",
        "breakfast", "lunch", "dinner", "bedtime", "mane", "nocte",
        "in", "the", "at", "a", "per", "day", "dose", "of",
    }
)

# Round 48 PR-MED-002: the POSITIVE witness an error-grade dose pair needs, on
# top of `_EXCLUSIVE_DOSE_CONTEXT`'s negative test. A strict subset of that
# vocabulary: every token here either asserts ADMINISTRATION or pins a
# SCHEDULE. Deliberately excluded as pure structure — `i`, `each`, `every`,
# `in`, `the`, `at`, `a`, `per`, `dose`, `of` — because a context built only
# from those (in the limit, none at all) states a strength and nothing about
# whether it is a current regimen, a product label, or stock. Keep this a
# subset: a token added here that is NOT in `_EXCLUSIVE_DOSE_CONTEXT` could
# never fire, and `test_the_administration_witness_is_a_strict_subset` pins
# that.
_ADMINISTRATION_WITNESS: Final[frozenset[str]] = frozenset(
    {
        "take", "takes", "taking", "on",
        "advised", "prescribed", "recommended", "continue", "continues",
        "daily", "nightly", "once", "twice",
        "morning", "evening", "night", "afternoon",
        "breakfast", "lunch", "dinner", "bedtime", "mane", "nocte", "day",
    }
)


def _words_for_coords(
    document: TranscriptDocument, coords: SourceCoords
) -> tuple[TranscriptWord, ...] | None:
    """The words ``coords`` address in the immutable transcript, or None.

    Segment coordinates address positions in ``transcript_segments`` — the
    exact enumeration ``_assemble_note_request`` performed, so a span
    verified here agrees with one verified against the ``NoteRequest``.
    """
    if coords.segment_index >= len(document.transcript_segments):
        return None
    words = document.transcript_segments[coords.segment_index].transcript_words
    if coords.last_word_index >= len(words):
        return None
    return words[coords.first_word_index : coords.last_word_index + 1]


def _resolved_coords(assertion: NoteAssertion) -> SourceCoords:
    coords = assertion.note_span.source_coords
    if coords is None:  # pragma: no cover - NoteSpan validates this away
        raise AssertionError("unreachable: a transcript span always carries source_coords")
    return coords


# ---------------------------------------------------------------------------
# Check 1 — exact coordinate reconstruction (Task 5.1).
# ---------------------------------------------------------------------------


def reconstruction_warnings(
    note: GeneratedNote, document: TranscriptDocument
) -> tuple[NoteWarning, ...]:
    """Errors for every ``transcript`` assertion that is not exactly what its
    coordinates say; review warnings for included low-confidence words.

    Uncertainty warnings are emitted only for assertions that reconstruct
    exactly: when reconstruction fails, the cited words are NOT the note's
    content, so flagging their probabilities would annotate text the note
    does not carry — the error already blocks.
    """
    warnings: list[NoteWarning] = []
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.provenance != "transcript":
                continue
            coords = _resolved_coords(assertion)
            words = _words_for_coords(document, coords)
            if words is None:
                warnings.append(
                    NoteWarning(
                        note_warning_code="source_coords_invalid",
                        severity="error",
                        section_key=section.section_key,
                        assertion_id=assertion.assertion_id,
                        source_coords=coords,
                    )
                )
                continue
            if reconstruct_span_text(words) != assertion.text:
                warnings.append(
                    NoteWarning(
                        note_warning_code="reconstruction_mismatch",
                        severity="error",
                        section_key=section.section_key,
                        assertion_id=assertion.assertion_id,
                        source_coords=coords,
                    )
                )
                continue
            for offset, word in enumerate(words):
                if word.probability < UNCERTAINTY_THRESHOLD:
                    index = coords.first_word_index + offset
                    warnings.append(
                        NoteWarning(
                            note_warning_code="low_confidence_source",
                            severity="review",
                            section_key=section.section_key,
                            assertion_id=assertion.assertion_id,
                            source_coords=SourceCoords(coords.segment_index, index, index),
                        )
                    )
    return tuple(warnings)


# ---------------------------------------------------------------------------
# Check 2 — structured contradictions (Task 5.2).
# ---------------------------------------------------------------------------

_ClaimType = Literal["laterality", "dose", "negation"]


class _StructuredClaim(NamedTuple):
    """One explicitly-structured claim: type, anchor, value — the ONLY shape
    Check 2 compares. Internal to this module and never returned, logged or
    serialized: warnings carry codes and coordinates, not claim text."""

    claim_type: _ClaimType
    claim_anchor: str
    claim_value: str
    # Transcript-side evidence only; None for clinician-authored text.
    min_probability: float | None
    source_coords: SourceCoords | None
    # Dose claims only (rounds 23-24): the assertion's full token sequence
    # with the strength atom collapsed to one placeholder. The `error` grade
    # requires IDENTICAL contexts that are also drawn wholly from the closed
    # exclusive-administration grammar (`_same_state`); anything less grades
    # `dose_mismatch` review.
    context: tuple[str, ...] | None = None


class _Token(NamedTuple):
    token: str
    probability: float | None
    word_index: int | None
    # Round 48 PR-MED-001: which CLAUSE this token sits in. ``content_tokens``
    # strips punctuation, so without this the parser could not tell "No
    # fever; pain persists" from "No fever pain persists" and bound the
    # negation to a symptom in the NEXT clause — manufacturing an
    # error-grade `contradiction` against a consistent note. Counted, never
    # injected as a sentinel token, so the dose grammar below is untouched.
    clause: int = 0


# Round 49 PR-MED-001: mechanically-recognised CONTRAST boundaries. Round 48
# scoped negation to the punctuation clause, which was too coarse in the
# unsafe direction: "No fever but right knee pain." is one punctuation clause,
# so `no` erased an explicit, unambiguous positive laterality pair and a real
# laterality-flip stopped being caught. An adversative closes the negated
# subclause, so the negation before it does not reach the assertion after it.
#
# Round 50 PR-MED-001 narrowed this list HARD, because a contrast boundary
# only ever LIMITS a negation's scope — i.e. it can only ADD positive claims,
# the unsafe direction — so a word earns a place here only if its contrastive
# reading is unambiguous:
#   - `yet` REMOVED: overwhelmingly temporal in clinical speech. "No evidence
#     yet of left knee pain." split the clause, moved `left knee` out of the
#     negation's reach, and emitted a positive left-knee claim that could
#     hard-block a consistent right-knee note.
#   - `though` / `although` / `whereas` / `except` REMOVED: subordinators that
#     are routinely PREPOSED ("Although no fever, right knee pain persists."),
#     where opening a new clause at the word puts the subordinate negation and
#     the main clause's positive claim on the SAME side, achieving nothing —
#     and `except` is a preposition as often as a conjunction.
#
# RESIDUE, named rather than implied: a preposed subordinate negation still
# suppresses its main clause's laterality ("Although no fever, right knee pain
# persists." yields no laterality claim). Recognising that needs preposed-
# clause grammar this module does not have, so it fails toward SILENCE — a
# missed true positive, never a false block — which is the direction the
# module's contract requires.
_CONTRAST_TOKENS: Final[frozenset[str]] = frozenset({"but", "however"})


# Round 50 PR-MED-004: characters that may follow a terminator without
# cancelling it — closing quotes and brackets. A closed set; anything else
# after a terminator leaves the chunk mid-clause, the safe direction.
_CLOSING_WRAPPERS: Final[frozenset[str]] = frozenset("\"'”’)]}»›")


def _ends_clause(raw: str) -> bool:
    """True when a raw (unstripped) chunk ends a clause.

    Classifies the chunk's trailing SUFFIX SHAPE against the one shared
    ``_TERMINAL_PUNCT`` definition — not merely its last character (round 50
    PR-MED-004). ``content_tokens`` strips surrounding punctuation, so a
    visually explicit sentence end wearing a closing quote (``fever."``) or
    bracket became indistinguishable from no boundary at all, and a negation
    then crossed it to negate the next sentence's symptom.

    Only closing wrappers are skipped, and only after a real terminator, so
    a decimal (``1.5``), a time (``14:30``) and an abbreviation chain's
    interior dots still end in a digit or letter and start no clause. A
    trailing terminator at the very end of the text increments past the last
    token and changes nothing, so "…advised." stays ONE clause — which is
    what keeps the pinned single-clause dose and laterality cases
    error-grade.
    """
    stripped = raw.rstrip()
    while stripped and stripped[-1] in _CLOSING_WRAPPERS:
        stripped = stripped[:-1]
    return bool(stripped) and stripped[-1] in _TERMINAL_PUNCT


def _tokens_from_text(text: str) -> list[_Token]:
    out: list[_Token] = []
    clause = 0
    for chunk in text.split():
        for token in content_tokens(chunk):
            out.append(_Token(token, None, None, clause))
            if token in _CONTRAST_TOKENS:
                # Round 50 PR-MED-001: the adversative CLOSES the negated
                # subclause; it does not open the new one. Round 49 put the
                # boundary word in the NEW clause, where it joined the
                # collapsed dose context and — being outside
                # `_EXCLUSIVE_DOSE_CONTEXT` — demoted a genuine current-regimen
                # conflict to review ("No ibuprofen, but I take paracetamol
                # 250 mg daily."). The boundary marker must not be able to
                # establish or disqualify a clinical state.
                clause += 1
        if _ends_clause(chunk):
            clause += 1
    return out


def _tokens_from_words(
    words: Sequence[TranscriptWord], first_word_index: int
) -> list[_Token]:
    """Per-word tokenisation through ``content_tokens`` — the same rule
    ``note_fill._first_phrase_match`` indexes by, so the structure parser and
    the trigger matcher can never disagree about what a word says."""
    out: list[_Token] = []
    clause = 0
    for offset, word in enumerate(words):
        for token in content_tokens(word.word_text):
            out.append(_Token(token, word.probability, first_word_index + offset, clause))
            if token in _CONTRAST_TOKENS:
                clause += 1  # closes the subclause; see `_tokens_from_text`
        if _ends_clause(word.word_text):
            clause += 1
    return out


def _dose_quantity(token: str) -> tuple[str, str | None] | None:
    """(canonical numeric value, canonical ATTACHED strength unit or None),
    or None when the token is not a bare number or number+strength-unit.

    Digit-vs-spelled pairs ("500" vs "five hundred") are NOT comparable —
    equating or distinguishing them would need the number-word parsing this
    phase does not claim — so spelled quantities yield nothing. A number
    with an unrecognised suffix ("20min", "3rd") is likewise nothing: only
    an exact closed-vocabulary strength suffix counts (round 22 — anything
    looser would over-accept digit-bearing non-units)."""
    match = _NUMBER_WITH_SUFFIX_RE.match(token)
    if match is None:
        return None
    suffix = match.group(2)
    if suffix is None:
        return format(float(match.group(1)), "g"), None
    unit = _STRENGTH_UNITS.get(suffix)
    if unit is None:
        return None
    return format(float(match.group(1)), "g"), unit


def _claim_evidence(
    segment_index: int | None, involved: Sequence[_Token]
) -> tuple[float | None, SourceCoords | None]:
    probabilities = [t.probability for t in involved if t.probability is not None]
    min_probability = min(probabilities) if probabilities else None
    if segment_index is None:
        return min_probability, None
    indices = [t.word_index for t in involved if t.word_index is not None]
    if not indices:
        return min_probability, None
    return min_probability, SourceCoords(segment_index, min(indices), max(indices))


class _StrengthAtom(NamedTuple):
    """One explicit strength in the token stream: number+unit attached in a
    single token, or a number followed immediately by a strength-unit
    token. An atom is the ONLY thing a dose claim can be built from."""

    first: int
    last: int
    value: str
    unit: str


def _strength_atoms(tokens: list[_Token]) -> list[_StrengthAtom]:
    atoms: list[_StrengthAtom] = []
    position = 0
    while position < len(tokens):
        quantity = _dose_quantity(tokens[position].token)
        if quantity is None:
            position += 1
            continue
        value, unit = quantity
        if unit is not None:
            atoms.append(_StrengthAtom(position, position, value, unit))
            position += 1
            continue
        if position + 1 < len(tokens):
            separated = _STRENGTH_UNITS.get(tokens[position + 1].token)
            # Round 49 PR-MED-002: the unit must be in the SAME clause as its
            # number — "…500. Mg…" is not a separated strength atom.
            if separated is not None and tokens[position + 1].clause == tokens[position].clause:
                atoms.append(_StrengthAtom(position, position + 1, value, separated))
                position += 2
                continue
        position += 1
    return atoms


class _DoseBinding(NamedTuple):
    """One resolved atom→medication binding: the medication index plus the
    indices of every relation token whose literal identity established the
    binding — connectors, ``of``, ``dose`` — so the claim's evidence
    (confidence AND coordinates) is derived from the COMPLETE binding
    (round 24 PR-MED-002), not just medication and atom."""

    medication: int
    evidence: tuple[int, ...]


def _connector_walk(tokens: list[_Token], start: int, clause: int) -> int | None:
    """Walk backward from ``start`` through at most ``_DOSE_WINDOW - 1``
    closed-set connectors; the index of the medication the walk lands on,
    or None. The whole gap must be connectors — any other word breaks the
    relation (round 24 PR-MED-001) — and every token walked, including the
    medication itself, must sit in ``clause`` (round 49 PR-MED-002: a
    relation spanning a sentence boundary is not established by the closed
    LOCAL grammar this module claims to require)."""
    position = start
    steps = 0
    while (
        position >= 0
        and steps < _DOSE_WINDOW - 1
        and tokens[position].clause == clause
        and tokens[position].token in _DOSE_CONNECTORS
    ):
        position -= 1
        steps += 1
    if (
        position >= 0
        and tokens[position].clause == clause
        and tokens[position].token in _MEDICATION_LEXICON
    ):
        return position
    return None


def _dose_binding(tokens: list[_Token], atom: _StrengthAtom) -> _DoseBinding | None:
    """The unambiguous binding of ``atom`` through the CLOSED relation
    allow-list, or None — an unbound OR ambiguous atom yields no claim and
    falls into the bounded residue (rounds 23-24; never a window search):

    - R2  ``<atom> of <medication>`` — exact adjacency, the inverse order.
    - R3  ``<medication> [connectors] dose of <atom>`` — the literal phrase
      ``dose of`` immediately before the atom, medication reached through
      closed connectors only.
    - R1  ``<medication> [connectors] <atom>`` — medication-first, the gap
      restricted to closed connectors (round 24: "any non-digit gap" bound
      water volumes to medications and let loose word order shadow R2).

    Candidates are collected across ALL relations before deciding: the
    exact local grammar (R2, then R3) outranks positional R1, and two
    relations naming DIFFERENT medications are ambiguous — silence, never
    a guessed anchor (round 24 PR-MED-001's invariant).
    """
    # Round 49 PR-MED-002: every token a relation rests on must share the
    # atom's clause. The parser gained clause identity in round 48 and used
    # it only for laterality and symptom negation, so a medication in one
    # sentence could still bind a strength in the next.
    clause = tokens[atom.first].clause
    candidates: list[_DoseBinding] = []
    if (
        atom.last + 2 < len(tokens)
        and tokens[atom.last + 1].token == "of"
        and tokens[atom.last + 2].token in _MEDICATION_LEXICON
        and tokens[atom.last + 1].clause == clause
        and tokens[atom.last + 2].clause == clause
    ):
        candidates.append(_DoseBinding(atom.last + 2, (atom.last + 1,)))
    if (
        atom.first >= 2
        and tokens[atom.first - 2].token == "dose"
        and tokens[atom.first - 1].token == "of"
        and tokens[atom.first - 2].clause == clause
        and tokens[atom.first - 1].clause == clause
    ):
        med = _connector_walk(tokens, atom.first - 3, clause)
        if med is not None:
            evidence = tuple(range(med + 1, atom.first))  # connectors + dose + of
            candidates.append(_DoseBinding(med, evidence))
    med = _connector_walk(tokens, atom.first - 1, clause)
    if med is not None:
        candidates.append(_DoseBinding(med, tuple(range(med + 1, atom.first))))
    if not candidates:
        return None
    if len({candidate.medication for candidate in candidates}) > 1:
        return None  # ambiguous — fail toward silence, never a guessed anchor
    return candidates[0]


def _dose_claims(
    tokens: list[_Token], segment_index: int | None
) -> list[_StructuredClaim]:
    """Dose claims from explicit strength atoms bound through the closed
    relations. Every token the claim's identity rests on — medication,
    quantity, a separated unit, and every relation word the binding needed
    (connectors, ``of``, ``dose``) — joins the evidence, so its probability
    grades confidence and its position joins the warning coordinates
    (rounds 23-24 PR-MED-001/002)."""
    claims: list[_StructuredClaim] = []
    for atom in _strength_atoms(tokens):
        binding = _dose_binding(tokens, atom)
        if binding is None:
            continue
        med = binding.medication
        clause = tokens[atom.first].clause
        # Round 50 PR-MED-003: the ADMINISTRATION WITNESS is the token that
        # decides whether this pair can hard-block at all (`_exclusive_context`
        # searches the collapsed context for one), so it is evidence and must
        # be graded like evidence. Without it, a witness word transcribed at
        # low confidence still produced an unacknowledgeable `contradiction`
        # instead of `contradiction_low_confidence` review, and the warning
        # pointed at coordinates that omitted the very word the upgrade rested
        # on. Drawn from the atom's own clause, matching the context scope.
        witnesses = tuple(
            entry
            for entry in tokens
            if entry.clause == clause and entry.token in _ADMINISTRATION_WITNESS
        )
        involved = (
            tokens[med],
            *(tokens[position] for position in binding.evidence),
            *tokens[atom.first : atom.last + 1],
            *witnesses,
        )
        min_probability, coords = _claim_evidence(segment_index, involved)
        # Round 49 PR-MED-002: the collapsed context — the thing `_same_state`
        # compares and `_exclusive_context` searches for its administration
        # witness — is scoped to the bound atom's CLAUSE. Whole-assertion
        # scope let a bare product-strength clause borrow "continue" or a
        # schedule word from an unrelated sentence and hard-block on it.
        # (`clause` is bound above, where the witness evidence is gathered
        # from the same scope — the two must not drift apart.)
        context = (
            *(entry.token for entry in tokens[: atom.first] if entry.clause == clause),
            "<dose>",
            *(entry.token for entry in tokens[atom.last + 1 :] if entry.clause == clause),
        )
        claims.append(
            _StructuredClaim(
                "dose",
                # The unit joins the ANCHOR: cross-unit pairs are unmatched,
                # never contradictions (rounds 19-22).
                f"{tokens[med].token} {atom.unit}",
                atom.value,
                min_probability,
                coords,
                context,
            )
        )
    return claims


def _claims_from_tokens(
    tokens: list[_Token], *, segment_index: int | None, interrogative: bool
) -> list[_StructuredClaim]:
    """Parse explicitly-structured claims out of one assertion's tokens.

    Everything here is deliberately narrow: a laterality value binds only to
    the anatomy token it directly precedes; a dose claim is built only from
    an explicit strength ATOM bound to a medication through the three
    closed relations of ``_bound_medication`` (the ``_DOSE_WINDOW`` comment
    records the rounds-19-23 lessons, the same-state severity contract, and
    the complete bounded residue); a negation binds only within
    ``_NEGATION_WINDOW`` tokens BEFORE its symptom, and a symptom counts as
    affirmed only when the whole assertion contains no negation token at
    all and is not a question. Text that fits none of these shapes produces
    no claim and is carried by confirmation alone.
    """
    # Round 50 PR-MED-002: a recognised QUESTION asserts nothing, so it may
    # contribute NO claim of any kind to the blocking comparison population.
    # Round 48 applied this to laterality and to affirmed symptoms only, while
    # `_dose_claims` ran unconditionally and the NEGATED-symptom branch never
    # consulted `interrogative` — so "No numbness?" contradicted "Numbness
    # persists." and "On paracetamol 250 mg?" hard-blocked against a 500 mg
    # assertion. Gating once, here, is what makes the rule structural rather
    # than three branches that must each remember it. (This does not touch the
    # recorded `is_interrogative` recognition bound — it only ensures that
    # what the heuristic DOES recognise is honoured everywhere.)
    if interrogative:
        return []
    claims: list[_StructuredClaim] = []
    negated_clauses = {entry.clause for entry in tokens if entry.token in _NEGATIONS}
    for index, entry in enumerate(tokens):
        if (
            entry.token in _LATERALITY_TOKENS
            and index + 1 < len(tokens)
            and tokens[index + 1].token in _ANATOMY_LEXICON
        ):
            anchor = tokens[index + 1]
            # Round 48 PR-MED-001: a laterality claim is a POSITIVE, ASSERTED
            # fact about a side. Three ways it is not, each of which used to
            # produce one anyway and could hard-block a consistent note:
            #   - the assertion is a QUESTION ("Is it the left knee?");
            #   - the clause is NEGATED ("No pain in the left knee") — the
            #     window that binds negation to a symptom is far too short to
            #     reach the anatomy here, so this is clause-scoped;
            #   - the pair straddles a clause boundary.
            # Each check only ever DROPS a claim, so no new contradiction can
            # appear from this change — the fail-toward-silence direction the
            # module's contract requires.
            if interrogative or anchor.clause != entry.clause:
                continue
            if entry.clause in negated_clauses:
                continue
            min_probability, coords = _claim_evidence(segment_index, (entry, anchor))
            claims.append(
                _StructuredClaim("laterality", anchor.token, entry.token, min_probability, coords)
            )
    claims.extend(_dose_claims(tokens, segment_index))
    negation_positions = [
        index for index, entry in enumerate(tokens) if entry.token in _NEGATIONS
    ]
    for index, entry in enumerate(tokens):
        if entry.token not in _SYMPTOM_LEXICON:
            continue
        negated_by = next(
            (
                position
                for position in negation_positions
                # Round 48 PR-MED-001: the window is necessary but not
                # sufficient — the negation must also be in the SAME clause.
                # "No fever; pain persists" put `no` two flattened tokens
                # before `pain` and negated it.
                if 0 < index - position <= _NEGATION_WINDOW
                and tokens[position].clause == entry.clause
            ),
            None,
        )
        if negated_by is not None:
            min_probability, coords = _claim_evidence(
                segment_index, (tokens[negated_by], entry)
            )
            claims.append(
                _StructuredClaim("negation", entry.token, "negated", min_probability, coords)
            )
        elif not negation_positions and not interrogative:
            min_probability, coords = _claim_evidence(segment_index, (entry,))
            claims.append(
                _StructuredClaim("negation", entry.token, "affirmed", min_probability, coords)
            )
    return claims


def _consolidated(
    claims: Sequence[_StructuredClaim],
) -> dict[tuple[_ClaimType, str], _StructuredClaim]:
    """One claim per (type, anchor) — an assertion that carries BOTH values
    for one anchor ("the left knee is better but the right knee is sore")
    is discussing both sides, and comparing either half against another
    assertion would fire on legitimate wording, so the anchor is dropped."""
    grouped: dict[tuple[_ClaimType, str], list[_StructuredClaim]] = {}
    for claim in claims:
        grouped.setdefault((claim.claim_type, claim.claim_anchor), []).append(claim)
    return {
        key: group[0]
        for key, group in grouped.items()
        if len({claim.claim_value for claim in group}) == 1
    }


def _structured_authored(
    note: GeneratedNote,
) -> list[tuple[NoteAssertion, dict[tuple[_ClaimType, str], _StructuredClaim]]]:
    out: list[tuple[NoteAssertion, dict[tuple[_ClaimType, str], _StructuredClaim]]] = []
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.provenance == "transcript":
                continue
            claims = _consolidated(
                _claims_from_tokens(
                    _tokens_from_text(assertion.text),
                    segment_index=None,
                    interrogative=is_interrogative(assertion.text),
                )
            )
            if claims:
                out.append((assertion, claims))
    return out


def _structured_quoted(
    note: GeneratedNote, document: TranscriptDocument
) -> list[tuple[NoteAssertion, dict[tuple[_ClaimType, str], _StructuredClaim]]]:
    """Structured claims from the note's exactly-reconstructing transcript
    assertions. An assertion Check 1 rejects contributes nothing here: text
    that is not what its coordinates say must not drive a contradiction."""
    out: list[tuple[NoteAssertion, dict[tuple[_ClaimType, str], _StructuredClaim]]] = []
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.provenance != "transcript":
                continue
            coords = _resolved_coords(assertion)
            words = _words_for_coords(document, coords)
            if words is None or reconstruct_span_text(words) != assertion.text:
                continue
            claims = _consolidated(
                _claims_from_tokens(
                    _tokens_from_words(words, coords.first_word_index),
                    segment_index=coords.segment_index,
                    interrogative=is_interrogative(assertion.text),
                )
            )
            if claims:
                out.append((assertion, claims))
    return out


def _contradiction_warning(
    flagged: NoteAssertion, evidence: _StructuredClaim | None
) -> NoteWarning:
    weak = (
        evidence is not None
        and evidence.min_probability is not None
        and evidence.min_probability < UNCERTAINTY_THRESHOLD
    )
    return NoteWarning(
        note_warning_code="contradiction_low_confidence" if weak else "contradiction",
        severity="review" if weak else "error",
        section_key=flagged.section_key,
        assertion_id=flagged.assertion_id,
        source_coords=evidence.source_coords if evidence is not None else None,
    )


def _exclusive_context(context: tuple[str, ...]) -> bool:
    """True when the context is the wording of a CURRENT REGIMEN FACT with one
    exclusive strength slot. TWO conditions, because round 48 PR-MED-002
    showed the first alone proves nothing:

    1. NEGATIVE (round 24 PR-MED-003): every token belongs to the closed
       exclusive-administration grammar — inventory, product-strength and
       novel wording contain words outside it and are not exclusive.
    2. POSITIVE (round 48 PR-MED-002): at least one token actually WITNESSES
       administration or a schedule. Condition 1 only establishes that no
       token disqualifies the context, so bare product-strength shorthand
       ("Paracetamol 500 mg") collapsed to ``("paracetamol", "<dose>")`` —
       every token allowed, nothing asserted — passed it and HARD-BLOCKED
       against another strength. That contradicted this module's own stated
       contract, which puts product strength in the review population
       because two strengths can be held at once. Absence of disqualifying
       words is not proof of an exclusive state.

    The witness set is an ALLOW-list drawn from the same closed vocabulary,
    minus the tokens that are pure structure — connectors (``in``, ``at``,
    ``a``, ``the``, ``per``, ``of``), the quantifiers ``each``/``every``, the
    pronoun ``i``, the relation word ``dose``, the medication names and the
    ``<dose>`` placeholder. What remains either asserts administration
    (``take``/``prescribed``/``advised``/``on``…) or pins a schedule
    (``daily``, ``twice``, ``morning``, ``night``…) — and the pinned
    error-grade cases are exactly those: "paracetamol 500 mg in the morning",
    "paracetamol 1000mg at night", "Paracetamol 500 mg advised."
    """
    if not all(
        token == "<dose>"
        or token in _EXCLUSIVE_DOSE_CONTEXT
        or token in _MEDICATION_LEXICON
        for token in context
    ):
        return False
    return any(token in _ADMINISTRATION_WITNESS for token in context)


def _same_state(mine: _StructuredClaim, other: _StructuredClaim) -> bool:
    """Mechanically-established same-EXCLUSIVE-state identity (rounds 23-24
    PR-MED-002/003): the two statements are token-identical once each dose
    atom is collapsed AND that shared wording is drawn wholly from the
    closed exclusive-administration grammar — a current regimen fact whose
    single strength slot cannot hold two values at once. Token identity
    alone is NOT sufficient: two identically-worded INVENTORY statements
    ("… tablets remaining") can both be true, a patient holding both
    strengths. Anything less than exclusive identity (a dose change, a
    titration, an inventory or product strength, differing or novel regimen
    wording) is not provably the same exclusive state and must not
    hard-block."""
    return (
        mine.context is not None
        and other.context is not None
        and mine.context == other.context
        and _exclusive_context(mine.context)
    )


def _dose_mismatch_warning(
    flagged: NoteAssertion, evidence: _StructuredClaim | None
) -> NoteWarning:
    return NoteWarning(
        note_warning_code="dose_mismatch",
        severity="review",
        section_key=flagged.section_key,
        assertion_id=flagged.assertion_id,
        source_coords=evidence.source_coords if evidence is not None else None,
    )


def contradiction_warnings(
    note: GeneratedNote, document: TranscriptDocument
) -> tuple[NoteWarning, ...]:
    """Anchored contradictions against confirmed clinician-authored
    assertions — pairwise among themselves (always ``contradiction``: both
    sides are confirmed text with no acoustic evidence to doubt), and each
    against the note's exactly-reconstructing transcript assertions, graded
    by the transcript evidence's raw probability. The warning is attributed
    to the clinician-authored assertion; for an authored-vs-authored pair it
    sits on the LATER assertion in note order, once per matched anchor."""
    authored = _structured_authored(note)
    quoted = _structured_quoted(note, document)
    warnings: list[NoteWarning] = []
    for (_, earlier_claims), (later, later_claims) in combinations(authored, 2):
        for key in sorted(set(earlier_claims) & set(later_claims)):
            mine, other = later_claims[key], earlier_claims[key]
            if mine.claim_value == other.claim_value:
                continue
            if key[0] == "dose" and not _same_state(mine, other):
                warnings.append(_dose_mismatch_warning(later, None))
            else:
                warnings.append(_contradiction_warning(later, None))
    for assertion, claims in authored:
        for _, quoted_claims in quoted:
            for key in sorted(set(claims) & set(quoted_claims)):
                mine, other = claims[key], quoted_claims[key]
                if mine.claim_value == other.claim_value:
                    continue
                if key[0] == "dose" and not _same_state(mine, other):
                    warnings.append(_dose_mismatch_warning(assertion, other))
                else:
                    warnings.append(_contradiction_warning(assertion, other))
    return tuple(warnings)


# ---------------------------------------------------------------------------
# Check 3 — provenance integrity (Task 5.3).
# ---------------------------------------------------------------------------


def _rule_for_assertion(
    config: NoteConfig, assertion: NoteAssertion, session_id: str
) -> AutofillRule | None:
    """The autofill rule that authored ``assertion``, re-derived through the
    content-derived proposal id (rule, entry position, config digest,
    session). A proposal id no (rule, entry) of THIS config reproduces —
    including any authored under a different config digest — resolves to
    None, and the caller fails closed into ``autofill_trigger_absent``."""
    config_digest = config.config_digest()
    for rule in config.autofill_rules:
        for entry_index in range(len(rule.expansion)):
            proposal_id = _proposal_id(
                "autofill", rule.rule_id, entry_index, config_digest, session_id
            )
            if proposal_id == assertion.proposal_id:
                return rule
    return None


def provenance_warnings(
    note: GeneratedNote,
    document: TranscriptDocument,
    config: NoteConfig,
    *,
    pending_proposals: Sequence[NoteProposal] = (),
) -> tuple[NoteWarning, ...]:
    """Check 3, codes exactly as the plan enumerates (module docstring).

    ``pending_proposals`` is the set of emitted proposals the clinician has
    not yet resolved when the check runs: each one is an
    ``unconfirmed_proposal`` error — unconfirmed content cannot BE in the
    note (structural), so the error's job is to block ``write_note`` until
    every proposal is explicitly confirmed or declined. A declined proposal
    is resolved and never reaches this function.

    A note whose ``template_profile_id`` is not a member of the presented
    config RAISES ``TemplateProfileUnboundError`` (via
    ``bind_template_profile``) rather than warning: that is a malformed
    artifact, unreachable through ``build_note_request``, and mis-checking
    it quietly would be false confidence. ``check_note``'s digest gate makes
    this unreachable for generation-produced notes checked against their
    own config.
    """
    resolved = _canonical_config(config)
    warnings: list[NoteWarning] = []
    for proposal in pending_proposals:
        warnings.append(
            NoteWarning(
                note_warning_code="unconfirmed_proposal",
                severity="error",
                section_key=proposal.section_key,
            )
        )
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.provenance == "transcript":
                continue
            warnings.append(
                NoteWarning(
                    note_warning_code="clinician_asserted",
                    severity="review",
                    section_key=section.section_key,
                    assertion_id=assertion.assertion_id,
                )
            )
            if assertion.provenance != "autofill":
                continue
            rule = _rule_for_assertion(resolved, assertion, note.session_id)
            if rule is None or (
                _first_phrase_match(document, content_tokens(rule.trigger_phrase)) is None
            ):
                warnings.append(
                    NoteWarning(
                        note_warning_code="autofill_trigger_absent",
                        severity="error",
                        section_key=section.section_key,
                        assertion_id=assertion.assertion_id,
                    )
                )
    for section in note.note_sections:
        if section.section_key not in CLINICIAN_OWNED_SECTIONS:
            continue
        if not section.note_assertions:
            continue
        if note.clinician_speaker is None:
            warnings.append(
                NoteWarning(
                    note_warning_code="role_unconfirmed",
                    severity="error",
                    section_key=section.section_key,
                )
            )
            continue
        for assertion in section.note_assertions:
            if assertion.provenance != "transcript":
                continue
            coords = _resolved_coords(assertion)
            words = _words_for_coords(document, coords)
            if words is None:
                # Check 1's `source_coords_invalid` already blocks this
                # assertion; there is no segment to derive a speaker from.
                continue
            source_speaker = document.transcript_segments[coords.segment_index].speaker
            if source_speaker != note.clinician_speaker:
                warnings.append(
                    NoteWarning(
                        note_warning_code="role_unconfirmed",
                        severity="error",
                        section_key=section.section_key,
                        assertion_id=assertion.assertion_id,
                        source_coords=coords,
                    )
                )
    binding = bind_template_profile(resolved, note.template_profile_id)
    warnings.extend(mapping_drop_warnings(binding.template_profile, note.note_sections))
    return tuple(warnings)


# ---------------------------------------------------------------------------
# Check 4 — scoped omission (Task 5.4).
# ---------------------------------------------------------------------------


def _is_high_risk_token(text: str, *, first_in_segment: bool) -> bool:
    if is_number_token(text) or is_name_like_token(text, first_in_segment=first_in_segment):
        return True
    return normalise_token(text) in _MEDICATION_LEXICON


def omission_warnings(
    note: GeneratedNote, document: TranscriptDocument
) -> tuple[NoteWarning, ...]:
    """One ``high_risk_omission`` review warning per clinician-attributed
    segment whose high-risk tokens are not all carried by some assertion's
    coordinates (Task 5.4; scope and stated limit in the module docstring).

    Coverage counts coordinate CARRIAGE, not faithfulness: an assertion
    whose text was mutated still cites the words, and Check 1's error
    already blocks it — a second warning here would be noise, not signal.
    """
    if note.clinician_speaker is None:
        return ()
    covered: set[tuple[int, int]] = set()
    for section in note.note_sections:
        for assertion in section.note_assertions:
            if assertion.provenance != "transcript":
                continue
            coords = _resolved_coords(assertion)
            if _words_for_coords(document, coords) is None:
                continue
            for word_index in range(coords.first_word_index, coords.last_word_index + 1):
                covered.add((coords.segment_index, word_index))
    warnings: list[NoteWarning] = []
    for segment_index, segment in enumerate(document.transcript_segments):
        if segment.speaker != note.clinician_speaker:
            continue
        uncovered = [
            word_index
            for word_index, word in enumerate(segment.transcript_words)
            if (segment_index, word_index) not in covered
            and _is_high_risk_token(word.word_text, first_in_segment=word_index == 0)
        ]
        if uncovered:
            warnings.append(
                NoteWarning(
                    note_warning_code="high_risk_omission",
                    severity="review",
                    source_coords=SourceCoords(segment_index, min(uncovered), max(uncovered)),
                )
            )
    return tuple(warnings)


# ---------------------------------------------------------------------------
# The stage entry point.
# ---------------------------------------------------------------------------


def check_note(
    note: GeneratedNote,
    document: TranscriptDocument,
    config: NoteConfig,
    *,
    pending_proposals: Sequence[NoteProposal] = (),
) -> tuple[NoteWarning, ...]:
    """Run all four checks over a composed note (pipeline order: compose ->
    confirm -> CHECK -> write) and return their warnings, check by check in
    a deterministic order.

    Refuses — rather than silently mis-checks — when the note's recorded
    ``transcript_digest`` or ``config_digest`` does not match the presented
    artifacts: a mismatch means this transcript or config is NOT what the
    note was generated from, and warnings computed against the wrong
    artifact would be false confidence in both directions. The individual
    check functions stay callable directly (the fixture matrix drives them
    that way); this gate is the composed entry's contract.
    """
    resolved = _canonical_config(config)
    if note.transcript_digest != transcript_digest(document):
        raise CheckTargetMismatchError(
            "the note's transcript_digest does not match the presented transcript"
        )
    if note.config_digest != resolved.config_digest():
        raise CheckTargetMismatchError(
            "the note's config_digest does not match the presented config"
        )
    return (
        *reconstruction_warnings(note, document),
        *contradiction_warnings(note, document),
        *provenance_warnings(
            note, document, resolved, pending_proposals=pending_proposals
        ),
        *omission_warnings(note, document),
    )


__all__ = [
    "CheckTargetMismatchError",
    "NoteCheckError",
    "check_note",
    "contradiction_warnings",
    "omission_warnings",
    "provenance_warnings",
    "reconstruction_warnings",
]
