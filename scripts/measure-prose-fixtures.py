"""Measure the REAL language model against the ten Phase 4 fixture notes.

Task 4.3 of the note-learning-and-styles plan records, per prose style, the
Check 5 pass rate over the ten fixture notes (acceptance >= 9/10) and the CPU
seconds per section on the practitioner's machine. The suite measures those
fixtures under ``MockLanguageModel`` (the parser + prompt contract); THIS
script is the real-model measurement — it loads the pinned GGUF exactly as
the app does (``apply_offline_env`` then ``LocalLanguageModel``), renders
every fixture in ``narrative`` and ``own_voice`` and prints one JSON report.
The per-section seconds are the provider's own per-SECTION measurements
(``SectionOutcome.seconds``: the mean and max are over sections, never over
per-note averages — codex round 23 PR-LOW-041) beside each note's wall time,
and the ``--verbose`` evidence is the MEASURED completion of each section
(recorded through a wrapper around the model — never a second generation,
PR-LOW-042).

    .venv\\Scripts\\python.exe scripts\\measure-prose-fixtures.py
        [--style narrative|own_voice] [--verbose]

Reads only. Writes nothing. Needs the ``[ml]`` stack, the pinned prose wheel
(``desktop/requirements-ml-prose.txt``) and the downloaded model (Task P.1);
it exits 2 with the reason when any of them is absent. The fixture notes are
the ones the suite pins (``desktop/tests/test_prose_style.py``); ``--verbose``
prints each section's inputs, the prose and the failing Check 5 rule, which is
the evidence prompt tuning works from.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "desktop" / "src"))
sys.path.insert(0, str(REPO / "desktop" / "tests"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--style", choices=["narrative", "own_voice"], help="one style only")
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="print every section's inputs, the measured prose and its verdict",
    )
    args = ap.parse_args(argv)

    try:
        import test_prose_style as fixtures  # the ten notes + the note/profile builders
        from scribe_desktop import note_check, prose_style
        from scribe_desktop.benchmark import apply_offline_env
        from scribe_desktop.language_model import LanguageModelError, LocalLanguageModel
    except ImportError as exc:
        print(f"cannot import the prose stack: {exc}", file=sys.stderr)
        return 2

    apply_offline_env()
    t0 = time.time()
    try:
        model = LocalLanguageModel()
    except LanguageModelError as exc:
        print(f"model not loadable: {exc}", file=sys.stderr)
        return 2
    report: dict = {"model_load_seconds": round(time.time() - t0, 1), "styles": {}}

    # Codex round 23 PR-LOW-042: the verbose evidence is the MEASURED call.
    # This wrapper stands between the provider and the loaded model, records
    # every completion of the one ``render`` (the provider's own prompt and
    # token budget), and hands the recording to the report; there is never a
    # second generation. It holds prompt and completion text in memory for
    # the run only — this is a read-only measurement tool, never the app.
    class RecordingModel:
        def __init__(self, inner):
            self._inner = inner
            self.calls: list[tuple[str, str, str]] = []

        @property
        def model_id(self):
            return self._inner.model_id

        def complete(self, *, system_text, user_text, max_tokens):
            completion = self._inner.complete(
                system_text=system_text, user_text=user_text, max_tokens=max_tokens
            )
            self.calls.append((system_text, user_text, completion))
            return completion

    recorder = RecordingModel(model)
    for style in ([args.style] if args.style else ["narrative", "own_voice"]):
        passed = 0
        section_seconds: list[float] = []  # PR-LOW-041: one entry per SECTION
        notes = []
        for index, sections in enumerate(fixtures.FIXTURE_NOTES):
            note = fixtures._note(sections, style=style)
            kwargs = {"profile": fixtures._style_profile()} if style == "own_voice" else {}
            provider = prose_style.ProseStyleProvider(recorder, style=style, **kwargs)
            prose_input = prose_style.ProseInput.from_note(note)
            recorder.calls.clear()
            started = time.time()
            result = provider.render(prose_input)
            wall = time.time() - started
            ok = fixtures._all_passed(result, note)
            passed += int(ok)
            section_seconds.extend(o.seconds for o in result.outcomes)
            entry: dict = {
                "note": index,
                "passed": ok,
                "wall_seconds": round(wall, 1),
                "section_seconds": [round(o.seconds, 1) for o in result.outcomes],
                "failed": [
                    f"{o.section_key}:{o.rule or o.failure}"
                    for o in result.outcomes
                    if not o.passed
                ],
            }
            if args.verbose:
                # One recorded call per section, in the provider's order (a
                # section whose call raised has no recording and is listed
                # from its outcome alone).
                detail = []
                completions = iter(recorder.calls)
                for outcome in result.outcomes:
                    lines = list(prose_input.texts(outcome.section_key) or ())
                    item = {"section": outcome.section_key, "inputs": lines,
                            "seconds": round(outcome.seconds, 1)}
                    if outcome.failure == "model_error":
                        item["error"] = outcome.detail
                    else:
                        _system, _user, completion = next(completions)
                        prose = prose_style.parse_section_prose(completion, outcome.section_key)
                        item["prose"] = prose
                        item["verdict"] = str(note_check.fidelity_verdict(lines, prose))
                    detail.append(item)
                entry["sections"] = detail
            notes.append(entry)
        note_walls = [n["wall_seconds"] for n in notes]
        report["styles"][style] = {
            "pass_rate": f"{passed}/10",
            "seconds_per_section_mean": round(sum(section_seconds) / len(section_seconds), 1),
            "seconds_per_section_max": round(max(section_seconds), 1),
            "seconds_per_note_min": min(note_walls),
            "seconds_per_note_max": max(note_walls),
            "notes": notes,
        }
        summary = report["styles"][style]
        print(
            f"{style}: {passed}/10 passed; {summary['seconds_per_section_mean']} s/section mean, "
            f"{summary['seconds_per_section_max']} max; "
            f"{summary['seconds_per_note_min']}-{summary['seconds_per_note_max']} s per note",
            flush=True,
        )
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
