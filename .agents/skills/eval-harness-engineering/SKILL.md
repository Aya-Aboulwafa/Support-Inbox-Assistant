---
name: eval-harness-engineering
description: Guidelines for building empirical LLM evaluation harnesses, benchmarking classification accuracy, priority agreement, latency, calculating metrics, and outputting structured reports to eval/results.json.
---

# Evaluation Harness Engineering Skill

## 1. Principles
Evaluation must be empirical, automated, and repeatable via a single command: `make eval`.
Never evaluate prompts qualitatively by inspecting single samples manually.

## 2. Evaluation Workflow
1. **Load Test Dataset**: Read `data/tickets.json` and `data/labels.json`.
2. **Execute Predictions**: Pass each ticket through the triage pipeline (`TriageService`).
3. **Compute Metrics**:
   - **Category Accuracy**: `(correct_category_predictions / total_tickets) * 100`
   - **Priority Agreement**: exact matches or weighted agreement between predicted and ground truth priority.
   - **Escalation Coverage**: percentage of ambiguous/critical tickets correctly flagged with `escalate=True`.
   - **Mean Latency**: average response time per ticket in milliseconds.
4. **Persist Results**: Write clean JSON to `eval/results.json`.
5. **Print Error Analysis**: Log confusion matrix and false-positive/false-negative analysis to console.
