# 📚 Project Documentation Hub

Welcome to the technical documentation for **Support Inbox Assistant**, an enterprise-grade human-in-the-loop automated triage copilot for support engineering teams.

---

## 📑 Documentation Index

1. **[System Architecture Blueprint](blueprint.md)**
   - Complete system vision and high-level design
   - End-to-end data flow and sequence diagrams
   - 3-Tier LLM resilience engineering pattern for `llama3.2:3b`
   - Clean Architecture directory structure and domain schemas
   - Safety, pre-filtering, and guardrails

2. **[REST API Specification](api.md)**
   - RESTful endpoints (`/api/v1/health`, `/api/v1/triage`, `/`)
   - Schema contracts, sample payloads, and status codes
   - Sentry exception tracking and structured logging integration

3. **[Evaluation Harness & Benchmarking Guide](eval-guide.md)**
   - Continuous benchmarking philosophy (`make eval`)
   - Golden datasets (`data/tickets.json`, `data/labels.json`)
   - Accuracy, priority agreement, escalation precision, and latency metrics
   - Output specifications for `eval/results.json`

4. **[Operations, Tooling & Workflow Guide](operations.md)**
   - Environment and dependency management with `uv`
   - Mandatory contracts in `meta.yaml` and `Makefile`
   - Multi-stage Docker build & `docker-compose.yml`
   - 3-Tier Git branching and Conventional Commit protocols

---

## 🚀 Quick Start Commands

```bash
# Setup dependencies
make setup

# Run tests
make test

# Run evaluation benchmark
make eval

# Start development server
make run
```
