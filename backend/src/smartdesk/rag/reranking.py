import threading
from dataclasses import replace

from fastembed.rerank.cross_encoder import TextCrossEncoder

from smartdesk.rag.models import Passage


class FastEmbedReranker:
    def __init__(self, model: str, cache_dir: str):
        self.model = model
        self.cache_dir = cache_dir
        self._lock = threading.Lock()
        self._model: TextCrossEncoder | None = None

    def rank(self, query: str, passages: list[Passage]) -> list[Passage]:
        if not passages:
            return []
        with self._lock:
            if self._model is None:
                self._model = TextCrossEncoder(self.model, cache_dir=self.cache_dir, threads=2)
        scores = self._model.rerank(query, [p.text for p in passages])
        return sorted(
            [replace(p, score=float(s)) for p, s in zip(passages, scores, strict=True)],
            key=lambda p: p.score,
            reverse=True,
        )
