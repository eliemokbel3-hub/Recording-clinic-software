"""Practitioner-profile plan Phase 1 Task 1.2: ``practitioner_profile``.

The model (shape, finiteness, dimension agreement, aware timestamps, the
frozen/extra-forbid boundary), the log tripwire's profile markers, and — on
Windows, through the real DPAPI helpers — custody: round-trip, key-first
deletion, re-enrolment under the existing key with only ``voice.enc``
replaced, fault injection around every step of a save, and every unusable
state ``load_profile`` names (key, blob, authentication, malformed, model).
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from scribe_desktop import practitioner_profile as pp
from scribe_desktop.logging_setup import (
    _PAYLOAD_SIGNATURES,
    ALLOWED_KEYS,
    PayloadTripwireFilter,
    dropped_record_count,
)
from scribe_desktop.practitioner_profile import (
    PROFILE_AAD,
    PROFILE_BLOB_FILENAME,
    PROFILE_KEY_DESCRIPTION,
    ConsentRecord,
    PractitionerProfile,
    ProfileUnusableError,
    default_profile_root,
    delete_profile,
    load_profile,
    profile_present,
    save_profile,
)
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session_store import (
    KEY_FILENAME,
    KeyCustodyError,
    StoreWriteError,
    unwrap_key_from_file,
    wrap_key_to_file,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")

NOW = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


def _consent(**over: Any) -> ConsentRecord:
    fields: dict[str, Any] = {
        "accepted_at": NOW,
        "consent_text_version": "consent-v1",
        "learning_opt_in": False,
    }
    fields.update(over)
    return ConsentRecord(**fields)


def _profile(**over: Any) -> PractitionerProfile:
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


class TestModel:
    def test_round_trips_through_bytes(self) -> None:
        profile = _profile(model_sha256="a" * 64, embedding=(0.1, -0.2, 0.3), embedding_dim=3)
        assert PractitionerProfile.from_bytes(profile.to_bytes()) == profile
        assert profile.schema_version == 1

    def test_dimension_must_agree(self) -> None:
        with pytest.raises(ValidationError, match="embedding_dim"):
            _profile(embedding=(0.6, 0.8, 0.0), embedding_dim=2)
        with pytest.raises(ValidationError):
            _profile(embedding=(1.0,), embedding_dim=1)

    def test_embedding_must_be_finite_and_non_zero(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            _profile(embedding=(float("nan"), 1.0))
        with pytest.raises(ValidationError, match="finite"):
            _profile(embedding=(float("inf"), 1.0))
        with pytest.raises(ValidationError, match="zero vector"):
            _profile(embedding=(0.0, 0.0))

    def test_timestamps_must_be_aware(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            _profile(created_at=datetime(2026, 9, 15, 8, 0))
        with pytest.raises(ValidationError, match="timezone-aware"):
            _consent(accepted_at=datetime(2026, 9, 15, 8, 0))

    def test_identity_fields_are_shaped(self) -> None:
        with pytest.raises(ValidationError):
            _profile(model_id="")
        with pytest.raises(ValidationError):
            _profile(model_id="has space")
        with pytest.raises(ValidationError):
            _profile(model_sha256="ABC")
        with pytest.raises(ValidationError):
            _consent(consent_text_version="v1")
        with pytest.raises(ValidationError):
            _profile(schema_version=2)

    def test_speech_seconds_and_device_name(self) -> None:
        with pytest.raises(ValidationError):
            _profile(enrolment_speech_seconds=0.0)
        with pytest.raises(ValidationError, match="finite"):
            _profile(enrolment_speech_seconds=float("inf"))
        with pytest.raises(ValidationError, match="single-line"):
            _profile(device_name="Mic\nB")
        with pytest.raises(ValidationError):
            _profile(device_name="x" * 201)

    def test_frozen_and_extra_forbidden(self) -> None:
        profile = _profile()
        with pytest.raises(ValidationError):
            profile.model_id = "other"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            _profile(audio=b"never")
        with pytest.raises(ValidationError):
            _consent(patient="never")


# --- the log tripwire (Critical Constraint: never logged) ------------------------


class TestTripwire:
    def _dropped(self, rendered: str) -> bool:
        record = logging.LogRecord("test_profile", logging.INFO, __file__, 1, rendered, None, None)
        before = dropped_record_count()
        result = PayloadTripwireFilter().filter(record) is False
        return result and dropped_record_count() == before + 1

    def test_profile_representations_are_dropped(self) -> None:
        profile = _profile()
        for rendered in (repr(profile), str(profile.model_dump()), profile.model_dump_json()):
            assert self._dropped(rendered), rendered

    def test_consent_representations_are_dropped_on_their_own(self) -> None:
        consent = _consent()
        for rendered in (repr(consent), str(consent.model_dump()), consent.model_dump_json()):
            assert self._dropped(rendered), rendered

    def test_markers_are_disjoint_from_every_log_event_key(self) -> None:
        for key in ALLOWED_KEYS:
            rendering = f"{key}="
            assert all(sig not in rendering for sig in _PAYLOAD_SIGNATURES), key

    def test_module_has_no_logging_channel(self) -> None:
        assert not hasattr(pp, "logging") and not hasattr(pp, "log_event")

    def test_unusable_error_carries_structure_only(self) -> None:
        error = ProfileUnusableError("model", "re-enrol")
        assert error.reason == "model" and "model" in str(error)


# Sentinel values that must never appear in any exception rendering: a vector
# component with a distinctive digit run and a consent record with a distinctive
# version and timestamp (peer round 14 PR-HIGH-003).
_SECRET_COMPONENT = 0.31337
_SECRET_CONSENT_VERSION = "consent-v7"
_SECRET_ACCEPTED_AT = datetime(2031, 1, 2, 3, 4, 5, tzinfo=UTC)
# The REJECTED consent value (fails the version pattern) is itself a sentinel,
# held here so no traceback-rendered call line carries it (peer round 15
# PR-LOW-024): without ``hide_input_in_errors`` pydantic would render it as
# ``input_value='consent-v7x'`` and the test below fails on BOTH assertions.
_SECRET_REJECTED_CONSENT_VERSION = "consent-v7x"
_SECRET_MARKERS = ("0.31337", "31337", "consent-v7", "2031-01-02", "2031")


def _rendered(exc: BaseException) -> str:
    """Everything a traceback logger would persist: the exception, its
    rendered chain (``__cause__`` / ``__context__``) and the frames."""
    return "".join(traceback.format_exception(exc))


class TestValidationErrorsCarryNoInput:
    """Peer round 14 PR-HIGH-003: neither the direct parse error nor the
    loader's error may render the vector or the consent record anywhere in
    the complete exception rendering."""

    def _payload(self, **over: Any) -> dict[str, Any]:
        payload = _profile(
            embedding=(_SECRET_COMPONENT, 0.8),
            consent=_consent(
                consent_text_version=_SECRET_CONSENT_VERSION,
                accepted_at=_SECRET_ACCEPTED_AT,
            ),
        ).model_dump(mode="json")
        payload.update(over)
        return payload

    def test_both_models_hide_their_input_structurally(self) -> None:
        """The configuration itself, so a dropped flag fails here whatever
        pydantic's rendering does (peer round 15 PR-LOW-024)."""
        assert PractitionerProfile.model_config.get("hide_input_in_errors") is True
        assert ConsentRecord.model_config.get("hide_input_in_errors") is True

    def test_non_finite_component_field_validator(self) -> None:
        payload = self._payload()
        payload["embedding"] = [_SECRET_COMPONENT, float("inf")]
        with pytest.raises(ValidationError) as exc:
            PractitionerProfile.model_validate(payload)
        rendered = _rendered(exc.value)
        assert "finite" in rendered  # the structural reason survives
        assert "input_value" not in rendered  # pydantic's input metadata is absent
        assert not any(marker in rendered for marker in _SECRET_MARKERS), rendered

    def test_dimension_mismatch_model_validator(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PractitionerProfile.from_bytes(json.dumps(self._payload(embedding_dim=3)).encode())
        rendered = _rendered(exc.value)
        assert "embedding_dim" in rendered
        # Representation-independent: the whole-record repr pydantic would
        # otherwise attach (truncated or not) is absent as metadata.
        assert "input_value" not in rendered
        assert not any(marker in rendered for marker in _SECRET_MARKERS), rendered

    def test_consent_record_error_hides_the_rejected_value(self) -> None:
        """The REJECTED field carries the sentinel: without the flag the
        rendering would read ``input_value='consent-v7x'``, failing both the
        metadata assertion and the marker assertion."""
        with pytest.raises(ValidationError) as exc:
            ConsentRecord.model_validate(
                {
                    "accepted_at": _SECRET_ACCEPTED_AT,
                    "consent_text_version": _SECRET_REJECTED_CONSENT_VERSION,
                    "learning_opt_in": True,
                }
            )
        rendered = _rendered(exc.value)
        assert "consent_text_version" in rendered  # the location survives
        assert "input_value" not in rendered
        assert not any(marker in rendered for marker in _SECRET_MARKERS), rendered


# --- custody (Windows, real DPAPI) -----------------------------------------------


@windows_only
class TestCustody:
    def test_default_root_under_localappdata(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert default_profile_root() == tmp_path / "ClinikoScribe" / "profile"

    def test_save_load_delete_round_trip(self, tmp_path: Path) -> None:
        root = tmp_path / "profile"
        assert load_profile(root=root) is None and not profile_present(root=root)
        profile = _profile()
        blob_path = save_profile(profile, root=root)
        assert blob_path == root / PROFILE_BLOB_FILENAME
        assert sorted(p.name for p in root.iterdir()) == [KEY_FILENAME, PROFILE_BLOB_FILENAME]
        assert profile_present(root=root)
        assert load_profile(root=root) == profile
        # Ciphertext only: the plaintext JSON never touches the disk.
        assert b'"embedding"' not in blob_path.read_bytes()
        delete_profile(root=root)
        assert list(root.iterdir()) == []
        assert load_profile(root=root) is None
        delete_profile(root=root)  # idempotent

    def test_delete_unlinks_the_key_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)
        order: list[str] = []
        real_unlink = Path.unlink

        def _record(self: Path, missing_ok: bool = False) -> None:
            order.append(self.name)
            real_unlink(self, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", _record)
        delete_profile(root=root)
        assert order == [KEY_FILENAME, PROFILE_BLOB_FILENAME]

    def test_delete_failure_is_typed_and_names_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)

        def _refuse(self: Path, missing_ok: bool = False) -> None:
            raise OSError(13, "locked")

        monkeypatch.setattr(Path, "unlink", _refuse)
        with pytest.raises(StoreWriteError, match="profile key"):
            delete_profile(root=root)

    def test_re_enrolment_keeps_the_key_and_replaces_only_the_blob(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)
        key_before = (root / KEY_FILENAME).read_bytes()
        blob_before = (root / PROFILE_BLOB_FILENAME).read_bytes()
        second = _profile(embedding=(-0.8, 0.6), enrolment_speech_seconds=40.0)
        save_profile(second, root=root)
        assert (root / KEY_FILENAME).read_bytes() == key_before
        assert (root / PROFILE_BLOB_FILENAME).read_bytes() != blob_before
        assert sorted(p.name for p in root.iterdir()) == [KEY_FILENAME, PROFILE_BLOB_FILENAME]
        assert load_profile(root=root) == second

    def test_failed_blob_write_on_re_enrolment_leaves_the_old_profile_usable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"
        first = _profile()
        save_profile(first, root=root)
        key_before = (root / KEY_FILENAME).read_bytes()

        def _fail(path: Path, blob: bytes, *, error_label: str) -> None:
            raise StoreWriteError(f"failed writing {error_label}: disk full")

        monkeypatch.setattr(pp, "atomic_write_bytes", _fail)
        with pytest.raises(StoreWriteError, match="practitioner profile"):
            save_profile(_profile(embedding=(-0.8, 0.6)), root=root)
        monkeypatch.undo()
        assert (root / KEY_FILENAME).read_bytes() == key_before
        assert load_profile(root=root) == first

    def test_failed_key_write_on_first_enrolment_leaves_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"

        def _fail(crypto: SessionCrypto, session_dir: Path, *, description: str) -> Path:
            raise StoreWriteError("failed writing key custody blob: disk full")

        monkeypatch.setattr(pp, "wrap_key_to_file", _fail)
        with pytest.raises(StoreWriteError, match="key custody"):
            save_profile(_profile(), root=root)
        assert list(root.iterdir()) == []
        assert load_profile(root=root) is None

    def test_failed_blob_write_after_the_key_is_absent_then_retry_reuses_the_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"

        def _fail(path: Path, blob: bytes, *, error_label: str) -> None:
            raise StoreWriteError(f"failed writing {error_label}: disk full")

        monkeypatch.setattr(pp, "atomic_write_bytes", _fail)
        with pytest.raises(StoreWriteError):
            save_profile(_profile(), root=root)
        monkeypatch.undo()
        assert [p.name for p in root.iterdir()] == [KEY_FILENAME]
        assert load_profile(root=root) is None  # a key with no blob is ABSENT
        assert not profile_present(root=root)
        key_before = (root / KEY_FILENAME).read_bytes()
        save_profile(_profile(), root=root)
        assert (root / KEY_FILENAME).read_bytes() == key_before
        assert load_profile(root=root) == _profile()

    def test_unusable_existing_key_refuses_the_save_and_touches_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)
        blob_before = (root / PROFILE_BLOB_FILENAME).read_bytes()
        (root / KEY_FILENAME).write_bytes(b"\xff" * 64)  # a non-dead, undecryptable blob
        with pytest.raises(ProfileUnusableError, match=r"\(key\)") as exc:
            save_profile(_profile(embedding=(-0.8, 0.6)), root=root)
        assert exc.value.reason == "key"
        assert (root / PROFILE_BLOB_FILENAME).read_bytes() == blob_before
        assert (root / KEY_FILENAME).read_bytes() == b"\xff" * 64

    def test_uninspectable_key_refuses_the_save_before_any_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 12 LOW-002: a stat failure that is not a confirmed absence
        must not be read as "no key" — that would write a NEW key over one
        the code merely could not inspect."""
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        real_stat = Path.stat

        def _refuse(self: Path, *args: Any, **kwargs: Any) -> Any:
            if self.name == KEY_FILENAME:
                raise PermissionError(13, "locked")
            return real_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", _refuse)
        with pytest.raises(StoreWriteError, match="not readable"):
            save_profile(_profile(embedding=(-0.8, 0.6)), root=root)
        monkeypatch.undo()
        assert {p.name: p.read_bytes() for p in root.iterdir()} == before

    def test_no_plaintext_and_key_destroyed_on_the_way_out(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "profile"
        cryptos: list[SessionCrypto] = []
        real_wrap = pp.wrap_key_to_file

        def _spy(crypto: SessionCrypto, session_dir: Path, *, description: str) -> Path:
            cryptos.append(crypto)
            return real_wrap(crypto, session_dir, description=description)

        monkeypatch.setattr(pp, "wrap_key_to_file", _spy)
        save_profile(_profile(), root=root)
        assert len(cryptos) == 1 and cryptos[0].destroyed


@windows_only
class TestLoadUnusableStates:
    def _saved(self, tmp_path: Path) -> Path:
        root = tmp_path / "profile"
        save_profile(_profile(), root=root)
        return root

    def _reason(self, root: Path, **kw: Any) -> str:
        with pytest.raises(ProfileUnusableError) as exc:
            load_profile(root=root, **kw)
        return exc.value.reason

    def test_blob_without_key_is_unusable_key(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        (root / KEY_FILENAME).unlink()
        assert self._reason(root) == "key"

    def test_dead_key_is_unusable_key(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        (root / KEY_FILENAME).write_bytes(b"")
        assert self._reason(root) == "key"

    def test_truncated_blob_fails_authentication(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        blob = root / PROFILE_BLOB_FILENAME
        blob.write_bytes(blob.read_bytes()[:-1])
        assert self._reason(root) == "authentication"
        blob.write_bytes(b"")
        assert self._reason(root) == "authentication"

    def test_tampered_blob_fails_authentication(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        blob = root / PROFILE_BLOB_FILENAME
        data = bytearray(blob.read_bytes())
        data[20] ^= 0x01
        blob.write_bytes(bytes(data))
        assert self._reason(root) == "authentication"

    def test_wrong_aad_fails_authentication(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=PROFILE_KEY_DESCRIPTION)
        (root / PROFILE_BLOB_FILENAME).write_bytes(
            crypto.encrypt(_profile().to_bytes(), b"clinikoscribe-practitioner-profile-v2")
        )
        assert self._reason(root) == "authentication"

    def test_authentic_but_invalid_content_is_malformed(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=PROFILE_KEY_DESCRIPTION)
        (root / PROFILE_BLOB_FILENAME).write_bytes(crypto.encrypt(b"{}", PROFILE_AAD))
        with pytest.raises(ProfileUnusableError) as exc:
            load_profile(root=root)
        assert exc.value.reason == "malformed"
        assert "validation error" in str(exc.value) and "embedding" in str(exc.value)
        assert exc.value.__cause__ is None and exc.value.__suppress_context__

    def test_malformed_blob_renders_no_vector_or_consent_anywhere(self, tmp_path: Path) -> None:
        """Peer round 14 PR-HIGH-003: an authenticated blob whose content
        fails validation (here the model-level dimension check, whose input
        is the WHOLE record) must surface as a structural error whose complete
        rendering — chain included — carries no vector component and no
        consent value."""
        root = self._saved(tmp_path)
        crypto = unwrap_key_from_file(root, description=PROFILE_KEY_DESCRIPTION)
        payload = _profile(
            embedding=(_SECRET_COMPONENT, 0.8),
            consent=_consent(
                consent_text_version=_SECRET_CONSENT_VERSION,
                accepted_at=_SECRET_ACCEPTED_AT,
            ),
        ).model_dump(mode="json")
        payload["embedding_dim"] = 3
        (root / PROFILE_BLOB_FILENAME).write_bytes(
            crypto.encrypt(json.dumps(payload).encode(), PROFILE_AAD)
        )
        with pytest.raises(ProfileUnusableError) as exc:
            load_profile(root=root)
        assert exc.value.reason == "malformed"
        rendered = _rendered(exc.value)
        assert "ValidationError" not in rendered  # not chained, not in the context
        assert not any(marker in rendered for marker in _SECRET_MARKERS), rendered

    def test_model_mismatch_is_unusable_model(self, tmp_path: Path) -> None:
        root = self._saved(tmp_path)
        assert load_profile(root=root, model_id="mock-speaker-embedder-v1") is not None
        assert self._reason(root, model_id="wespeaker-voxceleb-resnet34-LM") == "model"
        assert self._reason(root, model_id="mock-speaker-embedder-v1", model_sha256="a" * 64) == (
            "model"
        )

    def test_unreadable_blob_is_unusable_blob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._saved(tmp_path)
        real_read = Path.read_bytes

        def _refuse(self: Path) -> bytes:
            if self.name == PROFILE_BLOB_FILENAME:
                raise OSError(13, "locked")
            return real_read(self)

        monkeypatch.setattr(Path, "read_bytes", _refuse)
        assert self._reason(root) == "blob"

    def test_a_session_key_blob_cannot_serve_as_the_profile_key(self, tmp_path: Path) -> None:
        """The DPAPI description binds a key blob to its store: a session key
        (default description) placed in the profile root fails the unwrap
        typed, before any decryption is attempted."""
        root = tmp_path / "profile"
        root.mkdir()
        session_crypto = SessionCrypto()
        wrap_key_to_file(session_crypto, root)  # the SESSION description
        (root / PROFILE_BLOB_FILENAME).write_bytes(
            session_crypto.encrypt(_profile().to_bytes(), PROFILE_AAD)
        )
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root, description=PROFILE_KEY_DESCRIPTION)
        assert self._reason(root) == "key"
        # And the reverse: the profile key is not a session key.
        wrap_key_to_file(SessionCrypto(), root, description=PROFILE_KEY_DESCRIPTION)
        with pytest.raises(KeyCustodyError, match="different store"):
            unwrap_key_from_file(root)

    def test_load_destroys_the_in_memory_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = self._saved(tmp_path)
        unwrapped: list[SessionCrypto] = []
        real_unwrap = pp.unwrap_key_from_file

        def _spy(session_dir: Path, *, description: str) -> SessionCrypto:
            crypto = real_unwrap(session_dir, description=description)
            unwrapped.append(crypto)
            return crypto

        monkeypatch.setattr(pp, "unwrap_key_from_file", _spy)
        assert load_profile(root=root) is not None
        assert unwrapped and unwrapped[0].destroyed

    def test_created_at_survives_with_offset(self, tmp_path: Path) -> None:
        root = tmp_path / "profile"
        stamped = _profile(created_at=NOW + timedelta(hours=10))
        save_profile(stamped, root=root)
        loaded = load_profile(root=root)
        assert loaded is not None and loaded.created_at == stamped.created_at
