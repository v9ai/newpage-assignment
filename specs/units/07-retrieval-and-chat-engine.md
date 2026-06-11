# 07 — Retrieval & RAG Chat Engine

**Roadmap phases:** 4, 5 · **Integration deps:** 06 · **Teammate:** `rag` · *(merges old units 12 + 13)*

## Owns (files)
`api/app/retrieval.py`, `api/app/chat.py`, `api/app/prompts.py` (later hardened by 09 —
same teammate), and their tests. Router mounts → message the lead.

## Goal
A transparent retrieval endpoint proving search quality, and grounded, cited, streaming
answers built on top of it.

## Consumes / provides (contracts)
Consumes the Qdrant payload of 06; provides `POST /api/retrieve`, the SSE stream, and the
`Citation` shape from the [shared contracts](README.md#shared-contracts).

## Scope
- LlamaIndex retriever over the Qdrant index (query embedded with the same FastEmbed model)
- `POST /api/retrieve`: query → top-k nodes with scores + source metadata (doc, page, chunk);
  `k` and score threshold from config; visible in OpenAPI docs as a debug/transparency tool
- Chat engine: retrieve → grounded-answer prompt → OpenAI `gpt-5-mini`
  (via `LLM_BASE_URL`/`LLM_MODEL` settings)
- Custom system prompt: answer **only** from provided context; cite sources inline
- SSE streaming from FastAPI (`POST /api/sessions/{id}/messages`)
- Inline citations mapping to document + page/chunk
- Refusal path: relevant context below threshold → "not in the documents" answer, no
  hallucination
- Prompt template lives in code under version control (it's a documented decision)

## Parallel notes
Retriever and chat engine develop against hand-seeded Qdrant points (the payload contract),
so work starts before 06 lands. The SSE endpoint can mount on a stub session id until 08's
persistence merges — the stream format is fixed by contract either way.

## Done when
- Round-trip integration test passes against the compose stack: ingest sample doc → retrieve
  → expected chunk comes back
- Streamed answer cites real source locations for an answerable question
- An unanswerable question produces the refusal, not an invented answer
