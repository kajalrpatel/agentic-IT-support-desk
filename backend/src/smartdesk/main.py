import time
from contextlib import ExitStack, asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from smartdesk.api.routers import auth, conversations, health
from smartdesk.bootstrap import Services, bootstrap
from smartdesk.config import Settings, get_settings
from smartdesk.domain.support_models import ServiceError

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
    app.state.settings = configuration
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

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(conversations.router)
    return app
