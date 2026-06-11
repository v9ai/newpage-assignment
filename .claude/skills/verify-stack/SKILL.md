---
name: verify-stack
description: >
  Bring up the docker compose stack and prove the full RAG round trip works:
  health all-ok, upload a sample doc, wait for ingestion to reach ready,
  retrieve hits it, chat answers with citations. Use after changes to
  ingestion, retrieval, chat, compose, or Dockerfiles, or whenever asked
  "does the app still work?".
---

# Verify the DocChat stack end to end

The deployment story is localhost compose only. This skill proves the real path —
upload → parse → chunk → embed → store → retrieve → cited answer — not just unit tests.

## Prerequisites

- `.env.local` must exist with `OPENAI_API_KEY`. The api fails fast at startup if it is
  missing. Note: the key in `.env.local` may be a placeholder — health will still show
  `openai: configured`, but the chat step will fail with a 401. If the chat step 401s,
  report that the key is a placeholder rather than a code regression, and stop there:
  steps 1–5 still validate everything except the LLM call.
- Sample corpus: `make fetch-samples` populates `samples/docs/` if empty.

## Steps

1. `docker compose up --build -d`, then wait for health:
   `curl -s localhost:8000/api/health` until `postgres: ok`, `qdrant: ok`,
   `openai: configured`. First cold start downloads the ~80 MB FastEmbed model; give it
   time before declaring failure. On a port conflict, report which port and stop.
2. Upload one sample: `curl -s -F "file=@samples/docs/<some>.md" localhost:8000/api/documents`
   → expect a `DocumentOut` with status `uploaded` or `ingesting`. Keep the returned `id`.
3. Poll `GET /api/documents` until that id reaches `ready` (or `failed` — if failed,
   report the `failure_reason` verbatim).
4. Retrieval round trip: `POST /api/retrieve` with a query phrased from that document's
   content. Expect nodes whose `doc_id` equals the uploaded id and whose payload carries
   `filename`, `page`, `chunk_index`, `text`. Zero nodes for on-topic text means the
   ingestion/retrieval payload contract drifted — name that explicitly (see the
   contract-guardian agent).
5. Chat: create a session (`POST /api/sessions`), then `POST /api/sessions/{id}/messages`
   with an on-topic question. Read the SSE stream: expect `token` events, a `citations`
   event with at least one citation pointing at the uploaded doc, and `done`.
6. Negative check: ask something not in the corpus; expect a token-streamed refusal with
   `citations: []` on `done` — not an `error` event.

## Reporting

State plainly which steps passed and where the chain broke, with the failing step's raw
response. If everything passed, say the round trip is verified and which document/query
proved it. Leave the stack running unless asked to tear it down (`docker compose down`).
