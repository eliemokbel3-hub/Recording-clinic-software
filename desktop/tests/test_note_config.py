"""Tests for the note config engine (Phase 3A, Tasks 3.1-3.3).

Covers the Done-when clauses directly:
- 3.1: Template A's canonical->target mapping is expressed and pinned; a
  session cannot generate a note without a bound profile
  (``bind_template_profile`` refuses zero / unknown / ambiguous); a mapping
  that would drop a populated canonical section WARNS (``mapping_drop``)
  rather than silently discarding — and intentionally-unmapped stays silent.
- 3.2: malformed config fails loudly with a typed error and never partially
  applies; resolution precedence is per-file whole-file replacement;
  ``config_digest`` is well-defined over the resolved config.
- 3.3: shipped defaults resolve through ``importlib.resources`` — the
  mechanism a NON-EDITABLE install uses (recorded lesson: package mechanism,
  not LOCALAPPDATA) — and ``pyproject.toml`` pins the ``package-data``
  stanza that puts them in the wheel.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Any, Final

import pytest
from pydantic import ValidationError

import scribe_desktop.note_config as note_config_module
import scribe_desktop.note_fill as note_fill_module
from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    DEFAULT_SECTION_CUES,
    DIGEST_PATTERN,
    GeneratedSection,
    NoteAssertion,
    NoteSectionKey,
    NoteSpan,
    SourceCoords,
)
from scribe_desktop.note_config import (
    _ALLOWED_IN_CLAIM_PUNCT,
    AUTOFILL_RULES_FILENAME,
    CONFIG_FILENAMES,
    LEARNED_PHRASE_MAX_TOKENS,
    LEARNED_PHRASE_MIN_TOKENS,
    LEARNED_SIDECAR_FILENAME,
    LEARNING_CONTRACTED_STARTERS,
    LEARNING_OPENER_EXEMPTIONS,
    MAX_CONFIG_LABEL_CHARS,
    MAX_TRIGGER_CHARS,
    PREFILL_TEMPLATES_FILENAME,
    RECENTLY_LEARNED_LIMIT,
    SECTION_CUES_FILENAME,
    TEMPLATE_PROFILES_FILENAME,
    AutofillRule,
    AutofillRulesFile,
    BoundTemplateProfile,
    LearnedPhrase,
    LearnedPhrases,
    NoteConfig,
    NoteConfigError,
    NoteConfigInvalidError,
    NoteConfigUnreadableError,
    NoteConfigWriteError,
    PrefillTemplate,
    PrefillTemplatesFile,
    SectionCuesFile,
    TemplateProfile,
    TemplateProfilesFile,
    TemplateProfileUnboundError,
    _canonical_config,
    append_user_cues,
    bind_template_profile,
    build_note_request,
    default_config_root,
    delete_user_cue,
    load_learned_phrases,
    load_note_config,
    mapping_drop_warnings,
    propose_learning_phrase,
    refuse_learning_candidate,
)
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import (
    _COMMON_SEGMENT_STARTERS,
    SPEAKER_1,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
    is_name_like_token,
    is_number_token,
)

# ---------------------------------------------------------------------------
# Builders.
# ---------------------------------------------------------------------------


def _target(
    target_id: str = "field-1",
    target_type: str = "plain_text",
    group: str = "Group",
    field_label: str = "Field",
) -> dict[str, Any]:
    return {
        "target_id": target_id,
        "group": group,
        "field_label": field_label,
        "target_type": target_type,
    }


def _profile_data(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "template_profile_id": "p1",
        "display_name": "Profile one",
        "template_targets": [_target()],
        "section_mappings": [{"section_key": "assessment", "target_id": "field-1"}],
        "intentionally_unmapped": [],
    }
    base.update(overrides)
    return base


def _profile(**overrides: Any) -> TemplateProfile:
    return TemplateProfile.model_validate(_profile_data(**overrides))


def _rule_data(rule_id: str, trigger: str, *expansion: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "section_key": "advice_home_exercise",
        "trigger_phrase": trigger,
        "expansion": list(expansion) or ["Advice recorded"],
    }


def _populated_section(section_key: NoteSectionKey) -> GeneratedSection:
    assertion = NoteAssertion(
        assertion_id=f"a-{section_key}",
        section_key=section_key,
        note_span=NoteSpan(
            span_text="verbatim transcript span",
            provenance="transcript",
            source_coords=SourceCoords(0, 0, 2),
        ),
    )
    return GeneratedSection(section_key=section_key, note_assertions=(assertion,))


def _write_user_file(root: Path, filename: str, data: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / filename).write_text(json.dumps(data), encoding="utf-8")


def _tiny_document() -> TranscriptDocument:
    word = TranscriptWord(
        word_text="hello",
        start_seconds=0.0,
        end_seconds=0.3,
        probability=0.9,
        uncertain=False,
    )
    segment = TranscriptSegment(
        start_seconds=0.0,
        end_seconds=1.0,
        speaker=SPEAKER_1,
        transcript_words=(word,),
    )
    return TranscriptDocument(
        session_id="c" * 32,
        created_at=datetime(2026, 8, 10, 11, 0, tzinfo=UTC),
        model_name="mock",
        sample_rate=SAMPLE_RATE,
        transcript_segments=(segment,),
    )


# ---------------------------------------------------------------------------
# Task 3.1 — the shipped Template A profile.
# ---------------------------------------------------------------------------

# The plan's Schema / Data Changes table, pinned row by row (16 mapped rows;
# `consent` is intentionally unmapped — Template A's only consent target is
# the attestation checkbox, never written by this app).
EXPECTED_TEMPLATE_A: dict[str, tuple[str, str, str]] = {
    "presenting_complaint": ("History", "Presenting complaint/patient progress", "rich_text"),
    "history_presenting_complaint": (
        "History",
        "Presenting complaint/patient progress",
        "rich_text",
    ),
    "progress_since_last_visit": (
        "History",
        "Presenting complaint/patient progress",
        "rich_text",
    ),
    "past_medical_history": ("History", "Presenting complaint/patient progress", "rich_text"),
    "red_flags_screening": ("Examination", "Assessment", "plain_text"),
    "objective_examination": ("Examination", "Assessment", "plain_text"),
    "outcome_measures": ("Examination", "Assessment", "plain_text"),
    "assessment": ("Examination", "Assessment", "plain_text"),
    "diagnosis": ("Examination", "Diagnosis", "plain_text"),
    "treatment_performed": ("Treatment/Management", "Treatment", "plain_text"),
    "response_to_treatment": ("Treatment/Management", "Response to treatment", "plain_text"),
    "advice_home_exercise": ("Treatment/Management", "Management/Advice", "plain_text"),
    "management_plan": ("Treatment/Management", "Management/Advice", "plain_text"),
    "referrals_investigations": ("Treatment/Management", "Management/Advice", "plain_text"),
    "precautions_contraindications": ("Examination", "Assessment", "plain_text"),
    "follow_up_review": ("Treatment/Management", "Management/Advice", "plain_text"),
}


class TestTemplateAShippedDefaults:
    def test_first_run_loads_the_sole_shipped_profile(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        assert len(config.template_profiles) == 1
        assert config.template_profiles[0].template_profile_id == "template-a"

    def test_every_canonical_section_is_mapped_or_intentionally_unmapped(
        self, tmp_path: Path
    ) -> None:
        profile = load_note_config(tmp_path / "config").template_profiles[0]
        assert profile.unmapped_section_keys() == ()
        assert profile.intentionally_unmapped == ("consent",)

    def test_mapping_matches_the_captured_template_row_by_row(self, tmp_path: Path) -> None:
        profile = load_note_config(tmp_path / "config").template_profiles[0]
        for key in CANONICAL_SECTION_KEYS:
            target = profile.target_for(key)
            if key == "consent":
                assert target is None
                continue
            assert target is not None, key
            assert (target.group, target.field_label, target.target_type) == (
                EXPECTED_TEMPLATE_A[key]
            ), key

    def test_template_a_shape_three_groups_six_text_fields_one_checkbox(
        self, tmp_path: Path
    ) -> None:
        profile = load_note_config(tmp_path / "config").template_profiles[0]
        assert len(profile.template_targets) == 7
        assert {t.group for t in profile.template_targets} == {
            "History",
            "Examination",
            "Treatment/Management",
        }
        checkboxes = [
            t for t in profile.template_targets if t.target_type == "attestation_checkbox"
        ]
        assert [t.field_label for t in checkboxes] == ["Informed Consent"]
        text_fields = [t for t in profile.template_targets if t is not checkboxes[0]]
        assert len(text_fields) == 6
        rich = [t for t in text_fields if t.target_type == "rich_text"]
        assert [t.field_label for t in rich] == ["Presenting complaint/patient progress"]

    def test_nothing_maps_to_the_attestation_checkbox(self, tmp_path: Path) -> None:
        profile = load_note_config(tmp_path / "config").template_profiles[0]
        mapped_ids = {m.target_id for m in profile.section_mappings}
        assert "informed-consent" not in mapped_ids

    def test_shipped_autofill_and_prefill_defaults_are_empty(self, tmp_path: Path) -> None:
        # Deliberate: boilerplate is clinician-authored config; the app ships
        # none (Documentation-only Critical Constraint applies to defaults too).
        config = load_note_config(tmp_path / "config")
        assert config.autofill_rules == ()
        assert config.prefill_templates == ()


class TestProfileValidation:
    def test_mapping_to_attestation_target_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="attestation-typed target"):
            _profile(
                template_targets=[_target(target_type="attestation_checkbox")],
            )

    def test_attestation_rule_keys_on_target_type_not_on_consent(self) -> None:
        # `consent` maps fine to a free-text target in someone else's template.
        profile = _profile(
            section_mappings=[{"section_key": "consent", "target_id": "field-1"}],
        )
        target = profile.target_for("consent")
        assert target is not None and target.target_type == "plain_text"

    def test_mapping_to_unknown_target_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="unknown target"):
            _profile(section_mappings=[{"section_key": "assessment", "target_id": "ghost"}])

    def test_duplicate_target_ids_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="duplicate target_id"):
            _profile(template_targets=[_target(), _target()])

    def test_mapping_a_section_twice_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="mapped more than once"):
            _profile(
                section_mappings=[
                    {"section_key": "assessment", "target_id": "field-1"},
                    {"section_key": "assessment", "target_id": "field-1"},
                ]
            )

    def test_mapped_and_intentionally_unmapped_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="both mapped and intentionally unmapped"):
            _profile(intentionally_unmapped=["assessment"])

    def test_unmapped_section_keys_in_canonical_order(self) -> None:
        profile = _profile(intentionally_unmapped=["consent"])
        unmapped = profile.unmapped_section_keys()
        assert "assessment" not in unmapped
        assert "consent" not in unmapped
        assert unmapped == tuple(
            key for key in CANONICAL_SECTION_KEYS if key not in {"assessment", "consent"}
        )

    def test_profiles_are_frozen(self) -> None:
        profile = _profile()
        with pytest.raises(ValidationError):
            profile.display_name = "changed"  # type: ignore[misc]

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden|Extra inputs"):
            TemplateProfile.model_validate(_profile_data(surprise="field"))


# ---------------------------------------------------------------------------
# Task 3.1 — profile binding: no note generation without a bound profile.
# ---------------------------------------------------------------------------


class TestBindTemplateProfile:
    def test_the_sole_profile_binds_automatically_no_chooser(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        binding = bind_template_profile(config)
        assert binding.template_profile.template_profile_id == "template-a"
        assert binding.config_digest == config.config_digest()

    def test_explicit_id_binds(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        binding = bind_template_profile(config, "template-a")
        assert binding.template_profile.template_profile_id == "template-a"

    def test_unknown_id_raises(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        with pytest.raises(TemplateProfileUnboundError, match="unknown template_profile_id"):
            bind_template_profile(config, "template-z")

    def test_zero_profiles_cannot_generate(self) -> None:
        config = NoteConfig()
        with pytest.raises(TemplateProfileUnboundError, match="cannot generate a note"):
            bind_template_profile(config)

    def test_two_profiles_require_an_explicit_choice(self) -> None:
        config = NoteConfig(
            template_profiles=(
                _profile(),
                _profile(template_profile_id="p2", display_name="Profile two"),
            )
        )
        with pytest.raises(TemplateProfileUnboundError, match="explicit"):
            bind_template_profile(config)
        chosen = bind_template_profile(config, "p2")
        assert chosen.template_profile.template_profile_id == "p2"

    def test_binding_carries_its_own_configs_digest(self, tmp_path: Path) -> None:
        # Round 10 PR-MED-001: a profile resolved from one config cannot end
        # up paired with another config's digest — the binding is one value
        # produced by one resolution.
        shipped = load_note_config(tmp_path / "config")
        custom = NoteConfig(template_profiles=(_profile(),))
        binding = bind_template_profile(custom)
        assert binding.config_digest == custom.config_digest()
        assert binding.config_digest != shipped.config_digest()


class TestGenerationBoundary:
    """Round 10 PR-MED-001: generation-facing requests require binding
    EVIDENCE — a freely typed profile id is not enough."""

    def test_a_fabricated_profile_id_cannot_reach_a_request(self) -> None:
        # With zero profiles configured there is no binding and no request,
        # however regex-valid the invented id — both the resolver and the
        # generation boundary fail first.
        with pytest.raises(TemplateProfileUnboundError):
            bind_template_profile(NoteConfig(), "never-configured")
        with pytest.raises(TemplateProfileUnboundError):
            bind_template_profile(NoteConfig())
        with pytest.raises(TemplateProfileUnboundError):
            build_note_request(_tiny_document(), NoteConfig(), "never-configured")

    def test_sole_profile_binding_builds_a_request_without_a_chooser(
        self, tmp_path: Path
    ) -> None:
        config = load_note_config(tmp_path / "config")
        request = build_note_request(_tiny_document(), config)
        assert request.template_profile_id == "template-a"
        assert request.config_digest == config.config_digest()
        assert len(request.transcript_utterances) == 1

    def test_unknown_id_fails_before_provider_invocation(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        with pytest.raises(TemplateProfileUnboundError):
            build_note_request(_tiny_document(), config, "template-z")

    # Round 12 PR-MED-001: pydantic's validator-skipping escape hatches and
    # method-overriding subclasses must die at the generation boundary,
    # which canonicalises the config from field data before deriving.
    def test_a_lying_config_subclass_cannot_skew_the_digest(self) -> None:
        honest = NoteConfig(template_profiles=(_profile(),))

        class LyingConfig(NoteConfig):
            def config_digest(self) -> str:
                return "sha256-v1:" + "0" * 64

        request = build_note_request(
            _tiny_document(), LyingConfig(template_profiles=(_profile(),))
        )
        assert request.config_digest == honest.config_digest()

    def test_model_construct_forgery_fails_closed(self) -> None:
        # Duplicate profile ids can only coexist because validation was
        # skipped; the boundary re-validates and refuses, typed.
        duplicate = _profile()
        forged = NoteConfig.model_construct(
            template_profiles=(duplicate, duplicate),
            autofill_rules=(),
            prefill_templates=(),
        )
        with pytest.raises(NoteConfigInvalidError, match="generation boundary"):
            build_note_request(_tiny_document(), forged)

    def test_unchecked_model_copy_fails_closed(self) -> None:
        config = NoteConfig(template_profiles=(_profile(),))
        forged = config.model_copy(
            update={"template_profiles": (_profile(), _profile())}
        )
        with pytest.raises(NoteConfigInvalidError, match="generation boundary"):
            build_note_request(_tiny_document(), forged)

    def test_a_duck_typed_config_cannot_reach_a_provider(self) -> None:
        class FakeConfig:
            template_profiles = (
                NoteConfig(template_profiles=(_profile(),)).template_profiles
            )

        # Fails closed either at canonicalisation (unserialisable duck) or,
        # if the duck happens to serialise, at binding — never at a provider.
        with pytest.raises(NoteConfigError):
            build_note_request(_tiny_document(), FakeConfig())  # type: ignore[arg-type]

    def test_cross_config_pairing_is_unrepresentable(self) -> None:
        # Round 11 PR-MED-001's attack: configs A and B share the profile id
        # "p1" but map different sections. Pairing A's profile with B's
        # digest must fail through EVERY public construction surface.
        config_a = NoteConfig(template_profiles=(_profile(),))
        config_b = NoteConfig(
            template_profiles=(
                _profile(
                    section_mappings=[
                        {"section_key": "objective_examination", "target_id": "field-1"}
                    ]
                ),
            )
        )
        # Surface 1 — the round-10 shape (a supplied profile/digest pair) no
        # longer exists on the type at all:
        with pytest.raises(ValidationError):
            BoundTemplateProfile.model_validate(
                {
                    "template_profile": config_a.template_profiles[0].model_dump(),
                    "config_digest": config_b.config_digest(),
                }
            )
        # Surface 2 — VALIDATING construction derives BOTH values from the
        # one stored config (validator-skipping constructions are the
        # boundary's job — see the escape-hatch tests above):
        forged = BoundTemplateProfile(source_config=config_b, template_profile_id="p1")
        assert forged.config_digest == config_b.config_digest()
        assert forged.template_profile.target_for("objective_examination") is not None
        assert forged.template_profile.target_for("assessment") is None
        # Surface 3 — membership is validated at construction:
        with pytest.raises(ValidationError, match="not a member"):
            BoundTemplateProfile(source_config=config_a, template_profile_id="p2")
        # Surface 4 — the builder re-binds from the config it is handed, so
        # each request records the digest of the exact config its profile
        # came from:
        request_a = build_note_request(_tiny_document(), config_a)
        request_b = build_note_request(_tiny_document(), config_b)
        assert request_a.config_digest == config_a.config_digest()
        assert request_b.config_digest == config_b.config_digest()
        assert request_a.config_digest != request_b.config_digest

    def test_note_request_is_not_exported_public_api(self) -> None:
        from scribe_desktop import note

        assert "NoteRequest" not in note.__all__

    def test_phase_six_shaped_flow_through_the_one_public_path(
        self, tmp_path: Path
    ) -> None:
        # Loads config, binds for the UI, builds via the boundary — and
        # obtains everything mapping and persistence need (profile, id,
        # digest) from the supported path, all agreeing with each other.
        config = load_note_config(tmp_path / "config")
        binding = bind_template_profile(config)
        request = build_note_request(_tiny_document(), config)
        profile = binding.template_profile
        assert request.template_profile_id == profile.template_profile_id == "template-a"
        assert request.config_digest == binding.config_digest == config.config_digest()
        assert profile.target_for("assessment") is not None
        assert mapping_drop_warnings(profile, []) == ()


# ---------------------------------------------------------------------------
# Rounds 12-13 PR-MED-001 — the AST reference-confinement guard. A pydantic
# model cannot refuse its own constructor or classmethods, and round 13
# proved that ENUMERATING constructor spellings loses by default (the
# tripwire lesson of rounds 3-6, again). So the guard confines the SEMANTIC
# SURFACE instead: any runtime reference to a guarded symbol in shipping
# source is a violation unless it is an annotation, an un-renamed import, or
# the exact allow-listed direct call — whose package-wide node COUNT is
# pinned, so even a second call inside an allowed function fails by default.
# ---------------------------------------------------------------------------

_GUARDED_SYMBOLS: Final = ("NoteRequest", "BoundTemplateProfile", "_assemble_note_request")
# symbol -> (module rel-path, enclosing function, exact package-wide count of
# permitted direct-call nodes).
_ALLOWED_CALL_SITES: Final[dict[str, tuple[str, str, int]]] = {
    "NoteRequest": ("note.py", "_assemble_note_request", 1),
    "BoundTemplateProfile": ("note_config.py", "bind_template_profile", 2),
    "_assemble_note_request": ("note_config.py", "build_note_request", 1),
}


def _annotation_node_ids(tree: ast.AST) -> set[int]:
    """ids of every node inside an annotation expression — the one context
    where a guarded symbol may be referenced freely (importability for
    annotations is preserved by design)."""
    ids: set[int] = set()

    def add(subtree: ast.expr | None) -> None:
        if subtree is not None:
            for inner in ast.walk(subtree):
                ids.add(id(inner))

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            add(node.returns)
            arguments = node.args
            for arg in (
                *arguments.posonlyargs,
                *arguments.args,
                *arguments.kwonlyargs,
                arguments.vararg,
                arguments.kwarg,
            ):
                if arg is not None:
                    add(arg.annotation)
        elif isinstance(node, ast.AnnAssign):
            add(node.annotation)
    return ids


class _ConstructionGuard(ast.NodeVisitor):
    """Reference-confinement guard (rounds 12-13 PR-MED-001).

    THE RULE — semantic, not a spelling list: a guarded symbol may appear
    in shipping source ONLY as (1) an annotation, (2) an un-renamed import
    (the raw assembler importable only by note_config.py), or (3) the
    callee of its exact allow-listed direct call. EVERY other runtime
    reference — any pydantic classmethod present or future,
    ``TypeAdapter(...)``, ``__pydantic_validator__``, aliasing, walrus,
    containers, default arguments, subclass bases — is a violation BY
    DEFAULT, so a new construction spelling fails without being enumerated.
    Stated out of scope, here and at ``build_note_request``: references
    reached through a VALUE variable, ``getattr``-by-string, and runtime
    monkey-patching are statically invisible and outside the same-user
    threat model.
    """

    def __init__(self, rel_path: str, annotation_ids: set[int]) -> None:
        self.rel_path = rel_path
        self.annotation_ids = annotation_ids
        self.scope: list[str] = []
        self.violations: list[str] = []
        self.allowed_call_counts: dict[str, int] = dict.fromkeys(_ALLOWED_CALL_SITES, 0)
        self._allowed_nodes: set[int] = set()

    def _flag(self, node: ast.AST, message: str) -> None:
        lineno = getattr(node, "lineno", 0)
        self.violations.append(f"{self.rel_path}:{lineno}: {message}")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in _ALLOWED_CALL_SITES:
            module, function, _expected = _ALLOWED_CALL_SITES[func.id]
            enclosing = self.scope[-1] if self.scope else ""
            if self.rel_path == module and enclosing == function:
                self._allowed_nodes.add(id(func))
                self.allowed_call_counts[func.id] += 1
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if (
            node.id in _GUARDED_SYMBOLS
            and id(node) not in self.annotation_ids
            and id(node) not in self._allowed_nodes
        ):
            self._flag(node, f"runtime reference to guarded symbol {node.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _GUARDED_SYMBOLS and id(node) not in self.annotation_ids:
            self._flag(node, f"qualified runtime reference to guarded symbol {node.attr}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name in _GUARDED_SYMBOLS:
                if alias.asname is not None:
                    self._flag(node, f"import-renaming guarded symbol {alias.name}")
                elif (
                    alias.name == "_assemble_note_request"
                    and self.rel_path != "note_config.py"
                ):
                    self._flag(node, "importing the raw assembler outside note_config.py")
        self.generic_visit(node)


def _run_guard(source: str, rel_path: str) -> _ConstructionGuard:
    tree = ast.parse(source)
    guard = _ConstructionGuard(rel_path, _annotation_node_ids(tree))
    guard.visit(tree)
    return guard


def _guard_violations(source: str, rel_path: str) -> list[str]:
    return _run_guard(source, rel_path).violations


class TestConstructionGuard:
    def test_every_shipping_module_is_clean_including_note_py(self) -> None:
        import scribe_desktop

        package_dir = Path(scribe_desktop.__file__).parent
        violations: list[str] = []
        totals: dict[str, int] = dict.fromkeys(_ALLOWED_CALL_SITES, 0)
        for path in sorted(package_dir.rglob("*.py")):
            rel = path.relative_to(package_dir).as_posix()
            guard = _run_guard(path.read_text(encoding="utf-8"), rel)
            violations += guard.violations
            for symbol, count in guard.allowed_call_counts.items():
                totals[symbol] += count
        assert violations == []
        # The EXACT permitted construction surface, pinned by node count: a
        # new call — even inside an allow-listed function — changes a total
        # and fails here by default rather than extending the surface
        # invisibly (round 13's "assert the permitted nodes/counts").
        assert totals == {
            symbol: expected
            for symbol, (_module, _function, expected) in _ALLOWED_CALL_SITES.items()
        }

    def test_a_second_call_inside_the_allowed_site_is_counted_not_hidden(self) -> None:
        snippet = (
            "def _assemble_note_request():\n"
            "    NoteRequest(session_id='a')\n"
            "    NoteRequest(session_id='b')\n"
        )
        guard = _run_guard(snippet, "note.py")
        # Per-node the site is legal, so no violation line — but the count
        # is 2, and the package-wide exact-count assertion pins it to 1.
        assert guard.violations == []
        assert guard.allowed_call_counts["NoteRequest"] == 2

    @pytest.mark.parametrize(
        ("label", "snippet"),
        [
            ("bare call", "NoteRequest(session_id='x')"),
            ("qualified call", "import scribe_desktop.note as n\nn.NoteRequest(session_id='x')"),
            ("multiline call", "NoteRequest(\n    session_id='x',\n)"),
            ("aliased class", "NR = NoteRequest"),
            (
                "import-rename",
                "from scribe_desktop.note import NoteRequest as NR",
            ),
            ("model_validate", "NoteRequest.model_validate({})"),
            ("model_validate_json", "NoteRequest.model_validate_json('{}')"),
            ("model_construct", "NoteRequest.model_construct()"),
            ("model_copy", "NoteRequest.model_copy(x)"),
            (
                "qualified classmethod",
                "import scribe_desktop.note as n\nn.NoteRequest.model_construct()",
            ),
            ("request subclass", "class Sneaky(NoteRequest):\n    pass"),
            (
                "binding subclass",
                "class Lying(BoundTemplateProfile):\n    pass",
            ),
            (
                "binding model_construct",
                "BoundTemplateProfile.model_construct(source_config=1)",
            ),
            ("assembler call", "_assemble_note_request(doc)"),
            (
                "assembler import",
                "from scribe_desktop.note import _assemble_note_request",
            ),
            # Round 13 PR-MED-001 — the peer's bypass shapes: constructor
            # SPELLINGS the enumerating guard missed. The semantic rule
            # (any runtime reference outside annotations/allowed nodes)
            # rejects them without naming any pydantic API.
            ("model_validate_strings", "NoteRequest.model_validate_strings({})"),
            (
                "type adapter",
                "from pydantic import TypeAdapter\nTypeAdapter(NoteRequest).validate_python({})",
            ),
            ("legacy parse_obj", "NoteRequest.parse_obj({})"),
            ("legacy validate", "NoteRequest.validate({})"),
            (
                "pydantic validator",
                "NoteRequest.__pydantic_validator__.validate_python({})",
            ),
            ("walrus alias", "(NR := NoteRequest)"),
            ("container alias", "handlers = [NoteRequest]"),
            (
                "default-argument alias",
                "def make(cls=NoteRequest):\n    return cls()",
            ),
        ],
    )
    def test_guard_flags_the_bypass_routes(self, label: str, snippet: str) -> None:
        assert _guard_violations(snippet, "phase6.py"), label

    def test_guard_permits_annotation_use(self) -> None:
        snippet = (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from scribe_desktop.note import NoteRequest\n"
            "from scribe_desktop.note_config import BoundTemplateProfile\n"
            "def handle(request: NoteRequest) -> NoteRequest:\n"
            "    return request\n"
            "binding: BoundTemplateProfile | None = None\n"
        )
        assert _guard_violations(snippet, "phase6.py") == []

    def test_guard_would_not_exempt_a_future_ui_note_module(self) -> None:
        # The round-11 regex excluded every file NAMED note.py — which would
        # silently exempt Phase 7's planned ui/note.py. The allow-list keys
        # on the package-relative path, so only the root note.py assembler
        # site is legal.
        snippet = "def _assemble_note_request():\n    NoteRequest(session_id='x')\n"
        assert _guard_violations(snippet, "ui/note.py")


# ---------------------------------------------------------------------------
# Task 3.1 — mapping_drop: warn, never silently discard.
# ---------------------------------------------------------------------------


class TestMappingDropWarnings:
    def test_populated_unmapped_section_warns(self) -> None:
        profile = _profile()  # only `assessment` is mapped
        warnings = mapping_drop_warnings(profile, [_populated_section("objective_examination")])
        assert len(warnings) == 1
        assert warnings[0].note_warning_code == "mapping_drop"
        assert warnings[0].severity == "review"
        assert warnings[0].section_key == "objective_examination"

    def test_intentionally_unmapped_populated_section_is_silent(self) -> None:
        profile = _profile(intentionally_unmapped=["consent"])
        assert mapping_drop_warnings(profile, [_populated_section("consent")]) == ()

    def test_mapped_populated_section_is_silent(self) -> None:
        profile = _profile()
        assert mapping_drop_warnings(profile, [_populated_section("assessment")]) == ()

    def test_empty_unmapped_section_is_silent(self) -> None:
        profile = _profile()
        empty = GeneratedSection(section_key="objective_examination")
        assert mapping_drop_warnings(profile, [empty]) == ()

    def test_shipped_profile_drops_nothing(self, tmp_path: Path) -> None:
        profile = load_note_config(tmp_path / "config").template_profiles[0]
        populated = [_populated_section(key) for key in CANONICAL_SECTION_KEYS]
        assert mapping_drop_warnings(profile, populated) == ()


# ---------------------------------------------------------------------------
# Task 3.2 — schema validation: declarative, loud, typed.
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_control_characters_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="control character"):
            _profile(display_name="bad\x00name")

    def test_blank_text_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be blank"):
            _profile(display_name="   ")

    def test_field_length_limits_apply(self) -> None:
        with pytest.raises(ValidationError):
            _profile(display_name="x" * (MAX_CONFIG_LABEL_CHARS + 1))

    # Round 10 PR-MED-002: Zl/Zp separators and Cf format controls pass a
    # C0/DEL/C1-only range check, so pasted config could render differently
    # from the exact digested wording shown for confirmation.
    @pytest.mark.parametrize(
        "hidden",
        [
            chr(0x2028),  # LINE SEPARATOR (Zl)
            chr(0x2029),  # PARAGRAPH SEPARATOR (Zp)
            chr(0x202E),  # RIGHT-TO-LEFT OVERRIDE (Cf)
            chr(0x2066),  # LEFT-TO-RIGHT ISOLATE (Cf)
            chr(0x200B),  # ZERO WIDTH SPACE (Cf)
        ],
    )
    def test_unicode_layout_and_bidi_controls_are_rejected(self, hidden: str) -> None:
        with pytest.raises(ValidationError, match="not allowed in config text"):
            _profile(display_name=f"Clinic{hidden}name")
        with pytest.raises(ValidationError, match="not allowed in config text"):
            AutofillRule.model_validate(
                _rule_data("r1", "home exercise", f"Advice{hidden}given")
            )
        with pytest.raises(ValidationError, match="not allowed in config text"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": [
                        {
                            "section_key": "objective_examination",
                            "seed_text": f"ROM{hidden}full",
                        }
                    ],
                }
            )

    def test_ordinary_non_ascii_clinical_text_is_accepted(self) -> None:
        profile = _profile(display_name="Clinique française — naïve œdème 頸椎 evaluación")
        assert "œdème" in profile.display_name

    def test_loader_wraps_hidden_format_control_failure_typed(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            AUTOFILL_RULES_FILENAME,
            {
                "schema_version": 1,
                "autofill_rules": [
                    _rule_data("r1", "home exercise", "Advice" + chr(0x202E) + "given")
                ],
            },
        )
        with pytest.raises(NoteConfigInvalidError, match=AUTOFILL_RULES_FILENAME):
            load_note_config(root)

    def test_duplicate_normalised_triggers_are_rejected(self) -> None:
        # "Home Exercise!" and "home  exercise" are one trigger after the
        # module's single shared normalisation.
        with pytest.raises(ValidationError, match="share the same normalised trigger"):
            NoteConfig(
                autofill_rules=(
                    AutofillRule.model_validate(_rule_data("r1", "Home Exercise!")),
                    AutofillRule.model_validate(_rule_data("r2", "home  exercise")),
                )
            )

    def test_trigger_with_no_content_tokens_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="could never fire"):
            AutofillRule.model_validate(_rule_data("r1", "?!"))

    # Task 4.0 Done-when: a multi-claim expansion declared as a SINGLE STRING
    # fails validation with a message NAMING THE FIX. The reader is a
    # clinician editing JSON, so the message must say "one entry per claim"
    # and show the list shape — not just refuse the type.
    def test_expansion_as_a_single_string_fails_naming_the_fix(self) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = "Advice given to rest. Ice pack use explained."
        with pytest.raises(ValidationError, match="one entry per claim") as excinfo:
            AutofillRule.model_validate(data)
        message = str(excinfo.value)
        assert "single string" in message
        assert "JSON list" in message
        # The forbidden alternative is named: the app never splits prose.
        assert "never splits prose" in message

    def test_seed_assertions_as_a_single_string_fails_naming_the_fix(self) -> None:
        with pytest.raises(ValidationError, match="one entry per claim"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": "Knee inspected. ROM assessed.",
                }
            )

    def test_string_expansion_reaches_the_clinician_through_the_loader(
        self, tmp_path: Path
    ) -> None:
        # End-to-end: the fix-naming message survives into the typed loader
        # error the app surfaces, tagged with the file that needs editing.
        root = tmp_path / "config"
        data = _rule_data("r1", "home exercise")
        data["expansion"] = "One claim. Another claim."
        _write_user_file(
            root, AUTOFILL_RULES_FILENAME, {"schema_version": 1, "autofill_rules": [data]}
        )
        with pytest.raises(NoteConfigInvalidError, match="one entry per claim") as excinfo:
            load_note_config(root)
        assert AUTOFILL_RULES_FILENAME in str(excinfo.value)

    def test_region_keyword_with_no_content_tokens_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="could never fire"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["?!"],
                    "seed_assertions": [
                        {"section_key": "objective_examination", "seed_text": "ROM"}
                    ],
                }
            )

    def test_empty_expansion_is_rejected(self) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = []
        with pytest.raises(ValidationError):
            AutofillRule.model_validate(data)

    def test_duplicate_rule_ids_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate rule_id"):
            NoteConfig(
                autofill_rules=(
                    AutofillRule.model_validate(_rule_data("r1", "home exercise")),
                    AutofillRule.model_validate(_rule_data("r1", "ice the knee")),
                )
            )

    def test_duplicate_profile_ids_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate template_profile_id"):
            NoteConfig(template_profiles=(_profile(), _profile()))

    def test_duplicate_prefill_ids_are_rejected(self) -> None:
        prefill = {
            "prefill_id": "pf1",
            "display_name": "Knee",
            "region_keywords": ["knee"],
            "seed_assertions": [{"section_key": "objective_examination", "seed_text": "ROM"}],
        }
        with pytest.raises(ValidationError, match="duplicate prefill_id"):
            NoteConfig(
                prefill_templates=(
                    PrefillTemplate.model_validate(prefill),
                    PrefillTemplate.model_validate(prefill),
                )
            )

    def test_unknown_schema_version_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AutofillRulesFile.model_validate({"schema_version": 2, "autofill_rules": []})


# ---------------------------------------------------------------------------
# Practitioner-profile plan Task 4.2 — the fourth config file's own model.
# ---------------------------------------------------------------------------


class TestSectionCuesFile:
    def test_unknown_section_key_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SectionCuesFile.model_validate(
                {"schema_version": 1, "section_cues": {"not_a_section": ["pain in"]}}
            )

    def test_blank_phrase_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            SectionCuesFile.model_validate(
                {"schema_version": 1, "section_cues": {"assessment": [" "]}}
            )

    def test_control_character_in_a_phrase_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="control character"):
            SectionCuesFile.model_validate(
                {"schema_version": 1, "section_cues": {"assessment": ["my\tassessment"]}}
            )

    def test_phrase_with_no_content_tokens_is_refused(self) -> None:
        """A pure-disfluency phrase could never route an utterance, so it is
        refused at authoring time rather than silently ignored."""
        with pytest.raises(ValidationError, match="no content tokens"):
            SectionCuesFile.model_validate(
                {"schema_version": 1, "section_cues": {"assessment": ["um ..."]}}
            )

    def test_phrase_length_limit_applies(self) -> None:
        with pytest.raises(ValidationError):
            SectionCuesFile.model_validate(
                {
                    "schema_version": 1,
                    "section_cues": {"assessment": ["a" * (MAX_TRIGGER_CHARS + 1)]},
                }
            )
        parsed = SectionCuesFile.model_validate(
            {"schema_version": 1, "section_cues": {"assessment": ["a" * MAX_TRIGGER_CHARS]}}
        )
        assert parsed.section_cues["assessment"] == ("a" * MAX_TRIGGER_CHARS,)

    def test_duplicate_within_a_section_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="same phrase"):
            SectionCuesFile.model_validate(
                {
                    "schema_version": 1,
                    "section_cues": {"assessment": ["Consistent with!", "consistent  with"]},
                }
            )

    def test_duplicate_across_sections_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="same phrase"):
            SectionCuesFile.model_validate(
                {
                    "schema_version": 1,
                    "section_cues": {
                        "assessment": ["consistent with"],
                        "diagnosis": ["Consistent With"],
                    },
                }
            )

    def test_unknown_schema_version_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SectionCuesFile.model_validate({"schema_version": 2, "section_cues": {}})

    def test_extra_field_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SectionCuesFile.model_validate(
                {"schema_version": 1, "section_cues": {}, "surprise": True}
            )

    def test_a_missing_key_has_no_cues(self) -> None:
        parsed = SectionCuesFile.model_validate(
            {"section_cues": {"assessment": ["consistent with"]}}
        )
        config = NoteConfig(section_cues=parsed.section_cues)
        assert config.normalised_cues() == {"assessment": (("consistent", "with"),)}

    def test_note_config_holds_the_same_rule_without_the_file_model(self) -> None:
        """`_check_section_cues` is `NoteConfig`'s validator too, so a config
        assembled without the file model is held to the same rule."""
        with pytest.raises(ValidationError, match="no content tokens"):
            NoteConfig(section_cues={"assessment": ("um",)})
        with pytest.raises(ValidationError, match="same phrase"):
            NoteConfig(section_cues={"assessment": ("pain in",), "diagnosis": ("Pain in!",)})

    def test_file_is_frozen(self) -> None:
        parsed = SectionCuesFile.model_validate({"schema_version": 1, "section_cues": {}})
        with pytest.raises(ValidationError):
            parsed.schema_version = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Round 15 PR-HIGH-001 — entry-level atomicity: list shape is not proof of
# atomicity. One entry carrying two claims, or one claim authored twice,
# breaks the confirmation-unit = assertion-unit contract at the AUTHORING
# boundary. All checks are lexical/mechanical — never semantic parsing, and
# never runtime splitting.
# ---------------------------------------------------------------------------


class TestEntryAtomicity:
    def test_two_claim_expansion_entry_is_rejected_naming_the_fix(self) -> None:
        # The peer's exact reproduction: one entry, two claims, one click.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised. Ice pack use explained."]
        with pytest.raises(ValidationError, match="more than one claim") as excinfo:
            AutofillRule.model_validate(data)
        message = str(excinfo.value)
        assert "one list entry per claim" in message
        assert "single_claim" in message  # the override is named, not hidden

    def test_exact_duplicate_expansion_entries_are_rejected(self) -> None:
        data = _rule_data("r1", "ice pack")
        data["expansion"] = ["Ice pack use explained.", "Ice pack use explained."]
        with pytest.raises(ValidationError, match="same assertion"):
            AutofillRule.model_validate(data)

    def test_normalised_duplicate_expansion_entries_are_rejected(self) -> None:
        # Duplicates under the SINGLE tokenisation source, mirroring the
        # duplicate-trigger validator: case/punctuation variants are one
        # assertion.
        data = _rule_data("r1", "ice pack")
        data["expansion"] = ["Ice pack use explained.", "ice pack use EXPLAINED"]
        with pytest.raises(ValidationError, match="same assertion"):
            AutofillRule.model_validate(data)

    def test_two_claim_seed_text_is_rejected_naming_the_fix(self) -> None:
        with pytest.raises(ValidationError, match="more than one claim") as excinfo:
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": [
                        {
                            "section_key": "objective_examination",
                            "seed_text": "Knee inspected. ROM assessed.",
                        }
                    ],
                }
            )
        assert "single_claim" in str(excinfo.value)

    def test_duplicate_seed_assertions_are_rejected(self) -> None:
        seed = {"section_key": "objective_examination", "seed_text": "Knee inspected."}
        with pytest.raises(ValidationError, match="same assertion"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": [seed, dict(seed)],
                }
            )

    def test_two_claim_entry_is_rejected_through_the_loader(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised. Ice pack use explained."]
        _write_user_file(
            root, AUTOFILL_RULES_FILENAME, {"schema_version": 1, "autofill_rules": [data]}
        )
        with pytest.raises(NoteConfigInvalidError, match="more than one claim"):
            load_note_config(root)

    # Round 16 PR-MED-001 → the allow-list reframe: separator forms that
    # leaked through the round-15 deny-list, PLUS novel separators never
    # tested before. The novel forms are the proof the allow-list closes the
    # CLASS — they refuse because they do not match "atomic", not because
    # anyone put them on a list.
    def test_compact_semicolon_compound_is_rejected(self) -> None:
        # Round 16's exact reproduction: no space after the semicolon.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised;ice pack use explained."]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_compact_semicolon_seed_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="more than one claim"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": [
                        {
                            "section_key": "objective_examination",
                            "seed_text": "Knee inspected;ROM assessed.",
                        }
                    ],
                }
            )

    def test_no_space_period_capital_compound_is_rejected(self) -> None:
        # The round-16 leg-1 adjacent form: "advised.Ice".
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised.Ice pack use explained."]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_novel_colon_joined_compound_is_rejected(self) -> None:
        # NOVEL separator (never tested before this round): colon join.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised: ice pack use explained"]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_novel_spaced_dash_joined_compound_is_rejected(self) -> None:
        # NOVEL separator: spaced em-dash clause join.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised — ice pack use explained"]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    # The compound signal must stay NARROW: ordinary atomic assertions —
    # including a trailing terminator and an internal decimal — are accepted.
    @pytest.mark.parametrize(
        "atomic",
        [
            "Rest advised.",
            "Home exercise programme reviewed!",
            "Take 1.5 mg as prescribed.",
            "Pain rated 7/10 today.",
            "Continue exercises; ",  # trailing terminator + whitespace, no further text
            # Allow-list positions the shape must keep accepting WITHOUT the
            # override: hyphen compounds/ranges, typographic digit ranges,
            # digit colons, TERMINAL letter-dot abbreviation chains,
            # ordinary commas and measurements. (Round 17 removed the
            # running-on chain: "Take q.i.d. as directed" is now an
            # override case, tested below.)
            "ROM 90-110 degrees in the mid-back region.",
            "10–15 reps each session",
            "Review at 14:30",
            "Take paracetamol q.i.d.",
            "Ice (10 minutes), then reassess",
            "Grip strength >20 kg, pain <3/10",
        ],
    )
    def test_ordinary_atomic_entries_are_accepted(self, atomic: str) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [atomic]
        rule = AutofillRule.model_validate(data)
        assert rule.expansion_texts() == (atomic,)
        PrefillTemplate.model_validate(
            {
                "prefill_id": "pf1",
                "display_name": "Knee",
                "region_keywords": ["knee"],
                "seed_assertions": [
                    {"section_key": "objective_examination", "seed_text": atomic}
                ],
            }
        )

    # The chain allowance must not become a smuggling route: a letter-dot
    # chain (or any dot) followed by a Capitalised word reads as a sentence
    # boundary and refuses; so does a single letter-dot pair continuing in
    # lowercase (it is not a >=2-pair chain).
    @pytest.mark.parametrize(
        "smuggle",
        [
            "Take q.d. Rest advised",
            "Vitamin D. rest advised",
            "Vitamin D. Rest advised",
        ],
    )
    def test_chain_allowance_does_not_smuggle_a_second_claim(self, smuggle: str) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [smuggle]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    # Round 17 PR-MED-001 (fix-induced): a letter-dot chain is accepted only
    # when TERMINAL. Any continuation after the chain-final dot — lowercase,
    # digit, or capital — is mechanically indistinguishable from a new terse
    # claim and refuses into the override.
    def test_chain_lowercase_continuation_is_rejected(self) -> None:
        # The peer's exact reproduction: frequency claim + treatment claim.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Paracetamol q.i.d. ice applied."]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_chain_digit_continuation_is_rejected(self) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Take q.i.d. 3 times daily"]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_chain_continuation_seed_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="more than one claim"):
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Wound",
                    "region_keywords": ["wound"],
                    "seed_assertions": [
                        {
                            "section_key": "treatment_performed",
                            "seed_text": "Dressing b.i.d. wound reviewed.",
                        }
                    ],
                }
            )

    def test_unknown_character_fails_closed(self) -> None:
        # The allow-list's whole point: a separator nobody anticipated (here
        # a pipe) refuses because it does not match "atomic" — not because
        # someone added it to a list.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised | ice pack use explained"]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_title_abbreviation_refuses_into_the_override(self) -> None:
        # "Dr. Smith" is mechanically indistinguishable from a sentence end
        # (multi-letter word + '.' + space + Capital) — by design it refuses
        # WITHOUT the override and passes WITH it (the override tests below).
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Advised to see Dr. Smith for review."]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_semicolon_with_space_compound_still_rejected(self) -> None:
        # Round-15 behaviour retained through the reframe.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = ["Rest advised; ice pack use explained."]
        with pytest.raises(ValidationError, match="more than one claim"):
            AutofillRule.model_validate(data)

    def test_running_chain_is_a_single_claim_only_via_the_override(self) -> None:
        # Round 17: this exact wording was previously in the accepted matrix
        # — it was pinning the very continuation hole the round closed.
        # Whether "as directed" continues the claim or starts a new one is
        # semantic, so the author states it.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [
            {"assertion_text": "Take q.i.d. as directed", "single_claim": True}
        ]
        rule = AutofillRule.model_validate(data)
        assert rule.expansion_texts() == ("Take q.i.d. as directed",)

    def test_explicit_single_claim_override_is_accepted(self) -> None:
        # The documented false-refusal case, resolved by the author, not a
        # parser: an abbreviation inside ONE assertion.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [
            {"assertion_text": "Advised to see Dr. Smith for review.", "single_claim": True}
        ]
        rule = AutofillRule.model_validate(data)
        assert rule.expansion_texts() == ("Advised to see Dr. Smith for review.",)
        prefill = PrefillTemplate.model_validate(
            {
                "prefill_id": "pf1",
                "display_name": "Knee",
                "region_keywords": ["knee"],
                "seed_assertions": [
                    {
                        "section_key": "objective_examination",
                        "seed_text": "Referred by Dr. Smith. ",
                        "single_claim": True,
                    }
                ],
            }
        )
        assert prefill.seed_assertions[0].single_claim is True

    def test_override_must_be_explicitly_true(self) -> None:
        # Literal[True]: the author states it; "single_claim": false is not
        # a valid spelling of an entry object.
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [{"assertion_text": "Rest advised.", "single_claim": False}]
        with pytest.raises(ValidationError):
            AutofillRule.model_validate(data)

    def test_override_does_not_bypass_the_duplicate_check(self) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = [
            "Rest advised",
            {"assertion_text": "Rest advised.", "single_claim": True},
        ]
        with pytest.raises(ValidationError, match="same assertion"):
            AutofillRule.model_validate(data)

    def test_same_seed_text_in_different_sections_is_accepted(self) -> None:
        # The duplicate key is (section, normalised text): identical wording
        # in two sections is two distinct assertions, not a duplicate.
        prefill = PrefillTemplate.model_validate(
            {
                "prefill_id": "pf1",
                "display_name": "Knee",
                "region_keywords": ["knee"],
                "seed_assertions": [
                    {"section_key": "objective_examination", "seed_text": "Nil noted"},
                    {"section_key": "outcome_measures", "seed_text": "Nil noted"},
                ],
            }
        )
        assert len(prefill.seed_assertions) == 2

    # Round 18 PR-MED-001: the residue documentation is BY REFERENCE to the
    # permissive set, and both sides of that reference are pinned here so it
    # cannot silently drift — four hand-written residue lists in a row were
    # falsified by omission.
    def test_every_in_claim_punctuation_member_is_accepted_mid_claim(self) -> None:
        # Each member of the set is accepted at an arbitrary mid-claim
        # position in BOTH authoring models. This is the mechanical fact the
        # residue text points at: any of these characters can sit between
        # two claims, by design, because legitimate clinical wording needs
        # them. Narrowing the set without revisiting the residue text (or
        # vice versa) fails here.
        for member in sorted(_ALLOWED_IN_CLAIM_PUNCT):
            entry = f"Rest advised {member} ice applied"
            data = _rule_data("r1", "home exercise")
            data["expansion"] = [entry]
            rule = AutofillRule.model_validate(data)
            assert rule.expansion_texts() == (entry,), member
            PrefillTemplate.model_validate(
                {
                    "prefill_id": "pf1",
                    "display_name": "Knee",
                    "region_keywords": ["knee"],
                    "seed_assertions": [
                        {"section_key": "objective_examination", "seed_text": entry}
                    ],
                }
            )

    def test_residue_documentation_is_by_reference_not_enumeration(self) -> None:
        # Both modules must carry the by-reference residue form: naming the
        # SET as the source of truth (not a prose list of familiar
        # separators) and the complete-by-construction marker. A future
        # edit that reverts to a hand enumeration loses the reference and
        # fails here.
        config_src = Path(note_config_module.__file__).read_text(encoding="utf-8")
        fill_src = Path(note_fill_module.__file__).read_text(encoding="utf-8")
        assert "COMPLETE-BY-CONSTRUCTION" in config_src
        assert "COMPLETE-BY-CONSTRUCTION" in fill_src
        # note_fill never imports the set, so any occurrence there is the
        # documentation reference itself.
        assert "_ALLOWED_IN_CLAIM_PUNCT" in fill_src
        # note_config: definition + code use + at least one doc reference.
        assert config_src.count("_ALLOWED_IN_CLAIM_PUNCT") >= 3

    def test_override_entries_survive_canonical_round_trip(self) -> None:
        # `_canonical_config` re-validates from serialized field data; the
        # override must round-trip byte-stably or the generation boundary
        # would refuse a config the loader accepted.
        rule_data = _rule_data("r1", "home exercise")
        rule_data["expansion"] = [
            "Ice pack use explained.",
            {"assertion_text": "Advised to see Dr. Smith.", "single_claim": True},
        ]
        config = NoteConfig(autofill_rules=(AutofillRule.model_validate(rule_data),))
        rebuilt = NoteConfig.model_validate_json(config.to_bytes())
        assert rebuilt == config
        assert rebuilt.config_digest() == config.config_digest()


# ---------------------------------------------------------------------------
# Task 3.2 — loader: precedence, first-run, typed failure, all-or-nothing.
# ---------------------------------------------------------------------------


class TestLoader:
    def test_first_run_missing_root_loads_defaults_and_creates_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        config = load_note_config(root)
        assert config.template_profiles[0].template_profile_id == "template-a"
        assert not root.exists()

    def test_user_file_replaces_its_shipped_default_wholly_per_file(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            TEMPLATE_PROFILES_FILENAME,
            {
                "schema_version": 1,
                "template_profiles": [_profile_data(template_profile_id="custom-b")],
            },
        )
        config = load_note_config(root)
        # Whole-file replacement: only the user's profile exists now...
        assert [p.template_profile_id for p in config.template_profiles] == ["custom-b"]
        # ...while the files the user never overrode still ship defaults.
        assert config.autofill_rules == ()
        assert config.prefill_templates == ()

    def test_user_autofill_rules_leave_shipped_profiles_untouched(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            AUTOFILL_RULES_FILENAME,
            {"schema_version": 1, "autofill_rules": [_rule_data("r1", "home exercise")]},
        )
        config = load_note_config(root)
        assert [r.rule_id for r in config.autofill_rules] == ["r1"]
        assert config.template_profiles[0].template_profile_id == "template-a"

    def test_malformed_user_json_fails_loudly_and_typed(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / AUTOFILL_RULES_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigInvalidError, match=AUTOFILL_RULES_FILENAME):
            load_note_config(root)

    def test_extra_field_in_user_file_fails(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            PREFILL_TEMPLATES_FILENAME,
            {"schema_version": 1, "prefill_templates": [], "surprise": True},
        )
        with pytest.raises(NoteConfigInvalidError, match=PREFILL_TEMPLATES_FILENAME):
            load_note_config(root)

    def test_unreadable_user_file_is_a_loud_error_not_a_silent_fallback(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        # A directory where the file should be: read_bytes raises OSError.
        (root / AUTOFILL_RULES_FILENAME).mkdir()
        with pytest.raises(NoteConfigUnreadableError, match=AUTOFILL_RULES_FILENAME):
            load_note_config(root)

    def test_cross_file_validation_failure_is_typed(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            AUTOFILL_RULES_FILENAME,
            {
                "schema_version": 1,
                "autofill_rules": [
                    _rule_data("r1", "Home Exercise!"),
                    _rule_data("r2", "home  exercise"),
                ],
            },
        )
        with pytest.raises(NoteConfigInvalidError, match="resolved note config is invalid"):
            load_note_config(root)

    def test_default_config_root_shape(self) -> None:
        root = default_config_root()
        assert root.parts[-2:] == ("ClinikoScribe", "config")


# ---------------------------------------------------------------------------
# Practitioner-profile plan Task 4.2 — the cue file through the SAME loader:
# shipped default on first run, whole-file replacement, typed loud failure,
# and the cue set inside the config digest (D7).
# ---------------------------------------------------------------------------


def _shipped_cues_bytes() -> bytes:
    resource = resources.files("scribe_desktop") / "config_defaults" / SECTION_CUES_FILENAME
    return resource.read_bytes()


class TestSectionCuesLoader:
    def test_absent_file_loads_the_shipped_default(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        config = load_note_config(root)
        assert config.normalised_cues() == DEFAULT_SECTION_CUES
        assert tuple(config.section_cues) == CANONICAL_SECTION_KEYS
        assert not root.exists()

    def test_malformed_user_file_fails_loudly_naming_the_file(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / SECTION_CUES_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigInvalidError, match=SECTION_CUES_FILENAME):
            load_note_config(root)

    def test_unknown_key_in_the_user_file_names_the_file(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            SECTION_CUES_FILENAME,
            {"schema_version": 1, "section_cues": {"not_a_section": ["pain in"]}},
        )
        with pytest.raises(NoteConfigInvalidError, match=SECTION_CUES_FILENAME):
            load_note_config(root)

    def test_duplicate_in_the_user_file_names_the_file_and_the_phrase(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            SECTION_CUES_FILENAME,
            {
                "schema_version": 1,
                "section_cues": {
                    "assessment": ["consistent with"],
                    "diagnosis": ["Consistent With"],
                },
            },
        )
        with pytest.raises(NoteConfigInvalidError) as excinfo:
            load_note_config(root)
        assert SECTION_CUES_FILENAME in str(excinfo.value)
        assert "same phrase" in str(excinfo.value)

    def test_unreadable_user_file_is_loud_not_a_silent_fallback(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        (root / SECTION_CUES_FILENAME).mkdir(parents=True)
        with pytest.raises(NoteConfigUnreadableError, match=SECTION_CUES_FILENAME):
            load_note_config(root)

    def test_user_file_replaces_the_shipped_cues_wholly(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            SECTION_CUES_FILENAME,
            {"schema_version": 1, "section_cues": {"advice_home_exercise": ["home exercise"]}},
        )
        config = load_note_config(root)
        assert config.normalised_cues() == {"advice_home_exercise": (("home", "exercise"),)}
        # ...while the files the user never overrode still ship defaults.
        assert config.template_profiles[0].template_profile_id == "template-a"

    def test_a_user_file_identical_to_the_shipped_one_leaves_the_digest_unchanged(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / SECTION_CUES_FILENAME).write_bytes(_shipped_cues_bytes())
        shipped = load_note_config(tmp_path / "other").config_digest()
        assert load_note_config(root).config_digest() == shipped

    def test_digest_changes_with_a_one_phrase_edit(self, tmp_path: Path) -> None:
        shipped = load_note_config(tmp_path / "shipped").config_digest()
        payload = json.loads(_shipped_cues_bytes())
        payload["section_cues"]["advice_home_exercise"].remove("avoid lifting")
        removed_root = tmp_path / "removed"
        _write_user_file(removed_root, SECTION_CUES_FILENAME, payload)
        removed = load_note_config(removed_root).config_digest()
        assert removed != shipped

        payload = json.loads(_shipped_cues_bytes())
        payload["section_cues"]["advice_home_exercise"].append("keep moving")
        added_root = tmp_path / "added"
        _write_user_file(added_root, SECTION_CUES_FILENAME, payload)
        added = load_note_config(added_root).config_digest()
        assert added != shipped
        assert added != removed

    def test_cues_survive_the_canonical_round_trip(self, tmp_path: Path) -> None:
        config = load_note_config(tmp_path / "config")
        rebuilt = _canonical_config(config)
        assert rebuilt.normalised_cues() == config.normalised_cues()
        assert rebuilt.config_digest() == config.config_digest()


# ---------------------------------------------------------------------------
# Task 3.2 — config_digest.
# ---------------------------------------------------------------------------


class TestConfigDigest:
    def test_digest_is_well_formed_and_deterministic(self, tmp_path: Path) -> None:
        first = load_note_config(tmp_path / "config").config_digest()
        second = load_note_config(tmp_path / "config").config_digest()
        assert re.fullmatch(DIGEST_PATTERN, first)
        assert first == second

    def test_digest_changes_when_an_override_changes_the_resolved_config(
        self, tmp_path: Path
    ) -> None:
        shipped = load_note_config(tmp_path / "config").config_digest()
        root = tmp_path / "config"
        _write_user_file(
            root,
            AUTOFILL_RULES_FILENAME,
            {"schema_version": 1, "autofill_rules": [_rule_data("r1", "home exercise")]},
        )
        assert load_note_config(root).config_digest() != shipped

    def test_digest_is_over_canonical_bytes(self, tmp_path: Path) -> None:
        from scribe_desktop.note import digest_bytes

        config = load_note_config(tmp_path / "config")
        assert config.config_digest() == digest_bytes(config.to_bytes())
        assert config.to_bytes() == config.model_dump_json().encode("utf-8")


# ---------------------------------------------------------------------------
# Task 3.3 — shipped defaults in a non-editable install.
# ---------------------------------------------------------------------------


class TestShippedDefaultsPackaging:
    def test_defaults_resolve_through_importlib_resources(self) -> None:
        # The exact mechanism a wheel install uses — never __file__ paths.
        for filename in CONFIG_FILENAMES:
            blob = (
                resources.files("scribe_desktop") / "config_defaults" / filename
            ).read_bytes()
            assert blob, filename

    def test_each_shipped_default_validates_against_its_file_model(self) -> None:
        for filename, model in (
            (TEMPLATE_PROFILES_FILENAME, TemplateProfilesFile),
            (AUTOFILL_RULES_FILENAME, AutofillRulesFile),
            (PREFILL_TEMPLATES_FILENAME, PrefillTemplatesFile),
            (SECTION_CUES_FILENAME, SectionCuesFile),
        ):
            blob = (
                resources.files("scribe_desktop") / "config_defaults" / filename
            ).read_bytes()
            model.model_validate_json(blob)

    def test_pyproject_ships_config_defaults_as_package_data(self) -> None:
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        globs = data["tool"]["setuptools"]["package-data"]["scribe_desktop"]
        assert "config_defaults/*.json" in globs


# ---------------------------------------------------------------------------
# Practitioner-profile plan Phase 5 — consented phrase learning: the refusal
# filter (THE enforcing control), the phrase proposer, and the only writer of
# the user cue file plus its "recently learned" sidecar.
# ---------------------------------------------------------------------------

# Drug names WITHOUT a dose unit anywhere: each ends in one of the listed
# medication suffixes, which is the only thing that refuses them.
_MEDICATION_WORDS: Final[tuple[str, ...]] = (
    "atorvastatin",
    "amoxicillin",
    "metoprolol",
    "adalimumab",
    "omeprazole",
    "losartan",
    "amlodipine",
    "ramipril",
    "imatinib",
    "erythromycin",
)

# THE adversarial fixture: (id, tokens, first_in_segment, following, expected).
_REFUSAL_CASES: Final[tuple[tuple[str, list[str], bool, tuple[str, ...], str | None], ...]] = (
    # --- names -------------------------------------------------------------
    ("name-mid-phrase", ["Tell", "Margaret", "to", "rest"], True, (), "name"),
    ("name-sentence-initial", ["Margaret", "how", "is"], True, (), "name"),
    ("name-title", ["the", "patient", "Mr", "Jones"], False, (), "name"),
    ("common-starter-opens", ["The", "diagnosis", "is"], True, (), None),
    ("common-starter-lowercase", ["the", "diagnosis", "is"], False, (), None),
    # fail toward refusal: a segment-initial capitalised word outside the
    # common-starter set AND outside the learner's opener exemptions is
    # name-like (transcription.is_name_like_token, PR round 15) — the residue
    # the exemption narrows but keeps ("Examination" is unlisted)
    ("residue-examination-shows", ["Examination", "shows", "the", "range"], True, (), "name"),
    # Task 5.7: a listed opener at the REAL first word is admitted (the
    # round-15 residue case, re-pinned as the practitioner's exemption)
    ("admitted-opener-on-examination", ["On", "examination", "the", "range"], True, (), None),
    # --- numbers -----------------------------------------------------------
    ("number-digits", ["the", "dose", "is", "500"], True, (), "number"),
    ("number-word", ["take", "two", "tablets"], False, (), "number"),
    ("number-hyphenated", ["twenty-one", "days", "off"], False, (), "number"),
    ("number-ordinal", ["the", "third", "visit"], False, (), "number"),
    # --- dates -------------------------------------------------------------
    ("date-slash", ["review", "on", "12/03"], False, (), "date"),
    ("date-hyphen", ["review", "on", "12-03"], False, (), "date"),
    ("date-dot", ["review", "on", "12.03"], False, (), "date"),
    ("date-month", ["review", "in", "march"], False, (), "date"),
    ("date-month-abbrev", ["back", "in", "sept"], False, (), "date"),
    ("date-year-beats-number", ["since", "2024", "the"], False, (), "date"),
    # --- medication with a unit -------------------------------------------
    ("med-unit-in-candidate", ["paracetamol", "mg", "twice"], False, (), "medication"),
    ("med-unit-in-window", ["the", "paracetamol", "dose"], False, ("500", "mg"), "medication"),
    ("med-unit-past-window", ["the", "usual", "tablet"], False, ("at", "night", "mg"), None),
    ("med-unit-mixed-case", ["the", "usual", "tablet"], False, ("10", "mL"), "medication"),
    # --- the named anatomical exemptions and the suffix rule ---------------
    ("exempt-spine", ["the", "lumbar", "spine"], False, (), None),
    ("exempt-supine", ["lying", "supine", "today"], False, (), None),
    ("suffix-alone-is-not-a-drug", ["the", "pine", "table"], False, (), None),
    ("longer-than-the-suffix-is", ["the", "alpine", "route"], False, (), "medication"),
    # --- benign phrases the practitioner is allowed to teach ---------------
    ("benign-home-exercise", ["your", "home", "exercise", "is"], False, (), None),
    ("benign-consistent-with", ["consistent", "with", "a", "sprain"], False, (), None),
    ("benign-the-plan-is", ["The", "plan", "is", "to"], True, (), None),
) + tuple(
    (f"med-suffix-{drug}", ["continue", drug, "daily"], False, (), "medication")
    for drug in _MEDICATION_WORDS
)

_REFUSAL_CLASSES: Final[frozenset[str | None]] = frozenset(
    {"name", "number", "date", "medication", None}
)

# The one timestamp every learning write in this module records.
_LEARNED_AT: Final = datetime(2026, 9, 16, 6, 0, tzinfo=UTC)


def _fail_sidecar_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the ONE write path fail for the sidecar only (peer round 36
    PR-MED-023 / PR-MED-024): the cue file is replaced, the sidecar is not."""
    real = note_config_module.atomic_write_bytes

    def selective(path: Path, blob: bytes, *, error_label: str) -> None:
        if path.name == LEARNED_SIDECAR_FILENAME:
            raise StoreWriteError(f"failed writing {error_label}: disk full")
        real(path, blob, error_label=error_label)

    monkeypatch.setattr(note_config_module, "atomic_write_bytes", selective)


class TestRefusalFilter:
    @pytest.mark.parametrize(
        ("tokens", "first_in_segment", "following", "expected"),
        [case[1:] for case in _REFUSAL_CASES],
        ids=[case[0] for case in _REFUSAL_CASES],
    )
    def test_refusal_class(
        self,
        tokens: list[str],
        first_in_segment: bool,
        following: tuple[str, ...],
        expected: str | None,
    ) -> None:
        assert (
            refuse_learning_candidate(
                tokens, first_in_segment=first_in_segment, following=following
            )
            == expected
        )

    def test_the_fixture_only_expects_the_four_classes_or_none(self) -> None:
        for case in _REFUSAL_CASES:
            assert case[4] in _REFUSAL_CLASSES, case[0]

    def test_the_check_order_is_name_then_date_then_number_then_medication(self) -> None:
        # A four-digit run is a YEAR before it is a number, and a d/d pair is a
        # date before either; a bare three-digit run is only a number.
        assert refuse_learning_candidate(["2024"], first_in_segment=False) == "date"
        assert refuse_learning_candidate(["12/03"], first_in_segment=False) == "date"
        assert refuse_learning_candidate(["500"], first_in_segment=False) == "number"

    # --- Task 5.7: the practitioner's opener exemptions (2026-09-17) ---------

    @pytest.mark.parametrize("opener", sorted(LEARNING_OPENER_EXEMPTIONS))
    def test_an_exempted_opener_passes_the_name_check_at_the_real_start(
        self, opener: str
    ) -> None:
        tokens = [opener.capitalize(), "the", "knee", "moving"]
        assert refuse_learning_candidate(tokens, first_in_segment=True) is None

    @pytest.mark.parametrize("opener", sorted(LEARNING_OPENER_EXEMPTIONS))
    def test_an_exempted_opener_is_still_refused_off_the_real_start(
        self, opener: str
    ) -> None:
        capitalised = opener.capitalize()
        # Candidate index 0 but NOT the segment's first word (a filler before it).
        assert (
            refuse_learning_candidate([capitalised, "the", "knee"], first_in_segment=False)
            == "name"
        )
        # Mid-candidate, at the real start of the segment.
        assert (
            refuse_learning_candidate(["the", capitalised, "knee"], first_in_segment=True)
            == "name"
        )

    def test_an_unlisted_capitalised_opener_is_still_refused(self) -> None:
        assert refuse_learning_candidate(["Margaret", "how", "is"], first_in_segment=True) == "name"
        assert (
            refuse_learning_candidate(["Take", "the", "tablets"], first_in_segment=True) == "name"
        )
        assert "take" not in LEARNING_OPENER_EXEMPTIONS

    def test_an_exempted_opener_does_not_skip_the_other_checks(self) -> None:
        assert refuse_learning_candidate(["Use", "two", "tablets"], first_in_segment=True) == (
            "number"
        )
        assert (
            refuse_learning_candidate(
                ["Use", "the", "gel"], first_in_segment=True, following=("5", "mg")
            )
            == "medication"
        )
        assert refuse_learning_candidate(["Apply", "on", "12/03"], first_in_segment=True) == (
            "date"
        )
        assert (
            refuse_learning_candidate(["Continue", "the", "atorvastatin"], first_in_segment=True)
            == "medication"
        )

    def test_the_exemption_list_holds_no_number_word_and_no_name_homograph(self) -> None:
        assert LEARNING_OPENER_EXEMPTIONS == frozenset(
            """
            keep try avoid continue rest ice heat stretch apply hold repeat use start stop
            your on for with at in before after
            """.split()
        )
        for word in LEARNING_OPENER_EXEMPTIONS:
            assert not is_number_token(word), word
            assert word == word.lower() and word.isalpha(), word
            # Not one of the transcript's own starters: the pinned heuristic
            # still marks each as name-like at a segment start, so the list
            # ADDS to those starters rather than restating them.
            assert is_name_like_token(word.capitalize(), first_in_segment=True), word

    # --- the practitioner's 2026-09-18 re-smoke: a contracted starter -------

    def test_the_practitioners_contracted_starter_line_is_admitted(self) -> None:
        """The live refusal of the 2026-09-18 re-smoke ("Moved to History of
        presenting complaint … Not learned: contains a name/number/date/
        medication (name)." on the practitioner's own line), with the exact
        words — now ADMITTED (Task 5.8). The uncertainty marks are
        display-only, so the filter sees the raw ``We're``; the punctuation
        strip trims only the ENDS, so the apostrophe survives; ``we`` is a
        transcript starter but ``we're`` is not, so the pinned round-15
        heuristic still marks it name-like at a segment start (the transcript
        surface, untouched) — the learner's contracted-starter list admits it
        at the real first word for the name check only."""
        words = (
            "We're going to do a bit of a treatment, work through some of the muscles, "
            "do a bit of an assessment as well, obviously."
        ).split()
        candidate = propose_learning_phrase(words)
        assert candidate is not None
        assert candidate.source_words == ("We're", "going", "to", "do")
        assert candidate.first_in_segment is True
        assert candidate.following == ("a", "bit")
        assert "we" in _COMMON_SEGMENT_STARTERS
        assert "we're" not in _COMMON_SEGMENT_STARTERS
        assert "we're" not in LEARNING_OPENER_EXEMPTIONS
        assert "we're" in LEARNING_CONTRACTED_STARTERS
        assert is_name_like_token("We're", first_in_segment=True)  # the transcript's mark
        assert (
            refuse_learning_candidate(
                candidate.source_words,
                first_in_segment=candidate.first_in_segment,
                following=candidate.following,
            )
            is None
        )
        assert candidate.phrase == "we're going to do"

    # --- Task 5.8: the contracted starters (practitioner-decided 2026-09-18) --

    @pytest.mark.parametrize("form", sorted(LEARNING_CONTRACTED_STARTERS))
    def test_a_contracted_starter_passes_the_name_check_at_the_real_start(
        self, form: str
    ) -> None:
        tokens = [form.capitalize(), "give", "the", "knee"]
        assert refuse_learning_candidate(tokens, first_in_segment=True) is None

    @pytest.mark.parametrize("form", sorted(LEARNING_CONTRACTED_STARTERS))
    def test_a_contracted_starter_is_still_refused_off_the_real_start(
        self, form: str
    ) -> None:
        capitalised = form.capitalize()
        assert (
            refuse_learning_candidate([capitalised, "give", "the"], first_in_segment=False)
            == "name"
        )
        assert (
            refuse_learning_candidate(["the", capitalised, "knee"], first_in_segment=True)
            == "name"
        )

    def test_a_typographic_apostrophe_is_folded_before_the_lookup(self) -> None:
        curly = "We’re"
        assert curly not in LEARNING_CONTRACTED_STARTERS
        assert refuse_learning_candidate([curly, "going", "to"], first_in_segment=True) is None
        assert refuse_learning_candidate(["Don’t", "rush", "it"], first_in_segment=True) is None

    def test_an_apostrophe_less_lookalike_is_still_refused(self) -> None:
        # ("Were" is itself a transcript starter — the auxiliary — so the
        # lookalikes here are forms no list and no starter set holds.)
        assert refuse_learning_candidate(["Youre", "going", "to"], first_in_segment=True) == "name"
        assert refuse_learning_candidate(["Ill", "give", "the"], first_in_segment=True) == "name"
        assert refuse_learning_candidate(["Dont", "rush", "it"], first_in_segment=True) == "name"

    def test_a_contracted_starter_does_not_skip_the_other_checks(self) -> None:
        assert refuse_learning_candidate(["We'll", "take", "two"], first_in_segment=True) == (
            "number"
        )
        assert refuse_learning_candidate(["It's", "due", "12/03"], first_in_segment=True) == (
            "date"
        )
        assert (
            refuse_learning_candidate(
                ["I'll", "add", "the"], first_in_segment=True, following=("500", "mg")
            )
            == "medication"
        )
        named = ["We're", "seeing", "Margaret"]
        assert refuse_learning_candidate(named, first_in_segment=True) == "name"

    def test_the_contracted_list_is_the_practitioners_and_holds_no_number_word(self) -> None:
        assert LEARNING_CONTRACTED_STARTERS == frozenset(
            """
            we're we'll we've we'd i'm i'll i've i'd it's it'll that's there's here's he's
            he'll she's she'll they're they'll they've you're you'll you've you'd what's
            who's where's how's let's don't doesn't didn't can't couldn't won't wouldn't
            shouldn't isn't aren't wasn't weren't haven't hasn't hadn't
            """.split()
        )
        assert LEARNING_CONTRACTED_STARTERS.isdisjoint(LEARNING_OPENER_EXEMPTIONS)
        for form in LEARNING_CONTRACTED_STARTERS:
            assert not is_number_token(form), form
            assert form == form.lower() and "'" in form, form
            stem, _apostrophe, _suffix = form.partition("'")
            assert stem.isalpha(), form
        # Only ``let's`` was already a transcript starter; every other form
        # was name-like at a segment start, so the list ADDS to the pinned set.
        already = {f for f in LEARNING_CONTRACTED_STARTERS if f in _COMMON_SEGMENT_STARTERS}
        assert already == {"let's"}


class TestProposeLearningPhrase:
    def test_leading_content_tokens_and_the_following_window(self) -> None:
        candidate = propose_learning_phrase(
            ["Your", "home", "exercise", "is", "the", "wall", "slide"]
        )
        assert candidate is not None
        assert candidate.phrase == "your home exercise is"
        assert candidate.source_words == ("Your", "home", "exercise", "is")
        assert candidate.following == ("the", "wall")

    def test_fillers_and_punctuation_only_words_do_not_count(self) -> None:
        candidate = propose_learning_phrase(["um", "the", "-", "knee", "feels"])
        assert candidate is not None
        assert candidate.phrase == "the knee feels"
        assert candidate.source_words == ("the", "knee", "feels")
        assert candidate.following == ()

    @pytest.mark.parametrize(
        "word_texts",
        [[], ["um", "knee"], ["-", "..."]],
        ids=["empty", "one-content-word", "punctuation-only"],
    )
    def test_fewer_than_two_content_words_propose_nothing(self, word_texts: list[str]) -> None:
        assert propose_learning_phrase(word_texts) is None

    def test_exactly_the_minimum_proposes_a_phrase(self) -> None:
        candidate = propose_learning_phrase(["wall", "slide"])
        assert candidate is not None
        assert candidate.phrase == "wall slide"
        assert candidate.source_words == ("wall", "slide")
        assert candidate.following == ()

    def test_the_stored_phrase_is_normalised_not_the_source_words(self) -> None:
        candidate = propose_learning_phrase(["Wall", "Slide,"])
        assert candidate is not None
        assert candidate.phrase == "wall slide"
        assert candidate.source_words == ("Wall", "Slide,")

    def test_the_token_bounds_and_the_cap(self) -> None:
        assert LEARNED_PHRASE_MIN_TOKENS == 2
        assert LEARNED_PHRASE_MAX_TOKENS == 4
        candidate = propose_learning_phrase(
            ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
        )
        assert candidate is not None
        assert candidate.phrase == "alpha bravo charlie delta"
        assert len(candidate.source_words) == LEARNED_PHRASE_MAX_TOKENS
        assert candidate.following == ("echo", "foxtrot")

    def test_first_in_segment_follows_the_real_position(self) -> None:
        """Peer round 36 PR-HIGH-008 (verified MED): the opener exemption
        belongs to segment index 0 — a dropped leading filler must not hand
        it to the next word."""
        at_start = propose_learning_phrase(["Will", "needs", "the", "exercises"])
        after_filler = propose_learning_phrase(["Um,", "Will", "needs", "the", "exercises"])
        assert at_start is not None and after_filler is not None
        assert at_start.first_in_segment is True
        assert after_filler.first_in_segment is False
        assert at_start.source_words == after_filler.source_words == (
            "Will", "needs", "the", "exercises"
        )

    def test_a_name_after_a_leading_filler_is_refused_end_to_end(self) -> None:
        """The composed regression: extraction → filter. "Will" is both a
        common sentence opener and a name; after a filler it sits at
        segment position 1, where the transcript marks it name-like, and the
        filter must agree. At a true segment start the pinned heuristic's
        opener admission stands (recorded at PR round 15)."""
        after_filler = propose_learning_phrase(["Um,", "Will", "needs", "the", "exercises"])
        assert after_filler is not None
        assert (
            refuse_learning_candidate(
                after_filler.source_words,
                first_in_segment=after_filler.first_in_segment,
                following=after_filler.following,
            )
            == "name"
        )
        at_start = propose_learning_phrase(["Will", "needs", "the", "exercises"])
        assert at_start is not None
        assert (
            refuse_learning_candidate(
                at_start.source_words,
                first_in_segment=at_start.first_in_segment,
                following=at_start.following,
            )
            is None
        )
        # A genuine opener keeps its exemption only at the real start too.
        benign = propose_learning_phrase(["Um,", "The", "knee", "felt", "steady"])
        assert benign is not None
        assert benign.first_in_segment is False
        assert (
            refuse_learning_candidate(
                benign.source_words,
                first_in_segment=benign.first_in_segment,
                following=benign.following,
            )
            == "name"
        )


class TestAppendUserCues:
    def test_a_first_append_creates_both_files_from_the_shipped_default(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert result.added == (("advice_home_exercise", "wall slide"),)
        assert result.skipped == ()
        assert (root / SECTION_CUES_FILENAME).is_file()
        assert (root / LEARNED_SIDECAR_FILENAME).is_file()
        cues = load_note_config(root).normalised_cues()
        assert cues["advice_home_exercise"] == (
            *DEFAULT_SECTION_CUES["advice_home_exercise"],
            ("wall", "slide"),
        )
        for key in CANONICAL_SECTION_KEYS:
            if key != "advice_home_exercise":
                assert cues[key] == DEFAULT_SECTION_CUES[key], key

    def test_the_stored_form_is_normalised(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("advice_home_exercise", "Wall  Slide,")],
            config_root=root,
            learned_at=_LEARNED_AT,
        )
        assert result.added == (("advice_home_exercise", "wall slide"),)
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") in cues["advice_home_exercise"]

    def test_a_duplicate_under_normalisation_is_skipped_and_nothing_is_written(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("advice_home_exercise", "Home Exercise")],
            config_root=root,
            learned_at=_LEARNED_AT,
        )
        assert result.added == ()
        assert result.skipped == (("advice_home_exercise", "Home Exercise", "duplicate"),)
        assert not root.exists()

    def test_a_cross_section_duplicate_is_skipped_too(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("diagnosis", "home exercise")], config_root=root, learned_at=_LEARNED_AT
        )
        assert result.added == ()
        assert result.skipped == (("diagnosis", "home exercise", "duplicate"),)
        assert not root.exists()

    def test_the_same_phrase_twice_in_one_call_is_added_once(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("advice_home_exercise", "wall slide"), ("advice_home_exercise", "Wall slide")],
            config_root=root,
            learned_at=_LEARNED_AT,
        )
        assert result.added == (("advice_home_exercise", "wall slide"),)
        assert result.skipped == (("advice_home_exercise", "Wall slide", "duplicate"),)
        cues = load_note_config(root).normalised_cues()
        assert cues["advice_home_exercise"].count(("wall", "slide")) == 1

    @pytest.mark.parametrize("phrase", ["um", "..."], ids=["filler", "punctuation"])
    def test_a_phrase_with_no_content_tokens_is_skipped_as_empty(
        self, tmp_path: Path, phrase: str
    ) -> None:
        root = tmp_path / "config"
        result = append_user_cues(
            [("advice_home_exercise", phrase)], config_root=root, learned_at=_LEARNED_AT
        )
        assert result.added == ()
        assert result.skipped == (("advice_home_exercise", phrase, "empty"),)
        assert not root.exists()

    def test_a_second_append_keeps_the_first_phrase(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        later = datetime(2026, 9, 16, 7, 0, tzinfo=UTC)
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        result = append_user_cues(
            [("treatment_performed", "ice pack")], config_root=root, learned_at=later
        )
        assert result.added == (("treatment_performed", "ice pack"),)
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") in cues["advice_home_exercise"]
        assert ("ice", "pack") in cues["treatment_performed"]
        assert load_learned_phrases(root).recent == (
            LearnedPhrase("ice pack", "treatment_performed", later),
            LearnedPhrase("wall slide", "advice_home_exercise", _LEARNED_AT),
        )

    def test_an_over_long_phrase_raises_and_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        over_long = "aa " * 100
        assert len(" ".join(over_long.split())) > MAX_TRIGGER_CHARS
        with pytest.raises(NoteConfigInvalidError):
            append_user_cues(
                [("advice_home_exercise", over_long)],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert not (root / SECTION_CUES_FILENAME).exists()
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()

    def test_a_validation_failure_leaves_existing_files_byte_identical(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        before = (root / SECTION_CUES_FILENAME).read_bytes()
        sidecar_before = (root / LEARNED_SIDECAR_FILENAME).read_bytes()
        with pytest.raises(NoteConfigInvalidError):
            append_user_cues(
                [("management_plan", "bb " * 100)],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert (root / SECTION_CUES_FILENAME).read_bytes() == before
        assert (root / LEARNED_SIDECAR_FILENAME).read_bytes() == sidecar_before

    def test_a_malformed_user_cue_file_raises_and_is_left_alone(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / SECTION_CUES_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigInvalidError, match=re.escape(SECTION_CUES_FILENAME)):
            append_user_cues(
                [("advice_home_exercise", "wall slide")],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert (root / SECTION_CUES_FILENAME).read_text(encoding="utf-8") == "{not json"
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()

    def test_a_malformed_sidecar_raises_and_leaves_the_cue_file(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / SECTION_CUES_FILENAME).write_bytes(_shipped_cues_bytes())
        (root / LEARNED_SIDECAR_FILENAME).write_text("{not json", encoding="utf-8")
        before = (root / SECTION_CUES_FILENAME).read_bytes()
        with pytest.raises(NoteConfigInvalidError, match=re.escape(LEARNED_SIDECAR_FILENAME)):
            append_user_cues(
                [("advice_home_exercise", "wall slide")],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert (root / SECTION_CUES_FILENAME).read_bytes() == before

    def test_a_write_failure_is_typed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The atomic-write primitive's ``StoreWriteError`` surfaces as the
        loader-family ``NoteConfigWriteError`` (the seam is the ONE write
        path, ``_write_config_file``), and nothing is left behind: the
        primitive never leaves a partial file, and the sidecar write is never
        reached."""
        root = tmp_path / "config"

        def refuse(path: Path, blob: bytes, *, error_label: str) -> None:
            raise StoreWriteError(f"failed writing {error_label}: disk full")

        monkeypatch.setattr(note_config_module, "atomic_write_bytes", refuse)
        with pytest.raises(NoteConfigWriteError, match=SECTION_CUES_FILENAME):
            append_user_cues(
                [("advice_home_exercise", "wall slide")],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert not (root / SECTION_CUES_FILENAME).exists()
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()

    def test_a_config_root_that_is_a_file_cannot_be_written(self, tmp_path: Path) -> None:
        """A FILE where the config directory belongs: whichever typed error
        the read or the directory creation raises, it is a ``NoteConfigError``
        and nothing is written."""
        root = tmp_path / "config"
        root.write_text("not a directory", encoding="utf-8")
        with pytest.raises(NoteConfigError):
            append_user_cues(
                [("advice_home_exercise", "wall slide")],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert root.read_text(encoding="utf-8") == "not a directory"

    def test_the_written_file_loads_and_moves_the_digest(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        shipped = load_note_config(tmp_path / "shipped").config_digest()
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert load_note_config(root).config_digest() != shipped

    def test_a_sidecar_write_failure_after_the_cue_write_is_returned_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 36 PR-MED-023: the phrase IS on disk, so the outcome
        says so — learned, listed by section, no date."""
        root = tmp_path / "config"
        _fail_sidecar_writes(monkeypatch)
        outcome = append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert outcome.added == (("advice_home_exercise", "wall slide"),)
        assert outcome.skipped == ()
        assert outcome.sidecar_error is not None
        assert LEARNED_SIDECAR_FILENAME in outcome.sidecar_error
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") in cues["advice_home_exercise"]
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()
        learned = load_learned_phrases(root)
        assert learned.by_section == (("advice_home_exercise", ("wall slide",)),)
        assert learned.recent == ()

    def test_a_clean_append_reports_no_sidecar_error(self, tmp_path: Path) -> None:
        outcome = append_user_cues(
            [("advice_home_exercise", "wall slide")],
            config_root=tmp_path / "config",
            learned_at=_LEARNED_AT,
        )
        assert outcome.sidecar_error is None

    def test_a_raw_cleanup_error_on_the_sidecar_still_returns_the_committed_outcome(
        self, tmp_path: Path
    ) -> None:
        """Peer round 37 PR-MED-025, through the REAL atomic writer: a
        directory planted at the sidecar's temp path makes the write fail AND
        the cleanup unlink fail, so the writer surfaces a raw OSError; the
        config boundary folds it, and the committed cue is reported."""
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / (LEARNED_SIDECAR_FILENAME + ".tmp")).mkdir()
        outcome = append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert outcome.added == (("advice_home_exercise", "wall slide"),)
        assert outcome.sidecar_error is not None
        assert LEARNED_SIDECAR_FILENAME in outcome.sidecar_error
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") in cues["advice_home_exercise"]
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()
        assert load_learned_phrases(root).by_section == (
            ("advice_home_exercise", ("wall slide",)),
        )

    def test_a_raw_cleanup_error_on_the_cue_file_is_typed_and_writes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        root.mkdir(parents=True)
        (root / (SECTION_CUES_FILENAME + ".tmp")).mkdir()
        with pytest.raises(NoteConfigWriteError, match=re.escape(SECTION_CUES_FILENAME)):
            append_user_cues(
                [("advice_home_exercise", "wall slide")],
                config_root=root,
                learned_at=_LEARNED_AT,
            )
        assert not (root / SECTION_CUES_FILENAME).exists()
        assert not (root / LEARNED_SIDECAR_FILENAME).exists()


class TestLoadLearnedPhrases:
    def test_no_user_file_means_nothing_learned_even_with_a_sidecar(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            LEARNED_SIDECAR_FILENAME,
            {
                "schema_version": 1,
                "learned": {
                    "wall slide": {
                        "section": "advice_home_exercise",
                        "learned_at": _LEARNED_AT.isoformat(),
                    }
                },
            },
        )
        assert load_learned_phrases(root) == LearnedPhrases((), ())

    def test_recent_is_newest_first_and_by_section_is_canonical(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        later = datetime(2026, 9, 16, 8, 0, tzinfo=UTC)
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        append_user_cues(
            [("treatment_performed", "ice pack")], config_root=root, learned_at=later
        )
        learned = load_learned_phrases(root)
        assert learned.recent == (
            LearnedPhrase("ice pack", "treatment_performed", later),
            LearnedPhrase("wall slide", "advice_home_exercise", _LEARNED_AT),
        )
        # Canonical order (treatment_performed precedes advice_home_exercise)
        # and the SHIPPED phrases of both sections are absent.
        assert learned.by_section == (
            ("treatment_performed", ("ice pack",)),
            ("advice_home_exercise", ("wall slide",)),
        )

    def test_a_sidecar_entry_absent_from_the_cue_file_is_dropped(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        _write_user_file(
            root,
            LEARNED_SIDECAR_FILENAME,
            {
                "schema_version": 1,
                "learned": {
                    "wall slide": {
                        "section": "advice_home_exercise",
                        "learned_at": _LEARNED_AT.isoformat(),
                    },
                    "ghost phrase": {
                        "section": "management_plan",
                        "learned_at": _LEARNED_AT.isoformat(),
                    },
                },
            },
        )
        learned = load_learned_phrases(root)
        assert [entry.phrase for entry in learned.recent] == ["wall slide"]

    def test_recent_is_capped_at_the_limit(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        for index in range(RECENTLY_LEARNED_LIMIT + 1):
            append_user_cues(
                [("advice_home_exercise", f"learned phrase {index}")],
                config_root=root,
                learned_at=_LEARNED_AT + timedelta(minutes=index),
            )
        learned = load_learned_phrases(root)
        assert len(learned.recent) == RECENTLY_LEARNED_LIMIT
        assert [entry.phrase for entry in learned.recent] == [
            f"learned phrase {index}" for index in range(RECENTLY_LEARNED_LIMIT, 0, -1)
        ]
        # The cap is on the RECENT list only; every learned phrase is listed.
        assert learned.by_section == (
            (
                "advice_home_exercise",
                tuple(
                    f"learned phrase {index}"
                    for index in range(RECENTLY_LEARNED_LIMIT + 1)
                ),
            ),
        )

    def test_a_shipped_phrase_moved_by_hand_is_never_listed_as_learned(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            SECTION_CUES_FILENAME,
            {
                "schema_version": 1,
                "section_cues": {
                    "assessment": ["home exercise"],
                    "advice_home_exercise": ["wall slide"],
                },
            },
        )
        learned = load_learned_phrases(root)
        assert learned.by_section == (("advice_home_exercise", ("wall slide",)),)
        assert learned.recent == ()

    def test_a_malformed_sidecar_raises_naming_the_sidecar(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        (root / LEARNED_SIDECAR_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(NoteConfigInvalidError, match=re.escape(LEARNED_SIDECAR_FILENAME)):
            load_learned_phrases(root)


class TestDeleteUserCue:
    def test_no_user_file_returns_false_and_creates_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        assert delete_user_cue("wall slide", config_root=root) is False
        assert not root.exists()

    def test_a_learned_phrase_is_removed_from_both_files(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert delete_user_cue("wall slide", config_root=root) is True
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") not in cues["advice_home_exercise"]
        assert cues["advice_home_exercise"] == DEFAULT_SECTION_CUES["advice_home_exercise"]
        assert (root / SECTION_CUES_FILENAME).is_file()
        assert (root / LEARNED_SIDECAR_FILENAME).is_file()
        assert load_learned_phrases(root) == LearnedPhrases((), ())

    def test_the_match_is_case_and_punctuation_insensitive(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert delete_user_cue("Wall Slide,", config_root=root) is True
        cues = load_note_config(root).normalised_cues()
        assert ("wall", "slide") not in cues["advice_home_exercise"]

    def test_an_unknown_phrase_returns_false_and_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        before = (root / SECTION_CUES_FILENAME).read_bytes()
        sidecar_before = (root / LEARNED_SIDECAR_FILENAME).read_bytes()
        assert delete_user_cue("never said this", config_root=root) is False
        assert (root / SECTION_CUES_FILENAME).read_bytes() == before
        assert (root / LEARNED_SIDECAR_FILENAME).read_bytes() == sidecar_before

    def test_a_shipped_phrase_can_be_deleted_from_the_practitioners_own_file(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        assert delete_user_cue("home exercise", config_root=root) is True
        config = load_note_config(root)
        assert "advice_home_exercise" in config.section_cues
        cues = config.normalised_cues()["advice_home_exercise"]
        assert ("home", "exercise") not in cues
        assert ("wall", "slide") in cues
        assert load_learned_phrases(root).recent == (
            LearnedPhrase("wall slide", "advice_home_exercise", _LEARNED_AT),
        )

    def test_a_failed_sidecar_write_is_repaired_by_the_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 36 PR-MED-024: a delete whose sidecar write fails after
        the cue was removed leaves the phrase in the sidecar; the retry must
        remove it even though the cue is already gone."""
        root = tmp_path / "config"
        real = note_config_module.atomic_write_bytes
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        _fail_sidecar_writes(monkeypatch)
        with pytest.raises(NoteConfigWriteError, match=re.escape(LEARNED_SIDECAR_FILENAME)):
            delete_user_cue("wall slide", config_root=root)
        # The cue is gone, the sidecar entry survived, the lists hide it.
        assert ("wall", "slide") not in load_note_config(root).normalised_cues()[
            "advice_home_exercise"
        ]
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert "wall slide" in sidecar["learned"]
        assert load_learned_phrases(root) == LearnedPhrases((), ())
        # The retry finishes the job.
        monkeypatch.setattr(note_config_module, "atomic_write_bytes", real)
        assert delete_user_cue("wall slide", config_root=root) is True
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert sidecar["learned"] == {}
        # And a third attempt is a true no-op.
        before = (root / LEARNED_SIDECAR_FILENAME).read_bytes()
        assert delete_user_cue("wall slide", config_root=root) is False
        assert (root / LEARNED_SIDECAR_FILENAME).read_bytes() == before

    def test_a_raw_cleanup_error_on_delete_is_typed_and_the_retry_succeeds(
        self, tmp_path: Path
    ) -> None:
        """Peer round 37 PR-MED-025 through the REAL atomic writer on the
        delete path: the cue is removed, the sidecar write double-faults, the
        error is the config family (the tab's retryable branch), and the retry
        finishes once the temp path is clear."""
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide")], config_root=root, learned_at=_LEARNED_AT
        )
        blocker = root / (LEARNED_SIDECAR_FILENAME + ".tmp")
        blocker.mkdir()
        with pytest.raises(NoteConfigWriteError, match=re.escape(LEARNED_SIDECAR_FILENAME)):
            delete_user_cue("wall slide", config_root=root)
        assert ("wall", "slide") not in load_note_config(root).normalised_cues()[
            "advice_home_exercise"
        ]
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert "wall slide" in sidecar["learned"]
        blocker.rmdir()
        assert delete_user_cue("wall slide", config_root=root) is True
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert sidecar["learned"] == {}

    def test_a_later_delete_prunes_any_orphaned_sidecar_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        append_user_cues(
            [("advice_home_exercise", "wall slide"), ("treatment_performed", "ice pack")],
            config_root=root,
            learned_at=_LEARNED_AT,
        )
        payload = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        payload["learned"]["ghost phrase"] = {
            "section": "management_plan",
            "learned_at": _LEARNED_AT.isoformat(),
        }
        _write_user_file(root, LEARNED_SIDECAR_FILENAME, payload)
        assert delete_user_cue("ice pack", config_root=root) is True
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert set(sidecar["learned"]) == {"wall slide"}
        assert ("wall", "slide") in load_note_config(root).normalised_cues()[
            "advice_home_exercise"
        ]

    def test_a_sidecar_only_phrase_is_deletable_without_a_user_file(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "config"
        _write_user_file(
            root,
            LEARNED_SIDECAR_FILENAME,
            {
                "schema_version": 1,
                "learned": {
                    "wall slide": {
                        "section": "advice_home_exercise",
                        "learned_at": _LEARNED_AT.isoformat(),
                    }
                },
            },
        )
        assert delete_user_cue("wall slide", config_root=root) is True
        assert not (root / SECTION_CUES_FILENAME).exists()  # never created here
        sidecar = json.loads((root / LEARNED_SIDECAR_FILENAME).read_text(encoding="utf-8"))
        assert sidecar["learned"] == {}
