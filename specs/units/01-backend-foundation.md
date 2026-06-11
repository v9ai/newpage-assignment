# 01 — Backend Foundation

**Roadmap phase:** 1 · **Integration deps:** none · **Teammate:** `foundation` · *(merges old units 01 + 02)*

## Owns (files)
`api/app/settings.py`, `api/app/health.py`, `.env.example`, `api/tests/test_health.py`,
`api/tests/test_settings.py`, plus the initial scaffold of the lead-owned integration files
(`api/app/main.py`, `api/pyproject.toml`, root `Makefile`) — after scaffold, edits to those
go through the lead.

## Goal
A typed, linted, testable FastAPI skeleton in `api/` where all config flows through one typed
settings module and the OpenAI key lives only in `.env.local`.

## Provides (contracts)
The settings module and `/api/health` shape from the [shared contracts](README.md#shared-contracts) —
every other backend unit imports settings rather than reading env directly.

## Scope
- Init `api/` with `uv`; pin FastAPI, uvicorn, SQLAlchemy, Alembic, `psycopg[binary]`,
  `qdrant-client`, structlog, pydantic-settings
- mypy + ruff configured; root `Makefile` targets: `typecheck`, `lint`, `test`
- pydantic-settings module loading `.env` (defaults) then `.env.local` (overrides, wins),
  exposing every variable in the contracts table
- Fail fast at startup with a clear error if `OPENAI_API_KEY` is missing
- `GET /api/health` returning `{ ok, version }` with stubbed postgres/qdrant statuses and
  `openai: configured|missing` (key presence only — no live API call)
- `.env.example` documenting every variable with placeholders (`OPENAI_API_KEY=sk-...`)
- Key never logged, never sent to the frontend
- pytest set up with tests for the health endpoint and settings precedence

## Out of scope
- Real Postgres/Qdrant connectivity (02), LlamaIndex (06)

## Parallel notes
Nothing blocks this unit. Units 02–10 only need the *shape* of settings and health (already
fixed in the contracts), so they may start before this lands. `health.py` imports
`probe()` from `api/app/db.py` / `api/app/vectors.py` (02's files) — ship stub probes with
the contract signature until 02 replaces them (same teammate, so the handoff is internal).

## Done when
- `make typecheck && make lint && make test` exit 0
- `uvicorn` serves `/api/health` → 200 locally
- Starting the api without a key exits immediately with a readable error
- `git ls-files | grep -i env` returns only `.env.example`
- Unit test covers settings precedence (`.env.local` wins)
