# Leave policy ingestion: 2026-11-21

The user approved activating the synthetic NovaTech leave handbook. The reviewed document is `knowledge_base/hr/hr-leave-policy.md`, with domain `HR` and employee access scope. The existing paragraph chunker produced 12 chunks. The running backend ingested dense and sparse embeddings into its configured Qdrant collection: **12 indexed, 64 unchanged, 0 removed**. Corpus validation now finds **65 documents and 76 chunks**. A stray `i` before the front matter of `hr-609.md` was also corrected; its existing indexed content was unchanged.

Seven HR-filtered hybrid searches with reranking retrieved the leave policy in their top five results: sick, vacation, maternity, casual, and paternity entitlements, earned-leave carry-forward, and sick-leave encashment. This is a targeted retrieval check, not a new full benchmark or a comparison against dense-only retrieval.

Three live checks used the configured language model through `QueryPipeline` (retrieval, generation, and grounding verification):

| Question | Observed result |
| --- | --- |
| Annual sick leave | Cited answer: 8 paid days per calendar year, prorated for a partial year. |
| Annual vacation leave | Cited answer: 15 paid earned-leave days per full year. It also suggested casual leave could be considered vacation, an unnecessary interpretation not explicitly established by the policy. Do not count this as fully correct merely because grounding verification passed. |
| Personal remaining vacation balance | Abstained without citations and offered support; no personal balance invented. |

These checks did not exercise frontend/session routing, create Jira tickets, or publish a new LangSmith experiment. Standalone diagnostic tracing was disabled; application tracing settings were unchanged.

Evaluation version `2026-11-21-leave-policy-v1` replaces the three obsolete unknown entitlement cases and adds six cases covering more leave rules and unavailable personal records. There are 86 cases (43 per split). Dataset IDs and document references were validated; corpus preparation lint and `git diff --check` passed. Historical evaluation reports remain historical; rerun the full evaluation with `--limit 43` per split to measure this expanded corpus.
