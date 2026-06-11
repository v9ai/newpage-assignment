"""Ingestion pipeline: parsed document -> chunks -> embeddings -> Qdrant.

Drives the `uploaded -> ingesting -> ready | failed` status transitions on the
`documents` row and writes one Qdrant point per chunk with the payload the
retrieval side reads:

    { doc_id, filename, page, chunk_index, text }

Chunking is sentence-aware (LlamaIndex `SentenceSplitter`, size/overlap from
config). Embeddings use the local FastEmbed `BAAI/bge-small-en-v1.5` model
(384-dim ONNX on CPU) — the *same* model query embedding uses in retrieval.py,
so vectors are directly comparable. We talk to Qdrant through `qdrant_client`
directly rather than LlamaIndex's vector store so the point payload matches the
flat shape retrieval expects exactly. Re-ingesting a document deletes its prior
vectors (by `doc_id` filter) before writing new ones, so it is idempotent.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING
from uuid import uuid4

import structlog
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_engine
from app.models import Document
from app.parsing import PageText, ParseError, parse_file
from app.vectorstore import ensure_collection, get_qdrant

if TYPE_CHECKING:
    from fastembed import TextEmbedding

log = structlog.get_logger()


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None
    chunk_index: int


@lru_cache
def _embedder() -> "TextEmbedding":
    """Construct the FastEmbed model once; downloads ONNX weights on first use.

    Mirrors retrieval._embedder so ingestion and query share identical vectors.
    """
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=get_settings().embed_model)


def warmup() -> None:
    """Force the embedding model to load (and download if needed) up front.

    Called at app startup so the first upload never pays a surprise model
    download. Embedding a tiny string materialises the ONNX session.
    """
    list(_embedder().embed(["warmup"]))
    log.info("embedding_model_ready", model=get_settings().embed_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts to 384-dim vectors."""
    model = _embedder()
    return [[float(x) for x in vec] for vec in model.embed(texts)]


def chunk_blocks(blocks: list[PageText], settings: Settings | None = None) -> list[Chunk]:
    """Split `{text, page}` blocks into sentence-aware chunks with provenance.

    Each block is chunked independently so a chunk never straddles a page
    boundary and its `page` stays meaningful. `chunk_index` is a single running
    counter across the whole document (stable, unique per doc).
    """
    from llama_index.core.node_parser import SentenceSplitter

    settings = settings or get_settings()
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[Chunk] = []
    index = 0
    for block in blocks:
        for piece in splitter.split_text(block.text):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(Chunk(text=piece, page=block.page, chunk_index=index))
            index += 1
    return chunks


def delete_doc_vectors(doc_id: str) -> None:
    """Remove any existing vectors for this document (makes re-ingest idempotent)."""
    client = get_qdrant()
    client.delete(
        collection_name=get_settings().qdrant_collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )
        ),
    )


def _upsert_chunks(doc_id: str, filename: str, chunks: list[Chunk]) -> int:
    """Embed and write chunks as Qdrant points; returns the count written."""
    if not chunks:
        return 0
    vectors = embed_texts([c.text for c in chunks])
    settings = get_settings()
    points = [
        PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload={
                "doc_id": doc_id,
                "filename": filename,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    get_qdrant().upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def ingest_document(doc_id: int) -> None:
    """Full pipeline for one document, with status transitions and failure capture.

    Safe to run as a FastAPI background task: every failure mode (parse error,
    embedding/Qdrant error) lands the document in `failed` with a stored,
    human-readable reason rather than raising out of the task.
    """
    with Session(get_engine()) as session:
        doc = session.get(Document, doc_id)
        if doc is None:
            log.warning("ingest_missing_document", doc_id=doc_id)
            return
        filename = doc.filename
        doc.status = "ingesting"
        doc.error = None
        session.commit()

    try:
        from app.documents import stored_path

        blocks = parse_file(stored_path(doc_id, filename))
        chunks = chunk_blocks(blocks)
        ensure_collection()
        delete_doc_vectors(str(doc_id))
        count = _upsert_chunks(str(doc_id), filename, chunks)
    except ParseError as exc:
        _mark_failed(doc_id, str(exc))
        return
    except Exception as exc:
        log.exception("ingest_failed", doc_id=doc_id)
        _mark_failed(doc_id, f"Ingestion failed: {exc}")
        return

    if count == 0:
        _mark_failed(doc_id, "No text chunks were produced from this document.")
        return

    with Session(get_engine()) as session:
        doc = session.get(Document, doc_id)
        if doc is not None:
            doc.status = "ready"
            doc.error = None
            session.commit()
    log.info("ingest_ready", doc_id=doc_id, chunks=count)


def _mark_failed(doc_id: int, reason: str) -> None:
    with Session(get_engine()) as session:
        doc = session.get(Document, doc_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = reason
            session.commit()
    log.warning("ingest_marked_failed", doc_id=doc_id, reason=reason)
