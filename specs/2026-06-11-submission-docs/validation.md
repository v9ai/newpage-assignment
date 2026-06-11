# Submission Docs Validation

## Definition of Done

### 1. Setup instructions actually work
A fresh clone on a machine with only Docker + a key, following README verbatim,
reaches a working cited answer. No undocumented steps.

### 2. Every brief bullet is covered
Each "What to Submit" item in `assignment.md` maps to a README section:
quick setup · architecture (+diagram) · productionization (AWS/GCP/Azure/Cloudflare) ·
RAG/LLM decisions (LLM, embeddings, vector DB, orchestration, prompt & context,
guardrails, quality, observability) · key technical decisions · standards followed/skipped ·
AI-tool process · do-differently · screenshots (· video if recorded)

### 3. Decisions show alternatives
Section 4 names at least one rejected alternative per choice, with the reason —
"choices considered and final choice", not just the final choice.

### 4. Authorship
Sections 4–8 read as the author's voice and judgment (hand-written pass done);
the AI-tools section describes the actual workflow used in this repo (specs/, units,
validation gates), not generic advice.

### 5. Visuals
- Mermaid diagram renders on GitHub
- ≥5 screenshots committed and embedded, covering happy path + one designed error/refusal state
- Video linked if recorded

### 6. No leakage in docs
No real API key, no private URLs, no secrets in any screenshot or doc.
