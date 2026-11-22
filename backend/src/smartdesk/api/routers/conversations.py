import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from smartdesk.api.api_schemas import (
    ApprovalInput,
    ChatResponse,
    ConversationView,
    MessageInput,
    MessageView,
)
from smartdesk.domain.support_models import Identity, ServiceError
from smartdesk.infrastructure.identity.authentication import current_identity

router = APIRouter()


@router.post("/api/v1/conversations", response_model=ConversationView)
def create(request: Request, identity: Identity = Depends(current_identity)):
    value = request.app.state.services.repo.create_conversation(identity.user_id)
    return ConversationView(id=value.id, title=value.title, created_at=value.created_at.isoformat())


@router.get("/api/v1/conversations", response_model=list[ConversationView])
def conversations(request: Request, identity: Identity = Depends(current_identity)):
    return [
        ConversationView(id=c.id, title=c.title, created_at=c.created_at.isoformat())
        for c in request.app.state.services.repo.conversations(identity.user_id)
    ]


@router.get("/api/v1/conversations/{conversation_id}", response_model=ConversationView)
def conversation(
    conversation_id: str, request: Request, identity: Identity = Depends(current_identity)
):
    svc = request.app.state.services
    item = svc.repo.owned(conversation_id, identity.user_id)
    messages = [
        MessageView(id=m.id, role=m.role, content=m.content, response=m.response)
        for m in svc.repo.messages(conversation_id)
    ]
    state = svc.chat.state(conversation_id)
    value = state.values.get("response")
    if value:
        value = {**value, "pending_approval": bool(state.interrupts)}
    return ConversationView(
        id=item.id,
        title=item.title,
        created_at=item.created_at.isoformat(),
        messages=messages,
        response=ChatResponse(**value) if value else None,
    )


@router.post("/api/v1/conversations/{conversation_id}/messages", response_model=ChatResponse)
def message(
    conversation_id: str,
    payload: MessageInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    return request.app.state.services.chat.process(conversation_id, identity, payload)


@router.post("/api/v1/conversations/{conversation_id}/approval", response_model=ChatResponse)
def approval(
    conversation_id: str,
    payload: ApprovalInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    return request.app.state.services.chat.process(conversation_id, identity, payload)


@router.post("/api/v1/conversations/{conversation_id}/stream")
async def stream(
    conversation_id: str,
    payload: MessageInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    svc = request.app.state.services
    await asyncio.to_thread(svc.repo.owned, conversation_id, identity.user_id)

    async def events():
        task = asyncio.create_task(
            asyncio.to_thread(svc.chat.process, conversation_id, identity, payload)
        )
        yield 'event: progress\ndata: {"text":"Checking your request and supporting sources…"}\n\n'
        try:
            while not task.done():
                done, _ = await asyncio.wait({task}, timeout=10)
                if not done:
                    yield ": keepalive\n\n"
            result = await task
            yield "event: result\ndata: " + result.model_dump_json() + "\n\n"
        except ServiceError as exc:
            yield "event: error\ndata: " + json.dumps({"detail": str(exc)}) + "\n\n"
        finally:
            # The synchronous work finishes and persists even if the client disconnects.
            if not task.done():
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
