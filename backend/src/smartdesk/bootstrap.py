from contextlib import ExitStack
from dataclasses import dataclass

from langgraph.checkpoint.postgres import PostgresSaver

from smartdesk.application.chat_service import ChatService
from smartdesk.application.ticket_service import TicketService
from smartdesk.config import Settings
from smartdesk.infrastructure.identity.auth import Auth
from smartdesk.infrastructure.jira.client import JiraClient
from smartdesk.infrastructure.llm.client import LanguageModel
from smartdesk.infrastructure.postgres.repository import Repository
from smartdesk.rag.factory import build_rag
from smartdesk.rag.query_pipeline import QueryPipeline
from smartdesk.workflows.graph import build_graph


@dataclass
class Services:
    repo: Repository
    chat: ChatService
    auth: Auth
    settings: Settings


def bootstrap(settings: Settings, stack: ExitStack) -> Services:
    repo = Repository(settings.database_url)
    stack.callback(repo.engine.dispose)
    checkpointer = stack.enter_context(PostgresSaver.from_conn_string(settings.checkpoint_url))
    # Checkpointer migrations are run explicitly by `smartdesk migrate`.
    model = LanguageModel(settings)
    stack.callback(model.client.close)
    rag = build_rag(settings)
    stack.callback(rag.close)
    jira = JiraClient(settings)
    stack.callback(jira.client.close)
    graph = build_graph(
        model, QueryPipeline(rag.retrieval, model), TicketService(repo, jira), checkpointer
    )
    return Services(
        repo, ChatService(repo, graph, settings.max_messages_per_minute), Auth(settings), settings
    )
