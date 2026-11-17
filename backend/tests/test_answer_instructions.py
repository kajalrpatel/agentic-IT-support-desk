from unittest.mock import Mock

from smartdesk.infrastructure.llm.openai_client import LanguageModel
from smartdesk.rag.rag_models import GroundedAnswer


def test_specialist_instructions_are_system_context_not_user_data():
    model = LanguageModel.__new__(LanguageModel)
    model.parse = Mock()
    data = {
        "question": "Audio problems during an online meeting",
        "passages": [],
        "specialist_instructions": "Trusted IT instructions",
    }
    model.answer(data)
    prompt, payload, schema = model.parse.call_args.args
    assert "Trusted IT instructions" in prompt
    assert "specialist_instructions" not in payload
    assert payload["question"] == data["question"]
    assert data["specialist_instructions"] == "Trusted IT instructions"
    assert schema is GroundedAnswer
