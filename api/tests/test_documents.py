from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    # Background ingestion (triggered on upload) must hit the same test engine.
    monkeypatch.setattr("app.ingestion.get_engine", lambda: engine)
    # These tests cover the HTTP/validation layer, not the embedding+Qdrant
    # pipeline, so stub the embed/store steps: parse still runs (so corrupt
    # files are detected), but no vector store is required.
    monkeypatch.setattr("app.ingestion.ensure_collection", lambda: None)
    monkeypatch.setattr("app.ingestion.delete_doc_vectors", lambda doc_id: None)
    monkeypatch.setattr("app.ingestion._upsert_chunks", lambda doc_id, fn, chunks: len(chunks))
    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_upload_list_delete_roundtrip(client: TestClient) -> None:
    res = client.post(
        "/api/documents", files={"file": ("notes.md", b"# hello docchat", "text/markdown")}
    )
    assert res.status_code == 201
    doc = res.json()
    assert doc["filename"] == "notes.md"
    assert doc["status"] == "uploaded"
    assert doc["size"] == len(b"# hello docchat")

    # TestClient runs the background ingestion task before returning, so by the
    # time we list, status has progressed past "uploaded".
    listed = client.get("/api/documents").json()
    assert [d["id"] for d in listed] == [doc["id"]]
    assert listed[0]["status"] == "ready"

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert client.get("/api/documents").json() == []


def test_unsupported_type_rejected(client: TestClient) -> None:
    res = client.post(
        "/api/documents", files={"file": ("evil.exe", b"MZ", "application/octet-stream")}
    )
    assert res.status_code == 415
    assert "Unsupported" in res.json()["detail"]


def test_oversize_rejected(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    get_settings.cache_clear()
    res = client.post("/api/documents", files={"file": ("big.txt", b"x" * 10, "text/plain")})
    assert res.status_code == 413


def test_delete_missing_404(client: TestClient) -> None:
    assert client.delete("/api/documents/999").status_code == 404


def test_corrupt_pdf_marked_failed_with_reason(client: TestClient) -> None:
    res = client.post(
        "/api/documents", files={"file": ("bad.pdf", b"not a pdf at all", "application/pdf")}
    )
    assert res.status_code == 201
    # TestClient runs background tasks before returning, so status is final
    doc = client.get("/api/documents").json()[0]
    assert doc["status"] == "failed"
    assert doc["failure_reason"]
