"""The Past-sessions backup container (past-sessions-backup plan Task 1.3;
D2, D3; C8): a round trip, and every refusal of D2's reader by its closed
code — the preflight's through the size-and-read seam with ``zipfile`` never
called. Synthetic content only, fake key seams, the test KDF floor (D15)."""

from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import backup_fakes as fakes
from scribe_desktop import audit as audit_mod
from scribe_desktop import past_sessions_backup as backup
from scribe_desktop.past_sessions import LABEL_FILENAME, PastSessionLabel, _label_aad
from scribe_desktop.past_sessions_backup import (
    BackupFormatError,
    BackupReader,
    BackupRunError,
    HandleSource,
)
from scribe_desktop.secure_storage import SessionCrypto


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """D15: the test floor — the ONLY way a cheaper KDF is admitted."""
    monkeypatch.setattr(backup, "_kdf_floor_for_tests", backup.KdfFloor())


def _refused(code: str, source: Any, key: Any = None) -> BackupFormatError:
    with pytest.raises(BackupFormatError) as info:
        if key is None:
            backup.read_backup_header(source)
        else:
            backup.verify_backup(source, key)
    assert info.value.code == code
    assert str(info.value) == code  # the text is the code, nothing else
    return info.value


def _verify_refused(built: fakes.Built, code: str) -> None:
    _refused(code, io.BytesIO(built.blob), built.key)


class _Source:
    """The size-and-read seam over bytes, counting reads."""

    def __init__(self, blob: bytes, size: int | None = None) -> None:
        self.blob = blob
        self._size = len(blob) if size is None else size
        self.reads = 0

    def size(self) -> int:
        return self._size

    def read_at(self, offset: int, length: int) -> bytes:
        self.reads += 1
        return self.blob[offset : offset + length]


@pytest.fixture
def no_zipfile(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the reader used zipfile")

    monkeypatch.setattr(backup.zipfile, "ZipFile", boom)


def _header() -> bytes:
    return fakes.minimal_header()


# ---------------------------------------------------------------------------
# The round trip.
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_a_backup_opens_and_every_member_reads_back(self, tmp_path: Path) -> None:
        built = fakes.build(tmp_path, entries=2, rows=3)
        path = built.write(tmp_path / "ClinikoScribe-backup-2026-10-01.csbk")
        opened = backup.open_backup(path, fakes.PASSPHRASE)
        reader, key = opened.reader, opened.key
        facts = reader.facts
        assert facts.file_sha256 == hashlib.sha256(built.blob).hexdigest()
        assert set(facts.completed) == set(built.entry_keys)
        assert all(date == fakes.NOW for date in facts.completed.values())
        assert facts.importable_rows == frozenset(built.rows)
        assert facts.header.channel == "production"
        assert facts.header.app_version == backup.__version__
        assert list(facts.members)[0] == backup.HEADER_MEMBER
        assert list(facts.members)[-1] == backup.MANIFEST_MEMBER
        for session_id, plain_key in built.entry_keys.items():
            unwrapped = reader.unwrap_entry_key(session_id, key)
            assert isinstance(unwrapped, bytearray) and bytes(unwrapped) == plain_key
            assert reader.entry_files(session_id) == built.entry_files[session_id]
        audit_key = reader.unwrap_audit_key(key)
        assert audit_key is not None and bytes(audit_key) == built.audit_key
        for session_id, (month, blob) in built.rows.items():
            assert reader.read_member(backup.row_member(month, session_id)) == blob

    def test_an_audit_only_file_and_an_entries_only_file_round_trip(
        self, tmp_path: Path
    ) -> None:
        audit_only = fakes.build(tmp_path / "a", entries=0, rows=2)
        facts = backup.verify_backup(io.BytesIO(audit_only.blob), audit_only.key)
        assert facts.completed == {} and len(facts.importable_rows) == 2
        entries_only = fakes.build(tmp_path / "e", entries=2, rows=0)
        facts = backup.verify_backup(io.BytesIO(entries_only.blob), entries_only.key)
        assert len(facts.completed) == 2 and facts.importable_rows == frozenset()
        assert facts.manifest.audit_key is None

    def test_a_reader_refuses_a_member_changed_after_open(self, tmp_path: Path) -> None:
        built = fakes.build(tmp_path)
        path = built.write(tmp_path / "b.csbk")
        reader = backup.open_backup(path, fakes.PASSPHRASE).reader
        [session_id] = built.entry_keys
        name = backup.entry_member(session_id, "transcript")
        span = reader.facts.members[name]
        damaged = bytearray(built.blob)
        damaged[span.offset] ^= 0xFF
        path.write_bytes(bytes(damaged))
        with pytest.raises(BackupRunError) as info:
            reader.read_member(name)
        assert info.value.code == "source_changed"


# ---------------------------------------------------------------------------
# The preflight (D2 step 1), through the seam, ``zipfile`` never called.
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("no_zipfile")
class TestPreflight:
    def test_a_file_over_the_cap_is_refused_before_any_read(self) -> None:
        source = _Source(b"", size=backup.MAX_BACKUP_BYTES + 1)
        _refused("too_large", source)
        assert source.reads == 0

    def test_not_a_backup_a_comment_and_zip64(self) -> None:
        _refused("not_a_backup", _Source(b"hello world" * 10))
        _refused("not_a_backup", _Source(b"PK"))
        members = [(backup.HEADER_MEMBER, _header()), (backup.MANIFEST_MEMBER, b"m" * 40)]
        _refused("comment", _Source(fakes.raw_zip(members, comment=b"a comment")))
        _refused("zip64", _Source(fakes.raw_zip(members, zip64_locator=True)))

    def test_an_end_record_whose_own_fields_spell_its_signature_is_found(self) -> None:
        """Review round 39: a directory at offset 0x06054B50 puts the end
        record's signature inside its own offset field. The record is still
        read at its fixed place (the last 22 bytes) — before the fix a search
        from the end stopped inside it and refused the file as ``comment``.
        The directory here is zeros, so the walk refuses it instead."""
        directory_offset, directory_size = 0x06054B50, 60
        signature = int.from_bytes(backup._END_MAGIC, "little")
        end = backup._END.pack(signature, 0, 0, 1, 1, directory_size, directory_offset, 0)
        assert end[16:20] == backup._END_MAGIC

        class Sparse:
            """Zeros everywhere but the end record, which is the last 22 bytes."""

            def size(self) -> int:
                return directory_offset + directory_size + len(end)

            def read_at(self, offset: int, length: int) -> bytes:
                out = bytearray(length)
                start = self.size() - len(end)
                for index in range(max(offset, start), min(offset + length, self.size())):
                    out[index - offset] = end[index - start]
                return bytes(out)

        with pytest.raises(BackupFormatError) as info:
            backup.preflight(Sparse())
        assert info.value.code not in {"comment", "not_a_backup"}

    def test_the_directory_count_and_size(self) -> None:
        members = [(backup.HEADER_MEMBER, _header()), (backup.MANIFEST_MEMBER, b"m" * 40)]
        _refused("directory_count", _Source(fakes.raw_zip(members, declared_count=3)))
        _refused("directory_count", _Source(fakes.raw_zip(members, declared_count=1)))
        long_comment = {backup.MANIFEST_MEMBER: b"c" * 600}
        too_long = fakes.raw_zip(members, member_comment=long_comment)
        _refused("directory_too_large", _Source(too_long))

    def test_member_names(self) -> None:
        header = (backup.HEADER_MEMBER, _header())
        manifest = (backup.MANIFEST_MEMBER, b"m" * 40)
        long_name = "a" * 129
        _refused("member_name", _Source(fakes.raw_zip([header, manifest, (long_name, b"x")])))
        _refused(
            "member_name",
            _Source(fakes.raw_zip([header, manifest, ("x", b"x")], raw_names={"x": b"\xe9"})),
        )
        _refused("member_duplicate", _Source(fakes.raw_zip([header, manifest, manifest])))

    def test_extra_fields_comments_methods_flags_and_sizes(self) -> None:
        header = (backup.HEADER_MEMBER, _header())
        name = backup.MANIFEST_MEMBER
        members = [header, (name, b"m" * 40)]
        zip64_field = b"\x01\x00\x10\x00" + b"\0" * 16
        _refused("member_extra", _Source(fakes.raw_zip(members, central_extra={name: zip64_field})))
        _refused("member_extra", _Source(fakes.raw_zip(members, local_extra={name: zip64_field})))
        _refused("member_comment", _Source(fakes.raw_zip(members, member_comment={name: b"c"})))
        _refused("member_method", _Source(fakes.raw_zip(members, method={name: 8})))
        _refused("member_flags", _Source(fakes.raw_zip(members, flags={name: 0x0008})))
        _refused("member_flags", _Source(fakes.raw_zip(members, flags={name: 0x0001})))
        _refused("member_sizes", _Source(fakes.raw_zip(members, central_sizes={name: (40, 41)})))

    def test_a_local_header_must_match_its_directory_record(self) -> None:
        header = (backup.HEADER_MEMBER, _header())
        name = backup.MANIFEST_MEMBER
        members = [header, (name, b"m" * 40)]
        renamed = fakes.raw_zip(members, local_name={name: b"manifest.enx"})
        _refused("local_header", _Source(renamed))
        _refused("local_header", _Source(fakes.raw_zip(members, local_sizes={name: (39, 39)})))

    def test_the_header_and_manifest_records(self) -> None:
        header = (backup.HEADER_MEMBER, _header())
        manifest = (backup.MANIFEST_MEMBER, b"m" * 40)
        _refused("header_first", _Source(fakes.raw_zip([manifest, header])))
        _refused("header_first", _Source(fakes.raw_zip([])))
        big = (backup.HEADER_MEMBER, b" " * (backup.MAX_HEADER_BYTES + 1))
        _refused("header_too_large", _Source(fakes.raw_zip([big, manifest])))
        _refused("manifest_missing", _Source(fakes.raw_zip([header, ("other.enc", b"x")])))
        huge = (backup.MANIFEST_MEMBER, b"\0" * (backup.MAX_MANIFEST_BYTES + 1))
        _refused("manifest_too_large", _Source(fakes.raw_zip([header, huge])))


# ---------------------------------------------------------------------------
# The header, the KDF and the channel (D2 steps 2-3, D3).
# ---------------------------------------------------------------------------


def _with_header(change: Any) -> bytes:
    document = json.loads(_header())
    change(document)
    members = [
        (backup.HEADER_MEMBER, json.dumps(document).encode()),
        (backup.MANIFEST_MEMBER, b"m" * 40),
    ]
    return fakes.raw_zip(members)


class TestHeader:
    def test_a_newer_format_and_an_invalid_header(self) -> None:
        _refused("format_newer", _Source(_with_header(lambda d: d.update(format_version=2))))
        _refused("header_invalid", _Source(_with_header(lambda d: d.update(format_version=0))))
        _refused("header_invalid", _Source(_with_header(lambda d: d.update(format_version=True))))
        _refused("header_invalid", _Source(_with_header(lambda d: d.update(extra="x"))))
        _refused("header_invalid", _Source(_with_header(lambda d: d.pop("kdf"))))

    def test_nesting_past_the_stack_is_an_invalid_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The header is read before any key: a parse that runs out of
        stack is refused by its code, never raised as RecursionError."""
        source = _Source(_with_header(lambda d: None))

        def too_deep(*args: Any, **kwargs: Any) -> Any:
            raise RecursionError

        monkeypatch.setattr(backup.json, "loads", too_deep)
        _refused("header_invalid", source)

    @pytest.mark.parametrize(
        ("field", "value", "code"),
        [
            ("name", "scrypt", "kdf_unknown"),
            ("memory_cost", backup.KDF_MEMORY_RANGE[1] + 1, "kdf_out_of_range"),
            ("memory_cost", 7, "kdf_out_of_range"),
            ("iterations", backup.KDF_ITERATIONS_RANGE[1] + 1, "kdf_out_of_range"),
            ("iterations", 0, "kdf_out_of_range"),
            ("lanes", backup.KDF_LANES_RANGE[1] + 1, "kdf_out_of_range"),
            ("lanes", 0, "kdf_out_of_range"),
        ],
    )
    def test_the_kdf_envelope_is_checked_before_any_derivation(
        self, monkeypatch: pytest.MonkeyPatch, field: str, value: Any, code: str
    ) -> None:
        def never(*args: Any, **kwargs: Any) -> bytes:
            raise AssertionError("derived before the envelope was checked")

        monkeypatch.setattr(backup, "argon2id_derive", never)
        _refused(code, _Source(_with_header(lambda d: d["kdf"].update({field: value}))))
        params = backup.KdfParams(**{**json.loads(_header())["kdf"], field: value})
        with pytest.raises(BackupFormatError) as info:
            backup.derive_key(fakes.PASSPHRASE, params)
        assert info.value.code == code

    def test_without_the_test_floor_the_production_envelope_holds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(backup, "_kdf_floor_for_tests", None)
        params = backup.new_kdf_params()
        assert (params.memory_cost, params.iterations, params.lanes) == (262_144, 3, 1)
        for change in ({"memory_cost": 65_535}, {"iterations": 1}):
            with pytest.raises(BackupFormatError) as info:
                backup.check_kdf(backup.KdfParams(**{**params.model_dump(), **change}))
            assert info.value.code == "kdf_out_of_range"
        backup.check_kdf(backup.KdfParams(**{**params.model_dump(), "memory_cost": 65_536}))

    def test_a_memory_error_is_refused_by_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def no_memory(*args: Any, **kwargs: Any) -> bytes:
            raise MemoryError

        monkeypatch.setattr(backup, "argon2id_derive", no_memory)
        with pytest.raises(BackupFormatError) as info:
            backup.derive_key(fakes.PASSPHRASE, backup.new_kdf_params())
        assert info.value.code == "kdf_memory"

    def test_another_channel_is_refused_before_the_passphrase(self) -> None:
        error = _refused("other_channel", _Source(_with_header(lambda d: d.update(channel="dev"))))
        assert error.channel == "dev"


# ---------------------------------------------------------------------------
# The manifest, the member set and the hashes (D2 steps 4-5).
# ---------------------------------------------------------------------------


class TestManifest:
    def test_a_wrong_passphrase_and_a_damaged_manifest_give_one_code(
        self, tmp_path: Path
    ) -> None:
        built = fakes.build(tmp_path)
        wrong = backup.derive_key(b"another passphrase, also long", built.header.kdf)
        _refused("passphrase", io.BytesIO(built.blob), wrong)
        spans = backup.preflight(HandleSource(io.BytesIO(built.blob)))
        damaged = bytearray(built.blob)
        damaged[spans[backup.MANIFEST_MEMBER].offset + 20] ^= 0x01
        _refused("passphrase", io.BytesIO(bytes(damaged)), built.key)

    def test_a_changed_header_fails_the_manifest(self, tmp_path: Path) -> None:
        built = fakes.build(tmp_path)
        changed = built.blob.replace(b'"max_rows": 1', b'"max_rows": 2', 1)
        assert changed != built.blob
        _refused("passphrase", io.BytesIO(changed), built.key)

    def test_the_manifest_channel_and_its_bounds(self, tmp_path: Path) -> None:
        dev = fakes.build(tmp_path / "d", manifest=lambda m: m.update(channel="dev"))
        _verify_refused(dev, "other_channel")
        over = fakes.build(tmp_path / "o", header=lambda h: h.update(max_rows=0))
        _verify_refused(over, "manifest_bounds")

    @pytest.mark.parametrize(
        "change",
        [
            lambda m: m["entries"].update({"NOT-AN-ID": next(iter(m["entries"].values()))}),
            lambda m: m["rows"][next(iter(m["rows"]))].update(month="2026-13"),
            lambda m: m.update(audit_key=None),
            lambda m: m.update(unexpected=1),
        ],
    )
    def test_an_authentic_manifest_that_is_not_valid(self, tmp_path: Path, change: Any) -> None:
        _verify_refused(fakes.build(tmp_path, manifest=change), "manifest_invalid")

    def test_nesting_past_the_stack_is_an_invalid_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built = fakes.build(tmp_path)
        real_loads = json.loads
        calls: list[int] = []

        def deep_after_the_header(*args: Any, **kwargs: Any) -> Any:
            calls.append(1)
            if len(calls) == 1:  # the header parses as written
                return real_loads(*args, **kwargs)
            raise RecursionError

        monkeypatch.setattr(backup.json, "loads", deep_after_the_header)
        _verify_refused(built, "manifest_invalid")
        assert len(calls) == 2

    def test_the_member_set_differing_by_one_either_way(self, tmp_path: Path) -> None:
        extra = fakes.build(tmp_path / "x", members=lambda p: p.append(("stray.enc", b"x")))
        _verify_refused(extra, "member_set")
        missing = fakes.build(tmp_path / "y", members=lambda p: p.pop())
        _verify_refused(missing, "member_set")

    def test_a_mis_sized_member(self, tmp_path: Path) -> None:
        def resize(manifest: dict[str, Any]) -> None:
            entry = next(iter(manifest["entries"].values()))
            entry["files"]["transcript"]["size"] += 1

        _verify_refused(fakes.build(tmp_path, manifest=resize), "member_size")

    @pytest.mark.parametrize(
        "which", ["key", "row", "audit", "label", "transcript", "note", "generated"]
    )
    def test_a_byte_flipped_in_any_payload_member(self, tmp_path: Path, which: str) -> None:
        built = fakes.build(tmp_path)
        [session_id] = built.entry_keys
        [row_id] = built.rows
        name = {
            "key": backup.key_member(session_id),
            "row": backup.row_member(built.rows[row_id][0], row_id),
            "audit": backup.AUDIT_KEY_MEMBER,
        }.get(which, backup.entry_member(session_id, which))
        span = backup.preflight(HandleSource(io.BytesIO(built.blob)))[name]
        damaged = bytearray(built.blob)
        damaged[span.offset + span.size // 2] ^= 0x01
        _refused("member_hash", io.BytesIO(bytes(damaged)), built.key)


# ---------------------------------------------------------------------------
# The open check (D2 step 6).
# ---------------------------------------------------------------------------


def _reseal_label(built_entry_key: bytes, label: PastSessionLabel, aad_id: str) -> bytes:
    crypto = SessionCrypto.from_key(built_entry_key)
    try:
        return crypto.encrypt(label.to_bytes(), _label_aad(aad_id))
    finally:
        crypto.destroy()


class TestOpenCheck:
    def test_a_label_and_its_files_must_agree(self, tmp_path: Path) -> None:
        """``has_saved`` with no note member, and a generated note the label
        does not call for — each authentic, each refused."""

        def drop(kind: str) -> Any:
            def change(manifest: dict[str, Any]) -> None:
                next(iter(manifest["entries"].values()))["files"].pop(kind)

            return change

        def without(kind: str) -> Any:
            def change(payload: list[tuple[str, bytes]]) -> None:
                payload[:] = [item for item in payload if not item[0].endswith(f"/{kind}.enc")]

            return change

        for kind in ("note", "generated"):
            built = fakes.build(tmp_path / kind, manifest=drop(kind), members=without(kind))
            _verify_refused(built, "entry_does_not_open")

    def test_an_authentic_label_naming_another_id_is_refused(self, tmp_path: Path) -> None:
        holder: dict[str, Any] = {}
        store = fakes.archive(tmp_path)
        session_id = fakes.published(store)
        key = fakes.entry_key(store, session_id)
        label_blob = (store.root / session_id / LABEL_FILENAME).read_bytes()
        crypto = SessionCrypto.from_key(key)
        label = PastSessionLabel.model_validate_json(
            crypto.decrypt(label_blob, _label_aad(session_id))
        )
        crypto.destroy()
        other = fakes.sid()
        renamed = label.model_copy(update={"session_id": other})
        holder["blob"] = _reseal_label(key, renamed, session_id)

        def swap(payload: list[tuple[str, bytes]]) -> None:
            name = backup.entry_member(session_id, "label")
            payload[:] = [(n, holder["blob"] if n == name else b) for n, b in payload]

        def rehash(manifest: dict[str, Any]) -> None:
            manifest["entries"][session_id]["files"]["label"] = fakes.digest(holder["blob"])

        built = fakes.build(tmp_path, store=store, members=swap, manifest=rehash)
        _verify_refused(built, "entry_does_not_open")

    def test_an_entry_key_under_another_id_is_refused(self, tmp_path: Path) -> None:
        def misplace(payload: list[tuple[str, bytes]]) -> None:
            keys = [i for i, (n, _b) in enumerate(payload) if n.startswith("keys/")]
            first, second = keys
            (n1, b1), (n2, b2) = payload[first], payload[second]
            payload[first], payload[second] = (n1, b2), (n2, b1)

        def rehash(manifest: dict[str, Any]) -> None:
            ids = list(manifest["entries"])
            first, second = (manifest["entries"][i]["key"] for i in ids)
            manifest["entries"][ids[0]]["key"], manifest["entries"][ids[1]]["key"] = second, first

        built = fakes.build(tmp_path, entries=2, members=misplace, manifest=rehash)
        _verify_refused(built, "entry_key")

    def test_a_row_that_does_not_authenticate_is_refused(self, tmp_path: Path) -> None:
        holder: dict[str, bytes] = {}

        def garble(payload: list[tuple[str, bytes]]) -> None:
            for index, (name, blob) in enumerate(payload):
                if name.startswith("audit/"):
                    holder["blob"] = blob[:-1] + bytes([blob[-1] ^ 1])
                    payload[index] = (name, holder["blob"])

        def rehash(manifest: dict[str, Any]) -> None:
            row = next(iter(manifest["rows"].values()))
            row.update(fakes.digest(holder["blob"]))

        _verify_refused(fakes.build(tmp_path, members=garble, manifest=rehash), "row_unauthentic")

    def test_a_row_naming_another_month_is_not_importable(self, tmp_path: Path) -> None:
        def move(payload: list[tuple[str, bytes]]) -> None:
            payload[:] = [
                (n.replace("audit/2026-10/", "audit/2026-09/"), b) for n, b in payload
            ]

        def remonth(manifest: dict[str, Any]) -> None:
            for row in manifest["rows"].values():
                row["month"] = "2026-09"

        built = fakes.build(tmp_path, members=move, manifest=remonth)
        facts = backup.verify_backup(io.BytesIO(built.blob), built.key)
        assert facts.importable_rows == frozenset()

    def test_an_authentic_row_nested_past_the_stack_is_not_importable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 24 PR-LOW-2401: the audit parser's ``RecursionError``
        (injected for row plaintext only) leaves the row out of
        ``importable_rows``; the file still opens."""
        built = fakes.build(tmp_path)
        assert backup.verify_backup(io.BytesIO(built.blob), built.key).importable_rows
        real = json.loads
        seen: list[bytes] = []

        def too_deep_for_rows(text: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(text, bytes) and b'"session_date"' in text:
                seen.append(text)
                raise RecursionError
            return real(text, *args, **kwargs)

        monkeypatch.setattr(audit_mod.json, "loads", too_deep_for_rows)
        facts = backup.verify_backup(io.BytesIO(built.blob), built.key)
        assert seen
        assert facts.importable_rows == frozenset()

    def test_codes_are_closed(self) -> None:
        assert BackupFormatError("not-a-code").code == "unreadable"
        assert BackupRunError("not-a-code").code == "unexpected"


def test_the_reader_never_needs_a_key_to_name_its_members(tmp_path: Path) -> None:
    built = fakes.build(tmp_path)
    reader = BackupReader(
        io.BytesIO(built.blob), backup.verify_backup(io.BytesIO(built.blob), built.key)
    )
    assert reader.manifest.made_at == datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
