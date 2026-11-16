from dataclasses import asdict

from smartdesk.api.api_schemas import ChatResponse, Draft, TicketView
from smartdesk.application.ticket_service import TicketService
from smartdesk.domain.support_models import Identity, ServiceError
from smartdesk.workflows.conversation_state import ChatState


def build_ticket_nodes(tickets: TicketService):
    def prepare_ticket_draft(state: ChatState):
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

    def create_confirmed_ticket(state: ChatState):
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

    def lookup_ticket_status(state: ChatState):
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

    return prepare_ticket_draft, create_confirmed_ticket, lookup_ticket_status
