# Support Inbox Assistant - Frontend Architecture & API Integration Plan

## 1. Executive Summary & Design Overview

This directory contains the Human-in-the-Loop review queue interface for **Penta-Labs Support Copilot**. The application enables support agents to inspect, triage, reclassify, customize, approve, and escalate customer support tickets in real time.

### Visual & Aesthetic System
- **Theme**: Penta-Labs Eye-Comfort Muted Slate & Soft Paper Palette.
- **Canvas / Background**: `#E6EBF2` (soft muted slate-gray to eliminate screen glare).
- **Surface Cards**: `#F8FAFD` with crisp `#CBD5E1` borders.
- **Brand Accents**: Official Penta Lime (`#84CC16`) top bar rule, 5-dot geometric emblem, active state indicators, confidence gauges, and primary action buttons.
- **Typography**: Plus Jakarta Sans for UI elements and JetBrains Mono for ticket IDs, telemetry, and code tokens.

### Deployment & Serving Strategy
- **Turnkey Integration**: The frontend is mounted directly inside FastAPI (`src/main.py`) via `StaticFiles(directory="frontend", html=True)`.
- **Zero CORS / Single Port**: Accessing `http://localhost:8000/` immediately serves the review queue app without requiring a separate Node.js dev server or multi-port setup.

---

## 2. API Contract & Frontend Action Mapping

Every interactive control in the user interface is strictly bound to a verified backend endpoint:

| UI Component / Action | HTTP Method & Endpoint | Payload Sent | Backend Action / State Update | UI Reaction |
| :--- | :--- | :--- | :--- | :--- |
| **Initial Boot & Polling** | `GET /api/v1/health` | None | Verifies backend connectivity | Toggles top status badge to `FastAPI: Online (Live)` |
| **Queue Sidebar Load** | `GET /api/v1/tickets` | Query: `status`, `category`, `priority`, `limit=50`, `offset=0` | Fetches filtered `TicketRecord[]` from `TicketStore` | Renders ticket cards with urgency badges and confidence indicators |
| **Top Counter Badges** | `GET /api/v1/tickets/stats` | None | Returns count aggregates (`pending`, `urgent`, `approved`, etc.) | Updates `stat-total`, `stat-pending`, `stat-approved`, `stat-escalated` |
| **Ticket Selection** | `GET /api/v1/tickets/{id}` | Path param | Fetches single `TicketRecord` details | Populates detail card, message body, root cause, and response editor |
| **"Run AI Triage" Button** | `POST /api/v1/tickets/{id}/triage` | Empty body | Invokes `TriageService` with `llama3.2:3b` via Instructor | Disables button with spinner; updates root cause, category, confidence, and reply draft |
| **Editable Reply Draft** | `PATCH /api/v1/tickets/{id}` | `{ edited_reply: string, notes?: string }` | Persists edited draft and agent notes to ticket record | Displays "Saved" indicator, preserves draft during navigation |
| **Category Override Dropdown** | `PATCH /api/v1/tickets/{id}` | `{ category: TicketCategory }` | Updates classification in `TicketStore` | Updates card badge and recalculates stats |
| **Priority Override Dropdown** | `PATCH /api/v1/tickets/{id}` | `{ priority: TicketPriority }` | Updates priority in `TicketStore` | Re-sorts queue in real-time (urgent first) |
| **1-Click "Approve & Send"** | `POST /api/v1/tickets/{id}/approve` | `{ final_reply: string }` | Marks ticket as `approved`, sets `approved_at`, stores reply | Green success toast; ticket card moves to "Approved" tab |
| **"Escalate to Tier 2"** | `POST /api/v1/tickets/{id}/escalate` | `{ reason: string }` | Marks status as `escalated`, sets `escalate=True` and timestamp | Red pulse badge; ticket flagged for senior engineering triage |
| **"New Ticket" Ingest Modal** | `POST /api/v1/tickets` | `{ id, channel, sender, subject, body }` | Ingests new raw ticket into the active review queue | Inserts ticket at top of inbox with instant triage option |

---

## 3. Directory Structure & Deliverables

```text
frontend/
├── index.html          # Main HTML structure, Penta-Labs styles, and component markup
├── js/
│   └── api.js          # Centralized, typed API client module with timeout & retry handling
└── README.md           # This comprehensive architecture & integration plan document
```

### Module Responsibilities:
1. **`frontend/js/api.js`**:
   - Single point of truth for all backend communications.
   - Built-in `AbortController` timeouts (3s for health checks, 25s for LLM triage).
   - Structured JSON response parsing and normalized error bubbling.
2. **`frontend/index.html`**:
   - Semantic, glare-free layout with Left Sidebar (queue) and Right Panel (copilot workspace).
   - Ingest modal dialog for creating test/live tickets on demand.
   - Immediate feedback through non-intrusive toast alerts.
3. **`src/main.py`**:
   - Mounts `/` to `frontend/` using `StaticFiles`.
   - Leaves `/api/v1` intact for all REST endpoints and `/docs` for OpenAPI specs.

---

## 4. Sequence & Data Flow

```text
Browser User Action
       │
       ▼
frontend/index.html (DOM Event Listener)
       │
       ▼
frontend/js/api.js (Async Fetch Client)
       │
       ├──► HTTP Request with AbortController Timeout
       │
       ▼
FastAPI Backend (src/api/routes.py)
       │
       ├──► In-Memory TicketStore (src/services/store.py)
       └──► Ollama LLM Engine (src/services/triage.py) [when triaging]
       │
       ▼
HTTP JSON Response (200 / 201 / 4xx / 5xx)
       │
       ▼
frontend/js/api.js (Error Validation & JSON Parsing)
       │
       ▼
frontend/index.html (Reactive DOM Re-render & Toast Alert)
```

---

## 5. Risk Matrix & Failure Pre-Mortems

| Failure Mode | Likelihood | Impact | Mitigation / Fallback Strategy |
| :--- | :--- | :--- | :--- |
| **LLM Inference Latency** (3-8s) | High | Medium | UI shows spinning loader and disables button; background execution with 25s timeout; non-blocking to rest of queue. |
| **Backend Offline / Network Down** | Medium | Medium | Heartbeat probe (`GET /health`); UI gracefully displays "Offline Demo" indicator and preserves local edits in memory. |
| **Accidental Multi-Click** | Low | High | Action buttons (`Approve`, `Escalate`, `Triage`) are immediately disabled upon initial click until server responds. |
| **Invalid Form Inputs** | Low | Low | Client-side validation before dispatching `POST /tickets` or `PATCH` updates; backend Pydantic validation rejects invalid formats with 422. |

---

## 6. Verification & Test Gates

1. **Unit & API Integration Tests**:
   ```bash
   .venv/bin/pytest -q
   ```
2. **Turnkey Dev Run**:
   ```bash
   make run
   # Visit: http://localhost:8000/
   ```
3. **Endpoint Probing**:
   ```bash
   curl -s http://localhost:8000/api/v1/health | jq .
   curl -s http://localhost:8000/api/v1/tickets/stats | jq .
   ```
