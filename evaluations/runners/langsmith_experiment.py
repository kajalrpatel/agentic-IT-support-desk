"""Publish recorded retrieval results to LangSmith; does not call an LLM."""

import argparse
import json
from pathlib import Path

from langsmith import Client

if __package__:
    from .report_metrics import retrieval_scores
else:  # Direct invocation from backend/ remains supported.
    from report_metrics import retrieval_scores

from smartdesk.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def score_retrieval(run, example):
    scores = retrieval_scores(
        run.outputs["retrieved"], example.outputs["expected_documents"]
    )
    return {"results": [{"key": key, "score": value} for key, value in scores.items()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--dataset-name",
        required=True,
        help="New versioned name per benchmark revision",
    )
    args = parser.parse_args()
    settings = Settings(_env_file=ROOT / ".env")
    if not settings.langsmith_api_key.get_secret_value():
        raise SystemExit("Configure LANGSMITH_API_KEY before publishing")
    report = json.loads(args.report.read_text())
    labels = {
        c["id"]: c
        for c in map(
            json.loads,
            (ROOT / "evaluations/datasets/knowledge.jsonl").read_text().splitlines(),
        )
    }
    client = Client(
        api_key=settings.langsmith_api_key.get_secret_value(),
        api_url=settings.langsmith_endpoint,
    )
    dataset = client.create_dataset(
        dataset_name=args.dataset_name,
        description="Assistant-authored retrieval benchmark; recorded results",
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"id": c["id"], "query": c["query"]},
                "outputs": {
                    "expected_documents": labels[c["id"]]["expected_documents"]
                },
            }
            for c in report["modes"]["dense"]["cases"]
        ],
    )
    for mode, values in report["modes"].items():
        by_id = {c["id"]: c for c in values["cases"]}

        def replay_recorded_retrieval(inputs, records=by_id):
            value = records[inputs["id"]]
            return {
                "retrieved": value["retrieved"],
                "recorded_latency_ms": value["latency_ms"],
            }

        results = client.evaluate(
            replay_recorded_retrieval,
            data=dataset.id,
            evaluators=[score_retrieval],
            experiment_prefix=f"smartdesk-{mode}",
            max_concurrency=1,
            metadata={
                "mode": mode,
                "execution": "recorded-replay",
                "models": report["models"],
            },
        )
        print(f"{mode}: {results.experiment_name}")
    print(
        "LangSmith run latency measures replay. Use recorded_latency_ms for retrieval time."
    )


if __name__ == "__main__":
    main()
