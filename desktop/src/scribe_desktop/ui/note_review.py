"""The Note tab's review DECISIONS, Qt-free (note-learning plan Task H6).

``ui.note.NoteScreen`` keeps every piece of review STATE — the clicked
decisions, the removed / added / typed lines, the learning queues — and the
order in which it mutates them. What it asks of that state lives here: each
function takes the draft, the document, the config and the widget's current
dicts and sets as parameters and RETURNS its verdict, so the rules are
testable with plain inputs and no widget. Nothing here holds a reference to
the widget, imports Qt or ``logging`` (C9: the verdicts carry status text that
quotes clinical words, and the widget only shows it), or names the note
request types (the construction guard in ``tests/test_note_config.py``).

- Resolutions (C3, D5): a proposal replaced by a typed line or Removed is
  DECLINED by the clinician; a clicked decision stands; otherwise a config
  decision the emitter minted is passed on unchanged (the counted Save
  ratifies it); anything else stays pending. The shown-text digest is taken
  from the text the widget RENDERED — the map it filled by reading each row
  label back — never from the proposal, so a rendering bug produces evidence
  ``finalise_note`` refuses; only a pre-filled line, which has no row, names
  its own excerpt (the text the note body showed).
- Learned-rule outcomes at Save (D5): ``confirmed`` / ``removed`` per learned
  rule whose line was in play, ``removed`` winning.
- Phrase learning (D9 as amended) and shorthand learning (D5, D11): the
  verdict — what to queue, or nothing — plus the exact status texts the
  widget appends, in order. The ownership test comes FIRST and never consults
  the learning status: the status callable (the widget's re-read, which also
  repaints its learning line) is called only once the line is the confirmed
  clinician's own, or is a learned rule's own line. THE refusal filter
  (``note_config.refuse_learning_candidate``) is called here and nowhere else
  on the Note tab.
- The review counts ``NoteScreen.current_review_state`` reports.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NamedTuple

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    ConfirmationDecision,
    GeneratedNote,
    NoteAssertion,
    NoteDraft,
    NoteProposal,
    NoteSectionKey,
    ProposalResolution,
    content_tokens,
    first_matching_section,
    is_interrogative,
    reconstruct_span_text,
    spoken_by_confirmed_clinician,
    text_digest,
)
from scribe_desktop.note_config import (
    LearnedRuleCandidate,
    NoteConfig,
    RuleOutcome,
    is_learned_rule_id,
    learned_rule_problem,
    plain_rule_problem,
    propose_learning_phrase,
    propose_rule_trigger,
    refuse_learning_candidate,
    refuse_typed_wording,
)
from scribe_desktop.transcription import TranscriptDocument
from scribe_desktop.ui import models

ProposalDecision = Literal["confirmed", "declined"]
LearningStatusReader = Callable[[], models.LearningStatus]


class RuleReplacement(NamedTuple):
    """A learned rule's wording replaced in place at Save (D5). A tuple, so
    it compares equal to the ``(rule_id, wording)`` pair it types."""

    rule_id: str
    wording: str


@dataclass(frozen=True)
class PhraseLearningVerdict:
    """What an add or a move teaches: the ``(section, phrase)`` to queue, or
    None, and the status texts to append in order."""

    queued: tuple[NoteSectionKey, str] | None = None
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleLearningVerdict:
    """What a typed edit teaches: a new rule to queue, OR an in-place
    wording replacement, or neither — and the status texts to append."""

    rule: LearnedRuleCandidate | None = None
    replacement: RuleReplacement | None = None
    messages: tuple[str, ...] = ()


class ReviewCounts(NamedTuple):
    unconfirmed_proposals: int
    blocking_errors: int
    unacknowledged_reviews: int


def prefilled_ids(draft: NoteDraft | None) -> frozenset[str]:
    """The proposals the practitioner's own config decided (D5): no
    confirm/decline row — they are in the note, marked, until Removed."""
    if draft is None:
        return frozenset()
    return frozenset(decision.proposal_id for decision in draft.config_decisions)


def proposal_by_id(draft: NoteDraft | None, proposal_id: str) -> NoteProposal | None:
    if draft is None:
        return None
    return next((p for p in draft.note_proposals if p.proposal_id == proposal_id), None)


# --- resolutions (C3, D5) ----------------------------------------------------


def clinician_resolution(
    proposal: NoteProposal,
    decision: ProposalDecision,
    *,
    rendered_excerpt: Mapping[str, str],
    now: datetime,
) -> ProposalResolution:
    # The digest of what the row RENDERED for a proposal with a row; a
    # pre-filled line has no row and its decline names the text the note
    # body showed — the proposal's own excerpt, rendered by the one
    # rendering path (the same residue ``config_decisions`` states).
    rendered = rendered_excerpt.get(proposal.proposal_id, proposal.note_excerpt)
    return ProposalResolution(
        shown_text_digest=text_digest(rendered),
        confirmation=ConfirmationDecision(
            proposal_id=proposal.proposal_id,
            note_confirmation=decision,
            decided_at=now,
        ),
    )


def build_resolutions(
    draft: NoteDraft,
    *,
    resolutions: Mapping[str, ProposalDecision],
    removed: Collection[str],
    edited_proposals: Collection[str],
    rendered_excerpt: Mapping[str, str],
    now: datetime,
) -> list[ProposalResolution]:
    """One resolution per decided proposal, the clinician's decision first
    (D5): a proposal replaced by a typed line or Removed is DECLINED by the
    clinician; a clicked decision stands; otherwise a config decision the
    emitter minted is passed on unchanged (the counted Save ratifies it);
    anything else is pending."""
    minted = {decision.proposal_id: decision for decision in draft.config_decisions}
    built: list[ProposalResolution] = []
    for proposal in draft.note_proposals:
        pid = proposal.proposal_id
        if pid in edited_proposals or pid in removed:
            built.append(
                clinician_resolution(
                    proposal, "declined", rendered_excerpt=rendered_excerpt, now=now
                )
            )
            continue
        decision = resolutions.get(pid)
        if decision is not None:
            built.append(
                clinician_resolution(proposal, decision, rendered_excerpt=rendered_excerpt, now=now)
            )
            continue
        config_decision = minted.get(pid)
        if config_decision is not None:
            built.append(config_decision)
        # else pending -> finalise_note flags unconfirmed_proposal
    return built


# --- learned-rule outcomes at Save (D5) ----------------------------------------


def learned_rule_outcomes(
    draft: NoteDraft,
    *,
    resolutions: Mapping[str, ProposalDecision],
    removed: Collection[str],
    edited_proposals: Collection[str],
) -> dict[str, RuleOutcome]:
    """What this Save says about each LEARNED rule whose line was in play
    (D5): ``confirmed`` when its proposed line was confirmed by click, or its
    pre-filled line stood unedited; ``removed`` when the line was declined,
    Removed or replaced by a typed line — and ``removed`` wins for a rule with
    lines in both states."""
    prefilled = prefilled_ids(draft)
    outcomes: dict[str, RuleOutcome] = {}
    for proposal in draft.note_proposals:
        if proposal.provenance != "autofill" or not is_learned_rule_id(proposal.rule_id):
            continue
        pid = proposal.proposal_id
        if pid in edited_proposals or pid in removed:
            outcome: RuleOutcome | None = "removed"
        elif pid in prefilled:
            outcome = "confirmed"
        else:
            clicked = resolutions.get(pid)
            outcome = "confirmed" if clicked == "confirmed" else "removed" if clicked else None
        if outcome is None:
            continue
        if outcomes.get(proposal.rule_id) != "removed":
            outcomes[proposal.rule_id] = outcome
    return outcomes


# --- shorthand learning (note-learning plan Task 2.3; D5, D11) -----------------


def consider_rule_learning(
    typed: NoteAssertion,
    *,
    draft: NoteDraft,
    document: TranscriptDocument,
    config: NoteConfig,
    segment_index: int | None,
    learning_status: LearningStatusReader,
) -> RuleLearningVerdict:
    """The shorthand the typed line ``typed`` teaches, or why not. The
    source is what the line REPLACED (``typed.replaces``): one of the
    practitioner's OWN utterances — ``segment_index``, the segment the
    replaced line quotes, tested for ownership first and without reading the
    learning status — yields a new rule (trigger from the utterance's tail
    through THE refusal filter, wording through ``refuse_typed_wording``) or,
    when that trigger is already a learned rule's, an in-place wording
    replacement; a LEARNED rule's own line (proposed or pre-filled) yields an
    in-place replacement too. Both correction paths validate the wording as
    the rules file will at Save, so "Will update" is never withdrawn. A
    hand-authored config line has no utterance to learn from (the plan's
    Excluded item) and teaches nothing."""
    target = typed.replaces
    if target is None:
        return RuleLearningVerdict()
    proposal = proposal_by_id(draft, target)
    if proposal is not None:
        if proposal.provenance != "autofill" or not is_learned_rule_id(proposal.rule_id):
            return RuleLearningVerdict(
                messages=(
                    "Not learned: this line came from your own config, not from a line you said.",
                )
            )
        status = learning_status()
        if not status.enabled:
            return RuleLearningVerdict(messages=(status.reason or "",))
        refusal = refuse_typed_wording(typed.text)
        if refusal is not None:
            return RuleLearningVerdict(
                messages=(
                    f"Shorthand not updated: the wording contains a number/date/medication "
                    f"({refusal}).",
                )
            )
        # The rules file's own validation runs here too (Phase H smoke item
        # 2, leg h1l): the correction is validated against the rule it
        # replaces — the same trigger and section Save's
        # `replace_learned_rule_wording` validates — so "Will update" is never
        # withdrawn at Save, and the line says the clinician's reason.
        rule = next((r for r in config.autofill_rules if r.rule_id == proposal.rule_id), None)
        if rule is None:
            return RuleLearningVerdict(
                messages=("Shorthand not updated: that shorthand is no longer in your rules file.",)
            )
        correction = LearnedRuleCandidate(rule.section_key, rule.trigger_phrase, typed.text)
        if learned_rule_problem(correction) is not None:
            return RuleLearningVerdict(
                messages=(f"Shorthand not updated: {plain_rule_problem(typed.text)}.",)
            )
        return RuleLearningVerdict(
            replacement=RuleReplacement(proposal.rule_id, typed.text),
            messages=(
                "Will update this learned shorthand rule's wording to your line when you "
                "press Save note on this tab (it will propose again until confirmed 3 times).",
            ),
        )
    if segment_index is None:
        return RuleLearningVerdict()
    segment = document.transcript_segments[segment_index]
    if not spoken_by_confirmed_clinician(segment.speaker, draft.clinician_speaker):
        return RuleLearningVerdict(messages=(models.LEARNING_NOT_ATTRIBUTED_NOTE,))
    status = learning_status()
    if not status.enabled:
        return RuleLearningVerdict(messages=(status.reason or "",))
    words = [word.word_text for word in segment.transcript_words]
    candidate = propose_rule_trigger(words)
    if candidate is None:
        return RuleLearningVerdict(
            messages=("Not learned: the line is too short to make a trigger.",)
        )
    refusal = refuse_learning_candidate(
        candidate.source_words,
        first_in_segment=candidate.first_in_segment,
        following=candidate.following,
    )
    if refusal is not None:
        return RuleLearningVerdict(
            messages=(
                f"Not learned: the trigger contains a name/number/date/medication ({refusal}).",
            )
        )
    wording_refusal = refuse_typed_wording(typed.text)
    if wording_refusal is not None:
        return RuleLearningVerdict(
            messages=(
                f"Not learned: the typed wording contains a number/date/medication "
                f"({wording_refusal}).",
            )
        )
    queued = LearnedRuleCandidate(typed.section_key, candidate.phrase, typed.text)
    # Phase H round 24 LOW-005: the rules file's own validation runs at the
    # edit too (the same validator Save runs), so "Will learn" / "Will
    # update" is said only for a wording the file will accept — never a
    # promise Save then withdraws. It runs BEFORE the trigger match so a
    # correction to an already-learned shorthand is checked the same way
    # (Phase H smoke item 2), and the status line says the clinician's
    # reason — the validator's authoring message (rule id, entry position,
    # the JSON override) never reaches the screen.
    if learned_rule_problem(queued) is not None:
        return RuleLearningVerdict(messages=(f"Not learned: {plain_rule_problem(typed.text)}.",))
    trigger_tokens = tuple(candidate.phrase.split(" "))
    for rule in config.autofill_rules:
        if content_tokens(rule.trigger_phrase) != trigger_tokens:
            continue
        if is_learned_rule_id(rule.rule_id):
            # The same utterance was learned before: D5 — replace that
            # rule's wording in place, never a second rule under one trigger.
            return RuleLearningVerdict(
                replacement=RuleReplacement(rule.rule_id, typed.text),
                messages=(
                    f"Will update the learned shorthand for '{candidate.phrase}' to your "
                    "wording when you press Save note on this tab.",
                ),
            )
        return RuleLearningVerdict(
            messages=(
                f"Not learned: '{candidate.phrase}' is already a trigger in your rules file.",
            )
        )
    return RuleLearningVerdict(
        rule=queued,
        messages=(
            f"Will learn shorthand: '{candidate.phrase}' -> '{typed.text}' for "
            f"{models.section_title(typed.section_key)} when you press Save note on this tab.",
        ),
    )


# --- phrase learning (D9 as amended) -------------------------------------------


def consider_learning(
    assertion: NoteAssertion,
    *,
    draft: NoteDraft,
    document: TranscriptDocument,
    config: NoteConfig,
    learning_status: LearningStatusReader,
) -> PhraseLearningVerdict:
    """The phrase an added or moved line teaches, or why not. The ownership
    test comes FIRST and never reads the learning status: a line that is not
    the confirmed clinician's is never a candidate, whatever the status —
    but the verdict SAYS so (live smoke 2026-09-17: a silent skip reads as a
    broken feature)."""
    coords = assertion.note_span.source_coords
    if coords is None:
        return PhraseLearningVerdict()
    segment = document.transcript_segments[coords.segment_index]
    if not spoken_by_confirmed_clinician(segment.speaker, draft.clinician_speaker):
        return PhraseLearningVerdict(messages=(models.LEARNING_NOT_ATTRIBUTED_NOTE,))
    status = learning_status()
    if not status.enabled:
        return PhraseLearningVerdict(messages=(status.reason or "",))
    words = [word.word_text for word in segment.transcript_words]
    candidate = propose_learning_phrase(words)
    if candidate is None:
        return PhraseLearningVerdict(
            messages=("Not learned: the line is too short to make a phrase.",)
        )
    # The REAL segment-start status travels with the candidate (peer round
    # 36 PR-HIGH-008): a leading filler that was dropped does not hand the
    # opener exemption to the word after it.
    refusal = refuse_learning_candidate(
        candidate.source_words,
        first_in_segment=candidate.first_in_segment,
        following=candidate.following,
    )
    if refusal is not None:
        return PhraseLearningVerdict(
            messages=(f"Not learned: contains a name/number/date/medication ({refusal}).",)
        )
    tokens = tuple(candidate.phrase.split(" "))
    cues = config.normalised_cues()
    for key, phrases in cues.items():
        if tokens in phrases:
            return PhraseLearningVerdict(
                messages=(
                    f"Not learned: '{candidate.phrase}' is already a cue for "
                    f"{models.section_title(key)}.",
                )
            )
    section_key = assertion.section_key
    proposed = dict(cues)
    proposed[section_key] = (*proposed.get(section_key, ()), tokens)
    text = reconstruct_span_text(segment.transcript_words)
    winner = first_matching_section(
        proposed,
        content_tokens(text),
        CANONICAL_SECTION_KEYS,
        speaker=segment.speaker,
        clinician_speaker=draft.clinician_speaker,
        question=is_interrogative(text),
    )
    message = (
        f"Will learn '{candidate.phrase}' for {models.section_title(section_key)} "
        "when you press Save note on this tab."
    )
    if winner is not None and winner != section_key:
        # PR-MED-011: noted, never a silent cue deletion — the earlier
        # section's cue keeps first-match routing for lines like this one.
        message += f" Note: a {models.section_title(winner)} cue still routes this line first."
    return PhraseLearningVerdict(queued=(section_key, candidate.phrase), messages=(message,))


# --- the review counts ---------------------------------------------------------


def review_counts(
    draft: NoteDraft,
    note: GeneratedNote,
    *,
    resolutions: Collection[str],
    edited_proposals: Collection[str],
    acknowledged: Collection[str],
) -> ReviewCounts:
    """Pending proposals (neither clicked, pre-filled nor typed over), the
    blocking warnings, and the review-warning groups not yet acknowledged."""
    summary = models.summarise_warnings(note.note_warnings)
    decided = set(resolutions) | prefilled_ids(draft) | set(edited_proposals)
    pending = sum(1 for proposal in draft.note_proposals if proposal.proposal_id not in decided)
    unacknowledged = sum(1 for group in summary.review if group.code not in acknowledged)
    return ReviewCounts(
        unconfirmed_proposals=pending,
        blocking_errors=summary.blocking_count,
        unacknowledged_reviews=unacknowledged,
    )
