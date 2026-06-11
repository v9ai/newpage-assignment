# 19 — Hardening & E2E

**Roadmap phase:** 9 · **Depends on:** 15, 16

## Goal
The happy path is proven end-to-end and the unhappy paths fail gracefully.

## Scope
- One Playwright e2e: upload → ingest → ask → cited answer (uses a doc from the `make fetch-samples` corpus)
- Failure modes return designed errors (UI + API): OpenAI unreachable / invalid key / rate-limited; Qdrant down; Postgres down; oversized file
- Rate limiting on the chat endpoint (simple in-process limiter is fine)

## Done when
- `make e2e` passes against the compose stack
- Stopping each dependency produces a clean, user-readable error — no blank screens or raw 500s
