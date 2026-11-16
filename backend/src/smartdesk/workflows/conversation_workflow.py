from typing import Any

from langgraph.graph import END, START, StateGraph

from smartdesk.agents.hr_policy_agent import build_hr_policy_agent
from smartdesk.agents.it_support_agent import build_it_support_agent
from smartdesk.agents.supervisor_agent import build_supervisor_nodes
from smartdesk.application.ticket_service import TicketService
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.tools.ticket_tools import build_ticket_nodes
from smartdesk.workflows.conversation_state import ChatState
from smartdesk.workflows.ticket_approval import build_approval_nodes


def build_graph(
    model: LanguageModel, answers: QueryPipeline, tickets: TicketService, checkpointer: Any
):
    route, reply = build_supervisor_nodes(model)
    draft, create, status = build_ticket_nodes(tickets)
    preview, approval, cancel, preserve_draft = build_approval_nodes()
    it_agent = build_it_support_agent(answers)
    hr_agent = build_hr_policy_agent(answers)
    graph = StateGraph(ChatState)
    graph.add_node("preserve_draft", preserve_draft)
    for name, node in [
        ("route", route),
        ("it_support", it_agent),
        ("hr_policy", hr_agent),
        ("reply", reply),
        ("draft", draft),
        ("preview", preview),
        ("approval", approval),
        ("create", create),
        ("cancel", cancel),
        ("status", status),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda s: {
            "knowledge": "hr_policy" if s["route"]["category"] == "HR" else "it_support",
            "ticket": "draft",
            "status": "status",
        }.get(s["route"]["intent"], "reply"),
    )
    graph.add_conditional_edges("draft", lambda s: "preview" if s.get("draft") else END)
    graph.add_edge("preview", "approval")
    graph.add_conditional_edges(
        "approval",
        lambda s: {"confirm": "create", "cancel": "cancel", "edit": "preview", "message": "route"}[
            s["approval_action"]
        ],
    )
    graph.add_conditional_edges(
        "create", lambda s: "approval" if s["approval_action"] == "retry" else END
    )
    for name in ("it_support", "hr_policy", "reply", "status"):
        graph.add_edge(name, "preserve_draft")
    graph.add_conditional_edges("preserve_draft", lambda s: "approval" if s.get("draft") else END)
    graph.add_edge("cancel", END)
    return graph.compile(checkpointer=checkpointer)
