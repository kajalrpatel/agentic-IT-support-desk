# Evaluation

`datasets/knowledge.jsonl` has 40 development and 40 held-out cases: each split contains 32 answerable questions and 8 unknowns. Questions are not indexed. The supplied labels identify a preferred document; overlapping HR policies can make these labels conservative. Review relevance judgments before using a score as a deployment decision. These cases were assistant-authored alongside the fictional corpus, so a separately human-authored final set is still desirable.

From `backend/`:

```sh
uv run python ../evaluations/runners/evaluate.py --local --split development
uv run python ../evaluations/runners/evaluate.py --local --split held_out
```

Local evaluation uses real embedding, sparse, and reranking models with embedded Qdrant. The first run downloads model weights. Run without `--local` to use the configured Qdrant server and previously ingested collection. JSON reports include model IDs, thresholds, per-case rankings, Recall@5, MRR, and latency. Tune only on development cases. Reranker thresholds are model-specific; score rejection is disabled because a zero cutoff rejected relevant documents in development testing.

`--with-answers` explicitly enables paid model calls (up to three per single-turn query: routing, generation, verification, excluding retries). Reports include actual responses and citations; inspect correctness and count correct abstentions and unnecessary escalations. Retrieval scores alone do not establish faithfulness. Use `langsmith_answer_experiment.py <report.json> --dataset-name <new-name> --with-judge --limit 5` for optional paid faithfulness/relevance scoring with `gpt-4o-mini`, published directly to LangSmith. Omit `--with-judge` for citation coverage only.

Backend tests exercise more than 15 conversation and failure scenarios with controlled provider doubles. Those tests verify workflow behavior, not real-world model quality. Live LLM/Jira smoke tests require configured credentials and are reported separately.
## Multi-agent evaluation and LangSmith

See [agents and evaluation](../docs/agents_and_evaluation.md) for the current architecture, LangSmith setup, custom evaluators, commands, and measurement limits. `--with-answers` evaluates supervisor-to-specialist handoff and records full retrieved contexts.
