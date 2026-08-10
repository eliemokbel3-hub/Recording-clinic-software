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
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any, Final

import pytest
from pydantic import ValidationError

from scribe_desktop.note import (
    CANONICAL_SECTION_KEYS,
    DIGEST_PATTERN,
    GeneratedSection,
    NoteAssertion,
    NoteSectionKey,
    NoteSpan,
    SourceCoords,
)
from scribe_desktop.note_config import (
    AUTOFILL_RULES_FILENAME,
    CONFIG_FILENAMES,
    MAX_CONFIG_LABEL_CHARS,
    PREFILL_TEMPLATES_FILENAME,
    TEMPLATE_PROFILES_FILENAME,
    AutofillRule,
    AutofillRulesFile,
    BoundTemplateProfile,
    NoteConfig,
    NoteConfigError,
    NoteConfigInvalidError,
    NoteConfigUnreadableError,
    PrefillTemplate,
    PrefillTemplatesFile,
    TemplateProfile,
    TemplateProfilesFile,
    TemplateProfileUnboundError,
    bind_template_profile,
    build_note_request,
    default_config_root,
    load_note_config,
    mapping_drop_warnings,
)
from scribe_desktop.speech import SAMPLE_RATE
from scribe_desktop.transcription import (
    SPEAKER_1,
    TranscriptDocument,
    TranscriptSegment,
    TranscriptWord,
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

    def test_expansion_must_be_a_list_not_a_string(self) -> None:
        data = _rule_data("r1", "home exercise")
        data["expansion"] = "One claim. Another claim."
        with pytest.raises(ValidationError):
            AutofillRule.model_validate(data)

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
