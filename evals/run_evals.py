"""Evaluation harness for the DocChat RAG pipeline.

Measures retrieval and answer quality with the standard evaluators from
LlamaIndex core and DeepEval rather than a hand-rolled scorer, over the curated
golden set in golden_set.json against the sample corpus.

Run via `make eval`. Standalone:
    cd api && uv run python ../evals/run_evals.py [--limit N] [--no-deepeval]

The sample corpus is fetched by the `make fetch-samples` target (one fetch path
for the whole project); this harness only checks samples/docs/ is populated and
tells you to run that target if it is empty — it does not clone anything itself.

The harness is otherwise self-contained: it ingests samples/docs into a throwaway
Qdrant collection using the same FastEmbed model the app uses, so it does not
depend on the unit-06 ingestion service being up — only Qdrant and an OpenAI key.

Layers:
  1. LlamaIndex core (judge = configured OpenAI model) via BatchEvalRunner:
     Faithfulness, Relevancy, AnswerRelevancy, ContextRelevancy, Correctness,
     SemanticSimilarity, plus two Guideline checks; RetrieverEvaluator for
     hit_rate / mrr over query -> expected-source pairs.
  2. DeepEval (local mode): Faithfulness, AnswerRelevancy, TaskCompletion.

Refusal correctness is checked explicitly: unanswerable questions must produce
the refusal sentinel, not an answer.

Thresholds are documented in THRESHOLDS below and echoed in the report.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = Path(__file__).resolve().parent / "golden_set.json"
SAMPLES_DIR = REPO_ROOT / "samples" / "docs"

# Per-metric pass thresholds (0..1 unless noted). Documented in README too.
THRESHOLDS: dict[str, float] = {
    "faithfulness": 0.8,
    "relevancy": 0.7,
    "answer_relevancy": 0.7,
    "context_relevancy": 0.6,
    "correctness": 0.7,  # CorrectnessEvaluator is 1-5; normalized to /5 for the gate
    "semantic_similarity": 0.7,
    "guideline_citation": 0.5,
    "guideline_refusal": 0.5,
    "hit_rate": 0.7,
    "mrr": 0.6,
    "deepeval_faithfulness": 0.8,
    "deepeval_answer_relevancy": 0.7,
    "deepeval_task_completion": 0.7,
}

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


@dataclass
class GoldenItem:
    id: str
    question: str
    reference_answer: str
    expected_sources: list[str]
    answerable: bool


@dataclass
class AnswerRecord:
    item: GoldenItem
    answer: str
    contexts: list[str]
    source_files: list[str]
    refused: bool
    scores: dict[str, float] = field(default_factory=dict)


def load_golden(limit: int | None = None) -> list[GoldenItem]:
    data = json.loads(GOLDEN_PATH.read_text())
    items: list[GoldenItem] = []
    for entry in data["answerable"]:
        items.append(GoldenItem(answerable=True, **entry))
    for entry in data["unanswerable"]:
        items.append(GoldenItem(answerable=False, **entry))
    if limit is not None:
        # Keep a mix: front-load answerable, but always keep some unanswerable.
        answerable = [i for i in items if i.answerable][:limit]
        unanswerable = [i for i in items if not i.answerable][: max(1, limit // 3)]
        items = answerable + unanswerable
    return items


# --- Ingest + retrieve + answer (reuses the app's production retrieval path) ----
#
# Rather than a second LlamaIndex vector-store stack, the harness ingests into a
# throwaway Qdrant collection with the same FastEmbed embedder and direct upsert
# the app uses, then retrieves through app.retrieval.search and answers through
# app.chat — so the eval measures the real pipeline, not a parallel one.


def _configure_llama_settings() -> None:
    """Point the LlamaIndex evaluators' judge at the configured OpenAI model and
    give SemanticSimilarityEvaluator a local FastEmbed embed model (no judge cost)."""
    from llama_index.core import Settings as LISettings
    from llama_index.embeddings.fastembed import FastEmbedEmbedding
    from llama_index.llms.openai import OpenAI

    from app.config import get_settings

    s = get_settings()
    LISettings.llm = OpenAI(model=s.llm_model, api_key=s.openai_api_key, api_base=s.llm_base_url)
    LISettings.embed_model = FastEmbedEmbedding(model_name=s.embed_model)


def _chunk_markdown(text: str) -> list[str]:
    """Cheap fixed-window splitter mirroring CHUNK_SIZE/OVERLAP for ingestion."""
    from llama_index.core.node_parser import SentenceSplitter

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_text(text)


def build_index(collection: str) -> str:
    """Ingest samples/docs into a fresh Qdrant collection; return the collection name."""
    from qdrant_client.models import Distance, PointStruct, VectorParams

    from app.config import get_settings
    from app.retrieval import embed_query
    from app.vectorstore import get_qdrant

    settings = get_settings()
    client = get_qdrant()
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=settings.embed_dim, distance=Distance.COSINE),
    )

    points: list[Any] = []
    pid = 0
    for path in sorted(SAMPLES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for chunk_index, chunk in enumerate(_chunk_markdown(text)):
            points.append(
                PointStruct(
                    id=pid,
                    vector=embed_query(chunk),
                    payload={
                        "doc_id": path.stem,
                        "filename": path.name,
                        "page": None,
                        "chunk_index": chunk_index,
                        "text": chunk,
                    },
                )
            )
            pid += 1
    # Upsert in batches to stay under request size limits.
    for start in range(0, len(points), 256):
        client.upsert(collection_name=collection, points=points[start : start + 256], wait=True)
    print(f"  ingested {len(points)} chunks from {len(list(SAMPLES_DIR.glob('*.md')))} docs")
    return collection


def _answer_one(question: str, top_k: int) -> tuple[str, list[str], list[str]]:
    """Run the real chat pipeline for one question; return (answer, contexts, sources)."""
    import asyncio
    import json as _json

    from app.chat import InMemoryPersistence, stream_answer
    from app.retrieval import search

    nodes = search(question, k=top_k, apply_threshold=True)
    contexts = [n.text for n in nodes]
    sources = [n.filename for n in nodes]

    async def _run() -> str:
        parts = []
        async for ev in stream_answer("eval", question, InMemoryPersistence()):
            if ev["event"] == "token":
                parts.append(_json.loads(ev["data"])["delta"])
        return "".join(parts)

    return asyncio.run(_run()), contexts, sources


def answer_all(collection: str, items: list[GoldenItem], top_k: int = 5) -> list[AnswerRecord]:
    from app.config import get_settings
    from app.prompts import REFUSAL_TEXT

    settings = get_settings()
    original = settings.qdrant_collection
    object.__setattr__(settings, "qdrant_collection", collection)
    records: list[AnswerRecord] = []
    try:
        for item in items:
            answer, contexts, sources = _answer_one(item.question, top_k)
            refused = REFUSAL_TEXT.split(".")[0].lower() in answer.lower() or not contexts
            records.append(
                AnswerRecord(
                    item=item,
                    answer=answer,
                    contexts=contexts,
                    source_files=sources,
                    refused=refused,
                )
            )
            print(f"  answered {item.id}: refused={refused}")
    finally:
        object.__setattr__(settings, "qdrant_collection", original)
    return records


# --- Layer 1: LlamaIndex core evaluators ---------------------------------------


def run_llamaindex_layer(records: list[AnswerRecord]) -> None:
    import asyncio

    from llama_index.core.evaluation import (
        AnswerRelevancyEvaluator,
        BatchEvalRunner,
        ContextRelevancyEvaluator,
        CorrectnessEvaluator,
        FaithfulnessEvaluator,
        GuidelineEvaluator,
        RelevancyEvaluator,
        SemanticSimilarityEvaluator,
    )

    citation_guideline = (
        "The answer must support factual claims with an inline bracketed citation "
        "like [1], OR clearly state that the documents do not contain the answer."
    )
    refusal_guideline = (
        "If the provided context is insufficient to answer, the response must "
        "decline rather than guess."
    )

    evaluators = {
        "faithfulness": FaithfulnessEvaluator(),
        "relevancy": RelevancyEvaluator(),
        "answer_relevancy": AnswerRelevancyEvaluator(),
        "context_relevancy": ContextRelevancyEvaluator(),
        "correctness": CorrectnessEvaluator(),
        "semantic_similarity": SemanticSimilarityEvaluator(),
        "guideline_citation": GuidelineEvaluator(guidelines=citation_guideline),
        "guideline_refusal": GuidelineEvaluator(guidelines=refusal_guideline),
    }
    runner = BatchEvalRunner(evaluators, workers=4, show_progress=False)

    queries = [r.item.question for r in records]
    responses = [r.answer for r in records]
    contexts = [r.contexts for r in records]
    references = [r.item.reference_answer for r in records]

    results = asyncio.run(
        runner.aevaluate_response_strs(
            queries=queries,
            response_strs=responses,
            contexts_list=contexts,
            reference=references,
        )
    )

    for name, eval_results in results.items():
        for rec, res in zip(records, eval_results, strict=False):
            score = res.score
            if name == "correctness" and score is not None:
                score = score / 5.0  # normalize 1-5 to 0-1
            if score is None:
                score = 1.0 if res.passing else 0.0
            rec.scores[name] = float(score)


def run_retriever_metrics(collection: str, items: list[GoldenItem]) -> dict[str, float]:
    """hit_rate / mrr over answerable query -> expected-source pairs.

    A retrieval is a hit when any retrieved node's filename is in expected_sources.
    Ground truth is source filenames (not node ids), so this is computed directly
    against the same app.retrieval.search the chat engine uses.
    """
    from app.config import get_settings
    from app.retrieval import search

    answerable = [i for i in items if i.answerable and i.expected_sources]
    if not answerable:
        return {"hit_rate": 0.0, "mrr": 0.0}

    settings = get_settings()
    original = settings.qdrant_collection
    object.__setattr__(settings, "qdrant_collection", collection)
    hits = 0
    reciprocal = 0.0
    try:
        for item in answerable:
            nodes = search(item.question, k=5, apply_threshold=False)
            ranks = [
                r + 1
                for r, n in enumerate(nodes)
                if n.filename in item.expected_sources
            ]
            if ranks:
                hits += 1
                reciprocal += 1.0 / ranks[0]
    finally:
        object.__setattr__(settings, "qdrant_collection", original)
    n = len(answerable)
    return {"hit_rate": hits / n, "mrr": reciprocal / n}


# --- Layer 2: DeepEval ---------------------------------------------------------


def run_deepeval_layer(records: list[AnswerRecord]) -> None:
    try:
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            TaskCompletionMetric,
        )
        from deepeval.test_case import LLMTestCase
    except Exception as exc:  # deepeval optional / not installed
        print(f"  deepeval unavailable, skipping layer 2: {exc}")
        return

    from app.config import get_settings

    model = get_settings().llm_model

    faith = FaithfulnessMetric(threshold=THRESHOLDS["deepeval_faithfulness"], model=model)
    ans_rel = AnswerRelevancyMetric(threshold=THRESHOLDS["deepeval_answer_relevancy"], model=model)
    task = TaskCompletionMetric(threshold=THRESHOLDS["deepeval_task_completion"], model=model)

    for rec in records:
        tc = LLMTestCase(
            input=rec.item.question,
            actual_output=rec.answer,
            retrieval_context=rec.contexts or [""],
            expected_output=rec.item.reference_answer,
        )
        for key, metric in (
            ("deepeval_faithfulness", faith),
            ("deepeval_answer_relevancy", ans_rel),
            ("deepeval_task_completion", task),
        ):
            try:
                metric.measure(tc)
                rec.scores[key] = float(metric.score or 0.0)
            except Exception as exc:
                print(f"  deepeval {key} failed on {rec.item.id}: {exc}")


# --- Reporting -----------------------------------------------------------------


def check_refusals(records: list[AnswerRecord]) -> list[str]:
    """Return ids that failed the refusal contract (wrong direction either way)."""
    failures = []
    for rec in records:
        if rec.item.answerable and rec.refused:
            failures.append(f"{rec.item.id}: answerable question was refused")
        if not rec.item.answerable and not rec.refused:
            failures.append(f"{rec.item.id}: unanswerable question was answered (hallucination risk)")
    return failures


def print_report(
    records: list[AnswerRecord],
    retrieval_metrics: dict[str, float],
    refusal_failures: list[str],
) -> bool:
    metric_keys = [k for k in THRESHOLDS if k not in {"hit_rate", "mrr"}]
    present = [k for k in metric_keys if any(k in r.scores for r in records)]

    print("\n" + "=" * 100)
    print("PER-QUESTION SCORES (answerable questions; blank = metric not run)")
    print("=" * 100)
    header = "id     " + "".join(f"{k[:10]:>12}" for k in present)
    print(header)
    answerable = [r for r in records if r.item.answerable]
    for rec in answerable:
        row = f"{rec.item.id:<7}"
        for k in present:
            v = rec.scores.get(k)
            row += f"{'—':>12}" if v is None else f"{v:>12.2f}"
        print(row)

    print("\n" + "-" * 100)
    print("AGGREGATES vs THRESHOLDS")
    print("-" * 100)
    all_pass = True
    for k in present:
        vals = [r.scores[k] for r in answerable if k in r.scores]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        thr = THRESHOLDS[k]
        ok = mean >= thr
        all_pass = all_pass and ok
        print(f"  {k:<28} mean={mean:5.2f}  threshold={thr:4.2f}  {'PASS' if ok else 'FAIL'}")

    for k in ("hit_rate", "mrr"):
        v = retrieval_metrics.get(k, 0.0)
        thr = THRESHOLDS[k]
        ok = v >= thr
        all_pass = all_pass and ok
        print(f"  {k:<28} value={v:5.2f}  threshold={thr:4.2f}  {'PASS' if ok else 'FAIL'}")

    print("\n" + "-" * 100)
    print("REFUSAL CORRECTNESS")
    print("-" * 100)
    if refusal_failures:
        all_pass = False
        for f in refusal_failures:
            print(f"  FAIL  {f}")
    else:
        print("  PASS  all answerable questions answered, all unanswerable refused")

    surface_faithfulness_disagreements(answerable)

    print("\n" + "=" * 100)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 100)
    return all_pass


def surface_faithfulness_disagreements(records: list[AnswerRecord]) -> None:
    """Report where LlamaIndex and DeepEval faithfulness disagree — not averaged."""
    rows = []
    for rec in records:
        li = rec.scores.get("faithfulness")
        de = rec.scores.get("deepeval_faithfulness")
        if li is not None and de is not None and abs(li - de) >= 0.3:
            rows.append((rec.item.id, li, de))
    if rows:
        print("\n  Faithfulness disagreements (LlamaIndex vs DeepEval, |Δ| ≥ 0.3):")
        for rid, li, de in rows:
            print(f"    {rid}: llamaindex={li:.2f}  deepeval={de:.2f}")


# --- Orchestration -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG eval harness.")
    parser.add_argument("--limit", type=int, default=None, help="cap golden items")
    parser.add_argument("--no-deepeval", action="store_true", help="skip the DeepEval layer")
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "api"))

    if not list(SAMPLES_DIR.glob("*.md")):
        print(
            f"no sample docs in {SAMPLES_DIR}. Run `make fetch-samples` first.",
            file=sys.stderr,
        )
        return 1

    _configure_llama_settings()

    items = load_golden(args.limit)
    print(f"loaded {len(items)} golden items "
          f"({sum(i.answerable for i in items)} answerable)")

    collection = f"eval_{uuid.uuid4().hex[:8]}"
    from app.vectorstore import get_qdrant

    print(f"ingesting sample corpus into {collection} ...")
    build_index(collection)
    try:
        print("answering golden questions ...")
        records = answer_all(collection, items)

        print("running LlamaIndex core evaluators ...")
        run_llamaindex_layer(records)
        retrieval_metrics = run_retriever_metrics(collection, items)

        if not args.no_deepeval:
            print("running DeepEval layer ...")
            run_deepeval_layer(records)

        refusal_failures = check_refusals(records)
        ok = print_report(records, retrieval_metrics, refusal_failures)
        return 0 if ok else 1
    finally:
        try:
            get_qdrant().delete_collection(collection)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
