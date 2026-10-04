# Backlog Validation

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Reviewer stance | Critical architecture and release review (per `.claude/prompts/04-backlog-validation.md`) |
| Inputs | `docs/assessment/*`, `docs/architecture/*` (incl. owner approvals in `ADR_REGISTER.md`), `docs/backlog/*` as created on 2026-10-04 |
| Outcome | **Backlog approved with corrections.** 9 items split into 19, 1 item added (TST-03), 17 items corrected, 2 global rules added. `MASTER_BACKLOG.md` updated (72 → 83 items); `FINAL_EXECUTION_SEQUENCE.md` created and authoritative. |
| Files not changed | `EXECUTION_SEQUENCE.md`, `DEPENDENCY_MAP.md`, `RISK_REGISTER.md`, `SMALL_MODEL_EXECUTION_RULES.md` were left as they were, because only `MASTER_BACKLOG.md` may be corrected in this step. Their superseded parts are named in `FINAL_EXECUTION_SEQUENCE.md`, and the rule additions are placed in the `MASTER_BACKLOG.md` header, which every executor reads. |

---

## 1. Checks performed

| Check | Result | Evidence / action |
|---|---|---|
| Circular dependencies | **None** | Topological sort of all dependency fields (before and after corrections) |
| Dependencies pointing to a later phase | **None** | Checked programmatically |
| Dependencies to non-existent IDs | **None** after V-29 | Split IDs re-pointed |
| Every item has all 28 required fields | **Yes** (83/83) | Field-presence check on the rendered file |
| Tasks too large for one contained cycle | **9 found** | V-01 to V-09 (splits) |
| Tasks requiring hidden interpretation | **6 found** | V-14, V-22, V-24, V-26, MIG-02 labelling (V-03), DAT-06 store list (V-07) |
| Unsafe ordering | **3 found** | V-18 (update prompt before restore replace), V-09 (public deploy before publication checklist), V-12 (needless coupling, not unsafe) |
| Unnecessary framework migrations | **None** | Only dev-only Node/Playwright; no runtime framework (ADR-002) |
| Premature cloud integration | **1 found** | V-09: GitHub Pages publishes the app publicly, so it moved after REL-02 |
| Premature Microsoft Graph work | **None** | GRA-* BLOCKED with an entry criterion |
| Code migration without characterization tests | **None** | MIG-01A/MIG-02A parity against BAS-03 goldens; V-03 made the review mapping deterministic |
| Storage migration without backup | **1 latent issue** | V-13: additive record fields between releases could quarantine valid data. ODI-02A already gated by BAK-03 and PWA-03 |
| Service-worker change without recovery | **Resolved before review**, reinforced | PWA-04 precedes PWA-02; V-06 splits the generator from the worker; release R0.2 rule |
| Copilot assumptions without licence/tenant evidence | **Partly evidenced** | Licence: owner statement (Q-E), not a tenant record. Limits (12,000 / 8,000 chars) are settings with mandatory owner trials (BD-06, BD-07). V-25 prevents help text claiming untested behaviour. No change to CPL scope |
| OneDrive/SharePoint assumptions without auth evidence | **None** | V1/V2 use only local file APIs and the user's sync client; Graph BLOCKED |
| Tasks silently changing data boundaries | **2 found** | V-19 (kill-switch request to host), V-05 (clipboard history/cloud clipboard) |
| Tasks missing manual browser validation | **Gap found** | V-10: TST-03 checklist plus a rule that user-visible items append steps |
| Tasks missing rollback | **Gap for released items** | V-27 global rule: revert + patch release + kill-switch |
| Security work that could break the app | **2 found** | V-20 (namespace URIs vs URL rule), V-21 (pdf.js vs CSP and Trusted Types) |
| Repository cleanup scheduled too early | **None** | CLN-01 (Docker, broken, OD-4) early is safe. CLN-02 after parity per ADR-023 (owner doesn't run legacy). CLN-03 after CLN-02 |
| Duplicate items | **1 overlap** | V-26 (help text owned by both ODI-01 and DOC-02) |
| Untestable acceptance criteria | **4 found** | V-11 (logging), V-15 (email HTML), V-16 (no generated sentences), V-17 (byte-identical icons) |
| Statements not supported by evidence | **3 found** | V-23 (Node ≥ 18 claim), V-22 (deprecated Playwright API), V-09 (Pages visibility omitted) |

## 2. Challenged items

| # | Original ID | Issue | Recommended correction (applied) | Dependency change | Risk change |
|---|---|---|---|---|---|
| V-01 | IMP-02 | Too large: storage repos, atomic keep, duplicate detection, intake, preview UI and sources view in one cycle | Split into **IMP-02A** (storage: `keepPrepared`, `findDuplicate`, atomicity test) and **IMP-02B** (intake and preview UI) | IMP-02A ← IMP-01; IMP-02B ← IMP-02A, UI-03; former dependents now depend on IMP-02B | Lower: atomicity proven independently of UI |
| V-02 | MIG-01 | Too large: pure port, parity tests, storage, keep-time wiring, re-run | Split into **MIG-01A** (pure port + parity) and **MIG-01B** (store on keep, re-run via Trash) | MIG-01A ← IMP-03, IMP-04, BAS-03, CHT-01; MIG-01B ← MIG-01A, IMP-02B, DAT-06A; UI-05, DAT-07 ← MIG-01B | Lower: parity isolated from persistence; re-run can no longer delete items |
| V-03 | MIG-02 | Too large, and "maps 1:1 … or documented mapping" needed interpretation | Split into **MIG-02A** (pure engine; **four explicit labelling rules** for every legacy string; unclassifiable strings fail parity) and **MIG-02B** (persist against snapshots) | MIG-02A ← MIG-01A, BAS-04; MIG-02B ← MIG-02A, DAT-07; UI-06, AI-04, EXP-01A ← MIG-02B; CLN-02 ← MIG-01A, MIG-02A | Lower: fabricated-finding risk testable rule by rule |
| V-04 | EXP-01 | Too large: four formats, manifest, notice, view, records **and** a security allow-list change | Split into **EXP-01A** (pure builders), **EXP-01B** (HTML export + narrowly scoped allow-list entry with a negative test) and **EXP-01C** (view, boundary notice, ExportRecord) | Chain A → B → C; dependents point to EXP-01C | Lower: the allow-list change is reviewable on its own |
| V-05 | CPL-01 | Too large; clipboard boundary not disclosed; WebKit clipboard e2e not feasible | Split into **CPL-01A** (pure builder, splitter) and **CPL-01B** (dialog, clipboard, ZIP); notice adds clipboard-history/sync warning; clipboard read-back test Chromium-only | CPL-01A ← EXP-01A, CHT-03, MIG-02B; CPL-01B ← CPL-01A, EXP-02, UI-06 | Lower: data-boundary disclosure complete |
| V-06 | PWA-02 | Generator and worker together; the generator can be verified with zero user impact first | Split into **PWA-02A** (precache generator + CI freshness, no worker) and **PWA-02B** (worker, registration, offline, kill-switch integration) | PWA-02A ← PWA-04; PWA-02B ← PWA-02A, SEC-02; release R0.2 requires PWA-04, 02A, 02B, 03 | Lower: smaller service-worker change |
| V-07 | DAT-06 | Too large; "all stores with `projectId` index" would include the `trash` store itself | Split into **DAT-06A** (Trash, Undo, restore; **explicit store list**) and **DAT-06B** (typed permanent delete, expiry prompt, reset) | DAT-06A ← UI-03, DAT-03; DAT-06B ← DAT-06A, DAT-05; BAK-01 ← DAT-06B | Lower: no recursive trash bug; deletion paths auditable |
| V-08 | ODI-02 | Mixed the first schema migration with a Chromium-only feature; unnecessary dependency on DOCX | Split into **ODI-02A** (migration 1 → 2 only, four migration cases, release notes) and **ODI-02B** (connector and UI) | ODI-02A ← PWA-03, BAK-03, REL-01A; ODI-02B ← ODI-02A, IMP-02B (IMP-06 dependency removed) | Lower: migration verified independently of feature |
| V-09 | REL-01 | Optional GitHub Pages deploy sat in Phase 2, but **Pages sites are publicly reachable** (except private Pages on Enterprise plans). That would publish the app before the publication checklist | Split into **REL-01A** (checklist + release zip; private assets) and **REL-01B** (optional static deploy, Phase 3, after REL-02, hosting-neutral doc) | REL-01A ← TST-02, PWA-03, BLD-02, TST-03; REL-01B ← REL-01A, REL-02 | Removes premature publication |
| V-10 | (new) TST-03 | No single real-browser smoke check before gates and releases | Added **TST-03** manual smoke checklist; MASTER header rule: user-visible items append steps | TST-03 ← BAK-02, IMP-02B; REL-01A ← TST-03 | Lower: catches policy and real-dialog differences |
| V-11 | DGN-01 | "No log call passes document text (grep review)" isn't testable | `log(level, code, module, refs)` with **no free-text parameter**; refs values limited to numbers and IDs | — | Lower: content-free logging by construction |
| V-12 | DGN-01 | Depended on UI-02 (router) though the banner only needs the DOM builder; lengthened the storage chain | Depend on UI-01 only | DGN-01 ← UI-01 | Neutral; shorter path |
| V-13 | DAT-02 (global) | Validators would reject records stored by earlier releases once later items add fields, sending valid data to quarantine after an update | Schema-evolution rule in DAT-02 and the MASTER header: new fields optional with defaults; unknown fields ignored; required or renamed fields need a migration item | — | Prevents silent data set-aside after updates |
| V-14 | BAS-03 | Legacy code writes `projects_data` relative to the working directory; normalisation and call mapping unspecified | Run in a fresh temp working directory; explicit normalisation keys; explicit call mapping, with deviations recorded in the script header | — | Lower: deterministic goldens, no stray files |
| V-15 | IMP-04 | "No HTML from emails reaches the live DOM (code review)" isn't testable | e2e with `<img id="pwned" …>` email body: `#pwned` absent, no dialog | — | Lower |
| V-16 | CHT-03 / DAT-07 | "Zero generated sentences" untestable; snapshot scope referenced before snapshots exist | Criterion: every evidence text is an exact chunk substring, and other text comes from a fixed template list. Snapshot scope moved to DAT-07, which now edits `ask.js` | DAT-07 ← MIG-01B, CHT-03 | Lower |
| V-17 | PWA-01 | Byte-identical PNG regeneration isn't reproducible across platforms | Icons generated once (shapes only) and committed; acceptance checks dimensions | — | Neutral |
| V-18 | PWA-03 | Update prompt offered "backup first" before replace-restore existed | Depend on BAK-03 | PWA-03 ← PWA-02B, BAK-03 | Lower |
| V-19 | PWA-04 | Data-boundary impact said "None" although each start requests `kill-switch.json` from the host | Boundary impact stated; disclosed in help (V-25) | — | Transparency improved |
| V-20 | SEC-01 | The "no http(s) literal" rule would fail DOCX parsing (`http://schemas.openxmlformats.org/…`) and SVG creation (`http://www.w3.org/2000/svg`), tempting a blanket allow | Allow-list XML namespace URI constants explicitly | — | Prevents an over-broad workaround |
| V-21 | IMP-07 | pdf.js defaults conflict with CSP (eval for fonts) and Trusted Types (worker URL) | `isEvalSupported:false`; app creates the worker via the trusted `scriptURL` and passes `workerPort`; zero-violation acceptance | — | Prevents security controls breaking PDF import |
| V-22 | UI-07 | "Fix defects found" is open-ended; `page.accessibility.snapshot()` is deprecated | Test-only item that stops with a defect list (fix items created per defect); use `toHaveAccessibleName` | UI-07 no longer edits view files | Lower: no unbounded edits |
| V-23 | TST-01 / IMP-06 | "Node ≥ 18 has `DecompressionStream`": `'deflate-raw'` isn't available in older Node lines | `engines: node >= 22`, `.nvmrc` = 22; verified locally on v24.18.0 | — | Removes a false environmental assumption |
| V-24 | BLD-02 | "Refuse if port busy" had no method | OS-specific commands specified | — | Neutral |
| V-25 | DOC-02 | Help could describe Copilot behaviour before the owner's trial; kill-switch request undisclosed | Copilot section written from the recorded trial, otherwise "Not yet tested in your organisation"; disclose the kill-switch request | — | No unverified claims to users |
| V-26 | ODI-01 | Duplicated DOC-02's help responsibility via "help.js (new or existing)" | Help text removed from ODI-01 | — | Removes a file conflict |
| V-27 | (global) rollback | Default rollback `git revert` doesn't reach users once a release is installed | MASTER header rule: revert + patch release + update prompt; kill-switch/reset if broken | — | Rollback now real for released items |
| V-28 | (global) shared files | Parallel-safe sets didn't account for files many items edit | MASTER header rule lists shared files that forbid parallel execution | — | Fewer merge conflicts |
| V-29 | (all) | Free-text references to split IDs | Re-pointed to the correct part | — | Neutral |

## 3. Challenged and confirmed without change

| Item(s) | Challenge | Conclusion |
|---|---|---|
| CLN-02 in Phase 2 | Cleanup too early? | No. ADR-023 (owner doesn't use legacy). It runs after the parity items, the tag keeps the old app recoverable, and publication depends on it |
| CLN-01 in Phase 0 | Cleanup too early? | No. The Docker path is broken (D-1) and out of scope (OD-4); it touches no runtime code |
| TST-02 removes legacy CI jobs | Losing coverage? | No. The legacy jobs haven't passed in 200 runs and never executed a test (T-1) |
| AI-01 → AI-04 in Phase 3 (P2) | Should OpenRouter be earlier (OD-6)? | No. The app must be useful without AI (charter §9). The consent guard precedes network code, and the CORS spike may stop the chain |
| CPL-01A/B, CPL-02 in Phase 2 at P2 | Priority/phase mismatch? | Intentional: the prompt's priority rules make Copilot packages P2, and its phase plan puts Copilot package V1 in Phase 2 |
| CPL-04 Agent Builder kit | Premature agent work (P3 class)? | No. It's an export file; the user builds the agent manually through licensed UI (ADR-025). No API, connector or programmatic agent. Tenant-policy check is manual verification |
| EXP-02 depends on IMP-06 | Unnecessary coupling? | Accepted: the ZIP writer's round-trip test reuses the ZIP reader, avoiding a second test reader |
| DAT-01 `?test=1` hook | Test hook in production code? | Accepted as low risk: same-origin only, exposes storage functions the page already has, and creates no new capability. Revisit if an attacker model with script access appears (that model already has full access) |
| GRA-01 to GRA-04, CPL-05 | Premature Graph/Copilot API? | No. BLOCKED, with entry criteria and no partial work allowed |
| Phase 1 size (23 items) | Phase too large? | Accepted: the items are small and sequential, with an internal preview point |

## 4. Residual risks after validation

- Corporate browser policy (install, launchers, File System Access, OneDrive client) can only be confirmed by the owner's manual checks (R-04, R-15).
- OpenRouter browser access is unproven until the AI-02 spike (R-06).
- Copilot input and Agent Builder limits are unproven until the owner's trials (R-09).
- Real accessibility defects are unknown until UI-07 runs. Fix items will be created then.

## 5. Next action

Execute **BAS-01** using `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`, following `FINAL_EXECUTION_SEQUENCE.md`.
