# 🏛️ System Architecture Blueprint: Support Inbox Assistant

## 1. Executive Summary & Vision

The **Support Inbox Assistant** is an enterprise-grade, human-in-the-loop automated triage system engineered to optimize customer support workflows. Instead of blindly automating outbound customer responses—which introduces catastrophic hallucination and security risks—the system functions as an **Agentic Copilot for Support Teams**:

1. **Intakes** incoming tickets and emails asynchronously.
2. **Pre-filters & Enriches** deterministic patterns (e.g. VIP status, active incidents, explicit security triggers).
3. **Classifies & Scores** intent into strict categories and priority tiers using a lightweight local Small Language Model (SLM: `llama3.2:3b`).
4. **Calibrates Confidence**: Calculates a normalized confidence score $[0.0, 1.0]$ and sets defensive escalation flags (`escalate: true`).
5. **Generates Draft Replies & Summaries**: Provides a 1-line contextual summary and an editable suggested response for human verification.
6. **Empowers Human Review**: Serves a specialized review queue where human support agents approve, refine, or override classifications with single-click actions.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Ingestion Layer"]
        IncomingMail["Incoming Customer Email / Ticket"]
        FastAPIEndpoint["FastAPI /api/v1/triage"]
        IncomingMail --> FastAPIEndpoint
    end

    subgraph PreFilter["2. Deterministic Guardrails & Pre-filtering"]
        FastAPIEndpoint --> RuleChecker{"Deterministic Pre-filter"}
        RuleChecker -->|Explicit Breach / Exploit / CVE| EscalateInstant["Instant Escalation\nescalate=True, Priority=URGENT, Cat=SECURITY"]
        RuleChecker -->|Clean Ticket Body| PromptBuilder["Context Builder & Few-Shot Formatter"]
    end

    subgraph InferenceEngine["3. SLM Inference Engine"]
        PromptBuilder --> OllamaClient["Async OpenAI SDK Client\n(Ollama: llama3.2:3b)"]
        OllamaClient --> RawOutput["Raw JSON String"]
    end

    subgraph Validation["4. 3-Tier Validation & Resilience"]
        RawOutput --> PydanticValidator{"Pydantic v2\nSchema Validation"}
        PydanticValidator -->|Valid Schema| VerifiedResult["Structured TriageResult"]
        PydanticValidator -->|Invalid JSON / Schema Drift| RetryLoop{"Self-Correction Retry\n(Max 1 Retry with Feedback)"}
        RetryLoop -->|Success| VerifiedResult
        RetryLoop -->|Persistent Failure| SafeFallback["Safe Default Fallback\nescalate=True, Confidence=0.0"]
    end

    subgraph HumanInTheLoop["5. Human-in-the-Loop Review Queue"]
        EscalateInstant --> ReviewQueue["Review Queue UI\n(Human Agent Inbox)"]
        VerifiedResult --> ReviewQueue
        SafeFallback --> ReviewQueue
        ReviewQueue --> AgentAction{"Agent Review"}
        AgentAction -->|Approve & Send| OutboundDelivery["Outbound Email Delivery"]
        AgentAction -->|Edit Draft| OutboundDelivery
        AgentAction -->|Reclassify / Override| EvalDataset["Feedback Loop & Eval Gold Set"]
    end

    subgraph Observability["6. Observability & Telemetry"]
        FastAPIEndpoint -.-> Sentry["Sentry SDK (Crash & Trace Telemetry)"]
        OllamaClient -.-> StructuredLogs["Structured Logger (stdout)"]
        EvalDataset -.-> EvalHarness["make eval (Empirical Benchmark)"]
    end
```

---

## 3. Core Architectural Decisions & Trade-Offs

### Decision 1: Lightweight Client (`openai` SDK) over LangChain / LlamaIndex
* **Rationale:** LangChain introduces unnecessary layers of abstraction, bloated dependencies, and heavy memory overhead. For deterministic structured triage with local models, `openai>=1.0.0` (with `base_url="http://localhost:11434/v1"`) combined with `pydantic>=2.0` offers:
  - Sub-millisecond import and boot times.
  - Transparent error recovery loops without black-box framework internals.
  - Zero cognitive bloat for debugging and tracing.
* **Trade-off:** We hand-craft prompt templates and retry logic, which guarantees 100% control over edge-case behavior.

### Decision 2: 3-Tier LLM Resilience Pattern for SLMs (`llama3.2:3b`)
Local Small Language Models (SLMs) have significantly smaller parameter counts and can produce syntax anomalies or hallucinated categories under stress. We protect system stability using a strict 3-tier defense:

```mermaid
sequenceDiagram
    autonumber
    participant App as TriageService
    participant LLM as Ollama (llama3.2:3b)
    participant Val as Pydantic Schema
    participant Fallback as Safe Fallback

    App->>LLM: Send Few-Shot Structured Prompt (temperature=0.2)
    LLM-->>App: Raw String Response
    App->>Val: Validate against TriageResult
    alt Schema Valid
        Val-->>App: TriageResult Object
    else Validation Failed
        App->>LLM: Self-Correction Prompt (Error Message + Raw Output)
        LLM-->>App: Corrected String Response
        App->>Val: Re-validate
        alt Second Attempt Valid
            Val-->>App: TriageResult Object
        else Second Attempt Failed
            App->>Fallback: Trigger Safe Fallback (escalate=True, confidence=0.0)
            Fallback-->>App: Fallback TriageResult
        end
    end
```

### Decision 3: Clean Layered Architecture
The repository strictly isolates concerns into clean layers:
- `src/core/`: Configuration via environment variables, structured console logging, and Sentry error telemetry.
- `src/schemas/`: Immutable, strongly-typed Pydantic domain models.
- `src/services/`: Pure business logic (LLM API wrapper, triage classification, fallback handlers).
- `src/api/`: FastAPI routers and HTTP transport concerns.
- `eval/`: Empirical evaluation harness, ground truth testing, and benchmark metrics output.
- `frontend/`: Human review workspace.

---

## 4. Domain Data Schema

```mermaid
classDiagram
    class Ticket {
        +Optional[str] id
        +str subject
        +str body
        +Optional[str] sender
    }

    class TicketCategory {
        <<enumeration>>
        BILLING
        BUG
        FEATURE_REQUEST
        ACCOUNT
        SECURITY
        OTHER
    }

    class TicketPriority {
        <<enumeration>>
        LOW
        MEDIUM
        HIGH
        URGENT
    }

    class TriageResult {
        +Optional[str] ticket_id
        +Optional[TicketCategory] category
        +Optional[TicketPriority] priority
        +Optional[str] summary
        +Optional[str] suggested_reply
        +List[str] suggested_tags
        +float confidence
        +bool escalate
    }

    Ticket --> TriageResult : transforms into
    TriageResult o-- TicketCategory : contains
    TriageResult o-- TicketPriority : contains
```

---

## 5. Security & Safety Protocols

1. **No Automatic Unsupervised Outbound Communication:** The system never transmits an AI-generated email to an external customer without human agent sign-off.
2. **Defensive Prompt Injection Handling:** Incoming ticket bodies are quarantined as untrusted data inputs and parsed within explicit delimiter tags (`<ticket_body>...</ticket_body>`).
3. **Automated Security Incident Escalation:** Tickets matching security markers (`unauthorized access`, `vulnerability`, `credential leak`) bypass standard queues and automatically set `priority = URGENT` and `escalate = True`.
