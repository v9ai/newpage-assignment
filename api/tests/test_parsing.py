from pathlib import Path

import pytest

from app.parsing import ParseError, parse_file


def _make_pdf(text: str) -> bytes:
    """Build a minimal but fully valid single-page PDF with extractable text.

    Offsets in the xref table are computed at write time so pypdf accepts it
    (a hand-written PDF with wrong offsets / no %%EOF is rejected on read).
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\nBT /F1 24 Tf 72 720 Td (%s) Tj ET\nendstream"
        % (len(text) + 26, text.encode("ascii")),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i
        out += body
        out += b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos
    return bytes(out)


def test_markdown_extracts_text(tmp_path: Path) -> None:
    f = tmp_path / "notes.md"
    f.write_text("# Title\n\nSome content here.")
    pages = parse_file(f)
    assert len(pages) == 1
    assert "Some content here." in pages[0].text
    assert pages[0].page is None


def test_plaintext_extracts_text(tmp_path: Path) -> None:
    f = tmp_path / "notes.txt"
    f.write_text("plain body text")
    pages = parse_file(f)
    assert len(pages) == 1
    assert pages[0].text == "plain body text"
    assert pages[0].page is None


def test_empty_file_fails_with_reason(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("   \n  ")
    with pytest.raises(ParseError, match="no text"):
        parse_file(f)


def test_pdf_extracts_text_with_page(tmp_path: Path) -> None:
    f = tmp_path / "doc.pdf"
    f.write_bytes(_make_pdf("Hello DocChat"))
    pages = parse_file(f)
    assert len(pages) == 1
    assert "Hello DocChat" in pages[0].text
    assert pages[0].page == 1


def test_corrupt_pdf_fails_with_reason(tmp_path: Path) -> None:
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"this is definitely not a pdf")
    with pytest.raises(ParseError, match=r"(?i)pdf"):
        parse_file(f)


def test_unsupported_extension_fails(tmp_path: Path) -> None:
    f = tmp_path / "data.csv"
    f.write_text("a,b,c")
    with pytest.raises(ParseError, match=r"(?i)unsupported"):
        parse_file(f)
