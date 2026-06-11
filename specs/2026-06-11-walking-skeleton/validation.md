# Phase 1 Validation — Walking Skeleton

## Definition of Done

All of the following must be true before this phase is merged.

### 1. Types, lint, tests are clean
make typecheck
make lint
make test
All exit 0. At least the health-endpoint test exists and passes. (Backend-only in this phase — Vitest arrives with the first real frontend logic.)

### 2. Full stack comes up with one command
docker compose up --build
All four services (web, api, postgres, qdrant) reach healthy status. The only setup step is copying `.env.example` to `.env.local` and adding `OPENAI_API_KEY`. With the key missing, the api exits immediately with a clear error message.

### 3. Health endpoint does real checks
curl -s http://localhost:8000/api/health
Returns HTTP 200 with body containing "ok": true, connectivity status for both postgres and qdrant, and "openai": "configured" (key presence only — no live API call).

### 4. Migration applied
Alembic migration 0001 runs on startup (or via documented command); `documents` table exists in Postgres.

### 5. Frontend wired to backend
Landing page loads in a browser, is visibly not the default Vite template, and displays live health status fetched from the API.

### 6. No secret leakage
- `.env.local` is gitignored and dockerignored; `git ls-files | grep -i env` returns only `.env.example`
- `.env.example` contains a placeholder (`OPENAI_API_KEY=sk-...`), never a real key
- The key appears in no log output, no error message, no frontend bundle, no docker image layer (`docker history` clean)

### 7. Repo hygiene
- All versions pinned (uv.lock committed, Docker image tags, model ids in config, no `^` in web/package.json)
- `.env.example` present and documents every variable; `.gitignore` excludes `.env`, `.env.local`, venvs, node_modules, volumes
- README stub documents the run path accurately (copy `.env.example` → `.env.local`, add key, `docker compose up`)
