# 02 — Data Stores

**Roadmap phase:** 1 · **Integration deps:** 01 · **Teammate:** `foundation` · *(merges old units 03 + 04)*

## Owns (files)
`api/app/db.py`, `api/app/vectors.py`, `api/app/models.py` (the `documents` model — chat
models live in 08's `chat_models.py`), `api/alembic/` with migration revision id fixed to
`0001`, and their tests. New deps (SQLAlchemy extras, alembic) → message the lead.

## Goal
Postgres wired through SQLAlchemy with Alembic schema history from commit one, and Qdrant
reachable from the api — both proven by the health endpoint.

## Provides (contracts)
The `documents` table and Qdrant collection from the [shared contracts](README.md#shared-contracts).

## Scope
- SQLAlchemy 2 engine/session from settings
- Alembic initialised; migration 0001 creating the `documents` stub (id, filename, status, created_at)
- Migrations run on api startup (or documented one-liner)
- `qdrant-client` configured from settings; collection bootstrap helper
  (create-if-missing; name + vector size from config)
- `/api/health` performs a real `SELECT 1` and a Qdrant collections call

## Out of scope
- Writing vectors (06), chat tables (08 — its own migration)

## Parallel notes
Engine, session, Alembic env, and the Qdrant bootstrap helper are all plain modules coded
against the settings contract — implementable before 01 merges (stub a settings object in
tests). Only the health-endpoint wiring and the done-when checks need 01.

## Done when
- Fresh Postgres + api start → `documents` table exists
- Health endpoint reports `postgres: ok` and `qdrant: ok`; each flips to error when its
  service is down
