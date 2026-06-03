ROLE: Principal Systems Architect + Product Owner + Senior Full Stack Engineer

READ FIRST — SOURCE OF TRUTH
Before doing anything, read and follow these repo files as the source of truth:
- /docs/architecture/review_proposal_workbench_architecture.md
- /docs/planning/review_proposal_workbench_sprint_backlog.md

IF the codebase conflicts with the architecture docs:
- do NOT guess
- do NOT redesign
- report the conflict first, then propose the minimum safe fix

--------------------------------------------------
PRODUCT GOAL
--------------------------------------------------

Build a lightweight, production-ready Review & Proposal Workbench that helps users answer:

- What is missing?
- What is weak?
- What is unresolved?
- What should be decided next?
- Is this strong enough to become a proposal?

The product is NOT a one-shot LLM wrapper.
It is a traceable decision assistant built around:
- Project → Version → Review → Proposal
- review iteration
- explicit provenance
- human-in-the-loop reasoning
- proposal synthesis from selected reviews

The system must feel more valuable than ad hoc LLM chat because it preserves:
- context over time
- visible reasoning
- artifact-backed traceability
- review lineage
- proposal-ready synthesis

--------------------------------------------------
SCOPE BOUNDARY
--------------------------------------------------

This applies to:
- v2 UI / v2 workflows only

v1:
- remains unchanged
- serves as fallback / baseline
- should not be modified unless explicitly required for safe shared backward-compatible logic

--------------------------------------------------
CORE WORKFLOW (NON-NEGOTIABLE)
--------------------------------------------------

The core workflow must remain intact:

Ingest → Version → Review → Review Iteration → Reconciliation → Proposal → Proposal Review → Forward Guidance

Do NOT remove or break:
- Ingest
- Version creation
- Review creation
- Review Full Details

Current regressions must be fixed before later sprints continue.

--------------------------------------------------
CORE PRINCIPLES
--------------------------------------------------

1. Traceability first
Every important output should answer:
- why is this being said?
- which artifact / section / review supports it?

2. Reviews are evolving knowledge
A review is not disposable output.
A review can be refined, referenced, compared, and used in synthesis.

3. Proposal is synthesis, not raw generation
Proposal creation should reconcile selected reviews into one proposal-ready intelligence pack.

4. Human input improves intelligence
Weakness notes and status updates are part of the reasoning system.

5. Keep it lightweight
- no microservices
- no heavy platform redesign
- additive, modular changes only
- preserve backward compatibility

--------------------------------------------------
TARGET ARCHITECTURE / MODULES
--------------------------------------------------

Use internal modules / processors with clear responsibilities:

1. Version Context Builder
- builds trusted context for a selected Version
- outputs included artifacts and metadata

2. Review Analyzer
- runs persona-based review grounded in version context
- outputs risks, assumptions, dependencies, constraints, action_items, weaknesses, decision_points

3. Weakness + Note Handler
- supports weakness status and optional free-text user note

4. Review Iteration Handler
- creates a NEW review from one user-selected prior review
- stores previous_review_id
- allows persona change
- uses prior review as contextual input

5. Reconciliation Engine
- reconciles one anchor review + selected supplemental reviews
- outputs:
  - consensus_points
  - divergent_points / conflicts
  - confirmed_decisions
  - open_decisions
  - unresolved_weaknesses
  - merged_findings

6. Coverage Mapper
- maps reconciled intelligence to these domains:
  - Scope
  - Architecture
  - Delivery
  - Security / Compliance
  - Operations
  - Commercials
- statuses:
  - Addressed
  - Partial
  - Not Yet Addressed

7. Proposal Builder
- creates a client-format-agnostic Proposal Data Pack

8. Proposal Review Agent
- critiques the proposal output:
  - Covered Well
  - Still Weak
  - May Block Sign-off

9. Forward Guidance Agent
- suggests next best actions using only:
  - unresolved weaknesses
  - open decisions
  - conflicts
  - coverage gaps

--------------------------------------------------
PROVENANCE MODEL
--------------------------------------------------

Provenance must be human-meaningful and artifact-type aware.

Use lightweight provenance like:

Documents / PDFs / Word:
- artifact name
- section / heading
- page number if available

Slides:
- artifact name
- slide number
- slide title if available

Emails:
- subject
- date
- sender if available

Meetings:
- meeting name
- date
- timestamp / section if available

Spreadsheets:
- workbook
- sheet
- row range / label if available

Display provenance as lightweight chips / short references.
Do NOT flood UI with full citation text.

--------------------------------------------------
REVIEW FULL DETAILS CONTRACT
--------------------------------------------------

Review Full Details must show immediately (without requiring the entire page to grow excessively):
- Review ID
- Version ID
- Persona used
- Prompt used
- Top 3 risks
- Review status
- Created / updated date

Use expandable or in-panel scroll sections for:
- Included Artifacts
- Findings
- Weaknesses
- Decision Points
- Full output / raw details

For each weakness:
- weakness text
- status
- optional free-text note
- provenance if available

Clicking a review must open Review Full Details.
Compare must remain a secondary action.

--------------------------------------------------
REVIEW ITERATION RULE
--------------------------------------------------

Review iteration must:
- create a NEW review
- use ONE user-selected prior review as the base
- store previous_review_id
- allow persona change
- treat the prior review as contextual input

Do NOT overwrite existing reviews.
Do NOT auto-select a prior review.

--------------------------------------------------
RECONCILIATION RULE
--------------------------------------------------

Reconciliation is NOT proposal generation.

It must:
- use one explicit anchor review
- use zero or more explicitly selected supplemental reviews
- preserve provenance where possible
- not auto-select latest N reviews
- not lose visible source context

If Active Review exists, it may be pre-populated as anchor, but user selection must remain explicit.

--------------------------------------------------
PROPOSAL RULE
--------------------------------------------------

Proposal is a contextual action built from Version + selected Reviews.

Do NOT treat Proposal as a standalone primary experience.
Do NOT rely on a full Proposal tab as the main workflow.

Primary flow:
- select Version
- select anchor review
- select supplemental reviews
- generate proposal pack

Proposal data pack must include:
- Executive Position
- Client Need / Problem Framing
- Recommended Solution Approach
- What This Proposal Covers
- Key Assumptions
- Confirmed Decisions
- Open Decisions / Clarifications Needed
- Key Risks and Mitigations
- Delivery Approach and Phasing
- Operations / MSP Considerations
- Commercial Sensitivities
- Why This Proposal Is Credible
- Next Best Actions

--------------------------------------------------
CURRENT KNOWN ISSUES / GAPS TO FIX IN ORDER
--------------------------------------------------

Fix these before progressing too far:

1. Restore missing core workflow
- Ingest missing
- Version creation missing
- Review creation missing

2. Fix Review Full Details regressions
- Ensure weaknesses render
- Ensure weakness notes work
- Ensure Full Details shows Version ID, Persona, Prompt, Top 3 risks

3. Fix review interaction priority
- clicking a review must open Review Full Details
- compare must not replace review details

4. Fix anchor UX
- do not show misleading anchor hint
- if anchor change is not implemented yet, say:
  "This review is currently the anchor."

5. Keep navigation continuity
- do NOT remove main workflow sections from v2
- full tab redesign is not required, but workflow must remain accessible

--------------------------------------------------
IMPLEMENTATION ORDER
--------------------------------------------------

Do NOT implement everything at once.
Use this sequence:

Phase 0 — Workflow Stabilization
- restore Ingest → Version → Review in v2
- confirm the system can create inputs again
- do not touch later layers unless necessary

Phase 1 — Review Traceability
- fix Review Full Details contract
- show persona, prompt, top 3 risks
- render artifacts / provenance
- weakness status + note

Phase 2 — Review Iteration
- create review from one selected prior review
- store previous_review_id
- preserve lineage

Phase 3 — Reconciliation
- explicit anchor + supplemental reviews
- consensus / divergent / open decisions / unresolved weaknesses
- preserve provenance

Phase 4 — Coverage + Proposal Data Pack
- build coverage
- build proposal pack
- add proposal review pass

Phase 5 — Forward Guidance
- practical next actions grounded in current data

Do not move to the next phase until the current phase is stable and validated.

--------------------------------------------------
TESTING / REGRESSION RULES
--------------------------------------------------

For every phase:
- update test suite
- add only tests relevant to the changed module
- add non-regression tests so earlier phases still work
- keep tests deterministic
- reuse existing patterns

Always validate manually after each phase:
- create artifact
- create version
- create review
- open review
- iterate review
- reconcile reviews
- generate proposal (when implemented)

--------------------------------------------------
DOCUMENTATION / DIAGRAM RULES
--------------------------------------------------

Per phase:
- update only touched diagrams and traceability docs
- do NOT refresh unrelated diagrams

Likely files:
- /docs/architecture/review_proposal_workbench_architecture.md
- /docs/architecture/application_flow.md
- /docs/architecture/logic_flow.md
- /docs/architecture/data_model.md
- /docs/architecture/traceability_map.md

Full architecture refresh can happen at milestone boundaries, not every small change.

--------------------------------------------------
PR / BRANCH RULES
--------------------------------------------------

Always:
- create a NEW branch
- create a NEW PR
- do not append to an old PR

Each PR must include:
- summary
- files changed
- tests added / updated
- docs / diagrams updated
- assumptions / limitations

--------------------------------------------------
REQUESTED OUTPUT
--------------------------------------------------

Do NOT implement everything now.

First:
1. compare current codebase against this architecture
2. list missing or broken workflow layers
3. identify what was likely overwritten or regressed
4. propose the minimum safe implementation order
5. map that order to existing code files / modules
6. recommend whether to restore workflow first before continuing to later sprints

Keep the response practical, modular, and low-fluff.
