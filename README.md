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

## Installation

### 1. Clone & Navigate
```bash
git clone https://github.com/Aya-Aboulwafa/Support-Inbox-Assistant.git
cd Support-Inbox-Assistant
```

### 2. Install Dependencies with `uv`
Use `uv` to automatically create the virtual environment (`.venv`) and install dependencies:
```bash
make setup
# Or directly via uv:
uv sync
```

### 3. Configure Environment Variables
Copy the template configuration:
```bash
cp .env.example .env
```

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

## Execution Commands

All primary workflows are automated through standard `make` targets and contracts specified in `meta.yaml`:

### Run Server & UI
Start the FastAPI development server with hot-reload:
```bash
make run
```
The API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Run Test Suite
Run unit and integration tests via `pytest`:
```bash
make test
# Or directly:
pytest -q
```

### Run Evaluation Harness
Execute the triage benchmarking script and write results to `eval/results.json`:
```bash
make eval
```

### Docker Execution
To run the service inside Docker with local code mounting:
```bash
# Build and start container
docker compose up --build

# Run in background
docker compose up -d
```
If you wish to spin up a bundled Ollama container alongside the application:
```bash
docker compose --profile with-ollama up
```

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
├── eval/                     # Evaluation harness & metrics output (results.json)
├── frontend/                 # Review-queue frontend workspace
├── src/                      # Core application source
│   ├── api/                  # FastAPI router definitions
│   ├── core/                 # Config, logging, and Sentry initialization
│   ├── schemas/              # Pydantic data schemas
│   └── services/             # LLM client & triage services
└── tests/                    # Unit and integration test suite
```
