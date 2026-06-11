# 01 — Backend Scaffold

**Roadmap phase:** 1 · **Depends on:** nothing

## Goal
A typed, linted, testable FastAPI app skeleton in `api/`.

## Scope
- Init `api/` with `uv`; pin FastAPI, uvicorn, SQLAlchemy, Alembic, `psycopg[binary]`, `qdrant-client`, structlog, pydantic-settings
- mypy + ruff configured; root `Makefile` targets: `typecheck`, `lint`, `test`
- `GET /api/health` returning `{ ok: true, version }` with stubbed postgres/qdrant statuses
- pytest set up with one test for the health endpoint

## Out of scope
- Real connectivity checks (02, 03, 04), LlamaIndex (10)

## Done when
- `make typecheck && make lint && make test` exit 0
- `uvicorn` serves `/api/health` → 200 locally
