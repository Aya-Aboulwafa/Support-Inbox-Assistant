# 🚀 Future Improvements & System Roadmap

This document outlines architectural enhancements, engineering features, and operational improvements planned for the **Support Inbox Assistant** to scale from an automated triage assistant to an enterprise-grade customer support platform.

---

## 🗺️ Roadmap Overview

```text
Phase 1: Resilience & Persistence  ──▶  Phase 2: RAG & Omnichannel  ──▶  Phase 3: Agentic Workflows & Observability
  • PostgreSQL / Vector DB Storage        • Knowledge Base RAG Search       • Multi-Model Cascading Routing
  • Automated PII Redaction               • Real-Time WebSockets SSE         • Fine-Tuning / LoRA Feedback Loop
  • Agent Collision Detection             • Slack & Gmail Ingestion Bot      • Distributed Tracing (Langfuse)
```

---

## 1. Data Layer & Production Persistence

### 1.1 Relational Database Migration (PostgreSQL / SQLite)
- **Current State:** The review queue currently uses an in-memory `TicketStore` seeded from `data/tickets.json`.
- **Planned Improvement:** 
  - Introduce an asynchronous ORM (SQLAlchemy 2.0 or SQLModel) backed by PostgreSQL.
  - Implement Alembic database migrations.
  - Retain ticket history, state transitions (`pending` ➔ `triaged` ➔ `approved`), and agent response modifications.

### 1.2 Agent Audit Trail & Interaction History
- Record the full modification log when human support agents edit AI-drafted replies:
  - Track original AI draft vs. agent's approved final message.
  - Measure Edit Distance (Levenshtein) to benchmark how frequently agent corrections occur per category.

---

## 2. Advanced AI & LLM Architecture

### 2.1 Knowledge-Base Retrieval-Augmented Generation (RAG)
- **Problem:** Small models (`llama3.2:3b`) lack awareness of company-specific refund windows, SLA policies, and technical API troubleshooting procedures.
- **Solution:**
  - Embed support documentation, knowledge base articles, and historical resolved tickets into a local vector store (ChromaDB / Qdrant / pgvector).
  - Inject top-$k$ relevant documentation chunks into the prompt context prior to draft generation.
  - Ground `suggested_reply` with source citations.

### 2.2 Cascading Multi-Model Triage Routing
- **Architecture:**
  - **Tier 1 (SLM - Local `llama3.2:3b`):** Rapid classification, sentiment scoring, and priority categorization within ~100–300ms.
  - **Tier 2 (Frontier LLM - Claude 3.5 Sonnet / GPT-4o):** Conditionally invoked only when `confidence < 0.70` or `escalate = True`, generating complex multi-step technical responses and code patches.

### 2.3 Automated PII & Sensitive Data Sanitization
- **Pre-Processing Guardrail:**
  - Scrub customer credit card numbers, authorization tokens, passwords, and sensitive PII before transmitting ticket context to LLM inference engines.
  - Utilize Microsoft Presidio or deterministic regex sanitizers to mask entities as `[REDACTED_CREDIT_CARD]`, `[REDACTED_API_KEY]`.

---

## 3. Human-in-the-Loop Review Queue & Frontend

### 3.1 Real-Time Streaming & WebSockets
- **Current State:** Frontend uses polling and manual refresh to synchronize with backend ticket updates.
- **Planned Improvement:**
  - Implement FastAPI WebSocket endpoints or Server-Sent Events (SSE) at `/api/v1/stream/queue`.
  - Push new tickets, triage progress, and approval notifications to connected browsers instantly.

### 3.2 Agent Collision Detection & Live Presence
- Prevent two support agents from reviewing or answering the same ticket simultaneously.
- Show active avatar indicators (e.g., *"Agent Sarah is reviewing this draft..."*) and acquire soft locks on open tickets.

### 3.3 1-Click Multi-Language Translation
- Detect the customer's language automatically and draft responses in the original language while displaying an English translation to the human agent.

---

## 4. Omnichannel Ingestion Integrations

### 4.1 Ingestion Connectors
- **Gmail / Google Workspace Webhook:** Ingest support emails directly via Google Pub/Sub push notifications.
- **Slack Connect Bot:** Forward internal team requests from support channels directly into the triage queue.
- **Ticketing Helpdesks:** Two-way synchronization with Linear, Jira Service Management, and Zendesk.

---

## 5. Continuous Evaluation & Telemetry

### 5.1 LLM Observability & Tracing (Langfuse / OpenTelemetry)
- Instrument end-to-end trace collection for every LLM completion:
  - Token consumption (prompt vs. completion).
  - Cost tracking per ticket.
  - P50, P90, and P99 latency percentiles across model versions.

### 5.2 Automated Continuous Benchmark Gate in CI
- Integrate `make eval` as a mandatory blocking quality gate in GitHub Actions.
- Ensure that prompt adjustments never degrade Category Accuracy below 85% or increase False Negative escalations on critical security tickets.

### 5.3 Active Learning & LoRA Fine-Tuning Pipeline
- Export agent-approved ticket responses as high-quality synthetic training datasets (`data/fine_tune_pairs.jsonl`).
- Fine-tune custom LoRA adapters on local SLMs (`llama3.2:3b` / `qwen2.5:3b`) tailored precisely to the company's brand voice and tone.

## 6. Post-Evaluation Analysis & Targeted Enhancements (Empirical Findings from `eval/results.json`)

Based on our empirical evaluation run against the 16 ground-truth tickets in `data/labels.json`, the baseline metrics were recorded in `eval/results.json`:

```text
• Category Accuracy   : 62.5% (10/16 correct, 6 misclassified)
• Priority Agreement  : 81.2% (13/16 matching)
• Macro F1 Score      : 0.4571
• Mean Latency        : 24,416.9ms (~24.4s per ticket)
```

The error analysis reveals **three primary boundary confusions** and one operational bottleneck:

### 6.1 Failure Mode Analysis & Specific Remedies

#### 1. Security vs. Bug Over-Triggering
- **Mismatched Tickets:**
  - `T-006` (*"URGENT: production down for our whole team"*) ➔ Predicted: `security` | Ground Truth: `bug`.
  - `T-019` (*"Webhook signature mismatch"*) ➔ Predicted: `security` | Ground Truth: `bug`.
- **Root Cause:** Urgent downtime outages and developer cryptographic keywords (*"signature mismatch"*, *"HMAC"*) tripped the security pre-filter and classification rules.
- **Targeted Enhancement:**
  - Refine prompt taxonomy: Explicitly clarify that API integration errors (webhook signatures, token format errors) and platform downtime are **`bug`**, reserving **`security`** strictly for active credential theft, IDOR/exploit reports, and unauthorized access.
  - Add explicit few-shot counter-examples for developer integration bugs.

#### 2. Billing vs. Account Subscription Boundary
- **Mismatched Ticket:**
  - `T-017` (*"Cancel my subscription"*) ➔ Predicted: `account` | Ground Truth: `billing`.
- **Root Cause:** The model treated subscription cancellation as account lifecycle management.
- **Targeted Enhancement:**
  - Add explicit disambiguation directive: Any inquiry regarding payment methods, plan tiers, cancellations, refunds, or invoices must classify as **`billing`**. **`account`** is strictly for authentication, passwords, and user profile management.

#### 3. Account vs. Feature Request Disambiguation
- **Mismatched Tickets:**
  - `T-013` (*"how do I add a teammate"*) ➔ Predicted: `feature_request` | Ground Truth: `account`.
  - `T-024` (*"SSO / SAML for 200 users"*) ➔ Predicted: `account` | Ground Truth: `feature_request`.
- **Root Cause:** Asking for workspace administration (*"add teammate"*) was misunderstood as requesting new functionality, whereas requesting an unsupported enterprise capability (*"SAML/SSO for 200 users"*) was classified as account setup.
- **Targeted Enhancement:**
  - Provide clear prompt guidance: Standard administration queries belong to **`account`**, while inquiries asking if the platform supports new protocols (SAML, SCIM, bulk imports) are **`feature_request`**.

#### 4. Legal & General Policy Inquiries
- **Mismatched Ticket:**
  - `T-007` (*"Question about your data policy"*) ➔ Predicted: `feature_request` | Ground Truth: `other`.
- **Targeted Enhancement:**
  - Explicitly document that legal, privacy, terms of service, and general vendor inquiries route to **`other`**.

---

### 6.2 Latency Reduction Architecture
- **Current Observation:** Mean inference latency reached ~24.4s per ticket due to remote network round-trips and generation overhead.
- **Planned Optimizations:**
  1. **Strict Generation Token Cap:** Reduce `llm_max_tokens` from 600 to 250 for triage predictions.
  2. **Prompt Optimization:** Condense prompt tokens by 35% without losing few-shot guardrails.
  3. **Local GPU Runtime:** Transition local development to native hardware-accelerated Ollama (CUDA/Metal) to achieve target latency `< 2,000ms`.

---

### 6.3 Target Performance Milestones

| Metric | Current Baseline | Target Milestone |
| :--- | :---: | :---: |
| **Category Classification Accuracy** | 62.5% | **≥ 87.5%** (14+/16) |
| **Priority Agreement** | 81.2% | **≥ 90.0%** (15+/16) |
| **Macro F1 Score** | 0.4571 | **≥ 0.8500** |
| **Average Response Latency** | ~24.4s | **< 2.5s** (local) |

---

## 📊 Feature Prioritization Matrix

| Feature | Complexity | Business Impact | Target Phase |
| :--- | :---: | :---: | :---: |
| **Prompt Few-Shot Calibration (Fix 6 Eval Mismatches)** | Low | High (Accuracy: 62% ➔ 87%+) | Immediate / Phase 1 |
| **PostgreSQL & Database Persistence** | Medium | High | Phase 1 |
| **PII Data Sanitization Guardrail** | Low | Critical | Phase 1 |
| **Knowledge Base RAG Integration** | Medium | High | Phase 2 |
| **WebSockets Real-Time Queue Updates** | Low | Medium | Phase 2 |
| **Omnichannel Email / Slack Webhooks** | Medium | High | Phase 2 |
| **Multi-Model Cascading Routing** | Medium | High | Phase 3 |
| **Langfuse LLM Distributed Tracing** | Low | High | Phase 3 |
| **LoRA Domain Fine-Tuning Pipeline** | High | High | Phase 3 |
