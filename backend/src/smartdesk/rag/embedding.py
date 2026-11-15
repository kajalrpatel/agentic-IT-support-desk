import threading

from fastembed import SparseTextEmbedding, TextEmbedding

from smartdesk.rag.models import Embedding


class FastEmbedEmbedding:
    """Local dense and sparse inference shared by indexing and query retrieval."""

    def __init__(self, dense_model: str, sparse_model: str, cache_dir: str):
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self.cache_dir = cache_dir
        self._lock = threading.Lock()
        self._dense: TextEmbedding | None = None
        self._sparse: SparseTextEmbedding | None = None

    @property
    def signature(self) -> str:
        return f"{self.dense_model}|{self.sparse_model}"

    def _models(self):
        with self._lock:
            if self._dense is None:
                dense = TextEmbedding(self.dense_model, cache_dir=self.cache_dir, threads=2)
                sparse = SparseTextEmbedding(self.sparse_model, cache_dir=self.cache_dir, threads=2)
                self._dense, self._sparse = dense, sparse
        assert self._dense is not None and self._sparse is not None
        return self._dense, self._sparse

    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        dense, sparse = self._models()
        return [
            Embedding(d.tolist(), s.indices.tolist(), s.values.tolist())
            for d, s in zip(dense.embed(texts), sparse.embed(texts), strict=True)
        ]

    def embed_query(self, query: str) -> Embedding:
        dense, sparse = self._models()
        d = next(iter(dense.query_embed(query)))
        s = next(iter(sparse.query_embed(query)))
        return Embedding(d.tolist(), s.indices.tolist(), s.values.tolist())
