# 18 — Observability

**Roadmap phase:** 8 · **Depends on:** 13

## Goal
Every request is traceable: what was asked, what was retrieved, what it cost.

## Scope
- structlog JSON logs per request: query, retrieved node ids + scores, model, token usage, latency
- Request id generated at the edge and propagated through api → LlamaIndex/OpenAI calls
- Errors logged with context and surfaced to the client as clean messages — never swallowed
- `OPENAI_API_KEY` redacted from all log output
- Optional stretch: local Langfuse container wired to LlamaIndex instrumentation

## Done when
- One chat request produces a correlated, parseable JSON trace (grep by request id)
- A forced OpenAI failure shows up in logs with the request id and as a clean client error
