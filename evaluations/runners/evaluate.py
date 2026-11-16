"""Run actual retrieval comparisons. Paid answer checks require --with-answers."""

import argparse
import json
import statistics
import time
from contextlib import ExitStack
from pathlib import Path

from agent_case import run_agent_case
from qdrant_client import QdrantClient
from report_metrics import answer_behavior_scores, compare_retrieval_modes

from smartdesk.config import Settings
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.rag.rag_factory import build_rag

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["development", "held_out"], default="held_out")
    parser.add_argument(
        "--local", action="store_true", help="Use a temporary embedded Qdrant index"
    )
    parser.add_argument(
        "--with-answers", action="store_true", help="Calls the paid LLM for each case"
    )
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    settings = Settings(_env_file=ROOT / ".env", model_cache_dir=str(ROOT / ".cache/models"))
    client = QdrantClient(":memory:") if args.local else None
    with ExitStack() as stack:
        rag = build_rag(settings, client)
        stack.callback(rag.close)
        evaluate(args, settings, rag, stack)


def evaluate(args, settings, rag, stack):
    retriever = rag.retrieval
    if args.local:
        rag.ingestion.run(ROOT / "knowledge_base")
    cases = [
        json.loads(line)
        for line in (ROOT / "evaluations/datasets/knowledge.jsonl").read_text().splitlines()
    ]
    cases = [c for c in cases if c["split"] == args.split][: args.limit]
    report = {
        "split": args.split,
        "case_count": len(cases),
        "models": {
            "dense": settings.embedding_model,
            "sparse": settings.sparse_model,
            "reranker": settings.reranker_model,
        },
        "threshold": settings.reranker_min_score,
        "modes": {},
        "answers": None,
    }
    for mode in ("dense", "sparse", "hybrid", "reranked"):
        results = []
        for case in cases:
            if not case["answerable"]:
                continue
            start = time.perf_counter()
            passages = retriever.search(case["query"], mode)
            ids = [p.id.split(":")[0] for p in passages]
            expected = set(case["expected_documents"])
            ranks = [i + 1 for i, identifier in enumerate(ids) if identifier in expected]
            results.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "retrieved": ids,
                    "scores": [p.score for p in passages],
                    "recall": len(set(ids) & expected) / len(expected),
                    "reciprocal_rank": 1 / min(ranks) if ranks else 0,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                }
            )
        report["modes"][mode] = {
            "recall_at_5": statistics.mean(r["recall"] for r in results),
            "mrr": statistics.mean(r["reciprocal_rank"] for r in results),
            "mean_latency_ms": statistics.mean(r["latency_ms"] for r in results),
            "cases": results,
        }
        print(
            f"{mode}: Recall@5={report['modes'][mode]['recall_at_5']:.3f}, MRR={report['modes'][mode]['mrr']:.3f}",
            flush=True,
        )
    if args.with_answers:
        if not settings.openai_api_key.get_secret_value():
            raise SystemExit("OPENAI_API_KEY is required for --with-answers")
        model = LanguageModel(settings)
        stack.callback(model.client.close)
        service = QueryPipeline(retriever, model)
        report["answers"] = [run_agent_case(model, service, case) for case in cases]
        report["answer_behavior"] = answer_behavior_scores(report["answers"])
    report["comparison_vs_dense"] = compare_retrieval_modes(report["modes"])
    path = args.output or ROOT / f"evaluations/reports/{args.split}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
