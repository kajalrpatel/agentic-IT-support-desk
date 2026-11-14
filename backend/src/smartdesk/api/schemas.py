from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Draft(BaseModel):
    email: EmailStr
    summary: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    category: Literal["IT", "HR"] = "IT"
    priority: Literal["Low", "Medium", "High", "Critical"] = "Medium"


class MessageInput(BaseModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=4000)


class ApprovalInput(BaseModel):
    request_id: UUID
    version: int = Field(ge=1)
    action: Literal["confirm", "cancel", "edit"]
    draft: Draft | None = None


class Citation(BaseModel):
    id: str
    title: str
    excerpt: str
    source: str


class TicketView(BaseModel):
    id: str
    summary: str
    status: str
    url: str
    comments: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)
    draft: Draft | None = None
    draft_version: int | None = None
    tickets: list[TicketView] = Field(default_factory=list)
    pending_approval: bool = False


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
