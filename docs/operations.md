# ⚙️ Operations, Tooling & Workflow Guide

## 1. Environment Setup with `uv`

The project exclusively uses **Astral `uv`** for dependency resolution and virtual environment lifecycle management.

### Key Advantages of `uv`:
- **Deterministic Resolution:** Dependencies pinned in `uv.lock`.
- **High Performance:** 10–100x faster installation than traditional `pip`.
- **PEP 517/621 Standards:** All metadata and dependency groups declared in `pyproject.toml`.

### Setup Instructions:
```bash
# 1. Install dependencies and initialize .venv
make setup

# Or directly:
uv sync
```

---

## 2. Mandatory Submission Contracts (`meta.yaml` & `Makefile`)

The repository adheres to the mandatory submission contract specified in `meta.yaml`:

```yaml
language: python
run_command: "make run"
eval_command: "make eval"
test_command: "pytest -q"
```

### Makefile Targets:
| Target | Command | Purpose |
| :--- | :--- | :--- |
| `make setup` | `uv sync` | Installs dependencies into `.venv`. |
| `make run` | `uv run uvicorn src.main:app ...` | Boots FastAPI server with hot-reload. |
| `make test` | `pytest -q` | Executes the unit and integration test suite. |
| `make eval` | `uv run python -m eval.evaluate` | Executes evaluation benchmark against dataset. |
| `make clean` | `find . -name "__pycache__" -exec rm -rf {} +` | Removes cached bytecode artifacts. |

---

## 3. Containerization (Docker & Docker Compose)

### 3.1 Docker Architecture
The container build utilizes a multi-stage approach with Astral `uv` binaries to keep image size small:
- Base: `python:3.12-slim`
- Pre-installed virtual environment mounted under `/app/.venv`
- Non-root execution compatibility

### 3.2 Host Ollama Connectivity
When running the application inside Docker, it communicates with the host machine's Ollama instance via Docker's internal host gateway:
- **`host.docker.internal:host-gateway`** is declared in `docker-compose.yml`.
- `LLM_BASE_URL` is set to `http://host.docker.internal:11434/v1`.

### Commands:
```bash
# Start container with live volume mounting
docker compose up --build

# Run in background
docker compose up -d

# Spin up with optional bundled Ollama service
docker compose --profile with-ollama up
```

---

## 4. Git 3-Tier Branching & Commit Protocol

To preserve production stability, contributors must follow the 3-tier git hierarchy:

```text
       main (Production Release)
        ▲
        │  [STOP: Only upon explicit user request!]
        │
       dev (Integration / Staging)
        ▲
        │  [Merge verified feature branch via --no-ff]
        │
 feat/* | fix/* | chore/* (Working Branches)
   (All active work, code modifications, and tests happen here)
```

### Rules:
1. **Never work or commit on `main`**.
2. **Never commit directly on `dev`**.
3. **Always branch from `dev`** (`git checkout -b feat/<name>`).
4. **Commit every unit of change** using Conventional Commits (`feat`, `fix`, `chore`, `test`, `refactor`).
5. **Verify before merge**: Run `make test` and ensure all tests pass.
6. **Merge via non-fast-forward**: `git checkout dev && git merge --no-ff feat/<name>`.
7. **Retain and push**: Keep feature branches and push both the feature branch and `dev` to the remote repository.
