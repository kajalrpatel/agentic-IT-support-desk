from pathlib import Path

from smartdesk.rag.chunking import chunks
from smartdesk.rag.document_loader import load_documents


def test_corpus_has_provenance_and_both_domains():
    root = Path(__file__).resolve().parents[2] / "knowledge_base"
    docs = load_documents(root)
    assert len(docs) >= 60
    assert {doc.domain for doc in docs} == {"IT", "HR"}
    assert all(doc.source and doc.review_status for doc in docs)
    records = [c for doc in docs for c in chunks(doc)]
    assert len({c["id"] for c in records}) == len(records)
    assert all(len(c["text"]) <= 1500 for c in records)


def test_handbook_chunks_keep_their_policy_scope():
    docs = load_documents(Path(__file__).resolve().parents[2] / "knowledge_base")
    leave = next(d for d in docs if d.id == "hr-leave-policy")
    earned = [c["text"] for c in chunks(leave) if "## 6. Earned leave and vacation" in c["text"]]
    assert earned and any("1.25" in c for c in earned)
    assert all("## 5. Sick leave" not in c for c in earned)
