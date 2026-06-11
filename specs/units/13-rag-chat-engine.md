# 13 — RAG Chat Engine

**Roadmap phase:** 5 · **Depends on:** 02, 12

## Goal
Grounded, cited, streaming answers over the retrieved context.

## Scope
- Chat engine: retrieve → grounded-answer prompt → OpenAI `gpt-5-mini` (via `LLM_BASE_URL`/`LLM_MODEL` settings)
- Custom system prompt: answer **only** from provided context; cite sources inline
- SSE streaming from FastAPI (`POST /api/chat` or `/api/sessions/{id}/messages`)
- Inline citations mapping to document + page/chunk
- Refusal path: relevant context below threshold → "not in the documents" answer, no hallucination

## Done when
- Streamed answer cites real source locations for an answerable question
- An unanswerable question produces the refusal, not an invented answer
- Prompt template lives in code under version control (it's a documented decision)
