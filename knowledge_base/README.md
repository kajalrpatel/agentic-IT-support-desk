# Knowledge base

This corpus describes **NovaTech**, a fictional company. HR entries are curated from `strova-ai/hr-policies-qa-dataset`; IT documents are synthetic. Source policies are not statements about an actual employer or legal advice.

Each indexed Markdown document has YAML front matter: ID, title, domain, source, version, effective date, access scope, synthetic flag, and review status. Only `reviewed` or `reviewed-fictional` records are eligible for ingestion. Original HR files are downloaded to ignored `raw/`; the manifest preserves the exact revision and checksum.

The intended omissions are monitor hardware/flickering and office parking. Do not add answers for those topics without also updating the unanswerable evaluation cases.

Run the importer to reproduce the curated HR documents. Run `smartdesk validate-kb` before `smartdesk ingest`. Ingestion upserts changes and removes stale chunks in the configured collection; use a new collection for a changed embedding model or chunker.
