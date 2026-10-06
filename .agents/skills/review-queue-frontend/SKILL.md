---
name: review-queue-frontend
description: Guide for developing the human-in-the-loop review queue UI for customer support agents, including ticket triage queue, confidence scoring, editable AI drafts, and quick-approval actions.
---

# Review Queue Frontend Engineering

## 1. Core User Experience
The interface serves support agents who must triage dozens of tickets per hour:
- **Left Panel (Ticket Queue)**:
  - List of incoming tickets sorted by urgency.
  - Visual badges for `Category`, `Priority`, and `Escalate` alert flags.
  - Low-confidence (< 0.70) warning indicators.
- **Center/Right Panel (Triage Detail & Action)**:
  - Original customer email/message with sender details.
  - One-line AI Summary.
  - Editable Text Area with the AI-suggested response.
  - Action Controls:
    - **Approve & Send** (1-click response)
    - **Modify & Send**
    - **Reclassify** (override category or priority)
    - **Escalate to Human Tier 2**
