import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.config import Settings, require_api_key
from app.main import app, lifespan


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


@pytest.mark.anyio
async def test_lifespan_survives_qdrant_bootstrap_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Qdrant being down at startup must degrade gracefully, not kill the api.

    The collection bootstrap is wrapped in try/except; a raising
    ensure_collection logs qdrant_bootstrap_failed and the api still serves.
    """

    def boom() -> None:
        raise ConnectionError("qdrant unreachable")

    monkeypatch.setattr(main_module, "ensure_collection", boom)

    warnings: list[dict[str, object]] = []
    monkeypatch.setattr(
        main_module.log,
        "warning",
        lambda event, **kw: warnings.append({"event": event, **kw}),
    )

    # Lifespan must enter and exit cleanly despite the bootstrap failure.
    async with lifespan(app):
        pass

    assert any(w["event"] == "qdrant_bootstrap_failed" for w in warnings)
