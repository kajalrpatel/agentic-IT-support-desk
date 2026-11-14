"""Real API and workflow with deterministic external providers for browser tests."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from smartdesk.application.answer_service import AnswerService
from smartdesk.application.chat_service import ChatService
from smartdesk.application.ticket_service import TicketService
from smartdesk.bootstrap import Services
from smartdesk.config import Settings
from smartdesk.infrastructure.identity.auth import Auth
from smartdesk.infrastructure.postgres.models import Base
from smartdesk.infrastructure.postgres.repository import Repository
from smartdesk.main import create_app
from smartdesk.workflows.graph import build_graph
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
graph = build_graph(model, AnswerService(retriever, model), TicketService(repo, provider), saver)
app = create_app(services=Services(repo, ChatService(repo, graph, 1000), Auth(settings), settings))
