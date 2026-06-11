from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI

from app.chat import router as chat_router
from app.config import get_settings, require_api_key
from app.documents import router as documents_router
from app.logging import configure_logging
from app.middleware import RequestContextMiddleware
from app.retrieval import router as retrieval_router
from app.sessions import router as sessions_router
from app.vectorstore import ensure_collection

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    require_api_key(get_settings())
    try:
        ensure_collection()
    except Exception as exc:
        # Qdrant being down must not kill the api — health reports it and
        # ingestion surfaces a clear failure; the collection is created on
        # the next successful startup or first write.
        log.warning("qdrant_bootstrap_failed", error=str(exc))
    try:
        from app.ingestion import warmup

        warmup()
    except Exception as exc:
        # A failed model download degrades to a lazy download at first upload.
        log.warning("embedding_warmup_failed", error=str(exc))
    yield


app = FastAPI(title="DocChat API", version=get_settings().version, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(sessions_router)


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
