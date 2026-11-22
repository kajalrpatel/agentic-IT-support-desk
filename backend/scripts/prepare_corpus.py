"""Reproduce the curated HR subset and the reviewed fictional IT corpus."""

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml
from corpus_sources import HR_FILENAMES, IT_GUIDES

from smartdesk.rag.document_loader import load_documents

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "knowledge_base"


def write_document(identifier, title, domain, source, body, synthetic):
    metadata = {
        "id": identifier,
        "title": title,
        "domain": domain,
        "source": source,
        "version": "1",
        "effective_date": "2026-11-07",
        "access_scope": "employees",
        "synthetic": synthetic,
        "review_status": "reviewed-fictional",
    }
    filename = HR_FILENAMES[identifier] if domain == "HR" else identifier
    path = KB / domain.lower() / f"{filename}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n\n"
        + body
        + "\n",
        encoding="utf-8",
    )


def prepare_documents(revision: str):
    rows = [
        json.loads(line) for line in (KB / "raw/hr.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for identifier in HR_FILENAMES:
        index = int(identifier.removeprefix("hr-"))
        messages = rows[index]["messages"]
        question = next(m["content"] for m in messages if m["role"] == "user").replace(
            "Kreeda Labs", "NovaTech"
        )
        answer = next(m["content"] for m in messages if m["role"] == "assistant").replace(
            "Kreeda Labs", "NovaTech"
        )
        write_document(
            identifier,
            question,
            "HR",
            f"https://huggingface.co/datasets/strova-ai/hr-policies-qa-dataset/blob/{revision}/dataset.jsonl#L{index + 1}",
            f"# {question}\n\n{answer}",
            False,
        )
    for slug, title, body in IT_GUIDES:
        identifier = f"it-{slug}"
        write_document(
            identifier, title, "IT", f"synthetic:novatech/{slug}/v1", f"# {title}\n\n{body}", True
        )


def update_inventory(manifest: dict):
    docs = load_documents(KB)
    counts = Counter(d.domain for d in docs)
    manifest["curation"] = {
        "company": "NovaTech (fictional)",
        "hr_row_indices_zero_based": [int(key.removeprefix("hr-")) for key in HR_FILENAMES],
        "hr_changes": [
            "Company name changed from Kreeda Labs to NovaTech where present",
            "System-role instructions excluded",
        ],
        "hr_review": "Selected answers inspected for internal consistency; legal and real-employer applicability not asserted",
        "it_documents": counts["IT"],
        "it_generation": {
            "generator": "OpenAI Codex assistant (interactive generation)",
            "model_revision": "not captured",
            "prompt_version": "option-c-v1",
            "review": "Reviewed as vendor-neutral fictional company procedures; no product-specific command sequences included",
        },
        "synthetic_hr_documents": sorted(d.id for d in docs if d.synthetic and d.domain == "HR"),
        "synthetic_hr_review": "Assistant-authored fictional handbook content for the NovaTech project. The user approved indexing the leave policy on 2026-11-21 and requested wider topic coverage on 2026-11-22.",
        "document_count": len(docs),
        "documents": [{"id": d.id, "domain": d.domain} for d in sorted(docs, key=lambda d: d.id)],
    }
    (KB / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {counts['HR']} HR and {counts['IT']} IT documents")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="Inventory the reviewed Markdown without regenerating source documents",
    )
    args = parser.parse_args()
    manifest = json.loads((KB / "manifest.json").read_text(encoding="utf-8"))
    if not args.inventory_only:
        prepare_documents(manifest["hr_source"]["revision"])
    update_inventory(manifest)


if __name__ == "__main__":
    main()
