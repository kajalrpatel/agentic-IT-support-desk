"""Evaluate recorded answers directly in LangSmith with an optional paid judge."""

import argparse
import json
from pathlib import Path

from answer_evaluators import build_answer_judge, citation_coverage
from langsmith import Client
from openai import OpenAI

from smartdesk.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument(
        "--with-judge",
        action="store_true",
        help="Paid gpt-4o-mini faithfulness and relevance scores for cited answers",
    )
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    answers = json.loads(args.report.read_text(encoding="utf-8")).get("answers") or []
    if not answers:
        raise SystemExit("Generate an answer report with --with-answers first")
    selected = answers[: args.limit]
    records = {a["id"]: a for a in selected}
    settings = Settings(_env_file=Path(__file__).resolve().parents[2] / ".env")
    if not settings.langsmith_api_key.get_secret_value():
        raise SystemExit("Configure LANGSMITH_API_KEY before publishing")
    if args.with_judge and not settings.openai_api_key.get_secret_value():
        raise SystemExit("OPENAI_API_KEY is required for --with-judge")
    client = Client(
        api_key=settings.langsmith_api_key.get_secret_value(), api_url=settings.langsmith_endpoint
    )
    dataset = client.create_dataset(
        dataset_name=args.dataset_name,
        description="Recorded SmartDesk answers; citation coverage and optional custom answer judge",
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"id": a["id"], "query": a["query"]},
                "outputs": {"expected_answerable": a["expected_answerable"]},
            }
            for a in selected
        ],
    )

    def replay_recorded_answer(inputs):
        answer = records[inputs["id"]]
        return {
            "response": answer["response"],
            "retrieved_contexts": answer.get("retrieved_contexts")
            or [c["excerpt"] for c in answer["response"]["citations"]],
        }

    with OpenAI(
        api_key=settings.openai_api_key.get_secret_value() or "unused", timeout=35, max_retries=0
    ) as judge:
        evaluators = [citation_coverage]
        if args.with_judge:
            evaluators.append(build_answer_judge(judge))
        results = client.evaluate(
            replay_recorded_answer,
            data=dataset.id,
            evaluators=evaluators,
            max_concurrency=1,
            experiment_prefix="smartdesk-answers",
            metadata={
                "execution": "recorded-replay",
                "total_answer_count": len(answers),
                "selected_count": len(selected),
                "judge_model": "gpt-4o-mini" if args.with_judge else None,
            },
        )
        print(results.experiment_name)


if __name__ == "__main__":
    main()
