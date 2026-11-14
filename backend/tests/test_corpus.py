from pathlib import Path

from smartdesk.ingestion.documents import chunks, load_documents


def test_corpus_has_provenance_and_both_domains():
    root = Path(__file__).resolve().parents[2] / "knowledge_base"
    docs = load_documents(root)
    assert len(docs) >= 60
    assert {doc.domain for doc in docs} == {"IT", "HR"}
    assert all(doc.source and doc.review_status for doc in docs)
    records = [c for doc in docs for c in chunks(doc)]
    assert len({c["id"] for c in records}) == len(records)
    assert all(len(c["text"]) <= 1500 for c in records)
