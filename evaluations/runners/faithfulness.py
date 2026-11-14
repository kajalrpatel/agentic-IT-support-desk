"""Optional paid Ragas evaluation of previously generated answer reports."""
import argparse
import json
from pathlib import Path

from ragas import EvaluationDataset, evaluate
from ragas.metrics import Faithfulness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if not report.get("answers"):
        raise SystemExit("Generate an answer report with --with-answers first")
    questions = {c["id"]: c["query"] for c in report["modes"]["reranked"]["cases"]}
    samples = [{"user_input": questions[item["id"]], "response": item["response"]["text"], "retrieved_contexts": [c["excerpt"] for c in item["response"]["citations"]]} for item in report["answers"] if item["response"]["citations"] and item["id"] in questions]
    if not samples:
        raise SystemExit("No cited answers to evaluate")
    result = evaluate(EvaluationDataset.from_list(samples), metrics=[Faithfulness()])
    result.to_pandas().to_json(args.report.with_suffix(".faithfulness.json"), orient="records", indent=2)


if __name__ == "__main__":
    main()
