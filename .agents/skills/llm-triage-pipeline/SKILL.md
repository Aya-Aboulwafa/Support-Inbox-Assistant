---
name: llm-triage-pipeline
description: Best practices for engineering resilient LLM triage pipelines with small local models (Ollama, llama3.2:3b), Pydantic validation, structured JSON outputs, few-shot prompts, fallback recovery, and human-in-the-loop escalation.
---

# LLM Triage Pipeline Engineering

## 1. Context & Objectives
Small language models (e.g. `llama3.2:3b`) require defensive engineering to achieve high classification accuracy and deterministic JSON formatting for customer support inboxes.

## 2. 3-Tier Resilience Architecture

### Tier 1: Deterministic Pre-Filtering & Enrichment
- Extract sender domain, keywords, and priority signals before prompting.
- Detect explicit security keywords (`breach`, `exploit`, `unauthorized`) and force immediate escalation.

### Tier 2: In-Context Few-Shot Structured Prompting
- Define exact enums:
  - `category`: `billing`, `bug`, `feature_request`, `account`, `security`, `other`
  - `priority`: `low`, `medium`, `high`, `urgent`
- Provide 2–3 concrete, high-contrast few-shot examples illustrating edge cases.
- Force JSON output with temperature `<= 0.2`.
- Include refusal/escalation rules: *"If ambiguous or confidence < 0.7, set escalate: true."*

### Tier 3: Validation, Self-Correction & Safe Fallback
```python
# Validation workflow:
1. Parse JSON from model output (strip markdown fences if present).
2. Validate with Pydantic model (TriageResult).
3. If ValidationError or JSONDecodeError:
   - Attempt 1 self-correction retry with error feedback in prompt.
   - If retry fails, invoke safe fallback:
     TriageResult(
       category=TicketCategory.OTHER,
       priority=TicketPriority.MEDIUM,
       summary="Auto-fallback: Requires manual agent triage",
       confidence=0.0,
       escalate=True,
     )
```
