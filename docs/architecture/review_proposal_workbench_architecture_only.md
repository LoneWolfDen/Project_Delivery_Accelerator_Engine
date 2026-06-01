# Review & Proposal Workbench Architecture (v2 - Token Light)

## 1. Goal
Build a traceable, iterative review and proposal system that:
- preserves context across reviews
- supports human + AI reasoning
- enables structured proposal synthesis

This is NOT a one-shot LLM tool.
This is a decision and review workbench.

---

## 2. Core Model

Project → Version → Review → Proposal

Extensions:
- Review Iteration (review over review)
- Multi-review reconciliation (proposal stage)

---

## 3. Core Principles

- Traceability first (always answer “why”)
- Review is evolving knowledge
- Proposal = synthesis, not generation
- Human input improves system intelligence
- Keep system lightweight

---

## 4. Workflow

```mermaid
flowchart LR
A[Version] --> B[Review]
B --> C[Weakness + User Notes]
C --> D[Review Iteration]
D --> E[Select Reviews]
E --> F[Reconciliation]
F --> G[Coverage]
G --> H[Proposal]
H --> I[Proposal Review]
I --> J[Forward Guidance]
