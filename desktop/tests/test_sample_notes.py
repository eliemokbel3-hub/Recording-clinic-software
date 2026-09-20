"""Note-learning-and-styles plan Phase 3 Task 3.3: ``sample_notes``.

What is pinned here, per the plan's Phase 3 validation line:
- the learner never writes to or copies from the source directory (a
  before/after snapshot of the whole temporary tree);
- an exemplar with ANY refused token is dropped UNCHANGED — the sentence is
  absent, and no edited form of it is present (C5, the Excluded item);
- shorthand is split by the shipped controlled vocabulary (D10): recognised
  tokens carry the vocabulary's own spelling, unrecognised ones are offered
  and saved only when ticked, and ``build_style_profile`` refuses anything
  the draft did not offer;
- the delete-originals step touches exactly the listed paths;
- ``.docx`` is read through python-docx (skipped, by name, when absent);
- the three new log-tripwire markers are registered.
"""

from __future__ import annotations

import io
import os
import sys
import zipfile
import zlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scribe_desktop import sample_notes
from scribe_desktop.logging_setup import _PAYLOAD_SIGNATURES
from scribe_desktop.note_config import (
    MAX_SAMPLE_NOTES,
    MAX_STYLE_EXEMPLARS,
    StyleExemplar,
    refuse_learning_candidate,
)
from scribe_desktop.practitioner_profile import ConsentRecord
from scribe_desktop.sample_notes import (
    MAX_SAMPLE_NOTE_BYTES,
    SampleNote,
    SampleNoteError,
    StyleProfileDraft,
    build_style_profile,
    delete_sample_files,
    learn_style_profile,
    read_sample_note,
)
from scribe_desktop.ui import models

NOW = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)

# One note in the practitioner's own shape. Every body sentence is listed
# below with what THE refusal filter does to it under Task 3.7's two
# admissions — (a) a shipped abbreviation is never name-like, (b) a
# capitalised REAL-first word is admitted when its lowercase form appears
# elsewhere in the notes — so the expectations here are the filter's, not
# the learner's. ``KEPT_*`` are derived by hand from those rules.
KEPT_1 = "Keep the neck moving gently."  # exempt opener, nothing else capitalised
KEPT_2 = "ROM limited on the left."  # (a): ROM is in the vocabulary
KEPT_3 = "NAD on palpation today."  # (a)
KEPT_4 = "HVLA Cx applied with good release."  # (a) twice, one mid-sentence
KEPT_5 = "Continue with the home programme."  # exempt opener
REFUSED = {
    "Neck pain for three days.": "number",  # (b) admits "Neck" (neck is lowercase below)
    "Pt reports improvement (QWERTY protocol).": "name",  # "Pt" unlisted, never lowercase
    "Seen on 12/03 for follow up.": "name",  # "Seen" first; the date is second in order
    "Rest for two days each week.": "number",  # "Rest" is exempt; "two" is a number
    "Continue amoxicillin as prescribed.": "medication",  # "-cillin"
    "Review in one week.": "name",  # "Review" is not listed and never lowercase
    "L4 and C5/6 noted.": "name",  # "L4" is neither in the vocabulary nor lowercase
}
NOTE_A = "\n".join(
    [
        "C/O: Neck pain for three days.",
        KEPT_1,
        "O/E: ROM limited on the left. NAD on palpation today.",
        "Pt reports improvement (QWERTY protocol).",
        "Rx: HVLA Cx applied with good release.",
        KEPT_5,
        "Seen on 12/03 for follow up.",
        "Rest for two days each week.",
        "Continue amoxicillin as prescribed.",
        "Plan: Review in one week.",
        "L4 and C5/6 noted.",
    ]
)
NOTE_B = "\n".join(
    [
        "Assessment",
        "Keep up the good work at home.",
        "C/O",
        "Rest the shoulder for now.",
    ]
)


def _consent() -> ConsentRecord:
    return ConsentRecord(
        accepted_at=NOW, consent_text_version=models.CONSENT_TEXT_VERSION, learning_opt_in=True
    )


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Every entry under ``root`` with its size and mtime — the evidence
    that a read left the tree exactly as it was."""
    entries: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in (*dirnames, *filenames):
            path = Path(dirpath) / name
            stat = path.stat()
            entries[str(path.relative_to(root))] = (stat.st_size, stat.st_mtime_ns)
    return entries


def _draft(*texts: str) -> StyleProfileDraft:
    return learn_style_profile([SampleNote(text) for text in texts])


# --- reading -----------------------------------------------------------------


class TestReadSampleNote:
    def test_a_txt_file_is_read_into_memory_and_the_tree_is_untouched(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "notes"
        source.mkdir()
        (source / "a.txt").write_text(NOTE_A, encoding="utf-8")
        (source / "b.txt").write_text(NOTE_B, encoding="utf-8")
        before = _snapshot(tmp_path)

        first = read_sample_note(source / "a.txt")
        second = read_sample_note(source / "b.txt")
        draft = learn_style_profile([first, second])

        assert first.sample_text == NOTE_A and first.source_path == source / "a.txt"
        assert second.source_path == source / "b.txt"
        assert draft.source_paths == (source / "a.txt", source / "b.txt")
        assert _snapshot(tmp_path) == before, "the learner wrote or copied something"

    def test_pasted_text_has_no_path_and_carriage_returns_are_folded(self) -> None:
        note = read_sample_note("C/O: pain\r\nKeep the neck moving gently.\r")
        assert note.source_path is None
        assert note.sample_text == "C/O: pain\nKeep the neck moving gently.\n"
        assert learn_style_profile([note]).source_paths == ()

    def test_a_bom_and_a_cp1252_file_both_read(self, tmp_path: Path) -> None:
        bom = tmp_path / "bom.txt"
        bom.write_bytes(b"\xef\xbb\xbfKeep the neck moving.")
        assert read_sample_note(bom).sample_text == "Keep the neck moving."
        legacy = tmp_path / "legacy.txt"
        # 0x96 is cp1252's en dash and is NOT valid UTF-8, so the reader's
        # cp1252 fallback is what decodes it.
        legacy.write_bytes(b"Keep the neck moving \x96 gently.")
        assert "\u2013" in read_sample_note(legacy).sample_text

    @pytest.mark.parametrize(
        ("name", "size", "fragment"),
        [
            ("scan.pdf", 4, "not a .txt or .docx"),
            ("empty.txt", 0, "no text to learn from"),
            ("blank.txt", 5, "no text to learn from"),
            # Built inside the test: an oversized payload in the id would
            # overflow PYTEST_CURRENT_TEST.
            ("big.txt", MAX_SAMPLE_NOTE_BYTES + 1, "too large"),
        ],
        ids=["pdf", "empty", "blank", "oversized"],
    )
    def test_refusals_name_their_reason(
        self, tmp_path: Path, name: str, size: int, fragment: str
    ) -> None:
        path = tmp_path / name
        if name == "scan.pdf":
            payload = b"%PDF"
        elif name == "blank.txt":
            payload = b"  \n\t "
        else:
            payload = b"x" * size
        path.write_bytes(payload)
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert fragment in str(exc.value)

    def test_a_missing_file_and_empty_pasted_text_are_refused(self, tmp_path: Path) -> None:
        with pytest.raises(SampleNoteError):
            read_sample_note(tmp_path / "absent.txt")
        with pytest.raises(SampleNoteError):
            read_sample_note("   ")

    def test_sample_text_never_appears_in_a_repr(self) -> None:
        note = SampleNote("Zebra secret line", Path("C:/x/a.txt"))
        assert "Zebra" not in repr(note)

    def test_a_docx_is_read_paragraphs_then_table_cells(self, tmp_path: Path) -> None:
        docx = pytest.importorskip("docx", reason="python-docx is not installed")
        path = tmp_path / "note.docx"
        document = docx.Document()
        document.add_paragraph("C/O: Neck pain for three days.")
        document.add_paragraph(KEPT_1)
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Plan"
        table.cell(0, 1).text = KEPT_2
        document.save(str(path))
        before = _snapshot(tmp_path)

        note = read_sample_note(path)

        assert note.sample_text.split("\n") == [
            "C/O: Neck pain for three days.",
            KEPT_1,
            "Plan",
            KEPT_2,
        ]
        assert _snapshot(tmp_path) == before
        draft = learn_style_profile([note])
        assert draft.section_order == ("presenting_complaint", "management_plan")

    def test_a_docx_that_is_not_one_is_refused_by_name(self, tmp_path: Path) -> None:
        """Refused by the zip pre-check (PR-MED-020) before python-docx is
        even imported — so this needs no ``docx``."""
        path = tmp_path / "broken.docx"
        path.write_bytes(b"not a zip")
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "broken.docx" in str(exc.value) and "not a Word document" in str(exc.value)

    def _forbid_document(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whatever ``docx`` is installed, ``Document`` must not be reached."""

        def inflated(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("python-docx was asked to inflate the package")

        monkeypatch.setitem(sys.modules, "docx", SimpleNamespace(Document=inflated))

    def test_a_docx_declaring_more_than_the_bound_is_refused_before_inflating(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 17 PR-MED-020: the package's DECLARED sizes are checked
        from the central directory alone; a member over the per-member bound,
        a total over the package bound, or too many members refuses the file
        by name and python-docx never inflates anything."""
        self._forbid_document(monkeypatch)
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBER_BYTES", 1_000)
        monkeypatch.setattr(sample_notes, "MAX_DOCX_DECLARED_BYTES", 2_500)
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBERS", 4)

        big_member = tmp_path / "member.docx"
        with zipfile.ZipFile(big_member, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"0" * 4_000)  # tiny on disk, 4 000 declared
        assert big_member.stat().st_size < 1_000
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(big_member)
        assert "member.docx" in str(exc.value)
        assert "one part of the document package is more than 4,000 bytes" in str(exc.value)

        big_total = tmp_path / "total.docx"
        with zipfile.ZipFile(big_total, "w", zipfile.ZIP_DEFLATED) as archive:
            for index in range(3):
                archive.writestr(f"word/part{index}.xml", b"0" * 900)
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(big_total)
        assert "the document package is more than 2,700 bytes" in str(exc.value)

        many = tmp_path / "many.docx"
        with zipfile.ZipFile(many, "w", zipfile.ZIP_DEFLATED) as archive:
            for index in range(5):
                archive.writestr(f"word/p{index}.xml", b"x")
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(many)
        assert "holds 5 parts" in str(exc.value)

    @staticmethod
    def _patch_central_directory(path: Path, *, offset: int, value: bytes) -> None:
        """Overwrite bytes INSIDE the (single) central-directory header of a
        one-member archive — the field at ``offset`` from the header's start.
        The local header is left alone: the lie is the directory's."""
        blob = bytearray(path.read_bytes())
        start = blob.rfind(b"PK\x01\x02")
        assert start > 0
        blob[start + offset : start + offset + len(value)] = value
        path.write_bytes(bytes(blob))

    @staticmethod
    def _record_reads(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
        """Record the ``n`` this module passes to every member read — the
        REQUEST invariant (never ``-1``); the stdlib rounds it to its 4 KiB
        floor before handing it to the decompressor as ``max_length``
        (PR-LOW-027 / PR-LOW-031)."""
        asked: list[Any] = []
        real_read = zipfile.ZipExtFile.read

        def recording_read(self: Any, n: Any = -1) -> bytes:
            asked.append(n)
            return real_read(self, n)

        monkeypatch.setattr(zipfile.ZipExtFile, "read", recording_read)
        return asked

    def _understated(self, tmp_path: Path, name: str, *, forge_crc: bool) -> Path:
        """A deflated 4 000-byte member whose central directory claims 10
        bytes — optionally with the CRC forged to match those 10 bytes so the
        stdlib's own consistency check cannot be the tripwire."""
        path = tmp_path / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"0" * 4_000)
        # Central-directory offsets: CRC-32 at 16, uncompressed size at 24 (LE).
        self._patch_central_directory(path, offset=24, value=(10).to_bytes(4, "little"))
        if forge_crc:
            crc = zlib.crc32(b"0" * 10).to_bytes(4, "little")
            self._patch_central_directory(path, offset=16, value=crc)
        assert zipfile.ZipFile(path).infolist()[0].file_size == 10  # the lie is in place
        return path

    def test_every_member_read_carries_the_allocation_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 18 PR-LOW-027, the request invariant: this module never
        asks the stdlib for an unbounded read — every member read passes
        ``MAX_DOCX_MEMBER_BYTES + 1`` as ``n``. What the decompressor is then
        allowed per call is ``max(n, 4096)`` (PR-LOW-031); that allowance is
        observed separately below."""
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBER_BYTES", 1_000)
        asked = self._record_reads(monkeypatch)
        monkeypatch.setitem(
            sys.modules,
            "docx",
            SimpleNamespace(
                Document=lambda package: SimpleNamespace(
                    paragraphs=[SimpleNamespace(text=KEPT_1)], tables=[]
                )
            ),
        )
        path = tmp_path / "three.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for index in range(3):
                archive.writestr(f"word/p{index}.xml", b"0" * 900)
        read_sample_note(path)
        assert asked == [1_001, 1_001, 1_001]

    def test_an_understated_declared_size_is_refused_by_name_and_never_inflated_past_the_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A directory that UNDERSTATES a member's size passes the declared
        check; the capped request bounds the decompressor's allowance to
        ``max(1 001, 4 096)`` bytes, the stdlib returns at most the declared
        bytes and refuses the CRC mismatch — a named refusal, python-docx
        never reached."""
        self._forbid_document(monkeypatch)
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBER_BYTES", 1_000)
        asked = self._record_reads(monkeypatch)
        path = self._understated(tmp_path, "liar.docx", forge_crc=False)
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "liar.docx" in str(exc.value)
        assert "not a Word document (BadZipFile)" in str(exc.value)
        assert asked == [1_001]  # the one read was capped

    def test_an_understated_size_with_a_forged_crc_yields_only_the_declared_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With the CRC forged to match, the stdlib's check cannot fire: the
        member is truncated to its DECLARED 10 bytes, the package handed to
        python-docx holds exactly those, and the request stayed capped (the
        4 000 real bytes fit one ``max(1 001, 4 096)`` allowance here — the
        allocation bound itself is observed in the decompressor test)."""
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBER_BYTES", 1_000)
        asked = self._record_reads(monkeypatch)
        packages: list[bytes] = []

        def document(package: Any) -> Any:
            packages.append(package.getvalue())
            return SimpleNamespace(paragraphs=[SimpleNamespace(text=KEPT_1)], tables=[])

        monkeypatch.setitem(sys.modules, "docx", SimpleNamespace(Document=document))
        path = self._understated(tmp_path, "forged.docx", forge_crc=True)
        read_sample_note(path)
        assert asked == [1_001]
        with zipfile.ZipFile(io.BytesIO(packages[0])) as copied:
            assert copied.read("word/document.xml") == b"0" * 10

    def test_the_decompressor_allowance_is_the_cap_plus_its_sentinel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-LOW-031, the allocation bound observed where it is enforced:
        with a cap above the stdlib's 4 096-byte floor, every ``decompress``
        call's ``max_length`` equals ``MAX_DOCX_MEMBER_BYTES + 1``."""
        cap = 8_192
        monkeypatch.setattr(sample_notes, "MAX_DOCX_MEMBER_BYTES", cap)
        allowances: list[int] = []
        real_decompressobj = zlib.decompressobj

        class _Recording:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self._inner = real_decompressobj(*args, **kwargs)

            def decompress(self, data: bytes, max_length: int = 0) -> bytes:
                allowances.append(max_length)
                return self._inner.decompress(data, max_length)

            def __getattr__(self, name: str) -> Any:
                return getattr(self._inner, name)

        monkeypatch.setattr(zlib, "decompressobj", _Recording)
        monkeypatch.setitem(
            sys.modules,
            "docx",
            SimpleNamespace(
                Document=lambda package: SimpleNamespace(
                    paragraphs=[SimpleNamespace(text=KEPT_1)], tables=[]
                )
            ),
        )
        path = tmp_path / "wide.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"0" * 20_000)  # over the cap once inflated
        with pytest.raises(SampleNoteError):
            read_sample_note(path)  # refused at the directory stage: 20 000 declared > cap
        assert allowances == []  # nothing was inflated for a refused directory

        small = tmp_path / "narrow.docx"
        with zipfile.ZipFile(small, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"0" * 6_000)
        read_sample_note(small)
        assert allowances and all(allowance == cap + 1 for allowance in allowances)

    def test_an_encrypted_member_is_refused_by_name_before_any_open(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Peer round 19 PR-LOW-030: the encryption flag bit is refused at the
        directory stage, so the stdlib's password ``RuntimeError`` is never
        reached and python-docx never inflates anything."""
        self._forbid_document(monkeypatch)
        path = tmp_path / "locked.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")
        # General-purpose flags at offset 8; bit 0x1 = encrypted.
        self._patch_central_directory(path, offset=8, value=(0x0001).to_bytes(2, "little"))
        assert zipfile.ZipFile(path).infolist()[0].flag_bits & 0x1  # the flag is in place
        # The recorder goes in AFTER the fixture is written: ``writestr`` opens
        # the member for WRITING through the same method, and that open is the
        # fixture's, not the module's.
        opened: list[Any] = []
        real_open = zipfile.ZipFile.open

        def recording_open(self: Any, *args: Any, **kwargs: Any) -> Any:
            opened.append(args)
            return real_open(self, *args, **kwargs)

        monkeypatch.setattr(zipfile.ZipFile, "open", recording_open)
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "locked.docx" in str(exc.value)
        assert "not a Word document (a part is encrypted)" in str(exc.value)
        assert opened == []  # refused at the directory stage: no member was opened

    def test_corrupt_deflate_data_is_refused_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-LOW-030: a ``zlib.error`` from the decompressor inside the
        member read is translated narrowly into the named refusal."""
        self._forbid_document(monkeypatch)
        path = tmp_path / "corrupt.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"0" * 4_000)
        blob = bytearray(path.read_bytes())
        # The local header is 30 bytes + the name; corrupt the first
        # compressed bytes right after it.
        start = 30 + len("word/document.xml")
        blob[start : start + 4] = b"\xff\xff\xff\xff"
        path.write_bytes(bytes(blob))
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "corrupt.docx" in str(exc.value)
        assert "not a Word document (" in str(exc.value)
        assert "zlib.error" in str(exc.value) or "error" in str(exc.value)

    def test_a_programming_error_inside_the_pre_check_is_not_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-LOW-030's regression note: the boundary names input failures
        only — an ``AttributeError`` raised inside it propagates as a bug."""
        self._forbid_document(monkeypatch)
        path = tmp_path / "fine.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")

        def broken(self: Any, *args: Any, **kwargs: Any) -> Any:
            raise AttributeError("a bug in the pre-check")

        # Installed AFTER the fixture is written (``writestr`` opens for
        # writing through the same method), so only the module's read trips it.
        monkeypatch.setattr(zipfile.ZipFile, "open", broken)
        with pytest.raises(AttributeError, match="a bug in the pre-check"):
            read_sample_note(path)

    def test_an_unsupported_compression_method_is_refused_by_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._forbid_document(monkeypatch)
        path = tmp_path / "bz.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_BZIP2) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "bz.docx" in str(exc.value)
        assert f"compression method {zipfile.ZIP_BZIP2}" in str(exc.value)

    @pytest.mark.parametrize(
        ("patch", "expected"),
        [
            # General-purpose flag bit 0x800 (offset 8) + a name byte that is
            # not UTF-8 (the name starts at offset 46 in the directory header).
            pytest.param(
                ((8, (0x0800).to_bytes(2, "little")), (46, b"\xff")),
                "UnicodeDecodeError",
                id="invalid-utf8-name",
            ),
            # extract_version (offset 6) above MAX_EXTRACT_VERSION.
            pytest.param(((6, bytes([99])),), "NotImplementedError", id="extract-version"),
        ],
    )
    def test_malformed_directory_metadata_is_refused_by_name(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        patch: tuple[tuple[int, bytes], ...],
        expected: str,
    ) -> None:
        """Peer round 18 PR-LOW-028: the two stdlib raises that are neither
        ``BadZipFile`` nor ``OSError`` reach the tab as a named refusal, not
        an untyped exception."""
        self._forbid_document(monkeypatch)
        path = tmp_path / "meta.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")
        for offset, value in patch:
            self._patch_central_directory(path, offset=offset, value=value)
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "meta.docx" in str(exc.value)
        assert f"not a Word document ({expected})" in str(exc.value)

    def test_a_docx_inside_the_bounds_reaches_the_library_as_an_in_memory_package(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The pre-check admits a package inside every bound and only then
        hands ``Document`` (a stand-in that records the call) the bounded
        IN-MEMORY re-zip — never the chosen file — holding the same members."""
        calls: list[tuple[type, bytes]] = []

        def document(package: Any) -> Any:
            # The module closes the buffer once the library has parsed it, so
            # its bytes are snapshotted HERE, inside the call.
            calls.append((type(package), package.getvalue()))
            return SimpleNamespace(
                paragraphs=[SimpleNamespace(text="Plan"), SimpleNamespace(text=KEPT_1)],
                tables=[],
            )

        monkeypatch.setitem(sys.modules, "docx", SimpleNamespace(Document=document))
        path = tmp_path / "small.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")
            archive.writestr("word/media/", b"")
            archive.writestr("word/media/image1.png", b"\x89PNG")
        note = read_sample_note(path)
        assert len(calls) == 1
        kind, blob = calls[0]
        assert kind is io.BytesIO
        with zipfile.ZipFile(io.BytesIO(blob)) as copied:
            assert {i.filename: copied.read(i.filename) for i in copied.infolist()} == {
                "word/document.xml": b"<w:document/>",
                "word/media/image1.png": b"\x89PNG",
            }
            assert all(i.compress_type == zipfile.ZIP_STORED for i in copied.infolist())
        assert note.sample_text == f"Plan\n{KEPT_1}"

    def test_docx_text_is_bounded_while_it_is_collected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-MED-020's second half: the text limit applies during collection,
        so a package inside the size bounds cannot accumulate more text than a
        note before it is refused."""
        monkeypatch.setattr(sample_notes, "MAX_SAMPLE_NOTE_CHARS", 20)
        seen: list[int] = []

        class _Paragraph:
            def __init__(self, text: str) -> None:
                self._text = text

            @property
            def text(self) -> str:
                seen.append(len(self._text))
                return self._text

        paragraphs = [_Paragraph("x" * 15), _Paragraph("y" * 15), _Paragraph("z" * 15)]
        monkeypatch.setitem(
            sys.modules,
            "docx",
            SimpleNamespace(
                Document=lambda path: SimpleNamespace(paragraphs=paragraphs, tables=[])
            ),
        )
        path = tmp_path / "long.docx"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<w:document/>")
        with pytest.raises(SampleNoteError) as exc:
            read_sample_note(path)
        assert "more than 20 characters of text" in str(exc.value)
        assert seen == [15, 15]  # refused at the second paragraph, the third never read


# --- learning ----------------------------------------------------------------


class TestLearnStyleProfile:
    def test_one_to_five_notes(self) -> None:
        with pytest.raises(SampleNoteError):
            learn_style_profile([])
        with pytest.raises(SampleNoteError):
            learn_style_profile([SampleNote(NOTE_A)] * (MAX_SAMPLE_NOTES + 1))
        assert learn_style_profile([SampleNote(NOTE_A)] * MAX_SAMPLE_NOTES).source_count == 5

    def test_headings_map_to_sections_in_order_of_first_appearance(self) -> None:
        draft = _draft(NOTE_A, NOTE_B)
        assert draft.section_order == (
            "presenting_complaint",
            "objective_examination",
            "treatment_performed",
            "management_plan",
            "assessment",
        )
        assert draft.heading_labels == {
            "presenting_complaint": "C/O",
            "objective_examination": "O/E",
            "treatment_performed": "Rx",
            "management_plan": "Plan",
            "assessment": "Assessment",
        }
        # A later note's different order does not reorder what came first.
        assert _draft(NOTE_B, NOTE_A).section_order[:2] == ("assessment", "presenting_complaint")

    def test_exemplars_are_the_sentences_the_filter_passed_unchanged(self) -> None:
        draft = _draft(NOTE_A)
        # Round-robin across the sections in order of first appearance:
        # C/O [KEPT_1], O/E [KEPT_2, KEPT_3], Rx [KEPT_4, KEPT_5], Plan [].
        assert [e.exemplar_text for e in draft.exemplars] == [
            KEPT_1, KEPT_2, KEPT_4, KEPT_3, KEPT_5
        ]
        assert [e.section_key for e in draft.exemplars] == [
            "presenting_complaint",
            "objective_examination",
            "treatment_performed",
            "objective_examination",
            "treatment_performed",
        ]
        evidence = sample_notes._evidence([SampleNote(NOTE_A)])
        assert {"neck", "as", "review"} & evidence == {"neck", "as"}  # "Review" only capitalised
        for sentence, expected in REFUSED.items():
            assert (
                refuse_learning_candidate(
                    sentence.split(), first_in_segment=True, known_common=evidence
                )
                == expected
            ), sentence
        kept_lower = {e.exemplar_text.casefold() for e in draft.exemplars}
        for sentence in REFUSED:
            # Dropped whole: neither the sentence nor a re-cased or trimmed
            # form of it was kept (C5: refuse, never edit).
            assert sentence.casefold() not in kept_lower
            assert not any(sentence.casefold()[:12] in kept for kept in kept_lower)
        assert draft.refused_exemplars == {"name": 4, "number": 2, "medication": 1}
        # Every body sentence sits under a heading and none is over-long, so
        # nothing was left out for a reason other than the filter.
        assert draft.dropped_exemplars == 0

    def test_the_evidence_rule_admits_only_a_word_seen_in_lowercase(self) -> None:
        """Task 3.7 rule (b), end to end: the same sentence is kept when the
        notes also carry the word in lowercase and refused when they do not;
        a mid-sentence capitalised word is refused either way."""
        with_evidence = _draft("Plan\nReview the neck next week.\nBook a review for the knee.")
        assert [e.exemplar_text for e in with_evidence.exemplars] == ["Review the neck next week."]
        without = _draft("Plan\nReview the neck next week.\nKeep the knee moving.")
        assert [e.exemplar_text for e in without.exemplars] == ["Keep the knee moving."]
        assert without.refused_exemplars == {"name": 1}
        mid = _draft("Plan\nKeep the Review sheet handy.\nBook a review for the knee.")
        assert [e.exemplar_text for e in mid.exemplars] == []
        assert mid.refused_exemplars == {"name": 2}  # "Book" is unlisted too

    def test_a_heading_the_profile_would_refuse_is_not_a_heading(self) -> None:
        """Round 15 LOW-001: a heading label carrying a format control (a
        zero-width space here) would fail ``StyleProfile``'s label rule at
        Save; the parser refuses it as a heading instead, so its lines stay
        unsectioned and the Save can never trip on a label."""
        draft = _draft("Plan​\nKeep the neck moving gently.")
        assert draft.section_order == ()
        assert draft.heading_labels == {}
        assert draft.exemplars == ()
        assert draft.dropped_exemplars == 1
        # The same note with a clean heading keeps the sentence.
        clean = _draft("Plan\nKeep the neck moving gently.")
        assert [e.exemplar_text for e in clean.exemplars] == ["Keep the neck moving gently."]

    def test_text_before_any_heading_is_never_an_exemplar(self) -> None:
        draft = _draft("Keep the neck moving gently.\nPlan\nRest the shoulder for now.")
        assert [e.exemplar_text for e in draft.exemplars] == ["Rest the shoulder for now."]
        assert draft.dropped_exemplars == 1

    def test_shorthand_is_split_by_the_controlled_vocabulary(self) -> None:
        draft = _draft(NOTE_A)
        assert draft.recognised_shorthand == ("ROM", "NAD", "HVLA", "Cx")
        assert draft.unrecognised_shorthand == ("QWERTY",)
        for token in ("L4", "C5/6", "Pt", "Review", "AS", "as"):
            assert token not in draft.unrecognised_shorthand
            assert token not in draft.recognised_shorthand  # "as" is not the abbreviation AS
        lowercase = _draft("Plan\nhvla applied to the cx spine.")
        assert lowercase.recognised_shorthand == ()  # exact, case-preserving match only

    def test_the_exemplar_cap_spreads_across_sections(self) -> None:
        words = [
            "gently", "slowly", "often", "daily", "carefully", "lightly", "softly", "briefly",
            "evenly", "steadily", "calmly", "freely", "loosely", "quietly", "smoothly",
            "regularly", "patiently", "warmly", "safely", "easily",
        ]
        first = "\n".join(["C/O", *(f"Keep the neck moving {word}." for word in words)])
        second = "\n".join(["Plan", *(f"Continue with the {word} programme." for word in words)])
        draft = _draft(first + "\n" + second)
        assert len(draft.exemplars) == MAX_STYLE_EXEMPLARS
        by_section = [e.section_key for e in draft.exemplars]
        assert by_section.count("presenting_complaint") == 15
        assert by_section.count("management_plan") == 15
        assert draft.dropped_exemplars == 10
        assert draft.refused_exemplars == {}

    def test_measures_are_simple_counts(self) -> None:
        third_past = _draft("O/E\nPt reported pain. She was seen. He had tenderness.")
        assert third_past.measures.person == "third"
        assert third_past.measures.tense == "past"
        first_present = _draft("Plan\nI advise rest. We continue with treatment. My plan is easy.")
        assert first_present.measures.person == "first"
        assert first_present.measures.tense == "present"
        draft = _draft("Plan\nKeep the neck moving gently. Continue with the home programme now.")
        assert draft.measures.mean_sentence_words == 5.5
        assert 0.0 <= draft.measures.abbreviation_ratio <= 1.0
        unknown = _draft("Plan\nfoo bar baz")
        assert unknown.measures.person == "unknown" and unknown.measures.tense == "unknown"

    def test_the_draft_repr_carries_a_tripwire_marker(self) -> None:
        draft = _draft(NOTE_A)
        assert any(sig in repr(draft) for sig in _PAYLOAD_SIGNATURES)
        assert KEPT_1 not in repr(draft)  # the exemplars are repr-hidden too

    def test_the_learner_supplies_the_filter_only_the_lowercase_evidence(self) -> None:
        """The evidence set holds words seen in LOWERCASE only — a word seen
        capitalised never admits itself, and digits or punctuation-only
        tokens contribute nothing."""
        evidence = sample_notes._evidence([SampleNote("Review 12/03 (pain), neck. NAD - ok.")])
        assert evidence == frozenset({"pain", "neck", "ok"})


# --- building the profile ----------------------------------------------------


class TestBuildStyleProfile:
    def test_recognised_plus_ticked_tokens_and_the_kept_exemplars(self) -> None:
        draft = _draft(NOTE_A)
        profile = build_style_profile(
            draft,
            kept_unrecognised=("QWERTY",),
            kept_exemplars=(draft.exemplars[1],),
            consent=_consent(),
            learned_at=NOW,
        )
        assert profile.shorthand == ("ROM", "NAD", "HVLA", "Cx", "QWERTY")
        assert profile.exemplars == (draft.exemplars[1],)
        assert profile.section_order == draft.section_order
        assert profile.heading_labels == draft.heading_labels
        assert profile.measures == draft.measures
        assert profile.source_count == 1
        assert models.consent_is_current(profile)

    def test_an_unticked_unrecognised_token_is_not_saved(self) -> None:
        draft = _draft(NOTE_A)
        profile = build_style_profile(
            draft, kept_unrecognised=(), kept_exemplars=draft.exemplars,
            consent=_consent(), learned_at=NOW,
        )
        assert "QWERTY" not in profile.shorthand
        assert profile.exemplars == draft.exemplars

    def test_the_review_may_only_remove(self) -> None:
        draft = _draft(NOTE_A)
        with pytest.raises(SampleNoteError, match="not offered"):
            build_style_profile(
                draft, kept_unrecognised=("ZZZ",), kept_exemplars=(),
                consent=_consent(), learned_at=NOW,
            )
        edited = StyleExemplar(section_key="presenting_complaint", exemplar_text="Keep the neck.")
        with pytest.raises(SampleNoteError, match="not offered"):
            build_style_profile(
                draft, kept_unrecognised=(), kept_exemplars=(edited,),
                consent=_consent(), learned_at=NOW,
            )
        moved = StyleExemplar(section_key="assessment", exemplar_text=KEPT_1)
        with pytest.raises(SampleNoteError, match="not offered"):
            build_style_profile(
                draft, kept_unrecognised=(), kept_exemplars=(moved,),
                consent=_consent(), learned_at=NOW,
            )


# --- deleting the originals ----------------------------------------------------


class TestDeleteSampleFiles:
    def test_exactly_the_listed_paths_go(self, tmp_path: Path) -> None:
        keep = tmp_path / "keep.txt"
        folder = tmp_path / "folder"
        folder.mkdir()
        inside = folder / "inside.txt"
        for path in (tmp_path / "a.txt", tmp_path / "b.txt", keep, inside):
            path.write_text("x", encoding="utf-8")

        report = delete_sample_files([tmp_path / "a.txt", tmp_path / "b.txt", folder])

        assert report.deleted == (tmp_path / "a.txt", tmp_path / "b.txt")
        assert report.failed == ((folder, "is a folder, not a note"),)
        assert not (tmp_path / "a.txt").exists() and not (tmp_path / "b.txt").exists()
        assert keep.exists() and inside.exists()

    def test_a_file_already_gone_counts_as_deleted(self, tmp_path: Path) -> None:
        report = delete_sample_files([tmp_path / "gone.txt"])
        assert report.deleted == (tmp_path / "gone.txt",) and report.failed == ()


class TestTripwire:
    def test_the_three_markers_are_registered(self) -> None:
        for marker in ("sample_text", "recognised_shorthand", "unrecognised_shorthand"):
            assert f'"{marker}"' in _PAYLOAD_SIGNATURES
            assert f"{marker}=" in _PAYLOAD_SIGNATURES
