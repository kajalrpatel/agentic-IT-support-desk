from pydantic import BaseModel, Field

from smartdesk.application.conversation_models import (
    ApprovalInput,
    ChatResponse,
    Citation,
    Draft,
    MessageInput,
    TicketView,
)

__all__ = [
    "Draft",
    "MessageInput",
    "ApprovalInput",
    "ChatResponse",
    "TicketView",
    "Citation",
    "ConversationView",
    "MessageView",
]


class MessageView(BaseModel):
    id: int
    role: str
    content: str
    response: ChatResponse | None = None


class ConversationView(BaseModel):
    id: str
    title: str
    created_at: str
    messages: list[MessageView] = Field(default_factory=list)
    response: ChatResponse | None = None
