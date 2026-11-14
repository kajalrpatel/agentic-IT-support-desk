import threading
from dataclasses import replace
from uuid import NAMESPACE_URL, uuid5

from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import QdrantClient, models

from smartdesk.config import Settings
from smartdesk.domain.models import Passage, ServiceError


class HybridRetriever:
    def __init__(self, settings: Settings, client: QdrantClient | None = None):
        self.settings = settings
        self.client = client or QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key.get_secret_value() or None,
            timeout=20,
        )
        self._lock = threading.Lock()
        self._search_slots = threading.BoundedSemaphore(2)
        self._dense: TextEmbedding | None = None
        self._sparse: SparseTextEmbedding | None = None
        self._reranker: TextCrossEncoder | None = None

    def models(self):
        # Lazy loading keeps health checks and startup independent of downloads.
        with self._lock:
            if self._dense is None:
                dense = TextEmbedding(
                    self.settings.embedding_model,
                    cache_dir=self.settings.model_cache_dir,
                    threads=2,
                )
                sparse = SparseTextEmbedding(
                    self.settings.sparse_model, cache_dir=self.settings.model_cache_dir, threads=2
                )
                reranker = TextCrossEncoder(
                    self.settings.reranker_model, cache_dir=self.settings.model_cache_dir, threads=2
                )
                self._dense, self._sparse, self._reranker = dense, sparse, reranker
        assert self._dense is not None and self._sparse is not None and self._reranker is not None
        return self._dense, self._sparse, self._reranker

    def search(self, query: str, mode: str = "reranked") -> list[Passage]:
        if not self._search_slots.acquire(timeout=10):
            raise ServiceError("Knowledge search is busy. Please retry shortly.")
        try:
            return self._search(query, mode)
        finally:
            self._search_slots.release()

    def _search(self, query: str, mode: str) -> list[Passage]:
        if mode not in {"dense", "sparse", "hybrid", "reranked"}:
            raise ValueError("Unknown retrieval mode")
        try:
            dense, sparse, reranker = self.models()
            qdense = list(dense.query_embed(query))[0].tolist()
            qsparse = list(sparse.query_embed(query))[0]
            svector = models.SparseVector(
                indices=qsparse.indices.tolist(), values=qsparse.values.tolist()
            )
            filters = models.Filter(
                must=[
                    models.FieldCondition(
                        key="access_scope", match=models.MatchValue(value="employees")
                    )
                ]
            )
            if mode in {"dense", "sparse"}:
                results = self.client.query_points(
                    self.settings.qdrant_collection,
                    query=qdense if mode == "dense" else svector,
                    using=mode,
                    query_filter=filters,
                    limit=self.settings.candidate_limit,
                ).points
            else:
                results = self.client.query_points(
                    self.settings.qdrant_collection,
                    prefetch=[
                        models.Prefetch(
                            query=qdense,
                            using="dense",
                            filter=filters,
                            limit=self.settings.candidate_limit,
                        ),
                        models.Prefetch(
                            query=svector,
                            using="sparse",
                            filter=filters,
                            limit=self.settings.candidate_limit,
                        ),
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=self.settings.candidate_limit,
                ).points
            passages = [
                Passage(
                    id=p.payload["id"],
                    title=p.payload["title"],
                    text=p.payload["text"],
                    source=p.payload["source"],
                    score=p.score,
                )
                for p in results
                if p.payload
            ]
            if mode == "reranked" and passages:
                scores = list(reranker.rerank(query, [p.text for p in passages]))
                passages = sorted(
                    [
                        replace(p, score=float(score))
                        for p, score in zip(passages, scores, strict=True)
                    ],
                    key=lambda p: p.score,
                    reverse=True,
                )
                if self.settings.reranker_min_score is not None:
                    passages = [p for p in passages if p.score >= self.settings.reranker_min_score]
            return passages[: self.settings.context_limit]
        except Exception as exc:
            raise ServiceError(
                "Knowledge search is unavailable. Please retry shortly; this does not mean the policy is missing."
            ) from exc

    def ingest(self, records: list[dict]) -> dict:
        dense, sparse, _ = self.models()
        collection = self.settings.qdrant_collection
        if not self.client.collection_exists(collection):
            dimension = len(list(dense.embed(["dimension check"]))[0])
            self.client.create_collection(
                collection,
                vectors_config={
                    "dense": models.VectorParams(size=dimension, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
        signature = f"{self.settings.embedding_model}|{self.settings.sparse_model}|paragraph-v1"
        old: dict[str, dict] = {}
        offset = None
        while True:
            page, offset = self.client.scroll(
                collection, limit=100, offset=offset, with_payload=True, with_vectors=False
            )
            for item in page:
                old[str(item.id)] = item.payload or {}
            if offset is None:
                break
        if any(value.get("index_signature") != signature for value in old.values()):
            raise ValueError("Index model/chunker mismatch. Use a new QDRANT_COLLECTION.")
        identifiers = {str(uuid5(NAMESPACE_URL, record["id"])) for record in records}
        changed = [
            record
            for record in records
            if old.get(str(uuid5(NAMESPACE_URL, record["id"])), {}).get("hash") != record["hash"]
        ]
        if changed:
            texts = [record["title"] + "\n" + record["text"] for record in changed]
            dvectors = list(dense.embed(texts))
            svectors = list(sparse.embed(texts))
            points = [
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, record["id"])),
                    vector={
                        "dense": dv.tolist(),
                        "sparse": models.SparseVector(
                            indices=sv.indices.tolist(), values=sv.values.tolist()
                        ),
                    },
                    payload={**record, "index_signature": signature},
                )
                for record, dv, sv in zip(changed, dvectors, svectors, strict=True)
            ]
            self.client.upsert(collection, points=points, wait=True)
        removed = list(set(old) - identifiers)
        if removed:
            self.client.delete(
                collection,
                points_selector=models.PointIdsList(points=[str(p) for p in removed]),
                wait=True,
            )
        return {
            "indexed": len(changed),
            "unchanged": len(records) - len(changed),
            "removed": len(removed),
        }
