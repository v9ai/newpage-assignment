# Tech Stack

> This file is law for the coding agent. The rationale column feeds the README's
> "key technical decisions" section.

## Core

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python 3.12 + FastAPI | LlamaIndex is Python-native; FastAPI gives async, typing, OpenAPI docs, SSE streaming |
| Orchestration | LlamaIndex | Ingestion pipeline, node parsers, retrievers, query engines out of the box; document in README why chosen over LangChain / hand-rolled |
| LLM | OpenAI `gpt-5-mini` (pinned model id), key via `.env.local` | High quality, fast, no GPU requirements for evaluators; configured behind OpenAI-compatible env vars so another provider swaps in without code changes. Alternative considered: `gpt-5` (better quality, higher cost) — note trade-offs in README |
| Embeddings | FastEmbed `BAAI/bge-small-en-v1.5` (pinned), local ONNX | Runs locally on CPU — zero API cost for ingestion, documents never leave the box for embedding; Qdrant-native library with a LlamaIndex integration. Alternative considered: OpenAI `text-embedding-3-small` (one less moving part, but per-token cost and data egress) — record in README |
| Vector DB | Qdrant (Docker) | Self-hosted, metadata filtering, native LlamaIndex integration |
| App DB | Postgres 16 (Docker) | Documents metadata, ingestion status, chat sessions/messages — relational data does not belong in a vector store |
| ORM/Migrations | SQLAlchemy 2 + Alembic | Explicit schema history; shows engineering discipline |
| Frontend | React + Vite + TypeScript + Tailwind | Separate SPA talking to FastAPI; clean fullstack separation |
| Parsing | LlamaIndex readers (PDF via `pypdf`, txt/md) | Minimal custom code |
| Testing | pytest (backend), Vitest (frontend), 1 Playwright e2e | Pragmatic coverage |
| RAG evals | LlamaIndex `core.evaluation` (faithfulness, relevancy, answer/context relevancy, correctness, semantic similarity, guideline, retriever hit-rate/MRR via `BatchEvalRunner`) + DeepEval LlamaIndex integration (faithfulness, answer relevancy, task completion) | Standard, maintained evaluators over a hand-rolled scorer; two independent judges for the metrics that matter most; judge LLM = the configured OpenAI model |
| Observability | structlog JSON logs + per-request trace (query, node ids, scores, tokens, latency); optional local Langfuse container | Rubric item without cloud dependencies |
| Packaging | docker-compose: `frontend`, `api`, `postgres`, `qdrant` | One command after adding the API key to `.env.local` |
| Deps | `uv` with locked versions | Fast, reproducible installs |

## Rules

- **Deployment target is localhost only** — `docker compose up` on the evaluator's machine is the entire deployment story. Hyperscaler productionization is a README discussion item (per the brief), never implemented code/config.
- The only cloud dependency is the OpenAI API; data stores run locally in Docker.
- Pin exact versions (Python deps locked via `uv.lock`, Docker images by tag, model ids pinned in config).
- Type hints + `mypy` on the backend (chosen over pyright: one canonical checker, CI-friendly); strict TS on the frontend.
- Secrets via gitignored `.env.local` (`OPENAI_API_KEY` and optional overrides); ship `.env.example` documenting every variable. The key is backend-only — never exposed to the frontend, never logged.
- Config loading order: `.env` (defaults) then `.env.local` (secrets/overrides, wins). compose injects `.env.local` into the `api` service via `env_file`.
- The api fails fast at startup with a clear error if `OPENAI_API_KEY` is missing — not at first query.
- Every phase merges only when its `validation.md` passes.
- LLM answers **only** from retrieved context; refusal path is a feature.
- Escape hatch: the LLM is configured behind `LLM_BASE_URL` / `LLM_MODEL` env vars pointing at any OpenAI-compatible endpoint — so another provider swaps in without code changes. `EMBED_MODEL` selects the FastEmbed model (local; changing it requires re-ingestion — vector dims must match the Qdrant collection).
- The embedding model is pre-downloaded at image build (or explicit startup warmup) and cached in a volume — never a surprise download at first upload.
