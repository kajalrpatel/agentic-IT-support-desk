from uuid import uuid4

import pytest

from smartdesk.api.api_schemas import ApprovalInput, Draft, MessageInput
from smartdesk.application.chat_service import ChatService
from smartdesk.domain.support_models import Identity, ServiceError
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.workflows.conversation_workflow import build_graph


def send(system, text):
    return system.chat.process(
        system.conversation, system.identity, MessageInput(request_id=uuid4(), text=text)
    )


def approve(system, version, action="confirm", draft=None):
    return system.chat.process(
        system.conversation,
        system.identity,
        ApprovalInput(request_id=uuid4(), version=version, action=action, draft=draft),
    )


def test_grounded_answer_has_real_citation(system):
    reply = send(system, "How do I use the VPN?")
    assert reply.citations[0].id == "vpn:0"
    assert "[1]" in reply.text


def test_unknown_offers_ticket_without_creating(system):
    reply = send(system, "Where is parking?")
    assert "support ticket" in reply.text
    assert not system.provider.created


@pytest.mark.parametrize("attribute", ["invalid_citation", "unsupported"])
def test_invalid_evidence_abstains(system, attribute):
    setattr(system.model, attribute, True)
    reply = send(system, "How do I use the VPN?")
    assert not reply.citations
    assert "enough information" in reply.text


def test_followup_resolves_subject_from_history(system):
    send(system, "Tell me about the VPN")
    send(system, "Does it work on Mac?")
    assert system.model.last_query == "company VPN macOS support"


def test_long_conversation_has_summary_and_full_transcript(system):
    for _ in range(11):
        send(system, "Hello")
    state = system.chat.state(system.conversation).values
    assert state["summary"] and state["summary_count"] > 0
    assert len(state["history"]) <= 16
    assert len(system.repo.messages(system.conversation)) == 22


def test_draft_requires_confirmation(system):
    reply = send(system, "Create a ticket for my flickering monitor")
    assert reply.pending_approval and reply.draft.email == system.identity.email
    assert not system.provider.created
    result = approve(system, reply.draft_version)
    assert result.tickets[0].id == "IT-1"
    assert len(system.provider.created) == 1


def test_edit_invalidates_old_approval(system):
    reply = send(system, "Create a ticket")
    draft = reply.draft.model_copy(update={"summary": "Updated issue"})
    updated = approve(system, reply.draft_version, "edit", draft)
    assert updated.draft_version == reply.draft_version + 1
    with pytest.raises(ServiceError, match="matching approval"):
        approve(system, reply.draft_version)
    approve(system, updated.draft_version)
    assert system.provider.created[0][0].summary == "Updated issue"


def test_cancel_never_creates_ticket(system):
    reply = send(system, "Create a ticket")
    cancelled = approve(system, reply.draft_version, "cancel")
    assert "cancelled" in cancelled.text
    assert not system.provider.created


def test_conversational_confirmation(system):
    send(system, "Create a ticket")
    result = send(system, "Yes, please.")
    # Commas are normalized by the service, not an LLM approval decision.
    assert result.tickets


def test_restart_restores_pending_approval(system):
    reply = send(system, "Create a ticket")
    graph = build_graph(
        system.model, QueryPipeline(system.retriever, system.model), system.tickets, system.saver
    )
    chat = ChatService(system.repo, graph)
    result = chat.process(
        system.conversation,
        system.identity,
        ApprovalInput(request_id=uuid4(), version=reply.draft_version, action="confirm"),
    )
    assert result.tickets[0].id == "IT-1"


def test_retry_same_request_returns_original(system):
    reply = send(system, "Create a ticket")
    payload = ApprovalInput(request_id=uuid4(), version=reply.draft_version, action="confirm")
    first = system.chat.process(system.conversation, system.identity, payload)
    second = system.chat.process(system.conversation, system.identity, payload)
    assert first == second
    assert len(system.provider.created) == 1


def test_lost_create_response_reconciles_without_duplicate(system):
    system.provider.lost_response = True
    reply = send(system, "Create a ticket")
    uncertain = approve(system, reply.draft_version)
    assert uncertain.pending_approval
    result = approve(system, reply.draft_version)
    assert result.tickets[0].id == "IT-1"
    assert len(system.provider.created) == 1


def test_ticket_service_rejects_missing_approval(system):
    draft = Draft(
        email=system.identity.email, summary="A problem", description="My monitor is flickering"
    )
    with pytest.raises(ServiceError, match="confirm"):
        system.tickets.create(system.conversation, system.identity, draft, 1, None)


def test_zero_and_multiple_ticket_status(system):
    assert "No tickets" in send(system, "Ticket status").text
    for _ in range(2):
        draft = send(system, "Create a ticket")
        approve(system, draft.draft_version)
    assert len(send(system, "Ticket status").tickets) == 2


def test_single_ticket_returns_current_comments(system):
    draft = send(system, "Create a ticket")
    approve(system, draft.draft_version)
    reply = send(system, "Ticket status")
    assert reply.tickets[0].comments == ["Replacement ordered."]


def test_status_outage_is_not_no_tickets(system):
    system.provider.outage = True
    reply = send(system, "Ticket status")
    assert "unreachable" in reply.text and "No tickets" not in reply.text


def test_retrieval_outage_is_not_missing_policy(system):
    assert "unavailable" in send(system, "outage").text


def test_ownership_enforced(system):
    with pytest.raises(ServiceError, match="not found"):
        system.chat.process(
            system.conversation,
            Identity("other", "other@example.com"),
            MessageInput(request_id=uuid4(), text="Hello"),
        )
    with pytest.raises(ServiceError, match="not found"):
        system.tickets.detail(system.identity, "IT-999")


def test_edit_cannot_change_employee_identity(system):
    reply = send(system, "Create a ticket")
    with pytest.raises(ServiceError, match="identity"):
        approve(
            system,
            reply.draft_version,
            "edit",
            reply.draft.model_copy(update={"email": "other@example.com"}),
        )


def test_unrelated_question_does_not_approve_draft(system):
    send(system, "Create a ticket")
    send(system, "How do I use the VPN?")
    assert not system.provider.created
    result = send(system, "yes")
    assert result.tickets[0].id == "IT-1"


def test_api_auth_and_persistent_transcript(system):
    assert system.client.get("/api/v1/conversations").status_code in {401, 403}
    token = system.client.post("/api/v1/auth/demo").json()["token"]
    headers = {"Authorization": "Bearer " + token}
    conversation = system.client.post("/api/v1/conversations", headers=headers, json={}).json()
    response = system.client.post(
        f"/api/v1/conversations/{conversation['id']}/stream",
        headers=headers,
        json={"request_id": str(uuid4()), "text": "Hello"},
    )
    assert "event: progress" in response.text and "event: result" in response.text
    restored = system.client.get(
        f"/api/v1/conversations/{conversation['id']}", headers=headers
    ).json()
    assert len(restored["messages"]) == 2
    assert (
        system.client.get(
            f"/api/v1/conversations/{system.conversation}", headers=headers
        ).status_code
        == 404
    )
