# 20 — README & Submission

**Roadmap phase:** 10 · **Depends on:** all

> Detailed section-by-section content requirements, writing plan, and validation live in
> [`specs/2026-06-11-submission-docs/`](../2026-06-11-submission-docs/requirements.md).
> This unit is the execution checklist; that folder is the contract.

## Goal
The repo sells itself: an evaluator can run it first try and read the reasoning behind every decision.

## Scope (mirrors the brief's "What to Submit")
- Quick setup (copy `.env.example` → `.env.local`, add key, `docker compose up`)
- Architecture overview + simple diagram
- Productionization: secrets management, managed Postgres/Qdrant, AWS/GCP/Azure/Cloudflare deployment path
- RAG/LLM decisions: choices considered and final — LLM (OpenAI `gpt-5-mini`), embeddings (FastEmbed `bge-small-en-v1.5`, local), vector DB (Qdrant), orchestration (LlamaIndex), chunking, prompt & context management, guardrails, quality, observability
- Engineering standards followed/skipped; AI-tool workflow (do's & don'ts); what I'd do differently with more time
- Deferred items: auth, multi-user isolation, reranking, hybrid search, async ingestion queue, evals in CI
- Screenshots + short video
- **README prose written by hand — the brief explicitly wants my thoughts, not LLM output**

## Done when
- Fresh clone on a clean machine: follow the README verbatim → working cited answer
- Every "What to Submit" bullet from `assignment.md` is addressed
