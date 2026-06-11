# Phase 1 Plan — Walking Skeleton

## Group 1 — Backend Scaffold
1. Init `api/` with `uv`; add FastAPI, uvicorn, SQLAlchemy, Alembic, `psycopg[binary]`, `qdrant-client`, structlog, pydantic-settings (all pinned)
2. Configure mypy + ruff; add `make typecheck`, `make lint`, `make test`
3. Settings module (pydantic-settings) loading `.env` then `.env.local` (override); fail fast at startup if `OPENAI_API_KEY` is missing
4. `GET /api/health` returning `{ ok: true, version }` with stubbed postgres/qdrant statuses (made real in Group 2) and `openai: configured` (key present — no live API call)
5. pytest setup with one test for the health endpoint

## Group 2 — Database Plumbing
6. SQLAlchemy engine/session config from env vars
7. Alembic initialised; migration 0001 creating a `documents` table stub (id, filename, status, created_at)
8. Health endpoint performs a real `SELECT 1` against Postgres and a collections call against Qdrant

## Group 3 — Frontend Scaffold
9. Init `web/` with Vite + React + TS (strict) + Tailwind; pin versions
10. Minimal branded landing page (app name, tagline, disabled upload placeholder) — define base design tokens, not Vite defaults
11. Fetch and display `/api/health` status so frontend↔backend wiring is proven

## Group 4 — Compose the Local Stack
12. Dockerfiles: multi-stage for `api`; multi-stage build for `web` with nginx serving the static bundle **and proxying `/api/*` → `api:8000`** (same-origin, no CORS config needed)
13. `docker-compose.yml` with `web`, `api`, `postgres`, `qdrant` + volumes for pg data and qdrant storage; api gets `env_file: .env.local` (key never baked into images or compose yaml)
14. `.env.example` documenting every variable (`OPENAI_API_KEY` + optional `LLM_BASE_URL`/`LLM_MODEL` overrides, `EMBED_MODEL` FastEmbed id); `.dockerignore` excluding `.env.local`; healthchecks on all services. Note: the qdrant image ships no curl/wget — use a TCP-level healthcheck; postgres uses `pg_isready`

## Group 5 — Repo Hygiene
15. Monorepo layout: `api/`, `web/`, `specs/`, root `Makefile` + `docker-compose.yml`
16. `.gitignore` (must cover `.env.local`, `.env`, venvs, node_modules, volumes), commit, README stub with the run path (copy `.env.example` → `.env.local`, add key, one command)

## Group 6 — Verify
17. `make typecheck && make lint && make test` exit 0
18. `docker compose up --build` → all four services healthy
19. `curl localhost:8000/api/health` → 200, reports postgres: ok, qdrant: ok, openai: configured
20. Browser shows landing page with green health status
21. `git ls-files | grep -i env` shows only `.env.example` — no secrets tracked
