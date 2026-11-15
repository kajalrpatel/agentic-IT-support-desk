from pathlib import Path

import yaml

from smartdesk.rag.models import Document


def load_documents(root: Path) -> list[Document]:
    documents = []
    seen: set[str] = set()
    for path in sorted(root.glob("*/*.md")):
        if path.parent.name not in {"hr", "it"}:
            continue
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            continue
        _, metadata, body = content.split("---", 2)
        data = yaml.safe_load(metadata)
        # YAML may parse ISO dates into date objects.
        data["effective_date"] = str(data["effective_date"])
        data["version"] = str(data["version"])
        document = Document(**data, text=body.strip())
        if document.id in seen:
            raise ValueError(f"Duplicate document ID: {document.id}")
        if document.review_status not in {"reviewed", "reviewed-fictional"}:
            raise ValueError(f"Document needs review: {document.id}")
        seen.add(document.id)
        documents.append(document)
    if not documents:
        raise ValueError("No reviewed knowledge-base documents found")
    return documents
