"""Autofill and prefill (Phase 3A, Tasks 4.1-4.2).

This module turns clinician-authored config — autofill rules and prefill
templates (``note_config.py``) — into ``NoteProposal`` candidates against a
finished transcript. Its entire output surface is PROPOSALS:

- **Everything emitted here awaits confirmation.** A ``NoteProposal`` is
  structurally distinct from ``NoteAssertion`` and cannot be placed in a
  ``GeneratedSection`` (``note.py``), so nothing this module produces can
  reach ``note.enc`` without the clinician's explicit per-assertion
  confirmation of the exact shown wording. What enforces this: every
  public function here is TYPED to return only ``NoteProposal`` tuples
  (mypy-strict) and the outputs are pinned proposal-only by test — a
  matched trigger makes a rule a CANDIDATE, never a note line (plan
  Critical Constraints; the round-1 CRIT reversal).
- **One proposal per ATOMIC assertion.** Expansions and seeds are authored
  as lists of atomic assertions; each list entry becomes its own proposal,
  because confirming a block is not evidence about each claim inside it. No
  text is joined, split, deduplicated, or rewritten here — this module is a
  mechanical one-authored-entry -> one-proposal mapper (pinned by test).
  ATOMICITY of each entry is enforced at the CONFIG AUTHORING boundary
  (Task 4.0 + rounds 15-17 in ``note_config.py``): outer-shape refusal, a
  conservative single-claim ALLOW-LIST (``_is_atomic_shape`` — an entry is
  accepted only when it matches the atomic shape, so unforeseen separators
  fail closed) with an explicit per-entry ``single_claim`` override, and
  normalised duplicate rejection. The residue is COMPLETE-BY-CONSTRUCTION,
  defined in ``note_config.py``'s shape comment by REFERENCE to the
  shape's own permissive branches (rounds 15-18 each falsified a prose
  enumeration, so no list is repeated here): claims joined only through
  accepted material — every member of ``_ALLOWED_IN_CLAIM_PUNCT`` at any
  position, words/spaces, hyphen-between-alphanumerics, digit-boundary
  adjacency — plus override misuse, all mechanically inseparable from the
  legitimate wording those positions admit. Accepted by design; Phase 7's
  per-assertion confirmation UI and Phase 5's checking stage are the
  compensating controls, and nothing here or there parses sentence
  meaning.
- **Matching runs against the transcript, never against the note**, and is
  deliberately SPEAKER-AGNOSTIC: presence gates candidacy, not truth, so a
  trigger spoken by the patient produces exactly the same proposals as one
  spoken by the clinician — and in both cases only proposals (pinned; the
  round-1 CRIT's failure case).

Matching semantics, recorded because each is a decision:

- Tokenisation is ``note.content_tokens`` applied per transcript word — THE
  single normalisation source (Task 1.2's pin). Trigger phrases and
  transcript words normalise through the same function, so disfluencies
  ("um") interleaved inside a spoken trigger do not defeat the match and no
  second tokeniser exists.
- A phrase matches only as a contiguous token run WITHIN ONE SEGMENT. A
  trigger straddling a VAD segment boundary does not fire: a segment is one
  speaker's contiguous speech, and the failure direction is the safe one —
  a missed match yields no proposal (silence), never a wrong candidate.
- A rule fires on its FIRST occurrence in transcript order and carries that
  occurrence's start time. Later repetitions add nothing: the rule is
  already a candidate, and duplicate proposals for identical text would be
  confirmation fatigue with no additional evidence.

Config custody: both entry points canonicalise the incoming config
(``note_config._canonical_config`` — the round-12 boundary lesson), so the
``config_digest`` stamped on every proposal is derived from exact
re-validated field data, and the digest a later confirmation records
identifies the config content that actually authored the text.
"""

from __future__ import annotations

import hashlib
from typing import Final, NamedTuple

from scribe_desktop.note import NoteProposal, content_tokens
from scribe_desktop.note_config import (
    # Package-private by name, shared deliberately (the note.py convention):
    # the generation-boundary canonicaliser is THE answer to forged or
    # validator-skipping configs, and proposals must stamp the same digest
    # the boundary would derive.
    NoteConfig,
    PrefillTemplate,
    _canonical_config,
)
from scribe_desktop.transcription import TranscriptDocument

_PROPOSAL_ID_HEX_CHARS: Final = 24


class NoteFillError(Exception):
    """Base class for autofill/prefill failures."""


class UnknownPrefillError(NoteFillError):
    """An explicit prefill_id names no configured prefill template."""


class PrefillSelectionAmbiguousError(NoteFillError):
    """More than one prefill template matches and no explicit choice was
    made — the one case where a chooser UI appears (the
    ``bind_template_profile`` shape)."""

    def __init__(self, candidate_ids: tuple[str, ...]) -> None:
        self.candidate_ids = candidate_ids
        super().__init__(
            f"{len(candidate_ids)} prefill templates match "
            f"({', '.join(candidate_ids)}); an explicit prefill_id is required"
        )


class _PhraseMatch(NamedTuple):
    """Where a phrase first matched: transcript coordinates plus the start
    time of the first matched word (what a proposal carries as
    ``trigger_start_seconds``)."""

    segment_index: int
    first_word_index: int
    start_seconds: float


class PrefillCandidate(NamedTuple):
    """One detected body-region prefill, for the chooser/override UI."""

    prefill_id: str
    display_name: str
    start_seconds: float


def _first_phrase_match(
    document: TranscriptDocument, phrase_tokens: tuple[str, ...]
) -> _PhraseMatch | None:
    """First contiguous occurrence of ``phrase_tokens`` in transcript order,
    or None. Content tokens only, per word, within one segment (module
    docstring records why); an empty phrase never matches."""
    if not phrase_tokens:
        return None
    span = len(phrase_tokens)
    for segment_index, segment in enumerate(document.transcript_segments):
        indexed: list[tuple[str, int]] = []
        for word_index, word in enumerate(segment.transcript_words):
            for token in content_tokens(word.word_text):
                indexed.append((token, word_index))
        if len(indexed) < span:
            continue
        for start in range(len(indexed) - span + 1):
            if tuple(token for token, _ in indexed[start : start + span]) == phrase_tokens:
                first_word_index = indexed[start][1]
                return _PhraseMatch(
                    segment_index=segment_index,
                    first_word_index=first_word_index,
                    start_seconds=segment.transcript_words[first_word_index].start_seconds,
                )
    return None


def _proposal_id(
    provenance: str,
    source_id: str,
    entry_index: int,
    config_digest: str,
    session_id: str,
) -> str:
    """Deterministic, id-grammar-safe proposal id.

    Content-derived (rule/prefill id, entry position, config digest,
    session) so the same inputs always name the same proposal — confirmation
    evidence stays stable across regeneration — while staying inside
    ``_ID_PATTERN``'s 64-char bound regardless of how long the authored ids
    are.
    """
    key = "\x1f".join((provenance, source_id, str(entry_index), config_digest, session_id))
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"{provenance}-{digest[:_PROPOSAL_ID_HEX_CHARS]}"


def autofill_proposals(
    document: TranscriptDocument, config: NoteConfig
) -> tuple[NoteProposal, ...]:
    """Task 4.1: match each rule's trigger against the transcript and emit
    one ``NoteProposal`` PER ATOMIC ASSERTION in the matched rule's
    expansion — a three-assertion expansion is three proposals.

    A rule whose trigger is absent cannot fire. Matching is speaker-agnostic
    and the output is proposals only — never an assertion, never an
    insertion (module docstring; both pinned by test).
    """
    resolved = _canonical_config(config)
    config_digest = resolved.config_digest()
    proposals: list[NoteProposal] = []
    for rule in resolved.autofill_rules:
        match = _first_phrase_match(document, content_tokens(rule.trigger_phrase))
        if match is None:
            continue
        for entry_index, assertion_text in enumerate(rule.expansion_texts()):
            proposals.append(
                NoteProposal(
                    proposal_id=_proposal_id(
                        "autofill",
                        rule.rule_id,
                        entry_index,
                        config_digest,
                        document.session_id,
                    ),
                    section_key=rule.section_key,
                    provenance="autofill",
                    note_excerpt=assertion_text,
                    rule_id=rule.rule_id,
                    config_digest=config_digest,
                    trigger_start_seconds=match.start_seconds,
                )
            )
    return tuple(proposals)


def _earliest_keyword_match(
    document: TranscriptDocument, prefill: PrefillTemplate
) -> _PhraseMatch | None:
    """The earliest match among a prefill's region keywords, or None."""
    best: _PhraseMatch | None = None
    for keyword in prefill.region_keywords:
        match = _first_phrase_match(document, content_tokens(keyword))
        if match is None:
            continue
        if best is None or (match.segment_index, match.first_word_index) < (
            best.segment_index,
            best.first_word_index,
        ):
            best = match
    return best


def detect_prefill_candidates(
    document: TranscriptDocument, config: NoteConfig
) -> tuple[PrefillCandidate, ...]:
    """Task 4.2 detection: every prefill template whose region keywords
    occur in the transcript, ordered by earliest match (tie: config order).
    Detection PRESELECTS; it decides nothing — the clinician's explicit
    choice (``prefill_proposals``'s ``prefill_id``) always overrides.

    Deliberately does NOT canonicalise: detection emits ids and times only —
    no digest is stamped and no proposal text leaves here. The two proposal
    emitters canonicalise before stamping anything.
    """
    matched: list[tuple[tuple[int, int, int], PrefillCandidate]] = []
    for config_index, prefill in enumerate(config.prefill_templates):
        match = _earliest_keyword_match(document, prefill)
        if match is None:
            continue
        order = (match.segment_index, match.first_word_index, config_index)
        matched.append(
            (
                order,
                PrefillCandidate(
                    prefill_id=prefill.prefill_id,
                    display_name=prefill.display_name,
                    start_seconds=match.start_seconds,
                ),
            )
        )
    return tuple(candidate for _, candidate in sorted(matched))


def prefill_proposals(
    document: TranscriptDocument, config: NoteConfig, prefill_id: str | None = None
) -> tuple[NoteProposal, ...]:
    """Task 4.2: one ``NoteProposal`` per atomic assertion in the SELECTED
    seed.

    Selection mirrors ``bind_template_profile``: an explicit ``prefill_id``
    is the clinician's override and wins outright — it need not have been
    detected, because region keywords are a heuristic and the clinician is
    not (an unknown id raises). With no explicit choice, a single detected
    region selects itself, zero detections emit nothing, and several
    detections raise ``PrefillSelectionAmbiguousError`` — the chooser case;
    the engine never guesses which region the consultation was about.
    """
    resolved = _canonical_config(config)
    config_digest = resolved.config_digest()
    selected: PrefillTemplate | None = None
    if prefill_id is not None:
        for prefill in resolved.prefill_templates:
            if prefill.prefill_id == prefill_id:
                selected = prefill
                break
        if selected is None:
            raise UnknownPrefillError(f"unknown prefill_id: {prefill_id}")
    else:
        candidates = detect_prefill_candidates(document, resolved)
        if not candidates:
            return ()
        if len(candidates) > 1:
            raise PrefillSelectionAmbiguousError(
                tuple(candidate.prefill_id for candidate in candidates)
            )
        for prefill in resolved.prefill_templates:
            if prefill.prefill_id == candidates[0].prefill_id:
                selected = prefill
                break
        if selected is None:
            raise AssertionError(
                "unreachable: candidates derive from resolved.prefill_templates"
            )
    match = _earliest_keyword_match(document, selected)
    trigger_start = match.start_seconds if match is not None else None
    return tuple(
        NoteProposal(
            proposal_id=_proposal_id(
                "prefill",
                selected.prefill_id,
                entry_index,
                config_digest,
                document.session_id,
            ),
            section_key=seed.section_key,
            provenance="prefill",
            note_excerpt=seed.seed_text,
            rule_id=selected.prefill_id,
            config_digest=config_digest,
            trigger_start_seconds=trigger_start,
        )
        for entry_index, seed in enumerate(selected.seed_assertions)
    )
