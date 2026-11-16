"""Evaluate supervisor and specialists without granting Jira write capabilities."""

from smartdesk.agents.hr_policy_agent import build_hr_policy_agent
from smartdesk.agents.it_support_agent import build_it_support_agent
from smartdesk.agents.supervisor_agent import build_supervisor_nodes
from smartdesk.rag.query_pipeline import ESCALATE


def run_agent_case(model, pipeline, case):
    route, _ = build_supervisor_nodes(model)
    decision = route({"text": case["query"], "email": "evaluation@example.com"})["route"]
    result = {"response": {"text": decision["reply"] or ESCALATE, "citations": []}}
    if decision["intent"] == "knowledge":
        agent = (build_hr_policy_agent if decision["category"] == "HR" else build_it_support_agent)(
            pipeline
        )
        result = agent.invoke({"route": decision})
    return {
        "id": case["id"],
        "query": case["query"],
        "expected_answerable": case["answerable"],
        "expected_domain": ("HR" if case["expected_documents"][0].startswith("hr-") else "IT")
        if case["expected_documents"]
        else None,
        "route": decision,
        "response": result["response"],
        "retrieved_contexts": [p.text for p in result.get("passages", [])],
    }
