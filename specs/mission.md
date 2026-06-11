# Mission

**DocChat** (working name) is a conversational AI assistant that answers questions about a user-supplied document collection, built as a take-home assignment for the Fullstack AI role at Newpage Solutions.

## What We Do

Users upload documents (PDF, text), the system ingests them into a retrieval index, and a chat interface answers questions grounded strictly in those documents — with citations back to the source.

The data stores and embeddings run locally (Postgres, Qdrant, FastEmbed); only the LLM uses the OpenAI API, with the key supplied via a gitignored `.env.local`. Clone, add your key, compose up, use.

## Who We Serve

- **The evaluators** — they need to clone, add an API key, run one command, and see a working, well-designed RAG application with clean code.
- **The end user persona** — someone with a pile of documents who wants trustworthy, cited answers, not hallucinations. (Privacy-sensitive users who can't send documents to a cloud API can swap in a local model via the provider env vars — acknowledged as a trade-off in the README.)

## What Success Looks Like

- A working upload → ingest → ask → cited-answer loop with a polished UI.
- Code a stranger can read; containerised; tested where it matters.
- A README that explains the reasoning (chunking, models, retrieval, guardrails, observability) in my own words.
- Honest acknowledgement of trade-offs (hosted LLM convenience/quality vs local privacy, API cost) and what's deferred.

## Explicit Non-Goals

- Multi-tenancy, auth, billing — acknowledged in README as production concerns.
- Handling every document format and edge case.
- The "best" possible RAG pipeline — a solid, well-reasoned basic one beats an over-engineered broken one (per the assignment brief).
