from dataclasses import asdict
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from smartdesk.api.api_schemas import ChatResponse, Draft, TicketView
from smartdesk.application.ticket_service import TicketService
from smartdesk.domain.support_models import Identity, ServiceError
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.query_pipeline import QueryPipeline


class ChatState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    email: str
    text: str
    history: list[dict]
    older_history: list[dict]
    history_count: int
    summary: str
    summary_count: int
    route: dict
    draft: dict | None
    draft_version: int
    approval_action: str
    approved_version: int | None
    response: dict
    request_id: str


def build_graph(
    model: LanguageModel, answers: QueryPipeline, tickets: TicketService, checkpointer: Any
):
    def route(state: ChatState):
        summary = state.get("summary", "")
        summary_count = state.get("summary_count", 0)
        if state.get("older_history"):
            summary = model.summarize(
                {"previous_summary": summary, "older_turns": state["older_history"]}
            ).summary
            summary_count = state["history_count"] - len(state["history"])
        result = model.route(
            {
                "message": state["text"],
                "history": state.get("history", []),
                "summary": summary,
                "draft": state.get("draft"),
                "email": state["email"],
                "previous_response": state.get("response"),
            }
        )
        return {
            "route": result.model_dump(),
            "approved_version": None,
            "summary": summary,
            "summary_count": summary_count,
            "older_history": [],
        }

    def knowledge(state: ChatState):
        result = answers.answer(state["route"]["standalone_query"])
        return {"response": ChatResponse(**result.model_dump()).model_dump()}

    def reply(state: ChatState):
        fallback = (
            "Which issue or policy are you referring to?"
            if state["route"]["intent"] == "clarify"
            else "I can help with employee IT and HR questions. What do you need help with?"
        )
        return {"response": ChatResponse(text=state["route"]["reply"] or fallback).model_dump()}

    def draft(state: ChatState):
        details = state["route"]
        if (
            not details.get("summary")
            or not details.get("description")
            or len(details["description"]) < 10
        ):
            return {
                "draft": None,
                "response": ChatResponse(
                    text="Please describe the issue and what you have tried so I can prepare your ticket."
                ).model_dump(),
            }
        value = Draft(
            email=state["email"],
            summary=details["summary"][:200],
            description=details["description"][:5000],
            category=details["category"],
            priority=details["priority"],
        )
        version = state.get("draft_version", 0) + 1
        return {
            "draft": value.model_dump(mode="json"),
            "draft_version": version,
            "approved_version": None,
        }

    def preview(state: ChatState):
        assert state.get("draft") is not None
        value = Draft.model_validate(state["draft"])
        return {
            "response": ChatResponse(
                text="Please review this ticket. You can edit it, confirm submission, or cancel.",
                draft=value,
                draft_version=state["draft_version"],
                pending_approval=True,
            ).model_dump()
        }

    def approval(state: ChatState):
        decision = interrupt({"draft": state["draft"], "version": state["draft_version"]})
        action = decision["action"]
        if action == "message":
            return {
                "approval_action": "message",
                "text": decision["text"],
                "history": decision["history"],
                "older_history": decision.get("older_history", []),
                "history_count": decision.get("history_count", 0),
                "request_id": decision["request_id"],
                "approved_version": None,
            }
        if decision.get("version") != state["draft_version"]:
            raise ServiceError("This preview is out of date. Reload the current draft.", 409)
        if action == "edit":
            value = Draft(**decision["draft"])
            if str(value.email).lower() != state["email"].lower():
                raise ServiceError("The ticket email must match your identity.", 403)
            return {
                "draft": value.model_dump(mode="json"),
                "draft_version": state["draft_version"] + 1,
                "approval_action": "edit",
                "approved_version": None,
            }
        return {
            "approval_action": action,
            "approved_version": state["draft_version"] if action == "confirm" else None,
        }

    def create(state: ChatState):
        try:
            ticket = tickets.create(
                state["conversation_id"],
                Identity(state["user_id"], state["email"]),
                Draft.model_validate(state["draft"]),
                state["draft_version"],
                state.get("approved_version"),
            )
        except ServiceError as exc:
            return {
                "response": ChatResponse(
                    text=str(exc),
                    draft=Draft.model_validate(state["draft"]),
                    draft_version=state["draft_version"],
                    pending_approval=True,
                ).model_dump(),
                "approval_action": "retry",
                "approved_version": None,
            }
        return {
            "response": ChatResponse(
                text=f"Ticket {ticket.id} has been created. You can track it using the link below.",
                tickets=[TicketView.model_validate(asdict(ticket))],
            ).model_dump(),
            "draft": None,
            "approval_action": "done",
            "approved_version": None,
        }

    def cancel(state: ChatState):
        return {
            "draft": None,
            "approved_version": None,
            "response": ChatResponse(text="Ticket creation cancelled.").model_dump(),
        }

    def status(state: ChatState):
        identity = Identity(state["user_id"], state["email"])
        ticket_id = state["route"].get("ticket_id")
        if ticket_id:
            found = [tickets.detail(identity, ticket_id.upper())]
        else:
            found = tickets.list(identity)
            if len(found) == 1:
                found = [tickets.detail(identity, found[0].id)]
        text = (
            "No tickets were found for your account."
            if not found
            else "Here are your tickets. Choose one for details."
            if len(found) > 1
            else f"{found[0].id} is {found[0].status}."
        )
        return {
            "response": ChatResponse(
                text=text, tickets=[TicketView.model_validate(asdict(t)) for t in found]
            ).model_dump()
        }

    def preserve_draft(state: ChatState):
        if state.get("draft"):
            return {
                "response": {
                    **state["response"],
                    "draft": state["draft"],
                    "draft_version": state["draft_version"],
                    "pending_approval": True,
                }
            }
        return {}

    graph = StateGraph(ChatState)
    graph.add_node("preserve_draft", preserve_draft)
    for name, node in [
        ("route", route),
        ("knowledge", knowledge),
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
        lambda s: {"knowledge": "knowledge", "ticket": "draft", "status": "status"}.get(
            s["route"]["intent"], "reply"
        ),
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
    for name in ("knowledge", "reply", "status"):
        graph.add_edge(name, "preserve_draft")
    graph.add_conditional_edges("preserve_draft", lambda s: "approval" if s.get("draft") else END)
    graph.add_edge("cancel", END)
    return graph.compile(checkpointer=checkpointer)
