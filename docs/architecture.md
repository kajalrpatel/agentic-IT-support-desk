# SmartDesk architecture

The repository contains two independently buildable applications. The backend is a modular monolith with FastAPI transport, LangGraph orchestration, application services, and adapters for OpenAI, Jira, Qdrant, and PostgreSQL. The React frontend uses the versioned API; it does not access provider credentials or databases.

```mermaid
flowchart LR
  Browser[React browser client] -->|HTTP + streamed events| API[FastAPI]
  API --> Auth[Demo identity or OIDC JWT validation]
  API --> Chat[Conversation service]
  Chat --> Graph[Persistent LangGraph workflow]
  Graph --> RAG[Dense + BM25 / RRF / cross-encoder]
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

An email-derived employee label enables lookup of tickets created or deliberately tagged for this application. It does not import all existing Jira tickets. Only a verified identity's label is used, and direct ticket IDs must pass ownership checks. Restricted Jira comments are excluded from the response.

## Transport and concurrency

The chat endpoint streams progress/heartbeat events over HTTP and releases the verified answer as a final event. It does not stream unverified tokens. Ticket approvals use a normal POST. Disconnecting a stream does not undo work already committed; reload the conversation before retrying.

PostgreSQL advisory locks serialize updates to the same conversation across backend replicas. SQLite and its checkpointer are used only for isolated tests. Unique request IDs prevent replay of completed operations. An interrupted request ID is rejected with a recovery message; the user can reload persisted state and reconcile the pending ticket. Full automated recovery of every crash point is a remaining operational hardening item.

## Deployment boundary

Each application has its own Dockerfile, dependencies, lockfile, tests, and image tag. Nginx serves the frontend and proxies `/api` to the configured backend. Runtime config contains public UI configuration only. PostgreSQL and Qdrant use persistent storage outside the application images. Compose binds the demo application to loopback. AWS hosting is deferred.
