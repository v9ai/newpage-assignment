import pytest
from fastapi.testclient import TestClient

from app.config import Settings, require_api_key
from app.main import app


def test_health_shape() -> None:
    with TestClient(app) as client:
        res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "version" in body
    services = body["services"]
    assert set(services) == {"postgres", "qdrant", "openai"}
    assert services["openai"] == "configured"


def test_startup_fails_without_key() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        require_api_key(Settings(openai_api_key=""))
