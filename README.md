# Support Inbox Assistant

An intelligent, automated triage assistant and review-queue system for customer support inboxes. The system categorizes incoming tickets, assigns priority scores, generates summaries, and powers a human-in-the-loop review queue.

---

## Overview

Support Inbox Assistant provides an extensible backend service and evaluation harness powered by local Large Language Models (LLMs) via an Ollama OpenAI-compatible endpoint.

### Architecture Highlights
- **Framework**: FastAPI with asynchronous lifecycle management
- **Dependency & Tooling**: Managed with Astral `uv`
- **LLM Integration**: Lightweight `openai` client configured for local Ollama endpoints
- **Data Validation**: Pydantic v2 schemas
- **Human-in-the-Loop UI**: Interactive web queue for ticket triage review and draft approval
- **Observability**: Built-in Sentry error tracking integration and structured logging
- **Evaluation Harness**: Automated evaluation script benchmarking triage predictions against ground truth labels
- **CI/CD & Automation**: Automated Pytest & Docker build checks, automated git tagging and release notes via GitHub Actions

---

## Requirements

- **Operating System**: Linux / macOS / Windows (WSL2 recommended)
- **Python**: `>= 3.11` (Python 3.12 recommended)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (`>= 0.5.0`)
- **Container Runtime (Optional)**: Docker & Docker Compose
- **LLM Provider**: [Ollama](https://ollama.ai/) running locally with model `llama3.2:3b` (or any OpenAI-compatible API)

---

## Prerequisites & Model Setup

Ensure you have [Ollama](https://ollama.ai/) installed and pull the required model:

```bash
ollama pull llama3.2:3b
```

Ensure Ollama is running (`ollama serve` or standard service running on `http://localhost:11434`).

---

## Installation & Getting Started

First, clone and enter the repository:

```bash
git clone https://github.com/Aya-Aboulwafa/Support-Inbox-Assistant.git
cd Support-Inbox-Assistant
```

Choose your preferred way to install and run the application:
- [Method 1: The Makefile Way (Recommended)](#method-1-the-makefile-way-recommended)
- [Method 2: The Local Development / uv Way](#method-2-the-local-development--uv-way)
- [Method 3: The Docker & Docker Compose Way](#method-3-the-docker--docker-compose-way)

---

### Method 1: The Makefile Way (Recommended)

The project includes pre-configured `make` targets conforming to the project's submission contract (`meta.yaml`):

#### 1. Setup Environment & Dependencies
```bash
cp .env.example .env
make setup
```

#### 2. Start the Application & UI
```bash
make run
```
The server will start with hot-reload enabled at [http://localhost:8000](http://localhost:8000).

#### 3. Run the Test Suite
```bash
make test
```

#### 4. Run the Evaluation Benchmark
```bash
make eval
```
Executes the triage benchmark against `data/tickets.json` and records metrics to `eval/results.json`.

---

### Method 2: The Local Development / uv Way

For standard Python development using Astral `uv`:

#### 1. Environment Configuration
```bash
cp .env.example .env
```

#### 2. Install Dependencies
```bash
uv sync --all-groups
```

#### 3. Activate Virtual Environment (Optional)
```bash
source .venv/bin/activate
```

#### 4. Start Server with Hot Reload
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Run Tests
```bash
uv run pytest -v
```

#### 6. Run Evaluation Harness
```bash
uv run python -m eval.evaluate
```

---

### Method 3: The Docker & Docker Compose Way

#### Option A: Running with Host Ollama (Standard Development)
When Ollama is already running on your host machine:

```bash
# Build and start container in foreground
docker compose up --build

# Or run detached in background
docker compose up -d --build

# View container logs
docker compose logs -f app

# Stop the container
docker compose down
```
*Note: Uses `host.docker.internal:11434` to communicate with the host's Ollama instance. Source code is mounted live into `/app`.*

#### Option B: Full Stack in Docker (Bundled Ollama Container)
If you do not have Ollama installed on your host system:

```bash
# 1. Start both Application and Ollama services in background
docker compose --profile with-ollama up -d --build

# 2. Pull the model inside the Ollama container (first time only)
docker compose exec ollama ollama pull llama3.2:3b

# 3. View combined logs
docker compose --profile with-ollama logs -f
```

#### Option C: Standalone Production Docker Container
To build and run an isolated container without Docker Compose:

```bash
# 1. Build Docker image
docker build -t support-inbox-assistant .

# 2. Run container
docker run -p 8000:8000 \
  --add-host=host.docker.internal:host-gateway \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  -e LLM_MODEL=llama3.2:3b \
  support-inbox-assistant
```

---

## Access & Verification

Once the application is running (via any method above):

| Service / Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Review Queue Frontend** | [http://localhost:8000/ui](http://localhost:8000/ui) | Interactive human-in-the-loop triage UI |
| **Interactive API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI documentation & interactive testing |
| **Alternative Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Clean API reference |
| **Health Check Endpoint** | [http://localhost:8000/health](http://localhost:8000/health) | System health & LLM connectivity status |

---

## Environment Variables

The project uses the following environment variables (configured in `.env` or system environment):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | URL for the OpenAI-compatible endpoint (e.g. Ollama) |
| `LLM_MODEL` | `llama3.2:3b` | Target LLM model name |
| `LLM_API_KEY` | `ollama` | API key (required by client, set to dummy for Ollama) |
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`) |
| `DEBUG` | `false` | Enable verbose debugging and full tracebacks |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `SENTRY_DSN` | *(Optional)* | Sentry project DSN for error telemetry |

---

## How to Run Eval & Where to Read Results

The system includes an automated evaluation harness conforming strictly to the submission contract in `meta.yaml`:

```bash
make eval
# Or directly via uv:
uv run python -m eval.evaluate
```

### Where Results Are Written & Interpreting Output
The evaluation harness evaluates all 30 tickets in [`data/tickets.json`](data/tickets.json), computes accuracy metrics over the 16 ground-truth labels in [`data/labels.json`](data/labels.json), and writes the output directly to [`eval/results.json`](eval/results.json) adhering to the exact required contract:

```json
{
  "metrics": {
    "category_accuracy": 0.625,
    "priority_agreement": 0.8125
  },
  "predictions": [
    {
      "id": "T-001",
      "category": "billing",
      "priority": "high",
      "summary": "Customer requests refund for duplicate charge on June subscription.",
      "suggested_reply": "Hi Marta, ...",
      "confidence": 0.99,
      "escalate": false
    }
    // ... exactly 30 prediction objects
  ]
}
```

### Empirical Results Achieved

| Benchmark Metric | Score | Detail |
| :--- | :---: | :--- |
| **Total Predictions Generated** | **30 / 30** | Exactly 30 predictions generated and saved in `eval/results.json` |
| **Labeled Ground-Truth Subset** | **16 / 16** | Evaluated against verified ground truth in `data/labels.json` |
| **Category Classification Accuracy** | **62.5%** | 10 / 16 exact category matches (`category_accuracy: 0.625`) |
| **Priority Agreement** | **81.25%** | 13 / 16 exact priority matches (`priority_agreement: 0.8125`) |
| **Macro F1 Score** | **0.4571** | Class-balanced F1 score across all categories |
| **Mean Inference Latency** | **~20.7s** | Measured per ticket on the active model endpoint |

---

## Error Analysis

Evaluating `llama3.2:3b` empirically on the 16 ground-truth tickets revealed **6 boundary discrepancies**. Below is an objective analysis of where and why the model failed on specific tickets from the labeled subset:

| Ticket ID | Subject | Predicted | Ground Truth | Root Cause Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **`T-006`** | *URGENT: production down for our whole team* | `security` *(urgent)* | `bug` *(urgent)* | **Keyword / Urgency Bias:** The extreme urgency and outage terminology tripped the model's security sensitivity rather than classifying as an operational downtime bug. |
| **`T-007`** | *Question about your data policy* | `feature_request` *(medium)* | `other` *(medium)* | **Negative Space Defaulting:** Legal and privacy compliance inquiries did not match bug, billing, or account; the model defaulted to a feature request rather than the general `other` bucket. |
| **`T-013`** | *how do I add a teammate* | `feature_request` *(low)* | `account` *(low)* | **Intent Ambiguity:** Inquiring about adding team members was interpreted as asking whether collaboration features exist, rather than routine workspace user administration. |
| **`T-017`** | *Cancel my subscription* | `account` *(medium)* | `billing` *(medium)* | **Boundary Overlap:** Subscription lifecycle cancellations straddle account termination and payment processing. The model focused on the account entity rather than the financial subscription. |
| **`T-019`** | *Webhook signature mismatch* | `security` *(urgent)* | `bug` *(urgent)* | **Cryptographic Keyword Bias:** Words like *"signature"*, *"secret"*, and *"HMAC"* biased the model toward security, whereas developer integration bugs are operational engineering defects. |
| **`T-024`** | *SSO / SAML for 200 users* | `account` *(medium)* | `feature_request` *(medium)* | **Capability Gap vs. Config:** Requesting enterprise SSO/SAML integration was treated as configuring an existing account rather than requesting an unintegrated enterprise feature. |

### Technical Trade-offs & Parameter Limitations
1. **3B Model Capacity Limitations:** Compact models (`llama3.2:3b`) have strong semantic comprehension but exhibit keyword attraction (e.g. associating *"signature"* or *"production down"* disproportionately with `security`).
2. **Taxonomy Boundary Overlap:** Real customer tickets are inherently multifaceted. A customer asking to *"Cancel my subscription"* is simultaneously an account lifecycle event and a billing event.
3. **Mitigations for Next Iteration:**
   - **Few-Shot Boundary Calibration:** Add targeted counter-examples for developer integration webhooks and subscription cancellations directly to the system prompt.
   - **Taxonomy Disambiguation Rules:** Explicitly define precedence rules (e.g. *"Any financial or plan change takes precedence as billing"*).
   - **Human Review Safeguard:** The Human-in-the-Loop review queue catches all low-confidence and escalated tickets before any response is dispatched.

---

## Engineering Decisions, Trade-offs, Limitations & Next Steps

### 1. Key Architectural Decisions
- **`instructor` + `pydantic` over LangChain:**
  - Avoids bloated dependency graphs, high RAM usage, and opaque abstraction layers.
  - Guarantees strict runtime schema validation, automatic type coercion, and self-correction retry loops natively over the OpenAI client interface.
- **Strict Human-in-the-Loop (No Autonomous Auto-Replies):**
  - Completely eliminates catastrophic LLM hallucination and legal liability by ensuring no email is transmitted without human agent approval.
  - The model operates strictly as an intelligent copilot, populating draft replies and classification metadata for 1-click agent review.
- **3-Tier LLM Resilience Pattern:**
  - **Tier 1:** Structured system prompts with XML ticket isolation and few-shot calibration.
  - **Tier 2:** Instructor schema enforcement with validation retries and low temperature (`0.1`).
  - **Tier 3:** Deterministic fallback safety nets (`confidence: 0.0, escalate: True`) ensuring the service never crashes or drops a ticket during network/model degradation.

### 2. Architectural Trade-offs
| Decision | Advantage | Trade-off / Compromise |
| :--- | :--- | :--- |
| **In-Memory `TicketStore`** | Zero external infrastructure; instant startup for evaluation and testing. | State is reset upon process restart; not suited for distributed horizontal scaling without PostgreSQL. |
| **Local 3B SLM (`llama3.2:3b`)** | Complete data privacy, zero vendor token costs, fully offline runnable. | Reduced reasoning capacity compared to frontier models (Claude 3.5 Sonnet / GPT-4o) on ambiguous boundary cases. |
| **Vanilla HTML/Tailwind Frontend** | Single static file served directly by FastAPI; zero Node.js build step or asset bundling overhead. | Less reactive state management compared to React/Next.js component trees. |

### 3. Current Limitations
- **Inference Latency:** Sequential remote Ollama inference averages ~20.7s per ticket without dedicated GPU batching.
- **Single-Turn Context:** Current triage processes incoming tickets as isolated units without accessing previous multi-turn email history.
- **Degraded Short Messages:** Extreme short/noisy inputs (e.g. `T-004: "asdkjhasd test test ignore"`) lack semantic signal for high-confidence classification.

### 4. Next Steps & Production Scaling
1. **Durable Persistence:** Migrate `TicketStore` to PostgreSQL via SQLAlchemy 2.0 and Alembic migrations.
2. **Background Task Queues:** Decouple ticket ingestion from triage inference using Redis + Celery / ARQ workers for sub-50ms HTTP response times.
3. **Semantic Caching:** Cache triage outputs using vector embeddings for recurring FAQs (e.g. password resets, duplicate charge reports).
4. **LoRA Fine-Tuning Pipeline:** Feed human-agent approved replies back into a fine-tuning dataset to specialize local SLMs on company-specific domain terminology.

---

## Repository Structure

```text
Support-Inbox-Assistant/
├── .github/                  # GitHub Actions CI/CD & release automation
│   └── workflows/
│       ├── ci.yml            # Automated testing & Docker build quality gates
│       └── release.yml       # Auto-tagging & GitHub Release notes on merge to main
├── .env.example              # Sample environment configuration
├── .gitignore                # Git ignore patterns
├── .python-version           # Target Python version pin
├── Dockerfile                # Container build specification
├── Makefile                  # Lifecycle command targets (setup, run, eval, test)
├── README.md                 # Project documentation
├── docker-compose.yml        # Docker compose service definition
├── meta.yaml                 # Submission specification contract
├── pyproject.toml            # Project metadata & uv dependencies
├── uv.lock                   # Deterministic dependency lockfile
├── data/                     # Dataset directory (tickets.json & labels.json)
├── docs/                     # Comprehensive architecture and API documentation
│   ├── README.md             # Documentation hub
│   ├── api.md                # REST API specification
│   ├── blueprint.md          # End-to-end system architecture blueprint
│   ├── eval-guide.md         # Evaluation harness guide
│   ├── operations.md         # Tooling and operations guide
│   └── roadmap.md            # Future improvements & feature roadmap
├── eval/                     # Evaluation harness & metrics output (results.json)
├── frontend/                 # Review-queue frontend workspace
├── src/                      # Core application source
│   ├── api/                  # FastAPI router definitions
│   ├── core/                 # Config, logging, and Sentry initialization
│   ├── schemas/              # Pydantic data schemas
│   └── services/             # LLM client & triage services
└── tests/                    # Unit and integration test suite
```
