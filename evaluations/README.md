# Evaluation

`datasets/knowledge.jsonl` has 40 development and 40 held-out cases: each split contains 32 answerable questions and 8 unknowns. Questions are not indexed. The supplied labels identify a preferred document; overlapping HR policies can make these labels conservative. Review relevance judgments before using a score as a deployment decision. These cases were assistant-authored alongside the fictional corpus, so a separately human-authored final set is still desirable.

From `backend/`:

```sh
uv run python ../evaluations/runners/evaluate.py --local --split development
uv run python ../evaluations/runners/evaluate.py --local --split held_out
```

Local evaluation uses real embedding, sparse, and reranking models with embedded Qdrant. The first run downloads model weights. Run without `--local` to use the configured Qdrant server and previously ingested collection. JSON reports include model IDs, thresholds, per-case rankings, Recall@5, MRR, and latency. Tune only on development cases. Reranker thresholds are model-specific; score rejection is disabled because a zero cutoff rejected relevant documents in development testing.

`--with-answers` explicitly enables paid model calls (up to two per query). Reports include actual responses and citations; inspect correctness and count correct abstentions and unnecessary escalations. Retrieval scores alone do not establish faithfulness. For an additional paid judge, install `uv sync --group eval` and run `uv run python ../evaluations/runners/faithfulness.py <report.json>` with the judge's environment configured. Ragas may use a separate default judge model; check its configuration and budget before running.

Backend tests exercise more than 15 conversation and failure scenarios with controlled provider doubles. Those tests verify workflow behavior, not real-world model quality. Live LLM/Jira smoke tests require configured credentials and are reported separately.
