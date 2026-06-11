"""Unit tests for the ingestion pipeline.

Chunking is tested directly (no infra). The full ingest_document flow is tested
against a SQLite documents table with the embedding + Qdrant steps stubbed, so
status transitions and re-ingest idempotency are verified without standing up
Qdrant or downloading the ONNX model.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import ingestion
from app.config import get_settings
from app.models import Base, Document
from app.parsing import PageText


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    monkeypatch.setattr("app.ingestion.get_engine", lambda: eng)
    yield eng
    get_settings.cache_clear()


def test_chunk_blocks_preserves_page_and_indexes() -> None:
    blocks = [
        PageText(text="First page sentence. " * 50, page=1),
        PageText(text="Second page sentence. " * 50, page=2),
    ]
    chunks = ingestion.chunk_blocks(blocks)

    assert len(chunks) >= 2
    # chunk_index is a unique running counter across the document
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # a chunk never straddles a page boundary: pages stay with their source block
    pages = {c.page for c in chunks}
    assert pages == {1, 2}
    assert all(c.text.strip() for c in chunks)


def test_chunk_blocks_passthrough_for_pageless_text() -> None:
    chunks = ingestion.chunk_blocks([PageText(text="short note", page=None)])
    assert len(chunks) == 1
    assert chunks[0].page is None
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "short note"


def _seed_doc(engine: Engine, filename: str, body: bytes) -> int:
    with Session(engine) as session:
        doc = Document(
            filename=filename, status="uploaded", size_bytes=len(body), mime="text/plain"
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.id
    from app.documents import stored_path

    dest = stored_path(doc_id, filename)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return doc_id


def test_ingest_document_marks_ready(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_upsert(doc_id: str, filename: str, chunks: list[ingestion.Chunk]) -> int:
        captured["doc_id"] = doc_id
        captured["filename"] = filename
        captured["chunks"] = chunks
        return len(chunks)

    monkeypatch.setattr(ingestion, "ensure_collection", lambda: None)
    monkeypatch.setattr(ingestion, "delete_doc_vectors", lambda doc_id: None)
    monkeypatch.setattr(ingestion, "_upsert_chunks", fake_upsert)

    doc_id = _seed_doc(engine, "notes.md", b"# Title\n\nThis is the body of the note.")
    ingestion.ingest_document(doc_id)

    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        assert doc is not None
        assert doc.status == "ready"
        assert doc.error is None
    assert captured["doc_id"] == str(doc_id)
    assert captured["filename"] == "notes.md"


def test_ingest_document_corrupt_pdf_marks_failed(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ingestion, "ensure_collection", lambda: None)
    monkeypatch.setattr(ingestion, "delete_doc_vectors", lambda doc_id: None)
    monkeypatch.setattr(ingestion, "_upsert_chunks", lambda *a: 0)

    doc_id = _seed_doc(engine, "broken.pdf", b"definitely not a pdf")
    ingestion.ingest_document(doc_id)

    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        assert doc is not None
        assert doc.status == "failed"
        assert doc.error  # human-readable reason stored
        assert "pdf" in doc.error.lower()


def test_ingest_document_empty_result_marks_failed(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ingestion, "ensure_collection", lambda: None)
    monkeypatch.setattr(ingestion, "delete_doc_vectors", lambda doc_id: None)
    monkeypatch.setattr(ingestion, "_upsert_chunks", lambda *a: 0)
    # Chunking yields zero chunks (e.g. whitespace-only after split).
    monkeypatch.setattr(ingestion, "chunk_blocks", lambda blocks: [])

    doc_id = _seed_doc(engine, "notes.txt", b"some text")
    ingestion.ingest_document(doc_id)

    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        assert doc is not None
        assert doc.status == "failed"
        assert "no text chunks" in (doc.error or "").lower()


def test_reingest_deletes_old_vectors_first(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second ingest of the same doc deletes prior vectors before writing."""
    calls: list[str] = []

    monkeypatch.setattr(ingestion, "ensure_collection", lambda: None)
    monkeypatch.setattr(ingestion, "delete_doc_vectors", lambda doc_id: calls.append("delete"))
    monkeypatch.setattr(
        ingestion, "_upsert_chunks", lambda *a: (calls.append("upsert"), 1)[1]
    )

    doc_id = _seed_doc(engine, "notes.md", b"hello world body text here")
    ingestion.ingest_document(doc_id)
    ingestion.ingest_document(doc_id)

    # Every ingest deletes before upserting.
    assert calls == ["delete", "upsert", "delete", "upsert"]


def test_ingest_missing_document_is_noop(engine: Engine) -> None:
    # Should not raise even though no such row / file exists.
    ingestion.ingest_document(99999)
