# Repo-ready Architecture / Spec Document

**Suggested file name:**\
`/docs/architecture/review_proposal_workbench_architecture.md`

***

## Review & Proposal Workbench Architecture

### Purpose

Define the end-to-end design for a lightweight, traceable, multi-agent review and proposal system that turns project artifacts into evolving reviews, reconciled intelligence, and proposal-ready outputs.

***

## 1. Product Goal

The product should help users answer, clearly and repeatedly:

* What is missing?
* What is weak?
* What is unresolved?
* What should be decided next?
* Is this strong enough to turn into a proposal?

The system is **not** just a one-shot review generator.\
It is a **traceable decision assistant** built on top of:

* Project → Version → Review → Proposal
* iterative refinement
* explicit provenance
* lightweight human-in-the-loop reasoning

This aligns with the intended model already described in the existing repo notes: a review should display **Version ID, included files, categories + metadata, persona used, prompt used, and output**, and the system should support traceability and learning over time.

***

## 2. Core Principles

### 2.1 Traceability first

Every important output should answer:

* **why is this being said?**
* **which artifact or prior review supports it?**

### 2.2 Reviews are evolving knowledge

A review is not a disposable output.\
A review is a structured reasoning step that can be:

* refined
* referenced
* compared
* used in proposal synthesis

### 2.3 Proposal is synthesis, not raw generation

Proposal creation should reconcile selected reviews into a proposal-ready intelligence pack.\
It should not behave like a standalone free-form generator.

### 2.4 Keep it lightweight

* no microservices
* no heavy orchestration framework
* no unnecessary new entities
* additive changes only
* backward compatible wherever practical

### 2.5 Human input improves intelligence

User notes on weaknesses are part of the intelligence system, not just comments.\
They should shape later reviews, reconciliations, and proposals.

***

## 3. User Value by Step

### 3.1 Version Creation

User value:

* knows exactly which artifacts are included
* trusts that later reviews are based on selected evidence

### 3.2 Review Execution

User value:

* sees the review in context
* sees which persona and prompt were used
* sees top risks and supporting evidence

### 3.3 Review Tightening

User value:

* can refine thinking
* can add free-text notes to weaknesses
* can create a new review from a selected prior review

### 3.4 Proposal Synthesis

User value:

* can combine selected perspectives intentionally
* can move from review output to proposal-ready structure

### 3.5 Proposal Review and Guidance

User value:

* understands what is still weak
* sees what is covered
* gets next best actions

The attached SoW example shows exactly why this matters: it combines formal scope, delivery phases, technical assumptions, risks, comments, ownership split, exclusions, pricing, and iterative peer comments in one document. A generic LLM chat can discuss parts of that, but it does not naturally preserve iterative reasoning and provenance across steps.

***

## 4. End-to-End Workflow



***

## 5. Multi-Agent Pipeline

### Agent 1 — Version Context Builder

**Responsibility:** build the trusted context pack for a selected Version.

**Inputs**

* project
* version
* selected artifacts
* artifact metadata

**Outputs**

* version ID
* artifact inventory
* artifact refs
* comments / discussion presence
* normalized context summary

**User value**

* “I know what this version is based on.”

***

### Agent 2 — Review Analyzer

**Responsibility:** run persona-specific analysis grounded in the version context.

**Outputs**

* risks
* assumptions
* dependencies
* constraints
* action items
* weaknesses
* decision points

Each item should optionally include:

* source artifact ref
* section reference
* previous review reference if inherited

**User value**

* “I know why this review says what it says.”

This matches the structured review approach already described in your “Solution Review” notes, including explicit artifacts in the output.

***

### Agent 3 — Weakness + Note Handler

**Responsibility:** let the user update each weakness with:

* status
* optional free-text note

**Outputs**
Each weakness becomes:

* weakness text
* status
* user note
* provenance

**User value**

* “The system reflects my judgment, not just AI output.”

***

### Agent 4 — Review Iteration Agent

**Responsibility:** create a new review using:

* one **user-selected** prior review
* current version context
* optional new artifacts
* selected persona

**Outputs**

* new review
* `previous_review_id`
* refined findings
* issues carried forward or resolved

**Important rule**

* it creates a **new review**, it does not overwrite an old review
* prior review becomes part of the contextual input

**User value**

* “I can intentionally build on an earlier line of reasoning.”

***

### Agent 5 — Reconciliation Agent

**Responsibility:** reconcile explicitly selected reviews into one proposal-ready intelligence pack.

**Inputs**

* one anchor review
* selected supplemental reviews
* version context
* relevant user notes

**Outputs**

* consensus points
* divergent/conflicting points
* confirmed decisions
* open decisions
* unresolved weaknesses
* merged findings
* provenance retained

**User value**

* “I can combine perspectives without losing clarity.”

***

### Agent 6 — Coverage Mapper

**Responsibility:** translate reconciled intelligence into readiness domains.

**Coverage domains**

* Scope
* Architecture
* Delivery
* Security / Compliance
* Operations
* Commercials

**Statuses**

* Addressed
* Partial
* Not Yet Addressed

**User value**

* “I can see what my proposal actually covers.”

***

### Agent 7 — Proposal Builder

**Responsibility:** create a **Proposal Data Pack**, not a client-formatted document.

**Outputs**

* Executive Position
* Client Need / Problem Framing
* Recommended Solution Approach
* What This Proposal Covers
* Key Assumptions
* Confirmed Decisions
* Open Decisions / Clarifications Needed
* Key Risks and Mitigations
* Delivery Approach and Phasing
* Operations / MSP Considerations
* Commercial Sensitivities
* Why This Proposal Is Credible
* Next Best Actions

**User value**

* “I have a strong, reusable proposal intelligence pack.”

***

### Agent 8 — Proposal Review Agent

**Responsibility:** critique the proposal pack before it is used.

**Outputs**

* Covered Well
* Still Weak
* May Block Sign-off

Across:

* Scope
* Architecture
* Delivery
* Security / Compliance
* Operations
* Commercials

**User value**

* “I know what still needs strengthening.”

***

### Agent 9 — Forward Guidance Agent

**Responsibility:** suggest practical next steps.

**Grounding**
Must use only:

* unresolved weaknesses
* open decisions
* conflicts
* coverage gaps

**Outputs**

* Strengthen Weak Areas
* Resolve Key Decisions
* Improve Proposal Credibility
* Accelerate Client Alignment
* Optional Enhancements (only if grounded)

**User value**

* “I know what to do next.”

***

## 6. Provenance Model

### Goal

Provenance must be **human-meaningful**, not generic.

### Artifact-type-aware traceability

#### Documents / Word / PDF

* document name
* section / heading
* page number
* optional short excerpt

**Example**

* `Source: Solution_Architecture.docx → Section: Technical Assumptions → Page 7`

#### Slides / PPT

* deck name
* slide number
* optional slide title

**Example**

* `Source: Client_Deck.pptx → Slide 12 → Migration Approach`

#### Email

* subject
* date
* optional sender

**Example**

* `Source: Email → "Feedback on Proposal v2" → 14 June 2026`

#### Meeting notes / transcript

* meeting name
* date
* timestamp or section
* optional speaker if available

#### Spreadsheet

* workbook name
* sheet
* row range / label

***

### Provenance data structure (lightweight)

Each tagged output item can support:

```json
{
  "artifact_id": "a123",
  "artifact_name": "RFP.pdf",
  "artifact_type": "document",
  "section_reference": "Delivery Model",
  "page_reference": "3",
  "excerpt": "Optional short snippet"
}
```

### UI pattern

Do **not** show full provenance text everywhere.\
Use:

* small chips
* hover / expand for details

***

## 7. UI Contract

### 7.1 Review Full Details

### Must be visible immediately

Without expanding the full page, show:

* Review ID
* Version ID
* Persona used
* Prompt used
* Top 3 risks
* Status
* Created / updated date

### Expandable / scrollable sections

* Included artifacts
* Findings
* Weaknesses
* Decision points
* User notes
* Full output / raw sections

### Weakness UI

For each weakness:

* text
* status
* optional free-text note
* provenance chip

### Interaction rule

* clicking a review opens Full Details
* compare is a secondary action
* generate proposal is a contextual action

This matches your direction that v2 should stay clean and use in-line scroll / expand-collapse instead of letting the full page grow uncontrollably.

***

### 7.2 Proposal UI

Proposal should be a **contextual action**, not the primary experience.

**Primary path**

* select Version
* select anchor review
* optionally select supplemental reviews
* generate proposal

**Proposal view should show**

* summary
* coverage
* decisions
* risks
* blockers
* next actions
* lightweight provenance

***

## 8. Data Relationships



***

## 9. Minimal Data Model Changes

### Review

Ensure or add:

* `version_id`
* `artifact_refs[]`
* `persona_used`
* `prompt_used`
* `prompt_builder_state`
* `weaknesses[]`
* `decision_points[]`
* `previous_review_id`
* `user_note` per weakness

### Proposal

Ensure or add:

* `version_id`
* `anchor_review_id`
* `selected_review_ids[]`
* `reconciliation_result`
* `proposal_review_pass`
* `proposal_coverage`
* `forward_guidance`

### Important

No heavy new standalone business entity is required at this stage.

***

## 10. Sprint Roadmap (Independent Modules)

### Sprint 1 — Review Traceability + Full Details

**Goal**
Make reviews self-explanatory and trustworthy.

**Module**

* Review Full Details contract
* provenance display
* weakness note UI

**Stories**

* Show Version ID, Persona used, Prompt used, Top 3 risks
* Show included artifacts with section refs
* Add weakness status + optional note
* Ensure review click opens details, not compare

**Acceptance criteria**

* Users can understand a review without hidden context
* provenance visible
* page does not grow uncontrollably

***

### Sprint 2 — Review Iteration

**Goal**
Create a new review from one selected previous review.

**Module**

* review lineage + controlled iteration

**Stories**

* add/select `previous_review_id`
* create new review from selected prior review
* prior review used as part of contextual input
* persona can be changed

**Acceptance criteria**

* no overwrite of prior review
* lineage visible
* new review clearly linked to old review

***

### Sprint 3 — Reconciliation

**Goal**
Reconcile selected reviews into one proposal-ready decision pack.

**Module**

* review selection + reconciliation

**Stories**

* explicit anchor review
* explicit supplemental reviews
* consensus / conflicts / open decisions
* preserve provenance

**Acceptance criteria**

* no “latest N” auto-selection
* explicit user choice preserved
* provenance survives reconciliation

***

### Sprint 4 — Coverage + Proposal Data Pack

**Goal**
Turn reconciled intelligence into proposal-ready structure.

**Module**

* coverage + proposal builder + proposal review pass

**Stories**

* coverage by domain
* proposal pack generation
* proposal review pass for blockers / weak areas

**Acceptance criteria**

* proposal output is clear and client-format-agnostic
* covered / partial / missing visible

***

### Sprint 5 — Forward Guidance

**Goal**
Tell users what to do next.

**Module**

* forward guidance engine + UI surfacing

**Stories**

* grounded next steps
* focus areas
* credibility improvement suggestions
* stronger provenance display on proposal outputs

**Acceptance criteria**

* recommendations are practical and grounded
* not generic / speculative

***

## 11. Why this belongs in the repo

Yes — **store this in the repo and tell Kiro to treat it as the planning anchor**.

### Recommended practice

* save the architecture/spec document in `/docs/architecture/`
* save sprint backlog in `/docs/planning/` later if needed
* point Kiro to these files before each sprint

### Benefits

* stable context across sessions
* lower token usage
* less drift
* easier Git review
* better onboarding for future contributors

***

## 12. Kiro handoff prompt (to save this and use it)

Use this after you save the document:

```text
Read /docs/architecture/review_proposal_workbench_architecture.md and treat it as the source of truth for upcoming implementation work.

Rules:
- Do not redesign outside this document
- Implement sprint by sprint
- Preserve v1 behaviour unless explicitly changed
- Keep modules independent where possible
- Keep provenance, review lineage, and proposal synthesis aligned to the architecture doc

First task:
Review Sprint 1 only and produce implementation-ready stories with file targets and acceptance criteria.
Do not code yet.
```
