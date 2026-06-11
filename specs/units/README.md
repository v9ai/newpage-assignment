# Spec Units

The 10-phase [roadmap](../roadmap.md) compressed into **10 build units designed for parallel
implementation**. Each unit codes against the shared contracts below — never against another
unit's implementation — so all 10 can be developed concurrently; dependencies listed in a unit
are needed only for its final integration validation ("done when"), not to start work.

| # | Unit | Roadmap phases | Integration deps |
|---|---|---|---|
| 01 | [Backend Foundation](01-backend-foundation.md) | 1 | — |
| 02 | [Data Stores](02-data-stores.md) | 1 | 01 |
| 03 | [Frontend Shell & Upload UI](03-frontend-shell-and-upload-ui.md) | 1, 2 | 05 (live API) |
| 04 | [Docker Compose Stack](04-docker-compose-stack.md) | 1 | 01–03 |
| 05 | [Upload API & Parsing](05-upload-api-and-parsing.md) | 2 | 02 |
| 06 | [Ingestion Pipeline & Status](06-ingestion-pipeline-and-status.md) | 3 | 02, 05 |
| 07 | [Retrieval & RAG Chat Engine](07-retrieval-and-chat-engine.md) | 4, 5 | 06 |
| 08 | [Chat Persistence & Chat UI](08-chat-persistence-and-ui.md) | 5, 6 | 07 |
| 09 | [Guardrails & Evals](09-guardrails-and-evals.md) | 7 | 07 |
| 10 | [Observability, Hardening & Submission](10-observability-hardening-submission.md) | 8–10 | all |

All five tracks start simultaneously (everything inside a track is also internally
parallelizable via stubs; arrows are integration-validation order, not start order):

```
foundation:  01 ──► 02
ingest:      05 ──► 06
rag:         07 ──► 09
frontend:    03 ──► 08
platform:    04 ──► 10 (logging/middleware/docs day one; e2e + fresh-clone pass last)
```

Provider summary: LLM = OpenAI `gpt-5-mini` (key in gitignored `.env.local`);
embeddings = FastEmbed `BAAI/bge-small-en-v1.5` running locally (no API cost for ingestion);
vector DB = Qdrant; app DB = Postgres; orchestration = LlamaIndex.

---

## Shared contracts

These shapes are fixed up front; they are what makes parallel work possible. Any unit may rely
on them; changing one requires updating this file (and every consumer) in the same commit.

### Environment variables
Loaded by pydantic-settings from `.env` (defaults) then `.env.local` (overrides, wins):

| Var | Required | Default / notes |
|---|---|---|
| `OPENAI_API_KEY` | yes | api fails fast at startup if missing; never logged, never sent to frontend |
| `LLM_BASE_URL` | no | OpenAI-compatible endpoint override |
| `LLM_MODEL` | no | `gpt-5-mini` |
| `EMBED_MODEL` | no | `BAAI/bge-small-en-v1.5` (FastEmbed, local ONNX, 384-dim) |
| `DATABASE_URL` | no | Postgres DSN |
| `QDRANT_URL` | no | |
| `QDRANT_COLLECTION` | no | `documents` |
| `UPLOAD_MAX_BYTES` | no | server-side size cap |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | no | documented chunking choice |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_SCORE_THRESHOLD` | no | |
| `CHAT_TOKEN_BUDGET` | no | history condensation budget |

### Postgres schema
- `documents(id uuid pk, filename, size, mime, status, failure_reason nullable, created_at)`
  — `status`: `uploaded → ingesting → ready | failed` (failed always sets `failure_reason`)
- `chat_sessions(id uuid pk, title, created_at)`
- `chat_messages(id uuid pk, session_id fk, role, content, citations jsonb, created_at)`

### Qdrant
Collection `QDRANT_COLLECTION`, 384-dim cosine vectors; point payload:
`{ doc_id, filename, page, chunk_index, text }`. Re-ingest deletes by `doc_id` filter first.

### HTTP API (`/api/*`, same-origin via nginx proxy in compose)
- `GET /api/health` → `{ ok, version, services: { postgres: "ok"|"error", qdrant: "ok"|"error", openai: "configured"|"missing" } }`
- `POST /api/documents` (multipart; pdf/txt/md) → `DocumentOut` · `GET /api/documents` → `[DocumentOut]` · `DELETE /api/documents/{id}` → 204
  - `DocumentOut = { id, filename, size, mime, status, failure_reason, created_at }`
  - Rejections: 415 unsupported type, 413 oversized — JSON body `{ detail }`
- `POST /api/retrieve` `{ query, k? }` → `{ nodes: [{ text, score, doc_id, filename, page, chunk_index }] }`
- `POST /api/sessions` → `SessionOut` · `GET /api/sessions` → `[SessionOut]` · `GET /api/sessions/{id}` → session + messages
- `POST /api/sessions/{id}/messages` `{ content }` → SSE stream (below)
- `Citation = { doc_id, filename, page, chunk_index, snippet }`

### SSE stream (chat)
Named events, JSON data:
`token {delta}` (repeated) · `citations {citations: [Citation]}` · `error {message}` · `done {message_id, usage}`.
A refusal ("not in the documents") is a normal `token`-streamed answer — distinguishable by
`citations: []` on `done`.

---

## Running the build as a full-parallel agent team

The units are sized and file-partitioned to run as a [Claude Code agent team](https://code.claude.com/docs/en/agent-teams)
(experimental — requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings `env`):
one lead + five teammates, all five tracks started at once. Each teammate owns two units
(~5–6 tasks each); units sharing files are deliberately co-assigned to the same teammate so
cross-teammate file conflicts cannot happen.

### Team shape

| Teammate | Units | Spawn focus |
|---|---|---|
| `foundation` | 01, 02 | api scaffold, settings, health, Alembic 0001, Qdrant bootstrap |
| `ingest` | 05, 06 | upload routes, parsing, ingestion pipeline, status transitions |
| `rag` | 07, 09 | retriever, chat engine, SSE, prompts, guardrails, eval harness |
| `frontend` | 03, 08 | web shell, upload UI, chat UI, persistence + condenser |
| `platform` | 04, 10 | Dockerfiles, compose, observability, rate limiting, e2e, README |

The **lead** never implements units. It owns the shared integration files (below), applies
the one-line edits teammates request, reviews plans, and runs the integration checkpoints.

### File ownership — one writer per path

Each unit's spec lists what it owns; the partition in brief:

| Path | Owner |
|---|---|
| `api/app/main.py`, `api/pyproject.toml`, `api/uv.lock`, root `Makefile` | **lead** (integration files — teammates message the lead the exact router-mount / dep-pin / make-target lines to apply) |
| `api/app/settings.py`, `api/app/health.py`, `.env.example`, initial scaffold | `foundation` (01) |
| `api/app/db.py`, `api/app/vectors.py`, `api/app/models.py`, `api/alembic/` migration `0001` | `foundation` (02) |
| `api/app/documents.py`, `api/app/parsing.py`, `api/app/storage.py` | `ingest` (05) |
| `api/app/ingestion.py` | `ingest` (06) |
| `api/app/retrieval.py`, `api/app/chat.py`, `api/app/prompts.py` | `rag` (07, hardened by 09) |
| `evals/`, injection test suite | `rag` (09) |
| `web/` except `web/src/chat/`, `web/Dockerfile`, `web/nginx.conf` | `frontend` (03) |
| `api/app/sessions.py`, `api/app/chat_models.py`, `api/app/condenser.py`, migration `0002`, `web/src/chat/` | `frontend` (08) |
| `docker-compose.yml`, `api/Dockerfile`, `web/Dockerfile`, `web/nginx.conf`, `.dockerignore` | `platform` (04) |
| `api/app/logging.py`, `api/app/middleware.py`, `api/app/ratelimit.py`, `e2e/`, `README.md`, `docs/` | `platform` (10) |
| each unit's test files | that unit's owner |

Migration coordination without contact: 02 creates revision id `0001`; 08 creates `0002`
with `down_revision = "0001"` — fixed ids, no shared file.

### Task list

The lead seeds the shared task list with one task per unit **scope bullet** (5–6 per unit),
plus per-unit integration tasks that carry the dependencies from the table at the top
(e.g. "06 end-to-end done-when" depends on 02 + 05 integration tasks). Scope tasks have no
cross-unit dependencies — every teammate starts immediately against the contracts and stubs
named in its unit's *Parallel notes*.

### Spawn prompt (paste into the lead)

```text
Create an agent team to build this project. Read specs/units/README.md first — it defines
the shared contracts, the file-ownership partition, and the team shape. Spawn 5 teammates
named foundation, ingest, rag, frontend, platform; each owns the two units the README
assigns it. Require plan approval before implementation. Seed the shared task list with one
task per scope bullet plus the per-unit integration tasks, with dependencies only on
integration tasks. Teammates code against the contracts section and the stub strategies in
their units' "Parallel notes" — never against another teammate's implementation. You (lead)
do not implement units: you own api/app/main.py, api/pyproject.toml, api/uv.lock and the
root Makefile, apply the exact edit lines teammates message you, and run the integration
checkpoints (make typecheck lint test; docker compose up --build; make e2e) as integration
tasks unblock. Only approve plans that respect the file-ownership table.
```

### Integration checkpoints (lead-run, in dependency order)

1. `make typecheck && make lint && make test` once `foundation` lands (and again as each track merges)
2. `docker compose up --build` + health all-ok once 01–04 land
3. ingest→retrieve round-trip (07's done-when) once 06 + 07 land
4. `make eval` green (09) · `make e2e` green, failure-mode sweep, fresh-clone README pass (10)
