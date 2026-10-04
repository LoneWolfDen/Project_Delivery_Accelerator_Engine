# Dependency Map

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Generated from | the 'Dependencies' field of every item in `MASTER_BACKLOG.md` (checked: no cycles, no item depends on a later phase) |

## 1. Prerequisites (complete table)

| ID | Phase | Depends on | Required by | Depth |
|---|---|---|---|---|
| BAS-01 | 0 | — | BAS-03, BAS-04 | 1 |
| BAS-02 | 0 | — | BAS-03, IMP-01 | 1 |
| BAS-03 | 0 | BAS-01, BAS-02 | CLN-02, MIG-01 | 2 |
| BAS-04 | 0 | BAS-01 | CLN-02, MIG-02 | 2 |
| TST-01 | 0 | — | BLD-01, CHT-01, SEC-01, TST-02 | 1 |
| TST-02 | 0 | TST-01 | REL-01 | 2 |
| SEC-01 | 0 | TST-01 | BLD-01 | 2 |
| CHT-01 | 0 | TST-01 | CHT-03, MIG-01, UI-04 | 2 |
| DOC-01 | 0 | — | CLN-01, CLN-02 | 1 |
| CLN-01 | 0 | DOC-01 | — | 2 |
| BLD-01 | 1 | TST-01, SEC-01 | BLD-02, PWA-01, SEC-02, UI-01 | 3 |
| SEC-02 | 1 | BLD-01 | PWA-02 | 4 |
| UI-01 | 1 | BLD-01 | UI-02 | 4 |
| UI-02 | 1 | UI-01 | DAT-05, DGN-01, UI-03 | 5 |
| DGN-01 | 1 | UI-02 | DAT-01 | 6 |
| DAT-01 | 1 | DGN-01 | DAT-02 | 7 |
| DAT-02 | 1 | DAT-01 | DAT-03, DAT-04, DAT-05, IMP-01, UI-03 | 8 |
| DAT-03 | 1 | DAT-02 | DAT-06, DGN-02 | 9 |
| DAT-04 | 1 | DAT-02 | — | 9 |
| DAT-05 | 1 | DAT-02, UI-02 | — | 9 |
| UI-03 | 1 | DAT-02, UI-02 | DAT-06, IMP-02 | 9 |
| DAT-06 | 1 | UI-03, DAT-03 | BAK-01 | 10 |
| BAK-01 | 1 | DAT-06 | BAK-02, EXP-01, PWA-03 | 11 |
| BAK-02 | 1 | BAK-01 | BAK-03, UI-07 | 12 |
| BAK-03 | 1 | BAK-02 | DOC-02, ODI-02 | 13 |
| IMP-01 | 1 | DAT-02, BAS-02 | CHT-02, IMP-02 | 9 |
| IMP-02 | 1 | IMP-01, UI-03 | IMP-03, IMP-04, ODI-01, UI-04 | 10 |
| IMP-03 | 1 | IMP-02 | IMP-05, MIG-01 | 11 |
| IMP-04 | 1 | IMP-02 | CLN-02, MIG-01 | 11 |
| IMP-05 | 1 | IMP-03 | IMP-06 | 12 |
| PWA-01 | 2 | BLD-01 | PWA-04 | 4 |
| PWA-04 | 2 | PWA-01 | DOC-02, PWA-02 | 5 |
| PWA-02 | 2 | PWA-04, SEC-02 | IMP-07, PWA-03 | 6 |
| PWA-03 | 2 | PWA-02, BAK-01 | DGN-02, ODI-02, REL-01 | 12 |
| IMP-06 | 2 | IMP-05 | EXP-02, IMP-07, ODI-02 | 13 |
| MIG-01 | 2 | IMP-03, IMP-04, BAS-03, CHT-01 | CLN-02, DAT-07, MIG-02, UI-05 | 12 |
| UI-04 | 2 | IMP-02, CHT-01 | CHT-03, UI-05, UI-06 | 11 |
| UI-05 | 2 | MIG-01, UI-04 | — | 13 |
| CHT-02 | 2 | IMP-01 | CHT-03 | 10 |
| CHT-03 | 2 | CHT-02, UI-04, CHT-01 | AI-01, CPL-01, UI-07 | 12 |
| DAT-07 | 2 | MIG-01 | MIG-02 | 13 |
| MIG-02 | 2 | MIG-01, DAT-07, BAS-04 | AI-04, CLN-02, UI-06 | 14 |
| UI-06 | 2 | MIG-02, UI-04 | AI-01, CPL-01, EXP-01, UI-07 | 15 |
| ODI-01 | 2 | IMP-02 | — | 11 |
| EXP-01 | 2 | UI-06, BAK-01 | EXP-02, EXP-03, UI-07 | 16 |
| EXP-02 | 2 | EXP-01, IMP-06 | CPL-01 | 17 |
| CPL-01 | 2 | EXP-02, CHT-03, UI-06 | CPL-02, DOC-02, EXP-03 | 18 |
| CPL-02 | 2 | CPL-01 | CPL-03 | 19 |
| BLD-02 | 2 | BLD-01 | DOC-02, REL-01 | 4 |
| UI-07 | 2 | UI-06, CHT-03, EXP-01, BAK-02 | UI-08 | 17 |
| DOC-02 | 2 | PWA-04, BAK-03, CPL-01, BLD-02 | DOC-03 | 19 |
| REL-01 | 2 | TST-02, PWA-03, BLD-02 | DOC-03 | 13 |
| CLN-02 | 2 | MIG-01, MIG-02, BAS-03, BAS-04, IMP-04, DOC-01 | CLN-03, DOC-03, REL-02 | 15 |
| DOC-03 | 2 | CLN-02, REL-01, DOC-02 | REL-02 | 20 |
| AI-01 | 3 | CHT-03, UI-06 | AI-02 | 16 |
| AI-02 | 3 | AI-01 | AI-03 | 17 |
| AI-03 | 3 | AI-02 | AI-04 | 18 |
| AI-04 | 3 | AI-03, MIG-02 | — | 19 |
| IMP-07 | 3 | IMP-06, PWA-02 | — | 14 |
| ODI-02 | 3 | IMP-06, PWA-03, BAK-03 | — | 14 |
| EXP-03 | 3 | EXP-01, CPL-01 | CPL-03 | 19 |
| CPL-03 | 3 | CPL-02, EXP-03 | CPL-04 | 20 |
| CPL-04 | 3 | CPL-03 | — | 21 |
| UI-08 | 3 | UI-07 | — | 18 |
| DGN-02 | 3 | DAT-03, PWA-03 | — | 13 |
| CLN-03 | 3 | CLN-02 | — | 16 |
| REL-02 | 3 | CLN-02, DOC-03 | — | 21 |
| GRA-01 | 4 | — | CPL-05, GRA-02 | 1 |
| GRA-02 | 4 | GRA-01 | GRA-03, GRA-04 | 2 |
| GRA-03 | 4 | GRA-02 | — | 3 |
| GRA-04 | 4 | GRA-02 | — | 3 |
| CPL-05 | 4 | GRA-01 | — | 2 |

Depth = length of the longest prerequisite chain ending at the item (1 = no prerequisites).

## 2. Parallel-safe items

Items in the same phase and the same depth have no dependency on each other and touch different files, so they may be executed in parallel **in separate branches** (merge one at a time, re-running `npm test` after each merge). Items that edit the same shared file (`app/js/ui/router.js`, `app/js/domain/validate.js`, `app/js/ui/views/project.js`, `app/js/import/pipeline.js`, `app/js/import/intake.js`) must be merged sequentially even when listed together.

| Phase | Depth | Parallel-safe set |
|---|---|---|
| 0 | 1 | BAS-01, BAS-02, DOC-01, TST-01 |
| 0 | 2 | BAS-03, BAS-04, CHT-01, CLN-01, SEC-01, TST-02 |
| 1 | 4 | SEC-02, UI-01 |
| 1 | 9 | DAT-03, DAT-04, DAT-05, IMP-01, UI-03 |
| 1 | 10 | DAT-06, IMP-02 |
| 1 | 11 | BAK-01, IMP-03, IMP-04 |
| 1 | 12 | BAK-02, IMP-05 |
| 2 | 4 | BLD-02, PWA-01 |
| 2 | 11 | ODI-01, UI-04 |
| 2 | 12 | CHT-03, MIG-01, PWA-03 |
| 2 | 13 | DAT-07, IMP-06, REL-01, UI-05 |
| 2 | 15 | CLN-02, UI-06 |
| 2 | 17 | EXP-02, UI-07 |
| 2 | 19 | CPL-02, DOC-02 |
| 3 | 14 | IMP-07, ODI-02 |
| 3 | 16 | AI-01, CLN-03 |
| 3 | 18 | AI-03, UI-08 |
| 3 | 19 | AI-04, EXP-03 |
| 3 | 21 | CPL-04, REL-02 |
| 4 | 2 | CPL-05, GRA-02 |
| 4 | 3 | GRA-03, GRA-04 |

## 3. Mutually exclusive alternatives

| Decision point | Alternatives (choose one) | Items affected | Rule |
|---|---|---|---|
| Hosting route per organisation | (a) static HTTPS host such as GitHub Pages via `REL-01` `deploy-static` with `DEPLOY_PAGES=true`; (b) another organisation-approved static host (deploy `app/` manually); (c) release zip + launcher only (`BLD-02`) | REL-01, BLD-02, DOC-02, DOC-03 | Configuration only; the app code must be identical for all three (ADR-024). Never hard-code one. |
| OpenRouter from the browser | (a) direct browser call works (expected); (b) CORS blocked: then **stop**. The options are a proxy server (contradicts ADR-001), dropping OpenRouter, or Copilot-only. Each needs a new ADR | AI-02 → AI-03, AI-04 | AI-02 spike result decides; no proxy may be added inside AI-02. |
| Copilot agent route | (a) user-configured agent from the kit (CPL-04, no API); (b) programmatic agent/API/connector (CPL-05) | CPL-04, CPL-05 | (b) only if an API becomes available and is approved (Q-E: none today). (a) stays valid regardless. |
| SharePoint/OneDrive input route | (a) V1 file pick from synced folder (ODI-01); (b) V2 linked folder (ODI-02, Chromium); (c) V3 Microsoft picker (GRA-03) | ODI-01, ODI-02, GRA-03 | Not exclusive in code (fallback chain c → b → a), but each organisation documents one primary route. |
| Legacy security | (a) patch legacy (ADR-021); (b) retire it unpatched (ADR-023) | CLN-02 | **Decided: (b).** ADR-021 superseded. |
| Application access control | (a) no app authentication (ADR-020); (b) passphrase app lock | — | (a) for V1/V2; (b) needs a new ADR and item. |

## 4. High-risk sequences (must not be reordered)

| Sequence | Why it is high risk | Guard |
|---|---|---|
| `SEC-01` → `BLD-01` → every `app/` item | Code written before the forbidden-API check could include HTML sinks or outbound calls | `npm run check` in CI from TST-02 onward |
| `PWA-04` → `PWA-02` → `PWA-03` | A service worker without a recovery page can pin a broken release on non-technical users' machines (charter §10) | PWA-02 depends on PWA-04; PWA-02 must not be tagged in a release unless PWA-04 shipped in the same or earlier release |
| `BAK-01` → `BAK-02` → `BAK-03` → `PWA-03` → `ODI-02` (first schema migration 1 → 2) | Storage migration without a tested backup/restore and an update prompt risks data loss | ODI-02 depends on PWA-03 and BAK-03; release notes must flag the schema change |
| `DAT-06` before any delete or reset UI | Deletion without Trash/typed confirmation repeats legacy H-6/M-5 | Only `emptyTrash` and reset may delete records (DAT-06 acceptance) |
| `BAS-03`, `BAS-04` → `MIG-01`, `MIG-02` → `CLN-02` | Removing legacy before goldens and ports exist loses the only definition of working behaviour | CLN-02 depends on all four; tag `legacy-final` first |
| `CLN-02` → `REL-02` (publication) | Publishing while legacy code with BLOCKER vulnerabilities is in the tree (ADR-023) | REL-02 depends on CLN-02; visibility changed by owner only |
| `AI-01` → `AI-02` | Network code before the consent guard could transmit data silently | AI-02 depends on AI-01; interception test in AI-02 |
| `EXP-01` edits the SEC-01 allow-list | An over-broad allow-list entry would silently weaken XSS protection | Allow-list entry limited to `outerHTML` read in `app/js/exports/html.js`; reviewer checks the diff of `tools/check-forbidden-apis.mjs` |
| `TST-02` replaces the legacy CI | Until TST-02 lands there is no green/red signal | Do TST-01, TST-02 first in Phase 0 |

## 5. Items blocked by administrator or organisational approval

| ID | Blocked on | Fully or partly |
|---|---|---|
| GRA-01 | Tenant administrator answers for prerequisites P1–P8 | Fully: owner-driven documentation |
| GRA-02, GRA-03, GRA-04 | GRA-01 accepted (Entra registration, consent, hosting approval) | Fully |
| CPL-05 | A Copilot API being available and approved (none today, Q-E) | Fully |
| AI-02 (and AI-03, AI-04) | Organisation permission to send selected content to OpenRouter (owner confirms) | Partly: code can be built and tested with mocked routes; real use needs the permission |
| CPL-04 | Tenant policy allowing users to create agents with SharePoint/OneDrive knowledge | Partly: export can be built; manual verification needs the policy |
| REL-01 `deploy-static` | Enabling GitHub Pages (permitted in owner's organisation, Q-D) | Partly: optional job |
| BLD-02, PWA-01 (install), ODI-01, ODI-02, EXP-03 manual checks | Corporate device policy (script files, web-app install, File System Access) | Verification only |
| REL-02 | Owner (and employer, if applicable) approval to publish | Fully, for the visibility change |

## 6. Items blocked by missing source code

**None.** The assessment found no minified, obfuscated or source-less application code (`MINIFIED_AND_GENERATED_CODE_REGISTER.md` §1). Notes:

- Items that port legacy logic (BAS-03, BAS-04, MIG-01, MIG-02, IMP-03, IMP-04) read readable legacy Python. After CLN-02 that source is reachable only via tag `legacy-final`: use `git worktree add ../pdae-legacy legacy-final`.
- Two items need third-party source obtained from official releases, verified by hash and recorded in `app/vendor/VENDOR_MANIFEST.json`: IMP-07 (`pdf.js`) and GRA-02 (MSAL browser, blocked).
