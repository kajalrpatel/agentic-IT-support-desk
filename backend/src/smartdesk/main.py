import asyncio
import json
import time
from contextlib import ExitStack, asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from sqlalchemy import text

from smartdesk.api.schemas import (
    ApprovalInput,
    ChatResponse,
    ConversationView,
    MessageInput,
    MessageView,
)
from smartdesk.bootstrap import Services, bootstrap
from smartdesk.config import Settings, get_settings
from smartdesk.domain.models import Identity, ServiceError
from smartdesk.infrastructure.identity.auth import current_identity

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()]
)
log = structlog.get_logger()


def create_app(settings: Settings | None = None, services: Services | None = None):
    configuration = settings or (services.settings if services else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with ExitStack() as stack:
            app.state.services = services or bootstrap(configuration, stack)
            yield

    app = FastAPI(title="SmartDesk API", version="0.1.0", lifespan=lifespan)
    if services:
        app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuration.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health/live")

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        started = time.monotonic()
        request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        log.info(
            "request",
            request_id=request_id,
            method=request.method,
            status=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000),
        )
        return response

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready(request: Request):
        try:
            with request.app.state.services.repo.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.execute(text("SELECT 1 FROM conversations LIMIT 1"))
            return {
                "status": "ready",
                "llm_configured": bool(configuration.openai_api_key.get_secret_value()),
                "jira_configured": bool(
                    configuration.jira_base_url and configuration.jira_api_token.get_secret_value()
                ),
            }
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    @app.get("/api/v1/auth/config")
    def auth_config():
        return {"mode": configuration.auth_mode}

    @app.post("/api/v1/auth/demo")
    def demo(request: Request):
        return {
            "token": request.app.state.services.auth.demo_token(),
            "email": configuration.demo_email,
        }

    @app.get("/api/v1/me")
    def me(identity: Identity = Depends(current_identity)):
        return {"email": identity.email}

    @app.post("/api/v1/conversations", response_model=ConversationView)
    def create(request: Request, identity: Identity = Depends(current_identity)):
        value = request.app.state.services.repo.create_conversation(identity.user_id)
        return ConversationView(
            id=value.id, title=value.title, created_at=value.created_at.isoformat()
        )

    @app.get("/api/v1/conversations", response_model=list[ConversationView])
    def conversations(request: Request, identity: Identity = Depends(current_identity)):
        return [
            ConversationView(id=c.id, title=c.title, created_at=c.created_at.isoformat())
            for c in request.app.state.services.repo.conversations(identity.user_id)
        ]

    @app.get("/api/v1/conversations/{conversation_id}", response_model=ConversationView)
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

    @app.post("/api/v1/conversations/{conversation_id}/messages", response_model=ChatResponse)
    def message(
        conversation_id: str,
        payload: MessageInput,
        request: Request,
        identity: Identity = Depends(current_identity),
    ):
        return request.app.state.services.chat.process(conversation_id, identity, payload)

    @app.post("/api/v1/conversations/{conversation_id}/approval", response_model=ChatResponse)
    def approval(
        conversation_id: str,
        payload: ApprovalInput,
        request: Request,
        identity: Identity = Depends(current_identity),
    ):
        return request.app.state.services.chat.process(conversation_id, identity, payload)

    @app.post("/api/v1/conversations/{conversation_id}/stream")
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

    return app
