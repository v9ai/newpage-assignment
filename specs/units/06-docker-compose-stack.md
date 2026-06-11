# 06 — Docker Compose Stack

**Roadmap phase:** 1 · **Depends on:** 01–05

## Goal
One command brings up the whole stack: web, api, postgres, qdrant.

## Scope
- Multi-stage Dockerfile for `api`; multi-stage build for `web` with nginx serving the bundle and proxying `/api/*` → `api:8000` (same-origin, no CORS)
- `docker-compose.yml` with the four services + volumes for pg data and qdrant storage
- api service gets `env_file: .env.local` — key never baked into images or compose yaml
- Healthchecks on all services (`pg_isready` for postgres; TCP-level for qdrant — its image ships no curl/wget)
- `.dockerignore` excluding `.env.local`, venvs, node_modules

## Done when
- Copy `.env.example` → `.env.local`, add key, `docker compose up --build` → all four healthy
- `curl localhost:8000/api/health` → 200 with postgres/qdrant/openai all ok
- `docker history` shows no key in any layer
