from dataclasses import dataclass

from qdrant_client import QdrantClient

from smartdesk.config import Settings
from smartdesk.rag.embedding import FastEmbedEmbedding
from smartdesk.rag.ingestion import IngestionPipeline
from smartdesk.rag.qdrant_store import QdrantStore
from smartdesk.rag.reranking import FastEmbedReranker
from smartdesk.rag.retrieval import RetrievalPipeline


@dataclass
class RagComponents:
    store: QdrantStore
    ingestion: IngestionPipeline
    retrieval: RetrievalPipeline

    def close(self) -> None:
        self.store.close()


def build_rag(settings: Settings, client: QdrantClient | None = None) -> RagComponents:
    """Composition helper; importing or constructing it does not load model weights."""
    store = QdrantStore(
        client
        if client is not None
        else QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key.get_secret_value() or None,
            timeout=20,
        ),
        settings.qdrant_collection,
    )
    embedder = FastEmbedEmbedding(
        settings.embedding_model, settings.sparse_model, settings.model_cache_dir
    )
    reranker = FastEmbedReranker(settings.reranker_model, settings.model_cache_dir)
    return RagComponents(
        store,
        IngestionPipeline(embedder, store),
        RetrievalPipeline(
            embedder,
            store,
            reranker,
            settings.candidate_limit,
            settings.context_limit,
            settings.reranker_min_score,
        ),
    )
