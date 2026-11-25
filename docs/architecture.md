# SmartDesk architecture

The repository contains two independently buildable applications. The backend is a modular monolith with FastAPI transport, LangGraph orchestration, chat/ticket application services, and a self-contained `smartdesk.rag` feature. Shared adapters handle OpenAI, Jira, identity, and PostgreSQL; the Qdrant adapter belongs to RAG. The React frontend uses the versioned API; it does not access provider credentials or databases.

## System overview

```mermaid
flowchart LR
  Browser[React browser client] -->|HTTP + streamed events| API[FastAPI]
  API --> Auth[Demo identity or OIDC JWT validation]
  API --> Chat[Conversation service]
  Chat --> Graph[Persistent LangGraph workflow]
  Graph --> IT[IT support specialist]
  Graph --> HR[HR policy specialist]
  IT --> RAG[Domain-filtered dense + BM25 / RRF / cross-encoder]
  HR --> RAG
  RAG --> Qdrant[(Qdrant)]
  Graph --> Model[Structured LLM routing and evidence checks]
  Graph --> Approval[Versioned draft approval interrupt]
  Approval --> Tickets[Ticket service / creation attempt]
  Tickets --> Jira[Jira API]
  Graph --> Status[Owned ticket lookup]
  Status --> Jira
  Chat --> DB[(PostgreSQL application tables)]
  Graph --> CP[(PostgreSQL checkpoints)]
  Corpus[Reviewed HR + synthetic IT] --> Ingest[Ingestion command]
  Ingest --> Qdrant
```

## Shared state during a conversation

Each conversation has its own LangGraph thread. Its ID is the `thread_id` used to resume the graph from PostgreSQL. A node returns updates to named fields in `ChatState`. The specialist subgraphs share three field names with the parent graph: `text`, `route`, and `response`. The supervisor reads the conversation history and resolves the question before handing it to one specialist.

```mermaid
sequenceDiagram
    participant C as ChatService
    participant P as Parent graph (ChatState)
    participant S as Supervisor
    participant IT as IT specialist (SpecialistState)
    participant Q as Qdrant
    C->>P: Invoke same thread with text, history and verified email
    P->>S: Previous topic was VPN. Employee asks "Does it work on Mac?"
    S-->>P: Update route with IT category and standalone VPN question
    P->>IT: Pass text and route
    IT->>Q: Search employee-accessible IT passages
    Q-->>IT: Candidates for reranking
    IT->>IT: Store passages and candidate locally, verify claims
    IT-->>P: Update response with cited answer or escalation offer
    P-->>C: Return response and any pending approval
    C->>C: Save assistant message in PostgreSQL transcript
```

| State | Where it lives | What it enables |
| --- | --- | --- |
| Conversation identity, history, summary, route and response | Parent graph, checkpointed in PostgreSQL per conversation | The supervisor can resolve a follow-up when the browser sends the next message. |
| Retrieved passages and candidate answer | Selected specialist's subgraph | Search, generation and verification exchange intermediate results. The parent receives the employee-facing response. |
| Draft, draft version, approval action and approved version | Parent graph, checkpointed at the approval interrupt | An employee can refresh, edit or confirm the pending draft. |
| Ordered messages and ticket creation attempts | PostgreSQL application tables | The UI can reload the transcript and the ticket service can reconcile a repeated submission. |

See the [parent state definition](../backend/src/smartdesk/workflows/conversation_state.py), [specialist state definition](../backend/src/smartdesk/agents/specialist_graph.py), and [workflow wiring](../backend/src/smartdesk/workflows/conversation_workflow.py).

## Ticket approval lifecycle

```mermaid
stateDiagram-v2
    [*] --> Preview: Sufficient details for a draft
    Preview --> AwaitingApproval: Save version and interrupt
    AwaitingApproval --> Preview: Edit and increment version
    AwaitingApproval --> SideQuestion: Ask another question
    SideQuestion --> AwaitingApproval: Answer and preserve pending draft
    AwaitingApproval --> Cancelled: Cancel
    AwaitingApproval --> Submit: Confirm current version
    Submit --> Created: Jira returns ticket or reconciliation finds it
    Submit --> AwaitingApproval: Submission needs retry or reconciliation
    Created --> [*]
    Cancelled --> [*]
```

## API and storage boundaries

`main.py` creates the FastAPI application, installs middleware and registers the health, authentication and conversation routers in `api/routers/`. The conversation router owns messages, approval and streaming. Application models define the validated inputs and results shared with workflows. The API adds HTTP-specific conversation and transcript views.

`ChatService` uses the conversation store interface for ownership checks, locking, request replay, history and transcript writes. Its PostgreSQL adapter records each request with its user message and each completed response with its assistant message. `TicketService` uses a separate ticket-attempt store for reservation and completion. It owns the decision to create a Jira issue or reconcile an uncertain submission. `bootstrap.py` connects both services to their adapters.

## RAG module boundaries

`rag/ingestion.py` owns indexing: `document_loader.py` reads reviewed Markdown, `chunking.py` produces passages, `embedding.py` creates dense/sparse vectors, and `qdrant_store.py` persists them. There is one ingestion implementation. It compares hashes, rejects incompatible index signatures, updates changed chunks, and removes stale chunks only after successful upserts. Ingestion does not load the reranker.

`rag/retrieval.py` owns query embedding, candidate search, optional reranking, score filtering, and final context selection. Qdrant-specific requests and native RRF fusion stay in `qdrant_store.py`. Cross-encoder model loading and ranking stay in `reranking.py`. Both embedding and reranking adapters load lazily. Retrieval concurrency remains bounded to two calls per pipeline instance.

`rag/query_pipeline.py` remains the standalone grounded-answer entry point and component bundle. The conversation graph delegates to specialised IT and HR agents, which use its retrieval, generation, and verification components as separate graph steps. RAG returns `AnswerResult` from `rag/rag_models.py` and does not import FastAPI schemas, Jira services, or conversation storage. `rag/rag_interfaces.py` declares component contracts so pipelines can run with alternative implementations or controlled test doubles. See [agents and evaluation](agents_and_evaluation.md) for agent/tool boundaries and LangSmith setup.

`rag/rag_factory.py` constructs concrete embedding, store, and reranking components for application startup, the CLI, and evaluation. Its returned component bundle owns the Qdrant client and must be closed by the caller. The shared OpenAI client remains in `infrastructure/llm/` because routing and conversation summarization also use it; answer and verifier prompts belong to `rag/answer_prompts/`.

Short entries stay intact. Long handbooks split at Markdown headings, with the heading path repeated for context and a 1,500-character passage budget. On the same leave handbook, paragraph-v1 produced 12 passages, two spanning multiple major sections. With section-v2, 26 content passages retain their section heading and one carries the introduction. None crosses major sections. A same-embedding paragraph-v1 index upgrades in one ingestion; section passages receive distinct IDs. An embedding change requires a new collection.

## Conversations

A conversation has an owner and UUID. Its UUID is also the LangGraph thread ID. The frontend sends that ID on every turn and reloads the transcript after reconnecting. The server checks ownership on every read and write. The browser's local storage contains only the conversation ID; it does not authorize access.

PostgreSQL stores conversation metadata, ordered messages, request deduplication records, and ticket attempts. LangGraph stores graph checkpoints separately. Recent messages are passed to the router; older messages are summarized when the recent window is exceeded. Verified email, draft contents/version, and approval remain structured fields. Full transcripts remain stored even when the prompt history is compacted.

The router resolves conversational references into standalone retrieval queries. Retrieval runs again for follow-ups. Previous assistant messages help identify the topic, but source passages must support the answer. Ambiguous references should produce a clarifying question.

## Grounding

Documents have stable IDs, provenance, versions, and access scope. Both retrieval branches apply the employee-scope filter. Dense and BM25 rankings are merged with RRF. A cross-encoder reranks candidates. Numeric score rejection is optional and disabled by default following development-set evidence that a zero cutoff rejected useful passages.

The answer model emits claims and supporting chunk IDs. The service rejects nonexistent IDs and sends the claims to a second evidence check. Citations are rendered from retrieved metadata. Unsupported answers become escalation offers. These checks reduce unsupported output but still require live evaluation and review; they do not prove zero hallucinations.

## Approval and external writes

Drafts are displayed with employee email, summary, description, category, and requested priority. Editing increments the draft version. Confirmation must match the pending version. A persisted interrupt supports page refresh and server restart. Asking a side question preserves the draft and returns to its approval pause.

A unique creation-attempt record is committed before contacting Jira. The correlation label is attached to the issue in the same create request. Explicit provider rejections can be retried; uncertain outcomes are reconciled by searching the label. If reconciliation finds no unique ticket, the service reports uncertainty and does not issue another create request. Jira status is always fetched live.

The ticket service looks up the verified employee label and directly reported issues associated with the employee's verified Jira account. Both listing and detail use the same ownership checks. See [operations](operations.md) for Jira permissions and email visibility requirements.

## Transport and concurrency

The chat endpoint streams progress/heartbeat events over HTTP and releases the verified answer as a final event. It does not stream unverified tokens. Ticket approvals use a normal POST. Disconnecting a stream does not undo work already committed; reload the conversation before retrying.

PostgreSQL advisory locks serialize updates to the same conversation across backend replicas. SQLite and its checkpointer are used only for isolated tests. Unique request IDs prevent replay of completed operations. An interrupted request ID is rejected with a recovery message; the user can reload persisted state and reconcile the pending ticket. Full automated recovery of every crash point is a remaining operational hardening item.

## Deployment boundary

Each application has its own Dockerfile, dependencies, lockfile, tests, and image tag. Nginx serves the frontend and proxies `/api` to the configured backend. Runtime config contains public UI configuration only. PostgreSQL and Qdrant use persistent storage outside the application images. Compose binds the demo application to loopback. AWS hosting is deferred.
