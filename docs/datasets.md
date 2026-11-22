# Dataset provenance and review

HR comes from `strova-ai/hr-policies-qa-dataset`, revision `83682448cb8afe6a6123583e722ecdf04fb20b40`. Its dataset card declares MIT. The full downloaded JSONL has 644 rows and SHA-256 `c8d012fc78f1e8e10a1ccb3ab5bbf0b0a894533b8957f7d3b43d064c49e77777`. The repository contains a curated 32-row subset with source row links. Embedded system messages are excluded; occurrences of the original company name are replaced with NovaTech for the fictional demo. These adaptations are recorded in `knowledge_base/manifest.json`.

Source: https://huggingface.co/datasets/strova-ai/hr-policies-qa-dataset

The upstream source is concentrated on conduct, confidentiality, remote work, and compensatory leave. The additional assistant-drafted [Employee Leave Policy](../knowledge_base/hr/hr-leave-policy.md), approved for this fictional demo on 2026-11-21, establishes casual, sick, earned/vacation, maternity, paternity, and compensatory leave rules. These rules are synthetic company policy, not facts supplied by the upstream dataset or statements of applicable law. Individual payroll records, meal reimbursement limits, personal leave balances, and individual approval status remain unsupported. Review the license and upstream notices when distributing the corpus; a local copy of the source README is downloaded by the import script.

The 32 IT documents are assistant-generated, vendor-neutral procedures for the fictional NovaTech organization. They define company-specific processes explicitly, avoid invented real company URLs, and do not prescribe unverified product commands. Their metadata labels them synthetic and reviewed-fictional. The generation model's exact serving revision was not captured and is not invented in the manifest.

To reproduce the source download and HR curation from `backend/`:

```sh
uv run python scripts/import_hr.py --revision 83682448cb8afe6a6123583e722ecdf04fb20b40
uv run python scripts/prepare_corpus.py
```

The corpus now contains 72 documents: 32 curated HR documents, eight fictional HR handbook documents and 32 synthetic IT guides. The manifest lists the reviewed Markdown files by document ID and domain. After editing a handbook document, run `uv run python scripts/prepare_corpus.py --inventory-only` from `backend/` to refresh it. Evaluation questions are maintained separately under `evaluations/datasets/cases/`. From the repository root, `uv run --project backend python -m evaluations.assemble_dataset` checks their expected source IDs against the manifest and builds the benchmark. Questions are never indexed. The Console-AI ticket dataset is not used. The selected strategy is PROJECT.md Option C.
