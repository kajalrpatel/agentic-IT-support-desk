from typing import TypedDict


class ChatState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    email: str
    text: str
    history: list[dict]
    older_history: list[dict]
    history_count: int
    summary: str
    summary_count: int
    route: dict
    draft: dict | None
    draft_version: int
    approval_action: str
    approved_version: int | None
    response: dict
    request_id: str
