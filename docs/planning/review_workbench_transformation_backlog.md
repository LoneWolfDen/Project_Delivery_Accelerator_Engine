# Review Workbench Transformation Backlog

**Source of truth:** `review_workbench_transformation_backlog.json` (v1.0)

---

## Overall Goal

Mature the application from an **insight tool** into a **decision assistant**.

- The completeness score is demoted to a light visual cue — it is not the primary value signal.
- Primary value is helping teams **tighten solutions and proposals** through structured review cycles: guided clarification, visible iteration, decision tracking, and convergence toward proposal readiness.
- Reviews become **guided tightening loops**, not one-shot analyses.

---

## Product Context

| Dimension | Detail |
|---|---|
| First target domain | Pre-sales (extend to SDLC and operations later) |
| User type | Non-technical; minimal free-text input expected |
| Core shift | One-shot review → iterative tightening loop |
| Score role | Secondary badge, not dominant signal |
| Future direction | Self-learning from prompt and outcome history |

---

## Lenses Used to Shape the Backlog

Product Owner · Systems Architect · AI Specialist · Solution Architect · Delivery Manager · Solution Executive

---

## Design Principles

1. Traceability over opacity
2. Decision quality over review volume
3. Structured guidance over free-text prompting
4. Iteration visibility over static outputs
5. Minimal user input, high-value output
6. Backward-compatible and low-risk changes first

---

## Sprint Roadmap

| Sprint | Name | Priority | Depends On | Stories |
|---|---|---|---|---|
| S1 | Foundation and Review Chain Stability | High | — | 5 |
| S2 | Prompt Builder Foundation | High | S1 | 3 |
| S3 | Guided Tightening Loop | High | S2 | 4 |
| S4 | Weakness and Gap Intelligence | High | S3 | 3 |
| S5 | Decision Intelligence | High | S4 | 3 |
| S6 | Resolution and Iteration Intelligence | Medium | S5 | 3 |
| S7 | Convergence and Learning Foundation | Medium | S6 | 4 |

### Sprint Summaries

**S1 — Foundation and Review Chain Stability**
Version-scope reviews, add `previous_review_id` for explicit chaining, show iteration labels (R1, R2…), reposition Ask SME as a pre-review tightening step, and visually demote the completeness score.

**S2 — Prompt Builder Foundation**
Replace blank custom prompting with a structured builder: baseline persona prompt + injected suggested questions + user notes. Persist prompt state per review iteration and indicate baseline-vs-customised in the UI.

**S3 — Guided Tightening Loop**
Ask SME generates targeted clarification questions (not generic advice). Users select which questions feed the next review. A "what changed" summary compares current vs previous review findings.

**S4 — Weakness and Gap Intelligence**
Extract structured weaknesses and missing categories from reviews. Surface them visibly so Ask SME can use prior findings and gaps to generate more targeted questions.

**S5 — Decision Intelligence**
Extract explicit decision points (platform, DR, phasing, cost). Map SME questions to decisions so users understand why a question matters. Track decision status (open / addressed / validated / rejected) across iterations.

**S6 — Resolution and Iteration Intelligence**
Track whether weaknesses and decisions are resolved iteration-by-iteration. Structured diff engine (resolved / new / unchanged). Feed only unresolved client feedback into the next tightening cycle.

**S7 — Convergence and Learning Foundation**
Show a convergence indicator (resolved decisions + weaknesses). Gate proposal generation on convergence readiness. Log all prompt inputs and outcomes for future self-learning; provide basic retrieval by persona, scenario, or project context.

---

## Success Criteria

- Users can improve review quality across iterations
- The system can explain what changed and why
- Proposal generation uses the strongest review, not just the latest
- The system identifies unresolved decisions, not only missing categories
- Foundations exist for future prompt learning and self-improvement

---

## How This Roadmap Guides Future Work

1. **Strategic continuity** — Every fix, feature, or planning request should be evaluated against the overall transformation goal (insight tool → decision assistant) and the active sprint.
2. **Sprint dependencies are strict** — S2 requires S1 complete; S3 requires S2, and so on. Do not implement stories from a later sprint until prior sprints are validated.
3. **Additive changes only** — Prefer extending existing structures (`previous_review_id`, `prompt_builder_state`, `decision_points`) over replacing them.
4. **Score is not the goal** — Avoid optimising for completeness score improvements. Optimise for decision quality, traceability, and convergence.
5. **Non-technical users first** — All UI changes must remain simple. Reduce free-text friction wherever possible.
6. **Learning foundation is late-stage** — S7 logs data for future autonomous improvement. Do not implement self-learning or autonomous retraining before S7.

---

## Ambiguities and Open Questions

The following items are noted for clarification — no backlog changes have been made:

1. **"Strongest review" for proposal generation** (S7-02, success criteria) — Not yet defined. Is "strongest" the highest convergence score, the most recent validated review, or a manual selection? Needs a decision before S7-02 is implemented.
2. **Feedback source for S6-03** — "Client feedback" is referenced but the current data model for client feedback is not described in the backlog. Needs clarification on where feedback is stored and how it is linked to review iterations before S6-03 is implemented.
3. **Convergence computation (S7-01)** — The formula (resolved decisions + weaknesses) is directional but not specified. Weightings, thresholds, and the definition of "sufficiently tightened" for the proposal gate (S7-02) are not defined.
4. **Persona / scenario context for prompt retrieval (S7-04)** — "Persona" and "scenario" are mentioned as filter dimensions but are not defined in the data model. Clarification needed before S7-04 schema work begins.
5. **Scope of S1-05 (Demote score)** — The story explicitly says "no major logic changes required." Confirm whether the score can be removed from primary layout without touching scoring logic, or if a UI-only change risks inconsistencies elsewhere.
