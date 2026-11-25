# SmartDesk AI

An IT and HR support assistant for the fictional NovaTech company. It answers from cited company sources, offers escalation when evidence is missing, prepares tickets for explicit approval, and fetches ticket status from Jira.

React and FastAPI run as separate container images. PostgreSQL stores conversations and workflow checkpoints; Qdrant provides dense and BM25 retrieval with reciprocal rank fusion and cross-encoder reranking. Chat uses HTTP streaming for progress updates and delivers answers after evidence checks.

## Run locally

Requirements: Docker Desktop with Linux containers, network access for image/model downloads, and sufficient memory for the stack and local embedding/reranking models. For source development, use Python 3.12 or 3.13, uv, and Node 22.

1. Copy `.env.example` to `.env` if it does not already exist. Set a random `SESSION_SECRET` of at least 32 characters and a database password; keep both database URLs consistent with that password.
2. Configure `OPENAI_API_KEY` and an accessible `LLM_MODEL`. Configure `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`, and the project's `JIRA_ISSUE_TYPE` for real tickets. Keep credentials out of source control.
3. Start the stack and index the included reviewed corpus:

```sh
docker compose up -d --build
docker compose exec backend smartdesk ingest
```

Open [the local app](http://localhost:8080) and [API documentation](http://localhost:8000/docs). Migrations run automatically before the backend starts. First ingestion downloads model weights; subsequent ingestion skips unchanged documents. Demo mode uses a configured fictional identity and is restricted to local development. Production configuration requires OIDC.

After editing `.env`, run `docker compose up -d` to recreate affected services. `docker compose stop` preserves application data. Do not remove volumes unless you intend to erase their data.

The interface and health checks can start without provider credentials. Answer generation needs OpenAI access; ticket creation and status need Jira access. Missing configuration is reported rather than replaced with invented answers or tickets.

## Repository

```text
backend/
  src/smartdesk/
    api/                 HTTP schemas and routers for health, authentication, and conversations
    application/         Chat and ticket workflows, shared models, and storage interfaces
    domain/              Provider-independent models and errors
    workflows/           Persistent LangGraph orchestration
    infrastructure/      Shared identity, PostgreSQL, OpenAI, and Jira adapters
    rag/                 Complete ingestion, retrieval, and grounded-answer feature
      document_loader.py Reviewed Markdown loading
      chunking.py        Section-aware chunking and stable content hashes
      embedding.py       Local dense and sparse embeddings
      qdrant_store.py    Database operations and native hybrid fusion
      reranking.py       Local cross-encoder scoring
      ingestion.py       Incremental indexing pipeline
      retrieval.py       Query embedding, search, reranking, and context selection
      answer_generation.py Source-based claim generation
      grounding.py       Citation validation and evidence verification
      query_pipeline.py Public grounded-answer entry point
      rag_models.py      RAG data contracts
      rag_interfaces.py  Replaceable RAG component contracts
      rag_factory.py     RAG component construction and resource ownership
      answer_prompts/    Answer generation and evidence verification instructions
    conversation_prompts/ Intent routing and conversation summarization instructions
  migrations/            Application schema migrations
  scripts/               Dataset import and corpus preparation
  tests/                 Workflow, API, authorization, and provider tests
frontend/
  src/api/               Generated API types and transport
  src/features/tickets/  Editable ticket approval UI
  nginx.conf.template    Runtime API proxy configuration
  docker-entrypoint.d/   Public frontend runtime configuration
contracts/               Generated OpenAPI schema
knowledge_base/          40 HR and 32 synthetic IT documents, provenance
evaluations/             92 labeled cases, runners, measured results
tests/e2e/               Browser journeys
docs/                    Architecture, operations, datasets, demo
```

## Verify changes

From `backend/`:

```sh
uv sync --frozen --group dev
uv run ruff check src tests scripts migrations
uv run ruff format --check src tests scripts migrations
uv run mypy src
uv run pytest -q
```

From `frontend/`:

```sh
npm ci
npm run build
npx playwright install chromium
npm test
```

Browser tests start isolated API and UI servers on ports 8001 and 5173 with controlled provider doubles. They do not create real Jira tickets or call a paid model. The Docker demo can stay running on ports 8000 and 8080.

After changing API schemas, run `uv run smartdesk export-openapi` in `backend/` with `SESSION_SECRET` configured, then `npm run generate:api` in `frontend/`. Do not edit generated contracts manually. Frontend source uses Prettier; exclude `src/api/generated.ts` from manual formatting to preserve generator output.

## Evidence and remaining acceptance checks

See [verification results](docs/verification.md) and [retrieval metrics](evaluations/reports/status.json). Local workflow tests use controlled providers. Real embedding/reranking models were evaluated against 40 development and 40 held-out cases. The authorized Jira create/read smoke test passed (SCRUM-5). The application and evaluation judge use `LLM_MODEL`; `gpt-4o-mini` is the example/default, not a fixed requirement. Historical reports record the model actually used. Live smoke-test results are recorded in the verification report; the November 22 held-out answer run covered all 46 current cases (38 of 39 answerable questions received citations). AWS hosting, public authentication validation, load testing, and independently reviewed answer quality remain deployment gates.

The corpus includes adapted HR source material and explicitly synthetic IT guidance; it is not a real employer's policy. The original HR dataset's scope is narrower than all HR questions. Unsupported topics should escalate. See [dataset provenance and gaps](docs/datasets.md).

- Architecture diagrams: [system overview](docs/architecture.md#system-overview), [shared state during a conversation](docs/architecture.md#shared-state-during-a-conversation), and [ticket approval lifecycle](docs/architecture.md#ticket-approval-lifecycle).
- [Backend naming guide](docs/backend_naming.md)
- [Operations, authentication, backup, and deployment](docs/operations.md)
- [Demo walkthrough](docs/demo.md)
- [Evaluation commands and limitations](evaluations/README.md)
- [Approved implementation plan](IMPLEMENTATION_PLAN.md)
## Agent architecture and evaluation updates

The backend now has specialised IT/HR LangGraph sub-agents and separate agent, tool, workflow, RAG, and observability modules. See [agents and evaluation](docs/agents_and_evaluation.md) for the current structure, LangSmith configuration, and quantitative evaluation commands.
