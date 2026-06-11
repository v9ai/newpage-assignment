# 04 — Docker Compose Stack

**Roadmap phase:** 1 · **Integration deps:** 01–03 (for full-stack validation) · **Teammate:** `platform` · *(old unit 06)*

## Owns (files)
`docker-compose.yml`, `api/Dockerfile`, `web/Dockerfile`, `web/nginx.conf`, `.dockerignore`.

## Goal
One command brings up the whole stack: web, api, postgres, qdrant.

## Scope
- Multi-stage Dockerfile for `api`; multi-stage build for `web` with nginx serving the bundle
  and proxying `/api/*` → `api:8000` (same-origin, no CORS)
- `docker-compose.yml` with the four services + volumes for pg data, qdrant storage, uploads,
  and the FastEmbed model cache
- api service gets `env_file: .env.local` — key never baked into images or compose yaml
- Healthchecks on all services (`pg_isready` for postgres; TCP-level for qdrant — its image
  ships no curl/wget)
- `.dockerignore` excluding `.env.local`, venvs, node_modules

## Parallel notes
Ports, paths, and service names are fixed by the contracts, so Dockerfiles, compose yaml, and
healthchecks can be written against minimal placeholder apps before 01/03 land. Only the
done-when run needs the real scaffolds.

## Done when
- Copy `.env.example` → `.env.local`, add key, `docker compose up --build` → all four healthy
- `curl localhost:8000/api/health` → 200 with postgres/qdrant/openai all ok
- `docker history` shows no key in any layer
