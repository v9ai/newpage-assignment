"""Text extraction from uploaded files, keeping page provenance for citations."""

from dataclasses import dataclass
from pathlib import Path


class ParseError(Exception):
    """Raised when a file cannot be turned into text; message is user-facing."""


@dataclass(frozen=True)
class PageText:
    text: str
    page: int | None  # None for formats without pages (txt/md)


def parse_file(path: Path) -> list[PageText]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return _parse_plaintext(path)
    if ext == ".pdf":
        return _parse_pdf(path)
    raise ParseError(f"Unsupported file type: {ext}")


def _parse_plaintext(path: Path) -> list[PageText]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        raise ParseError(f"Could not read file: {exc}") from exc
    if not text:
        raise ParseError("File contains no text.")
    return [PageText(text=text, page=None)]


def _parse_pdf(path: Path) -> list[PageText]:
    from llama_index.readers.file import PDFReader

    try:
        docs = PDFReader().load_data(path)
    except Exception as exc:
        raise ParseError(f"Could not read PDF: {exc}") from exc

    pages: list[PageText] = []
    for i, doc in enumerate(docs):
        text = (doc.text or "").strip()
        if not text:
            continue
        label = doc.metadata.get("page_label")
        try:
            page = int(label) if label is not None else i + 1
        except (TypeError, ValueError):
            page = i + 1
        pages.append(PageText(text=text, page=page))

    if not pages:
        raise ParseError("PDF contains no extractable text (it may be scanned or empty).")
    return pages
