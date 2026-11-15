# Operations

## Local configuration and identity

Use `.env.example` as the configuration reference. `.env` is ignored. `AUTH_MODE=demo` is for a loopback-only fictional-user demo. It issues an eight-hour development token for `DEMO_EMAIL`; it is not employee authentication. `ENVIRONMENT=production` rejects demo authentication.

For a shared deployment configure `AUTH_MODE=oidc`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL`, and configure the frontend's OIDC authority/client ID. The identity provider must issue RS256 access tokens containing `sub`, `email`, and boolean `email_verified=true` for the backend audience. Register the exact `/auth/callback` URL. The frontend uses Authorization Code with PKCE. Validate your provider's claims and audience with a real login before deployment. Add provider-specific scopes/audience parameters if required; do not assume every provider's default access token contains email.

The local Compose application uses a single fictional organization and an employee-only KB scope. It does not implement arbitrary per-team or per-document ACLs. Do not ingest restricted HR case files into the employee-visible collection.

## Jira

Configure base URL, account email, API token, project key, and issue type. The service account needs create, browse, search, and comment-read permissions in the dedicated test project. Issue types with additional mandatory fields require adapter configuration. Requested priority is recorded in the issue description; mapping it to a Jira priority ID is intentionally project-specific.

SmartDesk issues include `smartdesk`, category, employee-hash, and request-correlation labels. Keep those labels intact. Existing Jira issues become discoverable only when deliberately assigned the appropriate employee label. Restricted/internal comments are excluded. Use appropriate project permissions for HR tickets before any real use.

When a create call has an unknown outcome, retry confirmation to reconcile the correlation label. If reconciliation remains empty, an administrator must inspect Jira before resolving the attempt. Never delete the attempt and blindly submit again. A ticket accepted by Jira but missing from search briefly may need time to become searchable.

## Database and index changes

Run `docker compose run --rm migrate` for application and LangGraph checkpoint migrations. Run one migration job before rolling out application replicas. Back up PostgreSQL and Qdrant before changing schemas or indexes. The initial migration establishes application tables; add a new Alembic revision for later schema changes.

Ingestion is an administrative job: `docker compose exec backend smartdesk ingest`. It validates the entire corpus, skips unchanged chunks, upserts changes, and removes stale chunks from the configured collection. Avoid running simultaneous ingestion jobs. For embedding/chunker changes, use a new collection, ingest it, verify retrieval, then point the backend at the new collection and restart. Retain the previous collection for rollback.

## Backup and recovery

Use PostgreSQL `pg_dump` with a custom-format backup and restore into a separate database with `pg_restore`; confirm the transcript, approval checkpoints, and ticket attempt tables are all included. Store backups outside the container volume. Test restoration before shared use. Use Qdrant collection snapshots or reproduce the index from the versioned corpus, pinned models, and manifest. Retain the same model/chunker configuration when rebuilding.

For application rollback, deploy the prior frontend/backend image tags and compatible database/index configuration. Do not automatically run destructive database downgrades. Independent release compatibility is checked with the exported OpenAPI contract and browser tests.

## Observability and limits

OpenAI failures are classified without logging provider bodies or key fragments. A project spending-limit error requires the project administrator to review the applicable spend controls; repeated requests do not restore access. All model-service failures return the same friendly user message without provider, budget, quota, or configuration details. Quota/billing exhaustion, request rate limiting, credential/model access errors, and temporary provider failures remain distinct categories in backend logs. Inspect the safe `model_call_failed` log category when diagnosing a failure. Existing chat messages retain their original text; the updated error message appears on new requests.

Request logs contain generated request IDs, status, and latency without request bodies or credentials. Model logs include model name, token counts, and duration. FastAPI has OpenTelemetry instrumentation; an SDK/exporter must be configured for external trace collection. No telemetry backend has been deployed.

Per-user chat rate limiting is enforced against persisted request timestamps. API and model timeouts, bounded safe-call retries, and output limits are configured. Nginx limits request size. CPU model inference is bounded to a small thread count; profile concurrent requests before increasing replicas or moving inference to a separate service. Health readiness checks database access; it is not proof that the paid LLM, Jira permissions, and index are ready.

Before AWS hosting, review TLS, OIDC claims, access controls, secrets storage, backup/restore, retention/deletion policy, cost limits, logs, and a representative load test. No real employee data or public deployment is part of the local verification.
