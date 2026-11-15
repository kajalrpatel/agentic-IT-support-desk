import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver

from smartdesk.application.chat_service import ChatService
from smartdesk.application.ticket_service import TicketService
from smartdesk.bootstrap import Services
from smartdesk.config import Settings
from smartdesk.domain.models import Identity, ServiceError, Ticket
from smartdesk.infrastructure.identity.auth import Auth
from smartdesk.infrastructure.llm.client import (
    ConversationSummary,
    Route,
)
from smartdesk.infrastructure.postgres.models import Base
from smartdesk.infrastructure.postgres.repository import Repository
from smartdesk.main import create_app
from smartdesk.rag.models import Claim, EvidenceVerdict, GroundedAnswer, Passage
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.workflows.graph import build_graph


class FakeModel:
    def __init__(self):
        self.last_query = ""
        self.invalid_citation = False
        self.unsupported = False

    def route(self, data):
        message = data["message"].lower()
        intent = "knowledge"
        if message in {"hi", "hello"}:
            intent = "greeting"
        if "create" in message or "prepare" in message:
            intent = "ticket"
        if "status" in message or "details for" in message:
            intent = "status"
        query = (
            "company VPN macOS support"
            if message == "does it work on mac?" and data["history"]
            else data["message"]
        )
        self.last_query = query
        return Route(
            intent=intent,
            standalone_query=query,
            reply="Hello! How can I help?",
            summary="Monitor flickering",
            description="My monitor has been flickering for two days.",
            category="IT",
            priority="Medium",
            ticket_id="IT-999" if "IT-999" in data["message"] else None,
        )

    def answer(self, data):
        return GroundedAnswer(
            answerable=True,
            claims=[
                Claim(
                    text="Company VPN supports managed macOS laptops.",
                    citation_ids=["invented" if self.invalid_citation else "vpn:0"],
                )
            ],
        )

    def verify(self, data):
        return EvidenceVerdict(supported=not self.unsupported, reason="Test verdict")

    def summarize(self, data):
        return ConversationSummary(summary="Earlier conversation concerned the company VPN.")


class FakeRetriever:
    def search(self, query, mode="reranked"):
        if "parking" in query.lower():
            return []
        if "outage" in query.lower():
            raise ServiceError("Knowledge search is unavailable.")
        return [
            Passage("vpn:0", "VPN", "Company VPN supports managed macOS laptops.", "synthetic:test")
        ]


class FakeTickets:
    def __init__(self):
        self.created = []
        self.lost_response = False
        self.outage = False

    def create(self, draft, correlation, employee_label):
        ticket = Ticket(
            f"IT-{len(self.created) + 1}", draft["summary"], "Open", "https://example.com/ticket"
        )
        self.created.append((ticket, correlation, employee_label))
        if self.lost_response:
            raise ServiceError("Jira response was lost.")
        return ticket

    def find(self, label):
        if self.outage:
            raise ServiceError("Jira is temporarily unreachable.")
        return [t for t, correlation, employee in self.created if label in {correlation, employee}]

    def get(self, ticket_id):
        return replace(
            next(t for t, _, _ in self.created if t.id == ticket_id),
            comments=["Replacement ordered."],
        )


@pytest.fixture
def system(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path}/app.db",
        session_secret="test-secret-that-is-more-than-32-characters",
    )
    repo = Repository(settings.database_url)
    Base.metadata.create_all(repo.engine)
    connection = sqlite3.connect(str(tmp_path / "checkpoints.db"), check_same_thread=False)
    saver = SqliteSaver(connection)
    model, retriever, provider = FakeModel(), FakeRetriever(), FakeTickets()
    ticket_service = TicketService(repo, provider)
    graph = build_graph(model, QueryPipeline(retriever, model), ticket_service, saver)
    chat = ChatService(repo, graph, rate_limit=100)
    identity = Identity("jane", "jane@example.com")
    conversation = repo.create_conversation(identity.user_id).id
    services = Services(repo, chat, Auth(settings), settings)
    with TestClient(create_app(services=services)) as client:
        yield SimpleNamespace(
            repo=repo,
            graph=graph,
            chat=chat,
            identity=identity,
            conversation=conversation,
            model=model,
            retriever=retriever,
            provider=provider,
            tickets=ticket_service,
            client=client,
            settings=settings,
            saver=saver,
        )
    connection.close()
    repo.engine.dispose()
