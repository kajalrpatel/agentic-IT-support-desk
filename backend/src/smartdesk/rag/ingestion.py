from pathlib import Path

from smartdesk.rag.chunking import CHUNKER_VERSION, chunks
from smartdesk.rag.document_loader import load_documents
from smartdesk.rag.rag_interfaces import Embedder, KnowledgeStore
from smartdesk.rag.rag_models import Chunk


class IngestionPipeline:
    def __init__(self, embedder: Embedder, store: KnowledgeStore):
        self.embedder = embedder
        self.store = store

    def run(self, root: Path) -> dict[str, int]:
        return self.ingest([c for doc in load_documents(root) for c in chunks(doc)])

    def ingest(self, records: list[Chunk]) -> dict[str, int]:
        if not records:
            raise ValueError("Refusing to replace the index with an empty corpus.")
        signature = f"{self.embedder.signature}|{CHUNKER_VERSION}"
        old = self.store.records()
        if any(r.get("index_signature") != signature for r in old.values()):
            raise ValueError("Index model/chunker mismatch. Use a new QDRANT_COLLECTION.")
        identifiers = {r["id"] for r in records}
        if len(identifiers) != len(records):
            raise ValueError("Duplicate chunk IDs")
        changed = [r for r in records if old.get(r["id"], {}).get("hash") != r["hash"]]
        if changed:
            vectors = self.embedder.embed_documents(
                [r["title"] + "\n" + r["text"] for r in changed]
            )
            if len(vectors) != len(changed):
                raise ValueError("Embedding count does not match chunk count")
            self.store.ensure_collection(len(vectors[0].dense))
            self.store.upsert(changed, vectors, signature)
        removed = list(set(old) - identifiers)
        if removed:
            self.store.delete(removed)
        return {
            "indexed": len(changed),
            "unchanged": len(records) - len(changed),
            "removed": len(removed),
        }
