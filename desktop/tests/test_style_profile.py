"""Note-learning-and-styles plan Phase 0 Task 0.3: the learned-style store.

The ``StyleProfile`` model (``note_config``, beside the other clinician-config
shapes), its DPAPI custody in ``practitioner_profile`` (its OWN root, key
description and AAD; the voice profile's custody ordering, shared code), the
THREE-key isolation the task's Done-when names (session, voice and style keys
cannot open each other's store), key-first deletion INDEPENDENT of the voice
profile (D9), the ``StyleProfile`` arm of ``ui.models.consent_is_current``,
and the log tripwire's ``exemplar_text`` marker.
"""

from __future__ import annotations

import json
import sys
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop import practitioner_profile as pp
from scribe_desktop.logging_setup import _PAYLOAD_SIGNATURES
from scribe_desktop.note_config import (
    MAX_SAMPLE_NOTES,
    MAX_STYLE_EXEMPLARS,
    StyleExemplar,
    StyleMeasures,
    StyleProfile,
)
from scribe_desktop.practitioner_profile import (
    PROFILE_AAD,
    PROFILE_BLOB_FILENAME,
    PROFILE_KEY_DESCRIPTION,
    STYLE_AAD,
    STYLE_BLOB_FILENAME,
    STYLE_KEY_DESCRIPTION,
    ConsentRecord,
    PractitionerProfile,
    ProfileUnusableError,
    default_profile_root,
    default_style_root,
    delete_profile,
    delete_style_profile,
    load_profile,
    load_style_profile,
    save_profile,
    save_style_profile,
    style_profile_present,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    KEY_FILENAME,
    KeyCustodyError,
    StoreWriteError,
    unwrap_key_from_file,
    wrap_key_to_file,
)
from scribe_desktop.ui import models

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

NOW = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)
EXEMPLAR = "HVLA applied to the cervical spine with good release."


def _consent(**over: Any) -> ConsentRecord:
    fields: dict[str, Any] = {
        "accepted_at": NOW,
        "consent_text_version": models.CONSENT_TEXT_VERSION,
        "learning_opt_in": True,
    }
    fields.update(over)
    return ConsentRecord(**fields)


def _measures(**over: Any) -> StyleMeasures:
    fields: dict[str, Any] = {
        "mean_sentence_words": 11.5,
        "abbreviation_ratio": 0.2,
        "person": "third",
        "tense": "past",
    }
    fields.update(over)
    return StyleMeasures(**fields)


def _exemplar(text: str = EXEMPLAR, section: str = "treatment_performed") -> StyleExemplar:
    return StyleExemplar(section_key=section, exemplar_text=text)  # type: ignore[arg-type]


def _style(**over: Any) -> StyleProfile:
    fields: dict[str, Any] = {
        "learned_at": NOW,
        "consent": _consent(),
        "section_order": ("presenting_complaint", "objective_examination", "assessment"),
        "heading_labels": {"presenting_complaint": "C/O", "assessment": "Assessment"},
        "shorthand": ("HVLA", "Cx"),
        "measures": _measures(),
        "exemplars": (_exemplar(),),
        "source_count": 3,
    }
    fields.update(over)
    return StyleProfile(**fields)


def _voice(**over: Any) -> PractitionerProfile:
    fields: dict[str, Any] = {
        "model_id": "mock-speaker-embedder-v1",
        "model_sha256": "",
        "embedding": (0.6, 0.8),
        "embedding_dim": 2,
        "created_at": NOW,
        "enrolment_speech_seconds": 31.5,
        "device_name": "Mock Microphone",
        "consent": _consent(),
    }
    fields.update(over)
    return PractitionerProfile(**fields)


# --- the model -----------------------------------------------------------------


class TestStyleModel:
    def test_round_trips_through_bytes(self) -> None:
        profile = _style()
        assert StyleProfile.from_bytes(profile.to_bytes()) == profile
        assert profile.schema_version == 1
        with pytest.raises(ValidationError):
            _style(schema_version=2)
        with pytest.raises(ValidationError):
            _style(surprise=True)

    def test_empty_lists_are_legal_and_bounded(self) -> None:
        bare = _style(section_order=(), heading_labels={}, shorthand=(), exemplars=())
        assert bare.exemplars == () and bare.shorthand == ()
        assert MAX_STYLE_EXEMPLARS == 30 and MAX_SAMPLE_NOTES == 5
        too_many = tuple(_exemplar(f"{EXEMPLAR} {n}") for n in range(MAX_STYLE_EXEMPLARS + 1))
        with pytest.raises(ValidationError):
            _style(exemplars=too_many)
        assert len(_style(exemplars=too_many[:MAX_STYLE_EXEMPLARS]).exemplars) == 30
        for count in (0, MAX_SAMPLE_NOTES + 1):
            with pytest.raises(ValidationError):
                _style(source_count=count)

    def test_learned_at_must_be_aware(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            _style(learned_at=datetime(2026, 9, 19, 8, 0))

    def test_sections_and_headings_are_shaped(self) -> None:
        with pytest.raises(ValidationError, match="repeat a section"):
            _style(section_order=("assessment", "assessment"))
        with pytest.raises(ValidationError):
            _style(section_order=("soap_subjective",))
        with pytest.raises(ValidationError):
            _style(heading_labels={"soap_subjective": "S"})
        with pytest.raises(ValidationError, match="blank"):
            _style(heading_labels={"assessment": "  "})
        with pytest.raises(ValidationError, match="control character"):
            _style(heading_labels={"assessment": "A\tB"})
        with pytest.raises(ValidationError):
            _style(heading_labels={"assessment": "x" * 121})

    def test_shorthand_tokens_are_single_words(self) -> None:
        with pytest.raises(ValidationError, match="one word"):
            _style(shorthand=("neck pain",))
        with pytest.raises(ValidationError):
            _style(shorthand=("",))
        with pytest.raises(ValidationError, match="repeat a token"):
            _style(shorthand=("HVLA", "HVLA"))
        with pytest.raises(ValidationError):
            _style(shorthand=("x" * 33,))
        with pytest.raises(ValidationError, match="control character"):
            _style(shorthand=("H\x00VLA",))
        with pytest.raises(ValidationError):
            _style(shorthand=tuple(f"t{n}" for n in range(501)))

    def test_exemplars_are_single_line_text(self) -> None:
        with pytest.raises(ValidationError, match="control character"):
            _exemplar("line one\nline two")
        with pytest.raises(ValidationError, match="blank"):
            _exemplar("   ")
        with pytest.raises(ValidationError):
            _exemplar("x" * 1_001)
        with pytest.raises(ValidationError):
            _exemplar(EXEMPLAR, section="not_a_section")

    def test_measures_are_finite_and_bounded(self) -> None:
        for bad in ({"mean_sentence_words": float("nan")}, {"mean_sentence_words": float("inf")}):
            with pytest.raises(ValidationError):
                _measures(**bad)
        with pytest.raises(ValidationError):
            _measures(abbreviation_ratio=1.5)
        with pytest.raises(ValidationError):
            _measures(mean_sentence_words=-1.0)
        with pytest.raises(ValidationError):
            _measures(person="second")
        with pytest.raises(ValidationError):
            _measures(tense="future")

    def test_validation_errors_hide_the_input(self) -> None:
        """The exemplars are sentences from the practitioner's own notes: a
        rendered validation error must carry structure only."""
        with pytest.raises(ValidationError) as exc:
            _exemplar("Zebra-secret\tsentence")
        assert "Zebra-secret" not in str(exc.value)
        with pytest.raises(ValidationError) as outer:
            StyleProfile.model_validate(
                {
                    **_style().model_dump(mode="json"),
                    "exemplars": [{"section_key": "assessment", "exemplar_text": "Zebra\tsecret"}],
                }
            )
        assert "Zebra" not in str(outer.value)

    def test_exemplar_text_is_a_tripwire_marker(self) -> None:
        """A bare exemplar's every rendering carries a registered signature,
        so the last-line log filter drops it (the whole profile already
        carries ``consent_text_version``)."""
        assert '"exemplar_text"' in _PAYLOAD_SIGNATURES
        exemplar = _exemplar()
        for rendering in (repr(exemplar), str(exemplar.model_dump()), exemplar.model_dump_json()):
            assert any(sig in rendering for sig in _PAYLOAD_SIGNATURES), rendering
        profile = _style()
        for rendering in (repr(profile), str(profile.model_dump()), profile.model_dump_json()):
            assert any(sig in rendering for sig in _PAYLOAD_SIGNATURES), rendering


class TestMalformedLocationRendering:
    """The renderer itself, DPAPI-free (codex PR-MED-016): declared field
    names, integer indices and pydantic's ``[key]`` marker pass; anything
    else — a mapping key, an unknown field — is the placeholder."""

    def _error(self, payload: dict[str, Any]) -> ValidationError:
        with pytest.raises(ValidationError) as exc:
            StyleProfile.model_validate(payload)
        return exc.value

    def test_declared_names_reach_nested_models(self) -> None:
        declared = pp._declared_field_names(StyleProfile)
        for name in ("heading_labels", "consent", "consent_text_version", "exemplars",
                     "exemplar_text", "measures", "mean_sentence_words"):
            assert name in declared
        assert "Zebra" not in declared

    def test_a_mapping_key_and_unknown_fields_render_as_the_placeholder(self) -> None:
        payload = _style().model_dump(mode="json")
        payload["heading_labels"]["Zebra-key"] = "x"
        payload["Zebra-field"] = 1
        payload["exemplars"] = [{"section_key": "assessment", "exemplar_text": "Zebra\tvalue"}]
        error = pp._malformed(pp._STYLE_STORE, StyleProfile, self._error(payload))
        message = str(error)
        assert "Zebra" not in message
        assert "heading_labels.<field>.[key]" in message
        assert "exemplars.0.exemplar_text" in message  # declared names still name the site
        assert message.startswith("learned style unusable (malformed): style.enc is not a valid")
        assert error.reason == "malformed"

    def test_the_voice_model_renders_the_same_way(self) -> None:
        payload = _voice().model_dump(mode="json")
        payload["Zebra-field"] = 1
        payload["consent"]["Zebra-nested"] = True
        with pytest.raises(ValidationError) as exc:
            PractitionerProfile.model_validate(payload)
        error = pp._malformed(pp._VOICE_STORE, PractitionerProfile, exc.value)
        assert "Zebra" not in str(error)
        assert "<field>" in str(error) and "consent.<field>" in str(error)
        assert str(error).startswith("practitioner profile unusable (malformed): voice.enc")


class TestConsentArm:
    def test_consent_is_current_reads_the_style_profile(self) -> None:
        """D9: the style store's own record is what makes sample learning
        consented with no voice profile; an older version re-asks."""
        assert models.consent_is_current(_style()) is True
        stale = _style(consent=_consent(consent_text_version="consent-v2"))
        assert models.consent_is_current(stale) is False


# --- custody ------------------------------------------------------------------


def test_the_style_root_is_a_sibling_of_the_profile_root() -> None:
    """D9: never a second artefact under ``profile\\`` — the voice key must
    not be the key that opens the learned style."""
    assert default_style_root().name == "style"
    assert default_style_root().parent == default_profile_root().parent
    assert default_style_root() != default_profile_root()
    assert STYLE_KEY_DESCRIPTION != PROFILE_KEY_DESCRIPTION
    assert STYLE_AAD != PROFILE_AAD
    assert STYLE_BLOB_FILENAME != PROFILE_BLOB_FILENAME


@windows_only
class TestStyleCustody:
    def test_save_load_round_trip_and_presence(self, tmp_path: Path) -> None:
        root = tmp_path / "style"
        assert load_style_profile(root=root) is None
        assert not style_profile_present(root=root)
        profile = _style()
        blob_path = save_style_profile(profile, root=root)
        assert blob_path == root / STYLE_BLOB_FILENAME
        assert sorted(p.name for p in root.iterdir()) == [KEY_FILENAME, STYLE_BLOB_FILENAME]
        sealed = blob_path.read_bytes()
        assert b"exemplar_text" not in sealed and EXEMPLAR.encode() not in sealed
        assert load_style_profile(root=root) == profile
        assert style_profile_present(root=root)

    def test_re_save_keeps_the_key_and_replaces_only_the_blob(self, tmp_path: Path) -> None:
        root = tmp_path / "style"
        save_style_profile(_style(), root=root)
        key_before = (root / KEY_FILENAME).read_bytes()
        blob_before = (root / STYLE_BLOB_FILENAME).read_bytes()
        second = _style(shorthand=("HVLA", "Cx", "Lx"), source_count=4)
        save_style_profile(second, root=root)
        assert (root / KEY_FILENAME).read_bytes() == key_before
        assert (root / STYLE_BLOB_FILENAME).read_bytes() != blob_before
        assert load_style_profile(root=root) == second

    def test_delete_is_key_first_idempotent_and_typed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "style"
        save_style_profile(_style(), root=root)
        order: list[str] = []
        real_unlink = Path.unlink

        def _record(self: Path, missing_ok: bool = False) -> None:
            order.append(self.name)
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", _record)
        delete_style_profile(root=root)
        monkeypatch.undo()
        assert order == [KEY_FILENAME, STYLE_BLOB_FILENAME]
        assert list(root.iterdir()) == []
        assert load_style_profile(root=root) is None
        delete_style_profile(root=root)  # idempotent

        save_style_profile(_style(), root=root)

        def _refuse(self: Path, missing_ok: bool = False) -> None:
            raise OSError(13, "locked")

        monkeypatch.setattr(Path, "unlink", _refuse)
        with pytest.raises(StoreWriteError, match="style key"):
            delete_style_profile(root=root)

    def test_failed_blob_write_on_re_save_leaves_the_old_style_usable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "style"
        first = _style()
        save_style_profile(first, root=root)
        key_before = (root / KEY_FILENAME).read_bytes()

        def _fail(path: Path, blob: bytes, *, error_label: str) -> None:
            raise StoreWriteError(f"failed writing {error_label}: disk full")

        monkeypatch.setattr(pp, "atomic_write_bytes", _fail)
        with pytest.raises(StoreWriteError, match="learned style"):
            save_style_profile(_style(source_count=5), root=root)
        monkeypatch.undo()
        assert (root / KEY_FILENAME).read_bytes() == key_before
        assert load_style_profile(root=root) == first

    def test_failed_key_write_on_first_save_leaves_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "style"

        def _fail(crypto: SessionCrypto, session_dir: Path, *, description: str) -> Path:
            raise StoreWriteError("failed writing key custody blob: disk full")

        monkeypatch.setattr(pp, "wrap_key_to_file", _fail)
        with pytest.raises(StoreWriteError, match="key custody"):
            save_style_profile(_style(), root=root)
        assert list(root.iterdir()) == []
        assert load_style_profile(root=root) is None

    def test_unusable_existing_key_refuses_the_save_and_touches_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "style"
        save_style_profile(_style(), root=root)
        blob_before = (root / STYLE_BLOB_FILENAME).read_bytes()
        (root / KEY_FILENAME).write_bytes(b"\xff" * 64)
        with pytest.raises(ProfileUnusableError, match=r"learned style unusable \(key\)") as exc:
            save_style_profile(_style(source_count=2), root=root)
        assert exc.value.reason == "key" and exc.value.store == "learned style"
        assert "learning again" in str(exc.value)
        assert (root / STYLE_BLOB_FILENAME).read_bytes() == blob_before

    def test_keys_are_destroyed_on_the_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "style"
        wrapped: list[SessionCrypto] = []
        unwrapped: list[SessionCrypto] = []
        real_wrap = pp.wrap_key_to_file
        real_unwrap = pp.unwrap_key_from_file

        def _spy_wrap(crypto: SessionCrypto, session_dir: Path, *, description: str) -> Path:
            wrapped.append(crypto)
            return real_wrap(crypto, session_dir, description=description)

        def _spy_unwrap(session_dir: Path, *, description: str) -> SessionCrypto:
            crypto = real_unwrap(session_dir, description=description)
            unwrapped.append(crypto)
            return crypto

        monkeypatch.setattr(pp, "wrap_key_to_file", _spy_wrap)
        monkeypatch.setattr(pp, "unwrap_key_from_file", _spy_unwrap)
        save_style_profile(_style(), root=root)
        assert load_style_profile(root=root) is not None
        assert len(wrapped) == 1 and wrapped[0].destroyed
        assert unwrapped and all(c.destroyed for c in unwrapped)


@windows_only
class TestStyleUnusableStates:
    def _saved(self, tmp_path: Path) -> Path:
        root = tmp_path / "style"
        save_style_profile(_style(), root=root)
        return root

    def _reason(self, root: Path) -> str:
        with pytest.raises(ProfileUnusableError) as exc:
            load_style_profile(root=root)
        assert exc.value.store == "learned style"
        assert str(exc.value).startswith("learned style unusable (")
        return exc.value.reason

    def test_blob_without_key_and_dead_key_are_unusable_key(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        (root / KEY_FILENAME).unlink()
        assert self._reason(root) == "key"
        (root / KEY_FILENAME).write_bytes(b"")
        assert self._reason(root) == "key"

    def test_truncated_and_tampered_blobs_fail_authentication(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        blob = root / STYLE_BLOB_FILENAME
        good = blob.read_bytes()
        blob.write_bytes(good[:-1])
        assert self._reason(root) == "authentication"
        data = bytearray(good)
        data[20] ^= 0x01
        blob.write_bytes(bytes(data))
        assert self._reason(root) == "authentication"

    def test_the_voice_aad_fails_under_the_style_key(self, tmp_path: Path) -> None:
        """Even the RIGHT key refuses a blob of another purpose: the AAD is
        the second wall between the stores."""
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=STYLE_KEY_DESCRIPTION)
        (root / STYLE_BLOB_FILENAME).write_bytes(crypto.encrypt(_style().to_bytes(), PROFILE_AAD))
        assert self._reason(root) == "authentication"

    def test_authentic_but_invalid_content_is_malformed_and_unchained(
        self, tmp_path: Path
    ) -> None:
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=STYLE_KEY_DESCRIPTION)
        payload = _style().model_dump(mode="json")
        payload["exemplars"] = [{"section_key": "assessment", "exemplar_text": "Zebra\tsecret"}]
        (root / STYLE_BLOB_FILENAME).write_bytes(
            crypto.encrypt(json.dumps(payload).encode(), STYLE_AAD)
        )
        with pytest.raises(ProfileUnusableError) as exc:
            load_style_profile(root=root)
        assert exc.value.reason == "malformed"
        assert "style.enc is not a valid style" in str(exc.value)
        assert "exemplars" in str(exc.value) and "Zebra" not in str(exc.value)
        assert exc.value.__cause__ is None and exc.value.__suppress_context__

    def test_unreadable_blob_is_unusable_blob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._saved(tmp_path)
        real_read = Path.read_bytes

        def _refuse(self: Path) -> bytes:
            if self.name == STYLE_BLOB_FILENAME:
                raise OSError(13, "locked")
            return real_read(self)

        monkeypatch.setattr(Path, "read_bytes", _refuse)
        assert self._reason(root) == "blob"

    @pytest.mark.parametrize(
        ("mutate", "expected_location"),
        [
            pytest.param(
                lambda payload: payload["heading_labels"].update({"Zebra-secret patient": "C/O"}),
                "heading_labels.<field>.[key]",
                id="mapping-key",
            ),
            pytest.param(
                lambda payload: payload.update({"Zebra-secret": 1}),
                "<field>",
                id="unknown-top-level-field",
            ),
            pytest.param(
                lambda payload: payload["consent"].update({"Zebra-secret": True}),
                "consent.<field>",
                id="unknown-nested-field",
            ),
        ],
    )
    def test_a_malformed_blob_renders_no_key_or_unknown_field_name(
        self, tmp_path: Path, mutate: Callable[[dict[str, Any]], None], expected_location: str
    ) -> None:
        """Codex PR-MED-016: a validation LOCATION is not input-free — a
        mapping key and an unknown field name reach ``error["loc"]`` and
        ``hide_input_in_errors`` hides values only — so the loader renders
        locations through the model's declared field names: no string outside
        that vocabulary, the ``[key]`` marker and the placeholder reaches the
        message, the traceback or the chain. The sentinels here are
        non-declared names; a key spelled like a declared field renders as
        that field name (codex PR-LOW-019 — a vocabulary bound, not a
        positional one)."""
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=STYLE_KEY_DESCRIPTION)
        payload = _style().model_dump(mode="json")
        mutate(payload)
        (root / STYLE_BLOB_FILENAME).write_bytes(
            crypto.encrypt(json.dumps(payload).encode(), STYLE_AAD)
        )
        with pytest.raises(ProfileUnusableError) as exc:
            load_style_profile(root=root)
        assert exc.value.reason == "malformed"
        assert exc.value.store == "learned style"
        assert expected_location in str(exc.value)
        rendered = "".join(traceback.format_exception(exc.value))
        assert "Zebra" not in str(exc.value)
        assert "Zebra" not in rendered
        assert exc.value.__cause__ is None and exc.value.__suppress_context__


@windows_only
class TestThreeKeyIsolation:
    """The task's Done-when: the SESSION, VOICE and STYLE keys cannot open
    each other's store. The DPAPI description is verified before any
    decryption, so a key blob of another store fails typed ("different
    store"), and each loader reports it as ``key``."""

    def _style_blob_under(self, root: Path, crypto: SessionCrypto) -> None:
        (root / STYLE_BLOB_FILENAME).write_bytes(crypto.encrypt(_style().to_bytes(), STYLE_AAD))

    def test_a_session_key_cannot_open_the_style_store(self, tmp_path: Path) -> None:
        root = tmp_path / "style"
        root.mkdir()
        session_crypto = SessionCrypto()
        wrap_key_to_file(session_crypto, root)  # the SESSION description
        self._style_blob_under(root, session_crypto)
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root, description=STYLE_KEY_DESCRIPTION)
        with pytest.raises(ProfileUnusableError) as exc:
            load_style_profile(root=root)
        assert exc.value.reason == "key"

    def test_a_voice_key_cannot_open_the_style_store(self, tmp_path: Path) -> None:
        root = tmp_path / "style"
        root.mkdir()
        voice_crypto = SessionCrypto()
        wrap_key_to_file(voice_crypto, root, description=PROFILE_KEY_DESCRIPTION)
        self._style_blob_under(root, voice_crypto)
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root, description=STYLE_KEY_DESCRIPTION)
        with pytest.raises(ProfileUnusableError) as exc:
            load_style_profile(root=root)
        assert exc.value.reason == "key"

    def test_a_style_key_opens_neither_the_voice_nor_a_session_store(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "profile"
        root.mkdir()
        style_crypto = SessionCrypto()
        wrap_key_to_file(style_crypto, root, description=STYLE_KEY_DESCRIPTION)
        (root / PROFILE_BLOB_FILENAME).write_bytes(
            style_crypto.encrypt(_voice().to_bytes(), PROFILE_AAD)
        )
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root, description=PROFILE_KEY_DESCRIPTION)
        with pytest.raises(ProfileUnusableError) as exc:
            load_profile(root=root)
        assert exc.value.reason == "key"
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root)  # the SESSION description

    def test_the_two_practitioner_stores_are_deleted_independently(self, tmp_path: Path) -> None:
        """D9 / codex PR-MED-009: deleting the learned style leaves the voice
        profile exactly as it was, and vice versa."""
        profile_root = tmp_path / "profile"
        style_root = tmp_path / "style"
        voice = _voice()
        style = _style()
        save_profile(voice, root=profile_root)
        save_style_profile(style, root=style_root)
        voice_files = {p.name: p.read_bytes() for p in profile_root.iterdir()}

        delete_style_profile(root=style_root)
        assert list(style_root.iterdir()) == []
        assert {p.name: p.read_bytes() for p in profile_root.iterdir()} == voice_files
        assert load_profile(root=profile_root) == voice

        save_style_profile(style, root=style_root)
        style_files = {p.name: p.read_bytes() for p in style_root.iterdir()}
        delete_profile(root=profile_root)
        assert list(profile_root.iterdir()) == []
        assert {p.name: p.read_bytes() for p in style_root.iterdir()} == style_files
        assert load_style_profile(root=style_root) == style
