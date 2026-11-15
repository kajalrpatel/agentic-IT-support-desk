import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from langgraph.types import Command
from sqlalchemy import func, select

from smartdesk.api.api_schemas import ApprovalInput, ChatResponse, MessageInput
from smartdesk.domain.support_models import Identity, ServiceError
from smartdesk.infrastructure.postgres.conversation_repository import Repository
from smartdesk.infrastructure.postgres.database_models import Conversation, Message, Request


class ChatService:
    def __init__(self, repo: Repository, graph, rate_limit: int = 20):
        self.repo = repo
        self.graph = graph
        self.rate_limit = rate_limit

    def state(self, conversation: str):
        return self.graph.get_state({"configurable": {"thread_id": conversation}})

    def process(
        self, conversation: str, identity: Identity, payload: MessageInput | ApprovalInput
    ) -> ChatResponse:
        self.repo.owned(conversation, identity.user_id)
        request_id = str(payload.request_id)
        fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
        config = {"configurable": {"thread_id": conversation}, "recursion_limit": 20}
        invocation: Command[Any] | dict[str, Any]
        with self.repo.lock(conversation):
            with self.repo.sessions.begin() as session:
                previous = session.get(Request, request_id)
                if previous:
                    if (
                        previous.conversation_id != conversation
                        or previous.fingerprint != fingerprint
                    ):
                        raise ServiceError(
                            "Request ID has already been used for a different operation.", 409
                        )
                    if previous.response:
                        return ChatResponse(**previous.response)
                    raise ServiceError(
                        "This request was interrupted or is still being reconciled. Reload the conversation before sending a new request.",
                        409,
                    )
                count = session.scalar(
                    select(func.count())
                    .select_from(Request)
                    .join(Conversation)
                    .where(
                        Conversation.owner == identity.user_id,
                        Request.created_at > datetime.now(UTC) - timedelta(minutes=1),
                    )
                )
                if count and count >= self.rate_limit:
                    raise ServiceError("Too many messages. Please wait a minute.", 429)
                state = self.state(conversation)
                pending = bool(state.interrupts)
                values = state.values
                if isinstance(payload, ApprovalInput):
                    if not pending or payload.version != values.get("draft_version"):
                        raise ServiceError(
                            "No matching approval is pending. Reload the conversation.", 409
                        )
                    if payload.action == "edit" and payload.draft is None:
                        raise ServiceError("An edited draft is required.", 422)
                    if payload.draft and str(payload.draft.email).lower() != identity.email.lower():
                        raise ServiceError("The ticket email must match your identity.", 403)
                    text = {
                        "confirm": "Confirm ticket submission",
                        "edit": "Update ticket draft",
                        "cancel": "Cancel ticket creation",
                    }[payload.action]
                    invocation = Command(resume=payload.model_dump(mode="json"))
                else:
                    text = payload.text.strip()
                    if not text:
                        raise ServiceError("Please enter a message.", 422)
                    messages = self.repo.messages(conversation)
                    history = [{"role": m.role, "content": m.content} for m in messages[-16:]]
                    older = [
                        {"role": m.role, "content": m.content[:4000]}
                        for m in messages[
                            values.get("summary_count", 0) : max(0, len(messages) - 16)
                        ]
                    ]
                    if pending:
                        normalized = text.lower().replace(",", "").strip(".! ")
                        action = (
                            "confirm"
                            if normalized in {"yes", "yes please", "confirm", "go ahead", "submit"}
                            else "cancel"
                            if normalized in {"cancel", "no", "no thanks"}
                            else "message"
                        )
                        invocation = Command(
                            resume={
                                "action": action,
                                "version": values.get("draft_version"),
                                "text": text,
                                "history": history,
                                "older_history": older,
                                "history_count": len(messages),
                                "request_id": request_id,
                            }
                        )
                    else:
                        invocation = {
                            "conversation_id": conversation,
                            "user_id": identity.user_id,
                            "email": identity.email,
                            "text": text,
                            "history": history,
                            "older_history": older,
                            "history_count": len(messages),
                            "request_id": request_id,
                        }
                session.add(
                    Request(id=request_id, conversation_id=conversation, fingerprint=fingerprint)
                )
                session.add(
                    Message(
                        conversation_id=conversation,
                        role="user",
                        content=text,
                        request_id=request_id,
                    )
                )
                item = session.get(Conversation, conversation)
                if item and item.title == "New conversation":
                    item.title = text[:80]
            try:
                result = self.graph.invoke(invocation, config=config)
                response = ChatResponse(**result["response"])
            except ServiceError as exc:
                response = ChatResponse(text=str(exc))
            except Exception as exc:
                # Do not return provider payloads, credentials, or internal tracebacks.
                structlog.get_logger().error(
                    "chat_failed", request_id=request_id, exception_type=type(exc).__name__
                )
                response = ChatResponse(
                    text="Something went wrong while processing your message. Your conversation is saved; please retry."
                )
            with self.repo.sessions.begin() as session:
                record = session.get(Request, request_id)
                assert record is not None
                record.status = "complete"
                record.response = response.model_dump(mode="json")
                session.add(
                    Message(
                        conversation_id=conversation,
                        role="assistant",
                        content=response.text,
                        request_id=request_id,
                        response=response.model_dump(mode="json"),
                    )
                )
            return response
