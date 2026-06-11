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
    assert doc["size_bytes"] == len(b"# hello docchat")

    listed = client.get("/api/documents").json()
    assert [d["id"] for d in listed] == [doc["id"]]

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
