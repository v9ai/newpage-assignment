# Phase 1 Requirements — Walking Skeleton

## Scope

Scaffold the full stack so the dev loop works end to end: typed FastAPI backend, React frontend, Postgres with migrations, Qdrant in compose, OpenAI key wiring via `.env.local`, health endpoint proving connectivity. Everything builds and runs with one command after adding the key.

## Out of Scope

- No upload, parsing, or RAG of any kind (Phases 2+)
- No LlamaIndex code or dependency yet — the library is installed and pinned in Phase 2, where its readers do the document parsing (keeps Phase 1's dependency surface minimal)
- No styling beyond a minimal intentional landing page
- No CI pipeline (optional later)

## Decisions

### Monorepo, two apps
`api/` (Python/FastAPI) and `web/` (React/Vite) in one repo with a root Makefile and docker-compose. Clean fullstack separation without multi-repo overhead.

### Migrations from commit one
Alembic is set up in this phase with a real (if tiny) migration, so schema history exists from the start instead of being retrofitted.

### Health endpoint does real checks
`/api/health` performs `SELECT 1` against Postgres and a collections call against Qdrant. A green health check means the stack is genuinely wired, which every later validation step relies on.

### Secrets via `.env.local`
`OPENAI_API_KEY` lives in a gitignored `.env.local`; `.env.example` documents every variable. compose injects `.env.local` into the api service via `env_file`. The api fails fast at startup with a clear error if the key is missing — not at first query. The key never reaches the frontend or the logs.

## Context

This phase proves the baseline: clone → add key to `.env.local` → `docker compose up` → four healthy services → frontend showing green status. It is the foundation and the evaluator's first impression.

## Stakeholder Notes

- **Evaluators** judge "engineering excellence" partly on whether the project runs first try — this phase is that promise.
