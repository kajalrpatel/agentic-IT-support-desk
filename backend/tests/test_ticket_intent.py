import pytest

from smartdesk.agents.ticket_intent import ticket_preparation_requested
from smartdesk.rag.query_pipeline import ESCALATE


@pytest.mark.parametrize(
    "message",
    [
        "i want to return my laptop",
        "yes, want to return mylaptop",
        "simplt return to company",
        "simply for returning it to the company",
        "How do I open a ticket?",
        "Don't create a ticket",
        "I do not want a ticket",
    ],
)
def test_procedures_and_clarification_replies_do_not_request_tickets(message):
    assert not ticket_preparation_requested(
        message, {"text": "Do you mean returning it to the company?"}
    )


@pytest.mark.parametrize(
    "message",
    [
        "Create a ticket",
        "Please open a support request for my laptop",
        "Can you raise an incident?",
        "I would like a ticket",
    ],
)
def test_explicit_ticket_request(message):
    assert ticket_preparation_requested(message, None)


def test_yes_only_accepts_an_actual_escalation_offer():
    assert ticket_preparation_requested("yes please", {"text": ESCALATE})
    assert not ticket_preparation_requested("yes please", {"text": "Is it a company laptop?"})


def test_acceptance_survives_escalation_copy_change():
    previous = "I don't have enough information in the knowledge base to answer that reliably. Would you like me to prepare a support ticket?"
    assert ticket_preparation_requested("yes please", {"text": previous})


def test_supervisor_blocks_model_ticket_route_without_request(system):
    from smartdesk.agents.supervisor_agent import build_supervisor_nodes

    original = system.model.route
    system.model.route = lambda data: original(data).model_copy(update={"intent": "ticket"})
    route, _ = build_supervisor_nodes(system.model)
    decision = route({"text": "simply return to company", "email": system.identity.email})
    assert decision["route"]["intent"] == "knowledge"


def test_explicit_ticket_request_takes_precedence_over_guidance(system):
    from smartdesk.agents.supervisor_agent import build_supervisor_nodes

    original = system.model.route
    system.model.route = lambda data: original(data).model_copy(update={"intent": "knowledge"})
    route, _ = build_supervisor_nodes(system.model)
    decision = route(
        {"text": "Please create a ticket for my laptop return", "email": system.identity.email}
    )
    assert decision["route"]["intent"] == "ticket"


@pytest.mark.parametrize(
    "acceptance", ["yes, please", "Sure, jane.doe@company.com.", "Yes, please do that."]
)
def test_accepting_escalation_reaches_ticket_preparation(system, acceptance):
    from smartdesk.agents.supervisor_agent import build_supervisor_nodes

    route, _ = build_supervisor_nodes(system.model)
    decision = route(
        {"text": acceptance, "email": system.identity.email, "response": {"text": ESCALATE}}
    )
    assert decision["route"]["intent"] == "ticket"


@pytest.mark.parametrize(
    "reply",
    ["Yes, but don't create a ticket", "Sure, first explain my options", "jane@example.com"],
)
def test_offer_with_qualification_or_only_email_is_not_consent(reply):
    assert not ticket_preparation_requested(reply, {"text": ESCALATE})
