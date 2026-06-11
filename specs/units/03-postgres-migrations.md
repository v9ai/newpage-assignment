# 03 — Postgres & Migrations

**Roadmap phase:** 1 · **Depends on:** 01, 02

## Goal
Postgres wired through SQLAlchemy with Alembic schema history from commit one.

## Scope
- SQLAlchemy 2 engine/session from settings
- Alembic initialised; migration 0001 creating `documents` stub (id, filename, status, created_at)
- Migrations run on api startup (or documented one-liner)
- `/api/health` performs a real `SELECT 1`

## Done when
- Fresh Postgres + api start → `documents` table exists
- Health endpoint reports `postgres: ok`; flips to error when Postgres is down
