# Decision Register (backlog)

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Relationship to ADRs | Architecture decisions live in `docs/architecture/ADR_REGISTER.md`. This register records (1) which ADRs the backlog depends on, (2) decisions that individual items need before or during execution, and (3) an append-only log of decisions taken while executing items. |
| Rule | **Append only.** Never edit or delete an earlier row; supersede it with a new row that references it. |

## 1. Architecture decisions the backlog relies on

| ADR | Status (2026-10-04) | Used by |
|---|---|---|
| ADR-001 Browser-only PWA, retire Python server | Proposed (implied by OD-1, OD-2, OD-4) | All `app/` items, CLN-02 |
| ADR-002 No-build, Node dev tooling only | Proposed | TST-01, BLD-01 |
| ADR-003 IndexedDB, schema versions, quarantine, Trash | Proposed | DAT-*, IMP-02, ODI-02 |
| ADR-004 Backup file format | Proposed | BAK-* |
| ADR-005 Hosting (amended by ADR-024) | Proposed / amended | BLD-02, REL-01 |
| ADR-006 OpenRouter only, off by default, consent | Accepted (provider, OD-6) | AI-* |
| ADR-007 Copilot Pattern A (amended by ADR-025) | Accepted (OD-6) | CPL-* |
| ADR-008 Deterministic retrieval, labels, citations | Proposed | CHT-*, MIG-02, UI-04–06, AI-03 |
| ADR-009 No runtime third-party code except pdf.js | Proposed | IMP-06, IMP-07, EXP-02 |
| ADR-010 CSP, Trusted Types, no innerHTML | Proposed | SEC-*, UI-01, BLD-01 |
| ADR-011 Service-worker strategy and kill-switch | Proposed | PWA-* |
| ADR-012 First-release scope | **Accepted (Q-A)** | MIG-02, DAT-07 |
| ADR-013 No legacy data migration | **Accepted (Q-B)** | — |
| ADR-015 Remove Docker | Accepted (OD-4) | CLN-01 |
| ADR-016 MIT licence | Accepted (OD-5) | DOC-01, REL-02 |
| ADR-018 Testing approach | Proposed | TST-*, all tests |
| ADR-019 Graph only after P1–P8 | Blocked | GRA-* |
| ADR-020 No app authentication in V1/V2 | Proposed | — |
| ADR-021 Patch legacy | **Superseded by ADR-023** | — |
| ADR-022 Fixed local port 8765 | Proposed | TST-01, BLD-02 |
| ADR-023 Retire legacy early, unpatched; no publication before removal | **Accepted (Q-C)** | BAS-*, CLN-02, REL-02 |
| ADR-024 Hosting-neutral app | **Accepted (Q-D)** | BLD-01, PWA-01, REL-01, DOC-02, DOC-03 |
| ADR-025 Copilot via licensed desktop surfaces, Agent Builder kit, no API | **Accepted (Q-E)** | CPL-01–05 |

**Owner action recommended before Phase 1:** confirm the Proposed ADRs above, or name the ones to revisit. The backlog assumes them.

## 2. Decisions needed by specific items

| ID | Decision needed | Needed by | Who decides | Default if not decided |
|---|---|---|---|---|
| BD-01 | Copyright holder name for `LICENSE` | DOC-01 | Owner | Item cannot complete |
| BD-02 | Exact Node LTS major and Playwright version to pin | TST-01 | Executing model proposes; owner accepts | Current Node LTS; latest Playwright at execution time, recorded here |
| BD-03 | Confirmation that nobody runs the legacy app before removal | CLN-02 | Owner | Item cannot complete |
| BD-04 | Accept each listed parity difference in `ACCEPTED_DIFFERENCES.md` | MIG-01, MIG-02, IMP-03 | Owner | Item cannot complete while unaccepted differences exist |
| BD-05 | Enable optional static deployment (`DEPLOY_PAGES`) | REL-01 | Owner | Off (zip + launcher only) |
| BD-06 | Copilot clipboard character limit (observed) | CPL-01 | Owner trial | 12,000 characters |
| BD-07 | Agent Builder instruction limit and knowledge-source options (observed) | CPL-04 | Owner trial | 8,000 characters |
| BD-08 | OpenRouter browser CORS result | AI-02 | Spike evidence | Stop if blocked (see DEPENDENCY_MAP §3) |
| BD-09 | Which content classes may be sent to OpenRouter in the owner's organisation, and default model ID | AI-02 | Owner / organisation policy | AI stays off |
| BD-10 | Import size limits (warn 25 MB, refuse 100 MB) | IMP-05 | Owner | Defaults apply |
| BD-11 | Trash retention (30 days, never auto-deleted without prompt) | DAT-06 | Owner | Default applies |
| BD-12 | Icon design | PWA-01 | Owner | Simple monogram |
| BD-13 | Publication approval | REL-02 | Owner (and employer, if applicable) | Repository stays private |
| BD-14 | Whether to keep `sample_data/` after fixtures exist | CLN-03 | Owner | Remove (copies in `tests/fixtures/synthetic/`) |

## 3. Execution decision log (append below; newest last)

| Date | Decision ID | Item | Decision | Evidence | Supersedes |
|---|---|---|---|---|---|
| 2026-10-04 | BD-00 | — | Backlog created from assessment and architecture with owner answers Q-A to Q-E | `ADR_REGISTER.md` owner answers section | — |
| 2026-10-04 | BD-15 | — | Owner accepted all Proposed ADRs and delegated architecture decisions to the assistant acting as enterprise/solution architect and full-stack developer | Owner message 2026-10-04; `ADR_REGISTER.md` "Owner approval of proposed decisions" | Statuses in §1 marked Proposed |
| 2026-10-04 | BD-01 | DOC-01 | Copyright holder supplied by owner: "Vamsi Yedlapalli / LoneWoldDen". The GitHub account is spelled `LoneWolfDen`, so DOC-01 must confirm the exact spelling with the owner before writing `LICENSE` | Owner message 2026-10-04 | — |
| 2026-10-04 | BD-02 | TST-01 | Node `>=22` (`engines`, `.nvmrc` = 22; local v24.18.0); `@playwright/test` pinned exactly to 1.63.0 (latest at execution), installed with `--ignore-scripts` (no browser download in this item) | `npm view @playwright/test version` → 1.63.0; `package.json` | — |
| 2026-10-04 | BD-16 | TST-01 | `test:unit` runs `node --test "tests/unit/**/*.test.mjs"` instead of the backlog's `node --test tests/unit/`, which on Node 24 treats the folder as one failing test. Later items' "`npm run test:unit`" commands are unaffected | Reproduced in scratch dir: directory argument → 1 failed test; glob → pass | — |
| 2026-10-04 | BD-17 | TST-01 | `test:e2e` runs `playwright test --pass-with-no-tests` (needed until the first spec exists, as TST-02 anticipates); `serve-dev` exposes `GET /__serve-dev-health` (200) so Playwright's `webServer` readiness check works while `app/` has no `index.html` | `playwright.config.mjs`; unit test 'health endpoint…' | — |
