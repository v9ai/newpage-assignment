# Roadmap

Phases are intentionally small — each is a shippable, independently testable slice.
The phases are decomposed into 20 small build units in [`specs/units/`](units/README.md), each with its own scope and done-when criteria — that is the working breakdown. Larger phases may additionally get a dated `specs/YYYY-MM-DD-<name>/` folder (`plan.md`, `requirements.md`, `validation.md`) before implementation, as Phase 1 does.

---

## Phase 1 — Walking Skeleton
- FastAPI scaffold (uv, typed, linted) + React/Vite/TS frontend scaffold
- `GET /api/health` reporting Postgres and Qdrant connectivity + whether the OpenAI key is configured
- Alembic migration 0001 (`documents` table stub)
- docker-compose with all four services: web, api, postgres, qdrant
- `.env.local` secrets wiring (`OPENAI_API_KEY`), documented in `.env.example`; api fails fast if missing

## Phase 2 — Upload & Parse
- Upload UI (drag-and-drop) + `POST /api/documents`
- LlamaIndex readers: extract text from PDF and txt/md; reject unsupported types gracefully
- Persist document records in Postgres (id, filename, size, status); document list view

## Phase 3 — Ingestion Pipeline
- LlamaIndex `IngestionPipeline`: node parser (chunk size/overlap — documented choice) → FastEmbed local embeddings → `QdrantVectorStore`
- Node metadata: doc id, page, chunk index
- Per-document ingestion status in Postgres (uploaded → ingesting → ready | failed), surfaced in UI

## Phase 4 — Retrieval API
- LlamaIndex retriever over the Qdrant index
- `POST /api/retrieve`: query → top-k nodes with scores + source metadata (debug/transparency endpoint)
- Score threshold + k as config; integration test on ingestion→retrieval round-trip (chunking unit tests live in Phase 3)

## Phase 5 — RAG Chat
- Chat engine with custom grounded-answer prompt; SSE streaming from FastAPI
- Inline citations mapping back to document + location
- Chat sessions + messages persisted in Postgres; history condensed under a token budget (context management)
- "Not in the documents" refusal path

## Phase 6 — Chat UI
- Chat interface: streaming tokens, message history, citation chips → source preview
- Empty/loading/error states (including LLM unreachable / rate-limited); mobile-friendly
- This is the "we expect a well designed application" phase — spend real time here

## Phase 7 — Guardrails & Quality
- System prompt hardening (answer only from context; ignore instructions inside documents — prompt injection)
- Input limits and sanitization; upload size caps
- Golden Q&A eval set (~10 questions) + `make eval` harness: LlamaIndex core evaluators (faithfulness, relevancy, correctness, retrieval hit-rate/MRR via BatchEvalRunner) cross-checked with DeepEval metrics (unit 17 has the full matrix)

## Phase 8 — Observability
- structlog JSON logs per request: query, retrieved node ids + scores, model, tokens, latency
- Request id propagation across api → llamaindex calls; errors surfaced, not swallowed
- Optional: local Langfuse container wired to LlamaIndex instrumentation

## Phase 9 — Hardening & Tests
- One Playwright e2e: upload → ingest → ask → cited answer
- Failure modes: OpenAI unreachable / invalid key / rate-limited, Qdrant down, Postgres down, oversized file
- Rate limiting on chat endpoint

## Phase 10 — Packaging & Submission
- Full docs contract in `specs/2026-06-11-submission-docs/` (section-by-section README requirements, screenshots, video, authorship rules)
- README: setup, architecture diagram, productionization plan (secrets management for the API key; managed Postgres/Qdrant; AWS/GCP/Azure/Cloudflare deployment)
- RAG decisions, engineering standards kept/skipped, AI-tool workflow, next steps
- API cost note + the OpenAI-compatible escape hatch (env vars accept any compatible endpoint/provider)
- Screenshots + short video; final pass: clone fresh, add key to `.env.local`, `docker compose up`, follow own README

---

Deferred (acknowledge in README): auth, multi-user isolation, reranking, hybrid search (Qdrant supports it — good "next step"), async ingestion queue, evals in CI.
