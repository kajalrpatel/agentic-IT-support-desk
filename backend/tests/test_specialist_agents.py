from uuid import uuid4

import pytest

from smartdesk.api.api_schemas import MessageInput


@pytest.mark.parametrize("domain", ["IT", "HR"])
def test_supervisor_hands_off_to_scoped_specialist(system, domain):
    original = system.model.route
    system.model.route = lambda data: original(data).model_copy(update={"category": domain})
    instructions = []
    employee_messages = []
    answer = system.model.answer

    def capture(data):
        instructions.append(data["specialist_instructions"])
        employee_messages.append(data["employee_message"])
        return answer(data)

    system.model.answer = capture
    response = system.chat.process(
        system.conversation,
        system.identity,
        MessageInput(request_id=uuid4(), text="Explain the policy"),
    )
    assert response.citations
    assert system.retriever.last_domain == domain
    assert domain in instructions[0]
    assert employee_messages == ["Explain the policy"]
    assert not system.provider.created


def test_empty_domain_evidence_skips_generation(system):
    def forbidden(data):
        raise AssertionError("No model generation without evidence")

    system.model.answer = forbidden
    response = system.chat.process(
        system.conversation,
        system.identity,
        MessageInput(request_id=uuid4(), text="Where is parking?"),
    )
    assert not response.citations
    assert "support ticket" in response.text
