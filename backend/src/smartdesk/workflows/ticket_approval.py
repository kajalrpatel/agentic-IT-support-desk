from langgraph.types import interrupt

from smartdesk.api.api_schemas import ChatResponse, Draft
from smartdesk.domain.support_models import ServiceError
from smartdesk.workflows.conversation_state import ChatState


def build_approval_nodes():
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

    def cancel(state: ChatState):
        return {
            "draft": None,
            "approved_version": None,
            "response": ChatResponse(text="Ticket creation cancelled.").model_dump(),
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

    return preview, approval, cancel, preserve_draft
