"""Note-learning-and-styles plan Phase 0 Task 0.3: the two shipped
vocabularies and the practitioner settings file; and (note-content-design
plan Task R.1) the shipped clinical-equivalents lexicon and its structural
invariants."""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

import pytest
from pydantic import ValidationError

import scribe_desktop.note_config as note_config_module
from scribe_desktop.note_config import (
    CLINICAL_ABBREVIATIONS,
    CLINICAL_ABBREVIATIONS_FILENAME,
    CLINICAL_EQUIVALENTS,
    CLINICAL_EQUIVALENTS_FILENAME,
    DEFAULT_NOTE_STYLE,
    PRACTITIONER_SETTINGS_FILENAME,
    PROSE_CONNECTIVES,
    PROSE_CONNECTIVES_FILENAME,
    ClinicalRegister,
    NoteConfigInvalidError,
    NoteConfigUnreadableError,
    NoteConfigWriteError,
    PractitionerSettings,
    _decode_clinical_equivalents,
    _parse_clinical_equivalents,
    _parse_shipped_vocabulary,
    load_practitioner_settings,
    save_practitioner_settings,
)
from scribe_desktop.session_store import StoreWriteError
from scribe_desktop.transcription import is_number_token

# ---------------------------------------------------------------------------
# The two shipped vocabularies (D6, D10).
# ---------------------------------------------------------------------------

_TEST_FILENAME = "x.json"
_TEST_KEY = "entries"


def _vocabulary_payload(entries: object) -> dict[str, object]:
    return {"schema_version": 1, _TEST_KEY: entries}


def _parse(payload: object, *, lower_case: bool = True) -> tuple[str, ...]:
    return _parse_shipped_vocabulary(
        payload, filename=_TEST_FILENAME, key=_TEST_KEY, lower_case=lower_case
    )


# Every payload a packaged vocabulary must REFUSE at import: the shape
# refusals, the completeness refusal (an emptied list must never import as
# "admit nothing" / "allow nothing") and the per-entry content rules.
_BROKEN_VOCABULARY_PAYLOADS = [
    pytest.param([], id="not-an-object"),
    pytest.param({"schema_version": 1}, id="no-key"),
    pytest.param(_vocabulary_payload([]), id="empty-list"),
    pytest.param(_vocabulary_payload([1]), id="non-string-entry"),
    pytest.param(_vocabulary_payload([" "]), id="blank-entry"),
    pytest.param(_vocabulary_payload(["neck pain"]), id="two-word-entry"),
    pytest.param(_vocabulary_payload(["a\tb"]), id="control-character"),
    pytest.param(_vocabulary_payload(["and", "and"]), id="duplicate-entry"),
    pytest.param(_vocabulary_payload(["And"]), id="upper-case-entry"),
]


@pytest.mark.parametrize("payload", _BROKEN_VOCABULARY_PAYLOADS)
def test_a_broken_packaged_vocabulary_is_refused_at_import(payload: object) -> None:
    with pytest.raises(RuntimeError, match="broken install"):
        _parse(payload)


def test_an_upper_case_entry_is_accepted_when_the_list_is_case_preserving() -> None:
    assert _parse(_vocabulary_payload(["And"]), lower_case=False) == ("And",)


def test_a_good_list_round_trips_to_a_tuple_in_order() -> None:
    assert _parse(_vocabulary_payload(["the", "and", "of"])) == ("the", "and", "of")


def _packaged_payload(filename: str) -> dict[str, object]:
    resource = resources.files("scribe_desktop") / "config_defaults" / filename
    payload = json.loads(resource.read_bytes())
    assert isinstance(payload, dict)
    return payload


_FORBIDDEN_CONNECTIVES = (
    "no",
    "not",
    "never",
    "none",
    "neither",
    "nor",
    "nil",
    "without",
    "denies",
    "deny",
    "denied",
    "left",
    "right",
    "bilateral",
    "bilaterally",
    "patient",
    "pain",
    # Architect correction at Task 0.3: quantifiers and epistemic modals change
    # scope or certainty ("both knees", "some pain", "may have a fracture"), so
    # they are not connectives either — Check 5 must fail them as added content.
    "both",
    "either",
    "all",
    "any",
    "some",
    "each",
    "such",
    "same",
    "other",
    "own",
    "may",
    "might",
    "could",
    "can",
    "must",
)
_FORBIDDEN_ABBREVIATIONS = ("mg", "mcg", "ml", "paracetamol")
_REQUIRED_ABBREVIATIONS = ("HVLA", "Cx", "Tx", "Lx", "ROM", "NAD", "Rx", "Hx")


class TestShippedVocabularies:
    """Both lists are package data read at import: the packaged file and the
    module constant cannot drift apart, and the content rules the checker and
    the shorthand lookup rely on hold on the shipped text itself."""

    def test_the_packaged_abbreviations_parse_to_the_module_constant(self) -> None:
        payload = _packaged_payload(CLINICAL_ABBREVIATIONS_FILENAME)
        assert payload["schema_version"] == 1
        parsed = _parse_shipped_vocabulary(
            payload,
            filename=CLINICAL_ABBREVIATIONS_FILENAME,
            key="abbreviations",
            lower_case=False,
        )
        assert parsed == CLINICAL_ABBREVIATIONS

    def test_the_packaged_connectives_parse_to_the_module_constant(self) -> None:
        payload = _packaged_payload(PROSE_CONNECTIVES_FILENAME)
        assert payload["schema_version"] == 1
        parsed = _parse_shipped_vocabulary(
            payload,
            filename=PROSE_CONNECTIVES_FILENAME,
            key="connectives",
            lower_case=True,
        )
        assert parsed == PROSE_CONNECTIVES

    def test_both_constants_are_non_empty_tuples_of_unique_one_word_strings(self) -> None:
        for vocabulary in (CLINICAL_ABBREVIATIONS, PROSE_CONNECTIVES):
            assert isinstance(vocabulary, tuple)
            assert vocabulary
            assert all(isinstance(entry, str) and entry.strip() for entry in vocabulary)
            assert all(not any(ch.isspace() for ch in entry) for entry in vocabulary)
            assert len(set(vocabulary)) == len(vocabulary)

    def test_the_named_clinical_abbreviations_are_shipped(self) -> None:
        for abbreviation in _REQUIRED_ABBREVIATIONS:
            assert abbreviation in CLINICAL_ABBREVIATIONS

    def test_every_connective_is_lower_case(self) -> None:
        assert all(entry == entry.lower() for entry in PROSE_CONNECTIVES)

    def test_no_polarity_laterality_or_clinical_token_is_a_connective(self) -> None:
        for token in _FORBIDDEN_CONNECTIVES:
            assert token not in PROSE_CONNECTIVES

    def test_an_abbreviation_that_folds_to_a_connective_is_a_broken_install(self) -> None:
        # Phase H round 28 SEC-001: the import-time guard, exercised directly.
        guard = note_config_module._refuse_vocabulary_overlap
        guard(CLINICAL_ABBREVIATIONS, PROSE_CONNECTIVES)  # the shipped pair passes
        with pytest.raises(RuntimeError, match=r"\['as'\].*broken install"):
            guard(("AS", "Cx"), ("a", "as", "the"))
        assert "AS" in CLINICAL_ABBREVIATIONS and "as" not in PROSE_CONNECTIVES

    def test_no_shipped_entry_is_a_number_token(self) -> None:
        for entry in (*PROSE_CONNECTIVES, *CLINICAL_ABBREVIATIONS):
            assert not is_number_token(entry)

    def test_no_dose_unit_or_drug_name_is_a_clinical_abbreviation(self) -> None:
        shipped = {entry.lower() for entry in CLINICAL_ABBREVIATIONS}
        for token in _FORBIDDEN_ABBREVIATIONS:
            assert token not in shipped


# ---------------------------------------------------------------------------
# The clinical register's lexicon (note-content-design plan D1, Task R.1):
# the shipped file and every STRUCTURAL invariant, refused in `note_config`
# at import (the SEMANTIC ones refuse in `note_check` — `test_note_check`).
# ---------------------------------------------------------------------------

_LBP: dict[str, object] = {"term": "LBP", "phrases": ["lower back pain"], "class": "symptom"}


def _equivalents_payload(
    *entries: object,
    exclusions: object = ("sore",),
    ordinary_words: object = ("as",),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "equivalents": list(entries),
        "exclusions": list(exclusions) if isinstance(exclusions, tuple) else exclusions,
        "ordinary_words": (
            list(ordinary_words) if isinstance(ordinary_words, tuple) else ordinary_words
        ),
    }


def _parse_equivalents(payload: object) -> ClinicalRegister:
    return _parse_clinical_equivalents(
        payload,
        filename=CLINICAL_EQUIVALENTS_FILENAME,
        abbreviations=CLINICAL_ABBREVIATIONS,
        connectives=PROSE_CONNECTIVES,
    )


def _entry(term: object, *phrases: object, klass: object = "anatomy") -> dict[str, object]:
    return {"term": term, "phrases": list(phrases), "class": klass}


def _without(key: str) -> dict[str, object]:
    payload = _equivalents_payload(_LBP)
    del payload[key]
    return payload


# Every payload the lexicon's loader must REFUSE: shape, completeness, and
# each structural invariant D1 names.
_BROKEN_EQUIVALENTS_PAYLOADS = [
    pytest.param([], id="not-an-object"),
    pytest.param(_without("exclusions"), id="missing-key"),
    pytest.param({**_equivalents_payload(_LBP), "extra": []}, id="extra-key"),
    pytest.param({**_equivalents_payload(_LBP), "schema_version": 2}, id="schema-2"),
    pytest.param({**_equivalents_payload(_LBP), "schema_version": True}, id="schema-bool"),
    pytest.param(_equivalents_payload(), id="no-entries"),
    pytest.param(_equivalents_payload(_LBP, exclusions=[]), id="empty-exclusions"),
    pytest.param(_equivalents_payload(_LBP, exclusions=("Sore",)), id="exclusion-case"),
    pytest.param(_equivalents_payload(_LBP, exclusions=("sore", "sore")), id="exclusion-dup"),
    pytest.param(_equivalents_payload(_LBP, exclusions=("sore.",)), id="exclusion-punct"),
    pytest.param(_equivalents_payload(_LBP, ordinary_words=("um",)), id="ordinary-filler"),
    pytest.param(_equivalents_payload(_LBP, ordinary_words=[]), id="empty-ordinary"),
    pytest.param(
        _equivalents_payload({"term": "LBP", "phrases": ["lower back pain"]}), id="entry-keys"
    ),
    pytest.param(_equivalents_payload(_entry(1, "lumbar")), id="term-not-string"),
    pytest.param(_equivalents_payload(_entry("Low back", "lumbago")), id="term-two-words"),
    pytest.param(_equivalents_payload(_entry("L\tB", "lumbago")), id="term-control"),
    pytest.param(_equivalents_payload(_entry("LBP.", "lumbago")), id="term-punctuation"),
    pytest.param(_equivalents_payload(_entry("Xq", "lumbago", klass="diagnosis")), id="class"),
    # Round 7 LOW-001: an unhashable class is the same named refusal, never a
    # TypeError from the set lookup.
    pytest.param(_equivalents_payload(_entry("Xq", "lumbago", klass=[])), id="class-list"),
    pytest.param(_equivalents_payload(_entry("Xq", "lumbago", klass={})), id="class-object"),
    pytest.param(_equivalents_payload(_entry("Xq")), id="no-phrases"),
    pytest.param(_equivalents_payload(_entry("Xq", 7)), id="phrase-not-string"),
    pytest.param(
        _equivalents_payload(_entry("Xq", "one two three four five")), id="phrase-five-tokens"
    ),
    pytest.param(_equivalents_payload(_entry("Xq", "Lumbago")), id="phrase-case"),
    pytest.param(_equivalents_payload(_entry("Xq", "low  back")), id="phrase-spacing"),
    pytest.param(_equivalents_payload(_entry("Xq", "low um back")), id="phrase-filler"),
    pytest.param(_equivalents_payload(_entry("Xq", "lumbago", "lumbago")), id="phrase-repeat"),
    pytest.param(_equivalents_payload(_entry("Xq", "about")), id="phrase-connective"),
    pytest.param(_equivalents_payload(_entry("Xq", "pain")), id="phrase-pain"),
    pytest.param(_equivalents_payload(_entry("Xq", "patient")), id="phrase-patient"),
    pytest.param(_equivalents_payload(_entry("The", "lumbago")), id="term-connective"),
    pytest.param(_equivalents_payload(_entry("L", "litre")), id="term-side"),
    pytest.param(_equivalents_payload(_entry("CX", "cervix")), id="term-case-twin"),
    pytest.param(_equivalents_payload(_entry("Xq", "lumbago", klass="duration")), id="dur-term"),
    pytest.param(
        _equivalents_payload(_entry("3/52", "3 weeks", klass="measure")), id="week-not-duration"
    ),
    pytest.param(
        _equivalents_payload(_entry("13/52", "13 weeks", klass="duration")), id="beyond-twelve"
    ),
    pytest.param(
        _equivalents_payload(_entry("3/52", "three weeks", "3 weeks", klass="duration")),
        id="duration-word-first",
    ),
    pytest.param(
        _equivalents_payload(_entry("1/52", "1 weeks", klass="duration")), id="duration-unit"
    ),
    pytest.param(
        _equivalents_payload(_entry("3/52", "3 weeks", "3 wks", klass="duration")),
        id="duration-phrase-unit",
    ),
    pytest.param(
        _equivalents_payload(_LBP, _entry("Xq", "lower back pain")), id="phrase-in-two-entries"
    ),
    pytest.param(
        _equivalents_payload(_entry("patella", "kneecap"), _entry("Patella", "knee cap")),
        id="term-in-two-entries",
    ),
    # Codex round 8 PR-LOW-015: the SAME term, exactly as spelled, in two
    # entries — repeated whole, or defined a second time.
    pytest.param(_equivalents_payload(_LBP, _LBP), id="term-repeated-identical"),
    pytest.param(
        _equivalents_payload(_LBP, _entry("LBP", "lumbar pain", klass="symptom")),
        id="term-repeated-conflicting",
    ),
    pytest.param(
        _equivalents_payload(_entry("Lx", "lumbar"), _entry("lumbar", "lumbar region")),
        id="phrase-is-another-term",
    ),
    pytest.param(
        _equivalents_payload(_LBP, _entry("Xq", "lower back")), id="phrase-prefix-of-another"
    ),
]


@pytest.mark.parametrize("payload", _BROKEN_EQUIVALENTS_PAYLOADS)
def test_a_broken_packaged_lexicon_is_refused_at_import(payload: object) -> None:
    with pytest.raises(RuntimeError, match="broken install"):
        _parse_equivalents(payload)


# Codex round 8 PR-LOW-016: the decode step, over raw bytes — `json` alone
# keeps the LAST of two equal keys, so a repeated key is refused before the
# shape is checked, at an entry and at the top level alike.
_GOOD_ENTRY = '{"term": "LBP", "phrases": ["lower back pain"], "class": "symptom"}'
_GOOD_REST = '"exclusions": ["sore"], "ordinary_words": ["as"]'


class TestTheLexiconDecode:
    def test_a_well_formed_file_decodes_and_parses(self) -> None:
        raw = f'{{"schema_version": 1, "equivalents": [{_GOOD_ENTRY}], {_GOOD_REST}}}'
        register = _parse_equivalents(_decode_clinical_equivalents(raw.encode()))
        assert [entry.term for entry in register.entries] == ["LBP"]

    def test_the_packaged_file_decodes_to_the_module_constant(self) -> None:
        resource = resources.files("scribe_desktop") / "config_defaults"
        data = (resource / CLINICAL_EQUIVALENTS_FILENAME).read_bytes()
        assert _parse_equivalents(_decode_clinical_equivalents(data)) == CLINICAL_EQUIVALENTS

    @pytest.mark.parametrize(
        "raw",
        [
            # An entry's key repeated — the unhashable class hidden behind a good one.
            '{"schema_version": 1, "equivalents": [{"term": "LBP", "phrases": '
            '["lower back pain"], "class": [], "class": "symptom"}], ' + _GOOD_REST + "}",
            # A top-level key repeated.
            '{"schema_version": 2, "schema_version": 1, "equivalents": ['
            + _GOOD_ENTRY + "], " + _GOOD_REST + "}",
        ],
        ids=["entry-key", "top-level-key"],
    )
    def test_a_repeated_key_is_refused(self, raw: str) -> None:
        assert json.loads(raw) is not None  # plain `json` accepts it silently
        with pytest.raises(RuntimeError, match="broken install.*repeated"):
            _decode_clinical_equivalents(raw.encode())

    def test_undecodable_bytes_and_deep_nesting_are_the_named_refusal(self) -> None:
        with pytest.raises(RuntimeError, match="broken install"):
            _decode_clinical_equivalents(b"\x80 not json")
        # Too deep for the decoder: its RecursionError is named, not raw.
        with pytest.raises(RuntimeError, match="broken install"):
            _decode_clinical_equivalents(b"[" * 1_000_000)


class TestShippedClinicalEquivalents:
    """The lexicon is package data read at import (Task 0.1's ratified
    content); the packaged file and the module constant cannot drift."""

    def test_the_packaged_lexicon_parses_to_the_module_constant(self) -> None:
        payload = _packaged_payload(CLINICAL_EQUIVALENTS_FILENAME)
        assert payload["schema_version"] == 1
        assert _parse_equivalents(payload) == CLINICAL_EQUIVALENTS

    def test_the_ratified_counts(self) -> None:
        entries = CLINICAL_EQUIVALENTS.entries
        assert len(entries) == 93
        by_class: dict[str, int] = {}
        for entry in entries:
            by_class[entry.equivalence_class] = by_class.get(entry.equivalence_class, 0) + 1
        assert by_class == {
            "anatomy": 49, "symptom": 4, "measure": 27, "side_neutral": 1, "duration": 12,
        }
        assert sum(len(entry.phrases) for entry in entries) == 138
        assert len(CLINICAL_EQUIVALENTS.exclusions) == 23
        assert len(CLINICAL_EQUIVALENTS.ordinary_words) == 86

    def test_terms_keep_their_display_case(self) -> None:
        terms = {entry.term for entry in CLINICAL_EQUIVALENTS.entries}
        assert {"LBP", "Cx", "TrA", "B/L", "C/O", "3/52", "patella"} <= terms
        lookup = CLINICAL_EQUIVALENTS.lookup
        assert lookup[("lbp",)].term == "LBP"
        assert lookup[("lower", "back", "pain")].term == "LBP"
        assert CLINICAL_EQUIVALENTS.longest == 4

    def test_a_week_is_not_a_duration_phrase(self) -> None:
        # "three times a week" must never fold into 1/52.
        assert ("a", "week") not in CLINICAL_EQUIVALENTS.lookup

    def test_the_pain_and_patient_pins_hold_for_one_word_phrases(self) -> None:
        for entry in CLINICAL_EQUIVALENTS.entries:
            for phrase in entry.phrases:
                if len(phrase) == 1:
                    assert phrase[0] not in {"pain", "patient", *PROSE_CONNECTIVES}

    def test_a_minimal_good_payload_parses(self) -> None:
        register = _parse_equivalents(
            _equivalents_payload(_LBP, _entry("3/52", "3 weeks", "three weeks", klass="duration"))
        )
        assert [entry.term for entry in register.entries] == ["LBP", "3/52"]
        assert register.entries[1].phrases == (("3", "weeks"), ("three", "weeks"))
        assert set(register.lookup) == {
            ("lbp",), ("lower", "back", "pain"), ("3/52",), ("3", "weeks"), ("three", "weeks"),
        }
        assert register.longest == 3
        assert register.exclusions == frozenset({"sore"})
        assert register.ordinary_words == frozenset({"as"})


# ---------------------------------------------------------------------------
# The practitioner settings file (D7).
# ---------------------------------------------------------------------------

_NOTE_STYLES = ("verbatim", "clean", "own_voice", "narrative")


class TestPractitionerSettings:
    """A fifth config file that is NOT part of ``NoteConfig``: absent means
    the defaults, and a hand-edited file fails loudly rather than parsing as
    a style the practitioner did not choose."""

    def test_the_defaults_are_schema_one_and_the_clean_style(self) -> None:
        settings = PractitionerSettings()
        assert settings.schema_version == 1
        assert settings.note_style == "clean"
        assert settings.note_style == DEFAULT_NOTE_STYLE

    def test_an_absent_file_loads_as_the_defaults_and_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        assert load_practitioner_settings(root) == PractitionerSettings()
        assert not root.exists()

    @pytest.mark.parametrize("style", _NOTE_STYLES)
    def test_each_style_round_trips_through_the_file(self, tmp_path: Path, style: str) -> None:
        root = tmp_path / "config"
        settings = PractitionerSettings.model_validate({"note_style": style})
        path = save_practitioner_settings(settings, config_root=root)
        assert path == root / PRACTITIONER_SETTINGS_FILENAME
        assert load_practitioner_settings(root).note_style == style

    def test_the_written_file_carries_exactly_the_two_keys(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        path = save_practitioner_settings(PractitionerSettings(), config_root=root)
        payload = json.loads(path.read_bytes())
        assert set(payload) == {"schema_version", "note_style"}
        assert payload == {"schema_version": 1, "note_style": "clean"}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param({"note_style": "heidi"}, id="unknown-style"),
            pytest.param({"schema_version": 2, "note_style": "clean"}, id="unknown-version"),
            pytest.param({"note_style": "clean", "extra": 1}, id="extra-key"),
        ],
    )
    def test_an_invalid_settings_file_is_refused(
        self, tmp_path: Path, data: dict[str, object]
    ) -> None:
        with pytest.raises(ValidationError):
            PractitionerSettings.model_validate(data)
        root = tmp_path / "config"
        root.mkdir()
        (root / PRACTITIONER_SETTINGS_FILENAME).write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(
            NoteConfigInvalidError, match=re.escape(PRACTITIONER_SETTINGS_FILENAME)
        ):
            load_practitioner_settings(root)

    def test_a_malformed_settings_file_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "config"
        root.mkdir()
        (root / PRACTITIONER_SETTINGS_FILENAME).write_text("not json {", encoding="utf-8")
        with pytest.raises(
            NoteConfigInvalidError, match=re.escape(PRACTITIONER_SETTINGS_FILENAME)
        ):
            load_practitioner_settings(root)

    def test_an_unreadable_settings_file_is_typed_not_defaulted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "config"
        root.mkdir()
        (root / PRACTITIONER_SETTINGS_FILENAME).write_bytes(PractitionerSettings().to_bytes())
        real_read_bytes = Path.read_bytes

        def fake_read_bytes(self: Path) -> bytes:
            if self.name == PRACTITIONER_SETTINGS_FILENAME:
                raise OSError(13, "locked")
            return real_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        with pytest.raises(NoteConfigUnreadableError, match="unreadable"):
            load_practitioner_settings(root)

    def test_a_failed_write_is_typed_and_leaves_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail(*args: object, **kwargs: object) -> None:
            raise StoreWriteError("disk full")

        monkeypatch.setattr(note_config_module, "atomic_write_bytes", fail)
        root = tmp_path / "config"
        with pytest.raises(NoteConfigWriteError, match="disk full"):
            save_practitioner_settings(PractitionerSettings(), config_root=root)
        assert not (root / PRACTITIONER_SETTINGS_FILENAME).exists()
