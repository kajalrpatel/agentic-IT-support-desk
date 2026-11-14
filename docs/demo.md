# Demo walkthrough

Use the real application after configuring the LLM, Jira, and index. Browser tests use deterministic provider doubles and must not be presented as evidence of live integrations.

1. Ask “How do I set up the company VPN?” Expand a source citation.
2. Follow up with “Does it work on Mac?” Confirm that the answer discusses VPN support and cites the guide.
3. Ask “My monitor has been flickering for two days. What should I replace?” The missing procedure should lead to an escalation offer.
4. Ask to prepare a ticket. Inspect email, summary, description, category, and priority. Edit the description and save it. Confirm that the new draft requires approval.
5. Confirm submission. Show the actual Jira ID/link and open the issue in the dedicated test project.
6. Ask for ticket status. Demonstrate a single ticket and multiple-ticket selection; use a separate fictional identity with no matching tickets for the empty case.
7. Refresh the page during a pending approval. Confirm that history and the draft return.
8. Show the evaluation report, architecture, source manifest, and passing test output. Clearly identify any live checks not yet completed.

For screenshots, use the desktop welcome, expanded source, ticket preview, and real ticket result screens. Avoid showing API tokens or private employee data.
