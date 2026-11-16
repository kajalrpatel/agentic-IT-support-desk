"""Explicit opt-in tracing; suppress employee chat payloads by default."""

import os

from smartdesk.config import Settings


def configure_langsmith(settings: Settings) -> None:
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
    if not settings.langsmith_tracing:
        return
    if not settings.langsmith_api_key.get_secret_value():
        raise ValueError("LANGSMITH_API_KEY is required when tracing is enabled")
    os.environ.update(
        {
            "LANGSMITH_API_KEY": settings.langsmith_api_key.get_secret_value(),
            "LANGSMITH_PROJECT": settings.langsmith_project,
            "LANGSMITH_ENDPOINT": settings.langsmith_endpoint,
            "LANGSMITH_HIDE_INPUTS": str(settings.langsmith_hide_inputs).lower(),
            "LANGSMITH_HIDE_OUTPUTS": str(settings.langsmith_hide_outputs).lower(),
        }
    )
