from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from smartdesk.rag.rag_models import Chunk, Embedding, Passage


class QdrantStore:
    """Database operations only; embedding and pipeline decisions belong to callers."""

    def __init__(self, client: QdrantClient, collection: str):
        self.client = client
        self.collection = collection

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, chunk_id))

    def close(self) -> None:
        self.client.close()

    def ensure_collection(self, dimension: int) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                self.collection,
                vectors_config={
                    "dense": models.VectorParams(size=dimension, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )

    def records(self) -> dict[str, Chunk]:
        if not self.client.collection_exists(self.collection):
            return {}
        records = {}
        offset = None
        while True:
            page, offset = self.client.scroll(
                self.collection, limit=100, offset=offset, with_payload=True, with_vectors=False
            )
            for point in page:
                if not point.payload or "id" not in point.payload:
                    raise ValueError(
                        "Index contains a record without a chunk ID. Use a new collection."
                    )
                records[point.payload["id"]] = point.payload
            if offset is None:
                return records

    def upsert(self, records: list[Chunk], vectors: list[Embedding], signature: str) -> None:
        points = [
            models.PointStruct(
                id=self._point_id(record["id"]),
                vector={"dense": vector.dense, "sparse": self._sparse(vector)},
                payload={**record, "index_signature": signature},
            )
            for record, vector in zip(records, vectors, strict=True)
        ]
        self.client.upsert(self.collection, points=points, wait=True)

    def delete(self, chunk_ids: list[str]) -> None:
        self.client.delete(
            self.collection,
            points_selector=models.PointIdsList(points=[self._point_id(i) for i in chunk_ids]),
            wait=True,
        )

    @staticmethod
    def _sparse(vector: Embedding) -> models.SparseVector:
        return models.SparseVector(indices=vector.sparse_indices, values=vector.sparse_values)

    def search(self, vectors: Embedding, mode: str, limit: int, access_scope: str) -> list[Passage]:
        filters = models.Filter(
            must=[
                models.FieldCondition(
                    key="access_scope", match=models.MatchValue(value=access_scope)
                )
            ]
        )
        sparse = self._sparse(vectors)
        if mode in {"dense", "sparse"}:
            points = self.client.query_points(
                self.collection,
                query=vectors.dense if mode == "dense" else sparse,
                using=mode,
                query_filter=filters,
                limit=limit,
            ).points
        elif mode == "hybrid":
            points = self.client.query_points(
                self.collection,
                prefetch=[
                    models.Prefetch(
                        query=vectors.dense, using="dense", filter=filters, limit=limit
                    ),
                    models.Prefetch(query=sparse, using="sparse", filter=filters, limit=limit),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
            ).points
        else:
            raise ValueError("Unknown store search mode")
        return [
            Passage(
                p.payload["id"], p.payload["title"], p.payload["text"], p.payload["source"], p.score
            )
            for p in points
            if p.payload
        ]
