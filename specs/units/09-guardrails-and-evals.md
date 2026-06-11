# 09 — Guardrails & Evals

**Roadmap phase:** 7 · **Integration deps:** 07 · **Teammate:** `rag` · *(merges old units 16 + 17)*

## Owns (files)
`evals/` (golden set, runner, fetch-samples script), the injection test suite, and the
prompt-hardening edits to 07's `prompts.py` (same teammate — internal handoff).
`make eval` / `make fetch-samples` targets + deepeval pin → message the lead.

## Goal
The assistant can't be talked out of its grounding — by users or by documents — and
retrieval/answer quality is measured, not vibed, using the standard evaluators from
LlamaIndex core and DeepEval rather than a hand-rolled scorer.

## Scope

### Guardrails
- System prompt hardening: answer only from context; ignore instructions embedded inside
  documents (prompt injection defense)
- Input limits: max question length, sanitization; upload size caps enforced server-side
  (05 confirms)
- Injection test cases: a document containing "ignore previous instructions…" must not change
  behavior

### Golden dataset
- Sample corpus: architecture docs from [github.com/v9ai/agentic-sales](https://github.com/v9ai/agentic-sales),
  fetched via `make fetch-samples` into gitignored `samples/docs/` (28 md files — never vendored)
- ~10 golden Q&A pairs over that corpus (answerable + unanswerable mix), committed alongside
  the eval script
- Bootstrap candidate questions with LlamaIndex `RagDatasetGenerator`, then hand-curate
  (the brief wants my judgment, not raw LLM output)

### Layer 1 — LlamaIndex core evaluators (`llama_index.core.evaluation`, judge = configured OpenAI model)
Run via `BatchEvalRunner` over the golden set:
- `FaithfulnessEvaluator` — answer grounded in retrieved context (hallucination check)
- `RelevancyEvaluator` — answer + context relevant to the query
- `AnswerRelevancyEvaluator` — answer addresses the question asked
- `ContextRelevancyEvaluator` — retrieved chunks relevant to the query (retrieval precision proxy)
- `CorrectnessEvaluator` — answer vs golden reference answer (1–5 score)
- `SemanticSimilarityEvaluator` — embedding similarity to reference (uses local FastEmbed — no judge cost)
- `GuidelineEvaluator` — custom guidelines: "every claim carries a citation", "refuses when
  context is insufficient"
- Retrieval metrics via `RetrieverEvaluator` (`hit_rate`, `mrr`) on the golden
  query → expected-source pairs
- Skipped, documented in README: `PairwiseComparisonEvaluator` (needs two systems to compare;
  useful later for prompt A/B), multi-modal and benchmark suites (out of scope)

### Layer 2 — DeepEval (LlamaIndex integration)
- `pip install -U deepeval` (pinned); span-based integration per
  [deepeval.com/integrations/frameworks/llamaindex](https://deepeval.com/integrations/frameworks/llamaindex)
- `FaithfulnessMetric` (with `retrieval_context`) and `AnswerRelevancyMetric` on LLM spans —
  independent second opinion on the two most important qualities
- `TaskCompletionMetric` on the chat engine span — did the assistant actually complete the ask
- DeepEval judge uses the same configured OpenAI model/key; no DeepEval cloud account required
  (local mode)

### Runner & reporting
- `make eval`: fetch samples (if absent) → ingest → run both layers → print a per-question ×
  per-metric table + aggregate scores
- Thresholds documented per metric (e.g. faithfulness ≥ 0.8, hit_rate ≥ 0.7); failures listed
  with the offending question
- Refusal correctness checked explicitly: unanswerable questions must score as refusals, not
  answers
- Not CI-gated — acknowledged as deferred (evals cost tokens; run on demand)

## Parallel notes
Dataset curation, the `make fetch-samples` target, eval runner scaffolding, and the injection
test corpus all build before 07 lands — they consume only the documented endpoint shapes.
Prompt-hardening iterations and the green eval run need 07.

## Done when
- Injection test suite passes (malicious doc + malicious question)
- Limits return clear 4xx errors, documented in OpenAPI
- `make eval` runs green against the compose stack with the sample corpus
- Both layers report scores; disagreements between LlamaIndex and DeepEval faithfulness are
  surfaced, not averaged away
- README quality-controls section cites the metric table and thresholds
