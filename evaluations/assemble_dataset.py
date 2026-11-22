"""Build the evaluation dataset using the reviewed knowledge document inventory."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "evaluations/datasets"


def main():
    manifest = json.loads(
        (ROOT / "knowledge_base/manifest.json").read_text(encoding="utf-8")
    )
    documents = {item["id"] for item in manifest["curation"]["documents"]}
    cases = []
    ids = set()
    for source in sorted((DATA / "cases").glob("*.jsonl")):
        for line in source.read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            identifier = case["id"]
            expected = set(case["expected_documents"])
            if identifier in ids or case["split"] not in {"development", "held_out"}:
                raise ValueError(f"Invalid ID or split in {source.name}: {identifier}")
            if expected - documents or bool(expected) != case["answerable"]:
                raise ValueError(
                    f"Invalid relevance labels for {identifier}: {expected}"
                )
            ids.add(identifier)
            cases.append(case)
    if not cases:
        raise ValueError("No evaluation cases found")
    (DATA / "knowledge.jsonl").write_text(
        "".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8"
    )
    print(f"Assembled {len(cases)} evaluation cases")


if __name__ == "__main__":
    main()
