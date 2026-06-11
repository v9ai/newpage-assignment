"""Retrieval tests.

The endpoint test mocks the vector search and runs anywhere. The round-trip test
is the unit-07 done-when: it seeds Qdrant with hand-built points carrying the
payload contract ({doc_id, filename, page, chunk_index, text}), embeds them with
the real FastEmbed model, and asserts a query returns the expected chunk. It
skips automatically when Qdrant or fastembed is unavailable (e.g. plain CI).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import retrieval
from app.main import app
from app.retrieval import RetrievedNode


def test_retrieve_endpoint_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    node = RetrievedNode(
        text="The deployment runbook lives in DEPLOYMENT.md.",
        score=0.82,
        doc_id="doc-42",
        filename="DEPLOYMENT.md",
        page=None,
        chunk_index=4,
    )
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [node])

    client = TestClient(app)
    resp = client.post("/api/retrieve", json={"query": "where is the runbook?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"][0]["doc_id"] == "doc-42"
    assert body["nodes"][0]["chunk_index"] == 4
    assert body["nodes"][0]["page"] is None


def test_retrieve_rejects_empty_query() -> None:
    client = TestClient(app)
    assert client.post("/api/retrieve", json={"query": ""}).status_code == 422


# --- live round-trip -----------------------------------------------------------


def _qdrant_available() -> bool:
    try:
        from app.vectorstore import get_qdrant

        get_qdrant().get_collections()
        return True
    except Exception:
        return False


def _fastembed_available() -> bool:
    try:
        import fastembed  # noqa: F401

        return True
    except Exception:
        return False


pytestmark_integration = pytest.mark.skipif(
    not (_qdrant_available() and _fastembed_available()),
    reason="needs a running Qdrant and the fastembed model",
)


@pytestmark_integration
def test_ingest_retrieve_roundtrip() -> None:
    from qdrant_client.models import Distance, PointStruct, VectorParams

    from app.config import get_settings
    from app.retrieval import embed_query, search
    from app.vectorstore import get_qdrant

    client = get_qdrant()
    collection = f"test_retrieval_{uuid.uuid4().hex[:8]}"
    settings = get_settings()

    passages = [
        ("doc-1", "onboarding.md", 1, 0, "New hires complete security training in week one."),
        ("doc-1", "onboarding.md", 2, 1, "Laptops are issued by IT on the first day."),
        ("doc-2", "benefits.md", 1, 0, "Vacation days accrue at 1.5 days per month worked."),
    ]
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=settings.embed_dim, distance=Distance.COSINE),
    )
    try:
        points = [
            PointStruct(
                id=i,
                vector=embed_query(text),
                payload={
                    "doc_id": doc_id,
                    "filename": filename,
                    "page": page,
                    "chunk_index": chunk_index,
                    "text": text,
                },
            )
            for i, (doc_id, filename, page, chunk_index, text) in enumerate(passages)
        ]
        client.upsert(collection_name=collection, points=points, wait=True)

        original = settings.qdrant_collection
        object.__setattr__(settings, "qdrant_collection", collection)
        try:
            nodes = search("how do vacation days accumulate?", apply_threshold=False)
        finally:
            object.__setattr__(settings, "qdrant_collection", original)

        assert nodes, "expected at least one retrieved chunk"
        top = nodes[0]
        assert top.filename == "benefits.md"
        assert "accrue" in top.text
    finally:
        client.delete_collection(collection)
