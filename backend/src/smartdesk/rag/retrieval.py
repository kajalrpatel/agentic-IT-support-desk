import threading

from smartdesk.domain.models import ServiceError
from smartdesk.rag.interfaces import Embedder, KnowledgeStore, Reranker
from smartdesk.rag.models import Passage


class RetrievalPipeline:
    def __init__(
        self,
        embedder: Embedder,
        store: KnowledgeStore,
        reranker: Reranker,
        candidate_limit: int = 20,
        context_limit: int = 5,
        min_score: float | None = None,
    ):
        self.embedder = embedder
        self.store = store
        self.reranker = reranker
        self.candidate_limit = candidate_limit
        self.context_limit = context_limit
        self.min_score = min_score
        self._slots = threading.BoundedSemaphore(2)

    def search(self, query: str, mode: str = "reranked") -> list[Passage]:
        if mode not in {"dense", "sparse", "hybrid", "reranked"}:
            raise ValueError("Unknown retrieval mode")
        if not self._slots.acquire(timeout=10):
            raise ServiceError("Knowledge search is busy. Please retry shortly.")
        try:
            vectors = self.embedder.embed_query(query)
            passages = self.store.search(
                vectors, "hybrid" if mode == "reranked" else mode, self.candidate_limit, "employees"
            )
            if mode == "reranked" and passages:
                passages = self.reranker.rank(query, passages)
                if self.min_score is not None:
                    passages = [p for p in passages if p.score >= self.min_score]
            return passages[: self.context_limit]
        except Exception as exc:
            raise ServiceError(
                "Knowledge search is unavailable. Please retry shortly; this does not mean the policy is missing."
            ) from exc
        finally:
            self._slots.release()
