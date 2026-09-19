"""Note-learning-and-styles plan Phase 0 Task 0.3: the two shipped
vocabularies and the practitioner settings file."""

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
    DEFAULT_NOTE_STYLE,
    PRACTITIONER_SETTINGS_FILENAME,
    PROSE_CONNECTIVES,
    PROSE_CONNECTIVES_FILENAME,
    NoteConfigInvalidError,
    NoteConfigUnreadableError,
    NoteConfigWriteError,
    PractitionerSettings,
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

    def test_no_shipped_entry_is_a_number_token(self) -> None:
        for entry in (*PROSE_CONNECTIVES, *CLINICAL_ABBREVIATIONS):
            assert not is_number_token(entry)

    def test_no_dose_unit_or_drug_name_is_a_clinical_abbreviation(self) -> None:
        shipped = {entry.lower() for entry in CLINICAL_ABBREVIATIONS}
        for token in _FORBIDDEN_ABBREVIATIONS:
            assert token not in shipped


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
