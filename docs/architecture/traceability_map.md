# Traceability Map

**Project Delivery Accelerator Engine — V2 Full Traceability**

> Maps every UI action to its logic path, API endpoint, data entity, and diagram reference. No orphan components. Naming is consistent across all layers.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `→` | Data/control flows to |
| `[file]` | Source file reference |
| `{entity}` | Data entity from data model |
| `GET/POST` | HTTP method |

---

## 1. UI → Logic → API → Data → Diagram Map

### 1.1 Page Load

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | `dashboard_v2.html` | `static/v2/dashboard_v2.html` | Entry point, served by server.py |
| **Logic** | `Dashboard.init()` | `static/v2/js/dashboard.js` | Bootstraps all components |
| **Logic** | `AppState.selectProject()` | `static/v2/js/state.js` | Sets initial project |
| **API** | `GET /api/projects` | `server.py → services/project.py` | Returns `{projects:[]}` |
| **Data** | `{Project}` | `models/project.py` | id, name, phase |
| **Diagram** | Application Flow §1 | `docs/architecture/application_flow.md` | Startup sequence |

---

### 1.2 Version Selection

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | Version dropdown | `static/v2/dashboard_v2.html` `#v2-version-select` | Header control |
| **UI** | Accordion header click | `static/v2/js/accordion.js` `onVersionHeaderClick()` | Expand/collapse |
| **UI** | Sidebar version click | `static/v2/js/dashboard.js` `onSidebarVersionClick()` | Left panel |
| **Logic** | `AppState.selectVersion()` | `static/v2/js/state.js` | Resets review + reviews[] |
| **Logic** | `Dashboard.onVersionChange()` | `static/v2/js/dashboard.js` | Calls fetchMetrics |
| **API** | `GET /hierarchy/metrics?version_id=` | `server.py → services/hierarchy.py` | Scoped metrics |
| **Data** | `{Version}` | `models/hierarchy.py → Version` | version_id, label, review_ids |
| **Data** | `{MetricsPayload}` | `models/hierarchy.py → get_metrics()` | risks, gaps, etc. |
| **Diagram** | Application Flow §Version Selection | `docs/architecture/application_flow.md` | Selection loop |
| **Diagram** | Sequence 2 | `docs/architecture/sequence_flows.md` | Full message sequence |

---

### 1.3 Review Selection → Drawer (Sprint 1: Full Details)

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | Review row click | `static/v2/js/accordion.js` `onReviewClick()` | Inside accordion — opens Full Details |
| **UI** | Sidebar review click | `static/v2/js/dashboard.js` `onSidebarReviewClick()` | Left panel |
| **Logic** | `AppState.selectReview()` | `static/v2/js/state.js` | Updates selectedReview |
| **Logic** | `AppState.openDrawer('review', data)` | `static/v2/js/state.js` | Sets drawerOpen=true |
| **Logic** | `Dashboard._syncDrawer()` | `static/v2/js/dashboard.js` | CSS class mutations |
| **Logic** | `ReviewDetail.renderReview(summary)` | `static/v2/js/review_detail.js` | Immediate render (Sprint 1) |
| **Logic** | `Dashboard._loadDrawerDetail()` | `static/v2/js/dashboard.js` | Async full fetch |
| **API** | `GET /hierarchy/reviews/{rid}` | `server.py → services/hierarchy.py` | Full review object |
| **Data** | `{Review}` | `models/hierarchy.py → Review` | findings, weaknesses, artifact_refs, prompt_used |
| **Diagram** | Application Flow §Review Selection | `docs/architecture/application_flow.md` | Drawer open flow |
| **Diagram** | Logic Flow §6 | `docs/architecture/logic_flow.md` | Drawer loading logic |

> **Sprint 1 rule:** clicking a review always opens Full Details. Compare is a secondary explicit button only — it never opens on review click.

---

### 1.4 Refresh (No Reload)

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | ↺ Refresh button | `static/v2/dashboard_v2.html` `#v2-refresh-btn` | Header control |
| **Logic** | `Dashboard.onRefresh()` | `static/v2/js/dashboard.js` | Calls loadAll |
| **Logic** | `AppState.set('loading', true)` | `static/v2/js/state.js` | Disables button |
| **API** | `GET /hierarchy` | `server.py → services/hierarchy.py` | Fresh tree |
| **API** | `GET /hierarchy/metrics` | `server.py → services/hierarchy.py` | Fresh metrics |
| **Logic** | `AppState.setData()` | `static/v2/js/state.js` | Sets lastUpdated |
| **Logic** | `Dashboard.renderAll()` | `static/v2/js/dashboard.js` | Re-renders all regions |
| **Diagram** | Application Flow §Refresh Loop | `docs/architecture/application_flow.md` | Refresh flow |
| **Diagram** | Sequence 4 | `docs/architecture/sequence_flows.md` | Full refresh sequence |

---

### 1.5 Expand / Collapse All

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | "Expand All" button | `static/v2/dashboard_v2.html` `#v2-expand-all-btn` | Section B header |
| **Logic** | `Dashboard.onExpandAll()` | `static/v2/js/dashboard.js` | Delegates to Accordion |
| **Logic** | `VersionAccordion.toggleExpandAll()` | `static/v2/js/accordion.js` | CSS class toggle |
| **Data** | No API call | — | Pure DOM state |
| **Diagram** | Sequence 6 | `docs/architecture/sequence_flows.md` | Toggle sequence |

---

### 1.6 Drawer Close

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | × button | `static/v2/dashboard_v2.html` `#v2-drawer-close` | Drawer header |
| **UI** | Esc key | `ui/v2/layout/MainLayout.js` `_handleKeydown()` | Keyboard shortcut |
| **Logic** | `AppState.closeDrawer()` | `static/v2/js/state.js` | drawerOpen=false |
| **Logic** | `Dashboard._syncDrawer(false)` | `static/v2/js/dashboard.js` | Removes CSS classes |
| **Data** | No API call | — | Pure state change |
| **Diagram** | Sequence 5 | `docs/architecture/sequence_flows.md` | Close sequence |

---

### 1.7 Weakness Note Persistence (Sprint 1)

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | Note textarea (blur) | `static/v2/js/review_detail.js` `onWeaknessNote()` | Per-weakness in Full Details drawer |
| **UI** | Status dropdown (change) | `static/v2/js/review_detail.js` `onWeaknessStatus()` | Per-weakness in Full Details drawer |
| **Logic** | `API.updateWeaknessNote()` | `static/v2/js/api.js` | POST to note endpoint |
| **Logic** | `API.updateWeaknessStatus()` | `static/v2/js/api.js` | POST to status endpoint |
| **API** | `POST /hierarchy/reviews/{rid}/weakness/{wid}/note` | `server.py → handlers/review.py` | Persists free-text note (Sprint 1) |
| **API** | `POST /hierarchy/reviews/{rid}/weakness/{wid}/status` | `server.py → handlers/review.py` | Persists status update |
| **Handler** | `handle_weakness_note()` | `handlers/review.py` | Reads `body["note"]` |
| **Service** | `update_weakness_note()` | `services/review.py` | Updates weakness dict in store |
| **Data** | `weakness.user_note` | `models/hierarchy.py → Review.weaknesses[]` | Stored within weakness JSON |
| **Diagram** | Logic Flow §8 | `docs/architecture/logic_flow.md` | Note + status persistence flow |

---

### 1.8 Review Iteration — Create New Review from Existing (Sprint 2)

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | "New Iteration" toggle button | `static/v2/js/review_detail.js` | Explicit user action — never automatic |
| **UI** | Persona select + prompt input | `static/v2/js/review_detail.js` | Inside `.ri-create-form` (hidden by default) |
| **UI** | "Create New Review" submit button | `static/v2/js/review_detail.js` | Triggers `onCreateIteration()` |
| **Logic** | `ReviewDetail.onToggleIterationForm(rid)` | `static/v2/js/review_detail.js` | Shows/hides iteration form |
| **Logic** | `ReviewDetail.onCreateIteration(btn)` | `static/v2/js/review_detail.js` | Collects persona + prompt, calls API |
| **Logic** | `API.createReviewIteration(pid, rid, persona, prompt)` | `static/v2/js/api.js` | POST to iterate endpoint |
| **API** | `POST /hierarchy/reviews/{rid}/iterate` | `server.py → handlers/review.py` | Creates new review with lineage *(Sprint 2)* |
| **Handler** | `handle_create_review_iteration()` | `handlers/review.py` | Reads `new_persona`, `custom_prompt` from body |
| **Service** | `create_review_iteration()` | `services/review.py` | Creates new review; base review unchanged |
| **Data** | `{Review}.previous_review_id` | `models/hierarchy.py → Review` | FK to base review; `""` for originals |
| **Data** | `{Review}.persona` | `models/hierarchy.py → Review` | New persona stored on new review only |
| **Data** | `{Review}.prompt_used` | `models/hierarchy.py → Review` | New prompt stored on new review only |
| **UI** | Lineage banner `.ri-lineage-banner` | `static/v2/js/review_detail.js` | Shown in drawer when `previous_review_id` present |
| **UI** | Result card `.ri-result-card` | `static/v2/js/review_detail.js` | Confirms new ID, persona, predecessor |
| **Diagram** | Application Flow §Review Iteration | `docs/architecture/application_flow.md` | Review iteration flow *(Sprint 2)* |

> **Sprint 2 invariants:**
> - `previous_review_id` is set **only** on the new review — the base is read-only.
> - If `new_persona` is omitted, the base review's persona is reused (`persona_changed = false`).
> - Open decision points from the base are carried forward into the new review.
> - Legacy reviews with `previous_review_id == ""` render safely — no banner shown.

---

## 2. Component Mapping

| V2 Component | File | Renders | Data Source | State Keys Read |
|--------------|------|---------|-------------|-----------------|
| Header | `ui/v2/components/Header.js` | Dropdowns, context label | AppState | projects, versions, selectedVersion, selectedReview |
| Sidebar | `ui/v2/components/Sidebar.js` | Version + review list | AppState | versions, selectedVersion, selectedReview |
| VersionAccordion | `static/v2/js/accordion.js` | Accordion items + review rows | versions[] | versions (via render param) |
| Cards | `ui/v2/components/Cards.js` | Snapshot metric tiles | MetricsPayload | metrics |
| ReviewDetail *(Sprint 1)* | `static/v2/js/review_detail.js` | Review Full Details drawer | API response (full review) | drawerEntity |
| ReviewDetail iteration form *(Sprint 2)* | `static/v2/js/review_detail.js` | Iteration form + lineage banner + result card | `API.createReviewIteration()` response | drawerEntity.previous_review_id |
| MainLayout | `ui/v2/layout/MainLayout.js` | CSS class mutations only | AppState events | drawerOpen, loading |
| Dashboard | `static/v2/js/dashboard.js` | Orchestrates all above | AppState + API | all |

> `ReviewDetail` is exposed as `window.ReviewDetail` and aliased as `window.DetailPanel` for backward compatibility with any remaining call sites.

---

## 3. API Endpoint → Component Mapping

| Endpoint | HTTP | Called By | Returns | Renders In |
|----------|------|-----------|---------|------------|
| `/api/projects` | GET | `API.fetchProjects()` | `Project[]` | Header project dropdown |
| `/api/projects/{pid}/hierarchy` | GET | `API.fetchHierarchy()` | `HierarchyPayload` | Sidebar, Accordion |
| `/api/projects/{pid}/hierarchy/metrics` | GET | `API.fetchMetrics()` | `MetricsPayload` | Snapshot Cards, Context Banner |
| `/api/projects/{pid}/hierarchy/versions` | GET | `API.fetchVersions()` | `Version[]` | Header version dropdown |
| `/api/projects/{pid}/hierarchy/reviews` | GET | `API.fetchReviews()` | `Review[]` | Header review dropdown |
| `/api/projects/{pid}/hierarchy/reviews/{rid}` | GET | `API.fetchReviewDetail()` | `Review (full)` | Detail Drawer — ReviewDetail |
| `/api/projects/{pid}/hierarchy/versions/{vid}` | GET | `API.fetchVersionDetail()` | `Version (full)` | Detail Drawer (version) |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status` | POST | `API.updateWeaknessStatus()` | `{updated, status}` | ReviewDetail weakness dropdown *(Sprint 1)* |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/note` | POST | `API.updateWeaknessNote()` | `{updated, user_note}` | ReviewDetail note textarea *(Sprint 1)* |
| `/api/projects/{pid}/hierarchy/reviews/{rid}/iterate` | POST | `API.createReviewIteration()` | `{review_id, previous_review_id, persona_used, persona_changed, iteration_number, created_at}` | ReviewDetail result card *(Sprint 2)* |

---

## 4. Data Entity → UI Mapping

| Entity | Attribute | Displayed In | Component |
|--------|-----------|--------------|-----------|
| `{Project}` | `name` | Header dropdown | `#v2-project-select` |
| `{Version}` | `version_id`, `label` | Header dropdown, Sidebar, Accordion header | Version controls |
| `{Version}` | `review_count` | Accordion header badge, Sidebar badge | VersionAccordion |
| `{Version}` | `active_review_id` | Accordion review "Active" badge | VersionAccordion |
| `{Review}` | `review_id`, `persona` | Accordion review row, Header review dropdown | Review rows |
| `{Review}` | `quality_status` | Status dot, badge | Review rows + ReviewDetail |
| `{Review}` | `total_findings` | Amber badge on review row | VersionAccordion |
| `{Review}` | `version_id` | Always-visible header in Full Details *(Sprint 1)* | ReviewDetail |
| `{Review}` | `persona` | Always-visible header in Full Details *(Sprint 1)* | ReviewDetail |
| `{Review}` | `prompt_used` | Expandable section in Full Details *(Sprint 1)* | ReviewDetail |
| `{Review}` | `findings.risks[0..2]` | Top 3 Risks — always visible *(Sprint 1)* | ReviewDetail |
| `{Review}` | `artifact_refs[]` | Provenance chips in Full Details *(Sprint 1)* | ReviewDetail |
| `{Review}` | `included_files[]` | Provenance fallback when artifact_refs absent *(Sprint 1)* | ReviewDetail |
| `{Review}` | `weaknesses[].status` | Status dropdown per weakness *(Sprint 1)* | ReviewDetail |
| `{Review}` | `weaknesses[].user_note` | Note textarea per weakness *(Sprint 1)* | ReviewDetail |
| `{Review}` | `decision_points[]` | Expandable section in Full Details *(Sprint 1)* | ReviewDetail |
| `{Review}` | `previous_review_id` | Lineage banner in Full Details drawer *(Sprint 2)* | ReviewDetail |
| `{Review}` | `persona` | Persona used shown in lineage result card *(Sprint 2)* | ReviewDetail |
| `{Review}` | `iteration_number` | Shown in result card after iteration *(Sprint 2)* | ReviewDetail |
| `{MetricsPayload}` | `total_versions` | Snapshot card | Cards.js |
| `{MetricsPayload}` | `total_reviews` | Snapshot card | Cards.js |
| `{MetricsPayload}` | `risks_identified` | Snapshot card (red) | Cards.js |
| `{MetricsPayload}` | `gaps_identified` | Snapshot card (amber) | Cards.js |
| `{MetricsPayload}` | `data_source` | Context banner | ContextBanner |
| `{Review}` | `findings{}` | Findings blocks (expandable) | ReviewDetail |
| `{Review}` | `weaknesses[]` | Weakness panel (expandable) | ReviewDetail |
| `{Review}` | `questions[]` | Open questions section | ReviewDetail |

---

## 5. Impact Analysis

> What breaks if a file changes?

| File Changed | Immediate Impact | Downstream Impact |
|--------------|-----------------|-------------------|
| `state.js` — change notify logic | All subscriber components stop updating | Full UI freezes on state changes |
| `api.js` — change endpoint path | Data fetch fails silently | Snapshot cards show stale/mock data |
| `accordion.js` — change `.expanded` class name | Accordion CSS transitions break | Layout broken (CSS targets that class) |
| `dashboard.js` — remove renderAll() | Components not re-rendered after state changes | Stale UI after project/version change |
| `server.py` — remove `_resolve_ui_version()` | `?ui=v2` param ignored | v2 unreachable via URL override |
| `services/hierarchy.py` — change `get_metrics()` response shape | MetricsPayload shape mismatch | Cards.js renders 0 for all values |
| `models/hierarchy.py` — rename `review_ids` | HierarchyStore breaks version→review links | Reviews not linked, active_review_id invalid |
| `theme.css` — remove `--primary` token | All primary-coloured elements lose colour | Accordion chevrons, badges, snapshot values |
| `review_detail.js` — remove `renderReview()` *(Sprint 1)* | Review Full Details drawer renders nothing | Users cannot see version/persona/risks/provenance |
| `review_detail.js` — remove `window.DetailPanel` alias *(Sprint 1)* | `dashboard.js` fallback call fails | Drawer shows empty on review click |
| `api.js` — remove `updateWeaknessNote` *(Sprint 1)* | Weakness notes cannot be saved | User annotations lost (UI still renders) |
| `db/database.py` — remove `artifact_refs` migration *(Sprint 1)* | New installs miss column; INSERT fails | Reviews with provenance cannot be stored |
| `services/review.py` — remove `create_review_iteration()` *(Sprint 2)* | POST /iterate returns 500 | Users cannot create new reviews from existing ones |
| `handlers/review.py` — remove `handle_create_review_iteration()` *(Sprint 2)* | Route silently 404s | Iteration form submit fails with no feedback |
| `review_detail.js` — remove `_renderIterationBanner()` *(Sprint 2)* | Lineage link invisible | Users cannot see which review an iteration was built from |
| `review_detail.js` — remove `_renderCreateIterationAction()` *(Sprint 2)* | Iteration form not rendered | Users cannot create new reviews from the drawer |
| `api.js` — remove `createReviewIteration` *(Sprint 2)* | Iteration form submit errors silently | New review never created; no user feedback |

---

## 6. Naming Consistency Audit

| Concept | Python (server/models) | JS (state/api) | HTML (template) | CSS (components) |
|---------|----------------------|----------------|-----------------|-----------------|
| Version identifier | `version_id` | `version_id` | `data-version-id` | `.accordion-version-id` |
| Review identifier | `review_id` | `review_id` | `data-review-id` | `.review-item-id` |
| Project identifier | `id` (Project) | `id` (projects[]) | `v2-project-select` value | — |
| Active review | `active_review_id` | `active_review_id` | `data-active` badge | `.active-review` |
| Quality status | `quality_status` | `quality_status` | `data-quality` | `.badge-green/amber/default` |
| Drawer open | `drawerOpen` (state) | `drawerOpen` | `#v2-drawer.open` | `.open` class |
| Loading | `loading` (state) | `loading` | `#v2-refresh-btn[disabled]` | `.spin` class |
| Version label | `label` | `label` | option text | `.accordion-version-label` |
| Artifact provenance | `artifact_refs` (Review) | `artifact_refs` | — | `.rd-prov-chip` *(Sprint 1)* |
| Weakness note | `weakness["user_note"]` | `user_note` | `rd-note-textarea` | `.rd-note-textarea` *(Sprint 1)* |
| Weakness status | `weakness["status"]` | `status` | `rd-status-select` | `.rd-status-select` *(Sprint 1)* |
| Review Full Details | `ReviewDetail` (JS module) | `window.ReviewDetail` | `review_detail.js` script | `.rd-*` prefix *(Sprint 1)* |
| Review iteration | `create_review_iteration()` (service) | `createReviewIteration()` (api.js) | `.ri-create-form` | `.ri-*` prefix *(Sprint 2)* |
| Previous review link | `previous_review_id` (Review) | `previous_review_id` (JS result) | `.ri-lineage-banner` | `.ri-lineage-base-id` *(Sprint 2)* |
| Persona used on iteration | `persona` (Review) | `persona_used` (result shape) | `.ri-persona-select` | `.ri-persona-changed-badge` *(Sprint 2)* |
