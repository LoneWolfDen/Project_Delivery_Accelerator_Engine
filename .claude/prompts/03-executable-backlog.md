This is a backlog creation task only.
Do not modify application code.
Read all files under:
docs/assessment/
docs/architecture/
Create an implementation backlog detailed enough that a smaller coding model can execute one item without interpreting the full repository.
A backlog item is invalid if it says only:
- refactor this
- improve architecture
- clean this up
- modernize this
- fix security
- integrate Copilot
- add SharePoint
- make production-ready
Every backlog item must include:
- unique ID
- title
- capability group
- priority
- phase
- current classification
- evidence
- exact problem
- reason this matters
- target behaviour
- smallest safe change
- explicit exclusions
- files expected to change
- files that must not change
- functions, symbols or components likely affected
- dependencies
- prerequisite decisions
- external approvals
- data-boundary impact
- storage or migration impact
- security and privacy impact
- automated tests
- manual verification
- acceptance criteria
- rollback
- recommended commit boundary
- completion evidence
- instructions for updating continuity documents
Use these capability groups:
- BASELINE AND RECOVERY
- HUMAN-READABLE SOURCE
- MINIFIED CODE MIGRATION
- BUILD AND STARTUP
- PWA AND OFFLINE
- UI AND ACCESSIBILITY
- DATA AND STORAGE
- BACKUP AND RESTORE
- FILE IMPORT
- ONEDRIVE INPUT
- SHAREPOINT INPUT
- ONEDRIVE OUTPUT
- SHAREPOINT OUTPUT
- CHAT AND RETRIEVAL
- MICROSOFT 365 COPILOT
- MICROSOFT GRAPH
- SECURITY AND PRIVACY
- DIAGNOSTICS
- TESTING
- DOCUMENTATION
- REPOSITORY CLEANUP
- RELEASE AND OPERATIONS
Use priorities:
P0:
- prevents data loss
- prevents external leakage
- prevents fabricated answers
- restores maintainable source
- required to establish a trustworthy baseline
P1:
- required for reliable daily use
- required for manual OneDrive or SharePoint file workflows
- required for grounded chat
- required for installable or dependable PWA use
P2:
- improves usability or assisted refresh
- manual Copilot package workflow
- folder-based workflows
- improved diagnostics
- additional file types
P3:
- live Microsoft Graph
- agents
- connectors
- multi-user
- enterprise hosting
- broader governance
Create these files:
docs/backlog/MASTER_BACKLOG.md
docs/backlog/DEPENDENCY_MAP.md
docs/backlog/EXECUTION_SEQUENCE.md
docs/backlog/RISK_REGISTER.md
docs/backlog/DECISION_REGISTER.md
docs/backlog/SMALL_MODEL_EXECUTION_RULES.md
MASTER_BACKLOG.md must list every item.
DEPENDENCY_MAP.md must identify:
- prerequisites
- parallel-safe items
- mutually exclusive alternatives
- high-risk sequences
- items blocked by admin approval
- items blocked by missing source code
EXECUTION_SEQUENCE.md must group work into contained phases:
Phase 0:
- baseline
- backups
- source recovery
- no outbound leakage
- truthful chat
- tests
Phase 1:
- maintainable application shell
- reliable storage
- file import
- provenance
Phase 2:
- PWA and daily use
- OneDrive and SharePoint V1
- grounded chatbot
- Copilot package V1
Phase 3:
- assisted folder workflows
- expanded formats
- OneDrive and SharePoint V2
- Copilot grounding V2
Phase 4:
- approved Graph, Copilot APIs or agent path
- only after governance decisions
SMALL_MODEL_EXECUTION_RULES.md must include:
- execute one backlog ID at a time
- read its dependencies
- inspect current code before editing
- do not widen scope
- do not clean unrelated files
- preserve API and UI compatibility unless explicitly changed
- add tests before or with the change
- run the named tests
- inspect the diff
- never commit secrets
- never introduce synthetic values into real data
- update continuity docs
- do not commit unless instructed
- stop on acceptance criteria failure
- report unverified browser behaviours
Also create a task prompt template:
.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md
The template must instruct a small model to:
1. Read one backlog item.
2. Verify prerequisites.
3. List intended edits.
4. Add or update tests.
5. Implement only that item.
6. Run tests.
7. inspect git diff.
8. verify acceptance criteria.
9. update project state.
10. stop without committing.
Do not implement any backlog item.
Stop after creating the backlog.

