# V2 Full-Spec Delivery Plan
### Review & Proposal Workbench — Complete v2 UI Implementation

**Spec source:** `docs/architecture/review_proposal_workbench_end_to_end.md`
**Parent plan:** `docs/planning/MASTER_SPRINT_PLAN.md`
**Created:** 2 June 2026
**Status:** Active — authoritative plan for all v2 UI work

---

## Purpose

The spec (§2) explicitly scopes the target architecture to **v2 UI and v2 workflows**.
v1 (`static/index.html`) is the fallback / baseline.
v2 (`static/v2/dashboard_v2.html`) is the primary delivery surface.

This document defines what must be built, sprint by sprint, to make v2 fully
satisfy the spec's intent — from Ingest through to Forward Guidance.

---

## Ground Rules

| Rule | Detail |
|---|---|
| Backend is complete | Every API, model, and DB change needed is already shipped. This plan is **UI-only**. |
| Source of logic | Port from `static/index.html` (v1). Do not rewrite logic — adapt it to v2's CSS/token system. |
| No new backend work | If something is missing from v2, it is a UI gap, not a backend gap. |
| One tab = one sprint = one PR | Each sprint delivers one complete tab to production quality. |
| Exit gate before next sprint | Do not start Sprint N+1 until Sprint N passes its exit gate. |
| v2 design tokens | Use v2's existing CSS variables and component classes throughout. Do not copy v1's dark-theme overrides. |
| Regression safety | v1 must remain fully functional throughout. No changes to `static/index.html`. |
| Offline-first | Every tab must work with `ai_backend = "files_only"`. |

---

## Current v2 State vs Target

### What v2 has today

| Area | State | Detail |
|---|---|---|
| TABS | ❌ Incomplete | Only `['dashboard','versions','reviews']` — 3 of 9 needed |
| Dashboard tab | ✅ Solid | Stats, context selector, risk trend chart, project create/select |
| Versions tab | ⚠️ Partial | Phase tree, inline compare — missing readiness badges, artifact inventory, set-active-review, detail trigger |
| Reviews tab | ⚠️ Partial | List with R1/R2/R3 labels, sort — missing everything from S2 onwards |
| Compare module | ✅ Complete | Full version + review side-by-side diff (`compare.js`, 804 lines) |
| Separate JS modules | ✅ Present | `api.js`, `state.js`, `accordion.js`, `dashboard.js`, `search.js`, `summary.js` |
| Ingest tab | ❌ Missing | Entire tab absent |
| Intelligence tab | ❌ Missing | Entire tab absent |
| Proposal/Presales tab | ❌ Missing | Entire proposal workflow absent |
| Phases tab | ❌ Missing | Entire tab absent |
| Admin tab | ❌ Missing | Required for AI backend configuration |
| Settings tab | ❌ Missing | User preferences absent |

### What v2 needs to reach full spec

```
v2 current:  Dashboard · Versions (partial) · Reviews (partial)
v2 target:   Dashboard · Ingest · Intelligence · Versions (complete) · Reviews (complete)
             · Proposal · Phases · Admin
```

---

## Spec Requirement → Sprint Mapping

| Spec Section | Requirement | Sprint |
|---|---|---|
| §6.1 Ingest and Version | User knows what artifacts are included | V2-S1 |
| §8.1 Version Context Builder | Artifact inventory visible | V2-S1, V2-S2 |
| §6.2 Review | Persona, prompt, top risks visible immediately | V2-S3 |
| §8.2 Review Analyzer | Findings, weaknesses, decisions in UI | V2-S3 |
| §8.3 Weakness + Note Handler | user_note editable per weakness | V2-S3 |
| §8.4 Review Iteration Handler | Tighten loop, previous_review_id | V2-S3 |
| §9 Provenance | Artifact inventory expandable, provenance chips | V2-S2, V2-S3 |
| §10.1 Review Full Details | All 7 sections, weakness interaction | V2-S3 |
| §8.5 Reconciliation Engine | Explicit reconcile step in UI | V2-S4 |
| §8.6 Coverage Mapper | 6-domain coverage table | V2-S4 |
| §8.7 Proposal Builder | Proposal data pack generation | V2-S4 |
| §8.8 Proposal Review Agent | 6-domain critique displayed | V2-S4 |
| §8.9 Forward Guidance | Next actions grounded in gaps | V2-S4 |
| §10.2 Proposal UI | Contextual workflow (not detached) | V2-S4 |
| §11.4 Reconciliation rules | User-explicit anchor + supplementals | V2-S4 |
| Phase lifecycle | Phase transitions, history | V2-S5 |
| Admin config | AI backend, storage mode, health | V2-S6 |

---

## Sprint Roadmap

| Sprint | Tab(s) | Priority | Depends On | PR |
|---|---|---|---|---|
| **V2-S1** | Ingest + Build Intelligence trigger | High | — | Next |
| **V2-S2** | Intelligence view + Versions (complete) | High | V2-S1 | — |
| **V2-S3** | Reviews (complete): full detail, prompt builder, weakness, decisions, tighten, SME | High | V2-S2 | — |
| **V2-S4** | Proposal/Presales: full workflow | High | V2-S3 | — |
| **V2-S5** | Phases tab | Medium | V2-S4 | — |
| **V2-S6** | Admin + Settings | Medium | V2-S5 | — |

Total: 6 sprints. Each is a self-contained PR. No sprint bleeds into another.

---


## V2-S1 — Ingest Tab + Build Intelligence Trigger

**Goal:** Users can add artifacts, manage the artifact list, and trigger Build Intelligence
from v2. This is the entry point of the entire spec flow (§6.1).
**Priority:** High | **Depends on:** Nothing
**Files changed:** `static/v2/dashboard_v2.html` only

---

### What to build

The Ingest tab is the starting point of the spec flow. Without it users cannot
get artifacts into a version, which means no reviews, no proposals.

**Port from v1:** `viewIngest()` (v1 lines 999–1352) and its helpers:
`switchIngestTab()`, `renderMetadataFields()`, `submitUploadFile()`,
`submitPasteText()`, `submitFilePaths()`, `toggleArtifact()`, `deleteArtifact()`,
`buildIntelligence()`, `toggleLegacyFile()`.

---

### V2-S1-01 · Add Ingest to TABS and nav

| File | Change |
|---|---|
| `dashboard_v2.html` — `const TABS` | Change to `['dashboard','ingest','intelligence','versions','reviews']` |
| `dashboard_v2.html` — `render()` views map | Add `ingest:viewIngest, intelligence:viewIntelligence` |
| `dashboard_v2.html` — `renderHeader()` | Nav will auto-render from TABS array — no change needed |

**Acceptance:** Ingest and Intelligence appear as nav tabs. Clicking them does not crash (empty view is acceptable at this stage).

---

### V2-S1-02 · Artifact constants and category definitions

| File | Change |
|---|---|
| `dashboard_v2.html` — top of `<script>` state block | Copy `ARTIFACT_CATEGORIES` array from v1 (lines ~490–510). This is pure data — no logic change. |

**Acceptance:** `ARTIFACT_CATEGORIES` is defined and usable by `viewIngest`.

---

### V2-S1-03 · viewIngest() — three-panel ingest form

Port the full ingest form. Three sub-tabs: Upload File, Paste Text, File Paths.

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewIngest()` |
| `dashboard_v2.html` | Add `function switchIngestTab(tab)` |
| `dashboard_v2.html` | Add `function renderMetadataFields(prefix)` |
| `dashboard_v2.html` | Add `async function submitUploadFile()` |
| `dashboard_v2.html` | Add `async function submitPasteText()` |
| `dashboard_v2.html` | Add `async function submitFilePaths()` |

**API calls used** (all existing, no changes):
- `POST /api/v1/projects/{id}/artifacts/upload` — file upload
- `POST /api/v1/projects/{id}/artifacts` — paste/path ingest
- `GET /api/v1/projects/{id}/artifacts` — artifact list

**CSS:** Use v2 tokens (`var(--surface2)`, `.card`, `.btn`, `.tag-*`). Do not copy v1 `.form-row` styles — use v2 flex patterns instead.

**Acceptance:**
- Upload File sub-tab: category select, title field, file picker, submit button visible.
- Paste Text sub-tab: category select, title field, large textarea, submit button visible.
- File Paths sub-tab: textarea for paths, submit button visible.
- Submitting a valid form POSTs to the correct endpoint and shows a toast on success.
- Errors show inline without crashing the page.

---

### V2-S1-04 · Artifact list with include/exclude and delete

| File | Change |
|---|---|
| `dashboard_v2.html` | Artifact list rendered inside `viewIngest()` below the add-form |
| `dashboard_v2.html` | Add `async function toggleArtifact(artifactId, include)` |
| `dashboard_v2.html` | Add `async function deleteArtifact(artifactId)` |

**API calls used:**
- `PATCH /api/v1/projects/{id}/artifacts/{artifactId}` — toggle include
- `DELETE /api/v1/projects/{id}/artifacts/{artifactId}` — delete

**Acceptance:**
- Artifact list shows: title, category badge, include/exclude toggle, delete button.
- Toggling include/exclude persists and re-renders the list.
- Deleting an artifact removes it from the list with a toast.
- Count badge (e.g. `3/5 included`) updates after each toggle.

---

### V2-S1-05 · Build Intelligence trigger

| File | Change |
|---|---|
| `dashboard_v2.html` — `viewIngest()` | Add "Build Intelligence" button at bottom of artifact list. On click, calls `buildIntelligence()`. Shows spinner during run. On success, shows version ID created and prompts to switch to Intelligence tab. |
| `dashboard_v2.html` | Add `async function buildIntelligence()` |

**API call used:** `POST /api/projects/{id}/intelligence/build` (existing).

**Acceptance:**
- Build Intelligence button is only enabled when at least one artifact is included.
- Running shows a spinner and disables the button.
- On success: toast shows version ID, button re-enables.
- On failure: error shown inline.
- Switching to Versions tab after a successful build shows the new version.

---

### V2-S1 Exit Gate

- [ ] Ingest and Intelligence tabs appear in nav
- [ ] All three ingest sub-tabs (Upload, Paste, File Paths) functional
- [ ] Artifact list shows with include/exclude toggle and delete
- [ ] Build Intelligence triggers correctly and shows version ID on success
- [ ] v1 (`static/index.html`) unchanged and still functional
- [ ] No JS errors in browser console

---


## V2-S2 — Intelligence View + Versions Tab (Complete)

**Goal:** Users can see what was built from their artifacts, navigate the Version/Review
hierarchy with full detail, and set active reviews. Satisfies spec §8.1 (Version Context
Builder output) and spec §9 (artifact inventory visible in UI).
**Priority:** High | **Depends on:** V2-S1
**Files changed:** `static/v2/dashboard_v2.html` only

---

### V2-S2-01 · viewIntelligence() — findings and version context

Port `viewIntelligence()` from v1 (lines 1353–1529).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewIntelligence()` |

**What this shows:**
- Version and review context selector (reuse dashboard context selectors)
- Scope text from the selected version
- Findings breakdown per category (risks, assumptions, dependencies, constraints, action_items) pulled from the active review
- "No review yet" empty state when version exists but no review run
- Link to run a review (switches to Reviews tab)

**API calls used:**
- `GET /api/projects/{id}/hierarchy/metrics?version_id=&review_id=` (existing)
- `GET /api/projects/{id}/hierarchy/reviews/{rid}` (existing) — for findings detail

**Acceptance:**
- Selecting a version shows its scope text.
- Selecting a review shows its findings grouped by category.
- Each category shows item count and up to 5 items expandable.
- "Run Review" button switches to Reviews tab.

---

### V2-S2-02 · Versions tab — Decision Readiness badges

Extend the existing `viewVersions()` to add Decision Readiness badges per version
(spec §7, S7-01 pattern from v1).

| File | Change |
|---|---|
| `dashboard_v2.html` — `viewVersions()` version summary row | After the version label, add `<span id="readiness-badge-${ver.version_id}">…</span>` |
| `dashboard_v2.html` — after `viewVersions()` renders | Add `_populateReadinessBadges()` function that fetches `GET /api/projects/{id}/hierarchy/versions/{vid}/readiness` for each visible version and sets badge text + colour |

Badge colours: `🟢 High` = tag-green, `🟡 Medium` = tag-yellow, `🔴 Low` = tag-red.

**Acceptance:**
- Each version row shows a readiness badge after load (async, non-blocking).
- High = green, Medium = yellow, Low = red.
- Versions with no reviews show no badge.

---

### V2-S2-03 · Versions tab — Artifact inventory expandable

Add an expandable "Included Artifacts (N)" section inside each version's detail area
(spec §10.1 — Included Artifacts section).

| File | Change |
|---|---|
| `dashboard_v2.html` — version detail body in `viewVersions()` | After the buttons row, add `<details><summary>Included Artifacts (N)</summary>…</details>`. Populate from `ver.included_artifacts` array. Show: artifact name, category badge, type. |

**Acceptance:**
- Version with 3 artifacts shows "Included Artifacts (3)" collapsed by default.
- Expanding lists each artifact name and category.
- Version with no `included_artifacts` shows nothing.

---

### V2-S2-04 · Versions tab — Set Active Review

Add a "Set as Active" button per review row in the Versions tree so users can
explicitly promote a review without going to v1.

| File | Change |
|---|---|
| `dashboard_v2.html` — review row inside version body | Add `<button class="btn btn-xs btn-ghost">Set Active</button>` beside compare button |
| `dashboard_v2.html` | Add `async function setActiveReview(versionId, reviewId)` — calls `POST /api/projects/{id}/hierarchy/versions/{vid}/active-review` |

**API call used:** `POST /api/projects/{id}/hierarchy/versions/{vid}/active-review` with `{review_id}` (existing).

**Acceptance:**
- Clicking "Set Active" on a review updates the active badge on that version row.
- Toast confirms success.
- The previously active review loses its "active" badge.

---

### V2-S2-05 · Versions tab — View Review Detail trigger

Review rows in the Versions tree currently have no way to open full detail.
Add a "View Detail" button that opens `viewReviewDetail(rid)` inline within the tab.

| File | Change |
|---|---|
| `dashboard_v2.html` — review row | Add `<button class="btn btn-xs btn-outline">View Detail →</button>` |
| `dashboard_v2.html` | Clicking it calls `state._reviewDetailId = rid; state.tab = 'reviews'; render()` so the Reviews tab opens at full detail |

**Acceptance:**
- Clicking "View Detail" switches to the Reviews tab and scrolls to that review's full detail.
- Navigating back to Versions preserves the version tree state.

---

### V2-S2 Exit Gate

- [ ] Intelligence tab shows scope, findings per category, version/review selector
- [ ] Versions tab: Decision Readiness badge per version (async, non-blocking)
- [ ] Versions tab: Included Artifacts expandable section per version
- [ ] Versions tab: Set Active Review button functional
- [ ] Versions tab: View Review Detail button switches to Reviews tab
- [ ] v1 unchanged and functional

---


## V2-S3 — Reviews Tab (Complete)

**Goal:** The Reviews tab becomes the full decision-support workbench defined in spec §10.1.
This is the largest single sprint — it ports the entire review experience including
prompt builder, SME questions, tighten loop, full detail view, weakness interaction,
decision points, review strength panel, and progression diff.
**Priority:** High | **Depends on:** V2-S2
**Files changed:** `static/v2/dashboard_v2.html` only

---

### What the spec requires (§10.1)

Review Full Details must show immediately:
- Review ID, Version ID, Persona used, Prompt used, Top 3 risks, Status, Created date

Expandable sections:
- Included Artifacts
- Findings (per category)
- Weaknesses (with status dropdown + user_note textarea + provenance chip)
- Decision Points (with status dropdown)
- User Notes (prompt builder state breakdown)
- Raw output / extra detail

Weakness interaction: text · status · optional note · provenance chip.

---

### V2-S3-01 · viewReviewDetail(rid) — full detail view

Port `viewReviewDetail()` from v1 (lines 1917–2228). This is the core of the spec's
§10.1 requirement.

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewReviewDetail(rid)` |

**Sections to render (in order):**
1. **Metadata row** — Review ID, Version ID, R{N} badge, Follows: {prev_id} if set, Persona, Backend, Status badge, Baseline/Customised badge, Decision Readiness badge, Date
2. **Review Strength panel** — `renderReviewStrength(r)` (port F1 from v1 lines 4637–4722)
3. **Prompt Builder state** — collapsible, shows injected questions + user notes used
4. **Findings** — collapsible per category, items as `findings-item` rows with provenance chip if available
5. **Weaknesses** — collapsible; per weakness: text, status `<select>`, `<textarea>` for user_note (blur saves), provenance chip; calls `updateWeaknessStatus()`
6. **Missing Categories** — visible if any standard categories have zero findings
7. **Decision Points** — collapsible; per DP: text, category, status `<select>` calls `updateDecisionStatus()`; enriched decision cards via `renderDecisionPointsEngine(r)` (port F2 from v1 lines 4723–4766)
8. **Next Best Actions** — `renderNextBestActions(r)` (port F6 from v1 lines 4904–4966)
9. **Review Progression** — if `previous_review_id` set, fetch diff and render `renderReviewProgression(diff, prevId)` (port F3 from v1 lines 4767–4834)
10. **Tighten button** — "🔁 Tighten with SME Questions" sets `state._previousReviewId = rid` and scrolls to run-review form

**API calls:**
- `GET /api/projects/{id}/hierarchy/reviews/{rid}` — full review
- `GET /api/projects/{id}/hierarchy/reviews/{rid}/diff` — if prev set
- `GET /api/projects/{id}/hierarchy/versions/{vid}/readiness` — readiness badge

**Acceptance:**
- All 10 sections render for a review with full data.
- Empty sections (no weaknesses, no decisions) are hidden, not shown blank.
- Weakness status change persists (PATCH + toast).
- Weakness user_note saves on textarea blur.
- Decision status change persists (PATCH + toast).
- Progression diff shows Resolved / Improved / Still Open / New counts.
- Tighten button sets state and scrolls to the run form.

---

### V2-S3-02 · Reviews list — trigger full detail

Clicking a review row in the existing list opens full detail inline (not a new page).

| File | Change |
|---|---|
| `dashboard_v2.html` — `viewReviews()` review row | Replace the current collapsed `<details>` body with a button "Open Full Detail →" that calls `viewReviewDetail(rid)` and inserts the result below the list row. Alternatively push into `state._reviewDetailId` and re-render. Use the push approach for consistency: `state._reviewDetailId=rid; render()`. |
| `dashboard_v2.html` — `viewReviews()` | At top: if `state._reviewDetailId` is set, render `viewReviewDetail(state._reviewDetailId)` with a "← Back to List" button that clears `state._reviewDetailId` and re-renders. |

**Acceptance:**
- Clicking a review in the list opens full detail view with back button.
- Back button returns to the review list with sort/filter preserved.
- URL does not change (SPA state only).

---

### V2-S3-03 · Run Review form — in Reviews tab

The run-review form (persona select, AI backend select, prompt builder) must live in
the Reviews tab so users can run a new review from v2.

| File | Change |
|---|---|
| `dashboard_v2.html` — `viewReviews()` | Add a collapsible "Run New Review" card at the top of the Reviews tab |
| `dashboard_v2.html` | Add `async function runReview()` (port from v1 lines 2490–2610) |
| `dashboard_v2.html` | Add `function _getBaselinePrompt(persona)` — populates baseline preview |
| `dashboard_v2.html` | Prompt builder: three sections — (1) Baseline Prompt `<details>` read-only, (2) Injected Questions `<div id="injectedQuestions">` chip list, (3) User Notes `<textarea id="userNotes">` |
| `dashboard_v2.html` | Add `function _assemblePrompt()` — joins injected questions + user notes |
| `dashboard_v2.html` | Add `function _renderInjectedChips()` — renders removable chips |
| `dashboard_v2.html` | Add `function removeInjectedQuestion(idx)` — removes chip by index |
| `dashboard_v2.html` | Persona dropdown populated from `GET /api/personas` |
| `dashboard_v2.html` | Backend dropdown populated from `state.backends` |

**Previous Review ID wiring:**
- Hidden input `<input type="hidden" id="previousReviewId">` pre-populated when Tighten button is clicked.
- `runReview()` reads it and sends `previous_review_id` in POST body.
- After successful run: clears `previousReviewId`, re-renders list, shows new review at top.

**API calls:**
- `GET /api/personas` — for persona dropdown
- `POST /api/review` with `{project_id, roles, ai_backend, custom_prompt, previous_review_id, prompt_builder_state}`

**Acceptance:**
- Run Review card is collapsed by default.
- Selecting a persona shows baseline prompt preview.
- Running a review shows spinner, then new review appears in list.
- Running with `previousReviewId` set chains the review (`previous_review_id` in response).
- Prompt builder state saved on new review (visible in detail view).

---

### V2-S3-04 · SME Questions (Ask SME) panel

Port the Ask SME / Deep Dive flow from v1.

| File | Change |
|---|---|
| `dashboard_v2.html` — Run Review card | Add "Ask SME Questions" collapsible section above the Run button |
| `dashboard_v2.html` | Add `async function runDeepDive()` (port from v1 lines 2611–2700) |
| `dashboard_v2.html` | Add `function ddGroup(grp)` — renders one question group |
| `dashboard_v2.html` | Add `function addSelectedToPrompt()` — pushes selected questions to `state._injectedQuestions` and calls `_renderInjectedChips()` |
| `dashboard_v2.html` | Add `function _getSelectedDDItems()` — returns checked question texts, stripped of role prefix |
| `dashboard_v2.html` | When a `review_id` is set (from Tighten button), include it in the deep-dive POST body so gap-aware questions are generated |

**API call:** `POST /api/projects/{id}/deep-dive` with `{persona, review_id?}` (existing).

**Acceptance:**
- Ask SME panel is available before running a review (not gated on prior review).
- Running Ask SME shows grouped questions with checkboxes.
- Selecting questions and clicking "Add to Prompt" populates injected chips in the prompt builder.
- When triggered from Tighten, questions are more targeted (gap-aware via review_id).
- Decision-linked questions show the decision reference below the question text.

---

### V2-S3-05 · Render helper functions (port from v1)

These are pure render helpers. Port them verbatim from v1, adapting CSS class names only.

| Function | v1 lines | Purpose |
|---|---|---|
| `renderReviewStrength(r)` | 4637–4722 | Missing / Weak / Unresolved / Impact Areas (F1) |
| `renderDecisionPointsEngine(r)` | 4723–4766 | Enriched decision cards (F2) |
| `renderReviewProgression(diff, prevId)` | 4767–4834 | Resolved / Improved / Still Open / New (F3) |
| `renderNextBestActions(r)` | 4904–4966 | 3–5 executable actions from weaknesses + decisions (F6) |
| `updateWeaknessStatus(reviewId, wId, status)` | ~2216 | PATCH weakness status |
| `updateDecisionStatus(reviewId, dId, status)` | ~2204 | PATCH decision status |
| `renderCoverageAssessment(review)` | 1866–1916 | Coverage assessment block |

**CSS additions required in `dashboard_v2.html` `<style>` block:**
```
.rs-grid, .rs-cell, .rs-cell-header, .rs-item   (Review Strength)
.pr-bar, .pr-bar.not-ready, .pr-bar.partial, .pr-bar.ready  (Proposal Readiness)
.nba-item  (Next Best Actions)
.dp-card   (Decision Points Engine)
.prog-row  (Review Progression)
.prop-strength-area, .prop-strength-strong, .prop-strength-weak
.fb-map-tag
```
These are already validated by `tests/test_sprint8_regression.py`. Copy the CSS
definitions from v1 directly into a new `<style>` block in v2.

**Acceptance:**
- All 7 helper functions render without errors.
- Sprint 8 regression tests continue to pass against v1 (unchanged).

---

### V2-S3 Exit Gate

- [ ] Clicking any review in the list opens full detail view
- [ ] Full detail shows all 10 sections (metadata, strength, prompt state, findings, weaknesses, missing, decisions, next actions, progression, tighten button)
- [ ] Weakness status + user_note save via API
- [ ] Decision point status saves via API
- [ ] Run Review form functional in Reviews tab (persona, backend, prompt builder)
- [ ] Ask SME generates questions; selected questions populate injected chips
- [ ] Tighten button wires previousReviewId through to next review run
- [ ] Decision Readiness badge shown in review detail metadata row
- [ ] All Sprint 8 CSS classes present in v2
- [ ] v1 unchanged and functional

---


## V2-S4 — Proposal Tab (Complete Workflow)

**Goal:** The full proposal workflow defined in spec §10.2 is available in v2.
User path: select Version → select anchor review → optionally select supplementals
→ reconcile → generate proposal data pack → view coverage, decisions, risks,
forward guidance, next actions.
**Priority:** High | **Depends on:** V2-S3
**Files changed:** `static/v2/dashboard_v2.html` only

---

### What the spec requires (§10.2)

```
Primary path:
  1. Select Version
  2. Select anchor review
  3. Optionally select supplemental reviews
  4. Reconcile
  5. Generate proposal data pack

Proposal output must show:
  summary · coverage · decisions · risks · blockers · next actions · lightweight provenance
```

This is not a detached standalone generator. It is a contextual workflow.

---

### V2-S4-01 · Add Proposal tab to TABS

| File | Change |
|---|---|
| `dashboard_v2.html` — `const TABS` | Add `'proposal'` → `['dashboard','ingest','intelligence','versions','reviews','proposal']` |
| `dashboard_v2.html` — `render()` views map | Add `proposal: viewPresales` |

**Note:** The backend calls this presales internally. The v2 tab is labelled "Proposal" to match the spec language. Wire to `viewPresales()`.

---

### V2-S4-02 · viewPresales() — contextual proposal workflow

Port `viewPresales()` from v1 (lines 3154–3719) and its helper functions.

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewPresales()` |

**Sections in order:**
1. **Pre-sales Overview card** — proposal name, client, current version status, active review link
2. **Decision Readiness indicator** — fetched for the selected version (informational, non-blocking)
3. **Create / Update Proposal section** — version selector, anchor review selector, supplemental review checkboxes (when version has >1 review), notes field
4. **Reconcile button** — "Reconcile Reviews" (calls `POST /api/projects/{id}/hierarchy/reconcile`). Shows consensus count and conflict count inline. Optional — generation can proceed without it.
5. **Generate Proposal Document button** — calls generate endpoint. Shows spinner.
6. **Proposal document view** — rendered inline after generation (see V2-S4-04)
7. **Feedback section** — capture feedback against current proposal version
8. **Version history** — list of all proposal versions with status badges

**API calls:**
- `GET /api/projects/{id}/presales/summary`
- `GET /api/projects/{id}/presales/feedback`
- `GET /api/projects/{id}/hierarchy/versions` — for version selector
- `GET /api/projects/{id}/hierarchy/reviews?version_id=` — for review selectors
- `GET /api/projects/{id}/hierarchy/versions/{vid}/readiness`
- `POST /api/projects/{id}/hierarchy/reconcile` — explicit reconcile step
- `POST /api/projects/{id}/proposals` — create proposal
- `POST /api/projects/{id}/proposals/versions` — add version
- `POST /api/projects/{id}/proposals/generate` — generate document
- `GET /api/projects/{id}/proposals/document?proposal_ver_id=` — fetch generated doc

---

### V2-S4-03 · showCreateProposal() and submitCreateProposal()

Port `showCreateProposal()` (v1 line 3720) and `submitCreateProposal()` (v1 line 3733).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `function showCreateProposal()` — shows/expands the create form |
| `dashboard_v2.html` | Add `async function submitCreateProposal()` — validates + POSTs |
| `dashboard_v2.html` | Add `async function submitAddVersion()` (v1 line 3858) — adds new version to existing proposal |

**Decision Readiness warning (non-blocking):**
When the selected version has readiness `Low`, show a banner:
"⚠ This version has unresolved decision points. You can proceed — review before sign-off."
A "Proceed" button dismisses the banner and enables Generate. Per spec §11 and AR-01: user is final authority.

**Acceptance:**
- Creating a proposal with a version and anchor review POSTs correctly.
- Low readiness shows warning banner (non-blocking).
- Submitting with confirmed Low readiness creates the proposal and shows success.

---

### V2-S4-04 · Proposal document view — all synthesis sections

Port the full proposal document display from v1 (v1 lines 4965–5248 and helpers).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function showProposalDoc(proposalVerId)` — fetches and renders the document |

**Sections to render (in order):**
1. **Executive Summary** — plain text
2. **Scope** — plain text
3. **Coverage Assessment** — 6-domain table (Addressed/Partial/Not Yet Addressed) — `renderCoverageAssessment()` already ported in V2-S3-05
4. **Delivery Phases** — phase list with duration
5. **Risks** — risk table with category, impact, probability, mitigation
6. **Assumptions** — assumption list with category
7. **Decision Summary** — Confirmed / Open / Sign-off Blockers — `renderDecisionSummary(doc)` (port from v1)
8. **Proposal Strength Summary** — `renderProposalStrength(review)` (F7 — port from v1 lines 4967–5070)
9. **Proposal Review Pass** — 6-domain collapsible critique — port `renderProposalReviewPass(doc)` from v1
10. **Forward Guidance** — recommended next actions — port `renderForwardGuidance(doc)` from v1

**Acceptance:**
- All 10 sections render for a generated document.
- Empty sections (no conflicts, no guidance) hidden gracefully.
- "Generate again" button re-runs generation on same version/review.

---

### V2-S4-05 · Reconcile step in Proposal workflow

The reconcile button between review selection and Generate (spec §10.2 step 4).

| File | Change |
|---|---|
| `dashboard_v2.html` — proposal form | Button: "🔀 Reconcile Reviews" visible after review selection |
| `dashboard_v2.html` | Add `async function reconcileReviews()` — POSTs to `/reconcile`, shows result inline: "N consensus points · M conflicts" |
| `dashboard_v2.html` — `submitCreateProposal()` | If reconcile was run, include `anchor_review_id` + `supplemental_review_ids` in the generate call body |

**API call:** `POST /api/projects/{id}/hierarchy/reconcile` with `{anchor_review_id, supplemental_review_ids}` (this endpoint is created in MASTER_SPRINT_PLAN S11).

**Note:** If S11 is not yet complete, this button is shown greyed-out with tooltip "Reconcile (coming soon)". Single-review proposals work without it.

**Acceptance:**
- Reconcile button visible after anchor review is selected.
- Running reconcile shows consensus / conflict summary inline.
- Reconcile is optional — proceeding without it still generates the proposal.

---

### V2-S4-06 · Feedback capture

Port the feedback capture form from v1 (`submitCaptureFeedback()`, `openCaptureFeedback()`, v1 lines 3970–4106).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `function openCaptureFeedback()` |
| `dashboard_v2.html` | Add `async function submitCaptureFeedback()` |

**API call:** `POST /api/projects/{id}/presales/feedback` (existing).

**Acceptance:**
- "Capture Feedback" button visible on the Proposal tab.
- Submitting feedback with accepted/rejected/concerns text POSTs correctly.
- New feedback item appears in the feedback list with status badge.

---

### V2-S4-07 · Proposal Strength + Forward Guidance render helpers

Port the remaining display helpers not covered by V2-S3-05.

| Function | v1 lines | Purpose |
|---|---|---|
| `renderProposalReviewPass(doc)` | ~5115 | 6-domain critique collapsible |
| `renderCoverageTable(doc)` | ~5148 | Domain coverage table |
| `renderDecisionSummary(doc)` | ~5186 | Confirmed / Open / Blockers |
| `renderForwardGuidance(doc)` | ~5213 | 5 collapsible guidance sections |
| `renderProposalStrength(review)` | 4967–5070 | Strong/Weak areas + risk-to-sign-off |

**Acceptance:**
- All functions render without errors on a generated document with data.
- Empty states (no decisions, no guidance) show "None identified" not blank sections.

---

### V2-S4 Exit Gate

- [ ] Proposal tab appears in nav
- [ ] Pre-sales overview shows proposal name, version, status
- [ ] Version + anchor review selectors functional
- [ ] Supplemental review checkboxes shown when version has >1 review
- [ ] Decision Readiness warning shown (non-blocking) for Low versions
- [ ] Generate creates/updates proposal and shows document
- [ ] All 10 document sections render (summary, scope, coverage, phases, risks, assumptions, decisions, strength, review pass, forward guidance)
- [ ] Reconcile button present (active if S11 complete, greyed if not)
- [ ] Feedback capture form functional
- [ ] v1 unchanged and functional

---


## V2-S5 — Phases Tab

**Goal:** Users can view the project phase lifecycle, transition between phases, and
see a history of phase transitions in v2.
**Priority:** Medium | **Depends on:** V2-S4
**Files changed:** `static/v2/dashboard_v2.html` only

---

### V2-S5-01 · Add Phases tab to TABS

| File | Change |
|---|---|
| `dashboard_v2.html` — `const TABS` | Add `'phases'` → `[..., 'phases']` |
| `dashboard_v2.html` — `render()` views map | Add `phases: viewPhases` |

---

### V2-S5-02 · viewPhases() — phase lifecycle view

Port `viewPhases()` (v1 lines 3055–3114) and `viewPhaseDetail(phaseId)` (v1 lines 3115–3153).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewPhases()` |
| `dashboard_v2.html` | Add `async function viewPhaseDetail(phaseId)` |
| `dashboard_v2.html` | Add `async function transitionPhase(phaseId)` |

**What to show:**
- Phase bar at top: Pre-sales → Design → Delivery → Support (use existing `.phase-bar` and `.phase-step` CSS in v2)
- Current phase highlighted
- Per phase: version count, review count, entered/exited dates
- "Transition to this phase" button (non-destructive; logs the change)
- Phase detail: versions in that phase as a list

**API calls:**
- `GET /api/projects/{id}/hierarchy` — for tree
- `POST /api/projects/{id}/phase-transition` with `{phase_id}` (existing)

**Acceptance:**
- Phase bar shows all 4 phases; current phase is highlighted.
- Clicking a phase shows its versions and review count.
- Transition button changes the current phase and re-renders.
- Phases with no versions show an empty state (not an error).

---

### V2-S5 Exit Gate

- [ ] Phases tab appears in nav
- [ ] Phase bar shows all 4 phases with current highlighted
- [ ] Phase detail shows version list
- [ ] Phase transition functional
- [ ] v1 unchanged

---

## V2-S6 — Admin + Settings Tab

**Goal:** Users can configure AI backends, view system health, and manage storage mode
from v2. Required for switching from `files_only` to an AI backend.
**Priority:** Medium | **Depends on:** V2-S5
**Files changed:** `static/v2/dashboard_v2.html` only

---

### V2-S6-01 · Add Admin tab to TABS

| File | Change |
|---|---|
| `dashboard_v2.html` — `const TABS` | Add `'admin'` → `[..., 'admin']` |
| `dashboard_v2.html` — `render()` views map | Add `admin: viewAdmin` |

---

### V2-S6-02 · viewAdmin() — system health and storage

Port `viewAdmin()` from v1 (lines 4180–4441).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewAdmin()` |

**Sections:**
1. **System Health** — last intelligence run status, API connectivity (backend configured/not)
2. **Storage Mode** — SQLite toggle, file dual-write toggle
3. **AI Backend Configuration** — per-backend API key inputs with save
4. **Auto-archive suggestions** — projects not accessed recently
5. **Lifecycle logs** — recent system events

**API calls:** `GET /api/admin/config`, `GET /api/admin/health`, `GET /api/admin/lifecycle`, `POST /api/admin/config`, `GET /api/admin/auto-archive-suggestions` (all existing).

**Acceptance:**
- Admin tab shows system health, last run status, backend config.
- Saving an API key POSTs to `/api/admin/config` and shows toast.
- Storage mode toggles update config and re-render.

---

### V2-S6-03 · viewSettings() — user preferences

Port `viewSettings()` from v1 (lines 4442–4636).

| File | Change |
|---|---|
| `dashboard_v2.html` | Add `async function viewSettings()` |
| `dashboard_v2.html` — `const TABS` | Settings can be reached from Admin tab (link) rather than its own tab — reduces nav clutter |

**Sections:**
- Default persona selector
- Default AI backend selector
- Project name edit
- Project description

**Acceptance:**
- Default persona and backend save to admin config.
- Project name edit updates the header on save.

---

### V2-S6 Exit Gate

- [ ] Admin tab shows health, backend config, storage mode
- [ ] Saving API key persists and shows toast
- [ ] Storage mode toggles functional
- [ ] Settings accessible from Admin tab
- [ ] All 6 complete TABS working: dashboard, ingest, intelligence, versions, reviews, proposal, phases, admin
- [ ] Full spec flow works end-to-end in v2: Ingest → Build → Review → Tighten → Proposal
- [ ] v1 unchanged

---


---

## File Impact Summary

Every sprint touches exactly one file: `static/v2/dashboard_v2.html`.
No backend changes. No new files unless noted.

| Sprint | Functions added to v2 | CSS additions |
|---|---|---|
| V2-S1 | `viewIngest`, `switchIngestTab`, `renderMetadataFields`, `submitUploadFile`, `submitPasteText`, `submitFilePaths`, `toggleArtifact`, `deleteArtifact`, `buildIntelligence` | None (existing v2 tokens sufficient) |
| V2-S2 | `viewIntelligence`, `_populateReadinessBadges`, `setActiveReview` + version detail HTML patches | None |
| V2-S3 | `viewReviewDetail`, `runReview`, `runDeepDive`, `ddGroup`, `addSelectedToPrompt`, `_getSelectedDDItems`, `_assemblePrompt`, `_renderInjectedChips`, `removeInjectedQuestion`, `_getBaselinePrompt`, `updateWeaknessStatus`, `updateDecisionStatus`, `renderReviewStrength`, `renderDecisionPointsEngine`, `renderReviewProgression`, `renderNextBestActions`, `renderCoverageAssessment` | `.rs-grid`, `.rs-cell`, `.rs-cell-header`, `.rs-item`, `.pr-bar` variants, `.nba-item`, `.dp-card`, `.prog-row`, `.prop-strength-*`, `.fb-map-tag` |
| V2-S4 | `viewPresales`, `showCreateProposal`, `submitCreateProposal`, `submitAddVersion`, `reconcileReviews`, `showProposalDoc`, `openCaptureFeedback`, `submitCaptureFeedback`, `renderProposalReviewPass`, `renderCoverageTable`, `renderDecisionSummary`, `renderForwardGuidance`, `renderProposalStrength` | None (Sprint 3 CSS covers these) |
| V2-S5 | `viewPhases`, `viewPhaseDetail`, `transitionPhase` | None (`.phase-bar`, `.phase-step` already in v2) |
| V2-S6 | `viewAdmin`, `viewSettings` | `.backend-grid`, `.backend-chip` (copy from v1) |

**Line count estimate for `dashboard_v2.html` after all sprints:**
Current: ~1088 lines. Adding ~4200 lines of ported JS/HTML. Target: ~5300 lines.
This is the same order of magnitude as v1 (5248 lines). Acceptable for a single-file SPA.

---

## Spec Compliance Check After All Sprints

| Spec Section | Requirement | Covered by |
|---|---|---|
| §6.1 Ingest and Version | User knows artifacts included, trusts context | V2-S1 |
| §6.2 Review | Persona, prompt, top risks immediately visible | V2-S3 |
| §6.3 Review Iteration | Build on prior review deliberately | V2-S3 |
| §6.4 Reconciliation | Combine perspectives without losing clarity | V2-S4 |
| §6.5 Proposal Output | Reusable intelligence pack, coverage, next actions | V2-S4 |
| §8.1 Version Context Builder | Artifact inventory, provenance-ready refs | V2-S1, V2-S2 |
| §8.2 Review Analyzer | All finding categories + weaknesses + decisions | V2-S3 |
| §8.3 Weakness + Note Handler | text + status + user_note + provenance chip | V2-S3 |
| §8.4 Review Iteration Handler | Explicit chain, no overwrite, persona change | V2-S3 |
| §8.5 Reconciliation Engine | Explicit user-selected reviews, provenance | V2-S4 |
| §8.6 Coverage Mapper | 6-domain, Addressed/Partial/Not Yet | V2-S4 |
| §8.7 Proposal Builder | 13-section data pack | V2-S4 |
| §8.8 Proposal Review Agent | 6-domain critique | V2-S4 |
| §8.9 Forward Guidance Agent | Grounded in unresolved items only | V2-S4 |
| §9 Provenance | Artifact inventory section, provenance chips | V2-S2, V2-S3 |
| §10.1 Review Full Details | All 7 sections + weakness interaction | V2-S3 |
| §10.2 Proposal UI | Contextual workflow, not detached | V2-S4 |
| §11 Business Logic Rules | All version/review/iteration/proposal rules | Backend (done) |

**After V2-S4 completes:** All spec sections §6–§11 are covered in v2.
V2-S5 and V2-S6 add operational completeness (phases, admin). Not required for spec
core intent but required for a fully usable product.

---

## Risks and Sequencing Notes

| Risk | Sprint | Mitigation |
|---|---|---|
| V2-S3 is the largest sprint (~1800 lines added) | V2-S3 | Split into two PRs if needed: S3a = detail view + run form; S3b = SME + helpers |
| Reconcile endpoint may not exist when V2-S4 starts | V2-S4 | Show button greyed with tooltip if MASTER_SPRINT_PLAN S11 not yet merged |
| v2 separate JS modules (api.js, state.js) may need extension | V2-S3 | Port inline into dashboard_v2.html first; refactor into modules later if needed |
| CSS class conflicts between v1 and v2 ports | V2-S3 | All new classes use specific prefixes (`.rs-`, `.pr-`, `.dp-`, `.nba-`) — no conflicts |
| `ARTIFACT_CATEGORIES` constant must match v1 exactly | V2-S1 | Copy verbatim, do not retype |
| `renderMetadataFields` uses DOM ID assumptions | V2-S1 | Use prefixes (`upload`, `paste`, `path`) as in v1 — same API, same IDs |

---

## What This Plan Does NOT Include

The following are explicitly out of scope for this plan per the spec (§2):

- **Client-specific proposal formatting** — spec says "not in scope"
- **Microservices or separate orchestration** — single-container constraint
- **v1 changes** — v1 is frozen as the fallback; no changes required
- **New backend work** — all API endpoints are complete; this is UI-only
- **Diagrams tab in v2** — `viewDiagrams()` exists in v1 but spec does not reference it; add in a post-V2-S6 sprint if needed
- **Self-learning / retraining** — S7 prompt log is the foundation; no autonomous behaviour planned

---

## Relationship to MASTER_SPRINT_PLAN.md

The master plan covers backend sprints (S9–S12).
This plan covers v2 UI sprints (V2-S1–V2-S6).

They are **parallel workstreams** with one dependency:
- V2-S4 (Proposal tab) benefits from MASTER S11 (reconcile endpoint). If S11 is not
  complete before V2-S4, show the Reconcile button as inactive and activate it when
  S11 merges. All other V2 sprints are independent of the backend sprint roadmap.

**Recommended execution order if one developer:**
```
S9 → V2-S1 → V2-S2 → S10 → V2-S3 → V2-S4 → S11 → V2-S4 (activate reconcile) → V2-S5 → S12 → V2-S6
```

**Recommended execution order if two developers:**
```
Dev A: S9 → S10 → S11 → S12
Dev B: V2-S1 → V2-S2 → V2-S3 → V2-S4 → V2-S5 → V2-S6
```
Dev B's V2-S4 reconcile button activates when Dev A's S11 merges.

---

*This document is the single source of truth for all v2 UI delivery work.*
*Update this document when sprints complete or scope changes are agreed.*
