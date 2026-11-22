# Knowledge base

This corpus describes **NovaTech**, a fictional company. It contains 32 HR entries curated from `strova-ai/hr-policies-qa-dataset`, eight fictional handbook documents covering leave, payroll, reimbursement, onboarding, performance reviews and harassment reporting, and 32 synthetic IT documents. Source policies are not statements about an actual employer or legal advice.

Each indexed Markdown document has YAML front matter: ID, title, domain, source, version, effective date, access scope, synthetic flag, and review status. Only `reviewed` or `reviewed-fictional` records are eligible for ingestion. Original HR files are downloaded to ignored `raw/`; the manifest preserves the exact revision and checksum.

HR and IT filenames describe their topics. Imported HR documents retain dataset-row IDs in their metadata (for example, `hr-company-assets-usage.md` has ID `hr-609`) so citations, evaluation labels, and indexed chunk IDs remain stable. `HR_FILENAMES` in `backend/scripts/prepare_corpus.py` preserves these descriptive filenames when regenerating the curated corpus.

The intended omissions are monitor hardware/flickering and office parking. Do not add answers for those topics without also updating the unanswerable evaluation cases.

Run the importer to reproduce the curated HR documents. Run `smartdesk validate-kb` before `smartdesk ingest`. Ingestion upserts changes and removes stale chunks in the configured collection; use a new collection for a changed embedding model or chunker.
