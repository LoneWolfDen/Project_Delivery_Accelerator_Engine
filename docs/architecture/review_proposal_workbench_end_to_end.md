# Review & Proposal Workbench — End-to-End Architecture and Specification

## 1. Purpose

This document defines the target end-to-end design for the Review & Proposal Workbench.

The goal is to move from isolated review outputs to a **traceable, iterative, decision-support system** that:
- preserves Version → Review context
- supports human + AI refinement
- reconciles selected reviews into proposal-ready intelligence
- shows why a risk, weakness, or recommendation exists
- remains lightweight and production-friendly

This document is the **source of truth** for future implementation planning and code review.

---

## 2. Scope

This architecture applies to:
- **v2 UI and v2 workflows**
- backend and data contracts needed to support v2 behaviour
- review, iteration, reconciliation, coverage, proposal, and guidance workflows

This architecture does **not** require:
- a full redesign of v1
- heavy new platform services
- client-specific proposal formatting
- microservices or a separate orchestration runtime

v1 remains a fallback / baseline unless explicitly changed.

---

## 3. Product Goal

The product should help users answer:

- What is missing?
- What is weak?
- What is unresolved?
- What should be decided next?
- Is this strong enough to move toward proposal / sign-off?

This is **not** a one-shot LLM wrapper.

This is a **decision and review workbench** built around:
- persistent context
- review evolution
- explicit provenance
- proposal synthesis from selected reviews

---

## 4. Design Principles

### 4.1 Traceability first
Every important output should be explainable:
- why is it being said?
- which artifact or prior review supports it?
- which persona and prompt produced it?

### 4.2 Review is evolving knowledge
A review is not disposable output.
A review can be:
- created
- refined
- compared
- referenced
- used as input to later reasoning

### 4.3 Proposal is synthesis
Proposal creation should reconcile **selected reviews** into a proposal-ready intelligence pack.
It should not behave like a free-form standalone generator.

### 4.4 Human input improves intelligence
User notes on weaknesses are part of the intelligence system.
They should influence future review iterations and later synthesis.

### 4.5 Keep it lightweight
- additive changes
- backward-compatible where possible
- module boundaries clear
- no unnecessary new entities
- no heavy new runtime

---

## 5. Core Conceptual Model

```mermaid
flowchart LR
    P[Project] --> V[Version]
    V --> R[Review]
    R --> RI[Review Iteration]
    R --> RS[Review Selection]
    RI --> RS
    RS --> RC[Reconciliation]
    RC --> CV[Coverage]
    CV --> PP[Proposal Data Pack]
    PP --> PR[Proposal Review]
    PR --> FG[Forward Guidance]



6. User Value by Stage
6.1 Ingest and Version
User value:

knows what artifacts are included
trusts the context behind later reviews

6.2 Review
User value:

sees persona, prompt, and top risks immediately
understands what the review is based on

6.3 Review Iteration
User value:

can build on one selected prior review
can refine a line of thinking deliberately

6.4 Reconciliation
User value:

can combine multiple selected perspectives without losing clarity
sees where reviews agree, disagree, or leave decisions open

6.5 Proposal Output
User value:

gets a reusable proposal intelligence pack
sees what is covered, what is weak, and what to do next

This matches the review style expected by the existing system: reviews should evaluate architecture, scope, delivery, resourcing, and financial concerns, and the output structure already expects discovered artefacts to be part of the result set.

7. End-to-End Workflow

<img width="4032" height="555" alt="image" src="https://github.com/user-attachments/assets/145105b9-7fb9-4bcc-822a-5316c1207069" />

8. Agent / Module Responsibilities
The implementation should be modular. These do not require separate services; they can be implemented as internal processors / modules.
8.1 Version Context Builder
Purpose: build trusted context for a selected Version
Input

project
version
selected artifacts
artifact metadata

Output

version ID
artifact inventory
normalized context summary
provenance-ready artifact refs


8.2 Review Analyzer
Purpose: run persona-specific review against version context
Output

risks
assumptions
dependencies
constraints
action items
weaknesses
decision points

Each item should preserve provenance if available.

8.3 Weakness + Note Handler
Purpose: attach user judgment to AI findings
Each weakness supports:

text
status
optional free-text user note
provenance


8.4 Review Iteration Handler
Purpose: create a new review from one user-selected prior review
Rules

prior review is explicit, never automatic
new review is created, old review is not overwritten
prior review becomes part of contextual input
persona may be changed


8.5 Reconciliation Engine
Purpose: reconcile explicitly selected reviews into one proposal-grade intelligence pack
Output

consensus points
divergent / conflicting points
confirmed decisions
open decisions
unresolved weaknesses
merged findings
provenance summary


8.6 Coverage Mapper
Purpose: show what proposal intelligence covers
Domains

Scope
Architecture
Delivery
Security / Compliance
Operations
Commercials

Statuses

Addressed
Partial
Not Yet Addressed


8.7 Proposal Builder
Purpose: create a Proposal Data Pack (not client-formatted document yet)
Output sections

Executive Position
Client Need / Problem Framing
Recommended Solution Approach
What This Proposal Covers
Key Assumptions
Confirmed Decisions
Open Decisions / Clarifications Needed
Key Risks and Mitigations
Delivery Approach and Phasing
Operations / MSP Considerations
Commercial Sensitivities
Why This Proposal Is Credible
Next Best Actions


8.8 Proposal Review Agent
Purpose: critique the proposal data pack
Output

Covered Well
Still Weak
May Block Sign-off

Across the same domains as coverage.

8.9 Forward Guidance Agent
Purpose: suggest practical next actions
Must be grounded only in:

unresolved weaknesses
open decisions
conflicts
coverage gaps


9. Provenance Model
Goal
Provenance must be human-meaningful, not generic.
9.1 Artifact-type-aware provenance
Documents / Word / PDF

artifact name
section / heading
page number
optional short excerpt

Slides / PowerPoint

artifact name
slide number
optional slide title

Email

subject
date
optional sender

Meeting notes / transcript

meeting name
date
timestamp or section
optional speaker if available

Spreadsheet

workbook name
sheet
row range / label if available

9.2 Provenance payload shape
{
  "artifact_id": "a123",
  "artifact_name": "RFP.pdf",
  "artifact_type": "document",
  "section_reference": "Delivery Model",
  "page_reference": "3",
  "excerpt": "Optional short snippet"
}

9.3 UI pattern
Use lightweight chips or short reference lines.
Do not flood the UI with full citations.

10. UI Contract
10.1 Review Full Details
Must be visible immediately

Review ID
Version ID
Persona used
Prompt used
Top 3 risks
Status
Created / updated date

Expandable / scrollable sections

Included Artifacts
Findings
Weaknesses
Decision Points
User Notes
Raw output / extra detail

Weakness interaction
For each weakness:

text
status
optional free-text note
provenance chip

Interaction rule

clicking a review opens Full Details
compare is a secondary action
review remains the primary interaction

This is consistent with the repo intent that each review must expose Version context, included files/categories, persona, prompt, and output.

10.2 Proposal UI
Proposal should be a contextual workflow, not a detached standalone experience.
Primary path

select Version
select anchor review
optionally select supplemental reviews
reconcile
generate proposal data pack

Proposal output should show

summary
coverage
decisions
risks
blockers
next actions
lightweight provenance


11. Business Logic Rules
11.1 Version
A Version is a snapshot of:

selected artifacts
metadata
available context

11.2 Review
A Review is:

an execution on a Version
tied to a persona and prompt
expected to expose Version context + output + provenance

11.3 Review Iteration
A new review can be created from one user-selected prior review.
That base review becomes contextual input.
The new review must:

link back via previous_review_id
retain its own persona and prompt

11.4 Reconciliation
Reconciliation combines:

one anchor review
optional supplemental reviews
current version context

Rules:

no auto “latest N” selection
user explicit selection
preserve provenance
keep consensus, divergence, open decisions, unresolved weaknesses explicit

11.5 Proposal
Proposal uses reconciled output to build a reusable intelligence pack.
Formatting into client templates is a separate concern and not in scope here.

12. Data Relationships

<img width="1107" height="2268" alt="image" src="https://github.com/user-attachments/assets/0de33265-d2f7-42d3-9b26-0d198573940c" />


13. Minimal Data Contract Expectations
Review
Ensure support for:

version_id
artifact_refs[]
persona_used
prompt_used
prompt_builder_state
weaknesses[]
decision_points[]
previous_review_id
user_note per weakness

Proposal
Ensure support for:

version_id
anchor_review_id
selected_review_ids[]
reconciliation_result
proposal_review_pass
proposal_coverage
forward_guidance

No heavy new standalone business entity is required for this stage.

14. Traceability Flow

<img width="1038" height="2268" alt="image" src="https://github.com/user-attachments/assets/6cf6a5ee-d1c3-4529-a189-dbe2bc4290d7" />

15. Module Independence
Implementation should be modular so Kiro can:

compare current code vs target behaviour
plan module-by-module changes
implement incrementally without broad regressions

Recommended independent modules:

Review Full Details + traceability
Review iteration
Reconciliation
Coverage
Proposal data pack
Proposal review
Forward guidance


16. Production-readiness Guidelines

additive changes only
backward-compatible where feasible
explicit contracts over hidden state
lightweight persistence
deterministic logic where possible before downstream LLM usage
provenance carried through all downstream steps
tests and affected diagrams updated with each module change
