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
- **Observability**: Built-in Sentry error tracking integration and structured logging
- **Evaluation Harness**: Automated evaluation script benchmarking triage predictions against ground truth labels

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

## Documentation

Comprehensive engineering documentation and architecture blueprints are located in the [docs/](docs/README.md) directory:
- [System Architecture Blueprint](docs/blueprint.md)
- [REST API Specification](docs/api.md)
- [Evaluation Harness & Benchmarking Guide](docs/eval-guide.md)
- [Operations, Tooling & Workflow Guide](docs/operations.md)

---

## Repository Structure

```text
Support-Inbox-Assistant/
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
│   └── operations.md         # Tooling and operations guide
├── eval/                     # Evaluation harness & metrics output (results.json)
├── frontend/                 # Review-queue frontend workspace
├── src/                      # Core application source
│   ├── api/                  # FastAPI router definitions
│   ├── core/                 # Config, logging, and Sentry initialization
│   ├── schemas/              # Pydantic data schemas
│   └── services/             # LLM client & triage services
└── tests/                    # Unit and integration test suite
```
