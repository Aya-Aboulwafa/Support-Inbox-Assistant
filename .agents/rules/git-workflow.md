---
description: Mandatory 3-tier branching protocol and git commit rule for Support Inbox Assistant
always_on: true
---

# Git Workflow & Branching Law

## 1. Branch Hierarchy
- **`main`**: Production / Release branch.
  - **PROHIBITION**: Never commit directly to `main`.
  - **PROHIBITION**: Never merge into `main` automatically. Stop and wait for explicit user command.
- **`dev`**: Integration branch preceding `main`.
  - **PROHIBITION**: Never commit directly to `dev`.
  - Serves as the integration point for tested feature branches.
- **Working Branches (`feat/*`, `fix/*`, `chore/*`, `task/*`)**:
  - All coding, testing, and modifications MUST take place on a dedicated working branch branched from `dev`.

## 2. Commit Requirements
- **Commit Every Change**: Every discrete modification or task step must be committed. Do not leave uncommitted work lingering.
- **Conventional Commits**: Format every commit message:
  ```text
  <type>(<scope>): <summary in imperative mood>

  [optional body with details]
  ```
  Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`.

## 3. Merging & Retention Protocol
- Run verification (`make test`, `pytest -q`, and `make eval` if applicable) before merging.
- Merge into `dev` using non-fast-forward merge:
  ```bash
  git checkout dev
  git merge --no-ff <branch-name>
  ```
- **Retain Branches**: Keep all working branches (do not delete them).
- **Push Branches**: Push both the working branch and `dev` branch to the remote origin (`git push origin <branch-name>` and `git push origin dev`).
