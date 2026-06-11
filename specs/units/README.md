# Spec Units

The 10-phase [roadmap](../roadmap.md) decomposed into 20 small, independently shippable units.
Each unit states its goal, dependencies, scope, and done-when criteria. Build in numeric order
unless dependencies say otherwise; a unit is "done" only when its checklist passes.

| # | Unit | Phase |
|---|---|---|
| 01 | [Backend Scaffold](01-backend-scaffold.md) | 1 |
| 02 | [Config & Env Handling](02-config-and-env.md) | 1 |
| 03 | [Postgres & Migrations](03-postgres-migrations.md) | 1 |
| 04 | [Qdrant Wiring](04-qdrant-wiring.md) | 1 |
| 05 | [Frontend Scaffold](05-frontend-scaffold.md) | 1 |
| 06 | [Docker Compose Stack](06-docker-compose-stack.md) | 1 |
| 07 | [Upload API](07-upload-api.md) | 2 |
| 08 | [Document Parsing](08-document-parsing.md) | 2 |
| 09 | [Upload UI](09-upload-ui.md) | 2 |
| 10 | [Ingestion Pipeline](10-ingestion-pipeline.md) | 3 |
| 11 | [Ingestion Status](11-ingestion-status.md) | 3 |
| 12 | [Retrieval API](12-retrieval-api.md) | 4 |
| 13 | [RAG Chat Engine](13-rag-chat-engine.md) | 5 |
| 14 | [Chat Persistence & Context Management](14-chat-persistence.md) | 5 |
| 15 | [Chat UI](15-chat-ui.md) | 6 |
| 16 | [Guardrails](16-guardrails.md) | 7 |
| 17 | [Golden Eval Set & RAG Evaluation Harness](17-golden-eval-set.md) | 7 |
| 18 | [Observability](18-observability.md) | 8 |
| 19 | [Hardening & E2E](19-hardening-and-e2e.md) | 9 |
| 20 | [README & Submission](20-readme-and-submission.md) | 10 |

Provider summary: LLM = OpenAI `gpt-5-mini` (key in gitignored `.env.local`);
embeddings = FastEmbed `BAAI/bge-small-en-v1.5` running locally (no API cost for ingestion);
vector DB = Qdrant; app DB = Postgres; orchestration = LlamaIndex.
