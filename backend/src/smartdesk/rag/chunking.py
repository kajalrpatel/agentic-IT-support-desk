import hashlib
import re
import textwrap
from collections.abc import Iterator

from smartdesk.rag.rag_models import Chunk, Document

CHUNKER_VERSION = "section-v2"


def section_passages(text: str, limit: int) -> Iterator[str]:
    # Repeat the nearest policy headings when a section spans several passages.
    # The heading is the overlap: leave rules from adjacent benefits stay separate.
    headings: dict[int, str] = {}
    body = ""
    for line in [*text.splitlines(), "## "]:
        heading = re.match(r"^(#{1,6}) (.*)$", line)
        if not heading:
            body += line + "\n"
            continue
        if body.strip():
            prefix = "\n".join(headings.values())
            budget = limit - len(prefix) - 2
            if budget < 1:
                raise ValueError("Section headings exceed the chunk size limit")
            block = ""
            for paragraph in body.strip().split("\n\n"):
                parts = (
                    [paragraph]
                    if len(paragraph) <= budget
                    else textwrap.wrap(paragraph, width=budget)
                )
                for part in parts:
                    merged = (block + "\n\n" + part).strip()
                    if len(merged) > budget:
                        yield (prefix + "\n\n" + block).strip()
                        merged = part
                    block = merged
            if block:
                yield (prefix + "\n\n" + block).strip()
        depth = len(heading.group(1))
        headings = {level: title for level, title in headings.items() if level < depth}
        headings[depth] = line
        body = ""


def chunks(document: Document, max_chars: int = 1500) -> Iterator[Chunk]:
    short = len(document.text) <= max_chars
    segments = [document.text] if short else section_passages(document.text, max_chars)
    for index, body in enumerate(segments):
        yield {
            **document.model_dump(exclude={"text"}),
            "document_id": document.id,
            "id": f"{document.id}:{index}" if short else f"{document.id}:section-{index}",
            "text": body,
            "hash": hashlib.sha256((document.model_dump_json() + body).encode()).hexdigest(),
        }
