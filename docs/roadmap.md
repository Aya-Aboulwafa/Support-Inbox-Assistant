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

---

## 📊 Feature Prioritization Matrix

| Feature | Complexity | Business Impact | Target Phase |
| :--- | :---: | :---: | :---: |
| **PostgreSQL & Database Persistence** | Medium | High | Phase 1 |
| **PII Data Sanitization Guardrail** | Low | Critical | Phase 1 |
| **Knowledge Base RAG Integration** | Medium | High | Phase 2 |
| **WebSockets Real-Time Queue Updates** | Low | Medium | Phase 2 |
| **Omnichannel Email / Slack Webhooks** | Medium | High | Phase 2 |
| **Multi-Model Cascading Routing** | Medium | High | Phase 3 |
| **Langfuse LLM Distributed Tracing** | Low | High | Phase 3 |
| **LoRA Domain Fine-Tuning Pipeline** | High | High | Phase 3 |
