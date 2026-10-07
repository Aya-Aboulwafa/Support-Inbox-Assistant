# 🔌 REST API Specification & Integration Guide

## 1. Overview

The Support Inbox Assistant backend exposes a high-performance RESTful API powered by **FastAPI**. It includes asynchronous lifespan management, automatic OpenAPI/Swagger documentation generation, and native CORS support for frontend consumption.

- **Interactive API Documentation:** `http://localhost:8000/docs`
- **OpenAPI JSON Schema:** `http://localhost:8000/openapi.json`
- **Base Prefix:** `/api/v1`

---

## 2. Endpoints

### 2.1 Service Health Check

Checks system availability and service version.

- **Route:** `GET /api/v1/health`
- **Response Code:** `200 OK`
- **Response Payload:**
  ```json
  {
    "status": "healthy",
    "version": "0.1.0"
  }
  ```

---

### 2.2 Root Service Information

Provides metadata regarding the active service deployment.

- **Route:** `GET /`
- **Response Code:** `200 OK`
- **Response Payload:**
  ```json
  {
    "app": "Support Inbox Assistant",
    "status": "online",
    "docs_url": "/docs"
  }
  ```

---

### 2.3 Ticket Triage Processing

Accepts an incoming customer support ticket, executes pre-filtering, triggers the LLM classification pipeline, and returns the structured triage analysis.

- **Route:** `POST /api/v1/triage`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "id": "tick_1029",
    "subject": "Charged twice on renewal invoice #INV-492",
    "body": "Hi team, I noticed my credit card was charged twice yesterday for my Pro annual renewal. Please issue a refund for the duplicate charge as soon as possible.",
    "sender": "sarah.connor@example.com"
  }
  ```

- **Successful Response:** `200 OK`
  ```json
  {
    "ticket_id": "tick_1029",
    "category": "billing",
    "priority": "high",
    "summary": "Customer charged twice for Pro annual renewal invoice #INV-492 requesting refund.",
    "suggested_reply": "Hi Sarah,\n\nThank you for bringing this to our attention. I have reviewed invoice #INV-492 and confirmed the duplicate charge. We have initiated a refund for the duplicate transaction, which will appear on your statement within 3-5 business days.\n\nPlease let us know if you have any questions.\n\nBest regards,\nCustomer Support Team",
    "suggested_tags": ["billing", "duplicate-charge", "refund"],
    "confidence": 0.95,
    "escalate": false
  }
  ```

- **Defensive Escalation Response (Ambiguous or Security Ticket):** `200 OK`
  ```json
  {
    "ticket_id": "tick_9941",
    "category": "security",
    "priority": "urgent",
    "summary": "Potential unauthorized access notification from unknown IP.",
    "suggested_reply": "Hello,\n\nWe have escalated your inquiry to our Information Security team for immediate investigation. A security specialist will contact you shortly.",
    "suggested_tags": ["security", "account-compromise"],
    "confidence": 0.35,
    "escalate": true
  }
  ```

- **Error Response:** `500 Internal Server Error`
  ```json
  {
    "detail": "Triage error: Connection refused to Ollama endpoint at http://localhost:11434/v1"
  }
  ```

---

## 3. Error Handling & Sentry Telemetry

1. **Structured Exception Logging:** All unexpected exceptions caught inside the API layer are logged via `src/core/logging.py` with full exception context.
2. **Sentry Error Tracking:** If `SENTRY_DSN` is configured in the environment:
   - All uncaught HTTP 500 exceptions are automatically forwarded to Sentry with call stack traces and environment tags.
   - Traces sample rate is governed dynamically based on the `DEBUG` environment flag (`1.0` during development, `0.1` in production).
