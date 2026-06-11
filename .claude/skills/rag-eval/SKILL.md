---
name: rag-eval
description: >
  Run the RAG quality gates: the golden-set eval harness (make eval) and the
  prompt-injection test suite, then interpret results against the documented
  thresholds. Use after changing prompts, retrieval parameters, chunking,
  guardrails, or the LLM/embedding configuration. Costs OpenAI tokens — confirm
  with the user before running unless they explicitly asked for evals.
---

# Run and interpret the RAG quality gates

Two layers guard answer quality: the eval harness in `evals/run_evals.py` (LlamaIndex
core evaluators + DeepEval over `evals/golden_set.json`) and the injection suite in
`api/tests/test_injection.py`.

## Prerequisites

- The compose stack must be up (the harness needs Qdrant; it ingests `samples/docs/`
  into a throwaway collection itself, so the ingestion service path is not required).
- A **real** `OPENAI_API_KEY` in `.env.local` — the judge models call OpenAI. The key
  on this machine may be a placeholder; a wall of 401s means fix the key, not the code.
- `make eval` costs real tokens (judge = the configured OpenAI model). It is on-demand
  by design. For a cheaper signal first, run the free layers: `make test` includes the
  injection suite, and `--no-deepeval --limit N` shrinks the eval run.

## Steps

1. `make test` first — it is free and includes `api/tests/test_injection.py` (injected
   instructions in documents must not override the system prompt, and out-of-corpus
   questions must hit the refusal sentinel).
2. `make eval` (or `cd api && uv run python ../evals/run_evals.py --limit N` to bound
   cost). It fetches samples itself if absent.
3. Read the report against `THRESHOLDS` in `evals/run_evals.py` (faithfulness ≥ 0.8,
   relevancy ≥ 0.7, correctness normalized /5, hit_rate/mrr for retrieval, etc. — the
   file is the source of truth, don't quote thresholds from memory).
4. Refusal correctness is binary: unanswerable golden-set questions must produce the
   refusal sentinel. Any answered-when-unanswerable case is a guardrail regression
   regardless of the metric scores.

## Interpreting failures

- Retrieval metrics (hit_rate, mrr, context_relevancy) down → suspect chunking
  (`CHUNK_SIZE`/`CHUNK_OVERLAP`), `RETRIEVAL_TOP_K`/`RETRIEVAL_SCORE_THRESHOLD`, or
  payload-contract drift between `api/app/ingestion.py` and `api/app/retrieval.py`.
- Faithfulness/correctness down with retrieval healthy → suspect `api/app/prompts.py`
  or context assembly in `api/app/chat.py`.
- Single-metric flake near threshold on one question → re-run that slice before
  concluding; LLM judges are noisy. Persistent or multi-question drops are real.

Report the per-metric pass/fail table, name the questions that failed, and state
whether the gate as a whole passed. Don't tune thresholds to make a run pass — if a
threshold seems wrong, say so and leave the decision to the user.
