from dataclasses import replace

import pytest
from qdrant_client import QdrantClient

from smartdesk.rag.ingestion import IngestionPipeline
from smartdesk.rag.qdrant_store import QdrantStore
from smartdesk.rag.rag_models import Embedding
from smartdesk.rag.retrieval import RetrievalPipeline


class StubEmbedder:
    signature = "test-dense|test-sparse"

    def __init__(self):
        self.embedded = []

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return [Embedding([1.0, 0.0], [1], [1.0]) for _ in texts]

    def embed_query(self, query):
        return Embedding([1.0, 0.0], [1], [1.0])


class StubReranker:
    def __init__(self):
        self.calls = 0

    def rank(self, query, passages):
        self.calls += 1
        return [replace(p, score=-1.0) for p in reversed(passages)]


def record(identifier, text="Reset the password", scope="employees"):
    return {
        "id": identifier,
        "title": identifier,
        "text": text,
        "source": "synthetic:test",
        "hash": text + scope,
        "access_scope": scope,
    }


@pytest.fixture
def components():
    store = QdrantStore(QdrantClient(":memory:"), "test")
    embedder = StubEmbedder()
    reranker = StubReranker()
    yield store, embedder, reranker, IngestionPipeline(embedder, store)
    store.close()


def test_ingestion_skips_unchanged_updates_and_removes_stale_chunks(components):
    store, embedder, _, ingestion = components
    assert ingestion.ingest([record("a"), record("b")])["indexed"] == 2
    embedder.embedded.clear()
    assert ingestion.ingest([record("a"), record("b")]) == {
        "indexed": 0,
        "unchanged": 2,
        "removed": 0,
    }
    assert embedder.embedded == []
    assert ingestion.ingest([record("a", "Updated policy")]) == {
        "indexed": 1,
        "unchanged": 0,
        "removed": 1,
    }
    assert store.records()["a"]["text"] == "Updated policy"
    assert set(store.records()) == {"a"}


def test_ingestion_rejects_incompatible_signature_without_changing_index(components):
    store, embedder, _, ingestion = components
    ingestion.ingest([record("a")])
    embedder.signature = "different-model"
    with pytest.raises(ValueError, match="mismatch"):
        ingestion.ingest([record("b")])
    assert set(store.records()) == {"a"}


@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid", "reranked"])
def test_retrieval_modes_enforce_scope_and_only_rerank_when_requested(components, mode):
    store, embedder, reranker, ingestion = components
    ingestion.ingest([record("public"), record("restricted", scope="admins")])
    retrieval = RetrievalPipeline(embedder, store, reranker)
    result = retrieval.search("password", mode)
    assert [p.id for p in result] == ["public"]
    assert reranker.calls == (1 if mode == "reranked" else 0)
    if mode == "reranked":
        assert result[0].score == -1.0  # Negative scores remain valid by default.


def test_retrieval_applies_context_limit_and_optional_threshold(components):
    store, embedder, reranker, ingestion = components
    ingestion.ingest([record("a"), record("b")])
    assert (
        len(RetrievalPipeline(embedder, store, reranker, context_limit=1).search("password")) == 1
    )
    assert RetrievalPipeline(embedder, store, reranker, min_score=0).search("password") == []


def test_empty_corpus_cannot_accidentally_erase_index(components):
    store, _, _, ingestion = components
    ingestion.ingest([record("a")])
    with pytest.raises(ValueError, match="empty corpus"):
        ingestion.ingest([])
    assert set(store.records()) == {"a"}


@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid", "reranked"])
@pytest.mark.parametrize("domain", ["IT", "HR"])
def test_domain_filter_applies_before_candidate_selection(components, mode, domain):
    store, embedder, reranker, ingestion = components
    ingestion.ingest(
        [
            {**record("it"), "domain": "IT"},
            {**record("hr"), "domain": "HR"},
            {**record("private", scope="admins"), "domain": domain},
        ]
    )
    retrieval = RetrievalPipeline(embedder, store, reranker, candidate_limit=1)
    assert [p.id for p in retrieval.search("support", mode, domain=domain)] == [domain.lower()]


def test_verifier_keeps_relevant_claim_using_only_its_own_evidence():
    from smartdesk.rag.grounding import GroundingVerifier
    from smartdesk.rag.rag_models import Claim, EvidenceVerdict, GroundedAnswer, Passage

    passages = [
        Passage("earned", "Vacation", "Vacation is 15 days.", "test"),
        Passage("casual", "Casual", "Casual leave is for short commitments.", "test"),
    ]

    class Judge:
        def verify(self, data):
            if "retained_claims" in data:
                assert len(data["retained_claims"]) == 1
                return EvidenceVerdict(supported=True, reason="Complete")
            claim = data["claim"]
            assert [p["id"] for p in data["passages"]] == claim["citation_ids"]
            return EvidenceVerdict(supported=claim["citation_ids"] == ["earned"], reason="Checked")

    result = GroundingVerifier(Judge()).verify(
        "How much vacation?",
        passages,
        GroundedAnswer(
            answerable=True,
            claims=[
                Claim(text="Vacation is 15 days.", citation_ids=["earned"]),
                Claim(text="Use casual leave as vacation.", citation_ids=["casual"]),
            ],
        ),
    )
    assert result and result.text == "Vacation is 15 days. [1]"
    assert [c.id for c in result.citations] == ["earned"]
