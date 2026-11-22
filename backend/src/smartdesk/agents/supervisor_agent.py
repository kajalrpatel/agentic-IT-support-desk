from smartdesk.agents.ticket_intent import ticket_preparation_requested
from smartdesk.application.conversation_models import ChatResponse
from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.observability.trace_events import record_event
from smartdesk.workflows.conversation_state import ChatState


def build_supervisor_nodes(model: LanguageModel):
    def route_support_request(state: ChatState):
        summary = state.get("summary", "")
        summary_count = state.get("summary_count", 0)
        if state.get("older_history"):
            summary = model.summarize(
                {"previous_summary": summary, "older_turns": state["older_history"]}
            ).summary
            summary_count = state["history_count"] - len(state["history"])
        wants_ticket = ticket_preparation_requested(state["text"], state.get("response"))
        result = model.route(
            {
                "message": state["text"],
                "history": state.get("history", []),
                "summary": summary,
                "draft": state.get("draft"),
                "email": state["email"],
                "previous_response": state.get("response"),
                "ticket_preparation_requested": wants_ticket,
            }
        )
        if wants_ticket and result.intent in {"knowledge", "clarify"}:
            record_event("ticket_route_selected", reason="explicit_preparation_request")
            result = result.model_copy(update={"intent": "ticket"})
        if result.intent == "ticket" and not wants_ticket:
            record_event("ticket_route_blocked", reason="no_ticket_preparation_request")
            result = result.model_copy(
                update={
                    "intent": "knowledge",
                    "reply": "",
                    "standalone_query": result.standalone_query or state["text"],
                }
            )
        return {
            "route": result.model_dump(),
            "approved_version": None,
            "summary": summary,
            "summary_count": summary_count,
            "older_history": [],
        }

    def reply_to_nonknowledge_request(state: ChatState):
        fallback = (
            "Could you please tell me which issue or policy you mean?"
            if state["route"]["intent"] == "clarify"
            else "Hello! I can help with IT support and HR questions. How can I help you today?"
        )
        return {"response": ChatResponse(text=state["route"]["reply"] or fallback).model_dump()}

    return route_support_request, reply_to_nonknowledge_request
