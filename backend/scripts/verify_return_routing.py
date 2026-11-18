"""Paid regression checks for procedural requests and clarification recovery."""

import json
from contextlib import ExitStack
from pathlib import Path

from smartdesk.agents.it_support_agent import build_it_support_agent
from smartdesk.agents.supervisor_agent import build_supervisor_nodes
from smartdesk.config import Settings
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.query_pipeline import ESCALATE, QueryPipeline
from smartdesk.rag.rag_factory import build_rag


def main():
    messages = [
        (
            "i want to return my laptop",
            "Could you please clarify if you want to return your laptop or if you are referring to something else?",
        ),
        (
            "yes, want to return mylaptop",
            "Could you clarify if you mean returning the laptop for repairs, exchange, or simply returning it to the company?",
        ),
        (
            "simplt return to company",
            "Could you clarify if you want to return your laptop for repairs, exchange, or simply for returning it to the company?",
        ),
        ("simply for returning it to the company", ""),
    ]
    rows = []
    with ExitStack() as stack:
        model = LanguageModel(Settings())
        stack.callback(model.client.close)
        rag = build_rag(model.settings)
        stack.callback(rag.close)
        agent = build_it_support_agent(QueryPipeline(rag.retrieval, model))
        route, _ = build_supervisor_nodes(model)
        history = []
        for index, (message, old_reply) in enumerate(messages):
            decision = route(
                {
                    "text": message,
                    "history": history,
                    "email": "evaluation@example.com",
                    "response": {"text": history[-1]["content"]} if history else None,
                }
            )["route"]
            passed = decision["intent"] == "knowledge" and decision["category"] == "IT"
            response = None
            if passed and index in {0, 3}:
                response = agent.invoke({"route": decision})["response"]
                passed = any(c["id"] == "it-device-return:0" for c in response["citations"])
            rows.append(
                {"query": message, "route": decision, "response": response, "passed": passed}
            )
            history += [
                {"role": "user", "content": message},
                {"role": "assistant", "content": old_reply},
            ]
        for message, previous in [
            ("Please create a ticket to arrange my laptop return", None),
            ("yes, please", {"text": ESCALATE}),
        ]:
            decision = route(
                {
                    "text": message,
                    "history": history,
                    "email": "evaluation@example.com",
                    "response": previous,
                }
            )["route"]
            rows.append(
                {"query": message, "route": decision, "passed": decision["intent"] == "ticket"}
            )
        report = {
            "model": model.settings.llm_model,
            "passed": sum(row["passed"] for row in rows),
            "total": len(rows),
            "cases": rows,
        }
        Path("/reports/return_routing_regressions.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, indent=2), flush=True)
        if not all(row["passed"] for row in rows):
            raise SystemExit("Routing regression failed")


if __name__ == "__main__":
    main()
