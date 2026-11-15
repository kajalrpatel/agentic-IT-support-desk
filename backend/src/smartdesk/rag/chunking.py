import hashlib
from collections.abc import Iterator

from smartdesk.rag.rag_models import Chunk, Document

CHUNKER_VERSION = "paragraph-v1"


def chunks(document: Document, max_chars: int = 1500) -> Iterator[Chunk]:
    """Preserve the existing paragraph-based boundaries and hash format."""
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
