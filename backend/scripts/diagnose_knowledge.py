"""Inspect a synthetic query's routing, retrieval and grounding (paid model calls)."""

import argparse
import json
from contextlib import ExitStack

from smartdesk.config import Settings
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.rag_factory import build_rag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="Audio problems during an online meeting")
    args = parser.parse_args()
    query = args.query
    with ExitStack() as stack:
        model = LanguageModel(Settings())
        stack.callback(model.client.close)
        rag = build_rag(model.settings)
        stack.callback(rag.close)
        route = model.route(
            {
                "message": query,
                "history": [],
                "summary": "",
                "draft": None,
                "email": "evaluation@example.com",
            }
        )
        print("ROUTE", route.model_dump_json(), flush=True)
        passages = rag.retrieval.search(route.standalone_query, domain=route.category)
        print(
            "RETRIEVED", json.dumps([{"id": p.id, "score": p.score} for p in passages]), flush=True
        )
        from smartdesk.agents.hr_policy_agent import build_hr_policy_agent
        from smartdesk.agents.it_support_agent import build_it_support_agent
        from smartdesk.rag.query_pipeline import QueryPipeline

        graph = (build_it_support_agent if route.category == "IT" else build_hr_policy_agent)(
            QueryPipeline(rag.retrieval, model)
        )
        for update in graph.stream({"route": route.model_dump()}, stream_mode="updates"):
            if "search_domain_knowledge" in update:
                continue
            print(
                "STEP",
                json.dumps(
                    update,
                    default=lambda value: (
                        value.model_dump() if hasattr(value, "model_dump") else vars(value)
                    ),
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
