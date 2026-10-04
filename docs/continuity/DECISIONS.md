# Decisions

Consolidated decision history for the PWA rebuild. **Append only.** Never edit or delete a row; record a change as a new row whose Status says `Supersedes D-nn`.
Detailed architecture rationale lives in `docs/architecture/ADR_REGISTER.md`. Item-level decisions taken during execution are logged in `docs/backlog/DECISION_REGISTER.md` §3 and summarised here at each phase gate.

| ID | Date | Decision | Reason | Impact | Status | Evidence |
|---|---|---|---|---|---|---|
| D-01 | 2026-10-01 | Assess the repository read-only against the PWA architecture charter before changing anything | Charter is mandatory guidance; README claims weren't trusted | Six assessment documents; no code changes | Done | `docs/assessment/*` (commit `8df93bd`) |
| D-02 | 2026-10-02 | Users are non-technical: start-up and every operation through the UI, no terminal (OD-1) | Owner answer | Rules out terminal-based start; favours browser-only app | Accepted | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §14 |
| D-03 | 2026-10-02 | Neither legacy UI is kept; both are disposable scaffolding (OD-2) | Owner answer | New UI; legacy UIs reference only | Accepted | same, OD-2 |
| D-04 | 2026-10-02 | External-reviewer feedback link out of scope (OD-3) | Owner answer | No network-exposed features | Accepted | OD-3; ADR-017 |
| D-05 | 2026-10-02 | Docker and Compose out of scope (OD-4) | Owner answer; Docker broken | CLN-01 removes them | Accepted | OD-4; ADR-015 |
| D-06 | 2026-10-02 | MIT licence; repository intended to become public later (OD-5) | Owner answer | DOC-01 adds LICENSE; REL-02 publication checklist | Accepted | OD-5; ADR-016 |
| D-07 | 2026-10-02 | OpenRouter is the only external AI provider; Copilot must work without an API (OD-6) | Owner answer | AI-01–04; CPL-* | Accepted | OD-6; ADR-006, ADR-007 |
| D-08 | 2026-10-02 | Commit the charter and prompts to the assessment branch (OD-7) | Owner answer | Governing docs under version control | Done | commit `491fc7e` |
| D-09 | 2026-10-02 | Treat the cross-site attack (H-3) as unmitigated (OD-8) | Owner can't assess | Target removes the cause (no local API) | Accepted | OD-8 |
| D-10 | 2026-10-04 | Target: browser-only, no-build PWA; retire the Python server | No healthy build to keep; non-technical users; removes server vulnerability classes | Whole backlog | Accepted | ADR-001, ADR-002; `TARGET_ARCHITECTURE.md` §1 |
| D-11 | 2026-10-04 | Deferred features (proposals, presales, reconciliation, synthesis, decision log, diagrams, phases) not in first release (Q-A) | "Each of them breaks at some point" | Smaller first scope | Accepted | ADR-012 |
| D-12 | 2026-10-04 | No migration of legacy data (Q-B) | No real data in legacy app | Users re-import documents | Accepted | ADR-013 |
| D-13 | 2026-10-04 | Retire legacy early, unpatched; no publication before removal (Q-C) | Owner doesn't use legacy | BAS-03/04 capture behaviour; CLN-02 removes; REL-02 depends on CLN-02 | Accepted (supersedes ADR-021) | ADR-023 |
| D-14 | 2026-10-04 | Hosting-neutral app; GitHub allowed in owner's organisation but never assumed (Q-D) | Owner answer | Relative paths; launcher route; optional deploy job | Accepted | ADR-024 |
| D-15 | 2026-10-04 | Copilot via licensed desktop surfaces (desktop app, Teams, SharePoint, Agent Builder); no API (Q-E) | All users have M365 Copilot premium, no API | CPL-01–04 at P2; CPL-05 BLOCKED | Accepted | ADR-025 |
| D-16 | 2026-10-04 | All Proposed ADRs accepted; architecture authority delegated to the assistant acting as enterprise/solution architect and full-stack developer | Owner instruction | ADR-001–004, 008–011, 014, 018, 020, 022 Accepted | Accepted | `ADR_REGISTER.md` "Owner approval…"; backlog BD-15 |
| D-17 | 2026-10-04 | Backlog validated and corrected (72 → 83 items); `FINAL_EXECUTION_SEQUENCE.md` authoritative | Review found oversized tasks, premature publication, untestable criteria | Execution follows the final sequence | Accepted | `docs/backlog/BACKLOG_VALIDATION.md` |
| D-18 | 2026-10-04 | Continuity documents created; `docs/continuity/PROJECT_STATE.md` is the item-status record | Prompt 05 | Executors update it per item | Accepted | `docs/continuity/*` |
