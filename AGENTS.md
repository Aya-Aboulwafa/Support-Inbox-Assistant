# Support Inbox Assistant - AI Agent Rules & Operational Guidelines

## 1. 3-Tier Branching & Git Commit Protocol (MANDATORY RULE)

All AI agents and contributors working in this repository MUST adhere strictly to the following 3-tier branching and commit protocol:

```text
       main (Production / Releases)
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

### Strict Rules:
1. **NEVER work or commit directly on `main`**:
   - `main` is strictly reserved for stable production releases.
   - Merging from `dev` to `main` is strictly forbidden unless the user explicitly requests it.
2. **`dev` is the integration branch before `main`**:
   - `dev` contains the integrated, tested codebase ready for release.
3. **NEVER commit directly on `dev`**:
   - Direct commits, editing files, or running hotfixes directly on `dev` are strictly forbidden.
4. **Always create a dedicated working branch off `dev`**:
   - Every feature, task, fix, or chore must be created from `dev`:
     ```bash
     git checkout dev
     git checkout -b <type>/<descriptive-name>
     ```
5. **Commit every change using Conventional Commits**:
   - All commits must follow Conventional Commits format (`feat`, `fix`, `chore`, `test`, `docs`, `refactor`, `perf`).
   - Every meaningful unit of change must be committed.
6. **Merge to `dev` and preserve branches**:
   - Once all unit tests and verifications pass on the working branch:
     ```bash
     git checkout dev
     git merge --no-ff <type>/<descriptive-name>
     ```
   - For this project, retain all working branches (do not delete them).
   - Push working branches and `dev` to the remote repository.

---

## 2. Architecture & Design Principles

- **Zero Bloat & Clean Architecture**: Maintain separation of concerns (`core/`, `schemas/`, `services/`, `api/`, `eval/`, `frontend/`).
- **Resilient LLM Engineering**:
  - Treat local models (`llama3.2:3b`) as non-deterministic.
  - Implement 3-tier resilience: Strict structured prompts (with few-shot examples) -> Pydantic validation -> Self-correction retry loop with safe fallbacks (`escalate=True`).
- **Strict Submission Contracts**:
  - `meta.yaml` defines the submission contract:
    - `run_command: "make run"`
    - `eval_command: "make eval"`
    - `test_command: "pytest -q"`
  - Never alter these command keys.
- **Evaluation Discipline**:
  - Any model or prompt adjustment must be verified against `make eval`.
  - Output metrics must be recorded in `eval/results.json`.
