---
name: git-workflow
description: Enforce the mandatory 3-tier branching protocol (feat -> dev -> main), conventional commits, non-fast-forward merges, branch retention, and push requirements. Use whenever creating branches, committing changes, merging, or managing version control.
---

# Git Workflow & Conventional Commits Skill

## Core Directives
1. **Never commit on `main`**: `main` is production-only and updated only on explicit user instruction.
2. **Never commit on `dev`**: `dev` is integration-only.
3. **Always work on dedicated branches**: Branch off `dev`:
   ```bash
   git checkout dev
   git checkout -b <type>/<description>
   ```
4. **Commit Every Change**: Use Conventional Commits (`feat`, `fix`, `chore`, `test`, `refactor`).
5. **Merge to `dev`**:
   ```bash
   # 1. Run tests
   pytest -q
   # 2. Switch to dev and merge
   git checkout dev
   git merge --no-ff <type>/<description>
   # 3. Retain branch and push
   git push origin <type>/<description>
   git push origin dev
   ```
6. **Stop before `main`**: Never promote `dev` to `main` without explicit confirmation.
