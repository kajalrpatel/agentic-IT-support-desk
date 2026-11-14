## 1. Project Overview

Welcome to your capstone project. Over the course of this program, you have learned how to build agents using a variety of frameworks, how to ground them with retrieval-augmented generation (RAG), how to orchestrate multi-agent workflows, and how to evaluate your systems. This project is your opportunity to pull all of those skills together into a single, end-to-end application.

You will build SmartDesk AI — an intelligent agent that serves as a first-line IT and HR help desk for an organisation. The agent must be able to answer common employee questions from a curated knowledge base, gracefully handle questions it cannot answer by creating support tickets on an external platform, and allow employees to check the status of tickets they have previously raised.

### 1.1 The Business Problem

In most organisations, IT and HR support teams are overwhelmed with repetitive queries: password resets, leave policies, VPN setup, reimbursement processes, onboarding checklists, and similar topics. A large fraction of these questions have well-documented answers that can be found in internal wikis, policy documents, or FAQ pages. Yet employees continue to raise tickets and wait for human agents because finding the right document is often harder than asking someone.

SmartDesk AI addresses this by placing an intelligent conversational agent between the employee and the support team. The agent tries to resolve the query from a knowledge base first. Only when it is genuinely unsure does it escalate by creating a ticket — and even then, it captures enough context so that the human agent who picks up the ticket does not have to ask the same questions again.

### 1.2 High-Level Architecture (Conceptual)

At the highest level, the system has three major capabilities. Think of them as three branches of decision-making that the agent must navigate:

Knowledge-Base Query (RAG): The employee asks a question. The agent searches a vector store (or hybrid search index) built from company IT and HR documents. If a confident answer is found, the agent responds directly.

Ticket Creation (Write Operation): If the agent cannot answer the question, it offers to create a support ticket on a project-management tool such as Jira, Asana, or Notion. Before creating the ticket, it must collect the employee’s email address (or another unique identifier) to link the ticket to the right person.

Ticket Status Check (Read Operation): An employee can ask “What is the status of my ticket?” The agent retrieves the current status from the external platform and reports back.

Important: You are not restricted to any specific framework, LLM provider, vector database, or project-management tool. The architecture described above is a logical requirement. How you implement it — whether with LangGraph, LangChain, Google ADK, CrewAI, AutoGen, raw function calling, or your own orchestration code — is entirely your decision.

## 2. Detailed Functional Requirements

### 2.1 Knowledge Base (RAG Pipeline)

#### 2.1.1 Data Preparation

You must prepare a realistic knowledge base that covers both IT and HR topics for a fictional (or real, anonymised) company. The knowledge base should contain at least 30–50 question–answer pairs or document chunks that span the categories listed below. You are encouraged to add more.

| Domain | Example Topics | Example Questions |
| --- | --- | --- |
| IT Support | Password reset process<br>VPN configuration<br>Software installation requests<br>MFA setup<br>Guest Wi-Fi access<br>Email configuration on mobile | "How do I reset my password?"<br>"How do I connect to the VPN?"<br>"How do I request a software licence?" |
| HR Policies | Leave policy (casual, sick, earned)<br>WFH guidelines<br>Reimbursement process<br>Code of conduct<br>Anti-harassment policy<br>Performance review cycle | "How many sick leaves per year?"<br>"What is the WFH policy?"<br>"How do I submit a reimbursement?" |
| Onboarding | Day-one checklist<br>IT equipment allocation<br>Benefits enrollment<br>Buddy programme<br>Probation period | "What do I do on my first day?"<br>"When do I get my laptop?"<br>"How do I enrol in insurance?" |
| Payroll & Comp | Pay-day schedule<br>Tax declaration process<br>Salary structure<br>Stock-option vesting | "When is payday?"<br>"How do I submit my tax declaration?"<br>"How does vesting work?" |

#### 2.1.2 Indexing & Retrieval

You must build an indexing pipeline that ingests the documents and makes them searchable. Your pipeline must include at least one of the following retrieval strategies (using more than one carries bonus marks):

- Dense vector search (e.g., embeddings from OpenAI, Cohere, HuggingFace, or Google, stored in FAISS, Pinecone, Qdrant, Weaviate, ChromaDB, or similar).

- Sparse keyword search (e.g., BM25 via Elasticsearch, Whoosh, or similar).

- Hybrid search that combines dense and sparse retrieval with a re-ranker.

Regardless of strategy, you must demonstrate that the retrieval pipeline returns relevant chunks for a given query, and that the LLM uses these chunks to generate a grounded answer. The agent must not hallucinate answers that are not present in the knowledge base.

#### 2.1.3 Confidence Handling & Escalation Logic

This is a critical design decision. Your agent must be able to determine when it does not know the answer. There is no single correct way to do this. Below are some approaches you might consider (you may use any other method):

- Retrieval-score threshold: If the top retrieved chunk has a similarity score below a certain threshold, treat the query as unanswerable.

- LLM self-assessment: Instruct the LLM via its system prompt to explicitly say “I don’t have enough information” when the retrieved context is insufficient.

- No-retrieval fallback: If zero chunks are returned, default to escalation.

- A combination of the above with a human-in-the-loop confirmation before escalating.

When the agent determines it cannot answer, it must transition to the Ticket Creation flow described in Section 2.2.

### 2.2 Ticket Creation (Write Operation)

When the agent cannot resolve a query from the knowledge base, it must offer to create a support ticket on an external project-management platform. You may choose any one of the following (or a comparable tool):

- Jira (Atlassian) — via REST API or Python/Node SDK.

- Asana — via REST API or official SDK.

- Notion — via the Notion API (database item creation).

- Linear, Trello, ClickUp, GitHub Issues, or any other ticketing system with a public API.

#### 2.2.1 Information Gathering Before Ticket Creation

Before the agent creates a ticket, it must collect at minimum the following:

| Field | Description | Mandatory? |
| --- | --- | --- |
| Employee Email | A unique identifier to link the ticket to the employee. The agent should ask for this explicitly if not already known. | Yes |
| Issue Summary | A short, one-line title for the ticket (e.g., "Unable to connect to VPN from home"). | Yes |
| Issue Description | A detailed description. The agent should summarise the conversation so far. The employee should be able to add more details. | Yes |
| Category / Label | Whether the issue falls under IT or HR. The agent should infer this from the conversation. | Recommended |
| Priority | Low, Medium, High, or Critical. The agent may infer this or ask the employee. | Optional |

#### 2.2.2 Human-in-the-Loop Confirmation

Before submitting the ticket, the agent must present a summary to the employee and ask for explicit confirmation. For example: “Here is the ticket I will create for you: [summary]. Shall I go ahead?” This is a mandatory requirement — the agent must not create tickets silently.

#### 2.2.3 Post-Creation Feedback

After the ticket is successfully created, the agent must confirm this to the employee and provide the ticket ID or a link so that the employee can track it independently.

### 2.3 Ticket Status Check (Read Operation)

An employee must be able to ask the agent about the status of a previously raised ticket. The flow is:

- The employee asks something like “What is the status of my ticket?” or “Did anyone look at my VPN issue?”

- The agent asks for the employee’s email address (if not already known in the current session) to look up their tickets.

- The agent queries the external platform (Jira / Asana / Notion) using the API to fetch tickets associated with that email.

- The agent presents the status (e.g., Open, In Progress, Resolved, Closed) along with any comments or updates from the support team.

If the employee has multiple open tickets, the agent should list them briefly and let the employee choose which one they want details on. If no tickets are found, the agent should say so clearly.

## 3. Data for Your Knowledge Base

Why this section matters: One of the most common challenges learners face in capstone projects is figuring out where to get realistic data. This section gives you three clear paths so you can move quickly.

### 3.1 Option A — Ready-Made Datasets (Hugging Face & Kaggle)

Several publicly available datasets contain HR policy Q&A pairs, IT support ticket data, and helpdesk conversation logs. Below are curated starting points.

**Hugging Face — HR Policy Datasets**

Search: https://huggingface.co/datasets?sort=trending&search=hr+pol

| Dataset | Rows | What It Contains |
| --- | --- | --- |
| strova-ai/hr-policies-qa-dataset | ~644 | HR policy Q&A pairs covering leave, conduct, benefits. Excellent starting point for the HR half of your KB. |
| EmbraceCoder/HR_Policy | ~123 | Concise HR policy snippets. Can be used directly as document chunks for RAG. |
| EmbraceCoder/New_Hr_Policy | ~98 | Updated version with additional policy areas. |
| SaumyaGupta/hr-policies-qa-dataset | ~644 | Q&A format HR dataset, suitable for both retrieval and evaluation. |

**Hugging Face — IT Support / Ticket Datasets**

Search: https://huggingface.co/datasets?sort=trending&search=it+tick

| Dataset | Rows | What It Contains |
| --- | --- | --- |
| Console-AI/IT-helpdesk-synthetic-tickets | ~500 | Synthetic IT helpdesk tickets with categories, priorities, and resolutions. |
| KameronB/synthetic-it-callcenter-tickets | ~27.6K | Large-scale synthetic IT call-centre tickets. Pick a subset and rewrite into Q&A format. |
| parth1609/IT_ticket_dataset | ~29.7K | IT ticket dataset with descriptions and categories. |
| interneuronai/it_support_ticket_classification_pegasus_dataset | ~3K | IT support tickets classified by type. Good for routing logic. |
| w1z4rd3k/it-support-l1-ticket-classification | ~480 | L1 IT support tickets with classification labels. |

**Kaggle Datasets**

| Dataset Name | URL |
| --- | --- |
| Customer Support Ticket Dataset | kaggle.com/datasets/suraj520/customer-support-ticket-dataset |
| IT Service Ticket Classification Dataset | kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset |
| Multilingual Customer Support Tickets | kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets |
| Support Ticket Priority Dataset (50K) | kaggle.com/datasets/albertobircoci/support-ticket-priority-dataset-50k |

Tip: You do not need to use these datasets as-is. Download, review the columns, then reshape the data into a format that fits your RAG pipeline (Markdown, JSON Q&A pairs, or CSV). Add your fictional company name, adapt the policies, and you’ll have a realistic knowledge base.

### 3.2 Option B — Generate Synthetic Data with AI Tools

If you want a knowledge base tailored to a fictional organisation, use an LLM (ChatGPT, Claude, Gemini, or any model) to generate synthetic HR and IT policy documents. This gives you full control over content and lets you design edge cases.

Step-by-Step Guide

- Define your fictional company. Give it a name, industry, size, and location. Example: “NovaTech Solutions, a 500-employee SaaS company in Bengaluru, India.”

- List policy categories. Use Section 2.1.1’s table as a starting point. For each category, write 3–5 sub-topics.

**Prompt the LLM to generate full policy documents. Example prompt:**

"You are an HR manager at NovaTech Solutions, a 500-employee SaaS

- company. Write a detailed Leave Policy document covering: casual leave

- (12 days/year), sick leave (8 days/year), earned leave (15 days/year),

- maternity leave (26 weeks), paternity leave (2 weeks), and compensatory

- off. Include eligibility, approval process, carry-forward rules, and

- encashment rules. Write in a professional tone for an employee handbook."

- Generate Q&A pairs from the documents. Prompt the LLM again:
- "Based on the Leave Policy above, generate 15 realistic employee
questions and answers. Include simple questions (‘How many casual leaves
do I get?’) and complex ones (‘Can I carry forward unused sick leaves
and encash them?’). Output as JSON: {question, answer, category}."

- Repeat for IT support topics. Example: “You are the IT Admin at NovaTech. Write an internal guide on VPN setup for remote employees, covering supported clients, step-by-step installation for Windows/Mac/Linux, common errors, and escalation contacts.”
- Include “unanswerable” scenarios. Deliberately leave some topics out (e.g., monitor flickering, office parking) so the agent correctly triggers escalation. This tests your confidence logic.
- Save in a structured format. Store as Markdown files (one per policy area), a JSON array, or CSV. Include in your repository.
### 3.3 Option C — Combine Both (Recommended)

The best knowledge bases combine real-world datasets with synthetic content. Download strova-ai/hr-policies-qa-dataset for a solid HR foundation, then use an LLM to generate IT support guides and troubleshooting documents. This gives you breadth (many topics) and depth (detailed documents for key areas).

### 3.4 What Makes a Good Knowledge Base?

Regardless of which option you choose, your KB will be evaluated on:

- Coverage: Does it span both IT and HR domains with at least 30–50 meaningful entries?

- Realism: Do the policies read like something a real company would have? (Generic copy-paste scores lower.)

- Diversity: Does it include simple factual, procedural how-to, and policy-interpretation questions?

- Deliberate gaps: Are there topics intentionally left out so that your escalation logic is testable?

- Structure: Is the data cleanly formatted and easy to ingest?

Remember: The quality of your knowledge base directly affects the quality of your RAG pipeline. Garbage in, garbage out. Invest time here — it is the foundation of your entire project.

## 4. Non-Functional Requirements

### 4.1 Conversation Quality

- The agent must maintain a polite, professional, and empathetic tone throughout.

The agent must handle greetings, small talk, and out-of-scope questions gracefully.

- The agent must not hallucinate. If the KB does not contain the answer, the agent must acknowledge it.

### 4.2 Session & Context Management

- The agent should remember context within a single session (e.g., do not re-ask for email).

- Multi-turn conversations must flow naturally without losing track of the topic.

### 4.3 Error Handling

If the external API is unreachable, the agent must inform the employee politely and suggest trying again later.

- If the LLM API call fails, the agent should have a retry mechanism or a graceful fallback.

- All API keys and secrets must be stored in environment variables — never hard-coded.

### 4.4 Code Quality & Documentation

- Well-structured, modular, readable code with meaningful names.

README.md with setup instructions, env var list, and run commands.

Architecture diagram (hand-drawn, Mermaid, draw.io, or any format) showing components and data flow.

## 5. Guiding Steps (Suggested, Not Mandatory)

- Disclaimer: The steps below are suggestions. You are free to use any approach, framework, or structure. You will not be penalised for deviating from these steps as long as your system meets the requirements in Sections 2–4.

- Set up your project environment. Create a repo, set up a virtual environment or Node.js project, install your chosen framework, and configure API keys as environment variables.

- Gather and prepare the knowledge base. Follow Section 3. Download datasets from Hugging Face or Kaggle, generate synthetic data with an LLM, or combine both. Aim for at least 30–50 entries across IT and HR.

- Build the indexing pipeline. Choose your embedding model and vector store. Write a script that reads documents, generates embeddings, and upserts them. Verify by running sample queries.

- Build the RAG chain. Wire the retriever to an LLM. Write a system prompt that instructs the LLM to answer only from context and to say “I don’t know” when context is insufficient.

- Add escalation logic. Decide how the agent detects unanswerable queries. Implement the transition to ticket creation — a conditional edge, tool call, or simple if-else.

- Implement ticket creation. Integrate with your chosen platform’s API. Write a function/tool that accepts required fields and creates a ticket. Test independently.

- Implement ticket status retrieval. Write a function/tool that takes an email and returns associated tickets. Test independently.

- Orchestrate the full agent. Connect all three capabilities into a single agent loop. Ensure correct routing based on intent. Frameworks like LangGraph or ADK help here, but a simple state machine works too.

- Add human-in-the-loop. Confirm with the employee before creating a ticket. Ask for email when needed.

- Test end-to-end. Run complete scenarios: KB answer, ticket creation, and status check. Record examples in your README.

- Evaluate (optional, bonus marks). Use LangSmith, Ragas, or DeepEval to run an evaluation suite with metrics like answer relevance, faithfulness, and latency.

Write documentation. README.md, architecture diagram, and a short demo video (optional). Ensure someone can clone and run with minimal friction.

## 6. Marking Scheme (Total: 100 Marks)

Your submission will be evaluated across six categories. Each has specific sub-criteria.

| # | Evaluation Category | Marks | Sub-Criteria (marks breakdown) |
| --- | --- | --- | --- |
| A | Knowledge Base & RAG Pipeline | 25 | Quality and breadth of KB content (5)<br>Chunking strategy and justification (5)<br>Retrieval quality — relevant results for test queries (5)<br>LLM grounding — no hallucination (5)<br>Confidence / escalation logic (5) |
| B | Ticket Creation (Write Operation) | 20 | Successful external API integration (5)<br>All mandatory fields collected (5)<br>Human-in-the-loop confirmation (5)<br>Post-creation feedback with ticket ID/link (5) |
| C | Ticket Status Check (Read Operation) | 15 | Status retrieval via API (5)<br>Multiple-ticket handling (listing & selection) (5)<br>Graceful handling when no tickets found (5) |
| D | Agent Orchestration & Routing | 15 | Correct intent detection and routing (5)<br>Smooth multi-turn conversations (5)<br>Out-of-scope / ambiguous query handling (5) |
| E | Code Quality & Documentation | 15 | Clean, modular, readable code (5)<br>README with setup instructions (5)<br>Architecture diagram (5) |
| F | Error Handling & Robustness | 10 | Graceful API failure degradation (3)<br>Retry logic / LLM fallback (3)<br>No hard-coded secrets (2)<br>Edge-case handling (2) |

### 6.1 Bonus Marks (Up to +10)

You can earn up to 10 bonus marks (total capped at 100) for going above and beyond:

- Hybrid search (dense + sparse + re-ranker) with demonstrable improvement.

- Multi-agent architecture with specialised IT and HR sub-agents.

- Evaluation pipeline (LangSmith, Ragas, DeepEval) with quantitative metrics.

- User-facing deployment (Streamlit, Gradio, Chainlit, or web app).

- Caching (semantic cache, Redis, or LLM cache) for repeated queries.

- Advanced memory (long-term, cross-session memory via database or memory framework).

Note: Bonus marks will not push your total above 100. They serve as a cushion if you lose marks elsewhere, or as a differentiator for top-performing submissions.

## 7. Submission Deliverables

| # | Deliverable | Details |
| --- | --- | --- |
| 1 | GitHub Repository | Public or private repo (add evaluator as collaborator). Must include all source code, KB files, and configuration. |
| 2 | README.md | Setup instructions, env var list, how to populate the KB, how to run the agent, and a brief description of your approach. |
| 3 | Architecture Diagram | Visual diagram (image or Mermaid in README) showing components and data flow. |
| 4 | Demo Video / Screenshots | 3–5 min screen recording or annotated screenshots showing all three flows: RAG answer, ticket creation, ticket status. |
| 5 | Knowledge Base Files | Raw documents / Q&A pairs / JSON / CSV used as your knowledge base. Must be included in the repo. |

## 8. Sample Conversation Flows

The following are illustrative flows. Your agent’s exact wording will differ, and that is perfectly fine.

### 8.1 Flow A — Query Answered from Knowledge Base

Employee: Hi, how do I reset my password?

Agent: Hello! To reset your password, please visit the Self-Service Password Portal at https://passwords.company.com. Click “Forgot Password”, enter your employee ID, and follow the instructions sent to your registered email. If you’re locked out, contact IT at ext. 2020. Anything else?

Employee: No, thanks!

Agent: You’re welcome! Have a great day.

### 8.2 Flow B — Query Escalated to Ticket Creation

Employee: My monitor has been flickering for two days.

Agent: I’m sorry to hear that. I don’t have a troubleshooting guide for this. I can create a support ticket for IT. Could you share your email?

Employee: Sure, jane.doe@company.com.

Agent: Thanks, Jane. Here’s the ticket summary:

• Title: Monitor Flickering Issue

• Description: Employee reports monitor flickering for the past two days.

• Category: IT Support

• Email: jane.doe@company.com

Agent: Shall I go ahead and create this?

Employee: Yes, please.

Agent: Done! Ticket IT-2847 has been created. Track it on Jira or ask me for updates anytime.

### 8.3 Flow C — Ticket Status Check

Employee: Any updates on my monitor ticket?

Agent: Sure! Could you share your email?

Employee: jane.doe@company.com

Agent: I found one open ticket:

• Ticket IT-2847: Monitor Flickering — Status: In Progress

• IT Team update: “Replacement monitor ordered, delivery by Thursday.”

Agent: Anything else?

## 9. Technology Stack — Your Choice

You are free to use any technology stack. The table below is illustrative, not exhaustive.

| Component | Options (Illustrative) |
| --- | --- |
| Agent Framework | LangGraph, LangChain, Google ADK, CrewAI, AutoGen, Semantic Kernel, raw function-calling, or custom code. |
| LLM Provider | OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini), Groq, Together AI, Ollama (local), or any chat-completions API. |
| Embedding Model | OpenAI text-embedding-3-small/large, Cohere embed-v3, Google text-embedding-004, HuggingFace sentence-transformers. |
| Vector Database | FAISS, ChromaDB, Pinecone, Qdrant, Weaviate, Milvus, pgvector, or any vector-capable store. |
| Ticketing Platform | Jira, Asana, Notion, Linear, Trello, ClickUp, GitHub Issues, or any tool with a public API. |
| Evaluation | LangSmith, Ragas, DeepEval, custom scripts, or manual testing. |
| UI (Optional) | Streamlit, Gradio, Chainlit, FastAPI + HTML, Flask, or CLI-based interaction. |
