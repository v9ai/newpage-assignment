"""Retrieval over the Qdrant chunk index.

Embeds the query with the same local FastEmbed model ingestion uses, then runs a
cosine search against the documents collection. Exposes POST /api/retrieve as a
transparency/debug tool so search quality is inspectable on its own, separate
from the chat engine that consumes it.
"""

from functools import lru_cache

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import Settings, get_settings
from app.vectorstore import get_qdrant

log = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["retrieval"])

# Defaults when the corresponding settings are absent; mirror the contract's
# RETRIEVAL_TOP_K / RETRIEVAL_SCORE_THRESHOLD knobs.
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.3


def retrieval_top_k(settings: Settings) -> int:
    return int(getattr(settings, "retrieval_top_k", DEFAULT_TOP_K))


def retrieval_score_threshold(settings: Settings) -> float:
    return float(getattr(settings, "retrieval_score_threshold", DEFAULT_SCORE_THRESHOLD))


@lru_cache
def _embedder() -> object:
    """Lazily construct the FastEmbed model (downloads ONNX weights on first use)."""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=get_settings().embed_model)


def embed_query(query: str) -> list[float]:
    """Embed a single query string to a 384-dim vector."""
    model = _embedder()
    # TextEmbedding.embed yields numpy arrays; one per input.
    vector = next(iter(model.embed([query])))  # type: ignore[attr-defined]
    return [float(x) for x in vector]


class RetrievedNode(BaseModel):
    text: str
    score: float
    doc_id: str
    filename: str
    page: int | None
    chunk_index: int


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int | None = Field(default=None, ge=1, le=50)


class RetrieveResponse(BaseModel):
    nodes: list[RetrievedNode]


def _payload_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return str(value) if value is not None else ""


def search(
    query: str,
    k: int | None = None,
    *,
    doc_id: str | None = None,
    apply_threshold: bool = True,
) -> list[RetrievedNode]:
    """Embed `query` and return up to `k` matching chunks, best score first.

    When `apply_threshold` is set, results below the configured score threshold
    are dropped — this is what powers the chat engine's refusal path. The raw
    /api/retrieve endpoint keeps the threshold off so search is fully inspectable.
    """
    settings = get_settings()
    top_k = k or retrieval_top_k(settings)
    client = get_qdrant()

    query_filter = None
    if doc_id is not None:
        query_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )

    hits = client.query_points(
        collection_name=settings.qdrant_collection,
        query=embed_query(query),
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    ).points

    threshold = retrieval_score_threshold(settings) if apply_threshold else 0.0
    nodes: list[RetrievedNode] = []
    for hit in hits:
        if hit.score is None or hit.score < threshold:
            continue
        payload = hit.payload or {}
        page_raw = payload.get("page")
        nodes.append(
            RetrievedNode(
                text=_payload_str(payload, "text"),
                score=float(hit.score),
                doc_id=_payload_str(payload, "doc_id"),
                filename=_payload_str(payload, "filename"),
                page=int(page_raw) if page_raw is not None else None,
                chunk_index=int(payload.get("chunk_index", 0) or 0),
            )
        )
    return nodes


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest) -> RetrieveResponse:
    """Top-k chunks for a query with scores and source metadata (debug view)."""
    nodes = search(req.query, req.k, apply_threshold=False)
    log.info("retrieve", query_len=len(req.query), returned=len(nodes))
    return RetrieveResponse(nodes=nodes)
