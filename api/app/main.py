from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI

from app.config import get_settings, require_api_key
from app.documents import router as documents_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    require_api_key(get_settings())
    yield


app = FastAPI(title="DocChat API", version=get_settings().version, lifespan=lifespan)
app.include_router(documents_router)


def _probe(name: str, check: Any) -> str:
    try:
        check()
        return "ok"
    except Exception as exc:
        log.warning("health_check_failed", service=name, error=str(exc))
        return "error"


@app.get("/api/health")
def health() -> dict[str, Any]:
    from app.db import check_postgres
    from app.vectorstore import check_qdrant

    settings = get_settings()
    return {
        "ok": True,
        "version": settings.version,
        "services": {
            "postgres": _probe("postgres", check_postgres),
            "qdrant": _probe("qdrant", check_qdrant),
            "openai": "configured" if settings.openai_api_key else "missing",
        },
    }
