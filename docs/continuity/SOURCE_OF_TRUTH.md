# Source of Truth

When documents disagree, the higher-ranked document wins. If a lower-ranked document needs to change as a result, record that as a decision; don't silently edit history.

## 1. Ranking of authoritative documents

| Rank | Document | Authoritative for |
|---|---|---|
| 1 | `docs/architecture/PWA_ARCHITECTURE_CHARTER.md` | Mandatory principles (data boundaries, readable source, PWA requirements, change control) |
| 2 | `docs/architecture/ADR_REGISTER.md` (including the "Owner answers" and "Owner approval" sections) | Architecture decisions and their status |
| 3 | `docs/continuity/DECISIONS.md` | Consolidated decision history (owner answers, phase-level decisions) |
| 4 | `docs/architecture/TARGET_ARCHITECTURE.md`, `DATA_AND_STORAGE_ARCHITECTURE.md`, `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md`, `COPILOT_AND_CHAT_ARCHITECTURE.md`, `MINIFIED_CODE_MIGRATION_STRATEGY.md` | Target design detail (ADRs added later override them where they conflict) |
| 5 | `docs/backlog/MASTER_BACKLOG.md` (83 items, corrected by validation) | What to build, item by item, with acceptance criteria |
| 6 | `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` | Order, dependencies, phase gates, release points |
| 7 | `docs/backlog/SMALL_MODEL_EXECUTION_RULES.md` + `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md` | How an item is executed |
| 8 | `docs/continuity/PROJECT_STATE.md` | **Current status** of every item, blockers, next task |
| 9 | `docs/continuity/NEXT_ACTIONS.md` | The next ≤ 15 items |
| 10 | `docs/backlog/DECISION_REGISTER.md` | Item-level decisions needed (§2) and taken during execution (§3) |
| 11 | `docs/backlog/RISK_REGISTER.md`, `docs/backlog/BACKLOG_VALIDATION.md`, `docs/backlog/DEPENDENCY_MAP.md` §3–6 | Risks, validation rationale, alternatives, high-risk sequences, approval blocks |
| 12 | `docs/assessment/*` | Evidence about the legacy code as of `1ca4319` (a fixed snapshot) |
| — | The code itself (`app/`, `tests/`, `tools/`) | What actually exists. When code and documents disagree about **current behaviour**, the code plus test results win, and the document gets corrected via a decision |

## 2. Superseded or non-authoritative files

| File | Status | Use instead |
|---|---|---|
| `docs/backlog/EXECUTION_SEQUENCE.md` | Superseded by validation | `FINAL_EXECUTION_SEQUENCE.md` |
| `docs/backlog/DEPENDENCY_MAP.md` §1–2 (tables) | Superseded (predate the splits) | `FINAL_EXECUTION_SEQUENCE.md` tables; §3–6 remain valid with split IDs read as their parts |
| `README.md` | Describes the legacy app; inaccurate (assessment §11) | Until DOC-01/DOC-03, use `SESSION_CONTEXT.md` |
| `docs/architecture.md`, `docs/architecture_diagram.drawio`, `docs/api-reference.md`, `docs/getting-started.md` | Legacy, unverified | Assessment documents (as evidence only) |
| `docs/architecture/{application_flow, data_model, logic_flow, Product_Source_of_Truth_2Jun2026, refactor-plan, review_proposal_workbench_end_to_end, sequence_flows, system_overview, traceability_map}.md` | Legacy; several describe code that isn't loaded (assessment U1–U5) | Target architecture documents |
| `docs/planning/*` (MASTER_SPRINT_PLAN, sprint_plan, V2_DELIVERY_PLAN, transformation backlog) | Superseded legacy plans | `MASTER_BACKLOG.md` |
| `docs/test-plans/*` | Legacy manual plans, never recorded as executed | `MANUAL_SMOKE_CHECKLIST.md` (TST-03) and item tests |
| `.kiro/**` | Steering for a previous agent tool | Charter + ADRs |
| `CONTRIBUTING.md` | Legacy contribution guide | `SMALL_MODEL_EXECUTION_RULES.md` |

These files are moved to `docs/history/` by CLN-03 or removed by CLN-02. Until then they stay in place, unedited.

## 3. Where things live

| Topic | Location |
|---|---|
| Architecture | `docs/architecture/TARGET_ARCHITECTURE.md` and the four companion documents; principles in the charter |
| Decisions | Architecture: `docs/architecture/ADR_REGISTER.md`. Consolidated history: `docs/continuity/DECISIONS.md`. Item-level: `docs/backlog/DECISION_REGISTER.md` |
| Backlog | `docs/backlog/MASTER_BACKLOG.md` (items), `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` (order) |
| Status | `docs/continuity/PROJECT_STATE.md` (per item), `docs/continuity/NEXT_ACTIONS.md` (queue), `docs/backlog/EXECUTION_LOG.md` (created by BAS-01; per-item execution lines) |
| Restart briefing | `docs/continuity/SESSION_CONTEXT.md` |
| Risks | `docs/backlog/RISK_REGISTER.md` |
| Release procedure | `docs/release/` (created by TST-03, REL-01A, REL-02) |
