# 12 — Retrieval API

**Roadmap phase:** 4 · **Depends on:** 10

## Goal
A transparent retrieval endpoint proving search quality before chat exists.

## Scope
- LlamaIndex retriever over the Qdrant index (query embedded with the same FastEmbed model)
- `POST /api/retrieve`: query → top-k nodes with scores + source metadata (doc, page, chunk)
- `k` and score threshold from config
- Integration test: ingest sample doc → retrieve → expected chunk comes back

## Done when
- Round-trip integration test passes against the compose stack
- Endpoint visible in OpenAPI docs; useful as a debug/transparency tool
