import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    title: str
    domain: str
    source: str
    version: str
    effective_date: str
    access_scope: str = "employees"
    synthetic: bool = False
    review_status: str
    text: str = Field(min_length=20)


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


def chunks(document: Document, max_chars: int = 1500):
    # Keep paragraphs intact unless unusually long. Token-limit enforcement occurs
    # in the embedder; this conservative character bound avoids typical truncation.
    paragraphs = document.text.split("\n\n")
    segments: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        for offset in range(0, len(paragraph), max_chars):
            part = paragraph[offset : offset + max_chars]
            if len(buffer) + len(part) > max_chars and buffer:
                segments.append(buffer.strip())
                buffer = ""
            buffer += part + "\n\n"
    if buffer.strip():
        segments.append(buffer.strip())
    for index, body in enumerate(segments):
        yield {
            **document.model_dump(exclude={"text"}),
            "document_id": document.id,
            "id": f"{document.id}:{index}",
            "text": body,
            "hash": hashlib.sha256((document.model_dump_json() + body).encode()).hexdigest(),
        }
