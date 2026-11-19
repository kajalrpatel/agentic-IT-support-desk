import json
import time
from pathlib import Path
from typing import Literal, TypeVar

import structlog
from langsmith.wrappers import wrap_openai
from openai import APIError, OpenAI, omit
from pydantic import BaseModel

from smartdesk.config import Settings
from smartdesk.domain.support_models import ServiceError
from smartdesk.observability.langsmith_tracing import configure_langsmith
from smartdesk.rag.rag_models import EvidenceVerdict, GroundedAnswer

T = TypeVar("T", bound=BaseModel)

SERVICE_UNAVAILABLE = "Sorry, I can't respond right now. Please try again later."


class Route(BaseModel):
    intent: Literal["knowledge", "ticket", "status", "greeting", "clarify", "out_of_scope"]
    standalone_query: str
    reply: str
    summary: str | None
    description: str | None
    category: Literal["IT", "HR"]
    priority: Literal["Low", "Medium", "High", "Critical"]
    ticket_id: str | None


class ConversationSummary(BaseModel):
    summary: str


class LanguageModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        configure_langsmith(settings)
        self.client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value() or "not-configured",
            timeout=settings.request_timeout_seconds,
            max_retries=2,
        )
        if settings.langsmith_tracing:
            self.client = wrap_openai(self.client)

    def parse(self, prompt: str, data: dict, schema: type[T]) -> T:
        if not self.settings.openai_api_key.get_secret_value():
            raise ServiceError(SERVICE_UNAVAILABLE)
        try:
            started = time.monotonic()
            result = self.client.responses.parse(
                model=self.settings.llm_model,
                reasoning=(
                    {"effort": self.settings.reasoning_effort}
                    if self.settings.reasoning_effort is not None
                    else omit
                ),
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(data)},
                ],
                text_format=schema,
                max_output_tokens=self.settings.max_output_tokens,
                store=False,
            )
            if result.output_parsed is None:
                raise ServiceError(SERVICE_UNAVAILABLE)
            structlog.get_logger().info(
                "model_call",
                schema=schema.__name__,
                model=self.settings.llm_model,
                duration_ms=round((time.monotonic() - started) * 1000),
                input_tokens=result.usage.input_tokens if result.usage else None,
                output_tokens=result.usage.output_tokens if result.usage else None,
            )
            return result.output_parsed
        except APIError as exc:
            code = getattr(exc, "code", None)
            status = getattr(exc, "status_code", None)
            if code == "project_spend_limit_exceeded":
                category = "project_spend_limit"
            elif code in {"insufficient_quota", "billing_hard_limit_reached"}:
                category = "quota_exhausted"
            elif status == 429:
                category = "rate_limited"
            elif status in {401, 403} or code == "model_not_found":
                category = "access_denied"
            else:
                category = "provider_unavailable"
            # Do not log the provider body: authentication errors can include key fragments.
            structlog.get_logger().warning(
                "model_call_failed", category=category, status=status, model=self.settings.llm_model
            )
            raise ServiceError(SERVICE_UNAVAILABLE) from exc

    def route(self, data: dict) -> Route:
        return self.parse(self.prompt("router") + "\n" + self.prompt("response_style"), data, Route)

    def answer(self, data: dict) -> GroundedAnswer:
        # Specialist instructions are supplied by server-side agent composition.
        # Keep them separate from untrusted questions and retrieved passages.
        instructions = data.get("specialist_instructions", "")
        payload = {key: value for key, value in data.items() if key != "specialist_instructions"}
        return self.parse(
            self.prompt("answer") + "\n" + instructions + "\n" + self.prompt("response_style"),
            payload,
            GroundedAnswer,
        )

    def verify(self, data: dict) -> EvidenceVerdict:
        return self.parse(self.prompt("verify"), data, EvidenceVerdict)

    def summarize(self, data: dict) -> ConversationSummary:
        return self.parse(self.prompt("summary"), data, ConversationSummary)

    @staticmethod
    def prompt(name: str) -> str:
        root = Path(__file__).parents[2]
        paths = {
            "router": root / "conversation_prompts" / "intent_routing.txt",
            "summary": root / "conversation_prompts" / "conversation_summary.txt",
            "response_style": root / "conversation_prompts" / "response_style.txt",
            "answer": root / "rag" / "answer_prompts" / "answer_generation.txt",
            "verify": root / "rag" / "answer_prompts" / "evidence_verification.txt",
        }
        return paths[name].read_text(encoding="utf-8")
