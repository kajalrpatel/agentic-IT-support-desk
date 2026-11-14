# Verification record

Local verification on 2026-11-08. Automated workflow tests use provider doubles; they do not establish live provider compatibility or model quality.

## Completed local checks

- 25 backend tests passed.
- 4 Chromium browser journeys passed: refresh persistence, ticket editing/confirmation/status, cancellation, and mobile layout.
- Ruff lint and formatting passed; Mypy passed for 19 source files.
- TypeScript and Vite production build passed.
- Both container images built; PostgreSQL application/checkpoint migrations and health checks passed.
- Frontend proxy authentication and real PostgreSQL conversation create/read smoke checks passed.
- All 64 documents were indexed in the Qdrant 1.20 container.
- Authorized live Jira smoke test passed: SCRUM-5 was created and fetched with status To Do. No real employee issue was submitted.
- Hosted CI has not run.

## Retrieval measurements

Each split has 32 answerable and 8 deliberately unknown questions. Recall and MRR below use answerable questions. The labels and questions were assistant-authored alongside the corpus; a separately human-reviewed benchmark is still needed.

| Method | Development Recall@5 | Held-out Recall@5 | Held-out MRR | Held-out mean latency |
| --- | ---: | ---: | ---: | ---: |
| Dense | 100% | 96.9% | 0.865 | 12 ms |
| BM25 | 87.5% | 87.5% | 0.820 | 12 ms |
| Hybrid RRF | 96.9% | 100% | 0.862 | 18 ms |
| Hybrid + reranker | 96.9% | 100% | 0.890 | 709 ms |

These are local embedded-Qdrant runs with real FastEmbed models, not production latency or load measurements. Reranking adds material CPU cost. Hybrid retrieval improved held-out recall but did not beat dense retrieval on development recall. A zero reranker score cutoff reduced development recall to 75%; score rejection was disabled before the final held-out run. No further held-out tuning was performed. Summaries are in `evaluations/reports/status.json`; runners reproduce per-case reports locally.

## Rubric evidence

| Criterion | Implemented evidence | Remaining live evidence |
| --- | --- | --- |
| Grounding | Retrieved-source citations, structured claims, second evidence check, invalid-citation and unsupported-answer tests | Paid answer evaluation, human claim review, faithfulness and false-escalation measurements |
| Escalation | Unknown-query offer, clarifying routes, controlled tests | Held-out model abstention quality |
| Ticket creation | Required fields, editable preview, versioned approval, durable attempt and timeout reconciliation tests | Create/read passed for configured Task issue type; verify any additional project-specific fields before expanding use |
| Ticket status | Paginated API adapter, ownership checks, permitted comments, zero/one/many tests | Basic live create/read/status passed; multi-ticket UI journey remains covered by doubles |
| Context | PostgreSQL transcripts/checkpoints, recent history plus older summary, contextual routing, restart and draft interruption tests | Live contextual language quality |
| Knowledge base | 32 reviewed HR documents and 32 synthetic IT guides; provenance and explicit gaps | Final reviewer sign-off on fictional policies |
| Code and docs | Separate image builds, module boundaries, generated contracts, tests, architecture and runbooks | Hosted CI execution and deployment review |

## Operational limitations

Public hosting is deferred. Production must use verified OIDC identity, TLS, secret management, and a reviewed access policy. Request replay is deduplicated and uncertain Jira writes are reconciled; fully automatic recovery from every application crash point is not implemented. Jira requested priority is currently recorded in the description, because each project's native priority/required-field mapping must be verified. Existing tickets require the app's employee ownership label to appear in lookup results.

Qdrant is pinned to 1.20.0 to match the installed client; see the [official release](https://github.com/qdrant/qdrant/releases/tag/v1.20.0). The initial 1.14 development index volume is retained separately; the final collection is rebuilt in a new volume.


## Live model setup: 2026-11-14

The supplied key rejected `gpt-5-mini` with HTTP 403 / `model_not_found`. Its available GPT mini model was `gpt-4o-mini`, which is now configured in `.env`, `.env.example`, and the backend default. Reasoning effort is optional and omitted for this model. The model supports structured output ([OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-4o-mini)).

Live testing found a follow-up routing failure and an unnecessary refusal to explain conditional source guidance. Routing instructions now explicitly resolve procedural follow-ups, and the answer prompt permits condition-preserving guidance without assuming the condition occurred. The independent evidence verifier remains unchanged. This smoke set was used for development; it is not a held-out quality benchmark.

Final live smoke run: 4/6 checks passed (cited IT answer, unknown-topic escalation, ticket preview, cancellation). Two checks failed: the contextual password-reset follow-up and compensatory-time-off question unnecessarily escalated despite relevant source material. Earlier runs answered the HR question with correct source citations, so this remains a model/prompt reliability issue, not verified stable behavior. The stored transcript restored all 12 messages. No Jira issue was created by these model tests. Backend regression tests remained 25/25, and lint/type checks passed. Full held-out answer-quality and abstention evaluation remains outstanding.
