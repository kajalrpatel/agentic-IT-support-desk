"""Paid smoke checks for short issue descriptions and unsupported requests."""

import argparse
import json
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from smartdesk.agents.hr_policy_agent import build_hr_policy_agent
from smartdesk.agents.it_support_agent import build_it_support_agent
from smartdesk.agents.supervisor_agent import build_supervisor_nodes
from smartdesk.config import Settings
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.rag.rag_factory import build_rag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [
        ("Audio problems during an online meeting", "it-meeting-audio:0"),
        (
            "My audio is not working in an online meeting. What should I check?",
            "it-meeting-audio:0",
        ),
        ("How much does NovaTech reimburse for dental implants?", None),
    ]
    rows = []
    with ExitStack() as stack:
        model = LanguageModel(Settings())
        stack.callback(model.client.close)
        rag = build_rag(model.settings)
        stack.callback(rag.close)
        pipeline = QueryPipeline(rag.retrieval, model)
        agents = {"IT": build_it_support_agent(pipeline), "HR": build_hr_policy_agent(pipeline)}
        route, _ = build_supervisor_nodes(model)
        for question, expected_citation in cases:
            decision = route({"text": question, "email": "evaluation@example.com"})["route"]
            if decision["intent"] != "knowledge":
                rows.append({"query": question, "passed": False, "route": decision})
                continue
            result = agents[decision["category"]].invoke({"route": decision})
            response = result["response"]
            cited = [c["id"] for c in response["citations"]]
            passed = (
                expected_citation in cited
                if expected_citation
                else not cited and "support ticket" in response["text"]
            )
            rows.append(
                {
                    "query": question,
                    "passed": passed,
                    "expected_citation": expected_citation,
                    "route": decision,
                    "response": response,
                }
            )
        report = {
            "date": datetime.now(UTC).isoformat(),
            "model": model.settings.llm_model,
            "passed": sum(r["passed"] for r in rows),
            "total": len(rows),
            "cases": rows,
        }
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        if not all(r["passed"] for r in rows):
            raise SystemExit("Knowledge regression check failed")


if __name__ == "__main__":
    main()
