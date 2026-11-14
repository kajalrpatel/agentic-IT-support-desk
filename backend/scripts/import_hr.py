"""Download the pinned HR source without executing dataset-provided code."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

DATASET = "strova-ai/hr-policies-qa-dataset"


def fetch(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("../knowledge_base"))
    parser.add_argument("--revision")
    args = parser.parse_args()
    revision = (
        args.revision or json.loads(fetch(f"https://huggingface.co/api/datasets/{DATASET}"))["sha"]
    )
    raw = fetch(f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/dataset.jsonl")
    readme = fetch(f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/README.md")
    target = args.root / "raw"
    target.mkdir(parents=True, exist_ok=True)
    (target / "hr.jsonl").write_bytes(raw)
    (target / "HR_SOURCE_README.md").write_bytes(readme)
    manifest_path = args.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest["hr_source"] = {
        "dataset": DATASET,
        "revision": revision,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "declared_license": "MIT",
        "rows": len(raw.splitlines()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["hr_source"]))
    for index, line in enumerate(raw.splitlines()):
        messages = json.loads(line)["messages"]
        question = next(m["content"] for m in messages if m["role"] == "user")
        print(f"{index}: {question}")


if __name__ == "__main__":
    main()
