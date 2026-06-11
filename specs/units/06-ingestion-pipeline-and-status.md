# 06 — Ingestion Pipeline & Status

**Roadmap phase:** 3 · **Integration deps:** 02, 05 · **Teammate:** `ingest` · *(merges old units 10 + 11)*

## Owns (files)
`api/app/ingestion.py` and its tests. Status updates go through 02's `models.py`/session
(read-only dependency on the schema contract). fastembed/integration pins → message the lead.

## Goal
Parsed documents become embedded chunks in Qdrant, with users able to see exactly where each
document is in the pipeline.

## Consumes / provides (contracts)
Consumes the parsing output of 05 and the Qdrant collection of 02; provides the point payload
`{ doc_id, filename, page, chunk_index, text }` and the status transitions from the
[shared contracts](README.md#shared-contracts).

## Scope
- Install + pin `fastembed` and the LlamaIndex integrations
  (`llama-index-embeddings-fastembed`, `llama-index-vector-stores-qdrant`)
- LlamaIndex `IngestionPipeline`: sentence-aware node parser (chunk size/overlap as documented
  config) → FastEmbed embeddings → `QdrantVectorStore`
- Embeddings: **FastEmbed `BAAI/bge-small-en-v1.5` (pinned), local ONNX on CPU** — no API cost
  or key needed for ingestion; model cached in a volume
- Pre-download the embedding model at image build (or explicit startup warmup) — never a
  surprise download at first upload
- Node metadata: doc id, page, chunk index
- Re-ingesting a document replaces its old vectors (delete by doc id filter first)
- Status transitions in Postgres: `uploaded → ingesting → ready | failed` (+ failure reason)
- Ingestion triggered on upload completion; runs without blocking the request (background
  task is fine — no queue infra)

## Parallel notes
The pipeline takes `{ text, page }` blocks as input — develop and unit-test it on hand-made
blocks before 05 lands. Status transitions are plain `documents` updates coded against the
schema contract. Only the end-to-end done-when needs 02 + 05 merged.

## Done when
- Unit tests on chunking (size/overlap/metadata)
- Ingesting a sample PDF yields the expected vector count in Qdrant (384-dim)
- Second ingest of the same doc doesn't duplicate vectors
- Upload → status visibly progresses to `ready` in the UI (via 03's list)
- A corrupt file shows `failed` + reason without breaking the list
