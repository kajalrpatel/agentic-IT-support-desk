# Backend naming guide

Names identify responsibility, especially when several files appear together in editor tabs. RAG remains a feature package; application services handle chat and tickets; shared infrastructure contains external-provider adapters. File renaming does not change API routes, database tables, checkpoint fields, or the Qdrant index.

| Previous path under `smartdesk/` | Current path | Responsibility |
| --- | --- | --- |
| `prompts/router.txt` | `conversation_prompts/intent_routing.txt` | Classify intent and resolve conversational references |
| `prompts/summary.txt` | `conversation_prompts/conversation_summary.txt` | Summarize older conversation history |
| `rag/prompts/answer.txt` | `rag/answer_prompts/answer_generation.txt` | Generate claims from retrieved evidence |
| `rag/prompts/verify.txt` | `rag/answer_prompts/evidence_verification.txt` | Verify claims against their cited evidence |
| `application/ports.py` | `application/ticket_provider.py` | Ticket-provider interface |
| `api/schemas.py` | `api/api_schemas.py` | HTTP request and response contracts |
| `domain/models.py` | `domain/support_models.py` | Identity, tickets, and shared service errors |
| `rag/models.py` | `rag/rag_models.py` | Documents, embeddings, passages, claims, and answer results |
| `rag/interfaces.py` | `rag/rag_interfaces.py` | Embedding, storage, retrieval, ranking, and answer-model contracts |
| `rag/factory.py` | `rag/rag_factory.py` | Construct RAG components and own their resources |
| `workflows/graph.py` | `workflows/conversation_workflow.py` | LangGraph conversation and approval workflow |
| `infrastructure/llm/client.py` | `infrastructure/llm/openai_client.py` | Shared OpenAI API integration |
| `infrastructure/jira/client.py` | `infrastructure/jira/jira_client.py` | Jira API integration |
| `infrastructure/postgres/models.py` | `infrastructure/postgres/database_models.py` | SQLAlchemy table definitions |
| `infrastructure/postgres/repository.py` | `infrastructure/postgres/conversation_repository.py` | Conversation persistence and locking |
| `infrastructure/identity/auth.py` | `infrastructure/identity/authentication.py` | Demo and OIDC identity validation |

The RAG processing names already describe their jobs: `document_loader.py`, `chunking.py`, `embedding.py`, `qdrant_store.py`, `reranking.py`, `ingestion.py`, `retrieval.py`, `answer_generation.py`, `grounding.py`, and `query_pipeline.py`.

Conventional entry points remain `main.py` (FastAPI application), `cli.py` (administration commands), `config.py` (settings), and `bootstrap.py` (application composition). Python's `__init__.py`, pytest's `conftest.py`, and Alembic's `env.py` retain their framework-standard names. Migration filenames remain stable to preserve their ordered history.

The frontend's `App.tsx`, `main.tsx`, and `src/api/client.ts` are unambiguous within the frontend package and retain their names. Generated API files retain generator-controlled names. Existing test filenames identify the feature they test rather than mirroring every implementation file.

Prompt selection uses an explicit mapping in `infrastructure/llm/openai_client.py`. Add new prompt purposes there; do not assume a shared generic prompt directory.
