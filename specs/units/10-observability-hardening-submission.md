# 10 — Observability, Hardening & Submission

**Roadmap phases:** 8–10 · **Integration deps:** all (for e2e + final pass) · **Teammate:** `platform` · *(merges old units 18 + 19 + 20)*

## Owns (files)
`api/app/logging.py`, `api/app/middleware.py`, `api/app/ratelimit.py`, `e2e/`, `README.md`,
`docs/`, and their tests. Middleware registration in `main.py` + Playwright/structlog pins
→ message the lead.

> Detailed section-by-section README content requirements, writing plan, and validation live in
> [`specs/2026-06-11-submission-docs/`](../2026-06-11-submission-docs/requirements.md).
> This unit is the execution checklist; that folder is the contract.

## Goal
Every request is traceable, the happy path is proven end-to-end, the unhappy paths fail
gracefully, and the repo sells itself — an evaluator can run it first try and read the
reasoning behind every decision.

## Scope

### Observability
- structlog JSON logs per request: query, retrieved node ids + scores, model, token usage,
  latency
- Request id generated at the edge and propagated through api → LlamaIndex/OpenAI calls
- Errors logged with context and surfaced to the client as clean messages — never swallowed
- `OPENAI_API_KEY` redacted from all log output
- Optional stretch: local Langfuse container wired to LlamaIndex instrumentation

### Hardening & E2E
- One Playwright e2e: upload → ingest → ask → cited answer (uses a doc from the
  `make fetch-samples` corpus)
- Failure modes return designed errors (UI + API): OpenAI unreachable / invalid key /
  rate-limited; Qdrant down; Postgres down; oversized file
- Rate limiting on the chat endpoint (simple in-process limiter is fine)

### README & submission (mirrors the brief's "What to Submit")
- Quick setup (copy `.env.example` → `.env.local`, add key, `docker compose up`)
- Architecture overview + simple diagram
- Productionization: secrets management, managed Postgres/Qdrant, AWS/GCP/Azure/Cloudflare
  deployment path
- RAG/LLM decisions: choices considered and final — LLM (OpenAI `gpt-5-mini`), embeddings
  (FastEmbed `bge-small-en-v1.5`, local), vector DB (Qdrant), orchestration (LlamaIndex),
  chunking, prompt & context management, guardrails, quality, observability
- Engineering standards followed/skipped; AI-tool workflow (do's & don'ts); what I'd do
  differently with more time
- Deferred items: auth, multi-user isolation, reranking, hybrid search, async ingestion
  queue, evals in CI
- API cost note + the OpenAI-compatible escape hatch (env vars accept any compatible
  endpoint/provider)
- Screenshots + short video
- **README prose written by hand — the brief explicitly wants my thoughts, not LLM output**

## Parallel notes
This is the cross-cutting track: the logging middleware, request-id propagation, and rate
limiter are standalone modules buildable from day one; README sections (architecture,
decisions, productionization) draft alongside the units they describe. Only the Playwright
e2e, failure-mode sweep, and final fresh-clone pass need the full stack.

## Done when
- One chat request produces a correlated, parseable JSON trace (grep by request id)
- A forced OpenAI failure shows up in logs with the request id and as a clean client error
- `make e2e` passes against the compose stack
- Stopping each dependency produces a clean, user-readable error — no blank screens or raw 500s
- Fresh clone on a clean machine: follow the README verbatim → working cited answer
- Every "What to Submit" bullet from `assignment.md` is addressed
