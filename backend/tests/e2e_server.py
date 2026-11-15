"""Real API and workflow with deterministic external providers for browser tests."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from smartdesk.application.chat_service import ChatService
from smartdesk.application.ticket_service import TicketService
from smartdesk.bootstrap import Services
from smartdesk.config import Settings
from smartdesk.infrastructure.identity.authentication import Auth
from smartdesk.infrastructure.postgres.conversation_repository import Repository
from smartdesk.infrastructure.postgres.database_models import Base
from smartdesk.main import create_app
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.workflows.conversation_workflow import build_graph
from tests.conftest import FakeModel, FakeRetriever, FakeTickets

root = Path(".cache") / ("browser-" + str(uuid4()))
root.mkdir(parents=True)
settings = Settings(
    environment="test",
    database_url=f"sqlite:///{root}/app.db",
    session_secret="browser-test-secret-more-than-thirty-two-characters",
    max_messages_per_minute=1000,
)
repo = Repository(settings.database_url)
Base.metadata.create_all(repo.engine)
saver = SqliteSaver(sqlite3.connect(str(root / "checkpoints.db"), check_same_thread=False))
model, retriever, provider = FakeModel(), FakeRetriever(), FakeTickets()
graph = build_graph(model, QueryPipeline(retriever, model), TicketService(repo, provider), saver)
app = create_app(services=Services(repo, ChatService(repo, graph, 1000), Auth(settings), settings))
