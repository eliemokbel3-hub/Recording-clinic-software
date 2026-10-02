"""The hardware check's prose-stage timing (installation plan Task 2.5, D11).

The Microphone tab's benchmark times the REAL prose stage —
``models.build_prose_stage`` for the Narrative style, in this process — over
fixed, non-clinical lines (sentences of the whisper benchmark's own script),
so the practitioner sees how long the two prose styles take on this machine
beside whisper's real-time factor. The note it renders is built here, held
in memory for the one call and dropped: nothing is saved, shown or logged,
and the result keeps numbers only (``benchmark.ProseBenchmark``).

The model comes from the process's one language-model cache, the Note
tab's, so the check never holds a second copy (round 13 MED-001): its load
is timed when this check is the one that loads it, and an already-resident
model is reported as such. With the language model absent the check is
skipped with the named line the prose styles already use. The model,
presence probe, cache and clocks are seams: tests never load a real model
and never touch the process's cache (C6).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final

from scribe_desktop.benchmark import ProseBenchmark
from scribe_desktop.language_model import LanguageModel, LanguageModelError, LocalLanguageModel
from scribe_desktop.note import (
    GeneratedNote,
    GeneratedSection,
    NoteAssertion,
    NoteSectionKey,
    NoteSpan,
    SourceCoords,
    text_digest,
)
from scribe_desktop.ui import models

# Fixed, deliberately non-clinical lines — each a phrase of
# ``benchmark.BENCHMARK_TEXT`` — three sections of two lines, the shape of a
# short note.
PROSE_BENCHMARK_LINES: Final[tuple[tuple[NoteSectionKey, tuple[str, ...]], ...]] = (
    (
        "presenting_complaint",
        (
            "a train left the station at nine forty five in the morning",
            "carrying two hundred and thirty passengers toward the coast",
        ),
    ),
    (
        "objective_examination",
        (
            "The lighthouse keeper recorded wind speeds of thirty two knots",
            "noted that the barometer had fallen sharply since noon",
        ),
    ),
    (
        "management_plan",
        (
            "William packed the instruments carefully into three wooden crates",
            "labelled each one with the date and destination",
        ),
    ),
)

_DIGEST: Final = text_digest("hardware-check")

# The advice the language-model cache adds to a load failure it remembers
# (``ui/models._LanguageModelCache``): the same words here, pinned by test.
RESTART_ADVICE: Final = "restart the app after fixing this"


def prose_benchmark_note() -> GeneratedNote:
    """The in-memory note the timing renders: ``PROSE_BENCHMARK_LINES`` as
    quoted lines (coordinates only satisfy the type; no transcript exists)."""
    sections: list[GeneratedSection] = []
    counter = 0
    for key, lines in PROSE_BENCHMARK_LINES:
        assertions = []
        for line in lines:
            assertions.append(
                NoteAssertion(
                    assertion_id=f"hw{counter}",
                    section_key=key,
                    note_span=NoteSpan(
                        span_text=line,
                        provenance="transcript",
                        source_coords=SourceCoords(counter, 0, len(line.split()) - 1),
                    ),
                )
            )
            counter += 1
        sections.append(GeneratedSection(section_key=key, note_assertions=tuple(assertions)))
    return GeneratedNote(
        session_id="0" * 32,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        template_profile_id="hardware-check",
        provider_name="hardware-check",
        transcript_digest=_DIGEST,
        config_digest=_DIGEST,
        note_sections=tuple(sections),
        style="narrative",
    )


def run_prose_benchmark(
    *,
    model_factory: Callable[[], LanguageModel] = LocalLanguageModel,
    available: Callable[[], bool] = models.language_model_available,
    cache: models._LanguageModelCache = models._LANGUAGE_MODEL_CACHE,
    wall_clock: Callable[[], float] = time.perf_counter,
    cpu_clock: Callable[[], float] = time.process_time,
) -> ProseBenchmark:
    """Time the Narrative prose stage once over ``prose_benchmark_note()``.
    Skipped — ``ProseBenchmark.skipped`` naming why — when the language
    model is absent or cannot be loaded, when any model call fails, or when
    no section could be given to the model. Never raises for those; anything
    else reaches the benchmark task's failure line like a whisper failure.

    The model comes from the process's ONE cache, the Note tab's (round 13
    MED-001: two resident copies must never exist), and is taken BEFORE the
    stage is clocked (round 14 LOW-002: a wait for another thread's load is
    never section time): a model already loaded is used as it is
    (``preloaded``, no load timed); otherwise it is loaded and timed here
    and stays resident, as the Note tab's first prose note would leave it. A
    failed load is remembered by that cache for the process — the Note tab's
    prose styles too — so its line always says to restart the app (round 14
    LOW-001), whichever of the two tried first."""
    if not available():
        return ProseBenchmark(skipped=models.language_model_absent_reason())
    load_wall: list[float] = []
    load_cpu: list[float] = []

    def timed_factory() -> LanguageModel:
        wall_started, cpu_started = wall_clock(), cpu_clock()
        try:
            return model_factory()
        finally:
            load_wall.append(wall_clock() - wall_started)
            load_cpu.append(cpu_clock() - cpu_started)

    try:
        cache.get(timed_factory)
    except LanguageModelError as exc:
        # The cache's remembered failure already carries the advice; a load
        # that failed just now (the factory ran) does not.
        reason = f"{exc}; {RESTART_ADVICE}" if load_wall else str(exc)
        return ProseBenchmark(skipped=f"the language model could not be loaded ({reason})")
    stage = models.build_prose_stage(
        "narrative", model_factory=timed_factory, cache=cache, available=lambda: True
    )
    assert stage is not None  # Narrative is a prose style
    note = prose_benchmark_note()
    wall_started, cpu_started = wall_clock(), cpu_clock()
    result = stage(note)
    wall, cpu = wall_clock() - wall_started, cpu_clock() - cpu_started
    if result.reason is not None:
        return ProseBenchmark(skipped=result.reason)
    sections = len(PROSE_BENCHMARK_LINES)
    # Round 13 MED-002: a failed call has no rendering and its time is only
    # the time to fail, so any model error is a named skip, never a verdict.
    model_errors = result.errored - result.too_long
    if model_errors:
        return ProseBenchmark(
            skipped=f"the language model failed on {model_errors} of {sections} sections"
        )
    # The sections the model rendered (a section refused before any call as
    # too long took no model time).
    rendered = result.passed + result.failed
    if not rendered:
        return ProseBenchmark(skipped="no section could be given to the language model")
    return ProseBenchmark(
        sections=sections,
        rendered=rendered,
        load_seconds=sum(load_wall),
        model_seconds=result.seconds,
        wall_seconds=wall,
        cpu_seconds=cpu,
        preloaded=not load_wall,
    )


__all__ = [
    "PROSE_BENCHMARK_LINES",
    "RESTART_ADVICE",
    "prose_benchmark_note",
    "run_prose_benchmark",
]
