from langsmith import traceable

from smartdesk.rag.rag_interfaces import Retriever
from smartdesk.rag.rag_models import Passage


class KnowledgeSearchTool:
    """An agent's domain is fixed by composition, never by user-supplied tool arguments."""

    def __init__(self, retriever: Retriever, domain: str):
        if domain not in {"IT", "HR"}:
            raise ValueError("Unsupported knowledge domain")
        self.retriever = retriever
        self.domain = domain

    @traceable(name="search_domain_knowledge", run_type="tool")
    def search(self, query: str) -> list[Passage]:
        return self.retriever.search(query, domain=self.domain)
