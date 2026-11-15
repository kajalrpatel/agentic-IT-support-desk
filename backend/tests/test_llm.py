from unittest.mock import Mock

import httpx
import pytest
from openai import APIStatusError

from smartdesk.config import Settings
from smartdesk.domain.models import ServiceError
from smartdesk.infrastructure.llm.client import ConversationSummary, LanguageModel


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (429, "project_spend_limit_exceeded", "project_spend_limit"),
        (429, "insufficient_quota", "quota_exhausted"),
        (429, "rate_limit_exceeded", "rate_limited"),
        (401, "invalid_api_key", "access_denied"),
        (403, "model_not_found", "access_denied"),
        (404, "model_not_found", "access_denied"),
        (503, "server_error", "provider_unavailable"),
    ],
)
def test_provider_details_stay_in_logs_and_users_get_friendly_message(
    status, code, expected, capsys
):
    model = LanguageModel(
        Settings(
            _env_file=None,
            session_secret="test-secret-that-is-more-than-32-characters",
            openai_api_key="test-only-not-a-real-key",
        )
    )
    model.client.close()
    error = APIStatusError(
        "Sensitive provider body: private-key-fragment",
        response=httpx.Response(
            status, request=httpx.Request("POST", "https://api.openai.com/v1/responses")
        ),
        body={"code": code},
    )
    model.client = Mock()
    model.client.responses.parse.side_effect = error
    with pytest.raises(ServiceError) as caught:
        model.parse("Summarize.", {"text": "Hello"}, ConversationSummary)
    assert str(caught.value) == "Sorry, I can't respond right now. Please try again later."
    output = capsys.readouterr().out
    assert expected in output
    assert "private-key-fragment" not in output
