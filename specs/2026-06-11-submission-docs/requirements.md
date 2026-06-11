# Submission Docs Requirements — README & Supporting Docs

## Scope

Every documentation deliverable from the brief's "What to Submit", specified section by
section so nothing is improvised at the end. Executed by unit 20, but the content
requirements live here.

## The README (root `README.md`)

### 1. Quick setup
- Prerequisites (Docker + an OpenAI API key) and tested one-path setup:
  `cp .env.example .env.local` → add key → `docker compose up --build` → URL to open
- `make fetch-samples` documented as the way to get the demo corpus
- Troubleshooting: the 2–3 most likely failures (missing key, port collisions, cold first build)

### 2. Architecture overview
- A simple diagram (Mermaid in the README — renders on GitHub, no image tooling):
  web (nginx) → api (FastAPI) → Postgres / Qdrant / OpenAI, with the ingestion path
  (upload → parse → chunk → FastEmbed → Qdrant) and query path (question → retrieve → LLM → cited answer)
- One paragraph per component on its responsibility

### 3. Productionization (AWS / GCP / Azure / Cloudflare)
- Secrets: `.env.local` → a managed secret store (e.g. AWS Secrets Manager / GCP Secret Manager / Azure Key Vault)
- Data: compose Postgres/Qdrant → managed equivalents (RDS/Cloud SQL/Azure DB; Qdrant Cloud or self-hosted on k8s)
- Compute: containers → ECS/Fargate, Cloud Run, Azure Container Apps, or Cloudflare Workers/Containers for the edge tier
- Plus: TLS/ingress, autoscaling stateless api, async ingestion queue, CI/CD, backups, rate limiting & auth

### 4. RAG/LLM approach & decisions
For each: choices considered → final choice → why (the tech-stack rationale column feeds this):
- LLM (`gpt-5-mini` vs `gpt-5` vs local), embeddings (FastEmbed `bge-small-en-v1.5` vs OpenAI), vector DB (Qdrant vs pgvector vs others), orchestration (LlamaIndex vs LangChain vs hand-rolled)
- Chunking (size/overlap and why), prompt engineering (grounded-answer prompt, refusal), context management (history condensation under token budget)
- Guardrails (injection defense, input limits), quality (the unit-17 eval matrix + thresholds), observability (structured traces, request ids)

### 5. Key technical decisions
- The non-RAG ones: monorepo, uv, Alembic-from-commit-one, nginx same-origin proxy,
  `.env.local` secrets pattern, typed-everything (mypy strict / strict TS)

### 6. Engineering standards followed — and skipped
- Followed: types, lint, migrations, tests where they matter, pinned versions, containerised
- Skipped, with honesty: no CI, no auth/multi-tenancy, evals not gated, single-node compose

### 7. AI tools in the development process
- Workflow actually used: spec-first (specs/ folder), small units, validation gates per phase
- Do's & don'ts learned; how the output is kept repeatable and maintainable (specs as law, review every diff, tests before merge)

### 8. What I'd do differently with more time
- Pull from the deferred list: reranking, hybrid search, async ingestion queue, evals in CI, auth — plus anything discovered during the build

### 9. Authorship note
- **Sections 4–8 are written by hand.** AI may draft structure/boilerplate elsewhere, but
  the reasoning sections must reflect the author's own judgment — the brief calls this out
  explicitly ("we need your thoughts, not an LLM's direct output").

## Beyond the README
- **Screenshots** (committed under `docs/screenshots/`): landing/health, upload + ingestion status, chat with streamed cited answer, citation→source preview, a designed error/refusal state
- **Video** (time permitting): ≤2 min walkthrough of upload → ask → cited answer; link in README
- **specs/ folder** referenced from the README as the AI-workflow exhibit itself

## Out of scope
- Marketing copy, hosted demo, exhaustive API reference (OpenAPI docs serve that)
