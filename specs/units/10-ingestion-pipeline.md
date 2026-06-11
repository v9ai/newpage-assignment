# 10 — Ingestion Pipeline

**Roadmap phase:** 3 · **Depends on:** 04, 08

## Goal
Parsed documents become embedded chunks in Qdrant.

## Scope
- Install + pin `fastembed` and the LlamaIndex integrations (`llama-index-embeddings-fastembed`, `llama-index-vector-stores-qdrant`)
- LlamaIndex `IngestionPipeline`: sentence-aware node parser (chunk size/overlap as documented config) → FastEmbed embeddings → `QdrantVectorStore`
- Embeddings: **FastEmbed `BAAI/bge-small-en-v1.5` (pinned), local ONNX on CPU** — no API cost or key needed for ingestion; model cached in a volume
- Pre-download the embedding model at image build (or explicit startup warmup) — never a surprise download at first upload
- Node metadata: doc id, page, chunk index
- Re-ingesting a document replaces its old vectors (delete by doc id filter first)

## Done when
- Unit tests on chunking (size/overlap/metadata)
- Ingesting a sample PDF yields the expected vector count in Qdrant (384-dim)
- Second ingest of the same doc doesn't duplicate vectors
