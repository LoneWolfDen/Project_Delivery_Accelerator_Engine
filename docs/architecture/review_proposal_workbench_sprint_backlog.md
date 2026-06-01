```md
# Review & Proposal Workbench — Sprint Backlog

## Sprint 1 — Review Traceability

### Goal
Make reviews self-explanatory.

### Scope
- Add persona_used
- Add prompt_used
- Show Version ID
- Show Top 3 risks
- Add artifact references (section-level)
- Add weakness status + free text note

### Acceptance
- Review can be understood without hidden context
- No page overflow (use collapsible sections)

---

## Sprint 2 — Review Iteration

### Goal
Enable “review from review”.

### Scope
- User selects base review
- Create new review with previous_review_id
- Include prior review as context
- Allow persona change

### Acceptance
- No overwrite of prior review
- Review lineage visible

---

## Sprint 3 — Reconciliation

### Goal
Combine multiple reviews.

### Scope
- User selects reviews explicitly
- Define anchor review
- Build reconciliation output:
  - consensus
  - conflicts
  - open decisions

### Acceptance
- No auto selection
- Provenance preserved

---

## Sprint 4 — Proposal + Coverage

### Goal
Generate proposal intelligence.

### Scope
- Coverage mapping:
  - Scope
  - Architecture
  - Delivery
  - Ops
  - Security
  - Commercials

- Proposal data pack:
  - summary
  - risks
  - assumptions
  - recommendations

### Acceptance
- Covered / Partial / Missing visible
- Output reusable

---

## Sprint 5 — Forward Guidance

### Goal
Guide next actions.

### Scope
- Suggestions based on:
  - unresolved weaknesses
  - open decisions
  - coverage gaps

### Acceptance
- Practical recommendations only
- No generic suggestions

---

## Execution Rules

- Implement one sprint at a time
- Do not jump ahead
- Do not redesign outside architecture doc
- Always verify with real data after each sprint
